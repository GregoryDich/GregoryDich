"""SnapPlay API client: multipart submit, SSE follow, polling fallback and error mapping."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from mcp_server.snapplay import JobOptions, SnapPlayApiError, SnapPlayClient, idempotency_key_for
from tests.conftest import (
    JOB_ID,
    SNAPPLAY_URL,
    job_status,
    make_job_result,
    mock_snapplay,
    sse_body,
)


def _client() -> SnapPlayClient:
    return SnapPlayClient(SNAPPLAY_URL, "sp_live_key", poll_interval=0, timeout=5, max_retries=2)


async def test_submit_sends_multipart_with_api_key(router: respx.Router) -> None:
    result = make_job_result()
    routes = mock_snapplay(router, result)
    async with _client() as client:
        accepted = await client.submit_job(b"RIFF....", "loop.wav", JobOptions(stems=["bass"]))
    assert accepted.job_id == JOB_ID
    request = routes["submit"].calls.last.request
    assert request.headers["X-API-Key"] == "sp_live_key"
    assert request.headers["content-type"].startswith("multipart/form-data")
    body = request.content
    assert b'name="audio"; filename="loop.wav"' in body
    assert b'name="options"' in body
    options_json = body.split(b'name="options"')[1].split(b"\r\n\r\n")[1].split(b"\r\n")[0]
    options = json.loads(options_json)
    assert options["stems"] == ["bass"]
    assert options["idempotency_key"] == idempotency_key_for(
        b"RIFF....", JobOptions(stems=["bass"])
    )


def test_idempotency_key_is_deterministic_per_clip_and_options() -> None:
    a = idempotency_key_for(b"abc", JobOptions(stems=["bass"]))
    assert a == idempotency_key_for(b"abc", JobOptions(stems=["bass"]))
    assert a != idempotency_key_for(b"abd", JobOptions(stems=["bass"]))
    assert a != idempotency_key_for(b"abc", JobOptions(stems=["drums"]))


async def test_sse_stream_yields_result(router: respx.Router) -> None:
    result = make_job_result()
    routes = mock_snapplay(router, result)
    async with _client() as client:
        status = await client.wait_for_result(JOB_ID)
    assert status.status == "succeeded"
    assert status.result is not None
    assert status.result.analysis.bpm == 124.0
    assert routes["poll"].call_count == 0


async def test_polling_fallback_when_stream_unavailable(router: respx.Router) -> None:
    result = make_job_result()
    routes = mock_snapplay(router, result, sse=False)
    routes["poll"].side_effect = [
        httpx.Response(200, json=job_status(JOB_ID)),
        httpx.Response(200, json=job_status(JOB_ID, result)),
    ]
    async with _client() as client:
        status = await client.wait_for_result(JOB_ID)
    assert status.result is not None
    assert routes["poll"].call_count == 2


async def test_polling_fallback_when_stream_ends_early(router: respx.Router) -> None:
    result = make_job_result()
    routes = mock_snapplay(router, result)
    routes["events"].mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_body([("progress", {"stage": "separate", "progress": 0.5})]),
        )
    )
    async with _client() as client:
        status = await client.wait_for_result(JOB_ID)
    assert status.result is not None
    assert routes["poll"].call_count == 1


async def test_sse_error_event_raises(router: respx.Router) -> None:
    result = make_job_result()
    routes = mock_snapplay(router, result)
    routes["events"].mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_body([("error", {"code": "worker_timeout", "message": "gave up"})]),
        )
    )
    async with _client() as client:
        with pytest.raises(SnapPlayApiError) as exc:
            await client.wait_for_result(JOB_ID)
    assert exc.value.code == "worker_timeout"


async def test_failed_job_raises_with_error_code(router: respx.Router) -> None:
    result = make_job_result()
    routes = mock_snapplay(router, result, sse=False)
    routes["poll"].mock(
        return_value=httpx.Response(
            200,
            json=job_status(
                JOB_ID, status="failed", error={"code": "worker_timeout", "message": "x"}
            ),
        )
    )
    async with _client() as client:
        with pytest.raises(SnapPlayApiError, match="worker_timeout"):
            await client.wait_for_result(JOB_ID)


async def test_contract_error_envelope_is_mapped(router: respx.Router) -> None:
    router.post(f"{SNAPPLAY_URL}/v1/jobs").mock(
        return_value=httpx.Response(
            402,
            json={
                "error": {
                    "code": "insufficient_credits",
                    "message": "You have 0 credits.",
                    "details": {"available": 0},
                }
            },
        )
    )
    async with _client() as client:
        with pytest.raises(SnapPlayApiError) as exc:
            await client.submit_job(b"x", "a.wav")
    assert exc.value.status == 402
    assert exc.value.code == "insufficient_credits"
    assert exc.value.details == {"available": 0}


async def test_rate_limit_is_retried_after_retry_after(router: respx.Router) -> None:
    route = router.post(f"{SNAPPLAY_URL}/v1/jobs")
    route.side_effect = [
        httpx.Response(
            429,
            headers={"Retry-After": "0"},
            json={"error": {"code": "rate_limited", "message": "slow down"}},
        ),
        httpx.Response(202, json={"job_id": JOB_ID, "status": "queued", "credits_reserved": 1}),
    ]
    async with _client() as client:
        accepted = await client.submit_job(b"x", "a.wav")
    assert accepted.job_id == JOB_ID
    assert route.call_count == 2
