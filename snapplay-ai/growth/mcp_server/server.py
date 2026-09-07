"""The ``snapplay-growth`` MCP server.

Tools are thin, typed wrappers over ``pipeline``/``batch``; every credential comes from the
environment (see ``config.py``) and every call opens its own HTTP client so the server holds
no long-lived connections.
"""

from __future__ import annotations

from typing import Any, Literal

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel

from . import batch, pipeline
from .config import Platform, get_settings
from .licensing import parse_attestation
from .metrics import MetricsReport, collect_metrics
from .render import Presenter, RenderResult, Scene
from .script import ScriptBrief, write_brief
from .sources import (
    RIGHTS_NOTICE,
    FreeMusicArchiveProvider,
    LicensedFolderProvider,
    SourceClip,
    SourceKind,
    UrlListProvider,
)
from .state import Store
from .voiceover import VoiceoverResult

INSTRUCTIONS = (
    "SnapPlay growth engine. Turns rights-cleared audio clips into 15-second vertical shorts "
    "(SnapPlay stem/MIDI processing → brief → voiceover → Remotion render) and publishes them. "
    f"{RIGHTS_NOTICE} Every post carries its licence attribution, an AI disclosure when the "
    "render is synthetic, and a UTM-tagged landing link. TikTok posts from unaudited apps stay "
    "private (status 'restricted')."
)

mcp = FastMCP("snapplay-growth", instructions=INSTRUCTIONS)


class SourceListing(BaseModel):
    source: SourceKind
    notice: str
    clips: list[SourceClip]


def _http() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=300.0), follow_redirects=True)


@mcp.tool
async def list_source_clips(
    source: Literal["licensed_folder", "free_music_archive", "urls"] = "licensed_folder",
    limit: int = 10,
    urls: list[str] | None = None,
    license_attestation: dict[str, Any] | None = None,
) -> SourceListing:
    """List candidate source clips with the licence each one actually carries.

    Only audio you hold advertising rights for may be used: commercial recordings (label
    releases, streaming catalogue, sample packs without a sync licence) must NOT be used for
    advertising. No provider invents a licence. ``licensed_folder`` (default) lists files under
    LICENSED_CLIPS_DIR and reads each clip's manifest entry (``<clip>.license.json`` beside it,
    or an entry in the folder's ``licences.json``); ``free_music_archive`` queries the FMA API
    (FMA_API_KEY) and keeps only CC0 / public domain / CC BY / CC BY-SA tracks (NonCommercial
    and NoDerivatives licences are dropped); ``urls`` wraps caller-supplied URLs, whose rights
    stay "unknown" unless ``license_attestation`` is given. Each clip carries a ``rights``
    record; ``process_clip`` refuses anything whose status is not "cleared".

    Args:
        source: Which provider to query.
        limit: Maximum number of clips to return.
        urls: Explicit clip URLs (required when source="urls").
        license_attestation: Your own declaration of the rights you hold for the listed URLs —
            ``{"license": ..., "permits_advertising": true, "authority": ..., "attribution":
            ...}``. Only supply it when you actually hold those rights.
    """
    settings = get_settings()
    attestation = parse_attestation(license_attestation)
    if source == "licensed_folder":
        clips = await LicensedFolderProvider(settings.licensed_clips_dir).list_clips(limit)
    elif source == "free_music_archive":
        if not settings.fma_api_key:
            raise ValueError("FMA_API_KEY is not set")
        async with _http() as http:
            provider = FreeMusicArchiveProvider(settings.fma_api_url, settings.fma_api_key, http)
            clips = await provider.list_clips(limit)
    else:
        if not urls:
            raise ValueError("source='urls' requires at least one URL")
        clips = await UrlListProvider(urls, attestation).list_clips(limit)
    return SourceListing(source=source, notice=RIGHTS_NOTICE, clips=clips)


