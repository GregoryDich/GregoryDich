"""FootDetector logic without torch/rfdetr: class selection, two-pass paste-back, orientation handling."""
import numpy as np
import pytest

from footmeasure.detector import ColorMockDetector, FootDetector
from footmeasure.util import rotate_to_upright
from synth import Scene


class FakeDetections:
    """Mimics supervision.Detections as returned by rfdetr predict()."""

    def __init__(self, masks, confs, class_ids, names):
        self.mask = np.asarray(masks, dtype=bool)
        self.confidence = np.asarray(confs, dtype=float)
        self.class_id = np.asarray(class_ids)
        self.xyxy = np.array([_bbox(m) for m in self.mask], dtype=float).reshape(-1, 4)
        self.data = {"class_name": np.asarray(names)}

    def __len__(self):
        return len(self.confidence)


def _bbox(m):
    ys, xs = np.nonzero(m)
    return [xs.min(), ys.min(), xs.max() + 1, ys.max() + 1] if len(xs) else [0, 0, 0, 0]


def _skin(img):
    r, g, b = img[..., 0].astype(int), img[..., 1].astype(int), img[..., 2].astype(int)
    return (r > g + 20) & (g > b + 10)


@pytest.fixture
def scene_frame():
    scene = Scene(L=260, W=100, yaw_deg=35)
    T = scene.camera(0.5, 10)
    return scene.render(T, rgb_size=(960, 720), depth_size=(128, 96))


def _detector_with_fake_model(monkeypatch, predict_fn, **kw):
    d = FootDetector(weights="weights/fake.pth", class_name="foot", **kw)
    monkeypatch.setattr(d, "_predict_raw", predict_fn)
    d._class_names = {0: "feet", 1: "foot"}
    return d


def test_two_pass_crop_pasted_back_and_rotated_to_sensor_frame(monkeypatch, scene_frame):
    calls = []

    def predict(img):  # a fake model that works on whatever crop it receives
        calls.append(img.shape)
        m = _skin(img)
        return FakeDetections([m], [0.8 if len(calls) == 1 else 0.95], [1], ["foot"])

    d = _detector_with_fake_model(monkeypatch, predict)
    det = d.detect(scene_frame["rgb"], orientation="portrait")
    assert det is not None and det.two_pass
    assert len(calls) == 2 and calls[1][0] < calls[0][0]      # second call is a crop
    assert calls[0][:2] == (960, 720)                            # first call saw the upright (rotated) frame
    gt = scene_frame["mask"]
    iou = (det.mask & gt).sum() / (det.mask | gt).sum()
    assert det.mask.shape == gt.shape and iou > 0.98              # back in the sensor frame
    assert det.confidence == pytest.approx(0.95)
    assert det.class_name == "foot"


def test_class_selection_prefers_named_class_then_confidence(monkeypatch, scene_frame):
    m = _skin(scene_frame["rgb"])
    other = np.zeros_like(m); other[10:60, 10:60] = True
    dets = FakeDetections([other, m, m], [0.99, 0.6, 0.7], [0, 1, 1], ["feet", "foot", "foot"])
    d = _detector_with_fake_model(monkeypatch, lambda img: dets, two_pass=False)
    assert d._select(dets) == 2
    det = d.detect(scene_frame["rgb"])
    assert det.confidence == pytest.approx(0.7) and not det.two_pass


def test_missing_class_falls_back_with_warning(monkeypatch, scene_frame):
    m = _skin(scene_frame["rgb"])
    dets = FakeDetections([m], [0.5], [7], ["person"])
    d = _detector_with_fake_model(monkeypatch, lambda img: dets, two_pass=False)
    with pytest.warns(UserWarning, match="not among model classes"):
        det = d.detect(scene_frame["rgb"])
    assert det is not None and det.class_name == "person"


def test_no_detection_returns_none(monkeypatch, scene_frame):
    d = _detector_with_fake_model(monkeypatch, lambda img: FakeDetections(np.zeros((0, 720, 960)), [], [], []))
    assert d.detect(scene_frame["rgb"]) is None


def test_mock_detector_matches_synthetic_mask(scene_frame):
    det = ColorMockDetector().detect(scene_frame["rgb"])
    gt = scene_frame["mask"]
    assert (det.mask & gt).sum() / (det.mask | gt).sum() > 0.99
