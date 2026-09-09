"""CLI: one subcommand per MVP stage so each can be checked on a real recording.

    footmeasure visualize <session>                 MVP-1  RGB | depth | confidence panels
    footmeasure detect    <session> --weights ...   MVP-2  RF-DETR foot masks
    footmeasure points    <session> --frame N       MVP-3  foot / floor point cloud -> .ply
    footmeasure measure   <session> --frame N       MVP-4  one frame -> length / width + debug.png
    footmeasure process   <session>                 MVP-5  many frames -> median -> result.json + debug.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from .session import Session


def _add_detector_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("RF-DETR")
    g.add_argument("--weights", default=None, help="fine-tuned RF-DETR-Seg checkpoint (checkpoint_best_total.pth)")
    g.add_argument("--size", default="small", choices=["nano", "small", "medium", "large", "xlarge", "2xlarge"])
    g.add_argument("--class-name", default=None, help="target class (default: 'foot' with weights, 'person' without)")
    g.add_argument("--threshold", type=float, default=0.3)
    g.add_argument("--device", default=None, help="cpu | mps | cuda (default: auto)")
    g.add_argument("--no-two-pass", action="store_true", help="disable the bbox->crop second pass")
    g.add_argument("--mock-detector", action="store_true", help="synthetic sessions only: colour-threshold 'foot'")


def _add_measure_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("measurement")
    g.add_argument("--method", default="contour", choices=["contour", "depth"])
    g.add_argument("--height-fraction", type=float, default=0.5, help="contour lift = fraction * local LiDAR height")
    g.add_argument("--h-min-mm", type=float, default=4.0, help="LiDAR points below this height count as floor")
    g.add_argument("--conf-min", type=int, default=1, help="min LiDAR confidence (0/1/2) for foot points")


def _make_detector(a):
    if a.mock_detector:
        from .detector import ColorMockDetector
        return ColorMockDetector()
    from .detector import FootDetector
    return FootDetector(a.weights, a.size, a.class_name, a.threshold, a.device, not a.no_two_pass)


def _measure_kwargs(a) -> dict:
    return dict(height_fraction=a.height_fraction, h_min=a.h_min_mm / 1000.0, conf_min=a.conf_min)


def _out_dir(a, session: Session) -> Path:
    out = Path(a.out) if a.out else Path("out") / session.path.name
    out.mkdir(parents=True, exist_ok=True)
    return out


def _load_mask_polygon(path: str, rgb_size) -> np.ndarray:
    from .measure import mask_from_polygon
    pts = np.asarray(json.loads(Path(path).read_text()), dtype=float)
    return mask_from_polygon(pts, rgb_size)


# ------------------------------------------------------------------ commands

def cmd_visualize(a) -> int:
    from . import visualize
    s = Session.load(a.session)
    visualize.run(s, step=a.step, out_dir=_out_dir(a, s), rotate=a.rotate, max_frames=a.max_frames)
    return 0


def cmd_detect(a) -> int:
    from .util import bgr, rotate_to_upright
    s = Session.load(a.session)
    det = _make_detector(a)
    out = _out_dir(a, s)
    n_ok = 0
    for f in s.iter_frames(step=a.step, max_frames=a.max_frames):
        d = det.detect(f.rgb, f.orientation)
        img = bgr(f.rgb)
        if d is None:
            print(f"  frame {f.index:5d}: no {getattr(det, 'class_name', 'foot')} detected")
        else:
            n_ok += 1
            img[d.mask] = (0.5 * img[d.mask] + 0.5 * np.array([0, 200, 0])).astype(np.uint8)
            x1, y1, x2, y2 = d.bbox.astype(int)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 220, 255), 2)
            print(f"  frame {f.index:5d}: {d.class_name} conf={d.confidence:.2f} area={int(d.mask.sum())}px "
                  f"two_pass={d.two_pass}")
        if a.rotate:
            img = rotate_to_upright(img, f.orientation)
        cv2.imwrite(str(out / f"detect_{f.index:05d}.png"), img)
    print(f"detected in {n_ok} frames -> {out}")
    return 0 if n_ok else 1


def _frame_and_mask(a, s: Session):
    idx = a.frame if a.frame is not None else s.n_frames // 2
    f = s.frame(idx)
    W, H = f.rgb.shape[1], f.rgb.shape[0]
    if a.mask_polygon:
        return f, _load_mask_polygon(a.mask_polygon, (W, H)), None
    d = _make_detector(a).detect(f.rgb, f.orientation)
    if d is None:
        print(f"frame {idx}: no detection", file=sys.stderr)
        return f, None, None
    return f, d.mask, d


def cmd_points(a) -> int:
    from .floor import estimate_floor
    from .geometry import background_depth_points, foot_depth_points, write_ply
    s = Session.load(a.session)
    f, mask, d = _frame_and_mask(a, s)
    if mask is None:
        return 1
    W, H = f.rgb.shape[1], f.rgb.shape[0]
    foot, _, _ = foot_depth_points(f.depth, f.confidence, f.K, (W, H), mask, conf_min=a.conf_min)
    bg = background_depth_points(f.depth, f.confidence, f.K, (W, H), mask)
    fl = estimate_floor(f.depth, f.confidence, f.K, (W, H), mask, f.T_world_cam)
    h = fl.plane.signed_distance(foot)
    out = _out_dir(a, s)
    pts = np.vstack([foot, bg])
    col = np.vstack([np.tile([220, 60, 60], (len(foot), 1)), np.tile([150, 150, 150], (len(bg), 1))]).astype(np.uint8)
    inl = np.abs(fl.plane.signed_distance(bg)) < 0.005
    col[len(foot):][inl] = [80, 200, 80]
    p = out / f"points_{f.index:05d}.ply"
    write_ply(p, pts, col)
    print(f"frame {f.index}: foot points {len(foot)} (above {a.h_min_mm} mm: {int((h > a.h_min_mm / 1000).sum())}), "
          f"floor candidates {len(bg)}, inliers {fl.n_inliers}, plane rms {fl.rms_mm:.2f} mm, "
          f"normal vs gravity {fl.normal_vs_up_deg}, foot height median {np.median(h[h > 0]) * 1000 if (h > 0).any() else 0:.1f} mm")
    for w in fl.warnings:
        print("  WARNING:", w)
    print(f"-> {p}  (red = foot, green = floor inliers, grey = other)")
    return 0


def cmd_measure(a) -> int:
    from .debug_image import render_debug
    from .measure import measure_frame
    s = Session.load(a.session)
    f, mask, d = _frame_and_mask(a, s)
    if mask is None:
        return 1
    W, H = f.rgb.shape[1], f.rgb.shape[0]
    kw = _measure_kwargs(a)
    if a.fixed_height_mm is not None:
        kw["fixed_height_m"] = a.fixed_height_mm / 1000.0
    m = measure_frame(f.depth, f.confidence, f.K, (W, H), mask, f.T_world_cam, method=a.method, **kw)
    out = _out_dir(a, s)
    img = render_debug(f.rgb, mask, m, f.K, None if d is None else d.confidence, f.orientation, a.rotate,
                       title=f"frame {f.index}")
    p = out / f"measure_{f.index:05d}.png"
    cv2.imwrite(str(p), img)
    res = m.as_dict()
    res.update(frame=f.index, debug_image=str(p))
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print(f"Length: {m.length_mm:.1f} mm\nWidth:  {m.width_mm:.1f} mm")
    return 0


def cmd_process(a) -> int:
    from .debug_image import render_debug
    from .multiframe import process_session
    s = Session.load(a.session)
    det = _make_detector(a)
    print(f"session {s.path}: {s.n_frames} frames; processing every {a.step}-th")
    res = process_session(s, det, step=a.step, top_k=a.top_k, method=a.method, min_conf=a.min_conf,
                          min_points=a.min_points, max_frames=a.max_frames, fuse=a.fuse,
                          measure_kwargs=_measure_kwargs(a))
    out = _out_dir(a, s)
    if res.best is not None:
        f = s.frame(res.best.index)
        img = render_debug(f.rgb, res.best.mask, res.best.measurement, f.K, res.best.confidence, f.orientation,
                           a.rotate, title=f"best frame {f.index} | median of {res.summary['frames_used']}:")
        p = out / "debug.png"
        cv2.imwrite(str(p), img)
        res.summary["debug_image"] = str(p)
    (out / "result.json").write_text(json.dumps(res.summary, indent=2, ensure_ascii=False))
    if res.summary.get("length_mm") is None:
        print("no valid frames", file=sys.stderr)
        print(json.dumps({k: v for k, v in res.summary.items() if k != "per_frame"}, indent=2))
        return 1
    print(json.dumps({k: v for k, v in res.summary.items() if k != "per_frame"}, indent=2, ensure_ascii=False))
    print(f"Length: {res.summary['length_mm']:.1f} mm\nWidth:  {res.summary['width_mm']:.1f} mm")
    return 0


# ------------------------------------------------------------------ parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="footmeasure", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, frames=True):
        sp.add_argument("session", help="session directory or .zip")
        sp.add_argument("--out", default=None, help="output dir (default out/<session>)")
        sp.add_argument("--rotate", action="store_true", help="rotate debug images upright per interface_orientation")
        if frames:
            sp.add_argument("--step", type=int, default=5, help="use every k-th frame")
            sp.add_argument("--max-frames", type=int, default=None)

    sp = sub.add_parser("visualize", help="MVP-1: RGB | depth | confidence panels"); common(sp)
    sp.set_defaults(func=cmd_visualize)

    sp = sub.add_parser("detect", help="MVP-2: RF-DETR foot masks"); common(sp); _add_detector_args(sp)
    sp.set_defaults(func=cmd_detect)

    for name, fn, helptxt in [("points", cmd_points, "MVP-3: foot/floor point cloud -> .ply"),
                              ("measure", cmd_measure, "MVP-4: measure one frame")]:
        sp = sub.add_parser(name, help=helptxt); common(sp, frames=False); _add_detector_args(sp); _add_measure_args(sp)
        sp.add_argument("--frame", type=int, default=None, help="frame index (default: middle frame)")
        sp.add_argument("--mask-polygon", default=None,
                        help="JSON [[u,v],...] pixel polygon used instead of RF-DETR (e.g. A4 sheet corners)")
        sp.add_argument("--fixed-height-mm", type=float, default=None,
                        help="lift the contour to this fixed height (flat objects, e.g. 0.2 for paper)")
        sp.set_defaults(func=fn)

    sp = sub.add_parser("process", help="MVP-5: whole session -> median"); common(sp); _add_detector_args(sp)
    _add_measure_args(sp)
    sp.add_argument("--top-k", type=int, default=7)
    sp.add_argument("--min-conf", type=float, default=0.3)
    sp.add_argument("--min-points", type=int, default=500)
    sp.add_argument("--fuse", action="store_true", help="also build the fused world-frame cloud (MVP-6 hook)")
    sp.set_defaults(func=cmd_process)
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    return int(a.func(a))


if __name__ == "__main__":
    sys.exit(main())
