-- SnapPlay AI — 0004: sign-up metadata and account deletion (docs/API_CONTRACT.md §1,
-- docs/SECURITY.md "Data-subject rights").
--
-- Sign-up: the website signs up through supabase-js with user metadata, so the
-- handle_new_user trigger now copies the referral code (only when it names an active
-- referral_codes row), the UTM attribution, the marketing consent and the terms
-- acceptance time from auth.users.raw_user_meta_data into profiles. The welcome grant is
-- unchanged. Nothing in the metadata can make the trigger raise: a sign-up must never
-- fail because of what a form sent.
--
-- Deleting an account keeps the accounting records and removes the person: the profile
-- becomes a tombstone (email replaced, deleted_at set), API keys go, jobs lose their
-- content, purchases and subscriptions lose the provider payloads, referral codes are
-- revoked, the remaining credits are written off through the ledger, and the ledger,
-- purchases and commissions stay attached to the tombstone. Because the tombstone must
-- outlive the auth.users row (the API deletes the login afterwards), profiles no longer
-- cascades from auth.users; a trigger runs the same function instead, so a login deleted
-- from the Supabase dashboard ends in exactly the same state.
--
-- Errors (SQLSTATE / MESSAGE): P0404 not_found (no profile), P0409 conflict (a job is
-- still queued or running — the caller retries once it has finished).

alter table public.profiles
  add column deleted_at timestamptz,
  add column referral_code text,
  add column utm_source text,
  add column utm_medium text,
  add column utm_campaign text,
  add column utm_content text,
  add column utm_term text,
  add column marketing_opt_in boolean not null default false,
  add column terms_accepted_at timestamptz;

-- ---------------------------------------------------------------------------
-- Sign-up metadata (contract §1)
-- ---------------------------------------------------------------------------
-- Readers of raw_user_meta_data: trimmed text capped at 100 characters, a boolean that
-- is false unless the value is a JSON boolean or the strings true/false, a timestamp
-- that is null when it does not parse.
create function public.signup_meta_text(p_meta jsonb, p_key text) returns text
language sql immutable as $$
  select left(nullif(btrim(p_meta ->> p_key), ''), 100);
$$;

create function public.signup_meta_bool(p_meta jsonb, p_key text) returns boolean
language sql immutable as $$
  select case
    when jsonb_typeof(p_meta -> p_key) = 'boolean' then (p_meta ->> p_key)::boolean
    when lower(btrim(p_meta ->> p_key)) in ('true', 'false') then lower(btrim(p_meta ->> p_key))::boolean
    else false
  end;
$$;

create function public.signup_meta_timestamp(p_meta jsonb, p_key text) returns timestamptz
language plpgsql immutable as $$
begin
  return nullif(btrim(p_meta ->> p_key), '')::timestamptz;
exception when others then
  return null;
end;
$$;

-- The code as it is spelled in referral_codes, when the sign-up named an active one.
create function public.signup_referral_code(p_meta jsonb) returns text
language sql stable as $$
  select r.code from public.referral_codes r
   where r.active and lower(r.code) = lower(btrim(p_meta ->> 'referral_code'))
   limit 1;
$$;

revoke execute on function
  public.signup_meta_text(jsonb, text),
  public.signup_meta_bool(jsonb, text),
  public.signup_meta_timestamp(jsonb, text),
  public.signup_referral_code(jsonb)
from public;

-- Same profile + credit account + welcome grant as 0001, plus the metadata columns.
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_signup_credits integer;
  v_meta jsonb := coalesce(new.raw_user_meta_data, '{}'::jsonb);
