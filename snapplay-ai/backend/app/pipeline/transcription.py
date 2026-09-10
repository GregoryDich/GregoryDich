"""Basic Pitch note transcription through onnxruntime (contract §7, 400 ms budget).

The ICASSP 2022 model that ships with ``basic-pitch`` is run in an
``onnxruntime.InferenceSession`` created with the TensorRT, CUDA and CPU execution
providers (in that order, whichever are installed); inference itself goes through
``basic_pitch.inference.predict`` so windowing and note segmentation match the
reference implementation. Notes are then cleaned up (minimum 40 ms, pitch 21–108,
velocity from the note amplitude); tick positions at PPQ 480 are added later from the
detected tempo by :mod:`app.pipeline.midi_export`.

Everything optional is imported inside functions so the module imports on the API
host; a missing extra raises :class:`ImportError` with an install hint.
"""

from __future__ import annotations

import logging
import math
import os
import tempfile
import threading
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import soundfile as sf

from app.pipeline.analysis import PITCH_RANGE_HZ, Note

log = logging.getLogger("snapplay.pipeline.transcription")

PROVIDERS: tuple[str, ...] = (
    "TensorrtExecutionProvider",
    "CUDAExecutionProvider",
    "CPUExecutionProvider",
)
MIN_NOTE_SECONDS = 0.04
PITCH_MIN = 21
PITCH_MAX = 108
ONSET_THRESHOLD = 0.5
FRAME_THRESHOLD = 0.3
SHM_DIR = Path("/dev/shm")
INSTALL_HINT = (
    "install the GPU extras: pip install -r requirements-gpu.txt && "
    "pip install --no-deps basic-pitch==0.4.0 (basic-pitch, onnxruntime-gpu)"
)


@dataclass(frozen=True)
class LoadedTranscriber:
    model: Any
    """Passed to ``basic_pitch.inference.predict`` as ``model_or_model_path``."""
    predict: Callable[..., Any]
    providers: tuple[str, ...]


_loaded: LoadedTranscriber | None = None
_lock = threading.Lock()


def is_available() -> bool:
    return find_spec("basic_pitch") is not None and find_spec("onnxruntime") is not None


def require_extras() -> None:
    """Raise :class:`ImportError` with an install hint when the extras are missing."""
    if not is_available():
        raise ImportError(
            f"Basic Pitch transcription needs basic-pitch and onnxruntime; {INSTALL_HINT}"
        )


def _import_extras() -> tuple[Any, Any, Any]:
    try:
        import basic_pitch
        import onnxruntime as ort
        from basic_pitch import inference
    except ImportError as exc:
        raise ImportError(
            f"Basic Pitch transcription needs basic-pitch and onnxruntime; {INSTALL_HINT}"
        ) from exc
    return ort, _onnx_model_path(basic_pitch), inference


def _onnx_model_path(basic_pitch: Any) -> str:
    """The bundled ONNX checkpoint. ``ICASSP_2022_MODEL_PATH`` points at whichever backend
    basic-pitch found at import time (TensorFlow or TFLite when installed), so the ONNX
    file is selected explicitly and the pipeline does not depend on what else the image
    happens to contain."""
    build = getattr(basic_pitch, "build_icassp_2022_model_path", None)
    suffix = getattr(getattr(basic_pitch, "FilenameSuffix", None), "onnx", None)
    if build is not None and suffix is not None:
        return str(build(suffix))
    return str(basic_pitch.ICASSP_2022_MODEL_PATH)


def _session(ort: Any, path: str) -> Any:
    """A session with the best available providers: the list is shortened from the front
    until one loads, so a TensorRT runtime that is compiled in but not installed still
    leaves CUDA in play instead of dropping straight to the CPU."""
    available = set(ort.get_available_providers())
    wanted = [p for p in PROVIDERS if p in available] or ["CPUExecutionProvider"]
    while len(wanted) > 1:
        try:
            return ort.InferenceSession(path, providers=wanted)
        except Exception as exc:
            log.warning("onnxruntime provider %s failed (%s); trying without it", wanted[0], exc)
            wanted = wanted[1:]
    return ort.InferenceSession(path, providers=wanted)


