"""Source separation (contract §7, 900 ms budget on an A10G).

The model named by ``SEPARATION_MODEL`` is loaded once per process (lazily, under a
lock) and kept on the GPU. Every model this module knows is listed in
:data:`SEPARATION_MODELS` together with the licence of its *weights*, which is what
matters commercially: the Demucs code is MIT, but Meta publishes the ``htdemucs*``
checkpoints for research use only, so a production worker refuses to load them unless
``ALLOW_UNLICENSED_SEPARATION_MODEL=1`` is set for internal testing
(:func:`check_model_licence`, called from :func:`load_model` and by the workers before
they poll).

On CUDA the forward pass runs under fp16 autocast; ``TONAMORPH_TRT=1`` additionally tries
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

from app.config import Settings, get_settings

log = logging.getLogger("tonamorph.pipeline.separation")

DEFAULT_MODEL = "htdemucs"
SOURCES: tuple[str, ...] = ("drums", "bass", "other", "vocals")
SAMPLE_RATE = 44100
SHIFTS = 0
OVERLAP = 0.25
DEFAULT_MAX_SEGMENT_SECONDS = 7.8  # htdemucs training segment; longer is rejected by demucs
INSTALL_HINT = "install the GPU extras: pip install -r requirements-gpu.txt (torch, demucs)"
ALLOW_UNLICENSED_ENV = "ALLOW_UNLICENSED_SEPARATION_MODEL"

FAMILY_DEMUCS = "demucs"
FAMILY_ROFORMER = "roformer"
FAMILY_API = "api"

DEMUCS_WEIGHTS_LICENCE = (
    "research use only: Meta's htdemucs checkpoints are not covered by the MIT code "
    "licence (facebookresearch/demucs#327) and were trained on the non-commercial MUSDB18-HQ"
)

SEPARATION_MODELS: dict[str, dict[str, Any]] = {
    "htdemucs": {
        "family": FAMILY_DEMUCS,
        "weights_licence": DEMUCS_WEIGHTS_LICENCE,
        "commercial_use": False,
    },
    "htdemucs_ft": {
        "family": FAMILY_DEMUCS,
        "weights_licence": DEMUCS_WEIGHTS_LICENCE,
        "commercial_use": False,
    },
    "htdemucs_6s": {
        "family": FAMILY_DEMUCS,
        "weights_licence": DEMUCS_WEIGHTS_LICENCE,
        "commercial_use": False,
    },
}
"""Model name → ``{"family", "weights_licence", "commercial_use"}``.

``commercial_use`` is ``True`` only once the licence of the exact checkpoint shipped has
been read and archived; ``False`` for weights known to be research-only; ``None`` for a
name this table does not list (any other Demucs bag name can be tried outside
production). Extending the table is the intended path off the Demucs blocker:

* **RoFormer checkpoint** (e.g. a Mel-Band RoFormer vocal model whose author relicensed
  the weights to MIT): add a row with ``"family": FAMILY_ROFORMER``, the checkpoint
  location under ``"checkpoint"`` and ``"commercial_use": True`` *after* verifying the
  licence on that checkpoint's model card, then give :func:`_load_family` a
  ``FAMILY_ROFORMER`` branch returning a model whose ``sources`` and ``segment``
  :class:`LoadedSeparator` can describe. Stems this pipeline needs are the four Demucs
  sources, so a vocals-only model has to be paired with a second stage for the rest.
* **Hosted API** (AudioShake, Music.ai, LALAL.AI and the like): add a row with
  ``"family": FAMILY_API`` and the vendor terms under ``"weights_licence"``, then let
  :func:`separate` route ``FAMILY_API`` models to an HTTP client instead of
  :func:`_separate`; the per-call price becomes a line item in ``docs/ECONOMICS.md``.
