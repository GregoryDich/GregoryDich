-- Credit ledger semantics (contract §6): signup grant, reserve/settle/grant/refund/adjust/expire,
-- idempotency of every entry point, and the balance invariants after a long mixed sequence.
\set ON_ERROR_STOP on

-- Session-local helper: every invariant the ledger must satisfy for one user.
create function pg_temp.assert_ledger_invariants(p_user_id uuid) returns void
language plpgsql as $$
declare
  v_account public.credit_accounts;
  v_last public.credit_ledger;
  v_sum integer;
  v_open integer;
  v_bad integer;
begin
  select * into v_account from public.credit_accounts where user_id = p_user_id;
  assert found, 'no credit account';

  select coalesce(sum(amount), 0) into v_sum from public.credit_ledger
   where user_id = p_user_id and entry_type in ('grant', 'capture', 'refund', 'expire', 'adjust');
  assert v_sum = v_account.balance, format('ledger sum %s <> balance %s', v_sum, v_account.balance);

  select coalesce(-sum(r.amount), 0) into v_open from public.credit_ledger r
   where r.user_id = p_user_id and r.entry_type = 'reserve'
     and not exists (select 1 from public.credit_ledger s
                      where s.job_id = r.job_id and s.entry_type in ('capture', 'release'));
  assert v_open = v_account.reserved, format('open reservations %s <> reserved %s', v_open, v_account.reserved);
  assert v_account.balance >= v_account.reserved and v_account.reserved >= 0, 'account bounds';

  select count(*) into v_bad from (
    select balance_after, reserved_after,
           sum(case when entry_type in ('grant', 'capture', 'refund', 'expire', 'adjust') then amount else 0 end)
             over w as run_balance,
           sum(case when entry_type in ('reserve', 'release') then -amount
                    when entry_type = 'capture' then amount else 0 end)
             over w as run_reserved
      from public.credit_ledger
     where user_id = p_user_id
    window w as (order by seq rows between unbounded preceding and current row)
  ) t
  where t.balance_after <> t.run_balance or t.reserved_after <> t.run_reserved;
  assert v_bad = 0, format('%s ledger rows have an inconsistent balance_after/reserved_after', v_bad);

  select * into v_last from public.credit_ledger where user_id = p_user_id order by seq desc limit 1;
  assert v_last.balance_after = v_account.balance and v_last.reserved_after = v_account.reserved,
    'latest ledger row does not match the account';
end;
$$;

do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000c001';
  v_job1 uuid;
  v_job2 uuid;
  v_job3 uuid;
  v_job4 uuid;
  v_bal public.credit_balance;
  v_row public.credit_ledger;
  v_count integer;
