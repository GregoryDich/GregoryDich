-- Result feedback and the bounded automatic refund (contract §2, GTM §2.6), plugin
-- installs, user_facts, and what account deletion does to the free text (0005).
\set ON_ERROR_STOP on

-- helper: a captured job, finished now
create function pg_temp.succeeded_job(p_user uuid) returns uuid
language plpgsql as $$
declare
  v_job public.jobs;
begin
  v_job := public.create_job(p_user, '{}'::jsonb, '{}'::jsonb, null);
  perform public.start_job(v_job.id, 'worker');
  perform public.complete_job(v_job.id, '{"analysis":{"bpm":120}}'::jsonb);
  return v_job.id;
end;
$$;

do $$
declare
  v_user uuid := '00000000-0000-4000-8000-000000009301';
  v_other uuid := '00000000-0000-4000-8000-000000009302';
  v_job uuid;
  v_failed public.jobs;
  v_queued public.jobs;
  v_row public.job_feedback;
  v_count integer;
begin
  insert into auth.users (id, email)
  values (v_user, 'quality-feedback@test.local'), (v_other, 'quality-other@test.local');

  -- a thumbs-down on a fresh succeeded job refunds the credit, once
  v_job := pg_temp.succeeded_job(v_user);
  assert public.get_balance(v_user) = row(2, 0, 2)::public.credit_balance, 'capture';
  v_row := public.record_job_feedback(v_job, v_user, 'down', 'bleed', 'bass in the drums', 4200);
  assert v_row.job_id = v_job and v_row.user_id = v_user and v_row.rating = 'down'
     and v_row.reason = 'bleed' and v_row.note = 'bass in the drums'
     and v_row.drop_to_ready_ms = 4200 and v_row.refunded, 'feedback row';
  assert public.get_balance(v_user) = row(3, 0, 3)::public.credit_balance, 'refund landed';
  select count(*) into v_count from public.credit_ledger
   where job_id = v_job and entry_type = 'refund' and note = 'user:unusable:bleed'
     and source = 'job:' || v_job::text;
  assert v_count = 1, 'one refund row with the feedback reason';

  -- re-rating refreshes the row, keeps the timer when omitted, and refunds nothing more
  v_row := public.record_job_feedback(v_job, v_user, 'down', 'clicks', null, null);
  assert v_row.reason = 'clicks' and v_row.note is null and v_row.drop_to_ready_ms = 4200
     and v_row.refunded, 'refreshed row';
  v_row := public.record_job_feedback(v_job, v_user, 'up', null, null, null);
  assert v_row.rating = 'up' and v_row.refunded, 'a later thumbs-up keeps the refund flag';
  select count(*) into v_count from public.job_feedback where job_id = v_job;
  assert v_count = 1, 'one row per job';
  select count(*) into v_count from public.credit_ledger where job_id = v_job and entry_type = 'refund';
  assert v_count = 1, 'refund is idempotent';
  assert public.refund_job_for_feedback(v_job, v_user, 'bleed'), 'an already refunded job reports true';

  -- thumbs-up and `slow` never refund
  v_job := pg_temp.succeeded_job(v_user);
  v_row := public.record_job_feedback(v_job, v_user, 'up', null, null, null);
  assert not v_row.refunded, 'thumbs-up refunded';
  v_row := public.record_job_feedback(v_job, v_user, 'down', 'slow', null, null);
  assert not v_row.refunded, 'slow refunded';
  assert public.get_balance(v_user) = row(2, 0, 2)::public.credit_balance, 'balance after slow';

  -- no reason is still a refund, labelled unspecified
  v_row := public.record_job_feedback(v_job, v_user, 'down', null, null, null);
  assert v_row.refunded, 'unspecified reason refused';
  assert exists (select 1 from public.credit_ledger where job_id = v_job and entry_type = 'refund'
                    and note = 'user:unusable:unspecified'), 'unspecified label';

  -- the free-account lifetime bound: two automatic refunds, then support
  v_job := pg_temp.succeeded_job(v_user);
  v_row := public.record_job_feedback(v_job, v_user, 'down', 'midi_off', null, null);
  assert not v_row.refunded, 'third lifetime auto-refund for a free account was granted';
  assert public.get_balance(v_user) = row(2, 0, 2)::public.credit_balance, 'balance after refusal';
  -- a support refund does not count as automatic and does not change the bound
  perform public.refund_job(v_job, 'support: manual review');
  assert public.get_balance(v_user) = row(3, 0, 3)::public.credit_balance, 'support refund';

  -- 24 h window
  v_job := pg_temp.succeeded_job(v_user);
  update public.jobs set finished_at = now() - interval '25 hours' where id = v_job;
  assert not public.refund_job_for_feedback(v_job, v_user, 'bleed'), 'stale job refunded';

  -- a failed job takes feedback but has nothing to refund; a queued one is too early
  v_failed := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, null);
  perform public.fail_job(v_failed.id, '{"code":"worker_timeout","message":"late"}'::jsonb);
  v_row := public.record_job_feedback(v_failed.id, v_user, 'down', 'other', null, null);
  assert v_row.rating = 'down' and not v_row.refunded, 'failed job feedback';
  v_queued := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, null);
  begin
    perform public.record_job_feedback(v_queued.id, v_user, 'up', null, null, null);
    raise exception 'feedback on a queued job did not raise';
  exception when sqlstate 'P0409' then
    assert sqlerrm = 'conflict', sqlerrm;
  end;

  -- scoped to the owner
  begin
    perform public.record_job_feedback(v_failed.id, v_other, 'down', null, null, null);
    raise exception 'feedback on another user''s job did not raise';
  exception when sqlstate 'P0404' then
    assert sqlerrm = 'not_found', sqlerrm;
  end;
  begin
    perform public.refund_job_for_feedback(v_failed.id, v_other, 'bleed');
    raise exception 'refund of another user''s job did not raise';
  exception when sqlstate 'P0404' then null;
  end;

  -- validation
  begin
    perform public.record_job_feedback(v_failed.id, v_user, 'meh', null, null, null);
    raise exception 'bad rating accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.record_job_feedback(v_failed.id, v_user, 'down', 'ugly', null, null);
    raise exception 'bad reason accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.record_job_feedback(v_failed.id, v_user, 'down', null, repeat('x', 141), null);
    raise exception 'long note accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.record_job_feedback(v_failed.id, v_user, 'down', null, null, -1);
    raise exception 'negative timer accepted';
  exception when sqlstate '22023' then null;
  end;
