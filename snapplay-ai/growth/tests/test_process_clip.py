"""process_clip through the MCP client: submit → SSE → downloads → stem choice → idempotency."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_server.state import Store
from tests.conftest import JOB_ID, make_job_result, make_wav_bytes, mock_snapplay


async def test_process_clip_end_to_end(
    mcp_client: Client, router: respx.Router, clip_file: Path, store: Store, settings
) -> None:
    routes = mock_snapplay(router, make_job_result())
    result = await mcp_client.call_tool(
        "process_clip",
        {"clip_path_or_url": str(clip_file), "options": {"stems": ["bass", "other"]}},
    )
    data = result.structured_content
    assert data["job_id"] == JOB_ID
    assert data["chosen_stem"] == "bass"
    assert data["reused"] is False
    assert data["source"] == "licensed_folder"
    assert len(data["midi_notes"]) == 60
    assert data["midi_notes"][0]["pitch"] == 41
    assert data["analysis"]["key"]["root"] == "F"
    assert data["stem_scores"][0]["name"] == "bass"
    assert Path(data["chosen_stem_path"]).read_bytes() == make_wav_bytes()
    assert Path(data["midi_path"]).stat().st_size > 0
    assert routes["submit"].call_count == 1
    assert routes["events"].call_count == 1
    assert routes["poll"].call_count == 0
    for name in ("bass", "drums", "other", "vocals"):
        assert routes[f"stem:{name}"].call_count == 1

    item = store.require(data["content_item_id"])
    assert item.job_id == JOB_ID
    assert item.chosen_stem == "bass"
    assert set(item.assets["stems"]) == {"bass", "drums", "other", "vocals"}
    assert Path(item.assets["job_result_path"]).is_file()
    assert (
        Path(item.assets["chosen_stem_path"]).parent == settings.growth_work_dir / item.id / "stems"
    )


async def test_process_clip_is_idempotent_per_source(
    mcp_client: Client, router: respx.Router, clip_file: Path
) -> None:
    routes = mock_snapplay(router, make_job_result())
    first = (
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(clip_file)})
    ).structured_content
    second = (
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(clip_file)})
    ).structured_content
    assert second["content_item_id"] == first["content_item_id"]
    assert second["reused"] is True
    assert routes["submit"].call_count == 1

    forced = (
        await mcp_client.call_tool(
            "process_clip", {"clip_path_or_url": str(clip_file), "options": {"force": True}}
        )
    ).structured_content
    assert forced["content_item_id"] != first["content_item_id"]
    assert routes["submit"].call_count == 2


async def test_process_clip_from_url_uses_polling_fallback(
    mcp_client: Client, router: respx.Router
) -> None:
    routes = mock_snapplay(router, make_job_result(), sse=False)
    router.get("https://cdn.test/beat.wav").mock(
        return_value=httpx.Response(200, content=make_wav_bytes(1.0))
    )
    data = (
        await mcp_client.call_tool(
            "process_clip",
            {
                "clip_path_or_url": "https://cdn.test/beat.wav",
                "options": {"source": "free_music_archive"},
            },
        )
    ).structured_content
    assert data["source"] == "free_music_archive"
    assert data["source_ref"] == "https://cdn.test/beat.wav"
    assert routes["poll"].call_count == 1


async def test_process_clip_rejects_oversized_upload(
    mcp_client: Client, router: respx.Router, settings
) -> None:
    big = settings.licensed_clips_dir / "big.wav"
    big.write_bytes(b"\0" * (10 * 1024 * 1024 + 1))
    with pytest.raises(ToolError, match="at most 10 MB"):
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(big)})


async def test_process_clip_requires_api_key(
    mcp_client: Client, router: respx.Router, clip_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SNAPPLAY_API_KEY")
    with pytest.raises(ToolError, match="SNAPPLAY_API_KEY"):
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(clip_file)})


async def test_process_clip_surfaces_contract_errors(
    mcp_client: Client, router: respx.Router, clip_file: Path
) -> None:
    router.post(f"{router.bases or ''}https://api.snapplay.test/v1/jobs").mock(
        return_value=httpx.Response(
            402, json={"error": {"code": "insufficient_credits", "message": "You have 0 credits."}}
        )
    )
    with pytest.raises(ToolError, match="insufficient_credits"):
        await mcp_client.call_tool("process_clip", {"clip_path_or_url": str(clip_file)})
