"""MVP-3: pixels <-> metric 3D in ARKit's camera convention.

Camera frame (ARKit): x right, y up, z backwards; a point in front of the
camera has z < 0 and depth = -z.  Pixel (u right, v down) at RGB resolution.

    x = (u - cx) * depth / fx
    y = -(v - cy) * depth / fy
    z = -depth

The 256x192 depth map is aligned with the 1920x1440 RGB image by pure
scaling; intrinsics are rescaled with pixel-centre convention.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


# ----------------------------------------------------------------- intrinsics

def scale_intrinsics(K: np.ndarray, src_size: tuple[int, int], dst_size: tuple[int, int]) -> np.ndarray:
    """Rescale K (for src W,H) to dst W,H using pixel-centre mapping u' = (u+0.5)*s - 0.5."""
    sx = dst_size[0] / src_size[0]
    sy = dst_size[1] / src_size[1]
    Kd = K.astype(np.float64).copy()
    Kd[0, 0] *= sx
    Kd[1, 1] *= sy
    Kd[0, 2] = (K[0, 2] + 0.5) * sx - 0.5
    Kd[1, 2] = (K[1, 2] + 0.5) * sy - 0.5
    return Kd


def rgb_to_depth_coords(uv: np.ndarray, rgb_size: tuple[int, int], depth_size: tuple[int, int]) -> np.ndarray:
    """RGB pixel coords (N,2) -> depth-map pixel coords (float)."""
    s = np.array([depth_size[0] / rgb_size[0], depth_size[1] / rgb_size[1]])
    return (uv + 0.5) * s - 0.5


def depth_to_rgb_coords(jd_id: np.ndarray, rgb_size: tuple[int, int], depth_size: tuple[int, int]) -> np.ndarray:
    s = np.array([depth_size[0] / rgb_size[0], depth_size[1] / rgb_size[1]])
    return (jd_id + 0.5) / s - 0.5


# ----------------------------------------------------------------- (un)projection

def pixel_rays(uv: np.ndarray, K: np.ndarray) -> np.ndarray:
    """Ray directions (N,3) through pixels, scaled so that -z == 1 (i.e. depth 1)."""
    uv = np.asarray(uv, dtype=np.float64)
    x = (uv[:, 0] - K[0, 2]) / K[0, 0]
    y = -(uv[:, 1] - K[1, 2]) / K[1, 1]
    return np.stack([x, y, -np.ones_like(x)], 1)


def unproject(depth: np.ndarray, K: np.ndarray, valid: np.ndarray | None = None
              ) -> tuple[np.ndarray, np.ndarray]:
    """Depth map (H,W) -> points (N,3) in camera frame + flat pixel indices (N,)."""
    H, W = depth.shape
    if valid is None:
        valid = np.isfinite(depth) & (depth > 0)
    ii, jj = np.nonzero(valid)
    d = depth[ii, jj].astype(np.float64)
    uv = np.stack([jj, ii], 1).astype(np.float64)
    pts = pixel_rays(uv, K) * d[:, None]
    return pts, ii * W + jj


def project(points_cam: np.ndarray, K: np.ndarray) -> np.ndarray:
    """Camera-frame points (N,3) -> pixel coords (N,2)."""
    p = np.asarray(points_cam, dtype=np.float64)
    depth = -p[:, 2]
    u = K[0, 0] * p[:, 0] / depth + K[0, 2]
    v = K[1, 1] * (-p[:, 1]) / depth + K[1, 2]
    return np.stack([u, v], 1)


def transform_points(T: np.ndarray, points: np.ndarray) -> np.ndarray:
    return points @ T[:3, :3].T + T[:3, 3]


# ----------------------------------------------------------------- planes

