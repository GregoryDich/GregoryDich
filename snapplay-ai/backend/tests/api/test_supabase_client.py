"""The PostgREST / Storage / GoTrue client: filters, error mapping and retries."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from app.config import Settings
from app.errors import ApiException
from app.services.supabase import (
    SupabaseClient,
    credit_counters,
    encode_filters,
    postgrest_error,
    rpc_is_retryable,
)

BASE = "http://supabase.test"


@pytest.fixture
def supabase(settings: Settings) -> SupabaseClient:
    return SupabaseClient(settings, backoff_seconds=0.0)


def test_filters_are_encoded_as_parameters_never_interpolated() -> None:
    params = encode_filters(
        [
            ("user_id", "eq", "3f6c"),
            ("status", "in", ["active", "past, due"]),
            ("seq", "lt", 42),
            ("active", "eq", True),
        ]
    )
    assert params == {
        "user_id": "eq.3f6c",
        "status": 'in.(active,"past, due")',
        "seq": "lt.42",
        "active": "eq.true",
    }


def test_sqlstate_mapping() -> None:
    insufficient = postgrest_error(400, {"code": "P0402", "details": "available=0 requested=1"})
    assert insufficient.status == 402 and insufficient.code == "insufficient_credits"
    assert insufficient.details == {"available": 0, "requested": 1}
    assert insufficient.message == "You have 0 credits."
    assert postgrest_error(400, {"code": "P0404"}).status == 404
    assert postgrest_error(400, {"code": "P0409"}).status == 409
    assert postgrest_error(400, {"code": "42501"}).status == 403
    assert postgrest_error(400, {"code": "22023"}).status == 422
    unknown = postgrest_error(400, {"code": "XX000", "message": "boom"})
    assert unknown.status == 500 and unknown.code == "internal_error"
    assert "boom" not in unknown.message


@respx.mock
async def test_rpc_sends_named_parameters(supabase: SupabaseClient) -> None:
    route = respx.post(f"{BASE}/rest/v1/rpc/reserve_credits").mock(
        return_value=httpx.Response(200, json={"credits": 3, "reserved": 1, "available": 2})
    )
    body = await supabase.rpc("reserve_credits", {"p_user_id": "u", "p_job_id": "j", "p_amount": 1})
    assert body == {"credits": 3, "reserved": 1, "available": 2}
    request = route.calls.last.request
    assert request.headers["apikey"] == "service-role-test"
    assert request.headers["authorization"] == "Bearer service-role-test"
    await supabase.aclose()


@respx.mock
async def test_5xx_is_retried_then_mapped(supabase: SupabaseClient) -> None:
    route = respx.get(f"{BASE}/rest/v1/jobs").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json=[{"id": "job"}]),
        ]
    )
    rows = await supabase.select("jobs", filters=[("id", "eq", "job")])
    assert rows == [{"id": "job"}] and route.call_count == 2

    respx.get(f"{BASE}/rest/v1/jobs").mock(return_value=httpx.Response(500, json={}))
    with pytest.raises(ApiException) as info:
        await supabase.select("jobs", filters=[("id", "eq", "job")])
    assert info.value.status == 500
    await supabase.aclose()


@respx.mock
async def test_transport_errors_become_internal_errors(supabase: SupabaseClient) -> None:
    respx.post(f"{BASE}/rest/v1/rpc/get_balance").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(ApiException) as info:
        await supabase.rpc("get_balance", {"p_user_id": "u"})
    assert info.value.status == 500 and info.value.code == "internal_error"
    await supabase.aclose()


@respx.mock
async def test_storage_upload_and_signed_url(supabase: SupabaseClient) -> None:
    path = "jobs/user/job/input.wav"
    upload = respx.put(f"{BASE}/storage/v1/object/jobs/{path}").mock(
        return_value=httpx.Response(200, json={"Key": path})
    )
    sign = respx.post(f"{BASE}/storage/v1/object/sign/jobs/{path}").mock(
        return_value=httpx.Response(200, json={"signedURL": f"/object/sign/jobs/{path}?token=abc"})
    )
    assert await supabase.storage_upload("jobs", path, b"data", "audio/wav") == path
    assert upload.calls.last.request.content == b"data"
    assert upload.calls.last.request.headers["content-type"] == "audio/wav"

    url = await supabase.storage_signed_url("jobs", path, 3600)
    assert url == f"{BASE}/storage/v1/object/sign/jobs/{path}?token=abc"
    assert json.loads(sign.calls.last.request.content) == {"expiresIn": 3600}
    await supabase.aclose()


@respx.mock
async def test_missing_object_is_404(supabase: SupabaseClient) -> None:
    respx.get(f"{BASE}/storage/v1/object/jobs/missing").mock(return_value=httpx.Response(404))
    with pytest.raises(ApiException) as info:
        await supabase.storage_download("jobs", "missing")
    assert info.value.status == 404
    await supabase.aclose()


@respx.mock
async def test_auth_grant_uses_the_anon_key_and_hides_provider_detail(
    supabase: SupabaseClient,
) -> None:
    route = respx.post(f"{BASE}/auth/v1/token").mock(
        return_value=httpx.Response(200, json={"access_token": "jwt", "user": {"id": "u"}})
    )
    payload: dict[str, Any] = await supabase.auth_grant("password", {"email": "a", "password": "b"})
    assert payload["access_token"] == "jwt"
    request = route.calls.last.request
    assert request.url.params["grant_type"] == "password"
    assert request.headers["apikey"] == "anon-test"
    assert "authorization" not in request.headers

    respx.post(f"{BASE}/auth/v1/token").mock(
        return_value=httpx.Response(400, json={"error_description": "Invalid login credentials"})
    )
    with pytest.raises(ApiException) as info:
        await supabase.auth_grant("password", {"email": "a", "password": "b"})
    assert info.value.status == 401 and "credentials" in info.value.message.lower()
    await supabase.aclose()


@respx.mock
async def test_non_idempotent_rpcs_are_never_replayed(supabase: SupabaseClient) -> None:
    """A retried ``create_job`` without an idempotency key would insert a second job and
    reserve a second credit, stranding the first reservation in ``queued`` forever."""
    route = respx.post(f"{BASE}/rest/v1/rpc/create_job").mock(
        side_effect=[httpx.Response(502), httpx.Response(200, json={"id": "job-b"})]
    )
    with pytest.raises(ApiException) as info:
        await supabase.rpc("create_job", {"p_user_id": "u", "p_idempotency_key": None})
    assert info.value.status == 500 and route.call_count == 1

    respx.post(f"{BASE}/rest/v1/rpc/create_api_key").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(ApiException):
        await supabase.rpc("create_api_key", {"p_user_id": "u", "p_name": "ci"})
    assert respx.calls.call_count == 2
    await supabase.aclose()


@respx.mock
async def test_idempotent_rpcs_are_replayed(supabase: SupabaseClient) -> None:
    keyed = respx.post(f"{BASE}/rest/v1/rpc/create_job").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"id": "job-a"})]
    )
    row = await supabase.rpc("create_job", {"p_user_id": "u", "p_idempotency_key": "k"})
    assert row == {"id": "job-a"} and keyed.call_count == 2

    started = respx.post(f"{BASE}/rest/v1/rpc/start_job").mock(
        side_effect=[httpx.Response(502), httpx.Response(200, json={"id": "job-a"})]
    )
    await supabase.rpc("start_job", {"p_job_id": "job-a", "p_worker_ref": None})
    assert started.call_count == 2
    await supabase.aclose()


def test_retryable_rpcs_are_an_allowlist() -> None:
    assert rpc_is_retryable("get_balance", {}) is True
    assert rpc_is_retryable("settle_reservation", {"p_job_id": "j"}) is True
    assert rpc_is_retryable("cancel_job", {"p_job_id": "j"}) is False
    assert rpc_is_retryable("create_api_key", {"p_user_id": "u"}) is False
    assert rpc_is_retryable("create_job", {"p_idempotency_key": None}) is False
    assert rpc_is_retryable("create_job", {"p_idempotency_key": "k"}) is True


@respx.mock
async def test_auth_grant_is_never_replayed(supabase: SupabaseClient) -> None:
    """A replay spends the caller's budget against GoTrue's own lockout twice."""
    route = respx.post(f"{BASE}/auth/v1/token").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"access_token": "jwt"})]
    )
    with pytest.raises(ApiException) as info:
        await supabase.auth_grant("password", {"email": "a", "password": "b"})
    assert info.value.status == 500 and route.call_count == 1
    await supabase.aclose()


def test_constraint_violations_do_not_leak_database_internals() -> None:
    """23505 names the constraint and the offending value; none of it may reach a client."""
    duplicate = postgrest_error(
        409,
        {
            "code": "23505",
            "message": 'duplicate key value violates unique constraint "profiles_email_key"',
            "details": "Key (email)=(player@example.test) already exists.",
            "hint": None,
        },
    )
    envelope = json.dumps(duplicate.envelope().model_dump(mode="json"))
    assert duplicate.status == 409 and duplicate.code == "conflict"
    assert duplicate.message == "Conflict."
    assert duplicate.details is None
    for secret in ("profiles_email_key", "player@example.test", "duplicate key", "Key ("):
        assert secret not in envelope


def test_only_the_credit_counters_survive_the_detail_string() -> None:
    forbidden = postgrest_error(
        403, {"code": "42501", "message": "permission denied for table credit_ledger"}
    )
    assert forbidden.details is None and "credit_ledger" not in forbidden.message

    noisy = postgrest_error(
        400, {"code": "P0402", "details": "available=0 requested=1 account=fbc0 email=a@b.test"}
    )
    assert noisy.details == {"available": 0, "requested": 1}
    assert noisy.message == "You have 0 credits."
    assert credit_counters("insufficient credits for user fbc0") is None
