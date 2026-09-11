-- The first-week gift (GTM Appendix B §3; 0006): grant_week1_gifts() gives 2 credits, once,
-- to profiles created 7–8 days ago with at least one succeeded job, and to nobody else.
\set ON_ERROR_STOP on

create function pg_temp.morph(p_user uuid) returns void
language plpgsql as $$
declare
  v_job public.jobs;
begin
  v_job := public.create_job(p_user, '{}'::jsonb, '{}'::jsonb, null);
  perform public.start_job(v_job.id, 'worker');
  perform public.complete_job(v_job.id, '{}'::jsonb);
end;
$$;

do $$
declare
  v_week uuid := '00000000-0000-4000-8000-00000000c101';   -- 7.5 days, one morph
  v_idle uuid := '00000000-0000-4000-8000-00000000c102';   -- 7.5 days, no morph
  v_fresh uuid := '00000000-0000-4000-8000-00000000c103';  -- 6 days, one morph
  v_old uuid := '00000000-0000-4000-8000-00000000c104';    -- 9 days, one morph
  v_gone uuid := '00000000-0000-4000-8000-00000000c105';   -- 7.5 days, one morph, deleted
  v_failed uuid := '00000000-0000-4000-8000-00000000c106'; -- 7.5 days, only a failed morph
  v_job public.jobs;
  v_granted uuid[];
  v_row public.credit_ledger;
begin
  insert into auth.users (id, email)
  values (v_week, 'gift-week@test.local'), (v_idle, 'gift-idle@test.local'), (v_fresh, 'gift-fresh@test.local'),
         (v_old, 'gift-old@test.local'), (v_gone, 'gift-gone@test.local'), (v_failed, 'gift-failed@test.local');
  perform pg_temp.morph(v_week);
  perform pg_temp.morph(v_fresh);
  perform pg_temp.morph(v_old);
  perform pg_temp.morph(v_gone);
  v_job := public.create_job(v_failed, '{}'::jsonb, '{}'::jsonb, null);
  perform public.fail_job(v_job.id, '{"code":"worker_timeout","message":"late"}'::jsonb);
  update public.profiles set created_at = now() - interval '7 days 12 hours'
   where id in (v_week, v_idle, v_gone, v_failed);
  update public.profiles set created_at = now() - interval '6 days' where id = v_fresh;
  update public.profiles set created_at = now() - interval '9 days' where id = v_old;
  -- the morphs happened the day after each sign-up, not just now
  update public.jobs j
     set created_at = p.created_at + interval '1 day',
         started_at = p.created_at + interval '1 day',
         finished_at = p.created_at + interval '1 day 2 seconds'
    from public.profiles p
   where p.id = j.user_id and j.user_id in (v_week, v_fresh, v_old, v_gone, v_failed);
  perform public.delete_user_account(v_gone);

  select coalesce(array_agg(user_id), '{}') into v_granted from public.grant_week1_gifts();
  assert v_granted = array[v_week], format('granted %s', v_granted);
  assert public.get_balance(v_week) = row(4, 0, 4)::public.credit_balance, format('gift balance %s', public.get_balance(v_week));
  select * into v_row from public.credit_ledger where idempotency_key = 'gift:week1:' || v_week::text;
  assert found and v_row.entry_type = 'grant' and v_row.amount = 2 and v_row.source = 'gift:week1'
     and v_row.note = 'One week in. Two morphs on us.' and v_row.expires_at is null, 'gift ledger row';
  assert public.get_balance(v_idle) = row(3, 0, 3)::public.credit_balance, 'a zero-morph account was gifted';
  assert public.get_balance(v_fresh) = row(2, 0, 2)::public.credit_balance, 'a six-day account was gifted';
  assert public.get_balance(v_old) = row(2, 0, 2)::public.credit_balance, 'a nine-day account was gifted';
  assert public.get_balance(v_failed) = row(3, 0, 3)::public.credit_balance, 'a failed-only account was gifted';
  assert not exists (select 1 from public.credit_ledger where user_id = v_gone and source = 'gift:week1'),
    'a deleted account was gifted';

  -- once: the next run grants nothing, even inside the window
  select coalesce(array_agg(user_id), '{}') into v_granted from public.grant_week1_gifts();
  assert v_granted = '{}'::uuid[], format('second run granted %s', v_granted);
  assert public.get_balance(v_week) = row(4, 0, 4)::public.credit_balance, 'gifted twice';

  -- the fresh account reaches day 7 and is gifted then
  update public.profiles set created_at = now() - interval '7 days 1 hour' where id = v_fresh;
  select coalesce(array_agg(user_id), '{}') into v_granted from public.grant_week1_gifts();
  assert v_granted = array[v_fresh], format('day-7 run granted %s', v_granted);
  assert public.get_balance(v_fresh) = row(4, 0, 4)::public.credit_balance, 'fresh account gift';
end;
$$;

-- privileges: the cron entry point is service_role only
do $$
begin
  execute 'set local role authenticated';
  begin
    perform public.grant_week1_gifts();
    raise exception 'grant_week1_gifts executable by authenticated';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';
  execute 'set local role service_role';
  assert (select count(*) from public.grant_week1_gifts()) = 0, 'service_role run';
  execute 'reset role';
end;
$$;
