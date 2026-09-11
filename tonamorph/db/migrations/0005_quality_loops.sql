-- Tonamorph — 0005: quality loops (docs/API_CONTRACT.md §2 feedback, §14; GTM plan §2.6,
-- Appendix C §3–6).
--
-- Result feedback with the bounded automatic refund, NPS answers, plugin installs (the
-- Plugin Installed event), the per-user facts and last-24 h numbers the API reads, the
-- growth_daily reporting view, and profiles.first_seen_at, stamped once when the API first
-- meets an account (the Signed Up event fires exactly once off that stamp).
--
-- Account deletion (0004) is extended so the free text a person wrote — feedback notes,
-- NPS comments — and their plugin installs leave with them; ratings and scores stay as
-- the books do.
--
-- Errors (SQLSTATE / MESSAGE): P0404 not_found, P0409 conflict, 22023 invalid_argument.

alter table public.profiles add column first_seen_at timestamptz;

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------
create table public.job_feedback (
  job_id uuid primary key references public.jobs (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  rating text not null check (rating in ('up', 'down')),
  reason text check (reason in ('bleed', 'wrong_key', 'midi_off', 'clicks', 'slow', 'other')),
  note text check (note is null or char_length(note) <= 140),
  drop_to_ready_ms integer check (drop_to_ready_ms is null or drop_to_ready_ms >= 0),
  refunded boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index job_feedback_user_idx on public.job_feedback (user_id, created_at desc);
create trigger job_feedback_set_updated_at
  before update on public.job_feedback
  for each row execute function public.set_updated_at();

create table public.nps_responses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  score integer not null check (score between 0 and 10),
  comment text check (comment is null or char_length(comment) <= 500),
  created_at timestamptz not null default now()
);
create index nps_responses_user_idx on public.nps_responses (user_id, created_at desc);

-- One row per (user, plugin version, host); the insert is the Plugin Installed event.
create table public.plugin_installs (
  user_id uuid not null references public.profiles (id) on delete cascade,
  plugin_version text not null check (char_length(plugin_version) between 1 and 32),
  host text not null check (char_length(host) between 1 and 64),
  os text check (os is null or char_length(os) <= 64),
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  primary key (user_id, plugin_version, host)
);

-- ---------------------------------------------------------------------------
-- Feedback and the automatic refund (contract §2; GTM §2.6)
-- ---------------------------------------------------------------------------
-- The refund rule, decided under the job row and the account lock so the bounds cannot be
-- raced: the job must be the caller's and `succeeded`, finished within 24 hours, and the
-- reason must not be `slow`. Bounds: automatic refunds (ledger `refund` rows whose reason
-- starts with `user:unusable:`) at most max(3, 20 % of the captures of the last 30 days)
-- per 30 days, and at most 2 ever for an account that never purchased. Returns whether
-- the job's credit is back — true again for a job already refunded, so a re-rating reports
-- the standing state; false when ineligible or over a bound (support reviews those).
create function public.refund_job_for_feedback(p_job_id uuid, p_user_id uuid, p_reason text)
returns boolean
language plpgsql security definer set search_path = public as $$
declare
  v_job public.jobs;
  v_auto_30d integer;
  v_captured_30d integer;
  v_auto_all integer;
begin
  select * into v_job from public.jobs where id = p_job_id and user_id = p_user_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('job %s', p_job_id);
  end if;
  perform public.lock_credit_account(p_user_id);

  if exists (select 1 from public.credit_ledger where job_id = p_job_id and entry_type = 'refund') then
    return true;
  end if;
  if v_job.status <> 'succeeded'
     or v_job.finished_at is null
     or v_job.finished_at < now() - interval '24 hours'
     or p_reason = 'slow' then
    return false;
  end if;

  select count(*) into v_auto_30d from public.credit_ledger
   where user_id = p_user_id and entry_type = 'refund' and note like 'user:unusable:%'
     and created_at >= now() - interval '30 days';
  select count(*) into v_captured_30d from public.credit_ledger
   where user_id = p_user_id and entry_type = 'capture'
     and created_at >= now() - interval '30 days';
  -- integer division: 20 % of the captures, rounded down
  if v_auto_30d >= greatest(3, v_captured_30d / 5) then
    return false;
  end if;
  if not exists (select 1 from public.purchases where user_id = p_user_id) then
    select count(*) into v_auto_all from public.credit_ledger
     where user_id = p_user_id and entry_type = 'refund' and note like 'user:unusable:%';
    if v_auto_all >= 2 then
      return false;
    end if;
  end if;

  perform public.refund_job(p_job_id, 'user:unusable:' || coalesce(p_reason, 'unspecified'));
  return true;
end;
$$;

-- One feedback row per job, refreshed on every call (a later drop_to_ready_ms of null keeps
-- the measured one). A thumbs-down runs refund_job_for_feedback in the same transaction and
-- records its answer in `refunded`, which stays true once a refund was made.
create function public.record_job_feedback(
  p_job_id uuid,
  p_user_id uuid,
  p_rating text,
  p_reason text,
  p_note text,
  p_drop_to_ready_ms integer
) returns public.job_feedback
language plpgsql security definer set search_path = public as $$
declare
  v_job public.jobs;
  v_row public.job_feedback;
begin
  if p_rating is null or p_rating not in ('up', 'down') then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_rating must be up or down';
  end if;
  if p_reason is not null and p_reason not in ('bleed', 'wrong_key', 'midi_off', 'clicks', 'slow', 'other') then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_reason is not a feedback reason';
  end if;
  if p_note is not null and char_length(p_note) > 140 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_note must be at most 140 characters';
  end if;
  if p_drop_to_ready_ms is not null and p_drop_to_ready_ms < 0 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_drop_to_ready_ms must not be negative';
  end if;

  select * into v_job from public.jobs where id = p_job_id and user_id = p_user_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('job %s', p_job_id);
  end if;
  if v_job.status in ('queued', 'running') then
    raise exception 'conflict' using errcode = 'P0409', detail = format('job is %s', v_job.status);
  end if;

  insert into public.job_feedback (job_id, user_id, rating, reason, note, drop_to_ready_ms)
  values (p_job_id, p_user_id, p_rating, p_reason, p_note, p_drop_to_ready_ms)
  on conflict (job_id) do update
    set rating = excluded.rating,
        reason = excluded.reason,
        note = excluded.note,
        drop_to_ready_ms = coalesce(excluded.drop_to_ready_ms, job_feedback.drop_to_ready_ms)
  returning * into v_row;

  -- Its own IF: SQL does not promise short-circuit evaluation, and this call refunds.
  if p_rating = 'down' and not v_row.refunded then
    if public.refund_job_for_feedback(p_job_id, p_user_id, p_reason) then
      update public.job_feedback set refunded = true where job_id = p_job_id returning * into v_row;
    end if;
  end if;
  return v_row;
end;
$$;

-- ---------------------------------------------------------------------------
-- NPS (contract §14): one answer per user per 30 days
-- ---------------------------------------------------------------------------
create function public.submit_nps(p_user_id uuid, p_score integer, p_comment text)
returns public.nps_responses
language plpgsql security definer set search_path = public as $$
declare
  v_row public.nps_responses;
begin
  if p_score is null or p_score < 0 or p_score > 10 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_score must be between 0 and 10';
  end if;
  if p_comment is not null and char_length(p_comment) > 500 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_comment must be at most 500 characters';
  end if;
  -- The profile lock serialises two answers sent at once.
  perform 1 from public.profiles where id = p_user_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('profile %s', p_user_id);
  end if;
  if exists (select 1 from public.nps_responses
              where user_id = p_user_id and created_at >= now() - interval '30 days') then
    raise exception 'conflict' using errcode = 'P0409', detail = 'nps answered within 30 days';
  end if;
  insert into public.nps_responses (user_id, score, comment)
  values (p_user_id, p_score, p_comment)
  returning * into v_row;
  return v_row;
end;
$$;

-- ---------------------------------------------------------------------------
-- Plugin installs (contract §1 headers, §14 Plugin Installed)
-- ---------------------------------------------------------------------------
-- True when this is the first time the user is seen with this (version, host) pair; every
-- later call only stamps last_seen_at (and fills os when it was unknown).
create function public.touch_plugin_install(p_user_id uuid, p_plugin_version text, p_host text, p_os text)
returns boolean
language plpgsql security definer set search_path = public as $$
begin
  if p_plugin_version is null or char_length(p_plugin_version) not between 1 and 32 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_plugin_version is required';
  end if;
  if p_host is null or char_length(p_host) not between 1 and 64 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_host is required';
  end if;
  if p_os is not null and char_length(p_os) > 64 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_os is too long';
  end if;
  if not exists (select 1 from public.profiles where id = p_user_id) then
    raise exception 'not_found' using errcode = 'P0404', detail = format('profile %s', p_user_id);
  end if;

  insert into public.plugin_installs (user_id, plugin_version, host, os)
  values (p_user_id, p_plugin_version, p_host, p_os)
  on conflict (user_id, plugin_version, host) do nothing;
  if found then
    return true;
  end if;
  update public.plugin_installs
     set last_seen_at = now(), os = coalesce(p_os, os)
   where user_id = p_user_id and plugin_version = p_plugin_version and host = p_host;
  return false;
end;
$$;

-- ---------------------------------------------------------------------------
-- Facts and numbers the API reads (contract §14)
-- ---------------------------------------------------------------------------
-- What a growth event says about its profile. No row for an unknown profile.
create function public.user_facts(p_user_id uuid)
returns table (
  email text,
  plan text,
  morphs_total integer,
  first_morph_at timestamptz,
  last_morph_at timestamptz,
  has_purchased boolean
)
language sql stable security definer set search_path = public as $$
  select p.email,
         p.plan,
         (select count(*) from public.jobs j where j.user_id = p.id and j.status = 'succeeded')::integer,
         (select min(j.finished_at) from public.jobs j where j.user_id = p.id and j.status = 'succeeded'),
         (select max(j.finished_at) from public.jobs j where j.user_id = p.id and j.status = 'succeeded'),
         exists (select 1 from public.purchases pu where pu.user_id = p.id)
    from public.profiles p
   where p.id = p_user_id;
$$;

-- Jobs that finished in the last 24 hours (cancellations excluded) and the latency
-- percentiles of the successful ones, measured from pickup (or submission) to the end.
create function public.status_last_24h()
returns table (morphs integer, succeeded integer, failed integer, p50_ms integer, p95_ms integer)
language sql stable security definer set search_path = public as $$
  with finished as (
    select status,
           extract(epoch from (finished_at - coalesce(started_at, created_at))) * 1000 as latency_ms
      from public.jobs
     where finished_at >= now() - interval '24 hours'
       and status in ('succeeded', 'failed')
  )
  select count(*)::integer,
         (count(*) filter (where status = 'succeeded'))::integer,
         (count(*) filter (where status = 'failed'))::integer,
         round(percentile_cont(0.5) within group (order by latency_ms) filter (where status = 'succeeded'))::integer,
         round(percentile_cont(0.95) within group (order by latency_ms) filter (where status = 'succeeded'))::integer
    from finished;
$$;

-- One row per UTC day with something to report: sign-ups (profiles created), morphs
-- started (jobs created), succeeded and failed (by the day they finished), the latency
-- percentiles of the day's successes, captures that left a balance at zero (the tracked
-- Credits Exhausted moment; refused reservations leave no row), purchases and revenue.
create view public.growth_daily as
with
  signups as (
    select (created_at at time zone 'UTC')::date as day, count(*) as signups
      from public.profiles group by 1),
  started as (
    select (created_at at time zone 'UTC')::date as day, count(*) as morphs_started
      from public.jobs group by 1),
  finished as (
    select (finished_at at time zone 'UTC')::date as day,
           count(*) filter (where status = 'succeeded') as morphs_succeeded,
           count(*) filter (where status = 'failed') as morphs_failed,
           percentile_cont(0.5) within group
             (order by extract(epoch from (finished_at - coalesce(started_at, created_at))) * 1000)
             filter (where status = 'succeeded') as p50_ms,
           percentile_cont(0.95) within group
             (order by extract(epoch from (finished_at - coalesce(started_at, created_at))) * 1000)
             filter (where status = 'succeeded') as p95_ms
      from public.jobs where finished_at is not null group by 1),
  exhausted as (
    select (created_at at time zone 'UTC')::date as day, count(*) as credits_exhausted
      from public.credit_ledger where entry_type = 'capture' and balance_after = 0 group by 1),
  bought as (
    select (created_at at time zone 'UTC')::date as day,
           count(*) as purchases, sum(amount_cents) as revenue_cents
      from public.purchases group by 1),
  days as (
    select day from signups union select day from started union select day from finished
    union select day from exhausted union select day from bought)