begin
  insert into public.profiles
    (id, email, referral_code, utm_source, utm_medium, utm_campaign, utm_content, utm_term,
     marketing_opt_in, terms_accepted_at)
  values
    (new.id, new.email, public.signup_referral_code(v_meta),
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
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Account deletion (contract §1)
-- ---------------------------------------------------------------------------

-- The tombstone outlives the login: drop the cascade from auth.users, whatever it is named.
do $$
declare
  v_constraint text;
begin
  for v_constraint in
    select con.conname
      from pg_constraint con
      join pg_class rel on rel.oid = con.conrelid
      join pg_namespace nsp on nsp.oid = rel.relnamespace
      join pg_class frel on frel.oid = con.confrelid
      join pg_namespace fnsp on fnsp.oid = frel.relnamespace
     where con.contype = 'f'
       and nsp.nspname = 'public' and rel.relname = 'profiles'
       and fnsp.nspname = 'auth' and frel.relname = 'users'
  loop
    execute format('alter table public.profiles drop constraint %I', v_constraint);
  end loop;
end;
$$;

create table public.account_deletions (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  requested_at timestamptz not null default now(),
  ledger_rows_kept integer not null check (ledger_rows_kept >= 0)
);
alter table public.account_deletions enable row level security;
grant all on public.account_deletions to service_role;
-- No policy and no grant for anon/authenticated: service_role only, like webhook_events.

-- Idempotent: a tombstoned profile answers with its account_deletions row and changes
-- nothing. Locks the profile and the credit account, so it serialises with create_job
-- and every credit mutation of the same user.
create function public.delete_user_account(p_user_id uuid)
returns public.account_deletions
language plpgsql security definer set search_path = public as $$
declare
  v_profile public.profiles;
  v_account public.credit_accounts;
  v_deletion public.account_deletions;
  v_active integer;
  v_available integer;
  v_ledger_rows integer;
begin
  select * into v_profile from public.profiles where id = p_user_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('profile %s', p_user_id);
  end if;
  if v_profile.deleted_at is not null then
    select * into v_deletion from public.account_deletions where user_id = p_user_id;
    return v_deletion;
  end if;

  select * into v_account from public.credit_accounts where user_id = p_user_id for update;

  select count(*) into v_active from public.jobs
   where user_id = p_user_id and status in ('queued', 'running');
  if v_active > 0 then
    raise exception 'conflict' using errcode = 'P0409',
      detail = format('%s unfinished jobs for user %s', v_active, p_user_id);
  end if;

  -- Write the unused credits off through the ledger so the account closes at zero and
  -- the balance invariant (README "Invariants") keeps holding for the tombstone.
  v_available := coalesce(v_account.balance - v_account.reserved, 0);
  if v_available > 0 then
    perform public.adjust_credits(p_user_id, -v_available, 'account_deletion',
                                  'deletion:' || p_user_id::text,
                                  'Account deleted; remaining credits forfeited');
  end if;

  delete from public.api_keys where user_id = p_user_id;
  delete from public.job_assets where user_id = p_user_id;
  -- Jobs stay as the rows the ledger's reserve/capture/release entries point at, with
  -- lifecycle and error only: no options, input metadata, result or client key.
  update public.jobs
     set options = '{}'::jsonb, input_meta = '{}'::jsonb, result = null,
         worker_ref = null, idempotency_key = null
   where user_id = p_user_id;
  -- Purchases and subscriptions are accounting records; the provider payloads are not.
  update public.purchases set raw = '{}'::jsonb where user_id = p_user_id;
  update public.subscriptions set raw = '{}'::jsonb where user_id = p_user_id;
  -- Commissions stay (they are owed or were paid); the codes stop working and the
  -- payout details go.
  update public.referral_codes r set active = false
    from public.affiliates a
   where a.id = r.affiliate_id and a.user_id = p_user_id;
  update public.affiliates set active = false, payout_details = '{}'::jsonb
   where user_id = p_user_id;

  -- The referral code and the terms acceptance stay (attribution and legal record);
  -- the attribution details and the marketing consent go.
  update public.profiles
     set email = 'deleted+' || p_user_id::text || '@invalid',
         display_name = null,
         utm_source = null, utm_medium = null, utm_campaign = null, utm_content = null,
         utm_term = null,
         marketing_opt_in = false,
         deleted_at = now()
   where id = p_user_id;

  select count(*) into v_ledger_rows from public.credit_ledger where user_id = p_user_id;
  insert into public.account_deletions (user_id, ledger_rows_kept)
  values (p_user_id, v_ledger_rows)
  returning * into v_deletion;
  return v_deletion;
end;
$$;

revoke execute on function public.delete_user_account(uuid) from public;
grant execute on function public.delete_user_account(uuid) to service_role;

-- A login deleted at the identity provider (Supabase dashboard, GoTrue admin API) leaves
-- the same tombstone; after the API's own deletion the profile is already tombstoned and
-- nothing happens here. A user with an unfinished job cannot be deleted this way either.
create function public.handle_deleted_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.profiles where id = old.id and deleted_at is null) then
    perform public.delete_user_account(old.id);
  end if;
  return old;
end;
$$;
grant execute on function public.handle_deleted_user() to public;
create trigger on_auth_user_deleted
  after delete on auth.users
  for each row execute function public.handle_deleted_user();
