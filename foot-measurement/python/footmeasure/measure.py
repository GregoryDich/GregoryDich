"""MVP-4: foot geometry -> length and maximum width (mm).

Two methods share the same 2D tail (floor-plane coordinates -> PCA axis -> extent / sections):

* ``contour`` (default): the RGB mask boundary gives the *direction* of each
  boundary ray, LiDAR gives the local foot height above the floor; each ray is
  intersected with the floor plane lifted by that height.  Immune to the
  LiDAR edge bleed and needs no erosion / percentile trimming.
* ``depth``: LiDAR points inside the eroded mask, above ``h_min``; robust
  percentiles for the extent (the classic point-cloud path, kept as a
  cross-check; it is biased low by a few mm by construction).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .floor import FloorResult, estimate_floor
from .geometry import (Plane, foot_depth_points, intersect_rays_plane, pixel_rays,
                       rgb_to_depth_coords)


@dataclass
class Measurement:
    length_mm: float
    width_mm: float
    method: str
    plane: Plane
    heel_3d: np.ndarray            # camera frame, metres
    toe_3d: np.ndarray
    width_left_3d: np.ndarray
    width_right_3d: np.ndarray
    axis_3d: np.ndarray            # longitudinal unit vector (camera frame)
    transverse_3d: np.ndarray
    n_points: int                  # LiDAR foot points above h_min
    foot_height_mm: float          # median LiDAR height of the foot above the floor
    plane_rms_mm: float
    floor_inliers: int
    normal_vs_up_deg: float | None
    pca_vs_rect_deg: float
    width_at_mm: float             # position of the max-width section along the axis (from heel)
    outline_ab_mm: np.ndarray      # (N,2) 2D outline / points in the PCA-aligned frame (a along, b across)
    contour_3d: np.ndarray | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return dict(length_mm=round(float(self.length_mm), 2), width_mm=round(float(self.width_mm), 2),
                    method=self.method, n_points=int(self.n_points),
                    foot_height_mm=round(float(self.foot_height_mm), 1),
                    plane_rms_mm=round(float(self.plane_rms_mm), 2), floor_inliers=int(self.floor_inliers),
                    normal_vs_up_deg=None if self.normal_vs_up_deg is None else round(float(self.normal_vs_up_deg), 1),
                    pca_vs_rect_deg=round(float(self.pca_vs_rect_deg), 1),
                    width_at_mm=round(float(self.width_at_mm), 1), warnings=list(self.warnings))


# ----------------------------------------------------------------- 2D helpers

def pca_axis(xy: np.ndarray) -> np.ndarray:
    c = xy.mean(0)
    _, _, vt = np.linalg.svd(xy - c, full_matrices=False)
    ax = vt[0]
    return ax / np.linalg.norm(ax)


def align_to_axis(xy: np.ndarray, axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Rotate so `axis` -> +a; returns (ab, R) with ab = (xy - 0) @ R.T."""
    R = np.array([[axis[0], axis[1]], [-axis[1], axis[0]]])
    return xy @ R.T, R


def min_area_rect_angle_deg(xy: np.ndarray) -> float:
    (_, _), (w, h), ang = cv2.minAreaRect(xy.astype(np.float32))
    return float(ang if w >= h else ang + 90.0)


def axis_angle_diff_deg(a1: float, a2: float) -> float:
    d = abs((a1 - a2 + 90.0) % 180.0 - 90.0)
    return float(d)


