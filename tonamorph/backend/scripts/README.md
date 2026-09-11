# Operator scripts

Tools run by hand from `backend/`, in the same virtualenv as the API
(`pip install -r requirements-dev.txt`). None of them is imported by the service. The
first two live in this directory; the other two are `python -m` entry points inside `app/`
and are listed here because they belong to the same launch checklist.

| command | proves | when |
|---|---|---|
| `python3 -m scripts.live_smoke` | a live deployment end to end: admin user → sign-in → 3 credits → job → 4 stems + MIDI → one captured credit → status/version → account deletion | after every deploy of the API and after any Supabase change (`docs/LAUNCH_CHECKLIST.md` §2.3, last step) |
| `python3 -m scripts.benchmark_modal` | the real pipeline's p50/p95 per stage and the cold start against the 2.0 s budget (contract §7) | before the beta and after any pipeline or model change (checklist day 3) |
| `python3 -m app.services.klaviyo seed --email <address>` | every §14 growth metric exists in Klaviyo, so flows can be built on them | once per Klaviyo account, before building flows |
| `python3 -m app.checks` | every paid plan has a checkout URL (`plans.provider_variant_ids` is filled in) | after the Paddle price-id `UPDATE` and as the gate of every deploy (checklist day 4) |

## `live_smoke.py`

```sh
export TONAMORPH_API_URL=https://api.<domain>
export SUPABASE_URL=https://<ref>.supabase.co
export SUPABASE_SERVICE_ROLE_KEY='<service_role key>'   # this terminal only; never printed
python3 -m scripts.live_smoke                            # real pipeline, synthetic 5 s clip
python3 -m scripts.live_smoke --audio ~/clips/loop.wav   # your own clip (WAV/FLAC/MP3/OGG/AIFF)
python3 -m scripts.live_smoke --pipeline-expect fake     # a staging API running TONAMORPH_PIPELINE=fake
python3 -m scripts.live_smoke --keep-user                # leave the account for a look in the dashboard
python3 -m scripts.live_smoke --timeout 900              # a cold GPU worker that needs longer
```

The steps, in order; each prints `PASS`, `FAIL` or `SKIP` with a one-line detail:

| step | what it proves |
|---|---|
| `health` | `GET /v1/health` is `200 {"status": "ok"}` — the URL is right before anything is created |
| `create_user` | `POST /auth/v1/admin/users` with `email_confirm: true` creates `smoke+<UTC time>@<domain>` (the API host without `api.`; `example.com` for localhost) — no e-mail is sent, and the `on_auth_user_created` trigger runs |
| `sign_in` | `POST /v1/auth/token` issues a session for that user |
| `me_fresh` | `GET /v1/me` shows `3 / 0 / 3`, plan `free`, and the `marketing_opt_in` / `referral_code` fields |
| `submit_job` | `POST /v1/jobs` answers `202` with one credit reserved |
| `job_finished` | `/events` (SSE) reaches `result` within the timeout — 60 s for `fake`, 600 s for `real`; if the stream cannot be opened (a proxy that buffers SSE) it polls `GET /v1/jobs/{id}` instead and says so in an `events_stream` line |
| `result_shape` | the result validates as the §2 `JobResult`: stems `bass, drums, other, vocals`, signed URLs, `credits_charged 1`, `balance_after 2`; with `--pipeline-expect fake` and the synthetic clip also the 5.0 s duration and at least one transcribed bass note |
| `stems_download` | every stem URL downloads a WAV |
| `midi_parses` | the MIDI URL downloads a file `mido` can parse |
| `ledger_capture` | `GET /v1/credits/ledger` holds exactly one `capture` of −1 for the job and no release or refund; `GET /v1/me` shows `2 / 0 / 2` |
| `status`, `version` | the public `GET /v1/status` and `GET /v1/version` match §14 (run even after a failure) |
| `delete_user` | `DELETE /v1/me` answers `{"status": "deleted"}`; without a session the account is removed through the GoTrue admin API instead |
| `tombstone` | `GET /v1/me` with the old token is `401` — the profile tombstone, not GoTrue, refuses it |

Exit status `0` when nothing failed, `1` otherwise, `2` when a variable is missing. The
account is deleted even when an earlier step failed, unless `--keep-user` is given; a
`delete_user` failure (for example `409` because the job is still running) names the
address so it can be removed from Authentication → Users. Tokens, the service-role key,
the password and object URLs (they carry their token in the query string) never appear
in the output. `tests/test_live_smoke.py` runs the same code against the in-process app.

## `benchmark_modal.py`

```sh
python3 -m scripts.benchmark_modal --clips ~/clips --gpu A10G --repeat 3          # inside the Modal worker image
python3 -m scripts.benchmark_modal --synthetic 5 --seconds 30 --local --pipeline fake   # plumbing check, no GPU
python3 -m scripts.benchmark_modal --clips ~/clips --json report.json --no-fail    # keep the numbers, never fail
```

Runs `app/pipeline/real.py` over a set of clips — on Modal with the production worker
image (`worker.modal_app.build_image`) or, with `--local`, in this process — and prints
p50/p95 per stage plus the cold start (container boot and model load). Exit status `1`
when the total p95 is over the budget (`--budget`, default 2.0 s; `--no-fail` disables
that). `ALLOW_UNLICENSED_SEPARATION_MODEL` is set for the benchmark only; read
`docs/ARCHITECTURE.md`, "Separation model and licence", before shipping the model it
loads. The p95 it measures is what replaces "seconds, not minutes" on the landing page.

## `python3 -m app.services.klaviyo seed --email <address>`

Needs `KLAVIYO_PRIVATE_API_KEY` in the environment or `.env`. Upserts one throwaway
profile for the address and sends one sample event per §14 metric (`Signed Up`, `Morph
Completed`, `Purchase Completed`, …), then prints `accepted N of N sample events` and
exits `1` if any was refused. Klaviyo lists a metric only after its first event, so run
this once before building the flows in `docs/GTM_PLAN.md`; the profile can be deleted in
Klaviyo afterwards.

## `python3 -m app.checks`

Reads the same settings as the API, lists the active paid plans and prints one JSON
object: `{"check": "checkout_configured", "ok": true, "unsellable_plan_ids": [], …}`.
Exit status `1` when any paid plan has no checkout URL — the state of a freshly migrated
database until `plans.provider_variant_ids` carries the Paddle price ids (`db/README.md`,
checklist §2.4). The API logs the same list at startup (error level in production); this
command is the version a deploy can gate on. From outside, the equivalent is
`curl -s "$API/v1/plans" | jq -r '.plans[] | select(.price_usd > 0) | "\(.id) \(.checkout_url // "MISSING")"'`.
