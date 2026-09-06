-- Row-level security and privileges (0003_rls.sql): authenticated users see only their own
-- rows, cannot write ledger/accounts/jobs, cannot execute mutating functions, and
-- get_balance refuses other users' ids. anon sees plans only; service_role sees everything.
\set ON_ERROR_STOP on

-- Setup as the migration owner.
do $$
declare
  v_a uuid := '00000000-0000-4000-8000-00000000e001';
  v_b uuid := '00000000-0000-4000-8000-00000000e002';
begin
  insert into auth.users (id, email) values (v_a, 'rls-a@test.local'), (v_b, 'rls-b@test.local');
  perform public.create_job(v_a, '{}'::jsonb, '{}'::jsonb, 'rls-a-1');
  perform public.create_job(v_b, '{}'::jsonb, '{}'::jsonb, 'rls-b-1');
  perform public.create_job(v_b, '{}'::jsonb, '{}'::jsonb, 'rls-b-2');
  insert into public.job_assets (job_id, user_id, kind, storage_key)
  select id, user_id, 'input', 'jobs/' || user_id || '/' || id || '/input.flac' from public.jobs
   where user_id in (v_a, v_b);
  insert into public.affiliates (user_id, code) values (v_b, 'RLSCODE');
  insert into public.api_keys (user_id, key_hash, prefix, name)
  values (v_a, 'hash-a', 'sp_live_aaaa', 'a'), (v_b, 'hash-b', 'sp_live_bbbb', 'b');
  insert into public.webhook_events (provider, event_name, idempotency_key, payload)
  values ('lemonsqueezy', 'order_created', 'lemonsqueezy:order_created:rls', '{}'::jsonb);
  perform public.record_purchase(v_a, 'lemonsqueezy', 'rls-ord-1', 'pack_50', 900, 820, 'RLSCODE',
                                 '{}'::jsonb, 'lemonsqueezy:order_created:rls');
end;
$$;

-- Authenticated user A.
do $$
declare
  v_a uuid := '00000000-0000-4000-8000-00000000e001';
  v_b uuid := '00000000-0000-4000-8000-00000000e002';
  v_count integer;
  v_bal public.credit_balance;
begin
  execute 'set local role authenticated';
  perform set_config('request.jwt.claim.sub', v_a::text, true);
  assert auth.uid() = v_a, 'auth shim did not pick up the subject';

  select count(*) into v_count from public.jobs;
  assert v_count = 1, format('A sees %s jobs', v_count);
  assert not exists (select 1 from public.jobs where user_id = v_b), 'A can read B''s jobs';
  select count(*) into v_count from public.job_assets;
  assert v_count = 1, format('A sees %s job assets', v_count);
  select count(*) into v_count from public.profiles;
  assert v_count = 1 and (select id from public.profiles) = v_a, 'A sees other profiles';
  select count(*) into v_count from public.credit_accounts;
  assert v_count = 1 and (select user_id from public.credit_accounts) = v_a, 'A sees other accounts';
  select count(*) into v_count from public.credit_ledger where user_id <> v_a;
  assert v_count = 0, 'A sees other users'' ledger rows';
  select count(*) into v_count from public.credit_ledger;
  assert v_count = 3, format('A sees %s of her own ledger rows', v_count);
  select count(*) into v_count from public.api_keys;
  assert v_count = 1 and (select prefix from public.api_keys) = 'sp_live_aaaa', 'A sees other API keys';
  select count(*) into v_count from public.purchases;
  assert v_count = 1, format('A sees %s purchases', v_count);
  select count(*) into v_count from public.affiliates;
  assert v_count = 0, 'A sees B''s affiliate row';
  select count(*) into v_count from public.referral_codes;
  assert v_count = 0, 'A sees B''s referral codes';
  select count(*) into v_count from public.affiliate_commissions;
  assert v_count = 0, 'A sees B''s commissions';
  select count(*) into v_count from public.plans;
  assert v_count = 3, format('A sees %s plans', v_count);

  -- no direct writes
  begin
    insert into public.credit_ledger (user_id, entry_type, amount, balance_after, reserved_after)
    values (v_a, 'grant', 100, 100, 0);
    raise exception 'ledger insert allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    update public.credit_accounts set balance = 1000 where user_id = v_a;
    raise exception 'account update allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    delete from public.credit_ledger;
    raise exception 'ledger delete allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    insert into public.jobs (user_id) values (v_a);
    raise exception 'job insert allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    update public.jobs set status = 'succeeded';
    raise exception 'job update allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    delete from public.jobs;
    raise exception 'job delete allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    update public.profiles set plan = 'subscription' where id = v_a;
    raise exception 'profile update allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    update public.plans set credits = 999;
    raise exception 'plan update allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    perform count(*) from public.webhook_events;
    raise exception 'webhook_events readable';
  exception when insufficient_privilege then null;
  end;

  -- get_balance: own account only
  v_bal := public.get_balance(v_a);
  assert v_bal = row(53, 1, 52)::public.credit_balance, format('own balance %s', v_bal);
  begin
    perform public.get_balance(v_b);
    raise exception 'get_balance of another user allowed';
  exception when insufficient_privilege then
    assert sqlerrm = 'forbidden', sqlerrm;
  end;

  -- mutating functions and internals are not executable
  begin
    perform public.reserve_credits(v_a, gen_random_uuid(), 1);
    raise exception 'reserve_credits executable';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.grant_credits(v_a, 100, 'self', 'self:1');
    raise exception 'grant_credits executable';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.create_job(v_a, '{}'::jsonb, '{}'::jsonb, 'self');
    raise exception 'create_job executable';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.cancel_job(gen_random_uuid(), v_a);
    raise exception 'cancel_job executable';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.record_purchase(v_a, 'lemonsqueezy', 'x', 'pack_50', 0, 0, null, null, 'x');
    raise exception 'record_purchase executable';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.expire_credits();
    raise exception 'expire_credits executable';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.create_api_key(v_a, 'x');
    raise exception 'create_api_key executable';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.lock_credit_account(v_a);
    raise exception 'lock_credit_account executable';
  exception when insufficient_privilege then null;
  end;

  execute 'reset role';
