"""Generate a SYNTHETIC measurement session (no iPhone needed) to exercise the pipeline.

A foot-shaped solid with the dimensions you pass here is rendered into the exact
files the iOS app writes (video.mov, depth.bin, confidence.bin, metadata.json).
The numbers you pass are parameters of the *generator only* — the pipeline never
sees them; it has to recover them from the video + depth:

    python make_synthetic_session.py out/demo_session --length-mm 262 --width-mm 98
    footmeasure process out/demo_session --mock-detector --step 1 --rotate

`--mock-detector` is required for synthetic sessions: the painted blob is not a real
foot, so RF-DETR is meaningless on it. Real recordings use `--weights`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "tests"))
from synth import Scene, write_session  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out_dir", help="session directory to create")
    p.add_argument("--length-mm", type=float, default=262.0)
    p.add_argument("--width-mm", type=float, default=98.0)
    p.add_argument("--height-mm", type=float, default=24.0, help="thickness of the synthetic foot")
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--camera-height-m", type=float, default=0.5)
    p.add_argument("--yaw-deg", type=float, default=-30.0, help="foot rotation on the floor")
    p.add_argument("--max-tilt-deg", type=float, default=15.0, help="camera tilt grows from 0 to this over the frames")
    p.add_argument("--rgb", default="1920x1440")
    p.add_argument("--depth", default="256x192")
    a = p.parse_args()

    rgb = tuple(int(v) for v in a.rgb.lower().split("x"))
    depth = tuple(int(v) for v in a.depth.lower().split("x"))
    scene = Scene(L=a.length_mm, W=a.width_mm, H=a.height_mm, yaw_deg=a.yaw_deg)
    frames = []
    for i in range(a.frames):
        tilt = a.max_tilt_deg * i / max(a.frames - 1, 1)
        T = scene.camera(height_m=a.camera_height_m + 0.005 * i, tilt_deg=tilt, azimuth_deg=25.0 * i)
        frames.append(scene.render(T, rgb_size=rgb, depth_size=depth, seed=i))
    out = write_session(Path(a.out_dir), frames, orientation="portrait")
    print(f"synthetic session written: {out}  ({a.frames} frames, video {rgb[0]}x{rgb[1]}, depth {depth[0]}x{depth[1]})")
    print(f"generator parameters (NOT visible to the pipeline): length={a.length_mm:g} mm, width={a.width_mm:g} mm")
    print(f"now compute them from the data:\n  footmeasure process {out} --mock-detector --step 1 --rotate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
