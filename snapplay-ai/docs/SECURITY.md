# SnapPlay AI — Security

Security posture for the components in this repository, derived from
[`API_CONTRACT.md`](API_CONTRACT.md) (cited as "§n"). The contract fixes *what* is
verified; this document fixes *how*, and lists the abuse cases the design has to
withstand.

## 1. Trust boundaries

| principal | holds | may call | must never see |
|-----------|-------|----------|----------------|
| Plugin (`plugin/Source/Cloud`) | a user's access JWT (memory) and refresh token (OS keychain) | `/v1/*` as that user | service-role key, webhook secrets, other users' jobs |
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
  plugin knows to refresh rather than re-login. Clock leeway is a few seconds, not
  minutes. `iss` is checked against the project's GoTrue URL when configured.
* **JWKS caching.** Keys are fetched once and cached in-process with a TTL of about an
  hour, keyed by `kid`. An unknown `kid` triggers at most one refetch per minute
  across the process; anything else with an unknown `kid` is rejected. This keeps a
  flood of forged tokens from turning the JWKS endpoint into a DoS amplifier and keeps
  verification off the network path.
* **Token handling in the plugin.** The access token lives in memory; the refresh
  token is stored in the OS keychain (macOS Keychain, Windows DPAPI), never in the DAW
  project file or plugin state. The password is never stored (§1). One refresh-and-
  retry per request; a second `401` surfaces to the UI.
* **WebSocket auth (§2).** The `?token=` query form exists for web clients; the plugin
  uses SSE with a header. Access logs at the ALB and application strip query strings so
  a token never lands in a log line.

### 2.2 API keys (§11)

* **Format.** `sp_live_` + 32 characters from a CSPRNG (≥ 190 bits). The plaintext is
  returned exactly once by `POST /v1/api-keys`; the row stores `sha256(key)` and the
  `prefix` for display.
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
* The idempotency key is inserted into `webhook_events` (unique) **inside the same
  transaction** as the credit grant, the `purchases` row and — when `checkout[custom]
  [ref]` resolves — the `affiliate_commissions` row. A duplicate delivery hits the
  unique constraint, rolls back, and answers `200 {"status": "duplicate"}` so the
  provider stops retrying. `grant_credits` is itself idempotent on the same key (§6),
  so even a partial retry cannot double-grant.
* The user is resolved from `meta.custom_data.user_id` first and only then by customer
  email; an event that resolves to no user is stored and answered `200` for manual
  review, not `4xx` (which would just cause retries).
* Amounts are taken from the event, never from the request path; the plan is matched
  by the provider's product / variant id, not by a name string.
* Several `h1` values may be present during Paddle key rotation; any matching one is
  accepted, none matching is rejected.

## 4. Database posture: RLS and service-role isolation (§6)

* Every table in `public` has RLS enabled. Authenticated users have `SELECT` on their
  own rows (`profiles`, `credit_accounts`, `credit_ledger`, `jobs`, `job_assets`,
  `purchases`, `subscriptions`, and `api_keys` minus the hash column). There are **no**
  `INSERT` / `UPDATE` / `DELETE` policies for `authenticated` or `anon` on any of
  these; `webhook_events`, `affiliates`, `referral_codes` and `affiliate_commissions`
  have no user-facing policy at all.
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
* The GPU worker has no database credential. It reports through the backend's
  `complete_job` / `fail_job`, which are authenticated with a worker credential
  distinct from user auth.

## 5. Object storage and signed URLs (§2, §10)

* The bucket blocks all public access. Objects live under
  `jobs/<user_id>/<job_id>/`; both path components are UUIDs produced by the server,
  never by the client, so no user input reaches an object key.
* Presigned URLs are `GET`-only, for one object key, and expire at `expires_at` (24 h,
  matching the lifecycle rule). The presigning identity is an IAM role limited to
  `s3:GetObject` on `jobs/*`; it cannot list, so a URL cannot be widened into a
  directory.
* With CloudFront, the origin is reachable only through OAC and the signed URLs use a
  key pair stored in Secrets Manager (`CLOUDFRONT_KEY_PAIR_ID` names it; the private
  key is never in config). The client sees an opaque URL either way.
* `input.flac` is stored too; it is deleted by the same 24 h rule. Nothing is retained
  beyond that without the user's own action (the plugin's local copy).

## 6. Rate limiting (§5)

* 10 job submissions / minute / user and 60 reads / minute / user, keyed by the
  authenticated identity (JWT `sub` or API-key owner), not by IP, so a shared NAT does
  not throttle a studio and a key cannot escape its owner's budget.
* Responses carry `Retry-After` and `X-RateLimit-Remaining`; the code is `429
  rate_limited`.
