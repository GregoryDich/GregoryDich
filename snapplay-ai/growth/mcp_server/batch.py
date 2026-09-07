"""Daily orchestration: clips → jobs → briefs → voiceovers → renders → (optionally) posts.

The run is bounded on both sides: per-platform daily caps decide how much may be published,
and the credit guard (§8) decides how much may be spent — the batch reads the account balance
before every clip and stops rather than crossing the configured floor or the per-run budget.
"""

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
from .snapplay import SnapPlayApiError, SnapPlayClient
from .sources import LicensedFolderProvider, SourceClip
from .state import Store

CREDITS_PER_CLIP = 1


class BatchItemReport(BaseModel):
    source_ref: str
    content_item_id: str | None = None
    angle: str
    status: str = Field(description="rendered | published | failed | skipped")
    skip_reason: str | None = Field(
        default=None, description="Why a skipped clip was not processed (credit guard)"
    )
    chosen_stem: str | None = None
    video_path: str | None = None
    renderer: str | None = None
    voiceover: bool = False
    publish: list[PlatformPublishResult] = Field(default_factory=list)
    skipped_platforms: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class CreditReport(BaseModel):
    """What the run was allowed to spend and what it actually spent (§8)."""

    floor: int
    budget: int | None = Field(default=None, description="Credits this run may spend at most")
    balance_checked: bool = False
    balance_before: int | None = None
    balance_after: int | None = None
    credits_spent: int = 0
    stopped_reason: str | None = Field(
        default=None, description="Why the run stopped before processing every clip"
    )


class BatchReport(BaseModel):
    dry_run: bool
    platforms: list[Platform]
    requested: int
    items: list[BatchItemReport] = Field(default_factory=list)
    published_due: list[PlatformPublishResult] = Field(default_factory=list)
    credits: CreditReport = Field(default_factory=lambda: CreditReport(floor=0))
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


class CreditGuard:
    """Keeps ``run_daily_batch`` from spending past the balance floor or the per-run budget.

    The balance comes from ``GET /v1/me`` (contract §1) with the engine's API key, re-read
    before every clip so a job someone else submits against the same account is seen.
    """

    def __init__(self, settings: Settings, http: httpx.AsyncClient, budget: int | None) -> None:
        self.settings = settings
        self.http = http
        self.floor = settings.growth_credit_floor
        self.budget = budget
        self.report = CreditReport(floor=self.floor, budget=budget)

    async def _available(self) -> int:
        client = SnapPlayClient(
            self.settings.snapplay_api_url,
            self.settings.snapplay_api_key or "",
            http=self.http,
            poll_interval=self.settings.snapplay_poll_interval_seconds,
            timeout=self.settings.snapplay_job_timeout_seconds,
        )
        balance = await client.get_balance()
        self.report.balance_checked = True
        if self.report.balance_before is None:
            self.report.balance_before = balance.available
        self.report.balance_after = balance.available
        return balance.available

    async def blocker(self) -> str | None:
        """A reason not to process another clip, or None when one more may be spent."""
        if self.budget is not None and self.report.credits_spent + CREDITS_PER_CLIP > self.budget:
            return (
                f"per-run credit budget of {self.budget} reached "
                f"({self.report.credits_spent} spent)"
            )
        if not self.settings.snapplay_api_key:
            return None
        try:
            available = await self._available()
        except (SnapPlayApiError, httpx.HTTPError) as exc:
            return f"credit balance could not be read ({type(exc).__name__}: {exc})"
        if available - CREDITS_PER_CLIP < self.floor:
            return (
                f"balance floor would be crossed: {available} credit(s) available, "
                f"floor is {self.floor}"
            )
        return None

    def spent(self, credits: int = CREDITS_PER_CLIP) -> None:
        self.report.credits_spent += credits


def resolve_platforms(settings: Settings, accounts: list[str] | None) -> list[Platform]:
    if accounts is None:
        return settings.configured_platforms()
    unknown = [a for a in accounts if a not in PLATFORMS]
    if unknown:
        raise ValueError(f"unknown platform(s): {', '.join(unknown)}; expected {list(PLATFORMS)}")
    return [a for a in PLATFORMS if a in accounts]


def _candidate_clips(settings: Settings, store: Store, clips: list[SourceClip]) -> tuple[
    list[SourceClip], list[str]
]:
    """Unprocessed clips whose rights are established, plus a note per clip that is not."""
    known = store.known_source_refs("licensed_folder")
    fresh = [c for c in clips if c.ref not in known]
    cleared = [c for c in fresh if c.rights.cleared]
    notes = [
        f"skipped {c.title}: {c.rights.reason}" for c in fresh if not c.rights.cleared
    ]
    if notes:
        notes.insert(
            0,
            f"{len(notes)} clip(s) in {settings.licensed_clips_dir} have no established licence "
            "and were not processed",
        )
    return cleared, notes


async def run_daily_batch(
    settings: Settings,
    store: Store,
    http: httpx.AsyncClient,
    *,
    count: int,
    accounts: list[str] | None,
    dry_run: bool,
    credit_budget: int | None = None,
) -> BatchReport:
    platforms = resolve_platforms(settings, accounts)
    budget = credit_budget if credit_budget is not None else settings.growth_credit_budget
    guard = CreditGuard(settings, http, budget)
    report = BatchReport(
        dry_run=dry_run, platforms=platforms, requested=count, credits=guard.report
    )
    if not dry_run and not platforms:
        report.notes.append("no platform credentials configured; nothing will be published")
    limiter = DailyLimiter(store, settings)

    if not dry_run and platforms:
        report.published_due = await publish_due(settings, store, http, platforms)
        for result in report.published_due:
            if result.status in ("published", "restricted"):
                limiter.consume(result.platform)

    provider = LicensedFolderProvider(settings.licensed_clips_dir)
    listed = await provider.list_clips(limit=max(count * 4, count))
    clips, rights_notes = _candidate_clips(settings, store, listed)
    report.notes.extend(rights_notes)
    if len(clips) < count:
        report.notes.append(
            f"only {len(clips)} unprocessed clip(s) in {settings.licensed_clips_dir};"
            f" requested {count}"
        )
    voice_enabled = bool(settings.elevenlabs_api_key)
    if not voice_enabled:
        report.notes.append("ELEVENLABS_API_KEY not set; rendering with on-screen text only")

    stop_reason: str | None = None
    for index, clip in enumerate(clips[:count]):
        angle = ANGLES[index % len(ANGLES)]
        if stop_reason is None:
            stop_reason = await guard.blocker()
            if stop_reason is not None:
                guard.report.stopped_reason = stop_reason
                report.notes.append(f"stopped before spending more credits: {stop_reason}")
        if stop_reason is not None:
            report.items.append(
                BatchItemReport(
                    source_ref=clip.ref, angle=angle, status="skipped", skip_reason=stop_reason
                )
            )
            continue
        entry = BatchItemReport(source_ref=clip.ref, angle=angle, status="failed")
        report.items.append(entry)
        try:
            processed = await process_clip(
                settings,
                store,
                http,
                clip.ref,
                {
                    "source": "licensed_folder",
                    "license": clip.rights.license,
                    "attribution": clip.rights.attribution,
                },
            )
            if not processed.reused:
                guard.spent()
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
    report.credits = guard.report
    return report
