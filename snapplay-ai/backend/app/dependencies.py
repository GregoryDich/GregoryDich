"""FastAPI dependencies: the wired services and the authenticated principal (§1, §11)."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from starlette.requests import HTTPConnection

from app.auth import Principal
from app.auth.api_keys import authenticate_api_key
from app.errors import UNAUTHORIZED, ApiException
from app.services.factory import Services

API_KEY_HEADER = "x-api-key"


def get_services(conn: HTTPConnection) -> Services:
    """The :class:`Services` container built once per app in ``create_app``."""
    return conn.app.state.services


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    token = token.strip()
    return token if scheme.lower() == "bearer" and token else None


def credentials_of(conn: HTTPConnection) -> tuple[str | None, str | None]:
    """``(bearer_token, api_key)`` from the request headers."""
    return bearer_token(conn.headers.get("authorization")), conn.headers.get(API_KEY_HEADER)


async def authenticate(
    services: Services, *, bearer: str | None = None, api_key: str | None = None
) -> Principal:
    """Resolve a JWT (preferred) or an API key to a :class:`Principal`, else ``401``.
    A JWT caller's profile is created on first sight (signup credits, §3)."""
    if bearer:
        claims = services.jwt.verify(bearer)
        user_id = UUID(str(claims["sub"]))
        email = str(claims.get("email") or "")
        await services.users.ensure(user_id, email)
        return Principal(user_id=user_id, email=email or None, via="jwt")
    if api_key:
        owner = await authenticate_api_key(api_key, services.api_keys)
        if owner is None:
            raise ApiException(UNAUTHORIZED, message="Invalid API key.")
        return Principal(user_id=owner, email=None, via="api_key")
    raise ApiException(UNAUTHORIZED)


async def get_principal(
    conn: HTTPConnection, services: Services = Depends(get_services)
) -> Principal:
    bearer, api_key = credentials_of(conn)
    return await authenticate(services, bearer=bearer, api_key=api_key)


async def get_optional_principal(
    conn: HTTPConnection, services: Services = Depends(get_services)
) -> Principal | None:
    """``None`` without credentials; invalid credentials are still rejected (§3 plans)."""
    bearer, api_key = credentials_of(conn)
    if not bearer and not api_key:
        return None
    return await authenticate(services, bearer=bearer, api_key=api_key)


async def get_session_principal(principal: Principal = Depends(get_principal)) -> Principal:
    """Routes an API key may not use — keys cannot manage keys (docs/SECURITY.md §2.2)."""
    if principal.via != "jwt":
        raise ApiException(UNAUTHORIZED, message="This route requires a user session.")
    return principal


__all__ = [
    "API_KEY_HEADER",
    "authenticate",
    "bearer_token",
    "credentials_of",
    "get_optional_principal",
    "get_principal",
    "get_services",
    "get_session_principal",
]
