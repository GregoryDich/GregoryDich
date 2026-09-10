"""§1 account export and deletion, §2 job listing and maintenance mode, §11 key listing —
over the in-memory backend."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.routers.jobs import MAINTENANCE_RETRY_AFTER_SECONDS
from app.routers.me import EXPORT_FILENAME
from app.schemas import ApiKeyInfo
from app.services.memory import MemoryStore, tombstone_email
from app.services.users import UNFINISHED_JOBS_MESSAGE
from tests.api.conftest import USER_EMAIL

pytestmark = pytest.mark.usefixtures("no_rate_limits")


def queued_jobs(store: MemoryStore, user: UUID, count: int) -> list[UUID]:
    """``count`` undispatched jobs, oldest first, one minute apart — except the last two,
    which share a timestamp so the id tie-break is exercised."""
    store.grant_credits(user, count, "test", f"listing:{uuid4()}")
    base = datetime(2026, 9, 1, tzinfo=UTC)
    ids: list[UUID] = []
    for i in range(count):
        row = store.create_job(user, {}, {"input_name": "input.wav"}, None)
        row.created_at = base + timedelta(minutes=min(i, count - 2))
        ids.append(row.id)
    return ids


def test_jobs_are_listed_newest_first_and_paged_by_keyset(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    ids = queued_jobs(store, registered_user, 5)
    expected = [str(j) for j in sorted(ids, key=lambda j: (store.jobs[j].created_at, j))][::-1]

    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        response = client.get("/v1/jobs", params=params, headers=auth)
        assert response.status_code == 200
        body = response.json()
        assert len(body["jobs"]) <= 2
        seen.extend(job["job_id"] for job in body["jobs"])
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert pages == 3 and seen == expected
    assert all(job["status"] == "queued" for job in body["jobs"])

    whole = client.get("/v1/jobs", headers=auth).json()
    assert [job["job_id"] for job in whole["jobs"]] == expected and whole["next_cursor"] is None


def test_job_listing_validates_its_parameters(
    client: TestClient, auth: dict[str, str], registered_user: UUID
) -> None:
    for params in ({"limit": 0}, {"limit": 101}, {"cursor": "yesterday"}):
        response = client.get("/v1/jobs", params=params, headers=auth)
        assert response.status_code == 422, params
        assert response.json()["error"]["code"] == "validation_error"


def test_job_listing_is_scoped_to_the_caller(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    mint_jwt: Callable[..., str],
) -> None:
    queued_jobs(store, registered_user, 2)
    other = {"Authorization": f"Bearer {mint_jwt()}"}
    assert client.get("/v1/jobs", headers=other).json() == {"jobs": [], "next_cursor": None}
    assert len(client.get("/v1/jobs", headers=auth).json()["jobs"]) == 2


def test_api_keys_are_listed_without_any_secret(
    client: TestClient, auth: dict[str, str], registered_user: UUID
) -> None:
    first = client.post("/v1/api-keys", json={"name": "ci"}, headers=auth).json()
    second = client.post("/v1/api-keys", json={"name": "growth"}, headers=auth).json()
    assert client.get("/v1/me", headers={"X-API-Key": first["key"]}).status_code == 200
    assert client.delete(f"/v1/api-keys/{second['id']}", headers=auth).status_code == 204

    listed = client.get("/v1/api-keys", headers=auth)
    assert listed.status_code == 200
    keys = listed.json()["keys"]
    assert [k["name"] for k in keys] == ["growth", "ci"]
    assert all(set(k) == set(ApiKeyInfo.model_fields) for k in keys)
    used, revoked = keys[1], keys[0]
    assert used["prefix"] == first["key"][:12] and used["last_used_at"] is not None
    assert used["revoked_at"] is None and revoked["revoked_at"] is not None
    assert first["key"] not in listed.text and second["key"] not in listed.text

    assert client.get("/v1/api-keys", headers={"X-API-Key": first["key"]}).status_code == 401


def test_export_holds_everything_but_no_object_url(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    submit: Callable[..., Any],
    poll_job: Callable[[str], dict[str, Any]],
) -> None:
    finished = poll_job(submit().json()["job_id"])
    assert finished["result"]["stems"][0]["url"].startswith("memory://")
    key = client.post("/v1/api-keys", json={"name": "ci"}, headers=auth).json()
    store.add_affiliate(registered_user, "MINE", "0.30")
    buyer = uuid4()
    store.ensure_user(buyer, "buyer@example.test")
    store.record_purchase(buyer, "paddle", "txn-b", "pack_50", 900, 800, "mine", {}, "k-b")
    store.record_purchase(
        registered_user, "lemonsqueezy", "ord-1", "pack_50", 900, 800, None, {}, "k"
    )

    response = client.get("/v1/me/export", headers=auth)
    assert response.status_code == 200
    assert response.headers["content-disposition"] == f'attachment; filename="{EXPORT_FILENAME}"'
    export = response.json()
    assert export["user"]["email"] == USER_EMAIL and export["user"]["plan"] == "credits"
    assert export["balance"]["credits"] == 52
    assert [e["entry_type"] for e in export["ledger"]] == ["grant", "reserve", "capture", "grant"]
    assert len(export["jobs"]) == 1 and export["jobs"][0]["job_id"] == finished["job_id"]
    result = export["jobs"][0]["result"]
    assert all(stem["url"] is None for stem in result["stems"]) and result["midi"]["url"] is None
    assert result["analysis"] == finished["result"]["analysis"]
    assert [p["provider_order_id"] for p in export["purchases"]] == ["ord-1"]
    assert export["api_keys"][0]["id"] == key["id"] and key["key"] not in response.text
    assert export["affiliate"]["code"] == "MINE"
    assert export["affiliate"]["referral_codes"][0]["uses"] == 1
    assert export["affiliate"]["commissions"][0]["amount_cents"] == 240
    assert "memory://" not in response.text

    assert client.get("/v1/me/export", headers={"X-API-Key": key["key"]}).status_code == 401


def test_export_is_limited_to_one_per_minute(
    client: TestClient, auth: dict[str, str], registered_user: UUID, mint_jwt: Callable[..., str]
) -> None:
    assert client.get("/v1/me/export", headers=auth).status_code == 200
    again = client.get("/v1/me/export", headers=auth)
    assert again.status_code == 429 and again.json()["error"]["code"] == "rate_limited"
    assert int(again.headers["retry-after"]) > 0
    other = {"Authorization": f"Bearer {mint_jwt()}"}
    assert client.get("/v1/me/export", headers=other).status_code == 200


def test_delete_account_requires_the_confirmation_email(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    for body in ({"confirm": "someone@else.test"}, {"confirm": ""}, {}):
        response = client.request("DELETE", "/v1/me", json=body, headers=auth)
        assert response.status_code == 422, body
        assert response.json()["error"]["code"] == "validation_error"
    assert store.profiles[registered_user].deleted_at is None
    assert client.get("/v1/me", headers=auth).status_code == 200


def test_delete_account_tombstones_the_data_and_ends_the_session(
    client: TestClient, store: MemoryStore, services: Any, wav_5s: bytes
) -> None:
    store.gotrue.autoconfirm = True
    session = client.post(
        "/v1/auth/signup", json={"email": "Leaving@Example.test", "password": "secret-pw"}
    ).json()["session"]
    auth = {"Authorization": f"Bearer {session['access_token']}"}
    user = UUID(client.get("/v1/me", headers=auth).json()["user"]["id"])
    job = client.post("/v1/jobs", files={"audio": ("c.wav", wav_5s, "audio/wav")}, headers=auth)
    assert job.status_code == 202
    deadline = time.monotonic() + 30
    while client.get(f"/v1/jobs/{job.json()['job_id']}", headers=auth).json()["status"] in (
        "queued",
        "running",
    ):
        assert time.monotonic() < deadline, "job did not finish"
        time.sleep(0.05)
    key = client.post("/v1/api-keys", headers=auth).json()["key"]
    prefix = f"jobs/{user}/"
    assert any(path.startswith(prefix) for path in services.storage.objects)
    ledger_rows = sum(1 for row in store.ledger if row.user_id == user)

    deleted = client.request(
        "DELETE", "/v1/me", json={"confirm": "leaving@example.test "}, headers=auth
    )
    assert deleted.status_code == 200 and deleted.json() == {"status": "deleted"}

    profile = store.profiles[user]
    assert profile.deleted_at is not None and profile.email == tombstone_email(user)
    assert store.get_balance(user).model_dump() == {"credits": 0, "reserved": 0, "available": 0}
    mine = [row for row in store.ledger if row.user_id == user]
    assert len(mine) == ledger_rows + 1 and mine[-1].entry_type == "adjust"
    assert mine[-1].amount == -2 and mine[-1].source == "account_deletion"
    assert store.account_deletions[user].ledger_rows_kept == ledger_rows + 1
    assert not any(path.startswith(prefix) for path in services.storage.objects)
    assert not any(k.user_id == user for k in store.api_keys.values())
    scrubbed = next(j for j in store.jobs.values() if j.user_id == user)
    assert scrubbed.status == "succeeded" and scrubbed.result is None and scrubbed.options == {}
    assert user not in store.gotrue.users

    # The still-valid token, the key and the refresh token are all refused from now on.
    for headers in (auth, {"X-API-Key": key}):
        refused = client.get("/v1/me", headers=headers)
        assert refused.status_code == 401 and refused.json()["error"]["code"] == "unauthorized"
    again = client.request("DELETE", "/v1/me", json={"confirm": "x"}, headers=auth)
    assert again.status_code == 401
    refresh = client.post("/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert refresh.status_code == 401
    # The address is free again: a new account starts from scratch, unrelated to the tombstone.
    reborn = client.post(
        "/v1/auth/signup", json={"email": "leaving@example.test", "password": "secret-pw"}
    )
    assert reborn.status_code == 201 and reborn.json()["user"]["id"] != str(user)


def test_delete_account_waits_for_unfinished_jobs(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    queued_job: str,
    registered_user: UUID,
) -> None:
    refused = client.request("DELETE", "/v1/me", json={"confirm": USER_EMAIL}, headers=auth)
    assert refused.status_code == 409
    assert refused.json()["error"] == {
        "code": "conflict",
        "message": UNFINISHED_JOBS_MESSAGE,
        "details": None,
    }
    assert store.profiles[registered_user].deleted_at is None

    assert client.delete(f"/v1/jobs/{queued_job}", headers=auth).status_code == 204
    accepted = client.request("DELETE", "/v1/me", json={"confirm": USER_EMAIL}, headers=auth)
    assert accepted.status_code == 200


def test_delete_account_is_session_only(
    client: TestClient, auth: dict[str, str], registered_user: UUID
) -> None:
    key = client.post("/v1/api-keys", headers=auth).json()["key"]
    response = client.request(
        "DELETE", "/v1/me", json={"confirm": USER_EMAIL}, headers={"X-API-Key": key}
    )
    assert response.status_code == 401


def test_me_reports_the_signup_metadata(client: TestClient, store: MemoryStore) -> None:
    """The website signs up through supabase-js with user metadata; the trigger copies
    it into the profile (§1), keeping the code only when it names an active one."""
    store.ensure_user(uuid4(), "affiliate@example.test")
    affiliate = next(iter(store.profiles))
    store.add_affiliate(affiliate, "GREG30")
    store.gotrue.autoconfirm = True

    def sign_up(email: str, data: dict[str, Any]) -> dict[str, str]:
        session = store.gotrue.signup(email, "secret-pw", redirect_to="x", data=data)
        return {"Authorization": f"Bearer {session['access_token']}"}

    referred = sign_up(
        "referred@example.test",
        {
            "referral_code": " greg30 ",
            "utm_source": "tiktok",
            "utm_campaign": "launch",
            "marketing_opt_in": True,
            "terms_accepted_at": "2026-09-01T10:00:00Z",
        },
    )
    me = client.get("/v1/me", headers=referred).json()
    assert me["user"]["referral_code"] == "GREG30" and me["user"]["marketing_opt_in"] is True
    assert me["balance"]["credits"] == 3
    assert set(me["user"]) == {"id", "email", "plan", "marketing_opt_in", "referral_code"}
    export = client.get("/v1/me/export", headers=referred).json()["user"]
    assert export["utm_source"] == "tiktok" and export["utm_campaign"] == "launch"
    assert export["terms_accepted_at"].startswith("2026-09-01T10:00:00")

    unknown = sign_up("unknown@example.test", {"referral_code": "NOPE", "marketing_opt_in": "yes"})
    me = client.get("/v1/me", headers=unknown).json()["user"]
    assert me["referral_code"] is None and me["marketing_opt_in"] is False

    bare = sign_up("bare@example.test", {})
    me = client.get("/v1/me", headers=bare).json()["user"]
    assert me["referral_code"] is None and me["marketing_opt_in"] is False
    assert store.referral_codes["greg30"].uses == 0


def test_maintenance_mode_pauses_submissions_only(
    settings: Settings, mint_jwt: Callable[..., str], wav_5s: bytes
) -> None:
    paused = settings.model_copy(update={"maintenance_mode": True})
    with TestClient(create_app(paused), raise_server_exceptions=False) as client:
        auth = {"Authorization": f"Bearer {mint_jwt()}"}
        refused = client.post(
            "/v1/jobs", files={"audio": ("c.wav", wav_5s, "audio/wav")}, headers=auth
        )
        assert refused.status_code == 503
        assert refused.headers["retry-after"] == str(MAINTENANCE_RETRY_AFTER_SECONDS)
        error = refused.json()["error"]
        assert error["code"] == "service_unavailable" and "maintenance" in error["message"]
        assert error["details"] == {"retry_after_seconds": MAINTENANCE_RETRY_AFTER_SECONDS}
        assert "x-ratelimit-remaining" not in refused.headers

        me = client.get("/v1/me", headers=auth)
        assert me.status_code == 200 and me.json()["balance"]["reserved"] == 0
        assert client.get("/v1/jobs", headers=auth).status_code == 200
        assert client.get("/v1/plans").status_code == 200
