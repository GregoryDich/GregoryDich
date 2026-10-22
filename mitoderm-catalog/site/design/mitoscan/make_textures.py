"""Textures for the three.js MITOSCAN scene (site/proto/scenes/mitoscan.js), sharp at any size: the print is typeset,
not cut from the photo (the largest packshot, protocols/print/img/mitoscan.webp, 1145×777, shows the screen ≈ 650 px
wide and the probe's panel ≈ 100 px). Places, sizes and colours are measured on the packshot rectified by the
reconstructed camera (scratchpad spec of 22/10: the glass's vanishing points; the display rectified to 1600×1000):
  glass.png   the whole glass, 1.000 × 0.6285 glass widths (gw), 3200 px per gw: the black border #070708, the display
              #161616 (u 0.0737…0.9304, v 0.0466…0.5846 gw from the glass's top left), on it the screen's print: the
              target (three rings and the cross in their neon colours, each colour taken round the rings by angle,
              the indigo inside, the soft halo, the white spark), «Mitoscan» white #f8f9f9 and «By Mitoderm Ltd» grey
              #7c7c7c. Nothing else is on the screen in the photo, so nothing else is drawn (no UI, no picture).
  panel.png   the probe's black panel (a stadium, u 1.058…1.166 × v 0.052…0.262 gw), the same lockup in #e8e8e7 turned
              90° to read upward, as photographed.
  badge.png   the cylinder's badge face (a stadium 0.135 × 0.031 gw, #f7f7f5) with «Mitoscan» in #3c3c3a.
  grille.png  the cylinder end's perforated disc (holes in curved rows, as on the photo), its metal and holes.
  brushed.png the aluminium's fine lengthwise grain (bump and roughness), tiling along the axis.
  haze.png    a soft shapeless cloud (luminance + alpha) for the silver haze of S2 (no edges, no rings).
Typeface: Rubik 400 (SIL OFL; the screen's two-storey «a» and x-height 0.761 of the caps are Rubik's, Jost's are not):
«Mitoscan» each glyph centred on its measured column, the grey line tracked to its measured width. The owner's vector
artwork would replace these glyph for glyph.
usage: python3 -I make_textures.py <font dir with Rubik[wght].ttf> <out dir: site/proto/img/mitoscan-3d>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

PXW = 3200                                     # glass texture px per gw
GW, GH = PXW, round(0.6285 * PXW)             # 3200 × 2011
DU, DV = (0.0737, 0.9304), (0.0466, 0.5846)   # the display on the glass (gw from its top left)
DX0, DX1, DY0, DY1 = DU[0] * PXW, DU[1] * PXW, DV[0] * PXW, DV[1] * PXW
WD, HD = DX1 - DX0, DY1 - DY0                 # the display in px (2741 × 1722)
BORDER, DISPLAY = (7, 7, 8), (22, 22, 22)
WHITE, GREY = (248, 249, 249), (124, 124, 124)

# ---- «Mitoscan»: ink columns of each glyph on the rectified display (1600 px wide), the cap line and the baseline
# (fractions of the display's height); «By Mitoderm Ltd»: its ink box (fractions of the display)
COLS = [('M', 660, 765), ('i', 785, 802), ('t', 813, 870), ('o', 879, 956), ('s', 968, 1037), ('c', 1049, 1122),
        ('a', 1133, 1204), ('n', 1224, 1299)]
CAP_Y, BASE_Y = 0.394, 0.510
SUB = ('By Mitoderm Ltd', 0.4763, 0.7469, 0.579, 0.621)   # text, ink x0, x1 (of W_d), the B's top, the baseline (of H_d)
WEIGHT = 400

# ---- the target (fractions of the display's width W_d; its centre as fractions of W_d, H_d), measured on the
# rectified display: ring radii at the half-max centres, line widths set a little under the photo's half-max widths
# (the photo is soft), the cross's three segments per arm (from the centre: the spark's cross, a dash over the inner
# ring, the long arm from the middle ring out past the outer one)
TC = (0.2849, 0.5120)
RINGS = [(0.0376, 0.0031), (0.0502, 0.0033), (0.0680, 0.0043)]   # (radius, width)
ARM_W, SEGS = 0.0025, [(0.0, 0.0244), (0.0312, 0.0435), (0.0481, 0.0830)]
# each ring's core colour by angle (degrees counter-clockwise from the right, every 15°; teal upper left, magenta lower
# right, lavender between): the brightest 40 % of the ring's pixels in 10° windows, the arms' angles interpolated
ANG = list(range(0, 360, 15))
RING_COL = {
    0: ['#a0679f', '#8a60a3', '#5d4494', '#4f4f9b', '#6d81ba', '#84b2d3', '#82b6d3', '#81bad3', '#84bed7', '#80b9d1', '#7bb5ce', '#7fb8d3',
        '#749fcc', '#689bc5', '#768ec0', '#514c97', '#624694', '#7b509c', '#937aa4', '#ab75ac', '#b179ab', '#b67faf', '#b178ac', '#aa6da7'],
    1: ['#b47ab4', '#aa79b4', '#977db6', '#9696c6', '#90add5', '#88c3e0', '#8bc8de', '#8ecddb', '#8ecad7', '#7cc2cd', '#7ec5d5', '#79c2d4',
        '#78b7d0', '#77adcd', '#87a6d0', '#8383bb', '#8e79b5', '#966aac', '#a56aaa', '#b469a7', '#c381b2', '#ca90bb', '#c783b5', '#bf80b4'],
    2: ['#b86dac', '#b077b3', '#a481b8', '#a6a2cc', '#a7bedf', '#8dc5e4', '#8fccdf', '#91d3da', '#89d0d6', '#7fcccd', '#7fcdd1', '#7dcdd4',
        '#78c5d5', '#74bed7', '#8eb0d9', '#a69ecb', '#ac8ec0', '#b285bb', '#b871b0', '#be5ea5', '#c566a4', '#ca65a5', '#cd6fac', '#c163a5']}
# the halo just outside the outer ring, by angle (above the display's grey), and its fall-off; the dark fill between the
# rings (indigo on the diagonals, deep teal upper left, deep magenta lower right) and inside the inner ring
HALO = {22: (42, 5, 52), 67: (11, 31, 60), 112: (7, 57, 66), 135: (0, 47, 53), 157: (4, 56, 65), 202: (6, 30, 54), 247: (38, 8, 56),
        292: (55, 0, 44), 315: (56, 0, 37), 337: (55, 0, 38)}
HALO_D0, HALO_L, HALO_GAIN = 0.0058, 0.0160, 1.2   # the halo: its sample distance outside the ring, decay length, gain
FILL_IN = {45: (31, 29, 80), 135: (24, 44, 84), 225: (34, 31, 84), 315: (40, 28, 81)}
FILL_RINGS = {45: (31, 30, 82), 135: (8, 58, 74), 225: (28, 28, 78), 315: (56, 19, 67)}
CORE_GAIN = 1.0                                # the line cores at the measured peaks (the typeset lines are sharper)


def hexrgb(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)


def by_angle(table, ang):   # a colour table {degrees: rgb} interpolated round the circle at angles `ang`
    ks = sorted(table); a = np.array(ks + [ks[0] + 360], float); c = np.array([table[k] for k in ks] + [table[ks[0]]], float)
    t = np.mod(ang - a[0], 360) + a[0]
    return np.stack([np.interp(t, a, c[:, i]) for i in range(3)], -1)


def target(img):   # draws the target into the float RGB glass image (px), vector by vector, no photo pixels
    cx, cy = DX0 + TC[0] * WD, DY0 + TC[1] * HD
    R = int(0.12 * WD); x0, y0 = int(cx) - R, int(cy) - R
    yy, xx = np.mgrid[y0:y0 + 2 * R, x0:x0 + 2 * R].astype(float) + 0.5
    dx, dy = (xx - cx) / WD, (yy - cy) / WD; r = np.hypot(dx, dy); ang = np.degrees(np.arctan2(-dy, dx)) % 360
    px = 1 / WD                                       # one texture px in W_d
    base = img[y0:y0 + 2 * R, x0:x0 + 2 * R].copy()
    # the fill: inside the inner ring a near-even indigo, between the rings the angle's deep colour; a soft step at
    # each ring (the photo's fill changes there), the halo outside the outer ring
    r_in, r_mid, r_out = (k[0] for k in RINGS)
    fin, fr = by_angle(FILL_IN, ang), by_angle(FILL_RINGS, ang)
    w = np.clip((r - r_in + 0.004) / 0.008, 0, 1)[..., None]
    fill = fin * (1 - w) + fr * w
    fill *= (1 - 0.12 * np.clip((r - r_mid) / (r_out - r_mid), 0, 1))[..., None]   # a little darker toward the outer ring
    halo = HALO_GAIN * by_angle(HALO, ang) * np.exp(-(r - r_out - HALO_D0) / HALO_L)[..., None]
    inside = np.clip((r_out - r) / px + 0.5, 0, 1)[..., None]
    col = inside * fill + (1 - inside) * (base + halo)
    # the lines: a crisp core (anti-aliased over one px) and a narrow glow of their own colour round it
    def line(d, width, c):   # d: distance to the centre line (W_d); adds the line of colour c (H×W×3)
        nonlocal col
        core = np.clip((width / 2 - d) / px + 0.5, 0, 1)[..., None]
        glow = 0.35 * np.exp(-np.maximum(d - width / 2, 0) / 0.0016)[..., None] * (1 - core)
        col = col * (1 - core) + c * core
        col = col + (c - col).clip(0) * glow
    for k, (rad, width) in enumerate(RINGS):
        cols = np.array([hexrgb(h) for h in RING_COL[k]]); tab = {a: cols[i] for i, a in enumerate(ANG)}
        c = np.clip(by_angle(tab, ang) * CORE_GAIN, 0, 255)
        line(np.abs(r - rad), width, c)
    # the cross: its colour is the outer ring's at that angle (teal arms left and up, magenta right and down), whitening
    # toward the centre (the photo's arms are near white within 0.01 W_d of the spark)
    cols = np.array([hexrgb(h) for h in RING_COL[2]]); tab = {a: cols[i] for i, a in enumerate(ANG)}
    for a in (0, 90, 180, 270):
        ux, uy = np.cos(np.radians(a)), -np.sin(np.radians(a))
        along = dx * ux + dy * uy; across = np.abs(-dx * uy + dy * ux)
        c = np.clip(by_angle(tab, np.full_like(r, a)) * CORE_GAIN, 0, 255)
        c = c + (np.array([245, 244, 250.]) - c) * np.exp(-(along / 0.005) ** 2)[..., None]
        for s0, s1 in SEGS:
            # a segment: across within the width, along within [s0, s1] with round ends
            d = np.where(along < s0, np.hypot(across, s0 - along), np.where(along > s1, np.hypot(across, along - s1), across))
            line(d, ARM_W, c)
    # the spark: a white point and its soft bloom, four short rays along the cross
    bloom = np.exp(-(r / 0.0026) ** 2) + 0.22 * np.exp(-(r / 0.0065) ** 2)
    rays = sum(np.exp(-((dx * np.cos(np.radians(a)) - dy * np.sin(np.radians(a))) / 0.0012) ** 2) * np.exp(-((dx * np.sin(np.radians(a)) + dy * np.cos(np.radians(a))) / 0.016) ** 2) for a in (0, 90))
    s = np.clip(bloom + 0.3 * rays, 0, 1)[..., None]
    col = col + (np.array([250, 250, 252.]) - col) * s
    img[y0:y0 + 2 * R, x0:x0 + 2 * R] = col


# ---- type
def font(fdir, size):
    f = ImageFont.truetype(os.path.join(fdir, 'Rubik[wght].ttf'), size); f.set_variation_by_axes([WEIGHT]); return f


def ink(f, ch):   # a glyph's ink box at the drawing origin (the half-coverage threshold, as measured on the photo)
    im = Image.new('L', (f.size * 3, f.size * 3)); ImageDraw.Draw(im).text((f.size, f.size), ch, font=f, fill=255, anchor='ls')
    ys, xs = np.nonzero(np.asarray(im) > 127)
    return xs.min() - f.size, xs.max() + 1 - f.size, ys.min() - f.size, ys.max() + 1 - f.size


def lockup(fdir, W, H, ox, oy, k, ss=4):
    """The screen's lockup as two coverage layers (Mitoscan, By Mitoderm Ltd) on a W×H canvas: a display-fraction point
    (fx, fy) lands at (ox + fx·k·WD/WD…): k scales the screen's lockup (1: the screen itself), (ox, oy) is where the
    display's origin would be. Drawn at ss× and box-filtered down."""
    Ws, Hs = W * ss, H * ss
    sx = lambda fx: (ox + fx * WD * k) * ss
    sy = lambda fy: (oy + fy * HD * k) * ss
    big, small = Image.new('L', (Ws, Hs)), Image.new('L', (Ws, Hs))
    cap = (BASE_Y - CAP_Y) * HD * k * ss
    f0 = font(fdir, 400); hx0, hx1, hy0, hy1 = ink(f0, 'H'); size = round(400 * cap / (hy1 - hy0))
    f = font(fdir, size); d = ImageDraw.Draw(big); widths = []
    for ch, c0, c1 in COLS:   # each glyph centred on its measured column
        a0, a1, _, _ = ink(f, ch); want = (c0 + c1) / 2 / 1600
        d.text((sx(want) - (a0 + a1) / 2, sy(BASE_Y)), ch, font=f, fill=255, anchor='ls')
        widths.append((ch, round((a1 - a0) / ss / k / WD * 1600, 1), c1 - c0 + 1))
    text, x0, x1, top, base = SUB
    fb0 = font(fdir, 400); _, _, by0, _ = ink(fb0, 'B'); bsize = round(400 * (base - top) * HD * k * ss / (0 - by0))
    fb = font(fdir, bsize)
    def run(track):   # ink extent of the line set with `track` px between glyphs, and the glyph origins
        x, xs, lo, hi = 0.0, [], 1e9, -1e9
        for ch in text:
            if ch != ' ':
                a0, a1, _, _ = ink(fb, ch); lo, hi = min(lo, x + a0), max(hi, x + a1)
            xs.append(x); x += fb.getlength(ch) + track
        return lo, hi, xs
    want = (x1 - x0) * WD * k * ss; t0, t1 = -0.2 * bsize, 0.2 * bsize
    for _ in range(40):   # the tracking that gives the measured width
        tm = (t0 + t1) / 2; lo, hi, _ = run(tm)
        if hi - lo > want: t1 = tm
        else: t0 = tm
    lo, hi, xs = run((t0 + t1) / 2); d2 = ImageDraw.Draw(small)
    for ch, x in zip(text, xs): d2.text((sx(x0) - lo + x, sy(base)), ch, font=fb, fill=255, anchor='ls')
    shrink = lambda im: np.asarray(im.resize((W, H), Image.BOX), float) / 255
    return shrink(big), shrink(small), widths, round((t0 + t1) / 2 / bsize, 4)


