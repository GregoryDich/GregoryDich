"""The SQS visibility claim (audit 1b) against moto: a message must stay invisible while
a slow (cold) job runs, even when the queue's own timeout is shorter than the job and
the extender thread has not ticked yet."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import boto3
import pytest
from moto import mock_aws

from app.config import Settings
from app.pipeline import fake
from app.pipeline.base import ProgressCallback
from app.schemas import PipelineOptions, PipelineResult
from app.services.aws.queue import encode_job_message, receive_messages
from tests.pipeline.conftest import StubJobs, StubServices, StubStorage, synth_beat
from worker import aws_worker
from worker.aws_worker import WorkerConfig, process_message

REGION = "us-east-1"
QUEUE_VISIBILITY_SECONDS = 1
JOB_SECONDS = 1.6
PROBE_AFTER_SECONDS = 1.2


@pytest.fixture
def sqs() -> Iterator[Any]:
    previous = {k: os.environ.get(k) for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")}
    os.environ.update({"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing"})
    try:
        with mock_aws():
            yield boto3.client("sqs", region_name=REGION)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _slow_pipeline(
    audio: bytes, options: PipelineOptions, progress: ProgressCallback
) -> PipelineResult:
    time.sleep(JOB_SECONDS)  # stands in for a cold model load on the worker thread
    return fake.run_pipeline(audio, options, progress)


async def _run_with_probe(
    sqs: Any, queue_url: str, config: WorkerConfig, settings: Settings
) -> tuple[str, list[dict[str, Any]]]:
    jobs, storage = StubJobs(), StubStorage()
    job_id, user_id = uuid4(), uuid4()
    input_key = f"jobs/{user_id}/{job_id}/input.wav"
    storage.objects[input_key] = (synth_beat(seconds=2.0), "audio/wav")
    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=encode_job_message(
            job_id, user_id, input_key, PipelineOptions(max_seconds=2.0)
        ),
    )
    (message,) = receive_messages(sqs, queue_url, 1, 0)
    task = asyncio.create_task(
        process_message(
            message,
            sqs=sqs,
            config=config,
            services=StubServices(jobs, storage),
            settings=settings,
            run=_slow_pipeline,
        )
    )
    await asyncio.sleep(PROBE_AFTER_SECONDS)
    redelivered = receive_messages(sqs, queue_url, 1, 0)
    outcome = await task
    assert job_id in jobs.completed
    return outcome, redelivered


def _config(queue_url: str) -> WorkerConfig:
    return WorkerConfig(
        queue_url=queue_url,
        wait_seconds=0,
        visibility_seconds=300,
        extend_interval_seconds=60.0,  # the timer thread never fires during the job
        worker_ref="moto-worker",
    )


async def test_message_stays_invisible_while_a_cold_job_runs(sqs: Any, settings: Settings) -> None:
    queue_url = sqs.create_queue(
        QueueName="jobs-short", Attributes={"VisibilityTimeout": str(QUEUE_VISIBILITY_SECONDS)}
    )["QueueUrl"]
    outcome, redelivered = await _run_with_probe(sqs, queue_url, _config(queue_url), settings)
    assert outcome == aws_worker.OUTCOME_SUCCEEDED
    assert redelivered == []
    assert receive_messages(sqs, queue_url, 1, 0) == []  # deleted after completion


async def test_without_the_claim_the_queue_redelivers_mid_job(
    sqs: Any, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Control: proves the probe would catch the audit's failure mode."""
    monkeypatch.setattr(aws_worker, "_claim", lambda *args: None)
    queue_url = sqs.create_queue(
        QueueName="jobs-unclaimed", Attributes={"VisibilityTimeout": str(QUEUE_VISIBILITY_SECONDS)}
    )["QueueUrl"]
    outcome, redelivered = await _run_with_probe(sqs, queue_url, _config(queue_url), settings)
    assert outcome == aws_worker.OUTCOME_SUCCEEDED
    assert len(redelivered) == 1


def test_claim_failure_is_logged_not_fatal(caplog: pytest.LogCaptureFixture) -> None:
    class Broken:
        def change_message_visibility(self, **params: Any) -> None:
            raise RuntimeError("boom")

    with caplog.at_level("WARNING", logger="tonamorph.worker.aws"):
        aws_worker._claim(Broken(), _config("https://q"), "rh")
    assert any("claim" in r.message for r in caplog.records)