select d.day,
       coalesce(s.signups, 0)::integer as signups,
       coalesce(st.morphs_started, 0)::integer as morphs_started,
       coalesce(f.morphs_succeeded, 0)::integer as morphs_succeeded,
       coalesce(f.morphs_failed, 0)::integer as morphs_failed,
       round(f.p50_ms)::integer as p50_ms,
       round(f.p95_ms)::integer as p95_ms,
       coalesce(e.credits_exhausted, 0)::integer as credits_exhausted,
       coalesce(b.purchases, 0)::integer as purchases,
       coalesce(b.revenue_cents, 0)::bigint as revenue_cents
  from days d
  left join signups s on s.day = d.day
  left join started st on st.day = d.day
  left join finished f on f.day = d.day
  left join exhausted e on e.day = d.day
  left join bought b on b.day = d.day
 order by d.day;

-- ---------------------------------------------------------------------------
-- Account deletion (0004) also removes the free text and the installs
-- ---------------------------------------------------------------------------
create or replace function public.delete_user_account(p_user_id uuid)
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

  v_available := coalesce(v_account.balance - v_account.reserved, 0);
  if v_available > 0 then
    perform public.adjust_credits(p_user_id, -v_available, 'account_deletion',
                                  'deletion:' || p_user_id::text,
                                  'Account deleted; remaining credits forfeited');
  end if;

  delete from public.api_keys where user_id = p_user_id;
  delete from public.job_assets where user_id = p_user_id;
  update public.jobs
     set options = '{}'::jsonb, input_meta = '{}'::jsonb, result = null,
         worker_ref = null, idempotency_key = null
   where user_id = p_user_id;
  update public.purchases set raw = '{}'::jsonb where user_id = p_user_id;
  update public.subscriptions set raw = '{}'::jsonb where user_id = p_user_id;
  update public.referral_codes r set active = false
    from public.affiliates a
   where a.id = r.affiliate_id and a.user_id = p_user_id;
  update public.affiliates set active = false, payout_details = '{}'::jsonb
   where user_id = p_user_id;
  -- The ratings and scores are the books; the words and the devices are the person.
  update public.job_feedback set note = null where user_id = p_user_id;
  update public.nps_responses set comment = null where user_id = p_user_id;
  delete from public.plugin_installs where user_id = p_user_id;

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

