"""Synthetic data for unit tests ONLY (real iPhone recordings are the source of truth).

Builds a rounded, extruded foot-shaped solid of known length / max width on a
floor plane, renders it with a pinhole camera in ARKit conventions
(camera x right, y up, z backwards; depth = -z), and can write a complete
measurement session directory in the iOS app's format.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

# --------------------------------------------------------------------- shape


def foot_half_width(x: np.ndarray, L: float, W: float) -> np.ndarray:
    """Half-width profile (mm) along the foot axis x in [0, L]; max width exactly W at x=0.70L."""
    rh, rt = 0.30 * W, 0.35 * W
    xs = np.array([0.0, rh, 0.45 * L, 0.70 * L, 0.85 * L, L - rt, L])
    hw = np.array([0.0, rh, 0.42 * W, 0.50 * W, 0.45 * W, rt, 0.0])
    h = np.interp(x, xs, hw)
    # round the two caps with quarter circles
    heel = x < rh
    h[heel] = np.sqrt(np.clip(rh ** 2 - (x[heel] - rh) ** 2, 0, None))
    toe = x > L - rt
    h[toe] = np.sqrt(np.clip(rt ** 2 - (x[toe] - (L - rt)) ** 2, 0, None))
    return h


def foot_outline(L: float = 260.0, W: float = 100.0, n: int = 400) -> np.ndarray:
    """Closed polygon (n*2, 2) of the footprint in the foot frame, mm. x: heel(0)->toe(L)."""
    x = np.linspace(0, L, n)
    h = foot_half_width(x, L, W)
    top = np.stack([x, h], 1)
    bot = np.stack([x[::-1], -h[::-1]], 1)
    return np.vstack([top, bot])


def foot_surface(L: float = 260.0, W: float = 100.0, H: float = 25.0,
                 dx: float = 0.5, n_phi: int = 90) -> np.ndarray:
    """Surface points (N, 3) of the solid with half-elliptic cross-sections of height H.

    For each x, the cross-section is y = hw(x) cos(phi), z = H(x) sin(phi), phi in [0, pi],
    so the widest point of every section is at floor level (z = 0), like a foot pad.
    """
    x = np.arange(0, L + dx / 2, dx)
    hw = foot_half_width(x, L, W)
    hz = H * np.clip(hw / (0.5 * W), 0.15, 1.0)  # thinner at the caps
    phi = np.linspace(0, np.pi, n_phi)
    X = np.repeat(x, n_phi)
    Y = (hw[:, None] * np.cos(phi)[None, :]).ravel()
    Z = (hz[:, None] * np.sin(phi)[None, :]).ravel()
    return np.stack([X, Y, Z], 1)


# --------------------------------------------------------------------- camera


def rotation_z(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def look_at_arkit(cam_pos: np.ndarray, target: np.ndarray, up_hint: np.ndarray) -> np.ndarray:
    """Camera-to-world 4x4 with ARKit axes: x right, y up, z backwards (looking down -z)."""
    fwd = target - cam_pos
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, up_hint)
    if np.linalg.norm(right) < 1e-6:  # looking straight along up_hint: pick another hint
        right = np.cross(fwd, np.array([0.0, 1.0, 0.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2] = right, up, -fwd
    T[:3, 3] = cam_pos
    return T


def intrinsics(W: int, H: int, fx: float | None = None) -> np.ndarray:
    fx = fx if fx is not None else 0.76 * W   # ~1460 px for 1920 wide, iPhone-like
    return np.array([[fx, 0, (W - 1) / 2.0], [0, fx, (H - 1) / 2.0], [0, 0, 1.0]])


def project_arkit(p_cam: np.ndarray, K: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """ARKit camera space -> pixels (u right, v down); returns (uv, depth)."""
    z = -p_cam[:, 2]
    u = K[0, 0] * p_cam[:, 0] / z + K[0, 2]
    v = K[1, 1] * (-p_cam[:, 1]) / z + K[1, 2]
    return np.stack([u, v], 1), z


# --------------------------------------------------------------------- scene


class Scene:
    """World frame: floor is z=0 (world), 'up' is +z. The foot lies on the floor."""

    def __init__(self, L=260.0, W=100.0, H=25.0, yaw_deg=0.0, foot_xy=(0.0, 0.0)):
        self.L, self.W, self.H = L, W, H
        self.R = rotation_z(np.radians(yaw_deg))
        self.t = np.array([foot_xy[0], foot_xy[1], 0.0])
        self.surface_mm = foot_surface(L, W, H)
        self.surface_world = (self.surface_mm - [L / 2, 0, 0]) @ self.R.T + self.t  # centred

    # Internal scene frame is z-up (mm).  ARKit's world frame is y-up (metres):
    # returned transforms are converted with M (z-up -> y-up) so that the
    # pipeline's gravity check (world +y) works like on the device.
    M = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])

    def camera(self, height_m=0.5, tilt_deg=0.0, azimuth_deg=90.0) -> np.ndarray:
        """ARKit-style camera-to-world (metres, world y-up) above the foot centre, tilted from vertical."""
        h = height_m * 1000.0
        d = h * np.tan(np.radians(tilt_deg))
        az = np.radians(azimuth_deg)
        pos = self.t + np.array([d * np.cos(az), d * np.sin(az), h])
        T = look_at_arkit(pos, self.t, np.array([0, 0, 1.0]))
        T[:3, 3] /= 1000.0
        M4 = np.eye(4); M4[:3, :3] = self.M
        return M4 @ T

    def _to_scene_frame(self, T_world_cam: np.ndarray) -> np.ndarray:
        M4 = np.eye(4); M4[:3, :3] = self.M.T
        return M4 @ T_world_cam

    def render(self, T_world_cam: np.ndarray, rgb_size=(960, 720), depth_size=(256, 192),
               depth_blur_px: float = 1.5, depth_noise_mm: float = 1.0, seed: int = 0):
        """Returns dict with mask (bool, rgb res), rgb (uint8), depth (m, depth res), conf, K."""
        rng = np.random.default_rng(seed)
        W, H = rgb_size
        Wd, Hd = depth_size
        K = intrinsics(W, H)
        s = Wd / W
        Kd = K.copy()
        Kd[0, 0] *= s; Kd[1, 1] *= s
        Kd[0, 2] = (K[0, 2] + 0.5) * s - 0.5
        Kd[1, 2] = (K[1, 2] + 0.5) * s - 0.5

        T_world_cam = self._to_scene_frame(T_world_cam)   # z-up, metres
        T_cam_world = np.linalg.inv(T_world_cam)
        pw = self.surface_world / 1000.0
        pc = pw @ T_cam_world[:3, :3].T + T_cam_world[:3, 3]

        # --- RGB-resolution mask: splat surface points, close small gaps
        uv, z = project_arkit(pc, K)
        mask = np.zeros((H, W), np.uint8)
        ui, vi = np.round(uv[:, 0]).astype(int), np.round(uv[:, 1]).astype(int)
        ok = (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
        mask[vi[ok], ui[ok]] = 1
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        mask = mask.astype(bool)

        # --- depth-resolution z-buffer: floor everywhere, foot where nearer
        jj, ii = np.meshgrid(np.arange(Wd), np.arange(Hd))
        rays = np.stack([(jj - Kd[0, 2]) / Kd[0, 0], -(ii - Kd[1, 2]) / Kd[1, 1], -np.ones_like(jj, float)], -1)
        rays_w = rays.reshape(-1, 3) @ T_world_cam[:3, :3].T
        cam_w = T_world_cam[:3, 3]
        # floor plane z_world = 0: cam_w.z + t * ray.z = 0
        t_floor = -cam_w[2] / rays_w[:, 2]
        depth = t_floor.reshape(Hd, Wd).astype(np.float32)  # ray param == -z_cam since ray z=-1
        uvd, zd = project_arkit(pc, Kd)
        ud, vd = np.round(uvd[:, 0]).astype(int), np.round(uvd[:, 1]).astype(int)
        okd = (ud >= 0) & (ud < Wd) & (vd >= 0) & (vd < Hd)
        foot_z = np.full((Hd, Wd), np.inf, np.float32)
        np.minimum.at(foot_z, (vd[okd], ud[okd]), zd[okd].astype(np.float32))
        near = foot_z < depth
        depth[near] = foot_z[near]
        if depth_blur_px > 0:
            depth = cv2.GaussianBlur(depth, (0, 0), depth_blur_px)
        depth += rng.normal(0, depth_noise_mm / 1000.0, depth.shape).astype(np.float32)
        conf = np.full((Hd, Wd), 2, np.uint8)

        rgb = np.full((H, W, 3), (140, 140, 140), np.uint8)
        rgb[mask] = (214, 170, 140)  # skin-ish
        M4 = np.eye(4); M4[:3, :3] = self.M
        return dict(mask=mask, rgb=rgb, depth=depth, confidence=conf, K=K, Kd=Kd, T_world_cam=M4 @ T_world_cam)


# --------------------------------------------------------------------- session writer


def write_session(out_dir: Path, frames: list[dict], fps: float = 30.0,
                  orientation: str = "landscapeRight", codec: str = "mp4v") -> Path:
    """Write video.mov / depth.bin / confidence.bin / metadata.json like the iOS app."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    H, W = frames[0]["rgb"].shape[:2]
    Hd, Wd = frames[0]["depth"].shape
    vw = cv2.VideoWriter(str(out_dir / "video.mov"), cv2.VideoWriter_fourcc(*codec), fps, (W, H))
    assert vw.isOpened()
    metas = []
    with open(out_dir / "depth.bin", "wb") as fd, open(out_dir / "confidence.bin", "wb") as fc:
        for i, f in enumerate(frames):
            vw.write(cv2.cvtColor(f["rgb"], cv2.COLOR_RGB2BGR))
            fd.write(np.ascontiguousarray(f["depth"], dtype="<f4").tobytes())
            fc.write(np.ascontiguousarray(f["confidence"], dtype="u1").tobytes())
            K, T = f["K"], f["T_world_cam"]
            metas.append(dict(index=i, t=i / fps, timestamp=1000.0 + i / fps,
                              fx=float(K[0, 0]), fy=float(K[1, 1]), cx=float(K[0, 2]), cy=float(K[1, 2]),
                              transform_row_major=[float(v) for v in np.asarray(T).reshape(-1)],
                              exposure_duration=0.008))
    vw.release()
    meta = dict(device="synthetic", ios="0", interface_orientation=orientation,
                video=dict(path="video.mov", width=W, height=H, fps=fps, codec=codec),
                depth=dict(width=Wd, height=Hd, dtype="float32", unit="m"),
                frames=metas)
    (out_dir / "metadata.json").write_text(json.dumps(meta))
    return out_dir


def scene_points_to_camera(scene: Scene, T_world_cam: np.ndarray, points_mm_world: np.ndarray) -> np.ndarray:
    """Scene-frame (z-up, mm) world points -> ARKit camera frame (metres)."""
    Tz = scene._to_scene_frame(T_world_cam)
    Tcw = np.linalg.inv(Tz)
    return (points_mm_world / 1000.0) @ Tcw[:3, :3].T + Tcw[:3, 3]
