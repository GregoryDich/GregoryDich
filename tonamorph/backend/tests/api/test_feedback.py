"""§2 result feedback with the bounded auto-refund (GTM §2.6) and §14 NPS."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.services.memory import MemoryStore
from app.services.quality import (
    AUTO_REFUND_FREE_LIFETIME,
    auto_refund_allowance,
    auto_refund_reason,
    percentile,
)

pytestmark = pytest.mark.usefixtures("no_rate_limits")


def succeeded_job(store: MemoryStore, user: UUID) -> UUID:
    """A captured job, finished just now, as complete_job leaves it."""
    row = store.create_job(user, {}, {"input_name": "input.wav"}, None)
    store.start_job(row.id, "worker")
    store.complete_job(row.id, {"analysis": {"bpm": 120}})
    return row.id


def test_thumbs_down_refunds_the_credit_once(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    submit: Callable[..., Any],
    poll_job: Callable[[str], dict[str, Any]],
    make_wav: Callable[..., bytes],
) -> None:
    job_id = submit(audio=make_wav(seconds=3.0)).json()["job_id"]
    assert poll_job(job_id)["status"] == "succeeded"
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 2

    response = client.post(
        f"/v1/jobs/{job_id}/feedback",
        json={
            "rating": "down",
            "reason": "bleed",
            "note": " bass in the drums ",
            "drop_to_ready_ms": 4200,
        },
        headers=auth,
    )
    assert response.status_code == 201, response.text
    assert response.json() == {
        "refunded": True,
        "balance": {"credits": 3, "reserved": 0, "available": 3},
    }
    row = store.job_feedback[UUID(job_id)]
    assert row.rating == "down" and row.reason == "bleed" and row.refunded
    assert row.note == "bass in the drums" and row.drop_to_ready_ms == 4200
    refunds = [r for r in store.ledger if r.entry_type == "refund"]
    assert len(refunds) == 1
    assert refunds[0].note == "user:unusable:bleed" and refunds[0].source == f"job:{job_id}"

    # Re-rating the same job refreshes the row and finds the refund already made.
    again = client.post(
        f"/v1/jobs/{job_id}/feedback", json={"rating": "down", "reason": "clicks"}, headers=auth
    )
    assert again.status_code == 201 and again.json()["refunded"] is True
    assert client.get("/v1/me", headers=auth).json()["balance"]["credits"] == 3
    assert sum(1 for r in store.ledger if r.entry_type == "refund") == 1
    assert store.job_feedback[UUID(job_id)].reason == "clicks"
    assert store.job_feedback[UUID(job_id)].drop_to_ready_ms == 4200  # kept when omitted
    assert len(store.job_feedback) == 1

    # A thumbs-up afterwards keeps the refund and the refunded flag.
    up = client.post(f"/v1/jobs/{job_id}/feedback", json={"rating": "up"}, headers=auth)
    assert up.status_code == 201 and up.json()["refunded"] is True
    assert store.job_feedback[UUID(job_id)].rating == "up"

    ledger = client.get("/v1/credits/ledger", headers=auth).json()["entries"]
    assert [e["entry_type"] for e in ledger] == ["refund", "capture", "reserve", "grant"]
    assert ledger[0]["note"] == "user:unusable:bleed"


def test_thumbs_up_and_slow_never_refund(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    job = succeeded_job(store, registered_user)
    up = client.post(f"/v1/jobs/{job}/feedback", json={"rating": "up"}, headers=auth)
    assert up.status_code == 201 and up.json()["refunded"] is False
    slow = client.post(
        f"/v1/jobs/{job}/feedback", json={"rating": "down", "reason": "slow"}, headers=auth
    )
    assert slow.status_code == 201 and slow.json()["refunded"] is False
    assert slow.json()["balance"]["credits"] == 2
    assert not any(r.entry_type == "refund" for r in store.ledger)


def test_feedback_without_a_reason_still_refunds(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    job = succeeded_job(store, registered_user)
    response = client.post(f"/v1/jobs/{job}/feedback", json={"rating": "down"}, headers=auth)
    assert response.status_code == 201 and response.json()["refunded"] is True
    assert store.ledger[-1].note == "user:unusable:unspecified"


def test_only_a_fresh_succeeded_job_is_refundable(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    stale = succeeded_job(store, registered_user)
    store.jobs[stale].finished_at = datetime.now(UTC) - timedelta(hours=25)
    late = client.post(
        f"/v1/jobs/{stale}/feedback", json={"rating": "down", "reason": "bleed"}, headers=auth
    )
    assert late.status_code == 201 and late.json()["refunded"] is False

    failed = store.create_job(registered_user, {}, {}, None)
    store.fail_job(failed.id, {"code": "worker_timeout", "message": "late"})
    lost = client.post(
        f"/v1/jobs/{failed.id}/feedback", json={"rating": "down", "reason": "other"}, headers=auth
    )
    assert lost.status_code == 201 and lost.json()["refunded"] is False
    assert store.job_feedback[failed.id].rating == "down"

    queued = store.create_job(registered_user, {}, {}, None)
    early = client.post(f"/v1/jobs/{queued.id}/feedback", json={"rating": "up"}, headers=auth)
    assert early.status_code == 409 and early.json()["error"]["code"] == "conflict"
    assert early.json()["error"]["message"] == "Rate a finished job."


def test_feedback_is_scoped_to_the_owner(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    mint_jwt: Callable[..., str],
) -> None:
    job = succeeded_job(store, registered_user)
    stranger = {"Authorization": f"Bearer {mint_jwt(str(uuid4()), email='s@example.test')}"}
    foreign = client.post(f"/v1/jobs/{job}/feedback", json={"rating": "down"}, headers=stranger)
    assert foreign.status_code == 404 and foreign.json()["error"]["message"] == "Job not found."
    unknown = client.post(f"/v1/jobs/{uuid4()}/feedback", json={"rating": "down"}, headers=auth)
    assert unknown.status_code == 404
    assert client.post(f"/v1/jobs/{job}/feedback", json={"rating": "down"}).status_code == 401
    assert store.job_feedback == {}


@pytest.mark.parametrize(
    "body",
    [
        {"rating": "meh"},
        {"rating": "down", "reason": "ugly"},
        {"rating": "down", "note": "x" * 141},
        {"rating": "down", "drop_to_ready_ms": -1},
        {"rating": "down", "extra": True},
        {},
    ],
)
def test_feedback_body_is_validated(
    client: TestClient,
    auth: dict[str, str],
    store: MemoryStore,
    registered_user: UUID,
    body: dict[str, Any],
) -> None:
    job = succeeded_job(store, registered_user)
    response = client.post(f"/v1/jobs/{job}/feedback", json=body, headers=auth)
    assert response.status_code == 422 and response.json()["error"]["code"] == "validation_error"


def test_free_accounts_get_two_lifetime_auto_refunds(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    outcomes = []
    for _ in range(AUTO_REFUND_FREE_LIFETIME + 1):
        job = succeeded_job(store, registered_user)  # each refund hands the credit back
        response = client.post(
            f"/v1/jobs/{job}/feedback", json={"rating": "down", "reason": "midi_off"}, headers=auth
        )
        assert response.status_code == 201
        outcomes.append(response.json()["refunded"])
    assert outcomes == [True, True, False]
    assert sum(1 for r in store.ledger if r.entry_type == "refund") == AUTO_REFUND_FREE_LIFETIME


def test_thirty_day_allowance_grows_with_captured_jobs(store: MemoryStore) -> None:
    """A buyer: ``max(3, 20 %)`` of the captures of the last 30 days, decided in the store
    exactly as ``refund_job_for_feedback`` does in SQL."""
    user = uuid4()
    store.ensure_user(user, "buyer@example.test")
    store.record_purchase(user, "lemonsqueezy", "order-1", "pack_50", 900, 800, None, {}, "k1")
    assert auto_refund_allowance(0) == 3 and auto_refund_allowance(19) == 3
    assert auto_refund_allowance(20) == 4 and auto_refund_allowance(25) == 5
    jobs = [succeeded_job(store, user) for _ in range(20)]
    refunded = [store.refund_job_for_feedback(job, user, "bleed") for job in jobs[:5]]
    assert refunded == [True, True, True, True, False]
    # A refund from a month ago no longer counts against the window.
    for row in store.ledger:
        if row.entry_type == "refund":
            row.created_at -= timedelta(days=31)
            break
    assert store.refund_job_for_feedback(jobs[5], user, "bleed") is True
    # ... and captures that old no longer widen it either.
    assert store.refund_job_for_feedback(jobs[6], user, "bleed") is False
    assert store.refund_job_for_feedback(jobs[0], user, "bleed") is True  # already refunded
    with pytest.raises(Exception, match="not_found"):
        store.refund_job_for_feedback(jobs[0], uuid4(), "bleed")
    assert auto_refund_reason(None) == "user:unusable:unspecified"


def test_support_refunds_do_not_count_as_automatic(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    first, second, third = (succeeded_job(store, user) for _ in range(3))
    store.refund_job(first, "support: duplicate charge")
    assert store.refund_job_for_feedback(second, user, "bleed") is True
    assert store.refund_job_for_feedback(third, user, "bleed") is True


def test_nps_is_one_answer_per_thirty_days(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    first = client.post("/v1/nps", json={"score": 10, "comment": "  fast  "}, headers=auth)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["score"] == 10 and body["comment"] == "fast"
    assert UUID(body["id"]) and body["created_at"]
    again = client.post("/v1/nps", json={"score": 2}, headers=auth)
    assert again.status_code == 409 and again.json()["error"]["code"] == "conflict"
    assert again.json()["error"]["message"] == "You already answered within the last 30 days."
    store.nps_responses[0].created_at -= timedelta(days=31)
    later = client.post("/v1/nps", json={"score": 7}, headers=auth)
    assert later.status_code == 201 and later.json()["comment"] is None
    assert [r.score for r in store.nps_responses] == [10, 7]
    assert client.post("/v1/nps", json={"score": 5}).status_code == 401


@pytest.mark.parametrize(
    "body", [{"score": 11}, {"score": -1}, {"score": "ten"}, {"score": 5, "comment": "c" * 501}, {}]
)
def test_nps_body_is_validated(
    client: TestClient, auth: dict[str, str], body: dict[str, Any]
) -> None:
    response = client.post("/v1/nps", json=body, headers=auth)
    assert response.status_code == 422


def test_account_deletion_scrubs_the_free_text(
    client: TestClient, auth: dict[str, str], store: MemoryStore, registered_user: UUID
) -> None:
    job = succeeded_job(store, registered_user)
    client.post(f"/v1/jobs/{job}/feedback", json={"rating": "up", "note": "nice"}, headers=auth)
    client.post("/v1/nps", json={"score": 9, "comment": "great"}, headers=auth)
    client.get("/v1/me", headers={**auth, "X-Plugin-Version": "0.1.0", "X-Host": "Live"})
    assert store.plugin_installs
    deletion = client.request(
        "DELETE", "/v1/me", json={"confirm": "player@example.test"}, headers=auth
    )
    assert deletion.status_code == 200
    assert store.job_feedback[job].rating == "up" and store.job_feedback[job].note is None
    assert store.nps_responses[0].score == 9 and store.nps_responses[0].comment is None
    assert store.plugin_installs == {}


def test_percentile_matches_percentile_cont() -> None:
    assert percentile([], 0.5) is None
    assert percentile([10.0], 0.95) == 10.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.95) == pytest.approx(3.85)
