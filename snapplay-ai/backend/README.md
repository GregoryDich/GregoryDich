# SnapPlay AI backend

FastAPI control plane for the SnapPlay AI plugin. The binding API is
[`docs/API_CONTRACT.md`](../docs/API_CONTRACT.md) (v2); everything in `app/schemas.py`
mirrors it field for field.

## Layout

```
app/
  main.py          create_app() factory, CORS, request-id + JSON access log, routers under /v1
  config.py        Settings (pydantic-settings), get_settings(), override_settings()
  schemas.py       contract payloads (§1–§3, §5, §7, §11)
  errors.py        ApiException + §5 error envelope handlers and code constants
  dependencies.py  get_services() (the wired container) and get_principal() (JWT or API key)
  auth/            jwt.py (Supabase token verification), api_keys.py (sp_live_ format + sha256)
  middleware/      rate_limit.py (per-principal token buckets)
  routers/         health, auth, me, jobs, credits, plans, api_keys, webhooks
  services/        Protocols (__init__.py) + one module per domain, both backends:
                   supabase.py (PostgREST/Storage/GoTrue over httpx), memory.py (tests/dev),
                   credits, jobs, storage, users, api_keys, webhooks, plans, dispatch, events,
                   factory.py (build_services), aws/ (S3 + SQS + reaper)
  pipeline/        base.py (run_pipeline Protocol, get_pipeline), fake.py (offline CPU stub)
worker/            GPU worker entry points (aws_worker, modal_app, runpod_handler)
tests/             pytest; conftest provides settings/app/client, mint_jwt, make_wav;
                   tests/api (routes and services), tests/pipeline, tests/aws
```

`create_app` builds the service container once (`app.state.services`) from `Settings` and
stores the rate-limit buckets next to it (`app.state.rate_limits`); routers depend only on
the Protocols in `app/services/__init__.py`, so the backend they run against is a
configuration choice. `python -m app.services.aws.reaper` reuses the same
`build_services()`.

## Run

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt          # or: pip install -e ".[dev]"
cp .env.example .env                          # edit as needed; defaults are offline-safe
uvicorn app.main:app --reload --port 8000
curl -s localhost:8000/v1/health              # {"status":"ok"}
```

`uvicorn app.main:app` uses `create_app()` with settings from the environment/`.env`.
Interactive docs are at `/docs` outside production.

## Authentication (§1, §11)

* `Authorization: Bearer <supabase jwt>` — verified with `SUPABASE_JWT_SECRET` (HS256) or
  `SUPABASE_JWKS_URL` (RS256/ES256, keys cached in-process). The algorithm comes from the
  configuration, never from the token header; `aud` must be `authenticated`, clock leeway
  is 30 s, and an expired token answers `401 token_expired` so the client refreshes
  instead of re-authenticating.
* `X-API-Key: sp_live_<32 hex>` — the key is hashed with SHA-256 and resolved through
  `authenticate_api_key`; keys act as their owner but cannot manage keys or use `/v1/auth/*`.
* Rate limits are keyed by the authenticated identity: 10 job submissions and 60 reads per
  minute, answering `429` with `Retry-After` and `X-RateLimit-Remaining`.

## Backends

| concern | selected by | options |
|---------|-------------|---------|
| data | `SUPABASE_URL` (and `ENV`) | PostgREST when set outside tests, otherwise the in-memory store |
| storage | `STORAGE_BACKEND` | `supabase`, `s3` (also R2 via `S3_ENDPOINT_URL`), `memory` |
| dispatch | `SNAPPLAY_PIPELINE` | `fake`/`local` in-process, `modal`, `runpod`, `aws` (SQS) |
| job events | `SNAPPLAY_PIPELINE` | in-process bus for `fake`/`local`, DB polling for remote workers |

`app/services/memory.py` mirrors `db/migrations/0002_functions.sql` function by function —
the same idempotency keys (`reserve:<job_id>`, `signup:<user_id>`, `expire:<grant id>`),
the same job state machine and the same `insufficient_credits` / `conflict` / `not_found`
errors — so the routes behave identically on either backend.

## Billing policies (§13)

* A purchase webhook is claimed in `webhook_events` before anything else; a replay answers
  `200 {"status": "duplicate"}` and changes nothing.
* `record_purchase` writes the purchase, the credit grant and the affiliate commission
  under the webhook's idempotency key, so commissions recur per payment but never double-pay.
* Subscription credits are granted with `expires_at` = the end of the billing period
  (`expire_credits()` reclaims the remainder); credit-pack credits never expire. A
  cancelled subscription keeps its plan until `current_period_end`.

## Test

```bash
python3 -m pytest -q
ruff check app tests
```

Tests are fully offline: `STORAGE_BACKEND=memory`, `SNAPPLAY_PIPELINE=fake`, HS256 test
JWTs minted in `tests/conftest.py`, AWS via moto, HTTP via respx. `tests/api` covers the
auth matrix (including `alg: none` and HS/RS confusion), the job lifecycle from upload to
signed result URLs, SSE and WebSocket streams, ledger pagination, both webhook providers
and the rate limiter.

## Environment

All keys are listed with placeholders in `.env.example`. The important groups:

| group | keys |
|-------|------|
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` (HS256) or `SUPABASE_JWKS_URL` (RS256/ES256) |
| Storage | `STORAGE_BACKEND=supabase\|s3\|memory`, `STORAGE_BUCKET`, `SIGNED_URL_TTL_SECONDS` |
| AWS | `AWS_REGION`, `S3_BUCKET`, `S3_ENDPOINT_URL` (R2), `CLOUDFRONT_DOMAIN`, `CLOUDFRONT_KEY_PAIR_ID`, `CLOUDFRONT_PRIVATE_KEY`, `SQS_JOB_QUEUE_URL`, `SQS_DLQ_URL`, `JOB_TIMEOUT_SECONDS` |
| Payments | `LEMONSQUEEZY_WEBHOOK_SECRET`, `PADDLE_WEBHOOK_SECRET` |
| Pipeline | `SNAPPLAY_PIPELINE=fake\|local\|modal\|runpod\|aws`, `MODAL_APP_NAME`, `RUNPOD_ENDPOINT_ID`, `RUNPOD_API_KEY` |
| Limits | `MAX_UPLOAD_BYTES`, `MAX_INPUT_SECONDS`, `FREE_SIGNUP_CREDITS`, `RATE_LIMIT_JOBS_PER_MIN`, `RATE_LIMIT_READS_PER_MIN`, `AFFILIATE_COMMISSION_RATE` |
| Misc | `ENV=development\|test\|staging\|production`, `CORS_ALLOW_ORIGINS` |

With `ENV=production` the settings refuse to start with the fake pipeline, in-memory
storage, or without JWT verification configured.

## Pipeline backends

`get_pipeline(settings)` imports `app.pipeline.<SNAPPLAY_PIPELINE>` and returns its
`run_pipeline(audio_bytes, options, progress)`. `fake` is deterministic, CPU-only and
processes 30 s of stereo audio in well under two seconds, producing real WAV stems and a
real Standard MIDI File so the whole job flow can be exercised without a GPU. The GPU
backends need `requirements-gpu.txt`.
