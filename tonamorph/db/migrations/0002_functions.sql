-- Tonamorph — 0002: credit ledger, job lifecycle, purchases and API-key functions.
-- Reference: docs/API_CONTRACT.md §6 (credits), §10 (worker), §11 (API keys), §12 (affiliates).
--
-- Every mutating function is SECURITY DEFINER with a pinned search_path, locks the
-- affected credit_accounts row FOR UPDATE before reading or writing the ledger, and is
-- idempotent so webhook replays and worker retries are safe.
--
-- Error contract (SQLSTATE / MESSAGE):
--   P0402 insufficient_credits   P0404 not_found   P0409 conflict
--   22023 invalid_argument       42501 forbidden

create type public.credit_balance as (credits integer, reserved integer, available integer);

-- ---------------------------------------------------------------------------
-- Internal helpers (not executable by API roles, see 0003_rls.sql)
-- ---------------------------------------------------------------------------
create function public.balance_of(p_account public.credit_accounts) returns public.credit_balance
language sql immutable as $$
  select row(p_account.balance, p_account.reserved, p_account.balance - p_account.reserved)::public.credit_balance;
$$;

create function public.lock_credit_account(p_user_id uuid) returns public.credit_accounts
language plpgsql as $$
declare
  v_account public.credit_accounts;
begin
  select * into v_account from public.credit_accounts where user_id = p_user_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('credit account for user %s', p_user_id);
  end if;
  return v_account;
end;
$$;

-- Appends one ledger row snapshotting the (already updated) account row.
create function public.append_ledger(
  p_account public.credit_accounts,
  p_entry_type public.ledger_entry_type,
  p_amount integer,
  p_job_id uuid,
  p_source text,
  p_idempotency_key text,
  p_note text,
  p_expires_at timestamptz
) returns public.credit_ledger
language plpgsql as $$
declare
  v_row public.credit_ledger;
begin
  insert into public.credit_ledger
    (user_id, entry_type, amount, balance_after, reserved_after, job_id, source, idempotency_key, note, expires_at)
  values
    (p_account.user_id, p_entry_type, p_amount, p_account.balance, p_account.reserved,
     p_job_id, p_source, p_idempotency_key, p_note, p_expires_at)
  returning * into v_row;
  return v_row;
end;
$$;

-- ---------------------------------------------------------------------------
-- Credits (contract §6)
-- ---------------------------------------------------------------------------
create function public.reserve_credits(p_user_id uuid, p_job_id uuid, p_amount integer)
returns public.credit_balance
language plpgsql security definer set search_path = public as $$
declare
  v_account public.credit_accounts;
begin
  if p_amount is null or p_amount <= 0 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_amount must be positive';
  end if;
  if p_job_id is null then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_job_id is required';
  end if;

  v_account := public.lock_credit_account(p_user_id);

  if exists (select 1 from public.credit_ledger where job_id = p_job_id and entry_type = 'reserve') then
    return public.balance_of(v_account);
  end if;

  if v_account.balance - v_account.reserved < p_amount then
    raise exception 'insufficient_credits' using errcode = 'P0402',
      detail = format('available=%s requested=%s', v_account.balance - v_account.reserved, p_amount);
  end if;

  update public.credit_accounts set reserved = reserved + p_amount
   where user_id = p_user_id returning * into v_account;
  perform public.append_ledger(v_account, 'reserve', -p_amount, p_job_id,
                               'job:' || p_job_id::text, 'reserve:' || p_job_id::text, null, null);
  return public.balance_of(v_account);
end;
$$;

create function public.settle_reservation(p_job_id uuid, p_success boolean)
returns public.credit_balance
language plpgsql security definer set search_path = public as $$
declare
  v_reserve public.credit_ledger;
  v_account public.credit_accounts;
  v_amount integer;
begin
  select * into v_reserve from public.credit_ledger where job_id = p_job_id and entry_type = 'reserve';
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('reservation for job %s', p_job_id);
  end if;

  v_account := public.lock_credit_account(v_reserve.user_id);

  if exists (select 1 from public.credit_ledger
              where job_id = p_job_id and entry_type in ('capture', 'release')) then
    return public.balance_of(v_account);
  end if;

  v_amount := -v_reserve.amount;
  if p_success then
    update public.credit_accounts
       set balance = balance - v_amount, reserved = reserved - v_amount
     where user_id = v_account.user_id returning * into v_account;
    perform public.append_ledger(v_account, 'capture', -v_amount, p_job_id,
                                 v_reserve.source, 'capture:' || p_job_id::text, null, null);
  else
    update public.credit_accounts
       set reserved = reserved - v_amount
     where user_id = v_account.user_id returning * into v_account;
    perform public.append_ledger(v_account, 'release', v_amount, p_job_id,
                                 v_reserve.source, 'release:' || p_job_id::text, null, null);
  end if;
  return public.balance_of(v_account);
