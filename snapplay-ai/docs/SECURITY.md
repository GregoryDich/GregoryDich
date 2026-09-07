# SnapPlay AI — Security

Security posture for the components in this repository, derived from
[`API_CONTRACT.md`](API_CONTRACT.md) (cited as "§n"). The contract fixes *what* is
verified; this document fixes *how*, and lists the abuse cases the design has to
withstand.

## 1. Trust boundaries

| principal | holds | may call | must never see |
|-----------|-------|----------|----------------|
| Plugin (`plugin/Source/Cloud`) | the user's access and refresh tokens in `AuthManager`'s `juce::PropertiesFile` (see §2.1), never in the DAW project | `/v1/*` as that user | service-role key, webhook secrets, other users' jobs |
| Growth engine (`growth/mcp_server`) | one `sp_live_…` API key (§11) | `/v1/*` as the key's owner | user JWTs, anything not reachable with a key |
| Backend (`backend/app`) on Fargate | Supabase service-role key, JWT secret / JWKS URL, webhook secrets, S3 presign role, CloudFront key pair | Postgres RPC, S3, SQS, GoTrue | plaintext API keys after creation, card data (never handled: checkout is hosted by the provider) |
| GPU worker (ECS) | S3 read/write on `jobs/*`, SQS receive/delete, a backend credential for `complete_job` / `fail_job` | S3, SQS, the backend | Postgres directly, payment secrets |
| Payment providers | webhook secret (shared) | `/v1/webhooks/*` | anything else |

Everything the plugin can do, it does as one user; everything privileged happens in
the backend under keys that never leave AWS Secrets Manager (§8).

## 2. Authentication

### 2.1 JWT verification (§1)

Supabase Auth (GoTrue) issues the tokens; the backend only verifies them.

* **Algorithm pinning.** The verifier accepts exactly the algorithm the deployment is
  configured for: `HS256` when `SUPABASE_JWT_SECRET` is set, `RS256` / `ES256` when
  `SUPABASE_JWKS_URL` is set — never both, never a list taken from the token header,
  never `none`. A token whose `alg` differs is rejected before any key lookup, which
  closes the classic HS/RS confusion.
* **Required claims.** `sub` (the user id, a UUID), `exp`, and `aud == "authenticated"`
  (§1). Missing or wrong → `401 unauthorized`; expired → `401 token_expired` so the
  plugin knows to refresh rather than re-login. Clock leeway is `LEEWAY_SECONDS` = 30 s.
  `iss` is checked against the project's GoTrue URL when configured.
* **JWKS caching.** Keys are fetched once and cached in-process for
  `JWKS_CACHE_SECONDS` = 3600 s, keyed by `kid`. An unknown `kid` triggers at most one refetch per minute
  across the process (`JWKS_REFETCH_INTERVAL_SECONDS` = 60, under a lock); anything else
  with an unknown `kid` is rejected. This keeps a
  flood of forged tokens from turning the JWKS endpoint into a DoS amplifier and keeps
  verification off the network path.
* **Token handling in the plugin.** The password is never stored (§1), and no token ever
  reaches the DAW project file or the plugin's `getStateInformation` — only the last job
  id does. `AuthManager` persists the token pair through a `juce::PropertiesFile`
  (`SnapPlayAI.settings` under a `SnapPlay` folder in the OS application-data location),
  which is a plain XML file with the platform's file permissions, **not** the macOS
  Keychain or Windows DPAPI; moving it there is an open hardening item. Renewal is
  proactive rather than reactive: a 30 s timer refreshes the access token 120 s before it
  expires, so requests normally never see a `401`. `ApiClient` retries only 429 and
  5xx/transport failures (`Cloud/RetryPolicy.h`) — a `401` is surfaced to the caller,
  and `JobClient` ends the job rather than retrying it.
* **WebSocket auth (§2).** `?token=` is the *only* accepted form on `WS
  /v1/jobs/{job_id}/ws`: there is no in-band authentication frame to smuggle a token
  through, and no header path on that route. It exists for web clients; the plugin uses
  SSE with an `Authorization` header. The token, the read rate limit and job ownership
  are all checked before the handshake is accepted, so an unauthorised socket is never
  upgraded: the application closes with code `4401` and the §5 error code as the reason,
  which uvicorn surfaces to the client as an HTTP `403` on the handshake. Access logs at
  the ALB and in the application strip query strings so a token never lands in a log
  line.

### 2.2 API keys (§11)

