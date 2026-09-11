"""Platform adapters. Each publishes one rendered short and reads back its metrics."""

from __future__ import annotations

import httpx

from ..config import Platform, Settings
from .base import (
    PostMetrics,
    Publisher,
    PublisherError,
    PublisherNotConfigured,
    PublishOutcome,
    PublishRequest,
)
from .meta import FacebookReelsPublisher, InstagramReelsPublisher
from .tiktok import TikTokPublisher
from .youtube import YouTubeShortsPublisher

__all__ = [
    "PostMetrics",
    "PublishOutcome",
    "PublishRequest",
    "Publisher",
    "PublisherError",
    "PublisherNotConfigured",
    "build_publisher",
]


def build_publisher(platform: Platform, settings: Settings, http: httpx.AsyncClient) -> Publisher:
    match platform:
        case "instagram":
            return InstagramReelsPublisher(settings, http)
        case "facebook":
            return FacebookReelsPublisher(settings, http)
        case "tiktok":
            return TikTokPublisher(settings, http)
        case "youtube":
            return YouTubeShortsPublisher(settings, http)
    raise PublisherError(f"unknown platform {platform}")