def load_model() -> LoadedTranscriber:
    """Load (once) the Basic Pitch model with GPU execution providers when possible."""
    global _loaded
    if _loaded is not None:
        return _loaded
    with _lock:
        if _loaded is not None:
            return _loaded
        ort, default_path, inference = _import_extras()
        path = os.environ.get("SNAPPLAY_BASIC_PITCH_MODEL", "").strip() or str(default_path)
        started = perf_counter()
        model_cls = getattr(inference, "Model", None)
        providers: tuple[str, ...]
        if model_cls is None:
            model: Any = path
            providers = ("basic-pitch",)
        else:
            model = model_cls(path)
            session = getattr(model, "model", None)
            if path.endswith(".onnx") and isinstance(session, ort.InferenceSession):
                # Basic Pitch builds a CPU-only session; swap in one with GPU providers
                # so its own predict() runs the same graph on the accelerator.
                model.model = _session(ort, path)
                providers = tuple(model.model.get_providers())
            else:
                providers = (f"basic-pitch:{getattr(model, 'model_type', 'native')}",)
        _loaded = LoadedTranscriber(model=model, predict=inference.predict, providers=providers)
        log.info(
            "basic pitch loaded from %s in %.2fs (providers=%s)",
            path,
            perf_counter() - started,
            ",".join(providers),
        )
        return _loaded


@contextmanager
def _temp_wav(mono: np.ndarray, sample_rate: int) -> Iterator[str]:
    directory = str(SHM_DIR) if SHM_DIR.is_dir() and os.access(SHM_DIR, os.W_OK) else None
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="snapplay-", dir=directory)
    os.close(fd)
    try:
        sf.write(path, np.clip(mono, -1.0, 1.0), sample_rate, format="WAV", subtype="FLOAT")
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def postprocess_notes(events: Iterable[Any]) -> list[Note]:
    """Basic Pitch ``(start_s, end_s, pitch, amplitude, bends)`` events → clean notes."""
    notes: list[Note] = []
    for event in events:
        start, end, pitch, amplitude = float(event[0]), float(event[1]), int(event[2]), event[3]
        duration = end - start
        if not math.isfinite(duration) or duration < MIN_NOTE_SECONDS or start < 0:
            continue
        amplitude = float(np.clip(float(amplitude), 0.0, 1.0))
        velocity = int(np.clip(round(20 + 107 * math.sqrt(amplitude)), 1, 127))
        notes.append(
            Note(
                start_seconds=round(start, 3),
                duration_seconds=round(duration, 3),
                pitch=int(np.clip(pitch, PITCH_MIN, PITCH_MAX)),
                velocity=velocity,
            )
        )
    notes.sort(key=lambda n: (n.start_seconds, n.pitch))
    return notes


def transcribe_mono(
    mono: np.ndarray, sample_rate: int, name: str = "other"
) -> list[Note]:
    """Notes for one stem; ``name`` selects the pitch range from :data:`PITCH_RANGE_HZ`."""
    loaded = load_model()
    fmin, fmax = PITCH_RANGE_HZ.get(name, (None, None))
    with _temp_wav(np.asarray(mono, dtype=np.float32), sample_rate) as path:
        _, _, events = loaded.predict(
            path,
            loaded.model,
            onset_threshold=ONSET_THRESHOLD,
            frame_threshold=FRAME_THRESHOLD,
            minimum_note_length=MIN_NOTE_SECONDS * 1000.0,
            minimum_frequency=fmin,
            maximum_frequency=fmax,
            melodia_trick=True,
        )
    return postprocess_notes(events)


def transcribe(stems: dict[str, np.ndarray], sample_rate: int) -> dict[str, list[Note]]:
    """``{stem: notes}`` for every ``{stem: (channels × samples)}`` given."""
    result: dict[str, list[Note]] = {}
    for name, audio in stems.items():
        mono = audio.mean(axis=0) if audio.ndim == 2 else audio
        started = perf_counter()
        result[name] = transcribe_mono(mono, sample_rate, name)
        log.debug(
            "transcribed %s: %d notes in %.0f ms",
            name,
            len(result[name]),
            1000.0 * (perf_counter() - started),
        )
    return result


def warm_up(seconds: float = 1.0, sample_rate: int = 44100) -> LoadedTranscriber:
    """Load the model and run it once (TensorRT builds its engine on the first run)."""
    loaded = load_model()
    started = perf_counter()
    transcribe_mono(np.zeros(int(seconds * sample_rate), dtype=np.float32), sample_rate)
    log.info("basic pitch warm-up took %.2fs", perf_counter() - started)
    return loaded


__all__ = [
    "FRAME_THRESHOLD",
    "INSTALL_HINT",
    "MIN_NOTE_SECONDS",
    "ONSET_THRESHOLD",
    "PITCH_MAX",
    "PITCH_MIN",
    "PROVIDERS",
    "LoadedTranscriber",
    "is_available",
    "load_model",
    "postprocess_notes",
    "require_extras",
    "transcribe",
    "transcribe_mono",
    "warm_up",
]
