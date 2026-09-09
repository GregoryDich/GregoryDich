"""§1 authentication matrix: JWT verification rules and API-key access."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any
from uuid import uuid4

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.jwt import JWKS_TIMEOUT_SECONDS, JwtVerifier
from app.config import Settings, override_settings
from app.errors import ApiException
from app.main import create_app
from app.middleware.rate_limit import AUTH_ATTEMPTS_PER_MIN, auth_bucket_key
from app.routers.auth import signup_response
from app.services.memory import MemoryGoTrue, MemoryStore, SentMail
from app.services.supabase import SupabaseClient
from tests.conftest import TEST_JWT_SECRET

BASE = "http://supabase.test"
CONFIRM_LINK = "http://localhost:3000/auth/confirm"
RESET_LINK = "http://localhost:3000/auth/reset-password"
EMAIL = "newcomer@example.test"
PASSWORD = "correct horse battery"


def bearer(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def gotrue(store: MemoryStore) -> MemoryGoTrue:
    return store.gotrue


@pytest.fixture
def account(gotrue: MemoryGoTrue) -> str:
    """``EMAIL`` signed up and confirmed, as if the link in the email had been clicked."""
    gotrue.signup(EMAIL, PASSWORD, redirect_to=CONFIRM_LINK)
    gotrue.confirm(EMAIL)
    gotrue.outbox.clear()
    return EMAIL


def sign_in(client: TestClient) -> dict[str, Any]:
    response = client.post("/v1/auth/token", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()


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


async def test_alg_none_is_rejected(settings: Settings) -> None:
    verifier = JwtVerifier(settings)
    unsigned = jwt.encode({"sub": str(uuid4()), "aud": "authenticated"}, key="", algorithm="none")
    with pytest.raises(ApiException) as info:
        await verifier.verify_async(unsigned)
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


async def test_rs256_token_is_rejected_by_an_hs256_deployment(settings: Settings) -> None:
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
        await verifier.verify_async(token)
    assert info.value.code == "unauthorized"


async def test_hs256_token_forged_with_the_public_key_is_rejected(settings: Settings) -> None:
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
        await verifier.verify_async(forged)
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
        await verifier.verify_async(token)


def test_a_token_without_an_issuer_is_rejected(client: TestClient) -> None:
    """L4: ``iss`` was only checked when present, so a token minted by another Supabase
    project — or by anyone who learned this project's secret name — passed by omitting it."""
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "aud": "authenticated",
            "exp": int(time.time()) + 60,
            "email": "player@example.test",
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    response = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_a_token_from_another_issuer_is_rejected(
    client: TestClient, mint_jwt: Callable[..., str]
) -> None:
    token = mint_jwt(iss="https://evil.test/auth/v1")
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


async def test_jwks_fetch_does_not_block_the_event_loop(settings: Settings) -> None:
    """L4: ``get_jwk_set`` is synchronous urllib under a lock, so calling it from the
    async auth path froze the whole worker for as long as the JWKS endpoint took."""
    verifier = JwtVerifier(_jwks_settings(settings))
    assert verifier._jwks is not None and verifier._jwks.timeout == JWKS_TIMEOUT_SECONDS

    def slow_signing_key(_: object) -> object:
        time.sleep(0.3)
        raise ApiException("unauthorized", message="Signing keys are unavailable.")

    verifier._signing_key = slow_signing_key  # type: ignore[method-assign, assignment]
    ticks = 0

    async def tick() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

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
        headers={"kid": "unknown"},
    )

    ticker = asyncio.create_task(tick())
    with pytest.raises(ApiException):
        await verifier.verify_async(token)
    ticker.cancel()
    assert ticks >= 5, "the event loop must keep running while the JWKS fetch blocks"


def test_auth_buckets_never_hold_the_submitted_credential(app: FastAPI) -> None:
    limiter = app.state.rate_limits.auth
    limiter.acquire(auth_bucket_key("email", "victim@example.test"))
    limiter.acquire(auth_bucket_key("refresh_token", "s3cret-refresh-token"))
    keys = list(limiter._buckets)
    assert all(len(key.split(":", 1)[1]) == 32 for key in keys)
    assert not any("victim" in key or "s3cret" in key for key in keys)


