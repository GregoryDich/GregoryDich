import asyncio
from uuid import UUID, uuid4

import pytest

from app.config import Settings
from app.pipeline import fake
from app.schemas import JobResult, PipelineOptions
from app.services.aws.queue import encode_job_message
from tests.pipeline.conftest import FakeSqs, StubJobs, StubServices, StubStorage
from worker import aws_worker
from worker.aws_worker import WorkerConfig, parse_args, process_message, run_loop
from worker.common import ProgressReporter

OPTIONS = PipelineOptions(max_seconds=4.0)


def _config() -> WorkerConfig:
    return WorkerConfig(
        queue_url="https://sqs.test/jobs",
        wait_seconds=0,
        visibility_seconds=300,
        extend_interval_seconds=0.05,
        worker_ref="test-worker",
    )


def _job(storage: StubStorage, audio: bytes) -> tuple[UUID, UUID, str]:
    job_id, user_id = uuid4(), uuid4()
    input_key = f"jobs/{user_id}/{job_id}/input.wav"
    storage.objects[input_key] = (audio, "audio/wav")
    return job_id, user_id, encode_job_message(job_id, user_id, input_key, OPTIONS)


async def test_worker_completes_a_job(settings: Settings, synthetic_wav: bytes) -> None:
    jobs, storage = StubJobs(), StubStorage()
    job_id, user_id, body = _job(storage, synthetic_wav)
    sqs = FakeSqs([body])

    handled = await run_loop(
        sqs=sqs,
        config=_config(),
        services=StubServices(jobs, storage),
        settings=settings,
        run=fake.run_pipeline,
        max_messages=1,
    )

    assert handled == 1 and sqs.deleted == ["rh-0"]
    assert sqs.receives[0]["WaitTimeSeconds"] == 0 and sqs.receives[0]["MaxNumberOfMessages"] == 1
    assert any(timeout == 300 for _, timeout in sqs.visibility)
    result = jobs.completed[job_id]
    assert isinstance(result, JobResult) and result.job_id == job_id
    prefix = f"jobs/{user_id}/{job_id}"
    assert set(storage.objects) == {
        f"{prefix}/input.wav",
        f"{prefix}/bass.wav",
        f"{prefix}/drums.wav",
        f"{prefix}/other.wav",
        f"{prefix}/vocals.wav",
        f"{prefix}/score.mid",
    }
    assert storage.objects[f"{prefix}/score.mid"][1] == "audio/midi"
    assert storage.objects[f"{prefix}/bass.wav"][0].startswith(b"RIFF")
    assert [s.url for s in result.stems] == [
        f"https://storage.test/{prefix}/{name}.wav?ttl={settings.signed_url_ttl_seconds}"
        for name in ("bass", "drums", "other", "vocals")
    ]
    assert result.midi.url == f"https://storage.test/{prefix}/score.mid?ttl=86400"
    assert result.stems[0].wav_bytes is None and result.midi.smf_bytes is None
    assert result.credits_charged == 1 and not jobs.failed
    assert jobs.progress[0] == ("separate", 0.0) and jobs.progress[-1] == ("done", 1.0)
    assert len(jobs.progress) >= 4


async def test_worker_fails_rejected_input(settings: Settings) -> None:
    jobs, storage = StubJobs(), StubStorage()
    job_id, _, body = _job(storage, b"definitely not audio")
    sqs = FakeSqs([body])
    outcome = await process_message(
        sqs.receive_message(MaxNumberOfMessages=1)["Messages"][0],
        sqs=sqs,
        config=_config(),
        services=StubServices(jobs, storage),
        settings=settings,
        run=fake.run_pipeline,
    )
    assert outcome == aws_worker.OUTCOME_FAILED
    assert jobs.failed[job_id][0] == "unsupported_media_type"
    assert sqs.deleted == ["rh-0"] and job_id not in jobs.completed


@pytest.mark.parametrize("receive_count", [1, 2])
async def test_transient_failure_leaves_message_for_redelivery(
    settings: Settings, synthetic_wav: bytes, receive_count: int
) -> None:
    jobs, storage = StubJobs(), StubStorage(fail_download=True)
    job_id, _, body = _job(storage, synthetic_wav)
    sqs = FakeSqs([body], receive_count=receive_count)
    outcome = await process_message(
        sqs.receive_message(MaxNumberOfMessages=1)["Messages"][0],
        sqs=sqs,
        config=_config(),
        services=StubServices(jobs, storage),
        settings=settings,
        run=fake.run_pipeline,
    )
    assert outcome == aws_worker.OUTCOME_RETRY
    assert sqs.deleted == [] and not jobs.failed and not jobs.completed
    assert sqs.visibility[-1] == ("rh-0", 0)


