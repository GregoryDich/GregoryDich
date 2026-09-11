"""Clip providers and the licence filter."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from fastmcp import Client

from mcp_server.licensing import LicenseAttestation
from mcp_server.sources import (
    FreeMusicArchiveProvider,
    LicensedFolderProvider,
    UrlListProvider,
    license_allows_ads,
)


@pytest.mark.parametrize(
    ("title", "allowed"),
    [
        ("Attribution", True),
        ("Attribution-ShareAlike", True),
        ("CC0 1.0 Universal", True),
        ("Public Domain Mark", True),
        ("Attribution-NonCommercial", False),
        ("Attribution-NoDerivatives", False),
        ("CC BY-NC-SA 4.0", False),
        ("All rights reserved", False),
        (None, False),
    ],
)
def test_license_filter(title: str | None, allowed: bool) -> None:
    assert license_allows_ads(title) is allowed


async def test_licensed_folder_lists_audio_with_sidecar(clip_file: Path) -> None:
    (clip_file.parent / "notes.txt").write_text("not audio")
    clips = await LicensedFolderProvider(clip_file.parent).list_clips(10)
    assert len(clips) == 1
    clip = clips[0]
    assert clip.ref == str(clip_file.resolve())
    assert clip.title == "Night Loop"
    assert clip.license == "operator-licensed"
    assert clip.attribution == "in-house"
    assert clip.duration_seconds == pytest.approx(2.0, abs=0.01)


async def test_licensed_folder_missing_dir_is_empty(tmp_path: Path) -> None:
    assert await LicensedFolderProvider(tmp_path / "nope").list_clips(5) == []


async def test_fma_provider_keeps_only_ad_safe_licences(router: respx.Router) -> None:
    route = router.get("https://fma.test/api/get/tracks.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "dataset": [
                    {
                        "track_id": 1,
                        "track_title": "Open",
                        "artist_name": "A",
                        "track_url": "https://fma.test/a/open",
                        "track_file_url": "https://cdn.fma.test/open.mp3",
                        "license_title": "Attribution",
                        "track_duration": "02:30",
                    },
                    {
                        "track_id": 2,
                        "track_title": "Closed",
                        "artist_name": "B",
                        "track_file_url": "https://cdn.fma.test/closed.mp3",
                        "license_title": "Attribution-NonCommercial",
                        "track_duration": "01:00",
                    },
                ]
            },
        )
    )
    async with httpx.AsyncClient() as http:
        clips = await FreeMusicArchiveProvider("https://fma.test/api/get", "k", http).list_clips(5)
    assert [c.title for c in clips] == ["Open"]
    assert clips[0].duration_seconds == 150.0
    assert clips[0].attribution == "A — https://fma.test/a/open"
    assert route.calls.last.request.url.params["api_key"] == "k"


async def test_url_provider_rights_stay_unknown_without_an_attestation() -> None:
    clips = await UrlListProvider(["https://x.test/a/beat.wav"]).list_clips(5)
    assert clips[0].title == "beat"
    assert clips[0].license == "unknown"
    assert clips[0].rights.status == "unknown"
    assert "license_attestation" in (clips[0].rights.reason or "")


async def test_url_provider_records_an_attestation() -> None:
    attestation = LicenseAttestation(
        license="buy-out contract 2026-03",
        permits_advertising=True,
        authority="Producer A, invoice 118",
        attribution="Producer A",
    )
    clips = await UrlListProvider(["https://x.test/a/beat.wav"], attestation).list_clips(5)
    assert clips[0].rights.status == "cleared"
    assert clips[0].rights.evidence == "operator attestation (Producer A, invoice 118)"
    assert clips[0].attribution == "Producer A"


async def test_list_source_clips_tool(mcp_client: Client, clip_file: Path) -> None:
    result = await mcp_client.call_tool("list_source_clips", {})
    data = result.structured_content
    assert data["source"] == "licensed_folder"
    assert "Commercial recordings" in data["notice"]
    assert [c["title"] for c in data["clips"]] == ["Night Loop"]

    result = await mcp_client.call_tool(
        "list_source_clips", {"source": "urls", "urls": ["https://x.test/loop.wav"]}
    )
    assert result.structured_content["clips"][0]["ref"] == "https://x.test/loop.wav"

    with pytest.raises(Exception, match="requires at least one URL"):
        await mcp_client.call_tool("list_source_clips", {"source": "urls"})
