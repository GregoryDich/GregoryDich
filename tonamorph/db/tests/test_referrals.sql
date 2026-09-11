-- User referrals (contract §1, §3, §12; 0006): every profile owns an 8-character code, a
-- sign-up with a friend's code links the profile and grants 2 extra credits, the friend's
-- first successful morph earns the referrer 3 credits exactly once, and at most ten
-- friends per 30 days are rewarded.
\set ON_ERROR_STOP on

-- helper: a job the user completes
create function pg_temp.morph(p_user uuid) returns uuid
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
  v_referrer uuid := '00000000-0000-4000-8000-00000000b101';
  v_friend uuid := '00000000-0000-4000-8000-00000000b102';
  v_affiliated uuid := '00000000-0000-4000-8000-00000000b103';
  v_unknown uuid := '00000000-0000-4000-8000-00000000b104';
  v_gone uuid := '00000000-0000-4000-8000-00000000b105';
  v_orphan uuid := '00000000-0000-4000-8000-00000000b106';
  v_late uuid := '00000000-0000-4000-8000-00000000b107';
  v_code text;
  v_gone_code text;
  v_job uuid;
  v_failed public.jobs;
  v_summary record;
  v_row public.credit_ledger;
  v_count integer;
begin
  insert into auth.users (id, email) values (v_referrer, 'ref-referrer@test.local');
  insert into public.affiliates (user_id, code) values (v_referrer, 'REFAFF');

  -- every profile owns one code from the unambiguous alphabet
  select code into v_code from public.user_referral_codes where user_id = v_referrer;
  assert v_code ~ '^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$', format('code %s', v_code);
  assert (select count(*) from public.user_referral_codes) = (select count(*) from public.profiles),
    'a profile without a code';
  assert (select count(distinct code) from public.user_referral_codes)
         = (select count(*) from public.user_referral_codes), 'duplicate codes';

  -- a friend signs up with the code, spelled loosely: linked, 3 + 2 credits, no affiliate code
  insert into auth.users (id, email, raw_user_meta_data)
  values (v_friend, 'ref-friend@test.local', jsonb_build_object('referral_code', '  ' || lower(v_code) || ' '));
  assert (select referred_by from public.profiles where id = v_friend) = v_referrer, 'referred_by not set';
  assert (select referral_code from public.profiles where id = v_friend) is null, 'a user code is not an affiliate code';
  assert public.get_balance(v_friend) = row(5, 0, 5)::public.credit_balance, format('friend credits %s', public.get_balance(v_friend));
  select * into v_row from public.credit_ledger where idempotency_key = 'referral_bonus:' || v_friend::text;
  assert found and v_row.entry_type = 'grant' and v_row.amount = 2 and v_row.source = 'referral_bonus'
     and v_row.note = 'Invited by a friend', 'referral bonus row';
  assert public.get_balance(v_referrer) = row(3, 0, 3)::public.credit_balance, 'the referrer earned at sign-up';

  -- an affiliate code wins over a user code and works as before
  insert into auth.users (id, email, raw_user_meta_data)
  values (v_affiliated, 'ref-affiliated@test.local', '{"referral_code":"refaff"}'::jsonb);
  assert (select referral_code from public.profiles where id = v_affiliated) = 'REFAFF'
     and (select referred_by from public.profiles where id = v_affiliated) is null, 'affiliate sign-up';
  assert public.get_balance(v_affiliated) = row(3, 0, 3)::public.credit_balance, 'affiliate sign-up credits';

  -- an unknown code changes nothing
  insert into auth.users (id, email, raw_user_meta_data)
  values (v_unknown, 'ref-unknown@test.local', '{"referral_code":"ZZZZZZZZ"}'::jsonb);
  assert (select referred_by from public.profiles where id = v_unknown) is null, 'unknown code linked';
  assert public.get_balance(v_unknown) = row(3, 0, 3)::public.credit_balance, 'unknown code granted';

  -- a deleted account's code stops working
  insert into auth.users (id, email) values (v_gone, 'ref-gone@test.local');
  select code into v_gone_code from public.user_referral_codes where user_id = v_gone;
  perform public.delete_user_account(v_gone);
  insert into auth.users (id, email, raw_user_meta_data)
  values (v_orphan, 'ref-orphan@test.local', jsonb_build_object('referral_code', v_gone_code));
  assert (select referred_by from public.profiles where id = v_orphan) is null, 'deleted referrer linked';
  assert public.get_balance(v_orphan) = row(3, 0, 3)::public.credit_balance, 'deleted referrer bonus';

  -- the reward: the friend's first successful morph, once, whatever happens later
  v_failed := public.create_job(v_friend, '{}'::jsonb, '{}'::jsonb, null);
  perform public.fail_job(v_failed.id, '{"code":"worker_timeout","message":"late"}'::jsonb);
  assert public.get_balance(v_referrer) = row(3, 0, 3)::public.credit_balance, 'a failed morph rewarded';
  v_job := pg_temp.morph(v_friend);
  assert public.get_balance(v_referrer) = row(6, 0, 6)::public.credit_balance, format('referrer after first morph %s', public.get_balance(v_referrer));
  select * into v_row from public.credit_ledger where idempotency_key = 'referral:' || v_friend::text;
  assert found and v_row.user_id = v_referrer and v_row.entry_type = 'grant' and v_row.amount = 3
     and v_row.source = 'referral' and v_row.note = 'A friend''s first morph', 'reward row';
  perform public.complete_job(v_job, '{}'::jsonb);
  perform pg_temp.morph(v_friend);
  assert public.get_balance(v_referrer) = row(6, 0, 6)::public.credit_balance, 'rewarded twice';
  select count(*) into v_count from public.credit_ledger where user_id = v_referrer and source = 'referral';
  assert v_count = 1, format('%s reward rows', v_count);
  assert public.reward_referral(v_friend) is null, 'reward_referral rewarded again';

  -- a referrer deleted after the sign-up earns nothing
  insert into auth.users (id, email, raw_user_meta_data)
  values (v_late, 'ref-late@test.local', jsonb_build_object('referral_code', v_code));
  assert (select referred_by from public.profiles where id = v_late) = v_referrer, 'late friend linked';
  update public.profiles set deleted_at = now() where id = v_referrer;
  perform pg_temp.morph(v_late);
  assert not exists (select 1 from public.credit_ledger where idempotency_key = 'referral:' || v_late::text),
    'a deleted referrer was rewarded';
  update public.profiles set deleted_at = null where id = v_referrer;

  -- the summary GET /v1/me shows
  select * into v_summary from public.user_referral_summary(v_referrer);
  assert v_summary.code = v_code and v_summary.friends_joined = 2 and v_summary.morphs_earned = 3,
    format('summary %s', v_summary);
  select * into v_summary from public.user_referral_summary(v_unknown);
  assert v_summary.friends_joined = 0 and v_summary.morphs_earned = 0, format('empty summary %s', v_summary);
  assert not exists (select 1 from public.user_referral_summary(gen_random_uuid())), 'summary for an unknown profile';

  -- a profile without a code is given one by the summary
  delete from public.user_referral_codes where user_id = v_unknown;
  select * into v_summary from public.user_referral_summary(v_unknown);
  assert v_summary.code ~ '^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$', 'no code assigned';
  assert (select code from public.user_referral_codes where user_id = v_unknown) = v_summary.code, 'assigned code not stored';

  -- a generated code never collides with an affiliate code
  assert not exists (select 1 from public.user_referral_codes c
                      join public.referral_codes r on lower(r.code) = lower(c.code)), 'user code equals an affiliate code';
