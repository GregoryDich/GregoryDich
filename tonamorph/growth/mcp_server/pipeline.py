"""The pipeline steps behind the MCP tools; ``run_daily_batch`` chains the same functions."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .attribution import build_landing_url
from .config import PLATFORMS, Platform, Settings
from .disclosure import Disclosure, disclosure_for, stored_disclosure
from .licensing import (
    LicenseAttestation,
    RightsRecord,
    attribution_line,
    parse_attestation,
    require_cleared,
    resolve_rights,
)
from .publishers import PublisherError, PublisherNotConfigured, PublishRequest, build_publisher
from .render import Presenter, RenderResult, Scene, render_item
from .scoring import StemScore, choose_stem, score_stems
from .tonamorph import Analysis, JobOptions, MidiNote, TonamorphClient
from .sources import probe_duration
from .state import ContentItem, PublishRecord, Store, parse_iso, utc_now_iso
from .voiceover import VoiceoverResult, synthesize

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_STEM_MIME = {"wav": "audio/wav", "flac": "audio/flac", "mp3": "audio/mpeg"}


class ProcessedClip(BaseModel):
    content_item_id: str
    job_id: str
    source: str
    source_ref: str
    chosen_stem: str
    chosen_stem_path: str
    midi_path: str
    stem_scores: list[StemScore]
    midi_notes: list[MidiNote]
    analysis: Analysis
    rights: RightsRecord = Field(description="The licence this clip was cleared for advertising on")
    reused: bool = Field(description="True when an earlier run of the same clip was returned")


class PlatformPublishResult(BaseModel):
    platform: Platform
    status: str
    post_id: str | None = None
    url: str | None = None
    note: str | None = None
    error: str | None = None
    already_posted: bool = False
    link: str | None = Field(default=None, description="UTM-tagged landing URL in the caption")
    disclosure_line: str | None = None
    ai_flag_set: bool = False


class PublishReport(BaseModel):
    content_item_id: str
    results: list[PlatformPublishResult]
    attribution_line: str | None = None
    disclosure_line: str | None = None


def _is_url(ref: str) -> bool:
    return ref.startswith(("http://", "https://"))


def _source_for(ref: str, settings: Settings, override: str | None) -> str:
    if override:
        return override
    if _is_url(ref):
        return "urls"
    try:
        Path(ref).resolve().relative_to(settings.licensed_clips_dir.resolve())
    except ValueError:
        return "local_file"
    return "licensed_folder"


def _reusable(item: ContentItem | None) -> bool:
    if item is None or not item.job_id:
        return False
    stem = item.assets.get("chosen_stem_path")
    notes = item.assets.get("midi_notes_path")
    return bool(stem and notes and Path(stem).is_file() and Path(notes).is_file())


def item_rights(item: ContentItem) -> RightsRecord | None:
    return RightsRecord.model_validate(item.rights) if item.rights else None


def _processed_from_item(item: ContentItem, rights: RightsRecord, reused: bool) -> ProcessedClip:
    result = json.loads(Path(item.assets["job_result_path"]).read_text())
    notes = json.loads(Path(item.assets["midi_notes_path"]).read_text())
    return ProcessedClip(
        content_item_id=item.id,
        job_id=item.job_id or "",
        source=item.source,
        source_ref=item.source_ref,
        chosen_stem=item.chosen_stem or "",
        chosen_stem_path=item.assets["chosen_stem_path"],
        midi_path=item.assets["midi_path"],
        stem_scores=[StemScore.model_validate(s) for s in item.stem_scores],
        midi_notes=[MidiNote.model_validate(n) for n in notes],
        analysis=Analysis.model_validate(result["analysis"]),
        rights=rights,
        reused=reused,
    )


async def _fetch_clip(ref: str, http: httpx.AsyncClient, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    if _is_url(ref):
        name = Path(httpx.URL(ref).path).name or "clip.bin"
        dest = dest_dir / f"source-{name}"
        async with http.stream("GET", ref) as response:
            response.raise_for_status()
            with dest.open("wb") as fh:
                async for chunk in response.aiter_bytes():
                    fh.write(chunk)
        return dest
    path = Path(ref)
    if not path.is_file():
        raise FileNotFoundError(f"clip not found: {ref}")
    return path


async def process_clip(
    settings: Settings,
    store: Store,
    http: httpx.AsyncClient,
    clip_path_or_url: str,
    options: dict[str, Any] | None = None,
    license_attestation: dict[str, Any] | LicenseAttestation | None = None,
) -> ProcessedClip:
    opts = dict(options or {})
    source = _source_for(clip_path_or_url, settings, opts.pop("source", None))
    force = bool(opts.pop("force", False))
    declared_license = opts.pop("license", None)
    declared_attribution = opts.pop("attribution", None)
    # The rights gate runs before anything is submitted, so a clip nobody licensed never
    # costs a credit and never reaches a render.
    rights = require_cleared(
        clip_path_or_url,
        source,
        resolve_rights(
            clip_path_or_url,
            source,
            declared_license=declared_license,
            declared_attribution=declared_attribution,
            attestation=parse_attestation(license_attestation),
        ),
    )
    existing = store.find_by_source_ref(source, clip_path_or_url)
    if not force and _reusable(existing):
        assert existing is not None
        existing = store.update(existing.id, rights=rights.model_dump())
        return _processed_from_item(existing, rights, reused=True)
    if not settings.tonamorph_api_key:
        raise RuntimeError("TONAMORPH_API_KEY is not set")

    item = store.create_item(source, clip_path_or_url)
    store.update(item.id, rights=rights.model_dump())
    work = settings.growth_work_dir / item.id
    clip_path = await _fetch_clip(clip_path_or_url, http, work)
    audio = clip_path.read_bytes()
    if len(audio) > MAX_UPLOAD_BYTES:
        raise ValueError(f"clip is {len(audio)} bytes; the API accepts at most 10 MB (§2)")

    job_options = JobOptions.model_validate(opts)
    client = TonamorphClient(
        settings.tonamorph_api_url,
        settings.tonamorph_api_key,
        http=http,
        poll_interval=settings.tonamorph_poll_interval_seconds,
        timeout=settings.tonamorph_job_timeout_seconds,
    )
    accepted = await client.submit_job(audio, clip_path.name, job_options)
    store.update(item.id, job_id=accepted.job_id)
    status = await client.wait_for_result(accepted.job_id)
    result = status.result
    assert result is not None

    stems_dir = work / "stems"
    stem_paths: dict[str, str] = {}
    for stem in result.stems:
        dest = stems_dir / f"{stem.name}.{stem.format or 'wav'}"
        await client.download(stem.url, dest)
        stem_paths[stem.name] = str(dest)
    midi_path = await client.download(result.midi.url, work / "score.mid")

    scores = score_stems(result)
    best = choose_stem(result)
    track = result.track_for(best.name)
    notes = track.notes if track else []
    notes_path = work / "midi_notes.json"
    notes_path.write_text(json.dumps([n.model_dump() for n in notes]))
    result_path = work / "job_result.json"
    result_path.write_text(result.model_dump_json())

    item = store.update(
        item.id,
        chosen_stem=best.name,
        stem_scores=[s.model_dump() for s in scores],
        assets={
            "clip_path": str(clip_path),
            "stems": stem_paths,
            "chosen_stem_path": stem_paths[best.name],
            "midi_path": str(midi_path),
            "midi_notes_path": str(notes_path),
            "job_result_path": str(result_path),
            "duration_seconds": probe_duration(clip_path) or result.input.duration_seconds,
        },
    )
    return _processed_from_item(item, rights, reused=False)


def clip_metadata(item: ContentItem) -> dict[str, Any]:
    """The metadata dict ``write_script`` expects, assembled from a processed item."""
    rights = item_rights(item)
    meta: dict[str, Any] = {
        "title": Path(item.source_ref).stem if not _is_url(item.source_ref) else item.source_ref,
        "chosen_stem": item.chosen_stem,
        "source": item.source,
        "attribution": rights.attribution if rights else None,
    }
    result_path = item.assets.get("job_result_path")
    if result_path and Path(result_path).is_file():
        result = json.loads(Path(result_path).read_text())
        meta["analysis"] = result.get("analysis", {})
        track = next(
            (t for t in result.get("midi", {}).get("tracks", []) if t["name"] == item.chosen_stem),
            None,
        )
        meta["note_count"] = len(track["notes"]) if track else 0
    return meta


async def generate_voiceover(
    settings: Settings,
    store: Store,
    http: httpx.AsyncClient,
    text: str,
    voice_id: str | None,
    content_item_id: str | None,
) -> VoiceoverResult:
    if not settings.elevenlabs_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    voice = voice_id or settings.elevenlabs_voice_id
    if content_item_id:
        store.require(content_item_id)
        dest = settings.growth_work_dir / content_item_id / "voiceover.mp3"
    else:
        digest = hashlib.sha256(f"{voice}:{text}".encode()).hexdigest()[:16]
        dest = settings.growth_work_dir / "voiceovers" / f"{digest}.mp3"
    result = await synthesize(
        text=text,
        api_url=settings.elevenlabs_api_url,
        api_key=settings.elevenlabs_api_key,
        voice_id=voice,
        model_id=settings.elevenlabs_model_id,
        dest=dest,
        http=http,
    )
    words_path = dest.with_name("voiceover_words.json")
    words_path.write_text(json.dumps([w.model_dump() for w in result.words]))
    if content_item_id:
        store.update(
            content_item_id,
            assets={"voiceover_path": result.audio_path, "voiceover_words_path": str(words_path)},
        )
    return result


async def render_video(
    settings: Settings,
    store: Store,
    content_item_id: str,
    *,
    scene: Scene,
    presenter: Presenter,
    avatar_clip: str | None,
    frames: tuple[int, int] | None = None,
) -> RenderResult:
    item = store.require(content_item_id)
    work = settings.growth_work_dir / item.id
    work.mkdir(parents=True, exist_ok=True)
    result = await render_item(
        item,
        settings,
        work_dir=work,
        scene=scene,
        presenter=presenter,
        avatar_clip=avatar_clip,
        frames=frames,
    )
    disclosure = disclosure_for(
        has_voiceover=bool(item.assets.get("voiceover_path")), presenter=presenter
    )
    store.update(
        item.id,
        assets={
            "video_path": result.video_path,
            "props_path": result.props_path,
            "renderer": result.renderer,
        },
        disclosure=disclosure.model_dump(),
    )
    return result


def build_request(
    settings: Settings,
    item: ContentItem,
    platform: Platform,
    *,
    caption: str,
    hashtags: list[str],
    schedule_at: str | None,
    disclosure: Disclosure | None = None,
) -> PublishRequest:
    """Compose one platform's post: caption, credit line, AI disclosure and the tagged link.

    The attribution and disclosure come from what was recorded on the content item (the licence
    ``process_clip`` cleared, the disclosure ``render_video`` wrote), never from the caller, so
    every publish of the same item says the same thing.
    """
    disclosed = disclosure or stored_disclosure(item)
    return PublishRequest(
        content_item_id=item.id,
        video_path=Path(item.assets["video_path"]),
        caption=caption,
        hashtags=hashtags,
        schedule_at=schedule_at,
        attribution=attribution_line(item_rights(item)),
        disclosure=disclosed.line,
        is_synthetic=disclosed.is_synthetic,
        link=build_landing_url(settings, platform=platform, content_item_id=item.id),
    )


async def publish_video(
    settings: Settings,
    store: Store,
    http: httpx.AsyncClient,
    content_item_id: str,
    platforms: list[Platform],
    caption: str,
    hashtags: list[str],
    schedule_at: str | None,
) -> PublishReport:
    item = store.require(content_item_id)
    video_path = item.assets.get("video_path")
    if not video_path or not Path(video_path).is_file():
        raise RuntimeError("content item has no rendered video; run render_video first")
    if schedule_at:
        parse_iso(schedule_at)
    disclosure = stored_disclosure(item)
    results: list[PlatformPublishResult] = []
    for platform in dict.fromkeys(platforms):
        if platform not in PLATFORMS:
            raise ValueError(f"unknown platform {platform}")
        record = item.publish_record(platform)
        if item.is_posted(platform):
            results.append(
                PlatformPublishResult(
                    platform=platform,
                    status=record.status,
                    post_id=record.post_id,
                    url=record.url,
                    note=record.note,
                    already_posted=True,
                    link=record.link,
                    disclosure_line=record.disclosure_line,
                    ai_flag_set=record.ai_flag_set,
                )
            )
            continue
        request = build_request(
            settings,
            item,
            platform,
            caption=caption,
            hashtags=hashtags,
            schedule_at=schedule_at,
            disclosure=disclosure,
        )
        results.append(
            await _publish_one(settings, store, http, item.id, platform, request, record)
        )
    return PublishReport(
        content_item_id=item.id,
        results=results,
        attribution_line=attribution_line(item_rights(item)),
        disclosure_line=disclosure.line,
    )


async def _publish_one(
    settings: Settings,
    store: Store,
    http: httpx.AsyncClient,
    item_id: str,
    platform: Platform,
    request: PublishRequest,
    record: PublishRecord,
) -> PlatformPublishResult:
    base = record.model_copy(
        update={
            "caption": request.caption,
            "hashtags": request.hashtags,
            "schedule_at": request.schedule_at,
            "link": request.link,
            "attribution_line": request.attribution,
            "disclosure_line": request.disclosure,
        }
    )
    try:
        publisher = build_publisher(platform, settings, http)
    except PublisherNotConfigured as exc:
        store.set_publish_record(item_id, platform, base.model_copy(update={"error": str(exc)}))
        return PlatformPublishResult(platform=platform, status="failed", error=str(exc))
    try:
        outcome = await publisher.publish(request, dict(record.checkpoint))
    except (PublisherError, httpx.HTTPError) as exc:
        checkpoint = getattr(exc, "checkpoint", None) or record.checkpoint
        store.set_publish_record(
            item_id,
            platform,
            base.model_copy(
                update={"status": "failed", "error": str(exc), "checkpoint": checkpoint}
            ),
        )
        return PlatformPublishResult(
            platform=platform, status="failed", error=str(exc), link=request.link
        )
    published_at = utc_now_iso() if outcome.status in ("published", "restricted") else None
    store.set_publish_record(
        item_id,
        platform,
        base.model_copy(
            update={
                "status": outcome.status,
                "post_id": outcome.post_id,
                "url": outcome.url,
                "note": outcome.note,
                "error": None,
                "published_at": published_at,
                "checkpoint": outcome.checkpoint,
                "ai_flag_set": outcome.ai_flag_set,
            }
        ),
    )
    return PlatformPublishResult(
        platform=platform,
        status=outcome.status,
        post_id=outcome.post_id,
        url=outcome.url,
        note=outcome.note,
        link=request.link,
        disclosure_line=request.disclosure,
        ai_flag_set=outcome.ai_flag_set,
    )


async def publish_due(
    settings: Settings, store: Store, http: httpx.AsyncClient, platforms: list[Platform]
) -> list[PlatformPublishResult]:
    """Publish locally scheduled posts (Instagram/TikTok) whose schedule_at has passed."""
    now = datetime.now(UTC)
    results: list[PlatformPublishResult] = []
    for item, platform in store.scheduled_items():
        record = item.publish_record(platform)
        if platform not in platforms or record.post_id or not record.schedule_at:
            continue
        if parse_iso(record.schedule_at) > now:
            continue
        video_path = item.assets.get("video_path")
        if not video_path:
            continue
        request = build_request(
            settings,
            item,
            platform,  # type: ignore[arg-type]
            caption=record.caption or "",
            hashtags=record.hashtags,
            schedule_at=None,
        )
        results.append(
            await _publish_one(
                settings,
                store,
                http,
                item.id,
                platform,
                request,
                record,  # type: ignore[arg-type]
            )
        )
    return results
