# SnapPlay AI

SnapPlay AI is a VST3/AU instrument plugin that turns any short audio clip into a
playable instrument. Drop a loop, a vocal take or a sampled record into the plugin;
a GPU backend separates it into **bass / drums / synth / vocals** stems, transcribes
them to MIDI, and detects key, tempo and downbeats. The plugin then maps the stems onto
the keyboard — pitched stems become chromatic, scale-snapped instruments; drums become
a sliced kit — and lets you drag the MIDI, an FL Studio `.fsc` score, or the stems
themselves straight back into your DAW.

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
   envelope sets ADSR, drum transients become slices from C1 upward. Play it, then drag
   `.mid`, `.fsc` or the stem files out of the plugin into the DAW timeline.

Pricing is credit-based: 3 free credits at signup, then a 50-credit pack for $9 or a
60-credit monthly subscription for $7.99 (see [`docs/ECONOMICS.md`](docs/ECONOMICS.md)).

## Repository layout

| path | what lives there |
|------|------------------|
| `docs/` | `API_CONTRACT.md` (the binding contract), `ARCHITECTURE.md`, `ECONOMICS.md`, `SECURITY.md`, `GROWTH.md` |
| `plugin/` | JUCE 8 / C++20 plugin. `Source/Core` (JUCE-free DSP and music-theory primitives, unit-tested without JUCE), `Source/Cloud` (auth, API and job clients, FLAC upload encoder), `Source/Engine` (sampler, stem voices, pitch shifting, drum kit, scale lock), `Source/Export` (MIDI, `.fsc`, drag-out), `Source/UI`, `Tests/` |
| `backend/` | FastAPI service (Python 3.11): `app/routers` for the `/v1` routes, plus auth, credits, storage, dispatch and the pipeline / GPU worker entry points (`fake`, `local`, `modal`, `runpod`, `aws`) |
| `db/` | Supabase / PostgreSQL 16 migrations: tables, RLS policies and the `SECURITY DEFINER` credit functions from contract §6 |
| `infra/` | `aws/` Terraform for the production path in contract §10: ECS Fargate + ALB, SQS + DLQ, ECS GPU worker capacity, S3 (+ optional CloudFront), Secrets Manager |
| `growth/` | UGC automation engine: `mcp_server/` exposes the pipeline (source → process → script → voiceover → render → publish → measure) as MCP tools, driven through an API key |
| `.github/` | CI workflows: plugin core tests, backend tests against the fake pipeline and mocked AWS, migration checks, Terraform validation, growth-engine tests |

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

Point the plugin at a backend with the `apiBaseUrl` setting (default
`https://api.snapplay.ai`).

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

**Verified by CI (no hardware or accounts needed)**

- Plugin `Source/Core` compiles and its unit tests pass without JUCE; the full plugin
  target configures against JUCE 8.0.8.
- Backend routes are exercised end-to-end against the `fake` pipeline, with AWS
  (S3 / SQS) mocked by moto and outbound HTTP (GoTrue, payment providers) mocked by
  respx. Contract shapes, credit reservation / settlement, webhook signature and
  idempotency handling, rate limits and input validation are covered here.
- Migrations apply cleanly to PostgreSQL 16 and the credit functions' invariants are
  tested in SQL.
- `terraform validate` on `infra/aws`.
- Growth-engine tools run against mocked platform APIs.
- Every mermaid diagram in `docs/` renders.

**Needs hardware or real accounts**

- The 2.0 s pipeline budget on an A10G (`g5.xlarge`); T4-class hardware needs a
  ~5 s target instead (contract §7).
- VST3 / AU hosting, drag-out and `.fsc` import inside real DAWs on macOS and Windows.
- A Supabase project for GoTrue sign-in and RLS-backed data.
- LemonSqueezy / Paddle checkouts and live webhook delivery, including affiliate
  attribution.
- An AWS account for the Fargate / SQS / ECS GPU deployment, and the resulting
  scale-on-queue-depth behaviour.
- TikTok, Meta and YouTube app review and publishing quotas for the growth engine.
- Real-network upload / download timings; the numbers in `docs/ARCHITECTURE.md` are
  estimates.
