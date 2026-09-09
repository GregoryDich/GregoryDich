import numpy as np
import pytest

from footmeasure.geometry import (Plane, intersect_rays_plane, pixel_rays, project, scale_intrinsics,
                                  unproject, rgb_to_depth_coords, depth_to_rgb_coords, mask_to_depth_res)
from synth import intrinsics


def test_unproject_project_roundtrip():
    K = intrinsics(1920, 1440)
    Kd = scale_intrinsics(K, (1920, 1440), (256, 192))
    rng = np.random.default_rng(0)
    depth = rng.uniform(0.3, 1.0, (192, 256)).astype(np.float32)
    pts, idx = unproject(depth, Kd)
    assert pts.shape == (192 * 256, 3)
    assert np.all(pts[:, 2] < 0)                       # in front of the camera: z negative
    assert np.allclose(-pts[:, 2], depth.ravel(), atol=1e-6)
    uv = project(pts, Kd)
    ii, jj = np.divmod(idx, 256)
    assert np.allclose(uv[:, 0], jj, atol=1e-6) and np.allclose(uv[:, 1], ii, atol=1e-6)


def test_pixel_centre_scaling_gives_same_ray():
    """RGB pixel and the corresponding depth pixel must be the same ray."""
    K = intrinsics(1920, 1440)
    Kd = scale_intrinsics(K, (1920, 1440), (256, 192))
    rng = np.random.default_rng(1)
    uv = rng.uniform(0, [1919, 1439], (500, 2))
    jd = rgb_to_depth_coords(uv, (1920, 1440), (256, 192))
    assert np.allclose(depth_to_rgb_coords(jd, (1920, 1440), (256, 192)), uv)
    r1 = pixel_rays(uv, K)
    r2 = pixel_rays(jd, Kd)
    assert np.allclose(r1, r2, atol=1e-9)
    # corner conventions: RGB pixel centre 0 maps to depth pixel centre -0.5 + 0.5*s
    assert np.allclose(rgb_to_depth_coords(np.array([[0.0, 0.0]]), (1920, 1440), (256, 192)),
                       [[0.5 * 256 / 1920 - 0.5, 0.5 * 192 / 1440 - 0.5]])


def test_ray_plane_intersection_and_2d_basis():
    K = intrinsics(1920, 1440)
    n = np.array([0.1, 0.2, 1.0]); n /= np.linalg.norm(n)
    plane = Plane(n, 0.6)          # camera at height 0.6 m on the positive side
    uv = np.array([[960.0, 720.0], [100.0, 50.0], [1800.0, 1400.0]])
    pts, ok = intersect_rays_plane(pixel_rays(uv, K), plane)
    assert ok.all()
    assert np.allclose(plane.signed_distance(pts), 0, atol=1e-9)
    assert np.allclose(project(pts, K), uv, atol=1e-6)
    xy = plane.to_2d(pts)
    back = plane.from_2d(xy, 0.0)
    assert np.allclose(back, pts, atol=1e-9)
    lifted = plane.from_2d(xy, 0.025)
    assert np.allclose(plane.signed_distance(lifted), 0.025)
    # in-plane distances are preserved
    d3 = np.linalg.norm(pts[0] - pts[1]); d2 = np.linalg.norm(xy[0] - xy[1])
    assert d3 == pytest.approx(d2, abs=1e-9)


def test_mask_to_depth_res_erodes():
    m = np.zeros((1440, 1920), bool)
    m[400:1000, 500:1300] = True
    md = mask_to_depth_res(m, (256, 192), erode_px=0)
    assert md.sum() == pytest.approx((600 / 7.5) * (800 / 7.5), rel=0.03)
    md1 = mask_to_depth_res(m, (256, 192), erode_px=1)
    assert md1.sum() < md.sum()
