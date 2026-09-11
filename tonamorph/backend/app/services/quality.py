"""Quality loops (docs/API_CONTRACT.md §2 feedback, §14; GTM plan §2.6, Appendix C §5–6):
result feedback with the bounded auto-refund, NPS, plugin installs, the per-user facts the
growth events carry, and the last-24 h numbers behind ``GET /v1/status``.

The PostgREST implementation calls the ``0005_quality_loops.sql`` functions and nothing
else; :class:`app.services.memory.MemoryQualityService` mirrors them rule for rule.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.errors import INTERNAL_ERROR, ApiException
from app.schemas import FeedbackRating, FeedbackReason, JobFeedbackRequest, JobStatus, PlanKind
from app.services.supabase import SupabaseClient

AUTO_REFUND_REASON_PREFIX = "user:unusable:"
"""``refund_job`` reason of an automatic feedback refund; the bounds count these rows."""
AUTO_REFUND_WINDOW_HOURS = 24
AUTO_REFUND_LOOKBACK_DAYS = 30
AUTO_REFUND_MIN_PER_30_DAYS = 3
AUTO_REFUND_SHARE_OF_CAPTURED = 0.2
AUTO_REFUND_FREE_LIFETIME = 2
NPS_COOLDOWN_DAYS = 30
DEGRADED_MIN_JOBS = 20
DEGRADED_SUCCESS_RATE = 0.9


def auto_refund_reason(reason: FeedbackReason | None) -> str:
    return f"{AUTO_REFUND_REASON_PREFIX}{reason or 'unspecified'}"


def auto_refund_allowance(captured_last_30_days: int) -> int:
    """Auto-refunds allowed per 30 days: ``max(3, 20 % of captured jobs)`` (GTM §2.6)."""
    return max(
        AUTO_REFUND_MIN_PER_30_DAYS, int(captured_last_30_days * AUTO_REFUND_SHARE_OF_CAPTURED)
    )


class FeedbackRecord(BaseModel):
    """A ``job_feedback`` row."""

    job_id: UUID
    user_id: UUID
    rating: FeedbackRating
    reason: FeedbackReason | None = None
    note: str | None = None
    drop_to_ready_ms: int | None = None
    refunded: bool = False
    created_at: datetime
    updated_at: datetime


class NpsRecord(BaseModel):
    """An ``nps_responses`` row."""

    id: UUID
    user_id: UUID
    score: int
    comment: str | None = None
    created_at: datetime


class UserFacts(BaseModel):
    """What a growth event says about its profile (``user_facts``)."""

    email: str | None = None
    plan: PlanKind = "free"
    morphs_total: int = 0
    first_morph_at: datetime | None = None
    last_morph_at: datetime | None = None
    has_purchased: bool = False


class Last24hStats(BaseModel):
    """``status_last_24h()``: jobs that finished in the window."""

    morphs: int = 0
    succeeded: int = 0
    failed: int = 0
    p50_ms: int | None = None
    p95_ms: int | None = None

    @property
    def success_rate(self) -> float | None:
        return self.succeeded / self.morphs if self.morphs else None


class QualityService(Protocol):
    async def record_feedback(
        self, job_id: UUID, user_id: UUID, feedback: JobFeedbackRequest
    ) -> FeedbackRecord:
        """``record_job_feedback``: one row per job (upsert); a thumbs-down runs the
        bounded auto-refund. ``ApiException(NOT_FOUND)`` for a job that is not the
        caller's, ``ApiException(CONFLICT)`` while it is still queued or running."""
        ...

    async def submit_nps(self, user_id: UUID, score: int, comment: str | None) -> NpsRecord:
        """``submit_nps``: ``ApiException(CONFLICT)`` within 30 days of the last answer."""
        ...

    async def touch_plugin_install(
        self, user_id: UUID, plugin_version: str, host: str, os: str | None
    ) -> bool:
        """``touch_plugin_install``: ``True`` the first time this user is seen with this
        ``(plugin_version, host)`` pair; later calls stamp ``last_seen_at``."""
        ...

    async def user_facts(self, user_id: UUID) -> UserFacts | None:
        """``user_facts``; ``None`` when there is no profile."""
        ...

    async def status_last_24h(self) -> Last24hStats:
        """``status_last_24h()``."""
        ...


