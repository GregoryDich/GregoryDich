-- Sign-up metadata (contract §1, 0004): handle_new_user copies the referral code, UTM
-- attribution, marketing consent and terms acceptance from auth.users.raw_user_meta_data
-- into profiles, tolerates anything a form can send, and still grants 3 credits once.
\set ON_ERROR_STOP on

do $$
declare
  v_affiliate_user uuid := '00000000-0000-4000-8000-00000000b001';
  v_full uuid := '00000000-0000-4000-8000-00000000b002';
  v_unknown uuid := '00000000-0000-4000-8000-00000000b003';
  v_bare uuid := '00000000-0000-4000-8000-00000000b004';
  v_messy uuid := '00000000-0000-4000-8000-00000000b005';
  v_inactive uuid := '00000000-0000-4000-8000-00000000b006';
  v_profile public.profiles;
  v_count integer;
begin
  insert into auth.users (id, email) values (v_affiliate_user, 'meta-affiliate@test.local');
  insert into public.affiliates (user_id, code) values (v_affiliate_user, 'META30');
  insert into public.referral_codes (code, affiliate_id)
  select 'meta-old', id from public.affiliates where user_id = v_affiliate_user;
  update public.referral_codes set active = false where code = 'meta-old';

  -- every field, the code in another case: stored as spelled in referral_codes
  insert into auth.users (id, email, raw_user_meta_data) values (v_full, 'meta-full@test.local',
    '{"referral_code":" meta30 ","utm_source":"tiktok","utm_medium":"video","utm_campaign":"launch",
      "utm_content":"clip-7","utm_term":"stems","marketing_opt_in":true,
      "terms_accepted_at":"2026-09-01T10:00:00+02:00"}'::jsonb);
  select * into v_profile from public.profiles where id = v_full;
  assert v_profile.referral_code = 'META30', format('referral code %s', v_profile.referral_code);
  assert v_profile.utm_source = 'tiktok' and v_profile.utm_medium = 'video' and v_profile.utm_campaign = 'launch'
     and v_profile.utm_content = 'clip-7' and v_profile.utm_term = 'stems', 'utm fields';
  assert v_profile.marketing_opt_in = true, 'marketing_opt_in';
  assert v_profile.terms_accepted_at = '2026-09-01T08:00:00Z'::timestamptz, 'terms_accepted_at';
  assert v_profile.email = 'meta-full@test.local' and v_profile.plan = 'free', 'base profile fields';
  assert public.get_balance(v_full) = row(3, 0, 3)::public.credit_balance, 'welcome credits';
  select count(*) into v_count from public.credit_ledger where user_id = v_full;
  assert v_count = 1, format('signup wrote %s ledger rows', v_count);
  assert (select uses from public.referral_codes where code = 'META30') = 0, 'sign-up counted a use';

  -- an unknown code is dropped, not an error; the rest is still copied
  insert into auth.users (id, email, raw_user_meta_data) values (v_unknown, 'meta-unknown@test.local',
    '{"referral_code":"NOPE","utm_source":"newsletter","marketing_opt_in":false}'::jsonb);
  select * into v_profile from public.profiles where id = v_unknown;
  assert v_profile.referral_code is null and v_profile.utm_source = 'newsletter'
     and v_profile.marketing_opt_in = false and v_profile.terms_accepted_at is null, 'unknown code profile';
  assert public.get_balance(v_unknown) = row(3, 0, 3)::public.credit_balance, 'welcome credits (unknown code)';

  -- an inactive code counts as unknown
  insert into auth.users (id, email, raw_user_meta_data) values (v_inactive, 'meta-inactive@test.local',
    '{"referral_code":"meta-old"}'::jsonb);
  assert (select referral_code from public.profiles where id = v_inactive) is null, 'inactive code accepted';

  -- no metadata at all: defaults
  insert into auth.users (id, email) values (v_bare, 'meta-bare@test.local');
  select * into v_profile from public.profiles where id = v_bare;
  assert v_profile.referral_code is null and v_profile.utm_source is null and v_profile.utm_term is null
     and v_profile.marketing_opt_in = false and v_profile.terms_accepted_at is null, 'bare profile';
  assert public.get_balance(v_bare) = row(3, 0, 3)::public.credit_balance, 'welcome credits (bare)';

  -- whatever a form sends: over-long and padded text is trimmed and capped, a non-boolean
  -- consent is false, an unparsable timestamp is null, and the sign-up still succeeds
  insert into auth.users (id, email, raw_user_meta_data) values (v_messy, 'meta-messy@test.local',
    jsonb_build_object('referral_code', 42, 'utm_source', '  ' || repeat('x', 150) || '  ',
                       'utm_medium', '   ', 'marketing_opt_in', 'yes', 'terms_accepted_at', 'not-a-date',
                       'utm_campaign', 'TRUE'));
  select * into v_profile from public.profiles where id = v_messy;
  assert v_profile.referral_code is null, 'numeric code accepted';
  assert length(v_profile.utm_source) = 100 and v_profile.utm_source = repeat('x', 100), 'utm_source not capped';
  assert v_profile.utm_medium is null, 'blank utm_medium stored';
  assert v_profile.utm_campaign = 'TRUE', 'utm_campaign';
  assert v_profile.marketing_opt_in = false and v_profile.terms_accepted_at is null, 'messy consent fields';
  assert public.get_balance(v_messy) = row(3, 0, 3)::public.credit_balance, 'welcome credits (messy)';

  -- the string forms of the consent flag are honoured
  update auth.users set raw_user_meta_data = '{"marketing_opt_in":"True"}'::jsonb where id = v_messy;
  assert public.signup_meta_bool('{"marketing_opt_in":"True"}'::jsonb, 'marketing_opt_in') = true, 'string true';
  assert public.signup_meta_bool('{"marketing_opt_in":null}'::jsonb, 'marketing_opt_in') = false, 'null consent';

  -- API roles cannot read profiles of others through the helpers either
  execute 'set local role authenticated';
  begin
    perform public.signup_referral_code('{"referral_code":"META30"}'::jsonb);
    raise exception 'signup_referral_code executable by authenticated';
  exception when insufficient_privilege then null;
  end;
  execute 'reset role';
end;
$$;
