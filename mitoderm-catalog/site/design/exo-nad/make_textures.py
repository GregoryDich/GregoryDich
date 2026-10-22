"""Textures for the three.js EXO-NAD scene (site/proto/scenes/exo-nad.js), sharp at any size: the print is typeset, not cut
from the packshot. Places and sizes are measured on the only packshot, protocols/print/img/exo-nad.webp (795×488: the box's
front seen square on, 476 px; the peel bottle, the two 5 ml vials before it), in edge coordinates (a pixel i spans
[i, i+1)), ink at half its contrast against the foil around it (spec: scratchpad pages/exo-nad/spec.md §1):
  lid   u, v: fractions of the front's width from its left edge (x 313) and from its top (y 5); the front is W × W, the
        sleeve covers v 0…0.877
  peel  fractions of the bottle's width W_b (94 px, x 192…285) and height H_b (211 px from the cap's top, y 271)
  vial  fractions of the vial's width W_v (65 px) and height H_v (138 px from the cap's top, y 343)
Typeface: Jost (SIL OFL, github.com/google/fonts ofl/jost), weights matched to the stems: «EXO-» 280, «NAD» 700
(stem 0.25 cap; N A D 0.916 / 1.040 / 0.891 cap wide on the packshot, Jost 700 0.921 / 1.050 / 0.893), «SKIN LONGEVITY
PEELING» 500, each letter's ink centred on its measured centre; «VM corporation»: «VM» 700 at the x-height of
«corporation» 400, fitted to its measured ink width. The VM monogram: three polygons traced on the packshot (threshold
L 90, ±0.5 px of its 48 px; fitted by overlay), symmetric but for its right half, 0.5 px wider as traced. The vials' «PH NORMALIZER» / «LONGEVITY SERUM»: Jost 700, each line fitted to its
measured ink box as the packshot shows them flat on the front; the scene wraps this print round the clear glass at 0.62
of that size (±35° of the front), small, as the owner's photos of 22/10 show it. The print is
black on all four (packaging-text.json says «bold white» for the vials: the packshot and the owner's photo 27 show black).
The print the packshot lacks follows the owner's photos of 22/10 as packaging-text.json transcribes them: the lid's small
block, the peel bottle's label, the tray's gold print; placed on the thumbnails (26, 28, 29, 32), the lines Jost (bold:
600), «℮» from DejaVu Sans Bold; lines unreadable in the photos are left out. The packaging's vector file would replace
all of it one for one.
Writes into <out dir>:
  lid-face.png     the sleeve's front, RGB 2048×1796 (u 0…1 × v 0…0.877; 1.9 texels per px of the largest front, 1056 px in
                   a 3840 key): the foil's colour and the black print
  lid-metal.png    its material, RGB 1024×898: G roughness (foil 0.30, ink 0.55), B metalness (foil 1, ink 0)
  foil-brush.jpg   the foil's fine horizontal brushing (bump), 512×512, tiling
  peel-print.png   alpha of the peel bottle's print, L 1024×(x −0.45…0.45 W_b of its axis × 0.525…0.80 H_b): the monogram,
                   «EXO-NAD» / «PEELING», the four-language description; no ink on an edge
  peel-liquid.png  the peel's two phases as photographed (median colours, the peach left of the upper phase, the line
                   between them, the light foot, a fine haze of gold), RGB 512×693 (the liquid's front, 0.755 W_b × 0.455 H_b),
                   ×1.22 in linear light (LIQ_GAIN: the scene's light and glass take that much; the ΔE probe lands ≤ 6)
  vial-ph.png, vial-ls.png   alpha of the vials' print, L 1024×913 / 924 (x −R…R as seen from the front × 0.30…0.72 H_v); the
                   unreadable line of small type under the monogram is left out (no placeholder marks for unknown text)
  tray-print.png   alpha of the tray's gold print, L 2048×(u 0.03…0.97 × v 0.03…0.88 of the front): see tray_print
usage: python3 -I make_textures.py <font dir with Jost[wght].ttf, DejaVuSans-Bold.ttf> <out dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

SS = 2                                    # drawn at 2× and reduced: smooth edges
FX, FY, FW = 313.0, 5.0, 476.0            # the front on the packshot: its left and top edges, its width (= height)
LID_V = 0.877                             # the sleeve's foot (the lid line: y 422)
TW = 2048; TH = round(TW * LID_V)          # lid-face.png
FOIL = (0xf2, 0xd2, 0x8f)                 # the foil's texture colour, calibrated on the 3840 keys: in the scene's light the
                                          # ΔE probe (u 0.5, v 0.30, light 1.07) renders #ebcc8b, ΔE 3.3 to the packshot's
                                          # #e4c381 (the median of its bare foil)
INK = (0x05, 0x06, 0x07)
# the lockup, in fractions of the front's width W: «EXO-NAD» (letter, weight, ink centre u), its cap and baseline (v)
EXO = [('E', 280, 0.1933), ('X', 280, 0.2836), ('O', 280, 0.3824), ('N', 700, 0.5557), ('A', 700, 0.6733), ('D', 700, 0.7909)]
EXO_CAP, EXO_BASE = 0.0842, 0.5316
DASH = (0.4685, 0.501, 0.0273, 0.0063)    # the hyphen: centre u, v, width, height (13 × 3 px)
SKIN = list(zip('SKINLONGEVITYPEELING', [0.1786, 0.2101, 0.2374, 0.2658, 0.3214, 0.3550, 0.3939, 0.4307, 0.4643, 0.4958, 0.5252,
                                          0.5494, 0.5809, 0.6345, 0.6649, 0.6975, 0.7279, 0.7542, 0.7836, 0.8193]))
SKIN_CAP, SKIN_BASE, SKIN_W = 0.0227, 0.5957, 500
VMCORP = (0.441, 0.561, 0.180)            # «VM corporation»: ink u0, u1, baseline v
MONO = (527.0, 37.0)                      # the monogram's frame on the packshot (48 × 44 px): polygons in its px, fitted
                                          # by overlay (ink mass and centroid within 3 % and 0.3 px of the packshot's)
MONO_V = [(4.75, 0), (12.25, 0), (23.7, 31), (35.25, 0), (42.75, 0), (23.7, 44)]
MONO_L = [(3.8, 11.2), (7.6, 25), (6.9, 36.5), (0, 36.5), (0.9, 23)]
MONO_R = [(47.6 - x, y) for x, y in MONO_L]   # the right half 0.5 px wider than the left, as traced
# the small block under the lockup (owner photos of 22/10, packaging-text.json; not on the packshot): centred, its print in
# two groups at v 0.73…0.77 and 0.81…0.84 and 0.21 W wide (measured on the thumbnails 26 and 32: ±0.01 W); every line at
# the cap height that fits the first to that width. Its Arabic line is unreadable in the photos: its place stays empty
LID_BLOCK_W = 0.21
LID_BLOCK = [(('Professional Cosmetic Kit – Three-Step Revitalizing System',), 0.738),
             (('', 'Kit Cosmetico Professionale Trifase Rivitalizzante'), 0.7465),
             (('', 'Kit Cosmético Profesional Trifásico Revitalizante'), 0.755),
             (('', 'Kit Cosmétique Professionnel Triphasé Revitalisant'), 0.7635),
             (('FACE & BODY',), 0.810),
             (('EXO-NAD PEELING:', ' 15 ml ℮ 0.51 fl.oz.'), 0.8215),
             (('PH NORMALIZER:', ' 5 x 5 ml ℮ 5 x 0.17 fl.oz.'), 0.830),
             (('LONGEVITY SERUM:', ' 5 x 5 ml ℮ 5 x 0.17 fl.oz.'), 0.8385)]
JOST = DEJAVU = None


def font(size, weight, path=None):   # Jost at a weight, or another face (path: «℮» from DejaVu Sans Bold)
    f = ImageFont.truetype(path or JOST, size, layout_engine=ImageFont.Layout.BASIC)
    if not path: f.set_variation_by_axes([weight])
    return f


def ink(img, thr=127):   # the ink box of an L image: x0, y0, x1, y1
    a = np.asarray(img) > thr; ys, xs = np.nonzero(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def run(parts, size, track=0.0):   # a line of (text, weight, scale[, font file]) on its baseline at row 2·size; with `track` px between letters
    fonts = [(t, font(round(size * k), w, *f)) for t, w, k, *f in parts]
    m = int(np.ceil(size)); width = int(sum(f.getlength(t) + track * len(t) for t, f in fonts)) + m * 2
    im = Image.new('L', (width, m * 3)); d = ImageDraw.Draw(im); x = m
    for t, f in fonts:
        for piece in (t if track else [t]):
            d.text((x, m * 2), piece, font=f, fill=255, anchor='ls'); x += f.getlength(piece) + track
    return im, m * 2


_caps = {}
def cap_of(weight, path=None):   # the H's ink height per px of size
    if (weight, path) not in _caps:
        im, _ = run([('H', weight, 1) + ((path,) if path else ())], 400); x0, y0, x1, y1 = ink(im); _caps[weight, path] = (y1 - y0) / 400
    return _caps[weight, path]


def glyph(ch, weight, cap):   # one letter at cap height `cap` px: its ink (float), the ink's top relative to the cap line
    size = cap / cap_of(weight)
    big = max(1.0, 4 * size); im, base = run([(ch, weight, 1)], big)   # drawn at 4× and reduced
    x0, y0, x1, y1 = ink(im, 0); k = size / big
    crop = im.crop((x0, y0, x1, y1)); w, h = max(1, round(crop.width * k)), max(1, round(crop.height * k))
    return np.asarray(crop.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255, (y0 - (base - cap / k)) * k


def paste(canvas, a, x, y, value=1.0):   # max-composite an alpha patch at canvas px (x, y), sub-pixel by resampling
    ix, iy = int(np.floor(x)), int(np.floor(y)); fx, fy = x - ix, y - iy
    if fx or fy:
        p = np.pad(a, ((1, 1), (1, 1)))
        a = (p[1:, 1:] * (1 - fx) * (1 - fy) + p[1:, :-1] * fx * (1 - fy) + p[:-1, 1:] * (1 - fx) * fy + p[:-1, :-1] * fx * fy)
    h, w = a.shape; H, W = canvas.shape
    X0, Y0, X1, Y1 = max(0, ix), max(0, iy), min(W, ix + w), min(H, iy + h)
    if X1 <= X0 or Y1 <= Y0: return
    canvas[Y0:Y1, X0:X1] = np.maximum(canvas[Y0:Y1, X0:X1], a[Y0 - iy:Y1 - iy, X0 - ix:X1 - ix] * value)


def poly(canvas, pts, value=1.0, S4=4):   # a filled polygon (canvas px), drawn at 4× in its own region and reduced
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]; ox, oy = int(min(xs)) - 2, int(min(ys)) - 2
    reg = Image.new('L', ((int(max(xs)) - ox + 3) * S4, (int(max(ys)) - oy + 3) * S4))
    ImageDraw.Draw(reg).polygon([((x - ox) * S4, (y - oy) * S4) for x, y in pts], fill=255)
    reg = reg.resize((reg.width // S4, reg.height // S4), Image.BOX)
    paste(canvas, np.asarray(reg).astype(np.float32) / 255, ox, oy, value)


def letters(canvas, items, cap, base, X, Y, k):   # letters (ch, weight, ink centre u) at cap height cap (W), baseline v
    for ch, weight, u in items:
        a, top = glyph(ch, weight, cap * k)
        paste(canvas, a, X(u) - a.shape[1] / 2, Y(base) - cap * k + top)


def lockup(canvas, X, Y, k):
    """the lid's «EXO-NAD» and «SKIN LONGEVITY PEELING» with X(u), Y(v) mapping the lid's fractions to canvas px and k
    canvas px per W (the same lockup scaled: the tray's)"""
    letters(canvas, EXO, EXO_CAP, EXO_BASE, X, Y, k)
    u, v, w, h = DASH; poly(canvas, [(X(u - w / 2), Y(v - h / 2)), (X(u + w / 2), Y(v - h / 2)), (X(u + w / 2), Y(v + h / 2)), (X(u - w / 2), Y(v + h / 2))])
    letters(canvas, [(ch, SKIN_W, u) for ch, u in SKIN], SKIN_CAP, SKIN_BASE, X, Y, k)


def monogram(canvas, X, Y, value=1.0):   # X, Y: packshot px (x, y) → canvas px
    for P in (MONO_V, MONO_L, MONO_R):
        poly(canvas, [(X(MONO[0] + x), Y(MONO[1] + y)) for x, y in P], value)


def fit_line(parts, x0, x1, base, xh=None):
    """a line of (text, weight, scale) fitted to the ink width x0…x1 (canvas px) on its baseline; its height follows the
    width (the font's own proportions)"""
    im, b = run(parts, 400); ix0, iy0, ix1, iy1 = ink(im)
    s = (x1 - x0) / (ix1 - ix0)
    a = np.asarray(im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)).astype(np.float32) / 255
    return a, x0 - ix0 * s, base - b * s