def stadium(W, H, ss=4):   # a stadium filling W×H (round ends on the short side), anti-aliased
    im = Image.new('L', (W * ss, H * ss)); r = min(W, H) * ss / 2
    ImageDraw.Draw(im).rounded_rectangle((0, 0, W * ss - 1, H * ss - 1), radius=r, fill=255)
    return np.asarray(im.resize((W, H), Image.BOX), float) / 255


def comp(img, a, c): return img * (1 - a[..., None]) + np.array(c, float) * a[..., None]


def glass(fdir):
    img = np.empty((GH, GW, 3)); img[:] = BORDER
    m = Image.new('L', (GW * 2, GH * 2))   # the display, its corners rounded 0.003 gw
    ImageDraw.Draw(m).rounded_rectangle((DX0 * 2, DY0 * 2, DX1 * 2, DY1 * 2), radius=0.003 * PXW * 2, fill=255)
    img = comp(img, np.asarray(m.resize((GW, GH), Image.BOX), float) / 255, DISPLAY)
    target(img)
    big, small, widths, track = lockup(fdir, GW, GH, DX0, DY0, 1.0)
    img = comp(comp(img, big, WHITE), small, GREY)
    return Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)), widths, track


# ---- the probe's panel: its stadium u 1.058…1.166 × v 0.052…0.262 gw; the lockup (the screen's, scaled) runs up the
# panel: «Mitoscan»'s cap line at u 1.0915, the lockup centred along the panel (v 0.157); caps 0.0230 gw tall
PU, PV, PK = (1.058, 1.166), (0.052, 0.262), 5926.0     # px per gw
PANEL_CAP, PANEL_TOP = 0.0230, 1.0915
PANEL_TOP_COL, PANEL_BOT_COL, PANEL_INK = (22, 22, 22), (18, 18, 18), (232, 232, 231)


