"""render_video: props, FFmpeg fallback and a short Remotion smoke render."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from mcp_server import pipeline
from mcp_server.config import Settings
from mcp_server.render import (
    RenderError,
    _escape_drawtext,
    build_props,
    captions_from_script,
    captions_from_words,
    remotion_available,
    remotion_command,
    render_item,
)
from mcp_server.script import write_brief
from mcp_server.state import ContentItem, Store
from tests.conftest import make_wav_bytes

REMOTION_DIR = Path(__file__).resolve().parents[1] / "remotion"
HEADLESS_SHELL = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell"
WORDS = [
    {"word": "Sample", "start_seconds": 0.1, "end_seconds": 0.5},
    {"word": "to", "start_seconds": 0.5, "end_seconds": 0.6},
    {"word": "playable", "start_seconds": 0.6, "end_seconds": 1.1},
    {"word": "keys", "start_seconds": 1.1, "end_seconds": 1.4},
    {"word": "now", "start_seconds": 1.4, "end_seconds": 1.7},
]


def _item_with_assets(store: Store, settings: Settings, *, voice: bool = False) -> ContentItem:
    item = store.create_item("licensed_folder", "/clips/loop.wav")
    work = settings.growth_work_dir / item.id
    (work / "stems").mkdir(parents=True)
    stem = work / "stems" / "bass.wav"
    stem.write_bytes(make_wav_bytes(2.0))
    notes = work / "midi_notes.json"
    notes.write_text(
        json.dumps(
            [
                {
                    "start_seconds": i * 0.5,
                    "duration_seconds": 0.4,
                    "start_ticks": 0,
                    "duration_ticks": 0,
                    "pitch": 41 + (i % 4) * 3,
                    "velocity": 100,
                }
                for i in range(4)
            ]
        )
    )
    assets = {"chosen_stem_path": str(stem), "midi_notes_path": str(notes)}
    if voice:
        voice_path = work / "voiceover.wav"
        voice_path.write_bytes(make_wav_bytes(1.5, freq=440.0))
        words = work / "voiceover_words.json"
        words.write_text(json.dumps(WORDS))
        assets |= {"voiceover_path": str(voice_path), "voiceover_words_path": str(words)}
    brief = write_brief({"title": "Loop", "chosen_stem": "bass", "bpm": 120}, "speed")
    return store.update(item.id, chosen_stem="bass", assets=assets, script=brief.model_dump())


def test_captions_from_words_chunks_by_four() -> None:
    chunks = captions_from_words(WORDS)
    assert [c["text"] for c in chunks] == ["Sample to playable keys", "now"]
    assert chunks[0]["start"] == 0.1
    assert chunks[0]["end"] == 1.4
    assert [w["word"] for w in chunks[0]["words"]] == ["Sample", "to", "playable", "keys"]


def test_captions_from_script_uses_beats() -> None:
    brief = write_brief({}, "bass").model_dump()
    chunks = captions_from_script(brief)
    assert [(c["start"], c["end"]) for c in chunks] == [(0.0, 3.0), (3.0, 10.0), (10.0, 15.0)]
    assert chunks[-1]["text"] == "3 free credits"
    assert captions_from_script(None) == []


def test_drawtext_escaping() -> None:
    assert _escape_drawtext("it's 100%: a,b;[c]=d\nx") == "it\\'s 100\\%\\: a\\,b\\;\\[c\\]\\=d x"


def test_build_props_requires_stem(store: Store, tmp_path: Path) -> None:
    item = store.create_item("licensed_folder", "/clips/x.wav")
    with pytest.raises(RenderError, match="process_clip first"):
        build_props(
            item, public_dir=tmp_path, scene="plugin_ui", presenter="waveform", avatar_clip=None
        )


def test_build_props_stages_assets(store: Store, settings: Settings, tmp_path: Path) -> None:
    item = _item_with_assets(store, settings, voice=True)
    public = tmp_path / "public"
    props = build_props(
        item, public_dir=public, scene="daw", presenter="waveform", avatar_clip=None
    )
    assert props["audioSrc"] == "stem.wav"
    assert props["voiceoverSrc"] == "voiceover.wav"
    assert (public / "stem.wav").is_file()
    assert (public / "voiceover.wav").is_file()
    assert props["scene"] == "daw"
    assert props["cta"] == "3 free credits"
    assert len(props["midiNotes"]) == 4
    assert props["midiNotes"][0] == {"start": 0.0, "duration": 0.4, "pitch": 41, "velocity": 100}
    assert props["captions"][0]["words"][0]["word"] == "Sample"
    with pytest.raises(RenderError, match="requires avatar_clip"):
        build_props(item, public_dir=public, scene="daw", presenter="avatar_clip", avatar_clip=None)


def test_remotion_command_flags(settings: Settings, tmp_path: Path) -> None:
    settings = settings.model_copy(
        update={"remotion_browser_executable": "/usr/bin/chrome", "remotion_gl": "swiftshader"}
    )
    cmd = remotion_command(
        settings,
        props_path=tmp_path / "props.json",
        public_dir=tmp_path / "public",
        output=tmp_path / "out.mp4",
        frames=(0, 59),
    )
    assert cmd[:6] == [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        "SplitScreenShort",
        str(tmp_path / "out.mp4"),
    ]
    assert f"--props={tmp_path / 'props.json'}" in cmd
    assert f"--public-dir={tmp_path / 'public'}" in cmd
    assert "--browser-executable=/usr/bin/chrome" in cmd
    assert "--gl=swiftshader" in cmd
    assert "--frames=0-59" in cmd
    assert not remotion_available(settings)  # REMOTION_DIR points at a missing folder


def _probe(path: Path) -> dict[str, str]:
    if not shutil.which("ffprobe"):
        return {}
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,codec_name",
            "-of",
            "default=noprint_wrappers=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return dict(line.split("=", 1) for line in out.strip().splitlines())


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
@pytest.mark.parametrize("voice", [False, True])
async def test_ffmpeg_fallback_renders_when_remotion_is_missing(
    store: Store, settings: Settings, voice: bool
) -> None:
    item = _item_with_assets(store, settings, voice=voice)
    work = settings.growth_work_dir / item.id
    result = await render_item(item, settings, work_dir=work, duration_seconds=1.0)
    assert result.renderer == "ffmpeg"
    assert "Remotion not installed" in (result.note or "")
    video = Path(result.video_path)
    assert video.is_file() and video.stat().st_size > 1000
    assert json.loads(Path(result.props_path).read_text())["captions"]
    probe = _probe(video)
    if probe:
        assert (probe["width"], probe["height"], probe["codec_name"]) == ("1080", "1920", "h264")


@pytest.mark.skipif(
    shutil.which("npx") is None or not (REMOTION_DIR / "node_modules" / "remotion").is_dir(),
    reason="node/npx or the Remotion install is unavailable",
)
async def test_remotion_smoke_render_two_seconds(
    store: Store, env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REMOTION_DIR", str(REMOTION_DIR))
    browser = os.environ.get("REMOTION_BROWSER_EXECUTABLE") or (
        HEADLESS_SHELL if Path(HEADLESS_SHELL).is_file() else ""
    )
    if browser:
        monkeypatch.setenv("REMOTION_BROWSER_EXECUTABLE", browser)
    settings = Settings()
    assert remotion_available(settings)
    item = _item_with_assets(store, settings, voice=True)
    result = await pipeline.render_video(
        settings,
        store,
        item.id,
        scene="plugin_ui",
        presenter="waveform",
        avatar_clip=None,
        frames=(0, 59),
    )
    assert result.renderer == "remotion"
    video = Path(result.video_path)
    assert video.is_file() and video.stat().st_size > 10_000
    assert store.require(item.id).assets["renderer"] == "remotion"
    probe = _probe(video)
    if probe:
        assert (probe["width"], probe["height"]) == ("1080", "1920")