def vmcorp(canvas, x0, x1, base):   # «VM corporation»: «VM» 700 at the x-height of «corporation» 400
    im, _ = run([('x', 400, 1)], 400); _, xy0, _, xy1 = ink(im); xk = (xy1 - xy0) / 400 / cap_of(700)
    a, ox, oy = fit_line([('VM', 700, xk), (' corporation', 400, 1)], x0, x1, base)
    paste(canvas, a, ox, oy)


def mono_at(canvas, cx, top, width):   # the monogram, its ink `width` canvas px wide, centred on cx, its top at `top`
    s = width / 47.6
    monogram(canvas, lambda x: cx + (x - MONO[0] - 23.8) * s, lambda y: top + (y - MONO[1]) * s)


def parts_of(text, weight):   # Jost, a «℮» set from DejaVu Sans Bold at the height of the capitals around it
    if '℮' not in text: return [(text, weight, 1)]
    a, b = text.split('℮')
    return [(a, weight, 1), ('℮', None, cap_of(weight) / cap_of(None, DEJAVU), DEJAVU), (b, weight, 1)]


def label(bold, rest='', wb=600, wr=400):   # a line of small print: its bold label, then the rest
    return ([(bold, wb, 1)] if bold else []) + (parts_of(rest, wr) if rest else [])


