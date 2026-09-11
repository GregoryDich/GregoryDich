"""The in-memory backend must match db/migrations/0002_functions.sql semantics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import Settings
from app.errors import ApiException
from app.schemas import JobOptions
from app.services.memory import MemoryStore


@pytest.fixture
def store(settings: Settings) -> MemoryStore:
    return MemoryStore(settings)


def test_signup_grants_three_credits_once(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "A@Example.test")
    store.ensure_user(user, "a@example.test")
    assert store.get_balance(user).model_dump() == {"credits": 3, "reserved": 0, "available": 3}
    grants = [row for row in store.ledger if row.entry_type == "grant"]
    assert len(grants) == 1 and grants[0].idempotency_key == f"signup:{user}"
    assert store.profiles[user].email == "a@example.test"


def test_reservation_capture_and_release(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    job = store.create_job(user, JobOptions().model_dump(mode="json"), {}, None)
    assert store.get_balance(user).model_dump() == {"credits": 3, "reserved": 1, "available": 2}

    # Reserving the same job twice is a no-op, as is settling twice.
    store.reserve_credits(user, job.id, 1)
    assert sum(1 for r in store.ledger if r.entry_type == "reserve") == 1
    store.settle_reservation(job.id, True)
    store.settle_reservation(job.id, True)
    assert store.get_balance(user).model_dump() == {"credits": 2, "reserved": 0, "available": 2}
    assert [r.entry_type for r in store.ledger] == ["grant", "reserve", "capture"]

    other = store.create_job(user, JobOptions().model_dump(mode="json"), {}, None)
    store.settle_reservation(other.id, False)
    assert store.get_balance(user).credits == 2
    assert store.ledger[-1].entry_type == "release"


def test_insufficient_credits_raises_the_402_equivalent(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    for _ in range(3):
        store.create_job(user, {}, {}, None)
    with pytest.raises(ApiException) as info:
        store.create_job(user, {}, {}, None)
    assert info.value.status == 402 and info.value.code == "insufficient_credits"
    assert info.value.details == {"available": 0, "requested": 1}
    assert len(store.jobs) == 3  # the rolled-back insert leaves no row


def test_idempotency_keys_are_honoured(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    first = store.create_job(user, {}, {}, "client-key")
    second = store.create_job(user, {}, {}, "client-key")
    assert first.id == second.id
    assert store.grant_credits(user, 5, "test", "grant-key").credits == 8
    assert store.grant_credits(user, 5, "test", "grant-key").credits == 8


def test_refund_reverses_a_capture_once(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    job = store.create_job(user, {}, {}, None)
    store.complete_job(job.id, {"input": {}})
    assert store.get_balance(user).credits == 2
    store.refund_job(job.id, "support")
    store.refund_job(job.id, "support")
    assert store.get_balance(user).credits == 3
    with pytest.raises(ApiException) as info:
        store.refund_job(uuid4(), "support")
    assert info.value.status == 404


def test_expire_credits_treats_expiring_credits_as_spent_first(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    past = datetime.now(UTC) - timedelta(minutes=1)
    store.grant_credits(user, 10, "sub", "sub:1", "Pro Monthly", past)
    job = store.create_job(user, {}, {}, None)
    store.complete_job(job.id, {})
    assert store.get_balance(user).credits == 12
    assert store.expire_credits() == 1
    # The captured credit came out of the perishable grant: 10 - 1 expired.
    assert store.get_balance(user).credits == 3
    assert store.expire_credits() == 0


def test_reserved_credits_are_never_expired(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    store.grant_credits(
        user, 2, "sub", "sub:1", None, datetime.now(UTC) - timedelta(seconds=1)
    )
    for _ in range(5):
        store.create_job(user, {}, {}, None)
    assert store.get_balance(user).model_dump() == {"credits": 5, "reserved": 5, "available": 0}
    store.expire_credits()
    assert store.get_balance(user).model_dump() == {"credits": 5, "reserved": 5, "available": 0}


def test_job_lifecycle_and_cancel_rules(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    job = store.create_job(user, {}, {}, None)
    store.start_job(job.id, "worker-1")
    assert store.jobs[job.id].status == "running" and store.jobs[job.id].started_at is not None
    with pytest.raises(ApiException) as info:
        store.cancel_job(job.id, user)
    assert info.value.status == 409

    store.complete_job(job.id, {"expires_at": "2026-01-01T00:00:00+00:00"})
    result = store.jobs[job.id].result
    assert result is not None
    assert result["credits_charged"] == 1 and result["balance_after"] == 2
    assert result["job_id"] == str(job.id) and result["expires_at"].startswith("2026-01-01")
    store.update_job_progress(job.id, "separate", 0.5)
    assert store.jobs[job.id].stage == "done" and store.jobs[job.id].progress == 1.0

    queued = store.create_job(user, {}, {}, None)
    store.cancel_job(queued.id, user)
    store.cancel_job(queued.id, user)
    assert store.jobs[queued.id].status == "cancelled"
    assert store.get_balance(user).reserved == 0
    with pytest.raises(ApiException) as info:
        store.cancel_job(queued.id, uuid4())
    assert info.value.status == 404


def test_reap_stale_jobs_releases_the_reservation(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    job = store.create_job(user, {}, {}, None)
    store.start_job(job.id)
    store.jobs[job.id].started_at = datetime.now(UTC) - timedelta(seconds=600)
    assert store.reap_stale_jobs(180) == [job.id]
    assert store.jobs[job.id].status == "failed"
    assert store.jobs[job.id].error == {
        "code": "worker_timeout",
        "message": "no completion within 180 seconds",
    }
    assert store.get_balance(user).model_dump() == {"credits": 3, "reserved": 0, "available": 3}
    assert store.reap_stale_jobs(180) == []


def test_reap_stale_jobs_releases_a_job_that_was_never_started(store: MemoryStore) -> None:
    """§10: a job whose message was lost before ``start_job`` stays queued with its credit
    reserved forever, permanently lowering the owner's usable balance."""
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    job = store.create_job(user, {}, {}, None)
    store.jobs[job.id].created_at = datetime.now(UTC) - timedelta(seconds=900)
    assert store.get_balance(user).model_dump() == {"credits": 3, "reserved": 1, "available": 2}

    # The queued grace is longer than the running timeout, so the running one leaves it.
    assert store.reap_stale_jobs(180) == []
    assert store.reap_stale_jobs(180, 600) == [job.id]
    assert store.jobs[job.id].status == "failed"
    assert store.jobs[job.id].error == {
        "code": "worker_timeout",
        "message": "no completion within 600 seconds",
    }
    assert store.get_balance(user).model_dump() == {"credits": 3, "reserved": 0, "available": 3}
    assert store.reap_stale_jobs(180, 600) == []
    with pytest.raises(ApiException) as info:
        store.reap_stale_jobs(180, 0)
    assert info.value.status == 422


