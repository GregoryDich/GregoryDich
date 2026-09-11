-- Tonamorph — 0006: provider refunds that move credits, user referrals, the first-week
-- gift and the support read view (docs/API_CONTRACT.md §1, §3, §4, §6, §12, §14, §15;
-- GTM plan §2.4, §4 P1, Appendix B §3 and §6).
--
-- Refunds: a provider refund or chargeback of a purchase takes back the credits of that
-- purchase that are still unspent — min(purchase credits, balance - reserved), never below
-- zero and never a credit a job already captured or holds reserved — voids the pending
-- affiliate commission, and ends a refunded subscription period. One purchase_refunds row
-- per purchase makes the whole step idempotent even when nothing could be removed.
--
-- Referrals ("send a morph to a friend", distinct from the affiliate programme of §12):
-- every profile owns one 8-character code from an unambiguous alphabet. A sign-up whose
-- referral_code names no affiliate code but a user code records profiles.referred_by and
-- grants the friend 2 extra credits at once; the referrer earns 3 only when the friend's
-- first job succeeds — inside complete_job, so the API-inline pipeline, the remote workers
-- and a replay all pass through the same idempotent seam — and at most 10 friends per 30
-- days are rewarded.
--
-- First-week gift: grant_week1_gifts() gives 2 credits, once, to profiles created 7–8 days
-- ago with at least one succeeded job; the cron runs it hourly, the API reaper task too.
--
-- Errors (SQLSTATE / MESSAGE): P0404 not_found, 22023 invalid_argument.

