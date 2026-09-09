import json
import shutil

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from footmeasure import server  # noqa: E402
from synth import Scene, write_session  # noqa: E402


def test_upload_zip_returns_measurement(tmp_path, monkeypatch):
    scene = Scene(L=255, W=96, yaw_deg=10)
    frames = [scene.render(scene.camera(0.5, 4 * i, 30 * i), (960, 720), (128, 96), seed=i) for i in range(4)]
    sdir = write_session(tmp_path / "s", frames, orientation="portrait")
    z = shutil.make_archive(str(tmp_path / "s"), "zip", root_dir=sdir.parent, base_dir=sdir.name)
    monkeypatch.setattr(server, "SESSIONS_DIR", tmp_path / "srv")
    monkeypatch.setenv("FOOTMEASURE_MOCK", "1")
    monkeypatch.setenv("FOOTMEASURE_STEP", "1")
    server._detector = None
    client = TestClient(server.app)
    assert client.get("/health").json() == {"ok": True}
    with open(z, "rb") as f:
        r = client.post("/sessions", content=f.read(), headers={"Content-Type": "application/zip"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["length_mm"] == pytest.approx(255, abs=4) and body["width_mm"] == pytest.approx(96, abs=4)
    assert body["valid_frames"] >= 3 and body["session_id"]
    png = client.get(body["debug_image"])
    assert png.status_code == 200 and png.content[:4] == b"\x89PNG"
    assert client.get(f"/sessions/{body['session_id']}/result.json").json()["frames_processed"] == 4
    assert client.post("/sessions", content=b"").status_code == 400
