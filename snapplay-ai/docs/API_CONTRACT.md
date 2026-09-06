# SnapPlay AI — API & Data Contract (v2)

This document is the single source of truth shared by the JUCE plugin client
(`plugin/`), the FastAPI backend (`backend/`), the Supabase schema (`db/`), the AWS
deployment (`infra/aws/`), and the growth engine (`growth/`). Any change here must be
mirrored in all of them.

Changes in v2: free tier 5 → 3 credits; upload cap 25 → 10 MB; latency target 2.5 → 2.0 s
on A10G; selectable Scale-Snap modes (§8); in-plugin paywall and `checkout_url` (§3);
AWS as the default production path (§10); first-class API keys (§11); affiliates (§12).

Base URL: `https://api.snapplay.ai` (configurable in the plugin as `apiBaseUrl`).
All routes are versioned under `/v1`. All request/response bodies are JSON
unless stated. Timestamps are RFC 3339 UTC strings. IDs are UUID v4 strings.

## 1. Authentication

* Identity provider: **Supabase Auth (GoTrue)**. Users sign in with
  email + password (or magic link on the website). The plugin never stores the
  password — only the `access_token` (JWT) and `refresh_token`.
* Every authenticated request carries `Authorization: Bearer <access_token>`.
* The backend verifies the JWT signature using either the project's JWT secret
  (HS256) or the JWKS endpoint (RS256/ES256) — configured by
  `SUPABASE_JWT_SECRET` / `SUPABASE_JWKS_URL`. Required claims: `sub` (user id),
  `exp`, `aud == "authenticated"`.
* Machine access (CI, scripts) may use an API key instead:
  `X-API-Key: sp_live_<32 chars>`. Keys are stored as SHA-256 hashes in
  `api_keys`.

### `POST /v1/auth/token`
Proxy to GoTrue password grant so the plugin talks to one host only.
```json
{ "email": "a@b.c", "password": "•••" }
```
→ `200`
```json
{ "access_token": "<jwt>", "refresh_token": "<opaque>", "expires_in": 3600,
  "token_type": "bearer", "user": { "id": "<uuid>", "email": "a@b.c" } }
```

### `POST /v1/auth/refresh`
```json
{ "refresh_token": "<opaque>" }
```
→ same shape as `/v1/auth/token`.

### `GET /v1/me`   (auth)
→ `200`
```json
{ "user": { "id": "<uuid>", "email": "a@b.c", "plan": "free|credits|subscription" },
  "balance": { "credits": 42, "reserved": 1, "available": 41,
               "subscription_renews_at": "2026-10-01T00:00:00Z" } }
```
`available = credits - reserved`. The plugin displays `available`.

## 2. Jobs (audio → stems + MIDI)

### `POST /v1/jobs`   (auth, multipart/form-data)
| field     | type   | notes |
|-----------|--------|-------|
| `audio`   | file   | FLAC (preferred, produced client-side with `juce::FlacAudioFormat`), WAV, MP3, OGG, AIFF. Max **10 MB**, max **60 s** (longer input is truncated server-side to the first 60 s, and `truncated: true` is reported). |
| `options` | string | JSON, see below |

`options` JSON (all optional):
```json
{ "client_sample_rate": 48000,
  "stems": ["bass", "drums", "other", "vocals"],
  "transcribe": ["bass", "other", "vocals"],
  "drum_slices": true,
  "target_root_midi": 48,
  "idempotency_key": "<client uuid>" }
```
* `stems` default = all four Demucs v4 sources. The UI label "Synth" maps to the
  Demucs source `other`.
* `target_root_midi` default `48` (C3). The server reports each stem's detected
  root so the client can transpose to this target.
* `idempotency_key`: re-posting with the same key returns the existing job
  (no second credit charge).

Behaviour:
1. Verify auth → `401`.
2. Validate file → `413` (too large) / `415` (unsupported) / `422` (bad options).
3. `reserve_credits(user, job_id, 1)` → `402 insufficient_credits` if it fails.
4. Persist job (`status = queued`), dispatch to GPU worker.
5. → `202`
```json
{ "job_id": "<uuid>", "status": "queued", "credits_reserved": 1,
  "balance": { "credits": 42, "reserved": 1, "available": 41 } }
```