* **Format.** `sp_live_` + 32 hex characters from a CSPRNG (`secrets.token_hex(16)` —
  128 bits of entropy; `backend/app/auth/api_keys.py` accepts `[A-Za-z0-9]{32}` on the way in).
  The plaintext is returned exactly once by `POST /v1/api-keys`; the row stores
  `sha256(key)` and the 12-character `prefix` for display.
* **Lookup.** The request key is hashed, the row is fetched by hash (unique index),
  and the stored hash is then compared with `hmac.compare_digest`. High-entropy keys do
  not need salting or slow hashing; the constant-time compare is what prevents a
  byte-by-byte timing oracle on the final equality. Revoked keys (`DELETE`) fail the
  same way as unknown ones.
* **Scope.** A key acts as its owner: same balance, same rate limits (§11), same RLS
  rows. Keys cannot create keys, cannot touch webhooks, and cannot read `/v1/auth/*`.
  `last_used_at` is recorded for revocation decisions.
* **Damage bound.** A stolen key can at most spend the owner's credits at 10 jobs per
  minute and read that owner's jobs; revocation is immediate.

## 3. Payment webhooks (§4, §12)

| provider | signature | replay bound | idempotency key |
|----------|-----------|--------------|-----------------|
| LemonSqueezy | `X-Signature` = hex HMAC-SHA256(raw body, `LEMONSQUEEZY_WEBHOOK_SECRET`) | no timestamp in the scheme — bounded by the idempotency key only | `lemonsqueezy:<event_name>:<data.id>` |
| Paddle | `Paddle-Signature: ts=…;h1=…`; HMAC-SHA256 over `"{ts}:{raw_body}"` with `PADDLE_WEBHOOK_SECRET` | reject when `abs(now − ts) > 5 min` | `paddle:<event_type>:<event_id>` |

Rules applied to both:

* The HMAC is computed over the **raw request bytes** read before any JSON parsing, and
  compared with `hmac.compare_digest`. A bad or missing signature is `401
  invalid_signature` and nothing is written.
* Delivery is **claim → apply → close**, not one transaction across the whole handler.
  The idempotency key is claimed in `webhook_events` (unique) first; a delivery that
  cannot claim it — because a previous one already applied it — answers
  `200 {"status": "duplicate"}` so the provider stops retrying. What *is* one
  transaction is the effect: `record_purchase` writes the `purchases` row, grants the
  plan's credits and — when `checkout[custom][ref]` resolves — the
  `affiliate_commissions` row, all under the same key, so a replay returns the existing
  purchase and changes nothing. `grant_credits` is separately idempotent on that key
  (§6).
* A delivery that fails halfway is marked processed **with an error**, which leaves the
  key claimable again, so the provider's retry re-runs it. A paid event is therefore
  never answered "duplicate" without having been applied — the failure mode is a repeated
  attempt, which the per-key idempotency inside the functions absorbs, rather than a lost
  payment.
* The user is resolved from `meta.custom_data.user_id` first and only then by customer
  email; an event that resolves to no user is stored and answered `200` for manual
  review, not `4xx` (which would just cause retries).
* Amounts are taken from the event, never from the request path; the plan is matched
  by the provider's product / variant id, not by a name string.
* Several `h1` values may be present during Paddle key rotation; any matching one is
  accepted, none matching is rejected.

## 4. Database posture: RLS and service-role isolation (§6)

* `0003_rls.sql` starts by revoking everything in `public` from `public`, `anon` and
  `authenticated`, then grants back only `SELECT`, and enables RLS on every table.
  Authenticated users see their own rows in `profiles`, `credit_accounts`,
  `credit_ledger`, `jobs`, `job_assets`, `api_keys`, `purchases` and `subscriptions`,
  their own affiliate rows in `affiliates` / `referral_codes` /
  `affiliate_commissions` (the last two through an `EXISTS` on `affiliates`), and active
  rows in `plans` (also for `anon`). `webhook_events` has RLS on, no policy and no grant:
  `service_role` only.
* There is **no** `INSERT` / `UPDATE` / `DELETE` policy for `authenticated` or `anon`
  anywhere, so the read grants are the whole user-facing surface.
* The `api_keys` grant is table-wide rather than column-level, so a user can read the
  `key_hash` of their **own** keys. That is a SHA-256 of a secret they already hold, so it
  leaks nothing; narrowing the grant to the displayed columns would still be tidier.
