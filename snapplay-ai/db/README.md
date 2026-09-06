# SnapPlay AI — database

PostgreSQL 16 / Supabase schema for the credit ledger, jobs, billing, API keys and
affiliates described in `docs/API_CONTRACT.md` (§3, §6, §10, §11, §12).

```
db/
├── migrations/
│   ├── 0001_schema.sql      extensions, enums, tables, indexes, triggers, plan seed
│   ├── 0002_functions.sql   credit_balance type and every SECURITY DEFINER function
│   └── 0003_rls.sql         roles, privileges, row-level security, function grants
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

After applying, set `plans.provider_variant_ids` (for example
`{"lemonsqueezy": "<variant id>", "paddle": "<price id>"}`) and, if the store subdomain
differs, `plans.checkout_url_template` (`{variant_id}`, `{user_id}` and `{ref}` are
substituted by the backend). Users that existed before the migration need a one-off
backfill of `profiles` and `credit_accounts`; the `on_auth_user_created` trigger only
covers new signups.

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
| `expire_credits()` | `integer` | cron; grants processed |
| `create_job(p_user_id, p_options, p_input_meta, p_idempotency_key)` | `jobs` | reserve + insert atomically |
| `start_job(p_job_id, p_worker_ref)` | `jobs` | queued → running |
| `update_job_progress(p_job_id, p_stage, p_progress)` | `jobs` | ignored once finished |
| `complete_job(p_job_id, p_result)` | `jobs` | captures; adds `job_id`, `credits_charged`, `balance_after`, `expires_at` to the result |
| `fail_job(p_job_id, p_error)` | `jobs` | releases |
| `cancel_job(p_job_id, p_user_id)` | `jobs` | queued only, else P0409 |
| `reap_stale_jobs(p_timeout_seconds)` | `integer` | fails running jobs past the timeout with `worker_timeout` |
| `record_purchase(p_user_id, p_provider, p_provider_order_id, p_plan_id, p_amount_cents, p_net_cents, p_referral_code, p_raw, p_idempotency_key)` | `purchases` | purchase + grant + commission, replay-safe |
| `create_api_key(p_user_id, p_name)` | `(id, prefix, plaintext)` | plaintext returned once |
| `authenticate_api_key(p_key_hash)` | `uuid` | owner or null; stamps `last_used_at` |
| `revoke_api_key(p_key_id, p_user_id)` | `boolean` | owner-scoped, idempotent |

Errors are raised with `SQLSTATE` / `MESSAGE` pairs the backend maps to HTTP:
`P0402 insufficient_credits` (402), `P0404 not_found` (404), `P0409 conflict` (409),
`22023 invalid_argument` (422), `42501 forbidden` (403). `DETAIL` carries specifics.

Credit expiry treats expiring credits as spent first: the amount expired for a grant is
`max(0, amount − credits captured or deducted since the grant)`, capped at the available
balance, so reserved credits are never expired.

## Running the tests

```bash
bash db/tests/run_tests.sh
```

The script needs the PostgreSQL 16 binaries (`PGBIN`, default
`/usr/lib/postgresql/16/bin`) and a non-root user able to write the data directory
(`SNAPPLAY_TEST_PGUSER`, default `pguser`; `SNAPPLAY_TEST_PGDATA`, default
`/home/user/pgdata/snapplay-test`). It creates a socket-only cluster on port
`SNAPPLAY_TEST_PGPORT` (54329), applies the shim and the migrations, runs every
`tests/test_*.sql`, runs a two-session race for the last credit, and always stops and
removes the cluster on exit. Any failed assertion, SQL error or unexpected race outcome
exits non-zero.
