"""§3 ledger pagination and plans, §11 API-key lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.services.memory import MemoryStore
from app.services.plans import build_checkout_url

pytestmark = pytest.mark.usefixtures("no_rate_limits")


def test_ledger_pagination_walks_the_seq_cursor(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    for i in range(6):
        store.grant_credits(registered_user, 1, "test", f"top-up:{i}", f"top up {i}")

    first = client.get("/v1/credits/ledger", params={"limit": 3}, headers=auth).json()
    assert len(first["entries"]) == 3 and first["next_cursor"] is not None
    second = client.get(
        "/v1/credits/ledger", params={"limit": 3, "cursor": first["next_cursor"]}, headers=auth
    ).json()
    assert len(second["entries"]) == 3 and second["next_cursor"] is not None
    last = client.get(
        "/v1/credits/ledger", params={"limit": 3, "cursor": second["next_cursor"]}, headers=auth
    ).json()
    assert last["entries"] == [] or last["next_cursor"] is None

    seen = [e["id"] for e in first["entries"] + second["entries"] + last["entries"]]
    assert len(seen) == len(set(seen))
    notes = [e["note"] for e in first["entries"]]
    assert notes == ["top up 5", "top up 4", "top up 3"]  # newest first


def test_ledger_is_scoped_to_the_caller(
    client: TestClient, auth: dict[str, str], mint_jwt: Callable[..., str], registered_user: UUID
) -> None:
    other = {"Authorization": f"Bearer {mint_jwt()}"}
    assert client.get("/v1/credits/ledger", headers=other).json()["entries"][0]["amount"] == 3
    mine = client.get("/v1/credits/ledger", headers=auth).json()["entries"]
    assert len(mine) == 1 and mine[0]["entry_type"] == "grant"


def test_ledger_rejects_a_malformed_cursor(client: TestClient, auth: dict[str, str]) -> None:
    response = client.get("/v1/credits/ledger", params={"cursor": "abc"}, headers=auth)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_plans_are_public_without_checkout_urls(client: TestClient, store: MemoryStore) -> None:
    for plan in store.plans.values():
        plan.provider_variant_ids = {"lemonsqueezy": f"var-{plan.id}"}
    body = client.get("/v1/plans").json()
    assert [p["id"] for p in body["plans"]] == ["free", "pack_50", "sub_monthly"]
    free, pack, sub = body["plans"]
    assert free["credits"] == 3 and free["price_usd"] == 0 and free["checkout_url"] is None
    assert pack["price_usd"] == 9.0 and sub["price_usd"] == 7.99 and sub["interval"] == "month"
    assert "user_id" not in (pack["checkout_url"] or "")


def test_plans_attach_the_caller_and_referral_code(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    for plan in store.plans.values():
        plan.provider_variant_ids = {"lemonsqueezy": f"var-{plan.id}"}
    body = client.get("/v1/plans", params={"ref": "friend"}, headers=auth).json()
    pack = next(p for p in body["plans"] if p["id"] == "pack_50")
    assert pack["checkout_url"] is not None
    assert f"checkout[custom][user_id]={registered_user}" in pack["checkout_url"]
    assert "checkout[custom][ref]=friend" in pack["checkout_url"]
    assert "var-pack_50" in pack["checkout_url"]


def test_a_referral_code_cannot_inject_checkout_parameters(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    """§3: ``ref`` is interpolated into the checkout URL. A value carrying ``&`` would add
    a second ``checkout[custom][user_id]``, and last-value-wins parsing would credit the
    attacker for someone else's payment."""
    for plan in store.plans.values():
        plan.provider_variant_ids = {"lemonsqueezy": f"var-{plan.id}"}
    attacker = uuid4()
    rejected = client.get(
        "/v1/plans",
        params={"ref": f"x&checkout[custom][user_id]={attacker}"},
        headers=auth,
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"

    # And nothing that does reach the builder can add a parameter of its own either.
    pack = store.plans["pack_50"]
    url = build_checkout_url(pack, registered_user, f"x&checkout[custom][user_id]={attacker}")
    assert url is not None
    assert str(attacker) not in url
    assert url.count("checkout[custom][user_id]") == 1
    assert f"checkout[custom][user_id]={registered_user}" in url


def test_plan_without_a_configured_variant_has_no_checkout_url(
    client: TestClient, auth: dict[str, str], registered_user: UUID
) -> None:
    plans = client.get("/v1/plans", headers=auth).json()["plans"]
    pack = next(p for p in plans if p["id"] == "pack_50")
    assert pack["checkout_url"] is None


def test_api_key_create_use_and_revoke(
    client: TestClient, auth: dict[str, str], registered_user: UUID, submit: Callable[..., Any]
) -> None:
    created = client.post("/v1/api-keys", json={"name": "growth"}, headers=auth)
    assert created.status_code == 201
    body = created.json()
    assert body["key"].startswith("sp_live_") and len(body["key"]) == len("sp_live_") + 32
    assert body["prefix"] == body["key"][:12] and body["name"] == "growth"

    key_headers = {"X-API-Key": body["key"]}
    assert client.get("/v1/me", headers=key_headers).status_code == 200
    submitted = submit(headers=key_headers)
    assert submitted.status_code == 202

    assert client.delete(f"/v1/api-keys/{body['id']}", headers=auth).status_code == 204
    assert client.get("/v1/me", headers=key_headers).status_code == 401
    assert client.delete(f"/v1/api-keys/{body['id']}", headers=auth).status_code == 204


def test_api_keys_cannot_manage_api_keys(
    client: TestClient, auth: dict[str, str], registered_user: UUID
) -> None:
    key = client.post("/v1/api-keys", headers=auth).json()["key"]
    assert client.post("/v1/api-keys", headers={"X-API-Key": key}).status_code == 401


def test_revoking_someone_elses_key_is_404(
    client: TestClient, auth: dict[str, str], mint_jwt: Callable[..., str], registered_user: UUID
) -> None:
    key_id = client.post("/v1/api-keys", headers=auth).json()["id"]
    other = {"Authorization": f"Bearer {mint_jwt()}"}
    assert client.delete(f"/v1/api-keys/{key_id}", headers=other).status_code == 404
    assert client.delete(f"/v1/api-keys/{uuid4()}", headers=auth).status_code == 404