end;
$$;

-- the 30-day allowance of a buyer: max(3, 20 % of the captures of the last 30 days)
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-000000009303';
  v_jobs uuid[] := '{}';
  v_refund uuid;
  i integer;
begin
  insert into auth.users (id, email) values (v_user, 'quality-buyer@test.local');
  perform public.record_purchase(v_user, 'lemonsqueezy', 'order-quality-1', 'pack_50', 900, 800, null, '{}'::jsonb, 'ls:order:quality-1');
  assert public.get_balance(v_user) = row(53, 0, 53)::public.credit_balance, 'pack landed';
  for i in 1..20 loop
    v_jobs := v_jobs || pg_temp.succeeded_job(v_user);
  end loop;
  -- 20 captures: 20 % is 4
  assert public.refund_job_for_feedback(v_jobs[1], v_user, 'bleed'), 'refund 1';
  assert public.refund_job_for_feedback(v_jobs[2], v_user, 'bleed'), 'refund 2';
  assert public.refund_job_for_feedback(v_jobs[3], v_user, 'bleed'), 'refund 3';
  assert public.refund_job_for_feedback(v_jobs[4], v_user, 'bleed'), 'refund 4';
  assert not public.refund_job_for_feedback(v_jobs[5], v_user, 'bleed'), 'fifth refund inside 30 days was granted';
  -- an automatic refund from a month ago no longer counts
  select id into v_refund from public.credit_ledger
   where user_id = v_user and entry_type = 'refund' order by seq limit 1;
  update public.credit_ledger set created_at = now() - interval '31 days' where id = v_refund;
  assert public.refund_job_for_feedback(v_jobs[6], v_user, 'bleed'), 'refund after the window moved';
  -- captures that old no longer widen the allowance either
  update public.credit_ledger set created_at = now() - interval '31 days'
   where user_id = v_user and entry_type = 'capture';
  assert not public.refund_job_for_feedback(v_jobs[7], v_user, 'bleed'), 'allowance did not shrink';
  -- but a job already refunded still answers true
  assert public.refund_job_for_feedback(v_jobs[1], v_user, 'bleed'), 'refunded job forgotten';
  assert public.get_balance(v_user) = row(38, 0, 38)::public.credit_balance, 'buyer balance';