### `GET /v1/jobs/{job_id}`   (auth)
→ `200` JobStatus:
```json
{ "job_id": "<uuid>", "status": "queued|running|succeeded|failed",
  "stage": "upload|separate|transcribe|analyze|package|done",
  "progress": 0.0,
  "created_at": "...", "started_at": "...", "finished_at": "...",
  "error": { "code": "worker_timeout", "message": "..." },
  "result": <JobResult | null> }
```
`404` if the job does not belong to the caller.

### `GET /v1/jobs/{job_id}/events`   (auth, `text/event-stream`)
Server-Sent Events. The plugin consumes this with `juce::WebInputStream`
(chunked read). Each event:
```
event: progress
data: {"stage":"separate","progress":0.35}

event: result
data: <JobStatus with result>

event: error
data: {"code":"...","message":"..."}
```
A `result` or `error` event ends the stream. Heartbeat comment lines (`: ping`)
are sent every 5 s.

### `WS /v1/jobs/{job_id}/ws`   (auth via `?token=` query or first message)
Same payloads as SSE, as JSON text frames. Provided for web clients; the plugin
uses SSE.

### `DELETE /v1/jobs/{job_id}`   (auth)
Cancels a queued job and releases its reservation. `409` if already running.

### JobResult
```json
{
  "job_id": "<uuid>",
  "credits_charged": 1,
  "balance_after": 41,
  "input": { "duration_seconds": 30.0, "sample_rate": 44100, "channels": 2,
             "truncated": false },
  "analysis": {
    "bpm": 124.0, "bpm_confidence": 0.91,
    "key": { "root": "F", "mode": "minor", "root_midi": 53, "confidence": 0.82,
             "scale_pitch_classes": [5, 7, 8, 10, 0, 1, 3] },
    "downbeats_seconds": [0.0, 1.935, 3.871],
    "beats_seconds": [0.0, 0.484, 0.968]
  },
  "stems": [
    { "name": "bass", "url": "https://…signed…", "format": "wav",
      "sample_rate": 44100, "channels": 2, "duration_seconds": 30.0,
      "root_midi": 41, "root_confidence": 0.77, "peak_db": -3.1, "rms_db": -18.2,
      "transients_seconds": [0.01, 0.49, 0.97],
      "suggested_adsr": { "attack_ms": 2.0, "decay_ms": 120.0,
                          "sustain": 0.8, "release_ms": 180.0 },
      "slices": [ { "start_seconds": 0.0, "end_seconds": 0.48, "midi_note": 36 } ] }
  ],
  "midi": {
    "url": "https://…signed…/score.mid", "ppq": 480, "bpm": 124.0,
    "tracks": [
      { "name": "bass", "channel": 0,
        "notes": [ { "start_seconds": 0.0, "duration_seconds": 0.5,
                     "start_ticks": 0, "duration_ticks": 496,
                     "pitch": 41, "velocity": 100 } ] }
    ]
  },
  "expires_at": "2026-09-06T12:00:00Z"
}
```
* Stem names are exactly `bass | drums | other | vocals`.
* `slices` is present only for `drums` when `drum_slices` is true. Slice
  `midi_note` starts at 36 (C1) and increments.
* Signed URLs are valid until `expires_at` (24 h). Files live in Supabase
  Storage bucket `jobs/<user_id>/<job_id>/`.

## 3. Credits

### `GET /v1/credits/ledger?limit=50&cursor=…`   (auth)
```json
{ "entries": [ { "id": "<uuid>", "created_at": "...", "entry_type": "grant|reserve|capture|release|refund|expire|adjust",
                 "amount": 50, "balance_after": 92, "job_id": null,
                 "source": "lemonsqueezy:order:123", "note": "Credit pack 50" } ],
  "next_cursor": null }
```

