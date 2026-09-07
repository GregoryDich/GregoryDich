"""Supabase (GoTrue) access-token verification (§1; docs/SECURITY.md §2.1).

The accepted algorithm set is fixed by configuration — ``HS256`` with
``SUPABASE_JWT_SECRET`` or ``RS256``/``ES256`` with ``SUPABASE_JWKS_URL`` — and the token's
``alg`` header is only ever compared against it, never used to pick a key. JWKS keys are
cached in-process for an hour; an unknown ``kid`` triggers at most one refetch per minute.
"""

from __future__ import annotations

import threading
import time
from typing import Any
from uuid import UUID

import jwt
from jwt import PyJWK, PyJWKClient, PyJWKSet

from app.config import Settings
from app.errors import TOKEN_EXPIRED, UNAUTHORIZED, ApiException

AUDIENCE = "authenticated"
LEEWAY_SECONDS = 30
REQUIRED_CLAIMS = ("sub", "exp", "aud")
HS_ALGORITHMS: tuple[str, ...] = ("HS256",)
JWKS_ALGORITHMS: tuple[str, ...] = ("RS256", "ES256")
JWKS_CACHE_SECONDS = 3600
JWKS_REFETCH_INTERVAL_SECONDS = 60


class JwtVerifier:
    def __init__(self, settings: Settings) -> None:
        secret = settings.supabase_jwt_secret.get_secret_value()
        self._secret: str | None = None
        self._jwks: PyJWKClient | None = None
        self._algorithms: tuple[str, ...] = ()
        if secret:
            self._secret = secret
            self._algorithms = HS_ALGORITHMS
        elif settings.supabase_jwks_url:
            self._jwks = PyJWKClient(
                settings.supabase_jwks_url, cache_jwk_set=True, lifespan=JWKS_CACHE_SECONDS
            )
            self._algorithms = JWKS_ALGORITHMS
        base = settings.supabase_url.rstrip("/")
        self._issuer = f"{base}/auth/v1" if base else None
        self._refetch_lock = threading.Lock()
        self._last_refetch = float("-inf")

    @property
    def configured(self) -> bool:
        return bool(self._algorithms)

    def verify(self, token: str) -> dict[str, Any]:
        """Return the claims of a valid token or raise ``unauthorized`` / ``token_expired``."""
        if not self.configured:
            raise ApiException(UNAUTHORIZED, message="Token verification is not configured.")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise ApiException(UNAUTHORIZED, message="Malformed access token.") from exc
        if header.get("alg") not in self._algorithms:
            raise ApiException(UNAUTHORIZED, message="Unsupported token algorithm.")

        key: str | PyJWK = (
            self._secret if self._secret is not None else self._signing_key(header.get("kid"))
        )
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=list(self._algorithms),
                audience=AUDIENCE,
                leeway=LEEWAY_SECONDS,
                options={"require": list(REQUIRED_CLAIMS)},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ApiException(TOKEN_EXPIRED) from exc
        except jwt.PyJWTError as exc:
            raise ApiException(UNAUTHORIZED, message="Invalid access token.") from exc

        if self._issuer and "iss" in claims and claims["iss"] != self._issuer:
            raise ApiException(UNAUTHORIZED, message="Invalid token issuer.")
        try:
            UUID(str(claims["sub"]))
        except ValueError as exc:
            raise ApiException(UNAUTHORIZED, message="Invalid token subject.") from exc
        return claims

    def _signing_key(self, kid: object) -> PyJWK:
        assert self._jwks is not None
        if not isinstance(kid, str) or not kid:
            raise ApiException(UNAUTHORIZED, message="Token has no key id.")
        with self._refetch_lock:
            key = self._match(self._jwk_set(refresh=False), kid)
            if key is None:
                now = time.monotonic()
                if now - self._last_refetch < JWKS_REFETCH_INTERVAL_SECONDS:
                    raise ApiException(UNAUTHORIZED, message="Unknown signing key.")
                self._last_refetch = now
                key = self._match(self._jwk_set(refresh=True), kid)
        if key is None:
            raise ApiException(UNAUTHORIZED, message="Unknown signing key.")
        return key

    def _jwk_set(self, refresh: bool) -> PyJWKSet:
        assert self._jwks is not None
        try:
            return self._jwks.get_jwk_set(refresh=refresh)
        except jwt.PyJWTError as exc:
            raise ApiException(UNAUTHORIZED, message="Signing keys are unavailable.") from exc

    def _match(self, jwk_set: PyJWKSet, kid: str) -> PyJWK | None:
        for candidate in jwk_set.keys:
            if candidate.key_id == kid and (
                candidate.algorithm_name is None or candidate.algorithm_name in self._algorithms
            ):
                return candidate
        return None


__all__ = ["AUDIENCE", "LEEWAY_SECONDS", "JwtVerifier"]
