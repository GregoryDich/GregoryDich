"""MVP-5: sample frames, gate by quality, measure each, aggregate with the median.

Each FrameResult keeps its camera pose and 3D contour so the frames can later
be fused into one world-frame cloud (``fuse_clouds``) — the architecture hook
for MVP-6; the numbers are aggregated per frame for now.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .geometry import transform_points
from .measure import Measurement, measure_frame
from .session import Frame, Session


@dataclass
class FrameResult:
    index: int
    t: float
    confidence: float | None
    measurement: Measurement | None
    rejected_reason: str | None
    T_world_cam: np.ndarray
    mask: np.ndarray | None = None
    two_pass: bool = False

    @property
    def accepted(self) -> bool:
        return self.measurement is not None and self.rejected_reason is None

    def to_json(self) -> dict:
        d = dict(index=self.index, t=round(self.t, 3),
                 confidence=None if self.confidence is None else round(float(self.confidence), 3),
                 rejected_reason=self.rejected_reason, two_pass=self.two_pass)
        if self.measurement is not None:
            d.update(self.measurement.as_dict())
        return d


@dataclass
class ProcessResult:
    summary: dict
    frames: list[FrameResult]
    best: FrameResult | None
    used: list[FrameResult] = field(default_factory=list)


def gate(m: Measurement, confidence: float, min_conf: float, min_points: int,
         min_floor_inliers: int, max_plane_rms_mm: float) -> str | None:
    if confidence < min_conf:
        return f"low confidence {confidence:.2f} < {min_conf}"
    if m.n_points < min_points:
        return f"too few LiDAR foot points {m.n_points} < {min_points}"
    if m.floor_inliers < min_floor_inliers:
        return f"too few floor inliers {m.floor_inliers} < {min_floor_inliers}"
    if m.plane_rms_mm > max_plane_rms_mm:
        return f"floor plane rms {m.plane_rms_mm:.1f} mm > {max_plane_rms_mm}"
    if m.normal_vs_up_deg is not None and m.normal_vs_up_deg > 20.0:
        return f"floor normal {m.normal_vs_up_deg:.0f} deg from gravity"
    return None


def measure_one(frame: Frame, detector, method: str = "contour", min_conf: float = 0.3, min_points: int = 500,
                min_floor_inliers: int = 2000, max_plane_rms_mm: float = 6.0, measure_kwargs: dict | None = None
                ) -> FrameResult:
    det = detector.detect(frame.rgb, frame.orientation)
    if det is None:
        return FrameResult(frame.index, frame.t, None, None, "no detection", frame.T_world_cam)
    W, H = frame.rgb.shape[1], frame.rgb.shape[0]
    try:
        m = measure_frame(frame.depth, frame.confidence, frame.K, (W, H), det.mask, frame.T_world_cam,
                          method=method, **(measure_kwargs or {}))
    except ValueError as e:
        return FrameResult(frame.index, frame.t, det.confidence, None, f"measure failed: {e}",
                           frame.T_world_cam, det.mask, det.two_pass)
    reason = gate(m, det.confidence, min_conf, min_points, min_floor_inliers, max_plane_rms_mm)
    return FrameResult(frame.index, frame.t, det.confidence, m, reason, frame.T_world_cam, det.mask, det.two_pass)


def aggregate(results: list[FrameResult], top_k: int = 7) -> tuple[dict, list[FrameResult]]:
    acc = [r for r in results if r.accepted]
    acc.sort(key=lambda r: (r.confidence, r.measurement.n_points), reverse=True)
    used = acc[:top_k]
    if not used:
        return dict(length_mm=None, width_mm=None, valid_frames=0, frames_used=0), []
    L = np.array([r.measurement.length_mm for r in used])
    Wd = np.array([r.measurement.width_mm for r in used])
    q = lambda x: float(np.percentile(x, 75) - np.percentile(x, 25))
    return dict(
        length_mm=round(float(np.median(L)), 1), width_mm=round(float(np.median(Wd)), 1),
        valid_frames=len(acc), frames_used=len(used),
        length_iqr_mm=round(q(L), 2), width_iqr_mm=round(q(Wd), 2),
        length_std_mm=round(float(L.std()), 2), width_std_mm=round(float(Wd.std()), 2),
        length_min_max_mm=[round(float(L.min()), 1), round(float(L.max()), 1)],
        width_min_max_mm=[round(float(Wd.min()), 1), round(float(Wd.max()), 1)],
    ), used


def fuse_clouds(results: list[FrameResult]) -> np.ndarray:
    """World-frame concatenation of the per-frame 3D contours (MVP-6 hook; not used for the numbers yet)."""
    parts = [transform_points(r.T_world_cam, r.measurement.contour_3d)
             for r in results if r.accepted and r.measurement.contour_3d is not None]
    return np.vstack(parts) if parts else np.zeros((0, 3))


def process_session(session: Session, detector, step: int = 5, top_k: int = 7, method: str = "contour",
                    min_conf: float = 0.3, min_points: int = 500, min_floor_inliers: int = 2000,
                    max_plane_rms_mm: float = 6.0, max_frames: int | None = None, fuse: bool = False,
                    measure_kwargs: dict | None = None, log=print) -> ProcessResult:
    t0 = time.time()
    results: list[FrameResult] = []
    for frame in session.iter_frames(step=step, max_frames=max_frames):
        r = measure_one(frame, detector, method, min_conf, min_points, min_floor_inliers, max_plane_rms_mm,
                        measure_kwargs)
        results.append(r)
        if log:
            if r.accepted:
                m = r.measurement
                log(f"  frame {r.index:5d}: L={m.length_mm:6.1f} W={m.width_mm:5.1f} conf={r.confidence:.2f} "
                    f"pts={m.n_points} rms={m.plane_rms_mm:.1f}")
            else:
                log(f"  frame {r.index:5d}: rejected ({r.rejected_reason})")
    summary, used = aggregate(results, top_k)
    best = used[0] if used else None
    summary.update(frames_processed=len(results), method=method, step=step,
                   best_frame=None if best is None else best.index,
                   per_frame=[r.to_json() for r in results],
                   processing_s=round(time.time() - t0, 1), session_warnings=list(session.warnings))
    if fuse:
        cloud = fuse_clouds(used)
        summary["fused_points"] = int(len(cloud))
    return ProcessResult(summary, results, best, used)
