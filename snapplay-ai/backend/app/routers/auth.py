"""§1 — GoTrue password-grant proxy."""

from fastapi import APIRouter

from app.errors import NOT_IMPLEMENTED, ApiException
from app.schemas import RefreshRequest, TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def token(body: TokenRequest) -> TokenResponse:
    raise ApiException(NOT_IMPLEMENTED)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    raise ApiException(NOT_IMPLEMENTED)
