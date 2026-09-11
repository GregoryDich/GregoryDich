# Tonamorph

Tonamorph is a VST3/AU instrument plugin that turns any short audio clip into a
playable instrument. Drop a loop, a vocal take or a sampled record into the plugin;
a GPU backend separates it into **bass / drums / synth / vocals** stems, transcribes
them to MIDI, and detects key, tempo and downbeats. The plugin then maps the stems onto
the keyboard — pitched stems become chromatic, scale-snapped instruments; drums become
a sliced kit — and lets you drag the MIDI or an FL Studio `.fsc` score straight back
into your DAW.

The product is a hybrid: everything that must feel instant (playing, scale snapping,
envelopes, drag-out, export) runs locally in the plugin; everything that needs a GPU
(source separation, transcription, analysis) runs in the cloud and is metered in
credits. The binding interface between the two halves is
[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md).

## The two-click workflow

1. **Drop.** Drag a clip (up to 10 MB / 60 s; longer input is truncated to the first
   60 s) onto the plugin. It is encoded to FLAC in the background, uploaded, and the
   job's progress streams back over Server-Sent Events. One credit is reserved for the
   job and only charged when the job succeeds.
2. **Play.** Within a couple of seconds of server time (plus your upload and download),
   the stems land on the keyboard: the detected key sets Scale-Snap, the analysed
   envelope sets ADSR, drum transients become slices from note 36 upward. Play it, then
   drag `.mid` or `.fsc` out of the plugin into the DAW timeline (the stem WAVs are kept
   in a local cache, not offered as a drag).

Pricing is credit-based: 3 free credits at signup, then a 50-credit pack for $9 or a
60-credit monthly subscription for $7.99 (see [`docs/ECONOMICS.md`](docs/ECONOMICS.md)).

## Repository layout

| path | what lives there |
|------|------------------|
| `docs/` | `API_CONTRACT.md` (the binding contract), `ARCHITECTURE.md`, `ECONOMICS.md`, `SECURITY.md`, `GROWTH.md` |
| `plugin/` | JUCE 8 / C++20 plugin. `plugin/Source/Core` (JUCE-free DSP and music-theory primitives, unit-tested without JUCE), `plugin/Source/Cloud` (auth, API and job clients, FLAC upload encoder), `plugin/Source/Engine` (sampler, stem voices, pitch shifting, drum kit, scale lock), `plugin/Source/Export` (MIDI, `.fsc`, drag-out), `plugin/Source/UI`, `plugin/Tests/` |
| `backend/` | FastAPI service (Python 3.11): `backend/app/routers` for the `/v1` routes, plus auth, credits, storage, dispatch and the pipeline / GPU worker entry points (`fake`, `local`, `modal`, `runpod`, `aws`) |
| `db/` | Supabase / PostgreSQL 16 migrations: tables, RLS policies and the `SECURITY DEFINER` credit functions from contract §6 |
| `infra/` | `aws/` Terraform for the production path in contract §10: ECS Fargate + ALB, SQS + DLQ, ECS GPU worker capacity, S3 (+ optional CloudFront), Secrets Manager |
| `growth/` | UGC automation engine: `mcp_server/` exposes the pipeline (source → process → script → voiceover → render → publish → measure) as MCP tools, driven through an API key |
| `web/` | Next.js 15 website and account portal: landing, pricing, download, sign-up / confirm / reset flows against Supabase Auth, `/account` (balance, checkout links, jobs, API keys, deletion), a Paddle.js checkout page and the `/legal/*` pages rendered from `legal/` |
| `legal/` | Terms, Privacy, Refund, Copyright, Cookie policy and the plugin EULA as lawyer-ready drafts with `[[PLACEHOLDER]]` tokens and `LAWYER-REVIEW` markers; `LICENSE` and `THIRD_PARTY_LICENSES.md` sit next to it at the project root |
| `plugin/packaging/` | Signed installers: macOS `.pkg` (codesign, auval, notarytool, stapler) and Windows Inno Setup, driven by `product.env` and `../.github/workflows/release.yml` |
| `backend/scripts/` | `benchmark_modal.py`: runs the real GPU pipeline in the production worker image on Modal (or locally) and reports p50/p95 per stage against the 2.0 s budget |

