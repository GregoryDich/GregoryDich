"""Textures for the three.js CELLULAR AGE DEFENSE 2.5% scene (site/proto/scenes/cellular-age-defense-2-5.js), sharp at
any size: the print is typeset, not cut from the photo. Places, sizes and colours are measured on the largest packshot,
protocols/print/img/cellular-age-25.webp (308×1023, never upscaled), in edge coordinates (a pixel i spans [i, i+1)):
  the front  x 0.2 … 262.0 (the rounded edge to the right side: its middle), top y = 1.6 − 0.00449 (x − 10), foot
             y = 1018.6 + 0.01102 (x − 10) (a slight trapezoid: the right edge nearer); the photo is rectified to the
             front's 261.8 × 1019 px (a homography of these four corners) and every measure below is on that grid
  the true proportions W : H = 0.2600: the medallion, a circle, is 0.988 as wide as tall on the photo (the front seen
             ~9° off square; with D = W the side's 0.175 of the front gives 10°); the depth is not on the photo: D = W
(the scratchpad spec of 22/10, §2–§4, remeasured on the rectified grid). Typeface: Rubik (SIL OFL,
github.com/google/fonts), the closest by its shapes (vertical M, flat C/S/G terminals, oval % zeros); each line's weight
by its ink area and stems (MITODERM 470, BIOSPICULE SYSTEM 390, the band 460, BIOSPICULE SERUM 360, the framed lines 440,
the volume 400), its narrowing the median of measured / natural ink widths; every glyph's ink centre stands on its
measured centre, its cap height and baseline as measured, so the spacing is the photo's, not the font's. The estimate
sign ℮ is DejaVu Sans (Rubik has none) in its measured box. The gold monogram M is the owner's file
site/img/mitoderm-m-gold.png (566 px, reduced to 181) fitted to the printed M (least squares of the silhouettes:
x 108.5–153.8, y 55.0–101.8), filled with the print's gold #C6A87F and its DNA ladder kept as light and shade (the file
is a rendered relief: its own gold is not the print's); its stone is the print's (a flat drop, not the file's
brilliant), inked from the photo. The medallion (centre 131.38, 620.0, R 92.78, by 180 rays, rms 0.46 px): its smooth
parts — the ring's colour round the angle, the bright inner rim, the disc's light and haze — are the photo's own, ×4
(they hold no edge); its edges are drawn at the texture's scale: the dark green spicules re-inked from the photo's
strokes (each stroke's ink found against the disc's light, its edge set at half contrast with a one-texel ramp, the
light filled in under it), the ring's outer edge a circle. The packaging's vector file would replace all of it.
Writes into <out dir>:
  box-face.png    the front's colours, RGB 1060×4076 (4 texels per photo px down, 4 / 0.988 across: square on the true
                  front; ≈ 3.2 texels per key px where the box is largest, 800 frame px in a 3840 key): the paper #F4EAE1, the band #183322, the inks and golds as pipetted
  box-side.png    the plain right side, RGB 64×2048 (u: the front edge 0 → the back 1, v: top 0 → foot 1): the photo's
                  side as pipetted (#C0AF99 at the top, #BCA790 in the middle, #AE9A83 at the foot), the rounded edge's
                  light strip along the front edge, the flaps' dark seams along the top and the foot
  renew-face.webp the sibling CELL RENEW 1.5% front, rectified from protocols/print/img/cell-renew-15.webp (x −0.3 … 262.0,
                  top y 2.2 → 1.0, foot 1008.4 → 1010.5), 262×1009: as photographed, never upscaled
  derma-face.webp the DERMA RECOVERY CREAM front, cut from protocols/assets/img/derma-recovery.webp (x 11.6–624.0,
                  y 12.7–986.8; its side ≤ 5 px), 612×974
usage: python3 -I make_textures.py <font dir with Rubik[wght].ttf> <out dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
PACK = f'{REPO}/protocols/print/img/cellular-age-25.webp'
RENEW = f'{REPO}/protocols/print/img/cell-renew-15.webp'
DERMA = f'{REPO}/protocols/assets/img/derma-recovery.webp'
MFILE = f'{REPO}/site/img/mitoderm-m-gold.png'
DEJAVU = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

FW, FH = 261.8, 1019.0                  # the front, photo px
FORE = 0.988                            # the front's width on the photo over its true width: the medallion, a circle,
                                        # measures 92.26 × 93.37 px (an ellipse fit, rms 0.23 px): the front is seen ~9°
                                        # off square (the side shows 0.175 of it), so its true W : H is 0.2600
K = 4; KX, KY = K / FORE, K             # texels per photo px across and down: square texels on the true front
W, H = 1060, 4076                       # the texture
PAPER, BAND, GOLD = (244, 234, 225), (24, 51, 34), (216, 207, 160)
MITO, BLACK, FRAME, MGOLD, SPIC = (29, 42, 29), (18, 17, 8), (190, 151, 96), (198, 168, 127), (34, 49, 30)
BAND_Y = (242.28, 367.55)               # the band's edges (half contrast, both ends of the row)
FRAME_Y, FRAME_X, FRAME_W = (810.19, 880.31), (22.90, 238.86), 2.0   # the gold frame's centre lines, its line width
MED = (131.38, 619.99, 93.37)           # the medallion: centre, its outer radius (the true one: the vertical semi-axis)
M_BOX = (108.5, 153.8, 55.0, 101.8)     # the M file's box on the print (x0, x1, y0, y1)
STONE = (106, 118, 94, 104)             # the print's stone, inked from the photo (a window round it)

# the lines: (glyphs, Rubik weight, cap top, baseline, ink centres, ink widths, colour). Spaces are not glyphs; '%' is
# measured as the union of its three parts; 'fl' as one (its two letters touch on the photo)
LINES = [
    ('MITODERM', 470, 146.8, 173.0, [37.8, 62.1, 82.6, 110.0, 139.5, 167.5, 194.6, 225.0],
     [24.0, 4.8, 20.8, 21.0, 20.5, 17.5, 19.2, 24.0], MITO),
    ('BIOSPICULESYSTEM', 390, 185.8, 200.4, [43.8, 52.5, 61.5, 73.9, 86.6, 95.0, 104.2, 117.2, 130.2, 141.4, 157.6, 169.4, 181.1, 192.6, 204.2, 217.6],
     [10.0, 2.0, 10.5, 10.2, 10.2, 2.0, 11.0, 10.5, 9.0, 9.2, 10.2, 10.8, 10.2, 10.2, 9.0, 12.2], BLACK),
    ('CELLULARAGE', 460, 274.5, 296.8, [38.9, 57.2, 74.5, 90.9, 107.9, 126.8, 144.5, 164.0, 188.6, 208.1, 227.2],
     [16.8, 14.0, 13.5, 13.8, 15.8, 13.5, 18.0, 15.0, 18.2, 16.2, 13.5], GOLD),
    ('DEFENSE2.5%', 460, 313.5, 335.8, [42.4, 61.0, 78.2, 95.2, 113.8, 132.8, 150.9, 174.5, 187.1, 199.5, 219.6],
     [15.8, 14.0, 13.5, 13.5, 15.5, 16.0, 13.8, 14.5, 3.8, 14.5, 19.65], GOLD),
    ('BIOSPICULE', 360, 417.1, 436.2, [71.0, 82.0, 93.6, 109.0, 124.9, 135.2, 147.0, 162.9, 179.0, 192.6],
     [12.5, 2.0, 13.2, 12.5, 12.8, 2.5, 13.5, 12.8, 11.0, 11.2], BLACK),
    ('SERUM', 365, 446.8, 466.0, [96.8, 112.2, 127.6, 143.5, 161.8], [13.0, 11.5, 12.8, 13.0, 15.0], BLACK),
    ('ADVANCED', 440, 827.6, 840.4, [93.4, 104.6, 115.2, 125.2, 136.4, 147.4, 157.6, 168.0],
     [9.8, 8.8, 9.5, 10.0, 8.8, 8.8, 7.2, 9.0], BLACK),
    ('BIOSPICULETECHNOLOGY', 440, 849.3, 862.3, [37.5, 45.0, 52.6, 63.0, 73.5, 80.5, 88.1, 98.8, 109.1, 118.2, 130.8, 140.5, 150.4, 161.4, 172.6, 183.8, 194.1, 203.6, 214.5, 224.9],
     [8.5, 2.0, 8.8, 8.5, 8.5, 2.0, 8.8, 8.5, 7.2, 7.5, 8.5, 7.5, 8.8, 8.8, 8.8, 9.0, 7.8, 9.2, 9.0, 9.2], BLACK),
    (['3', '0', 'm', 'l', '1', '.', '0', 'fl', '.', 'o', 'z', '.'], 400, 946.7, 961.8,
     [61.9, 73.0, 91.1, 101.1, 143.9, 150.4, 158.9, 173.8, 182.0, 190.1, 200.0, 207.1],
     [9.2, 9.5, 14.2, 1.8, 5.8, 2.2, 9.8, 9.5, 2.0, 9.2, 8.0, 2.2], BLACK)]
ESTIMATE = ('℮', (113.0, 130.8, 945.2, 962.2), BLACK)   # ℮: its measured ink box
NARROW_SKIP = set('I.l')                                      # stems and dots say nothing of a line's narrowing


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
    report = []
    for text, weight, top, base, centres, widths, colour in LINES:
        cap = (base - top) * KY
        gl = [glyph(font, ch, weight) for ch in text]
        nat = [g.width * cap / gc for (g, _, gc) in gl]
        narrow = float(np.median([w * KX / n for ch, w, n in zip(text, widths, nat) if ch not in NARROW_SKIP]))
        for ch, cx, (g, gtop, gc) in zip(text, centres, gl):
            s = cap / gc; nw = 1 if ch in NARROW_SKIP else narrow
            gw, gh = max(1, round(g.width * s * nw)), max(1, round(g.height * s))
            # placed at sub-texel precision: the glyph drawn into a canvas offset by the fraction
            fx, fy = cx * KX - gw / 2, base * KY - cap + gtop * s
            a = np.asarray(g.resize((gw, gh), Image.LANCZOS)).astype(float) / 255
            a = ndimage.shift(np.pad(a, 2), (fy - np.floor(fy), fx - np.floor(fx)), order=1)
            put(canvas, np.clip(a, 0, 1), colour, int(np.floor(fx)) - 2, int(np.floor(fy)) - 2)
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
    shade = 0.84 + 0.30 * n                                               # the print's gold ± its leaf's texture (L* 61–82)
    rgb = np.clip(np.array(MGOLD, float)[None, None] * shade[..., None], 0, 255)
    alpha = np.where(solid, 1.0, 0.0)
    x0, x1, y0, y1 = M_BOX[0] * KX, M_BOX[1] * KX, M_BOX[2] * KY, M_BOX[3] * KY; w, h = round(x1 - x0), round(y1 - y0)
    rs = lambda arr: np.asarray(Image.fromarray(arr.astype(np.float32), 'F').resize((w, h), Image.LANCZOS))
    a = np.clip(rs(alpha), 0, 1); col = np.stack([rs(rgb[..., c] * alpha) for c in range(3)], -1) / np.maximum(a, 1e-3)[..., None]
    X, Y = round(x0), round(y0)
    reg = canvas[Y:Y + h, X:X + w]; reg[:] = reg * (1 - a[..., None]) + np.clip(col, 0, 255) * a[..., None]
    # the stone: the photo's own ink at half contrast, a one-texel ramp
    sx0, sx1, sy0, sy1 = round(STONE[0] * KX), round(STONE[1] * KX), STONE[2] * KY, STONE[3] * KY
    L = rect[sy0:sy1, sx0:sx1, :3] @ [0.299, 0.587, 0.114]
    d = ndimage.gaussian_filter(np.clip((233 - L) / (233 - 160), 0, 1), 0.8)
    put(canvas, np.clip((d - 0.5) * 2.2 + 0.5, 0, 1), MGOLD, sx0, sy0)


def medallion(canvas, rect):
    cx, cy, R = MED[0] * KX, MED[1] * KY, MED[2] * KY; r0 = int(R + 4)
    X0, Y0 = int(cx - r0), int(cy - r0); sl = (slice(Y0, Y0 + 2 * r0), slice(X0, X0 + 2 * r0))
    img = rect[sl][..., :3].copy(); L = img @ [0.299, 0.587, 0.114]
    yy, xx = np.mgrid[0:2 * r0, 0:2 * r0]; r = np.hypot(xx + X0 + 0.5 - cx, yy + Y0 + 0.5 - cy); th = np.arctan2(-(yy + Y0 + 0.5 - cy), xx + X0 + 0.5 - cx)
    # the spicules: dark, narrower than 8 px of the photo (what a closing of the light takes out), their darkness d
    # against the disc's light (0 the light, 1 the strokes' core #22311E); the light under them filled in from around
    # each stroke; then each stroke redrawn in the core's colour through a steeper ramp of d (an S-curve 0.15 → 0.85):
    # the photo's strokes, tips and crossings all kept, their soft edges made sharp (a ramp of ~3 texels, not ~8)
    light = ndimage.gaussian_filter(ndimage.grey_closing(L, size=(31, 31)), 3)   # the disc's light, also where strokes cross
    d = np.clip((light - L) / np.maximum(light - 45, 20), 0, 1) * np.clip((0.89 * R - r) / (0.02 * R), 0, 1)
    hole = ndimage.binary_dilation(d > 0.1, iterations=2)
    wgt = (~hole).astype(float); fill = np.stack([ndimage.gaussian_filter(img[..., c] * wgt, 9) for c in range(3)], -1) / np.maximum(ndimage.gaussian_filter(wgt, 9), 1e-3)[..., None]
    base = np.where(hole[..., None], fill, img)
    base = np.stack([ndimage.gaussian_filter(base[..., c], 1.2) for c in range(3)], -1)   # the photo's ×4 steps smoothed
    t = np.clip((d - 0.15) / 0.7, 0, 1); a_sp = t * t * (3 - 2 * t)
    # the ring's outer band: its colour round the angle (the photo's, at 0.925–0.975 R), up to a sharp circle at R
    bins = np.round((th + np.pi) / (2 * np.pi) * 360).astype(int) % 360; band = (r > 0.93 * R) & (r < 0.965 * R)
    ring = np.zeros((360, 3))
    for c in range(3):
        s = np.bincount(bins[band], img[..., c][band], 360) / np.maximum(np.bincount(bins[band], None, 360), 1)
        ring[:, c] = ndimage.gaussian_filter1d(s, 2, mode='wrap')
    t = np.clip((r - 0.955 * R) / (0.015 * R), 0, 1)[..., None]
    base = base * (1 - t) + ring[bins] * t
    med = base * (1 - a_sp[..., None]) + np.array(SPIC, float) * a_sp[..., None]
    a_out = np.clip(R + 0.5 - r, 0, 1)[..., None]                        # the outer edge: a circle, one texel of ramp
    canvas[sl] = canvas[sl] * (1 - a_out) + med * a_out


def frame(canvas):
    x0, x1 = (v * KX for v in FRAME_X); y0, y1 = (v * KY for v in FRAME_Y); hw = FRAME_W * K / 2
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
    top, mid, foot = np.array([192, 175, 153.]), np.array([188, 167, 144.]), np.array([174, 154, 131.])
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
    top = lambda x: 1.6 - 0.0044898 * (x - 10); foot = lambda x: 1018.6 + 0.0110204 * (x - 10)
    rect = rectify(PACK, [[0.2, top(0.2)], [262.0, top(262.0)], [262.0, foot(262.0)], [0.2, foot(0.2)]], (FW, FH), (KX, KY), PAPER)
    rect = np.pad(rect, ((0, max(0, H - rect.shape[0])), (0, max(0, W - rect.shape[1])), (0, 0)), mode='edge')
    face = np.zeros((H, W, 3)) + np.array(PAPER, float)
    face[int(np.ceil(BAND_Y[0] * KY)):int(np.floor(BAND_Y[1] * KY))] = BAND
    for edge, (a, b) in ((BAND_Y[0] * KY, (PAPER, BAND)), (BAND_Y[1] * KY, (BAND, PAPER))):   # the band's edges: exact coverage
        i = int(np.floor(edge)); f = edge - i; face[i] = np.array(a, float) * f + np.array(b, float) * (1 - f)
    report = typeset(face, font)
    monogram(face, rect); medallion(face, rect); frame(face)
    Image.fromarray(np.clip(np.round(face), 0, 255).astype(np.uint8)).save(f'{out}/box-face.png', optimize=True)
    side().save(f'{out}/box-side.png', optimize=True)
    renew = rectify(RENEW, [[-0.3, 2.2], [262.0, 1.0], [262.0, 1010.5], [-0.3, 1008.4]], (262.3, 1008.9), 1, PAPER)
    Image.fromarray(np.clip(np.round(renew[..., :3]), 0, 255).astype(np.uint8)).save(f'{out}/renew-face.webp', quality=92, method=6)
    derma = rectify(DERMA, [[11.6, 12.7], [624.0, 12.7], [624.0, 986.8], [11.6, 986.8]], (612.4, 974.1), 1, (243, 233, 223))
    Image.fromarray(np.clip(np.round(derma[..., :3]), 0, 255).astype(np.uint8)).save(f'{out}/derma-face.webp', quality=92, method=6)
    print('\n'.join(report))
    for n in ('box-face.png', 'box-side.png', 'renew-face.webp', 'derma-face.webp'):
        im = Image.open(f'{out}/{n}'); print(n, im.size, os.path.getsize(f'{out}/{n}') // 1024, 'KB')
