"""The first-week gift (§3, GTM Appendix B §3): two credits, once, on day 7, to accounts
that morphed at least once — granted by the reaper tick on the memory backend exactly as
``grant_week1_gifts()`` does on Supabase."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.config import Settings
from app.services.aws import reaper
from app.services.factory import Services
from app.services.memory import MemoryStore
from app.services.rewards import week1_gift_key


@pytest.fixture
def store(settings: Settings) -> MemoryStore:
    return MemoryStore(settings)


def account(store: MemoryStore, days_old: float, *, morphs: int = 1, failed: bool = False) -> UUID:
    user = uuid4()
    store.ensure_user(user, f"{user}@example.test")
    store.profiles[user].created_at = datetime.now(UTC) - timedelta(days=days_old)
    for _ in range(morphs):
        job = store.create_job(user, {}, {}, None)
        store.start_job(job.id, "worker")
        store.complete_job(job.id, {})
    if failed:
        job = store.create_job(user, {}, {}, None)
        store.fail_job(job.id, {"code": "worker_timeout", "message": "late"})
    return user


def test_week1_gift_goes_to_seven_day_old_accounts_with_a_morph_once(store: MemoryStore) -> None:
    week = account(store, 7.5)
    idle = account(store, 7.5, morphs=0)
    only_failed = account(store, 7.5, morphs=0, failed=True)
    fresh = account(store, 6)
    old = account(store, 9)
    gone = account(store, 7.5)
    store.delete_user_account(gone)

    assert store.grant_week1_gifts() == [week]
    assert store.get_balance(week).credits == 4
    gift = store._ledger_keys[week1_gift_key(week)]
    assert gift.entry_type == "grant" and gift.amount == 2 and gift.expires_at is None
    assert gift.source == "gift:week1" and gift.note == "One week in. Two morphs on us."
    for user, credits in ((idle, 3), (only_failed, 3), (fresh, 2), (old, 2), (gone, 0)):
        assert store.get_balance(user).credits == credits, user

    assert store.grant_week1_gifts() == []
    assert store.get_balance(week).credits == 4

    store.profiles[fresh].created_at = datetime.now(UTC) - timedelta(days=7, hours=1)
    assert store.grant_week1_gifts() == [fresh]
    assert store.get_balance(fresh).credits == 4


async def test_the_reaper_tick_reaps_and_gifts(app: object) -> None:
    services: Services = app.state.services  # type: ignore[attr-defined]
    memory = services.memory
    assert memory is not None
    week = account(memory, 7.5)
    stuck = memory.create_job(week, {}, {}, None)
    memory.start_job(stuck.id, "dead-worker")
    stuck.started_at = datetime.now(UTC) - timedelta(hours=1)

    assert await reaper.run_once(services, 180) == (1, 1)
    assert memory.jobs[stuck.id].status == "failed"
    assert memory.get_balance(week).model_dump() == {"credits": 4, "reserved": 0, "available": 4}
    assert await reaper.run_once(services, 180) == (0, 0)