@mcp.tool
async def process_clip(
    clip_path_or_url: str,
    options: dict[str, Any] | None = None,
    license_attestation: dict[str, Any] | None = None,
) -> pipeline.ProcessedClip:
    """Submit a rights-cleared clip to the SnapPlay API and pick the most usable stem.

    Refuses, before spending a credit, any clip whose advertising rights are not established:
    a local file needs a manifest entry (``<clip>.license.json`` beside it or an entry in the
    folder's ``licences.json``) naming its licence, a Free Music Archive track needs the
    licence the listing carries (pass it as ``options.license``), and anything else needs
    ``license_attestation``. The refusal names what is missing and how to supply it.

    Uploads the clip (≤ 10 MB, first 60 s used) as multipart ``POST /v1/jobs`` with the
    X-API-Key from SNAPPLAY_API_KEY, follows ``GET /v1/jobs/{id}/events`` (SSE) to the result
    and falls back to polling ``GET /v1/jobs/{id}``, downloads every stem plus the MIDI file,
    and scores stems on note density, pitch range and RMS (see ``scoring.py``). Re-running on
    the same clip returns the existing content item instead of spending another credit. The
    licence and attribution are stored on the content item, and publish_video puts the credit
    line in the caption.

    Args:
        clip_path_or_url: Local audio path or http(s) URL of a rights-cleared clip.
        options: Job options per API contract §2 (``stems``, ``transcribe``, ``drum_slices``,
            ``target_root_midi``, ``client_sample_rate``) plus ``source`` (provider name to
            record, e.g. "free_music_archive"), ``license`` / ``attribution`` (as reported by
            list_source_clips) and ``force`` (true reprocesses a known clip).
        license_attestation: An explicit declaration that you hold advertising rights the
            engine cannot see — ``{"license": ..., "permits_advertising": true, "authority":
            ..., "attribution": ...}``. It overrides the manifest check, so pass it only as a
            deliberate act for material you really are licensed to use.
    """
    settings = get_settings()
    store = Store(settings.growth_db_path)
    async with _http() as http:
        return await pipeline.process_clip(
            settings, store, http, clip_path_or_url, options, license_attestation
        )


@mcp.tool
def write_script(
    clip_metadata: dict[str, Any],
    angle: Literal["speed", "bass", "sample_flip", "tutorial"],
) -> ScriptBrief:
    """Build a structured 15-second brief for the calling model to voice.

    Pure templating from the metadata (no LLM is called): a hook line, three beats with start
    and end timestamps, on-screen text per beat and the "3 free credits" CTA. Pass
    ``content_item_id`` inside ``clip_metadata`` to store the brief on that content item so
    render_video can use its on-screen text when no voiceover exists.

    Args:
        clip_metadata: Fields such as ``title``, ``chosen_stem``, ``bpm``, ``key`` (string or
            ``{"root","mode"}``), ``note_count``, ``analysis`` (a JobResult analysis block),
            and optionally ``content_item_id``.
        angle: The creative angle: speed, bass, sample_flip or tutorial.
    """
    brief = write_brief(clip_metadata, angle)
    item_id = clip_metadata.get("content_item_id")
    if isinstance(item_id, str) and item_id:
        settings = get_settings()
        Store(settings.growth_db_path).update(item_id, script=brief.model_dump())
    return brief


@mcp.tool
async def generate_voiceover(
    text: str, voice_id: str | None = None, content_item_id: str | None = None
) -> VoiceoverResult:
    """Synthesize narration with ElevenLabs and return word timings for captions.

    Calls ``POST /v1/text-to-speech/{voice_id}/with-timestamps`` (ELEVENLABS_API_KEY), writes
    the mp3 under GROWTH_WORK_DIR and reduces the character alignment to per-word timings.

    Args:
        text: The narration to voice (typically the beats of a write_script brief).
        voice_id: ElevenLabs voice id; defaults to ELEVENLABS_VOICE_ID.
        content_item_id: When given, the audio and timings are attached to that content item
            so render_video mixes the narration in and shows word-timed captions.
    """
    settings = get_settings()
    store = Store(settings.growth_db_path)
    async with _http() as http:
        return await pipeline.generate_voiceover(
            settings, store, http, text, voice_id, content_item_id
        )


@mcp.tool
async def render_video(
    content_item_id: str,
    scene: Literal["daw", "plugin_ui"] = "plugin_ui",
    presenter: Literal["waveform", "avatar_clip"] = "waveform",
    avatar_clip: str | None = None,
) -> RenderResult:
    """Render the content item's 1080x1920, 15 s, 30 fps short and return the mp4 path.

    Writes a props JSON and renders the ``SplitScreenShort`` Remotion composition
    (REMOTION_DIR) with ``npx remotion render``; when Remotion is unavailable or fails, FFmpeg
    composites a ``showwaves`` waveform with ``drawtext`` captions instead (``renderer`` in the
    result says which path ran).

    Args:
        content_item_id: Id returned by process_clip.
        scene: Top half: a stylised SnapPlay plugin UI or a DAW arrangement view.
        presenter: Bottom half: an audio-reactive waveform or a supplied avatar clip.
        avatar_clip: Path or URL of the presenter video (required for presenter="avatar_clip").
    """
    settings = get_settings()
    store = Store(settings.growth_db_path)
    return await pipeline.render_video(
        settings,
        store,
        content_item_id,
        scene=_scene(scene),
        presenter=_presenter(presenter),
        avatar_clip=avatar_clip,
    )


