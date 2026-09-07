"""SQLite store: persistence, merging and publish bookkeeping."""

from __future__ import annotations

import pytest

from mcp_server.state import PublishRecord, Store


def test_create_get_update(store: Store) -> None:
    item = store.create_item("licensed_folder", "/clips/a.wav")
    assert store.get(item.id) == item
    assert store.get("missing") is None
    with pytest.raises(KeyError):
        store.require("missing")
    updated = store.update(item.id, job_id="j1", chosen_stem="bass", assets={"a": "1"})
    updated = store.update(item.id, assets={"b": "2"}, script={"hook": "h"})
    assert updated.job_id == "j1"
    assert updated.chosen_stem == "bass"
    assert updated.assets == {"a": "1", "b": "2"}
    assert updated.script == {"hook": "h"}
    assert store.find_by_source_ref("licensed_folder", "/clips/a.wav").id == item.id
    assert store.known_source_refs("licensed_folder") == {"/clips/a.wav"}


def test_publish_records_and_queries(store: Store) -> None:
    a = store.create_item("licensed_folder", "/clips/a.wav")
    b = store.create_item("licensed_folder", "/clips/b.wav")
    store.set_publish_record(
        a.id,
        "youtube",
        PublishRecord(status="published", post_id="y1", published_at="2026-09-01T00:00:00Z"),
    )
    store.set_publish_record(
        b.id,
        "youtube",
        PublishRecord(status="published", post_id="y2", published_at="2026-09-06T00:00:00Z"),
    )
    store.set_publish_record(
        b.id, "instagram", PublishRecord(status="scheduled", schedule_at="2026-09-07T00:00:00Z")
    )
    store.set_publish_record(b.id, "tiktok", PublishRecord(status="failed", error="boom"))

    assert store.require(a.id).is_posted("youtube")
    assert store.require(b.id).is_posted("instagram")
    assert not store.require(b.id).is_posted("tiktok")
    assert {(i.id, p) for i, p in store.published_items()} == {(a.id, "youtube"), (b.id, "youtube")}
    assert [(i.id, p) for i, p in store.published_items("2026-09-05T00:00:00Z")] == [
        (b.id, "youtube")
    ]
    assert store.count_published_since("youtube", "2026-01-01T00:00:00Z") == 2
    assert store.count_published_since("instagram", "2026-01-01T00:00:00Z") == 0
    assert [(i.id, p) for i, p in store.scheduled_items()] == [(b.id, "instagram")]
    assert store.scheduled_items("youtube") == []


def test_metrics_are_stored_per_platform(store: Store) -> None:
    item = store.create_item("urls", "https://x/a.wav")
    store.set_metrics(item.id, "youtube", {"views": 10})
    store.set_metrics(item.id, "tiktok", {"views": 3})
    assert store.require(item.id).metrics == {"youtube": {"views": 10}, "tiktok": {"views": 3}}
