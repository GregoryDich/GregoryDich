"""``profiles`` rows over PostgREST (§1, §3, §4), the account export and account deletion
(§1, GDPR Art. 15/17/20)."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.config import Settings
from app.errors import CONFLICT, NOT_FOUND, ApiException
from app.schemas import (
    AccountExport,
    AffiliateExport,
    CommissionExport,
    ExportedUser,
    PlanKind,
    Profile,
    PurchaseExport,
    ReferralCodeExport,
    SubscriptionExport,
)
from app.services import PurgeableStorageService, StorageService
from app.services.api_keys import API_KEY_INFO_COLUMNS, api_key_info_from_record
from app.services.credits import (
    ACTIVE_SUBSCRIPTION_STATUSES,
    SupabaseCreditsService,
    ledger_entry_from_record,
)
from app.services.jobs import job_status_from_record, user_prefix, without_signed_urls
from app.services.supabase import Filter, SupabaseClient

log = logging.getLogger("tonamorph.users")

SIGNUP_SOURCE = "signup"
SIGNUP_NOTE = "Welcome credits"
UNFINISHED_JOBS_MESSAGE = "Wait for your queued and running jobs to finish, then retry."
EXPORT_PAGE_ROWS = 500
"""Rows per PostgREST page while exporting; under Supabase's 1000-row response cap."""


def signup_idempotency_key(user_id: UUID) -> str:
    return f"signup:{user_id}"


def normalise_email(email: str) -> str:
    return email.strip().lower()


def profile_from_record(record: Mapping[str, Any]) -> Profile:
    return Profile(
        id=record["id"],
        email=record.get("email") or "",
        plan=record.get("plan") or "free",
        marketing_opt_in=bool(record.get("marketing_opt_in")),
        referral_code=record.get("referral_code"),
        deleted_at=record.get("deleted_at"),
    )


def exported_user_from_record(record: Mapping[str, Any]) -> ExportedUser:
    base = profile_from_record(record).model_dump(exclude={"deleted_at"})
    extra = {k: record.get(k) for k in ExportedUser.model_fields if k not in base}
    return ExportedUser.model_validate({**base, **extra})


me_user_from_record = profile_from_record
"""Kept under its former name for the callers that only need the §1 user."""


def purchase_export_from_record(record: Mapping[str, Any]) -> PurchaseExport:
    return PurchaseExport.model_validate(
        {k: v for k, v in record.items() if k in PurchaseExport.model_fields}
    )


def subscription_export_from_record(record: Mapping[str, Any]) -> SubscriptionExport:
    return SubscriptionExport.model_validate(
        {k: v for k, v in record.items() if k in SubscriptionExport.model_fields}
    )


async def purge_user_objects(storage: StorageService, user_id: UUID) -> int | None:
    """Remove the user's job objects before the account is deleted (§1). ``None`` when the
    backend cannot list a prefix; those objects then leave with the 24 h lifecycle rule
    (docs/SECURITY.md §5), which is the retention bound either way."""
    if isinstance(storage, PurgeableStorageService):
        return await storage.delete_prefix(user_prefix(user_id))
    log.warning(
        "storage backend cannot purge a prefix; relying on the 24 h lifecycle rule",
        extra={"user_id": str(user_id)},
    )
    return None