### `GET /v1/plans`   (public, `user_id` attached when called with auth)
```json
{ "plans": [
  { "id": "free",         "name": "Free",          "credits": 3,  "price_usd": 0,    "interval": null,    "checkout_url": null },
  { "id": "pack_50",      "name": "50 Credits",    "credits": 50, "price_usd": 9.00, "interval": null,    "checkout_url": "https://…/checkout/buy/…?checkout[custom][user_id]=…" },
  { "id": "sub_monthly",  "name": "Pro Monthly",   "credits": 60, "price_usd": 7.99, "interval": "month", "checkout_url": "https://…" } ] }
```
`checkout_url` carries the caller's `user_id` as provider custom data so the webhook can
attribute the purchase without an email lookup. When the request is unauthenticated the
URL is returned without that parameter. New accounts are granted **3 credits** at signup.

### In-plugin paywall
When `balance.available` reaches 0 the plugin shows a prompt built from `/v1/plans`:
"You've used your 3 free credits — unlock 50 more for $9, or subscribe for $7.99/mo",
with buttons opening the corresponding `checkout_url` in the system browser. The plugin
polls `GET /v1/me` every 5 s while the prompt is open so the balance updates within a
second of the webhook landing.

### `GET /v1/plans` for machines
The growth engine (see §11) authenticates with an API key and never sees this prompt.

## 4. Payment webhooks

### `POST /v1/webhooks/lemonsqueezy`
* Header `X-Signature`: hex HMAC-SHA256 of the raw body with
  `LEMONSQUEEZY_WEBHOOK_SECRET`. Reject with `401` when invalid.
* Events handled: `order_created` (credit pack), `subscription_created`,
  `subscription_payment_success`, `subscription_cancelled`, `subscription_expired`.
* The user is identified by `meta.custom_data.user_id` (set at checkout) or by
  customer email lookup.
* Idempotency key = `lemonsqueezy:<event_name>:<data.id>`; duplicates → `200`
  with `{ "status": "duplicate" }`.

### `POST /v1/webhooks/paddle`
* Header `Paddle-Signature`: `ts=…;h1=…`; verify HMAC-SHA256 over
  `"{ts}:{raw_body}"` with `PADDLE_WEBHOOK_SECRET`; reject if `|now - ts| > 5 min`.
* Events: `transaction.completed`, `subscription.activated`,
  `subscription.updated`, `subscription.canceled`.
* Idempotency key = `paddle:<event_type>:<event_id>`.

## 5. Errors
```json
{ "error": { "code": "insufficient_credits", "message": "You have 0 credits.",
             "details": { "available": 0 } } }
```
| HTTP | code |
|------|------|
| 400 | `bad_request` |
| 401 | `unauthorized`, `token_expired`, `invalid_signature` |
| 402 | `insufficient_credits` |
| 404 | `not_found` |
| 409 | `conflict` |
| 413 | `payload_too_large` |
| 415 | `unsupported_media_type` |
| 422 | `validation_error` |
| 429 | `rate_limited` (headers `Retry-After`, `X-RateLimit-Remaining`) |
| 500 | `internal_error` |
| 503 | `worker_unavailable` |

Rate limits: 10 job submissions / minute / user, 60 reads / minute / user.

## 6. Database (Supabase / PostgreSQL) — public API surface

Tables (schema `public`): `profiles`, `credit_accounts`, `credit_ledger`,
`jobs`, `job_assets`, `api_keys`, `plans`, `purchases`, `subscriptions`,
`webhook_events`. Full DDL in `db/migrations/`.

Balance invariant: `credit_accounts.balance` is a cached value that must equal
the sum of `credit_ledger.amount` for the user; it is only mutated inside the
functions below, under `SELECT … FOR UPDATE` on the account row.

Functions (all `SECURITY DEFINER`, callable via PostgREST `rpc/` by the
service-role key only; RLS blocks direct ledger writes):

