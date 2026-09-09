"""Measurement session loader.

Session layout (written by the iOS FootCapture app):

    session/
        video.mov        H.264, frame i <-> frames[i] in metadata.json
        depth.bin        concatenated float32 LE depth maps, H_d x W_d each, metres
        confidence.bin   concatenated uint8 confidence maps (0 low, 1 medium, 2 high)
        metadata.json    see FrameMeta for the per-frame fields

All geometry stays in ARKit's sensor frame (landscape). Frames are decoded
sequentially with cv2.VideoCapture — no seeking — so index i of the video
always pairs with depth frame i.
"""
from __future__ import annotations

import json
import warnings
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

DEPTH_DTYPE = np.dtype("<f4")
CONF_DTYPE = np.dtype("u1")


@dataclass
class FrameMeta:
    index: int
    t: float                 # seconds since recording start (video presentation time)
    timestamp: float         # ARFrame.timestamp (device uptime, seconds)
    K: np.ndarray            # 3x3 intrinsics for the RGB image resolution
    T_world_cam: np.ndarray  # 4x4 camera-to-world (ARKit convention: x right, y up, z back)
    exposure_duration: float = 0.0

    @classmethod
    def from_json(cls, d: dict) -> "FrameMeta":
        if "fx" in d:
            K = np.array([[d["fx"], 0.0, d["cx"]], [0.0, d["fy"], d["cy"]], [0.0, 0.0, 1.0]], dtype=np.float64)
        else:  # legacy nested 3x3
            K = np.asarray(d["intrinsics"], dtype=np.float64).reshape(3, 3)
        if "transform_row_major" in d:
            T = np.asarray(d["transform_row_major"], dtype=np.float64).reshape(4, 4)
        elif "transform" in d:
            T = np.asarray(d["transform"], dtype=np.float64).reshape(4, 4)
        else:
            T = np.eye(4)
        return cls(
            index=int(d["index"]),
            t=float(d.get("t", 0.0)),
            timestamp=float(d.get("timestamp", 0.0)),
            K=K,
            T_world_cam=T,
            exposure_duration=float(d.get("exposure_duration", 0.0)),
        )


@dataclass
class Frame:
    index: int
    t: float
    rgb: np.ndarray          # H x W x 3 uint8, RGB
    depth: np.ndarray        # H_d x W_d float32, metres (0 / NaN = invalid)
    confidence: np.ndarray   # H_d x W_d uint8
    K: np.ndarray            # 3x3, RGB resolution
    T_world_cam: np.ndarray  # 4x4
    orientation: str | None = None


