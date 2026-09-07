# SnapPlay growth engine

An MCP server (`snapplay-growth`) that turns rights-cleared audio clips into 15-second vertical
shorts and publishes them: SnapPlay API job → best stem + MIDI → scripted brief → ElevenLabs
voiceover → Remotion render (FFmpeg fallback) → Instagram / Facebook / TikTok / YouTube.

## Rights and platform constraints (read first)

* **Only audio you hold advertising rights for may be used, and `process_clip` enforces it.**
  Commercial recordings — label releases, streaming catalogue, sample packs without a sync
  licence — must not be turned into ads. Every clip carries a rights record, and a clip whose
  status is not `cleared` is refused *before* anything is uploaded or a credit is spent, with
  an error naming what is missing and how to supply it. A licensed-folder clip is cleared by
  its manifest entry (below); a Free Music Archive track by the licence the listing carries
  (CC0 / public-domain / CC BY / CC BY-SA pass, NonCommercial and NoDerivatives are dropped);
  anything else only by an explicit `license_attestation`.
* **The licence manifest.** Write one of these next to the audio — the per-file form wins when
  both exist:

  ```jsonc
  // licensed_clips/night-loop.wav.license.json
  { "title": "Night Loop",
    "license": "commissioned buy-out (advertising + derivative use)",
    "attribution": "Producer A",        // optional; becomes the caption's credit line
    "permits_advertising": true,        // optional; false blocks the clip
    "evidence": "contracts/2026-03-night-loop.pdf" }
  ```

  ```jsonc
  // licensed_clips/licences.json — keyed by file name, flat or under "clips"
  { "clips": { "night-loop.wav": { "license": "CC BY 4.0", "attribution": "A — https://…" } } }
  ```

  An entry clears a clip when it names a non-empty `license`, does not set
  `permits_advertising: false` and does not name a NonCommercial / NoDerivatives licence. The
  older `<name>.json` sidecar still counts when it names a `license`. A clip with no entry is
  listed with `rights.status: "unknown"` and is never processed.
* **The override is an affirmative act.** `process_clip(..., license_attestation={"license":
  "...", "permits_advertising": true, "authority": "contract / invoice", "attribution": "..."})`
  clears material whose paperwork the engine cannot see. All three fields are required and the
  record stores where the clearance came from. Leaving it out means refusal, never a pass.
* **TikTok:** an app that has not passed TikTok's audit can only post with `SELF_ONLY`
  visibility. The adapter posts privately and returns `status: "restricted"` with a note; it
  never pretends the post is public.
* **Instagram / TikTok** have no API-side scheduling. A future `schedule_at` is stored locally
  and `run_daily_batch` publishes it when due. Facebook (`scheduled_publish_time`) and YouTube
  (`publishAt`) schedule natively.
* **YouTube Shorts** must be vertical and ≤ 60 s; the adapter tags the title with `#Shorts`.
* **SnapPlay API:** clips are capped at 10 MB / 60 s and each job costs one credit (contract
  §2). Re-processing a known clip returns the stored content item instead of a new job.
* Publishing is idempotent per (content item, platform): a repeat call returns the stored post
  id, and a failed attempt resumes from its last checkpoint (container id, upload, …).
* **Attribution and AI disclosure are automatic.** `publish_video` composes each post from
  what the content item records: the caption you pass, the licence credit line
  (`Audio: <attribution> (<licence>)`), the AI disclosure when the render used a generated
  voice or presenter, the UTM-tagged landing link, then the hashtags. The AI-content flag is
  set where the publishing API has one — TikTok `post_info.is_aigc` (with
  `brand_organic_toggle` for own-brand promotion) and YouTube `status.containsSyntheticMedia`;
  Meta's endpoints have no such field at v21.0, so there the caption carries it and the result
  says so. The disclosure state is stored on the item, so a later publish or a scheduled post
  discloses the same thing. `docs/GROWTH.md` §2 and §6 spell out the obligations.
* **Every published link is campaign-tagged.** `utm_source` per platform, `utm_medium`,
  `utm_campaign`, `utm_content` = the content item id, plus `ref` when `GROWTH_REFERRAL_CODE`
  is set; built from `GROWTH_LANDING_URL` and stored on the item (`docs/GROWTH.md` §7).
* **The batch cannot drain the account.** Before each clip `run_daily_batch` reads
  `GET /v1/me` and stops rather than taking the balance below `GROWTH_CREDIT_FLOOR` or
  spending more than the run's `credit_budget` (or `GROWTH_CREDIT_BUDGET`). Skipped clips are
  reported with `status: "skipped"` and the reason, and the report's `credits` block shows the
  floor, budget, balances and what was spent.

## Setup

```bash
cd growth
python3 -m pip install -r requirements.txt        # or: pip install -e .[dev]
cp .env.example .env                              # fill in real values
set -a; . ./.env; set +a                          # export into the shell
cd remotion && npm install && cd ..               # optional: Remotion renderer
```

`ffmpeg` (with `libx264`, `showwaves`, `drawtext`) must be on `PATH` or named by `FFMPEG_BIN`
for the fallback renderer. Node 22 and Chromium are needed for Remotion (see
`remotion/README.md`).

## Environment variables

Credentials are read from the process environment only (pydantic-settings); nothing reads a
file for secrets. `.env.example` lists every variable:

