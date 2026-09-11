-- Job lifecycle (contract §2, §10): create_job idempotency and atomic reservation,
-- start/progress/complete/fail/cancel transitions, and the stale-job reaper.
\set ON_ERROR_STOP on

do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000d001';
  v_other uuid := '00000000-0000-4000-8000-00000000d002';
  v_job1 public.jobs;
  v_job2 public.jobs;
  v_job3 public.jobs;
  v_job public.jobs;
  v_bal public.credit_balance;
  v_count integer;
begin
  insert into auth.users (id, email)
  values (v_user, 'jobs@test.local'), (v_other, 'jobs-other@test.local');

  -- create_job reserves one credit and inserts the job atomically
  v_job1 := public.create_job(v_user, '{"stems":["bass"]}'::jsonb, '{"duration_seconds":30}'::jsonb, 'key-1');
  assert v_job1.status = 'queued' and v_job1.stage = 'upload' and v_job1.progress = 0
     and v_job1.options = '{"stems":["bass"]}'::jsonb and v_job1.input_meta = '{"duration_seconds":30}'::jsonb
     and v_job1.idempotency_key = 'key-1' and v_job1.started_at is null and v_job1.finished_at is null,
    'new job shape';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(3, 1, 2)::public.credit_balance, format('after create_job %s', v_bal);
  assert exists (select 1 from public.credit_ledger where job_id = v_job1.id and entry_type = 'reserve'),
    'create_job did not reserve';

  -- the same idempotency key returns the same job with no second reservation
  v_job := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, 'key-1');
  assert v_job.id = v_job1.id, 'replayed create_job returned a different job';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(3, 1, 2)::public.credit_balance, format('after replayed create_job %s', v_bal);
  select count(*) into v_count from public.jobs where user_id = v_user;
  assert v_count = 1, 'replayed create_job inserted a job';

  -- idempotency keys are scoped per user
  v_job := public.create_job(v_other, '{}'::jsonb, '{}'::jsonb, 'key-1');
  assert v_job.id <> v_job1.id and v_job.user_id = v_other, 'idempotency key leaked across users';

  v_job2 := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, 'key-2');
  v_job3 := public.create_job(v_user, null, null, null);
  assert v_job3.options = '{}'::jsonb and v_job3.input_meta = '{}'::jsonb and v_job3.idempotency_key is null,
    'null arguments default';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(3, 3, 0)::public.credit_balance, format('three queued jobs %s', v_bal);

  -- out of credits: the job row does not survive the failed reservation
  begin
    perform public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, 'key-4');
    raise exception 'create_job without credits did not raise';
  exception when sqlstate 'P0402' then
    assert sqlerrm = 'insufficient_credits', sqlerrm;
  end;
  select count(*) into v_count from public.jobs where user_id = v_user;
  assert v_count = 3, format('failed create_job left %s jobs', v_count);

  -- cancel_job: owner-scoped, queued only, idempotent
  begin
    perform public.cancel_job(v_job1.id, v_other);
    raise exception 'cancel by another user did not raise';
  exception when sqlstate 'P0404' then
    assert sqlerrm = 'not_found', sqlerrm;
  end;
  v_job := public.cancel_job(v_job1.id, v_user);
  assert v_job.status = 'cancelled' and v_job.finished_at is not null, 'cancel state';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(3, 2, 1)::public.credit_balance, format('after cancel %s', v_bal);
  assert exists (select 1 from public.credit_ledger where job_id = v_job1.id and entry_type = 'release'),
    'cancel did not release';
  v_job := public.cancel_job(v_job1.id, v_user);
  assert v_job.status = 'cancelled', 'replayed cancel';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(3, 2, 1)::public.credit_balance, format('after replayed cancel %s', v_bal);
  begin
    perform public.complete_job(v_job1.id, '{}'::jsonb);
    raise exception 'completing a cancelled job did not raise';
  exception when sqlstate 'P0409' then
    assert sqlerrm = 'conflict', sqlerrm;
  end;

  -- start_job / update_job_progress
  v_job := public.start_job(v_job2.id, 'worker-1');
  assert v_job.status = 'running' and v_job.started_at is not null and v_job.worker_ref = 'worker-1', 'start state';
  v_job := public.start_job(v_job2.id, null);
  assert v_job.status = 'running' and v_job.worker_ref = 'worker-1', 'redelivered start changed the job';
  begin
    perform public.cancel_job(v_job2.id, v_user);
    raise exception 'cancelling a running job did not raise';
  exception when sqlstate 'P0409' then
    assert sqlerrm = 'conflict', sqlerrm;
  end;
  v_job := public.update_job_progress(v_job2.id, 'separate', 0.35);
  assert v_job.stage = 'separate' and abs(v_job.progress - 0.35) < 1e-6, 'progress update';
  v_job := public.update_job_progress(v_job2.id, null, 0.5);
  assert v_job.stage = 'separate' and abs(v_job.progress - 0.5) < 1e-6, 'progress update must keep the stage';
  v_job := public.update_job_progress(v_job2.id, 'transcribe', 7);
  assert v_job.stage = 'transcribe' and v_job.progress = 1, 'progress is clamped';

  -- complete_job captures the credit and decorates the result
  v_job := public.complete_job(v_job2.id, '{"analysis":{"bpm":124}}'::jsonb);
  assert v_job.status = 'succeeded' and v_job.stage = 'done' and v_job.progress = 1
     and v_job.finished_at is not null and v_job.expires_at > now() + interval '23 hours', 'complete state';
  assert v_job.result -> 'analysis' = '{"bpm":124}'::jsonb, 'result payload lost';
  assert (v_job.result ->> 'credits_charged')::integer = 1
     and (v_job.result ->> 'balance_after')::integer = 2
     and (v_job.result ->> 'job_id')::uuid = v_job2.id
     and (v_job.result ->> 'expires_at')::timestamptz = v_job.expires_at, 'result decoration';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(2, 1, 1)::public.credit_balance, format('after complete %s', v_bal);
  v_job := public.complete_job(v_job2.id, '{"changed":true}'::jsonb);
  assert v_job.result -> 'analysis' = '{"bpm":124}'::jsonb and not (v_job.result ? 'changed'),
    'replayed complete changed the result';
  assert public.get_balance(v_user) = row(2, 1, 1)::public.credit_balance, 'replayed complete charged again';
  begin
    perform public.fail_job(v_job2.id, '{"code":"late"}'::jsonb);
    raise exception 'failing a succeeded job did not raise';
  exception when sqlstate 'P0409' then null;
  end;
  v_job := public.update_job_progress(v_job2.id, 'upload', 0);
  assert v_job.stage = 'done' and v_job.progress = 1, 'late progress update was applied';

  -- fail_job releases the credit, idempotent
  v_job := public.fail_job(v_job3.id, '{"code":"worker_error","message":"boom"}'::jsonb);
  assert v_job.status = 'failed' and v_job.error ->> 'code' = 'worker_error' and v_job.finished_at is not null,
    'fail state';
  assert public.get_balance(v_user) = row(2, 0, 2)::public.credit_balance, 'fail did not release';
  v_job := public.fail_job(v_job3.id, '{"code":"other"}'::jsonb);
  assert v_job.error ->> 'code' = 'worker_error', 'replayed fail overwrote the error';
  assert public.get_balance(v_user) = row(2, 0, 2)::public.credit_balance, 'replayed fail released twice';
  begin
    perform public.start_job(v_job3.id, 'worker-2');
    raise exception 'starting a failed job did not raise';
  exception when sqlstate 'P0409' then null;
  end;

  -- unknown ids
  begin
    perform public.complete_job(gen_random_uuid(), '{}'::jsonb);
    raise exception 'completing an unknown job did not raise';
  exception when sqlstate 'P0404' then null;
  end;
  begin
    perform public.fail_job(gen_random_uuid(), '{}'::jsonb);
    raise exception 'failing an unknown job did not raise';
  exception when sqlstate 'P0404' then null;
  end;
  begin
    perform public.start_job(gen_random_uuid(), null);
    raise exception 'starting an unknown job did not raise';
  exception when sqlstate 'P0404' then null;
  end;
  begin
    perform public.update_job_progress(gen_random_uuid(), 'done', 1);
    raise exception 'progress on an unknown job did not raise';
  exception when sqlstate 'P0404' then null;
  end;
  begin
    perform public.create_job(gen_random_uuid(), '{}'::jsonb, '{}'::jsonb, null);
    raise exception 'create_job for an unknown user did not raise';
  exception when sqlstate 'P0404' then null;
  end;

  -- a queued job may complete without start_job; a worker-supplied expires_at is kept
  v_job := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, 'key-5');
  v_job := public.complete_job(v_job.id, jsonb_build_object('expires_at', '2030-01-01T00:00:00Z'));
  assert v_job.status = 'succeeded' and v_job.started_at is not null
     and v_job.expires_at = '2030-01-01T00:00:00Z'::timestamptz
     and v_job.result ->> 'expires_at' = '2030-01-01T00:00:00Z', 'queued -> succeeded';
  assert public.get_balance(v_user) = row(1, 0, 1)::public.credit_balance, 'balance after direct completion';

  -- refund of a completed job flows back through the ledger
  assert public.refund_job(v_job.id, 'bad output') = row(2, 0, 2)::public.credit_balance, 'refund of job';
