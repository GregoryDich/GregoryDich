# Tonamorph — database

PostgreSQL 16 / Supabase schema for the credit ledger, jobs, billing, API keys,
affiliates and the quality loops (feedback, NPS, status) described in
`docs/API_CONTRACT.md` (§2, §3, §6, §10, §11, §12, §14).

> ## ⚠ The seed cannot sell anything until you fill in `provider_variant_ids`
>
> `0001_schema.sql` seeds `plans` with prices and a `checkout_url_template`, but
> `provider_variant_ids` keeps its column default `'{}'::jsonb` — the ids belong to your
> LemonSqueezy / Paddle store, so no migration can know them.
>
> The backend's `build_checkout_url()` returns `None` when a template contains
> `{variant_id}` and the plan has no id for any provider. So on a freshly migrated
> database **`GET /v1/plans` returns `"checkout_url": null` for every plan**, and the
> plugin's `PaywallPrompt` ignores plans without a checkout URL: the paywall opens with
> **no buttons**, showing only "You've used your 3 free credits. Visit tonamorph.com to add
> more."
>
> The migration succeeds, RLS is correct, the API is healthy and the plugin does exactly
> what it was written to do — the only symptom is that nobody can pay. The backend says so
> rather than leaving it silent: it logs every unsellable plan id at startup (error level
> under `ENV=production`), and `python3 -m app.checks` in `backend/` prints
> `{"check": "checkout_configured", "ok": false, "unsellable_plan_ids": [...]}` and exits
> non-zero, which is what a deployment should gate on.
>
> Fix it immediately after applying the migrations:
>
> ```sql
> update public.plans
>    set provider_variant_ids = '{"lemonsqueezy": "<variant id>"}'::jsonb   -- or {"paddle": "<price id>"}
>  where id = 'pack_50';
> update public.plans
>    set provider_variant_ids = '{"lemonsqueezy": "<variant id>"}'::jsonb
>  where id = 'sub_monthly';
> ```
>
> and verify from outside:
>
> ```sh
> curl -s "$API/v1/plans" | jq -r '.plans[] | select(.price_usd > 0) | "\(.id) \(.checkout_url // "MISSING")"'
> ```
>
> Any line ending in `MISSING` is a plan nobody can buy — the same answer `app.checks`
> gives from inside, without needing the API to be reachable first.
>
> The webhook side depends on the same column:
> before calling `record_purchase` the handler resolves the event's variant to a plan with
> `find_by_variant(provider, variant_id)`, falling back to a `plan_id` passed in the
> checkout's custom data. With `provider_variant_ids` empty and no `plan_id` in the custom
> data, that lookup raises `404 No plan matches this purchase.` — the delivery stays
> unprocessed and the provider keeps retrying. So a payment taken through a checkout link
> built outside this system would not grant credits either.
>
> `checkout_url_template` is seeded for the `tonamorph.lemonsqueezy.com` store; change it if
> your store subdomain or provider differs. `{variant_id}`, `{user_id}` and `{ref}` are
> substituted by the backend, and parameters left empty are dropped from the query string.

```
db/
├── migrations/
│   ├── 0001_schema.sql      extensions, enums, tables, indexes, triggers, plan seed
│   ├── 0002_functions.sql   credit_balance type and every SECURITY DEFINER function
│   ├── 0003_rls.sql         roles, privileges, row-level security, function grants
│   ├── 0004_account_deletion.sql  sign-up metadata on profiles, tombstone deletion, auth.users delete trigger
│   └── 0005_quality_loops.sql     job_feedback + bounded auto-refund, nps_responses, plugin_installs,
│                                  user_facts / status_last_24h, growth_daily view, profiles.first_seen_at
└── tests/
    ├── 00_local_auth_shim.sql   minimal auth.users / auth.uid() for local clusters only
    ├── run_tests.sh             throwaway PostgreSQL 16 cluster + all tests
    └── test_*.sql               assertions as plpgsql DO blocks
```

## Applying the migrations

The files are plain SQL, numbered, and must be applied in order. They assume the
Supabase `auth` schema exists (`auth.users`, `auth.uid()`) and the `anon`,
`authenticated` and `service_role` roles are present (a `DO` block creates them on a
plain cluster).