`tonamorph/` is one project inside this repository, so the CI workflows live at the
**repository root**, one level up: `../.github/workflows/` holds `plugin.yml` (build +
`ctest` on Linux, macOS and Windows), `backend.yml` (ruff + pytest against the fake
pipeline and moto), `db.yml` (`db/tests/run_tests.sh` on PostgreSQL 16), `growth.yml`
(pytest with every platform API mocked), `web.yml` (eslint, tsc, vitest, `next build`),
`infra.yml` (`terraform validate`, compose config, hadolint), `release.yml` (tag-driven
signed installers and a draft GitHub Release) and `deploy.yml` (image build/push,
`terraform plan`, a gated `terraform apply`, then `python -m app.checks` as a one-off task).
`docs/LAUNCH_CHECKLIST.md` is the founder's runbook for every account, secret and decision
the launch needs; `docs/BETA_TEST_PLAN.md` the DAW acceptance table and beta protocol.

## Quickstart

Each component has its own toolchain; none of them require the others to be running
except where noted.

### Plugin (`plugin/`)

Requires CMake ≥ 3.22, a C++20 compiler and JUCE 8.0.8 (a local checkout via
`-DJUCE_SOURCE_DIR`, otherwise fetched from GitHub). Rubber Band is picked up through
`pkg-config` when present and enables high-quality pitch shifting.

```sh
cmake -S plugin -B build/plugin -DCMAKE_BUILD_TYPE=Release \
      -DJUCE_SOURCE_DIR=/path/to/JUCE          # optional
cmake --build build/plugin -j2
ctest --test-dir build/plugin                  # JUCE-free Core tests
```

The base URL defaults to `https://api.tonamorph.com`; point the plugin somewhere else with
`tonamorph::cloud::ApiClient::setBaseUrl()`. Build options, the test and pluginval
commands, install paths per OS and a tour of the window are in
[`plugin/README.md`](plugin/README.md).

### Backend (`backend/`)

Python 3.11. The default pipeline for development is `fake` — a deterministic CPU stub
that produces contract-shaped results without a GPU.

```sh
cd backend
python3.11 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                           # fill in Supabase / storage settings
TONAMORPH_PIPELINE=fake uvicorn app.main:app --reload
pytest
```

`TONAMORPH_PIPELINE=local` runs the real Demucs / Basic Pitch stack in-process and
needs the GPU extras; `aws`, `modal` and `runpod` select the remote worker paths.

### Database (`db/`)

Apply the migrations in order to a Supabase project (`supabase db push`) or to a local
PostgreSQL 16 (`psql -f` in filename order). The credit functions are only callable with
the service-role key; direct writes to `credit_ledger` are blocked by RLS.

> ### Before you ship: fill in `plans.provider_variant_ids`
>
> `db/migrations/0001_schema.sql` seeds the three plans with a `checkout_url_template`
> but leaves `provider_variant_ids` at its default `'{}'`. `build_checkout_url()` returns
> `None` when the template needs a `{variant_id}` it does not have, so **`GET /v1/plans`
> answers `"checkout_url": null` for every plan**, and `PaywallPrompt` skips plans
> without a checkout URL — the in-plugin paywall opens with no buttons and the fallback
> line "Visit tonamorph.com to add more."
>
> **Nothing fails loudly.** No error, no log line, no failing test: the seed is valid,
> the API is healthy, the plugin is behaving as written. It simply cannot be paid.
>
> After applying the migrations, run something like
>
> ```sql
> update public.plans
>    set provider_variant_ids = '{"lemonsqueezy": "<variant id>"}'::jsonb
>  where id in ('pack_50', 'sub_monthly');
> ```
>
> and check with `curl -s $API/v1/plans | jq '.plans[].checkout_url'` that no purchasable
> plan is `null`. Make that curl part of the deployment checklist — it is the only signal
> you get. Details in [`db/README.md`](db/README.md).

### Infrastructure (`infra/aws/`)

```sh
cd infra/aws
terraform init && terraform validate
terraform plan -var gpu_instance_type=g5.xlarge
```

`terraform apply` needs a real AWS account; see `docs/ARCHITECTURE.md` for the topology
and `docs/ECONOMICS.md` before choosing the instance type.

### Growth engine (`growth/`)

```sh
cd growth
pip install -e ".[dev]"
TONAMORPH_API_KEY=tm_live_... python -m mcp_server   # exposes the MCP tools
pytest                                              # platform APIs are mocked
```

Create the API key with `POST /v1/api-keys` (contract §11). Read
[`docs/GROWTH.md`](docs/GROWTH.md) — in particular the rights section — before pointing
the engine at any audio source.

## Status

Every component is implemented. What follows separates what is actually *tested here*
from what needs hardware, an account or a DAW and is therefore **unverified**. The counts
are what the suites printed on this tree at the time of writing, not estimates — re-run
the commands rather than trusting the numbers after the code moves.

