"""``profiles`` rows over PostgREST (§1, §3, §4)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from app.config import Settings
from app.errors import NOT_FOUND, ApiException
from app.schemas import MeUser, PlanKind
from app.services.credits import ACTIVE_SUBSCRIPTION_STATUSES
from app.services.supabase import SupabaseClient

SIGNUP_SOURCE = "signup"
SIGNUP_NOTE = "Welcome credits"


def signup_idempotency_key(user_id: UUID) -> str:
    return f"signup:{user_id}"


def normalise_email(email: str) -> str:
    return email.strip().lower()


def me_user_from_record(record: Mapping[str, Any]) -> MeUser:
    return MeUser(
        id=record["id"], email=record.get("email") or "", plan=record.get("plan") or "free"
    )


class SupabaseUsersService:
    def __init__(self, client: SupabaseClient, settings: Settings) -> None:
        self._client = client
        self._signup_credits = settings.free_signup_credits

    async def get(self, user_id: UUID) -> MeUser | None:
        rows = await self._client.select("profiles", filters=[("id", "eq", str(user_id))], limit=1)
        return me_user_from_record(rows[0]) if rows else None

    async def find_by_email(self, email: str) -> MeUser | None:
        rows = await self._client.select(
            "profiles", filters=[("email", "eq", normalise_email(email))], limit=1
        )
        return me_user_from_record(rows[0]) if rows else None

    async def ensure(self, user_id: UUID, email: str) -> MeUser:
        """The signup trigger normally creates the profile; this covers accounts that
        predate it. Every step is idempotent, so a concurrent first request is harmless."""
        existing = await self.get(user_id)
        if existing is not None:
            return existing
        await self._client.insert(
            "profiles",
            {"id": str(user_id), "email": normalise_email(email) or None},
            on_conflict="id",
            resolution="ignore-duplicates",
        )
        await self._client.insert(
            "credit_accounts",
            {"user_id": str(user_id)},
            on_conflict="user_id",
            resolution="ignore-duplicates",
        )
        if self._signup_credits > 0:
            await self._client.rpc(
                "grant_credits",
                {
                    "p_user_id": str(user_id),
                    "p_amount": self._signup_credits,
                    "p_source": SIGNUP_SOURCE,
                    "p_idempotency_key": signup_idempotency_key(user_id),
                    "p_note": SIGNUP_NOTE,
                    "p_expires_at": None,
                },
            )
        created = await self.get(user_id)
        if created is None:
            raise ApiException(NOT_FOUND, message="Profile could not be created.")
        return created

    async def set_plan(self, user_id: UUID, plan: PlanKind, renews_at: datetime | None) -> MeUser:
        rows = await self._client.update(
            "profiles", {"plan": plan}, filters=[("id", "eq", str(user_id))]
        )
        if not rows:
            raise ApiException(NOT_FOUND, message="Profile not found.")
        if renews_at is not None:
            await self._client.update(
                "subscriptions",
                {"current_period_end": renews_at.isoformat()},
                filters=[
                    ("user_id", "eq", str(user_id)),
                    ("status", "in", ACTIVE_SUBSCRIPTION_STATUSES),
                ],
            )
        return me_user_from_record(rows[0])


__all__ = [
    "SIGNUP_NOTE",
    "SIGNUP_SOURCE",
    "SupabaseUsersService",
    "me_user_from_record",
    "normalise_email",
    "signup_idempotency_key",
]