begin
  insert into auth.users (id, email) values (v_user, 'ledger@test.local');

  -- signup grants exactly 3 credits, exactly once
  v_bal := public.get_balance(v_user);
  assert v_bal = row(3, 0, 3)::public.credit_balance, format('signup balance %s', v_bal);
  select count(*) into v_count from public.credit_ledger where user_id = v_user;
  assert v_count = 1, format('signup wrote %s ledger rows', v_count);
  select * into v_row from public.credit_ledger where user_id = v_user;
  assert v_row.entry_type = 'grant' and v_row.amount = 3 and v_row.balance_after = 3
     and v_row.reserved_after = 0 and v_row.source = 'signup'
     and v_row.idempotency_key = 'signup:' || v_user::text, 'signup ledger row';
  assert (select plan from public.profiles where id = v_user) = 'free', 'new profile plan';
  assert (select email from public.profiles where id = v_user) = 'ledger@test.local', 'profile email';

  -- reserve reduces available but not balance; idempotent per job
  insert into public.jobs (user_id) values (v_user) returning id into v_job1;
  v_bal := public.reserve_credits(v_user, v_job1, 1);
  assert v_bal = row(3, 1, 2)::public.credit_balance, format('after reserve %s', v_bal);
  assert (select balance from public.credit_accounts where user_id = v_user) = 3, 'reserve changed balance';
  v_bal := public.reserve_credits(v_user, v_job1, 1);
  assert v_bal = row(3, 1, 2)::public.credit_balance, format('after replayed reserve %s', v_bal);
  select count(*) into v_count from public.credit_ledger where job_id = v_job1 and entry_type = 'reserve';
  assert v_count = 1, 'reserve is not idempotent';
  select * into v_row from public.credit_ledger where job_id = v_job1 and entry_type = 'reserve';
  assert v_row.amount = -1 and v_row.balance_after = 3 and v_row.reserved_after = 1, 'reserve ledger row';

  -- overdraft raises P0402 / insufficient_credits and changes nothing
  insert into public.jobs (user_id) values (v_user) returning id into v_job2;
  begin
    perform public.reserve_credits(v_user, v_job2, 3);
    raise exception 'overdraft did not raise';
  exception when sqlstate 'P0402' then
    assert sqlerrm = 'insufficient_credits', sqlerrm;
  end;
  v_bal := public.get_balance(v_user);
  assert v_bal = row(3, 1, 2)::public.credit_balance, format('after failed reserve %s', v_bal);
  assert not exists (select 1 from public.credit_ledger where job_id = v_job2), 'failed reserve wrote a row';

  -- settle success captures; every later settle is a no-op
  v_bal := public.settle_reservation(v_job1, true);
  assert v_bal = row(2, 0, 2)::public.credit_balance, format('after capture %s', v_bal);
  select * into v_row from public.credit_ledger where job_id = v_job1 and entry_type = 'capture';
  assert v_row.amount = -1 and v_row.balance_after = 2 and v_row.reserved_after = 0, 'capture ledger row';
  v_bal := public.settle_reservation(v_job1, true);
  assert v_bal = row(2, 0, 2)::public.credit_balance, format('after replayed capture %s', v_bal);
  v_bal := public.settle_reservation(v_job1, false);
  assert v_bal = row(2, 0, 2)::public.credit_balance, format('release after capture %s', v_bal);
  select count(*) into v_count from public.credit_ledger where job_id = v_job1;
  assert v_count = 2, format('job1 has %s ledger rows', v_count);

  -- settle failure releases; every later settle is a no-op
  v_bal := public.reserve_credits(v_user, v_job2, 1);
  assert v_bal = row(2, 1, 1)::public.credit_balance, format('reserve job2 %s', v_bal);
  v_bal := public.settle_reservation(v_job2, false);
  assert v_bal = row(2, 0, 2)::public.credit_balance, format('release job2 %s', v_bal);
  select * into v_row from public.credit_ledger where job_id = v_job2 and entry_type = 'release';
  assert v_row.amount = 1 and v_row.balance_after = 2 and v_row.reserved_after = 0, 'release ledger row';
  v_bal := public.settle_reservation(v_job2, true);
  assert v_bal = row(2, 0, 2)::public.credit_balance, 'capture after release must be a no-op';
  select count(*) into v_count from public.credit_ledger where job_id = v_job2;
  assert v_count = 2, format('job2 has %s ledger rows', v_count);

  begin
    perform public.settle_reservation(gen_random_uuid(), true);
    raise exception 'settling an unknown job did not raise';
  exception when sqlstate 'P0404' then
    assert sqlerrm = 'not_found', sqlerrm;
  end;

  -- grant idempotency by key
  v_bal := public.grant_credits(v_user, 50, 'lemonsqueezy:order:1', 'grant:k1', 'Credit pack 50');
  assert v_bal = row(52, 0, 52)::public.credit_balance, format('grant %s', v_bal);
  v_bal := public.grant_credits(v_user, 50, 'lemonsqueezy:order:1', 'grant:k1', 'Credit pack 50');
  assert v_bal = row(52, 0, 52)::public.credit_balance, format('replayed grant %s', v_bal);
  select count(*) into v_count from public.credit_ledger where idempotency_key = 'grant:k1';
  assert v_count = 1, 'grant replay wrote a second row';
  select * into v_row from public.credit_ledger where idempotency_key = 'grant:k1';
  assert v_row.amount = 50 and v_row.balance_after = 52 and v_row.note = 'Credit pack 50'
     and v_row.source = 'lemonsqueezy:order:1', 'grant ledger row';

  -- refund_job reverses a capture exactly once
  v_bal := public.refund_job(v_job1, 'test refund');
  assert v_bal = row(53, 0, 53)::public.credit_balance, format('refund %s', v_bal);
  v_bal := public.refund_job(v_job1, 'test refund again');
  assert v_bal = row(53, 0, 53)::public.credit_balance, format('replayed refund %s', v_bal);
  select count(*) into v_count from public.credit_ledger where job_id = v_job1 and entry_type = 'refund';
  assert v_count = 1, 'refund is not idempotent';
  select * into v_row from public.credit_ledger where job_id = v_job1 and entry_type = 'refund';
  assert v_row.amount = 1 and v_row.note = 'test refund', 'refund ledger row';
  begin
    perform public.refund_job(v_job2, 'never captured');
    raise exception 'refunding a released job did not raise';
  exception when sqlstate 'P0404' then null;
  end;

  -- argument validation
  begin
    perform public.grant_credits(v_user, 0, 'x', 'grant:zero');
    raise exception 'zero grant accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.grant_credits(v_user, 1, 'x', null);
    raise exception 'grant without idempotency key accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.reserve_credits(v_user, v_job2, -1);
    raise exception 'negative reserve accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.reserve_credits(gen_random_uuid(), v_job2, 1);
    raise exception 'reserve for an unknown account accepted';
  exception when sqlstate 'P0404' then null;
  end;

  -- adjust_credits: idempotent, cannot overdraw
  v_bal := public.adjust_credits(v_user, -3, 'support', 'adjust:k1', 'chargeback');
  assert v_bal = row(50, 0, 50)::public.credit_balance, format('adjust %s', v_bal);
  v_bal := public.adjust_credits(v_user, -3, 'support', 'adjust:k1', 'chargeback');
  assert v_bal = row(50, 0, 50)::public.credit_balance, format('replayed adjust %s', v_bal);
  begin
    perform public.adjust_credits(v_user, -51, 'support', 'adjust:k2');
    raise exception 'adjust overdraft accepted';
  exception when sqlstate 'P0402' then
    assert sqlerrm = 'insufficient_credits', sqlerrm;
  end;

  -- expire_credits: a due grant expires in full, exactly once
  v_bal := public.grant_credits(v_user, 5, 'promo', 'grant:k2', null, now() - interval '1 second');
  assert v_bal = row(55, 0, 55)::public.credit_balance, format('expiring grant %s', v_bal);
  assert public.expire_credits() = 1, 'expire_credits should process one grant';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(50, 0, 50)::public.credit_balance, format('after expiry %s', v_bal);
  select * into v_row from public.credit_ledger where user_id = v_user and entry_type = 'expire';
  assert v_row.amount = -5 and v_row.balance_after = 50 and v_row.source = 'promo', 'expire ledger row';
  assert public.expire_credits() = 0, 'expire_credits re-processed an expired grant';

  -- partial expiry: credits captured after the grant count as spent from it first
  perform public.grant_credits(v_user, 10, 'promo', 'grant:k3', null, now() - interval '1 second');
  insert into public.jobs (user_id) values (v_user) returning id into v_job3;
  perform public.reserve_credits(v_user, v_job3, 4);
  perform public.settle_reservation(v_job3, true);
  perform public.grant_credits(v_user, 7, 'promo', 'grant:k4', null, now() + interval '1 day');
  assert public.expire_credits() = 1, 'only the due grant expires';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(57, 0, 57)::public.credit_balance, format('after partial expiry %s', v_bal);
  -- the spend belonged to that grant alone: the pack bought before it keeps its credits
  assert public.perishable_pool(v_user) = 7, 'perishable pool after partial expiry';

  -- reserved credits are never expired
  perform public.grant_credits(v_user, 5, 'promo', 'grant:k5', null, now() - interval '1 second');
  insert into public.jobs (user_id) values (v_user) returning id into v_job4;
  perform public.reserve_credits(v_user, v_job4, 60);
  assert public.expire_credits() = 1, 'due grant with an open reservation';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(60, 60, 0)::public.credit_balance, format('expiry capped by available %s', v_bal);
  perform public.settle_reservation(v_job4, false);
  v_bal := public.get_balance(v_user);
  assert v_bal = row(60, 0, 60)::public.credit_balance, format('after release %s', v_bal);

  -- get_balance for an account that does not exist is empty, not an error
  assert public.get_balance(gen_random_uuid()) = row(0, 0, 0)::public.credit_balance, 'missing account balance';

  -- an API caller without a subject reads nothing but its own account: auth.uid() is null
  -- there, and null must not pass the check as "no caller at all"
  begin
    execute 'set local role authenticated';
    perform set_config('request.jwt.claim.sub', '', true);
    begin
      perform public.get_balance(v_user);
      execute 'reset role';
      raise exception 'get_balance without a JWT subject read another account';
    exception when sqlstate '42501' then
      assert sqlerrm = 'forbidden', sqlerrm;
    end;
    execute 'reset role';
  end;

  perform pg_temp.assert_ledger_invariants(v_user);