@dataclass
class Session:
    path: Path
    meta: dict
    frames: list[FrameMeta]
    depth: np.ndarray        # memmap N x H_d x W_d float32
    confidence: np.ndarray   # memmap N x H_d x W_d uint8
    video_path: Path
    video_size: tuple[int, int]   # (W, H)
    depth_size: tuple[int, int]   # (W_d, H_d)
    warnings: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ loading
    @classmethod
    def load(cls, path: str | Path) -> "Session":
        path = Path(path)
        if path.is_file() and path.suffix.lower() == ".zip":
            path = _extract_zip(path)
        root = _find_session_root(path)
        meta = json.loads((root / "metadata.json").read_text())
        warns: list[str] = []

        frames = [FrameMeta.from_json(f) for f in meta["frames"]]
        vid = meta["video"]
        W, H = int(vid["width"]), int(vid["height"])
        dep = meta["depth"]
        Wd, Hd = int(dep["width"]), int(dep["height"])
        video_path = root / vid.get("path", "video.mov")

        n_meta = len(frames)
        depth_mm = _memmap(root / "depth.bin", DEPTH_DTYPE, Hd, Wd)
        conf_mm = _memmap(root / "confidence.bin", CONF_DTYPE, Hd, Wd)
        n = min(n_meta, depth_mm.shape[0], conf_mm.shape[0])
        if n != n_meta or n != depth_mm.shape[0] or n != conf_mm.shape[0]:
            warns.append(
                f"frame count mismatch: metadata={n_meta} depth.bin={depth_mm.shape[0]} "
                f"confidence.bin={conf_mm.shape[0]} -> using first {n}"
            )
        frames = frames[:n]
        depth_mm = depth_mm[:n]
        conf_mm = conf_mm[:n]

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise FileNotFoundError(f"cannot open video {video_path}")
        vw, vh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        vcount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if (vw, vh) != (W, H):
            warns.append(f"video size {vw}x{vh} != metadata {W}x{H}; using metadata intrinsics as-is")
            W, H = vw, vh
        if vcount > 0 and vcount != n:
            warns.append(f"video reports {vcount} frames, metadata has {n}; pairing by index up to min")

        # Sanity checks on calibration (catch transposed matrices / wrong resolution).
        if frames:
            K0 = frames[0].K
            if not (0.3 * W < K0[0, 2] < 0.7 * W and 0.3 * H < K0[1, 2] < 0.7 * H):
                warns.append(f"principal point {K0[0, 2]:.0f},{K0[1, 2]:.0f} not near image centre of {W}x{H}")
            T0 = frames[0].T_world_cam
            if not np.allclose(T0[3], [0, 0, 0, 1], atol=1e-4):
                warns.append("transform last row is not (0,0,0,1): expected row-major camera-to-world")

        for w in warns:
            warnings.warn(w)
        return cls(
            path=root, meta=meta, frames=frames, depth=depth_mm, confidence=conf_mm,
            video_path=video_path, video_size=(W, H), depth_size=(Wd, Hd), warnings=warns,
        )

    # ------------------------------------------------------------------ access
    @property
    def n_frames(self) -> int:
        return len(self.frames)

    @property
    def orientation(self) -> str | None:
        return self.meta.get("interface_orientation")

    @property
    def fps(self) -> float:
        return float(self.meta.get("video", {}).get("fps", 30.0))

    def iter_frames(self, step: int = 1, indices: list[int] | None = None,
                    max_frames: int | None = None) -> Iterator[Frame]:
        """Yield frames sequentially. `indices` (sorted) overrides `step`."""
        wanted = set(indices) if indices is not None else None
        cap = cv2.VideoCapture(str(self.video_path))
        try:
            yielded = 0
            drift_warned = False
            for i in range(self.n_frames):
                ok, bgr_img = cap.read()
                if not ok:
                    self.warnings.append(f"video ended at frame {i} but metadata has {self.n_frames}")
                    warnings.warn(self.warnings[-1])
                    return
                take = (i in wanted) if wanted is not None else (i % step == 0)
                if not take:
                    continue
                pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                fm = self.frames[i]
                if (not drift_warned and pos_ms > 0
                        and abs(pos_ms / 1000.0 - fm.t) > 1.5 / max(self.fps, 1.0) + 1e-3):
                    # POS_MSEC may be the time *after* the read on some backends;
                    # allow 1.5 frames of slack before complaining (once).
                    drift_warned = True
                    self.warnings.append(
                        f"video time {pos_ms / 1000.0:.3f}s vs metadata t={fm.t:.3f}s at frame {i}: "
                        "possible dropped frames / index drift")
                    warnings.warn(self.warnings[-1])
                yield Frame(
                    index=i, t=fm.t, rgb=cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB),
                    depth=np.array(self.depth[i]), confidence=np.array(self.confidence[i]),
                    K=fm.K, T_world_cam=fm.T_world_cam, orientation=self.orientation,
                )
                yielded += 1
                if max_frames is not None and yielded >= max_frames:
                    return
        finally:
            cap.release()

    def frame(self, index: int) -> Frame:
        for f in self.iter_frames(indices=[index]):
            return f
        raise IndexError(index)


# ---------------------------------------------------------------------- helpers

def _memmap(path: Path, dtype: np.dtype, h: int, w: int) -> np.ndarray:
    size = path.stat().st_size
    per = h * w * dtype.itemsize
    n = size // per
    if size % per:
        warnings.warn(f"{path.name}: size {size} is not a multiple of a frame ({per} bytes)")
    if n == 0:
        return np.zeros((0, h, w), dtype=dtype)
    return np.memmap(path, dtype=dtype, mode="r", shape=(n, h, w))


def _find_session_root(path: Path) -> Path:
    if (path / "metadata.json").exists():
        return path
    cands = sorted(path.rglob("metadata.json"))
    if not cands:
        raise FileNotFoundError(f"no metadata.json under {path}")
    return cands[0].parent


def _extract_zip(zpath: Path) -> Path:
    out = zpath.with_suffix("")
    if not (out.exists() and any(out.rglob("metadata.json"))):
        out.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(out)
    return out
