"""Klaviyo events (docs/API_CONTRACT.md §14; GTM plan §3.2–3.3, Appendix C §3–4).

Every product event the backend emits is a Klaviyo metric in Title Case (:data:`METRICS`),
sent server-side with the private key through the Create Event API, which also creates or
updates the profile it names (``external_id`` = user id, plus the email when known).

Emission never sits on a request's critical path: :meth:`KlaviyoEvents.emit` schedules a
background task on the running loop and returns at once; the task retries once and logs
when the event is dropped; nothing here raises into a router or a worker. Without
``KLAVIYO_PRIVATE_API_KEY`` the emitter is disabled and drops every event before building it.

Events carry a deterministic ``unique_id`` wherever they have a natural one (a job id, a
webhook idempotency key), which Klaviyo uses to deduplicate: a replayed ``complete_job``,
a re-delivered webhook or a retried request can never count twice.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Coroutine, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx

from app.config import Settings, get_settings

log = logging.getLogger("tonamorph.klaviyo")

KLAVIYO_API_BASE = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = "2024-10-15"
EVENTS_PATH = "/events/"
PROFILE_IMPORT_PATH = "/profile-import/"
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
DEFAULT_RETRY_DELAY_SECONDS = 0.5
FLUSH_TIMEOUT_SECONDS = 5.0

# The metric names, exactly as the GTM plan spells them (Appendix C §3).
SIGNED_UP = "Signed Up"
PLUGIN_INSTALLED = "Plugin Installed"
MORPH_COMPLETED = "Morph Completed"
MORPH_FAILED = "Morph Failed"
CREDITS_EXHAUSTED = "Credits Exhausted"
CHECKOUT_STARTED = "Checkout Started"
PURCHASE_COMPLETED = "Purchase Completed"
SUBSCRIPTION_CANCELLED = "Subscription Cancelled"
REFUND_ISSUED = "Refund Issued"
NPS_SUBMITTED = "NPS Submitted"
REFERRAL_JOINED = "Referral Joined"
REFERRAL_REWARDED = "Referral Rewarded"
GIFT_GRANTED = "Gift Granted"
METRICS: tuple[str, ...] = (
    SIGNED_UP,
    PLUGIN_INSTALLED,
    MORPH_COMPLETED,
    MORPH_FAILED,
    CREDITS_EXHAUSTED,
    CHECKOUT_STARTED,
    PURCHASE_COMPLETED,
    SUBSCRIPTION_CANCELLED,
    REFUND_ISSUED,
    NPS_SUBMITTED,
    REFERRAL_JOINED,
    REFERRAL_REWARDED,
    GIFT_GRANTED,
)


@dataclass(frozen=True, slots=True)
class Event:
    """One metric occurrence for one profile. ``properties`` are the event's own;
    ``profile_properties`` are written onto the profile (plan, morphs_total, ...)."""

    metric: str
    user_id: UUID
    email: str | None
    properties: Mapping[str, Any]
    unique_id: str | None = None
    profile_properties: Mapping[str, Any] | None = None
    time: datetime | None = None

    def payload(self) -> dict[str, Any]:
        """The ``POST /api/events/`` body (JSON:API)."""
        profile: dict[str, Any] = {"external_id": str(self.user_id)}
        if self.email:
            profile["email"] = self.email
        if self.profile_properties:
            profile["properties"] = dict(self.profile_properties)
        attributes: dict[str, Any] = {
            "properties": dict(self.properties),
            "time": iso_utc(self.time or datetime.now(UTC)),
            "metric": {"data": {"type": "metric", "attributes": {"name": self.metric}}},
            "profile": {"data": {"type": "profile", "attributes": profile}},
        }
        if self.unique_id:
            attributes["unique_id"] = self.unique_id
        return {"data": {"type": "event", "attributes": attributes}}


def iso_utc(moment: datetime) -> str:
    """RFC 3339 in UTC with ``Z``, the way the API's own responses render timestamps."""
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


