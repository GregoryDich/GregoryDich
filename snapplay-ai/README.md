# SnapPlay AI

SnapPlay AI is a VST3/AU instrument plugin that turns any short audio clip into a
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

`snapplay-ai/` is one project inside this repository, so the CI workflows live at the
**repository root**, one level up: `../.github/workflows/` holds `plugin.yml` (build +
`ctest` on Linux, macOS and Windows), `backend.yml` (ruff + pytest against the fake
pipeline and moto), `db.yml` (`db/tests/run_tests.sh` on PostgreSQL 16), `growth.yml`
(pytest with every platform API mocked) and `deploy.yml` (image build/push, then
`terraform plan` and a gated `terraform apply`).

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

The base URL defaults to `https://api.snapplay.ai`; point the plugin somewhere else with
`snapplay::cloud::ApiClient::setBaseUrl()`. Build options, the test and pluginval
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
SNAPPLAY_PIPELINE=fake uvicorn app.main:app --reload
pytest
```

`SNAPPLAY_PIPELINE=local` runs the real Demucs / Basic Pitch stack in-process and
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
> line "Visit snapplay.ai to add more."
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
SNAPPLAY_API_KEY=sp_live_... python -m mcp_server   # exposes the MCP tools
pytest                                              # platform APIs are mocked
```

Create the API key with `POST /v1/api-keys` (contract §11). Read
[`docs/GROWTH.md`](docs/GROWTH.md) — in particular the rights section — before pointing
the engine at any audio source.

## Status

Every component is implemented. What follows separates what is actually *tested here*
from what needs hardware, an account or a DAW and is therefore **unverified**. The counts
are the numbers the suites print on this repository, not estimates.

### Verified offline — no hardware, no accounts

| suite | command | result |
|-------|---------|--------|
| Plugin core (JUCE-free) | `ctest --test-dir build` | **34 passed, 0 failed** — Scale-Snap and its tie-breaking, envelope/ADSR derivation, transient detection, zero-crossing trimming, the SMF writer, the `.fsc` writer, one combined export fixture |
| Export round-trip | `SNAPPLAY_TEST_OUT=… ./snapplay_core_tests && python3 plugin/Tests/roundtrip.py …` | `.mid` re-read with **mido** (SMF type 1, PPQ 480, tempo + 4/4 meta, per-track channels, note ordering) and `.fsc` re-read byte for byte and cross-checked against **PyFLP 2.2.1**'s own event ids, `FileFormat.Score`, PPQ table and 24-byte note struct: **7 notes over 2 tracks, 7 note records** |
| Backend | `cd backend && python3 -m pytest -q` | **207 passed, 2 skipped** (209 collected: 99 API/route, 46 pipeline, 50 AWS, 14 top-level). Skips are the GPU extras and `modal`, neither installed |
| AWS paths | part of the above (`backend/tests/aws`) | **50 tests** against S3, SQS and the reaper mocked by **moto** |
| Database | `bash db/tests/run_tests.sh` | **6 test groups pass** on a throwaway PostgreSQL 16 cluster — affiliates, api_keys, jobs, ledger, RLS, plus a real two-session race for the last credit (one winner, one `insufficient_credits`) |
| Growth engine | `cd growth && python3 -m pytest -q` | **81 passed, 1 skipped** — every platform API mocked with respx; the skip is the Remotion smoke render when Node/Remotion is absent |
| Live API smoke test | uvicorn + a real HTTP/SSE/WebSocket client | **14/14 checks** — `/health` and `/v1/health`, anonymous `/v1/plans`, first-touch registration with the 3-credit grant, a full `POST /v1/jobs` → SSE `progress` events → `result` round trip returning four stems and a real MIDI file, credit reserve → capture in the ledger, `POST /v1/api-keys` and the key acting as its owner, and the WebSocket accepting `?token=` while rejecting its absence |
| Docs | `@mermaid-js/mermaid-cli` over every fenced block | **9/9 mermaid diagrams render** |

`terraform validate` on `infra/aws` is the documented check for the Terraform, and
`deploy.yml` runs `terraform plan`, but **no Terraform binary is installed in this
environment**, so neither was executed for this pass. The committed
`.terraform.lock.hcl` records only the `linux_amd64` provider hash.

### Unverified — needs hardware, an account, or a DAW

* **The 2.0 s pipeline budget.** There is no GPU here. The budget in contract §7 is a
  design target for an A10G (`g5.xlarge`); it has never been measured. On a T4
  (`g4dn.xlarge`) separation alone is 3–5 s, so that deployment must advertise ~5 s.
  The `fake` pipeline the tests use is a deterministic CPU stub — it proves the contract
  shapes and the job flow, and says nothing about latency.
* **A live Supabase project.** GoTrue sign-in, PostgREST, Storage and RLS-as-deployed are
  exercised against the in-memory backend and against a local PostgreSQL 16 cluster, never
  against a real project.
* **Real payment webhooks.** LemonSqueezy and Paddle signatures, idempotency and affiliate
  attribution are tested against synthetic payloads we sign ourselves. No live checkout
  has been completed and no provider has ever delivered to this code.
* **Loading the plugin in a DAW.** No VST3 or AU has been opened in FL Studio, Ableton
  Live, Logic or any other host. CI builds the binaries; nothing hosts them. pluginval is
  documented in [`plugin/README.md`](plugin/README.md) but is not part of CI.
* **`.fsc` import into FL Studio.** The writer is verified against PyFLP's reverse-
  engineered structures, which is not the same as FL Studio opening the file. `.mid`
  remains the guaranteed interchange path (contract §9).
* **Social publishing.** Every TikTok / Meta / YouTube call is mocked. Real posting needs
  app review and audits (see `docs/GROWTH.md` §5), and the AI-disclosure flags described
  there are not implemented yet.
* **The AWS deployment itself.** No account, so no ECS, ALB, SQS or GPU capacity provider
  has ever been created, and the scale-on-queue-depth behaviour is unobserved.
* **Real-network timings.** The upload/download figures in `docs/ARCHITECTURE.md` §5 are
  arithmetic on assumed bandwidths.

### One deployment trap worth repeating

`plans.provider_variant_ids` is empty in the seed, so `checkout_url` comes back `null`
and the in-plugin paywall ships with no working buttons until an operator fills those ids
in. Nothing fails loudly. See the boxed note under [Database](#database-db) above and
[`db/README.md`](db/README.md).
