# SnapPlay growth engine

An MCP server (`snapplay-growth`) that turns rights-cleared audio clips into 15-second vertical
shorts and publishes them: SnapPlay API job → best stem + MIDI → scripted brief → ElevenLabs
voiceover → Remotion render (FFmpeg fallback) → Instagram / Facebook / TikTok / YouTube.

## Rights and platform constraints (read first)

* **Only audio you hold advertising rights for may be used.** Commercial recordings — label
  releases, streaming catalogue, sample packs without a sync licence — must not be turned into
  ads. The default source is a local folder of licensed clips; the Free Music Archive provider
  keeps only CC0 / public-domain / CC BY / CC BY-SA tracks and drops NonCommercial and
  NoDerivatives licences; the URL provider records that the caller asserted the rights.
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
* **Attribution and AI disclosure are yours to add.** `list_source_clips` reports each clip's
  `license` and `attribution`, but `write_script` does not put them in the caption — what
  `publish_video` posts is `hook + cta_line` plus the brief's hashtags. Nothing sets a
  platform AI-generated flag either, although `run_daily_batch` voices every item when
  `ELEVENLABS_API_KEY` is present. Pass the credit line in `caption` and set the disclosure
  in each platform's own composer. `docs/GROWTH.md` §2 and §6 spell out the obligations.
* **There is no credit budget.** `run_daily_batch` spends one credit per new clip until it
  runs out of unprocessed clips in `LICENSED_CLIPS_DIR` or the API answers `402`. Bound it
  with `count` and by topping the engine account up deliberately.

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
| `LICENSED_CLIPS_DIR` | Folder of licensed clips (`<name>.json` sidecars may add `title`, `license`, `attribution`) |
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
| `list_source_clips(source, limit, urls)` | Candidate clips from `licensed_folder` (default), `free_music_archive` or explicit `urls` |
| `process_clip(clip_path_or_url, options)` | Multipart `POST /v1/jobs`, SSE follow with polling fallback, downloads stems + MIDI, scores stems (`scoring.py`: 0.4 density + 0.3 pitch range + 0.3 RMS) and returns a content item id, the chosen stem and its notes |
| `write_script(clip_metadata, angle)` | Deterministic 15 s brief (hook, three timed beats, on-screen text, "3 free credits" CTA); no LLM call |
| `generate_voiceover(text, voice_id, content_item_id)` | ElevenLabs `with-timestamps` → mp3 + word timings |
| `render_video(content_item_id, scene, presenter, avatar_clip)` | Props JSON → `npx remotion render` (1080x1920, 450 frames @ 30 fps); FFmpeg `showwaves` + `drawtext` fallback |
| `publish_video(content_item_id, platforms, caption, hashtags, schedule_at)` | Platform adapters in `mcp_server/publishers/`, idempotent per platform |
| `report_metrics(since_iso)` | Views / likes / CTR per post, stored on the item |
| `run_daily_batch(count, accounts, dry_run)` | The whole chain with daily caps; `dry_run=True` (default) skips publishing |

## State

`GROWTH_DB_PATH` holds one `content_items` row per clip: source, job id, chosen stem and
scores, script JSON, asset paths, per-platform publish status / post ids / checkpoints and
metrics. Working files live under `GROWTH_WORK_DIR/<content_item_id>/`.

## Tests

```bash
cd growth
python3 -m pytest -q
ruff check .
```

Every external API (SnapPlay including the SSE stream, ElevenLabs, Meta, TikTok, YouTube) is
mocked with respx; no test reaches the network. A full run reports **81 passed, 1 skipped** —
the skip is the Remotion smoke render when Node or the Remotion install is missing.
`tests/test_tools_schema.py` pins every tool's JSON schema against
`tests/snapshots/tools.json`, so a changed signature fails the suite instead of silently
drifting from `docs/GROWTH.md` §3.
