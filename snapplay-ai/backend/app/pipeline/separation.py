"""Demucs v4 ``htdemucs`` source separation (contract §7, 900 ms budget on an A10G).

The model is loaded once per process (lazily, under a lock) and kept on the GPU. On
CUDA the forward pass runs under fp16 autocast; ``SNAPPLAY_TRT=1`` additionally tries
``torch.compile`` with the TensorRT backend (``torch_tensorrt``) and then the default
backend, keeping the eager model whenever compilation or the warm-up run fails.

torch and demucs are imported inside functions so the module imports on the API host,
where neither is installed.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, replace
from importlib.util import find_spec
from time import perf_counter
from typing import Any

import numpy as np

log = logging.getLogger("snapplay.pipeline.separation")

DEFAULT_MODEL = "htdemucs"
SOURCES: tuple[str, ...] = ("drums", "bass", "other", "vocals")
SAMPLE_RATE = 44100
SHIFTS = 0
OVERLAP = 0.25
DEFAULT_MAX_SEGMENT_SECONDS = 7.8  # htdemucs training segment; longer is rejected by demucs
INSTALL_HINT = "install the GPU extras: pip install -r requirements-gpu.txt (torch, demucs)"


@dataclass(frozen=True)
class LoadedSeparator:
    model: Any
    device: str
    fp16: bool
    segment: float
    sources: tuple[str, ...]
    backend: str


_loaded: LoadedSeparator | None = None
_lock = threading.Lock()


def is_available() -> bool:
    return find_spec("torch") is not None and find_spec("demucs") is not None


def require_extras() -> None:
    """Raise :class:`ImportError` with an install hint when torch or demucs is missing."""
    if not is_available():
        raise ImportError(f"Demucs separation needs torch and demucs; {INSTALL_HINT}")


def _import_torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise ImportError(f"Demucs separation needs torch; {INSTALL_HINT}") from exc
    return torch


def _device(torch: Any) -> str:
    requested = os.environ.get("SNAPPLAY_DEVICE", "").strip()
    if requested:
        return requested
    return "cuda" if torch.cuda.is_available() else "cpu"


def _max_segment(model: Any) -> float:
    limit = getattr(model, "max_allowed_segment", None)
    if isinstance(limit, int | float) and np.isfinite(limit) and limit > 0:
        return float(limit)
    segment = getattr(model, "segment", None)
    if isinstance(segment, int | float) and segment > 0:
        return float(segment)
    return DEFAULT_MAX_SEGMENT_SECONDS


def _segment_seconds(model: Any) -> float:
    """The chunk length: the largest the model allows (fewest chunks) unless
    ``SNAPPLAY_DEMUCS_SEGMENT`` asks for a shorter one to save GPU memory."""
    limit = _max_segment(model)
    requested = os.environ.get("SNAPPLAY_DEMUCS_SEGMENT", "").strip()
    if requested:
        try:
            return float(np.clip(float(requested), 1.0, limit))
        except ValueError:
            log.warning("ignoring invalid SNAPPLAY_DEMUCS_SEGMENT=%r", requested)
    return limit


def load_model() -> LoadedSeparator:
    """Load (once) and return the eager model on the selected device."""
    global _loaded
    if _loaded is not None:
        return _loaded
    with _lock:
        if _loaded is not None:
            return _loaded
        torch = _import_torch()
        try:
            from demucs.pretrained import get_model
        except ImportError as exc:
            raise ImportError(f"Demucs separation needs demucs; {INSTALL_HINT}") from exc
        name = os.environ.get("SNAPPLAY_DEMUCS_MODEL", "").strip() or DEFAULT_MODEL
        started = perf_counter()
        model = get_model(name)
        model.eval()
        device = _device(torch)
        model.to(device)
        fp16 = device.startswith("cuda") and os.environ.get("SNAPPLAY_FP16", "1") != "0"
        sources = tuple(str(s) for s in getattr(model, "sources", SOURCES))
        _loaded = LoadedSeparator(
            model=model,
            device=device,
            fp16=fp16,
            segment=_segment_seconds(model),
            sources=sources,
            backend="eager",
        )
        log.info(
            "demucs %s loaded on %s in %.2fs (fp16=%s, segment=%.2fs, sources=%s)",
            name,
            device,
            perf_counter() - started,
            fp16,
            _loaded.segment,
            ",".join(sources),
        )
        return _loaded


def _compile(loaded: LoadedSeparator, torch: Any, backend: str) -> tuple[Any, Callable[[], None]]:
    """``torch.compile`` the network(s) behind ``loaded.model``; returns the model to use
    and a callable that restores the eager modules."""
    model = loaded.model
    submodels = getattr(model, "models", None)
    if submodels is not None:  # demucs BagOfModels; apply_model must see the bag itself
        originals = list(submodels)
        compiled = [torch.compile(m, backend=backend, dynamic=True) for m in originals]
        model.models = torch.nn.ModuleList(compiled)

        def restore() -> None:
            model.models = torch.nn.ModuleList(originals)

        return model, restore
    return torch.compile(model, backend=backend, dynamic=True), lambda: None


def _trt_requested() -> bool:
    return os.environ.get("SNAPPLAY_TRT", "").strip() == "1"


def _dummy_mix(seconds: float) -> np.ndarray:
    return np.zeros((2, int(seconds * SAMPLE_RATE)), dtype=np.float32)


def warm_up(seconds: float = 2.0) -> LoadedSeparator:
    """Load the model and run one separation so the first job pays no start-up cost.
    With ``SNAPPLAY_TRT=1`` this is also where compilation happens (and is abandoned if
    the compiled graph fails)."""
    global _loaded
    loaded = load_model()
    if loaded.backend == "eager" and _trt_requested():
        torch = _import_torch()
        backends = ["tensorrt"] if find_spec("torch_tensorrt") is not None else []
        backends.append("inductor")
        for backend in backends:
            try:
                model, restore = _compile(loaded, torch, backend)
            except Exception as exc:
                log.warning("torch.compile(backend=%s) failed: %s", backend, exc)
                continue
            candidate = replace(loaded, model=model, backend=f"compile:{backend}")
            try:
                started = perf_counter()
                _separate(candidate, _dummy_mix(seconds))
            except Exception as exc:
                log.warning("compiled Demucs (%s) failed at run time: %s", backend, exc)
                restore()
                continue
            with _lock:
                _loaded = candidate
            log.info("demucs compiled with %s in %.1fs", backend, perf_counter() - started)
            return candidate
        log.warning("SNAPPLAY_TRT=1 but no compile backend worked; using the eager model")
    started = perf_counter()
    _separate(loaded, _dummy_mix(seconds))
    log.info("demucs warm-up separation took %.2fs", perf_counter() - started)
    return loaded


def _separate(loaded: LoadedSeparator, mix: np.ndarray) -> dict[str, np.ndarray]:
    torch = _import_torch()
    from demucs.apply import apply_model

    x = torch.from_numpy(np.ascontiguousarray(mix, dtype=np.float32))
    ref = x.mean(0)
    mean = ref.mean()
    std = ref.std() + 1e-8
    x = ((x - mean) / std)[None].to(loaded.device)
    autocast = (
        torch.autocast(device_type="cuda", dtype=torch.float16) if loaded.fp16 else nullcontext()
    )
    with torch.inference_mode(), autocast:
        out = apply_model(
            loaded.model,
            x,
            shifts=SHIFTS,
            overlap=OVERLAP,
            segment=loaded.segment,
            device=loaded.device,
            progress=False,
            num_workers=0,
        )
    out = (out[0].float() * std + mean).cpu().numpy()
    return {name: np.ascontiguousarray(out[i]) for i, name in enumerate(loaded.sources)}


def separate(mix: np.ndarray) -> dict[str, np.ndarray]:
    """Separate ``mix`` (2 × samples, float32, 44.1 kHz) into ``{source: (2 × samples)}``
    for every Demucs source (``drums``, ``bass``, ``other``, ``vocals``)."""
    if mix.ndim != 2 or mix.shape[0] != 2:
        raise ValueError("separate() expects a (2, samples) stereo array")
    return _separate(load_model(), mix)


__all__ = [
    "DEFAULT_MODEL",
    "INSTALL_HINT",
    "OVERLAP",
    "SAMPLE_RATE",
    "SHIFTS",
    "SOURCES",
    "LoadedSeparator",
    "is_available",
    "load_model",
    "require_extras",
    "separate",
    "warm_up",
]
