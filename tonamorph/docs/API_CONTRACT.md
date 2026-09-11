# Tonamorph — API & Data Contract (v2)

This document is the single source of truth shared by the JUCE plugin client
(`plugin/`), the FastAPI backend (`backend/`), the Supabase schema (`db/`), the AWS
deployment (`infra/aws/`), and the growth engine (`growth/`). Any change here must be
mirrored in all of them.

Changes in v2: free tier 5 → 3 credits; upload cap 25 → 10 MB; latency target 2.5 → 2.0 s
on A10G; selectable Scale-Snap modes (§8); in-plugin paywall and `checkout_url` (§3);
AWS as the default production path (§10); first-class API keys (§11); affiliates (§12).

Clarified against the shipped implementation (no behaviour changed): WebSocket auth is
`?token=` only (§2); `GET /health` is documented as an unversioned alias of
`GET /v1/health` (below); `403 unauthorized` is added to the §5 table for the
`SQLSTATE 42501` RLS-misconfiguration case.

Added for the quality loops of the go-to-market plan (`docs/GTM_PLAN.md` §2.6, §3.2,
Appendix C §3–6): result feedback with the bounded automatic refund
(`POST /v1/jobs/{job_id}/feedback`, §2), the optional plugin identity headers on
`GET /v1/me` (§1), provider refund events (§4), and a new §14 — `POST /v1/nps`,
`GET /v1/status`, `GET /v1/version`, `POST /v1/telemetry/crash` and the growth events the
backend emits to Klaviyo. Migration `0005_quality_loops.sql` carries the tables (§6).

Base URL: `https://api.tonamorph.com` (the plugin's default; overridable at runtime with
`tonamorph::cloud::ApiClient::setBaseUrl()`, which sets `ApiClient::Config::baseUrl`).
All routes are versioned under `/v1`. All request/response bodies are JSON
unless stated. Timestamps are RFC 3339 UTC strings. IDs are UUID v4 strings.

### `GET /v1/health` (public) — and the unversioned `GET /health` alias

```json
{ "status": "ok" }
```

The health router is mounted twice: once unversioned and once under `/v1`, so both
`GET /health` and `GET /v1/health` answer `200 {"status": "ok"}`. `/health` exists only
as a compatibility alias for probes that cannot be given a prefix; everything shipped in
this repository — the ALB target-group health check, the API container's own
`HEALTHCHECK`, and the smoke steps in the READMEs — uses `/v1/health`. It is the single
exception to "all routes are versioned under `/v1`"; do not add others.

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
  `X-API-Key: tm_live_<32 chars>`. Keys are stored as SHA-256 hashes in
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

A password grant for an account that has not confirmed its email answers
`401 unauthorized` with the message `Confirm your email address before signing in.`;
GoTrue checks the password before the confirmation state, so this reaches nobody who could
not already sign in. Every other refusal is `401 unauthorized` / `Invalid credentials.`,
so a wrong password and an unknown address are indistinguishable.

### `POST /v1/auth/signup`
Proxy to GoTrue `POST /auth/v1/signup` (anon key, `redirect_to` =
`<AUTH_SITE_URL>/auth/confirm`).
```json
{ "email": "a@b.c", "password": "•••" }
```
→ `201` when the project requires email confirmation (the default): the account exists
but cannot sign in until the link in the confirmation email is followed.
```json
{ "status": "confirmation_pending", "user": { "id": "<uuid>", "email": "a@b.c" },
  "session": null }
```
→ `201` when confirmation is disabled (GoTrue auto-confirm): a session is issued at once.
```json
{ "status": "session", "user": { "id": "<uuid>", "email": "a@b.c" },
  "session": { "access_token": "<jwt>", "refresh_token": "<opaque>", "expires_in": 3600,
               "token_type": "bearer" } }
```
Errors: `409 conflict` when the address already has a confirmed account (GoTrue's
`user_already_exists` and its obfuscated identity-less user answer alike);
`422 validation_error` carrying GoTrue's own message for a rejected password
(`weak_password`) or address (`validation_failed`), and for `signup_disabled`;
`429 rate_limited` from GoTrue's own email limits. A second sign-up for an address whose
account is still unconfirmed answers `201 confirmation_pending` again and re-sends the
confirmation email. Malformed addresses (no `local@domain`, over 254 characters) are
refused `422` before anything reaches GoTrue.

Disclosure on this route is deliberate — a user who forgot they have an account would
otherwise wait for an email that never comes — and bounded: the per-address budget below
applies, and `/token`, `/recover` and `/resend` never confirm that an address exists.

### `POST /v1/auth/recover`
Proxy to GoTrue `POST /auth/v1/recover` (`redirect_to` = `<AUTH_SITE_URL>/auth/reset-password`).
```json
{ "email": "a@b.c" }
```
→ `200 {"status": "ok"}` **always**, known address or not. Every GoTrue 4xx is swallowed
— including its send-frequency `429`, which only a known address can trigger — and only a
GoTrue 5xx becomes `500 internal_error`.

