"""Dispatch backends (§7): the in-process runner, the event bus and the remote paths."""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
import respx

from app.config import Settings
from app.errors import ApiException
from app.pipeline.base import PipelineError
from app.schemas import JobOptions, PipelineOptions
from app.services.dispatch import (
    RUNPOD_API_BASE,
    LocalDispatch,
    ModalDispatch,
    RunPodDispatch,
    job_message,
)
from app.services.events import JobEventBus
from app.services.factory import build_dispatch, build_services, data_backend, events_mode
from app.services.memory import (
    MemoryCreditsService,
    MemoryJobsService,
    MemoryStorageService,
    MemoryStore,
)


@pytest.fixture
def store(settings: Settings) -> MemoryStore:
    return MemoryStore(settings)


async def wait_for_status(store: MemoryStore, job_id: UUID, status: str, tries: int = 500) -> None:
    for _ in range(tries):
        if store.jobs[job_id].status == status:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"job stayed {store.jobs[job_id].status}, expected {status}")


async def test_local_dispatch_fails_the_job_when_the_pipeline_rejects_the_input(
    settings: Settings, store: MemoryStore
) -> None:
    bus = JobEventBus()
    jobs = MemoryJobsService(store, bus)
    storage = MemoryStorageService()
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    job = store.create_job(user, JobOptions().model_dump(mode="json"), {}, None)
    key = f"jobs/{user}/{job.id}/input.wav"
    await storage.upload_bytes(key, b"not audio", "audio/wav")

    def failing(*_: object) -> Any:
        raise PipelineError("unsupported_media_type", "cannot decode")

    dispatch = LocalDispatch(
        settings,
        jobs=jobs,
        storage=storage,
        credits=MemoryCreditsService(store),
        run_pipeline=failing,
    )
    await dispatch.dispatch(job.id, user, key, PipelineOptions())
    await wait_for_status(store, job.id, "failed")
    await dispatch.aclose()
    assert store.jobs[job.id].status == "failed"
    assert store.jobs[job.id].error == {
        "code": "unsupported_media_type",
        "message": "cannot decode",
    }
    assert store.get_balance(user).model_dump() == {"credits": 3, "reserved": 0, "available": 3}


async def test_missing_input_fails_the_job(settings: Settings, store: MemoryStore) -> None:
    bus = JobEventBus()
    jobs = MemoryJobsService(store, bus)
    user = uuid4()
    store.ensure_user(user, "a@b.c")
    job = store.create_job(user, JobOptions().model_dump(mode="json"), {}, None)
    dispatch = LocalDispatch(
        settings,
        jobs=jobs,
        storage=MemoryStorageService(),
        credits=MemoryCreditsService(store),
        run_pipeline=lambda *_: pytest.fail("the pipeline must not run"),
    )
    await dispatch.dispatch(job.id, user, "jobs/x/y/input.wav", PipelineOptions())
    await wait_for_status(store, job.id, "failed")
    await dispatch.aclose()
    assert store.jobs[job.id].error is not None
    assert store.jobs[job.id].error["code"] == "internal_error"


async def test_event_bus_fans_out_and_unsubscribes() -> None:
    bus = JobEventBus()
    job_id = uuid4()
    async with bus.subscription(job_id) as first, bus.subscription(job_id) as second:
        assert bus.subscriber_count(job_id) == 2
        bus.publish(job_id, "progress", {"stage": "separate", "progress": 0.5})
        assert await first.get() == {
            "event": "progress",
            "data": {"stage": "separate", "progress": 0.5},
        }
        assert (await second.get())["event"] == "progress"
    assert bus.subscriber_count(job_id) == 0
    bus.publish(job_id, "result", {})  # nobody listening is not an error


@pytest.mark.skipif(find_spec("modal") is not None, reason="modal is installed")
async def test_modal_dispatch_without_the_sdk_is_503(settings: Settings) -> None:
    dispatch = ModalDispatch(settings.model_copy(update={"snapplay_pipeline": "modal"}))
    with pytest.raises(ApiException) as info:
        await dispatch.dispatch(uuid4(), uuid4(), "jobs/a/b/input.wav", PipelineOptions())
    assert info.value.status == 503 and info.value.code == "worker_unavailable"
    assert await dispatch.cancel(uuid4()) is False


