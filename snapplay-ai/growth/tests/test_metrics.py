"""report_metrics: one insights call per published post, stored on the item."""

from __future__ import annotations

import httpx
import respx
from fastmcp import Client

from mcp_server.state import PublishRecord, Store
from tests.conftest import META_GRAPH_URL, TIKTOK_URL, YOUTUBE_URL

GRAPH = f"{META_GRAPH_URL}/v21.0"


def _published(store: Store, platform: str, post_id: str, published_at: str) -> str:
    item = store.create_item("licensed_folder", f"/clips/{platform}.wav")
    store.set_publish_record(
        item.id,
        platform,
        PublishRecord(status="published", post_id=post_id, published_at=published_at),
    )
    return item.id


def mock_metrics(router: respx.Router) -> None:
    router.get(f"{GRAPH}/M1/insights").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"name": "views", "values": [{"value": 1000}]},
                    {"name": "likes", "values": [{"value": 50}]},
                    {"name": "comments", "values": [{"value": 5}]},
                    {"name": "shares", "total_value": {"value": 10}},
                    {"name": "reach", "values": [{"value": 900}]},
                ]
            },
        )
    )
    router.get(f"{GRAPH}/4242_V1/video_insights").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"name": "total_video_views", "values": [{"value": 500}]},
                    {"name": "total_video_impressions", "values": [{"value": 2000}]},
                    {
                        "name": "total_video_reactions_by_type_total",
                        "values": [{"value": {"like": 30, "love": 2}}],
                    },
                    {"name": "post_video_social_actions", "values": [{"value": 7}]},
                ]
            },
        )
    )
    router.post(f"{TIKTOK_URL}/v2/video/query/").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "videos": [
                        {
                            "id": "7001",
                            "view_count": 300,
                            "like_count": 20,
                            "comment_count": 2,
                            "share_count": 1,
                        }
                    ]
                }
            },
        )
    )
    router.get(f"{YOUTUBE_URL}/youtube/v3/videos").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "yt1",
                        "statistics": {"viewCount": "800", "likeCount": "40", "commentCount": "3"},
                    }
                ]
            },
        )
    )


async def test_report_metrics_across_platforms(
    mcp_client: Client, router: respx.Router, store: Store
) -> None:
    mock_metrics(router)
    ids = {
        "instagram": _published(store, "instagram", "M1", "2026-09-06T10:00:00Z"),
        "facebook": _published(store, "facebook", "4242_V1", "2026-09-06T10:00:00Z"),
        "tiktok": _published(store, "tiktok", "7001", "2026-09-06T10:00:00Z"),
        "youtube": _published(store, "youtube", "yt1", "2026-09-06T10:00:00Z"),
    }
    result = await mcp_client.call_tool("report_metrics", {"since_iso": "2026-09-01T00:00:00Z"})
    report = result.structured_content
    assert report["errors"] == []
    posts = {p["platform"]: p for p in report["posts"]}
    assert set(posts) == set(ids)
    assert posts["instagram"]["views"] == 1000
    assert posts["instagram"]["shares"] == 10
    assert posts["instagram"]["ctr"] == 0.065
    assert posts["instagram"]["ctr_kind"] == "engagement"
    assert posts["facebook"]["impressions"] == 2000
    assert posts["facebook"]["likes"] == 32
    assert posts["facebook"]["ctr"] == 0.25
    assert posts["facebook"]["ctr_kind"] == "click"
    assert posts["tiktok"]["views"] == 300
    assert posts["tiktok"]["ctr"] == round(23 / 300, 4)
    assert posts["youtube"]["views"] == 800
    assert posts["youtube"]["likes"] == 40
    assert posts["youtube"]["ctr"] == round(43 / 800, 4)
    for platform, item_id in ids.items():
        stored = store.require(item_id).metrics[platform]
        assert stored["post_id"] == posts[platform]["post_id"]
        assert stored["fetched_at"]


async def test_report_metrics_honours_since(
    mcp_client: Client, router: respx.Router, store: Store
) -> None:
    mock_metrics(router)
    _published(store, "youtube", "yt1", "2026-08-01T00:00:00Z")
    result = await mcp_client.call_tool("report_metrics", {"since_iso": "2026-09-01T00:00:00Z"})
    assert result.structured_content["posts"] == []


async def test_report_metrics_collects_errors(
    mcp_client: Client, router: respx.Router, store: Store
) -> None:
    router.get(f"{YOUTUBE_URL}/youtube/v3/videos").mock(
        return_value=httpx.Response(403, json={"error": {"code": 403, "message": "quota"}})
    )
    _published(store, "youtube", "yt1", "2026-09-06T00:00:00Z")
    result = await mcp_client.call_tool("report_metrics", {"since_iso": "2026-09-01T00:00:00Z"})
    assert result.structured_content["posts"] == []
    assert "403" in result.structured_content["errors"][0]