| Variable | Purpose |
|---|---|
| `SNAPPLAY_API_URL`, `SNAPPLAY_API_KEY` | SnapPlay API base URL and `sp_live_…` key sent as `X-API-Key` |
| `GROWTH_DB_PATH`, `GROWTH_WORK_DIR` | SQLite state file and per-item working directory |
| `LICENSED_CLIPS_DIR` | Folder of licensed clips; each clip's licence comes from `<name>.license.json` or the folder's `licences.json` (see above) |
| `GROWTH_CREDIT_FLOOR`, `GROWTH_CREDIT_BUDGET` | Credits `run_daily_batch` must leave on the account, and its default per-run budget |
| `GROWTH_LANDING_URL`, `GROWTH_UTM_CAMPAIGN`, `GROWTH_UTM_MEDIUM`, `GROWTH_REFERRAL_CODE` | Campaign attribution for the link in every caption |
| `FMA_API_KEY`, `FMA_API_URL` | Free Music Archive API |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL_ID`, `ELEVENLABS_API_URL` | Text-to-speech |
| `REMOTION_DIR`, `REMOTION_BROWSER_EXECUTABLE`, `REMOTION_GL`, `REMOTION_CONCURRENCY` | Remotion project and Chromium options |
| `FFMPEG_BIN`, `FFMPEG_FONT_FILE` | Fallback renderer binary and caption font |
| `META_GRAPH_API_URL`, `META_UPLOAD_API_URL`, `META_API_VERSION`, `META_IG_USER_ID`, `META_IG_ACCESS_TOKEN`, `META_PAGE_ID`, `META_PAGE_ACCESS_TOKEN` | Instagram Reels and Facebook Page Reels |
| `TIKTOK_API_URL`, `TIKTOK_ACCESS_TOKEN` | TikTok Content Posting API (`video.publish` scope) |
| `YOUTUBE_API_URL`, `YOUTUBE_ACCESS_TOKEN` | YouTube Data API v3 OAuth token (`youtube.upload` scope) |
| `GROWTH_MAX_POSTS_PER_DAY_<PLATFORM>` | Daily caps enforced by `run_daily_batch` |

## Running the server

```bash
python -m mcp_server                       # stdio (what MCP clients spawn)
python -m mcp_server --transport http --host 127.0.0.1 --port 8765   # streamable HTTP at /mcp
```

### MCP client configuration

```json
{
  "mcpServers": {
    "snapplay-growth": {
      "command": "python3",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/snapplay-ai/growth",
      "env": {
        "SNAPPLAY_API_KEY": "sp_live_…",
        "LICENSED_CLIPS_DIR": "/path/to/licensed_clips",
        "REMOTION_DIR": "/path/to/snapplay-ai/growth/remotion",
        "ELEVENLABS_API_KEY": "…"
      }
    }
  }
}
```

For the HTTP transport point the client at `http://127.0.0.1:8765/mcp`.

## Tools

| Tool | What it does |
|---|---|
| `list_source_clips(source, limit, urls, license_attestation)` | Candidate clips from `licensed_folder` (default), `free_music_archive` or explicit `urls`, each with the licence it carries and a `rights` record |
| `process_clip(clip_path_or_url, options, license_attestation)` | Refuses a clip whose rights are not established, then multipart `POST /v1/jobs`, SSE follow with polling fallback, downloads stems + MIDI, scores stems (`scoring.py`: 0.4 density + 0.3 pitch range + 0.3 RMS) and returns a content item id, the chosen stem, its notes and the rights record |
| `write_script(clip_metadata, angle)` | Deterministic 15 s brief (hook, three timed beats, on-screen text, "3 free credits" CTA); no LLM call |
| `generate_voiceover(text, voice_id, content_item_id)` | ElevenLabs `with-timestamps` → mp3 + word timings |
| `render_video(content_item_id, scene, presenter, avatar_clip)` | Props JSON → `npx remotion render` (1080x1920, 450 frames @ 30 fps); FFmpeg `showwaves` + `drawtext` fallback |
| `publish_video(content_item_id, platforms, caption, hashtags, schedule_at)` | Platform adapters in `mcp_server/publishers/`, idempotent per platform; caption = caption + licence credit + AI disclosure + UTM link + hashtags, with the platform AI flag where the API takes one |
| `report_metrics(since_iso)` | Views / likes / CTR per post, stored on the item |
| `run_daily_batch(count, accounts, dry_run, credit_budget)` | The whole chain with daily caps and the credit guard; `dry_run=True` (default) skips publishing |

## State

`GROWTH_DB_PATH` holds one `content_items` row per clip: source, job id, chosen stem and
scores, script JSON, asset paths, the rights record the clip was cleared on, the AI-disclosure
state recorded at render time, and per-platform publish status / post ids / links /
checkpoints and metrics. Working files live under `GROWTH_WORK_DIR/<content_item_id>/`. A
database written by an earlier version is migrated in place when it is opened.

## Tests

```bash
cd growth
python3 -m pytest -q
ruff check .
```

Every external API (SnapPlay including the SSE stream and `GET /v1/me`, ElevenLabs, Meta,
TikTok, YouTube) is mocked with respx; no test reaches the network. A full run reports
**126 passed, 1 skipped** — the skip is the Remotion smoke render when Node or the Remotion
install is missing. `test_licensing.py`, `test_disclosure.py`, `test_attribution.py` and
`test_credit_guard.py` cover the four compliance guarantees above.
`tests/test_tools_schema.py` pins every tool's JSON schema against
`tests/snapshots/tools.json`, so a changed signature fails the suite instead of silently
drifting from `docs/GROWTH.md` §3.
