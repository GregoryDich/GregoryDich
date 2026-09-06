-- Purchases and affiliates (contract §4, §12): record_purchase grants credits, attributes a
-- commission to a valid referral code exactly once, and is a no-op under webhook replay.
\set ON_ERROR_STOP on

do $$
declare
  v_aff_user uuid := '00000000-0000-4000-8000-00000000f001';
  v_buyer uuid := '00000000-0000-4000-8000-00000000f002';
  v_buyer2 uuid := '00000000-0000-4000-8000-00000000f003';
  v_affiliate_id uuid;
  v_purchase public.purchases;
  v_again public.purchases;
  v_commission public.affiliate_commissions;
  v_count integer;
  v_sum integer;
begin
  insert into auth.users (id, email)
  values (v_aff_user, 'affiliate@test.local'), (v_buyer, 'buyer@test.local'), (v_buyer2, 'buyer2@test.local');

  insert into public.affiliates (user_id, code, commission_rate)
  values (v_aff_user, 'GREG30', 0.30) returning id into v_affiliate_id;
  assert (select count(*) from public.referral_codes where affiliate_id = v_affiliate_id and code = 'GREG30') = 1,
    'primary code was not mirrored into referral_codes';
  insert into public.referral_codes (code, affiliate_id) values ('greg-alias', v_affiliate_id);
  begin
    insert into public.referral_codes (code, affiliate_id) values ('greg30', v_affiliate_id);
    raise exception 'case-insensitive code uniqueness not enforced';
  exception when unique_violation then null;
  end;

  -- valid referral: purchase + grant + commission, in one call
  v_purchase := public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-1', 'pack_50', 900, 820, 'GREG30',
                                       '{"event":"order_created"}'::jsonb, 'lemonsqueezy:order_created:1');
  assert v_purchase.user_id = v_buyer and v_purchase.provider = 'lemonsqueezy'
     and v_purchase.provider_order_id = 'ord-1' and v_purchase.plan_id = 'pack_50'
     and v_purchase.credits = 50 and v_purchase.amount_cents = 900 and v_purchase.net_cents = 820
     and v_purchase.currency = 'USD' and v_purchase.referral_code = 'GREG30'
     and v_purchase.raw ->> 'event' = 'order_created'
     and v_purchase.idempotency_key = 'lemonsqueezy:order_created:1', 'purchase row';
  assert public.get_balance(v_buyer) = row(53, 0, 53)::public.credit_balance, 'credits not granted';
  assert (select source from public.credit_ledger where idempotency_key = 'lemonsqueezy:order_created:1')
         = 'lemonsqueezy:order:ord-1', 'grant source';
  select * into v_commission from public.affiliate_commissions where purchase_id = v_purchase.id;
  assert found and v_commission.affiliate_id = v_affiliate_id and v_commission.amount_cents = 246
     and v_commission.rate = 0.30 and v_commission.status = 'pending'
     and v_commission.referral_code_id = (select id from public.referral_codes where code = 'GREG30'),
    'commission row';
  assert (select uses from public.referral_codes where code = 'GREG30') = 1, 'uses not counted';
  assert (select plan from public.profiles where id = v_buyer) = 'credits', 'buyer plan';

  -- webhook replay: the identical call changes nothing
  v_again := public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-1', 'pack_50', 900, 820, 'GREG30',
                                    '{"event":"order_created"}'::jsonb, 'lemonsqueezy:order_created:1');
  assert v_again.id = v_purchase.id, 'replay created a second purchase';
  assert public.get_balance(v_buyer) = row(53, 0, 53)::public.credit_balance, 'replay granted again';
  select count(*) into v_count from public.affiliate_commissions where affiliate_id = v_affiliate_id;
  assert v_count = 1, 'replay paid the affiliate twice';
  assert (select uses from public.referral_codes where code = 'GREG30') = 1, 'replay counted a use';
  assert (select count(*) from public.purchases where user_id = v_buyer) = 1, 'replay inserted a purchase';

  -- the same order re-sent under a new event id is still the same purchase
  v_again := public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-1', 'pack_50', 900, 820, 'GREG30',
                                    '{}'::jsonb, 'lemonsqueezy:order_created:1-resent');
  assert v_again.id = v_purchase.id, 're-sent order created a second purchase';
  assert public.get_balance(v_buyer) = row(53, 0, 53)::public.credit_balance, 're-sent order granted again';
  select count(*) into v_count from public.affiliate_commissions where affiliate_id = v_affiliate_id;
  assert v_count = 1, 're-sent order paid the affiliate twice';

  -- the same order id for another user is a conflict
  begin
    perform public.record_purchase(v_buyer2, 'lemonsqueezy', 'ord-1', 'pack_50', 900, 820, null,
                                   '{}'::jsonb, 'lemonsqueezy:order_created:1-other');
    raise exception 'order id reuse across users accepted';
  exception when sqlstate 'P0409' then
    assert sqlerrm = 'conflict', sqlerrm;
  end;

  -- alias code, case-insensitive, second provider
  v_purchase := public.record_purchase(v_buyer2, 'paddle', 'txn_1', 'pack_50', 900, 810, 'Greg-Alias',
                                       '{}'::jsonb, 'paddle:transaction.completed:txn_1');
  select * into v_commission from public.affiliate_commissions where purchase_id = v_purchase.id;
  assert found and v_commission.affiliate_id = v_affiliate_id and v_commission.amount_cents = 243,
    'alias commission';
  assert (select uses from public.referral_codes where code = 'greg-alias') = 1, 'alias uses';

  -- unknown code: purchase and grant, no commission; subscription plan switches the profile
  v_purchase := public.record_purchase(v_buyer2, 'paddle', 'txn_2', 'sub_monthly', 799, 720, 'NOPE',
                                       '{}'::jsonb, 'paddle:transaction.completed:txn_2');
  assert not exists (select 1 from public.affiliate_commissions where purchase_id = v_purchase.id),
    'unknown code earned a commission';
  assert public.get_balance(v_buyer2) = row(113, 0, 113)::public.credit_balance, 'subscription credits';
  assert (select plan from public.profiles where id = v_buyer2) = 'subscription', 'buyer2 plan';

  -- self-referral earns nothing
  v_purchase := public.record_purchase(v_aff_user, 'lemonsqueezy', 'ord-2', 'pack_50', 900, 820, 'GREG30',
                                       '{}'::jsonb, 'lemonsqueezy:order_created:2');
  assert not exists (select 1 from public.affiliate_commissions where purchase_id = v_purchase.id),
    'self-referral earned a commission';
  assert (select uses from public.referral_codes where code = 'GREG30') = 1, 'self-referral counted a use';

  -- inactive code, then inactive affiliate
  update public.referral_codes set active = false where code = 'greg-alias';
  v_purchase := public.record_purchase(v_buyer2, 'paddle', 'txn_3', 'pack_50', 900, 820, 'greg-alias',
                                       '{}'::jsonb, 'paddle:transaction.completed:txn_3');
  assert not exists (select 1 from public.affiliate_commissions where purchase_id = v_purchase.id),
    'inactive code earned a commission';
  update public.affiliates set active = false where id = v_affiliate_id;
  v_purchase := public.record_purchase(v_buyer2, 'paddle', 'txn_4', 'pack_50', 900, 820, 'GREG30',
                                       '{}'::jsonb, 'paddle:transaction.completed:txn_4');
  assert not exists (select 1 from public.affiliate_commissions where purchase_id = v_purchase.id),
    'inactive affiliate earned a commission';
  update public.affiliates set active = true where id = v_affiliate_id;
  assert public.get_balance(v_buyer2) = row(213, 0, 213)::public.credit_balance, 'buyer2 credits';
  assert (select plan from public.profiles where id = v_buyer2) = 'subscription', 'pack purchase downgraded plan';

  -- unknown plan: nothing is written
  begin
    perform public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-9', 'pack_999', 900, 820, 'GREG30',
                                   '{}'::jsonb, 'lemonsqueezy:order_created:9');
    raise exception 'unknown plan accepted';
  exception when sqlstate 'P0404' then
    assert sqlerrm = 'not_found', sqlerrm;
  end;
  assert not exists (select 1 from public.purchases where provider_order_id = 'ord-9'), 'purchase written for unknown plan';
  assert public.get_balance(v_buyer) = row(53, 0, 53)::public.credit_balance, 'credits granted for unknown plan';

  -- a zero-credit plan records the purchase and grants nothing
  insert into public.plans (id, name, credits, price_cents, active) values ('test_zero', 'Zero', 0, 0, false);
  v_purchase := public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-zero', 'test_zero', 0, 0, null, null,
                                       'lemonsqueezy:order_created:zero');
  assert v_purchase.credits = 0 and v_purchase.raw = '{}'::jsonb, 'zero-credit purchase row';
  assert public.get_balance(v_buyer) = row(53, 0, 53)::public.credit_balance, 'zero-credit plan granted credits';
  assert not exists (select 1 from public.credit_ledger where idempotency_key = 'lemonsqueezy:order_created:zero'),
    'zero-credit plan wrote a ledger row';

  -- required arguments
  begin
    perform public.record_purchase(v_buyer, 'lemonsqueezy', 'ord-10', 'pack_50', 900, 820, null, '{}'::jsonb, null);
    raise exception 'missing idempotency key accepted';
  exception when sqlstate '22023' then null;
  end;

  -- the affiliate earned exactly two commissions
  select count(*), sum(amount_cents) into v_count, v_sum
    from public.affiliate_commissions where affiliate_id = v_affiliate_id;
  assert v_count = 2 and v_sum = 489, format('commissions %s / %s cents', v_count, v_sum);

  -- deleting the affiliate user removes codes and commissions but not the purchases
  delete from auth.users where id = v_aff_user;
  assert not exists (select 1 from public.affiliates where id = v_affiliate_id), 'affiliate survived';
  assert not exists (select 1 from public.referral_codes where affiliate_id = v_affiliate_id), 'codes survived';
  assert not exists (select 1 from public.affiliate_commissions where affiliate_id = v_affiliate_id), 'commissions survived';
  assert (select count(*) from public.purchases where user_id in (v_buyer, v_buyer2)) = 6, 'purchases lost';
end;
$$;
