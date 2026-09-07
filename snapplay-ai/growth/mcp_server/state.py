"""SQLite persistence for content items.

One row per content item. Per-platform publish state and metrics are JSON columns so a
re-run of any tool can look up what already happened and never double-post.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

PublishStatus = Literal["pending", "scheduled", "published", "restricted", "failed"]
ACTIVE_PUBLISH_STATUSES: frozenset[str] = frozenset({"scheduled", "published", "restricted"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS content_items (
    id           TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    source_ref   TEXT NOT NULL,
    job_id       TEXT,
    chosen_stem  TEXT,
    stem_scores  TEXT NOT NULL DEFAULT '[]',
    script_json  TEXT,
    assets_json  TEXT NOT NULL DEFAULT '{}',
    publish_json TEXT NOT NULL DEFAULT '{}',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    rights_json  TEXT,
    disclosure_json TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS content_items_source_ref ON content_items (source, source_ref);
CREATE INDEX IF NOT EXISTS content_items_job_id ON content_items (job_id);
"""
# Columns added after the first release; a database written by an earlier version is migrated
# in place on open.
_ADDED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("rights_json", "TEXT"),
    ("disclosure_json", "TEXT"),
)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class PublishRecord(BaseModel):
    status: PublishStatus = "pending"
    post_id: str | None = None
    url: str | None = None
    note: str | None = None
    error: str | None = None
    schedule_at: str | None = None
    published_at: str | None = None
    caption: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    link: str | None = Field(
        default=None, description="The UTM-tagged landing URL this post sends viewers to"
    )
    attribution_line: str | None = None
    disclosure_line: str | None = None
    ai_flag_set: bool = Field(
        default=False, description="True when the platform API accepted an AI-content flag"
    )


class ContentItem(BaseModel):
    id: str
    source: str
    source_ref: str
    job_id: str | None = None
    chosen_stem: str | None = None
    stem_scores: list[dict[str, Any]] = Field(default_factory=list)
    script: dict[str, Any] | None = None
    assets: dict[str, Any] = Field(default_factory=dict)
    publish: dict[str, PublishRecord] = Field(default_factory=dict)
    metrics: dict[str, dict[str, Any]] = Field(default_factory=dict)
    rights: dict[str, Any] | None = Field(
        default=None, description="The RightsRecord process_clip cleared the source with"
    )
    disclosure: dict[str, Any] | None = Field(
        default=None, description="The AI-disclosure state render_video recorded"
    )
    created_at: str
    updated_at: str

    def publish_record(self, platform: str) -> PublishRecord:
        return self.publish.get(platform) or PublishRecord()

    def is_posted(self, platform: str) -> bool:
        return self.publish_record(platform).status in ACTIVE_PUBLISH_STATUSES


