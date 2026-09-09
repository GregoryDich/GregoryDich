import numpy as np
import pytest

from footmeasure.floor import estimate_floor, fit_plane_ransac
from footmeasure.geometry import Plane
from synth import Scene, scene_points_to_camera


def test_ransac_recovers_plane_with_outliers():
    rng = np.random.default_rng(3)
    n = np.array([0.05, -0.1, 1.0]); n /= np.linalg.norm(n)
    plane = Plane(n, 0.55)
    e1, e2, o = plane.basis()
    xy = rng.uniform(-0.4, 0.4, (3000, 2))
    inl = o + xy[:, :1] * e1 + xy[:, 1:] * e2 + rng.normal(0, 0.001, (3000, 1)) * n
    out = rng.uniform(-0.5, 0.5, (1300, 3)) + [0, 0, -0.6]
    pts = np.vstack([inl, out])
    fit, mask = fit_plane_ransac(pts, thresh=0.005, seed=1)
    assert np.degrees(np.arccos(abs(fit.n @ n))) < 0.3
    assert fit.d == pytest.approx(0.55, abs=0.001)
    assert fit.d > 0
    assert mask[:3000].mean() > 0.98
    rms = np.sqrt(np.mean(fit.signed_distance(inl) ** 2))
    assert rms < 0.0015


def test_estimate_floor_on_synthetic_scene():
    scene = Scene(L=260, W=100, yaw_deg=30)
    T = scene.camera(height_m=0.5, tilt_deg=25)
    f = scene.render(T, rgb_size=(1920, 1440), depth_size=(256, 192))
    res = estimate_floor(f["depth"], f["confidence"], f["K"], (1920, 1440), f["mask"], T)
    assert res.rms_mm < 3.0
    assert res.normal_vs_up_deg is not None and res.normal_vs_up_deg < 1.0
    assert res.warnings == []
    # camera height above the floor is 0.5 m
    assert res.plane.d == pytest.approx(0.5, abs=0.003)
    # foot points must be on the positive side (towards the camera)
    top = scene_points_to_camera(scene, T, scene.surface_world[scene.surface_world[:, 2] > 20])
    assert (res.plane.signed_distance(top) > 0.015).mean() > 0.95