def panel(fdir):
    W, H = round((PU[1] - PU[0]) * PK), round((PV[1] - PV[0]) * PK)   # 640 × 1244 (u across, v along)
    # the lockup drawn horizontally on an H × W canvas, then turned 90° counter-clockwise (it reads upward; letter tops
    # toward −u, as photographed)
    k = PANEL_CAP * PK / ((BASE_Y - CAP_Y) * HD)
    lx0, lx1 = COLS[0][1] / 1600, COLS[-1][2] / 1600          # Mitoscan's ink across the display (the longer line)
    ox = H / 2 - (lx0 + lx1) / 2 * WD * k                       # centred along the panel
    oy = (PANEL_TOP - PU[0]) * PK - CAP_Y * HD * k              # the cap line at u PANEL_TOP
    big, small, _, _ = lockup(fdir, H, W, ox, oy, k)
    yy = np.linspace(0, 1, H)[:, None, None]
    bg = np.array(PANEL_TOP_COL, float) * (1 - yy) + np.array(PANEL_BOT_COL, float) * yy
    bg = np.repeat(bg, W, 1)
    a = np.rot90(np.maximum(big, small), 1)                     # H × W after the turn
    img = comp(bg, a, PANEL_INK)
    al = stadium(W, H)
    return Image.fromarray(np.dstack([np.clip(img + 0.5, 0, 255), al * 255 + 0.5]).astype(np.uint8))


