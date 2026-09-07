# SnapPlay AI — database

PostgreSQL 16 / Supabase schema for the credit ledger, jobs, billing, API keys and
affiliates described in `docs/API_CONTRACT.md` (§3, §6, §10, §11, §12).

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
> **no buttons**, showing only "You've used your 3 free credits. Visit snapplay.ai to add
> more."
>
> **Nothing fails loudly.** The migration succeeds, RLS is correct, the API is healthy,
> every test passes, and the plugin does exactly what it was written to do. The only
> symptom is that nobody can pay.
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
> Any line ending in `MISSING` is a plan nobody can buy. Put that check in the deployment
> checklist; it is the only alarm there is. The webhook side depends on the same column:
> before calling `record_purchase` the handler resolves the event's variant to a plan with
> `find_by_variant(provider, variant_id)`, falling back to a `plan_id` passed in the
> checkout's custom data. With `provider_variant_ids` empty and no `plan_id` in the custom
> data, that lookup raises `404 No plan matches this purchase.` — the delivery stays
> unprocessed and the provider keeps retrying. So a payment taken through a checkout link
> built outside this system would not grant credits either.
>
> `checkout_url_template` is seeded for the `snapplay.lemonsqueezy.com` store; change it if
> your store subdomain or provider differs. `{variant_id}`, `{user_id}` and `{ref}` are
> substituted by the backend, and parameters left empty are dropped from the query string.

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

A passing run ends with `ALL TESTS PASSED (6 test groups)`: the five
`tests/test_*.sql` files (affiliates, api_keys, jobs, ledger, rls) plus the concurrency
race, which must end with exactly one winner and one `insufficient_credits`.