### Verified offline — no hardware, no accounts

| suite | command | result |
|-------|---------|--------|
| Plugin core (JUCE-free) | `ctest --test-dir build` | **34 passed, 0 failed** — Scale-Snap and its tie-breaking, envelope/ADSR derivation, transient detection, zero-crossing trimming, the SMF writer, the `.fsc` writer, one combined export fixture |
| Export round-trip | `TONAMORPH_TEST_OUT=… ./tonamorph_core_tests && python3 plugin/Tests/roundtrip.py …` | `.mid` re-read with **mido** (SMF type 1, PPQ 480, tempo + 4/4 meta, per-track channels, note ordering) and `.fsc` re-read byte for byte and cross-checked against **PyFLP 2.2.1**'s own event ids, `FileFormat.Score`, PPQ table and 24-byte note struct: **7 notes over 2 tracks, 7 note records** |
| Backend | `cd backend && python3 -m pytest -q` | **341 passed, 2 skipped** — routes (including sign-up / recover / resend / logout against an in-memory GoTrue, job and key lists, account export and deletion, maintenance mode, unconfigured-provider webhooks), pipeline (with the separation-model licence gate), workers (visibility claim before model load, entrypoint), AWS paths, observability and the benchmark script. The two skips are `backend/tests/pipeline/test_pipeline_real.py` (GPU extras) and `backend/tests/pipeline/test_worker_serverless.py` (`modal` not installed) |
| AWS paths | part of the above (`backend/tests/aws`) | **50 tests** against S3, SQS and the reaper mocked by **moto** |
| Database | `bash db/tests/run_tests.sh` | **10 test groups pass** on a throwaway PostgreSQL 16 cluster — account deletion (tombstone keeps the ledger consistent), affiliates, api_keys, jobs, ledger, RLS, sign-up metadata, webhooks, plus two real two-session races: one for the last credit and one for a stale webhook claim (one winner each) |
| Growth engine | `cd growth && python3 -m pytest -q` | **126 passed, 1 skipped** — every platform API mocked with respx; covers the licence gate, AI disclosure, campaign attribution and the credit guard; the skip is the Remotion smoke render when Node/Remotion is absent |
| Live API smoke test | uvicorn + a real HTTP/SSE/WebSocket client | **14/14 checks** — `/health` and `/v1/health`, anonymous `/v1/plans`, first-touch registration with the 3-credit grant, a full `POST /v1/jobs` → SSE `progress` events → `result` round trip returning four stems and a real MIDI file, credit reserve → capture in the ledger, `POST /v1/api-keys` and the key acting as its owner, and the WebSocket accepting `?token=` while rejecting its absence |
| Website | `cd web && npm run lint && npm run typecheck && npm test && npm run build` | **eslint clean, tsc clean, 15 vitest tests, production build of 27 routes** with every legal page pre-rendered and no placeholder left; the brand string lives in one file (checked by `web.yml`) |
| Legal pack | the greps in `legal/README.md` | only the 11 allowed placeholder tokens, no product name, **37 lawyer-review markers** indexed in the README |
| Packaging | `pytest plugin/packaging/common`, `shellcheck`, `actionlint`, `DRY_RUN=1` traces | **8 converter tests**, clean shellcheck and actionlint, every script prints its intended command line on Linux |
| Docs | `@mermaid-js/mermaid-cli` over every fenced block | **9/9 mermaid diagrams render** |

`terraform fmt -check -recursive`, `terraform init -backend=false` and `terraform validate`
were run on `infra/aws` with Terraform 1.9.8 and the pinned AWS provider 5.100.0 served
from a local filesystem mirror (the registry is unreachable from this environment);
`deploy.yml` runs `terraform plan`, applies, then runs `python -m app.checks` in the
production environment. The committed `.terraform.lock.hcl` records only the
`linux_amd64` provider hash. The GPU worker image (`infra/Dockerfile.worker`) could not
be built here (no Docker daemon, no CUDA base image); its pins were checked against
PyPI and hadolint, not built.

### Unverified — needs hardware, an account, or a DAW

* **The 2.0 s pipeline budget.** There is no GPU here. The budget in contract §7 is a
  design target for an A10G (`g5.xlarge`); it has never been measured —
  `backend/scripts/benchmark_modal.py` is written for exactly that and has only run
  against the fake pipeline. On a T4
  (`g4dn.xlarge`) separation alone is 3–5 s, so that deployment must advertise ~5 s.
  The `fake` pipeline the tests use is a deterministic CPU stub — it proves the contract
  shapes and the job flow, and says nothing about latency.
