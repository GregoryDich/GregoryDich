"""Minimal HTTP service: iPhone POSTs the zipped session, gets JSON back.

    uvicorn footmeasure.server:app --host 0.0.0.0 --port 8000

Environment: FOOTMEASURE_WEIGHTS, FOOTMEASURE_SIZE, FOOTMEASURE_CLASS, FOOTMEASURE_DEVICE,
FOOTMEASURE_METHOD, FOOTMEASURE_STEP, FOOTMEASURE_SESSIONS (storage dir).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import cv2
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

from .session import Session

app = FastAPI(title="footmeasure")
SESSIONS_DIR = Path(os.environ.get("FOOTMEASURE_SESSIONS", "sessions"))
_detector = None


def get_detector():
    global _detector
    if _detector is None:
        if os.environ.get("FOOTMEASURE_MOCK"):
            from .detector import ColorMockDetector
            _detector = ColorMockDetector()
        else:
            from .detector import FootDetector
            _detector = FootDetector(weights=os.environ.get("FOOTMEASURE_WEIGHTS") or None,
                                     size=os.environ.get("FOOTMEASURE_SIZE", "small"),
                                     class_name=os.environ.get("FOOTMEASURE_CLASS") or None,
                                     device=os.environ.get("FOOTMEASURE_DEVICE") or None)
    return _detector


def _process(zip_path: Path, out: Path) -> dict:
    from .debug_image import render_debug
    from .multiframe import process_session
    s = Session.load(zip_path)
    res = process_session(s, get_detector(), step=int(os.environ.get("FOOTMEASURE_STEP", "5")),
                          method=os.environ.get("FOOTMEASURE_METHOD", "contour"))
    if res.best is not None:
        f = s.frame(res.best.index)
        img = render_debug(f.rgb, res.best.mask, res.best.measurement, f.K, res.best.confidence, f.orientation,
                           rotate=True, title=f"best frame {f.index}:")
        cv2.imwrite(str(out / "debug.png"), img)
    (out / "result.json").write_text(json.dumps(res.summary, indent=2, ensure_ascii=False))
    return res.summary


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/sessions")
async def upload_session(request: Request):
    sid = time.strftime("%Y%m%d-%H%M%S")
    out = SESSIONS_DIR / sid
    out.mkdir(parents=True, exist_ok=True)
    zip_path = out / "upload.zip"
    n = 0
    with open(zip_path, "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)
            n += len(chunk)
    if n == 0:
        raise HTTPException(400, "empty body; POST the zipped session as the request body")
    try:
        summary = await run_in_threadpool(_process, zip_path, out)
    except Exception as e:  # MVP: surface the error to the phone
        raise HTTPException(500, f"processing failed: {e}")
    body = {k: v for k, v in summary.items() if k != "per_frame"}
    body["session_id"] = sid
    body["debug_image"] = f"/sessions/{sid}/debug.png"
    body["bytes_received"] = n
    return JSONResponse(body)


@app.get("/sessions/{sid}/debug.png")
def debug_image(sid: str):
    p = SESSIONS_DIR / sid / "debug.png"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/sessions/{sid}/result.json")
def result_json(sid: str):
    p = SESSIONS_DIR / sid / "result.json"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)