* Token buckets live in a store shared across Fargate tasks; a per-process limiter
  would multiply the budget by the task count.
* Unauthenticated routes get stricter, IP-keyed budgets: `/v1/auth/token` and
  `/v1/auth/refresh` (credential stuffing), `/v1/webhooks/*` (signature-check CPU),
  `/v1/plans`. The ALB / WAF layer handles volumetric abuse above that.

## 7. Input validation (§2, §5)

* **Size.** 10 MB is enforced twice: at the ALB / ingress on `Content-Length`, and in
  the handler by counting bytes as the multipart stream is read, aborting with `413`
  the moment the count passes the cap. `Content-Length` is a hint, not a limit.
* **Type.** The container is identified by **magic bytes** — `fLaC`, `RIFF…WAVE`,
  `FORM…AIFF`, `OggS`, an ID3 tag or an MPEG frame sync — and never by the filename
  or the client's `Content-Type`. Anything else is `415`.
* **Duration.** Input longer than 60 s is truncated server-side to the first 60 s and
  reported as `truncated: true`. The header-declared sample count × channels ×
  sample size is checked against a hard ceiling before decoding so a small file that
  declares hours of audio (a decompression bomb) is rejected instead of decoded.
* **Decoding location.** Full decoding happens in the worker, in a process that has
  no secrets and can be killed by the `JOB_TIMEOUT_SECONDS` reaper; the API only sniffs
  and bounds.
* **`options`.** Parsed with a pydantic model that forbids unknown fields, restricts
  `stems` / `transcribe` to the four names, bounds `target_root_midi` to 0–127 and
  `client_sample_rate` to sane values, and requires `idempotency_key` to be a UUID.
  Violations are `422 validation_error` with field paths, before any credit is touched.
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
| **Affiliate self-referral** | buy with one's own `ref` code, or with a second account, to claw back 30 % | commission is refused when the resolved affiliate's `user_id` equals the buyer's, or the affiliate's payout identity matches the buyer's email; commissions start `pending` and pay out only after the chargeback window; a refund sets `void`; velocity checks on new referral codes | §12 |
| **Commission double-pay** | replay the webhook to get two commission rows | commission row keyed by the same idempotency key as the grant, in the same transaction | §12 |
| **Free-credit farming** | mass signups for 3 credits each | email verification before the grant; signup rate limit per IP and per email domain; the grant is idempotent per user; 3 credits ≈ $0.0075 of cost so the loss is bounded, but the GPU queue is protected by the submission limit | §3, §5 |
| **Credential stuffing** | password guessing through `/v1/auth/token` | strict IP-keyed limit on the auth proxy, GoTrue's own lockout, no distinguishable error between wrong email and wrong password | §1 |
| **Algorithm confusion** | sign a token with the public key as an HMAC secret | single pinned algorithm per deployment; `alg` from the token is never consulted for key selection | §1 |
| **JWKS DoS** | flood with tokens carrying random `kid`s | cached keys; one refetch per minute; unknown `kid` rejected | §1 |
| **API-key theft** | leaked `sp_live_…` from CI or the growth engine | `DELETE /v1/api-keys/{id}` revokes instantly; damage capped by the owner's balance and rate limits; keys never appear in logs; the growth engine loads it from the environment only | §11 |
| **Decompression bomb / malformed audio** | tiny file declaring hours of audio, or a crafted container | header sample-count ceiling before decode; magic-byte sniff; full decode only in the worker under the job timeout | §2, §5, §10 |
| **Oversized upload** | send > 10 MB with a lying `Content-Length` | ALB limit plus streaming byte count in the handler → `413` | §2 |
| **Worker-death credit leak** | a crashed worker leaves a job `running` and a credit reserved forever | reaper settles jobs past `JOB_TIMEOUT_SECONDS` as failed → `release`; SQS redelivery and DLQ handle the message side; `settle_reservation` is idempotent | §6, §10 |
| **Balance tampering** | write to `credit_ledger` / `credit_accounts` through PostgREST | RLS: no write policies; functions callable by `service_role` only | §6 |
| **Token in logs** | `?token=` on the WebSocket route | query strings stripped from access logs; SSE (header auth) is the plugin path | §2 |
| **Growth engine over-spend** | a runaway daily batch burns the owner's credits | the engine budgets jobs per batch and stops at a configured balance floor; keys are per environment; 10 submissions / min | §5, §11 |

## 10. Logging and privacy

* Logs carry request id, route, status, user id and job id — never tokens, keys,
  signature headers, request bodies or audio.
* Audio inputs and outputs are deleted after 24 h by the bucket rule; the ledger and
  job metadata (durations, BPM, key, error codes) are retained for accounting.
* Emails live in `profiles` and the payment provider; the plugin never sees another
  user's email, and API-key rows expose only the prefix.
