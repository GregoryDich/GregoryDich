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
  routers/         health, auth, me, jobs, credits, plans, api_keys, webhooks
  services/        Protocols: Credits, Jobs, Storage, Users, ApiKeys, WebhookEvents, Dispatch
  pipeline/        base.py (run_pipeline Protocol, get_pipeline), fake.py (offline CPU stub)
tests/             pytest; conftest provides settings/app/client, mint_jwt, make_wav
```

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

## Test

```bash
python3 -m pytest -q
ruff check .
```

Tests are fully offline: `STORAGE_BACKEND=memory`, `SNAPPLAY_PIPELINE=fake`, HS256 test
JWTs minted in `tests/conftest.py`, AWS via moto, HTTP via respx.

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