class KlaviyoError(Exception):
    """A response Klaviyo refused; ``status`` decides whether it is retried."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"klaviyo answered {status}")


class KlaviyoClient:
    """The two Klaviyo calls the backend makes. Disabled (no HTTP client at all) when
    the private key is empty; the key travels only in the ``Authorization`` header."""

    def __init__(
        self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        key = settings.klaviyo_private_api_key.get_secret_value()
        self.enabled = bool(key)
        self._http: httpx.AsyncClient | None = None
        if self.enabled:
            self._http = httpx.AsyncClient(
                base_url=KLAVIYO_API_BASE,
                timeout=settings.klaviyo_timeout_seconds,
                transport=transport,
                headers={
                    "Authorization": f"Klaviyo-API-Key {key}",
                    "revision": KLAVIYO_REVISION,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    async def _post(self, path: str, payload: Mapping[str, Any]) -> None:
        if self._http is None:
            raise RuntimeError("Klaviyo is not configured")
        response = await self._http.post(path, json=dict(payload))
        if not response.is_success:
            raise KlaviyoError(response.status_code)

    async def create_event(self, event: Event) -> None:
        """``POST /api/events/``; raises on transport failure or a non-2xx answer."""
        await self._post(EVENTS_PATH, event.payload())

    async def upsert_profile(
        self, user_id: UUID, email: str | None, properties: Mapping[str, Any]
    ) -> None:
        """``POST /api/profile-import/``: create or update the profile keyed by
        ``external_id`` (the user id) with ``properties``."""
        attributes: dict[str, Any] = {"external_id": str(user_id), "properties": dict(properties)}
        if email:
            attributes["email"] = email
        await self._post(
            PROFILE_IMPORT_PATH, {"data": {"type": "profile", "attributes": attributes}}
        )


@dataclass
class KlaviyoEvents:
    """Fire-and-forget emitter over :class:`KlaviyoClient`.

    :meth:`emit` and :meth:`schedule` return immediately; the work runs as a task on the
    running loop and its failures are logged, never raised. :meth:`flush` awaits whatever
    is pending (workers call it before their loop ends; tests call it before asserting).
    """

    client: KlaviyoClient
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS
    _tasks: set[asyncio.Task[Any]] = field(default_factory=set, init=False, repr=False)

    @property
    def enabled(self) -> bool:
        return self.client.enabled

    @property
    def pending(self) -> int:
        return len(self._tasks)

    def schedule(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Run ``coro`` in the background; nothing when disabled or outside a loop."""
        if not self.enabled:
            coro.close()
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            coro.close()
            log.warning("klaviyo event dropped: no running event loop")
            return
        task = loop.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def emit(self, event: Event) -> None:
        self.schedule(self.send(event))

    async def send(self, event: Event) -> bool:
        """Deliver ``event`` with one retry on a transport failure, a 429 or a 5xx;
        returns whether Klaviyo accepted it. Never raises."""
        if not self.enabled:
            return False
        extra = {"metric": event.metric, "user_id": str(event.user_id)}
        for attempt in (1, 2):
            try:
                await self.client.create_event(event)
                return True
            except KlaviyoError as exc:
                extra["status"] = exc.status
                if exc.status not in RETRY_STATUSES:
                    log.warning("klaviyo refused the event", extra=extra)
                    return False
            except httpx.HTTPError as exc:
                extra["reason"] = type(exc).__name__
            except Exception:
                log.exception("klaviyo event failed", extra=extra)
                return False
            if attempt == 1:
                await asyncio.sleep(self.retry_delay_seconds)
        log.warning("klaviyo event dropped after retry", extra=extra)
        return False

    async def flush(self, timeout: float = FLUSH_TIMEOUT_SECONDS) -> None:
        """Wait for the pending deliveries (at most ``timeout`` seconds)."""
        pending = list(self._tasks)
        if not pending:
            return
        await asyncio.wait(pending, timeout=timeout)

    async def aclose(self) -> None:
        await self.flush()
        for task in list(self._tasks):
            task.cancel()
        await self.client.aclose()