def _scene(value: str) -> Scene:
    return "daw" if value == "daw" else "plugin_ui"


def _presenter(value: str) -> Presenter:
    return "avatar_clip" if value == "avatar_clip" else "waveform"


@mcp.tool
async def publish_video(
    content_item_id: str,
    platforms: list[Literal["instagram", "facebook", "tiktok", "youtube"]],
    caption: str,
    hashtags: list[str],
    schedule_at: str | None = None,
) -> pipeline.PublishReport:
    """Publish the rendered short to the given platforms and return each post id.

    Adapters: Meta Graph API Reels for Instagram (resumable container → publish) and Facebook
    Pages (start → upload → finish), TikTok Content Posting API (an unaudited app can only post
    privately; the result then carries status "restricted" plus a note instead of failing) and
    YouTube Data API v3 resumable upload for Shorts. Publishing is idempotent per (content
    item, platform): a repeat call returns the stored post id and never posts twice.
    Facebook and YouTube schedule natively; Instagram and TikTok store the schedule locally
    and run_daily_batch publishes them when due.

    Every post is composed from what the content item records, not from the caller: the source
    licence's attribution line, the AI disclosure line when the render used a generated voice
    or presenter (plus the platform's AI-content flag on TikTok and YouTube — Meta's endpoints
    have no such field, so there the caption carries it), and a landing link tagged with
    utm_source (the platform), utm_medium, utm_campaign, utm_content (the content item id) and
    the referral code when GROWTH_REFERRAL_CODE is set. The final link is stored on the item.

    Args:
        content_item_id: Id returned by process_clip (must have been rendered).
        platforms: Target platforms.
        caption: Post caption / description.
        hashtags: Hashtags appended to the caption (with or without '#').
        schedule_at: Optional RFC 3339 UTC time to publish at instead of now.
    """
    settings = get_settings()
    store = Store(settings.growth_db_path)
    targets: list[Platform] = list(platforms)
    async with _http() as http:
        return await pipeline.publish_video(
            settings, store, http, content_item_id, targets, caption, hashtags, schedule_at
        )


@mcp.tool
async def report_metrics(since_iso: str) -> MetricsReport:
    """Fetch views, likes and CTR for every post published since ``since_iso`` and store them.

    Instagram and Facebook use Graph API insights, TikTok ``/v2/video/query/`` and YouTube
    ``videos.list(part=statistics)``. ``ctr`` is views/impressions where the platform reports
    impressions (``ctr_kind="click"``) and otherwise (likes+comments+shares)/views
    (``ctr_kind="engagement"``).

    Args:
        since_iso: RFC 3339 timestamp; posts published before it are skipped.
    """
    settings = get_settings()
    store = Store(settings.growth_db_path)
    async with _http() as http:
        return await collect_metrics(store, settings, http, since_iso)


@mcp.tool
async def run_daily_batch(
    count: int = 3,
    accounts: list[str] | None = None,
    dry_run: bool = True,
    credit_budget: int | None = None,
) -> batch.BatchReport:
    """Run the whole chain for ``count`` unprocessed clips from the licensed folder.

    For each clip: process_clip → write_script (angles rotate) → generate_voiceover (when
    ELEVENLABS_API_KEY is set) → render_video → publish_video, honouring per-platform daily
    caps (GROWTH_MAX_POSTS_PER_DAY_*) and first publishing locally scheduled posts that are
    due. ``dry_run`` performs everything except publishing. Clips with no established licence
    are never processed and are listed in the report's notes.

    Spending is bounded: before every clip the account balance is read from ``GET /v1/me`` and
    the run stops rather than taking the balance below GROWTH_CREDIT_FLOOR or spending more
    than the run's credit budget. Skipped clips appear in ``items`` with status "skipped" and
    the reason, and ``credits`` reports the floor, budget, balances and what was spent.

    Args:
        count: Number of new clips to process.
        accounts: Platforms to publish to (instagram, facebook, tiktok, youtube); defaults to
            every platform with credentials configured.
        dry_run: When true (default) nothing is published.
        credit_budget: Maximum credits this run may spend; defaults to GROWTH_CREDIT_BUDGET,
            and without either the run is bounded by ``count`` and the balance floor.
    """
    settings = get_settings()
    store = Store(settings.growth_db_path)
    async with _http() as http:
        return await batch.run_daily_batch(
            settings,
            store,
            http,
            count=count,
            accounts=accounts,
            dry_run=dry_run,
            credit_budget=credit_budget,
        )


__all__ = ["mcp"]