# --- password and refresh grants over the in-memory GoTrue ---------------------------


def test_auth_token_issues_a_session_the_api_accepts(client: TestClient, account: str) -> None:
    body = sign_in(client)
    assert body["token_type"] == "bearer" and body["expires_in"] == 3600
    assert body["user"]["email"] == account
    me = client.get("/v1/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["user"]["id"] == body["user"]["id"]


def test_wrong_password_and_unknown_address_are_indistinguishable(
    client: TestClient, account: str
) -> None:
    wrong = client.post("/v1/auth/token", json={"email": account, "password": "guess"})
    unknown = client.post(
        "/v1/auth/token", json={"email": "nobody@example.test", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_refresh_rotates_the_token_and_refuses_a_spent_one(
    client: TestClient, account: str
) -> None:
    first = sign_in(client)
    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != first["refresh_token"]
    assert refreshed.json()["user"] == first["user"]
    stale = client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "unauthorized"


def test_the_memory_gotrue_cannot_mint_without_the_jwt_secret(settings: Settings) -> None:
    """Local development without ``SUPABASE_JWT_SECRET`` gets the same answer the
    unconfigured proxy always gave, not an unverifiable token."""
    blank = type(settings.supabase_jwt_secret)("")
    unsigned = settings.model_copy(update={"supabase_jwt_secret": blank})
    with override_settings(unsigned), TestClient(create_app(unsigned)) as client:
        gotrue = client.app.state.services.memory.gotrue
        gotrue.signup(EMAIL, PASSWORD, redirect_to=CONFIRM_LINK)
        gotrue.confirm(EMAIL)
        response = client.post("/v1/auth/token", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 401
    assert "not configured" in response.json()["error"]["message"]


# --- the pre-authentication budget ----------------------------------------------------


@pytest.fixture
def count_grants(gotrue: MemoryGoTrue, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Count what actually reaches GoTrue; nobody is registered, so every attempt fails."""
    seen: list[str] = []
    password_grant, refresh_grant = gotrue.password_grant, gotrue.refresh_grant

    def counted_password(email: str, password: str) -> dict[str, Any]:
        seen.append("password")
        return password_grant(email, password)

    def counted_refresh(token: str) -> dict[str, Any]:
        seen.append("refresh_token")
        return refresh_grant(token)

    monkeypatch.setattr(gotrue, "password_grant", counted_password)
    monkeypatch.setattr(gotrue, "refresh_grant", counted_refresh)
    return seen


def test_password_guessing_is_rate_limited_per_email(
    client: TestClient, count_grants: list[str]
) -> None:
    """M6: neither auth route had any limit, and because the API proxies GoTrue every
    attempt reached it from this server's address — one shared bucket for every user."""
    body = {"email": "victim@example.test", "password": "guess"}
    for _ in range(AUTH_ATTEMPTS_PER_MIN):
        assert client.post("/v1/auth/token", json=body).status_code == 401
    limited = client.post("/v1/auth/token", json=body)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["Retry-After"]) >= 1
    assert len(count_grants) == AUTH_ATTEMPTS_PER_MIN, "GoTrue is shielded"


def test_one_hammered_account_does_not_lock_the_others_out(
    client: TestClient, count_grants: list[str]
) -> None:
    for _ in range(AUTH_ATTEMPTS_PER_MIN + 5):
        client.post("/v1/auth/token", json={"email": "victim@example.test", "password": "x"})
    other = client.post("/v1/auth/token", json={"email": "player@example.test", "password": "x"})
    assert other.status_code == 401, "the budget is per credential, not one global bucket"


def test_the_email_bucket_ignores_case_and_padding(
    client: TestClient, count_grants: list[str]
) -> None:
    for index in range(AUTH_ATTEMPTS_PER_MIN):
        spelling = " Victim@Example.test " if index % 2 else "victim@example.test"
        assert client.post("/v1/auth/token", json={"email": spelling, "password": "x"}).status_code
    assert client.post(
        "/v1/auth/token", json={"email": "VICTIM@EXAMPLE.TEST", "password": "x"}
    ).status_code == 429


def test_refresh_is_rate_limited_per_token(client: TestClient, count_grants: list[str]) -> None:
    body = {"refresh_token": "stolen-token"}
    for _ in range(AUTH_ATTEMPTS_PER_MIN):
        assert client.post("/v1/auth/refresh", json=body).status_code == 401
    assert client.post("/v1/auth/refresh", json=body).status_code == 429
    assert client.post(
        "/v1/auth/refresh", json={"refresh_token": "another"}
    ).status_code == 401


# --- sign-up ------------------------------------------------------------------------------


def test_signup_then_confirm_then_sign_in_shows_the_welcome_credits(
    client: TestClient, gotrue: MemoryGoTrue
) -> None:
    signed = client.post("/v1/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert signed.status_code == 201
    body = signed.json()
    assert body["status"] == "confirmation_pending" and body["session"] is None
    assert body["user"]["email"] == EMAIL
    assert gotrue.outbox == [SentMail("signup", EMAIL, CONFIRM_LINK)]

    early = client.post("/v1/auth/token", json={"email": EMAIL, "password": PASSWORD})
    assert early.status_code == 401
    assert "confirm" in early.json()["error"]["message"].lower()

    gotrue.confirm(EMAIL)
    session = sign_in(client)
    assert session["user"]["id"] == body["user"]["id"]
    me = client.get("/v1/me", headers=bearer(session["access_token"]))
    assert me.status_code == 200
    assert me.json()["user"]["id"] == body["user"]["id"]
    assert me.json()["balance"] == {
        "credits": 3,
        "reserved": 0,
        "available": 3,
        "subscription_renews_at": None,
    }


def test_signup_issues_a_session_when_the_project_auto_confirms(
    client: TestClient, gotrue: MemoryGoTrue
) -> None:
    gotrue.autoconfirm = True
    signed = client.post("/v1/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert signed.status_code == 201
    body = signed.json()
    assert body["status"] == "session" and body["session"]["token_type"] == "bearer"
    assert body["session"]["expires_in"] == 3600 and body["session"]["refresh_token"]
    me = client.get("/v1/me", headers=bearer(body["session"]["access_token"]))
    assert me.status_code == 200 and me.json()["balance"]["available"] == 3
    assert gotrue.outbox == []


def test_signup_discloses_an_existing_confirmed_account(
    client: TestClient, account: str, gotrue: MemoryGoTrue
) -> None:
    """Both GoTrue answers for a taken address — the obfuscated identity-less user when
    confirmation is on, the explicit refusal when it is off — become ``409``."""
    for autoconfirm in (False, True):
        gotrue.autoconfirm = autoconfirm
        taken = client.post("/v1/auth/signup", json={"email": account, "password": "another"})
        assert taken.status_code == 409
        assert taken.json()["error"]["code"] == "conflict"
        assert "already exists" in taken.json()["error"]["message"]
    assert len(gotrue.users) == 1 and gotrue.outbox == []


def test_signup_for_an_unconfirmed_address_resends_the_confirmation(
    client: TestClient, gotrue: MemoryGoTrue
) -> None:
    first = client.post("/v1/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    again = client.post("/v1/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert first.status_code == again.status_code == 201
    assert again.json() == first.json()
    assert len(gotrue.users) == 1
    assert gotrue.outbox == [SentMail("signup", EMAIL, CONFIRM_LINK)] * 2


def test_signup_forwards_the_password_policy(client: TestClient, gotrue: MemoryGoTrue) -> None:
    response = client.post("/v1/auth/signup", json={"email": EMAIL, "password": "short"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "at least 6 characters" in response.json()["error"]["message"]
    assert gotrue.users == {}


def test_lifecycle_routes_validate_the_address_before_gotrue(
    client: TestClient, gotrue: MemoryGoTrue
) -> None:
    for address in ("not-an-address", "@example.test", "user@", "a" * 260 + "@example.test"):
        assert client.post(
            "/v1/auth/signup", json={"email": address, "password": PASSWORD}
        ).status_code == 422
        assert client.post("/v1/auth/recover", json={"email": address}).status_code == 422
        assert client.post("/v1/auth/resend", json={"email": address}).status_code == 422
    assert gotrue.users == {} and gotrue.outbox == []


def test_signup_shares_the_per_address_budget_with_password_guessing(
    client: TestClient, gotrue: MemoryGoTrue
) -> None:
    """Sign-up draws on the same bucket as ``/token``, so it can neither enumerate nor
    send mail faster than password guessing can."""
    body = {"email": EMAIL, "password": PASSWORD}
    for _ in range(AUTH_ATTEMPTS_PER_MIN):
        assert client.post("/v1/auth/signup", json=body).status_code == 201
    limited = client.post("/v1/auth/signup", json=body)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["Retry-After"]) >= 1
    assert len(gotrue.outbox) == AUTH_ATTEMPTS_PER_MIN, "GoTrue is shielded"
    assert client.post("/v1/auth/token", json=body).status_code == 429
    other = client.post(
        "/v1/auth/signup", json={"email": "someone@example.test", "password": PASSWORD}
    )
    assert other.status_code == 201


def test_an_unexpected_signup_body_is_a_server_error() -> None:
    with pytest.raises(ApiException) as info:
        signup_response({"msg": "nothing useful"})
    assert info.value.status == 500


# --- recovery and confirmation resend ----------------------------------------------------


def test_recover_sends_the_reset_link_to_the_website(
    client: TestClient, account: str, gotrue: MemoryGoTrue
) -> None:
    response = client.post("/v1/auth/recover", json={"email": account})
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    assert gotrue.outbox == [SentMail("recovery", account, RESET_LINK)]


def test_recover_answers_an_unknown_address_identically(
    client: TestClient, account: str, gotrue: MemoryGoTrue
) -> None:
    known = client.post("/v1/auth/recover", json={"email": account})
    unknown = client.post("/v1/auth/recover", json={"email": "nobody@example.test"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert [mail.email for mail in gotrue.outbox] == [account]


def test_recover_is_rate_limited_per_address(client: TestClient) -> None:
    body = {"email": "victim@example.test"}
    for _ in range(AUTH_ATTEMPTS_PER_MIN):
        assert client.post("/v1/auth/recover", json=body).status_code == 200
    limited = client.post("/v1/auth/recover", json=body)
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) >= 1
    assert client.post("/v1/auth/recover", json={"email": "other@example.test"}).status_code == 200


def test_resend_repeats_the_confirmation_only_while_unconfirmed(
    client: TestClient, gotrue: MemoryGoTrue
) -> None:
    gotrue.signup(EMAIL, PASSWORD, redirect_to=CONFIRM_LINK)
    pending = client.post("/v1/auth/resend", json={"email": EMAIL, "type": "signup"})
    assert pending.status_code == 200 and pending.json() == {"status": "ok"}
    assert gotrue.outbox[-1] == SentMail("signup", EMAIL, CONFIRM_LINK)

    gotrue.confirm(EMAIL)
    sent = len(gotrue.outbox)
    confirmed = client.post("/v1/auth/resend", json={"email": EMAIL})
    unknown = client.post("/v1/auth/resend", json={"email": "nobody@example.test"})
    assert confirmed.status_code == unknown.status_code == 200
    assert confirmed.json() == unknown.json() == pending.json()
    assert len(gotrue.outbox) == sent


def test_resend_accepts_only_the_signup_type(client: TestClient) -> None:
    response = client.post("/v1/auth/resend", json={"email": EMAIL, "type": "sms"})
    assert response.status_code == 422


def test_resend_is_rate_limited_per_address(client: TestClient) -> None:
    body = {"email": "victim@example.test"}
    for _ in range(AUTH_ATTEMPTS_PER_MIN):
        assert client.post("/v1/auth/resend", json=body).status_code == 200
    assert client.post("/v1/auth/resend", json=body).status_code == 429
    assert client.post("/v1/auth/resend", json={"email": "other@example.test"}).status_code == 200


# --- logout ----------------------------------------------------------------------------


def test_logout_revokes_the_refresh_token(client: TestClient, account: str) -> None:
    session = sign_in(client)
    out = client.post("/v1/auth/logout", headers=bearer(session["access_token"]))
    assert out.status_code == 200 and out.json() == {"status": "ok"}
    stale = client.post("/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert stale.status_code == 401


def test_logout_requires_a_user_session(
    client: TestClient, auth: dict[str, str], registered_user: object
) -> None:
    assert client.post("/v1/auth/logout").status_code == 401
    key = client.post("/v1/api-keys", json={"name": "ci"}, headers=auth).json()["key"]
    with_key = client.post("/v1/auth/logout", headers={"X-API-Key": key})
    assert with_key.status_code == 401
    assert client.post("/v1/auth/logout", headers=auth).status_code == 200


# --- the Supabase client's GoTrue calls -------------------------------------------------


@pytest.fixture
async def supabase(settings: Settings) -> AsyncIterator[SupabaseClient]:
    client = SupabaseClient(settings, backoff_seconds=0.0)
    yield client
    await client.aclose()


def _sent_json(route: respx.Route) -> dict[str, Any]:
    return json.loads(route.calls.last.request.content)


@respx.mock
async def test_signup_request_carries_the_confirmation_redirect(supabase: SupabaseClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/signup").mock(
        return_value=httpx.Response(200, json={"id": "u", "email": "a@b.c", "identities": [{}]})
    )
    body = await supabase.auth_signup("a@b.c", "hunter22", redirect_to="https://site.test/auth/confirm")
    assert body["id"] == "u"
    request = route.calls.last.request
    assert request.url.params["redirect_to"] == "https://site.test/auth/confirm"
    assert _sent_json(route) == {"email": "a@b.c", "password": "hunter22"}
    assert request.headers["apikey"] == "anon-test"
    assert "authorization" not in request.headers


@respx.mock
async def test_signup_refusals_are_mapped(supabase: SupabaseClient) -> None:
    codes = {409: "conflict", 422: "validation_error", 429: "rate_limited"}
    cases = [
        (422, {"error_code": "user_already_exists", "msg": "User already registered"}, 409),
        (422, {"msg": "User already registered"}, 409),  # releases before error_code existed
        (422, {"error_code": "weak_password", "msg": "Password should be at least 6 chars."}, 422),
        (400, {"error_code": "validation_failed", "msg": "Unable to validate email address"}, 422),
        (422, {"error_code": "signup_disabled", "msg": "Signups not allowed"}, 422),
        (400, {"error_code": "bad_json", "msg": "could not parse"}, 422),
        (429, {"error_code": "over_email_send_rate_limit", "msg": "slow down"}, 429),
    ]
    for status, payload, expected in cases:
        respx.post(f"{BASE}/auth/v1/signup").mock(return_value=httpx.Response(status, json=payload))
        with pytest.raises(ApiException) as info:
            await supabase.auth_signup("a@b.c", "x", redirect_to="r")
        assert (info.value.status, info.value.code) == (expected, codes[expected]), payload
        if payload.get("error_code") in ("weak_password", "validation_failed"):
            assert info.value.message == payload["msg"], "GoTrue's own wording is forwarded"
        else:
            assert info.value.message != payload["msg"]
    assert info.value.headers == {"Retry-After": "60", "X-RateLimit-Remaining": "0"}


@respx.mock
async def test_signup_is_never_replayed(supabase: SupabaseClient) -> None:
    """A replay would send a second confirmation email."""
    route = respx.post(f"{BASE}/auth/v1/signup").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"id": "u"})]
    )
    with pytest.raises(ApiException) as info:
        await supabase.auth_signup("a@b.c", "x", redirect_to="r")
    assert info.value.status == 500 and route.call_count == 1


@respx.mock
async def test_recover_and_resend_carry_their_redirects_and_swallow_refusals(
    supabase: SupabaseClient,
) -> None:
    recover = respx.post(f"{BASE}/auth/v1/recover").mock(return_value=httpx.Response(200, json={}))
    resend = respx.post(f"{BASE}/auth/v1/resend").mock(return_value=httpx.Response(200, json={}))
    await supabase.auth_recover("a@b.c", redirect_to="https://site.test/auth/reset-password")
    await supabase.auth_resend("a@b.c", "signup", redirect_to="https://site.test/auth/confirm")
    assert recover.calls.last.request.url.params["redirect_to"] == "https://site.test/auth/reset-password"
    assert _sent_json(recover) == {"email": "a@b.c"}
    assert resend.calls.last.request.url.params["redirect_to"] == "https://site.test/auth/confirm"
    assert _sent_json(resend) == {"email": "a@b.c", "type": "signup"}
    assert recover.calls.last.request.headers["apikey"] == "anon-test"

    # GoTrue's send-frequency 429 only ever happens for a known address, so it must not
    # surface; neither may any other refusal.
    recover.mock(
        return_value=httpx.Response(429, json={"error_code": "over_email_send_rate_limit"})
    )
    resend.mock(return_value=httpx.Response(400, json={"error_code": "validation_failed"}))
    assert await supabase.auth_recover("a@b.c", redirect_to="r") is None
    assert await supabase.auth_resend("a@b.c", "signup", redirect_to="r") is None

    recover.mock(return_value=httpx.Response(503))
    with pytest.raises(ApiException) as info:
        await supabase.auth_recover("a@b.c", redirect_to="r")
    assert info.value.status == 500 and recover.call_count == 3


@respx.mock
async def test_logout_revokes_as_the_user(supabase: SupabaseClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/logout").mock(return_value=httpx.Response(204))
    await supabase.auth_logout("the-jwt")
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer the-jwt"
    assert request.headers["apikey"] == "anon-test"
    assert request.url.params["scope"] == "local"

    route.mock(return_value=httpx.Response(401, json={"error_code": "session_not_found"}))
    assert await supabase.auth_logout("the-jwt") is None
    route.mock(return_value=httpx.Response(500))
    with pytest.raises(ApiException):
        await supabase.auth_logout("the-jwt")


@respx.mock
async def test_password_grant_names_only_the_unconfirmed_case(supabase: SupabaseClient) -> None:
    route = respx.post(f"{BASE}/auth/v1/token").mock(
        return_value=httpx.Response(
            400, json={"error_code": "email_not_confirmed", "msg": "Email not confirmed"}
        )
    )
    with pytest.raises(ApiException) as info:
        await supabase.auth_grant("password", {"email": "a@b.c", "password": "x"})
    assert info.value.status == 401 and "confirm" in info.value.message.lower()

    route.mock(
        return_value=httpx.Response(
            400, json={"error": "invalid_grant", "error_description": "Email not confirmed"}
        )
    )
    with pytest.raises(ApiException) as info:
        await supabase.auth_grant("password", {"email": "a@b.c", "password": "x"})
    assert "confirm" in info.value.message.lower(), "pre-error_code releases"

    route.mock(
        return_value=httpx.Response(
            400, json={"error_code": "invalid_credentials", "msg": "Invalid login credentials"}
        )
    )
    with pytest.raises(ApiException) as info:
        await supabase.auth_grant("password", {"email": "a@b.c", "password": "x"})
    assert info.value.message == "Invalid credentials."


@respx.mock
def test_signup_route_proxies_gotrue_with_the_configured_site(settings: Settings) -> None:
    """Outside tests the router talks to the real client: the redirect it sends comes from
    ``AUTH_SITE_URL`` and GoTrue's bare-user answer becomes ``confirmation_pending``."""
    live = settings.model_copy(update={"env": "development", "auth_site_url": "https://site.test/"})
    respx.get(f"{BASE}/rest/v1/plans").mock(return_value=httpx.Response(200, json=[]))
    user_id = str(uuid4())
    route = respx.post(f"{BASE}/auth/v1/signup").mock(
        return_value=httpx.Response(
            200, json={"id": user_id, "email": "a@b.c", "identities": [{"provider": "email"}]}
        )
    )
    with override_settings(live), TestClient(create_app(live)) as client:
        assert client.app.state.services.memory is None
        response = client.post("/v1/auth/signup", json={"email": "a@b.c", "password": "hunter22"})
        fake_user = {"id": str(uuid4()), "email": "a@b.c", "identities": []}
        obfuscated = respx.post(f"{BASE}/auth/v1/signup").mock(
            return_value=httpx.Response(200, json=fake_user)
        )
        taken = client.post("/v1/auth/signup", json={"email": "a@b.c", "password": "hunter22"})
    assert response.status_code == 201
    assert response.json() == {
        "status": "confirmation_pending",
        "user": {"id": user_id, "email": "a@b.c"},
        "session": None,
    }
    assert route.calls[0].request.url.params["redirect_to"] == "https://site.test/auth/confirm"
    assert taken.status_code == 409 and obfuscated.called
