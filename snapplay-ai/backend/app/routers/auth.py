"""§1 — GoTrue password-grant proxy so the plugin only ever talks to this host."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_services
from app.errors import UNAUTHORIZED, ApiException
from app.schemas import AuthUser, RefreshRequest, TokenRequest, TokenResponse
from app.services.factory import Services

router = APIRouter(prefix="/auth", tags=["auth"])

PASSWORD_GRANT = "password"
REFRESH_GRANT = "refresh_token"


def _token_response(payload: dict[str, object]) -> TokenResponse:
    user = payload.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        raise ApiException(UNAUTHORIZED, message="Invalid credentials.")
    return TokenResponse(
        access_token=str(payload.get("access_token") or ""),
        refresh_token=str(payload.get("refresh_token") or ""),
        expires_in=int(payload.get("expires_in") or 0),
        user=AuthUser(id=user["id"], email=str(user.get("email") or "")),
    )


async def _grant(services: Services, grant_type: str, body: dict[str, object]) -> TokenResponse:
    if services.supabase is None:
        raise ApiException(UNAUTHORIZED, message="Authentication is not configured.")
    return _token_response(await services.supabase.auth_grant(grant_type, body))


@router.post("/token", response_model=TokenResponse)
async def token(body: TokenRequest, services: Services = Depends(get_services)) -> TokenResponse:
    return await _grant(
        services, PASSWORD_GRANT, {"email": body.email, "password": body.password}
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest, services: Services = Depends(get_services)
) -> TokenResponse:
    return await _grant(services, REFRESH_GRANT, {"refresh_token": body.refresh_token})
