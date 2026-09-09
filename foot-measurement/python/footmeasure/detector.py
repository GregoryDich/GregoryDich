"""MVP-2: RF-DETR-Seg wrapper — the ONLY neural network in the pipeline.

RF-DETR answers "where is the foot?" (instance mask); it never measures.
Two passes with the same model: full frame -> bbox, then a padded square
crop so the foot fills the model input and the mask boundary is sharp at
RGB resolution.  Images are rotated upright (training data is upright) and
the mask is rotated back into the sensor frame.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .measure import clean_mask
from .util import rotate_from_upright, rotate_to_upright

_SIZES = {"nano": "RFDETRSegNano", "small": "RFDETRSegSmall", "medium": "RFDETRSegMedium",
          "large": "RFDETRSegLarge", "xlarge": "RFDETRSegXLarge", "2xlarge": "RFDETRSeg2XLarge"}


@dataclass
class FootDetection:
    mask: np.ndarray        # bool H x W, sensor frame (same as the RGB frame)
    confidence: float
    bbox: np.ndarray        # x1, y1, x2, y2 in the sensor frame
    class_id: int
    class_name: str
    two_pass: bool


class FootDetector:
    def __init__(self, weights: str | Path | None = None, size: str = "small", class_name: str | None = None,
                 threshold: float = 0.3, device: str | None = None, two_pass: bool = True,
                 crop_scale: float = 1.3, classes_json: str | Path | None = None):
        if size not in _SIZES:
            raise ValueError(f"size must be one of {list(_SIZES)}")
        self.weights = Path(weights) if weights else None
        self.size = size
        self.class_name = (class_name or ("foot" if weights else "person")).lower()
        self.threshold = threshold
        self.device = device
        self.two_pass = two_pass
        self.crop_scale = crop_scale
        self.classes_json = Path(classes_json) if classes_json else None
        self._model = None
        self._class_names: dict[int, str] | None = None
        self._warned_missing_class = False

    # ------------------------------------------------------------------ model
    def load(self):
        if self._model is not None:
            return self._model
        import rfdetr  # lazy: tests and the iOS-side tooling never need torch

        cls = getattr(rfdetr, _SIZES[self.size])
        kwargs = {}
        if self.weights:
            kwargs["pretrain_weights"] = str(self.weights)
        if self.device:
            kwargs["device"] = self.device
        self._model = cls(**kwargs)
        try:
            self._model.optimize_for_inference()
        except Exception as e:  # e.g. torch.compile / MPS quirks: plain eager inference still works
            warnings.warn(f"optimize_for_inference() failed ({e}); using eager inference")
        self._class_names = self._resolve_class_names()
        return self._model

    def _resolve_class_names(self) -> dict[int, str]:
        cj = self.classes_json
        if cj is None and self.weights is not None and (self.weights.parent / "classes.json").exists():
            cj = self.weights.parent / "classes.json"
        if cj is not None:
            raw = json.loads(Path(cj).read_text())
            return {int(k): str(v) for k, v in (raw.items() if isinstance(raw, dict) else enumerate(raw))}
        names = getattr(self._model, "class_names", None)
        if names:
            return {i: str(n) for i, n in enumerate(names)}
        return {}

    def class_names(self) -> dict[int, str]:
        self.load()
        return dict(self._class_names or {})

    # ------------------------------------------------------------------ inference
    def _predict_raw(self, rgb: np.ndarray):
        model = self.load()
        try:
            return model.predict(rgb, threshold=self.threshold, include_source_image=False)
        except TypeError:  # older rfdetr without include_source_image
            return model.predict(rgb, threshold=self.threshold)

    def _names_for(self, det) -> list[str]:
        data = getattr(det, "data", None) or {}
        if "class_name" in data:
            return [str(n).lower() for n in np.asarray(data["class_name"]).tolist()]
        names = self._class_names or {}
        return [str(names.get(int(c), c)).lower() for c in det.class_id]

    def _select(self, det) -> int | None:
        if det is None or len(det) == 0:
            return None
        names = self._names_for(det)
        conf = np.asarray(det.confidence, dtype=float)
        cand = [i for i, n in enumerate(names) if n == self.class_name]
        if not cand:
            if self.class_name in set(names):
                return None
            if not self._warned_missing_class:
                warnings.warn(f"class '{self.class_name}' not among model classes {sorted(set(names))}; "
                              "falling back to the most confident detection")
                self._warned_missing_class = True
            cand = list(range(len(names)))
        return int(cand[int(np.argmax(conf[cand]))])

    @staticmethod
    def _mask_at(det, i: int, shape: tuple[int, int]) -> np.ndarray:
        m = np.asarray(det.mask[i])
        if m.shape != shape:
            m = cv2.resize(m.astype(np.uint8), (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
        return m.astype(bool)

    def detect(self, rgb: np.ndarray, orientation: str | None = None) -> FootDetection | None:
        up = rotate_to_upright(rgb, orientation)
        H, W = up.shape[:2]
        det = self._predict_raw(up)
        i = self._select(det)
        if i is None:
            return None
        conf = float(det.confidence[i])
        class_id = int(det.class_id[i])
        name = self._names_for(det)[i]
        mask = self._mask_at(det, i, (H, W))
        used_two_pass = False

        if self.two_pass:
            x1, y1, x2, y2 = np.asarray(det.xyxy[i], dtype=float)
            cx, cy = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
            side = self.crop_scale * max(x2 - x1, y2 - y1)
            x0, y0 = int(max(0, np.floor(cx - side / 2))), int(max(0, np.floor(cy - side / 2)))
            x3, y3 = int(min(W, np.ceil(cx + side / 2))), int(min(H, np.ceil(cy + side / 2)))
            crop = np.ascontiguousarray(up[y0:y3, x0:x3])
            if crop.size and min(crop.shape[:2]) >= 32 and (x3 - x0) * (y3 - y0) < 0.9 * W * H:
                det2 = self._predict_raw(crop)
                j = self._select(det2)
                if j is not None:
                    full = np.zeros((H, W), bool)
                    full[y0:y3, x0:x3] = self._mask_at(det2, j, crop.shape[:2])
                    if full.sum() > 0.3 * mask.sum():   # sanity: the crop pass must find (roughly) the same foot
                        mask = full
                        conf = float(det2.confidence[j])
                        used_two_pass = True

        mask = clean_mask(mask)
        if not mask.any():
            return None
        mask_s = rotate_from_upright(mask.astype(np.uint8), orientation).astype(bool)
        ys, xs = np.nonzero(mask_s)
        bbox = np.array([xs.min(), ys.min(), xs.max(), ys.max()], dtype=float)
        return FootDetection(mask_s, conf, bbox, class_id, name, used_two_pass)


class ColorMockDetector:
    """Synthetic-session helper (tests / dry runs): 'detects' the skin-coloured blob painted by tests.synth."""

    def __init__(self, confidence: float = 0.9):
        self.confidence = confidence

    def detect(self, rgb: np.ndarray, orientation: str | None = None) -> FootDetection | None:
        r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
        mask = clean_mask((r > g + 20) & (g > b + 10))
        if not mask.any():
            return None
        ys, xs = np.nonzero(mask)
        return FootDetection(mask, self.confidence, np.array([xs.min(), ys.min(), xs.max(), ys.max()], float), 1, "foot", False)
