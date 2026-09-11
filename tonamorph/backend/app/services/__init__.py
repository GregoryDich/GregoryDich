"""Service interfaces used by the routers.

Each Protocol is implemented once per backend (Supabase/PostgREST, S3/SQS, in-memory for
tests) and wired in ``create_app``. Routers depend only on these Protocols. All methods are
coroutines; implementations raise :class:`app.errors.ApiException` for contract errors and
let other exceptions propagate.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from app.schemas import (
    AccountExport,
    ApiKeyCreateResponse,
    ApiKeyInfo,
    Balance,
    CreditBalance,
    JobOptions,
    JobResult,
    JobsPage,
    JobStatus,
    LedgerPage,
    PipelineOptions,
    PlanKind,
    Profile,
)


class CreditsService(Protocol):
    """Credit accounting on top of the §6 SQL functions; every method is idempotent as
    documented there."""

    async def get_balance(self, user_id: UUID) -> Balance:
        """``get_balance``; ``subscription_renews_at`` comes from the active subscription."""
        ...

    async def reserve(self, user_id: UUID, job_id: UUID, amount: int = 1) -> CreditBalance:
        """``reserve_credits``; raises ``ApiException(INSUFFICIENT_CREDITS)`` (402) when
        ``available < amount``. Repeating for the same ``job_id`` is a no-op."""
        ...

    async def settle(self, job_id: UUID, success: bool) -> CreditBalance:
        """``settle_reservation``: capture on success, release on failure."""
        ...

    async def grant(
        self,
        user_id: UUID,
        amount: int,
        source: str,
        idempotency_key: str,
        note: str | None = None,
        expires_at: datetime | None = None,
    ) -> CreditBalance:
        """``grant_credits``; a repeated ``idempotency_key`` returns the current balance."""
        ...

    async def refund_job(self, job_id: UUID, reason: str) -> CreditBalance:
        """``refund_job``: reverse a captured job."""
        ...

    async def ledger(self, user_id: UUID, limit: int = 50, cursor: str | None = None) -> LedgerPage:
        """Newest-first page of ``credit_ledger`` rows (§3)."""
        ...


class JobsService(Protocol):
    """Persistence and fan-out for ``jobs`` rows (§2, §6 lifecycle)."""

    async def create(
        self,
        user_id: UUID,
        options: JobOptions,
        input_key: str,
        credits_reserved: int,
    ) -> JobStatus:
        """Insert a ``queued`` job; ``input_key`` is the storage path of the uploaded audio."""
        ...

    async def find_by_idempotency_key(self, user_id: UUID, key: str) -> JobStatus | None:
        """Existing job for ``options.idempotency_key`` so a re-post is not charged twice."""
        ...

    async def get(self, job_id: UUID, user_id: UUID) -> JobStatus | None:
        """The job, or ``None`` when it does not exist or belongs to another user (→ 404)."""
        ...

    async def list(self, user_id: UUID, limit: int = 20, cursor: str | None = None) -> JobsPage:
        """Newest-first page of the user's jobs, keyed by ``(created_at, id)`` (§2)."""
        ...

    async def set_progress(self, job_id: UUID, stage: str, progress: float) -> None:
        """Move to ``running`` (setting ``started_at`` once) and record stage/progress."""
        ...

    async def complete(self, job_id: UUID, result: JobResult) -> JobStatus:
        """Mark ``succeeded`` with the result; idempotent for a finished job."""
        ...

    async def fail(self, job_id: UUID, code: str, message: str) -> JobStatus:
        """Mark ``failed`` with the §5-style error; idempotent for a finished job."""
        ...

    async def cancel(self, job_id: UUID, user_id: UUID) -> JobStatus:
        """Cancel a ``queued`` job; raises ``ApiException(CONFLICT)`` (409) once running."""
        ...

    def events(self, job_id: UUID) -> AsyncIterator[dict[str, Any]]:
        """Stream of ``{"event": "progress"|"result"|"error", "data": <payload>}`` for the
        SSE/WS routes; ends after ``result`` or ``error``."""
        ...

    async def reap_stale(self, timeout_seconds: int) -> int:
        """Fail jobs left ``running`` longer than ``timeout_seconds`` (``worker_timeout``)
        and release their reservations; returns the number reaped."""
        ...