# ---- the badge: a stadium 0.135 × 0.031 gw, face #f7f7f5, «Mitoscan» #3c3c3a 0.080 gw long, centred
BW_, BH_, BK = 0.135, 0.031, 8148.0
BADGE_LEN, FACE, BINK = 0.080, (247, 247, 245), (60, 60, 58)


def badge(fdir):
    W, H = round(BW_ * BK), round(BH_ * BK)   # 1100 × 253
    lx0, lx1 = COLS[0][1] / 1600, COLS[-1][2] / 1600
    k = BADGE_LEN * BK / ((lx1 - lx0) * WD)
    ox = W / 2 - (lx0 + lx1) / 2 * WD * k
    oy = H / 2 - (CAP_Y + BASE_Y) / 2 * HD * k                  # the caps centred on the face
    big, _, _, _ = lockup(fdir, W, H, ox, oy, k)
    img = comp(np.full((H, W, 3), FACE, float), big, BINK)
    return Image.fromarray(np.dstack([np.clip(img + 0.5, 0, 255), stadium(W, H) * 255 + 0.5]).astype(np.uint8))


def grille(n=512):   # the perforated end: holes on a sunflower (Vogel) spiral, ≈ 900 of them, dark in the metal
    img = np.full((n, n), 176.0); ss = 3; N = 900; R = n * ss / 2 * 0.985
    big = Image.new('L', (n * ss, n * ss), 176); d = ImageDraw.Draw(big)
    hr = 0.0072 * n * ss   # hole radius
    for i in range(N):
        rr = R * np.sqrt((i + 0.5) / N) * 0.97; th = i * np.radians(137.508)
        x, y = n * ss / 2 + rr * np.cos(th), n * ss / 2 + rr * np.sin(th)
        d.ellipse((x - hr, y - hr, x + hr, y + hr), fill=42)
    img = np.asarray(big.resize((n, n), Image.BOX), float)
    return Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8))