async def test_last_receive_fails_job_and_keeps_message(
    settings: Settings, synthetic_wav: bytes
) -> None:
    jobs, storage = StubJobs(), StubStorage(fail_download=True)
    job_id, _, body = _job(storage, synthetic_wav)
    sqs = FakeSqs([body], receive_count=3)
    outcome = await process_message(
        sqs.receive_message(MaxNumberOfMessages=1)["Messages"][0],
        sqs=sqs,
        config=_config(),
        services=StubServices(jobs, storage),
        settings=settings,
        run=fake.run_pipeline,
    )
    assert outcome == aws_worker.OUTCOME_RETRY
    assert jobs.failed[job_id][0] == "internal_error"
    assert sqs.deleted == [] and sqs.visibility[-1] == ("rh-0", 0)


async def test_finished_job_is_skipped(settings: Settings, synthetic_wav: bytes) -> None:
    jobs, storage = StubJobs(status="cancelled"), StubStorage()
    job_id, _, body = _job(storage, synthetic_wav)
    sqs = FakeSqs([body])
    outcome = await process_message(
        sqs.receive_message(MaxNumberOfMessages=1)["Messages"][0],
        sqs=sqs,
        config=_config(),
        services=StubServices(jobs, storage),
        settings=settings,
        run=fake.run_pipeline,
    )
    assert outcome == aws_worker.OUTCOME_SKIPPED
    assert sqs.deleted == ["rh-0"] and not jobs.completed and not jobs.failed
    assert jobs.progress == []


async def test_malformed_message_is_dropped(settings: Settings) -> None:
    sqs = FakeSqs(['{"job_id": "nope"}'])
    outcome = await process_message(
        sqs.receive_message(MaxNumberOfMessages=1)["Messages"][0],
        sqs=sqs,
        config=_config(),
        services=StubServices(StubJobs(), StubStorage()),
        settings=settings,
        run=fake.run_pipeline,
    )
    assert outcome == aws_worker.OUTCOME_DROPPED and sqs.deleted == ["rh-0"]


async def test_once_and_stop(settings: Settings) -> None:
    services = StubServices(StubJobs(), StubStorage())
    sqs = FakeSqs([])
    handled = await run_loop(
        sqs=sqs, config=_config(), services=services, settings=settings, run=fake.run_pipeline,
        once=True,
    )
    assert handled == 0 and len(sqs.receives) == 1
    stop = asyncio.Event()
    stop.set()
    handled = await run_loop(
        sqs=sqs, config=_config(), services=services, settings=settings, run=fake.run_pipeline,
        stop=stop,
    )
    assert handled == 0 and len(sqs.receives) == 1


def test_parse_args() -> None:
    args = parse_args(["--once", "--max-messages", "2"])
    assert args.once and args.max_messages == 2 and not args.no_warm_up
    assert parse_args([]).max_messages is None
    with pytest.raises(SystemExit):
        parse_args(["--max-messages", "0"])


def test_worker_config_requires_queue_url() -> None:
    with pytest.raises(ValueError, match="SQS_JOB_QUEUE_URL"):
        WorkerConfig.from_env(Settings(_env_file=None))
    config = WorkerConfig.from_env(Settings(_env_file=None, sqs_job_queue_url="https://q"))
    assert config.max_receive_count == 3 and config.visibility_seconds == 300


async def test_progress_reporter_coalesces_and_orders() -> None:
    jobs = StubJobs()
    reporter = ProgressReporter(asyncio.get_running_loop(), jobs, uuid4())
    await asyncio.to_thread(
        lambda: [reporter(s, p) for s, p in (
            ("separate", 0.0), ("separate", 0.01), ("separate", 0.2),
            ("transcribe", 0.21), ("done", 1.0),
        )]
    )
    await reporter.drain()
    assert jobs.progress == [
        ("separate", 0.0),
        ("separate", 0.2),
        ("transcribe", 0.21),
        ("done", 1.0),
    ]
