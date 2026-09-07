"""§1 authentication matrix: JWT verification rules and API-key access."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth.jwt import JwtVerifier
from app.config import Settings
from app.errors import ApiException
from app.services.factory import Services
from tests.conftest import TEST_JWT_SECRET


def test_valid_hs256_token_is_accepted(client: TestClient, auth: dict[str, str]) -> None:
    assert client.get("/v1/me", headers=auth).status_code == 200


def test_missing_credentials_are_unauthorized(client: TestClient) -> None:
    response = client.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_expired_token_reports_token_expired(
    client: TestClient, mint_jwt: Callable[..., str]
) -> None:
    token = mint_jwt(expires_in=-3600)
    response = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "token_expired"


def test_token_within_leeway_is_accepted(client: TestClient, mint_jwt: Callable[..., str]) -> None:
    assert client.get(
        "/v1/me", headers={"Authorization": f"Bearer {mint_jwt(expires_in=-10)}"}
    ).status_code == 200


def test_wrong_audience_is_rejected(client: TestClient, mint_jwt: Callable[..., str]) -> None:
    token = mint_jwt(aud="anon")
    response = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_wrong_secret_is_rejected(client: TestClient, mint_jwt: Callable[..., str]) -> None:
    token = mint_jwt(secret="not-the-secret")
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_alg_none_is_rejected(settings: Settings) -> None:
    verifier = JwtVerifier(settings)
    unsigned = jwt.encode({"sub": str(uuid4()), "aud": "authenticated"}, key="", algorithm="none")
    with pytest.raises(ApiException) as info:
        verifier.verify(unsigned)
    assert info.value.status == 401 and info.value.code == "unauthorized"


def _b64(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def _forge_hs256(payload: dict[str, object], secret: bytes) -> str:
    """Sign a token with an arbitrary key; PyJWT refuses PEM keys for HMAC, an attacker
    would not."""
    signing_input = (
        _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        + b"."
        + _b64(json.dumps(payload).encode())
    )
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    return (signing_input + b"." + _b64(signature)).decode()


def _jwks_settings(settings: Settings) -> Settings:
    return settings.model_copy(
        update={
            "supabase_jwt_secret": settings.supabase_jwt_secret.__class__(""),
            "supabase_jwks_url": "https://supabase.test/auth/v1/.well-known/jwks.json",
        }
    )


def test_rs256_token_is_rejected_by_an_hs256_deployment(settings: Settings) -> None:
    """Algorithm confusion: an RS256 token must not be verified with the HMAC secret."""
    verifier = JwtVerifier(settings)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    token = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60},
        pem,
        algorithm="RS256",
    )
    with pytest.raises(ApiException) as info:
        verifier.verify(token)
    assert info.value.code == "unauthorized"


def test_hs256_token_forged_with_the_public_key_is_rejected(settings: Settings) -> None:
    """The classic HS/RS confusion attack against a JWKS deployment."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    verifier = JwtVerifier(_jwks_settings(settings))
    forged = _forge_hs256(
        {"sub": str(uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60}, public_pem
    )
    with pytest.raises(ApiException) as info:
        verifier.verify(forged)
    assert info.value.code == "unauthorized"


def test_jwt_subject_must_be_a_uuid(client: TestClient, mint_jwt: Callable[..., str]) -> None:
    token = mint_jwt("not-a-uuid")
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_api_key_authenticates_as_its_owner(
    client: TestClient, auth: dict[str, str], registered_user: object
) -> None:
    created = client.post("/v1/api-keys", json={"name": "ci"}, headers=auth)
    assert created.status_code == 201
    key = created.json()["key"]
    with_key = client.get("/v1/me", headers={"X-API-Key": key})
    assert with_key.status_code == 200
    assert with_key.json()["user"]["id"] == client.get("/v1/me", headers=auth).json()["user"]["id"]


def test_unknown_and_malformed_api_keys_are_rejected(client: TestClient) -> None:
    assert client.get("/v1/me", headers={"X-API-Key": "sp_live_" + "0" * 32}).status_code == 401
    assert client.get("/v1/me", headers={"X-API-Key": "nonsense"}).status_code == 401


async def test_jwks_deployment_pins_algorithms(settings: Settings) -> None:
    verifier = JwtVerifier(_jwks_settings(settings))
    token = jwt.encode({"sub": str(uuid4()), "aud": "authenticated"}, TEST_JWT_SECRET, "HS256")
    with pytest.raises(ApiException):
        verifier.verify(token)


async def test_auth_token_proxies_gotrue(
    services: Services, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    user = {"id": str(uuid4()), "email": "a@b.c"}
    captured: dict[str, object] = {}

    async def fake_grant(grant_type: str, payload: dict[str, object]) -> dict[str, object]:
        captured["grant_type"] = grant_type
        captured["payload"] = payload
        return {
            "access_token": "jwt",
            "refresh_token": "opaque",
            "expires_in": 3600,
            "token_type": "bearer",
            "user": user,
        }

    assert services.supabase is not None
    monkeypatch.setattr(services.supabase, "auth_grant", fake_grant)
    response = client.post("/v1/auth/token", json={"email": "a@b.c", "password": "hunter2"})
    assert response.status_code == 200
    assert response.json()["user"] == user
    assert captured["grant_type"] == "password"
    assert captured["payload"] == {"email": "a@b.c", "password": "hunter2"}


async def test_auth_refresh_maps_provider_401(
    services: Services, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    assert services.supabase is not None

    async def failing_request(*_: object, **__: object) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    monkeypatch.setattr(services.supabase._http, "request", failing_request)
    response = client.post("/v1/auth/refresh", json={"refresh_token": "stale"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
