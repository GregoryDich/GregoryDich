-- Account deletion (contract §1, 0004_account_deletion.sql): the tombstone keeps the
-- accounting rows and loses the person, unfinished jobs block it, it is idempotent, the
-- ledger invariants survive it, a login deleted at the provider ends in the same state,
-- and API roles can neither call it nor read the deletion log.
\set ON_ERROR_STOP on

create function pg_temp.assert_deletion_invariants(p_user_id uuid) returns void
language plpgsql as $$
declare
  v_account public.credit_accounts;
  v_sum integer;
  v_last public.credit_ledger;
begin
  select * into v_account from public.credit_accounts where user_id = p_user_id;
  assert found, 'credit account lost';
  select coalesce(sum(amount), 0) into v_sum from public.credit_ledger
   where user_id = p_user_id and entry_type in ('grant', 'capture', 'refund', 'expire', 'adjust');
  assert v_sum = v_account.balance, format('ledger sum %s <> balance %s', v_sum, v_account.balance);
  assert v_account.balance = v_account.reserved and v_account.reserved = 0,
    format('tombstone account not closed: balance %s reserved %s', v_account.balance, v_account.reserved);
  select * into v_last from public.credit_ledger where user_id = p_user_id order by seq desc limit 1;
  assert v_last.balance_after = v_account.balance and v_last.reserved_after = v_account.reserved,
    'latest ledger row does not match the account';
end;
$$;

do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000a101';
  v_referrer uuid := '00000000-0000-4000-8000-00000000a102';
  v_affiliate_id uuid;
  v_done public.jobs;
  v_running public.jobs;
  v_key record;
  v_deletion public.account_deletions;
  v_again public.account_deletions;
  v_profile public.profiles;
  v_count integer;
  v_ledger_before integer;