async def test_runpod_dispatch_requires_configuration(settings: Settings) -> None:
    dispatch = RunPodDispatch(settings)
    with pytest.raises(ApiException) as info:
        await dispatch.dispatch(uuid4(), uuid4(), "jobs/a/b/input.wav", PipelineOptions())
    assert info.value.status == 503


@respx.mock
async def test_runpod_dispatch_posts_the_job_message(settings: Settings) -> None:
    configured = settings.model_copy(
        update={
            "snapplay_pipeline": "runpod",
            "runpod_endpoint_id": "ep1",
            "runpod_api_key": settings.runpod_api_key.__class__("rp-key"),
        }
    )
    route = respx.post(f"{RUNPOD_API_BASE}/ep1/run").mock(
        return_value=httpx.Response(200, json={"id": "run-1", "status": "IN_QUEUE"})
    )
    cancel = respx.post(f"{RUNPOD_API_BASE}/ep1/cancel/run-1").mock(
        return_value=httpx.Response(200, json={"status": "CANCELLED"})
    )
    dispatch = RunPodDispatch(configured)
    job_id, user_id = uuid4(), uuid4()
    await dispatch.dispatch(job_id, user_id, "jobs/a/b/input.wav", PipelineOptions())
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer rp-key"
    assert request.read().decode().count(str(job_id)) == 1
    assert await dispatch.cancel(job_id) is True and cancel.called
    await dispatch.aclose()


@respx.mock
async def test_runpod_rejection_is_worker_unavailable(settings: Settings) -> None:
    configured = settings.model_copy(
        update={
            "runpod_endpoint_id": "ep1",
            "runpod_api_key": settings.runpod_api_key.__class__("rp-key"),
        }
    )
    respx.post(f"{RUNPOD_API_BASE}/ep1/run").mock(return_value=httpx.Response(500))
    dispatch = RunPodDispatch(configured)
    with pytest.raises(ApiException) as info:
        await dispatch.dispatch(uuid4(), uuid4(), "jobs/a/b/input.wav", PipelineOptions())
    assert info.value.code == "worker_unavailable"
    await dispatch.aclose()


def test_job_message_shape() -> None:
    job_id, user_id = uuid4(), uuid4()
    message = job_message(job_id, user_id, "jobs/a/b/input.flac", PipelineOptions())
    assert message["job_id"] == str(job_id) and message["user_id"] == str(user_id)
    assert message["input_key"] == "jobs/a/b/input.flac"
    assert message["options"]["max_seconds"] == 60.0


def test_backend_selection_follows_settings(settings: Settings) -> None:
    assert data_backend(settings) == "memory"
    assert events_mode(settings) == "bus"
    assert events_mode(settings.model_copy(update={"snapplay_pipeline": "aws"})) == "poll"
    assert data_backend(settings.model_copy(update={"env": "staging"})) == "supabase"

    services = build_services(settings)
    assert isinstance(services.jobs, MemoryJobsService)
    assert isinstance(services.storage, MemoryStorageService)
    assert isinstance(services.dispatch, LocalDispatch)

    modal = build_dispatch(
        settings.model_copy(update={"snapplay_pipeline": "modal"}),
        jobs=services.jobs,
        storage=services.storage,
        credits=services.credits,
    )
    assert isinstance(modal, ModalDispatch)


async def test_job_ids_are_isolated_between_users(settings: Settings, store: MemoryStore) -> None:
    bus = JobEventBus()
    jobs = MemoryJobsService(store, bus)
    owner, stranger = uuid4(), uuid4()
    store.ensure_user(owner, "a@b.c")
    job = store.create_job(owner, {}, {}, None)
    assert await jobs.get(job.id, stranger) is None
    assert await jobs.get(UUID(int=0), owner) is None
