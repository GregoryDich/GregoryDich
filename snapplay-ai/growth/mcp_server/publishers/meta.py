"""Meta Graph API Reels publishing: Instagram (resumable container → publish) and Facebook
Page Reels (start → upload → finish). Insights fetch metrics for both.
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
    to_unix,
)


def _metric_value(entry: dict[str, Any]) -> int | None:
    values = entry.get("values")
    if isinstance(values, list) and values:
        value = values[0].get("value")
    else:
        value = (entry.get("total_value") or {}).get("value")
    if isinstance(value, dict):
        return sum(v for v in value.values() if isinstance(v, int))
    return int(value) if isinstance(value, int | float) else None


class InstagramReelsPublisher:
    platform = "instagram"

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        if not (settings.meta_ig_user_id and settings.meta_ig_access_token):
            raise PublisherNotConfigured("META_IG_USER_ID / META_IG_ACCESS_TOKEN not set")
        self.graph = f"{settings.meta_graph_api_url.rstrip('/')}/{settings.meta_api_version}"
        self.upload = (
            f"{settings.meta_upload_api_url.rstrip('/')}/ig-api-upload/{settings.meta_api_version}"
        )
        self.user_id = settings.meta_ig_user_id
        self.token = settings.meta_ig_access_token
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
        # The Instagram content publishing API has no native scheduling: a future
        # schedule_at is kept locally and published by run_daily_batch when due.
        if is_future(request.schedule_at):
            return PublishOutcome(
                platform="instagram",
                status="scheduled",
                note="Instagram has no API-side scheduling; will publish when due",
                checkpoint=cp,
            )
        if "container_id" not in cp:
            response = await self.http.post(
                f"{self.graph}/{self.user_id}/media",
                data={
                    "media_type": "REELS",
                    "upload_type": "resumable",
                    "caption": request.full_caption(),
                    "share_to_feed": "true",
                    "access_token": self.token,
                },
            )
            body = response_json(response, "instagram: create container")
            cp["container_id"] = body["id"]
        if not cp.get("uploaded"):
            video = read_video(request.video_path)
            response = await self.http.post(
                f"{self.upload}/{cp['container_id']}",
                headers={
                    "Authorization": f"OAuth {self.token}",
                    "offset": "0",
                    "file_size": str(len(video)),
                    "Content-Type": "application/octet-stream",
                },
                content=video,
            )
            body = response_json(response, "instagram: upload")
            if not body.get("success", False):
                raise PublisherError("instagram: upload rejected")
            cp["uploaded"] = True
        if "media_id" not in cp:
            await self._wait_container(cp["container_id"])
            response = await self.http.post(
                f"{self.graph}/{self.user_id}/media_publish",
                data={"creation_id": cp["container_id"], "access_token": self.token},
            )
            body = response_json(response, "instagram: publish")
            cp["media_id"] = body["id"]
        url = await self._permalink(cp["media_id"])
        return PublishOutcome(
            platform="instagram", status="published", post_id=cp["media_id"], url=url, checkpoint=cp
        )

    async def _wait_container(self, container_id: str) -> None:
        async def ready() -> bool:
            response = await self.http.get(
                f"{self.graph}/{container_id}",
                params={"fields": "status_code,status", "access_token": self.token},
            )
            body = response_json(response, "instagram: container status")
            code = body.get("status_code")
            if code in ("ERROR", "EXPIRED"):
                raise PublisherError(f"instagram: container {code}")
            return code == "FINISHED"

        await poll_until(
            ready,
            interval=self.poll_interval,
            attempts=self.poll_attempts,
            what="instagram container",
        )

    async def _permalink(self, media_id: str) -> str | None:
        response = await self.http.get(
            f"{self.graph}/{media_id}", params={"fields": "permalink", "access_token": self.token}
        )
        if response.status_code >= 400:
            return None
        return response.json().get("permalink")

    async def metrics(self, post_id: str) -> PostMetrics:
        response = await self.http.get(
            f"{self.graph}/{post_id}/insights",
            params={"metric": "views,likes,comments,shares,reach", "access_token": self.token},
        )
        body = response_json(response, "instagram: insights")
        values = {e.get("name"): _metric_value(e) for e in body.get("data", [])}
        return finish_metrics(
            PostMetrics(
                platform="instagram",
                post_id=post_id,
                views=values.get("views"),
                likes=values.get("likes"),
                comments=values.get("comments"),
                shares=values.get("shares"),
                fetched_at=utc_now_iso(),
            )
        )


class FacebookReelsPublisher:
    platform = "facebook"

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        if not (settings.meta_page_id and settings.meta_page_access_token):
            raise PublisherNotConfigured("META_PAGE_ID / META_PAGE_ACCESS_TOKEN not set")
        self.graph = f"{settings.meta_graph_api_url.rstrip('/')}/{settings.meta_api_version}"
        self.upload = (
            f"{settings.meta_upload_api_url.rstrip('/')}/video-upload/{settings.meta_api_version}"
        )
        self.page_id = settings.meta_page_id
        self.token = settings.meta_page_access_token
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
        if "video_id" not in cp:
            response = await self.http.post(
                f"{self.graph}/{self.page_id}/video_reels",
                data={"upload_phase": "start", "access_token": self.token},
            )
            body = response_json(response, "facebook: start")
            cp["video_id"] = body["video_id"]
            cp["upload_url"] = body.get("upload_url") or f"{self.upload}/{body['video_id']}"
        if not cp.get("uploaded"):
            video = read_video(request.video_path)
            response = await self.http.post(
                cp["upload_url"],
                headers={
                    "Authorization": f"OAuth {self.token}",
                    "offset": "0",
                    "file_size": str(len(video)),
                    "Content-Type": "application/octet-stream",
                },
                content=video,
            )
            body = response_json(response, "facebook: upload")
            if not body.get("success", False):
                raise PublisherError("facebook: upload rejected")
            cp["uploaded"] = True
        if not cp.get("finished"):
            await self._wait_upload(cp["video_id"])
            data = {
                "upload_phase": "finish",
                "video_id": cp["video_id"],
                "description": request.full_caption(),
                "access_token": self.token,
            }
            scheduled = is_future(request.schedule_at)
            if scheduled:
                data["video_state"] = "SCHEDULED"
                data["scheduled_publish_time"] = str(to_unix(request.schedule_at or ""))
            else:
                data["video_state"] = "PUBLISHED"
            response = await self.http.post(f"{self.graph}/{self.page_id}/video_reels", data=data)
            body = response_json(response, "facebook: finish")
            if not body.get("success", False):
                raise PublisherError("facebook: finish rejected")
            cp["finished"] = True
            cp["post_id"] = body.get("post_id") or cp["video_id"]
            cp["scheduled"] = scheduled
        status = "scheduled" if cp.get("scheduled") else "published"
        return PublishOutcome(
            platform="facebook",
            status=status,
            post_id=cp["post_id"],
            url=f"https://www.facebook.com/reel/{cp['video_id']}",
            checkpoint=cp,
        )

    async def _wait_upload(self, video_id: str) -> None:
        async def ready() -> bool:
            response = await self.http.get(
                f"{self.graph}/{video_id}", params={"fields": "status", "access_token": self.token}
            )
            body = response_json(response, "facebook: video status")
            status = body.get("status") or {}
            if status.get("video_status") == "error":
                raise PublisherError("facebook: video processing error")
            phase = (status.get("uploading_phase") or {}).get("status")
            return phase == "complete" or status.get("video_status") in ("upload_complete", "ready")

        await poll_until(
            ready, interval=self.poll_interval, attempts=self.poll_attempts, what="facebook upload"
        )

    async def metrics(self, post_id: str) -> PostMetrics:
        response = await self.http.get(
            f"{self.graph}/{post_id}/video_insights",
            params={
                "metric": "total_video_views,total_video_impressions,"
                "total_video_reactions_by_type_total,post_video_social_actions",
                "access_token": self.token,
            },
        )
        body = response_json(response, "facebook: video insights")
        values = {e.get("name"): _metric_value(e) for e in body.get("data", [])}
        return finish_metrics(
            PostMetrics(
                platform="facebook",
                post_id=post_id,
                views=values.get("total_video_views"),
                impressions=values.get("total_video_impressions"),
                likes=values.get("total_video_reactions_by_type_total"),
                shares=values.get("post_video_social_actions"),
                fetched_at=utc_now_iso(),
            )
        )