Recommended: `db/apply.sh` — a transactional, tracked runner (one transaction per file,
`public.schema_migrations` records what ran, re-runs are no-ops, `--dry-run` previews,
`--from NNNN` baselines files you already applied by hand, and it ends with a PostgREST
schema reload):

```bash
DATABASE_URL='postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres' bash db/apply.sh
```

Use either the script or the Supabase CLI below, not both: the CLI keeps its own,
separate migration ledger.

With the Supabase CLI (linked project):

```bash
supabase link --project-ref <ref>
for f in db/migrations/*.sql; do
  supabase migration new "$(basename "$f" .sql)"            # creates supabase/migrations/<ts>_<name>.sql
  cp "$f" "$(ls -t supabase/migrations/*.sql | head -n 1)"
done
supabase db push
```

Or directly with `psql` against the project's connection string:

```bash
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
```

Never apply `tests/00_local_auth_shim.sql` to Supabase; it exists only so a plain
PostgreSQL cluster has something for the `profiles` foreign key and the signup trigger to
point at.

After applying, set `plans.provider_variant_ids` — see the warning at the top of this
file; it is the one step whose omission is completely silent. Users that existed before
the migration need a one-off backfill of `profiles` and `credit_accounts`; the
`on_auth_user_created` trigger only covers new signups.

## Invariants

* `credit_accounts.balance` = `SUM(credit_ledger.amount)` over entry types
  `grant`, `capture`, `refund`, `expire`, `adjust` for that user.
* `credit_accounts.reserved` = `-SUM(amount)` of `reserve` rows whose job has no
  `capture` or `release` row yet; `0 <= reserved <= balance` is a table constraint.
* `available = balance - reserved` is what the plugin displays.
* Sign convention, enforced by a CHECK: `grant`/`refund`/`release` > 0,
  `reserve`/`capture` < 0, `expire` <= 0, `adjust` <> 0.
* Every ledger row snapshots `balance_after` and `reserved_after`; `seq` is a monotonic
  cursor for `GET /v1/credits/ledger`.
* `subscriptions.referral_code` keeps the affiliate code of the checkout that started the
  subscription. A renewal event that no longer carries `custom_data` is attributed from
  it, and an event without a code never clears it (§12).
* One row per `(job_id, entry_type)`, one row per `idempotency_key`. Both are unique
  indexes, and every function checks them under the account lock, so replays and retries
  never double-charge or double-grant.
* All account/ledger writes happen inside the functions below, after
  `SELECT … FOR UPDATE` on the `credit_accounts` row; no API role can write these
  tables directly.

## Functions (PostgREST `rpc/`)

All are `SECURITY DEFINER` with `search_path = public`. Only `service_role` may execute
the mutating ones; `get_balance` is also granted to `authenticated` and refuses any
`p_user_id` other than `auth.uid()`.