### `POST /v1/auth/resend`
Proxy to GoTrue `POST /auth/v1/resend` (`redirect_to` = `<AUTH_SITE_URL>/auth/confirm`).
```json
{ "email": "a@b.c", "type": "signup" }
```
→ `200 {"status": "ok"}` always, exactly as `/recover`. `type` accepts only `signup`
(the default). An email is only actually sent for an account that is still unconfirmed.

### `POST /v1/auth/logout`   (auth — session token only, never an API key)
No body. Proxies GoTrue `POST /auth/v1/logout?scope=local` as the caller, revoking the
session's refresh token → `200 {"status": "ok"}`. The access token is a signed JWT that
nothing consults GoTrue about, so it stays valid until `exp`; the client discards both
tokens (the plugin does). A GoTrue 4xx — the session is already gone — is still `ok`;
only a 5xx is `500 internal_error`. Counts against the reads budget (§5).

### Pre-authentication rate limit
`token`, `signup`, `recover` and `resend` share one budget of 10 attempts per minute per
submitted email address (case- and whitespace-insensitive); `refresh` has the same budget
per refresh token. Over budget answers `429 rate_limited` with `Retry-After` before
anything reaches GoTrue. The budget is keyed on the credential rather than the client
address because the API proxies GoTrue from a single address (`docs/SECURITY.md` §6).

