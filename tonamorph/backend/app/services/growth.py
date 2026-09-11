"""The product moments that become Klaviyo events (docs/API_CONTRACT.md §14; GTM plan
Appendix C §3–4), with the properties each metric carries.

Each hook is synchronous and returns at once: it hands a coroutine to
:class:`app.services.klaviyo.KlaviyoEvents`, which runs it in the background. The
coroutine looks up what the event still lacks — the profile's email, ``morphs_total``,
the per-user checkout URLs — and sends. A hook on a disabled emitter costs one ``if``.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from app.schemas import JobStatus, PlanKind
from app.services.klaviyo import (
    CREDITS_EXHAUSTED,
    MORPH_COMPLETED,
    MORPH_FAILED,
    NPS_SUBMITTED,
    PLUGIN_INSTALLED,
    PURCHASE_COMPLETED,
    REFUND_ISSUED,
    SIGNED_UP,
    SUBSCRIPTION_CANCELLED,
    Event,
    KlaviyoEvents,
    iso_utc,
)
from app.services.plans import PlanRecord, PlansService, build_checkout_url
from app.services.quality import QualityService, UserFacts, latency_ms

log = logging.getLogger("tonamorph.growth")

SignupSource = Literal["web", "plugin"]
UTM_FIELDS: tuple[str, ...] = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
)
NOTIFIED_JOB_STATES = frozenset({"succeeded", "failed"})
"""Terminal states that are a morph outcome; a cancellation is the user's own doing."""


@dataclass(frozen=True, slots=True)
class SignupFacts:
    """What the ``Signed Up`` event and the profile's sign-up properties are built from —
    the ``profiles`` row as ``handle_new_user`` filled it."""

    user_id: UUID
    email: str | None
    plan: PlanKind
    created_at: datetime
    referral_code: str | None
    marketing_opt_in: bool
    utm: Mapping[str, str | None]

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SignupFacts:
        created = record.get("created_at")
        if isinstance(created, str):
            created = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if not isinstance(created, datetime):
            created = datetime.now(UTC)
        return cls(
            user_id=UUID(str(record["id"])),
            email=record.get("email") or None,
            plan=record.get("plan") or "free",
            created_at=created if created.tzinfo else created.replace(tzinfo=UTC),
            referral_code=record.get("referral_code"),
            marketing_opt_in=bool(record.get("marketing_opt_in")),
            utm={key: record.get(key) for key in UTM_FIELDS},
        )


def cohort_week(moment: datetime) -> str:
    """ISO week the account was created in, e.g. ``2026-W37`` (a Klaviyo profile property)."""
    year, week, _ = moment.isocalendar()
    return f"{year}-W{week:02d}"


def exhausted_unique_id(user_id: UUID, moment: datetime | None = None) -> str:
    """One ``Credits Exhausted`` per user per UTC day, however often the paywall is hit."""
    day = (moment or datetime.now(UTC)).astimezone(UTC).date().isoformat()
    return f"credits_exhausted:{user_id}:{day}"


