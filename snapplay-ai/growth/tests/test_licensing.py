"""Rights records and the process_clip gate: no licence, no job (docs/GROWTH.md §2)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_server.licensing import (
    LicenseAttestation,
    RightsNotEstablished,
    parse_attestation,
    resolve_rights,
    rights_from_manifest,
)
from mcp_server.state import Store
from tests.conftest import SNAPPLAY_URL, make_job_result, make_wav_bytes, mock_snapplay


def _clip(directory: Path, name: str = "unlicensed.wav") -> Path:
    path = directory / name
    path.write_bytes(make_wav_bytes(0.5))
    return path


# --- manifest formats ------------------------------------------------------------------------


def test_missing_manifest_entry_is_unknown(tmp_path: Path) -> None:
    rights = rights_from_manifest(_clip(tmp_path))
    assert rights.status == "unknown"
    assert rights.cleared is False
    assert "unlicensed.wav.license.json" in (rights.reason or "")
    assert "licences.json" in (rights.reason or "")


def test_per_file_manifest_clears_and_beats_the_folder_manifest(tmp_path: Path) -> None:
    clip = _clip(tmp_path, "loop.wav")
    (tmp_path / "licences.json").write_text(
        json.dumps({"loop.wav": {"license": "folder licence", "attribution": "folder"}})
    )
    clip.with_name("loop.wav.license.json").write_text(
        json.dumps(
            {
                "license": "commissioned buy-out (ads + derivatives)",
                "attribution": "Producer A",
                "evidence": "contracts/2026-03.pdf",
            }
        )
    )
    rights = rights_from_manifest(clip)
    assert rights.status == "cleared"
    assert rights.license == "commissioned buy-out (ads + derivatives)"
    assert rights.attribution == "Producer A"
    assert rights.evidence == "loop.wav.license.json"


@pytest.mark.parametrize("wrapped", [True, False])
def test_folder_manifest_flat_or_under_clips(tmp_path: Path, wrapped: bool) -> None:
    clip = _clip(tmp_path, "loop.wav")
    entries = {"loop.wav": {"license": "CC BY 4.0", "attribution": "B — https://fma.test/b"}}
    (tmp_path / "licences.json").write_text(
        json.dumps({"clips": entries} if wrapped else entries)
    )
    rights = rights_from_manifest(clip)
    assert rights.status == "cleared"
    assert rights.attribution == "B — https://fma.test/b"
    assert "licences.json entry" in rights.evidence


@pytest.mark.parametrize(
    ("entry", "reason_fragment"),
    [
        ({"title": "no licence field"}, "carries no 'license' field"),
        ({"license": "personal use", "permits_advertising": False}, "permits_advertising: false"),
        ({"license": "CC BY-NC 4.0"}, "NonCommercial or NoDerivatives"),
    ],
)
def test_manifest_entries_that_do_not_clear(
    tmp_path: Path, entry: dict[str, object], reason_fragment: str
) -> None:
    clip = _clip(tmp_path, "loop.wav")
    clip.with_name("loop.wav.license.json").write_text(json.dumps(entry))
    rights = rights_from_manifest(clip)
    assert rights.cleared is False
    assert reason_fragment in (rights.reason or "")


def test_urls_are_unknown_and_fma_licences_are_checked() -> None:
    assert resolve_rights("https://cdn.test/a.wav", "urls").status == "unknown"
    cleared = resolve_rights(
        "https://cdn.test/a.wav",
        "free_music_archive",
        declared_license="Attribution",
        declared_attribution="A — https://fma.test/a",
    )
    assert cleared.status == "cleared"
    denied = resolve_rights(
        "https://cdn.test/a.wav", "free_music_archive", declared_license="Attribution-NonCommercial"
    )
    assert denied.status == "denied"


def test_attestation_must_name_licence_authority_and_permission() -> None:
    with pytest.raises(ValueError, match="permits_advertising"):
        parse_attestation({"license": "mine"})
    attested = parse_attestation(
        {"license": "buy-out", "permits_advertising": True, "authority": "invoice 118"}
    )
    assert isinstance(attested, LicenseAttestation)
    attested_rights = resolve_rights("https://cdn.test/a.wav", "urls", attestation=attested)
    assert attested_rights.status == "cleared"


def test_refusal_names_what_is_missing() -> None:
    rights = resolve_rights("https://cdn.test/a.wav", "urls")
    error = RightsNotEstablished("https://cdn.test/a.wav", "urls", rights, "pass an attestation")
    details = error.details()
    assert details["code"] == "rights_not_established"
    assert details["status"] == "unknown"
    assert details["missing"] == "a licence that permits advertising and derivative use"
    assert details["remedy"] == "pass an attestation"


# --- the gate in process_clip ----------------------------------------------------------------


async def test_process_clip_refuses_a_clip_without_an_established_licence(
    mcp_client: Client, router: respx.Router, settings, store: Store
) -> None:
    routes = mock_snapplay(router, make_job_result())
    clip = _clip(settings.licensed_clips_dir)
    with pytest.raises(ToolError) as excinfo:
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(clip)})
    message = str(excinfo.value)
    assert "rights not established" in message
    assert "no licence is recorded for unlicensed.wav" in message
    assert "licences.json" in message and "license_attestation" in message
    assert routes["submit"].call_count == 0, "a clip with no licence must not cost a credit"
    assert store.list_items() == []


async def test_process_clip_refuses_a_url_and_accepts_an_explicit_attestation(
    mcp_client: Client, router: respx.Router, store: Store
) -> None:
    routes = mock_snapplay(router, make_job_result())
    router.get("https://cdn.test/beat.wav").mock(
        return_value=httpx.Response(200, content=make_wav_bytes(1.0))
    )
    args = {"clip_path_or_url": "https://cdn.test/beat.wav"}
    with pytest.raises(ToolError, match="rights not established"):
        await mcp_client.call_tool("process_clip", args)
    assert routes["submit"].call_count == 0

    data = (
        await mcp_client.call_tool(
            "process_clip",
            {
                **args,
                "license_attestation": {
                    "license": "buy-out contract 2026-03",
                    "permits_advertising": True,
                    "authority": "Producer A, invoice 118",
                    "attribution": "Producer A",
                },
            },
        )
    ).structured_content
    assert data["rights"]["status"] == "cleared"
    assert data["rights"]["evidence"] == "operator attestation (Producer A, invoice 118)"
    assert routes["submit"].call_count == 1
    item = store.require(data["content_item_id"])
    assert item.rights == {
        "status": "cleared",
        "license": "buy-out contract 2026-03",
        "attribution": "Producer A",
        "evidence": "operator attestation (Producer A, invoice 118)",
        "authority": "Producer A, invoice 118",
        "reason": None,
    }


async def test_process_clip_refuses_a_non_commercial_manifest_entry(
    mcp_client: Client, router: respx.Router, settings
) -> None:
    routes = mock_snapplay(router, make_job_result())
    clip = _clip(settings.licensed_clips_dir, "nc.wav")
    clip.with_name("nc.wav.license.json").write_text(json.dumps({"license": "CC BY-NC-SA 4.0"}))
    with pytest.raises(ToolError, match="NonCommercial or NoDerivatives"):
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(clip)})
    assert routes["submit"].call_count == 0


async def test_process_clip_records_the_licence_for_the_caption(
    mcp_client: Client, router: respx.Router, clip_file: Path, store: Store
) -> None:
    mock_snapplay(router, make_job_result())
    data = (
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(clip_file)})
    ).structured_content
    assert data["rights"]["license"] == "operator-licensed"
    assert data["rights"]["attribution"] == "in-house"
    assert store.require(data["content_item_id"]).rights["attribution"] == "in-house"


async def test_list_source_clips_reports_unknown_rights_instead_of_inventing_one(
    mcp_client: Client, settings
) -> None:
    _clip(settings.licensed_clips_dir)
    clips = (await mcp_client.call_tool("list_source_clips", {})).structured_content["clips"]
    assert [c["license"] for c in clips] == ["unknown"]
    assert clips[0]["rights"]["status"] == "unknown"


async def test_batch_skips_clips_without_a_licence(
    mcp_client: Client, router: respx.Router, settings, clip_file: Path
) -> None:
    mock_snapplay(router, make_job_result())
    _clip(settings.licensed_clips_dir)
    report = (await mcp_client.call_tool("run_daily_batch", {"count": 2})).structured_content
    assert [i["source_ref"] for i in report["items"]] == [str(clip_file.resolve())]
    assert any("have no established licence" in n for n in report["notes"])
    assert any("no licence is recorded for unlicensed.wav" in n for n in report["notes"])


async def test_api_key_is_never_needed_to_refuse(
    mcp_client: Client, router: respx.Router, settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate runs before the client is built, so an unlicensed clip fails on rights."""
    monkeypatch.delenv("SNAPPLAY_API_KEY")
    router.post(f"{SNAPPLAY_URL}/v1/jobs")
    clip = _clip(settings.licensed_clips_dir)
    with pytest.raises(ToolError, match="rights not established"):
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(clip)})
