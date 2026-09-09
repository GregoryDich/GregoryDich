import json
import warnings

import numpy as np
import pytest

from footmeasure.session import Session
from synth import Scene, write_session


@pytest.fixture(scope="module")
def session_dir(tmp_path_factory):
    scene = Scene(L=260, W=100, yaw_deg=20)
    frames = []
    for i in range(6):
        T = scene.camera(height_m=0.5, tilt_deg=5 * i)
        f = scene.render(T, rgb_size=(480, 360), depth_size=(64, 48), depth_blur_px=0)
        f["depth"][:] = 0.5 + 0.01 * i  # recognisable per-frame depth
        f["rgb"][:] = (10 * i + 30, 20, 200)  # recognisable per-frame colour
        frames.append(f)
    return write_session(tmp_path_factory.mktemp("sess") / "s1", frames, fps=30.0, orientation="portrait")


def test_load_and_pair_by_index(session_dir):
    s = Session.load(session_dir)
    assert s.n_frames == 6
    assert s.video_size == (480, 360)
    assert s.depth_size == (64, 48)
    assert s.orientation == "portrait"
    assert s.warnings == []
    got = list(s.iter_frames(step=2))
    assert [f.index for f in got] == [0, 2, 4]
    for f in got:
        assert f.rgb.shape == (360, 480, 3)
        assert f.depth.shape == (48, 64) and f.confidence.shape == (48, 64)
        assert np.allclose(f.depth, 0.5 + 0.01 * f.index, atol=1e-6)
        # lossy codec: colour approximately preserved, and it is RGB (red channel small, blue large)
        mean = f.rgb.reshape(-1, 3).mean(0)
        assert abs(mean[0] - (10 * f.index + 30)) < 12 and mean[2] > 150
        assert f.K.shape == (3, 3) and f.K[2, 2] == 1.0
        assert f.T_world_cam.shape == (4, 4) and np.allclose(f.T_world_cam[3], [0, 0, 0, 1])
        assert abs(f.t - f.index / 30.0) < 1e-9


def test_indices_and_single_frame(session_dir):
    s = Session.load(session_dir)
    got = [f.index for f in s.iter_frames(indices=[1, 5])]
    assert got == [1, 5]
    f = s.frame(3)
    assert f.index == 3 and np.allclose(f.depth, 0.53, atol=1e-6)
    assert [f.index for f in s.iter_frames(step=1, max_frames=2)] == [0, 1]


def test_zip_roundtrip(session_dir, tmp_path):
    import shutil
    z = shutil.make_archive(str(tmp_path / "upload"), "zip", root_dir=session_dir.parent, base_dir=session_dir.name)
    s = Session.load(z)
    assert s.n_frames == 6
    assert s.path.name == session_dir.name


def test_truncated_depth_is_trimmed_with_warning(session_dir, tmp_path):
    import shutil
    d = tmp_path / "trunc"
    shutil.copytree(session_dir, d)
    raw = (d / "depth.bin").read_bytes()
    per = 64 * 48 * 4
    (d / "depth.bin").write_bytes(raw[: per * 4])  # keep 4 of 6 frames
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        s = Session.load(d)
    assert s.n_frames == 4
    assert any("mismatch" in str(x.message) for x in w)


def test_legacy_nested_matrices(session_dir, tmp_path):
    import shutil
    d = tmp_path / "legacy"
    shutil.copytree(session_dir, d)
    meta = json.loads((d / "metadata.json").read_text())
    for fr in meta["frames"]:
        K = [[fr.pop("fx"), 0, fr.pop("cx")], [0, fr.pop("fy"), fr.pop("cy")], [0, 0, 1]]
        fr["intrinsics"] = K
        fr["transform"] = np.array(fr.pop("transform_row_major")).reshape(4, 4).tolist()
    (d / "metadata.json").write_text(json.dumps(meta))
    s = Session.load(d)
    assert s.frames[0].K[0, 2] == pytest.approx((480 - 1) / 2)
