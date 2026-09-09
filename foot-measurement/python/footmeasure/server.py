"""Minimal HTTP service around the pipeline (uvicorn footmeasure.server:app --host 0.0.0.0 --port 8000).

Endpoints (interactive docs: http://<host>:8000/docs, Postman collection: python/postman/):

    GET  /health
    POST /sessions                  raw zip body (what the iPhone app sends)      -> measurement JSON
    POST /sessions/upload           multipart/form-data: `zip`  OR  `video`+`depth`+`confidence`+`metadata`
                                    (+ optional text fields step, method, mock)   -> measurement JSON
    GET  /sessions                  list processed sessions
    GET  /sessions/{id}/result.json  full result incl. per-frame values
    GET  /sessions/{id}/debug.png    mask + contour + L/W lines + top-down view
    POST /detect                    multipart: `video` only (no LiDAR needed)     -> RF-DETR detections per frame
                                    (+ step, max_frames, orientation, class_name, mock)
    GET  /detect/{id}/result.json,  GET /detect/{id}/frame_00015.png   preview with the mask

Environment: FOOTMEASURE_WEIGHTS, FOOTMEASURE_SIZE, FOOTMEASURE_CLASS, FOOTMEASURE_DEVICE,
FOOTMEASURE_METHOD, FOOTMEASURE_STEP, FOOTMEASURE_SESSIONS (storage dir), FOOTMEASURE_MOCK=1
(colour-threshold detector for synthetic sessions).
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

from .session import Session
from .util import bgr, rotate_to_upright

app = FastAPI(title="footmeasure", description=__doc__)
SESSIONS_DIR = Path(os.environ.get("FOOTMEASURE_SESSIONS", "sessions"))
_detectors: dict = {}
_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_PNG_RE = re.compile(r"^frame_\d{5}\.png$")


# ------------------------------------------------------------------ helpers

def get_detector(mock: bool = False, class_name: str | None = None):
    """Lazy singleton per configuration (RF-DETR weights load once)."""
    if mock or os.environ.get("FOOTMEASURE_MOCK"):
        key = ("mock",)
    else:
        key = ("rfdetr", class_name or os.environ.get("FOOTMEASURE_CLASS") or None)
    if key not in _detectors:
        if key[0] == "mock":
            from .detector import ColorMockDetector
            _detectors[key] = ColorMockDetector()
        else:
            from .detector import FootDetector
            _detectors[key] = FootDetector(weights=os.environ.get("FOOTMEASURE_WEIGHTS") or None,
                                           size=os.environ.get("FOOTMEASURE_SIZE", "small"),
                                           class_name=key[1],
                                           device=os.environ.get("FOOTMEASURE_DEVICE") or None)
    return _detectors[key]


def _new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]


def _check_id(value: str) -> str:
    if not _ID_RE.match(value):
        raise HTTPException(400, "bad id")
    return value


async def _save_upload(up: UploadFile, dest: Path) -> int:
    n = 0
    with open(dest, "wb") as f:
        while True:
            chunk = await up.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
    return n


def _process(src: Path, out: Path, step: int | None = None, method: str | None = None, mock: bool = False) -> dict:
    from .debug_image import render_debug
    from .multiframe import process_session
    s = Session.load(src)
    res = process_session(s, get_detector(mock),
                          step=step or int(os.environ.get("FOOTMEASURE_STEP", "5")),
                          method=method or os.environ.get("FOOTMEASURE_METHOD", "contour"))
    if res.best is not None:
        f = s.frame(res.best.index)
        img = render_debug(f.rgb, res.best.mask, res.best.measurement, f.K, res.best.confidence, f.orientation,
                           rotate=True, title=f"best frame {f.index}:")
        cv2.imwrite(str(out / "debug.png"), img)
    (out / "result.json").write_text(json.dumps(res.summary, indent=2, ensure_ascii=False))
    return res.summary


def _detect_video(video: Path, out: Path, did: str, step: int, max_frames: int, orientation: str | None,
                  mock: bool, class_name: str | None) -> dict:
    """Run only the RF-DETR stage on a plain video (no depth): per-frame confidence + mask previews."""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError("cannot open video (expected .mov / .mp4)")
    det = get_detector(mock, class_name)
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    n_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames, i = [], 0
    try:
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if i % step == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                d = det.detect(rgb, orientation)
                entry: dict = {"index": i, "t_s": round(i / fps, 3), "detected": d is not None}
                if d is not None:
                    prev = bgr(rgb)
                    prev[d.mask] = (0.5 * prev[d.mask] + 0.5 * np.array([0, 200, 0])).astype(np.uint8)
                    x1, y1, x2, y2 = d.bbox.astype(int)
                    cv2.rectangle(prev, (x1, y1), (x2, y2), (0, 220, 255), 2)
                    cv2.putText(prev, f"{d.class_name} {d.confidence:.2f}", (x1, max(30, y1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 255), 2)
                    prev = rotate_to_upright(prev, orientation)
                    scale = min(1.0, 960 / max(prev.shape[:2]))
                    if scale < 1.0:
                        prev = cv2.resize(prev, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                    name = f"frame_{i:05d}.png"
                    cv2.imwrite(str(out / name), prev)
                    entry.update(confidence=round(float(d.confidence), 3), class_name=d.class_name,
                                 bbox=[int(v) for v in d.bbox], mask_area_px=int(d.mask.sum()),
                                 two_pass=bool(d.two_pass), preview=f"/detect/{did}/{name}")
                frames.append(entry)
            i += 1
    finally:
        cap.release()
    conf = [f["confidence"] for f in frames if f["detected"]]
    summary = {
        "detect_id": did,
        "video": {"width": W, "height": H, "fps": fps, "frames": n_total},
        "step": step, "orientation": orientation,
        "frames_processed": len(frames), "frames_detected": len(conf),
        "mean_confidence": round(float(np.mean(conf)), 3) if conf else None,
        "detector": "mock" if (mock or os.environ.get("FOOTMEASURE_MOCK")) else "rfdetr",
        "frames": frames,
    }
    (out / "result.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def _measurement_response(summary: dict, sid: str, extra: dict | None = None) -> JSONResponse:
    body = {k: v for k, v in summary.items() if k != "per_frame"}
    body["session_id"] = sid
    body["result_json"] = f"/sessions/{sid}/result.json"
    body["debug_image"] = f"/sessions/{sid}/debug.png"
    body.update(extra or {})
    return JSONResponse(body)


def _validate_method(method: str | None) -> str | None:
    if method not in (None, "", "contour", "depth"):
        raise HTTPException(400, "method must be 'contour' or 'depth'")
    return method or None


# ------------------------------------------------------------------ endpoints

@app.get("/health")
def health():
    return {"ok": True, "sessions_dir": str(SESSIONS_DIR)}


@app.post("/sessions")
async def upload_session(request: Request, step: int | None = None, method: str | None = None, mock: bool = False):
    """Raw request body = zipped session directory (this is what the iPhone app sends)."""
    method = _validate_method(method)
    sid = _new_id()
    out = SESSIONS_DIR / sid
    out.mkdir(parents=True, exist_ok=True)
    zip_path = out / "upload.zip"
    n = 0
    with open(zip_path, "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)
            n += len(chunk)
    if n == 0:
        raise HTTPException(400, "empty body; POST the zipped session as the request body "
                                 "(or use multipart /sessions/upload)")
    try:
        summary = await run_in_threadpool(_process, zip_path, out, step, method, mock)
    except Exception as e:  # MVP: surface the error to the client
        raise HTTPException(500, f"processing failed: {e}")
    return _measurement_response(summary, sid, {"bytes_received": n})


@app.post("/sessions/upload")
async def upload_session_form(
    archive: UploadFile | None = File(None, alias="zip", description="zipped session directory"),
    video: UploadFile | None = File(None, description="video.mov"),
    depth: UploadFile | None = File(None, description="depth.bin"),
    confidence: UploadFile | None = File(None, description="confidence.bin"),
    metadata: UploadFile | None = File(None, description="metadata.json"),
    step: int | None = Form(None, description="use every k-th frame (default env FOOTMEASURE_STEP or 5)"),
    method: str | None = Form(None, description="contour | depth"),
    mock: bool = Form(False, description="colour-threshold detector for synthetic sessions"),
):
    """multipart/form-data upload for Postman / curl: either one `zip` file or the four session files."""
    method = _validate_method(method)
    sid = _new_id()
    out = SESSIONS_DIR / sid
    out.mkdir(parents=True, exist_ok=True)
    received: dict[str, int] = {}
    if archive is not None:
        src = out / "upload.zip"
        received["zip"] = await _save_upload(archive, src)
    elif all(u is not None for u in (video, depth, confidence, metadata)):
        src = out / "session"
        src.mkdir(exist_ok=True)
        for name, up in (("video.mov", video), ("depth.bin", depth), ("confidence.bin", confidence),
                         ("metadata.json", metadata)):
            received[name] = await _save_upload(up, src / name)
    else:
        raise HTTPException(400, "send either form field `zip` (file) or all four files: "
                                 "`video`, `depth`, `confidence`, `metadata`")
    if any(v == 0 for v in received.values()):
        raise HTTPException(400, f"empty upload: {received}")
    try:
        summary = await run_in_threadpool(_process, src, out, step, method, mock)
    except Exception as e:
        raise HTTPException(500, f"processing failed: {e}")
    return _measurement_response(summary, sid, {"bytes_received": received})


@app.get("/sessions")
def list_sessions():
    items = []
    if SESSIONS_DIR.exists():
        for d in sorted(SESSIONS_DIR.iterdir()):
            rj = d / "result.json"
            if not rj.exists():
                continue
            try:
                r = json.loads(rj.read_text())
            except json.JSONDecodeError:
                continue
            items.append({"session_id": d.name, "length_mm": r.get("length_mm"), "width_mm": r.get("width_mm"),
                          "valid_frames": r.get("valid_frames"), "frames_processed": r.get("frames_processed"),
                          "result_json": f"/sessions/{d.name}/result.json",
                          "debug_image": f"/sessions/{d.name}/debug.png" if (d / "debug.png").exists() else None})
    return {"sessions": items}


@app.get("/sessions/{sid}/debug.png")
def debug_image(sid: str):
    p = SESSIONS_DIR / _check_id(sid) / "debug.png"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/sessions/{sid}/result.json")
def result_json(sid: str):
    p = SESSIONS_DIR / _check_id(sid) / "result.json"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.post("/detect")
async def detect_video(
    video: UploadFile = File(..., description="any .mov/.mp4; RF-DETR only, no LiDAR needed"),
    step: int = Form(15, description="use every k-th frame"),
    max_frames: int = Form(20, description="stop after this many processed frames"),
    orientation: str | None = Form(None, description="portrait | landscapeRight | ... (rotate frames upright "
                                                     "before RF-DETR; leave empty for ordinary videos)"),
    class_name: str | None = Form(None, description="override target class, e.g. person for COCO weights"),
    mock: bool = Form(False),
):
    """Test the neural-network stage alone: upload a video, get per-frame confidence + mask previews."""
    if step < 1 or max_frames < 1:
        raise HTTPException(400, "step and max_frames must be >= 1")
    did = _new_id()
    out = SESSIONS_DIR / "detect" / did
    out.mkdir(parents=True, exist_ok=True)
    suffix = Path(video.filename or "video.mov").suffix or ".mov"
    src = out / f"video{suffix}"
    n = await _save_upload(video, src)
    if n == 0:
        raise HTTPException(400, "empty video upload")
    try:
        summary = await run_in_threadpool(_detect_video, src, out, did, step, max_frames, orientation, mock, class_name)
    except Exception as e:
        raise HTTPException(500, f"detection failed: {e}")
    summary["result_json"] = f"/detect/{did}/result.json"
    return JSONResponse(summary)


@app.get("/detect/{did}/result.json")
def detect_result(did: str):
    p = SESSIONS_DIR / "detect" / _check_id(did) / "result.json"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/detect/{did}/{name}")
def detect_preview(did: str, name: str):
    if not _PNG_RE.match(name):
        raise HTTPException(404)
    p = SESSIONS_DIR / "detect" / _check_id(did) / name
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)
