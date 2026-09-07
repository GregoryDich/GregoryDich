"""Render a content item to a 1080x1920, 15 s, 30 fps mp4.

Primary path: ``npx remotion render`` of the ``SplitScreenShort`` composition with a props JSON
and a per-item ``--public-dir`` holding the audio. Fallback when Remotion is unavailable or
fails: FFmpeg composites a ``showwaves`` waveform over a dark canvas and burns the captions and
CTA in with ``drawtext``.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from .config import Settings
from .state import ContentItem

Scene = Literal["daw", "plugin_ui"]
Presenter = Literal["waveform", "avatar_clip"]
WIDTH, HEIGHT, FPS, DURATION_SECONDS = 1080, 1920, 30, 15.0
CTA_TEXT = "3 free credits"
CAPTION_WORDS_PER_CHUNK = 4
_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
)


class RenderError(RuntimeError):
    pass


class RenderResult(BaseModel):
    content_item_id: str
    video_path: str
    renderer: Literal["remotion", "ffmpeg"]
    props_path: str
    duration_seconds: float
    width: int = WIDTH
    height: int = HEIGHT
    fps: int = FPS
    note: str | None = None


def captions_from_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group word timings into short caption chunks the composition can highlight word by word."""
    chunks: list[dict[str, Any]] = []
    for i in range(0, len(words), CAPTION_WORDS_PER_CHUNK):
        group = words[i : i + CAPTION_WORDS_PER_CHUNK]
        chunks.append(
            {
                "text": " ".join(w["word"] for w in group),
                "start": float(group[0]["start_seconds"]),
                "end": float(group[-1]["end_seconds"]),
                "words": [
                    {
                        "word": w["word"],
                        "start": float(w["start_seconds"]),
                        "end": float(w["end_seconds"]),
                    }
                    for w in group
                ],
            }
        )
    return chunks