end;
$$;

-- plugin installs and user_facts
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-000000009304';
  v_install public.plugin_installs;
  v_facts record;
  v_job uuid;
begin
  insert into auth.users (id, email) values (v_user, 'quality-installs@test.local');
  assert public.touch_plugin_install(v_user, '0.1.0', 'Ableton Live 12', null), 'first sight is true';
  assert not public.touch_plugin_install(v_user, '0.1.0', 'Ableton Live 12', 'macOS 15'), 'second sight is false';
  select * into v_install from public.plugin_installs
   where user_id = v_user and plugin_version = '0.1.0' and host = 'Ableton Live 12';
  assert v_install.os = 'macOS 15' and v_install.last_seen_at >= v_install.first_seen_at, 'touch updated the row';
  assert public.touch_plugin_install(v_user, '0.2.0', 'Ableton Live 12', 'macOS 15'), 'a new version is a new install';
  assert public.touch_plugin_install(v_user, '0.2.0', 'FL Studio 21', 'Windows 11'), 'a new host is a new install';
  assert (select count(*) from public.plugin_installs where user_id = v_user) = 3, 'install rows';
  begin
    perform public.touch_plugin_install(v_user, '', 'Live', null);
    raise exception 'empty version accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.touch_plugin_install(gen_random_uuid(), '0.1.0', 'Live', null);
    raise exception 'unknown profile accepted';
  exception when sqlstate 'P0404' then null;
  end;

  select * into v_facts from public.user_facts(v_user);
  assert v_facts.email = 'quality-installs@test.local' and v_facts.plan = 'free'
     and v_facts.morphs_total = 0 and v_facts.first_morph_at is null
     and v_facts.last_morph_at is null and not v_facts.has_purchased, format('fresh facts %s', v_facts);
  v_job := pg_temp.succeeded_job(v_user);
  v_job := pg_temp.succeeded_job(v_user);
  select * into v_facts from public.user_facts(v_user);
  assert v_facts.morphs_total = 2 and v_facts.first_morph_at <= v_facts.last_morph_at, 'facts after morphs';
  assert not exists (select 1 from public.user_facts(gen_random_uuid())), 'facts for an unknown profile';
end;
$$;

-- account deletion keeps ratings and scores, drops the words and the installs
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-000000009305';
  v_job uuid;
  v_nps public.nps_responses;
begin
  insert into auth.users (id, email) values (v_user, 'quality-erase@test.local');
  v_job := pg_temp.succeeded_job(v_user);
  perform public.record_job_feedback(v_job, v_user, 'up', null, 'lovely', 900);
  v_nps := public.submit_nps(v_user, 9, 'keep going');
  perform public.touch_plugin_install(v_user, '0.1.0', 'Live', 'macOS');
  perform public.delete_user_account(v_user);
  assert (select rating from public.job_feedback where job_id = v_job) = 'up', 'rating lost';
  assert (select note from public.job_feedback where job_id = v_job) is null, 'note kept';
  assert (select score from public.nps_responses where id = v_nps.id) = 9, 'score lost';
  assert (select comment from public.nps_responses where id = v_nps.id) is null, 'comment kept';
  assert not exists (select 1 from public.plugin_installs where user_id = v_user), 'installs kept';
  assert (select first_seen_at from public.profiles where id = v_user) is null, 'first_seen_at appeared';
end;
$$;

drop function pg_temp.succeeded_job(uuid);
