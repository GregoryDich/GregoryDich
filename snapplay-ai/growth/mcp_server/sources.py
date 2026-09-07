"""Pluggable clip providers.

Only rights-cleared audio may be turned into advertising. Commercial recordings must never be
used here: the licensed-folder provider lists clips the operator holds a licence for, the Free
Music Archive provider keeps only licences that allow commercial *and* derivative use, and the
URL provider records that the caller asserted the rights.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, Protocol

import httpx
import soundfile as sf
from pydantic import BaseModel, Field

SourceKind = Literal["licensed_folder", "free_music_archive", "urls"]
AUDIO_SUFFIXES: frozenset[str] = frozenset({".wav", ".flac", ".mp3", ".ogg", ".aiff", ".aif"})
RIGHTS_NOTICE = (
    "Use only audio you hold advertising rights for. Commercial recordings (label releases, "
    "streaming catalogue, sample packs without a sync licence) must not be used in ads."
)


class SourceClip(BaseModel):
    ref: str = Field(description="Local path or URL passed to process_clip")
    title: str
    source: SourceKind
    license: str | None = None
    attribution: str | None = None
    duration_seconds: float | None = None


class ClipProvider(Protocol):
    async def list_clips(self, limit: int) -> list[SourceClip]: ...


def _read_sidecar(path: Path) -> dict[str, str]:
    sidecar = path.with_suffix(".json")
    if not sidecar.is_file():
        return {}
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: str(v) for k, v in data.items() if isinstance(v, str | int | float)}


def probe_duration(path: Path) -> float | None:
    try:
        info = sf.info(str(path))
    except (RuntimeError, OSError):
        return None
    return round(info.frames / info.samplerate, 3) if info.samplerate else None


class LicensedFolderProvider:
    """Audio files under ``LICENSED_CLIPS_DIR``; ``<name>.json`` sidecars add licence metadata."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    async def list_clips(self, limit: int) -> list[SourceClip]:
        if not self.directory.is_dir():
            return []
        files = sorted(
            p
            for p in self.directory.iterdir()
            if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
        )
        clips: list[SourceClip] = []
        for path in files[:limit]:
            meta = _read_sidecar(path)
            clips.append(
                SourceClip(
                    ref=str(path.resolve()),
                    title=meta.get("title", path.stem),
                    source="licensed_folder",
                    license=meta.get("license", "operator-licensed"),
                    attribution=meta.get("attribution"),
                    duration_seconds=probe_duration(path),
                )
            )
        return clips


_NON_COMMERCIAL = re.compile(r"non[- ]?commercial|\bNC\b|no[- ]?derivatives?|\bND\b", re.I)
_COMMERCIAL_OK = re.compile(r"CC0|public domain|attribution|\bBY\b", re.I)


def license_allows_ads(license_title: str | None) -> bool:
    """True for CC0 / public domain / CC BY / CC BY-SA; NC and ND variants are rejected."""
    if not license_title:
        return False
    if _NON_COMMERCIAL.search(license_title):
        return False
    return bool(_COMMERCIAL_OK.search(license_title))


class FreeMusicArchiveProvider:
    """``GET {FMA_API_URL}/tracks.json?api_key=…&limit=…`` filtered to ad-safe licences."""

    def __init__(self, api_url: str, api_key: str, http: httpx.AsyncClient) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.http = http

    async def list_clips(self, limit: int) -> list[SourceClip]:
        response = await self.http.get(
            f"{self.api_url}/tracks.json",
            params={"api_key": self.api_key, "limit": max(limit * 3, limit)},
        )
        response.raise_for_status()
        rows = response.json().get("dataset", [])
        clips: list[SourceClip] = []
        for row in rows:
            license_title = row.get("license_title")
            if not license_allows_ads(license_title):
                continue
            file_url = row.get("track_file_url") or row.get("track_file")
            if not file_url:
                continue
            duration = _parse_duration(row.get("track_duration"))
            artist = row.get("artist_name") or "Unknown artist"
            clips.append(
                SourceClip(
                    ref=file_url,
                    title=row.get("track_title") or f"track {row.get('track_id')}",
                    source="free_music_archive",
                    license=license_title,
                    attribution=f"{artist} — {row.get('track_url') or 'freemusicarchive.org'}",
                    duration_seconds=duration,
                )
            )
            if len(clips) >= limit:
                break
        return clips


def _parse_duration(value: object) -> float | None:
    """FMA reports ``mm:ss`` or ``hh:mm:ss``; numbers pass through."""
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str) or not value:
        return None
    parts = value.split(":")
    try:
        numbers = [float(p) for p in parts]
    except ValueError:
        return None
    total = 0.0
    for n in numbers:
        total = total * 60 + n
    return total


class UrlListProvider:
    def __init__(self, urls: list[str]) -> None:
        self.urls = urls

    async def list_clips(self, limit: int) -> list[SourceClip]:
        return [
            SourceClip(
                ref=url,
                title=Path(httpx.URL(url).path).stem or url,
                source="urls",
                license="asserted by caller",
            )
            for url in self.urls[:limit]
        ]