class SupabaseUsersService:
    def __init__(self, client: SupabaseClient, settings: Settings) -> None:
        self._client = client
        self._credits = SupabaseCreditsService(client)
        self._signup_credits = settings.free_signup_credits

    async def get(self, user_id: UUID) -> Profile | None:
        rows = await self._client.select("profiles", filters=[("id", "eq", str(user_id))], limit=1)
        return profile_from_record(rows[0]) if rows else None

    async def find_by_email(self, email: str) -> Profile | None:
        rows = await self._client.select(
            "profiles", filters=[("email", "eq", normalise_email(email))], limit=1
        )
        return profile_from_record(rows[0]) if rows else None

    async def ensure(self, user_id: UUID, email: str) -> Profile:
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

    async def set_plan(self, user_id: UUID, plan: PlanKind, renews_at: datetime | None) -> Profile:
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
        return profile_from_record(rows[0])

    async def _select_all(
        self, table: str, filters: list[Filter], key: str, columns: str = "*"
    ) -> list[dict[str, Any]]:
        """Every matching row, paged by the unique column ``key`` so the export is not
        silently cut at PostgREST's row cap."""
        rows: list[dict[str, Any]] = []
        last: Any = None
        while True:
            page_filters = list(filters)
            if last is not None:
                page_filters.append((key, "gt", last))
            page = await self._client.select(
                table,
                filters=page_filters,
                columns=columns,
                order=f"{key}.asc",
                limit=EXPORT_PAGE_ROWS,
            )
            rows.extend(page)
            if len(page) < EXPORT_PAGE_ROWS:
                return rows
            last = page[-1][key]

    async def export(self, user_id: UUID) -> AccountExport:
        rows = await self._client.select("profiles", filters=[("id", "eq", str(user_id))], limit=1)
        if not rows:
            raise ApiException(NOT_FOUND, message="Profile not found.")
        profile = rows[0]
        owner: list[Filter] = [("user_id", "eq", str(user_id))]
        ledger = await self._select_all("credit_ledger", owner, "seq")
        jobs = await self._select_all("jobs", owner, "id")
        purchases = await self._select_all("purchases", owner, "id")
        subscriptions = await self._select_all("subscriptions", owner, "id")
        keys = await self._select_all("api_keys", owner, "id", columns=API_KEY_INFO_COLUMNS)
        affiliates = await self._client.select("affiliates", filters=owner, limit=1)
        affiliate: AffiliateExport | None = None
        if affiliates:
            row = affiliates[0]
            by_affiliate: list[Filter] = [("affiliate_id", "eq", row["id"])]
            codes = await self._select_all("referral_codes", by_affiliate, "id")
            commissions = await self._select_all("affiliate_commissions", by_affiliate, "id")
            affiliate = AffiliateExport(
                code=row["code"],
                commission_rate=float(row["commission_rate"]),
                active=bool(row["active"]),
                payout_details=dict(row.get("payout_details") or {}),
                created_at=row["created_at"],
                referral_codes=[
                    ReferralCodeExport.model_validate(
                        {k: v for k, v in c.items() if k in ReferralCodeExport.model_fields}
                    )
                    for c in codes
                ],
                commissions=[
                    CommissionExport.model_validate(
                        {k: v for k, v in c.items() if k in CommissionExport.model_fields}
                    )
                    for c in commissions
                ],
            )
        statuses = sorted(
            (job_status_from_record(job) for job in jobs),
            key=lambda status: (status.created_at, status.job_id),
            reverse=True,
        )
        return AccountExport(
            exported_at=datetime.now(UTC),
            user=exported_user_from_record(profile),
            balance=await self._credits.get_balance(user_id),
            ledger=[ledger_entry_from_record(row) for row in ledger],
            jobs=[without_signed_urls(status) for status in statuses],
            purchases=[purchase_export_from_record(row) for row in purchases],
            subscriptions=[subscription_export_from_record(row) for row in subscriptions],
            api_keys=[api_key_info_from_record(row) for row in keys],
            affiliate=affiliate,
        )

    async def delete_account(self, user_id: UUID) -> None:
        try:
            deletion = await self._client.rpc("delete_user_account", {"p_user_id": str(user_id)})
        except ApiException as exc:
            if exc.code == CONFLICT:
                raise ApiException(CONFLICT, message=UNFINISHED_JOBS_MESSAGE) from exc
            raise
        kept = deletion.get("ledger_rows_kept") if isinstance(deletion, Mapping) else None
        log.info(
            "account data deleted", extra={"user_id": str(user_id), "ledger_rows_kept": kept}
        )
        await self._client.auth_admin_delete_user(user_id)
        log.info("account identity deleted", extra={"user_id": str(user_id)})


__all__ = [
    "EXPORT_PAGE_ROWS",
    "SIGNUP_NOTE",
    "SIGNUP_SOURCE",
    "UNFINISHED_JOBS_MESSAGE",
    "SupabaseUsersService",
    "exported_user_from_record",
    "me_user_from_record",
    "normalise_email",
    "profile_from_record",
    "purchase_export_from_record",
    "purge_user_objects",
    "signup_idempotency_key",
    "subscription_export_from_record",
]
