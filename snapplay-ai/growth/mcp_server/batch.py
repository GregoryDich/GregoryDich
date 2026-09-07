"""Daily orchestration: clips → jobs → briefs → voiceovers → renders → (optionally) posts."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, Field

from .config import PLATFORMS, Platform, Settings
from .pipeline import (
    PlatformPublishResult,
    clip_metadata,
    generate_voiceover,
    process_clip,
    publish_due,
    publish_video,
    render_video,
)
from .script import ANGLES, brief_voice_text, write_brief
from .sources import LicensedFolderProvider
from .state import Store


class BatchItemReport(BaseModel):
    source_ref: str
    content_item_id: str | None = None
    angle: str
    status: str = Field(description="rendered | published | failed")
    chosen_stem: str | None = None
    video_path: str | None = None
    renderer: str | None = None
    voiceover: bool = False
    publish: list[PlatformPublishResult] = Field(default_factory=list)
    skipped_platforms: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class BatchReport(BaseModel):
    dry_run: bool
    platforms: list[Platform]
    requested: int
    items: list[BatchItemReport] = Field(default_factory=list)
    published_due: list[PlatformPublishResult] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def day_start_iso() -> str:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat().replace("+00:00", "Z")


class DailyLimiter:
    """Per-platform daily caps backed by the store, so restarts never exceed the cap."""

    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self.since = day_start_iso()
        self._extra: dict[str, int] = {}

    def allowance(self, platform: Platform) -> int:
        used = self.store.count_published_since(platform, self.since) + self._extra.get(platform, 0)
        return self.settings.max_posts_per_day(platform) - used

    def consume(self, platform: Platform) -> None:
        self._extra[platform] = self._extra.get(platform, 0) + 1


def resolve_platforms(settings: Settings, accounts: list[str] | None) -> list[Platform]:
    if accounts is None:
        return settings.configured_platforms()
    unknown = [a for a in accounts if a not in PLATFORMS]
    if unknown:
        raise ValueError(f"unknown platform(s): {', '.join(unknown)}; expected {list(PLATFORMS)}")
    return [a for a in PLATFORMS if a in accounts]


async def run_daily_batch(
    settings: Settings,
    store: Store,
    http: httpx.AsyncClient,
    *,
    count: int,
    accounts: list[str] | None,
    dry_run: bool,
) -> BatchReport:
    platforms = resolve_platforms(settings, accounts)
    report = BatchReport(dry_run=dry_run, platforms=platforms, requested=count)
    if not dry_run and not platforms:
        report.notes.append("no platform credentials configured; nothing will be published")
    limiter = DailyLimiter(store, settings)

    if not dry_run and platforms:
        report.published_due = await publish_due(settings, store, http, platforms)
        for result in report.published_due:
            if result.status in ("published", "restricted"):
                limiter.consume(result.platform)

    provider = LicensedFolderProvider(settings.licensed_clips_dir)
    known = store.known_source_refs("licensed_folder")
    clips = [
        c for c in await provider.list_clips(limit=max(count * 4, count)) if c.ref not in known
    ]
    if len(clips) < count:
        report.notes.append(
            f"only {len(clips)} unprocessed clip(s) in {settings.licensed_clips_dir};"
            f" requested {count}"
        )
    voice_enabled = bool(settings.elevenlabs_api_key)
    if not voice_enabled:
        report.notes.append("ELEVENLABS_API_KEY not set; rendering with on-screen text only")

    for index, clip in enumerate(clips[:count]):
        angle = ANGLES[index % len(ANGLES)]
        entry = BatchItemReport(source_ref=clip.ref, angle=angle, status="failed")
        report.items.append(entry)
        try:
            processed = await process_clip(
                settings, store, http, clip.ref, {"source": "licensed_folder"}
            )
            entry.content_item_id = processed.content_item_id
            entry.chosen_stem = processed.chosen_stem
            item = store.require(processed.content_item_id)
            brief = write_brief({**clip_metadata(item), "title": clip.title}, angle)
            store.update(item.id, script=brief.model_dump())
            if voice_enabled:
                await generate_voiceover(
                    settings, store, http, brief_voice_text(brief), None, item.id
                )
                entry.voiceover = True
            rendered = await render_video(
                settings, store, item.id, scene="plugin_ui", presenter="waveform", avatar_clip=None
            )
            entry.video_path = rendered.video_path
            entry.renderer = rendered.renderer
            entry.status = "rendered"
        except Exception as exc:
            entry.error = f"{type(exc).__name__}: {exc}"
            continue

        if dry_run or not platforms:
            continue
        allowed: list[Platform] = []
        for platform in platforms:
            if limiter.allowance(platform) <= 0:
                entry.skipped_platforms[platform] = "daily cap reached"
            else:
                allowed.append(platform)
        if not allowed:
            continue
        caption = f"{brief.hook} {brief.cta_line}"
        published = await publish_video(
            settings, store, http, item.id, allowed, caption, brief.hashtags, None
        )
        entry.publish = published.results
        for result in published.results:
            if (
                result.status in ("published", "restricted", "scheduled")
                and not result.already_posted
            ):
                limiter.consume(result.platform)
        if any(r.status in ("published", "restricted") for r in published.results):
            entry.status = "published"
    return report
