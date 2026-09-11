-- Provider refunds (contract §4, 0006): apply_purchase_refund takes back the unspent part
-- of a purchase — min(purchase credits, balance - reserved), never a captured or reserved
-- credit — voids the pending commission, ends a refunded subscription, and is idempotent.
\set ON_ERROR_STOP on

-- helper: a captured job for the user (spends one credit)
create function pg_temp.spend_one(p_user uuid) returns void
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
  v_aff_user uuid := '00000000-0000-4000-8000-00000000a201';
  v_buyer uuid := '00000000-0000-4000-8000-00000000a202';
  v_affiliate_id uuid;
  v_purchase public.purchases;
  v_queued public.jobs;
  v_out record;
  v_row public.credit_ledger;
  v_refund public.purchase_refunds;
  v_sum integer;
  v_count integer;
begin
  insert into auth.users (id, email)
  values (v_aff_user, 'refund-affiliate@test.local'), (v_buyer, 'refund-buyer@test.local');
  insert into public.affiliates (user_id, code, commission_rate)
  values (v_aff_user, 'AFF30', 0.30) returning id into v_affiliate_id;

  -- a pack bought through an affiliate, two morphs spent, one job still holding a credit
  v_purchase := public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-r1', 'pack_50', 900, 820, 'AFF30',
                                       '{}'::jsonb, 'lemonsqueezy:order_created:r1');
  assert public.get_balance(v_buyer) = row(53, 0, 53)::public.credit_balance, 'pack granted';
  assert (select status from public.affiliate_commissions where purchase_id = v_purchase.id) = 'pending',
    'commission pending';
  perform pg_temp.spend_one(v_buyer);
  perform pg_temp.spend_one(v_buyer);
  v_queued := public.create_job(v_buyer, '{}'::jsonb, '{}'::jsonb, null);
  assert public.get_balance(v_buyer) = row(51, 1, 50)::public.credit_balance, 'before refund';

  -- the refund removes min(50, available 50) = 50, never the reserved credit
  select * into v_out from public.apply_purchase_refund('lemonsqueezy', 'ord-r1', 'requested_by_customer');
  assert v_out.credits_removed = 50 and v_out.commission_voided, format('refund outcome %s', v_out);
  assert public.get_balance(v_buyer) = row(1, 1, 0)::public.credit_balance, format('after refund %s', public.get_balance(v_buyer));
  select * into v_row from public.credit_ledger where idempotency_key = 'refund:lemonsqueezy:ord-r1';
  assert found and v_row.entry_type = 'adjust' and v_row.amount = -50 and v_row.user_id = v_buyer
     and v_row.source = 'lemonsqueezy:order:ord-r1'
     and v_row.note = 'Refunded at the provider: requested_by_customer'
     and v_row.balance_after = 1 and v_row.reserved_after = 1, 'refund ledger row';
  assert (select status from public.affiliate_commissions where purchase_id = v_purchase.id) = 'void',
    'commission not voided';
  select * into v_refund from public.purchase_refunds where purchase_id = v_purchase.id;
  assert found and v_refund.user_id = v_buyer and v_refund.provider = 'lemonsqueezy'
     and v_refund.provider_order_id = 'ord-r1' and v_refund.credits_removed = 50
     and v_refund.commission_voided and v_refund.reason = 'requested_by_customer', 'purchase_refunds row';
  assert (select plan from public.profiles where id = v_buyer) = 'free', 'a refunded pack leaves no plan';

  -- replay: the recorded outcome, nothing moves
  select * into v_out from public.apply_purchase_refund('lemonsqueezy', 'ord-r1', 'again');
  assert v_out.credits_removed = 50 and v_out.commission_voided, 'replay outcome';
  assert public.get_balance(v_buyer) = row(1, 1, 0)::public.credit_balance, 'replay moved credits';
  select count(*) into v_count from public.credit_ledger where user_id = v_buyer and entry_type = 'adjust';
  assert v_count = 1, 'replay wrote a second adjust row';
  assert (select count(*) from public.purchase_refunds where user_id = v_buyer) = 1, 'replay wrote a second refund row';

  -- the queued job still settles normally on the credit it holds
  perform public.settle_reservation(v_queued.id, true);
  assert public.get_balance(v_buyer) = row(0, 0, 0)::public.credit_balance, 'reserved credit was taken by the refund';

  -- everything already spent: nothing to remove, still recorded, and later credits are safe
  v_purchase := public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-r2', 'pack_50', 900, 820, null,
                                       '{}'::jsonb, 'lemonsqueezy:order_created:r2');
  perform public.adjust_credits(v_buyer, -50, 'test', 'refund-test:drain-r2');
  select * into v_out from public.apply_purchase_refund('lemonsqueezy', 'ord-r2', null);
  assert v_out.credits_removed = 0 and not v_out.commission_voided, format('spent refund %s', v_out);
  assert not exists (select 1 from public.credit_ledger where idempotency_key = 'refund:lemonsqueezy:ord-r2'),
    'a zero refund wrote a ledger row';
  assert (select credits_removed from public.purchase_refunds where purchase_id = v_purchase.id) = 0
     and (select reason from public.purchase_refunds where purchase_id = v_purchase.id) is null, 'zero refund row';
  perform public.grant_credits(v_buyer, 10, 'support', 'refund-test:support-10');
  select * into v_out from public.apply_purchase_refund('lemonsqueezy', 'ord-r2', null);
  assert v_out.credits_removed = 0, 'a replay after new credits removed them';
  assert public.get_balance(v_buyer) = row(10, 0, 10)::public.credit_balance, 'later credits touched by a replay';

  -- partially spent: only what is left of the purchase
  v_purchase := public.record_purchase(v_buyer, 'paddle', 'txn-r3', 'pack_50', 900, 800, null,
                                       '{}'::jsonb, 'paddle:transaction.completed:r3');
  perform public.adjust_credits(v_buyer, -40, 'test', 'refund-test:drain-r3');
  assert public.get_balance(v_buyer) = row(20, 0, 20)::public.credit_balance, 'before partial refund';
  select * into v_out from public.apply_purchase_refund('paddle', 'txn-r3', 'chargeback');
  assert v_out.credits_removed = 20, format('partial refund %s', v_out);
  assert public.get_balance(v_buyer) = row(0, 0, 0)::public.credit_balance, 'partial refund balance';
  assert (select note from public.credit_ledger where idempotency_key = 'refund:paddle:txn-r3')
         = 'Refunded at the provider: chargeback', 'partial refund note';

  -- a subscription refund cancels the subscription as of now and drops the profile to the
  -- pack it still holds
  v_purchase := public.record_purchase(v_buyer, 'paddle', 'txn-r4', 'pack_50', 900, 800, null,
                                       '{}'::jsonb, 'paddle:transaction.completed:r4');
  v_purchase := public.record_purchase(v_buyer, 'paddle', 'txn-s1', 'sub_monthly', 799, 720, null,
                                       '{}'::jsonb, 'paddle:transaction.completed:s1');
  insert into public.subscriptions (user_id, provider, provider_subscription_id, plan_id, status, current_period_end)
  values (v_buyer, 'paddle', 'sub-r1', 'sub_monthly', 'active', now() + interval '20 days');
  assert (select plan from public.profiles where id = v_buyer) = 'subscription', 'subscription plan';
  assert public.get_balance(v_buyer) = row(110, 0, 110)::public.credit_balance, 'pack + subscription credits';
  select * into v_out from public.apply_purchase_refund('paddle', 'txn-s1', 'requested_by_customer');
  assert v_out.credits_removed = 60, format('subscription refund %s', v_out);
  assert (select status from public.subscriptions where provider_subscription_id = 'sub-r1') = 'cancelled'
     and (select cancelled_at from public.subscriptions where provider_subscription_id = 'sub-r1') is not null
     and (select current_period_end from public.subscriptions where provider_subscription_id = 'sub-r1') <= now(),
    'subscription not ended';
  assert (select plan from public.profiles where id = v_buyer) = 'credits', 'plan after subscription refund';
  assert public.get_balance(v_buyer) = row(50, 0, 50)::public.credit_balance, 'pack credits survived';

  -- a commission already paid out is left for the operator
  v_purchase := public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-r5', 'pack_50', 900, 820, 'AFF30',
                                       '{}'::jsonb, 'lemonsqueezy:order_created:r5');
  update public.affiliate_commissions set status = 'paid', paid_at = now() where purchase_id = v_purchase.id;
  select * into v_out from public.apply_purchase_refund('lemonsqueezy', 'ord-r5', null);
  assert v_out.credits_removed = 50 and not v_out.commission_voided, format('paid commission refund %s', v_out);
  assert (select status from public.affiliate_commissions where purchase_id = v_purchase.id) = 'paid',
    'a paid commission was voided';

  -- unknown purchase, bad provider, empty order id
  begin
    perform public.apply_purchase_refund('lemonsqueezy', 'ord-nope', null);
    raise exception 'unknown purchase refunded';
  exception when sqlstate 'P0404' then
    assert sqlerrm = 'not_found', sqlerrm;
  end;
  begin
    perform public.apply_purchase_refund('stripe', 'ord-r1', null);
    raise exception 'unknown provider accepted';
  exception when sqlstate '22023' then null;
  end;
  begin
    perform public.apply_purchase_refund('paddle', '', null);
    raise exception 'empty order id accepted';
  exception when sqlstate '22023' then null;
  end;

  -- the ledger invariant holds throughout
  select coalesce(sum(amount), 0) into v_sum from public.credit_ledger
   where user_id = v_buyer and entry_type in ('grant', 'capture', 'refund', 'expire', 'adjust');
  assert v_sum = (select balance from public.credit_accounts where user_id = v_buyer),
    format('ledger sum %s <> balance', v_sum);
end;
$$;

-- privileges: service_role only
do $$
declare
  v_out record;
begin
  execute 'set local role authenticated';
  perform set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-00000000a202', true);
  begin
    perform public.apply_purchase_refund('lemonsqueezy', 'ord-r1', null);
    raise exception 'apply_purchase_refund executable by authenticated';
  exception when insufficient_privilege then null;
  end;
  begin
    perform count(*) from public.purchase_refunds;
    raise exception 'purchase_refunds readable by authenticated';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';

  execute 'set local role service_role';
  select * into v_out from public.apply_purchase_refund('lemonsqueezy', 'ord-r1', null);
  assert v_out.credits_removed = 50, 'service_role replay';
  assert (select count(*) from public.purchase_refunds) >= 5, 'service_role cannot read purchase_refunds';
  execute 'reset role';
end;
$$;
