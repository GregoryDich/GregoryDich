"""Reference check (spec section 24): system vs. hand measurement, several recordings.

reference.csv:
    session,reference_length_mm,reference_width_mm
    sessions/20260909-101500,268,101
    ...

    python evaluate.py reference.csv --weights weights/checkpoint_best_total.pth [--step 5] [--method contour]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from footmeasure.cli import _add_detector_args, _add_measure_args, _make_detector, _measure_kwargs  # noqa: E402
from footmeasure.multiframe import process_session  # noqa: E402
from footmeasure.session import Session  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("reference_csv")
    p.add_argument("--step", type=int, default=5)
    p.add_argument("--top-k", type=int, default=7)
    p.add_argument("--out", default="out/evaluation.json")
    _add_detector_args(p)
    _add_measure_args(p)
    a = p.parse_args()
    det = _make_detector(a)
    rows = list(csv.DictReader(open(a.reference_csv)))
    results = []
    print(f"{'session':40s} {'L_sys':>7s} {'L_ref':>6s} {'dL':>6s} {'W_sys':>7s} {'W_ref':>6s} {'dW':>6s} frames")
    for r in rows:
        s = Session.load(r["session"])
        res = process_session(s, det, step=a.step, top_k=a.top_k, method=a.method,
                              measure_kwargs=_measure_kwargs(a), log=None).summary
        Lr, Wr = float(r["reference_length_mm"]), float(r["reference_width_mm"])
        Ls, Ws = res.get("length_mm"), res.get("width_mm")
        dL = None if Ls is None else Ls - Lr
        dW = None if Ws is None else Ws - Wr
        results.append(dict(session=r["session"], length_mm=Ls, width_mm=Ws, reference_length_mm=Lr,
                            reference_width_mm=Wr, length_error_mm=dL, width_error_mm=dW,
                            valid_frames=res.get("valid_frames"), length_iqr_mm=res.get("length_iqr_mm"),
                            width_iqr_mm=res.get("width_iqr_mm")))
        f = lambda v: "   n/a" if v is None else f"{v:6.1f}"
        print(f"{r['session']:40s} {f(Ls):>7s} {Lr:6.1f} {f(dL):>6s} {f(Ws):>7s} {Wr:6.1f} {f(dW):>6s} {res.get('valid_frames')}")
    dLs = [x["length_error_mm"] for x in results if x["length_error_mm"] is not None]
    dWs = [x["width_error_mm"] for x in results if x["width_error_mm"] is not None]
    if dLs:
        import numpy as np
        print(f"\nlength error: mean {np.mean(dLs):+.1f} mm, |max| {np.max(np.abs(dLs)):.1f} mm, std {np.std(dLs):.1f} mm")
        print(f"width  error: mean {np.mean(dWs):+.1f} mm, |max| {np.max(np.abs(dWs)):.1f} mm, std {np.std(dWs):.1f} mm")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