end;
$$;

-- Two subscription periods in a row: a capture belongs to the grant it consumed, and the
-- next period's grant must not be charged for it a second time. Counting every capture
-- after a grant's seq leaves credits behind that were never granted, every month.
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000c003';
  v_job uuid;
  v_bal public.credit_balance;
  v_expired integer;
begin
  insert into auth.users (id, email) values (v_user, 'periods@test.local');
  perform public.adjust_credits(v_user, -3, 'test', 'periods:drain');  -- the signup grant

  perform public.grant_credits(v_user, 60, 'sub', 'periods:1', 'Pro Monthly', now() - interval '30 days');
  insert into public.jobs (user_id) values (v_user) returning id into v_job;
  perform public.reserve_credits(v_user, v_job, 10);
  perform public.settle_reservation(v_job, true);

  perform public.grant_credits(v_user, 60, 'sub', 'periods:2', 'Pro Monthly', now() - interval '1 second');
  insert into public.jobs (user_id) values (v_user) returning id into v_job;
  perform public.reserve_credits(v_user, v_job, 10);
  perform public.settle_reservation(v_job, true);

  v_bal := public.get_balance(v_user);
  assert v_bal = row(100, 0, 100)::public.credit_balance, format('before expiry %s', v_bal);

  assert public.expire_credits() = 2, 'both periods are due';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(0, 0, 0)::public.credit_balance, format('after both periods expired %s', v_bal);
  select coalesce(-sum(amount), 0) into v_expired from public.credit_ledger
   where user_id = v_user and entry_type = 'expire';
  assert v_expired = 100, format('expired %s of the 100 credits left', v_expired);
  assert public.perishable_pool(v_user) = 0, 'perishable pool after both periods expired';

  -- a pack bought during the period survives: perishable credits are spent first (§13)
  perform public.grant_credits(v_user, 10, 'sub', 'periods:3', 'Pro Monthly', now() - interval '1 second');
  perform public.grant_credits(v_user, 5, 'lemonsqueezy:order:9', 'periods:pack', '50 Credits');
  insert into public.jobs (user_id) values (v_user) returning id into v_job;
  perform public.reserve_credits(v_user, v_job, 12);
  perform public.settle_reservation(v_job, true);
  assert public.expire_credits() = 1, 'the third period is due';
  v_bal := public.get_balance(v_user);
  assert v_bal = row(3, 0, 3)::public.credit_balance, format('pack credits expired too %s', v_bal);

  perform pg_temp.assert_ledger_invariants(v_user);