| function | returns | behaviour |
|----------|---------|-----------|
| `reserve_credits(p_user_id uuid, p_job_id uuid, p_amount int)` | `credit_balance` | Locks account; raises `SQLSTATE 'P0402'` (`insufficient_credits`) when `balance - reserved < p_amount`; inserts ledger `reserve` (amount = -p_amount, does not change `balance`, increments `reserved`). Idempotent per `(job_id, 'reserve')`. |
| `settle_reservation(p_job_id uuid, p_success boolean)` | `credit_balance` | On success: ledger `capture` (balance -= amount, reserved -= amount). On failure: ledger `release` (reserved -= amount). Idempotent: a second call is a no-op returning the current balance. |
| `grant_credits(p_user_id uuid, p_amount int, p_source text, p_idempotency_key text, p_note text default null, p_expires_at timestamptz default null)` | `credit_balance` | Inserts ledger `grant`; duplicate `p_idempotency_key` is a no-op returning the current balance. |
| `refund_job(p_job_id uuid, p_reason text)` | `credit_balance` | Reverses a captured job (ledger `refund`), idempotent. |
| `get_balance(p_user_id uuid)` | `credit_balance` | `(credits, reserved, available)` — read-only. |
| `expire_credits()` | `int` | Cron helper: expires grants past `expires_at` (ledger `expire`), returns rows affected. |

`credit_balance` is a composite type `(credits int, reserved int, available int)`.

Job lifecycle in `jobs.status`: `queued → running → succeeded | failed | cancelled`.

## 7. Pipeline interface (backend ↔ GPU worker)

```python
class PipelineOptions(BaseModel):
    stems: list[Literal["bass","drums","other","vocals"]]
    transcribe: list[Literal["bass","drums","other","vocals"]]
    drum_slices: bool = True
    target_root_midi: int = 48
    max_seconds: float = 60.0

class PipelineResult(BaseModel):   # mirrors JobResult minus job_id/credits/urls
    input: InputInfo
    analysis: Analysis
    stems: list[StemResult]        # each carries `wav_bytes: bytes` before upload
    midi: MidiResult               # carries `smf_bytes: bytes` before upload

def run_pipeline(audio_bytes: bytes, options: PipelineOptions,
                 progress: Callable[[str, float], None]) -> PipelineResult: ...
```
Stages and the **2.0 s** budget on an A10G (`g5.xlarge`) for a 30 s stereo clip:

| stage | tool | budget |
|-------|------|--------|
| decode + resample to 44.1 kHz | soundfile / torchaudio | 50 ms |
| separate | Demucs v4 `htdemucs` (fp16, CUDA, optional TensorRT) | 900 ms |
| transcribe | Basic Pitch ONNX (TensorRT EP), per stem in one batch | 400 ms |
| analyze | aubio tempo + onset, key via chroma template matching | 150 ms |
| package | WAV encode, MIDI write, upload to storage | 300 ms |
| **total** | | **≈1.8 s** (+ network) |

The budget holds only on A10G-class hardware. On a T4 (`g4dn.xlarge`) separation alone
costs ~3–5 s, so a T4 deployment must advertise a ~5 s target instead; the instance type
is a deployment variable, not a contract guarantee.

`SNAPPLAY_PIPELINE` selects the backend: `fake` (deterministic CPU stub for tests and
local development), `local` (in-process, requires the GPU extras), `modal`
(`worker/modal_app.py`), `runpod` (`worker/runpod_handler.py`), or `aws`
(SQS queue + ECS GPU worker, `worker/aws_worker.py` — see §10).

## 8. Plugin-side derived values

* Root transposition: `semitones = target_root_midi - stem.root_midi`.
* Scale-Snap is client-side. The `scale_mode` parameter selects the pitch-class set,
  and `scale_root` (0–11, default = `analysis.key.root_midi % 12`) rotates it:

  | `scale_mode` | intervals from root | source |
  |--------------|--------------------|--------|
  | `detected` (default) | — | `analysis.key.scale_pitch_classes` verbatim |
  | `major` | 0 2 4 5 7 9 11 | computed |
  | `minor` | 0 2 3 5 7 8 10 | computed (natural minor) |
  | `pentatonic_major` | 0 2 4 7 9 | computed |
  | `pentatonic_minor` | 0 3 5 7 10 | computed |
  | `off` | — | passthrough, no snapping |

  Incoming MIDI notes snap to the nearest pitch class in the set; ties resolve downward.
  A note-off always uses the pitch its note-on was snapped to, even if the mode changed
  while the note was held.