end;
$$;

create function public.grant_credits(
  p_user_id uuid,
  p_amount integer,
  p_source text,
  p_idempotency_key text,
  p_note text default null,
  p_expires_at timestamptz default null
) returns public.credit_balance
language plpgsql security definer set search_path = public as $$
declare
  v_account public.credit_accounts;
begin
  if p_amount is null or p_amount <= 0 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_amount must be positive';
  end if;
  if p_idempotency_key is null then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_idempotency_key is required';
  end if;

  v_account := public.lock_credit_account(p_user_id);

  if exists (select 1 from public.credit_ledger where idempotency_key = p_idempotency_key) then
    return public.balance_of(v_account);
  end if;

  update public.credit_accounts set balance = balance + p_amount
   where user_id = p_user_id returning * into v_account;
  perform public.append_ledger(v_account, 'grant', p_amount, null, p_source, p_idempotency_key, p_note, p_expires_at);
  return public.balance_of(v_account);
end;
$$;

-- Manual correction by support tooling. Negative amounts may not exceed the available balance.
create function public.adjust_credits(
  p_user_id uuid,
  p_amount integer,
  p_source text,
  p_idempotency_key text,
  p_note text default null
) returns public.credit_balance
language plpgsql security definer set search_path = public as $$
declare
  v_account public.credit_accounts;
begin
  if p_amount is null or p_amount = 0 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_amount must be non-zero';
  end if;
  if p_idempotency_key is null then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_idempotency_key is required';
  end if;

  v_account := public.lock_credit_account(p_user_id);

  if exists (select 1 from public.credit_ledger where idempotency_key = p_idempotency_key) then
    return public.balance_of(v_account);
  end if;
  if p_amount < 0 and v_account.balance - v_account.reserved < -p_amount then
    raise exception 'insufficient_credits' using errcode = 'P0402',
      detail = format('available=%s requested=%s', v_account.balance - v_account.reserved, -p_amount);
  end if;

  update public.credit_accounts set balance = balance + p_amount
   where user_id = p_user_id returning * into v_account;
  perform public.append_ledger(v_account, 'adjust', p_amount, null, p_source, p_idempotency_key, p_note, null);
  return public.balance_of(v_account);
end;
$$;

create function public.refund_job(p_job_id uuid, p_reason text)
returns public.credit_balance
language plpgsql security definer set search_path = public as $$
declare
  v_capture public.credit_ledger;
  v_account public.credit_accounts;
  v_amount integer;
begin
  select * into v_capture from public.credit_ledger where job_id = p_job_id and entry_type = 'capture';
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('capture for job %s', p_job_id);
  end if;

  v_account := public.lock_credit_account(v_capture.user_id);

  if exists (select 1 from public.credit_ledger where job_id = p_job_id and entry_type = 'refund') then
    return public.balance_of(v_account);
  end if;

  v_amount := -v_capture.amount;
  update public.credit_accounts set balance = balance + v_amount
   where user_id = v_account.user_id returning * into v_account;
  perform public.append_ledger(v_account, 'refund', v_amount, p_job_id,
                               v_capture.source, 'refund:' || p_job_id::text, p_reason, null);
  return public.balance_of(v_account);
end;
$$;

-- Read-only. Executable by authenticated users, but a JWT subject may only read itself.
create function public.get_balance(p_user_id uuid)
returns public.credit_balance
language plpgsql stable security definer set search_path = public as $$
declare
  v_caller uuid;
  v_role text;
  v_account public.credit_accounts;
begin
  v_caller := auth.uid();
  v_role := current_setting('role', true);
  -- `is distinct from`, not `<>`: a token without a subject leaves auth.uid() null, and a
  -- null must not read as "no caller" and pass the check. PostgREST switches to the API
  -- role for the request, so service_role (the backend) and the owner (cron, migrations)
  -- keep reading any account.
  if v_role in ('authenticated', 'anon') and v_caller is distinct from p_user_id then
    raise exception 'forbidden' using errcode = '42501', detail = 'get_balance is limited to the caller''s own account';
  end if;
  select * into v_account from public.credit_accounts where user_id = p_user_id;
  if not found then
    return row(0, 0, 0)::public.credit_balance;
  end if;
  return public.balance_of(v_account);