| function | returns | notes |
|----------|---------|-------|
| `reserve_credits(p_user_id, p_job_id, p_amount)` | `credit_balance` | P0402 on shortfall; idempotent per job |
| `settle_reservation(p_job_id, p_success)` | `credit_balance` | capture or release; later calls are no-ops |
| `grant_credits(p_user_id, p_amount, p_source, p_idempotency_key, p_note, p_expires_at)` | `credit_balance` | duplicate key is a no-op |
| `adjust_credits(p_user_id, p_amount, p_source, p_idempotency_key, p_note)` | `credit_balance` | support corrections; negative bounded by available |
| `refund_job(p_job_id, p_reason)` | `credit_balance` | reverses a capture once; P0404 if never captured |
| `get_balance(p_user_id)` | `credit_balance` | read-only |
| `expire_credits()` | `integer` | cron; grants processed. Expires grants in `expires_at` order and attributes spend to the grant that actually consumed it, so a credit spent once is not charged against every earlier grant |
| `create_job(p_user_id, p_options, p_input_meta, p_idempotency_key)` | `jobs` | reserve + insert atomically |
| `start_job(p_job_id, p_worker_ref)` | `jobs` | queued → running |
| `update_job_progress(p_job_id, p_stage, p_progress)` | `jobs` | ignored once finished |
| `complete_job(p_job_id, p_result)` | `jobs` | captures; adds `job_id`, `credits_charged`, `balance_after`, `expires_at` to the result |
| `fail_job(p_job_id, p_error)` | `jobs` | releases |
| `cancel_job(p_job_id, p_user_id)` | `jobs` | queued only, else P0409 |
| `reap_stale_jobs(p_timeout_seconds)` | `integer` | cron entry point (the only signature `service_role` may execute); delegates to the two-argument form with `p_queued_timeout_seconds = p_timeout_seconds * 10` |
| `reap_stale_jobs(p_timeout_seconds, p_queued_timeout_seconds)` | `integer` | fails `running` jobs past the first timeout **and** `queued` jobs never picked up past the second, each with `worker_timeout`, releasing their reservations; rows are taken `for update skip locked` so two reapers cannot fight |
| `record_purchase(p_user_id, p_provider, p_provider_order_id, p_plan_id, p_amount_cents, p_net_cents, p_referral_code, p_raw, p_idempotency_key)` | `purchases` | purchase + grant + commission, replay-safe |
| `claim_webhook_event(p_idempotency_key, p_provider, p_event_name, p_payload, p_lease_seconds)` | `boolean` | true when this caller owns applying the event. Insert wins outright; otherwise the row is taken `for update` and reclaimed only if it carries an `error` (the previous delivery failed) or its claim is older than `p_lease_seconds` with nothing recorded either way (the holder was killed mid-apply). A reclaim re-stamps `received_at` under the lock, so two workers cannot both take the same stranded event |
| `create_api_key(p_user_id, p_name)` | `(id, prefix, plaintext)` | plaintext returned once |
| `authenticate_api_key(p_key_hash)` | `uuid` | owner or null; stamps `last_used_at` |
| `revoke_api_key(p_key_id, p_user_id)` | `boolean` | owner-scoped, idempotent |
| `delete_user_account(p_user_id)` | `account_deletions` | GDPR erasure (`service_role` only, also fired by `on_auth_user_deleted`): `P0404` unknown profile, `P0409` while a job is `queued`/`running`, idempotent on a tombstone; writes off unused credits with one `adjust` row, deletes API keys and job assets, scrubs job/purchase payloads, revokes referral codes, replaces the e-mail with `deleted+<uuid>@invalid` and stamps `deleted_at`; ledger, purchases and commissions stay for accounting |
| `handle_new_user()` (trigger) | — | on `auth.users` insert: creates the profile, copies `referral_code` (active codes only), `utm_*`, `marketing_opt_in` and `terms_accepted_at` from `raw_user_meta_data`, grants the sign-up credits |
| `refund_job_for_feedback(p_job_id, p_user_id, p_reason)` | `boolean` | the GTM §2.6 rule under the job row and the account lock: the caller's `succeeded` job, `finished_at` within 24 h, `p_reason <> 'slow'`; automatic refunds (ledger `refund` rows whose note starts `user:unusable:`) at most `max(3, captured_last_30_days / 5)` per 30 days and at most 2 ever for an account with no `purchases` row. Calls `refund_job(p_job_id, 'user:unusable:<reason|unspecified>')`; returns whether the job's credit is back (true again for a job already refunded, false when ineligible or over a bound); `P0404` for another user's job |
| `record_job_feedback(p_job_id, p_user_id, p_rating, p_reason, p_note, p_drop_to_ready_ms)` | `job_feedback` | one row per job (upsert; a null `p_drop_to_ready_ms` keeps the stored one); `22023` for a rating outside `up`/`down`, an unknown reason, a note over 140 characters or a negative timer; `P0404` for another user's job, `P0409` while it is `queued`/`running`; a `down` rating runs `refund_job_for_feedback` and sets `refunded` |
| `submit_nps(p_user_id, p_score, p_comment)` | `nps_responses` | `22023` outside 0–10 or a comment over 500 characters, `P0404` unknown profile, `P0409` when the user answered within 30 days (decided under the profile row lock) |
| `touch_plugin_install(p_user_id, p_plugin_version, p_host, p_os)` | `boolean` | true the first time the user is seen with this `(plugin_version, host)` pair (the `Plugin Installed` event); afterwards stamps `last_seen_at`, fills `os` when it was null, returns false. `22023` for an empty or over-long value, `P0404` unknown profile |
| `user_facts(p_user_id)` | `(email, plan, morphs_total, first_morph_at, last_morph_at, has_purchased)` | read-only facts a growth event carries; no row for an unknown profile |
| `status_last_24h()` | `(morphs, succeeded, failed, p50_ms, p95_ms)` | jobs that finished in the last 24 h (`succeeded`/`failed` only) and the latency percentiles of the successes, `finished_at - coalesce(started_at, created_at)`; nulls when nothing succeeded |