def test_expiry_charges_a_spend_only_to_the_grant_that_paid_for_it(
    store: MemoryStore,
) -> None:
    """Two subscription periods, one credit spent in each: counting every later capture
    against every earlier grant leaves credits behind that were never granted."""
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    store.adjust_credits(user, -3, "test", "drain")  # the signup grant, out of the way
    period_1 = datetime.now(UTC) - timedelta(days=30)
    period_2 = datetime.now(UTC) - timedelta(seconds=1)

    store.grant_credits(user, 60, "sub", "sub:1", "Pro Monthly", period_1)
    first = store.create_job(user, {}, {}, None)
    store.complete_job(first.id, {})
    store.grant_credits(user, 60, "sub", "sub:2", "Pro Monthly", period_2)
    second = store.create_job(user, {}, {}, None)
    store.complete_job(second.id, {})
    assert store.get_balance(user).credits == 118

    assert store.expire_credits() == 2
    assert store.get_balance(user).model_dump() == {"credits": 0, "reserved": 0, "available": 0}
    expired = sorted(-row.amount for row in store.ledger if row.entry_type == "expire")
    assert sum(expired) == 118


def test_expiry_leaves_a_credit_pack_bought_during_the_period(store: MemoryStore) -> None:
    """§13: perishable credits are spent first, so heavy spend empties the subscription
    grant and the pack keeps the rest."""
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    store.adjust_credits(user, -3, "test", "drain")
    store.grant_credits(
        user, 10, "sub", "sub:1", "Pro Monthly", datetime.now(UTC) - timedelta(seconds=1)
    )
    store.grant_credits(user, 5, "lemonsqueezy:order:1", "pack:1", "50 Credits")
    for _ in range(12):
        job = store.create_job(user, {}, {}, None)
        store.complete_job(job.id, {})
    assert store.get_balance(user).credits == 3

    assert store.expire_credits() == 1
    assert store.get_balance(user).credits == 3