* All mutations go through the `SECURITY DEFINER` functions — `reserve_credits`,
  `settle_reservation`, `grant_credits`, `refund_job`, `expire_credits`, plus job
  creation / completion. `EXECUTE` is revoked from `public`, `anon` and
  `authenticated` and granted to `service_role` only, so the functions cannot be
  reached through PostgREST with a user JWT even though RLS is bypassed inside them.
* Each function that touches a balance takes `SELECT … FOR UPDATE` on the
  `credit_accounts` row, keeping the invariant `balance = Σ ledger.amount` (§6) and
  serialising concurrent reservations (see §9, credit races).
* The service-role key exists only in the backend task's environment (from Secrets
  Manager). The backend still filters every query by the caller's `user_id` and answers
  `404` for anything else (§2); "the key can see everything" is never relied on to mean
  "the caller can".
* If those grants are ever deployed wrong, PostgreSQL answers the backend's own
  statement with `SQLSTATE 42501` and `backend/app/services/supabase.py` turns that into
  `403 unauthorized` (contract §5) rather than a generic `500`. A `403` in production is
  therefore a deployment alarm — the migrations or the key do not match
  `db/migrations/0003_rls.sql` — never a statement about the end user's rights.
* The GPU worker has no database credential. It reports through the backend's
  `complete_job` / `fail_job`, which are authenticated with a worker credential
  distinct from user auth.

## 5. Object storage and signed URLs (§2, §10)

* The bucket blocks all public access. Objects live under
  `jobs/<user_id>/<job_id>/`; both path components are UUIDs produced by the server,
  never by the client, so no user input reaches an object key.
* Presigned URLs are `GET`-only, for one object key, and expire at `expires_at`
  (`SIGNED_URL_TTL_SECONDS`, 24 h, matching the lifecycle rule). A presigned URL never
  carries more than the signing identity has, and the URL itself names one key and one
  method, so it cannot be widened into a directory listing. The signing identity is the
  API task role, which holds `s3:GetObject`/`PutObject`/`DeleteObject` on
  `<bucket>/jobs/*` and `s3:ListBucket` only under the `jobs/` prefix — enough to write
  the input and sign reads, and nothing outside that prefix. The worker role is scoped
  identically.
* With CloudFront, the origin is reachable only through OAC and the signed URLs use a
  key pair stored in Secrets Manager (`CLOUDFRONT_KEY_PAIR_ID` names it; the private
  key is never in config). The client sees an opaque URL either way.
* `input.flac` is stored too; it is deleted by the same 24 h rule. Nothing is retained
  beyond that without the user's own action (the plugin's local copy).

## 6. Rate limiting (§5)

* 10 job submissions / minute / user and 60 reads / minute / user
  (`RATE_LIMIT_JOBS_PER_MIN`, `RATE_LIMIT_READS_PER_MIN`), keyed by the authenticated
  identity (JWT `sub` or API-key owner), not by IP, so a shared NAT does not throttle a
  studio and a key cannot escape its owner's budget. `/v1/plans` is public but consumes
  a read token when the caller happens to be authenticated.
* Responses carry `Retry-After` and `X-RateLimit-Remaining`; the code is `429
  rate_limited`.
* `/v1/auth/token` and `/v1/auth/refresh` have no principal yet, so they are bucketed at
  **10 attempts / minute per submitted credential** — the key is `sha256` of the
  normalised email or of the refresh token, so a token never sits in memory as a
  dictionary key — with a cap of `AUTH_MAX_BUCKETS` = 10,000. Eviction drops refilled
  buckets first and then the *fullest* remaining ones, so flooding the store never
  flushes the exhausted bucket of the account under attack, which is exactly what an
  attacker would want. That bounds guessing against *one* account; spraying many accounts from one IP
  is bounded by GoTrue's own lockout and by the ALB / WAF layer, not here.
* A principal may hold at most **5 concurrent SSE / WebSocket streams**
  (`MAX_CONCURRENT_STREAMS`), because a stream costs one read token to open and then
  lives for minutes.
* `/v1/webhooks/*` is **not** rate limited in the application: the signature check is the
  gate, and throttling a provider's retries would cost deliveries. Volumetric abuse there
  is an ALB / WAF concern.
* **The buckets are per process** (`app.state.rate_limits`, in memory). With *N* Fargate
  tasks behind the ALB the effective ceiling is *N* × the configured rate, and a task
  restart resets every bucket. That is acceptable at one or two tasks and stops being so
  as the service scales out: moving the buckets to a shared store (Redis or equivalent) is
  a known prerequisite for raising `api_desired_count`, not something already done.