-- ---------------------------------------------------------------------------
-- Privileges and row-level security (same model as 0003)
-- ---------------------------------------------------------------------------
grant all on public.job_feedback, public.nps_responses, public.plugin_installs to service_role;
grant select on public.growth_daily to service_role;
grant select on public.job_feedback, public.nps_responses to authenticated;

alter table public.job_feedback enable row level security;
alter table public.nps_responses enable row level security;
alter table public.plugin_installs enable row level security;

create policy job_feedback_select_own on public.job_feedback
  for select to authenticated using (user_id = (select auth.uid()));
create policy nps_responses_select_own on public.nps_responses
  for select to authenticated using (user_id = (select auth.uid()));
-- plugin_installs: service_role only (no policies, no grants for API roles).

revoke execute on function
  public.refund_job_for_feedback(uuid, uuid, text),
  public.record_job_feedback(uuid, uuid, text, text, text, integer),
  public.submit_nps(uuid, integer, text),
  public.touch_plugin_install(uuid, text, text, text),
  public.user_facts(uuid),
  public.status_last_24h()
from public;
grant execute on function
  public.refund_job_for_feedback(uuid, uuid, text),
  public.record_job_feedback(uuid, uuid, text, text, text, integer),
  public.submit_nps(uuid, integer, text),
  public.touch_plugin_install(uuid, text, text, text),
  public.user_facts(uuid),
  public.status_last_24h()
to service_role;
