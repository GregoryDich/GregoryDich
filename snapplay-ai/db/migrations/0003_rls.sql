-- SnapPlay AI — 0003: roles, privileges and row-level security.
--
-- Model: authenticated users may only SELECT their own rows (plans are public); every
-- write goes through the SECURITY DEFINER functions in 0002, which only service_role may
-- execute. get_balance is the one function authenticated users may call, and it enforces
-- p_user_id = auth.uid() itself. Supabase already provides anon/authenticated/service_role;
-- the DO block only creates them for a plain PostgreSQL cluster (local tests).

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  end if;
end;
$$;

grant usage on schema public to anon, authenticated, service_role;

-- ---------------------------------------------------------------------------
-- Table privileges
-- ---------------------------------------------------------------------------
revoke all on all tables in schema public from public, anon, authenticated;
grant all on all tables in schema public to service_role;

grant select on
  public.profiles,
  public.credit_accounts,
  public.credit_ledger,
  public.jobs,
  public.job_assets,
  public.api_keys,
  public.purchases,
  public.subscriptions,
  public.affiliates,
  public.referral_codes,
  public.affiliate_commissions
to authenticated;
grant select on public.plans to anon, authenticated;

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.credit_accounts enable row level security;
alter table public.credit_ledger enable row level security;
alter table public.jobs enable row level security;
alter table public.job_assets enable row level security;
alter table public.api_keys enable row level security;
alter table public.plans enable row level security;
alter table public.purchases enable row level security;
alter table public.subscriptions enable row level security;
alter table public.webhook_events enable row level security;
alter table public.affiliates enable row level security;
alter table public.referral_codes enable row level security;
alter table public.affiliate_commissions enable row level security;

create policy profiles_select_own on public.profiles
  for select to authenticated using (id = (select auth.uid()));

create policy credit_accounts_select_own on public.credit_accounts
  for select to authenticated using (user_id = (select auth.uid()));

create policy credit_ledger_select_own on public.credit_ledger
  for select to authenticated using (user_id = (select auth.uid()));

create policy jobs_select_own on public.jobs
  for select to authenticated using (user_id = (select auth.uid()));

create policy job_assets_select_own on public.job_assets
  for select to authenticated using (user_id = (select auth.uid()));

create policy api_keys_select_own on public.api_keys
  for select to authenticated using (user_id = (select auth.uid()));

create policy plans_select_active on public.plans
  for select to anon, authenticated using (active);

create policy purchases_select_own on public.purchases
  for select to authenticated using (user_id = (select auth.uid()));

create policy subscriptions_select_own on public.subscriptions
  for select to authenticated using (user_id = (select auth.uid()));

-- webhook_events: service_role only (no policies, no grants for API roles).

create policy affiliates_select_own on public.affiliates
  for select to authenticated using (user_id = (select auth.uid()));

create policy referral_codes_select_own on public.referral_codes
  for select to authenticated using (
    exists (select 1 from public.affiliates a
             where a.id = referral_codes.affiliate_id and a.user_id = (select auth.uid()))
  );

create policy affiliate_commissions_select_own on public.affiliate_commissions
  for select to authenticated using (
    exists (select 1 from public.affiliates a
             where a.id = affiliate_commissions.affiliate_id and a.user_id = (select auth.uid()))
  );

-- ---------------------------------------------------------------------------
-- Function privileges
-- ---------------------------------------------------------------------------
revoke execute on all functions in schema public from public, anon, authenticated, service_role;

-- Trigger functions keep the default so the auth service can fire on_auth_user_created;
-- they return `trigger` and cannot be invoked through PostgREST.
grant execute on function public.set_updated_at() to public;
grant execute on function public.handle_new_user() to public;
grant execute on function public.affiliates_seed_referral_code() to public;

grant execute on function public.get_balance(uuid) to authenticated, service_role;

grant execute on function
  public.reserve_credits(uuid, uuid, integer),
  public.settle_reservation(uuid, boolean),
  public.grant_credits(uuid, integer, text, text, text, timestamptz),
  public.adjust_credits(uuid, integer, text, text, text),
  public.refund_job(uuid, text),
  public.expire_credits(),
  public.create_job(uuid, jsonb, jsonb, text),
  public.start_job(uuid, text),
  public.update_job_progress(uuid, public.job_stage, real),
  public.complete_job(uuid, jsonb),
  public.fail_job(uuid, jsonb),
  public.cancel_job(uuid, uuid),
  public.reap_stale_jobs(integer),
  public.record_purchase(uuid, public.purchase_provider, text, text, integer, integer, text, jsonb, text),
  public.claim_webhook_event(text, public.purchase_provider, text, jsonb, integer),
  public.create_api_key(uuid, text),
  public.authenticate_api_key(text),
  public.revoke_api_key(uuid, uuid)
to service_role;