end;
$$;

-- Long pseudo-random mixed sequence, then the invariants.
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000c002';
  v_job uuid;
  v_i integer;
  v_op integer;
  v_amount integer;
  v_before public.credit_balance;
  v_after public.credit_balance;
  v_overdrafts integer := 0;
  v_counts record;
begin
  insert into auth.users (id, email) values (v_user, 'mixed@test.local');
  perform public.grant_credits(v_user, 5, 'mix', 'mix:grant:0');
  perform setseed(0.4242);

  for v_i in 1..400 loop
    v_op := floor(random() * 8)::integer;
    v_amount := 1 + floor(random() * 5)::integer;
    case v_op
      when 0 then
        perform public.grant_credits(v_user, v_amount, 'mix', format('mix:grant:%s', v_i));
      when 1 then
        begin
          insert into public.jobs (user_id) values (v_user) returning id into v_job;
          perform public.reserve_credits(v_user, v_job, v_amount);
        exception when sqlstate 'P0402' then
          v_overdrafts := v_overdrafts + 1;
          assert (public.get_balance(v_user)).available < v_amount, 'P0402 raised with enough credits';
        end;
      when 2, 3 then
        select r.job_id into v_job from public.credit_ledger r
         where r.user_id = v_user and r.entry_type = 'reserve'
           and not exists (select 1 from public.credit_ledger s
                            where s.job_id = r.job_id and s.entry_type in ('capture', 'release'))
         order by random() limit 1;
        if v_job is not null then
          perform public.settle_reservation(v_job, v_op = 2);
        end if;
      when 4 then
        select c.job_id into v_job from public.credit_ledger c
         where c.user_id = v_user and c.entry_type = 'capture'
           and not exists (select 1 from public.credit_ledger f
                            where f.job_id = c.job_id and f.entry_type = 'refund')
         order by random() limit 1;
        if v_job is not null then
          perform public.refund_job(v_job, 'mix');
        end if;
      when 5 then
        perform public.grant_credits(v_user, v_amount, 'mix', format('mix:expiring:%s', v_i), null,
                                     now() - interval '1 second');
        perform public.expire_credits();
      when 6 then
        begin
          perform public.adjust_credits(v_user, -v_amount, 'mix', format('mix:adjust:%s', v_i));
        exception when sqlstate 'P0402' then
          v_overdrafts := v_overdrafts + 1;
        end;
      else
        v_before := public.get_balance(v_user);
        perform public.grant_credits(v_user, 999, 'mix', 'mix:grant:0');
        v_after := public.get_balance(v_user);
        assert v_before = v_after, 'replayed grant changed the balance';
    end case;
    if v_i % 50 = 0 then
      perform pg_temp.assert_ledger_invariants(v_user);
    end if;
  end loop;

  perform pg_temp.assert_ledger_invariants(v_user);

  select count(*) filter (where entry_type = 'grant') as grants,
         count(*) filter (where entry_type = 'reserve') as reserves,
         count(*) filter (where entry_type = 'capture') as captures,
         count(*) filter (where entry_type = 'release') as releases,
         count(*) filter (where entry_type = 'refund') as refunds,
         count(*) filter (where entry_type = 'expire') as expires,
         count(*) filter (where entry_type = 'adjust') as adjusts
    into v_counts
    from public.credit_ledger where user_id = v_user;
  assert v_counts.grants > 0 and v_counts.reserves > 0 and v_counts.captures > 0 and v_counts.releases > 0
     and v_counts.refunds > 0 and v_counts.expires > 0 and v_counts.adjusts > 0,
    format('sequence did not cover every entry type: %s', v_counts);
  assert v_overdrafts > 0, 'sequence never hit an overdraft';