def captions_from_script(script: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Without a voiceover, show each beat's on-screen text for the beat's duration."""
    if not script:
        return []
    return [
        {
            "text": beat["on_screen_text"],
            "start": float(beat["start_seconds"]),
            "end": float(beat["end_seconds"]),
            "words": [],
        }
        for beat in script.get("beats", [])
    ]


def _stage(src: str, public_dir: Path, name: str) -> str:
    """Copy a local asset into the public dir; URLs are passed through untouched."""
    if src.startswith(("http://", "https://", "data:")):
        return src
    source = Path(src)
    if not source.is_file():
        raise RenderError(f"asset not found: {src}")
    dest = public_dir / f"{name}{source.suffix.lower() or '.bin'}"
    if dest.resolve() != source.resolve():
        shutil.copyfile(source, dest)
    return dest.name


def build_props(
    item: ContentItem,
    *,
    public_dir: Path,
    scene: Scene,
    presenter: Presenter,
    avatar_clip: str | None,
) -> dict[str, Any]:
    stem_path = item.assets.get("chosen_stem_path")
    if not stem_path:
        raise RenderError("content item has no chosen stem audio; run process_clip first")
    public_dir.mkdir(parents=True, exist_ok=True)
    notes_path = item.assets.get("midi_notes_path")
    midi_notes = json.loads(Path(notes_path).read_text()) if notes_path else []
    voice_path = item.assets.get("voiceover_path")
    words_path = item.assets.get("voiceover_words_path")
    words = json.loads(Path(words_path).read_text()) if words_path else []
    captions = captions_from_words(words) if words else captions_from_script(item.script)
    if presenter == "avatar_clip" and not avatar_clip:
        raise RenderError("presenter='avatar_clip' requires avatar_clip")
    return {
        "audioSrc": _stage(stem_path, public_dir, "stem"),
        "voiceoverSrc": _stage(voice_path, public_dir, "voiceover") if voice_path else None,
        "midiNotes": [
            {
                "start": n["start_seconds"],
                "duration": n["duration_seconds"],
                "pitch": n["pitch"],
                "velocity": n["velocity"],
            }
            for n in midi_notes
        ],
        "captions": captions,
        "scene": scene,
        "presenter": presenter,
        "avatarSrc": _stage(avatar_clip, public_dir, "avatar") if avatar_clip else None,
        "cta": CTA_TEXT,
        "title": "SnapPlay AI",
        "stemName": item.chosen_stem or "bass",
    }


def remotion_available(settings: Settings) -> bool:
    return bool(
        shutil.which("npx") and (settings.remotion_dir / "node_modules" / "remotion").is_dir()
    )


def remotion_command(
    settings: Settings,
    *,
    props_path: Path,
    public_dir: Path,
    output: Path,
    frames: tuple[int, int] | None,
) -> list[str]:
    cmd = [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        "SplitScreenShort",
        str(output),
        f"--props={props_path}",
        f"--public-dir={public_dir}",
        f"--concurrency={settings.remotion_concurrency}",
        "--log=error",
        "--overwrite",
    ]
    if settings.remotion_browser_executable:
        cmd.append(f"--browser-executable={settings.remotion_browser_executable}")
    if settings.remotion_gl:
        cmd.append(f"--gl={settings.remotion_gl}")
    if frames:
        cmd.append(f"--frames={frames[0]}-{frames[1]}")
    return cmd


def _run(cmd: list[str], cwd: Path | None, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )


async def render_with_remotion(
    settings: Settings,
    *,
    props_path: Path,
    public_dir: Path,
    output: Path,
    frames: tuple[int, int] | None = None,
    timeout: float = 1800.0,
) -> None:
    cmd = remotion_command(
        settings, props_path=props_path, public_dir=public_dir, output=output, frames=frames
    )
    try:
        proc = await asyncio.to_thread(_run, cmd, settings.remotion_dir, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"remotion render failed to run: {exc}") from exc
    if proc.returncode != 0 or not output.is_file():
        tail = (proc.stderr or proc.stdout or "")[-2000:]
        raise RenderError(f"remotion render exited with {proc.returncode}: {tail}")


def _escape_drawtext(text: str) -> str:
    out = []
    for ch in text:
        if ch in "\\':%,;[]=":
            out.append("\\" + ch)
        elif ch == "\n":
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def find_font(settings: Settings) -> str | None:
    if settings.ffmpeg_font_file:
        return settings.ffmpeg_font_file
    return next((f for f in _FONT_CANDIDATES if Path(f).is_file()), None)


def ffmpeg_command(
    settings: Settings,
    *,
    stem_path: Path,
    voiceover_path: Path | None,
    captions: list[dict[str, Any]],
    title: str,
    output: Path,
    duration_seconds: float,
) -> list[str]:
    font = find_font(settings)
    font_arg = f":fontfile={font}" if font else ""

    def text(value: str, size: int, y: str, color: str, enable: str | None = None) -> str:
        parts = [
            f"drawtext=text='{_escape_drawtext(value)}'",
            f"fontsize={size}",
            f"fontcolor={color}",
            "x=(w-text_w)/2",
            f"y={y}",
            "box=1",
            "boxcolor=0x05070dAA",
            "boxborderw=24",
        ]
        if enable:
            parts.append(f"enable='{enable}'")
        return ":".join(parts) + font_arg

    overlays = [text(title, 72, "120", "white")]
    for c in captions:
        overlays.append(
            text(c["text"], 60, "h-420", "white", f"between(t\\,{c['start']:.3f}\\,{c['end']:.3f})")
        )
    cta_from = max(0.0, duration_seconds - 3.0)
    overlays.append(text(CTA_TEXT, 84, "h-220", "0xff5c8a", f"gte(t\\,{cta_from:.3f})"))

    cmd = [settings.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-i", str(stem_path)]
    if voiceover_path:
        cmd += ["-i", str(voiceover_path)]
    canvas_index = 2 if voiceover_path else 1
    cmd += [
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x0b0f19:s={WIDTH}x{HEIGHT}:r={FPS}:d={duration_seconds:.3f}",
    ]
    wave = (
        f"[0:a]showwaves=s={WIDTH}x600:mode=cline:colors=0x7c5cff|0xa892ff:rate={FPS}[wave];"
        f"[{canvas_index}:v][wave]overlay=0:1060:shortest=1[base];"
    )
    if voiceover_path:
        audio = "[0:a]volume=0.55[a0];[a0][1:a]amix=inputs=2:duration=first:normalize=0[aout];"
        audio_map = "[aout]"
    else:
        audio = ""
        audio_map = "0:a"
    graph = wave + audio + "[base]" + ",".join(overlays) + "[v]"
    cmd += [
        "-filter_complex",
        graph,
        "-map",
        "[v]",
        "-map",
        audio_map,
        "-t",
        f"{duration_seconds:.3f}",
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(output),
    ]
    return cmd


async def render_with_ffmpeg(
    settings: Settings,
    *,
    stem_path: Path,
    voiceover_path: Path | None,
    captions: list[dict[str, Any]],
    title: str,
    output: Path,
    duration_seconds: float = DURATION_SECONDS,
    timeout: float = 900.0,
) -> None:
    if not shutil.which(settings.ffmpeg_bin):
        raise RenderError(f"ffmpeg binary not found: {settings.ffmpeg_bin}")
    cmd = ffmpeg_command(
        settings,
        stem_path=stem_path,
        voiceover_path=voiceover_path,
        captions=captions,
        title=title,
        output=output,
        duration_seconds=duration_seconds,
    )
    try:
        proc = await asyncio.to_thread(_run, cmd, None, timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"ffmpeg failed to run: {exc}") from exc
    if proc.returncode != 0 or not output.is_file():
        raise RenderError(f"ffmpeg exited with {proc.returncode}: {(proc.stderr or '')[-2000:]}")


async def render_item(
    item: ContentItem,
    settings: Settings,
    *,
    work_dir: Path,
    scene: Scene = "plugin_ui",
    presenter: Presenter = "waveform",
    avatar_clip: str | None = None,
    frames: tuple[int, int] | None = None,
    duration_seconds: float = DURATION_SECONDS,
) -> RenderResult:
    """Write props, render with Remotion, fall back to FFmpeg; returns the mp4 path."""
    public_dir = work_dir / "public"
    props = build_props(
        item, public_dir=public_dir, scene=scene, presenter=presenter, avatar_clip=avatar_clip
    )
    props_path = work_dir / "props.json"
    props_path.write_text(json.dumps(props, indent=2))
    output = work_dir / "short.mp4"

    remotion_error: str | None = None
    if remotion_available(settings):
        try:
            await render_with_remotion(
                settings, props_path=props_path, public_dir=public_dir, output=output, frames=frames
            )
            return RenderResult(
                content_item_id=item.id,
                video_path=str(output),
                renderer="remotion",
                props_path=str(props_path),
                duration_seconds=duration_seconds,
            )
        except RenderError as exc:
            remotion_error = str(exc)
    else:
        remotion_error = (
            "Remotion not installed (npx or REMOTION_DIR/node_modules/remotion missing)"
        )

    voice = props["voiceoverSrc"]
    await render_with_ffmpeg(
        settings,
        stem_path=public_dir / props["audioSrc"],
        voiceover_path=(public_dir / voice) if voice else None,
        captions=props["captions"],
        title=props["title"],
        output=output,
        duration_seconds=duration_seconds,
    )
    return RenderResult(
        content_item_id=item.id,
        video_path=str(output),
        renderer="ffmpeg",
        props_path=str(props_path),
        duration_seconds=duration_seconds,
        note=f"FFmpeg fallback used: {remotion_error}",
    )
