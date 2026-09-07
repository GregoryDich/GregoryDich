"""§11 — machine API keys."""

from uuid import UUID

from fastapi import APIRouter, status

from app.errors import NOT_IMPLEMENTED, ApiException
from app.schemas import ApiKeyCreateRequest, ApiKeyCreateResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiKeyCreateResponse)
async def create_api_key(body: ApiKeyCreateRequest | None = None) -> ApiKeyCreateResponse:
    raise ApiException(NOT_IMPLEMENTED)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: UUID) -> None:
    raise ApiException(NOT_IMPLEMENTED)
