-- SnapPlay AI — 0001: extensions, enums, tables, triggers, seed data.
-- Conventions: uuid primary keys via gen_random_uuid(), timestamptz everywhere.
-- Functions live in 0002_functions.sql, row-level security in 0003_rls.sql.
-- Reference: docs/API_CONTRACT.md §3, §6, §11, §12.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
create type public.job_status as enum ('queued', 'running', 'succeeded', 'failed', 'cancelled');
create type public.job_stage as enum ('upload', 'separate', 'transcribe', 'analyze', 'package', 'done');
create type public.ledger_entry_type as enum ('grant', 'reserve', 'capture', 'release', 'refund', 'expire', 'adjust');
create type public.purchase_provider as enum ('lemonsqueezy', 'paddle');
create type public.commission_status as enum ('pending', 'paid', 'void');

-- ---------------------------------------------------------------------------
-- Generic updated_at maintenance
-- ---------------------------------------------------------------------------
create function public.set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Identity and credits
-- ---------------------------------------------------------------------------
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  display_name text,
  plan text not null default 'free' check (plan in ('free', 'credits', 'subscription')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- balance is a cache of the ledger (see 0002 / README "Invariants"); reserved is the
-- sum of open job reservations. Both are only ever written by the ledger functions.
create table public.credit_accounts (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  balance integer not null default 0 check (balance >= 0),
  reserved integer not null default 0 check (reserved >= 0),
  updated_at timestamptz not null default now(),
  check (reserved <= balance)
);
create trigger credit_accounts_set_updated_at
  before update on public.credit_accounts
  for each row execute function public.set_updated_at();

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  status public.job_status not null default 'queued',
  stage public.job_stage not null default 'upload',
  progress real not null default 0 check (progress >= 0 and progress <= 1),
  options jsonb not null default '{}'::jsonb,
  input_meta jsonb not null default '{}'::jsonb,
  result jsonb,
  error jsonb,
  idempotency_key text,
  worker_ref text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz not null default now(),
  expires_at timestamptz,
  unique (user_id, idempotency_key)
);
create index jobs_user_created_idx on public.jobs (user_id, created_at desc);
create index jobs_status_started_idx on public.jobs (status, started_at);
create trigger jobs_set_updated_at
  before update on public.jobs
  for each row execute function public.set_updated_at();

-- Append-only. Sign convention (enforced below):
--   grant/refund/release  > 0      reserve/capture < 0      expire <= 0      adjust <> 0
-- balance = SUM(amount) over grant/capture/refund/expire/adjust
-- reserved = -SUM(amount) over reserve rows whose job has no capture/release row
create table public.credit_ledger (
  id uuid primary key default gen_random_uuid(),
  seq bigint generated always as identity unique,
  user_id uuid not null references public.profiles (id) on delete cascade,
  entry_type public.ledger_entry_type not null,
  amount integer not null,
  balance_after integer not null check (balance_after >= 0),
  reserved_after integer not null check (reserved_after >= 0),
  job_id uuid references public.jobs (id),
  source text,
  idempotency_key text unique,
  note text,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  check (
    (entry_type in ('grant', 'refund', 'release') and amount > 0)
    or (entry_type in ('reserve', 'capture') and amount < 0)
    or (entry_type = 'expire' and amount <= 0)
    or (entry_type = 'adjust' and amount <> 0)
  ),
  check (expires_at is null or entry_type = 'grant')
);
create unique index credit_ledger_job_entry_idx
  on public.credit_ledger (job_id, entry_type) where job_id is not null;
create index credit_ledger_user_seq_idx on public.credit_ledger (user_id, seq desc);
create index credit_ledger_expiring_idx
  on public.credit_ledger (expires_at) where entry_type = 'grant' and expires_at is not null;

create table public.job_assets (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  kind text not null check (kind in ('input', 'stem', 'midi')),
  name text,
  storage_key text not null,
  content_type text,
  size_bytes bigint check (size_bytes >= 0),
  meta jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  unique (job_id, storage_key)
);
create index job_assets_user_idx on public.job_assets (user_id);
create index job_assets_expires_idx on public.job_assets (expires_at) where expires_at is not null;

-- ---------------------------------------------------------------------------
-- API keys (§11): sha256 hex of "sp_live_<32 hex chars>", prefix kept for display
-- ---------------------------------------------------------------------------
create table public.api_keys (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  key_hash text not null unique,
  prefix text not null,
  name text,
  last_used_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);
create index api_keys_user_idx on public.api_keys (user_id);

-- ---------------------------------------------------------------------------
-- Billing (§3, §4)
-- ---------------------------------------------------------------------------
create table public.plans (
  id text primary key,
  name text not null,
  credits integer not null check (credits >= 0),
  price_cents integer not null check (price_cents >= 0),
  currency text not null default 'USD',
  interval text check (interval in ('month', 'year')),
  provider_variant_ids jsonb not null default '{}'::jsonb,
  checkout_url_template text,
  active boolean not null default true,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create trigger plans_set_updated_at
  before update on public.plans
  for each row execute function public.set_updated_at();

create table public.purchases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  provider public.purchase_provider not null,
  provider_order_id text not null,
  plan_id text references public.plans (id),
  credits integer not null check (credits >= 0),
  amount_cents integer not null check (amount_cents >= 0),
  net_cents integer not null check (net_cents >= 0),
  currency text not null default 'USD',
  referral_code text,
  raw jsonb not null default '{}'::jsonb,
  idempotency_key text not null unique,
  created_at timestamptz not null default now(),
  unique (provider, provider_order_id)
);
create index purchases_user_idx on public.purchases (user_id, created_at desc);

