"""Plans (§3): the ``plans`` table and per-caller checkout URLs."""

from __future__ import annotations

import re
from typing import Any, Protocol
from urllib.parse import quote
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.schemas import PlanInfo, PlanInterval
from app.services.supabase import SupabaseClient

CHECKOUT_PROVIDERS: tuple[str, ...] = ("lemonsqueezy", "paddle")
REFERRAL_CODE_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
"""Referral codes as ``referral_codes.code`` holds them: letters, digits, ``-`` and ``_``.

Anything else is refused rather than interpolated: a ``ref`` carrying ``&`` or ``=`` would
otherwise append parameters of its own to the checkout URL — a second
``checkout[custom][user_id]`` wins under last-value-wins parsing and redirects the credits
(and the commission) of someone else's payment to the attacker (§3, §4).
"""
_REFERRAL_CODE = re.compile(REFERRAL_CODE_PATTERN)


def is_referral_code(value: str | None) -> bool:
    return value is not None and _REFERRAL_CODE.match(value) is not None


def _encoded(value: str | None) -> str:
    """Percent-encode a value for a URL, reserved characters included."""
    return quote(value, safe="") if value else ""


class PlanRecord(BaseModel):
    """A ``plans`` row; ``provider_variant_ids`` maps provider → variant / price id."""

    id: str
    name: str
    credits: int
    price_cents: int
    currency: str = "USD"
    interval: PlanInterval | None = None
    provider_variant_ids: dict[str, str] = {}
    checkout_url_template: str | None = None
    active: bool = True
    sort_order: int = 0

    @field_validator("provider_variant_ids", mode="before")
    @classmethod
    def _stringify(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items() if v is not None}
        return value or {}

    def variant_id(self, provider: str) -> str | None:
        return self.provider_variant_ids.get(provider)

    def to_plan_info(self, checkout_url: str | None) -> PlanInfo:
        return PlanInfo(
            id=self.id,
            name=self.name,
            credits=self.credits,
            price_usd=self.price_cents / 100,
            interval=self.interval,
            checkout_url=checkout_url,
        )


class PlansService(Protocol):
    async def list_active(self) -> list[PlanRecord]: ...

    async def get(self, plan_id: str) -> PlanRecord | None: ...

    async def find_by_variant(self, provider: str, variant_id: str) -> PlanRecord | None:
        """The plan whose ``provider_variant_ids[provider]`` equals ``variant_id``."""
        ...


def build_checkout_url(plan: PlanRecord, user_id: UUID | None, ref: str | None) -> str | None:
    """Fill ``{variant_id}``, ``{user_id}`` and ``{ref}`` in the plan's template and drop
    query parameters left empty (an anonymous caller gets no ``user_id`` parameter, §3).
    ``None`` when the plan has no template or needs a variant id that is not configured.

    Every substituted value is percent-encoded, and a ``ref`` that is not a referral code
    is dropped: an interpolated value must never be able to add a parameter of its own."""
    template = plan.checkout_url_template
    if not template:
        return None
    variant = next((plan.variant_id(p) for p in CHECKOUT_PROVIDERS if plan.variant_id(p)), None)
    if "{variant_id}" in template and not variant:
        return None
    url = (
        template.replace("{variant_id}", _encoded(variant))
        .replace("{user_id}", _encoded(str(user_id) if user_id else None))
        .replace("{ref}", _encoded(ref if is_referral_code(ref) else None))
    )
    base, _, query = url.partition("?")
    kept = [pair for pair in query.split("&") if pair and pair.partition("=")[2] != ""]
    return f"{base}?{'&'.join(kept)}" if kept else base


class SupabasePlansService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def list_active(self) -> list[PlanRecord]:
        rows = await self._client.select(
            "plans", filters=[("active", "eq", True)], order="sort_order.asc"
        )
        return [PlanRecord.model_validate(row) for row in rows]

    async def get(self, plan_id: str) -> PlanRecord | None:
        rows = await self._client.select("plans", filters=[("id", "eq", plan_id)], limit=1)
        return PlanRecord.model_validate(rows[0]) if rows else None

    async def find_by_variant(self, provider: str, variant_id: str) -> PlanRecord | None:
        for plan in await self.list_active():
            if plan.variant_id(provider) == variant_id:
                return plan
        return None


__all__ = [
    "CHECKOUT_PROVIDERS",
    "REFERRAL_CODE_PATTERN",
    "PlanRecord",
    "PlansService",
    "SupabasePlansService",
    "build_checkout_url",
    "is_referral_code",
]