begin
  insert into auth.users (id, email) values (v_referrer, 'referrer@test.local');
  insert into public.affiliates (user_id, code, payout_details) values (v_referrer, 'REF10', '{"paypal":"referrer@test.local"}'::jsonb)
  returning id into v_affiliate_id;
  insert into auth.users (id, email, raw_user_meta_data) values (v_user, 'leaving@test.local',
    '{"referral_code":"ref10","utm_source":"tiktok","utm_campaign":"launch","marketing_opt_in":true,
      "terms_accepted_at":"2026-09-01T10:00:00Z"}'::jsonb);

  -- a life: a purchase with a referral, a finished job, a running job, a key, a name
  perform public.record_purchase(v_user, 'lemonsqueezy', 'del-ord-1', 'pack_50', 900, 820, 'REF10',
                                 '{"customer_email":"leaving@test.local"}'::jsonb, 'lemonsqueezy:order_created:del-1');
  v_done := public.create_job(v_user, '{"stems":["bass"]}'::jsonb, '{"input_name":"input.wav"}'::jsonb, 'del-key-1');
  v_done := public.complete_job(v_done.id, '{"stems":[{"name":"bass","url":"https://signed"}]}'::jsonb);
  insert into public.job_assets (job_id, user_id, kind, storage_key)
  values (v_done.id, v_user, 'stem', 'jobs/' || v_user || '/' || v_done.id || '/bass.wav');
  v_running := public.create_job(v_user, '{}'::jsonb, '{}'::jsonb, 'del-key-2');
  perform public.start_job(v_running.id, 'worker-1');
  select * into v_key from public.create_api_key(v_user, 'ci');
  update public.profiles set display_name = 'Leaving Person' where id = v_user;
  assert public.get_balance(v_user) = row(52, 1, 51)::public.credit_balance, 'setup balance';

  -- an unfinished job blocks the deletion and nothing changes
  begin
    perform public.delete_user_account(v_user);
    raise exception 'deletion with a running job did not raise';
  exception when sqlstate 'P0409' then
    assert sqlerrm = 'conflict', sqlerrm;
  end;
  assert (select deleted_at from public.profiles where id = v_user) is null, 'refused deletion tombstoned';
  assert (select count(*) from public.api_keys where user_id = v_user) = 1, 'refused deletion dropped keys';
  begin
    delete from auth.users where id = v_user;
    raise exception 'provider deletion with a running job did not raise';
  exception when sqlstate 'P0409' then null;
  end;
  assert exists (select 1 from auth.users where id = v_user), 'refused provider deletion removed the login';

  -- unknown profile
  begin
    perform public.delete_user_account(gen_random_uuid());
    raise exception 'deletion of an unknown user did not raise';
  exception when sqlstate 'P0404' then null;
  end;

  perform public.fail_job(v_running.id, '{"code":"worker_error","message":"boom"}'::jsonb);
  select count(*) into v_ledger_before from public.credit_ledger where user_id = v_user;

  -- the deletion itself
  v_deletion := public.delete_user_account(v_user);
  assert v_deletion.user_id = v_user and v_deletion.requested_at is not null
     and v_deletion.ledger_rows_kept = v_ledger_before + 1, format('deletion row %s', v_deletion);

  select * into v_profile from public.profiles where id = v_user;
  assert v_profile.email = 'deleted+' || v_user::text || '@invalid' and v_profile.display_name is null
     and v_profile.deleted_at is not null and v_profile.plan = 'credits', 'profile tombstone';
  assert position('leaving@test.local' in v_profile::text) = 0, 'email survived on the profile';
  assert v_profile.referral_code = 'REF10' and v_profile.terms_accepted_at = '2026-09-01T10:00:00Z'::timestamptz,
    'attribution code or terms record lost';
  assert v_profile.utm_source is null and v_profile.utm_campaign is null and v_profile.marketing_opt_in = false,
    'utm attribution or marketing consent survived';

  -- credits written off through the ledger; the ledger itself is intact
  assert public.get_balance(v_user) = row(0, 0, 0)::public.credit_balance, 'credits not forfeited';
  assert (select count(*) from public.credit_ledger where user_id = v_user) = v_ledger_before + 1, 'ledger rows lost';
  assert exists (select 1 from public.credit_ledger where user_id = v_user and entry_type = 'adjust'
                    and amount = -52 and source = 'account_deletion'
                    and idempotency_key = 'deletion:' || v_user::text), 'forfeit ledger row';
  perform pg_temp.assert_deletion_invariants(v_user);

  -- keys and assets gone; jobs kept as lifecycle rows only
  assert not exists (select 1 from public.api_keys where user_id = v_user), 'api keys survived';
  assert public.authenticate_api_key(encode(sha256(convert_to(v_key.plaintext, 'UTF8')), 'hex')) is null,
    'deleted key still authenticates';
  assert not exists (select 1 from public.job_assets where user_id = v_user), 'job assets survived';
  select count(*) into v_count from public.jobs where user_id = v_user;
  assert v_count = 2, format('%s jobs left', v_count);
  assert not exists (select 1 from public.jobs where user_id = v_user
                        and (options <> '{}'::jsonb or input_meta <> '{}'::jsonb or result is not null
                             or worker_ref is not null or idempotency_key is not null)), 'job content survived';
  assert (select status from public.jobs where id = v_done.id) = 'succeeded'
     and (select error ->> 'code' from public.jobs where id = v_running.id) = 'worker_error', 'job lifecycle lost';
  assert exists (select 1 from public.credit_ledger where job_id = v_done.id and entry_type = 'capture'),
    'ledger lost its job reference';

  -- purchases and the referrer's commission stay; the provider payload does not
  select count(*) into v_count from public.purchases where user_id = v_user;
  assert v_count = 1 and (select raw from public.purchases where user_id = v_user) = '{}'::jsonb, 'purchase row';
  assert (select count(*) from public.affiliate_commissions where affiliate_id = v_affiliate_id) = 1,
    'commission lost';
  assert exists (select 1 from public.account_deletions where user_id = v_user), 'deletion not recorded';

  -- idempotent: a second call returns the same row and moves nothing
  v_again := public.delete_user_account(v_user);
  assert v_again = v_deletion, 'replayed deletion changed the record';
  assert (select count(*) from public.credit_ledger where user_id = v_user) = v_ledger_before + 1,
    'replayed deletion wrote to the ledger';

  -- the identity goes last (the API calls GoTrue); the tombstone survives it
  delete from auth.users where id = v_user;
  assert exists (select 1 from public.profiles where id = v_user and deleted_at is not null), 'tombstone lost with the login';
  assert (select count(*) from public.credit_ledger where user_id = v_user) = v_ledger_before + 1, 'ledger lost with the login';
  assert exists (select 1 from public.purchases where user_id = v_user), 'purchase lost with the login';
  perform pg_temp.assert_deletion_invariants(v_user);