end;
$$;

-- reap_stale_jobs releases reservations of jobs stuck in running
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000d003';
  v_stuck public.jobs;
  v_fresh public.jobs;
  v_queued public.jobs;
  v_job public.jobs;
begin
  insert into auth.users (id, email) values (v_user, 'reaper@test.local');
  v_stuck := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, 'stuck');
  v_fresh := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, 'fresh');
  v_queued := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, 'queued');
  perform public.start_job(v_stuck.id, 'dead-worker');
  perform public.start_job(v_fresh.id, 'live-worker');
  update public.jobs set started_at = now() - interval '2 hours' where id = v_stuck.id;
  assert public.get_balance(v_user) = row(3, 3, 0)::public.credit_balance, 'reaper setup';

  assert public.reap_stale_jobs(3600) = 1, 'reaper count';
  select * into v_job from public.jobs where id = v_stuck.id;
  assert v_job.status = 'failed' and v_job.error ->> 'code' = 'worker_timeout' and v_job.finished_at is not null,
    'stuck job state';
  assert (select status from public.jobs where id = v_fresh.id) = 'running', 'fresh running job was reaped';
  assert (select status from public.jobs where id = v_queued.id) = 'queued', 'queued job was reaped';
  assert public.get_balance(v_user) = row(3, 2, 1)::public.credit_balance, 'reaper released exactly one credit';
  assert public.reap_stale_jobs(3600) = 0, 'reaper is not idempotent';

  -- a late completion from the dead worker is rejected and cannot charge
  begin
    perform public.complete_job(v_stuck.id, '{}'::jsonb);
    raise exception 'late completion of a reaped job did not raise';
  exception when sqlstate 'P0409' then null;
  end;
  assert public.get_balance(v_user) = row(3, 2, 1)::public.credit_balance, 'late completion charged';

  -- a job the worker never picked up holds its credit forever unless the reaper releases
  -- it too; queued jobs wait the longer p_queued_timeout_seconds grace first
  update public.jobs set created_at = now() - interval '2 hours' where id = v_queued.id;
  assert public.reap_stale_jobs(3600) = 0, 'queued job reaped before its own grace';
  assert public.reap_stale_jobs(3600, 600) = 1, 'queued job was not reaped';
  select * into v_job from public.jobs where id = v_queued.id;
  assert v_job.status = 'failed' and v_job.error ->> 'code' = 'worker_timeout'
     and v_job.error ->> 'message' = 'no completion within 600 seconds'
     and v_job.finished_at is not null, 'reaped queued job state';
  assert public.get_balance(v_user) = row(3, 1, 2)::public.credit_balance,
    'reaping the queued job did not release its credit';
  assert public.reap_stale_jobs(3600, 600) = 0, 'queued reaper is not idempotent';
  begin
    perform public.reap_stale_jobs(3600, 0);
    raise exception 'zero queued timeout accepted';
  exception when sqlstate '22023' then null;
  end;

  begin
    perform public.reap_stale_jobs(0);
    raise exception 'zero timeout accepted';
  exception when sqlstate '22023' then null;
  end;
end;
$$;
