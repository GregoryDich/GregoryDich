"""reap_once / main against minimal in-memory Jobs and Credits fakes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.config import Settings, override_settings
from app.schemas import Balance, CreditBalance, JobError, JobStatus
from app.services.aws import reaper


class FakeCredits:
    """Single-account credit ledger: only the balance methods the reaper path needs."""

    def __init__(self, credits: int) -> None:
        self.credits = credits
        self.reserved: dict[UUID, int] = {}

    def _balance(self) -> CreditBalance:
        reserved = sum(self.reserved.values())
        return CreditBalance(
            credits=self.credits, reserved=reserved, available=self.credits - reserved
        )

    async def get_balance(self, user_id: UUID) -> Balance:
        return Balance(**self._balance().model_dump())

    async def reserve(self, user_id: UUID, job_id: UUID, amount: int = 1) -> CreditBalance:
        self.reserved.setdefault(job_id, amount)
        return self._balance()

    async def settle(self, job_id: UUID, success: bool) -> CreditBalance:
        amount = self.reserved.pop(job_id, 0)
        if success:
            self.credits -= amount
        return self._balance()


@dataclass
class FakeJobs:
    credits: FakeCredits
    jobs: dict[UUID, JobStatus] = field(default_factory=dict)

    async def start(self, user_id: UUID, started_at: datetime) -> JobStatus:
        job = JobStatus(
            job_id=uuid4(),
            status="running",
            stage="separate",
            progress=0.3,
            created_at=started_at,
            started_at=started_at,
        )
        await self.credits.reserve(user_id, job.job_id)
        self.jobs[job.job_id] = job
        return job

    async def reap_stale(self, timeout_seconds: int) -> int:
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=timeout_seconds)
        reaped = 0
        for job_id, job in list(self.jobs.items()):
            if job.status != "running" or job.started_at is None or job.started_at >= cutoff:
                continue
            await self.credits.settle(job_id, False)
            self.jobs[job_id] = job.model_copy(
                update={
                    "status": "failed",
                    "finished_at": now,
                    "error": JobError(code="worker_timeout", message="worker timed out"),
                }
            )
            reaped += 1
        return reaped


@dataclass
class Services:
    jobs: FakeJobs
    credits: FakeCredits


@pytest.fixture
def services() -> Services:
    credits = FakeCredits(credits=3)
    return Services(jobs=FakeJobs(credits), credits=credits)


async def test_reap_once_releases_stuck_reservation(services: Services) -> None:
    user_id = uuid4()
    now = datetime.now(UTC)
    stuck = await services.jobs.start(user_id, now - timedelta(minutes=10))
    fresh = await services.jobs.start(user_id, now)
    before = await services.credits.get_balance(user_id)
    assert (before.credits, before.reserved, before.available) == (3, 2, 1)

    assert await reaper.reap_once(services, 180) == 1

    after = await services.credits.get_balance(user_id)
    assert (after.credits, after.reserved, after.available) == (3, 1, 2)
    reaped = services.jobs.jobs[stuck.job_id]
    assert reaped.status == "failed"
    assert reaped.error == JobError(code="worker_timeout", message="worker timed out")
    assert reaped.finished_at is not None
    assert services.jobs.jobs[fresh.job_id].status == "running"

    assert await reaper.reap_once(services, 180) == 0


async def test_reap_once_rejects_non_positive_timeout(services: Services) -> None:
    with pytest.raises(ValueError):
        await reaper.reap_once(services, 0)


def test_main_uses_settings_timeout_and_exits_zero(
    services: Services, monkeypatch: pytest.MonkeyPatch, make_settings: Callable[..., Settings]
) -> None:
    seen: list[int] = []
    original = services.jobs.reap_stale

    async def recording_reap(timeout_seconds: int) -> int:
        seen.append(timeout_seconds)
        return await original(timeout_seconds)

    monkeypatch.setattr(services.jobs, "reap_stale", recording_reap)
    monkeypatch.setattr(reaper, "build_services", lambda settings: services)
    with override_settings(make_settings(job_timeout_seconds=45)):
        assert reaper.main() == 0
    assert seen == [45]
