"""Shared publisher contracts.

Every adapter is idempotent per (content item, platform): the caller passes the stored
``checkpoint`` of a previous attempt and the adapter resumes from the last completed step
(container created, bytes uploaded, …) instead of creating a second post.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field

from ..config import Platform
from ..state import parse_iso, utc_now_iso

OutcomeStatus = Literal["published", "scheduled", "restricted", "failed"]


class PublisherError(RuntimeError):
    def __init__(self, message: str, checkpoint: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.checkpoint = checkpoint


class PublisherNotConfigured(PublisherError):
    pass


class PublishRequest(BaseModel):
    content_item_id: str
    video_path: Path
    caption: str
    hashtags: list[str] = Field(default_factory=list)
    title: str = "Tonamorph"
    schedule_at: str | None = None
    attribution: str | None = Field(
        default=None, description="Credit line the source licence requires (§2)"
    )
    disclosure: str | None = Field(
        default=None, description="AI disclosure line, appended on every platform (§6)"
    )
    is_synthetic: bool = Field(
        default=False, description="Drives the platform AI-content flag where the API has one"
    )
    link: str | None = Field(default=None, description="UTM-tagged landing URL (§7)")

    def full_caption(self) -> str:
        """Caption, then the credit line, the AI disclosure and the tagged link, then tags."""
        tags = " ".join(_normalize_tag(t) for t in self.hashtags if t.strip())
        parts = [self.caption.strip(), self.attribution, self.disclosure, self.link, tags]
        return "\n\n".join(p.strip() for p in parts if p and p.strip())


class PublishOutcome(BaseModel):
    platform: Platform
    status: OutcomeStatus
    post_id: str | None = None
    url: str | None = None
    note: str | None = None
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    ai_flag_set: bool = Field(
        default=False, description="True when the publishing API took an AI-content flag"
    )


class PostMetrics(BaseModel):
    platform: Platform
    post_id: str
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    impressions: int | None = None
    ctr: float | None = Field(
        default=None,
        description="views/impressions when the platform reports impressions (ctr_kind=click),"
        " else (likes+comments+shares)/views (ctr_kind=engagement)",
    )
    ctr_kind: Literal["click", "engagement"] | None = None
    fetched_at: str = Field(default_factory=utc_now_iso)


class Publisher(Protocol):
    platform: Platform
    # True when this platform's publishing endpoint carries an AI-content field. Where it is
    # False the disclosure still ships, in the caption (see ``PublishRequest.full_caption``).
    ai_flag_supported: bool

    async def publish(
        self, request: PublishRequest, checkpoint: dict[str, Any]
    ) -> PublishOutcome: ...

    async def metrics(self, post_id: str) -> PostMetrics: ...


def _normalize_tag(tag: str) -> str:
    cleaned = re.sub(r"[^\w]", "", tag.strip().lstrip("#"))
    return f"#{cleaned}" if cleaned else ""


def finish_metrics(metrics: PostMetrics) -> PostMetrics:
    """Fill ``ctr``/``ctr_kind`` from the counts an adapter managed to fetch."""
    if metrics.impressions and metrics.views is not None:
        metrics.ctr = round(metrics.views / metrics.impressions, 4)
        metrics.ctr_kind = "click"
    elif metrics.views:
        engagement = (metrics.likes or 0) + (metrics.comments or 0) + (metrics.shares or 0)
        metrics.ctr = round(engagement / metrics.views, 4)
        metrics.ctr_kind = "engagement"
    return metrics


async def poll_until(
    check: Callable[[], Awaitable[bool]], *, interval: float, attempts: int, what: str
) -> None:
    """Call ``check`` until it returns True; raise PublisherError after ``attempts``."""
    for _ in range(max(1, attempts)):
        if await check():
            return
        await asyncio.sleep(interval)
    raise PublisherError(f"{what} did not complete after {attempts} checks")


def response_json(response: httpx.Response, what: str) -> dict[str, Any]:
    """Decode a JSON body or raise a PublisherError carrying the status (never the body)."""
    try:
        body = response.json()
    except ValueError as exc:
        raise PublisherError(f"{what}: non-JSON response ({response.status_code})") from exc
    if response.status_code >= 400:
        err = body.get("error") if isinstance(body, dict) else None
        code = (err or {}).get("code") if isinstance(err, dict) else None
        message = (err or {}).get("message") if isinstance(err, dict) else None
        raise PublisherError(
            f"{what}: HTTP {response.status_code} {code or ''} {message or ''}".strip()
        )
    return body if isinstance(body, dict) else {}


def read_video(path: Path) -> bytes:
    if not path.is_file():
        raise PublisherError(f"video file not found: {path}")
    return path.read_bytes()


def is_future(schedule_at: str | None) -> bool:
    return bool(schedule_at) and parse_iso(schedule_at or "") > datetime.now(UTC)


def to_unix(schedule_at: str) -> int:
    return int(parse_iso(schedule_at).timestamp())
