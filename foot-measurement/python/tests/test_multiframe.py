import json

import cv2
import numpy as np
import pytest

from footmeasure import cli
from footmeasure.debug_image import render_debug
from footmeasure.detector import ColorMockDetector, FootDetection
from footmeasure.multiframe import aggregate, fuse_clouds, process_session
from footmeasure.session import Session
from synth import Scene, write_session

L, W = 262.0, 98.0


@pytest.fixture(scope="module")
def session_dir(tmp_path_factory):
    scene = Scene(L=L, W=W, H=24, yaw_deg=-30)
    frames = []
    for i in range(10):
        T = scene.camera(height_m=0.48 + 0.01 * i, tilt_deg=2 * i, azimuth_deg=20 * i)
        f = scene.render(T, rgb_size=(1920, 1440), depth_size=(256, 192), seed=i)
        if i == 4:   # one bad frame: no foot painted -> "no detection"
            f["rgb"][:] = 128
        frames.append(f)
    return write_session(tmp_path_factory.mktemp("mf") / "s", frames, orientation="portrait")


class FlakyDetector(ColorMockDetector):
    """Mock with a low-confidence frame to exercise gating."""

    def detect(self, rgb, orientation=None):
        d = super().detect(rgb, orientation)
        if d is None:
            return None
        conf = 0.1 if abs(int(rgb[0, 0, 0]) - 128) > 5 and rgb[..., 0].mean() > 150 else 0.9
        return FootDetection(d.mask, conf, d.bbox, 1, "foot", False)


def test_process_session_median_and_gating(session_dir):
    s = Session.load(session_dir)
    res = process_session(s, ColorMockDetector(), step=1, top_k=5, log=None)
    sm = res.summary
    assert sm["frames_processed"] == 10
    assert sm["valid_frames"] == 9 and sm["frames_used"] == 5
    assert sm["length_mm"] == pytest.approx(L, abs=3.0)
    assert sm["width_mm"] == pytest.approx(W, abs=3.0)
    assert sm["length_iqr_mm"] < 3.0
    rejected = [p for p in sm["per_frame"] if p["rejected_reason"]]
    assert len(rejected) == 1 and rejected[0]["index"] == 4 and "no detection" in rejected[0]["rejected_reason"]
    assert res.best is not None and res.best.accepted
    cloud = fuse_clouds(res.used)
    assert cloud.shape[1] == 3 and len(cloud) > 100
    # fused contours from different camera poses land on the same floor (world y ~ 0) and inside the foot box
    assert np.abs(cloud[:, 1]).max() < 0.03
    assert np.ptp(cloud[:, 0]) < 0.30 and np.ptp(cloud[:, 2]) < 0.30


def test_gate_rejects_low_confidence():
    from footmeasure.multiframe import FrameResult, gate
    from footmeasure.measure import Measurement
    from footmeasure.geometry import Plane

    def mk(n_points=1000, inl=5000, rms=1.0, up=0.5):
        z = np.zeros(3)
        return Measurement(260, 100, "contour", Plane(np.array([0, 0, 1.0]), 0.5), z, z, z, z, z, z, n_points,
                           15.0, rms, inl, up, 1.0, 180.0, np.zeros((3, 2)))

    assert gate(mk(), 0.9, 0.3, 500, 2000, 6.0) is None
    assert "confidence" in gate(mk(), 0.1, 0.3, 500, 2000, 6.0)
    assert "LiDAR" in gate(mk(n_points=10), 0.9, 0.3, 500, 2000, 6.0)
    assert "inliers" in gate(mk(inl=10), 0.9, 0.3, 500, 2000, 6.0)
    assert "rms" in gate(mk(rms=9), 0.9, 0.3, 500, 2000, 6.0)
    assert "gravity" in gate(mk(up=40), 0.9, 0.3, 500, 2000, 6.0)
    r = FrameResult(0, 0.0, 0.9, mk(), None, np.eye(4))
    summary, used = aggregate([r, r, r], top_k=2)
    assert summary["frames_used"] == 2 and summary["length_mm"] == 260


def test_cli_process_writes_result_and_debug_image(session_dir, tmp_path):
    out = tmp_path / "out"
    rc = cli.main(["process", str(session_dir), "--mock-detector", "--step", "2", "--out", str(out), "--rotate"])
    assert rc == 0
    res = json.loads((out / "result.json").read_text())
    assert res["length_mm"] == pytest.approx(L, abs=3.0) and res["width_mm"] == pytest.approx(W, abs=3.0)
    img = cv2.imread(str(out / "debug.png"))
    assert img is not None and img.shape[0] == 1920 and img.shape[1] > 1440   # rotated upright + top-down panel


def test_cli_measure_visualize_points(session_dir, tmp_path):
    out = tmp_path / "o"
    assert cli.main(["visualize", str(session_dir), "--step", "5", "--out", str(out)]) == 0
    assert (out / "frame_00000.png").exists() and (out / "frame_00005.png").exists()
    assert cli.main(["measure", str(session_dir), "--mock-detector", "--frame", "2", "--out", str(out)]) == 0
    assert (out / "measure_00002.png").exists()
    assert cli.main(["measure", str(session_dir), "--mock-detector", "--frame", "2", "--method", "depth", "--out", str(out)]) == 0
    assert cli.main(["points", str(session_dir), "--mock-detector", "--frame", "2", "--out", str(out)]) == 0
    assert (out / "points_00002.ply").stat().st_size > 1000
    assert cli.main(["detect", str(session_dir), "--mock-detector", "--step", "5", "--out", str(out)]) == 0
    # A4-style polygon mask instead of the detector: corners of the painted foot's bbox act as the polygon
    s = Session.load(session_dir)
    f = s.frame(2)
    ys, xs = np.nonzero(ColorMockDetector().detect(f.rgb).mask)
    poly = tmp_path / "poly.json"
    poly.write_text(json.dumps([[int(xs.min()), int(ys.min())], [int(xs.max()), int(ys.min())],
                                [int(xs.max()), int(ys.max())], [int(xs.min()), int(ys.max())]]))
    assert cli.main(["measure", str(session_dir), "--frame", "2", "--mask-polygon", str(poly),
                     "--fixed-height-mm", "0", "--out", str(out)]) == 0


def test_render_debug_shapes(session_dir):
    s = Session.load(session_dir)
    f = s.frame(1)
    from footmeasure.measure import measure_frame
    det = ColorMockDetector().detect(f.rgb)
    m = measure_frame(f.depth, f.confidence, f.K, (1920, 1440), det.mask, f.T_world_cam)
    img = render_debug(f.rgb, det.mask, m, f.K, 0.9, f.orientation, rotate=False, title="t")
    assert img.shape[0] == 1440 and img.shape[1] > 1920