def elapsed_ms(started_at: datetime | None, created_at: datetime, finished_at: datetime) -> int:
    """Wall time from pickup (or submission, when a job finished without a worker) to the
    terminal state — the ``latency_ms`` every morph event and the status page report."""
    started = started_at or created_at
    return max(int(round((finished_at - started).total_seconds() * 1000)), 0)


def latency_ms(status: JobStatus) -> int | None:
    if status.finished_at is None:
        return None
    return elapsed_ms(status.started_at, status.created_at, status.finished_at)


def percentile(values: Sequence[float], fraction: float) -> float | None:
    """PostgreSQL's ``percentile_cont``: linear interpolation between order statistics."""
    if not values:
        return None
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _record(payload: Any, what: str) -> Mapping[str, Any]:
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    if not isinstance(payload, Mapping):
        raise ApiException(INTERNAL_ERROR, message=f"Database returned no {what}.")
    return payload


class SupabaseQualityService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def record_feedback(
        self, job_id: UUID, user_id: UUID, feedback: JobFeedbackRequest
    ) -> FeedbackRecord:
        row = await self._client.rpc(
            "record_job_feedback",
            {
                "p_job_id": str(job_id),
                "p_user_id": str(user_id),
                "p_rating": feedback.rating,
                "p_reason": feedback.reason,
                "p_note": feedback.note,
                "p_drop_to_ready_ms": feedback.drop_to_ready_ms,
            },
        )
        return FeedbackRecord.model_validate(_record(row, "feedback row"))

    async def submit_nps(self, user_id: UUID, score: int, comment: str | None) -> NpsRecord:
        row = await self._client.rpc(
            "submit_nps", {"p_user_id": str(user_id), "p_score": score, "p_comment": comment}
        )
        return NpsRecord.model_validate(_record(row, "NPS row"))

    async def touch_plugin_install(
        self, user_id: UUID, plugin_version: str, host: str, os: str | None
    ) -> bool:
        fresh = await self._client.rpc(
            "touch_plugin_install",
            {
                "p_user_id": str(user_id),
                "p_plugin_version": plugin_version,
                "p_host": host,
                "p_os": os,
            },
        )
        return bool(fresh)

    async def user_facts(self, user_id: UUID) -> UserFacts | None:
        rows = await self._client.rpc("user_facts", {"p_user_id": str(user_id)})
        if not isinstance(rows, list) or not rows:
            return None
        return UserFacts.model_validate(rows[0])

    async def status_last_24h(self) -> Last24hStats:
        rows = await self._client.rpc("status_last_24h", {})
        return Last24hStats.model_validate(_record(rows, "status row"))


__all__ = [
    "AUTO_REFUND_FREE_LIFETIME",
    "AUTO_REFUND_LOOKBACK_DAYS",
    "AUTO_REFUND_MIN_PER_30_DAYS",
    "AUTO_REFUND_REASON_PREFIX",
    "AUTO_REFUND_SHARE_OF_CAPTURED",
    "AUTO_REFUND_WINDOW_HOURS",
    "DEGRADED_MIN_JOBS",
    "DEGRADED_SUCCESS_RATE",
    "NPS_COOLDOWN_DAYS",
    "FeedbackRecord",
    "Last24hStats",
    "NpsRecord",
    "QualityService",
    "SupabaseQualityService",
    "UserFacts",
    "auto_refund_allowance",
    "auto_refund_reason",
    "elapsed_ms",
    "latency_ms",
    "percentile",
]
