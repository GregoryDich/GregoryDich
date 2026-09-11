"""Platform adapters with every HTTP call mocked, plus publish idempotency and resumption."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx
from fastmcp import Client

from mcp_server import pipeline
from mcp_server.config import Settings
from mcp_server.publishers import PublishRequest, build_publisher
from mcp_server.publishers.tiktok import UNAUDITED_CODE
from mcp_server.state import Store
from tests.conftest import META_GRAPH_URL, META_UPLOAD_URL, TIKTOK_URL, YOUTUBE_URL

GRAPH = f"{META_GRAPH_URL}/v21.0"
FUTURE = "2099-01-01T12:00:00Z"


@pytest.fixture
def video(tmp_path: Path) -> Path:
    path = tmp_path / "short.mp4"
    path.write_bytes(b"\0" * 1000)
    return path


def _request(video: Path, schedule_at: str | None = None) -> PublishRequest:
    return PublishRequest(
        content_item_id="item-1",
        video_path=video,
        caption="Sample to keys in 2 s",
        hashtags=["producer", "#tonamorph"],
        schedule_at=schedule_at,
    )


def _form(request: httpx.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


# --- Instagram -------------------------------------------------------------------------------


def mock_instagram(router: respx.Router, *, upload_ok: bool = True) -> dict[str, respx.Route]:
    routes = {
        "create": router.post(f"{GRAPH}/1789/media").mock(
            return_value=httpx.Response(
                200, json={"id": "C1", "uri": f"{META_UPLOAD_URL}/ig-api-upload/v21.0/C1"}
            )
        ),
        "upload": router.post(f"{META_UPLOAD_URL}/ig-api-upload/v21.0/C1").mock(
            return_value=httpx.Response(200, json={"success": True})
            if upload_ok
            else httpx.Response(500, json={"error": {"code": 1, "message": "upload failed"}})
        ),
        "status": router.get(f"{GRAPH}/C1").mock(
            side_effect=[
                httpx.Response(200, json={"status_code": "IN_PROGRESS"}),
                httpx.Response(200, json={"status_code": "FINISHED"}),
            ]
        ),
        "publish": router.post(f"{GRAPH}/1789/media_publish").mock(
            return_value=httpx.Response(200, json={"id": "M1"})
        ),
        "permalink": router.get(f"{GRAPH}/M1").mock(
            return_value=httpx.Response(
                200, json={"permalink": "https://www.instagram.com/reel/M1/"}
            )
        ),
    }
    return routes


async def test_instagram_container_publish_flow(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_instagram(router)
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("instagram", settings, http).publish(_request(video), {})
    assert outcome.status == "published"
    assert outcome.post_id == "M1"
    assert outcome.url == "https://www.instagram.com/reel/M1/"
    create = _form(routes["create"].calls.last.request)
    assert create["media_type"] == "REELS"
    assert create["upload_type"] == "resumable"
    assert create["caption"] == "Sample to keys in 2 s\n\n#producer #tonamorph"
    upload = routes["upload"].calls.last.request
    assert upload.headers["offset"] == "0"
    assert upload.headers["file_size"] == "1000"
    assert upload.headers["Authorization"] == "OAuth ig-token"
    assert routes["status"].call_count == 2
    assert _form(routes["publish"].calls.last.request)["creation_id"] == "C1"


async def test_instagram_schedule_is_kept_locally(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_instagram(router)
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("instagram", settings, http).publish(
            _request(video, FUTURE), {}
        )
    assert outcome.status == "scheduled"
    assert routes["create"].call_count == 0


# --- Facebook --------------------------------------------------------------------------------


def mock_facebook(router: respx.Router) -> dict[str, respx.Route]:
    return {
        "reels": router.post(f"{GRAPH}/4242/video_reels").mock(
            side_effect=[
                httpx.Response(
                    200,
                    json={
                        "video_id": "V1",
                        "upload_url": f"{META_UPLOAD_URL}/video-upload/v21.0/V1",
                    },
                ),
                httpx.Response(200, json={"success": True, "post_id": "4242_V1"}),
            ]
        ),
        "upload": router.post(f"{META_UPLOAD_URL}/video-upload/v21.0/V1").mock(
            return_value=httpx.Response(200, json={"success": True})
        ),
        "status": router.get(f"{GRAPH}/V1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "status": {
                        "video_status": "upload_complete",
                        "uploading_phase": {"status": "complete"},
                    }
                },
            )
        ),
    }


async def test_facebook_start_upload_finish(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_facebook(router)
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("facebook", settings, http).publish(_request(video), {})
    assert outcome.status == "published"
    assert outcome.post_id == "4242_V1"
    assert outcome.url == "https://www.facebook.com/reel/V1"
    start, finish = (_form(c.request) for c in routes["reels"].calls)
    assert start["upload_phase"] == "start"
    assert finish["upload_phase"] == "finish"
    assert finish["video_state"] == "PUBLISHED"
    assert finish["video_id"] == "V1"
    assert routes["upload"].calls.last.request.headers["file_size"] == "1000"


async def test_facebook_native_scheduling(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_facebook(router)
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("facebook", settings, http).publish(
            _request(video, FUTURE), {}
        )
    assert outcome.status == "scheduled"
    finish = _form(routes["reels"].calls.last.request)
    assert finish["video_state"] == "SCHEDULED"
    assert finish["scheduled_publish_time"] == "4070952000"


# --- TikTok ----------------------------------------------------------------------------------


def mock_tiktok(router: respx.Router, *, public: bool) -> dict[str, respx.Route]:
    options = (
        ["PUBLIC_TO_EVERYONE", "SELF_ONLY"] if public else ["MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"]
    )
    return {
        "creator": router.post(f"{TIKTOK_URL}/v2/post/publish/creator_info/query/").mock(
            return_value=httpx.Response(
                200, json={"data": {"privacy_level_options": options}, "error": {"code": "ok"}}
            )
        ),
        "init": router.post(f"{TIKTOK_URL}/v2/post/publish/video/init/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {"publish_id": "P1", "upload_url": "https://upload.tiktok.test/u/P1"},
                    "error": {"code": "ok"},
                },
            )
        ),
        "upload": router.put("https://upload.tiktok.test/u/P1").mock(
            return_value=httpx.Response(201)
        ),
        "status": router.post(f"{TIKTOK_URL}/v2/post/publish/status/fetch/").mock(
            side_effect=[
                httpx.Response(200, json={"data": {"status": "PROCESSING_UPLOAD"}}),
                httpx.Response(
                    200,
                    json={
                        "data": {
                            "status": "PUBLISH_COMPLETE",
                            "publicaly_available_post_id": [7001],
                        }
                    },
                ),
            ]
        ),
    }


async def test_tiktok_unaudited_app_posts_privately_and_says_so(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_tiktok(router, public=False)
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("tiktok", settings, http).publish(_request(video), {})
    assert outcome.status == "restricted"
    assert outcome.post_id == "7001"
    assert "unaudited" in (outcome.note or "")
    assert "SELF_ONLY" in (outcome.note or "")
    init = json.loads(routes["init"].calls.last.request.content)
    assert init["post_info"]["privacy_level"] == "SELF_ONLY"
    assert init["source_info"] == {
        "source": "FILE_UPLOAD",
        "video_size": 1000,
        "chunk_size": 1000,
        "total_chunk_count": 1,
    }
    upload = routes["upload"].calls.last.request
    assert upload.headers["Content-Range"] == "bytes 0-999/1000"
    assert routes["creator"].calls.last.request.headers["Authorization"] == "Bearer tt-token"


async def test_tiktok_audited_app_posts_publicly(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_tiktok(router, public=True)
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("tiktok", settings, http).publish(_request(video), {})
    assert outcome.status == "published"
    assert outcome.note is None
    assert (
        json.loads(routes["init"].calls.last.request.content)["post_info"]["privacy_level"]
        == "PUBLIC_TO_EVERYONE"
    )


async def test_tiktok_init_rejection_falls_back_to_private(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_tiktok(router, public=True)
    routes["init"].side_effect = [
        httpx.Response(
            200, json={"data": {}, "error": {"code": UNAUDITED_CODE, "message": "nope"}}
        ),
        httpx.Response(
            200,
            json={
                "data": {"publish_id": "P1", "upload_url": "https://upload.tiktok.test/u/P1"},
                "error": {"code": "ok"},
            },
        ),
    ]
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("tiktok", settings, http).publish(_request(video), {})
    assert outcome.status == "restricted"
    assert routes["init"].call_count == 2
    assert (
        json.loads(routes["init"].calls.last.request.content)["post_info"]["privacy_level"]
        == "SELF_ONLY"
    )


# --- YouTube ---------------------------------------------------------------------------------


def mock_youtube(router: respx.Router) -> dict[str, respx.Route]:
    return {
        "session": router.post(f"{YOUTUBE_URL}/upload/youtube/v3/videos").mock(
            return_value=httpx.Response(
                200, headers={"Location": f"{YOUTUBE_URL}/upload/session/1"}
            )
        ),
        "upload": router.put(f"{YOUTUBE_URL}/upload/session/1").mock(
            return_value=httpx.Response(200, json={"id": "yt1", "kind": "youtube#video"})
        ),
    }


async def test_youtube_resumable_upload(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_youtube(router)
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("youtube", settings, http).publish(_request(video), {})
    assert outcome.status == "published"
    assert outcome.post_id == "yt1"
    assert outcome.url == "https://youtube.com/shorts/yt1"
    session = routes["session"].calls.last.request
    assert session.url.params["uploadType"] == "resumable"
    assert session.url.params["part"] == "snippet,status"
    assert session.headers["X-Upload-Content-Length"] == "1000"
    assert session.headers["Authorization"] == "Bearer yt-token"
    body = json.loads(session.content)
    assert body["snippet"]["title"] == "Tonamorph #Shorts"
    assert body["snippet"]["tags"] == ["producer", "tonamorph"]
    assert body["status"]["privacyStatus"] == "public"
    upload = routes["upload"].calls.last.request
    assert upload.headers["Content-Type"] == "video/mp4"
    assert upload.content == b"\0" * 1000


async def test_youtube_resumes_after_server_error(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_youtube(router)
    routes["upload"].side_effect = [
        httpx.Response(503),
        httpx.Response(308, headers={"Range": "bytes=0-499"}),
        httpx.Response(201, json={"id": "yt2"}),
    ]
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("youtube", settings, http).publish(_request(video), {})
    assert outcome.post_id == "yt2"
    calls = routes["upload"].calls
    assert len(calls) == 3
    assert calls[1].request.headers["Content-Range"] == "bytes */1000"
    assert calls[2].request.headers["Content-Range"] == "bytes 500-999/1000"
    assert calls[2].request.content == b"\0" * 500


async def test_youtube_native_scheduling(
    router: respx.Router, settings: Settings, video: Path
) -> None:
    routes = mock_youtube(router)
    async with httpx.AsyncClient() as http:
        outcome = await build_publisher("youtube", settings, http).publish(
            _request(video, FUTURE), {}
        )
    assert outcome.status == "scheduled"
    status = json.loads(routes["session"].calls.last.request.content)["status"]
    assert status == {
        "selfDeclaredMadeForKids": False,
        "privacyStatus": "private",
        "publishAt": FUTURE,
    }


# --- Idempotency and resumption through the pipeline / MCP tool -------------------------------


def _rendered_item(store: Store, video: Path):
    item = store.create_item("licensed_folder", "/clips/a.wav")
    return store.update(item.id, assets={"video_path": str(video)})


async def test_publishing_twice_yields_one_post(
    mcp_client: Client, router: respx.Router, store: Store, video: Path
) -> None:
    routes = mock_youtube(router)
    item = _rendered_item(store, video)
    args = {
        "content_item_id": item.id,
        "platforms": ["youtube"],
        "caption": "hi",
        "hashtags": ["tonamorph"],
    }
    first = (await mcp_client.call_tool("publish_video", args)).structured_content["results"][0]
    second = (await mcp_client.call_tool("publish_video", args)).structured_content["results"][0]
    assert first["status"] == "published"
    assert first["post_id"] == "yt1"
    assert first["already_posted"] is False
    assert second["post_id"] == "yt1"
    assert second["already_posted"] is True
    assert routes["session"].call_count == 1
    assert routes["upload"].call_count == 1
    record = store.require(item.id).publish_record("youtube")
    assert record.status == "published"
    assert record.published_at is not None
    assert record.caption == "hi"


async def test_failed_attempt_resumes_from_checkpoint(
    router: respx.Router, settings: Settings, store: Store, video: Path
) -> None:
    routes = mock_instagram(router, upload_ok=False)
    item = _rendered_item(store, video)
    async with httpx.AsyncClient() as http:
        report = await pipeline.publish_video(
            settings, store, http, item.id, ["instagram"], "cap", [], None
        )
    assert report.results[0].status == "failed"
    assert "upload" in (report.results[0].error or "")
    record = store.require(item.id).publish_record("instagram")
    assert record.status == "failed"
    assert record.checkpoint["container_id"] == "C1"

    routes["upload"].mock(return_value=httpx.Response(200, json={"success": True}))
    async with httpx.AsyncClient() as http:
        report = await pipeline.publish_video(
            settings, store, http, item.id, ["instagram"], "cap", [], None
        )
    assert report.results[0].status == "published"
    assert report.results[0].post_id == "M1"
    assert routes["create"].call_count == 1  # container was reused, not recreated


async def test_unconfigured_platform_is_reported_not_raised(
    mcp_client: Client,
    router: respx.Router,
    store: Store,
    video: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TIKTOK_ACCESS_TOKEN")
    item = _rendered_item(store, video)
    result = await mcp_client.call_tool(
        "publish_video",
        {"content_item_id": item.id, "platforms": ["tiktok"], "caption": "c", "hashtags": []},
    )
    entry = result.structured_content["results"][0]
    assert entry["status"] == "failed"
    assert "TIKTOK_ACCESS_TOKEN" in entry["error"]
    assert not store.require(item.id).is_posted("tiktok")


async def test_publish_requires_rendered_video(mcp_client: Client, store: Store) -> None:
    item = store.create_item("licensed_folder", "/clips/a.wav")
    with pytest.raises(Exception, match="render_video first"):
        await mcp_client.call_tool(
            "publish_video",
            {"content_item_id": item.id, "platforms": ["youtube"], "caption": "c", "hashtags": []},
        )