end;
$$;

-- Authenticated user B sees her own affiliate data.
do $$
declare
  v_b uuid := '00000000-0000-4000-8000-00000000e002';
  v_count integer;
begin
  execute 'set local role authenticated';
  perform set_config('request.jwt.claim.sub', v_b::text, true);

  select count(*) into v_count from public.jobs;
  assert v_count = 2, format('B sees %s jobs', v_count);
  select count(*) into v_count from public.affiliates;
  assert v_count = 1, 'B cannot see her affiliate row';
  select count(*) into v_count from public.referral_codes;
  assert v_count = 1 and (select code from public.referral_codes) = 'RLSCODE', 'B cannot see her referral code';
  select count(*) into v_count from public.affiliate_commissions;
  assert v_count = 1 and (select amount_cents from public.affiliate_commissions) = 246, 'B cannot see her commission';
  select count(*) into v_count from public.purchases;
  assert v_count = 0, 'B sees the referred purchase itself';
  assert public.get_balance(v_b) = row(3, 2, 1)::public.credit_balance, 'B balance';

  execute 'reset role';
end;
$$;

-- anon: active plans only.
do $$
declare
  v_a uuid := '00000000-0000-4000-8000-00000000e001';
  v_count integer;
begin
  execute 'set local role anon';
  select count(*) into v_count from public.plans;
  assert v_count = 3, format('anon sees %s plans', v_count);
  begin
    perform count(*) from public.jobs;
    raise exception 'anon reads jobs';
  exception when insufficient_privilege then null;
  end;
  begin
    perform count(*) from public.profiles;
    raise exception 'anon reads profiles';
  exception when insufficient_privilege then null;
  end;
  begin
    perform public.get_balance(v_a);
    raise exception 'anon calls get_balance';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';
end;
$$;

-- Inactive plans are hidden from API roles.
update public.plans set active = false where id = 'sub_monthly';
do $$
declare
  v_count integer;
begin
  execute 'set local role anon';
  select count(*) into v_count from public.plans;
  assert v_count = 2, format('anon sees %s plans after deactivation', v_count);
  execute 'reset role';
end;
$$;
update public.plans set active = true where id = 'sub_monthly';

-- service_role bypasses RLS and may execute the mutating functions, but not the internals.
do $$
declare
  v_a uuid := '00000000-0000-4000-8000-00000000e001';
  v_count integer;
begin
  execute 'set local role service_role';
  select count(*) into v_count from public.jobs;
  assert v_count >= 3, format('service_role sees %s jobs', v_count);
  select count(*) into v_count from public.webhook_events;
  assert v_count >= 1, 'service_role cannot read webhook_events';
  assert public.get_balance(v_a) = row(53, 1, 52)::public.credit_balance, 'service_role get_balance';
  perform public.expire_credits();
  perform public.grant_credits(v_a, 1, 'service', 'service:1');
  assert public.get_balance(v_a) = row(54, 1, 53)::public.credit_balance, 'service_role grant';
  begin
    perform public.lock_credit_account(v_a);
    raise exception 'internal helper executable by service_role';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';
end;
$$;
