"""MVP-1: prove that RGB, depth and confidence arrive and are aligned.

Writes one PNG per sampled frame:
    top row:    RGB | depth (turbo colormap) | confidence
    bottom row: RGB with a semi-transparent depth overlay (alignment check)
and prints simple depth statistics.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .session import Frame, Session
from .util import bgr, rotate_to_upright


def colorize_depth(depth: np.ndarray, dmin: float = 0.2, dmax: float = 1.5) -> np.ndarray:
    d = np.nan_to_num(depth.astype(np.float32), nan=0.0)
    valid = d > 0
    norm = np.clip((d - dmin) / (dmax - dmin), 0, 1)
    img = cv2.applyColorMap((255 * (1 - norm)).astype(np.uint8), cv2.COLORMAP_TURBO)
    img[~valid] = 0
    return img


def colorize_confidence(conf: np.ndarray) -> np.ndarray:
    lut = np.array([[0, 0, 200], [0, 200, 200], [0, 200, 0]], dtype=np.uint8)  # low, med, high (BGR)
    return lut[np.clip(conf, 0, 2)]


def depth_overlay(rgb: np.ndarray, depth: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    H, W = rgb.shape[:2]
    dcol = cv2.resize(colorize_depth(depth), (W, H), interpolation=cv2.INTER_NEAREST)
    return cv2.addWeighted(bgr(rgb), 1 - alpha, dcol, alpha, 0)


def make_panel(frame: Frame, orientation: str | None = None, scale: float = 0.5) -> np.ndarray:
    H, W = frame.rgb.shape[:2]
    size = (int(W * scale), int(H * scale))
    a = cv2.resize(bgr(frame.rgb), size)
    b = cv2.resize(colorize_depth(frame.depth), size, interpolation=cv2.INTER_NEAREST)
    c = cv2.resize(colorize_confidence(frame.confidence), size, interpolation=cv2.INTER_NEAREST)
    top = np.hstack([a, b, c])
    ov = cv2.resize(depth_overlay(frame.rgb, frame.depth), size)
    pad = np.zeros_like(top)
    pad[:, : ov.shape[1]] = ov
    panel = np.vstack([top, pad])
    d = frame.depth
    valid = np.isfinite(d) & (d > 0)
    hd, wd = d.shape
    centre = d[hd // 2 - 8: hd // 2 + 8, wd // 2 - 8: wd // 2 + 8]
    txt = (f"frame {frame.index}  t={frame.t:.3f}s  valid={valid.mean() * 100:.0f}%  "
           f"centre depth={np.nanmedian(centre):.3f}m  conf hi={np.mean(frame.confidence == 2) * 100:.0f}%")
    cv2.putText(panel, txt, (10, panel.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return rotate_to_upright(panel, orientation)


def run(session: Session, step: int = 15, out_dir: str | Path = "out", rotate: bool = False,
        max_frames: int | None = None) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    print(f"session {session.path}: {session.n_frames} frames, video {session.video_size}, "
          f"depth {session.depth_size}, orientation={session.orientation}")
    for w in session.warnings:
        print(f"  WARNING: {w}")
    for frame in session.iter_frames(step=step, max_frames=max_frames):
        panel = make_panel(frame, session.orientation if rotate else None)
        p = out / f"frame_{frame.index:05d}.png"
        cv2.imwrite(str(p), panel)
        written.append(p)
        d = frame.depth
        valid = np.isfinite(d) & (d > 0)
        print(f"  frame {frame.index:5d} t={frame.t:7.3f}s depth[min/med/max]="
              f"{d[valid].min():.3f}/{np.median(d[valid]):.3f}/{d[valid].max():.3f} m "
              f"valid={valid.mean() * 100:.0f}% fx={frame.K[0, 0]:.1f} -> {p.name}")
    return written
