"""ElevenLabs voiceover: alignment → word timings, file output, item attachment."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
import respx
from fastmcp import Client

from mcp_server.state import Store
from mcp_server.voiceover import words_from_alignment
from tests.conftest import ELEVENLABS_URL


def _alignment(text: str) -> dict[str, list]:
    chars = list(text)
    starts = [round(i * 0.1, 2) for i in range(len(chars))]
    ends = [round(s + 0.1, 2) for s in starts]
    return {
        "characters": chars,
        "character_start_times_seconds": starts,
        "character_end_times_seconds": ends,
    }


def test_words_from_alignment_groups_on_whitespace() -> None:
    a = _alignment("Hi  there")
    words = words_from_alignment(
        a["characters"], a["character_start_times_seconds"], a["character_end_times_seconds"]
    )
    assert [w.word for w in words] == ["Hi", "there"]
    assert words[0].start_seconds == 0.0
    assert words[0].end_seconds == 0.2
    assert words[1].start_seconds == 0.4
    assert words[1].end_seconds == 0.9


def mock_elevenlabs(router: respx.Router, voice_id: str, text: str) -> respx.Route:
    return router.post(f"{ELEVENLABS_URL}/v1/text-to-speech/{voice_id}/with-timestamps").mock(
        return_value=httpx.Response(
            200,
            json={
                "audio_base64": base64.b64encode(b"ID3fake-mp3-bytes").decode(),
                "alignment": _alignment(text),
            },
        )
    )


async def test_generate_voiceover_tool_attaches_to_item(
    mcp_client: Client, router: respx.Router, store: Store, settings
) -> None:
    text = "Sample to keys"
    route = mock_elevenlabs(router, "21m00Tcm4TlvDq8ikWAM", text)
    item = store.create_item("licensed_folder", "/clips/a.wav")
    result = await mcp_client.call_tool(
        "generate_voiceover", {"text": text, "content_item_id": item.id}
    )
    data = result.structured_content
    assert [w["word"] for w in data["words"]] == ["Sample", "to", "keys"]
    assert data["duration_seconds"] == 1.4
    assert Path(data["audio_path"]).read_bytes() == b"ID3fake-mp3-bytes"
    request = route.calls.last.request
    assert request.headers["xi-api-key"] == "el-test"
    assert request.url.params["output_format"] == "mp3_44100_128"
    assert json.loads(request.content)["text"] == text
    assets = store.require(item.id).assets
    assert assets["voiceover_path"] == data["audio_path"]
    words = json.loads(Path(assets["voiceover_words_path"]).read_text())
    assert words[0]["word"] == "Sample"


async def test_generate_voiceover_custom_voice_without_item(
    mcp_client: Client, router: respx.Router, settings
) -> None:
    route = mock_elevenlabs(router, "voice-x", "Hello")
    result = await mcp_client.call_tool(
        "generate_voiceover", {"text": "Hello", "voice_id": "voice-x"}
    )
    assert route.called
    assert result.structured_content["voice_id"] == "voice-x"
    assert (
        Path(result.structured_content["audio_path"]).parent
        == settings.growth_work_dir / "voiceovers"
    )
