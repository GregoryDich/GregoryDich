"""Earned morphs (docs/API_CONTRACT.md §1, §3, §12; GTM plan §2.4, Appendix B §3):
user referrals — "send a morph to a friend", a programme distinct from the affiliates of
§12 — and the first-week gift.

The credits move inside the database: ``handle_new_user`` links a sign-up to the friend
who invited it and grants the +2 bonus, ``complete_job`` rewards the referrer when the
friend's first morph succeeds, ``grant_week1_gifts()`` gives two credits on day 7. This
module only reads what those functions left behind — the referral summary ``GET /v1/me``
shows, the reward row a ``Referral Rewarded`` event is built from — and runs the gift
function from the reaper task so ``Gift Granted`` can be emitted per user.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.services.supabase import SupabaseClient

REFERRAL_FRIEND_BONUS = 2
"""Extra sign-up credits for the friend, on top of the welcome credits."""
REFERRAL_REWARD = 3
"""Credits the referrer earns when the friend's first morph succeeds."""
REFERRAL_REWARD_CAP_PER_30_DAYS = 10
"""Friends a referrer is rewarded for per 30 days (``reward_referral``, anti-farming)."""
REFERRAL_REWARD_WINDOW_DAYS = 30
REFERRAL_SOURCE = "referral"
REFERRAL_BONUS_SOURCE = "referral_bonus"
REFERRAL_REWARD_NOTE = "A friend's first morph"
REFERRAL_BONUS_NOTE = "Invited by a friend"
REFERRAL_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
"""No 0/O, 1/I/L: a code can be read aloud and typed without ambiguity."""
REFERRAL_CODE_LENGTH = 8
REFERRAL_PATH = "/m/"
"""``<AUTH_SITE_URL>/m/<code>`` is the page a friend lands on (GTM Appendix B §3)."""

WEEK1_GIFT_CREDITS = 2
WEEK1_GIFT_SOURCE = "gift:week1"
WEEK1_GIFT_NOTE = "One week in. Two morphs on us."
WEEK1_GIFT_MIN_DAYS = 7
WEEK1_GIFT_MAX_DAYS = 8


def referral_reward_key(friend_user_id: UUID) -> str:
    """Ledger key of the referrer's reward: one per friend, ever."""
    return f"referral:{friend_user_id}"


def referral_bonus_key(friend_user_id: UUID) -> str:
    return f"referral_bonus:{friend_user_id}"


def week1_gift_key(user_id: UUID) -> str:
    return f"{WEEK1_GIFT_SOURCE}:{user_id}"


def referral_url(site_url: str, code: str) -> str:
    return f"{site_url.rstrip('/')}{REFERRAL_PATH}{code}"


class ReferralSummary(BaseModel):
    """``user_referral_summary``: the caller's code and what it brought in."""

    code: str
    friends_joined: int = 0
    morphs_earned: int = 0


class ReferralReward(BaseModel):
    """The ledger row ``referral:<friend>``: who was rewarded for which friend."""

    referrer_id: UUID
    friend_id: UUID
    credits: int
    created_at: datetime


class RewardsService(Protocol):
    async def referral_summary(self, user_id: UUID) -> ReferralSummary | None:
        """The profile's code, friends joined and credits earned; ``None`` when there is
        no profile. A profile without a code is given one."""
        ...

    async def referral_reward(self, friend_user_id: UUID) -> ReferralReward | None:
        """The reward granted for this friend's first morph, or ``None`` when none was
        (not referred, referrer deleted, or over the 30-day cap)."""
        ...

    async def grant_week1_gifts(self) -> list[UUID]:
        """``grant_week1_gifts()``: the users gifted in this run."""
        ...


def reward_from_ledger_record(record: dict[str, Any]) -> ReferralReward:
    key = str(record["idempotency_key"])
    return ReferralReward(
        referrer_id=UUID(str(record["user_id"])),
        friend_id=UUID(key.removeprefix("referral:")),
        credits=int(record["amount"]),
        created_at=record["created_at"],
    )


class SupabaseRewardsService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def referral_summary(self, user_id: UUID) -> ReferralSummary | None:
        rows = await self._client.rpc("user_referral_summary", {"p_user_id": str(user_id)})
        if not isinstance(rows, list) or not rows:
            return None
        return ReferralSummary.model_validate(rows[0])

    async def referral_reward(self, friend_user_id: UUID) -> ReferralReward | None:
        rows = await self._client.select(
            "credit_ledger",
            filters=[("idempotency_key", "eq", referral_reward_key(friend_user_id))],
            columns="user_id,amount,idempotency_key,created_at",
            limit=1,
        )
        return reward_from_ledger_record(rows[0]) if rows else None

    async def grant_week1_gifts(self) -> list[UUID]:
        rows = await self._client.rpc("grant_week1_gifts", {})
        if not isinstance(rows, list):
            return []
        return [UUID(str(row["user_id"])) for row in rows if isinstance(row, dict)]


__all__ = [
    "REFERRAL_BONUS_NOTE",
    "REFERRAL_BONUS_SOURCE",
    "REFERRAL_CODE_ALPHABET",
    "REFERRAL_CODE_LENGTH",
    "REFERRAL_FRIEND_BONUS",
    "REFERRAL_PATH",
    "REFERRAL_REWARD",
    "REFERRAL_REWARD_CAP_PER_30_DAYS",
    "REFERRAL_REWARD_NOTE",
    "REFERRAL_REWARD_WINDOW_DAYS",
    "REFERRAL_SOURCE",
    "WEEK1_GIFT_CREDITS",
    "WEEK1_GIFT_MAX_DAYS",
    "WEEK1_GIFT_MIN_DAYS",
    "WEEK1_GIFT_NOTE",
    "WEEK1_GIFT_SOURCE",
    "ReferralReward",
    "ReferralSummary",
    "RewardsService",
    "SupabaseRewardsService",
    "referral_bonus_key",
    "referral_reward_key",
    "referral_url",
    "reward_from_ledger_record",
    "week1_gift_key",
]
