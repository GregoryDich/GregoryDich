"""Fixtures for the pipeline and worker tests: a synthetic beat, in-memory service
stubs implementing the ``app.services`` Protocol methods the worker uses, and a fake
SQS client."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import numpy as np
import pytest
import soundfile as sf

from app.schemas import JobError, JobResult, JobStatus

SR = 44100


def synth_beat(
    seconds: float = 4.0, bpm: float = 120.0, bass_hz: float = 55.0, channels: int = 2
) -> bytes:
    """A bass tone plus short noise clicks on every beat, as 16-bit WAV."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    bass = 0.5 * np.sin(2 * np.pi * bass_hz * t)
    rng = np.random.default_rng(7)
    clicks = np.zeros(n)
    click_len = int(0.02 * SR)
    envelope = np.exp(-np.arange(click_len) / (0.004 * SR))
    for start in np.arange(0.0, seconds, 60.0 / bpm):
        i = int(start * SR)
        stop = min(i + click_len, n)
        clicks[i:stop] += 0.6 * envelope[: stop - i] * rng.standard_normal(stop - i)
    mono = bass + clicks
    mono = (0.8 * mono / np.max(np.abs(mono))).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, np.repeat(mono[:, None], channels, axis=1), SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture(scope="session")
def synthetic_wav() -> bytes:
    return synth_beat()


class StubJobs:
    """Records what the worker does; ``get`` reports ``status`` for every job."""

    def __init__(self, status: str = "queued") -> None:
        self.status = status
        self.progress: list[tuple[str, float]] = []
        self.completed: dict[UUID, JobResult] = {}
        self.failed: dict[UUID, tuple[str, str]] = {}

    def _status(self, job_id: UUID, **updates: Any) -> JobStatus:
        return JobStatus(
            job_id=job_id,
            status=self.status,  # type: ignore[arg-type]
            stage="upload",
            progress=0.0,
            created_at=datetime.now(UTC),
            **updates,
        )

    async def get(self, job_id: UUID, user_id: UUID) -> JobStatus | None:
        return self._status(job_id)

    async def set_progress(self, job_id: UUID, stage: str, progress: float) -> None:
        self.progress.append((stage, progress))

    async def complete(self, job_id: UUID, result: JobResult) -> JobStatus:
        self.completed[job_id] = result
        self.status = "succeeded"
        return self._status(job_id, result=result)

    async def fail(self, job_id: UUID, code: str, message: str) -> JobStatus:
        self.failed[job_id] = (code, message)
        self.status = "failed"
        return self._status(job_id, error=JobError(code=code, message=message))


class StubStorage:
    def __init__(self, fail_download: bool = False) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.fail_download = fail_download

    async def upload_bytes(self, path: str, data: bytes, content_type: str) -> str:
        self.objects[path] = (data, content_type)
        return path

    async def download_bytes(self, path: str) -> bytes:
        if self.fail_download:
            raise RuntimeError("storage unavailable")
        try:
            return self.objects[path][0]
        except KeyError:
            raise FileNotFoundError(path) from None

    async def signed_url(self, path: str, ttl_seconds: int) -> str:
        return f"https://storage.test/{path}?ttl={ttl_seconds}"


class StubServices:
    def __init__(self, jobs: StubJobs, storage: StubStorage) -> None:
        self.jobs = jobs
        self.storage = storage


class FakeSqs:
    """The subset of the boto3 SQS client the worker uses, over an in-memory queue."""

    def __init__(self, bodies: list[str], receive_count: int = 1) -> None:
        self.messages = [
            {
                "MessageId": str(i),
                "ReceiptHandle": f"rh-{i}",
                "Body": body,
                "Attributes": {"ApproximateReceiveCount": str(receive_count)},
            }
            for i, body in enumerate(bodies)
        ]
        self.receives: list[dict[str, Any]] = []
        self.deleted: list[str] = []
        self.visibility: list[tuple[str, int]] = []

    def receive_message(self, **params: Any) -> dict[str, Any]:
        self.receives.append(params)
        batch = self.messages[: params["MaxNumberOfMessages"]]
        self.messages = self.messages[params["MaxNumberOfMessages"] :]
        return {"Messages": batch} if batch else {}

    def change_message_visibility(self, **params: Any) -> None:
        self.visibility.append((params["ReceiptHandle"], params["VisibilityTimeout"]))

    def delete_message(self, **params: Any) -> None:
        self.deleted.append(params["ReceiptHandle"])
