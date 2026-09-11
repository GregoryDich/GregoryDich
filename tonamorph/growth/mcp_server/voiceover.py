"""ElevenLabs v1 text-to-speech with character timestamps, reduced to word timings."""

from __future__ import annotations

import base64
from pathlib import Path

import httpx
from pydantic import BaseModel


class WordTiming(BaseModel):
    word: str
    start_seconds: float
    end_seconds: float


class VoiceoverResult(BaseModel):
    audio_path: str
    voice_id: str
    duration_seconds: float
    words: list[WordTiming]


class ElevenLabsError(RuntimeError):
    pass


def words_from_alignment(
    characters: list[str], starts: list[float], ends: list[float]
) -> list[WordTiming]:
    """Group per-character timings into words split on whitespace."""
    words: list[WordTiming] = []
    current: list[str] = []
    start = 0.0
    end = 0.0
    for ch, s, e in zip(characters, starts, ends, strict=False):
        if ch.isspace():
            if current:
                words.append(
                    WordTiming(word="".join(current), start_seconds=start, end_seconds=end)
                )
                current = []
            continue
        if not current:
            start = float(s)
        current.append(ch)
        end = float(e)
    if current:
        words.append(WordTiming(word="".join(current), start_seconds=start, end_seconds=end))
    return words


async def synthesize(
    *,
    text: str,
    api_url: str,
    api_key: str,
    voice_id: str,
    model_id: str,
    dest: Path,
    http: httpx.AsyncClient,
) -> VoiceoverResult:
    """``POST /v1/text-to-speech/{voice_id}/with-timestamps`` → mp3 file + word timings."""
    url = f"{api_url.rstrip('/')}/v1/text-to-speech/{voice_id}/with-timestamps"
    response = await http.post(
        url,
        headers={"xi-api-key": api_key, "Accept": "application/json"},
        params={"output_format": "mp3_44100_128"},
        json={"text": text, "model_id": model_id},
    )
    if response.status_code >= 400:
        raise ElevenLabsError(f"ElevenLabs returned {response.status_code}")
    body = response.json()
    audio = base64.b64decode(body["audio_base64"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(audio)
    alignment = body.get("alignment") or body.get("normalized_alignment") or {}
    words = words_from_alignment(
        alignment.get("characters", []),
        alignment.get("character_start_times_seconds", []),
        alignment.get("character_end_times_seconds", []),
    )
    duration = words[-1].end_seconds if words else 0.0
    return VoiceoverResult(
        audio_path=str(dest), voice_id=voice_id, duration_seconds=duration, words=words
    )