class GrowthHooks:
    def __init__(
        self, events: KlaviyoEvents, *, plans: PlansService, quality: QualityService
    ) -> None:
        self._events = events
        self._plans = plans
        self._quality = quality

    @property
    def enabled(self) -> bool:
        return self._events.enabled

    # --- delivery -----------------------------------------------------------------------------

    def _emit(
        self,
        metric: str,
        user_id: UUID,
        email: str | None,
        properties: Mapping[str, Any],
        *,
        unique_id: str,
        profile_properties: Mapping[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        self._events.schedule(
            self._deliver(metric, user_id, email, properties, unique_id, profile_properties)
        )

    async def _deliver(
        self,
        metric: str,
        user_id: UUID,
        email: str | None,
        properties: Mapping[str, Any],
        unique_id: str,
        profile_properties: Mapping[str, Any] | None,
    ) -> None:
        if email is None:
            facts = await self._facts(user_id)
            email = facts.email if facts is not None else None
        await self._events.send(
            Event(
                metric,
                user_id,
                email,
                properties,
                unique_id=unique_id,
                profile_properties=profile_properties,
            )
        )

    async def _facts(self, user_id: UUID) -> UserFacts | None:
        try:
            return await self._quality.user_facts(user_id)
        except Exception:
            log.warning("user facts unavailable for an event", extra={"user_id": str(user_id)})
            return None

    async def _checkout_urls(self, user_id: UUID) -> dict[str, str | None]:
        try:
            plans = await self._plans.list_active()
        except Exception:
            log.warning("plans unavailable for an event", extra={"user_id": str(user_id)})
            return {}
        return {
            f"checkout_url_{plan.id}": build_checkout_url(plan, user_id, None)
            for plan in plans
            if plan.price_cents > 0
        }

    # --- hooks --------------------------------------------------------------------------------

    def signed_up(self, facts: SignupFacts, source: SignupSource) -> None:
        """``Signed Up``: once per account, when the API first meets it (§14)."""
        properties = {
            "user_id": str(facts.user_id),
            "source": source,
            "referral_code": facts.referral_code,
            **dict(facts.utm),
            "marketing_opt_in": facts.marketing_opt_in,
        }
        profile = {
            "signup_source": source,
            "referral_code": facts.referral_code,
            **dict(facts.utm),
            "marketing_opt_in": facts.marketing_opt_in,
            "plan": facts.plan,
            "cohort_week": cohort_week(facts.created_at),
        }
        self._emit(
            SIGNED_UP,
            facts.user_id,
            facts.email,
            properties,
            unique_id=f"signed_up:{facts.user_id}",
            profile_properties=profile,
        )

    def plugin_installed(
        self,
        user_id: UUID,
        email: str | None,
        *,
        plugin_version: str,
        host: str,
        os: str | None,
    ) -> None:
        """``Plugin Installed``: the first ``/v1/me`` from a new version/host pair (§1)."""
        properties = {"os": os, "daw": host, "plugin_version": plugin_version}
        self._emit(
            PLUGIN_INSTALLED,
            user_id,
            email,
            properties,
            unique_id=f"plugin_installed:{user_id}:{plugin_version}:{host}",
            profile_properties=properties,
        )

    def job_finished(self, status: JobStatus, user_id: UUID) -> None:
        """``Morph Completed`` / ``Morph Failed`` at the one seam every backend crosses
        (``JobsService.complete`` / ``fail``), plus ``Credits Exhausted`` when the capture
        left the balance at zero. Replays are deduplicated by the job id."""
        if status.status not in NOTIFIED_JOB_STATES or not self.enabled:
            return
        self._events.schedule(self._job_finished(status, user_id))

    async def _job_finished(self, status: JobStatus, user_id: UUID) -> None:
        facts = await self._facts(user_id)
        email = facts.email if facts is not None else None
        job_id = str(status.job_id)
        if status.status == "succeeded" and status.result is not None:
            result = status.result
            key = result.analysis.key
            morphs_total = facts.morphs_total if facts is not None else None
            await self._events.send(
                Event(
                    MORPH_COMPLETED,
                    user_id,
                    email,
                    {
                        "job_id": job_id,
                        "latency_ms": latency_ms(status),
                        "credits_charged": result.credits_charged,
                        "balance_after": result.balance_after,
                        "morphs_total": morphs_total,
                        "bpm": result.analysis.bpm,
                        "key": f"{key.root} {key.mode}",
                    },
                    unique_id=f"morph_completed:{job_id}",
                    profile_properties={
                        "morphs_total": morphs_total,
                        "first_morph_at": _iso(facts.first_morph_at if facts else None),
                        "last_morph_at": _iso(status.finished_at),
                        "credits_available": result.balance_after,
                    },
                    time=status.finished_at,
                )
            )
            if result.balance_after == 0:
                await self._credits_exhausted(user_id, email, facts, status.finished_at)
            return
        error = status.error
        await self._events.send(
            Event(
                MORPH_FAILED,
                user_id,
                email,
                {
                    "job_id": job_id,
                    "error_code": error.code if error is not None else None,
                    "stage": status.stage,
                    "latency_ms": latency_ms(status),
                },
                unique_id=f"morph_failed:{job_id}",
                time=status.finished_at,
            )
        )

    def credits_refused(self, user_id: UUID, email: str | None) -> None:
        """``Credits Exhausted`` when ``reserve_credits`` answered 402 (§2)."""
        if not self.enabled:
            return
        self._events.schedule(self._credits_refused(user_id, email))

    async def _credits_refused(self, user_id: UUID, email: str | None) -> None:
        facts = await self._facts(user_id)
        await self._credits_exhausted(user_id, email or (facts.email if facts else None), facts)

    async def _credits_exhausted(
        self,
        user_id: UUID,
        email: str | None,
        facts: UserFacts | None,
        moment: datetime | None = None,
    ) -> None:
        plan = facts.plan if facts is not None else "free"
        await self._events.send(
            Event(
                CREDITS_EXHAUSTED,
                user_id,
                email,
                {"plan": plan, **await self._checkout_urls(user_id)},
                unique_id=exhausted_unique_id(user_id, moment),
                profile_properties={"plan": plan, "credits_available": 0},
                time=moment,
            )
        )

    def purchase_completed(
        self,
        user_id: UUID,
        email: str | None,
        *,
        plan: PlanRecord,
        price_usd: float,
        credits: int,
        is_renewal: bool,
        referral_code: str | None,
        unique_id: str,
    ) -> None:
        """``Purchase Completed`` for the one webhook event that pays for a sale (§4)."""
        kind: PlanKind = "subscription" if plan.interval is not None else "credits"
        self._emit(
            PURCHASE_COMPLETED,
            user_id,
            email,
            {
                "plan_id": plan.id,
                "price_usd": price_usd,
                "credits": credits,
                "is_renewal": is_renewal,
                "referral_code": referral_code,
            },
            unique_id=unique_id,
            profile_properties={"plan": kind},
        )

    def subscription_cancelled(
        self,
        user_id: UUID,
        email: str | None,
        *,
        plan_id: str | None,
        period_end: datetime | None,
        unique_id: str,
    ) -> None:
        self._emit(
            SUBSCRIPTION_CANCELLED,
            user_id,
            email,
            {"plan_id": plan_id, "period_end": _iso(period_end)},
            unique_id=unique_id,
        )

    def refund_issued(
        self,
        user_id: UUID,
        email: str | None,
        *,
        amount_usd: float,
        reason: str | None,
        unique_id: str,
    ) -> None:
        """``Refund Issued`` for a provider refund or chargeback (money, not credits)."""
        self._emit(
            REFUND_ISSUED,
            user_id,
            email,
            {"amount_usd": amount_usd, "reason": reason},
            unique_id=unique_id,
        )

    def nps_submitted(
        self,
        user_id: UUID,
        email: str | None,
        *,
        score: int,
        comment: str | None,
        response_id: UUID,
    ) -> None:
        self._emit(
            NPS_SUBMITTED,
            user_id,
            email,
            {"score": score, "comment": comment},
            unique_id=f"nps_submitted:{response_id}",
            profile_properties={"nps_score": score},
        )


def _iso(moment: datetime | None) -> str | None:
    return iso_utc(moment) if moment is not None else None


__all__ = [
    "NOTIFIED_JOB_STATES",
    "UTM_FIELDS",
    "GrowthHooks",
    "SignupFacts",
    "SignupSource",
    "cohort_week",
    "exhausted_unique_id",
]
