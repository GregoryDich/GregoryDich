"""§11 — machine API keys; the plaintext is returned exactly once."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth import Principal
from app.dependencies import get_services, get_session_principal
from app.errors import NOT_FOUND, ApiException
from app.middleware.rate_limit import rate_limit
from app.schemas import ApiKeyCreateRequest, ApiKeyCreateResponse
from app.services.factory import Services

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreateResponse,
    dependencies=[Depends(rate_limit("reads"))],
)
async def create_api_key(
    body: ApiKeyCreateRequest | None = None,
    principal: Principal = Depends(get_session_principal),
    services: Services = Depends(get_services),
) -> ApiKeyCreateResponse:
    request = body or ApiKeyCreateRequest()
    return await services.api_keys.create(principal.user_id, request.name)


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[Depends(rate_limit("reads"))],
)
async def revoke_api_key(
    key_id: UUID,
    principal: Principal = Depends(get_session_principal),
    services: Services = Depends(get_services),
) -> None:
    if not await services.api_keys.revoke(principal.user_id, key_id):
        raise ApiException(NOT_FOUND, message="API key not found.")
