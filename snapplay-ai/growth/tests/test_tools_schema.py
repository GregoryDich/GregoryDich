"""Tool listing and input-schema snapshot through the in-process FastMCP client."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastmcp import Client

SNAPSHOT = Path(__file__).parent / "snapshots" / "tools.json"
EXPECTED_TOOLS = [
    "list_source_clips",
    "process_clip",
    "write_script",
    "generate_voiceover",
    "render_video",
    "publish_video",
    "report_metrics",
    "run_daily_batch",
]


async def test_tool_names(mcp_client: Client) -> None:
    tools = await mcp_client.list_tools()
    assert [t.name for t in tools] == EXPECTED_TOOLS


async def test_rights_and_llm_statements_in_docstrings(mcp_client: Client) -> None:
    tools = {t.name: " ".join((t.description or "").split()) for t in await mcp_client.list_tools()}
    assert "must NOT be used for advertising" in tools["list_source_clips"]
    assert "no LLM is called" in tools["write_script"]
    assert "restricted" in tools["publish_video"]


async def test_input_schema_snapshot(mcp_client: Client) -> None:
    tools = await mcp_client.list_tools()
    current = {t.name: t.input_schema for t in tools}
    if os.environ.get("UPDATE_SNAPSHOTS") == "1" or not SNAPSHOT.exists():
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    expected = json.loads(SNAPSHOT.read_text())
    assert current == expected, "tool input schemas changed; rerun with UPDATE_SNAPSHOTS=1"


async def test_schema_details(mcp_client: Client) -> None:
    tools = {t.name: t.input_schema for t in await mcp_client.list_tools()}
    assert tools["list_source_clips"]["properties"]["source"]["enum"] == [
        "licensed_folder",
        "free_music_archive",
        "urls",
    ]
    assert tools["list_source_clips"]["properties"]["source"]["default"] == "licensed_folder"
    assert tools["write_script"]["properties"]["angle"]["enum"] == [
        "speed",
        "bass",
        "sample_flip",
        "tutorial",
    ]
    assert tools["render_video"]["properties"]["scene"]["default"] == "plugin_ui"
    assert tools["render_video"]["properties"]["presenter"]["default"] == "waveform"
    platforms = tools["publish_video"]["properties"]["platforms"]["items"]["enum"]
    assert platforms == ["instagram", "facebook", "tiktok", "youtube"]
    assert tools["run_daily_batch"]["properties"]["dry_run"]["default"] is True
    assert tools["run_daily_batch"]["properties"]["count"]["default"] == 3
    assert tools["process_clip"]["required"] == ["clip_path_or_url"]
    assert tools["report_metrics"]["required"] == ["since_iso"]