## 7. Input validation (§2, §5)

* **Size.** `BodyLimitMiddleware` runs before the multipart parser, because starlette's
  parser enforces no total size and spools parts above 1 MB to disk — otherwise an
  unauthenticated client could make the process spool an arbitrary body on `POST /v1/jobs`
  and collect its `401` afterwards. Three gates fire before the first byte reaches the
  parser: an upload without credentials is `401`; a `Content-Length` over the route's cap
  is `413`; and the body is counted as it streams, so a missing or lying `Content-Length`
  (chunked transfer) is cut off at the same cap. `/v1/jobs` gets `MAX_UPLOAD_BYTES` plus
  8 KB of multipart head-room, every other route 1 MB. The handler then counts the audio
  part itself as defence in depth. The ingress is configured to reject oversized requests
  too, but nothing depends on it being there.
* **Type.** The container is identified by **magic bytes** — `fLaC`, `RIFF…WAVE`,
  `FORM…AIFF`, `OggS`, an ID3 tag or an MPEG frame sync — and never by the filename
  or the client's `Content-Type`. Anything else is `415`.
* **Duration.** Input longer than `MAX_INPUT_SECONDS` (60 s) is truncated to the first
  60 s **after** decoding and reported as `truncated: true`. There is no header-declared
  sample-count check before decoding, so a decompression bomb is bounded by the other
  limits rather than pre-empted: at most 10 MB reaches the decoder, decoding happens only
  in the worker, ffmpeg is capped at `FFMPEG_TIMEOUT_SECONDS` (30 s) and at
  `MAX_CHANNELS` (2), and the whole job dies at `JOB_TIMEOUT_SECONDS`. A header ceiling
  before decode would still be the cheaper gate and is an open item.
* **Decoding location.** Full decoding happens in the worker, in a process that has
  no secrets and can be killed by the `JOB_TIMEOUT_SECONDS` reaper; the API only sniffs
  and bounds.
* **`options`.** Parsed with a pydantic model that forbids unknown fields, restricts
  `stems` / `transcribe` to the four contract names, bounds `target_root_midi` and
  `client_sample_rate`, and caps `idempotency_key` at 128 characters (it is an opaque
  string scoped to `(user_id, key)`, not a validated UUID). Violations are
  `422 validation_error` with field paths, before any credit is touched.
* **Order.** Auth → validation → `reserve_credits` → persist → enqueue (§2). A
  rejected upload therefore never creates a reservation.

## 8. Secrets (§10)

| secret | lives in | reaches |
|--------|----------|---------|
| `SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL` | Secrets Manager (URL may be plain config) | backend task |
| Supabase service-role key | Secrets Manager | backend task |
| `LEMONSQUEEZY_WEBHOOK_SECRET`, `PADDLE_WEBHOOK_SECRET` | Secrets Manager | backend task |
| CloudFront private key (`CLOUDFRONT_KEY_PAIR_ID` is the public handle) | Secrets Manager | backend task |
| worker → backend credential | Secrets Manager | worker task |
| Terraform state | remote backend with encryption and locking; contains ARNs, not values | operators |
| local development | `.env` from `.env.example` (placeholders only), git-ignored | developer machine |

Secrets are injected as ECS task secrets (`valueFrom` an ARN), never baked into images,
never in Terraform variables, never in CI logs. Rotation is a Secrets Manager update
plus a task restart; the JWKS path rotates itself. Nothing logs a token, an API key, a
signature header or a request body (rule shared across all components).

## 9. Abuse cases and mitigations