### Email confirmation and password recovery
1. The website (or the plugin's "Create account" link, which opens `<website>/signup`)
   posts to `/v1/auth/signup`. The `auth.users` row is inserted at once and the
   `handle_new_user` trigger (§6) grants the 3 welcome credits, which stay unreachable
   until the account can sign in.
2. GoTrue emails a link that verifies the token and redirects to
   `<AUTH_SITE_URL>/auth/confirm`; a browser session arrives in the URL fragment, which
   the page may ignore and simply say "confirmed — open the plugin and sign in".
   `/v1/auth/resend` re-sends that email.
3. `/v1/auth/token` before confirmation answers the `Confirm your email address` `401`
   above; afterwards it issues the session and `GET /v1/me` shows the 3 credits.
4. Recovery: "Forgot password?" in the plugin opens `<website>/reset-password`, which
   posts to `/v1/auth/recover`. The emailed link lands on
   `<AUTH_SITE_URL>/auth/reset-password` with a recovery session in the fragment, and the
   page sets the new password against GoTrue directly (`PUT /auth/v1/user`, e.g.
   supabase-js `updateUser`); the API proxies no step of that, since the browser already
   talks to Supabase.

`AUTH_SITE_URL` (backend setting, default `http://localhost:3000`) is the base of both
landing routes; both must be registered in the Supabase Auth redirect allow-list, or
GoTrue silently redirects to its own site URL instead.

### `GET /v1/me`   (auth)
→ `200`
```json
{ "user": { "id": "<uuid>", "email": "a@b.c", "plan": "free|credits|subscription",
            "marketing_opt_in": false, "referral_code": "GREG30" },
  "balance": { "credits": 42, "reserved": 1, "available": 41,
               "subscription_renews_at": "2026-10-01T00:00:00Z" } }
```
`available = credits - reserved`. The plugin displays `available`.

Optional request headers, sent by the plugin and ignored on every other route:

| header | value |
|--------|-------|
| `X-Plugin-Version` | the plugin's release, e.g. `0.1.0` (≤ 32 characters, `[0-9A-Za-z.+_-]`) |
| `X-Host` | the DAW as the host reports it, e.g. `Ableton Live 12` (≤ 64 printable ASCII characters) |
| `X-Plugin-OS` | optional, e.g. `macOS 15.1` (≤ 64 printable ASCII characters) |

`X-Plugin-Version` and `X-Host` together identify an installation: the first `GET /v1/me`
that carries a pair the account has not sent before is recorded in `plugin_installs`
(§6) and emits the `Plugin Installed` growth event (§14); every later request only stamps
`last_seen_at`. A malformed or absent header is ignored — it never fails the route — and
the response is the same either way.

`marketing_opt_in` and `referral_code` come from the sign-up: the website signs up
through supabase-js with `options.data`, which GoTrue stores as
`auth.users.raw_user_meta_data`, and the `handle_new_user` trigger (§6,
`0004_account_deletion.sql`) copies `referral_code`, `utm_source`, `utm_medium`,
`utm_campaign`, `utm_content`, `utm_term` (text, trimmed, at most 100 characters each),
`marketing_opt_in` (boolean, default `false`) and `terms_accepted_at` (timestamp, `null`
when absent or unparsable) into `profiles`. `referral_code` is kept only when it names an
**active** `referral_codes` row at sign-up time, spelled as that row spells it, and is
`null` otherwise — an unknown code never fails a sign-up. The welcome grant is unchanged.
The UTM fields and `terms_accepted_at` are not in this response; the export below carries
them. Accounts created any other way (an API-first JWT, a sign-up without metadata) have
`marketing_opt_in: false` and `referral_code: null`.

### `GET /v1/me/export`   (auth — session token only, never an API key)
Everything the service holds about the caller, as one JSON document (GDPR Art. 15 / 20).
→ `200` with `Content-Disposition: attachment; filename="account-export.json"`:
```json
{ "exported_at": "...",
  "user": { "id": "<uuid>", "email": "a@b.c", "plan": "free|credits|subscription",
            "marketing_opt_in": false, "referral_code": "GREG30", "created_at": "...",
            "utm_source": "tiktok", "utm_medium": null, "utm_campaign": null,
            "utm_content": null, "utm_term": null, "terms_accepted_at": "..." },
  "balance": { "credits": 42, "reserved": 0, "available": 42, "subscription_renews_at": null },
  "ledger": [ <LedgerEntry, §3>… ],
  "jobs": [ <JobStatus, §2>… ],
  "purchases": [ { "id", "provider", "provider_order_id", "plan_id", "credits", "amount_cents",
                   "net_cents", "currency", "referral_code", "created_at" }… ],
  "subscriptions": [ { "id", "provider", "provider_subscription_id", "plan_id", "status",
                       "current_period_end", "cancelled_at", "referral_code", "created_at" }… ],
  "api_keys": [ { "id", "name", "prefix", "created_at", "last_used_at", "revoked_at" }… ],
  "affiliate": { "code", "commission_rate", "active", "payout_details", "created_at",
                 "referral_codes": [ { "code", "uses", "active", "created_at" }… ],
                 "commissions": [ { "id", "purchase_id", "rate", "amount_cents", "status",
                                    "paid_at", "created_at" }… ] } | null }
```
`ledger` is complete and oldest first; `jobs` is complete and newest first, and every
`result` keeps its analysis but has `stems[].url` and `midi.url` set to `null` — object
URLs are access tokens, not data, and the objects themselves are gone after 24 h. Raw
provider payloads and key hashes are never part of it. Budgets: the reads budget plus
**1 export per minute per user** (`429 rate_limited` with `Retry-After`, §5).

### `DELETE /v1/me`   (auth — session token only, never an API key)
```json
{ "confirm": "a@b.c" }
```
`confirm` must equal the session's email address (case- and whitespace-insensitive),
otherwise `422 validation_error` with `loc: ["body", "confirm"]` and nothing changes.
→ `200 {"status": "deleted"}`. Errors: `409 conflict` (`Wait for your queued and running
jobs to finish, then retry.`) while any job of the caller is `queued` or `running` —
cancel it or let it finish, then retry; `401` for an API key. Counts against the reads
budget. The three steps run in this order: the caller's storage objects under
`jobs/<user_id>/` are deleted, then `delete_user_account` (§6) tombstones the data in
one transaction, then the login is deleted at GoTrue (`DELETE /auth/v1/admin/users/{id}`
with the service-role key). Should the last step fail, the response is `500
internal_error`: the data is already gone, every later request with that account's
tokens answers `401`, and the failure is logged with the user id so the operator finishes
the login deletion from the Supabase dashboard (which ends in the same state, see §6).

Afterwards the access token is still a valid signature until `exp`, and an API key of
the account no longer exists: **every** request carrying either answers
`401 unauthorized` with the message `This account has been deleted.` — the profile
tombstone, not GoTrue, is what refuses it. The address may sign up again and starts a
new, unrelated account.

### Account deletion and export
Deletion removes the person and keeps the books (`docs/SECURITY.md`, "Data-subject
rights"): the profile stays as a tombstone (`email = deleted+<user_id>@invalid`,
`display_name`, the UTM fields and `marketing_opt_in` cleared, `deleted_at` set;
`referral_code` and `terms_accepted_at` kept as attribution and legal record), API keys and `job_assets` rows are deleted,
job rows keep only their lifecycle (`status`, `stage`, timestamps, `error`) and lose
`options`, `input_meta`, `result`, `worker_ref` and `idempotency_key`, purchases and
subscriptions keep their amounts and ids but lose the provider payload (`raw`), referral
codes are revoked and the affiliate's payout details cleared while commissions owed stay,
feedback rows keep their rating and reason but lose the `note`, NPS answers keep the
score but lose the `comment`, the account's `plugin_installs` rows are deleted (§14),
the unused credits are written off with one `adjust` ledger entry (`source =
"account_deletion"`) so the account closes at zero, and a row is written to
`account_deletions(user_id, requested_at, ledger_rows_kept)`. The ledger, purchases and
commissions therefore keep pointing at the tombstone. A subscription at the payment
provider is **not** cancelled by this call; the user cancels it in the provider's
customer portal. Export first, delete second: the export is the last chance to read the
data.

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

With `MAINTENANCE_MODE=true` (backend setting, default `false`) this route answers
`503 service_unavailable` with `Retry-After: 300`, the message `New jobs are paused for
maintenance; retry in a few minutes.` and `details.retry_after_seconds = 300`, before the
jobs budget is touched. Every other route keeps working — results, events, balances and
cancellations stay reachable during maintenance.

### `GET /v1/jobs?limit=20&cursor=…`   (auth)
The caller's jobs, newest first (`created_at desc, id desc`), `limit` 1–100 (default 20).
→ `200`
```json
{ "jobs": [ <JobStatus>… ], "next_cursor": "2026-09-01T12:00:00.123456Z_<uuid>" }
```
`next_cursor` is `null` on the last page; otherwise pass it back verbatim as `cursor` —
it is opaque to clients (a UTC timestamp and the last job id, URL-safe as is). A cursor
not produced by this route is `422 validation_error`. Counts against the reads budget.

### `GET /v1/jobs/{job_id}`   (auth)
→ `200` JobStatus:
```json
{ "job_id": "<uuid>", "status": "queued|running|succeeded|failed|cancelled",
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

### `WS /v1/jobs/{job_id}/ws`   (auth via `?token=` query **only**)
Same payloads as SSE, as JSON text frames. Provided for web clients; the plugin
uses SSE. The access token is carried by the `?token=` query parameter and nothing
else — there is no in-band authentication frame, and `Authorization` headers are not
read on this route (`docs/SECURITY.md` §2.1 explains why the query form is the only one
and how tokens are kept out of logs).

Authentication, the read rate limit and job ownership are all checked **before** the
handshake is accepted. On failure the application closes with code **4401** and the §5
error code as the close reason (`unauthorized`, `token_expired`, `rate_limited`,
`not_found`). Because that close is emitted before `websocket.accept()`, an ASGI server
that cannot deliver a close frame during the upgrade reports the rejection as an HTTP
**403** on the handshake instead — uvicorn does exactly that. A client must therefore
treat both a 4401 close and a 403 handshake rejection as "not authorised for this job".

### `DELETE /v1/jobs/{job_id}`   (auth)
Cancels a queued job and releases its reservation. → `204` with an empty body;
`409 conflict` if the job is already running, `404` if it is not the caller's.

### `POST /v1/jobs/{job_id}/feedback`   (auth)
The thumbs on a result, and the automatic refund of an unusable morph
(`docs/GTM_PLAN.md` §2.6).
```json
{ "rating": "up|down",
  "reason": "bleed|wrong_key|midi_off|clicks|slow|other",
  "note": "≤ 140 characters",
  "drop_to_ready_ms": 4200 }
```
`reason`, `note` and `drop_to_ready_ms` (the plugin's own drop-to-playable timer, ≥ 0)
are optional; blank text is stored as `null`. → `201`
```json
{ "refunded": true, "balance": { "credits": 3, "reserved": 0, "available": 3 } }
```
One row per job (`job_feedback`, §6): a second call for the same job replaces the rating,
reason and note (an omitted `drop_to_ready_ms` keeps the measured one). `refunded`
reports whether the job's credit is back — by this call or an earlier one.

The refund rule, decided in one database transaction (`record_job_feedback` →
`refund_job_for_feedback`, §6): a `down` rating on a job that is `succeeded`, finished
within **24 hours**, with a reason other than `slow`, writes one ledger `refund` entry
(`source = job:<id>`, note `user:unusable:<reason>` or `user:unusable:unspecified`), so
the balance in the response — and in the next `GET /v1/me` — already carries the credit.
Bounds against abuse: automatic refunds are limited to `max(3, 20 % of the account's
captured jobs of the last 30 days)` per 30 days, and to **2 lifetime** for an account
that never purchased; beyond a bound the feedback is stored, `refunded` is `false`, and
support reviews it. A thumbs-up, a `slow` reason, a failed job (never charged) or a job
older than 24 hours records the feedback without a refund. Errors: `404 not_found` for a
job that is not the caller's, `409 conflict` (`Rate a finished job.`) while the job is
`queued` or `running`, `422 validation_error` for anything outside the shape above.
Counts against the reads budget (§5).

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
`source` names what moved the credits: `signup`, `job:<job_id>`, `<provider>:order:<id>`,
`support` for manual adjustments, and `account_deletion` for the single `adjust` entry
that writes the unused balance off when the account is deleted (§1).

### `GET /v1/plans?ref=<code>`   (public, `user_id` attached when called with auth)
```json
{ "plans": [
  { "id": "free",         "name": "Free",          "credits": 3,  "price_usd": 0,    "interval": null,    "checkout_url": null },
  { "id": "pack_50",      "name": "50 Credits",    "credits": 50, "price_usd": 9.00, "interval": null,    "checkout_url": "https://…/checkout/buy/…?checkout[custom][user_id]=…" },
  { "id": "sub_monthly",  "name": "Pro Monthly",   "credits": 60, "price_usd": 7.99, "interval": "month", "checkout_url": "https://…" } ] }
```
`checkout_url` carries the caller's `user_id` as provider custom data so the webhook can
attribute the purchase without an email lookup, and the optional `ref` query parameter as
`checkout[custom][ref]` (§12). `ref` must match `^[A-Za-z0-9_-]{1,64}$` — it is
interpolated straight into the checkout URL, so anything else is `422 validation_error`.
When the request is unauthenticated the URL is returned without the `user_id` parameter;
empty parameters are dropped rather than sent blank. `checkout_url` is `null` for the free
plan **and for any plan whose `plans.provider_variant_ids` has no id for a checkout
provider** — see the deployment note in `db/README.md`. That configuration gap is
announced rather than silent: the API logs every such plan id at startup (error level
under `ENV=production`), and `python -m app.checks` prints the same list and exits
non-zero, so a deployment can gate on it before a user meets a paywall with no buttons. New accounts are granted
**3 credits** at signup.

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
  `subscription_payment_success`, `subscription_cancelled`, `subscription_expired`, and
  `order_refunded` (a money refund: emits `Refund Issued`, §14, and moves no credits).
* **Exactly one event per sale grants credits and writes the affiliate commission.**
  LemonSqueezy splits a subscription checkout over several events with different
  `data.id`s, so the plan decides which one pays: a one-off pack is paid for by its
  `order_created`, a subscription period by its `subscription_payment_success` (the first
  period included). Every other event only moves subscription and plan state. Paddle bills
  each period as its own `transaction.completed`, so that event alone pays there.
* The user is identified by `meta.custom_data.user_id` (set at checkout) or by
  customer email lookup.
* Idempotency key = `lemonsqueezy:<event_name>:<data.id>`; duplicates → `200`
  with `{ "status": "duplicate" }`.
* **A claim never strands a paid event.** The key is claimed before the event is applied
  and released with an error if applying fails, so the provider's retry re-runs it. A
  claim left behind by a process that died mid-apply expires after
  `WEBHOOK_CLAIM_LEASE_SECONDS` (default 300) and the next retry takes it over; the
  reclaim is decided under a row lock, so two retries cannot both apply it.
* **The affiliate `ref` survives a store that drops it.** It is read from the paying
  event's `custom_data`, and failing that from the code the checkout event stored on the
  subscription, so a store that does not forward `custom_data` onto
  `subscription_payment_success` does not silently lose the commission (§12). A payment
  that can be attributed neither way is logged at warning level with its subscription id.

**At least one** webhook secret is required in production: `Settings` refuses to start
with `ENV=production` unless `LEMONSQUEEZY_WEBHOOK_SECRET` or `PADDLE_WEBHOOK_SECRET` is
set (along with `SUPABASE_URL`, a JWT secret or JWKS URL, an https non-localhost
`AUTH_SITE_URL`, a real pipeline and real storage). A provider whose secret is empty is
one this deployment does not sell through: its route answers `404 not_found` (`This
payment provider is not configured.`) before reading the body, so an empty secret is
never used as an HMAC key. The GPU worker builds the same settings with
`SERVICE_ROLE=worker`, which skips the webhook-secret and `AUTH_SITE_URL` checks it has
no use for; the API runs with the default `SERVICE_ROLE=api`.

### `POST /v1/webhooks/paddle`
* Header `Paddle-Signature`: `ts=…;h1=…`; verify HMAC-SHA256 over
  `"{ts}:{raw_body}"` with `PADDLE_WEBHOOK_SECRET`; reject if `|now - ts| > 5 min`.
* Events: `transaction.completed`, `subscription.activated`,
  `subscription.updated`, `subscription.canceled`, and `adjustment.created` /
  `adjustment.updated` when `data.status = approved` and `data.action` is `refund` or
  `chargeback` (any other adjustment is acknowledged `ok` and ignored).
* Idempotency key = `paddle:<event_type>:<event_id>`.

### Growth events from webhooks (§14)
The paying event of a sale emits `Purchase Completed` (`is_renewal` is LemonSqueezy's
`billing_reason = renewal` or Paddle's `origin = subscription_recurring`); a
`subscription_cancelled` / `subscription.canceled` event emits `Subscription Cancelled`;
a refund or chargeback emits `Refund Issued` with the money amount and the provider's
reason. A Paddle adjustment names neither the customer nor the checkout's custom data,
so it is attributed through the purchase whose `provider_order_id` is its
`transaction_id`; an unknown one is `404 not_found` and retried by the provider like any
other unattributable event. Refunds never move credits here (that reconciliation is
manual, GTM plan §4 P1); every event is deduplicated at Klaviyo by the adjustment or order
it names, so `adjustment.created` and `adjustment.updated` for one refund count once.

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
| 403 | `unauthorized` (RLS / grant misconfiguration — see below) |
| 404 | `not_found` |
| 409 | `conflict` |
| 413 | `payload_too_large` |
| 415 | `unsupported_media_type` |
| 422 | `validation_error` |
| 429 | `rate_limited` (headers `Retry-After`, `X-RateLimit-Remaining`) |
| 500 | `internal_error` |
| 503 | `worker_unavailable`, `service_unavailable` (`MAINTENANCE_MODE`, §2; header `Retry-After: 300`) |

`403` is not a route-level authorisation answer: user-scoped lookups answer `404` so
existence never leaks (§2). It appears only when PostgreSQL refuses the backend's own
statement with `SQLSTATE 42501` (`insufficient_privilege`) — that is, when the deployed
role grants or RLS policies of §6 do not match `db/migrations/0003_rls.sql`, for example
a service-role key that is missing `EXECUTE` on a `SECURITY DEFINER` credit function.
`backend/app/services/supabase.py` maps `42501` to `403` with the code `unauthorized` so the
misconfiguration is visible in the response rather than hidden inside a `500`. A
correctly deployed database never produces it; seeing it in production means the
migrations or the key are wrong, not that the caller lacked rights.

Other SQLSTATEs the same mapper translates: `P0402` → `402 insufficient_credits`,
`P0404` → `404 not_found`, `P0409` / `23505` → `409 conflict`, `22023` →
`422 validation_error`. Anything else is logged and answered `500 internal_error`.

Rate limits: 10 job submissions / minute / user, 60 reads / minute / user, 1 account
export / minute / user on top of the reads budget (§1), and 5 anonymous crash reports /
hour / client address (§14). `409 conflict` is also the answer to feedback on an
unfinished job (§2) and to a second NPS answer within 30 days (§14).

`401 unauthorized` with the message `This account has been deleted.` is the answer to any
credential of a deleted account (§1): the JWT verifies until `exp`, the profile tombstone
refuses it.

## 6. Database (Supabase / PostgreSQL) — public API surface

Tables (schema `public`): `profiles`, `credit_accounts`, `credit_ledger`,
`jobs`, `job_assets`, `api_keys`, `plans`, `purchases`, `subscriptions`,
`webhook_events`, and — since `0005_quality_loops.sql` — `job_feedback`, `nps_responses`,
`plugin_installs` plus the reporting view `growth_daily`. Full DDL in `db/migrations/`.

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

The same migration defines the job, billing and API-key functions the rest of this
contract refers to, under the same rules (`SECURITY DEFINER`, `service_role` only):
`create_job`, `start_job`, `update_job_progress`, `complete_job`, `fail_job`,
`cancel_job`, `reap_stale_jobs` (§10), `record_purchase` and `claim_webhook_event`
(§4, §12, §13),
`adjust_credits`, and `create_api_key` / `authenticate_api_key` / `revoke_api_key`
(§11). `db/README.md` lists their exact signatures. `0004_account_deletion.sql` adds
`delete_user_account(p_user_id uuid) → account_deletions` (§1: raises `P0409` while a job
is `queued`/`running`, `P0404` for an unknown profile, idempotent for a tombstoned one),
the `account_deletions` table (`service_role` only) and `profiles.deleted_at`; `profiles`
no longer cascades from `auth.users` — an `after delete` trigger on `auth.users` runs the
same function instead, so a login deleted from the Supabase dashboard leaves the same
tombstone and the same accounting rows.

`0005_quality_loops.sql` (§2 feedback, §14) adds `profiles.first_seen_at` — set once by
the backend with a conditional update when it first meets an account, which is when the
`Signed Up` event fires — and, all `SECURITY DEFINER`, `service_role` only:
`refund_job_for_feedback(p_job_id uuid, p_user_id uuid, p_reason text) → boolean` (the
§2 refund rule and bounds, decided under the job row and the account lock; `P0404` for
another user's job), `record_job_feedback(p_job_id, p_user_id, p_rating, p_reason,
p_note, p_drop_to_ready_ms) → job_feedback` (upsert; `P0409` while queued/running;
runs the refund on `down`), `submit_nps(p_user_id, p_score, p_comment) → nps_responses`
(`P0409` within 30 days of the last answer), `touch_plugin_install(p_user_id,
p_plugin_version, p_host, p_os) → boolean` (true on first sight of the pair),
`user_facts(p_user_id) → (email, plan, morphs_total, first_morph_at, last_morph_at,
has_purchased)` and `status_last_24h() → (morphs, succeeded, failed, p50_ms, p95_ms)`.
The view `growth_daily` has one row per UTC day: `signups`, `morphs_started`,
`morphs_succeeded`, `morphs_failed`, `p50_ms`, `p95_ms`, `credits_exhausted` (captures
that left the balance at zero), `purchases`, `revenue_cents`. `delete_user_account` now
also clears feedback notes and NPS comments and deletes the plugin installs (§1).
Authenticated users may `select` their own `job_feedback` and `nps_responses` rows;
`plugin_installs` and `growth_daily` are `service_role` only.

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
| analyze | librosa tempo + onset (numpy fallback), key via chroma template matching | 150 ms |
| package | WAV encode, MIDI write, upload to storage | 300 ms |
| **total** | | **≈1.8 s** (+ network) |

The budget holds only on A10G-class hardware. On a T4 (`g4dn.xlarge`) separation alone
costs ~3–5 s, so a T4 deployment must advertise a ~5 s target instead; the instance type
is a deployment variable, not a contract guarantee.

`TONAMORPH_PIPELINE` selects the backend: `fake` (deterministic CPU stub for tests and
local development), `local` (in-process, requires the GPU extras), `modal`
(`backend/worker/modal_app.py`), `runpod` (`backend/worker/runpod_handler.py`), or `aws`
(SQS queue + ECS GPU worker, `backend/worker/aws_worker.py` — see §10).

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

Machine clients authenticate with `X-API-Key: tm_live_<32 chars>`, stored as a SHA-256
hash in `api_keys` (`prefix` — the first 12 characters — kept in clear for display).
Keys carry the owning user's credit balance and are subject to the same rate limits.

`POST /v1/api-keys` (auth, JWT only) takes `{ "name": "ci" }` (optional, default
`"default"`) and answers `201` with the plaintext exactly once:

```json
{ "id": "<uuid>", "name": "ci", "prefix": "tm_live_ab12", "key": "tm_live_<32 chars>",
  "created_at": "..." }
```

`GET /v1/api-keys` (auth, JWT only) lists the caller's keys, newest first, revoked ones
included so a revocation stays visible; exactly what the row stores besides the hash:

```json
{ "keys": [ { "id": "<uuid>", "name": "ci", "prefix": "tm_live_ab12", "created_at": "...",
              "last_used_at": "...|null", "revoked_at": "...|null" } ] }
```

Neither the plaintext nor its hash is ever returned again. Counts against the reads budget.

`DELETE /v1/api-keys/{id}` (auth, JWT only) revokes it and answers `204`; an unknown or
foreign id is `404`. An API key cannot manage keys, call `/v1/auth/*`, export or delete
the account.

The UGC automation engine (`growth/`) uses such a key to submit jobs and never touches
user JWTs.

## 12. Affiliates

Tables `affiliates` (user, code, commission rate, payout details), `referral_codes`
(code → affiliate, uses, active), and `affiliate_commissions` (purchase, affiliate,
`amount_cents` = 30 % of net revenue after provider fees, status `pending|paid|void`).
A checkout carries `checkout[custom][ref]`; the webhook resolves it to an affiliate and
writes a commission row in the same transaction as the credit grant, keyed by the same
idempotency key so a replayed webhook cannot double-pay. The code is also kept on
`subscriptions.referral_code`, so a renewal whose `custom_data` no longer carries it is
still attributed to the affiliate who brought the subscriber in.

## 13. Policies left open by earlier drafts

* **Affiliate commissions recur.** Every purchase event that reaches `record_purchase`
  (a credit pack, a subscription's first payment, and each renewal payment) writes one
  `affiliate_commissions` row at the affiliate's rate on `net_cents`, keyed by the
  webhook's idempotency key. A replayed webhook never pays twice.
* **Subscription credits do not roll over.** Each renewal grants the plan's credits with
  `expires_at` = the end of that billing period; `expire_credits()` (cron) removes what
  is left. Expiring credits are spent before non-expiring ones, so a subscriber with a
  spare credit pack always uses the perishable balance first.
* **Credit-pack credits never expire.**
* **Cancelled subscriptions** keep their remaining credits until `current_period_end`,
  then lose them like any other period.

## 14. Feedback, status, version, telemetry and growth events

### `POST /v1/nps`   (auth)
```json
{ "score": 9, "comment": "≤ 500 characters" }
```
`score` is 0–10; `comment` is optional (blank is stored as `null`). → `201`
```json
{ "id": "<uuid>", "score": 9, "comment": "…", "created_at": "..." }
```
One answer per user per **30 days**: a second one is `409 conflict` (`You already
answered within the last 30 days.`). Stored in `nps_responses` (§6); emits
`NPS Submitted`. Counts against the reads budget.

### `GET /v1/status`   (public)
```json
{ "components": { "api": "operational",
                  "engine": "operational|degraded|paused",
                  "payments": "operational|unconfigured",
                  "website": "operational" },
  "last_24h": { "morphs": 128, "success_rate": 0.992, "p50_ms": 1840, "p95_ms": 4210 } }
```
`last_24h` counts the jobs that finished (`succeeded` or `failed`; cancellations are not
outcomes) in the last 24 hours, from `status_last_24h()` (§6); `success_rate` is
`succeeded / morphs` and `null` until a job finished; `p50_ms` / `p95_ms` are
`finished_at - coalesce(started_at, created_at)` over the successes and `null` until one
succeeded. `engine` is `paused` under `MAINTENANCE_MODE` (§2), `degraded` once **20 or
more** jobs finished in the window with a success rate below **0.9**, `operational`
otherwise; `payments` is `unconfigured` when neither webhook secret is set (§4). The
numbers are cached in-process for **60 seconds**; the component states are derived per
request. Unauthenticated requests are free; with credentials the request counts against
the reads budget (§5).

### `GET /v1/version`   (public)
```json
{ "latest": "0.1.0", "min_supported": "0.1.0",
  "download_url": "https://tonamorph.com/download",
  "notes_url": "https://tonamorph.com/changelog" }
```
From the settings `PLUGIN_LATEST_VERSION` and `PLUGIN_MIN_SUPPORTED_VERSION` (semantic
versions, default `0.1.0`) and `AUTH_SITE_URL` (§1) with `/download` and `/changelog`
appended. The plugin compares its own version: below `min_supported` it must update
before morphing, below `latest` it shows the update banner. Not rate limited.

### `POST /v1/telemetry/crash`   (auth optional)
```json
{ "plugin_version": "0.1.0", "os": "macOS 15.1", "host": "Ableton Live 12",
  "occurred_at": "2026-09-11T12:00:00Z",
  "backtrace": "≤ 16 KB of text", "opted_in": true }
```
→ `202 {"status": "accepted"}`. Sent only after the user opted in: `opted_in` must be
`true`, anything else is `422`. `plugin_version` ≤ 32 characters, `os` and `host` ≤ 64,
`backtrace` 1 byte to 16 KB of UTF-8. Never carries audio, tokens or the user's email.

With `SENTRY_DSN` set the report reaches Sentry as an error-level message tagged
`role=plugin`, `plugin_version`, `host` and `os`, with the backtrace as the attachment
`backtrace.txt`, the caller's user id when a session token was sent, and a fingerprint
of platform, version and the backtrace's first line. Without Sentry the report is logged
at warning level without the backtrace body. Budgets: a request with a session token
spends the reads budget (§5); without one it is limited to **5 per hour per client
address** (`429 rate_limited` with `Retry-After`) — behind the load balancer that address
is shared, so a signed-in plugin should send its token. Invalid credentials are still
`401`.

### Growth events (Klaviyo)
With `KLAVIYO_PRIVATE_API_KEY` set (empty disables everything; the key is never logged)
the backend sends these metrics to Klaviyo's Create Event API (`revision 2024-10-15`)
from a background task — never on a request's critical path, one retry, failures logged
and never surfaced. The profile is identified by `external_id` = user id plus the email
when known; the same call sets the profile properties listed. Every event carries a
deterministic `unique_id` so a replay (an idempotent `complete_job`, a re-delivered
webhook, a retried request) counts once. `KLAVIYO_TIMEOUT_SECONDS` (default 5) bounds
each call. Both the API and the GPU worker need the key: `Morph Completed` /
`Morph Failed` leave from whichever process finishes the job.

| metric | fires when | properties | profile properties |
|--------|-----------|------------|--------------------|
| `Signed Up` | the API first meets an account: at `POST /v1/auth/signup`, or on the first authenticated request of a profile the trigger created (`source = web`) or that the API had to create itself (`source = plugin`); `profiles.first_seen_at` makes it exactly once | `user_id`, `source`, `referral_code`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, `marketing_opt_in` | `signup_source`, `referral_code`, `utm_*`, `marketing_opt_in`, `plan`, `cohort_week` (`2026-W37`) |
| `Plugin Installed` | the first `GET /v1/me` with a new `X-Plugin-Version` / `X-Host` pair (§1) | `os`, `daw`, `plugin_version` | `os`, `daw`, `plugin_version` |
| `Morph Completed` | `complete_job` — the API-inline pipeline, a remote worker or a replay, all through `JobsService.complete` | `job_id`, `latency_ms`, `credits_charged`, `balance_after`, `morphs_total`, `bpm`, `key` (`F minor`) | `morphs_total`, `first_morph_at`, `last_morph_at`, `credits_available` |
| `Morph Failed` | `fail_job`, including the reaper's `worker_timeout` | `job_id`, `error_code`, `stage`, `latency_ms` | — |
| `Credits Exhausted` | a capture leaves the balance at zero, or `POST /v1/jobs` answers `402`; at most once per user per UTC day | `plan`, `checkout_url_pack_50`, `checkout_url_sub_monthly` (the caller's §3 URLs) | `plan`, `credits_available = 0` |
| `Checkout Started` | the website (`/checkout`); the backend has no trigger of its own, only the metric name (`app.services.klaviyo`) | `plan_id`, `ref` | — |
| `Purchase Completed` | the paying webhook event of a sale (§4) | `plan_id`, `price_usd`, `credits`, `is_renewal`, `referral_code` | `plan` |
| `Subscription Cancelled` | a provider cancellation event (§4) | `plan_id`, `period_end` | — |
| `Refund Issued` | an approved provider refund or chargeback (§4) | `amount_usd`, `reason` | — |
| `NPS Submitted` | `POST /v1/nps` | `score`, `comment` | `nps_score` |

Klaviyo lists a metric only after its first event, so before flows are built the
operator runs `python -m app.services.klaviyo seed --email <address>` in `backend/`,
which upserts one throwaway profile and sends one sample event per metric.

### Uptime probe
`.github/workflows/health-probe.yml` runs `curl -fsS "$API_URL/v1/health"` every five
minutes with the repository variable `API_URL` (skipped, not failed, while it is unset),
opens or updates one issue labelled `slo-breach` while the probe fails, and closes it on
the next healthy probe.