end;
$$;

-- An affiliate who leaves: codes are revoked, payout details go, commissions stay.
do $$
declare
  v_affiliate_user uuid := '00000000-0000-4000-8000-00000000a103';
  v_buyer uuid := '00000000-0000-4000-8000-00000000a104';
  v_affiliate_id uuid;
begin
  insert into auth.users (id, email) values (v_affiliate_user, 'aff-leaving@test.local'), (v_buyer, 'aff-buyer@test.local');
  insert into public.affiliates (user_id, code, payout_details) values (v_affiliate_user, 'LEAVE30', '{"iban":"DE00"}'::jsonb)
  returning id into v_affiliate_id;
  perform public.record_purchase(v_buyer, 'paddle', 'aff-txn-1', 'pack_50', 900, 820, 'LEAVE30', '{}'::jsonb,
                                 'paddle:transaction.completed:aff-txn-1');
  assert (select count(*) from public.affiliate_commissions where affiliate_id = v_affiliate_id) = 1, 'setup commission';

  -- deleted at the provider: the trigger runs the same function
  delete from auth.users where id = v_affiliate_user;
  assert (select deleted_at from public.profiles where id = v_affiliate_user) is not null, 'affiliate not tombstoned';
  assert (select active from public.affiliates where id = v_affiliate_id) = false, 'affiliate still active';
  assert (select payout_details from public.affiliates where id = v_affiliate_id) = '{}'::jsonb, 'payout details survived';
  assert not exists (select 1 from public.referral_codes where affiliate_id = v_affiliate_id and active), 'code still active';
  assert (select count(*) from public.affiliate_commissions where affiliate_id = v_affiliate_id) = 1, 'commission lost';
  assert (select count(*) from public.purchases where user_id = v_buyer) = 1, 'buyer purchase lost';

  -- a revoked code earns nothing any more
  perform public.record_purchase(v_buyer, 'paddle', 'aff-txn-2', 'pack_50', 900, 820, 'LEAVE30', '{}'::jsonb,
                                 'paddle:transaction.completed:aff-txn-2');
  assert (select count(*) from public.affiliate_commissions where affiliate_id = v_affiliate_id) = 1,
    'revoked code earned a commission';
end;
$$;

-- API roles: the function is not executable and the deletion log is not readable.
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000a101';
begin
  execute 'set local role authenticated';
  perform set_config('request.jwt.claim.sub', v_user::text, true);
  begin
    perform public.delete_user_account(v_user);
    raise exception 'delete_user_account executable by authenticated';
  exception when insufficient_privilege then null;
  end;
  begin
    perform count(*) from public.account_deletions;
    raise exception 'account_deletions readable by authenticated';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';

  execute 'set local role service_role';
  assert (select count(*) from public.account_deletions where user_id = v_user) = 1, 'service_role cannot read the log';
  perform public.delete_user_account(v_user);
  execute 'reset role';
end;
$$;