end;
$$;

-- The perishable pool: expiring credits are spent before non-expiring ones (§13), so every
-- capture comes out of the pool first and only the overflow touches permanent credits.
-- Replaying the user's ledger in order is what keeps a spend attributed to the grant it
-- actually consumed; a plain "everything captured after this grant" sum charges the same
-- spend to every earlier grant as well, and leaves credits that were never granted behind
-- month after month.
create function public.perishable_pool(p_user_id uuid) returns integer
language plpgsql stable as $$
declare
  v_row public.credit_ledger;
  v_pool integer := 0;
begin
  for v_row in
    select * from public.credit_ledger where user_id = p_user_id order by seq
  loop
    if v_row.entry_type = 'grant' and v_row.expires_at is not null then
      v_pool := v_pool + v_row.amount;
    elsif v_row.entry_type = 'expire'
       or (v_row.amount < 0 and v_row.entry_type in ('capture', 'adjust')) then
      v_pool := greatest(v_pool + v_row.amount, 0);
    end if;
  end loop;
  return v_pool;
end;
$$;

-- Cron helper. Grants are expired in `expires_at` order, so the grant being processed is
-- the head of the perishable pool: everything spent so far came off it, and what is left
-- for it is the pool minus the perishable grants queued behind it. Capped at the grant's
-- own amount and at the available balance, so reserved credits are never expired. One
-- `expire` row per grant, keyed by 'expire:<grant ledger id>', so a grant is processed
-- exactly once.
create function public.expire_credits()
returns integer
language plpgsql security definer set search_path = public as $$
declare
  v_grant public.credit_ledger;
  v_account public.credit_accounts;
  v_pool integer;
  v_behind integer;
  v_remaining integer;
  v_count integer := 0;
begin
  for v_grant in
    select g.* from public.credit_ledger g
     where g.entry_type = 'grant' and g.expires_at is not null and g.expires_at <= now()
       and not exists (select 1 from public.credit_ledger e where e.idempotency_key = 'expire:' || g.id::text)
     order by g.user_id, g.expires_at, g.seq
  loop
    v_account := public.lock_credit_account(v_grant.user_id);
    continue when exists (select 1 from public.credit_ledger e where e.idempotency_key = 'expire:' || v_grant.id::text);

    v_pool := public.perishable_pool(v_grant.user_id);
    select coalesce(sum(g.amount), 0) into v_behind
      from public.credit_ledger g
     where g.user_id = v_grant.user_id and g.entry_type = 'grant' and g.expires_at is not null
       and (g.expires_at, g.seq) > (v_grant.expires_at, v_grant.seq)
       and not exists (select 1 from public.credit_ledger e where e.idempotency_key = 'expire:' || g.id::text);

    v_remaining := least(least(greatest(v_pool - v_behind, 0), v_grant.amount),
                         v_account.balance - v_account.reserved);

    update public.credit_accounts set balance = balance - v_remaining
     where user_id = v_grant.user_id returning * into v_account;
    perform public.append_ledger(v_account, 'expire', -v_remaining, null, v_grant.source,
                                 'expire:' || v_grant.id::text,
                                 format('%s of %s credits expired', v_remaining, v_grant.amount), null);
    v_count := v_count + 1;
  end loop;
  return v_count;
end;
$$;

-- ---------------------------------------------------------------------------
-- Jobs (contract §2, §10)
-- ---------------------------------------------------------------------------
-- Reserves one credit and inserts the job atomically. The account lock serializes
-- calls per user, so an idempotency-key replay always returns the existing job.
create function public.create_job(p_user_id uuid, p_options jsonb, p_input_meta jsonb, p_idempotency_key text)
returns public.jobs
language plpgsql security definer set search_path = public as $$
declare
  v_job public.jobs;
begin
  perform public.lock_credit_account(p_user_id);

  if p_idempotency_key is not null then
    select * into v_job from public.jobs where user_id = p_user_id and idempotency_key = p_idempotency_key;
    if found then
      return v_job;
    end if;
  end if;

  insert into public.jobs (user_id, options, input_meta, idempotency_key)
  values (p_user_id, coalesce(p_options, '{}'::jsonb), coalesce(p_input_meta, '{}'::jsonb), p_idempotency_key)
  returning * into v_job;

  perform public.reserve_credits(p_user_id, v_job.id, 1);
  return v_job;