| abuse | attack | mitigation | contract |
|-------|--------|------------|----------|
| **Credit race** | two `POST /v1/jobs` in flight with `available = 1`, hoping both pass the check | `reserve_credits` runs under `SELECT … FOR UPDATE` on the account row; the second call sees `reserved = 1`, raises `P0402` → `402`. Reservation is idempotent per `(job_id, 'reserve')` so a retry of the *same* job never double-reserves. | §6 |
| **Double submit / retry storm** | client retries after a timeout, hoping for a free duplicate | `idempotency_key` scoped to `(user_id, key)` returns the existing job with no second reservation | §2 |
| **Replayed webhook** | re-send a captured `order_created` to mint credits again | HMAC over the raw body; unique idempotency key in `webhook_events`; Paddle `ts` window of 5 min; grant and commission share the key in one transaction | §4, §12 |
| **Forged webhook** | craft an event for a victim's `user_id` | signature required; secret only in Secrets Manager; the user id in `custom_data` is trusted only after the signature passes | §4 |
| **Job enumeration** | walk `GET /v1/jobs/{id}` for other users' results | UUID v4 ids (122 random bits); every lookup is filtered by `user_id` and answers `404` rather than `403` so existence does not leak; 60 reads / min | §2, §5 |
| **Signed-URL sharing / scraping** | pass a stem URL around, or guess others | one object, `GET`-only, 24 h, no list permission; the key path is UUIDs; the plugin uses each URL once | §2, §10 |
| **Affiliate self-referral** | buy with one's own `ref` code, or with a second account, to claw back 30 % | `record_purchase` resolves the code only through an active `referral_codes` row joined to an active `affiliates` row `where a.user_id <> p_user_id`, so a self-referral simply writes no commission. Commissions are written `pending` and are meant to be paid only after the chargeback window, with a refund setting `void` — but the payout hold, the void-on-refund step and any velocity check on new codes are **operational procedures, not code**; nothing in this repository pays out or voids automatically. A second account with a different `user_id` is not caught at all | §12 |
| **Commission double-pay** | replay the webhook to get two commission rows | commission row keyed by the same idempotency key as the grant, in the same transaction | §12 |
| **Free-credit farming** | mass signups for 3 credits each | the grant is idempotent per user (`signup:<user id>`), and 3 credits ≈ $0.0075 of cost, so the loss per account is bounded and the GPU queue is protected by the 10/min submission limit. But the `on_auth_user_created` trigger fires on the `auth.users` insert, **before** any e-mail confirmation, and signup itself happens in GoTrue rather than in this API — so requiring confirmation before the grant, and rate-limiting signups per IP and e-mail domain, are Supabase Auth settings an operator must turn on, not something this repository enforces | §3, §5 |
| **Credential stuffing** | password guessing through `/v1/auth/token` | strict IP-keyed limit on the auth proxy, GoTrue's own lockout, no distinguishable error between wrong email and wrong password | §1 |
| **Algorithm confusion** | sign a token with the public key as an HMAC secret | single pinned algorithm per deployment; `alg` from the token is never consulted for key selection | §1 |
| **JWKS DoS** | flood with tokens carrying random `kid`s | cached keys; one refetch per minute; unknown `kid` rejected | §1 |
| **API-key theft** | leaked `sp_live_…` from CI or the growth engine | `DELETE /v1/api-keys/{id}` revokes instantly; damage capped by the owner's balance and rate limits; keys never appear in logs; the growth engine loads it from the environment only | §11 |
| **Decompression bomb / malformed audio** | tiny file declaring hours of audio, or a crafted container | magic-byte sniff and the 10 MB cap at the edge; full decode only in the worker, under a 30 s ffmpeg timeout, 2 channels and the job timeout; no pre-decode header ceiling yet (§7) | §2, §5, §10 |
| **Oversized upload** | send > 10 MB with a lying `Content-Length`, or spool a huge body and take the `401` | `BodyLimitMiddleware` runs before the multipart parser: no credentials → `401`, oversized `Content-Length` → `413`, and a streaming byte count catches a chunked body; the handler counts the audio part again | §2 |
| **Worker-death credit leak** | a crashed worker leaves a job `running` and a credit reserved forever | reaper settles jobs past `JOB_TIMEOUT_SECONDS` as failed → `release`; SQS redelivery and DLQ handle the message side; `settle_reservation` is idempotent | §6, §10 |
| **Balance tampering** | write to `credit_ledger` / `credit_accounts` through PostgREST | RLS: no write policies; functions callable by `service_role` only | §6 |
| **Token in logs** | `?token=` on the WebSocket route | query strings stripped from access logs; the socket is rejected before the upgrade (4401 close / 403 handshake) so no session exists to log; SSE (header auth) is the plugin path | §2 |
| **Growth engine over-spend** | a runaway daily batch burns the owner's credits | the engine budgets jobs per batch and stops at a configured balance floor; keys are per environment; 10 submissions / min | §5, §11 |

## 10. Logging and privacy

* Logs carry request id, route, status, user id and job id — never tokens, keys,
  signature headers, request bodies or audio.
* Audio inputs and outputs are deleted after 24 h by the bucket rule; the ledger and
  job metadata (durations, BPM, key, error codes) are retained for accounting.
* Emails live in `profiles` and the payment provider; the plugin never sees another
  user's email, and API-key rows expose only the prefix.
