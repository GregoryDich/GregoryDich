-- The growth_daily view and status_last_24h() (contract §14; GTM Appendix C §6), and
-- profiles.first_seen_at as the API stamps it. Earlier test files leave jobs finished today,
-- so today's numbers are checked against the window's definition and as deltas; the rows
-- placed two days ago are this file's alone.
\set ON_ERROR_STOP on

do $$
declare
  v_user uuid := '00000000-0000-4000-8000-000000009101';
  v_old uuid := '00000000-0000-4000-8000-000000009102';
  v_job public.jobs;
  v_before record;
  v_after record;
  v_expected record;
  v_today record;
  v_earlier record;
  v_day date := (now() at time zone 'UTC')::date;
  v_then timestamptz;
  v_stamped integer;
begin
  v_then := ((v_day - 2)::timestamp at time zone 'UTC') + interval '12 hours';
  select * into v_before from public.status_last_24h();

  insert into auth.users (id, email) values (v_user, 'growth-daily@test.local'), (v_old, 'growth-daily-old@test.local');
  update public.profiles set created_at = v_then where id = v_old;
  perform public.record_purchase(v_user, 'paddle', 'txn-growth-1', 'pack_50', 900, 800, null, '{}'::jsonb, 'paddle:txn:growth-1');

  -- today: four successes at 1, 2, 3 and 4 seconds, one failure, one cancellation
  for i in 1..4 loop
    v_job := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, null);
    perform public.start_job(v_job.id, 'w');
    perform public.complete_job(v_job.id, '{}'::jsonb);
    update public.jobs set started_at = finished_at - make_interval(secs => i) where id = v_job.id;
  end loop;
  v_job := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, null);
  perform public.fail_job(v_job.id, '{"code":"internal_error","message":"boom"}'::jsonb);
  v_job := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, null);
  perform public.cancel_job(v_job.id, v_user);

  -- two days ago: one failure and one 5 s success by the old user, whose last credit that
  -- success captured
  v_job := public.create_job(v_old, '{}'::jsonb, '{}'::jsonb, null);
  perform public.fail_job(v_job.id, '{"code":"worker_timeout","message":"late"}'::jsonb);
  update public.jobs set created_at = v_then, finished_at = v_then where id = v_job.id;
  perform public.adjust_credits(v_old, -2, 'test', 'growth-daily:drain');
  v_job := public.create_job(v_old, '{}'::jsonb, '{}'::jsonb, null);
  perform public.complete_job(v_job.id, '{}'::jsonb);
  update public.jobs set created_at = v_then, started_at = v_then, finished_at = v_then + interval '5 seconds'
   where id = v_job.id;
  update public.credit_ledger set created_at = v_then
   where job_id = v_job.id and entry_type = 'capture';
  assert (select balance_after from public.credit_ledger where job_id = v_job.id and entry_type = 'capture') = 0,
    'the old user''s capture should leave zero';

  -- status_last_24h: this file added five outcomes to the window (the cancellation and the
  -- two-day-old rows are outside), and the percentiles are those of the window's successes
  select * into v_after from public.status_last_24h();
  assert v_after.morphs - v_before.morphs = 5
     and v_after.succeeded - v_before.succeeded = 4
     and v_after.failed - v_before.failed = 1, format('status deltas %s -> %s', v_before, v_after);
  select round(percentile_cont(0.5) within group (order by latency))::integer as p50,
         round(percentile_cont(0.95) within group (order by latency))::integer as p95
    into v_expected
    from (select extract(epoch from (finished_at - coalesce(started_at, created_at))) * 1000 as latency
            from public.jobs
           where status = 'succeeded' and finished_at >= now() - interval '24 hours') w;
  assert v_after.p50_ms = v_expected.p50 and v_after.p95_ms = v_expected.p95,
    format('status percentiles %s vs %s', v_after, v_expected);
  assert v_after.p50_ms between 1000 and 4000 and v_after.p95_ms >= v_after.p50_ms, 'plausible latencies';

  -- growth_daily, today: every column matches its definition over the tables
  select * into v_today from public.growth_daily where day = v_day;
  assert v_today.signups = (select count(*) from public.profiles where (created_at at time zone 'UTC')::date = v_day),
    'today signups';
  assert v_today.morphs_started = (select count(*) from public.jobs where (created_at at time zone 'UTC')::date = v_day),
    'today morphs_started';
  assert v_today.morphs_succeeded = (select count(*) from public.jobs
                                      where status = 'succeeded' and (finished_at at time zone 'UTC')::date = v_day),
    'today morphs_succeeded';
  assert v_today.morphs_failed = (select count(*) from public.jobs
                                   where status = 'failed' and (finished_at at time zone 'UTC')::date = v_day),
    'today morphs_failed';
  assert v_today.credits_exhausted = (select count(*) from public.credit_ledger
                                       where entry_type = 'capture' and balance_after = 0
                                         and (created_at at time zone 'UTC')::date = v_day),
    'today credits_exhausted';
  assert v_today.purchases = (select count(*) from public.purchases where (created_at at time zone 'UTC')::date = v_day)
     and v_today.revenue_cents = (select coalesce(sum(amount_cents), 0) from public.purchases
                                   where (created_at at time zone 'UTC')::date = v_day),
    'today purchases';
  assert v_today.morphs_succeeded >= 4 and v_today.morphs_failed >= 1 and v_today.purchases >= 1
     and v_today.p50_ms is not null and v_today.p95_ms >= v_today.p50_ms, format('today %s', v_today);

  -- growth_daily, two days ago: this file's rows alone
  select * into v_earlier from public.growth_daily where day = v_day - 2;
  assert v_earlier.signups = 1 and v_earlier.morphs_started = 2
     and v_earlier.morphs_succeeded = 1 and v_earlier.morphs_failed = 1
     and v_earlier.p50_ms = 5000 and v_earlier.p95_ms = 5000
     and v_earlier.credits_exhausted = 1 and v_earlier.purchases = 0
     and v_earlier.revenue_cents = 0, format('two days ago %s', v_earlier);
  assert (select count(*) from public.growth_daily where day > v_day) = 0, 'a day in the future';
  assert (select count(*) from public.growth_daily where day = v_day - 1) = 0, 'an empty day has a row';

  -- first_seen_at: null after the trigger, set once by the API's conditional update
  assert (select first_seen_at from public.profiles where id = v_user) is null, 'trigger stamped first_seen_at';
  update public.profiles set first_seen_at = now() where id = v_user and first_seen_at is null and deleted_at is null;
  get diagnostics v_stamped = row_count;
  assert v_stamped = 1, 'first stamp';
  update public.profiles set first_seen_at = now() where id = v_user and first_seen_at is null and deleted_at is null;
  get diagnostics v_stamped = row_count;
  assert v_stamped = 0, 'second stamp changed a row';
end;
$$;

-- an empty window answers zeros and nulls, not an error
do $$
declare
  v_status record;
begin
  update public.jobs set finished_at = finished_at - interval '2 days' where finished_at is not null;
  select * into v_status from public.status_last_24h();
  assert v_status.morphs = 0 and v_status.succeeded = 0 and v_status.failed = 0
     and v_status.p50_ms is null and v_status.p95_ms is null, format('empty window %s', v_status);
end;
$$;