end;
$$;

create function public.start_job(p_job_id uuid, p_worker_ref text default null)
returns public.jobs
language plpgsql security definer set search_path = public as $$
declare
  v_job public.jobs;
begin
  select * into v_job from public.jobs where id = p_job_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('job %s', p_job_id);
  end if;
  if v_job.status = 'running' then
    update public.jobs set worker_ref = coalesce(p_worker_ref, worker_ref)
     where id = p_job_id returning * into v_job;
    return v_job;
  end if;
  if v_job.status <> 'queued' then
    raise exception 'conflict' using errcode = 'P0409', detail = format('job is %s', v_job.status);
  end if;
  update public.jobs
     set status = 'running', started_at = now(), worker_ref = coalesce(p_worker_ref, worker_ref)
   where id = p_job_id returning * into v_job;
  return v_job;
end;
$$;

-- Progress updates after the job has finished are ignored (the row is returned unchanged).
create function public.update_job_progress(p_job_id uuid, p_stage public.job_stage, p_progress real)
returns public.jobs
language plpgsql security definer set search_path = public as $$
declare
  v_job public.jobs;
begin
  update public.jobs
     set stage = coalesce(p_stage, stage),
         progress = least(greatest(coalesce(p_progress, progress), 0), 1)
   where id = p_job_id and status in ('queued', 'running')
   returning * into v_job;
  if found then
    return v_job;
  end if;
  select * into v_job from public.jobs where id = p_job_id;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('job %s', p_job_id);
  end if;
  return v_job;
end;
$$;

-- Captures the reservation and stores the result. The stored result is the worker's
-- JSON plus job_id, credits_charged, balance_after and expires_at (JobResult, §2).
create function public.complete_job(p_job_id uuid, p_result jsonb)
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
  return v_job;
end;
$$;

create function public.fail_job(p_job_id uuid, p_error jsonb)
returns public.jobs
language plpgsql security definer set search_path = public as $$
declare
  v_job public.jobs;
begin
  select * into v_job from public.jobs where id = p_job_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('job %s', p_job_id);
  end if;
  if v_job.status = 'failed' then
    return v_job;
  end if;
  if v_job.status not in ('queued', 'running') then
    raise exception 'conflict' using errcode = 'P0409', detail = format('job is %s', v_job.status);
  end if;

  perform public.settle_reservation(p_job_id, false);
  update public.jobs
     set status = 'failed',
         error = coalesce(p_error, jsonb_build_object('code', 'internal_error', 'message', 'job failed')),
         finished_at = now()
   where id = p_job_id returning * into v_job;
  return v_job;
end;
$$;

-- Only queued jobs can be cancelled (contract §2: 409 once running).
create function public.cancel_job(p_job_id uuid, p_user_id uuid)
returns public.jobs
language plpgsql security definer set search_path = public as $$
declare
  v_job public.jobs;
begin
  select * into v_job from public.jobs where id = p_job_id and user_id = p_user_id for update;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('job %s', p_job_id);
  end if;
  if v_job.status = 'cancelled' then
    return v_job;
  end if;
  if v_job.status <> 'queued' then
    raise exception 'conflict' using errcode = 'P0409', detail = format('job is %s', v_job.status);
  end if;

  perform public.settle_reservation(p_job_id, false);
  update public.jobs set status = 'cancelled', finished_at = now()
   where id = p_job_id returning * into v_job;
  return v_job;
end;
$$;

-- Reaper (contract §10): fails jobs left running past the timeout and releases their credit,
-- and does the same for jobs never picked up at all. A job whose message was lost before
-- start_job — a worker that died, a malformed body, a dead-lettered message — stays 'queued'
-- with its credit reserved forever, and every leak permanently lowers the owner's usable
-- balance. Queued jobs get the longer grace of p_queued_timeout_seconds, since a queue
-- backlog is not yet a failure.
create function public.reap_stale_jobs(p_timeout_seconds integer, p_queued_timeout_seconds integer)
returns integer
language plpgsql security definer set search_path = public as $$
declare
  v_job record;
  v_count integer := 0;