def test_api_key_hashing_and_revocation(store: MemoryStore) -> None:
    from app.auth.api_keys import hash_api_key

    user = uuid4()
    store.ensure_user(user, "a@b.c")
    row, plaintext = store.create_api_key(user, "ci")
    assert plaintext.startswith("tm_live_") and len(plaintext) == 40
    assert row.key_hash == hash_api_key(plaintext) and plaintext not in row.__dict__.values()
    assert store.authenticate_api_key(hash_api_key(plaintext)) == user
    assert store.api_keys[row.id].last_used_at is not None
    assert store.revoke_api_key(row.id, user) is True
    assert store.authenticate_api_key(hash_api_key(plaintext)) is None
    assert store.revoke_api_key(row.id, uuid4()) is False


def test_webhook_event_claim_is_single_use(store: MemoryStore) -> None:
    assert store.claim_webhook_event("k", "paddle", "transaction.completed", {}) is True
    assert store.claim_webhook_event("k", "paddle", "transaction.completed", {}) is False
    # A delivery that failed to apply stays claimable, or the paid event is lost.
    store.mark_webhook_processed("k", "internal_error")
    assert store.claim_webhook_event("k", "paddle", "transaction.completed", {}) is True
    store.mark_webhook_processed("k", None)
    assert store.claim_webhook_event("k", "paddle", "transaction.completed", {}) is False
    store.mark_webhook_processed("k", None)
    assert store.webhook_events["k"].processed_at is not None


def test_purchase_of_an_unknown_plan_is_404(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    with pytest.raises(ApiException) as info:
        store.record_purchase(user, "paddle", "txn", "nope", 100, 90, None, {}, "key")
    assert info.value.status == 404


def test_purchase_belonging_to_another_user_conflicts(store: MemoryStore) -> None:
    first, second = uuid4(), uuid4()
    store.ensure_user(first, "a@b.c")
    store.ensure_user(second, "c@d.e")
    store.record_purchase(first, "paddle", "txn-1", "pack_50", 900, 800, None, {}, "key-1")
    with pytest.raises(ApiException) as info:
        store.record_purchase(second, "paddle", "txn-1", "pack_50", 900, 800, None, {}, "key-2")
    assert info.value.status == 409


def test_affiliate_cannot_earn_on_their_own_purchase(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    store.add_affiliate(user, "SELF")
    store.record_purchase(user, "paddle", "txn-1", "pack_50", 900, 800, "self", {}, "key")
    assert store.commissions == {}
    assert store.referral_codes["self"].uses == 0


def test_ledger_page_uses_the_seq_cursor(store: MemoryStore) -> None:
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    for i in range(5):
        store.grant_credits(user, 1, "test", f"k{i}")
    first = store.ledger_page(user, 2, None)
    assert len(first.entries) == 2 and first.next_cursor is not None
    second = store.ledger_page(user, 2, int(first.next_cursor))
    assert [e.id for e in second.entries] != [e.id for e in first.entries]
    assert all(e.balance_after >= 0 for e in first.entries + second.entries)
