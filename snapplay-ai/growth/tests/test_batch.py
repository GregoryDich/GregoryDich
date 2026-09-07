"""run_daily_batch: dry run renders without publishing; live run honours daily caps."""

from __future__ import annotations

from pathlib import Path

import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_server.render import RenderResult
from mcp_server.state import PublishRecord, Store
from tests.conftest import make_job_result, make_wav_bytes, mock_snapplay
from tests.test_publishers import mock_instagram, mock_youtube
from tests.test_voiceover import mock_elevenlabs


@pytest.fixture
def two_clips(clip_file: Path) -> list[Path]:
    second = clip_file.with_name("loop2.wav")
    second.write_bytes(make_wav_bytes(1.5, freq=220.0))
    return [clip_file, second]


@pytest.fixture
def fake_render(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    rendered: list[str] = []

    async def render_item(
        item,
        settings,
        *,
        work_dir,
        scene,
        presenter,
        avatar_clip,
        frames=None,
        duration_seconds=15.0,
    ):
        work_dir.mkdir(parents=True, exist_ok=True)
        out = work_dir / "short.mp4"
        out.write_bytes(b"\0" * 64)
        rendered.append(item.id)
        return RenderResult(
            content_item_id=item.id,
            video_path=str(out),
            renderer="ffmpeg",
            props_path=str(work_dir / "props.json"),
            duration_seconds=duration_seconds,
        )

    monkeypatch.setattr("mcp_server.pipeline.render_item", render_item)
    return rendered


async def test_dry_run_processes_and_renders_but_never_publishes(
    mcp_client: Client,
    router: respx.Router,
    store: Store,
    two_clips: list[Path],
    fake_render: list[str],
) -> None:
    mock_snapplay(router, make_job_result())
    mock_elevenlabs(router, "21m00Tcm4TlvDq8ikWAM", "narration")
    youtube = mock_youtube(router)
    report = (await mcp_client.call_tool("run_daily_batch", {"count": 2})).structured_content
    assert report["dry_run"] is True
    assert report["requested"] == 2
    assert [i["status"] for i in report["items"]] == ["rendered", "rendered"]
    assert [i["angle"] for i in report["items"]] == ["speed", "bass"]
    assert all(i["voiceover"] for i in report["items"])
    assert all(i["publish"] == [] for i in report["items"])
    assert len(fake_render) == 2
    assert youtube["session"].call_count == 0
    for entry in report["items"]:
        item = store.require(entry["content_item_id"])
        assert item.script["angle"] == entry["angle"]
        assert item.assets["voiceover_path"]
        assert item.publish == {}


async def test_live_run_publishes_within_daily_cap(
    mcp_client: Client,
    router: respx.Router,
    store: Store,
    two_clips: list[Path],
    fake_render: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROWTH_MAX_POSTS_PER_DAY_YOUTUBE", "1")
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    mock_snapplay(router, make_job_result())
    youtube = mock_youtube(router)
    report = (
        await mcp_client.call_tool(
            "run_daily_batch", {"count": 2, "accounts": ["youtube"], "dry_run": False}
        )
    ).structured_content
    assert report["platforms"] == ["youtube"]
    assert "ELEVENLABS_API_KEY not set" in report["notes"][0]
    first, second = report["items"]
    assert first["status"] == "published"
    assert first["publish"][0]["post_id"] == "yt1"
    assert first["voiceover"] is False
    assert second["status"] == "rendered"
    assert second["skipped_platforms"] == {"youtube": "daily cap reached"}
    assert youtube["session"].call_count == 1
    assert store.require(first["content_item_id"]).publish_record("youtube").post_id == "yt1"


async def test_live_run_publishes_due_scheduled_posts(
    mcp_client: Client, router: respx.Router, store: Store, tmp_path: Path
) -> None:
    ig = mock_instagram(router)
    video = tmp_path / "short.mp4"
    video.write_bytes(b"\0" * 64)
    item = store.create_item("licensed_folder", "/clips/old.wav")
    store.update(item.id, assets={"video_path": str(video)})
    store.set_publish_record(
        item.id,
        "instagram",
        PublishRecord(
            status="scheduled", schedule_at="2020-01-01T00:00:00Z", caption="due", hashtags=["x"]
        ),
    )
    report = (
        await mcp_client.call_tool(
            "run_daily_batch", {"count": 0, "accounts": ["instagram"], "dry_run": False}
        )
    ).structured_content
    assert report["items"] == []
    assert report["published_due"][0]["status"] == "published"
    assert report["published_due"][0]["post_id"] == "M1"
    assert ig["create"].call_count == 1
    assert "#x" in ig["create"].calls.last.request.content.decode().replace("%23", "#")
    assert store.require(item.id).publish_record("instagram").status == "published"


async def test_unknown_account_is_rejected(mcp_client: Client, router: respx.Router) -> None:
    with pytest.raises(ToolError, match="unknown platform"):
        await mcp_client.call_tool("run_daily_batch", {"count": 1, "accounts": ["myspace"]})


async def test_batch_reports_short_supply_and_isolated_failures(
    mcp_client: Client,
    router: respx.Router,
    store: Store,
    two_clips: list[Path],
    fake_render: list[str],
    monkeypatch,
) -> None:
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    routes = mock_snapplay(router, make_job_result())
    routes["submit"].side_effect = [
        routes["submit"].return_value,
        __import__("httpx").Response(
            402, json={"error": {"code": "insufficient_credits", "message": "0 left"}}
        ),
    ]
    report = (await mcp_client.call_tool("run_daily_batch", {"count": 3})).structured_content
    assert any("only 2 unprocessed clip" in n for n in report["notes"])
    assert [i["status"] for i in report["items"]] == ["rendered", "failed"]
    assert "insufficient_credits" in report["items"][1]["error"]