* **A live Supabase project.** GoTrue sign-in, PostgREST, Storage and RLS-as-deployed are
  exercised against the in-memory backend and against a local PostgreSQL 16 cluster, never
  against a real project.
* **Real payment webhooks.** LemonSqueezy and Paddle signatures, idempotency and affiliate
  attribution are tested against synthetic payloads we sign ourselves. No live checkout
  has been completed and no provider has ever delivered to this code — so which events a
  real store actually sends, and what `custom_data` it forwards onto each of them, is
  assumed rather than observed (see the residual risks below).
* **Signing and notarization.** `plugin/packaging` and `release.yml` are verified up to
  the point where `codesign`, `notarytool`, `signtool` and Inno Setup would run; the first
  tag build on the macOS and Windows runners is the real test.
* **Account deletion against real GoTrue.** `DELETE /v1/me` and the `auth.users` delete
  trigger are proven on the local cluster and the in-memory backend only.
* **Loading the plugin in a DAW.** No VST3 or AU has been opened in FL Studio, Ableton
  Live, Logic or any other host. CI builds the binaries; nothing hosts them. pluginval is
  documented in [`plugin/README.md`](plugin/README.md) but is not part of CI.
* **`.fsc` import into FL Studio.** The writer is verified against PyFLP's reverse-
  engineered structures, which is not the same as FL Studio opening the file. `.mid`
  remains the guaranteed interchange path (contract §9).
* **Social publishing.** Every TikTok / Meta / YouTube call is mocked. Real posting needs
  app review and audits (see `docs/GROWTH.md` §5). The AI-disclosure flags are set
  (`growth/mcp_server/publishers/tiktok.py` `brand_organic_toggle` / `is_aigc`,
  `youtube.py` `containsSyntheticMedia`) but no live platform has ever accepted them.
* **The AWS deployment itself.** No account, so no ECS, ALB, SQS or GPU capacity provider
  has ever been created, and the scale-on-queue-depth behaviour is unobserved.
* **Real-network timings.** The upload/download figures in `docs/ARCHITECTURE.md` §5 are
  arithmetic on assumed bandwidths.

### Open launch blocker: the separation model is not licensed for commercial use

The default separation model, Demucs `htdemucs` (also `htdemucs_ft`, `htdemucs_6s`),
has MIT *code* but weights Meta publishes for research only, trained on a
non-commercial dataset. A production worker therefore refuses to start with it
(`SEPARATION_MODEL` gate in `backend/app/pipeline/separation.py`;
`ALLOW_UNLICENSED_SEPARATION_MODEL=1` is for internal testing only). Three ways out,
detailed in `docs/ARCHITECTURE.md` ("Separation model and licence"):

1. a licence grant from Meta for the htdemucs weights;
2. a commercially licensed RoFormer checkpoint (Mel-Band RoFormer, reportedly MIT —
   verify the exact checkpoint and archive its model card);
3. a commercial separation API, which turns the GPU line into a per-call price
   (`docs/ECONOMICS.md` §3.4).

None of the three is implemented; the table in `separation.py` is the extension point.

### Known residual risks (recorded, not fixed)

* **Storage purge on account deletion is immediate only on the memory backend.** The
  Supabase and S3 storage services do not implement `delete_prefix` yet, so a deleted
  user's audio objects wait for the 24 h lifecycle rule (contract §1, SECURITY.md §10).
* **Rate limits are per process.** With several API tasks the effective ceiling is N× the
  configured rate and a restart resets every bucket (SECURITY.md §6).
* **The LemonSqueezy subscription path assumes the store forwards checkout custom data.**
  The affiliate `ref` is read from the paying event (`subscription_payment_success`); a
  store configured not to carry the checkout's `custom_data` onto that event would drop
  the commission for that sale, silently. Verify it on the first live subscription.
* **Refunds and affiliate payouts are manual.** No webhook path reverses credits or sets
  a commission to `void`; `commission_status` has the states but nothing writes them.

### One deployment trap worth repeating

`plans.provider_variant_ids` is empty in the seed, so `checkout_url` comes back `null`
and the in-plugin paywall ships with no working buttons until an operator fills those ids
in. Nothing fails loudly at request time; `python -m app.checks` does, and `deploy.yml`
now runs it after every apply. See the boxed note under [Database](#database-db) above
and [`db/README.md`](db/README.md).