@dataclass
class Plane:
    """n . p + d = 0, |n| = 1.  Oriented so the camera origin is on the positive side (d > 0)."""
    n: np.ndarray
    d: float

    def signed_distance(self, points: np.ndarray) -> np.ndarray:
        return np.asarray(points) @ self.n + self.d

    def offset(self, h: float | np.ndarray) -> "Plane | list":
        """Plane shifted towards the camera by h (metres): points with height h above the floor."""
        return Plane(self.n, self.d - h)

    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Orthonormal in-plane axes (e1, e2) and the foot of the perpendicular from the origin."""
        n = self.n
        a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
        e1 = np.cross(n, a); e1 /= np.linalg.norm(e1)
        e2 = np.cross(n, e1)
        origin = -self.d * n
        return e1, e2, origin

    def to_2d(self, points: np.ndarray) -> np.ndarray:
        e1, e2, o = self.basis()
        q = np.asarray(points) - o
        return np.stack([q @ e1, q @ e2], 1)

    def from_2d(self, xy: np.ndarray, height: float | np.ndarray = 0.0) -> np.ndarray:
        e1, e2, o = self.basis()
        xy = np.asarray(xy, dtype=np.float64)
        h = np.asarray(height, dtype=np.float64)
        return o + xy[:, :1] * e1 + xy[:, 1:2] * e2 + (h[..., None] if h.ndim else h) * self.n


def intersect_rays_plane(rays: np.ndarray, plane: Plane) -> tuple[np.ndarray, np.ndarray]:
    """Rays from the camera origin -> intersection points and a validity mask (t > 0)."""
    denom = rays @ plane.n
    with np.errstate(divide="ignore", invalid="ignore"):
        t = -plane.d / denom
    ok = np.isfinite(t) & (t > 0)
    return rays * t[:, None], ok


# ----------------------------------------------------------------- masks & point selection

def mask_to_depth_res(mask: np.ndarray, depth_size: tuple[int, int], erode_px: int = 1) -> np.ndarray:
    """Full-res bool mask -> depth-res bool mask (area-averaged > 0.5, then eroded)."""
    m = cv2.resize(mask.astype(np.float32), depth_size, interpolation=cv2.INTER_AREA) > 0.5
    if erode_px > 0:
        k = np.ones((2 * erode_px + 1, 2 * erode_px + 1), np.uint8)
        m = cv2.erode(m.astype(np.uint8), k).astype(bool)
    return m


def valid_depth(depth: np.ndarray, confidence: np.ndarray | None, conf_min: int,
                dmin: float, dmax: float) -> np.ndarray:
    v = np.isfinite(depth) & (depth > dmin) & (depth < dmax)
    if confidence is not None and conf_min > 0:
        v &= confidence >= conf_min
    return v


def foot_depth_points(depth: np.ndarray, confidence: np.ndarray, K_rgb: np.ndarray,
                      rgb_size: tuple[int, int], mask_rgb: np.ndarray,
                      conf_min: int = 1, dmin: float = 0.15, dmax: float = 1.5, erode_px: int = 1
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """LiDAR points inside the (eroded) foot mask.  Returns (points_cam, flat_idx, mask_d)."""
    Hd, Wd = depth.shape
    Kd = scale_intrinsics(K_rgb, rgb_size, (Wd, Hd))
    md = mask_to_depth_res(mask_rgb, (Wd, Hd), erode_px)
    v = md & valid_depth(depth, confidence, conf_min, dmin, dmax)
    pts, idx = unproject(depth, Kd, v)
    return pts, idx, md


def background_depth_points(depth: np.ndarray, confidence: np.ndarray, K_rgb: np.ndarray,
                            rgb_size: tuple[int, int], mask_rgb: np.ndarray,
                            dilate_px: int = 5, conf_min: int = 2, dmin: float = 0.15, dmax: float = 2.0
                            ) -> np.ndarray:
    """High-confidence LiDAR points outside the dilated foot mask (floor candidates)."""
    Hd, Wd = depth.shape
    Kd = scale_intrinsics(K_rgb, rgb_size, (Wd, Hd))
    md = mask_to_depth_res(mask_rgb, (Wd, Hd), erode_px=0)
    k = np.ones((2 * dilate_px + 1, 2 * dilate_px + 1), np.uint8)
    far = ~cv2.dilate(md.astype(np.uint8), k).astype(bool)
    v = far & valid_depth(depth, confidence, conf_min, dmin, dmax)
    pts, _ = unproject(depth, Kd, v)
    return pts


# ----------------------------------------------------------------- io

def write_ply(path: str | Path, points: np.ndarray, colors: np.ndarray | None = None) -> None:
    pts = np.asarray(points, dtype=np.float32)
    n = len(pts)
    if colors is None:
        colors = np.full((n, 3), 200, np.uint8)
    with open(path, "wb") as f:
        f.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {n}\n"
                 "property float x\nproperty float y\nproperty float z\n"
                 "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n").encode())
        rec = np.empty(n, dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1")])
        rec["x"], rec["y"], rec["z"] = pts[:, 0], pts[:, 1], pts[:, 2]
        rec["r"], rec["g"], rec["b"] = colors[:, 0], colors[:, 1], colors[:, 2]
        f.write(rec.tobytes())
