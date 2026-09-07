"""Pluggable clip providers.

Only rights-cleared audio may be turned into advertising. Commercial recordings must never be
used here, and no provider invents a licence: the licensed-folder provider reads the manifest
the operator wrote next to each clip (``licensing.py``), the Free Music Archive provider keeps
only licences that allow commercial *and* derivative use, and the URL provider reports
``unknown`` unless the caller attests to the rights explicitly. ``process_clip`` refuses
anything that is not cleared.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

import httpx
import soundfile as sf
from pydantic import BaseModel, Field

from .licensing import (
    LicenseAttestation,
    RightsRecord,
    license_allows_ads,
    manifest_entry,
    read_folder_manifest,
    rights_from_attestation,
    rights_from_fma,
    rights_from_manifest,
    unknown_rights,
)

SourceKind = Literal["licensed_folder", "free_music_archive", "urls"]
AUDIO_SUFFIXES: frozenset[str] = frozenset({".wav", ".flac", ".mp3", ".ogg", ".aiff", ".aif"})
RIGHTS_NOTICE = (
    "Use only audio you hold advertising rights for. Commercial recordings (label releases, "
    "streaming catalogue, sample packs without a sync licence) must not be used in ads. Clips "
    "whose rights are not established are listed with rights.status='unknown' and process_clip "
    "refuses them."
)

__all__ = [
    "AUDIO_SUFFIXES",
    "RIGHTS_NOTICE",
    "ClipProvider",
    "FreeMusicArchiveProvider",
    "LicensedFolderProvider",
    "SourceClip",
    "SourceKind",
    "UrlListProvider",
    "license_allows_ads",
    "probe_duration",
]


class SourceClip(BaseModel):
    ref: str = Field(description="Local path or URL passed to process_clip")
    title: str
    source: SourceKind
    license: str | None = None
    attribution: str | None = None
    duration_seconds: float | None = None
    rights: RightsRecord = Field(description="Where the licence came from and whether it clears")


class ClipProvider(Protocol):
    async def list_clips(self, limit: int) -> list[SourceClip]: ...


def _clip(
    ref: str, title: str, source: SourceKind, rights: RightsRecord, duration: float | None = None
) -> SourceClip:
    return SourceClip(
        ref=ref,
        title=title,
        source=source,
        license=rights.license,
        attribution=rights.attribution,
        duration_seconds=duration,
        rights=rights,
    )


def probe_duration(path: Path) -> float | None:
    try:
        info = sf.info(str(path))
    except (RuntimeError, OSError):
        return None
    return round(info.frames / info.samplerate, 3) if info.samplerate else None


def _title_from_manifest(path: Path, manifest: dict[str, dict[str, object]]) -> str:
    found = manifest_entry(path, manifest)
    title = found[0].get("title") if found else None
    return str(title) if title else path.stem


class LicensedFolderProvider:
    """Audio under ``LICENSED_CLIPS_DIR``, with the licence its manifest entry records.

    A clip with no manifest entry is listed with ``rights.status == "unknown"`` so the operator
    can see what is missing; nothing downstream will process it until an entry exists.
    """

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
        manifest = read_folder_manifest(self.directory)
        return [
            _clip(
                ref=str(path.resolve()),
                title=_title_from_manifest(path, manifest),
                source="licensed_folder",
                rights=rights_from_manifest(path, manifest),
                duration=probe_duration(path),
            )
            for path in files[:limit]
        ]


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
            artist = row.get("artist_name") or "Unknown artist"
            attribution = f"{artist} — {row.get('track_url') or 'freemusicarchive.org'}"
            clips.append(
                _clip(
                    ref=file_url,
                    title=row.get("track_title") or f"track {row.get('track_id')}",
                    source="free_music_archive",
                    rights=rights_from_fma(license_title, attribution),
                    duration=_parse_duration(row.get("track_duration")),
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
    """Caller-supplied URLs. A URL is not evidence of a licence: without an attestation the
    rights stay ``unknown`` and ``process_clip`` refuses the clip."""

    def __init__(self, urls: list[str], attestation: LicenseAttestation | None = None) -> None:
        self.urls = urls
        self.attestation = attestation

    async def list_clips(self, limit: int) -> list[SourceClip]:
        rights = (
            rights_from_attestation(self.attestation)
            if self.attestation is not None
            else unknown_rights(
                evidence="none",
                reason=(
                    "a caller-supplied URL carries no licence the engine can verify; pass "
                    "license_attestation to record the rights you hold"
                ),
            )
        )
        return [
            _clip(
                ref=url,
                title=Path(httpx.URL(url).path).stem or url,
                source="urls",
                rights=rights,
            )
            for url in self.urls[:limit]
        ]