def sample_events(user_id: UUID, email: str) -> list[Event]:
    """One representative event per metric: Klaviyo only lists a metric after its first
    event, so flows referencing one cannot be built before this has run (GTM plan §3.3)."""
    stamp = datetime.now(UTC)
    common = {"user_id": str(user_id)}
    samples: dict[str, dict[str, Any]] = {
        SIGNED_UP: {**common, "source": "web", "referral_code": None, "marketing_opt_in": False},
        PLUGIN_INSTALLED: {"os": "macOS", "daw": "Ableton Live", "plugin_version": "0.1.0"},
        MORPH_COMPLETED: {
            "job_id": str(uuid4()),
            "latency_ms": 1800,
            "credits_charged": 1,
            "balance_after": 2,
            "morphs_total": 1,
            "bpm": 124.0,
            "key": "F minor",
        },
        MORPH_FAILED: {
            "job_id": str(uuid4()),
            "error_code": "worker_timeout",
            "stage": "separate",
            "latency_ms": 180000,
        },
        CREDITS_EXHAUSTED: {"plan": "free"},
        CHECKOUT_STARTED: {"plan_id": "pack_50", "ref": None},
        PURCHASE_COMPLETED: {
            "plan_id": "pack_50",
            "price_usd": 9.0,
            "credits": 50,
            "is_renewal": False,
            "referral_code": None,
        },
        SUBSCRIPTION_CANCELLED: {"plan_id": "sub_monthly", "period_end": stamp.isoformat()},
        REFUND_ISSUED: {
            "amount_usd": 9.0,
            "reason": "requested_by_customer",
            "credits_removed": 50,
            "commission_voided": False,
        },
        NPS_SUBMITTED: {"score": 9, "comment": "test event"},
        REFERRAL_JOINED: {"friend_user_id": str(uuid4()), "source": "web", "bonus_credits": 2},
        REFERRAL_REWARDED: {"friend_user_id": str(uuid4()), "credits": 3},
        GIFT_GRANTED: {"gift": "week1", "credits": 2},
    }
    return [
        Event(
            metric,
            user_id,
            email,
            properties,
            unique_id=f"seed:{metric}:{user_id}",
            time=stamp,
        )
        for metric, properties in samples.items()
    ]


async def seed_metrics(settings: Settings, email: str) -> int:
    """Send :func:`sample_events` for a throwaway profile; returns how many were accepted."""
    client = KlaviyoClient(settings)
    events = KlaviyoEvents(client)
    if not events.enabled:
        raise RuntimeError("KLAVIYO_PRIVATE_API_KEY is not set")
    user_id = uuid4()
    accepted = 0
    try:
        await client.upsert_profile(user_id, email, {"signup_source": "seed", "plan": "free"})
        for event in sample_events(user_id, email):
            accepted += await events.send(event)
    finally:
        await events.aclose()
    return accepted


def main(argv: list[str] | None = None) -> int:
    """``python -m app.services.klaviyo seed --email <address>``: one test event per metric."""
    parser = argparse.ArgumentParser(prog="app.services.klaviyo", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed", help="send one sample event per metric")
    seed.add_argument("--email", required=True, help="profile the sample events are attached to")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    accepted = asyncio.run(seed_metrics(get_settings(), args.email))
    print(f"accepted {accepted} of {len(METRICS)} sample events")
    return 0 if accepted == len(METRICS) else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "CHECKOUT_STARTED",
    "CREDITS_EXHAUSTED",
    "GIFT_GRANTED",
    "KLAVIYO_API_BASE",
    "KLAVIYO_REVISION",
    "METRICS",
    "MORPH_COMPLETED",
    "MORPH_FAILED",
    "NPS_SUBMITTED",
    "PLUGIN_INSTALLED",
    "PURCHASE_COMPLETED",
    "REFERRAL_JOINED",
    "REFERRAL_REWARDED",
    "REFUND_ISSUED",
    "SIGNED_UP",
    "SUBSCRIPTION_CANCELLED",
    "Event",
    "KlaviyoClient",
    "KlaviyoError",
    "KlaviyoEvents",
    "iso_utc",
    "sample_events",
    "seed_metrics",
]
