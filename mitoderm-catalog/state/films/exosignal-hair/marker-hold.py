#!/usr/bin/env python3
"""marker-hold.py <frame A.png> <frame B.png> <out.mp4 | out.png> <frames> [single frame index]
A held shot of the MITOSCAN tablet with dashed circles drawn on its screen (in the screen's perspective).
The base cross-fades from frame A to frame B over the hold (pass the same file twice for a plain freeze).
Timeline (96 frames): a scan line sweeps the screen, three circles lock on one after another, stay, fade out."""
import subprocess, sys, os, tempfile, math

A, B, OUT, N = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
ONLY = int(sys.argv[5]) if len(sys.argv) > 5 else None
FW, FH = 1912, 1080
CW, CH = 1200, 800                       # the flat canvas that is warped onto the screen
QUAD = [(120, 423), (684, 448), (795, 821), (212, 852)]   # lit screen area: TL, TR, BR, BL (measured on the frame)
SPOTS = [((321, 578), 110), ((405, 725), 96), ((606, 766), 104)]  # circle centre on the frame, radius on the canvas
VX, VY, VW, VH = 100, 400, 720, 470     # viewport of the warp inside the frame


def solve(m, v):
    n = len(v); a = [row[:] + [v[i]] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c])); a[c], a[p] = a[p], a[c]
        for r in range(n):
            if r != c:
                f = a[r][c] / a[c][c]
                a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [a[i][n] / a[i][i] for i in range(n)]


def homography(src, dst):
    m, v = [], []
    for (x, y), (u, w) in zip(src, dst):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); v.append(u)
        m.append([0, 0, 0, x, y, 1, -w * x, -w * y]); v.append(w)
    h = solve(m, v) + [1.0]
    return lambda x, y: ((h[0] * x + h[1] * y + h[2]) / (h[6] * x + h[7] * y + 1),
                         (h[3] * x + h[4] * y + h[5]) / (h[6] * x + h[7] * y + 1))


to_canvas = homography(QUAD, [(0, 0), (CW, 0), (CW, CH), (0, CH)])
CIRCLES = [(to_canvas(*c), r) for c, r in SPOTS]
ease = lambda t: 1 - (1 - max(0.0, min(1.0, t))) ** 3


def frame(i, path):
    k = N / 96.0
    fade = 1.0 if i < 86 * k else max(0.0, 1 - (i - 86 * k) / (9 * k))
    draw = []
    s = (i - 4 * k) / (24 * k)                      # the scan line, 0..1
    if 0 <= s <= 1:
        y = s * CH; a = 0.34 * math.sin(math.pi * s)
        draw += [f"fill rgba(255,255,255,{a:.3f}) stroke none rectangle 0,{y - 5:.1f} {CW},{y + 5:.1f}",
                 f"fill rgba(255,255,255,{a * 0.35:.3f}) stroke none rectangle 0,{y - 46:.1f} {CW},{y - 5:.1f}"]
    for n, ((cx, cy), r) in enumerate(CIRCLES):
        p = ease((i - (20 + 12 * n) * k) / (14 * k))
        if p <= 0:
            continue
        rr = r * (1.35 - 0.35 * p); a = p * fade; off = -i * 1.6
        for col, w in ((f"rgba(20,16,12,{0.38 * a:.3f})", 13), (f"rgba(255,255,255,{0.96 * a:.3f})", 7)):
            draw.append(f"fill none stroke {col} stroke-width {w} stroke-linecap round stroke-dasharray 30 22 "
                        f"stroke-dashoffset {off:.1f} circle {cx:.1f},{cy:.1f} {cx + rr:.1f},{cy:.1f}")
    b = min(1.0, i / max(1, N - 1))
    base = ["convert", A]
    if A != B:
        base += [B, "-define", f"compose:args={b * 100:.2f}", "-compose", "blend", "-composite"]
    if not draw:
        subprocess.run(base + [path], check=True); return
    q = QUAD
    warp = (f"0,0 {q[0][0]},{q[0][1]} {CW},0 {q[1][0]},{q[1][1]} {CW},{CH} {q[2][0]},{q[2][1]} 0,{CH} {q[3][0]},{q[3][1]}")
    subprocess.run(base + ["(", "-size", f"{CW}x{CH}", "xc:none", "-draw", " ".join(draw), "-virtual-pixel", "transparent",
                           "-define", f"distort:viewport={VW}x{VH}+{VX}+{VY}", "-distort", "Perspective", warp, "+repage", ")",
                           "-compose", "over", "-geometry", f"+{VX}+{VY}", "-composite", path], check=True)


if ONLY is not None:
    frame(ONLY, OUT); sys.exit(0)
with tempfile.TemporaryDirectory() as t:
    for i in range(N):
        frame(i, os.path.join(t, f"f{i:04d}.png"))
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-framerate", "24", "-i", os.path.join(t, "f%04d.png"),
                    "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "8", "-pix_fmt", "yuv420p", "-r", "24", OUT], check=True)
print(OUT, N, "frames")
