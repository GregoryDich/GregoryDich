"""Deterministic 15-second briefs for the calling model to voice.

This module never calls an LLM: it fills angle templates from clip metadata so the MCP client
(the model) can voice, tweak or translate the brief before generating the voiceover.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Angle = Literal["speed", "bass", "sample_flip", "tutorial"]
ANGLES: tuple[Angle, ...] = ("speed", "bass", "sample_flip", "tutorial")
CTA_TEXT = "3 free credits"
DURATION_SECONDS = 15.0


class Beat(BaseModel):
    start_seconds: float
    end_seconds: float
    label: str
    voice: str = Field(description="What the presenter says during this beat")
    on_screen_text: str
    visual: str = Field(description="What the composition shows during this beat")


class ScriptBrief(BaseModel):
    angle: Angle
    duration_seconds: float = DURATION_SECONDS
    hook: str
    beats: list[Beat]
    on_screen_text: list[str]
    cta: str = CTA_TEXT
    cta_line: str
    hashtags: list[str]
    voice_direction: str
    stem: str
    bpm: float | None = None
    key: str | None = None


class ClipMetadata(BaseModel):
    title: str = "this clip"
    stem: str = "bass"
    bpm: float | None = None
    key: str | None = None
    note_count: int | None = None
    source: str | None = None
    attribution: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClipMetadata:
        key = data.get("key")
        if isinstance(key, dict):
            key = f"{key.get('root', '')} {key.get('mode', '')}".strip() or None
        analysis = data.get("analysis") if isinstance(data.get("analysis"), dict) else {}
        return cls(
            title=str(data.get("title") or "this clip"),
            stem=str(data.get("chosen_stem") or data.get("stem") or "bass"),
            bpm=_as_float(data.get("bpm", analysis.get("bpm"))),
            key=key if isinstance(key, str) else _key_from_analysis(analysis),
            note_count=_as_int(data.get("note_count")),
            source=data.get("source"),
            attribution=data.get("attribution"),
        )


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _key_from_analysis(analysis: dict[str, Any]) -> str | None:
    key = analysis.get("key")
    if isinstance(key, dict):
        return f"{key.get('root', '')} {key.get('mode', '')}".strip() or None
    return None


_STEM_LABEL = {"bass": "bassline", "other": "synth", "vocals": "vocal", "drums": "drum hits"}


def _tempo_phrase(meta: ClipMetadata) -> str:
    parts = []
    if meta.bpm:
        parts.append(f"{round(meta.bpm)} BPM")
    if meta.key:
        parts.append(meta.key)
    return ", ".join(parts) if parts else "any tempo, any key"


def _template(angle: Angle, meta: ClipMetadata) -> tuple[str, list[Beat], str, list[str]]:
    stem_label = _STEM_LABEL.get(meta.stem, meta.stem)
    tempo = _tempo_phrase(meta)
    if angle == "speed":
        hook = "Sample to playable keys in two seconds. Watch."
        beats = [
            Beat(
                start_seconds=0,
                end_seconds=3,
                label="hook",
                voice=hook,
                on_screen_text="2 seconds. Any sample.",
                visual="Clip lands in the drop zone; timer starts",
            ),
            Beat(
                start_seconds=3,
                end_seconds=10,
                label="proof",
                voice=(
                    f"Tonamorph pulls the {stem_label} out, transcribes it, "
                    f"and it is already on the keys. {tempo}."
                ),
                on_screen_text=f"{stem_label} → MIDI → keys",
                visual="Stems separate, piano roll lights up with the transcription",
            ),
            Beat(
                start_seconds=10,
                end_seconds=15,
                label="cta",
                voice="Free plugin, three free credits, no card. Link in bio.",
                on_screen_text=CTA_TEXT,
                visual="Brand outro with CTA",
            ),
        ]
        direction = "Fast, confident, slightly amazed. No filler words."
        tags = ["#producer", "#musicproduction", "#sampling", "#vst", "#tonamorph"]
    elif angle == "bass":
        hook = "Stop re-programming basslines by ear."
        beats = [
            Beat(
                start_seconds=0,
                end_seconds=3,
                label="hook",
                voice=hook,
                on_screen_text="That bassline? Yours now.",
                visual="Waveform of the clip, bass region highlighted",
            ),
            Beat(
                start_seconds=3,
                end_seconds=10,
                label="proof",
                voice=(
                    "Drop the clip, Tonamorph isolates the bass and hands you the MIDI, "
                    f"root detected, ready to transpose. {tempo}."
                ),
                on_screen_text="Bass stem → MIDI notes → play it",
                visual="Bass stem solo, piano roll follows the notes, key lights",
            ),
            Beat(
                start_seconds=10,
                end_seconds=15,
                label="cta",
                voice="Try it on your own loop. Three free credits, no card.",
                on_screen_text=CTA_TEXT,
                visual="Brand outro with CTA",
            ),
        ]
        direction = "Calm producer-to-producer tone, a little dry."
        tags = ["#bassline", "#beatmaking", "#producerlife", "#midi", "#tonamorph"]
    elif angle == "sample_flip":
        hook = "Flip a sample into a new key without pitching the whole thing."
        beats = [
            Beat(
                start_seconds=0,
                end_seconds=3,
                label="hook",
                voice=hook,
                on_screen_text="Same sample. New key.",
                visual="Clip plays once at original pitch",
            ),
            Beat(
                start_seconds=3,
                end_seconds=10,
                label="proof",
                voice=(
                    f"The {stem_label} becomes MIDI, so you play the flip on the keys "
                    f"instead of chopping it. Scale-snap keeps every note in key. {tempo}."
                ),
                on_screen_text="Play the flip on the keys",
                visual="Piano roll with the transcribed notes, then a re-played phrase",
            ),
            Beat(
                start_seconds=10,
                end_seconds=15,
                label="cta",
                voice="Start with three free credits. Link in bio.",
                on_screen_text=CTA_TEXT,
                visual="Brand outro with CTA",
            ),
        ]
        direction = "Playful and quick, like showing a friend a trick."
        tags = ["#sampleflip", "#flip", "#beats", "#producer", "#tonamorph"]
    else:
        hook = "Three steps from audio to a playable instrument."
        beats = [
            Beat(
                start_seconds=0,
                end_seconds=3,
                label="step 1",
                voice=f"{hook} One: drag the clip in.",
                on_screen_text="1. Drop the clip",
                visual="Drop zone in the plugin UI",
            ),
            Beat(
                start_seconds=3,
                end_seconds=10,
                label="step 2",
                voice=(
                    f"Two: pick the stem. We take the {stem_label}. "
                    f"Tonamorph transcribes it to MIDI and maps it to the keys. {tempo}."
                ),
                on_screen_text="2. Pick a stem",
                visual="Stem list appears, chosen stem highlighted, piano roll fills",
            ),
            Beat(
                start_seconds=10,
                end_seconds=15,
                label="step 3 + cta",
                voice="Three: play it. It is free to try with three free credits.",
                on_screen_text=f"3. Play it — {CTA_TEXT}",
                visual="Keys light with the notes, brand outro with CTA",
            ),
        ]
        direction = "Clear and instructional, even pace, no hype."
        tags = ["#tutorial", "#musicproduction", "#vst", "#daw", "#tonamorph"]
    return hook, beats, direction, tags


def write_brief(metadata: dict[str, Any], angle: Angle) -> ScriptBrief:
    meta = ClipMetadata.from_dict(metadata)
    hook, beats, direction, tags = _template(angle, meta)
    return ScriptBrief(
        angle=angle,
        hook=hook,
        beats=beats,
        on_screen_text=[b.on_screen_text for b in beats],
        cta_line=f"Try Tonamorph free — {CTA_TEXT}, no card required.",
        hashtags=tags,
        voice_direction=direction,
        stem=meta.stem,
        bpm=meta.bpm,
        key=meta.key,
    )


def brief_voice_text(brief: ScriptBrief) -> str:
    """The plain narration a TTS voice reads, beat by beat."""
    return " ".join(b.voice.strip() for b in brief.beats)
