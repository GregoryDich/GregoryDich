"""Pull per-post metrics from each platform and store them on the content item."""

from __future__ import annotations

import httpx
from pydantic import BaseModel, Field

from .config import Settings
from .publishers import PostMetrics, PublisherError, PublisherNotConfigured, build_publisher
from .state import Store


class MetricsReport(BaseModel):
    since: str
    posts: list[PostMetrics] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


async def collect_metrics(
    store: Store, settings: Settings, http: httpx.AsyncClient, since_iso: str
) -> MetricsReport:
    report = MetricsReport(since=since_iso)
    for item, platform in store.published_items(since_iso):
        record = item.publish_record(platform)
        try:
            publisher = build_publisher(platform, settings, http)  # type: ignore[arg-type]
            metrics = await publisher.metrics(record.post_id or "")
        except (PublisherNotConfigured, PublisherError, httpx.HTTPError) as exc:
            report.errors.append(f"{item.id}/{platform}: {exc}")
            continue
        store.set_metrics(item.id, platform, metrics.model_dump())
        report.posts.append(metrics)
    return report