create table public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  provider public.purchase_provider not null,
  provider_subscription_id text not null unique,
  plan_id text references public.plans (id),
  status text not null check (status in ('trialing', 'active', 'past_due', 'paused', 'cancelled', 'expired')),
  current_period_end timestamptz,
  cancelled_at timestamptz,
  raw jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index subscriptions_user_idx on public.subscriptions (user_id);
create trigger subscriptions_set_updated_at
  before update on public.subscriptions
  for each row execute function public.set_updated_at();

create table public.webhook_events (
  id uuid primary key default gen_random_uuid(),
  provider public.purchase_provider not null,
  event_name text not null,
  idempotency_key text not null unique,
  payload jsonb not null,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  error text
);
create index webhook_events_unprocessed_idx
  on public.webhook_events (received_at) where processed_at is null;

-- ---------------------------------------------------------------------------
-- Affiliates (§12)
-- ---------------------------------------------------------------------------
create table public.affiliates (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references public.profiles (id) on delete cascade,
  code text not null,
  commission_rate numeric(5, 4) not null default 0.30 check (commission_rate >= 0 and commission_rate <= 1),
  payout_details jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create unique index affiliates_code_idx on public.affiliates (lower(code));
create trigger affiliates_set_updated_at
  before update on public.affiliates
  for each row execute function public.set_updated_at();

create table public.referral_codes (
  id uuid primary key default gen_random_uuid(),
  code text not null,
  affiliate_id uuid not null references public.affiliates (id) on delete cascade,
  uses integer not null default 0 check (uses >= 0),
  active boolean not null default true,
  created_at timestamptz not null default now()
);
create unique index referral_codes_code_idx on public.referral_codes (lower(code));
create index referral_codes_affiliate_idx on public.referral_codes (affiliate_id);

-- An affiliate's primary code is also a referral code, so all lookups go through
-- referral_codes and `uses` is counted in one place.
create function public.affiliates_seed_referral_code() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.referral_codes (code, affiliate_id) values (new.code, new.id);
  return new;
end;
$$;
create trigger affiliates_seed_referral_code
  after insert on public.affiliates
  for each row execute function public.affiliates_seed_referral_code();

create table public.affiliate_commissions (
  id uuid primary key default gen_random_uuid(),
  purchase_id uuid not null unique references public.purchases (id) on delete cascade,
  affiliate_id uuid not null references public.affiliates (id) on delete cascade,
  referral_code_id uuid references public.referral_codes (id) on delete set null,
  rate numeric(5, 4) not null,
  amount_cents integer not null check (amount_cents >= 0),
  status public.commission_status not null default 'pending',
  paid_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index affiliate_commissions_affiliate_idx on public.affiliate_commissions (affiliate_id, status);
create trigger affiliate_commissions_set_updated_at
  before update on public.affiliate_commissions
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Signup: profile + credit account + welcome grant (plans.free.credits, contract §3)
-- ---------------------------------------------------------------------------
create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_signup_credits integer;
begin
  insert into public.profiles (id, email) values (new.id, new.email) on conflict (id) do nothing;
  insert into public.credit_accounts (user_id) values (new.id) on conflict (user_id) do nothing;
  select credits into v_signup_credits from public.plans where id = 'free';
  v_signup_credits := coalesce(v_signup_credits, 3);
  if v_signup_credits > 0 then
    perform public.grant_credits(new.id, v_signup_credits, 'signup', 'signup:' || new.id::text, 'Welcome credits');
  end if;
  return new;
end;
$$;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- Seed plans (contract §3). provider_variant_ids / checkout_url_template are
-- operator configuration and are left untouched on re-apply.
-- Template placeholders: {variant_id}, {user_id}, {ref}.
-- ---------------------------------------------------------------------------
insert into public.plans (id, name, credits, price_cents, currency, interval, checkout_url_template, sort_order)
values
  ('free', 'Free', 3, 0, 'USD', null, null, 0),
  ('pack_50', '50 Credits', 50, 900, 'USD', null,
   'https://snapplay.lemonsqueezy.com/checkout/buy/{variant_id}?checkout[custom][user_id]={user_id}&checkout[custom][ref]={ref}', 1),
  ('sub_monthly', 'Pro Monthly', 60, 799, 'USD', 'month',
   'https://snapplay.lemonsqueezy.com/checkout/buy/{variant_id}?checkout[custom][user_id]={user_id}&checkout[custom][ref]={ref}', 2)
on conflict (id) do update set
  name = excluded.name,
  credits = excluded.credits,
  price_cents = excluded.price_cents,
  currency = excluded.currency,
  interval = excluded.interval,
  sort_order = excluded.sort_order;
