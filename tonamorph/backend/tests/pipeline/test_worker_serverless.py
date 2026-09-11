import base64
from importlib.util import find_spec
from uuid import uuid4

import pytest

from app.config import Settings
from app.pipeline import fake
from tests.pipeline.conftest import StubJobs, StubServices, StubStorage
from worker import modal_app, runpod_handler
from worker.common import JobSpec, run_job


def _payload(audio: bytes) -> dict:
    return {
        "job_id": str(uuid4()),
        "user_id": str(uuid4()),
        "options": {"max_seconds": 4.0},
        "audio_base64": base64.b64encode(audio).decode("ascii"),
    }


def test_job_spec_parsing() -> None:
    spec = JobSpec.from_payload(_payload(b"x"))
    assert spec.options.max_seconds == 4.0 and spec.input_key is None and spec.credits_reserved == 1
    assert spec.prefix == f"jobs/{spec.user_id}/{spec.job_id}"
    with pytest.raises(ValueError, match="malformed"):
        JobSpec.from_payload({"job_id": "nope"})
    with pytest.raises(ValueError, match="malformed"):
        JobSpec.from_payload({"job_id": str(uuid4()), "user_id": str(uuid4()), "options": {"x": 1}})


def test_runpod_handler_success(settings: Settings, synthetic_wav: bytes) -> None:
    jobs, storage = StubJobs(), StubStorage()
    payload = _payload(synthetic_wav)
    response = runpod_handler.handler(
        {"input": payload},
        settings=settings,
        services=StubServices(jobs, storage),
        run=fake.run_pipeline,
    )
    assert response["status"] == "succeeded" and response["job_id"] == payload["job_id"]
    result = response["result"]
    assert [s["name"] for s in result["stems"]] == ["bass", "drums", "other", "vocals"]
    assert result["stems"][0]["url"].startswith("https://storage.test/jobs/")
    assert "wav_bytes" not in result["stems"][0] and "smf_bytes" not in result["midi"]
    prefix = f"jobs/{payload['user_id']}/{payload['job_id']}"
    assert f"{prefix}/score.mid" in storage.objects and len(storage.objects) == 5
    assert jobs.progress[-1] == ("done", 1.0)


def test_runpod_handler_failures(settings: Settings) -> None:
    jobs, storage = StubJobs(), StubStorage()
    services = StubServices(jobs, storage)
    assert runpod_handler.handler({})["error"]["code"] == "bad_request"
    malformed = runpod_handler.handler(
        {"input": {"job_id": "x"}}, settings=settings, services=services, run=fake.run_pipeline
    )
    assert malformed["status"] == "failed" and malformed["error"]["code"] == "bad_request"
    payload = _payload(b"not audio")
    rejected = runpod_handler.handler(
        {"input": payload}, settings=settings, services=services, run=fake.run_pipeline
    )
    assert rejected["status"] == "failed"
    assert rejected["error"]["code"] == "unsupported_media_type"
    assert jobs.failed[JobSpec.from_payload(payload).job_id][0] == "unsupported_media_type"


async def test_run_job_from_storage_key_and_crash(settings: Settings, synthetic_wav: bytes) -> None:
    jobs, storage = StubJobs(), StubStorage()
    job_id, user_id = uuid4(), uuid4()
    key = f"jobs/{user_id}/{job_id}/input.wav"
    storage.objects[key] = (synthetic_wav, "audio/wav")
    payload = {"job_id": str(job_id), "user_id": str(user_id), "options": {}, "input_key": key}
    response = await run_job(
        payload, settings=settings, services=StubServices(jobs, storage), run=fake.run_pipeline
    )
    assert response["status"] == "succeeded" and job_id in jobs.completed

    def explode(*_: object) -> object:
        raise RuntimeError("cuda died")

    crashed_id = uuid4()
    payload = {"job_id": str(crashed_id), "user_id": str(user_id), "options": {}, "input_key": key}
    with pytest.raises(RuntimeError, match="cuda died"):
        await run_job(payload, settings=settings, services=StubServices(jobs, storage), run=explode)
    assert jobs.failed[crashed_id][0] == "internal_error"


@pytest.mark.skipif(find_spec("modal") is not None, reason="modal is installed")
def test_modal_module_imports_without_modal() -> None:
    assert modal_app.app is None and modal_app.TonamorphWorker is None
    assert modal_app.APP_NAME == "tonamorph-worker" and modal_app.DEFAULT_GPU == "A10G"
    with pytest.raises(ImportError):
        modal_app.build_app()


@pytest.mark.skipif(find_spec("modal") is None, reason="modal not installed")
def test_modal_app_builds() -> None:
    app, cls = modal_app.build_app()
    assert app.name == modal_app.APP_NAME and cls.__name__ == modal_app.CLASS_NAME
