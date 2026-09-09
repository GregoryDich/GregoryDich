"""Floor plane from LiDAR points around the foot (RANSAC + least squares)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .geometry import Plane, background_depth_points


@dataclass
class FloorResult:
    plane: Plane
    n_candidates: int
    n_inliers: int
    rms_mm: float
    normal_vs_up_deg: float | None
    warnings: list[str] = field(default_factory=list)


def fit_plane_lsq(points: np.ndarray) -> Plane:
    c = points.mean(0)
    _, _, vt = np.linalg.svd(points - c, full_matrices=False)
    n = vt[-1]
    n /= np.linalg.norm(n)
    d = -float(n @ c)
    if d < 0:  # camera origin (0,0,0) on the positive side
        n, d = -n, -d
    return Plane(n, d)


def fit_plane_ransac(points: np.ndarray, thresh: float = 0.005, iters: int = 300, seed: int = 0
                     ) -> tuple[Plane, np.ndarray]:
    pts = np.asarray(points, dtype=np.float64)
    if len(pts) < 3:
        raise ValueError("need >= 3 points for a plane")
    rng = np.random.default_rng(seed)
    best_inl = None
    best_cnt = -1
    for _ in range(iters):
        i = rng.choice(len(pts), 3, replace=False)
        p0, p1, p2 = pts[i]
        n = np.cross(p1 - p0, p2 - p0)
        nn = np.linalg.norm(n)
        if nn < 1e-12:
            continue
        n /= nn
        d = -n @ p0
        dist = np.abs(pts @ n + d)
        inl = dist < thresh
        cnt = int(inl.sum())
        if cnt > best_cnt:
            best_cnt, best_inl = cnt, inl
    plane = fit_plane_lsq(pts[best_inl])
    inl = np.abs(plane.signed_distance(pts)) < thresh
    plane = fit_plane_lsq(pts[inl])  # one more refinement on the refined inlier set
    return plane, inl


def estimate_floor(depth: np.ndarray, confidence: np.ndarray, K_rgb: np.ndarray,
                   rgb_size: tuple[int, int], mask_rgb: np.ndarray, T_world_cam: np.ndarray | None = None,
                   thresh: float = 0.005, dilate_px: int = 5, conf_min: int = 2, seed: int = 0) -> FloorResult:
    pts = background_depth_points(depth, confidence, K_rgb, rgb_size, mask_rgb, dilate_px, conf_min)
    warns: list[str] = []
    if len(pts) < 50:
        raise ValueError(f"only {len(pts)} floor candidate points")
    plane, inl = fit_plane_ransac(pts, thresh=thresh, seed=seed)
    res = plane.signed_distance(pts[inl])
    rms_mm = float(np.sqrt(np.mean(res ** 2)) * 1000.0)
    ang = None
    if T_world_cam is not None:
        up_cam = T_world_cam[:3, :3].T @ np.array([0.0, 1.0, 0.0])  # world +y (gravity up) in camera frame
        ang = float(np.degrees(np.arccos(np.clip(abs(plane.n @ up_cam), -1, 1))))
        if ang > 15.0:
            warns.append(f"floor normal is {ang:.1f} deg from ARKit gravity-up: not a floor?")
    if inl.mean() < 0.5:
        warns.append(f"floor inliers only {inl.mean() * 100:.0f}% of background points")
    return FloorResult(plane, len(pts), int(inl.sum()), rms_mm, ang, warns)
