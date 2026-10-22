"""Textures for the three.js DERMA RECOVERY CREAM scene (site/proto/scenes/derma-recovery-cream.js), sharp at any size:
the print is typeset, not cut from the photo. As the sibling pages of the BIOSPICULE line (design/cell-renew-1-5,
cellular-age-defense-2-5, micro-boost-10: their make_textures.py), step by step.

The box's front: the current print (the sage band), measured on protocols/assets/img/derma-recovery.webp (642×1000,
the front square to the camera), in edge coordinates (a pixel i spans [i, i+1)):
  the front  x 11.6 … 627.4, y 12.8 … 987.0 (half alpha; the right 2 px of the dark rounded edge left out, so the
             print's own axis, x 319.5 for the M, the frame and every centred line, is the front's middle), 615.8 × 974.2:
             W : H 0.6321. The depth is not on any photo of this print: D = W (the old ¾ packshot,
             protocols/print/img/derma-recovery.webp, agrees within its error; its dark band is the old print and is
             not used)
Typeface: Rubik (SIL OFL, github.com/google/fonts), the closest by its shapes (as on the sibling boxes: vertical M, flat
C/S terminals); every line fitted on the photo (tools of 22/10): its em size and baseline by least squares of every
glyph's half-contrast ink top and foot (rms 0.05–0.15 px), its narrowing the median of measured / natural glyph
widths; every glyph's ink centroid (not its box's middle: L, E, r, 1 are not symmetric) stands on its measured
(ink-weighted) centroid, so the spacing is the photo's, not the font's (the 3840 key, rectified onto the packshot: every
glyph within 0.5 photo px). The weights are fitted on the rendered key, not on the texture: the GPU's linear-light
minification and the shading thin the small black lines by a quarter, so a weight fitted on the texture alone (the
first fit: ink 0.97–1.02 there) drew them 26–30 % light; on the key (the front 960 px tall, rectified onto the
packshot's pixels) every dark line's half-contrast ink area is now 0.99–1.07 of the packshot's and its ink sum 0.86–0.96
(the rest: the print's near-black cores, which a minified texture cannot reach). The estimate sign ℮ is DejaVu Sans set
into its measured ink box (the print's ℮ is wider than Rubik's).
Colours pipetted (inner pixels of each stroke): the paper #F3E9DF, the band #889881, MITODERM #0F1C13, SNAIL COLLAGEN
#122B1B, the thin black lines #0A0805. The band's gold and the frame's gold are not flat on the print: both run lighter
to darker from left to right (the paper beside them does not: it is the print, not light), set as measured per 50 and
40 photo px (the band's letters #F4D990 → #EDC56B, the frame #D1B68C → #9C6A30).
The gold monogram M is the owner's file site/img/mitoderm-m-gold.png (566×600, reduced), fitted to the printed M's ink
box (x 281.57–353.88, y 75.23–149.07: the print's M is 4 % wider than the file), its colours scaled to the print's
median gold. The illustration (the pearl sphere and the cream swirl) is the photo's own picture, laid on the typeset
paper with a soft edge: the scene keeps the opaque box at most 600 frame px tall (960 px in a 3840 key, under the
photo's 974), so it is never drawn above the photo's pixels; the packaging's vector file would replace it.

The jar's print: no packshot of the jar exists, only the owner's two small photos (Figma: photo 1, the closed jar,
88×124; photo 73, the open jar and its lid beside it, 59×83). Its places (in jar diameters Ø; φ the angle from the
front, y the height over the foot) are read off photo 1 within ±1 photo px (±0.017 Ø; the jar x 14.5…73.3, its axis
x 43.9: sin φ = (x − 43.9) / 29.4, y = (105.4 − row) / 58.8); its text is site/packaging-text.json's, set in the box's
typography (each line that the box has too keeps the box's measured spacing, scaled): vertical, reading upward,
MITODERM (columns 22–25: φ −42.8°, cap 0.080 Ø) and BIOSPICULE SYSTEM (columns 27–29: φ −31.6°, cap 0.047 Ø) over
y 0.089…0.721; the gold M (φ +1°, y 0.665, 0.067 Ø tall); DERMA / RECOVERY / CREAM (cap 0.035, baselines 0.558 /
0.512 / 0.466); SNAIL COLLAGEN (cap 0.031, baseline 0.389, φ −2.5°); the thin frame (51.3° wide about φ +1.2°,
y 0.232…0.332, 0.004 Ø) with its two lines; MADE IN KOREA (cap 0.028, baseline 0.154); 50 ml ℮ 1.69 fl.oz. (cap
0.025, baseline 0.080). All black (#121212 on the photo) but the M.

The S5 neighbours (the line's other boxes, as photographed): CELL RENEW 1.5%, CELLULAR AGE DEFENSE 2.5% and
MICRO BOOST 10%, each rectified from its largest packshot (protocols/print/img/*.webp, the corners as their own pages'
scripts measured them) at 1 texel per photo px: never upscaled, never softened (the scene draws the home branch at most
420 frame px tall and MICRO BOOST at most 440, on a phone: ≤ 672 and 704 px in a 3840 key, under the photos' 1008–1019
and 1243), their front and their right side as photographed side by side in one picture (u: the front 0…f, the side
f…1).
Writes into <out dir>:
  box-face.webp  the DERMA front, RGB 1536×2430 (2.494 texels per photo px), lossless
  box-side.png   the plain left side, RGB 64×2048 (u: the front edge 0 → the back 1, v: top 0 → foot 1): the paper, the
                 rounded fold's light along the front edge, the flaps' seams along the top and the foot (as the old ¾
                 packshot shows them: a dark gap ≈ 0.001 H, the flap's strip ≈ 0.006 H)
  jar-label.png  the jar's print, RGBA 1501×1475 (2048 texels per Ø; u: φ −50° → +34°, v: y 0.76 → 0.04): black ink in
                 the alpha, the M in its colours
  renew.webp, cad.webp, mb.webp   the neighbours' fronts and sides (their front's share of the width printed below)
usage: python3 -I make_textures.py <font dir with Rubik[wght].ttf> <out dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
FRONT = f'{REPO}/protocols/assets/img/derma-recovery.webp'
MFILE = f'{REPO}/site/img/mitoderm-m-gold.png'
DEJAVU = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

XL, XR, YT, YB = 11.6, 627.4, 12.8, 987.0           # the front on the packshot (photo px)
H = 2430; K = H / (YB - YT); W = round((XR - XL) * K)  # 2.4944 texels per photo px: 1536 × 2430
PAPER, BAND = (243.5, 232.7, 222.8), (136.0, 151.6, 129.0)
MITO, SNAIL, BLACK = (15, 28, 19), (18, 43, 27), (10, 8, 5)
BAND_Y = (325.1, 482.0)                               # the band's edges (half contrast, both margins agree ±0.03)
# the band's gold: inner pixels (eroded 1 px) per 50 photo px across, at the bins' middles
GOLD = [(120, (244, 217, 144)), (170, (243, 216, 142)), (220, (243, 214, 138)), (270, (242, 211, 132)), (320, (241, 207, 125)),
        (370, (240, 204, 118)), (420, (239, 202, 116)), (470, (237, 199, 112)), (520, (237, 197, 107))]
# the gold frame: centre lines (dip centroids), width; its colour per 40 px of the top line, the sides' darkest pixels
FRAME_Y, FRAME_X, FRAME_W = (778.83, 865.03), (125.58, 514.16), 2.5
FGOLD = [(125.6, (209, 182, 140)), (150, (213, 182, 137)), (190, (206, 173, 125)), (230, (198, 164, 107)), (270, (194, 156, 96)),
         (310, (189, 150, 81)), (350, (175, 131, 64)), (390, (171, 123, 54)), (430, (165, 117, 48)), (470, (162, 113, 44)),
         (514.2, (156, 106, 48))]
M_BOX = (281.57, 353.88, 75.23, 149.07)               # the printed M's ink box (half contrast)
M_PRINT = (171, 137, 86)                              # its median colour on the photo (the file's: #B89A67)
ILLU = (140, 505, 562, 774)                           # the illustration's window on the photo (x0, x1, y0, y1)
EST = (278.67, 305.79, 901.8, 929.97)                 # the estimate sign's ink box

# the lines: (glyphs, Rubik weight, cap top, baseline, ink centres, ink widths, colour or 'gold'), all fitted on the photo
LINES = [
    ('MITODERM', 550, 199.58, 243.15, [165.48, 204.84, 238.94, 282.69, 329.95, 374.73, 420.78, 471.43],
     [39.17, 8.37, 33.25, 34.91, 33.64, 29.31, 33.11, 39.21], MITO),
    ('BIOSPICULESYSTEM', 450, 260.16, 282.80, [174.92, 189.62, 204.92, 225.86, 245.37, 260.42, 274.21, 297.15, 315.04, 335.07,
                                               363.92, 383.14, 402.84, 421.75, 439.67, 463.40],
     [16.62, 2.95, 17.55, 16.20, 16.19, 2.86, 17.28, 17.10, 14.36, 14.56, 16.24, 17.71, 16.28, 16.71, 14.85, 19.54], BLACK),
    ('DERMARECOVERY', 575, 357.08, 397.40, [117.33, 149.64, 183.05, 221.42, 260.20, 304.74, 336.60, 369.56, 405.03, 438.87,
                                            471.43, 504.74, 535.86],
     [28.27, 25.10, 28.32, 34.59, 33.78, 28.31, 25.11, 29.27, 29.67, 33.22, 24.93, 28.04, 29.90], 'gold'),
    ('CREAM', 575, 415.43, 455.88, [252.71, 288.08, 320.52, 356.00, 394.32], [29.15, 28.93, 25.20, 33.82, 34.07], 'gold'),
    ('SNAILCOLLAGEN', 550, 527.71, 552.78, [190.26, 212.65, 236.98, 253.72, 266.53, 297.21, 321.15, 339.76, 359.51, 383.26,
                                            405.71, 426.95, 449.69],
     [18.53, 18.41, 21.59, 4.62, 15.84, 19.42, 19.77, 15.78, 15.96, 21.86, 19.71, 16.28, 18.47], SNAIL),
    ('Dailynourishingcollagencream', 600, 797.77, 815.90,
     [168.95, 183.71, 192.86, 198.51, 207.85, 226.32, 240.12, 254.06, 264.79, 273.39, 282.45, 294.78, 305.45, 315.33, 329.52,
      347.42, 361.02, 370.54, 376.44, 385.95, 399.29, 412.35, 425.82, 444.18, 454.89, 466.61, 480.06, 496.32],
     [12.72, 10.39, 2.63, 2.73, 11.67, 10.96, 11.12, 10.91, 7.54, 2.88, 10.02, 11.00, 2.91, 10.99, 11.24, 10.58, 11.15, 2.81,
      2.75, 10.61, 10.88, 10.91, 10.98, 10.84, 7.44, 11.15, 10.54, 17.18], BLACK),
    ('forhealthy-lookingglow', 575, 829.71, 847.93,
     [205.67, 216.57, 227.45, 244.28, 258.45, 271.85, 281.34, 288.59, 299.87, 313.71, 325.97, 334.40, 344.10, 357.54, 369.66,
      379.64, 389.78, 403.99, 423.17, 432.68, 442.48, 458.18],
     [8.71, 11.08, 7.42, 11.01, 10.95, 10.68, 2.80, 8.53, 11.04, 11.36, 8.12, 2.76, 11.25, 11.16, 10.24, 2.84, 10.89, 11.02,
      10.90, 2.65, 11.14, 16.31], BLACK),
    ('50ml1.69fl.oz.', 475, 905.19, 929.50, [188.46, 207.57, 240.24, 258.91, 327.29, 336.66, 350.25, 369.36, 396.22, 406.53,
                                             415.10, 429.00, 446.51, 459.12],
     [15.85, 16.38, 24.39, 2.78, 9.77, 4.26, 16.50, 16.21, 13.27, 2.98, 4.19, 15.77, 13.63, 3.99], BLACK)]
SKIP = set('Iil.-')                                   # stems, dots and the hyphen say nothing of a line's narrowing


def glyph(font, ch, weight, size=480):   # a glyph's alpha cropped to its ink, its ink top below the cap line, the cap px
    f = ImageFont.truetype(font, size)
    if weight: f.set_variation_by_axes([weight])
    im = Image.new('L', (1400, 1000)); ImageDraw.Draw(im).text((300, 200), ch, font=f, fill=255)
    hh = Image.new('L', (1400, 1000)); ImageDraw.Draw(hh).text((300, 200), 'H', font=f, fill=255)
    hy = np.nonzero(np.asarray(hh).max(1))[0]; a = np.asarray(im); ys, xs = np.nonzero(a > 3)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)), ys.min() - hy[0], hy[-1] + 1 - hy[0]


def put(canvas, alpha, colour, x0, y0):   # composite a colour (or an alpha into an alpha layer) at texel (x0, y0)
    h, w = alpha.shape; X0, Y0 = max(0, x0), max(0, y0); X1, Y1 = min(canvas.shape[1], x0 + w), min(canvas.shape[0], y0 + h)
    if X1 <= X0 or Y1 <= Y0: return
    a = alpha[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    if colour is None: canvas[Y0:Y1, X0:X1] = 1 - (1 - canvas[Y0:Y1, X0:X1]) * (1 - a); return
    canvas[Y0:Y1, X0:X1] = canvas[Y0:Y1, X0:X1] * (1 - a[..., None]) + np.array(colour, float) * a[..., None]


def setline(layer, font, text, weight, top, base, centres, widths, k, ox, oy, narrow=None):
    """Typeset one line into an alpha layer: every glyph's ink centred on its measured centre, its cap height and
    baseline as measured; photo px → texels by x·k + ox, y·k + oy. Returns the narrowing used."""
    P = 8; cap = (base - top) * k
    gl = [glyph(font, ch, weight) for ch in text]
    if narrow is None:
        narrow = float(np.median([w * k / (g.width * cap / gc) for ch, w, (g, _, gc) in zip(text, widths, gl) if ch not in SKIP]))
    for ch, cx, (g, gtop, gc) in zip(text, centres, gl):
        s = cap / gc; nw = 1 if ch in SKIP else narrow
        gw, gh = max(1, round(g.width * s * nw)), max(1, round(g.height * s))
        a = np.asarray(g.resize((gw, gh), Image.LANCZOS)).astype(float) / 255
        # the glyph's ink centroid (not its box's middle) on the measured one: L, E, r, 1 … are not symmetric
        col = a.sum(0); icx = ((np.arange(gw) + 0.5) * col).sum() / col.sum()
        fx, fy = cx * k + ox - icx, base * k + oy - cap + gtop * s
        a = np.clip(ndimage.shift(np.pad(a, P), (fy - np.floor(fy), fx - np.floor(fx)), order=1), 0, 1)
        put(layer, a, None, int(np.floor(fx)) - P, int(np.floor(fy)) - P)
    return narrow


def boxed(layer, font, ch, box, k, ox, oy):   # one glyph stretched into its measured ink box
    g, _, _ = glyph(font, ch, None)
    x0, x1, y0, y1 = box[0] * k + ox, box[1] * k + ox, box[2] * k + oy, box[3] * k + oy
    a = np.asarray(g.resize((max(1, round(x1 - x0)), max(1, round(y1 - y0))), Image.LANCZOS)).astype(float) / 255
    put(layer, a, None, round(x0), round(y0))


def ramp(stops, x):   # a colour along photo x through measured stops (flat beyond the ends)
    xs = np.array([s[0] for s in stops], float); cs = np.array([s[1] for s in stops], float)
    return np.stack([np.interp(x, xs, cs[:, c]) for c in range(3)], -1)


def front(font):
    face = np.zeros((H, W, 3)) + np.array(PAPER)
    tx = lambda x: (x - XL) * K; ty = lambda y: (y - YT) * K
    y0, y1 = ty(BAND_Y[0]), ty(BAND_Y[1])
    yy = np.arange(H) + 0.5
    cov = np.clip(np.minimum(yy - y0, y1 - yy) + 0.5, 0, 1)[:, None, None]   # the band's edges: exact coverage
    face = face * (1 - cov) + np.array(BAND) * cov
    xs_photo = (np.arange(W) + 0.5) / K + XL
    report = []
    for text, weight, top, base, centres, widths, colour in LINES:
        layer = np.zeros((H, W))
        n = setline(layer, font, text, weight, top, base, centres, widths, K, -XL * K, -YT * K)
        col = ramp(GOLD, xs_photo)[None] if colour == 'gold' else np.array(colour, float)
        face = face * (1 - layer[..., None]) + col * layer[..., None]
        report.append(f'{text} w{weight} narrow {n:.3f}')
    layer = np.zeros((H, W)); boxed(layer, DEJAVU, '℮', EST, K, -XL * K, -YT * K)
    face = face * (1 - layer[..., None]) + np.array(BLACK, float) * layer[..., None]
    # the gold frame: four lines of FRAME_W, exact coverage, the colour along x
    hw = FRAME_W * K / 2; X = np.arange(W) + 0.5; Y = np.arange(H) + 0.5
    fx0, fx1, fy0, fy1 = tx(FRAME_X[0]), tx(FRAME_X[1]), ty(FRAME_Y[0]), ty(FRAME_Y[1])
    c = lambda v, m: np.clip(hw + 0.5 - np.abs(v - m), 0, 1)
    ins = lambda v, a, b: np.clip(np.minimum(v - (a - hw) + 0.5, (b + hw) - v + 0.5), 0, 1)
    a = np.maximum.reduce([c(Y, fy0)[:, None] * ins(X, fx0, fx1)[None], c(Y, fy1)[:, None] * ins(X, fx0, fx1)[None],
                           c(X, fx0)[None] * ins(Y, fy0, fy1)[:, None], c(X, fx1)[None] * ins(Y, fy0, fy1)[:, None]])
    face = face * (1 - a[..., None]) + ramp(FGOLD, xs_photo)[None] * a[..., None]
    # the monogram: the owner's file in the print's ink box, its colours scaled to the print's gold
    m = Image.open(MFILE).convert('RGBA'); A = np.asarray(m.getchannel('A')).astype(float) / 255
    rgb = np.asarray(m.convert('RGB')).astype(float)
    gain = np.array(M_PRINT, float) / np.median(rgb[A > 0.8], 0)
    mx0, mx1, my0, my1 = tx(M_BOX[0]), tx(M_BOX[1]), ty(M_BOX[2]), ty(M_BOX[3])
    w, h = round(mx1 - mx0), round(my1 - my0)
    rs = lambda arr: np.asarray(Image.fromarray(arr.astype(np.float32), 'F').resize((w, h), Image.LANCZOS))
    a = np.clip(rs(A), 0, 1); col = np.stack([rs(rgb[..., i] * A) for i in range(3)], -1) / np.maximum(a, 1e-3)[..., None]
    col = np.clip(col * gain, 0, 255); X0, Y0 = round(mx0), round(my0)
    reg = face[Y0:Y0 + h, X0:X0 + w]; reg[:] = reg * (1 - a[..., None]) + col * a[..., None]
    # the illustration: the photo's own pixels in their window, ×K (cubic), a soft edge onto the typeset paper
    ph = np.asarray(Image.open(FRONT).convert('RGB')).astype(float)
    x0, x1, y0_, y1_ = ILLU
    X0, X1, Y0, Y1 = int(np.floor(tx(x0))), int(np.ceil(tx(x1))), int(np.floor(ty(y0_))), int(np.ceil(ty(y1_)))
    gx, gy = np.meshgrid((np.arange(X0, X1) + 0.5) / K + XL - 0.5, (np.arange(Y0, Y1) + 0.5) / K + YT - 0.5)
    pic = np.stack([ndimage.map_coordinates(ph[..., i], [gy, gx], order=3, mode='nearest') for i in range(3)], -1)
    fe = 8 * K   # an 8 photo px feather inside the window
    wx = np.clip(np.minimum((np.arange(X0, X1) + 0.5) - tx(x0), tx(x1) - (np.arange(X0, X1) + 0.5)) / fe, 0, 1)
    wy = np.clip(np.minimum((np.arange(Y0, Y1) + 0.5) - ty(y0_), ty(y1_) - (np.arange(Y0, Y1) + 0.5)) / fe, 0, 1)
    wgt = (np.minimum(wy[:, None], wx[None]) ** 2 * (3 - 2 * np.minimum(wy[:, None], wx[None])))[..., None]
    face[Y0:Y1, X0:X1] = face[Y0:Y1, X0:X1] * (1 - wgt) + np.clip(pic, 0, 255) * wgt
    return face, report


def side():   # the left side: the plain board (no print reaches it on the old ¾ packshot)
    h, w = 2048, 64
    img = np.zeros((h, w, 3)) + np.array(PAPER)
    u = (np.arange(w) + 0.5) / w; v = (np.arange(h) + 0.5) / h
    edge = np.clip(1 - u / 0.03, 0, 1)[None, :, None]                         # the rounded fold's light
    img = img * (1 - 0.5 * edge) + np.array([250, 243, 235.]) * 0.5 * edge
    seam = lambda c, hw: np.clip(1 - np.abs(v - c) / hw, 0, 1)
    flap = np.maximum(seam(0.003, 0.003), seam(0.997, 0.003))                # the flaps' strips: a little lighter
    dark = np.maximum(seam(0.0065, 0.0011), seam(0.9935, 0.0011))            # their seams: a dark gap
    img = img * (1 - 0.4 * flap[:, None, None]) + np.array([249, 241, 232.]) * 0.4 * flap[:, None, None]
    img = img * (1 - 0.55 * dark[:, None, None]) + np.array([120, 108, 96.]) * 0.55 * dark[:, None, None]
    return Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8))


# ---- the jar's label: texels per Ø, its window on the cylinder (r 0.5)
TJ = 2048; PHI0, PHI1, YLO, YHI = -50.0, 34.0, 0.04, 0.76
JW, JH = round(0.5 * np.radians(PHI1 - PHI0) * TJ), round((YHI - YLO) * TJ)
jx = lambda phi: (0.5 * np.radians(phi) - 0.5 * np.radians(PHI0)) * TJ   # φ (deg) → texel x
jy = lambda y: (YHI - y) * TJ                                             # height (Ø) → texel y
INK = (18, 18, 18)


def ink_box(text, centres, widths):   # a measured line's ink extent (photo px)
    return min(c - w / 2 for c, w in zip(centres, widths)), max(c + w / 2 for c, w in zip(centres, widths))


def jar_line(layer, font, line, cap, base_y, cx_phi, sel=None, narrow=None):
    """One of the box's lines (or the glyphs `sel` of it) on the jar: the box's spacing scaled to `cap` Ø, its ink
    centred at φ `cx_phi`, its baseline at height `base_y`."""
    text, weight, top, base, centres, widths, _ = line
    if sel: text, centres, widths = text[sel], centres[sel], widths[sel]
    k = cap * TJ / (base - top); a, b = ink_box(text, centres, widths)
    ox = jx(cx_phi) - (a + b) / 2 * k; oy = jy(base_y) - base * k
    return setline(layer, font, text, weight, top, base, centres, widths, k, ox, oy, narrow)


def jar_label(font):
    layer = np.zeros((JH, JW)); L = {t[0]: t for t in LINES}
    # vertical, reading upward (tops to the left): typeset level into a strip, then turned a quarter left
    for name, cap, phi in (('MITODERM', 0.080, -42.8), ('BIOSPICULESYSTEM', 0.047, -31.6)):
        text, weight, top, base, centres, widths, _ = L[name]
        a, b = ink_box(text, centres, widths); capT = cap * TJ; k = capT / (base - top)
        sw, sh, yb = int((b - a) * k + 60), int(capT * 1.6 + 40), 20 + capT * 1.25   # yb: the strip's baseline
        strip = np.zeros((sh, sw))
        setline(strip, font, text, weight, top, base, centres, widths, k, 20 - a * k, yb - base * k)
        rot = np.rot90(strip)   # a quarter left: the strip's start at the foot, its cap line to the left (−φ)
        put(layer, rot, None, round(jx(phi) + capT / 2 - yb), round(jy(0.089) - (sw - 20)))   # the ink from y 0.089 up
    jar_line(layer, font, L['DERMARECOVERY'], 0.035, 0.558, -0.5, slice(0, 5))
    jar_line(layer, font, L['DERMARECOVERY'], 0.035, 0.512, -0.5, slice(5, 13))
    jar_line(layer, font, L['CREAM'], 0.035, 0.466, -0.5)
    nS = jar_line(layer, font, L['SNAILCOLLAGEN'], 0.031, 0.389, -2.5)
    # the frame block: the box's frame and its two lines, scaled as one (its width 51.3° of the jar)
    kf = np.radians(51.3) * 0.5 * TJ / (FRAME_X[1] - FRAME_X[0])
    fcx, fcy = jx(1.2), jy(0.282); bcx, bcy = (FRAME_X[0] + FRAME_X[1]) / 2, (FRAME_Y[0] + FRAME_Y[1]) / 2
    ox, oy = fcx - bcx * kf, fcy - bcy * kf
    for name in ('Dailynourishingcollagencream', 'forhealthy-lookingglow'):
        text, weight, top, base, centres, widths, _ = L[name]
        setline(layer, font, text, weight, top, base, centres, widths, kf, ox, oy)
    hw = 0.004 * TJ / 2; X = np.arange(JW) + 0.5; Y = np.arange(JH) + 0.5
    x0, x1, y0, y1 = FRAME_X[0] * kf + ox, FRAME_X[1] * kf + ox, FRAME_Y[0] * kf + oy, FRAME_Y[1] * kf + oy
    c = lambda v, m: np.clip(hw + 0.5 - np.abs(v - m), 0, 1)
    ins = lambda v, a, b: np.clip(np.minimum(v - (a - hw) + 0.5, (b + hw) - v + 0.5), 0, 1)
    fr = np.maximum.reduce([c(Y, y0)[:, None] * ins(X, x0, x1)[None], c(Y, y1)[:, None] * ins(X, x0, x1)[None],
                            c(X, x0)[None] * ins(Y, y0, y1)[:, None], c(X, x1)[None] * ins(Y, y0, y1)[:, None]])
    layer = 1 - (1 - layer) * (1 - fr)
    # MADE IN KOREA: not on the box; Rubik at the box's SNAIL COLLAGEN weight and narrowing, its natural spacing
    f = ImageFont.truetype(font, 400); f.set_variation_by_axes([L['SNAILCOLLAGEN'][1]])
    im = Image.new('L', (4200, 700)); ImageDraw.Draw(im).text((100, 500), 'MADE IN KOREA', font=f, fill=255, anchor='ls')
    hh = Image.new('L', (4200, 700)); ImageDraw.Draw(hh).text((100, 500), 'H', font=f, fill=255, anchor='ls')
    capf = 500 - np.nonzero(np.asarray(hh).max(1))[0][0]; a = np.asarray(im); ys, xs = np.nonzero(a > 3)
    g = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)); s = 0.028 * TJ / capf
    gw, gh = round(g.width * s * nS), round(g.height * s)
    put(layer, np.asarray(g.resize((gw, gh), Image.LANCZOS)).astype(float) / 255, None, round(jx(-2.5) - gw / 2), round(jy(0.154) - gh))
    # 50 ml ℮ 1.69 fl.oz.: the box's line and its ℮ box, scaled as one
    line = L['50ml1.69fl.oz.']; kv = 0.025 * TJ / (line[3] - line[2]); a_, b_ = 188.46 - 15.85 / 2, 459.12 + 3.99 / 2
    ox, oy = jx(-3.0) - (a_ + b_) / 2 * kv, jy(0.080) - line[3] * kv
    setline(layer, font, *line[:6], kv, ox, oy); boxed(layer, DEJAVU, '℮', EST, kv, ox, oy)
    # the M: the owner's file, 0.067 Ø tall at the print's width share
    out = np.zeros((JH, JW, 4)); out[..., :3] = INK; out[..., 3] = layer * 255
    m = Image.open(MFILE).convert('RGBA'); A = np.asarray(m.getchannel('A')).astype(float) / 255; rgb = np.asarray(m.convert('RGB')).astype(float)
    h = round(0.067 * TJ); w = round(h * (M_BOX[1] - M_BOX[0]) / (M_BOX[3] - M_BOX[2]))
    rs = lambda arr: np.asarray(Image.fromarray(arr.astype(np.float32), 'F').resize((w, h), Image.LANCZOS))
    ma = np.clip(rs(A), 0, 1); mc = np.stack([rs(rgb[..., i] * A) for i in range(3)], -1) / np.maximum(ma, 1e-3)[..., None]
    X0, Y0 = round(jx(1.0) - w / 2), round(jy(0.665) - h / 2)
    reg = out[Y0:Y0 + h, X0:X0 + w]; ra = reg[..., 3:] / 255
    na = ma[..., None] + ra * (1 - ma[..., None])
    reg[..., :3] = (np.clip(mc, 0, 255) * ma[..., None] + reg[..., :3] * ra * (1 - ma[..., None])) / np.maximum(na, 1e-3)
    reg[..., 3:] = na * 255
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), 'RGBA')


# ---- the neighbours, as photographed: front and right side rectified side by side
def homography(a, b):   # the 3×3 map taking the four points a onto b
    A = []
    for (x, y), (u, v) in zip(a, b):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y, -u], [0, 0, 0, x, y, 1, -v * x, -v * y, -v]]
    _, _, vt = np.linalg.svd(np.array(A, float)); return vt[-1].reshape(3, 3) / vt[-1, -1]


def rectify(im, corners, size):   # the quad `corners` (TL TR BR BL, edge coordinates) onto size texels, 1 per photo px
    w, h = round(size[0]), round(size[1])
    Hinv = homography([[0, 0], [w, 0], [w, h], [0, h]], corners)
    uu, vv = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    q = Hinv @ np.stack([uu.ravel(), vv.ravel(), np.ones(uu.size)])
    xs, ys = q[0] / q[2] - 0.5, q[1] / q[2] - 0.5
    return np.stack([ndimage.map_coordinates(im[..., c], [ys, xs], order=3, mode='nearest').reshape(h, w) for c in range(3)], -1)


# (file, front corners, side's far corners (TR, BR), front size): the fronts as their own pages measured them; the sides'
# far edge at half alpha, its top and foot by the half-alpha rows of three columns, extrapolated to it
NEIGHBOURS = {
    'renew': ('cell-renew-15.webp', [[0.05, 2.55], [261.8, 1.25], [261.8, 1011.1], [0.05, 1008.6]], [[307.4, 18.2], [307.4, 982.1]], (261.75, 1008)),
    'cad': ('cellular-age-25.webp', [[0.2, 1.64], [262.0, 0.47], [262.0, 1021.38], [0.2, 1018.49]], [[306.9, 18.8], [306.9, 994.0]], (261.8, 1019)),
    'mb': ('micro-boost-10.webp', [[0.87, 5.24], [304.91, 1.23], [304.91, 1251.2], [0.87, 1245.6]], [[383.5, 28.5], [383.5, 1217.9]], (304.04, 1243))}


def neighbour(name):
    f, fr, far, size = NEIGHBOURS[name]
    src = Image.open(f'{REPO}/protocols/print/img/{f}').convert('RGBA')
    bg = Image.new('RGBA', src.size, (243, 233, 224, 255)); bg.alpha_composite(src); im = np.asarray(bg).astype(float)
    a = rectify(im, fr, size)
    sw = far[0][0] - fr[1][0]
    b = rectify(im, [fr[1], far[0], far[1], fr[2]], (sw, size[1]))
    out = np.concatenate([a, b], 1)
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8)), a.shape[1] / out.shape[1]


if __name__ == '__main__':
    fdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
    font = os.path.join(fdir, 'Rubik[wght].ttf')
    face, report = front(font)
    Image.fromarray(np.clip(np.round(face), 0, 255).astype(np.uint8)).save(f'{out}/box-face.webp', lossless=True, quality=100, method=6)
    side().save(f'{out}/box-side.png', optimize=True)
    jar_label(font).save(f'{out}/jar-label.png', optimize=True)
    print('\n'.join(report))
    for n in NEIGHBOURS:
        im, share = neighbour(n); im.save(f'{out}/{n}.webp', quality=92, method=6); print(n, 'front share of the width', round(share, 4))
    for n in sorted(os.listdir(out)):
        im = Image.open(f'{out}/{n}'); print(n, im.size, os.path.getsize(f'{out}/{n}') // 1024, 'KB')
