import json
import shutil

import pytest

pytest.importorskip("httpx")
pytest.importorskip("multipart")  # python-multipart, needed for form-data endpoints
from fastapi.testclient import TestClient  # noqa: E402

from footmeasure import server  # noqa: E402
from synth import Scene, write_session  # noqa: E402

TRUE_L, TRUE_W = 255.0, 96.0   # synthetic generator parameters, never seen by the server


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("srv")
    scene = Scene(L=TRUE_L, W=TRUE_W, yaw_deg=10)
    frames = [scene.render(scene.camera(0.5, 4 * i, 30 * i), (960, 720), (128, 96), seed=i) for i in range(4)]
    sdir = write_session(tmp / "s", frames, orientation="portrait")
    z = shutil.make_archive(str(tmp / "s"), "zip", root_dir=sdir.parent, base_dir=sdir.name)
    return sdir, z


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "SESSIONS_DIR", tmp_path / "srv")
    monkeypatch.delenv("FOOTMEASURE_MOCK", raising=False)
    monkeypatch.setenv("FOOTMEASURE_STEP", "1")
    server._detectors.clear()
    return TestClient(server.app)


def _check_measurement(body):
    assert body["length_mm"] == pytest.approx(TRUE_L, abs=4) and body["width_mm"] == pytest.approx(TRUE_W, abs=4)
    assert body["valid_frames"] >= 3 and body["session_id"] and body["result_json"] and body["debug_image"]


def test_raw_zip_body_like_iphone(client, synthetic, monkeypatch):
    _, z = synthetic
    monkeypatch.setenv("FOOTMEASURE_MOCK", "1")
    assert client.get("/health").json()["ok"] is True
    r = client.post("/sessions", content=open(z, "rb").read(), headers={"Content-Type": "application/zip"})
    assert r.status_code == 200, r.text
    body = r.json()
    _check_measurement(body)
    png = client.get(body["debug_image"])
    assert png.status_code == 200 and png.content[:4] == b"\x89PNG"
    assert client.get(body["result_json"]).json()["frames_processed"] == 4
    assert client.post("/sessions", content=b"").status_code == 400
    assert client.post("/sessions?method=bogus", content=b"x").status_code == 400
    listed = client.get("/sessions").json()["sessions"]
    assert [s["session_id"] for s in listed] == [body["session_id"]]


def test_multipart_zip_upload(client, synthetic):
    _, z = synthetic
    with open(z, "rb") as f:
        r = client.post("/sessions/upload", files={"zip": ("s.zip", f, "application/zip")},
                        data={"step": "1", "method": "contour", "mock": "true"})
    assert r.status_code == 200, r.text
    _check_measurement(r.json())
    assert r.json()["bytes_received"]["zip"] > 1000


def test_multipart_four_files_upload(client, synthetic):
    sdir, _ = synthetic
    files = {"video": ("video.mov", open(sdir / "video.mov", "rb"), "video/quicktime"),
             "depth": ("depth.bin", open(sdir / "depth.bin", "rb"), "application/octet-stream"),
             "confidence": ("confidence.bin", open(sdir / "confidence.bin", "rb"), "application/octet-stream"),
             "metadata": ("metadata.json", open(sdir / "metadata.json", "rb"), "application/json")}
    r = client.post("/sessions/upload", files=files, data={"step": "1", "mock": "true"})
    assert r.status_code == 200, r.text
    _check_measurement(r.json())
    # incomplete set -> 400
    r = client.post("/sessions/upload", files={"video": ("video.mov", open(sdir / "video.mov", "rb"))},
                    data={"mock": "true"})
    assert r.status_code == 400


def test_detect_video_only(client, synthetic):
    sdir, _ = synthetic
    with open(sdir / "video.mov", "rb") as f:
        r = client.post("/detect", files={"video": ("video.mov", f, "video/quicktime")},
                        data={"step": "1", "max_frames": "3", "orientation": "portrait", "mock": "true"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["frames_processed"] == 3 and body["frames_detected"] == 3
    assert body["video"]["width"] == 960 and body["detector"] == "mock"
    assert body["mean_confidence"] == pytest.approx(0.9)
    fr = body["frames"][0]
    assert fr["detected"] and fr["mask_area_px"] > 1000 and fr["preview"].endswith("frame_00000.png")
    png = client.get(fr["preview"])
    assert png.status_code == 200 and png.content[:4] == b"\x89PNG"
    assert client.get(body["result_json"]).json()["detect_id"] == body["detect_id"]
    assert client.get(f"/detect/{body['detect_id']}/../../etc").status_code in (400, 404)
    assert client.post("/detect", files={"video": ("v.mov", b"", "video/quicktime")}).status_code == 400
