"""YouTube Data API v3 resumable upload for Shorts (vertical, ≤ 60 s, ``#Shorts`` tagged)."""

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
    read_video,
    response_json,
)

MUSIC_CATEGORY_ID = "10"


class YouTubeShortsPublisher:
    platform = "youtube"

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        if not settings.youtube_access_token:
            raise PublisherNotConfigured("YOUTUBE_ACCESS_TOKEN not set")
        self.api = settings.youtube_api_url.rstrip("/")
        self.auth = {"Authorization": f"Bearer {settings.youtube_access_token}"}
        self.http = http

    async def publish(self, request: PublishRequest, checkpoint: dict[str, Any]) -> PublishOutcome:
        cp = dict(checkpoint)
        try:
            return await self._publish(request, cp)
        except PublisherError as exc:
            exc.checkpoint = cp
            raise

    async def _publish(self, request: PublishRequest, cp: dict[str, Any]) -> PublishOutcome:
        video = read_video(request.video_path)
        scheduled = is_future(request.schedule_at)
        if "video_id" not in cp:
            if "upload_url" not in cp:
                cp["upload_url"] = await self._start_session(request, len(video), scheduled)
            cp["video_id"] = await self._upload(cp["upload_url"], video)
            cp["scheduled"] = scheduled
        return PublishOutcome(
            platform="youtube",
            status="scheduled" if cp.get("scheduled") else "published",
            post_id=cp["video_id"],
            url=f"https://youtube.com/shorts/{cp['video_id']}",
            checkpoint=cp,
        )

    async def _start_session(self, request: PublishRequest, size: int, scheduled: bool) -> str:
        title = request.title if "#shorts" in request.title.lower() else f"{request.title} #Shorts"
        status: dict[str, Any] = {"selfDeclaredMadeForKids": False}
        if scheduled:
            status["privacyStatus"] = "private"
            status["publishAt"] = request.schedule_at
        else:
            status["privacyStatus"] = "public"
        response = await self.http.post(
            f"{self.api}/upload/youtube/v3/videos",
            params={"uploadType": "resumable", "part": "snippet,status"},
            headers={
                **self.auth,
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(size),
                "X-Upload-Content-Type": "video/mp4",
            },
            json={
                "snippet": {
                    "title": title[:100],
                    "description": request.full_caption()[:5000],
                    "tags": [t.lstrip("#") for t in request.hashtags][:30],
                    "categoryId": MUSIC_CATEGORY_ID,
                },
                "status": status,
            },
        )
        if response.status_code >= 400:
            response_json(response, "youtube: start session")
        location = response.headers.get("Location")
        if not location:
            raise PublisherError("youtube: resumable session returned no Location header")
        return location

    async def _upload(self, upload_url: str, video: bytes) -> str:
        size = len(video)
        response = await self.http.put(
            upload_url,
            headers={**self.auth, "Content-Type": "video/mp4", "Content-Length": str(size)},
            content=video,
        )
        if response.status_code in (500, 502, 503, 504):
            # Ask the session how much arrived, then send the remainder once.
            probe = await self.http.put(
                upload_url,
                headers={**self.auth, "Content-Length": "0", "Content-Range": f"bytes */{size}"},
            )
            if probe.status_code == 308:
                received = probe.headers.get("Range", "bytes=0--1").split("-")[-1]
                offset = int(received) + 1 if received.lstrip("-").isdigit() else 0
                response = await self.http.put(
                    upload_url,
                    headers={
                        **self.auth,
                        "Content-Type": "video/mp4",
                        "Content-Length": str(size - offset),
                        "Content-Range": f"bytes {offset}-{size - 1}/{size}",
                    },
                    content=video[offset:],
                )
            elif probe.status_code in (200, 201):
                response = probe
        body = response_json(response, "youtube: upload")
        video_id = body.get("id")
        if not video_id:
            raise PublisherError("youtube: upload response carried no video id")
        return str(video_id)

    async def metrics(self, post_id: str) -> PostMetrics:
        response = await self.http.get(
            f"{self.api}/youtube/v3/videos",
            params={"part": "statistics", "id": post_id},
            headers=self.auth,
        )
        body = response_json(response, "youtube: statistics")
        items = body.get("items") or []
        stats = (items[0].get("statistics") if items else None) or {}

        def count(key: str) -> int | None:
            value = stats.get(key)
            return int(value) if value is not None and str(value).isdigit() else None

        return finish_metrics(
            PostMetrics(
                platform="youtube",
                post_id=post_id,
                views=count("viewCount"),
                likes=count("likeCount"),
                comments=count("commentCount"),
                fetched_at=utc_now_iso(),
            )
        )