end;
$$;

-- Deleting the auth user tombstones the profile through delete_user_account (0004): the
-- accounting rows stay, the unused credits are written off, and the invariants still hold.
do $$
declare
  v_user uuid := '00000000-0000-4000-8000-00000000c001';
  v_rows integer;
begin
  -- the jobs above were inserted directly and never left 'queued'; an unfinished job
  -- blocks the deletion, and every reservation of theirs is settled
  update public.jobs set status = 'succeeded' where user_id = v_user and status = 'queued';
  select count(*) into v_rows from public.credit_ledger where user_id = v_user;
  delete from auth.users where id = v_user;
  assert exists (select 1 from public.profiles where id = v_user and deleted_at is not null
                    and email = 'deleted+' || v_user::text || '@invalid'), 'profile not tombstoned';
  assert exists (select 1 from public.credit_accounts where user_id = v_user), 'account lost';
  assert (select count(*) from public.credit_ledger where user_id = v_user) = v_rows + 1, 'ledger lost';
  assert public.get_balance(v_user) = row(0, 0, 0)::public.credit_balance, 'credits not written off';
  assert (select count(*) from public.jobs where user_id = v_user) = 4, 'jobs lost';
  assert (select ledger_rows_kept from public.account_deletions where user_id = v_user) = v_rows + 1,
    'deletion not recorded';
  perform pg_temp.assert_ledger_invariants(v_user);
end;
$$;
