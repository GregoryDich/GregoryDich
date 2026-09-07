"""AI disclosure: synthetic renders are labelled in the caption and flagged where the API can
carry it (docs/GROWTH.md §6)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from fastmcp import Client

from mcp_server import pipeline
from mcp_server.config import Settings
from mcp_server.disclosure import BOTH_LINE, PRESENTER_LINE, VOICE_LINE, disclosure_for
from mcp_server.publishers import build_publisher
from mcp_server.publishers.meta import META_AI_NOTE
from mcp_server.render import RenderResult
from mcp_server.state import Store
from tests.conftest import YOUTUBE_URL
from tests.test_publishers import _request, mock_instagram, mock_tiktok, mock_youtube


@pytest.fixture
def fake_render(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _item(store: Store, *, voiceover: bool) -> str:
    item = store.create_item("licensed_folder", "/clips/a.wav")
    assets: dict[str, str] = {"chosen_stem_path": "/clips/a.wav"}
    if voiceover:
        assets["voiceover_path"] = "/work/voiceover.mp3"
    store.update(item.id, assets=assets)
    return item.id


def test_disclosure_lines() -> None:
    assert disclosure_for(has_voiceover=False, presenter="waveform").line is None
    assert disclosure_for(has_voiceover=True, presenter="waveform").line == VOICE_LINE
    assert disclosure_for(has_voiceover=False, presenter="avatar_clip").line == PRESENTER_LINE
    both = disclosure_for(has_voiceover=True, presenter="avatar_clip")
    assert both.line == BOTH_LINE and both.is_synthetic


async def test_render_records_the_disclosure_on_the_content_item(
    mcp_client: Client, store: Store, fake_render: None
) -> None:
    voiced = _item(store, voiceover=True)
    plain = _item(store, voiceover=False)
    await mcp_client.call_tool("render_video", {"content_item_id": voiced})
    await mcp_client.call_tool("render_video", {"content_item_id": plain})
    assert store.require(voiced).disclosure == {
        "synthetic_voice": True,
        "synthetic_presenter": False,
        "line": VOICE_LINE,
    }
    assert store.require(plain).disclosure["line"] is None


async def test_tiktok_sets_the_aigc_flag_and_the_caption_line(
    mcp_client: Client, router: respx.Router, store: Store, fake_render: None
) -> None:
    routes = mock_tiktok(router, public=True)
    item_id = _item(store, voiceover=True)
    await mcp_client.call_tool("render_video", {"content_item_id": item_id})
    result = await mcp_client.call_tool(
        "publish_video",
        {
            "content_item_id": item_id,
            "platforms": ["tiktok"],
            "caption": "Sample to keys",
            "hashtags": ["snapplay"],
        },
    )
    entry = result.structured_content["results"][0]
    assert entry["ai_flag_set"] is True
    assert entry["disclosure_line"] == VOICE_LINE
    post_info = json.loads(routes["init"].calls.last.request.content)["post_info"]
    assert post_info["is_aigc"] is True
    assert post_info["brand_organic_toggle"] is True
    assert VOICE_LINE in post_info["title"]
    record = store.require(item_id).publish_record("tiktok")
    assert record.ai_flag_set is True
    assert record.disclosure_line == VOICE_LINE


async def test_youtube_sets_contains_synthetic_media_only_when_synthetic(
    mcp_client: Client, router: respx.Router, store: Store, fake_render: None
) -> None:
    routes = mock_youtube(router)
    voiced = _item(store, voiceover=True)
    await mcp_client.call_tool("render_video", {"content_item_id": voiced})
    await mcp_client.call_tool(
        "publish_video",
        {"content_item_id": voiced, "platforms": ["youtube"], "caption": "c", "hashtags": []},
    )
    body = json.loads(routes["session"].calls.last.request.content)
    assert body["status"]["containsSyntheticMedia"] is True
    assert VOICE_LINE in body["snippet"]["description"]

    routes["upload"].mock(return_value=httpx.Response(200, json={"id": "yt2"}))
    plain = _item(store, voiceover=False)
    await mcp_client.call_tool("render_video", {"content_item_id": plain})
    await mcp_client.call_tool(
        "publish_video",
        {"content_item_id": plain, "platforms": ["youtube"], "caption": "c", "hashtags": []},
    )
    body = json.loads(routes["session"].calls.last.request.content)
    assert "containsSyntheticMedia" not in body["status"]
    assert VOICE_LINE not in body["snippet"]["description"]


async def test_meta_has_no_api_flag_so_the_caption_carries_it(
    router: respx.Router, settings: Settings, tmp_path: Path
) -> None:
    routes = mock_instagram(router)
    video = tmp_path / "short.mp4"
    video.write_bytes(b"\0" * 1000)
    request = _request(video).model_copy(
        update={"disclosure": VOICE_LINE, "is_synthetic": True, "link": "https://snapplay.test/x"}
    )
    async with httpx.AsyncClient() as http:
        publisher = build_publisher("instagram", settings, http)
        assert publisher.ai_flag_supported is False
        outcome = await publisher.publish(request, {})
    assert outcome.ai_flag_set is False
    assert outcome.note == META_AI_NOTE
    caption = routes["create"].calls.last.request.content.decode()
    assert VOICE_LINE.replace(" ", "+") in caption


async def test_disclosure_survives_metrics_and_a_later_publish(
    mcp_client: Client, router: respx.Router, store: Store, fake_render: None
) -> None:
    """The state lives on the content item, so a second platform discloses the same thing."""
    mock_youtube(router)
    tiktok = mock_tiktok(router, public=True)
    router.get(f"{YOUTUBE_URL}/youtube/v3/videos").mock(
        return_value=httpx.Response(200, json={"items": [{"statistics": {"viewCount": "10"}}]})
    )
    item_id = _item(store, voiceover=True)
    await mcp_client.call_tool("render_video", {"content_item_id": item_id})
    await mcp_client.call_tool(
        "publish_video",
        {"content_item_id": item_id, "platforms": ["youtube"], "caption": "c", "hashtags": []},
    )
    await mcp_client.call_tool("report_metrics", {"since_iso": "2020-01-01T00:00:00Z"})
    item = store.require(item_id)
    assert item.disclosure["line"] == VOICE_LINE
    assert item.metrics["youtube"]["views"] == 10

    await mcp_client.call_tool(
        "publish_video",
        {"content_item_id": item_id, "platforms": ["tiktok"], "caption": "c", "hashtags": []},
    )
    post_info = json.loads(tiktok["init"].calls.last.request.content)["post_info"]
    assert post_info["is_aigc"] is True
    assert VOICE_LINE in post_info["title"]


async def test_publish_due_keeps_the_disclosure_of_the_original_render(
    settings: Settings, store: Store, router: respx.Router, tmp_path: Path
) -> None:
    from mcp_server.state import PublishRecord

    routes = mock_instagram(router)
    video = tmp_path / "short.mp4"
    video.write_bytes(b"\0" * 64)
    item = store.create_item("licensed_folder", "/clips/a.wav")
    store.update(
        item.id,
        assets={"video_path": str(video)},
        disclosure={"synthetic_voice": True, "synthetic_presenter": False, "line": VOICE_LINE},
    )
    store.set_publish_record(
        item.id,
        "instagram",
        PublishRecord(status="scheduled", schedule_at="2020-01-01T00:00:00Z", caption="due"),
    )
    async with httpx.AsyncClient() as http:
        results = await pipeline.publish_due(settings, store, http, ["instagram"])
    assert results[0].status == "published"
    caption = routes["create"].calls.last.request.content.decode()
    assert VOICE_LINE.replace(" ", "+") in caption
    assert store.require(item.id).publish_record("instagram").disclosure_line == VOICE_LINE