"""


class SeparationModelLicenceError(RuntimeError):
    """``SEPARATION_MODEL`` cannot be used in this environment (see :func:`check_model_licence`)."""


@dataclass(frozen=True)
class LoadedSeparator:
    name: str
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


def model_info(name: str) -> dict[str, Any]:
    """The :data:`SEPARATION_MODELS` row for ``name``; an unlisted name is treated as a
    Demucs bag whose weights licence is unknown."""
    return dict(
        SEPARATION_MODELS.get(name)
        or {"family": FAMILY_DEMUCS, "weights_licence": "unknown", "commercial_use": None}
    )


def unlicensed_allowed() -> bool:
    """``ALLOW_UNLICENSED_SEPARATION_MODEL=1`` (also ``true`` / ``yes``) in the environment."""
    return os.environ.get(ALLOW_UNLICENSED_ENV, "").strip().lower() in {"1", "true", "yes"}


def check_model_licence(
    name: str, env: str, *, allow_unlicensed: bool = False
) -> dict[str, Any]:
    """Return ``model_info(name)`` or raise :class:`SeparationModelLicenceError`.

    Outside ``production`` every model is allowed. In production a model is allowed
    only when its weights are recorded as licensed for commercial use, or when the
    operator explicitly accepts the risk for internal testing with ``allow_unlicensed``
    (``ALLOW_UNLICENSED_SEPARATION_MODEL=1``), which is logged as a warning.
    """
    info = model_info(name)
    if env != "production" or info["commercial_use"] is True:
        return info
    if allow_unlicensed:
        log.warning(
            "SEPARATION_MODEL %r weights are not licensed for commercial use; running because "
            "%s is set (internal testing only)",
            name,
            ALLOW_UNLICENSED_ENV,
        )
        return info
    reason = (
        "are not licensed for commercial use"
        if info["commercial_use"] is False
        else "have no recorded licence"
    )
    raise SeparationModelLicenceError(
        f"SEPARATION_MODEL {name!r} weights {reason}; set SEPARATION_MODEL to a licensed "
        f"model or {ALLOW_UNLICENSED_ENV}=1 for internal testing"
    )


def ensure_licensed(settings: Settings | None = None) -> dict[str, Any]:
    """:func:`check_model_licence` for the configured model and environment."""
    settings = settings if settings is not None else get_settings()
    return check_model_licence(
        settings.separation_model, settings.env, allow_unlicensed=unlicensed_allowed()
    )


def _import_torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise ImportError(f"Demucs separation needs torch; {INSTALL_HINT}") from exc
    return torch


def _device(torch: Any) -> str:
    requested = os.environ.get("TONAMORPH_DEVICE", "").strip()
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
    ``TONAMORPH_DEMUCS_SEGMENT`` asks for a shorter one to save GPU memory."""
    limit = _max_segment(model)
    requested = os.environ.get("TONAMORPH_DEMUCS_SEGMENT", "").strip()
    if requested:
        try:
            return float(np.clip(float(requested), 1.0, limit))
        except ValueError:
            log.warning("ignoring invalid TONAMORPH_DEMUCS_SEGMENT=%r", requested)
    return limit


def _load_family(name: str, info: dict[str, Any]) -> Any:
    """Construct the eager model for ``name``; one branch per model family."""
    family = info["family"]
    if family == FAMILY_DEMUCS:
        try:
            from demucs.pretrained import get_model
        except ImportError as exc:
            raise ImportError(f"Demucs separation needs demucs; {INSTALL_HINT}") from exc
        return get_model(name)
    raise NotImplementedError(
        f"SEPARATION_MODEL {name!r} belongs to family {family!r}, which has no loader yet; "
        "see SEPARATION_MODELS in app/pipeline/separation.py"
    )


def load_model() -> LoadedSeparator:
    """Load (once) and return the eager model on the selected device, after the licence
    check for the current environment."""
    global _loaded
    if _loaded is not None:
        return _loaded
    with _lock:
        if _loaded is not None:
            return _loaded
        settings = get_settings()
        name = settings.separation_model
        info = ensure_licensed(settings)
        torch = _import_torch()
        started = perf_counter()
        model = _load_family(name, info)
        model.eval()
        device = _device(torch)
        model.to(device)
        fp16 = device.startswith("cuda") and os.environ.get("TONAMORPH_FP16", "1") != "0"
        sources = tuple(str(s) for s in getattr(model, "sources", SOURCES))
        _loaded = LoadedSeparator(
            name=name,
            model=model,
            device=device,
            fp16=fp16,
            segment=_segment_seconds(model),
            sources=sources,
            backend="eager",
        )
        log.info(
            "%s %s loaded on %s in %.2fs (fp16=%s, segment=%.2fs, sources=%s)",
            info["family"],
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
    return os.environ.get("TONAMORPH_TRT", "").strip() == "1"


def _dummy_mix(seconds: float) -> np.ndarray:
    return np.zeros((2, int(seconds * SAMPLE_RATE)), dtype=np.float32)


def warm_up(seconds: float = 2.0) -> LoadedSeparator:
    """Load the model and run one separation so the first job pays no start-up cost.
    With ``TONAMORPH_TRT=1`` this is also where compilation happens (and is abandoned if
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
                log.warning("compiled %s (%s) failed at run time: %s", loaded.name, backend, exc)
                restore()
                continue
            with _lock:
                _loaded = candidate
            log.info("%s compiled with %s in %.1fs", loaded.name, backend, perf_counter() - started)
            return candidate
        log.warning("TONAMORPH_TRT=1 but no compile backend worked; using the eager model")
    started = perf_counter()
    _separate(loaded, _dummy_mix(seconds))
    log.info("%s warm-up separation took %.2fs", loaded.name, perf_counter() - started)
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
    "ALLOW_UNLICENSED_ENV",
    "DEFAULT_MODEL",
    "FAMILY_API",
    "FAMILY_DEMUCS",
    "FAMILY_ROFORMER",
    "INSTALL_HINT",
    "OVERLAP",
    "SAMPLE_RATE",
    "SEPARATION_MODELS",
    "SHIFTS",
    "SOURCES",
    "LoadedSeparator",
    "SeparationModelLicenceError",
    "check_model_licence",
    "ensure_licensed",
    "is_available",
    "load_model",
    "model_info",
    "require_extras",
    "separate",
    "unlicensed_allowed",
    "warm_up",
]