def polygon_section_widths(ab: np.ndarray, step: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact cross-section widths of a closed polygon at lines a = const, every `step` mm."""
    a = ab[:, 0]; b = ab[:, 1]
    a2 = np.roll(a, -1); b2 = np.roll(b, -1)
    amin, amax = a.min(), a.max()
    grid = np.arange(amin + step / 2, amax - step / 2 + 1e-9, step)
    inner = a[(a > amin + 1e-6) & (a < amax - 1e-6)]
    samples = np.unique(np.concatenate([grid, inner]))
    widths = np.full(len(samples), np.nan)
    bmin = np.full(len(samples), np.nan)
    bmax = np.full(len(samples), np.nan)
    for k, s in enumerate(samples):
        cross = ((a <= s) & (a2 > s)) | ((a2 <= s) & (a > s))
        if cross.sum() < 2:
            continue
        t = (s - a[cross]) / (a2[cross] - a[cross])
        bs = b[cross] + t * (b2[cross] - b[cross])
        bmin[k], bmax[k] = bs.min(), bs.max()
        widths[k] = bmax[k] - bmin[k]
    return samples, widths, bmin, bmax


def measure_outline_ab(ab: np.ndarray, step: float = 1.0) -> dict:
    """Length = extent along a; width = max cross-section (exact polygon slicing)."""
    i_heel, i_toe = int(np.argmin(ab[:, 0])), int(np.argmax(ab[:, 0]))
    length = float(ab[i_toe, 0] - ab[i_heel, 0])
    samples, widths, bmin, bmax = polygon_section_widths(ab, step)
    if np.all(np.isnan(widths)):
        raise ValueError("degenerate outline")
    k = int(np.nanargmax(widths))
    return dict(length=length, width=float(widths[k]), heel=ab[i_heel], toe=ab[i_toe],
                wl=np.array([samples[k], bmin[k]]), wr=np.array([samples[k], bmax[k]]),
                width_at=float(samples[k] - ab[i_heel, 0]))


def measure_points_ab(ab: np.ndarray, p_lo: float = 1.0, p_hi: float = 99.0,
                      n_sections: int = 20, min_pts: int = 15, wp_lo: float = 2.0, wp_hi: float = 98.0) -> dict:
    """Robust extent of a point cloud: percentiles along a, max over sections of percentile width."""
    a = ab[:, 0]; b = ab[:, 1]
    a_lo, a_hi = np.percentile(a, [p_lo, p_hi])
    edges = np.linspace(a_lo, a_hi, n_sections + 1)
    best = (-1.0, 0.0, 0.0, 0.0)
    for k in range(n_sections):
        sel = (a >= edges[k]) & (a < edges[k + 1]) if k < n_sections - 1 else (a >= edges[k]) & (a <= edges[k + 1])
        if sel.sum() < min_pts:
            continue
        lo, hi = np.percentile(b[sel], [wp_lo, wp_hi])
        if hi - lo > best[0]:
            best = (float(hi - lo), float(0.5 * (edges[k] + edges[k + 1])), float(lo), float(hi))
    if best[0] < 0:
        raise ValueError("no section with enough points")
    b_mid = float(np.median(b))
    return dict(length=float(a_hi - a_lo), width=best[0], heel=np.array([a_lo, b_mid]), toe=np.array([a_hi, b_mid]),
                wl=np.array([best[1], best[2]]), wr=np.array([best[1], best[3]]), width_at=float(best[1] - a_lo))


# ----------------------------------------------------------------- mask -> contour / heights

def clean_mask(mask: np.ndarray) -> np.ndarray:
    m = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 1:
        return np.zeros_like(mask, dtype=bool)
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return lab == biggest


def contour_from_mask(mask: np.ndarray, epsilon_px: float = 1.0) -> np.ndarray:
    m = clean_mask(mask).astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        raise ValueError("empty mask")
    c = max(cnts, key=cv2.contourArea)
    if epsilon_px > 0:
        c = cv2.approxPolyDP(c, epsilon_px, True)
    return c.reshape(-1, 2).astype(np.float64)


def mask_from_polygon(corners_uv: np.ndarray, rgb_size: tuple[int, int]) -> np.ndarray:
    W, H = rgb_size
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(np.asarray(corners_uv)).astype(np.int32)], 1)
    return m.astype(bool)


def local_heights_along_contour(contour_uv: np.ndarray, height_map_d: np.ndarray, rgb_size: tuple[int, int],
                                radius_d: int = 3, fallback: float = 0.0) -> np.ndarray:
    """Median LiDAR height (m) of foot pixels within `radius_d` depth-pixels of each contour point."""
    Hd, Wd = height_map_d.shape
    jd_id = np.round(rgb_to_depth_coords(contour_uv, rgb_size, (Wd, Hd))).astype(int)
    out = np.full(len(contour_uv), np.nan)
    for k, (j, i) in enumerate(jd_id):
        win = height_map_d[max(0, i - radius_d): i + radius_d + 1, max(0, j - radius_d): j + radius_d + 1]
        vals = win[np.isfinite(win)]
        if vals.size:
            out[k] = np.median(vals)
    bad = ~np.isfinite(out)
    out[bad] = fallback
    return out


# ----------------------------------------------------------------- main entry

def measure_frame(depth: np.ndarray, confidence: np.ndarray, K: np.ndarray, rgb_size: tuple[int, int],
                  mask: np.ndarray, T_world_cam: np.ndarray | None = None, method: str = "contour",
                  fixed_height_m: float | None = None, h_min: float = 0.004, h_max: float = 0.15,
                  conf_min: int = 1, floor: FloorResult | None = None, radius_d: int = 3,
                  height_fraction: float = 0.5) -> Measurement:
    """Measure one frame.  See module docstring for the two methods.

    height_fraction: the silhouette of a rounded foot is tangent to the surface somewhere
    between the floor and the local top height; contour rays are lifted to
    ``height_fraction * local LiDAR height``.  0.5 is a neutral default to be
    calibrated against reference measurements (README, section "эталонная проверка").
    """
    warns: list[str] = []
    if floor is None:
        floor = estimate_floor(depth, confidence, K, rgb_size, mask, T_world_cam)
    warns += floor.warnings
    plane = floor.plane
    Hd, Wd = depth.shape

    # LiDAR points of the foot and their heights above the floor
    pts, idx, _ = foot_depth_points(depth, confidence, K, rgb_size, mask, conf_min=conf_min)
    h = plane.signed_distance(pts) if len(pts) else np.zeros(0)
    keep = h < h_max
    pts, idx, h = pts[keep], idx[keep], h[keep]
    hmap = np.full(Hd * Wd, np.nan)
    hmap[idx] = h
    hmap = hmap.reshape(Hd, Wd)
    above = h > h_min
    n_points = int(above.sum())
    foot_height = float(np.median(h[above])) if n_points else 0.0

    if method == "contour":
        contour = contour_from_mask(mask)
        if fixed_height_m is not None:
            hc = np.full(len(contour), float(fixed_height_m))
        else:
            hc = local_heights_along_contour(contour, hmap, rgb_size, radius_d, fallback=foot_height)
            hc = np.clip(hc * height_fraction, 0.0, 0.08)
        rays = pixel_rays(contour, K)
        denom = rays @ plane.n
        with np.errstate(divide="ignore", invalid="ignore"):
            t = -(plane.d - hc) / denom
        ok = np.isfinite(t) & (t > 0)
        if ok.sum() < 3:
            raise ValueError("contour rays do not hit the floor plane")
        contour_3d = (rays * t[:, None])[ok]
        xy_mm = plane.to_2d(contour_3d) * 1000.0
        axis = pca_axis(xy_mm)
        ab, R = align_to_axis(xy_mm, axis)
        res = measure_outline_ab(ab)
        if res["width_at"] < 0.5 * res["length"]:   # widest section is near the toes: put the toe at +a
            axis = -axis
            ab, R = align_to_axis(xy_mm, axis)
            res = measure_outline_ab(ab)
        z_draw = float(np.median(hc[ok]))
    elif method == "depth":
        sel = above
        if sel.sum() < 30:
            raise ValueError(f"only {int(sel.sum())} LiDAR foot points above h_min")
        xy_mm = plane.to_2d(pts[sel]) * 1000.0
        c = np.median(xy_mm, 0)
        xy_mm = xy_mm[np.linalg.norm(xy_mm - c, axis=1) < 250.0]  # nothing foot-like is > 25 cm from centre
        axis = pca_axis(xy_mm)
        ab, R = align_to_axis(xy_mm, axis)
        res = measure_points_ab(ab)
        if res["width_at"] < 0.5 * res["length"]:
            axis = -axis
            ab, R = align_to_axis(xy_mm, axis)
            res = measure_points_ab(ab)
        contour_3d = None
        z_draw = h_min
    else:
        raise ValueError(method)

    pca_deg = float(np.degrees(np.arctan2(axis[1], axis[0])))
    rect_deg = min_area_rect_angle_deg(xy_mm)
    dang = axis_angle_diff_deg(pca_deg, rect_deg)
    if dang > 12.0:
        warns.append(f"PCA axis differs from min-area-rect axis by {dang:.1f} deg: axis unreliable?")

    def lift(ab_pt: np.ndarray) -> np.ndarray:
        xy = (np.asarray(ab_pt)[None, :] @ R) / 1000.0
        return plane.from_2d(xy, z_draw)[0]

    e1, e2, _ = plane.basis()
    axis_3d = axis[0] * e1 + axis[1] * e2
    trans_3d = -axis[1] * e1 + axis[0] * e2
    return Measurement(
        length_mm=res["length"], width_mm=res["width"], method=method, plane=plane,
        heel_3d=lift(res["heel"]), toe_3d=lift(res["toe"]), width_left_3d=lift(res["wl"]), width_right_3d=lift(res["wr"]),
        axis_3d=axis_3d, transverse_3d=trans_3d, n_points=n_points, foot_height_mm=foot_height * 1000.0,
        plane_rms_mm=floor.rms_mm, floor_inliers=floor.n_inliers, normal_vs_up_deg=floor.normal_vs_up_deg,
        pca_vs_rect_deg=dang, width_at_mm=res["width_at"], outline_ab_mm=ab, contour_3d=contour_3d, warnings=warns,
    )