end;
$$;

-- the cap: at most ten rewarded friends per referrer per 30 days
do $$
declare
  v_referrer uuid := '00000000-0000-4000-8000-00000000b201';
  v_code text;
  v_friend uuid;
  v_first uuid;
  v_summary record;
begin
  insert into auth.users (id, email) values (v_referrer, 'ref-cap@test.local');
  select code into v_code from public.user_referral_codes where user_id = v_referrer;
  for i in 1..11 loop
    v_friend := gen_random_uuid();
    if i = 1 then
      v_first := v_friend;
    end if;
    insert into auth.users (id, email, raw_user_meta_data)
    values (v_friend, format('ref-cap-%s@test.local', i), jsonb_build_object('referral_code', v_code));
    perform pg_temp.morph(v_friend);
  end loop;
  assert public.get_balance(v_referrer) = row(33, 0, 33)::public.credit_balance,
    format('capped referrer %s', public.get_balance(v_referrer));
  select * into v_summary from public.user_referral_summary(v_referrer);
  assert v_summary.friends_joined = 11 and v_summary.morphs_earned = 30, format('capped summary %s', v_summary);

  -- once the window has moved on, the next friend is rewarded again
  update public.credit_ledger set created_at = now() - interval '31 days'
   where idempotency_key = 'referral:' || v_first::text;
  v_friend := gen_random_uuid();
  insert into auth.users (id, email, raw_user_meta_data)
  values (v_friend, 'ref-cap-12@test.local', jsonb_build_object('referral_code', v_code));
  perform pg_temp.morph(v_friend);
  assert public.get_balance(v_referrer) = row(36, 0, 36)::public.credit_balance, 'window did not reopen';
end;
$$;

-- privileges: the summary is service_role only; the reward and the generator are internal;
-- the codes table is not readable by API roles
do $$
declare
  v_referrer uuid := '00000000-0000-4000-8000-00000000b101';
  v_summary record;
begin
  execute 'set local role authenticated';
  perform set_config('request.jwt.claim.sub', v_referrer::text, true);
  begin
    perform public.user_referral_summary(v_referrer);
    raise exception 'user_referral_summary executable by authenticated';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.reward_referral(v_referrer);
    raise exception 'reward_referral executable by authenticated';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.generate_user_referral_code();
    raise exception 'generate_user_referral_code executable by authenticated';
  exception when insufficient_privilege then null;
  end;
  begin
    perform count(*) from public.user_referral_codes;
    raise exception 'user_referral_codes readable by authenticated';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';

  execute 'set local role service_role';
  select * into v_summary from public.user_referral_summary(v_referrer);
  assert v_summary.friends_joined = 2, 'service_role summary';
  begin
    perform public.reward_referral(v_referrer);
    raise exception 'reward_referral executable by service_role';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';
end;
$$;
