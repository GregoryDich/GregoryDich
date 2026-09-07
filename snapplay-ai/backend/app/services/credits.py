"""Credits (§3, §6) over PostgREST: the SQL functions plus the ledger page."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from app.errors import VALIDATION_ERROR, ApiException
from app.schemas import Balance, CreditBalance, LedgerEntry, LedgerPage
from app.services.supabase import SupabaseClient

ACTIVE_SUBSCRIPTION_STATUSES: tuple[str, ...] = ("active", "trialing")
_LEDGER_FIELDS = frozenset(LedgerEntry.model_fields)


def parse_ledger_cursor(cursor: str | None) -> int | None:
    """The ``cursor`` query parameter is the ``seq`` of the last entry already seen."""
    if cursor is None or cursor == "":
        return None
    if not cursor.isdigit():
        raise ApiException(
            VALIDATION_ERROR,
            details={
                "errors": [
                    {
                        "loc": ["query", "cursor"],
                        "msg": "cursor must be a ledger sequence number",
                        "type": "value_error",
                    }
                ]
            },
        )
    return int(cursor)


def ledger_entry_from_record(record: Mapping[str, Any]) -> LedgerEntry:
    return LedgerEntry.model_validate({k: v for k, v in record.items() if k in _LEDGER_FIELDS})


def ledger_page(rows: list[Mapping[str, Any]], limit: int) -> LedgerPage:
    """``rows`` are newest-first and were fetched with ``limit + 1`` to detect a next page."""
    page = rows[:limit]
    next_cursor = str(page[-1]["seq"]) if len(rows) > limit and page else None
    return LedgerPage(entries=[ledger_entry_from_record(r) for r in page], next_cursor=next_cursor)


class SupabaseCreditsService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def get_balance(self, user_id: UUID) -> Balance:
        raw = await self._client.rpc("get_balance", {"p_user_id": str(user_id)})
        balance = CreditBalance.model_validate(raw)
        rows = await self._client.select(
            "subscriptions",
            filters=[
                ("user_id", "eq", str(user_id)),
                ("status", "in", ACTIVE_SUBSCRIPTION_STATUSES),
            ],
            columns="current_period_end",
            order="current_period_end.desc",
            limit=1,
        )
        renews_at = rows[0].get("current_period_end") if rows else None
        return Balance(**balance.model_dump(), subscription_renews_at=renews_at)

    async def reserve(self, user_id: UUID, job_id: UUID, amount: int = 1) -> CreditBalance:
        raw = await self._client.rpc(
            "reserve_credits",
            {"p_user_id": str(user_id), "p_job_id": str(job_id), "p_amount": amount},
        )
        return CreditBalance.model_validate(raw)

    async def settle(self, job_id: UUID, success: bool) -> CreditBalance:
        raw = await self._client.rpc(
            "settle_reservation", {"p_job_id": str(job_id), "p_success": success}
        )
        return CreditBalance.model_validate(raw)

    async def grant(
        self,
        user_id: UUID,
        amount: int,
        source: str,
        idempotency_key: str,
        note: str | None = None,
        expires_at: datetime | None = None,
    ) -> CreditBalance:
        raw = await self._client.rpc(
            "grant_credits",
            {
                "p_user_id": str(user_id),
                "p_amount": amount,
                "p_source": source,
                "p_idempotency_key": idempotency_key,
                "p_note": note,
                "p_expires_at": expires_at.isoformat() if expires_at else None,
            },
        )
        return CreditBalance.model_validate(raw)

    async def refund_job(self, job_id: UUID, reason: str) -> CreditBalance:
        raw = await self._client.rpc("refund_job", {"p_job_id": str(job_id), "p_reason": reason})
        return CreditBalance.model_validate(raw)

    async def ledger(self, user_id: UUID, limit: int = 50, cursor: str | None = None) -> LedgerPage:
        seq_cursor = parse_ledger_cursor(cursor)
        filters: list[tuple[str, str, Any]] = [("user_id", "eq", str(user_id))]
        if seq_cursor is not None:
            filters.append(("seq", "lt", seq_cursor))
        rows = await self._client.select(
            "credit_ledger", filters=filters, order="seq.desc", limit=limit + 1
        )
        return ledger_page(rows, limit)


__all__ = [
    "ACTIVE_SUBSCRIPTION_STATUSES",
    "SupabaseCreditsService",
    "ledger_entry_from_record",
    "ledger_page",
    "parse_ledger_cursor",
]
