"""End-to-end synthetic check of the measurement geometry (no neural network involved).

TRUE_L / TRUE_W are the dimensions of the synthetic foot model that tests/synth.py renders.
The pipeline never receives them: it only gets video/depth/intrinsics and has to *recover*
them; the asserts compare what it computed with what was rendered.
"""
import numpy as np
import pytest

from footmeasure.measure import measure_frame, mask_from_polygon, measure_outline_ab, polygon_section_widths
from synth import Scene, foot_outline, project_arkit, scene_points_to_camera

TRUE_L, TRUE_W = 260.0, 100.0   # generator parameters, not pipeline inputs


def test_outline_slicing_exact_on_known_polygon():
    poly = foot_outline(TRUE_L, TRUE_W)
    res = measure_outline_ab(poly)
    assert res["length"] == pytest.approx(TRUE_L, abs=1e-9)
    assert res["width"] == pytest.approx(TRUE_W, abs=0.05)
    assert res["width_at"] == pytest.approx(0.70 * TRUE_L, abs=0.5)
    # a rotated copy measures the same after PCA alignment inside measure_frame; here just rotate & slice
    th = np.radians(37)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    from footmeasure.measure import pca_axis, align_to_axis
    ab, _ = align_to_axis(poly @ R.T, pca_axis(poly @ R.T))
    res2 = measure_outline_ab(ab)
    assert res2["length"] == pytest.approx(TRUE_L, abs=0.5)
    assert res2["width"] == pytest.approx(TRUE_W, abs=0.5)
    assert res2["toe"][0] > res2["heel"][0]


@pytest.mark.parametrize("tilt,yaw,tol", [(0, 0, 3.0), (0, 40, 3.0), (15, -25, 3.0), (25, 70, 4.0)])
def test_contour_method_recovers_length_width(tilt, yaw, tol):
    scene = Scene(L=TRUE_L, W=TRUE_W, H=25, yaw_deg=yaw)
    T = scene.camera(height_m=0.5, tilt_deg=tilt, azimuth_deg=30)
    f = scene.render(T, rgb_size=(1920, 1440), depth_size=(256, 192), depth_blur_px=1.5, depth_noise_mm=1.0)
    m = measure_frame(f["depth"], f["confidence"], f["K"], (1920, 1440), f["mask"], T, method="contour")
    assert m.length_mm == pytest.approx(TRUE_L, abs=tol), m.as_dict()
    assert m.width_mm == pytest.approx(TRUE_W, abs=tol), m.as_dict()
    assert m.n_points > 500
    assert m.plane_rms_mm < 3.0
    assert m.width_at_mm == pytest.approx(0.70 * TRUE_L, abs=8.0)   # toe end is +a
    assert 5.0 < m.foot_height_mm < 25.0
    assert m.contour_3d is not None and len(m.contour_3d) > 20   # approxPolyDP simplifies smooth outlines
    # drawing endpoints project inside the image and are ~L apart in 3D
    assert np.linalg.norm(m.toe_3d - m.heel_3d) * 1000 == pytest.approx(TRUE_L, abs=tol + 1)
    assert np.linalg.norm(m.width_right_3d - m.width_left_3d) * 1000 == pytest.approx(TRUE_W, abs=tol + 1)


def test_depth_method_is_biased_low_but_sane():
    scene = Scene(L=TRUE_L, W=TRUE_W, H=25, yaw_deg=15)
    T = scene.camera(height_m=0.5, tilt_deg=10)
    f = scene.render(T, rgb_size=(1920, 1440), depth_size=(256, 192), depth_blur_px=1.5)
    m = measure_frame(f["depth"], f["confidence"], f["K"], (1920, 1440), f["mask"], T, method="depth")
    # Documented bias of the pure LiDAR-point path: mask erosion (1 depth px ~ 2.6 mm/side),
    # h_min, depth-edge blur and 1/99 percentile trimming of the rounded caps all shave the extent.
    assert TRUE_L - 35 < m.length_mm < TRUE_L + 1
    assert TRUE_W - 25 < m.width_mm < TRUE_W + 1


def test_a4_sheet_polygon_mode():
    """Flat 297x210 sheet on the floor, mask given as 4 pixel corners (no neural net)."""
    class Sheet(Scene):
        def __init__(self):
            self.L, self.W, self.H = 297.0, 210.0, 0.2
            self.R = np.eye(3); self.t = np.zeros(3)
            xs = np.arange(0, 297.01, 0.5); ys = np.arange(-105, 105.01, 0.5)
            X, Y = np.meshgrid(xs, ys)
            self.surface_mm = np.stack([X.ravel(), Y.ravel(), np.full(X.size, 0.2)], 1)
            self.surface_world = self.surface_mm - [148.5, 0, 0]
    sheet = Sheet()
    T = sheet.camera(height_m=0.55, tilt_deg=15, azimuth_deg=200)
    f = sheet.render(T, rgb_size=(1920, 1440), depth_size=(256, 192), depth_blur_px=1.5)
    corners_w = np.array([[-148.5, -105, 0.2], [148.5, -105, 0.2], [148.5, 105, 0.2], [-148.5, 105, 0.2]])
    uv, _ = project_arkit(scene_points_to_camera(sheet, T, corners_w), f["K"])
    mask = mask_from_polygon(uv, (1920, 1440))
    m = measure_frame(f["depth"], f["confidence"], f["K"], (1920, 1440), mask, T, method="contour", fixed_height_m=0.0002)
    assert m.length_mm == pytest.approx(297.0, abs=1.5)
    assert m.width_mm == pytest.approx(210.0, abs=1.5)
