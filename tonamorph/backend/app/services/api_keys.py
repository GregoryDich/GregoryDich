"""``api_keys`` rows over PostgREST (§11); hashing lives in ``app.auth.api_keys``."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.auth.api_keys import hash_api_key, is_well_formed
from app.errors import INTERNAL_ERROR, ApiException
from app.schemas import ApiKeyCreateResponse, ApiKeyInfo
from app.services.supabase import SupabaseClient

API_KEY_INFO_COLUMNS = ",".join(ApiKeyInfo.model_fields)
"""The listed columns; ``key_hash`` is deliberately not among them."""


def api_key_info_from_record(record: Mapping[str, Any]) -> ApiKeyInfo:
    return ApiKeyInfo.model_validate(
        {k: v for k, v in record.items() if k in ApiKeyInfo.model_fields}
    )


class SupabaseApiKeysService:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def create(self, user_id: UUID, name: str) -> ApiKeyCreateResponse:
        rows = await self._client.rpc(
            "create_api_key", {"p_user_id": str(user_id), "p_name": name}
        )
        if not isinstance(rows, list) or not rows:
            raise ApiException(INTERNAL_ERROR, message="API key could not be created.")
        row = rows[0]
        return ApiKeyCreateResponse(
            id=row["id"],
            name=name,
            prefix=row["prefix"],
            key=row["plaintext"],
            created_at=datetime.now(UTC),
        )

    async def list(self, user_id: UUID) -> list[ApiKeyInfo]:
        rows = await self._client.select(
            "api_keys",
            filters=[("user_id", "eq", str(user_id))],
            columns=API_KEY_INFO_COLUMNS,
            order="created_at.desc",
        )
        return [api_key_info_from_record(row) for row in rows]

    async def revoke(self, user_id: UUID, key_id: UUID) -> bool:
        revoked = await self._client.rpc(
            "revoke_api_key", {"p_key_id": str(key_id), "p_user_id": str(user_id)}
        )
        return bool(revoked)

    async def resolve(self, plaintext: str) -> UUID | None:
        if not is_well_formed(plaintext):
            return None
        owner = await self._client.rpc(
            "authenticate_api_key", {"p_key_hash": hash_api_key(plaintext)}
        )
        return UUID(str(owner)) if owner else None


__all__ = ["API_KEY_INFO_COLUMNS", "SupabaseApiKeysService", "api_key_info_from_record"]
