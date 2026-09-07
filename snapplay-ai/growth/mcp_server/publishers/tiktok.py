"""TikTok Content Posting API (direct post, FILE_UPLOAD source).

Apps that have not passed TikTok's audit may only post with ``SELF_ONLY`` visibility. The
adapter detects that from ``creator_info/query`` (no ``PUBLIC_TO_EVERYONE`` option) or from the
``unaudited_client_can_only_post_to_private_accounts`` error, posts privately, and returns
``status="restricted"`` with an explanatory note instead of failing.
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings
from ..state import utc_now_iso
from .base import (
    PostMetrics,
    PublisherError,
    PublisherNotConfigured,
    PublishOutcome,
    PublishRequest,
    finish_metrics,
    is_future,
    poll_until,
    read_video,
    response_json,
)

MAX_SINGLE_CHUNK = 64 * 1024 * 1024
UNAUDITED_CODE = "unaudited_client_can_only_post_to_private_accounts"
UNAUDITED_NOTE = (
    "TikTok app is unaudited: the video was posted with SELF_ONLY visibility. It is visible "
    "only to the account owner until the app passes TikTok's audit for public posting."
)


class TikTokPublisher:
    platform = "tiktok"

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        if not settings.tiktok_access_token:
            raise PublisherNotConfigured("TIKTOK_ACCESS_TOKEN not set")
        self.api = settings.tiktok_api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.tiktok_access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        self.http = http
        self.poll_interval = settings.publish_poll_interval_seconds
        self.poll_attempts = settings.publish_poll_attempts

    async def publish(self, request: PublishRequest, checkpoint: dict[str, Any]) -> PublishOutcome:
        cp = dict(checkpoint)
        try:
            return await self._publish(request, cp)
        except PublisherError as exc:
            exc.checkpoint = cp
            raise

    async def _publish(self, request: PublishRequest, cp: dict[str, Any]) -> PublishOutcome:
        if is_future(request.schedule_at):
            return PublishOutcome(
                platform="tiktok",
                status="scheduled",
                note="TikTok has no API-side scheduling; will publish when due",
                checkpoint=cp,
            )
        video = read_video(request.video_path)
        if len(video) > MAX_SINGLE_CHUNK:
            raise PublisherError("tiktok: video exceeds the 64 MB single-chunk limit")
        if "publish_id" not in cp:
            privacy, restricted = await self._privacy_level()
            body, err_code = await self._init(request, privacy, len(video))
            if err_code == UNAUDITED_CODE and privacy != "SELF_ONLY":
                privacy, restricted = "SELF_ONLY", True
                body, err_code = await self._init(request, privacy, len(video))
            if err_code not in (None, "ok"):
                raise PublisherError(f"tiktok: init failed with {err_code}")
            cp["publish_id"] = body["data"]["publish_id"]
            cp["upload_url"] = body["data"]["upload_url"]
            cp["privacy_level"] = privacy
            cp["restricted"] = restricted
        if not cp.get("uploaded"):
            response = await self.http.put(
                cp["upload_url"],
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{len(video) - 1}/{len(video)}",
                },
                content=video,
            )
            if response.status_code >= 400:
                raise PublisherError(f"tiktok: upload failed ({response.status_code})")
            cp["uploaded"] = True
        post_id = await self._wait_publish(cp["publish_id"])
        cp["post_id"] = post_id
        restricted = bool(cp.get("restricted"))
        return PublishOutcome(
            platform="tiktok",
            status="restricted" if restricted else "published",
            post_id=post_id,
            note=UNAUDITED_NOTE if restricted else None,
            checkpoint=cp,
        )

    async def _privacy_level(self) -> tuple[str, bool]:
        response = await self.http.post(
            f"{self.api}/v2/post/publish/creator_info/query/", headers=self.headers
        )
        body = response_json(response, "tiktok: creator info")
        options = (body.get("data") or {}).get("privacy_level_options") or []
        if "PUBLIC_TO_EVERYONE" in options:
            return "PUBLIC_TO_EVERYONE", False
        return "SELF_ONLY", True

    async def _init(
        self, request: PublishRequest, privacy: str, size: int
    ) -> tuple[dict[str, Any], str | None]:
        response = await self.http.post(
            f"{self.api}/v2/post/publish/video/init/",
            headers=self.headers,
            json={
                "post_info": {
                    "title": request.full_caption()[:2200],
                    "privacy_level": privacy,
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": size,
                    "chunk_size": size,
                    "total_chunk_count": 1,
                },
            },
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise PublisherError(
                f"tiktok: init non-JSON response ({response.status_code})"
            ) from exc
        code = (body.get("error") or {}).get("code")
        return body, code

    async def _wait_publish(self, publish_id: str) -> str:
        result: dict[str, str] = {}

        async def done() -> bool:
            response = await self.http.post(
                f"{self.api}/v2/post/publish/status/fetch/",
                headers=self.headers,
                json={"publish_id": publish_id},
            )
            body = response_json(response, "tiktok: status")
            data = body.get("data") or {}
            status = data.get("status")
            if status == "FAILED":
                raise PublisherError(f"tiktok: publish failed ({data.get('fail_reason')})")
            if status == "PUBLISH_COMPLETE":
                ids = data.get("publicaly_available_post_id") or []
                result["post_id"] = str(ids[0]) if ids else publish_id
                return True
            return False

        await poll_until(
            done, interval=self.poll_interval, attempts=self.poll_attempts, what="tiktok publish"
        )
        return result["post_id"]

    async def metrics(self, post_id: str) -> PostMetrics:
        response = await self.http.post(
            f"{self.api}/v2/video/query/",
            headers=self.headers,
            params={"fields": "id,view_count,like_count,comment_count,share_count"},
            json={"filters": {"video_ids": [post_id]}},
        )
        body = response_json(response, "tiktok: video query")
        videos = (body.get("data") or {}).get("videos") or []
        video = videos[0] if videos else {}
        return finish_metrics(
            PostMetrics(
                platform="tiktok",
                post_id=post_id,
                views=video.get("view_count"),
                likes=video.get("like_count"),
                comments=video.get("comment_count"),
                shares=video.get("share_count"),
                fetched_at=utc_now_iso(),
            )
        )
