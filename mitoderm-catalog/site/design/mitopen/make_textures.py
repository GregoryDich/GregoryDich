"""Textures for the three.js MITOPEN scene (site/proto/scenes/mitopen.js), sharp at any size. The only packshot
(protocols/print/img/mitopen.webp, 273×891, the same photo as protocols/assets/img/mitopen.webp with a 12 px border) is
far too small to put on the model, so the pen is modelled from its measurements and its print is typeset:
  print.png   alpha of the white print «MITOPEN» (packaging-text.json: "'MITOPEN' printed vertically in white along the
              body"), unwrapped onto the body: x along the axis (from the ring toward the cone: the reading direction),
              y the arc across it (letter tops toward the button's meridian). 2048 × 384.
  vmark.png   the engraved V near the top cone (packaging-text.json: "a small engraved V"): R its relief (bump, 1 the
              surface, 0 the groove's floor), G its coverage (the decal's alpha), B the groove's cavity (darkening);
              x the angle round the axis, y along the axis. 512 × 512.
  vtech-system.webp, exosignal-hair.webp   the two partner products of S5 (story3d: billboards of their packshots),
              from the lossless print packshots, never enlarged.
Measurements (scratchpad spec of 22/10, re-measured here on the lossless print file): the axis is 12.49° from vertical;
u is px along it from the silhouette's top (the top end's plane at u 4.3, the bottom's at 902), t px across it (+ right).
The camera saw the pen from 11° right of the button's meridian (α_cam) and 9° below its axis (el), so a point on the
front at angle α (+ toward the right flat) and radius R(u) shows at t = R·sin(α − 11°) and 0.156·R·cos(α − 11°) above
its own plane (u_plane = u_front + 0.156·R).
Letters (half-max of letter − local body, columns and rows; the T at 0.35 for its fainter bar), facade px: the print's
centre line is the generatrix α = 7.35° (M 7.1°, N 7.6°), its cap height 20.4 px of arc (M 20.6, N 19.9), the stems
3.0 px (I 3.0, T 3.1, N 2.9); set at 6.5° and 21.0 px so that the rendered print, measured the same way on the scene's
render in the packshot's pose, lands on these (the texture's own edge softening narrows it): Jost 450 (SIL OFL, a geometric sans like the print; the owner's artwork would replace it
glyph for glyph), each glyph set to its measured width. The V: its two grooves traced as luminance minima row by row.
usage: python3 -I make_textures.py <font dir with Jost[wght].ttf> <out dir: site/proto/img/mitopen-3d> <repo root>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

# the body's radius (px of the packshot) at u (plane), from the silhouette: the part the print and the V lie on
RU = [(76, 53.3), (78, 50.1), (80, 48.1), (82, 48.1), (84, 49.7), (86, 50.3), (91, 50.3), (94, 49.8), (100, 49.1), (110, 47.2),
      (120, 45.0), (130, 43.5), (140, 42.0), (260, 46.1), (280, 47.7), (300, 49.8), (320, 51.7), (340, 53.8), (360, 55.7), (380, 57.3),
      (400, 59.9), (420, 61.4), (440, 63.5)]
R = lambda u: float(np.interp(u, *zip(*RU)))
EL, AZ = np.radians(9.0), 11.0


def _plane(uf, alpha=6.5):   # a facade point's own plane: u_plane = u_front + sin(el)·R(u_plane)·cos(α − α_cam), solved
    u = uf
    for _ in range(4): u = uf + np.sin(EL) * R(u) * np.cos(np.radians(alpha - AZ))
    return u


# ---- the print: decal window (plane u, arc px from the centre line) and the measured letters
U0, U1 = 432.0, 286.0                 # x 0 … 2048 ↔ u 432 (beyond the M) … 286 (beyond the N)
S0, S1 = -13.7, 13.7                  # y 0 … 384 ↔ arc −13.7 (the letter tops' side, −α) … +13.7
ALPHA_C, CAP = 6.5, 21.0             # the centre line (degrees from the button's meridian) and the cap height (arc px), set so the
#                                       rendered print's half-max box lands on the measured one (overlay: +0.8 px across, −0.7 px tall at 7.35°, 20.4)
PW, PH = 2048, 384
LETTERS = [('M', 416.3, 395.5), ('I', 389.5, 386.5), ('T', 382.5, 366.9), ('O', 363.7, 343.7), ('P', 339.2, 323.7),
           ('E', 319.0, 304.6), ('N', 300.1, 283.3)]   # facade u of each letter's ink, from its M-side edge to its N-side edge
WEIGHT = 450


def glyph(font, ch, size=800):   # a glyph's alpha at a large size, its 50 % ink box, the cap line and the baseline
    f = ImageFont.truetype(font, size); f.set_variation_by_axes([WEIGHT])
    im = Image.new('L', (size * 2, size * 2)); ImageDraw.Draw(im).text((size // 2, size // 4), ch, font=f, fill=255)
    h = Image.new('L', (size * 2, size * 2)); ImageDraw.Draw(h).text((size // 2, size // 4), 'H', font=f, fill=255)
    a, ha = np.asarray(im) > 127, np.asarray(h) > 127
    ys, xs = np.nonzero(a); hy = np.nonzero(ha.any(1))[0]
    return im, (xs.min(), xs.max() + 1), (hy[0], hy[-1] + 1)


def print_tex(font):
    kx, ky = PW / (U0 - U1), PH / (S1 - S0)
    out = np.zeros((PH, PW), np.float32)
    placed = []
    for ch, ua, ub in LETTERS:
        pa, pb = _plane(ua), _plane(ub)                         # plane u of the ink's two edges
        x0, x1 = (U0 - pa) * kx, (U0 - pb) * kx                  # texture px
        im, (gx0, gx1), (cap0, base) = glyph(font, ch)
        sy = CAP * ky / (base - cap0); sx = (x1 - x0) / (gx1 - gx0)
        top = (-CAP / 2 - S0) * ky                               # the cap line's row
        # the glyph's own pixels mapped by an affine resample (x: ink box → [x0, x1], y: cap line → top, scale sy)
        yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
        gx = gx0 + (xx + 0.5 - x0) / sx - 0.5; gy = cap0 + (yy + 0.5 - top) / sy - 0.5
        sm = ndimage.gaussian_filter(np.asarray(im, np.float32), sigma=0.5 / min(sx, sy))   # no aliasing when shrinking
        v = ndimage.map_coordinates(sm, [gy, gx], order=1, cval=0)
        out = np.maximum(out, v)
        placed.append((ch, round(pa, 2), round(pb, 2)))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), placed


def check_print(tex, placed):   # the typeset string back in packshot px: its length and each letter's edges
    a = np.asarray(tex) > 127; kx = PW / (U0 - U1)
    cols = np.flatnonzero(a.any(0)); length = (cols[-1] + 1 - cols[0]) / kx
    want = placed[0][1] - placed[-1][2]
    print(f'print: string {length:.2f} px of plane (measured {want:.2f}), cap rows {np.flatnonzero(a.any(1))[[0, -1]]}')
    assert abs(length - want) < 0.5, 'string length off by more than 0.5 px'
    runs, on = [], False
    for x in range(PW):
        if a[:, x].any() and not on: start, on = x, True
        if not a[:, x].any() and on: runs.append((start, x)); on = False
    assert len(runs) == 7, runs
    for (ch, pa, pb), (r0, r1) in zip(placed, runs):
        ea, eb = U0 - r0 / kx, U0 - r1 / kx
        assert abs(ea - pa) < 0.5 and abs(eb - pb) < 0.5, (ch, ea, pa, eb, pb)
    print('print: every letter within 0.5 px of its measured place')


# ---- the V: groove traces (facade u, t), converted to the plane and to α; decal window α −22…+18°, u 78…122
VL = [(76, -22.0), (78, -20.5), (80, -20.0), (82, -18.8), (84, -18.2), (86, -16.8), (88, -16.2), (90, -15.8), (92, -14.5),
      (94, -14.0), (96, -13.5), (98, -13.0), (100, -12.5), (102, -12.0), (104, -11.8), (106, -10.2)]
VR = [(76, 0.5), (78, -0.2), (80, -1.8), (82, -2.2), (84, -3.8), (86, -4.5), (88, -5.0), (90, -5.5), (92, -6.2), (94, -6.8),
      (96, -7.5), (98, -8.0), (100, -8.5), (102, -8.2), (104, -8.8)]
VERTEX = (106.5, -10.0)
VA0, VA1, VU0, VU1, VW = -22.0, 18.0, 78.0, 122.0, 512
GROOVE, DEPTH_SIDE = 1.05, 0.55   # half width of the groove (px), its far wall a little lighter (bump does the shading)


def to_alpha(uf, t):
    u = uf + 8
    for _ in range(4):
        r = R(u); a = AZ + np.degrees(np.arcsin(t / r)); u = uf + np.sin(EL) * r * np.cos(np.radians(a - AZ))
    return a, u


def vmark():
    arms = []
    for pts in (VL + [VERTEX], VR + [VERTEX]):
        P = np.array([to_alpha(u, t) for u, t in pts])           # (α, u_plane)
        A = np.polyfit(P[:, 1], P[:, 0], 2)                      # α as a smooth function of u along the arm
        us = np.linspace(P[:, 1].min(), P[:, 1].max(), 400); arms.append(np.c_[np.polyval(A, us), us])
    # the arms meet at the vertex: both fits end at the same point (their mean)
    vx = (arms[0][-1] + arms[1][-1]) / 2
    for k in range(2): arms[k] += (vx - arms[k][-1]) * np.linspace(0, 1, len(arms[k]))[:, None]
    ka, ku = VW / (VA1 - VA0), VW / (VU1 - VU0)
    yy, xx = np.mgrid[0:VW, 0:VW].astype(np.float64)
    al = VA0 + (xx + 0.5) / ka; uu = VU0 + (yy + 0.5) / ku
    rr = np.vectorize(R)(uu)
    d = np.full(al.shape, 1e9)
    for arm in arms:   # distance (px on the surface) to the polyline, through its densely sampled points
        for a, u in arm[::2]:
            d = np.minimum(d, np.hypot((al - a) * np.pi / 180 * rr, uu - u))
    g = np.clip(1 - d / GROOVE, 0, 1)                            # 1 on the groove's line, 0 at its edges
    height = 1 - g ** 1.5                                        # a rounded V-section groove
    cover = np.clip(1.6 - d / GROOVE, 0, 1)                      # the decal's alpha: the groove and a little round it
    cavity = g ** 2
    rgb = np.stack([height, cover, cavity], -1)
    return Image.fromarray((rgb * 255 + 0.5).astype(np.uint8)), arms


if __name__ == '__main__':
    fdir, out, repo = sys.argv[1:4]; os.makedirs(out, exist_ok=True)
    tex, placed = print_tex(os.path.join(fdir, 'Jost[wght].ttf'))
    check_print(tex, placed); tex.save(f'{out}/print.png', optimize=True)
    print('letters (plane u of the ink edges):', placed)
    vm, arms = vmark(); vm.save(f'{out}/vmark.png', optimize=True)
    print('V: top ends', [tuple(np.round(a[0], 1)) for a in arms], 'vertex', tuple(np.round(arms[0][-1], 1)), '(α°, plane u)')
    vt = Image.open(f'{repo}/protocols/print/img/vtech-system.webp').convert('RGBA')
    vt = vt.resize((round(vt.width * 960 / vt.height), 960), Image.LANCZOS)   # S5 shows it ≤ 432 px tall on a 3840 key
    vt.save(f'{out}/vtech-system.webp', quality=86, alpha_quality=92, method=6)
    Image.open(f'{repo}/protocols/print/img/exosignal-hair.webp').convert('RGBA').save(f'{out}/exosignal-hair.webp', quality=86, alpha_quality=92, method=6)
    total = 0
    for n in ('print.png', 'vmark.png', 'vtech-system.webp', 'exosignal-hair.webp'):
        im = Image.open(f'{out}/{n}'); s = os.path.getsize(f'{out}/{n}'); total += s; print(n, im.size, im.mode, s // 1024, 'KB')
    print('folder', total // 1024, 'KB')