* Auto-ADSR: use `suggested_adsr` when present, else derive from the stem's
  envelope (see `plugin/Source/Core/Envelope.h`).
* Drum mode: `slices[i]` mapped to MIDI note `slices[i].midi_note`; if absent,
  slice locally from `transients_seconds`.

## 9. Export formats

* `.mid`: Standard MIDI File type 1, PPQ 480, tempo meta event from
  `analysis.bpm`, one track per transcribed stem, notes from `midi.tracks`.
* `.fsc`: FL Studio score file. Chunk layout `FLhd` (format `0x10`, channel
  count, PPQ 96) + `FLdt` containing an FL version text event (id 199) and one
  `PatternNotes` data event (id 224) holding 24-byte note records
  (position u32, flags u16, rack_channel u16, length u32, key u32,
  fine_pitch u8, u1 u8, release u8, midi_channel u8, pan u8, velocity u8,
  mod_x u8, mod_y u8). This layout follows community reverse-engineering
  (PyFLP); `.mid` remains the guaranteed interchange path.

## 10. AWS deployment (default production path)

**Storage.** `S3StorageService` (boto3) writes to `s3://<bucket>/jobs/<user_id>/<job_id>/`
and returns presigned GET URLs valid until `expires_at`. Setting `S3_ENDPOINT_URL` points
the same code at Cloudflare R2. A bucket lifecycle rule expires objects after 24 h.
CloudFront (OAC to the bucket, signed URLs) is optional and changes nothing client-side —
`stems[].url` stays an opaque signed URL.

**Queue.** `POST /v1/jobs` enqueues `{job_id, user_id, input_key, options}` on SQS after
`create_job` reserves the credit. The worker long-polls, extends message visibility while
processing, uploads results, and calls `complete_job` / `fail_job` idempotently. Three
failed receives move the message to a DLQ. A reaper releases reservations for jobs left
`running` past `JOB_TIMEOUT_SECONDS`, so a dead worker never silently consumes a credit.

**Control plane.** FastAPI on ECS Fargate behind an ALB. API Gateway HTTP APIs do not
support SSE, which §2 requires, so Lambda is not used for the job routes.

Config keys: `AWS_REGION`, `S3_BUCKET`, `S3_ENDPOINT_URL`, `CLOUDFRONT_DOMAIN`,
`CLOUDFRONT_KEY_PAIR_ID`, `SQS_JOB_QUEUE_URL`, `SQS_DLQ_URL`, `JOB_TIMEOUT_SECONDS`,
`GPU_INSTANCE_TYPE` (Terraform `var.gpu_instance_type`, default `g5.xlarge`).

## 11. API keys and the growth engine

Machine clients authenticate with `X-API-Key: sp_live_<32 chars>`, stored as a SHA-256
hash in `api_keys` (`prefix` kept in clear for display). Keys carry the owning user's
credit balance and are subject to the same rate limits. `POST /v1/api-keys` (auth)
creates one and returns the plaintext exactly once; `DELETE /v1/api-keys/{id}` revokes it.

The UGC automation engine (`growth/`) uses such a key to submit jobs and never touches
user JWTs.

## 12. Affiliates

Tables `affiliates` (user, code, commission rate, payout details), `referral_codes`
(code → affiliate, uses, active), and `affiliate_commissions` (purchase, affiliate,
`amount_cents` = 30 % of net revenue after provider fees, status `pending|paid|void`).
A checkout carries `checkout[custom][ref]`; the webhook resolves it to an affiliate and
writes a commission row in the same transaction as the credit grant, keyed by the same
idempotency key so a replayed webhook cannot double-pay.
