"""Textures for the three.js CELL RENEW 1.5% scene (site/proto/scenes/cell-renew-1-5.js), sharp at any size: the print
is typeset, not cut from the photo. The box is the sibling CELLULAR AGE DEFENSE 2.5%'s (one series, one 30 ml box, one
print template: design/cellular-age-defense-2-5/make_textures.py), so this follows that script step by step. Places,
sizes and colours are measured on the largest packshot, protocols/print/img/cell-renew-15.webp (309×1012, never
upscaled), in edge coordinates (a pixel i spans [i, i+1)):
  the front  x 0.05 … 261.8 (the band's print ends at the fold to the right side: x 260 is band, 261 mixed, 262 side),
             top y 2.55 → 1.25 and foot y 1008.6 → 1011.1 left to right (50 % alpha; a slight trapezoid, the right edge
             nearer); the photo is rectified to the front's 261.75 × 1008 px (a homography of these four corners) and
             every measure below is on that grid
  the true proportions W : H = 0.2597, as photographed: the owner's M file sits on the print at its own proportions
             (scale 0.081 across and down), so this photo is not squeezed (the 2.5%'s is, by 1.2 %); the medallion on
             this print is a little taller than wide (182 × 188 px, an ellipse to ±1 px) and is kept as printed. The
             depth is not on the photo: D = W, as for the 2.5% (its right side shows 0.176 of the front: about 10°)
Typeface: Rubik (SIL OFL, github.com/google/fonts), the closest by its shapes (vertical M, flat C/S terminals, oval
zeros), as on the 2.5%; each block's weight by its ink area and stems (MITODERM 470, BIOSPICULE SYSTEM 390, the band
460, BIOSPICULE SERUM 365, the framed lines 455, the volume 400; MITODERM and the band's gold by their ink summed
unclipped against each picture's own paper and ink plateau, so the photo's blur and sharpening cancel out: texture :
photo MITODERM 1.03 (0.975 clipped at one ink level), CELL RENEW 1.00, 1.5% 1.00 (0.98, 0.94 at one gold level: the
photo's gold has a gradient)), each block's narrowing (its lines share one size and face)
the median of measured / natural ink widths; every glyph's ink centre stands on its measured centre, its cap height and baseline as measured, so the
spacing is the photo's, not the font's. The band's gold letters have a thin dark olive edge on the print (#5C633E, about
1 photo px outside the gold): typeset too. The estimate sign ℮ is DejaVu Sans (Rubik has none) in its measured box; the
volume line reads «30 ml ℮ 1.0 fl.oz.» as printed (packaging-text.json writes «30ml»: the print has the space).
The gold monogram M is the owner's file site/img/mitoderm-m-gold.png (566 px, reduced to 184) fitted to the printed M
(least squares of the silhouettes: x 109.0–154.85, y 53.5–102.1), filled with the print's gold and its DNA ladder kept
as light and shade; its stone is the print's (a flat drop, not the file's brilliant), inked from the photo. The
medallion (centre 131.1, 625.2; semi-axes 91.0 across, 94.05 down, from 36 rays at half contrast) is the print's own
picture: its smooth parts (the ring's colour round the angle, the bright inner rim, the disc's light) are the photo's,
×4; its dark green spicules keep the photo's strokes with their soft edges made steep (their darkness against the
disc's light through an S-curve, the light filled in under them); the ring's outer band is its own colour round the
angle up to a sharp edge. It is the photo's picture, not a redrawing: the scene keeps the opaque box at most 630 frame
px tall (1008 px in a 3840 key, the photo's own front), so the medallion is never drawn above the photo's pixels. The
packaging's print (vector) file would replace all of it and let the box be shown larger.
Writes into <out dir>:
  box-face.webp   the front's colours, RGB 1048×4032, lossless (4 texels per photo px; 4 per key px where the box is
                  largest): the paper #F3E9E0, the band #5A755F, the inks and golds as pipetted (MITODERM #1C2819, the
                  black #10100A, the band's gold #DED6A6 with its edge #5C633E, the frame #B79873 1.8 px, the M #B59671,
                  the spicules' core #243220)
  box-side.png    the plain right side, RGB 64×2048 (u: the front edge 0 → the back 1, v: top 0 → foot 1): the photo's
                  side as pipetted (#C0AE97 at the top, #BEA991 in the middle, #B4A088 at the foot), the rounded edge's
                  light strip along the front edge, the flaps' seams along the top and the foot (as the 2.5%'s)
  cad-face.webp   the next step CELLULAR AGE DEFENSE 2.5%'s front, rectified from protocols/print/img/cellular-age-25.webp
                  (its corners as in the 2.5%'s script), 262×1019, as photographed: never upscaled, never softened
                  (everything HD: the scene shows it behind by its depth, its size and a dimmer glow, not by a blur)
  derma-face.webp the DERMA RECOVERY CREAM front, cut from protocols/assets/img/derma-recovery.webp (x 11.6–624.0,
                  y 12.7–986.8; its side ≤ 5 px), 612×974, as the 2.5%'s page has it
usage: python3 -I make_textures.py <font dir with Rubik[wght].ttf> <out dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
PACK = f'{REPO}/protocols/print/img/cell-renew-15.webp'
CAD = f'{REPO}/protocols/print/img/cellular-age-25.webp'
DERMA = f'{REPO}/protocols/assets/img/derma-recovery.webp'
MFILE = f'{REPO}/site/img/mitoderm-m-gold.png'
DEJAVU = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

XL, XR = 0.05, 261.8                    # the front's left and right edges, photo px
FW, FH = XR - XL, 1008.0                # the front, photo px
W, H = 1048, 4032                       # the texture: 4 texels per photo px down, as near 4 across
KX, KY = W / FW, H / FH
PAPER, BAND, GOLD, KANT = (243, 233, 224), (90, 117, 95), (222, 214, 166), (92, 99, 62)
MITO, BLACK, FRAME, MGOLD, SPIC = (28, 40, 25), (16, 16, 10), (183, 152, 115), (185, 152, 115), (36, 50, 32)
BAND_Y = (252.71, 361.42)               # the band's edges (half contrast, both ends of the row)
FRAME_Y, FRAME_X, FRAME_W = (807.09, 878.08), (27.28, 235.96), 1.8   # the gold frame's centre lines, its line width
MED = (131.1, 625.2, 91.0, 94.05)       # the medallion: centre, semi-axes across and down (its outer edge)
M_BOX = (109.0, 154.85, 53.5, 102.1)    # the M file's box on the print (x0, x1, y0, y1)
STONE = (106, 119, 93, 104)             # the print's stone, inked from the photo (a window round it)

# the lines: (glyphs, Rubik weight, cap top, baseline, ink centres, ink widths, colour, edged). Spaces are not glyphs;
# '%' is measured as the union of its three parts. Measured at half contrast on the rectified front (×4)
LINES = [
    ('MITODERM', 470, 149.5, 176.2, [37.8, 62.0, 83.0, 110.2, 140.1, 168.1, 195.5, 225.9],
     [24.5, 4.5, 20.5, 21.0, 20.8, 17.8, 20.0, 24.2], MITO, False),
    ('BIOSPICULESYSTEM', 390, 188.85, 203.75, [42.1, 51.2, 60.5, 73.5, 86.5, 95.0, 104.5, 117.9, 131.0, 142.2, 158.8, 170.8, 183.0, 194.6, 206.6, 220.1],
     [10.2, 2.0, 11.0, 10.5, 10.5, 2.0, 11.0, 10.8, 9.0, 9.5, 10.5, 11.0, 10.5, 10.8, 9.2, 12.2], BLACK, False),
    ('CELLRENEW', 460, 281.9, 305.7, [44.0, 65.1, 84.9, 103.8, 131.0, 151.5, 172.5, 194.5, 217.5],
     [19.0, 15.8, 15.2, 15.0, 17.5, 15.5, 17.5, 15.5, 24.0], GOLD, True),
    ('1.5%', 460, 318.2, 342.2, [102.5, 115.4, 129.8, 152.5], [11.5, 4.8, 17.0, 23.0], GOLD, True),
    ('BIOSPICULE', 365, 421.0, 442.5, [63.9, 75.8, 88.8, 106.9, 124.6, 136.2, 149.5, 167.5, 185.9, 201.0],
     [14.2, 2.5, 15.0, 14.2, 14.2, 2.5, 15.0, 14.5, 12.2, 12.5], BLACK, False),
    ('SERUM', 365, 455.1, 476.95, [94.2, 111.2, 128.2, 146.2, 166.4], [14.5, 12.5, 14.0, 14.5, 16.8], BLACK, False),
    ('ADVANCED', 455, 825.8, 838.5, [95.4, 106.2, 116.5, 126.4, 137.5, 148.2, 158.1, 168.2],
     [9.8, 8.5, 9.0, 9.8, 8.5, 8.5, 7.2, 8.5], BLACK, False),
    ('BIOSPICULETECHNOLOGY', 455, 847.5, 860.5, [41.6, 48.9, 56.1, 66.1, 76.4, 83.1, 90.5, 100.8, 110.6, 119.6, 131.9, 141.2, 150.8, 161.2, 172.2, 182.9, 192.9, 202.0, 212.6, 222.5],
     [8.2, 1.8, 8.8, 8.2, 8.2, 1.8, 8.5, 8.0, 6.8, 7.2, 8.8, 7.0, 8.5, 8.5, 8.5, 8.8, 7.2, 9.0, 8.8, 9.0], BLACK, False),
    (['3', '0', 'm', 'l', '1', '.', '0', 'f', 'l', '.', 'o', 'z', '.'], 400, 937.8, 951.6,
     [66.2, 76.9, 94.2, 103.9, 139.6, 146.0, 153.6, 166.8, 171.8, 176.5, 183.8, 193.4, 200.6],
     [8.5, 8.8, 13.0, 1.8, 5.2, 2.0, 8.8, 7.0, 1.5, 2.2, 8.5, 7.8, 1.8], BLACK, False)]
ESTIMATE = ('℮', (112.5, 128.0, 936.2, 952.0), BLACK)    # ℮: its measured ink box
BLOCK = {'MITODERM': 0, 'BIOSPICULESYSTEM': 1, 'CELLRENEW': 2, '1.5%': 2, 'BIOSPICULE': 3, 'SERUM': 3, 'ADVANCED': 4,
         'BIOSPICULETECHNOLOGY': 4, '30ml1.0fl.oz.': 5}
NARROW_SKIP = set('I.l')                                   # stems and dots say nothing of a line's narrowing
EDGE = 1.0                                                 # the gold's dark edge, photo px outside the gold


def homography(a, b):   # the 3×3 map taking the four points a onto b
    A = []
    for (x, y), (u, v) in zip(a, b):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y, -u], [0, 0, 0, x, y, 1, -v * x, -v * y, -v]]
    _, _, vt = np.linalg.svd(np.array(A, float)); return vt[-1].reshape(3, 3) / vt[-1, -1]


def rectify(path, corners, size, k, under):   # the quad `corners` (TL TR BR BL, edge coordinates) onto size·k texels,
    src = Image.open(path).convert('RGBA')         # the photo first laid on its paper (its cut-out edge is not black)
    bg = Image.new('RGBA', src.size, tuple(under) + (255,)); bg.alpha_composite(src)
    im = np.asarray(bg).astype(float)
    kx, ky = k if isinstance(k, tuple) else (k, k)
    w, h = int(round(size[0] * kx)), int(round(size[1] * ky))
    Hinv = homography([[0, 0], [size[0], 0], list(size), [0, size[1]]], corners)
    uu, vv = np.meshgrid((np.arange(w) + 0.5) / kx, (np.arange(h) + 0.5) / ky)
    q = Hinv @ np.stack([uu.ravel(), vv.ravel(), np.ones(uu.size)])
    xs, ys = q[0] / q[2] - 0.5, q[1] / q[2] - 0.5   # pixel centres
    return np.stack([ndimage.map_coordinates(im[..., c], [ys, xs], order=3, mode='nearest').reshape(h, w) for c in range(4)], -1)


def glyph(font, ch, weight, size=480):   # a glyph's alpha cropped to its ink, its ink top below the cap line, the cap px
    f = ImageFont.truetype(font, size)
    if weight: f.set_variation_by_axes([weight])
    im = Image.new('L', (1400, 1000)); ImageDraw.Draw(im).text((300, 200), ch, font=f, fill=255)
    hh = Image.new('L', (1400, 1000)); ImageDraw.Draw(hh).text((300, 200), 'H', font=f, fill=255)
    hy = np.nonzero(np.asarray(hh).max(1))[0]; a = np.asarray(im); ys, xs = np.nonzero(a > 3)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)), ys.min() - hy[0], hy[-1] + 1 - hy[0]


def put(canvas, alpha, colour, x0, y0):   # composite a colour through an alpha (float 0…1) at texel (x0, y0)
    h, w = alpha.shape; X0, Y0 = max(0, x0), max(0, y0); X1, Y1 = min(canvas.shape[1], x0 + w), min(canvas.shape[0], y0 + h)
    a = alpha[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0, None]
    canvas[Y0:Y1, X0:X1] = canvas[Y0:Y1, X0:X1] * (1 - a) + np.array(colour, float) * a


def typeset(canvas, font):
    report, P = [], 8
    rr = EDGE * KY; yy, xx = np.mgrid[-int(rr) - 1:int(rr) + 2, -int(rr) - 1:int(rr) + 2]
    disc = np.hypot(xx, yy) <= rr                                     # the gold's edge: the glyph grown by EDGE
    ratios = {}   # a block's lines share one size and face on the print: one narrowing per block, from all its glyphs
    for text, weight, top, base, centres, widths, colour, edged in LINES:
        cap = (base - top) * KY
        for ch, w in zip(text, widths):
            if ch not in NARROW_SKIP:
                g, _, gc = glyph(font, ch, weight); ratios.setdefault(BLOCK[''.join(text)], []).append(w * KX / (g.width * cap / gc))
    for text, weight, top, base, centres, widths, colour, edged in LINES:
        cap = (base - top) * KY
        gl = [glyph(font, ch, weight) for ch in text]
        narrow = float(np.median(ratios[BLOCK[''.join(text)]]))
        placed = []
        for ch, cx, (g, gtop, gc) in zip(text, centres, gl):
            s = cap / gc; nw = 1 if ch in NARROW_SKIP else narrow
            gw, gh = max(1, round(g.width * s * nw)), max(1, round(g.height * s))
            # placed at sub-texel precision: the glyph drawn into a canvas offset by the fraction
            fx, fy = cx * KX - gw / 2, base * KY - cap + gtop * s
            a = np.asarray(g.resize((gw, gh), Image.LANCZOS)).astype(float) / 255
            a = np.clip(ndimage.shift(np.pad(a, P), (fy - np.floor(fy), fx - np.floor(fx)), order=1), 0, 1)
            placed.append((a, int(np.floor(fx)) - P, int(np.floor(fy)) - P))
        if edged:   # every edge first, then the golds over them
            for a, x, y in placed: put(canvas, ndimage.maximum_filter(a, footprint=disc), KANT, x, y)
        for a, x, y in placed: put(canvas, a, colour, x, y)
        report.append(f'{"".join(text)} w{weight} narrow {narrow:.3f}')
    ch, (x0, x1, y0, y1), colour = ESTIMATE
    g, _, _ = glyph(DEJAVU, ch, None)
    a = np.asarray(g.resize((round((x1 - x0) * KX), round((y1 - y0) * KY)), Image.LANCZOS)).astype(float) / 255
    put(canvas, a, colour, round(x0 * KX), round(y0 * KY))
    return report


def monogram(canvas, rect):
    m = Image.open(MFILE).convert('RGBA'); A = np.asarray(m.getchannel('A')).astype(float) / 255
    A[500:, :90] = 0                                                      # the file's brilliant: the print's stone instead
    lum = np.asarray(m.convert('L')).astype(float)
    solid = ndimage.binary_closing(A > 0.5, structure=np.ones((13, 13)), iterations=1) | (A > 0.5)   # the ladder's gaps closed:
    solid = ndimage.binary_fill_holes(solid)                              # the printed leaf is filled
    v = lum[A > 0.5]; lo, hi = np.percentile(v, 5), np.percentile(v, 95)
    n = np.where(A > 0.5, np.clip((lum - lo) / (hi - lo), 0, 1), 0.85)    # the relief's light and shade, the gaps light
    shade = 0.86 + 0.26 * n                                               # the print's gold ± its leaf's texture (p10 #9B8060,
    rgb = np.clip(np.array(MGOLD, float)[None, None] * shade[..., None], 0, 255)   # p90 #C8A983 on the photo)
    alpha = np.where(solid, 1.0, 0.0)
    x0, x1, y0, y1 = M_BOX[0] * KX, M_BOX[1] * KX, M_BOX[2] * KY, M_BOX[3] * KY; w, h = round(x1 - x0), round(y1 - y0)
    rs = lambda arr: np.asarray(Image.fromarray(arr.astype(np.float32), 'F').resize((w, h), Image.LANCZOS))
    a = np.clip(rs(alpha), 0, 1); col = np.stack([rs(rgb[..., c] * alpha) for c in range(3)], -1) / np.maximum(a, 1e-3)[..., None]
    X, Y = round(x0), round(y0)
    reg = canvas[Y:Y + h, X:X + w]; reg[:] = reg * (1 - a[..., None]) + np.clip(col, 0, 255) * a[..., None]
    # the stone: the photo's own ink at half contrast, a one-texel ramp
    sx0, sx1, sy0, sy1 = round(STONE[0] * KX), round(STONE[1] * KX), round(STONE[2] * KY), round(STONE[3] * KY)
    L = rect[sy0:sy1, sx0:sx1, :3] @ [0.299, 0.587, 0.114]
    d = ndimage.gaussian_filter(np.clip((234 - L) / (234 - 160), 0, 1), 0.8)
    put(canvas, np.clip((d - 0.5) * 2.2 + 0.5, 0, 1), MGOLD, sx0, sy0)


def medallion(canvas, rect):
    cx, cy, A, B = MED[0] * KX, MED[1] * KY, MED[2] * KX, MED[3] * KY; r0 = int(max(A, B) + 4)
    X0, Y0 = int(cx - r0), int(cy - r0); sl = (slice(Y0, Y0 + 2 * r0), slice(X0, X0 + 2 * r0))
    img = rect[sl][..., :3].copy(); L = img @ [0.299, 0.587, 0.114]
    yy, xx = np.mgrid[0:2 * r0, 0:2 * r0]; dx, dy = xx + X0 + 0.5 - cx, yy + Y0 + 0.5 - cy
    rn = np.hypot(dx / A, dy / B); th = np.arctan2(-dy / B, dx / A)   # the radius as a share of the edge's, its angle
    R = 0.5 * (A + B)                                                  # texels per unit of rn (for widths in texels)
    # the spicules: dark, narrower than 8 px of the photo (what a closing of the light takes out), their darkness d
    # against the disc's light (0 the light, 1 the strokes' core); the light under them filled in from around each
    # stroke; then each stroke redrawn in the core's colour through a steeper ramp of d (an S-curve 0.15 → 0.85): the
    # photo's strokes, tips and crossings all kept, their soft edges made sharp (a ramp of ~3 texels, not ~8)
    light = ndimage.gaussian_filter(ndimage.grey_closing(L, size=(31, 31)), 3)
    d = np.clip((light - L) / np.maximum(light - 45, 20), 0, 1) * np.clip((0.89 - rn) / 0.02, 0, 1)
    hole = ndimage.binary_dilation(d > 0.1, iterations=2)
    wgt = (~hole).astype(float); fill = np.stack([ndimage.gaussian_filter(img[..., c] * wgt, 9) for c in range(3)], -1) / np.maximum(ndimage.gaussian_filter(wgt, 9), 1e-3)[..., None]
    base = np.where(hole[..., None], fill, img)
    base = np.stack([ndimage.gaussian_filter(base[..., c], 1.2) for c in range(3)], -1)   # the photo's ×4 steps smoothed
    t = np.clip((d - 0.15) / 0.7, 0, 1); a_sp = t * t * (3 - 2 * t)
    # the ring's outer band: its colour round the angle (the photo's, at 0.93–0.965 of the edge), from 0.955 up to a
    # sharp edge at 1
    bins = np.round((th + np.pi) / (2 * np.pi) * 360).astype(int) % 360; band = (rn > 0.93) & (rn < 0.965)
    ring = np.zeros((360, 3))
    for c in range(3):
        s = np.bincount(bins[band], img[..., c][band], 360) / np.maximum(np.bincount(bins[band], None, 360), 1)
        ring[:, c] = ndimage.gaussian_filter1d(s, 2, mode='wrap')
    t = np.clip((rn - 0.955) / 0.015, 0, 1)[..., None]
    base = base * (1 - t) + ring[bins] * t
    med = base * (1 - a_sp[..., None]) + np.array(SPIC, float) * a_sp[..., None]
    a_out = np.clip((1 - rn) * R + 0.5, 0, 1)[..., None]                 # the outer edge: one texel of ramp
    canvas[sl] = canvas[sl] * (1 - a_out) + med * a_out


def frame(canvas):
    x0, x1 = (v * KX for v in FRAME_X); y0, y1 = (v * KY for v in FRAME_Y); hw = FRAME_W * KY / 2
    yy, xx = np.mgrid[0:canvas.shape[0], 0:canvas.shape[1]] + 0.5
    sl = (slice(int(y0 - hw - 2), int(y1 + hw + 3)), slice(int(x0 - hw - 2), int(x1 + hw + 3)))
    X, Y = xx[sl], yy[sl]
    cov = lambda v, c: np.clip(hw + 0.5 - np.abs(v - c), 0, 1)
    inside = lambda v, a, b: np.clip(np.minimum(v - (a - hw) + 0.5, (b + hw) - v + 0.5), 0, 1)
    a = np.maximum.reduce([cov(Y, y0) * inside(X, x0, x1), cov(Y, y1) * inside(X, x0, x1), cov(X, x0) * inside(Y, y0, y1), cov(X, x1) * inside(Y, y0, y1)])
    canvas[sl] = canvas[sl] * (1 - a[..., None]) + np.array(FRAME, float) * a[..., None]


def side():   # the right side as photographed (no print reaches it)
    h, w = 2048, 64
    v = (np.arange(h) + 0.5) / h
    top, mid, foot = np.array([192, 174, 151.]), np.array([190, 169, 145.]), np.array([180, 160, 136.])
    col = np.where(v[:, None] < 0.5, top + (mid - top) * (v[:, None] / 0.5), mid + (foot - mid) * ((v[:, None] - 0.5) / 0.5))
    img = np.repeat(col[:, None, :], w, 1)
    u = (np.arange(w) + 0.5) / w
    img = img * (1 - 0.6 * np.clip(1 - u / 0.02, 0, 1)[None, :, None]) + np.array([211, 193, 179.]) * 0.6 * np.clip(1 - u / 0.02, 0, 1)[None, :, None]
    seam = lambda c, hw: np.clip(1 - np.abs(v - c) / hw, 0, 1)
    flap = np.maximum(seam(0.0025, 0.0025), seam(0.9975, 0.0025))       # the flaps' edges: light
    dark = np.maximum(seam(0.0055, 0.0012), seam(0.9945, 0.0012))       # their seams: dark
    img = img * (1 - 0.5 * flap[:, None, None]) + np.array([214, 200, 182.]) * 0.5 * flap[:, None, None]
    img = img * (1 - 0.6 * dark[:, None, None]) + np.array([90, 77, 64.]) * 0.6 * dark[:, None, None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


if __name__ == '__main__':
    fdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
    font = os.path.join(fdir, 'Rubik[wght].ttf')
    top = lambda x: 2.55 + (1.25 - 2.55) * (x - XL) / (XR - XL); foot = lambda x: 1008.6 + (1011.1 - 1008.6) * (x - XL) / (XR - XL)
    rect = rectify(PACK, [[XL, top(XL)], [XR, top(XR)], [XR, foot(XR)], [XL, foot(XL)]], (FW, FH), (KX, KY), PAPER)
    rect = np.pad(rect, ((0, max(0, H - rect.shape[0])), (0, max(0, W - rect.shape[1])), (0, 0)), mode='edge')[:H, :W]
    face = np.zeros((H, W, 3)) + np.array(PAPER, float)
    face[int(np.ceil(BAND_Y[0] * KY)):int(np.floor(BAND_Y[1] * KY))] = BAND
    for edge, (a, b) in ((BAND_Y[0] * KY, (PAPER, BAND)), (BAND_Y[1] * KY, (BAND, PAPER))):   # the band's edges: exact coverage
        i = int(np.floor(edge)); f = edge - i; face[i] = np.array(a, float) * f + np.array(b, float) * (1 - f)
    report = typeset(face, font)
    monogram(face, rect); medallion(face, rect); frame(face)
    Image.fromarray(np.clip(np.round(face), 0, 255).astype(np.uint8)).save(f'{out}/box-face.webp', lossless=True, quality=100, method=6)
    side().save(f'{out}/box-side.png', optimize=True)
    ct = lambda x: 1.6 - 0.0044898 * (x - 10); cf = lambda x: 1018.6 + 0.0110204 * (x - 10)   # the 2.5%'s corners (its script)
    cad = rectify(CAD, [[0.2, ct(0.2)], [262.0, ct(262.0)], [262.0, cf(262.0)], [0.2, cf(0.2)]], (261.8, 1019.0), 1, PAPER)
    Image.fromarray(np.clip(np.round(cad[..., :3]), 0, 255).astype(np.uint8)).save(f'{out}/cad-face.webp', quality=92, method=6)
    derma = rectify(DERMA, [[11.6, 12.7], [624.0, 12.7], [624.0, 986.8], [11.6, 986.8]], (612.4, 974.1), 1, (243, 233, 223))
    Image.fromarray(np.clip(np.round(derma[..., :3]), 0, 255).astype(np.uint8)).save(f'{out}/derma-face.webp', quality=92, method=6)
    print('\n'.join(report))
    for n in ('box-face.webp', 'box-side.png', 'cad-face.webp', 'derma-face.webp'):
        im = Image.open(f'{out}/{n}'); print(n, im.size, os.path.getsize(f'{out}/{n}') // 1024, 'KB')