def ink_w(parts, cap):   # a line's ink width at cap height `cap`
    im, _ = run(parts, 400); x0, _, x1, _ = ink(im, 0)
    return (x1 - x0) * cap / (cap_of(400) * 400)


def set_line(canvas, parts, cap, cx, base):   # a line at cap height `cap` canvas px on baseline `base`, its ink centred on cx
    im, b = run(parts, 400); x0, _, x1, _ = ink(im, 0); s = cap / (cap_of(400) * 400)
    a = np.asarray(im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)).astype(np.float32) / 255
    paste(canvas, a, cx - (x0 + x1) / 2 * s, base - b * s)


def ring(canvas, cx, cy, r, w, S4=4):   # a circle's stroke (radius r to the stroke's middle, w wide), drawn at 4× and reduced
    ox, oy = int(cx - r - w) - 2, int(cy - r - w) - 2; n = int(2 * (r + w)) + 6
    reg = Image.new('L', (n * S4, n * S4)); d = ImageDraw.Draw(reg)
    for R, fill in ((r + w / 2, 255), (r - w / 2, 0)):
        d.ellipse([((cx - ox) - R) * S4, ((cy - oy) - R) * S4, ((cx - ox) + R) * S4, ((cy - oy) + R) * S4], fill=fill)
    paste(canvas, np.asarray(reg.resize((n, n), Image.BOX)).astype(np.float32) / 255, ox, oy)