begin
  if p_timeout_seconds is null or p_timeout_seconds <= 0 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_timeout_seconds must be positive';
  end if;
  if p_queued_timeout_seconds is null or p_queued_timeout_seconds <= 0 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_queued_timeout_seconds must be positive';
  end if;
  for v_job in
    select id, status from public.jobs
     where (status = 'running'
            and coalesce(started_at, created_at) < now() - make_interval(secs => p_timeout_seconds))
        or (status = 'queued'
            and created_at < now() - make_interval(secs => p_queued_timeout_seconds))
     for update skip locked
  loop
    perform public.fail_job(v_job.id, jsonb_build_object(
      'code', 'worker_timeout',
      'message', format('no completion within %s seconds',
                        case when v_job.status = 'running' then p_timeout_seconds
                             else p_queued_timeout_seconds end)));
    v_count := v_count + 1;
  end loop;
  return v_count;
end;
$$;

-- The cron entry point keeps its one-argument shape (0003_rls.sql grants this signature):
-- a job that was never picked up waits ten worker timeouts before it is failed.
create function public.reap_stale_jobs(p_timeout_seconds integer)
returns integer
language plpgsql security definer set search_path = public as $$
begin
  if p_timeout_seconds is null or p_timeout_seconds <= 0 then
    raise exception 'invalid_argument' using errcode = '22023', detail = 'p_timeout_seconds must be positive';
  end if;
  return public.reap_stale_jobs(p_timeout_seconds, p_timeout_seconds * 10);
end;
$$;

-- ---------------------------------------------------------------------------
-- Purchases and affiliates (contract §4, §12)
-- ---------------------------------------------------------------------------
-- Inserts the purchase, grants the plan's credits and writes the affiliate commission in
-- one transaction, all keyed by the webhook idempotency key: a replay returns the
-- existing purchase and changes nothing.
create function public.record_purchase(
  p_user_id uuid,
  p_provider public.purchase_provider,
  p_provider_order_id text,
  p_plan_id text,
  p_amount_cents integer,
  p_net_cents integer,
  p_referral_code text,
  p_raw jsonb,
  p_idempotency_key text
) returns public.purchases
language plpgsql security definer set search_path = public as $$
declare
  v_purchase public.purchases;
  v_plan public.plans;
  v_referral record;
  v_commission integer;
begin
  if p_idempotency_key is null or p_provider_order_id is null then
    raise exception 'invalid_argument' using errcode = '22023',
      detail = 'p_idempotency_key and p_provider_order_id are required';
  end if;

  perform public.lock_credit_account(p_user_id);

  select * into v_purchase from public.purchases
   where idempotency_key = p_idempotency_key
      or (provider = p_provider and provider_order_id = p_provider_order_id)
   limit 1;
  if found then
    if v_purchase.user_id <> p_user_id then
      raise exception 'conflict' using errcode = 'P0409',
        detail = format('order %s:%s belongs to another user', p_provider, p_provider_order_id);
    end if;
    return v_purchase;
  end if;

  select * into v_plan from public.plans where id = p_plan_id;
  if not found then
    raise exception 'not_found' using errcode = 'P0404', detail = format('plan %s', p_plan_id);
  end if;

  insert into public.purchases
    (user_id, provider, provider_order_id, plan_id, credits, amount_cents, net_cents, currency,
     referral_code, raw, idempotency_key)
  values
    (p_user_id, p_provider, p_provider_order_id, v_plan.id, v_plan.credits,
     greatest(coalesce(p_amount_cents, 0), 0), greatest(coalesce(p_net_cents, 0), 0), v_plan.currency,
     p_referral_code, coalesce(p_raw, '{}'::jsonb), p_idempotency_key)
  returning * into v_purchase;

  if v_plan.credits > 0 then
    perform public.grant_credits(p_user_id, v_plan.credits,
                                 p_provider::text || ':order:' || p_provider_order_id,
                                 p_idempotency_key, v_plan.name);
  end if;

  update public.profiles
     set plan = case when v_plan.interval is not null then 'subscription'
                     when plan = 'free' then 'credits'
                     else plan end
   where id = p_user_id;

  if p_referral_code is not null then
    select r.id as referral_code_id, a.id as affiliate_id, a.commission_rate
      into v_referral
      from public.referral_codes r
      join public.affiliates a on a.id = r.affiliate_id
     where lower(r.code) = lower(p_referral_code) and r.active and a.active and a.user_id <> p_user_id;
    if found then
      v_commission := round(v_referral.commission_rate * v_purchase.net_cents)::integer;
      insert into public.affiliate_commissions (purchase_id, affiliate_id, referral_code_id, rate, amount_cents)
      values (v_purchase.id, v_referral.affiliate_id, v_referral.referral_code_id,
              v_referral.commission_rate, v_commission);
      update public.referral_codes set uses = uses + 1 where id = v_referral.referral_code_id;
    end if;
  end if;

  return v_purchase;