def _row_to_item(row: sqlite3.Row) -> ContentItem:
    return ContentItem(
        id=row["id"],
        source=row["source"],
        source_ref=row["source_ref"],
        job_id=row["job_id"],
        chosen_stem=row["chosen_stem"],
        stem_scores=json.loads(row["stem_scores"]),
        script=json.loads(row["script_json"]) if row["script_json"] else None,
        assets=json.loads(row["assets_json"]),
        publish={k: PublishRecord(**v) for k, v in json.loads(row["publish_json"]).items()},
        metrics=json.loads(row["metrics_json"]),
        rights=json.loads(row["rights_json"]) if row["rights_json"] else None,
        disclosure=json.loads(row["disclosure_json"]) if row["disclosure_json"] else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class Store:
    """Thread-safe by construction: one short-lived connection per operation."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30)
        try:
            conn.executescript(_SCHEMA)
            existing = {r[1] for r in conn.execute("PRAGMA table_info(content_items)")}
            for column, kind in _ADDED_COLUMNS:
                if column not in existing:
                    conn.execute(f"ALTER TABLE content_items ADD COLUMN {column} {kind}")
            conn.commit()
        finally:
            conn.close()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def create_item(self, source: str, source_ref: str) -> ContentItem:
        now = utc_now_iso()
        item_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO content_items (id, source, source_ref, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (item_id, source, source_ref, now, now),
            )
        return ContentItem(
            id=item_id, source=source, source_ref=source_ref, created_at=now, updated_at=now
        )

    def get(self, item_id: str) -> ContentItem | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_item(row) if row else None

    def require(self, item_id: str) -> ContentItem:
        item = self.get(item_id)
        if item is None:
            raise KeyError(f"content item {item_id} not found")
        return item

    def find_by_source_ref(self, source: str, source_ref: str) -> ContentItem | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM content_items WHERE source = ? AND source_ref = ?"
                " ORDER BY created_at DESC LIMIT 1",
                (source, source_ref),
            ).fetchone()
        return _row_to_item(row) if row else None

    def list_items(self, limit: int = 100) -> list[ContentItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM content_items ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_item(r) for r in rows]

    def known_source_refs(self, source: str) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT source_ref FROM content_items WHERE source = ?", (source,)
            ).fetchall()
        return {r["source_ref"] for r in rows}

    def update(
        self,
        item_id: str,
        *,
        job_id: str | None = None,
        chosen_stem: str | None = None,
        stem_scores: list[dict[str, Any]] | None = None,
        script: dict[str, Any] | None = None,
        assets: dict[str, Any] | None = None,
        rights: dict[str, Any] | None = None,
        disclosure: dict[str, Any] | None = None,
    ) -> ContentItem:
        """Set the given columns; ``assets`` is merged into the stored asset map."""
        sets: list[str] = []
        params: list[Any] = []
        if job_id is not None:
            sets.append("job_id = ?")
            params.append(job_id)
        if chosen_stem is not None:
            sets.append("chosen_stem = ?")
            params.append(chosen_stem)
        if stem_scores is not None:
            sets.append("stem_scores = ?")
            params.append(json.dumps(stem_scores))
        if script is not None:
            sets.append("script_json = ?")
            params.append(json.dumps(script))
        if rights is not None:
            sets.append("rights_json = ?")
            params.append(json.dumps(rights))
        if disclosure is not None:
            sets.append("disclosure_json = ?")
            params.append(json.dumps(disclosure))
        with self._connect() as conn:
            if assets is not None:
                row = conn.execute(
                    "SELECT assets_json FROM content_items WHERE id = ?", (item_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(f"content item {item_id} not found")
                merged = {**json.loads(row["assets_json"]), **assets}
                sets.append("assets_json = ?")
                params.append(json.dumps(merged))
            sets.append("updated_at = ?")
            params.append(utc_now_iso())
            params.append(item_id)
            cur = conn.execute(f"UPDATE content_items SET {', '.join(sets)} WHERE id = ?", params)
            if cur.rowcount == 0:
                raise KeyError(f"content item {item_id} not found")
            row = conn.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_item(row)

    def set_publish_record(self, item_id: str, platform: str, record: PublishRecord) -> ContentItem:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT publish_json FROM content_items WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"content item {item_id} not found")
            publish = json.loads(row["publish_json"])
            publish[platform] = record.model_dump()
            conn.execute(
                "UPDATE content_items SET publish_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(publish), utc_now_iso(), item_id),
            )
            row = conn.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_item(row)

    def set_metrics(self, item_id: str, platform: str, metrics: dict[str, Any]) -> ContentItem:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT metrics_json FROM content_items WHERE id = ?", (item_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"content item {item_id} not found")
            stored = json.loads(row["metrics_json"])
            stored[platform] = metrics
            conn.execute(
                "UPDATE content_items SET metrics_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(stored), utc_now_iso(), item_id),
            )
            row = conn.execute("SELECT * FROM content_items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_item(row)

    def published_items(self, since_iso: str | None = None) -> list[tuple[ContentItem, str]]:
        """(item, platform) pairs with a published post, optionally published on/after since."""
        since = parse_iso(since_iso) if since_iso else None
        pairs: list[tuple[ContentItem, str]] = []
        for item in self.list_items(limit=100_000):
            for platform, record in item.publish.items():
                if record.status != "published" or not record.post_id:
                    continue
                if since and record.published_at and parse_iso(record.published_at) < since:
                    continue
                pairs.append((item, platform))
        return pairs

    def count_published_since(self, platform: str, since_iso: str) -> int:
        return sum(1 for _, p in self.published_items(since_iso) if p == platform)

    def scheduled_items(self, platform: str | None = None) -> list[tuple[ContentItem, str]]:
        pairs: list[tuple[ContentItem, str]] = []
        for item in self.list_items(limit=100_000):
            for plat, record in item.publish.items():
                if record.status == "scheduled" and (platform is None or plat == platform):
                    pairs.append((item, plat))
        return pairs
