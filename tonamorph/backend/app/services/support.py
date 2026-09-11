"""The support read view (docs/API_CONTRACT.md §15): one row per profile from
``support_user_overview``, looked up by user id or by email for the founder's macros."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

from app.schemas import SupportUserOverview
from app.services.supabase import SupabaseClient
from app.services.users import normalise_email

SUPPORT_VIEW = "support_user_overview"


def overview_from_record(record: Mapping[str, Any]) -> SupportUserOverview:
    return SupportUserOverview.model_validate(
        {k: v for k, v in record.items() if k in SupportUserOverview.model_fields}
    )


class SupportService(Protocol):
    async def overview(
        self, *, user_id: UUID | None = None, email: str | None = None
    ) -> SupportUserOverview | None:
        """The view row for the user id, or for the profile holding ``email`` (matched as
        stored: trimmed and lower-cased); ``None`` when neither names a profile."""
        ...


class SupabaseSupportService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def overview(
        self, *, user_id: UUID | None = None, email: str | None = None
    ) -> SupportUserOverview | None:
        if user_id is not None:
            filters = [("user_id", "eq", str(user_id))]
        elif email:
            filters = [("email", "eq", normalise_email(email))]
        else:
            return None
        rows = await self._client.select(SUPPORT_VIEW, filters=filters, limit=1)
        return overview_from_record(rows[0]) if rows else None


__all__ = ["SUPPORT_VIEW", "SupabaseSupportService", "SupportService", "overview_from_record"]