class StorageService(Protocol):
    """Object storage for inputs and results under ``jobs/<user_id>/<job_id>/`` (§2, §10)."""

    async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str:
        """Store ``data`` at ``path`` (bucket-relative) and return the stored path."""
        ...

    async def download_bytes(self, path: str) -> bytes:
        """Read the object at ``path`` (workers fetch the job input this way)."""
        ...

    async def signed_url(self, path: str, ttl_seconds: int) -> str:
        """Time-limited GET URL for ``path``; opaque to clients."""
        ...


@runtime_checkable
class PurgeableStorageService(Protocol):
    """Optional storage capability used by account deletion (§1): a backend that can
    remove a user's objects at once. Backends without it rely on the 24 h lifecycle rule."""

    async def delete_prefix(self, prefix: str) -> int:
        """Delete every object whose path starts with ``prefix``; returns how many."""
        ...


class UsersService(Protocol):
    """``profiles`` rows keyed by the Supabase auth user id."""

    async def get(self, user_id: UUID) -> Profile | None: ...

    async def find_by_email(self, email: str) -> Profile | None:
        """Webhook fallback when the provider payload carries no ``user_id``."""
        ...

    async def ensure(self, user_id: UUID, email: str) -> Profile:
        """Create the profile on first sight and grant ``FREE_SIGNUP_CREDITS`` (idempotent).
        The first call that meets a profile also runs :meth:`first_sight` for it."""
        ...

    async def first_sight(self, user_id: UUID, source: str) -> bool:
        """Stamp ``profiles.first_seen_at`` once and emit ``Signed Up`` (§14) with the
        profile's sign-up facts; ``True`` only for the call that stamped it. ``source``
        is ``web`` for a profile the sign-up trigger created, ``plugin`` for one created
        here on an API-first token."""
        ...

    async def set_plan(self, user_id: UUID, plan: PlanKind, renews_at: datetime | None) -> Profile:
        """Update the plan after a purchase or subscription event."""
        ...

    async def export(self, user_id: UUID) -> AccountExport:
        """Everything held about the user (§1 ``GET /v1/me/export``), or
        ``ApiException(NOT_FOUND)`` when there is no profile."""
        ...

    async def delete_account(self, user_id: UUID) -> None:
        """``delete_user_account`` then the identity-provider deletion (§1 ``DELETE /v1/me``).
        Raises ``ApiException(CONFLICT)`` (409) while a job is queued or running; the data
        step is idempotent, so a repeat after an identity-provider failure completes it."""
        ...


class ApiKeysService(Protocol):
    """``api_keys`` rows (§11); plaintext is returned once and only its SHA-256 is stored."""

    async def create(self, user_id: UUID, name: str) -> ApiKeyCreateResponse: ...

    async def list(self, user_id: UUID) -> list[ApiKeyInfo]:
        """The user's keys, revoked ones included, newest first; never the hash."""
        ...

    async def revoke(self, user_id: UUID, key_id: UUID) -> bool:
        """Revoke the caller's key; ``False`` when it does not exist or is not theirs."""
        ...

    async def resolve(self, plaintext: str) -> UUID | None:
        """Owning user id for a presented ``X-API-Key`` (touches ``last_used_at``), or
        ``None`` when unknown or revoked."""
        ...


class WebhookEventsService(Protocol):
    """``webhook_events`` idempotency ledger for §4 (key = ``<provider>:<event>:<id>``)."""

    async def claim(
        self,
        idempotency_key: str,
        provider: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        """Record the event; ``False`` when ``idempotency_key`` was already recorded."""
        ...

    async def mark_processed(self, idempotency_key: str, error: str | None = None) -> None:
        """Finalise the record with an optional processing error."""
        ...


class DispatchService(Protocol):
    """Hands a queued job to the pipeline selected by ``TONAMORPH_PIPELINE`` (§7, §10)."""

    async def dispatch(
        self,
        job_id: UUID,
        user_id: UUID,
        input_key: str,
        options: PipelineOptions,
    ) -> None:
        """Enqueue or start processing; raises ``ApiException(WORKER_UNAVAILABLE)`` (503)
        when no backend can accept the job."""
        ...

    async def cancel(self, job_id: UUID) -> bool:
        """Best-effort withdrawal of a queued job; ``False`` if it already started."""
        ...


__all__ = [
    "ApiKeysService",
    "CreditsService",
    "DispatchService",
    "JobsService",
    "PurgeableStorageService",
    "StorageService",
    "UsersService",
    "WebhookEventsService",
]
