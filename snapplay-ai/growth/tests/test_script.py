"""write_script: deterministic 15 s briefs, no LLM, CTA present."""

from __future__ import annotations

import pytest
from fastmcp import Client

from mcp_server.script import ANGLES, ScriptBrief, brief_voice_text, write_brief


@pytest.mark.parametrize("angle", ANGLES)
def test_brief_structure(angle: str) -> None:
    brief = write_brief(
        {
            "title": "Night Loop",
            "chosen_stem": "bass",
            "bpm": 124.0,
            "key": {"root": "F", "mode": "minor"},
        },
        angle,  # type: ignore[arg-type]
    )
    assert brief.duration_seconds == 15
    assert brief.hook
    assert len(brief.beats) == 3
    assert brief.beats[0].start_seconds == 0
    assert brief.beats[-1].end_seconds == 15
    for prev, nxt in zip(brief.beats, brief.beats[1:], strict=False):
        assert prev.end_seconds == nxt.start_seconds
    assert brief.cta == "3 free credits"
    assert "3 free credits" in brief.cta_line
    assert brief.on_screen_text == [b.on_screen_text for b in brief.beats]
    assert "124 BPM" in brief_voice_text(brief)
    assert "F minor" in brief_voice_text(brief)
    assert brief.key == "F minor"


def test_brief_tolerates_missing_metadata() -> None:
    brief = write_brief({}, "speed")
    assert brief.stem == "bass"
    assert brief.bpm is None
    assert "any tempo" in brief_voice_text(brief)


def test_brief_reads_analysis_block() -> None:
    brief = write_brief(
        {"analysis": {"bpm": 90.4, "key": {"root": "A", "mode": "major"}}, "chosen_stem": "other"},
        "tutorial",
    )
    assert brief.bpm == 90.4
    assert brief.key == "A major"
    assert "synth" in brief_voice_text(brief)


async def test_write_script_tool_stores_brief_on_item(mcp_client: Client, store) -> None:
    item = store.create_item("licensed_folder", "/clips/x.wav")
    result = await mcp_client.call_tool(
        "write_script",
        {"clip_metadata": {"title": "x", "content_item_id": item.id}, "angle": "sample_flip"},
    )
    brief = ScriptBrief.model_validate(result.structured_content)
    assert brief.angle == "sample_flip"
    assert store.require(item.id).script["hook"] == brief.hook
