"""The credit guard: run_daily_batch cannot drain the account (docs/GROWTH.md §8)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from fastmcp import Client

from tests.conftest import TONAMORPH_URL, make_job_result, make_wav_bytes, me_body, mock_tonamorph
from tests.test_voiceover import mock_elevenlabs


@pytest.fixture
def three_clips(clip_file: Path) -> list[Path]:
    clips = [clip_file]
    entries: dict[str, dict[str, str]] = {}
    for index in (2, 3):
        path = clip_file.with_name(f"loop{index}.wav")
        path.write_bytes(make_wav_bytes(1.0, freq=110.0 * index))
        entries[path.name] = {"title": f"Loop {index}", "license": "operator-licensed"}
        clips.append(path)
    (clip_file.parent / "licences.json").write_text(json.dumps({"clips": entries}))
    return clips


@pytest.fixture(autouse=True)
def voiceover(router: respx.Router) -> None:
    mock_elevenlabs(router, "21m00Tcm4TlvDq8ikWAM", "narration")


@pytest.fixture
def fake_render(monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp_server.render import RenderResult

    async def render_item(item, settings, *, work_dir, scene, presenter, avatar_clip, frames=None):
        work_dir.mkdir(parents=True, exist_ok=True)
        out = work_dir / "short.mp4"
        out.write_bytes(b"\0" * 64)
        return RenderResult(
            content_item_id=item.id,
            video_path=str(out),
            renderer="ffmpeg",
            props_path=str(work_dir / "props.json"),
            duration_seconds=15.0,
        )

    monkeypatch.setattr("mcp_server.pipeline.render_item", render_item)


async def test_balance_floor_stops_the_run_before_the_first_clip(
    mcp_client: Client,
    router: respx.Router,
    three_clips: list[Path],
    fake_render: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROWTH_CREDIT_FLOOR", "41")
    routes = mock_tonamorph(router, make_job_result(), available=41)
    report = (await mcp_client.call_tool("run_daily_batch", {"count": 3})).structured_content
    assert [i["status"] for i in report["items"]] == ["skipped", "skipped", "skipped"]
    reason = report["items"][0]["skip_reason"]
    assert "balance floor would be crossed" in reason
    assert "41 credit(s) available" in reason and "floor is 41" in reason
    assert report["credits"] == {
        "floor": 41,
        "budget": None,
        "balance_checked": True,
        "balance_before": 41,
        "balance_after": 41,
        "credits_spent": 0,
        "stopped_reason": reason,
    }
    assert routes["submit"].call_count == 0, "the floor must be enforced before any job is posted"
    assert any("stopped before spending more credits" in n for n in report["notes"])


async def test_run_stops_when_the_next_clip_would_cross_the_floor(
    mcp_client: Client,
    router: respx.Router,
    three_clips: list[Path],
    fake_render: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROWTH_CREDIT_FLOOR", "10")
    routes = mock_tonamorph(router, make_job_result())
    routes["me"].side_effect = [
        httpx.Response(200, json=me_body(12)),
        httpx.Response(200, json=me_body(11)),
        httpx.Response(200, json=me_body(10)),
    ]
    report = (await mcp_client.call_tool("run_daily_batch", {"count": 3})).structured_content
    assert [i["status"] for i in report["items"]] == ["rendered", "rendered", "skipped"]
    assert routes["submit"].call_count == 2
    assert routes["me"].call_count == 3, "the balance is re-read before every clip"
    credits = report["credits"]
    assert credits["balance_before"] == 12
    assert credits["balance_after"] == 10
    assert credits["credits_spent"] == 2
    assert "floor is 10" in credits["stopped_reason"]


async def test_per_run_credit_budget_is_honoured(
    mcp_client: Client, router: respx.Router, three_clips: list[Path], fake_render: None
) -> None:
    routes = mock_tonamorph(router, make_job_result(), available=1000)
    report = (
        await mcp_client.call_tool("run_daily_batch", {"count": 3, "credit_budget": 2})
    ).structured_content
    assert [i["status"] for i in report["items"]] == ["rendered", "rendered", "skipped"]
    assert routes["submit"].call_count == 2
    assert report["credits"]["budget"] == 2
    assert report["credits"]["credits_spent"] == 2
    assert "per-run credit budget of 2 reached" in report["items"][2]["skip_reason"]


async def test_configured_budget_applies_without_an_argument(
    mcp_client: Client,
    router: respx.Router,
    three_clips: list[Path],
    fake_render: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROWTH_CREDIT_BUDGET", "1")
    routes = mock_tonamorph(router, make_job_result(), available=1000)
    report = (await mcp_client.call_tool("run_daily_batch", {"count": 3})).structured_content
    assert [i["status"] for i in report["items"]] == ["rendered", "skipped", "skipped"]
    assert routes["submit"].call_count == 1
    assert report["credits"]["budget"] == 1


def test_blank_env_values_mean_unset(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    """`GROWTH_CREDIT_BUDGET=` in a sourced .env must not break every tool."""
    from mcp_server.config import Settings

    monkeypatch.setenv("GROWTH_CREDIT_BUDGET", "")
    monkeypatch.setenv("GROWTH_REFERRAL_CODE", "")
    settings = Settings()
    assert settings.growth_credit_budget is None
    assert settings.growth_referral_code is None


async def test_an_unreadable_balance_stops_the_run_rather_than_spending(
    mcp_client: Client, router: respx.Router, three_clips: list[Path], fake_render: None
) -> None:
    routes = mock_tonamorph(router, make_job_result())
    routes["me"].mock(
        return_value=httpx.Response(
            500, json={"error": {"code": "internal", "message": "boom"}}
        )
    )
    report = (await mcp_client.call_tool("run_daily_batch", {"count": 2})).structured_content
    assert [i["status"] for i in report["items"]] == ["skipped", "skipped"]
    assert "credit balance could not be read" in report["credits"]["stopped_reason"]
    assert report["credits"]["balance_checked"] is False
    assert routes["submit"].call_count == 0


async def test_the_guard_reads_the_balance_with_the_api_key(
    mcp_client: Client, router: respx.Router, three_clips: list[Path], fake_render: None
) -> None:
    routes = mock_tonamorph(router, make_job_result(), available=1000)
    await mcp_client.call_tool("run_daily_batch", {"count": 1})
    request = routes["me"].calls.last.request
    assert request.url == f"{TONAMORPH_URL}/v1/me"
    assert request.headers["X-API-Key"].startswith("tm_live_")