Tables added by `0005_quality_loops.sql`: `job_feedback` (one row per job: `rating`,
`reason`, `note`, `drop_to_ready_ms`, `refunded`; owner may `select`), `nps_responses`
(`score`, `comment`; owner may `select`), `plugin_installs` (`service_role` only; primary
key `(user_id, plugin_version, host)`, `os`, `first_seen_at`, `last_seen_at`) and the
column `profiles.first_seen_at`, which the backend sets once with `update … where
first_seen_at is null` when it first meets an account (the `Signed Up` event). The view
`growth_daily` (`service_role` only) has one row per UTC day with something to report:
`signups`, `morphs_started`, `morphs_succeeded`, `morphs_failed`, `p50_ms`, `p95_ms`,
`credits_exhausted` (captures that left the balance at zero), `purchases`, `revenue_cents`.
`delete_user_account` now also clears `job_feedback.note` and `nps_responses.comment` and
deletes the user's `plugin_installs`; ratings and scores stay.

Internal helpers, called by the functions above and granted to nobody:
`balance_of(p_account)`, `lock_credit_account(p_user_id)`, `append_ledger(...)` and
`perishable_pool(p_user_id)` — the last replays a user's ledger in `seq` order to compute
how many *expiring* credits are still unspent, which is what lets `expire_credits()`
charge a spend to the grant it came off.

Errors are raised with `SQLSTATE` / `MESSAGE` pairs the backend maps to HTTP:
`P0402 insufficient_credits` (402), `P0404 not_found` (404), `P0409 conflict` (409),
`22023 invalid_argument` (422), `42501 forbidden` (403). `DETAIL` carries specifics.

Credit expiry treats expiring credits as spent first. For each grant, in `expires_at`
order, the amount expired is the perishable pool (`perishable_pool`) minus the perishable
grants still queued behind it, capped at the grant's own amount **and** at
`balance - reserved`, so reserved credits are never expired. One `expire` row per grant,
keyed `expire:<grant ledger id>`, so a grant is processed exactly once however often the
cron runs.

## Running the tests

```bash
bash db/tests/run_tests.sh
```

The script needs the PostgreSQL 16 binaries (`PGBIN`, default
`/usr/lib/postgresql/16/bin`) and a non-root user able to write the data directory
(`TONAMORPH_TEST_PGUSER`, default `pguser`; `TONAMORPH_TEST_PGDATA`, default
`/home/user/pgdata/tonamorph-test`). It creates a socket-only cluster on port
`TONAMORPH_TEST_PGPORT` (54329), applies the shim and the migrations, runs every
`tests/test_*.sql`, runs the two-session races (the last credit, and the reclaim of a
stranded webhook claim), and always stops and removes the cluster on exit. Any failed assertion, SQL error or unexpected race outcome
exits non-zero.

A passing run ends with `ALL TESTS PASSED (13 test groups)`: the eleven `tests/test_*.sql`
files (account_deletion, affiliates, api_keys, growth_daily, jobs, ledger, nps,
quality_loops, rls, signup_metadata, webhooks) plus two concurrency races — the last
credit, which must end with exactly one winner and one `insufficient_credits`, and a
stranded webhook claim past its lease, which exactly one of two simultaneous workers may
reclaim.