end;
$$;

-- ---------------------------------------------------------------------------
-- Webhook delivery claim (contract §4)
-- ---------------------------------------------------------------------------
-- Claims one provider delivery: true means this caller owns applying the event, false
-- means it is a duplicate to be acknowledged without side effects.
--
-- A row that already exists is still claimable in two cases:
--   * it carries an `error` — the previous delivery failed halfway, so this delivery is
--     the retry that has to run it;
--   * it was claimed more than p_lease_seconds ago and was never closed at all
--     (`processed_at` and `error` both null) — the process holding the claim was killed
--     between claim and completion (OOM, SIGKILL, container eviction). Without this rule
--     the claim is held forever, every provider retry is answered "duplicate", and a
--     customer who paid is never credited.
--
-- The row is taken `for update`, and reclaiming a stale row stamps `received_at = now()`
-- before the lock is released. Two workers reclaiming the same stale event therefore
-- serialise: the loser re-reads the row after the winner commits, sees a claim inside its
-- lease, and stands down. Exactly one of them applies the event.
create function public.claim_webhook_event(
  p_idempotency_key text,
  p_provider public.purchase_provider,
  p_event_name text,
  p_payload jsonb,
  p_lease_seconds integer
) returns boolean
language plpgsql security definer set search_path = public as $$
declare
  v_event public.webhook_events;
begin
  if p_idempotency_key is null or p_idempotency_key = '' then
    raise exception 'invalid_argument' using errcode = '22023',
      detail = 'p_idempotency_key is required';
  end if;
  if p_lease_seconds is null or p_lease_seconds <= 0 then
    raise exception 'invalid_argument' using errcode = '22023',
      detail = 'p_lease_seconds must be positive';
  end if;

  insert into public.webhook_events (provider, event_name, idempotency_key, payload)
  values (p_provider, p_event_name, p_idempotency_key, coalesce(p_payload, '{}'::jsonb))
  on conflict (idempotency_key) do nothing;
  if found then
    return true;
  end if;

  select * into v_event from public.webhook_events
   where idempotency_key = p_idempotency_key
     for update;
  if not found then
    return false;
  end if;
  if v_event.error is not null then
    return true;
  end if;
  if v_event.processed_at is not null
     or v_event.received_at > now() - make_interval(secs => p_lease_seconds) then
    return false;
  end if;
  update public.webhook_events set received_at = now() where id = v_event.id;
  return true;
end;
$$;

-- ---------------------------------------------------------------------------
-- API keys (contract §11). The plaintext is returned exactly once, by create_api_key.
-- Hashing uses core sha256() so no extension schema is needed on the search_path.
-- ---------------------------------------------------------------------------
create function public.create_api_key(p_user_id uuid, p_name text default null)
returns table (id uuid, prefix text, plaintext text)
language plpgsql security definer set search_path = public as $$
declare
  v_plaintext text;
  v_id uuid;
begin
  if not exists (select 1 from public.profiles where profiles.id = p_user_id) then
    raise exception 'not_found' using errcode = 'P0404', detail = format('profile %s', p_user_id);
  end if;
  v_plaintext := 'tm_live_' || replace(gen_random_uuid()::text, '-', '');
  insert into public.api_keys (user_id, key_hash, prefix, name)
  values (p_user_id, encode(sha256(convert_to(v_plaintext, 'UTF8')), 'hex'), left(v_plaintext, 12), p_name)
  returning api_keys.id into v_id;
  return query select v_id, left(v_plaintext, 12), v_plaintext;
end;
$$;

-- Returns the owning user id for an unrevoked key hash (sha256 hex of the plaintext) and
-- stamps last_used_at; null when the key is unknown or revoked.
create function public.authenticate_api_key(p_key_hash text)
returns uuid
language plpgsql security definer set search_path = public as $$
declare
  v_user_id uuid;
begin
  update public.api_keys set last_used_at = now()
   where key_hash = p_key_hash and revoked_at is null
   returning user_id into v_user_id;
  return v_user_id;
end;
$$;

-- True when the key exists for the user (already-revoked keys stay revoked); false otherwise.
create function public.revoke_api_key(p_key_id uuid, p_user_id uuid)
returns boolean
language plpgsql security definer set search_path = public as $$
begin
  update public.api_keys set revoked_at = coalesce(revoked_at, now())
   where id = p_key_id and user_id = p_user_id;
  return found;
end;
$$;