-- ---------------------------------------------------------------------------
-- Provider refunds (contract §4)
-- ---------------------------------------------------------------------------
create table public.purchase_refunds (
  purchase_id uuid primary key references public.purchases (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  provider public.purchase_provider not null,
  provider_order_id text not null,
  credits_removed integer not null check (credits_removed >= 0),
  commission_voided boolean not null default false,
  reason text,
  created_at timestamptz not null default now(),
  unique (provider, provider_order_id)
);
create index purchase_refunds_user_idx on public.purchase_refunds (user_id, created_at desc);

-- The refund rule: what the purchase granted, capped at what is still available. Credits
-- a job captured are gone and credits a running job holds reserved stay reserved; neither
-- is taken back, so the balance never goes below zero and a job in flight never loses its
-- credit. A replay answers with the recorded row and changes nothing.
create function public.apply_purchase_refund(p_provider text, p_order_id text, p_reason text)
returns table (credits_removed integer, commission_voided boolean)
language plpgsql security definer set search_path = public as $$
declare
  v_provider public.purchase_provider;
  v_purchase public.purchases;
  v_account public.credit_accounts;
  v_refund public.purchase_refunds;
  v_plan public.plans;
  v_remove integer;
  v_voided boolean;
begin
  if p_provider is null or p_provider not in ('lemonsqueezy', 'paddle') then
    raise exception 'invalid_argument' using errcode = '22023',
      detail = 'p_provider must be lemonsqueezy or paddle';
  end if;
  if p_order_id is null or p_order_id = '' then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_order_id is required';
  end if;
  v_provider := p_provider::public.purchase_provider;

  select * into v_purchase from public.purchases
   where provider = v_provider and provider_order_id = p_order_id;
  if not found then
    raise exception 'not_found' using errcode = 'P0404',
      detail = format('purchase %s:%s', p_provider, p_order_id);
  end if;

  v_account := public.lock_credit_account(v_purchase.user_id);

  select * into v_refund from public.purchase_refunds where purchase_id = v_purchase.id;
  if found then
    credits_removed := v_refund.credits_removed;
    commission_voided := v_refund.commission_voided;
    return next;
    return;
  end if;

  v_remove := least(v_purchase.credits, greatest(v_account.balance - v_account.reserved, 0));
  if v_remove > 0 then
    perform public.adjust_credits(v_purchase.user_id, -v_remove,
                                  v_provider::text || ':order:' || p_order_id,
                                  'refund:' || v_provider::text || ':' || p_order_id,
                                  'Refunded at the provider' || coalesce(': ' || p_reason, ''));
  end if;

  -- A commission already paid out stays `paid`; clawing it back is an operator decision.
  update public.affiliate_commissions set status = 'void'
   where purchase_id = v_purchase.id and status = 'pending';
  v_voided := found;

  select * into v_plan from public.plans where id = v_purchase.plan_id;
  if found and v_plan.interval is not null then
    -- The refunded period is over: the subscription is cancelled as of now, so nothing
    -- keeps reporting it as renewing, and the profile drops off the plan below.
    update public.subscriptions
       set status = 'cancelled',
           cancelled_at = coalesce(cancelled_at, now()),
           current_period_end = least(coalesce(current_period_end, now()), now())
     where user_id = v_purchase.user_id and provider = v_provider
       and (plan_id = v_purchase.plan_id or plan_id is null)
       and status in ('trialing', 'active', 'past_due', 'paused');
  end if;

  insert into public.purchase_refunds
    (purchase_id, user_id, provider, provider_order_id, credits_removed, commission_voided, reason)
  values
    (v_purchase.id, v_purchase.user_id, v_provider, p_order_id, v_remove, v_voided, p_reason);

  -- The plan the profile is left on: a subscription still running (a cancelled one keeps
  -- its plan until the period ends, §13), else a pack that was not refunded, else free.
  update public.profiles p
     set plan = case
       when exists (select 1 from public.subscriptions s
                     where s.user_id = p.id
                       and (s.status in ('trialing', 'active', 'past_due', 'paused')
                            or (s.status = 'cancelled' and s.current_period_end > now())))
         then 'subscription'
       when exists (select 1 from public.purchases pu
                      join public.plans pl on pl.id = pu.plan_id
                     where pu.user_id = p.id and pl.interval is null and pl.credits > 0
                       and not exists (select 1 from public.purchase_refunds r
                                        where r.purchase_id = pu.id))
         then 'credits'
       else 'free' end
   where p.id = v_purchase.user_id;

  credits_removed := v_remove;
  commission_voided := v_voided;
  return next;
end;
$$;

-- ---------------------------------------------------------------------------
-- User referral codes (contract §1, §3, §12)
-- ---------------------------------------------------------------------------
alter table public.profiles
  add column referred_by uuid references public.profiles (id) on delete set null;
create index profiles_referred_by_idx on public.profiles (referred_by) where referred_by is not null;

create table public.user_referral_codes (
  code text primary key check (code ~ '^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$'),
  user_id uuid not null unique references public.profiles (id) on delete cascade,
  created_at timestamptz not null default now()
);

-- Eight characters from an alphabet without 0/O, 1/I/L: readable aloud and typed without
-- ambiguity. Randomness comes from gen_random_uuid() (core PostgreSQL) so nothing depends
-- on the pgcrypto schema being on the search path. Unique against the user codes and,
-- so a sign-up form can never be ambiguous, against the affiliate codes too.
create function public.generate_user_referral_code() returns text
language plpgsql as $$
declare
  v_alphabet constant text := 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
  v_bytes bytea;
  v_code text;
begin
  loop
    v_bytes := decode(replace(gen_random_uuid()::text, '-', ''), 'hex');
    v_code := '';
    for i in 0..7 loop
      v_code := v_code || substr(v_alphabet, (get_byte(v_bytes, i) % length(v_alphabet)) + 1, 1);
    end loop;
    exit when not exists (select 1 from public.user_referral_codes c where c.code = v_code)
          and not exists (select 1 from public.referral_codes r where lower(r.code) = lower(v_code));
  end loop;
  return v_code;
end;
$$;

create function public.assign_user_referral_code() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.user_referral_codes (code, user_id)
  values (public.generate_user_referral_code(), new.id)
  on conflict (user_id) do nothing;
  return new;
end;
$$;
create trigger profiles_assign_referral_code
  after insert on public.profiles
  for each row execute function public.assign_user_referral_code();

-- Backfill, one row at a time so every generated code sees the ones before it.
do $$
declare
  v_profile record;
begin
  for v_profile in
    select p.id from public.profiles p
     where not exists (select 1 from public.user_referral_codes c where c.user_id = p.id)
     order by p.created_at
  loop
    insert into public.user_referral_codes (code, user_id)
    values (public.generate_user_referral_code(), v_profile.id);
  end loop;
end;
$$;

-- The referrer a sign-up names with a user code: spelled in any case, never the new user
-- themselves, never a deleted account. Null when the metadata names no live user code.
create function public.signup_referrer(p_meta jsonb, p_user_id uuid) returns uuid
language sql stable as $$
  select c.user_id
    from public.user_referral_codes c
    join public.profiles p on p.id = c.user_id
   where c.code = upper(btrim(p_meta ->> 'referral_code'))
     and p.deleted_at is null
     and c.user_id <> p_user_id
   limit 1;
$$;

-- Same profile + credit account + welcome grant as 0004; the referral code in the sign-up
-- metadata now resolves to an affiliate code first (profiles.referral_code, unchanged) and
-- otherwise to a user code (profiles.referred_by plus 2 extra credits for the friend).
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_signup_credits integer;
  v_meta jsonb := coalesce(new.raw_user_meta_data, '{}'::jsonb);
  v_affiliate_code text := public.signup_referral_code(v_meta);
  v_referrer uuid;
begin
  if v_affiliate_code is null then
    v_referrer := public.signup_referrer(v_meta, new.id);
  end if;
  insert into public.profiles
    (id, email, referral_code, referred_by, utm_source, utm_medium, utm_campaign, utm_content,
     utm_term, marketing_opt_in, terms_accepted_at)
  values
    (new.id, new.email, v_affiliate_code, v_referrer,
     public.signup_meta_text(v_meta, 'utm_source'), public.signup_meta_text(v_meta, 'utm_medium'),
     public.signup_meta_text(v_meta, 'utm_campaign'), public.signup_meta_text(v_meta, 'utm_content'),
     public.signup_meta_text(v_meta, 'utm_term'),
     public.signup_meta_bool(v_meta, 'marketing_opt_in'),
     public.signup_meta_timestamp(v_meta, 'terms_accepted_at'))
  on conflict (id) do nothing;
  insert into public.credit_accounts (user_id) values (new.id) on conflict (user_id) do nothing;
  select credits into v_signup_credits from public.plans where id = 'free';
  v_signup_credits := coalesce(v_signup_credits, 3);
  if v_signup_credits > 0 then
    perform public.grant_credits(new.id, v_signup_credits, 'signup', 'signup:' || new.id::text, 'Welcome credits');
  end if;
  if v_referrer is not null
     and (select referred_by from public.profiles where id = new.id) = v_referrer then
    perform public.grant_credits(new.id, 2, 'referral_bonus', 'referral_bonus:' || new.id::text,
                                 'Invited by a friend');
  end if;
  return new;
end;
$$;

-- The referrer's reward for a friend's first morph: 3 credits under `referral:<friend>`,
-- so it can only ever be granted once per friend, and at most 10 friends per 30 days per
-- referrer (anti-farming). Returns the rewarded referrer, null when nothing was granted.
-- Called by complete_job; not executable by any API role.
create function public.reward_referral(p_friend_id uuid) returns uuid
language plpgsql security definer set search_path = public as $$
declare
  v_referrer uuid;
  v_recent integer;
begin
  select f.referred_by into v_referrer
    from public.profiles f
    join public.profiles r on r.id = f.referred_by
   where f.id = p_friend_id and r.deleted_at is null;
  if v_referrer is null then
    return null;
  end if;
  if exists (select 1 from public.credit_ledger where idempotency_key = 'referral:' || p_friend_id::text) then
    return null;
  end if;
  perform public.lock_credit_account(v_referrer);
  select count(*) into v_recent from public.credit_ledger
   where user_id = v_referrer and entry_type = 'grant' and source = 'referral'
     and created_at >= now() - interval '30 days';
  if v_recent >= 10 then
    return null;
  end if;
  perform public.grant_credits(v_referrer, 3, 'referral', 'referral:' || p_friend_id::text,
                               'A friend''s first morph');
  return v_referrer;
end;
$$;

-- complete_job as in 0002, plus the referral reward when this is the user's first success.
create or replace function public.complete_job(p_job_id uuid, p_result jsonb)
returns public.jobs
language plpgsql security definer set search_path = public as $$
declare
  v_job public.jobs;
  v_balance public.credit_balance;
  v_charged integer;
  v_expires_at timestamptz;
begin
  select * into v_job from public.jobs where id = p_job_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('job %s', p_job_id);
  end if;
  if v_job.status = 'succeeded' then
    return v_job;
  end if;
  if v_job.status not in ('queued', 'running') then
    raise exception 'conflict' using errcode = 'P0409', detail = format('job is %s', v_job.status);
  end if;

  v_balance := public.settle_reservation(p_job_id, true);
  select -amount into v_charged from public.credit_ledger where job_id = p_job_id and entry_type = 'capture';
  v_expires_at := coalesce((p_result ->> 'expires_at')::timestamptz, now() + interval '24 hours');

  update public.jobs
     set status = 'succeeded',
         stage = 'done',
         progress = 1,
         result = jsonb_build_object('expires_at', v_expires_at)
                  || coalesce(p_result, '{}'::jsonb)
                  || jsonb_build_object('job_id', id, 'credits_charged', v_charged, 'balance_after', v_balance.credits),
         error = null,
         started_at = coalesce(started_at, now()),
         finished_at = now(),
         expires_at = v_expires_at
   where id = p_job_id returning * into v_job;

  -- The friend's first successful morph is what earns the referrer their credits.
  if not exists (select 1 from public.jobs j
                  where j.user_id = v_job.user_id and j.status = 'succeeded' and j.id <> p_job_id) then
    perform public.reward_referral(v_job.user_id);
  end if;
  return v_job;
end;
$$;

-- What GET /v1/me shows: the code, how many friends signed up with it and how many
-- credits it earned. A profile that somehow has no code (created before this migration
-- on a path the backfill missed) is given one here.
create function public.user_referral_summary(p_user_id uuid)
returns table (code text, friends_joined integer, morphs_earned integer)
language plpgsql security definer set search_path = public as $$
begin
  insert into public.user_referral_codes (code, user_id)
  select public.generate_user_referral_code(), p_user_id
   where exists (select 1 from public.profiles p where p.id = p_user_id)
     and not exists (select 1 from public.user_referral_codes c where c.user_id = p_user_id);
  return query
    select c.code,
           (select count(*) from public.profiles f where f.referred_by = p_user_id)::integer,
           (select coalesce(sum(l.amount), 0) from public.credit_ledger l
             where l.user_id = p_user_id and l.entry_type = 'grant' and l.source = 'referral')::integer
      from public.user_referral_codes c
     where c.user_id = p_user_id;
end;
$$;

-- ---------------------------------------------------------------------------
-- First-week gift (GTM Appendix B §3): day 7, two morphs on us, once
-- ---------------------------------------------------------------------------
-- Profiles created between 8 and 7 days ago with at least one succeeded job and no gift
-- yet. Returns the ids granted in this run so the caller can tell each of them; the
-- idempotency key makes an hourly cron and the API reaper safe to run side by side.
create function public.grant_week1_gifts()
returns table (user_id uuid)
language plpgsql security definer set search_path = public as $$
declare
  v_profile record;
begin
  for v_profile in
    select p.id from public.profiles p
     where p.deleted_at is null
       and p.created_at <= now() - interval '7 days'
       and p.created_at > now() - interval '8 days'
       and exists (select 1 from public.credit_accounts a where a.user_id = p.id)
       and exists (select 1 from public.jobs j where j.user_id = p.id and j.status = 'succeeded')
       and not exists (select 1 from public.credit_ledger l
                        where l.idempotency_key = 'gift:week1:' || p.id::text)
     order by p.created_at
  loop
    perform public.grant_credits(v_profile.id, 2, 'gift:week1', 'gift:week1:' || v_profile.id::text,
                                 'One week in. Two morphs on us.');
    user_id := v_profile.id;
    return next;
  end loop;
end;
$$;

-- ---------------------------------------------------------------------------
-- Support read view (contract §15): one row per profile, service_role only
-- ---------------------------------------------------------------------------
create view public.support_user_overview as
select p.id as user_id,
       p.email,
       p.plan,
       p.created_at,
       p.deleted_at,
       coalesce(a.balance, 0) as balance,
       coalesce(a.reserved, 0) as reserved,
       (select count(*) from public.jobs j where j.user_id = p.id and j.status = 'succeeded')::integer as morphs_total,
       (select max(j.finished_at) from public.jobs j where j.user_id = p.id and j.status = 'succeeded') as last_morph_at,
       (select count(*) from public.purchases pu where pu.user_id = p.id)::integer as purchases,
       (select count(*) from public.purchase_refunds r where r.user_id = p.id)::integer as refunds,
       (select count(*) from public.api_keys k where k.user_id = p.id and k.revoked_at is null)::integer as api_keys,
       (select n.score from public.nps_responses n where n.user_id = p.id order by n.created_at desc limit 1) as nps_score,
       (select count(*) from public.job_feedback f where f.user_id = p.id and f.rating = 'up')::integer as feedback_up,
       (select count(*) from public.job_feedback f where f.user_id = p.id and f.rating = 'down')::integer as feedback_down,
       (select count(*) from public.job_feedback f where f.user_id = p.id and f.refunded)::integer as feedback_refunds,
       c.code as referral_code,
       p.referred_by,
       (select count(*) from public.profiles f where f.referred_by = p.id)::integer as friends_joined
  from public.profiles p
  left join public.credit_accounts a on a.user_id = p.id
  left join public.user_referral_codes c on c.user_id = p.id;

-- ---------------------------------------------------------------------------
-- Privileges and row-level security (same model as 0003)
-- ---------------------------------------------------------------------------
grant all on public.purchase_refunds, public.user_referral_codes to service_role;
grant select on public.support_user_overview to service_role;
alter table public.purchase_refunds enable row level security;
alter table public.user_referral_codes enable row level security;
-- No policies and no grants for anon/authenticated: both tables are service_role only.

revoke execute on function
  public.apply_purchase_refund(text, text, text),
  public.generate_user_referral_code(),
  public.signup_referrer(jsonb, uuid),
  public.reward_referral(uuid),
  public.user_referral_summary(uuid),
  public.grant_week1_gifts()
from public;
grant execute on function public.assign_user_referral_code() to public;
grant execute on function
  public.apply_purchase_refund(text, text, text),
  public.user_referral_summary(uuid),
  public.grant_week1_gifts()
to service_role;