def brushed(w=1024, h=64, seed=3):   # fine grain along the axis (x): noise stretched along x, tiling
    rng = np.random.default_rng(seed); a = rng.normal(0, 1, (h, w))
    a = ndimage.gaussian_filter(a, (0.6, 18), mode='wrap'); a = (a - a.min()) / (a.max() - a.min())
    return Image.fromarray((96 + a * 64 + 0.5).astype(np.uint8))


def haze(n=512, seed=7):   # a shapeless cloud: three octaves of smooth noise under a soft round fall-off
    rng = np.random.default_rng(seed); v = np.zeros((n, n))
    for s, w in ((48, 1.0), (20, 0.5), (8, 0.25)):
        v += w * ndimage.gaussian_filter(rng.normal(0, 1, (n, n)), s, mode='wrap')
    v = (v - v.mean()) / v.std()
    yy, xx = (np.mgrid[0:n, 0:n] + 0.5) / n * 2 - 1; r2 = xx ** 2 + yy ** 2
    a = np.exp(-2.6 * r2) * np.clip(1 + 0.45 * v, 0, None) * (1 - np.clip((r2 - 0.55) / 0.45, 0, 1)) ** 2
    a = a / a.max()
    lum = np.full((n, n), 255.0)
    return Image.fromarray(np.dstack([lum, a * 255 + 0.5]).astype(np.uint8), 'LA')


if __name__ == '__main__':
    fdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
    g, widths, track = glass(fdir); g.save(f'{out}/glass.png', optimize=True)
    print('Mitoscan glyph ink widths (display px of 1600: typeset vs measured):', widths)
    print('By Mitoderm Ltd: tracking', track, 'of the size')
    panel(fdir).save(f'{out}/panel.png', optimize=True)
    badge(fdir).save(f'{out}/badge.png', optimize=True)
    grille().save(f'{out}/grille.png', optimize=True)
    brushed().save(f'{out}/brushed.png', optimize=True)
    haze().save(f'{out}/haze.png', optimize=True)
    total = 0
    for n in ('glass.png', 'panel.png', 'badge.png', 'grille.png', 'brushed.png', 'haze.png'):
        im = Image.open(f'{out}/{n}'); s = os.path.getsize(f'{out}/{n}'); total += s; print(n, im.size, im.mode, s // 1024, 'KB')
    print('folder', total // 1024, 'KB')