def lid_face():
    W, H = TW * SS, TH * SS; k = W                              # canvas px per W
    X = lambda u: u * k; Y = lambda v: v * k
    a = np.zeros((H, W), np.float32)
    lockup(a, X, Y, k)
    monogram(a, lambda x: X((x - FX) / FW), lambda y: Y((y - FY) / FW))
    u0, u1, vb = VMCORP; vmcorp(a, X(u0), X(u1), Y(vb))
    cap = LID_BLOCK_W * k / ink_w(label(*LID_BLOCK[0][0]), 1)
    for text, vb in LID_BLOCK: set_line(a, label(*text), cap, X(0.5), Y(vb))
    rgb =np.array(FOIL, np.float32)[None, None, :] + (np.array(INK, np.float32) - FOIL)[None, None, :] * a[..., None]
    face = Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8)).resize((TW, TH), Image.LANCZOS)
    m = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((TW // 2, TH // 2), Image.BOX)).astype(np.float32) / 255
    mat = np.stack([np.zeros_like(m), 255 * (0.30 + (0.55 - 0.30) * m), 255 * (1 - m)], -1)
    return face, Image.fromarray(np.clip(mat + 0.5, 0, 255).astype(np.uint8)), a


def foil(n=512, seed=11):   # tiling fine brushing: grain stretched along x, a few longer streaks
    r = np.random.default_rng(seed)
    a = ndimage.gaussian_filter(r.standard_normal((n, n)), (0.6, n / 6), mode='wrap')
    b = ndimage.gaussian_filter(r.standard_normal((n, n)), (1.5, n / 2.5), mode='wrap')
    v = a / a.std() + 0.6 * b / b.std()
    return Image.fromarray(np.clip(128 + v * 22, 0, 255).astype(np.uint8))


# ---- the peel bottle: its label as on the owner's photo of the bottle (22/10; packaging-text.json), placed by the photo
# (the thumbnail 28: ±0.01 H_b), sized in the packshot's proportions (W_b = 0.4455 H_b): the monogram, «EXO-NAD» / «PEELING»
# bold on two lines (0.70 W_b wide, as photographed), four lines of the description under them; its fifth line is
# unreadable in the photos and is left out. The plane spans x −0.45…0.45 W_b of the axis × 0.525…0.80 H_b from the cap's top
PEEL_WB, PEEL_HB = 94.0, 211.0
PEEL_PLANE = (-0.45, 0.45, 0.525, 0.80)  # in W_b (x) and H_b (y from the top); = the scene's PP
PEEL_MONO = (0.10, 0.532)                # the monogram's ink width (W_b), its top (H_b)
PEEL_NAME = (0.045, [('EXO-NAD', 0.6325), ('PEELING', 0.7065)])   # Jost 700: cap (H_b), lines and baselines (H_b)
PEEL_DESC = (0.66, [('Exfoliating and revitalizing cosmetic solution', 0.738), ('Soluzione cosmetica esfoliante e rivitalizzante', 0.754),
                    ('Solución cosmética exfoliante y revitalizante', 0.770), ('Solution cosmétique exfoliante et revitalisante', 0.786)])
PEEL_TW = 1024                           # (Jost 400: the longest line's ink width (W_b); every line at its cap height)
LIQ_GAIN = 1.22                          # peel-liquid.png in linear light: the scene renders it at ≈ 0.8 (see peel_liquid)


def peel_print():
    x0, x1, y0, y1 = PEEL_PLANE
    W = PEEL_TW * SS; kb = W / (x1 - x0); kh = kb * PEEL_HB / PEEL_WB   # canvas px per W_b, per H_b
    H = round(kh * (y1 - y0)); X = lambda x: (x - x0) * kb; Y = lambda y: (y - y0) * kh
    a = np.zeros((H, W), np.float32)
    mono_at(a, X(0), Y(PEEL_MONO[1]), PEEL_MONO[0] * kb)
    cap, lines = PEEL_NAME
    for text, yb in lines: set_line(a, [(text, 700, 1)], cap * kh, X(0), Y(yb))
    w, lines = PEEL_DESC; cap = w * kb / max(ink_w([(t, 400, 1)], 1) for t, _ in lines)
    for text, yb in lines: set_line(a, [(text, 400, 1)], cap, X(0), Y(yb))
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((PEEL_TW, H // SS), Image.LANCZOS)


def peel_liquid(w=512, seed=5):
    """the two phases as photographed (median colours over the flakes): the upper phase 0.25 of the column, peach on its
    left and pale on its right, a thin darker line under it; the lower phase cream, a little yellower in the middle where
    the gold hangs thickest, lighter toward the foot; a fine gold haze (the flakes too small to draw one by one)"""
    h = round(w * 0.455 / (0.755 * PEEL_WB / PEEL_HB))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); yy = (yy + 0.5) / h; xx = (xx + 0.5) / w
    hexs = lambda s: np.array([int(s[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
    def ramp(t, stops):   # piecewise linear colour ramp
        xs = [p for p, _ in stops]; cs = np.stack([hexs(c) for _, c in stops])
        return np.stack([np.interp(t, xs, cs[:, i]) for i in range(3)], -1)
    up = ramp(xx, [(0, '#c69a6b'), (0.13, '#d8b37d'), (0.3, '#e6cd96'), (0.5, '#eedfae'), (0.7, '#ece0bb'), (1, '#dcd5b8')])
    lo = ramp(xx, [(0, '#d9c6a8'), (0.12, '#e3d4b2'), (0.45, '#e8dbb8'), (0.75, '#ede4c8'), (1, '#e0d9c5')])
    foot = ramp(xx, [(0, '#d8cfbc'), (0.2, '#e6decb'), (0.6, '#eae3d1'), (1, '#dfd9c9')])
    lo = lo + (foot - lo) * np.clip((yy - 0.80) / 0.15, 0, 1)[..., None]
    cloud = np.exp(-(((xx - 0.55) / 0.22) ** 2 + ((yy - 0.55) / 0.28) ** 2))
    lo = lo + (hexs('#dcc68c') - lo) * (0.25 * cloud)[..., None]
    img = np.where((yy < 0.25)[..., None], up, lo)
    line = np.exp(-((yy - 0.25) / 0.006) ** 2)
    img = img + (hexs('#c5ab8a') - img) * (0.8 * line)[..., None]
    # the haze: gold specks (#d1b55d, #b69843…#eacf77), 0.2…0.8 packshot px across (1.4…5.5 texels), densest in a cloud
    # down the middle (6.5 % of the liquid's area: the packshot's sub-pixel glitter reads that dense); drawn at 4×, reduced
    r = np.random.default_rng(seed); S4 = 4
    cov = Image.new('L', (w * S4, h * S4)); col = Image.new('RGB', (w * S4, h * S4)); dc, dk = ImageDraw.Draw(cov), ImageDraw.Draw(col)
    area, target = 0.0, 0.065 * w * h
    while area < target:
        px, py = r.uniform(0.02, 0.98), r.uniform(0.0, 0.97)
        dens = 0.06 + 0.94 * np.exp(-(((px - 0.48) / 0.17) ** 2 + ((py - 0.48) / 0.34) ** 2))
        if r.uniform() > dens: continue
        rad = r.uniform(0.7, 2.75); tone = r.uniform()
        c = tuple(int(np.interp(tone, [0, 0.5, 1], ch)) for ch in ([0xb6, 0xd1, 0xea], [0x98, 0xb5, 0xcf], [0x43, 0x5d, 0x77]))
        box = ((px * w - rad) * S4, (py * h - rad) * S4, (px * w + rad) * S4, (py * h + rad) * S4)
        dc.ellipse(box, fill=255); dk.ellipse(box, fill=c); area += np.pi * rad * rad
    a = np.asarray(cov.resize((w, h), Image.BOX)).astype(np.float32) / 255
    c = np.asarray(col.resize((w, h), Image.BOX)).astype(np.float32) / np.maximum(a[..., None], 1e-3)
    img = img + (np.clip(c, 0, 255) - img) * a[..., None]
    # the scene's light and glass take ≈ 0.8 of it (linear, measured at the ΔE probe): the texture is that much lighter
    lin = np.where(img / 255 <= 0.04045, img / 255 / 12.92, ((img / 255 + 0.055) / 1.055) ** 2.4) * LIQ_GAIN
    img = 255 * np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.clip(lin, 0, 1) ** (1 / 2.4) - 0.055)
    return Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8))


# ---- the vials: the print as seen from the front (x −R…R), rows 0.30…0.72 H_v from the cap's top. Each vial in its own
# packshot px (the teal one stands nearer: ×1.04): its silhouette's left edge, width, top, height; the monogram's ink box,
# the small line under it (y, width / W_v: measured, not drawn, its text unknown); the lines (text, cap / H_v, baseline / H_v, ink x0, x1 in packshot px)
V_Y0, V_Y1 = 0.30, 0.72
V_DY = 0.6                         # the whole print 0.6 px lower than the ink rows' edges say (fitted by overlay ×8: the
VIAL_TW = 1024                     # ink's half-contrast edge of a 7 px line is that much inside its last row)
VIALS = {
    'ph': dict(x0=1.0, w=65.0, top=343.0, h=138.0, mono=(21.0, 44.0, 390.0, 410.0), line=(414.5, 0.32),
               lines=[('PH', 0.051, 0.616, 25.0, 38.0), ('NORMALIZER', 0.051, 0.684, 3.0, 63.0)]),
    'ls': dict(x0=94.0, w=67.0, top=343.0, h=144.0, mono=(116.0, 139.0, 391.0, 411.0), line=(416.5, 0.32),
               lines=[('LONGEVITY', 0.056, 0.627, 98.0, 160.0), ('SERUM', 0.056, 0.702, 109.0, 147.0)]),
}


def vial_print(kind):
    d = VIALS[kind]; V_WV, V_HV = d['w'], d['h']; W = VIAL_TW * SS; k = W / V_WV   # canvas px per packshot px
    H = round(k * (V_Y1 - V_Y0) * V_HV)
    X = lambda x: (x - d['x0']) * k; Y = lambda y: (y + V_DY - d['top'] - V_Y0 * V_HV) * k
    a = np.zeros((H, W), np.float32)
    mx0, mx1, my0, my1 = d['mono']; sx, sy = (mx1 - mx0) / 48.0, (my1 - my0) / 44.0
    monogram(a, lambda x: X(mx0 + (x - MONO[0]) * sx), lambda y: Y(my0 + (y - MONO[1]) * sy))
    for text, cap, base, x0, x1 in d['lines']:   # Jost 700, fitted to the measured ink box (its height: the cap)
        im, b = run([(text, 700, 1)], 400); ix0, iy0, ix1, iy1 = ink(im)
        sxl, syl = (X(x1) - X(x0)) / (ix1 - ix0), cap * V_HV * k / (cap_of(700) * 400)
        g = np.asarray(im.resize((max(1, round(im.width * sxl)), max(1, round(im.height * syl))), Image.LANCZOS)).astype(np.float32) / 255
        paste(a, g, X(x0) - ix0 * sxl, Y(d['top'] + base * V_HV) - b * syl)
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((VIAL_TW, H // SS), Image.LANCZOS)


# ---- the tray's gold print, as on the owner's photos of the open kit (22/10; packaging-text.json), placed on the thumbnail
# 29 (1 px = 0.0159 W both ways, from the rows' pitch; ±0.01 W) round the scene's vessels (the peel: axis u 0.129, cap's top
# v 0.362; the first column u 0.317: the pH caps' top v 0.205, the serum feet v 0.740): at the top the monogram and «VM
# corporation» (the lid's pair ×0.55); over the peel «EXO-NAD PEELING», a short vertical leader down to a circled 1 (in the
# kit's pose, photo A, the sleeve's foot is at v 0.317: the ring and the leader's last 0.012 W show under it); over
# the first pH vial «PH NORMALIZER», a leader, a circled 2; under the first serum vial a circled 3, a leader, «LONGEVITY
# SERUM»; at the foot the lid's lockup, 0.30 W wide as photographed (photo A 0.30, photo 29 0.26–0.28: it reads at the
# offer card's size), with its «SKIN LONGEVITY PEELING», and «MADE IN ITALY» under it, centred a little right of the middle
# (u 0.56, as on photo 29: clear of the serum's label), all above the base's band (v 0.881). The labels Jost 500, the
# numerals 500 in rings of 0.0115 W (stroke 0.0016)
TRAY = (0.03, 0.97, 0.03, 0.88)    # u0, u1, v0, v1 of the texture (the tray's face: u 0.026…0.974, v 0…0.881)
TRAY_TW = 2048
TRAY_MONO = (0.055, 0.062)         # the monogram's ink width (W), its top (v)
TRAY_LABELS = [('EXO-NAD PEELING', 0.129, 0.310, 0.343, '1'), ('PH NORMALIZER', 0.317, 0.150, 0.183, '2'),
               ('LONGEVITY SERUM', 0.317, 0.803, 0.7625, '3')]   # text, axis u, its baseline v, the ring's centre v, numeral
TRAY_CAP, TRAY_RING, TRAY_STROKE, TRAY_NUM = 0.0068, 0.0115, 0.0016, 0.0105
TRAY_LOGO = (0.30, 0.815, 0.56)    # the lockup's «EXO-NAD» ink width (W), its baseline (v), its centre (u)
TRAY_MADE = (0.866, 0.0085)        # «MADE IN ITALY»: its baseline (v) and cap (W), Jost 500


def tray_print():
    u0, u1, v0, v1 = TRAY; W = TRAY_TW * SS; k0 = W / (u1 - u0); H = round(k0 * (v1 - v0))
    X = lambda u: (u - u0) * k0; Y = lambda v: (v - v0) * k0
    a = np.zeros((H, W), np.float32)
    w, top = TRAY_MONO; s = w / (47.6 / FW)                      # ×0.55 of the lid's monogram and its «VM corporation»
    mono_at(a, X(0.5), Y(top), w * k0)
    u0c, u1c, vb = VMCORP; mtop = (MONO[1] - FY) / FW
    vmcorp(a, X(0.5 + (u0c - 0.5) * s), X(0.5 + (u1c - 0.5) * s), Y(top + (vb - mtop) * s))
    cap, r, sw, lw = TRAY_CAP * k0, TRAY_RING * k0, TRAY_STROKE * k0, 0.0014 * k0
    for text, u, vb, vr, n in TRAY_LABELS:
        set_line(a, [(text, 500, 1)], cap, X(u), Y(vb))
        ring(a, X(u), Y(vr), r, sw); set_line(a, [(n, 500, 1)], TRAY_NUM * k0, X(u), Y(vr) + TRAY_NUM * k0 / 2)
        y0, y1 = (Y(vb) + 0.004 * k0, Y(vr) - r - 0.002 * k0) if vr > vb else (Y(vr) + r + 0.002 * k0, Y(vb) - cap - 0.004 * k0)
        poly(a, [(X(u) - lw / 2, y0), (X(u) + lw / 2, y0), (X(u) + lw / 2, y1), (X(u) - lw / 2, y1)])
    k = k0 * TRAY_LOGO[0] / 0.6596; cu = TRAY_LOGO[2]
    lockup(a, lambda u: X(cu) + (u - 0.5) * k, lambda v: Y(TRAY_LOGO[1]) + (v - EXO_BASE) * k, k)
    set_line(a, [('MADE IN ITALY', 500, 1)], TRAY_MADE[1] * k0, X(cu), Y(TRAY_MADE[0]))
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((TRAY_TW, H // SS), Image.LANCZOS)


if __name__ == '__main__':
    fdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
    JOST, DEJAVU = os.path.join(fdir, 'Jost[wght].ttf'), os.path.join(fdir, 'DejaVuSans-Bold.ttf')
    face, metal, _ = lid_face()
    face.save(f'{out}/lid-face.png', optimize=True); metal.save(f'{out}/lid-metal.png', optimize=True)
    foil().save(f'{out}/foil-brush.jpg', quality=88)
    peel_print().save(f'{out}/peel-print.png', optimize=True)
    peel_liquid().save(f'{out}/peel-liquid.png', optimize=True)
    vial_print('ph').save(f'{out}/vial-ph.png', optimize=True); vial_print('ls').save(f'{out}/vial-ls.png', optimize=True)
    tray_print().save(f'{out}/tray-print.png', optimize=True)
    total = 0
    for n in ('lid-face.png', 'lid-metal.png', 'foil-brush.jpg', 'peel-print.png', 'peel-liquid.png', 'vial-ph.png', 'vial-ls.png', 'tray-print.png'):
        im = Image.open(f'{out}/{n}'); sz = os.path.getsize(f'{out}/{n}'); total += sz; print(n, im.size, im.mode, sz // 1024, 'KB')
    print('total', total // 1024, 'KB')
