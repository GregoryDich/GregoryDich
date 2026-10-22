"""Textures for the three.js MICRO BOOST 10% scene (site/proto/scenes/micro-boost-10.js), sharp at any size: the print is
typeset, not cut from the photo. Places, sizes and colours are measured on the largest packshot,
protocols/print/img/micro-boost-10.webp (385×1252, never upscaled), in edge coordinates (a pixel i spans [i, i+1)):
  the front  x 0.87 … 304.91 (the edge to the right side), top y = 5.25 − 0.01317 x, foot y = 1245.58 + 0.01844 x;
             a point of the front is u = (x − 0.87) / 304.04 across, v = (y − top) / (foot − top) down (the print sits
             on the photo linearly in x: what the designer centred reads u 0.500 ± 0.001)
  the true proportions H : W : D = 4.21 : 1 : 1.21 (the medallion's ring is a circle: the photo is stretched ×1.05 in x),
             so the front is W/H = 0.2376 and the texture's texels are square
(the measurements and their corrections: the spec of 22/10, §2). Typeface: Rubik (SIL OFL, github.com/google/fonts),
the closest by overlay (0.87–0.95 correlation, Jost and Inter lower), each line at its own narrowing; every glyph's
ink centre stands on its measured centre (ink-weighted, ±0.0017 u), its cap height and baseline as measured, so the
spacing is the photo's, not the font's. The gold monogram M is the owner's file site/img/mitoderm-m-gold.png reduced
(566 → 170 px). The medallion keeps no pixel of the photo: it is drawn at the texture's own resolution (≈ 3.2 texels
per photo px), from numbers measured on the photo:
  fields the silver disc, its thin dark outline and the gold ring's two bands (the darker inner one, a step, the lighter
         outer one), each a zone between circles at the photo's half-contrast radii (0.826, 0.845, 0.930, 0.991 R; the
         outer R = 0.10256 H) with sharp, anti-aliased edges; inside each zone its colour is a smooth function of radius
         and angle (polynomials × angles up to 10θ: the lens's bevel, light at the upper right, dark at the left, and the
         ring's), fitted by least squares to the photo's pixels in that zone (the strokes left out); 0.5–14 levels rms
         from the photo, which is its blur and the disc's foil grain. The disc's faint grey «ghost» marks are left out:
         on the photo they are broken shards between the strokes, not lines; traced, they come out as leaves on the rim
  strokes the dark green spicules (#243523) traced on the photo and drawn as vectors: each stroke found in turn (a
         Hough vote of the stroke map, each pixel voting only along its own stroke's direction), its centre line
         refitted to the ink (straight, or a parabola where it bends), its tips out to where the ink fades, its width
         from the ink across it; pieces cut by crossings joined; drawn as spindles (pointed at both ends) with edges
         anti-aliased at the texture's scale. About 60 strokes, centre lines on the photo's ink; the photo's tangle has
         more: its faintest lines are left out with the ghosts, pieces under 15 px too; a hand check by overlay remains
The packaging's vector file would replace all of it one for one (a question to the owner).
Writes into <out dir>:
  box-face.png   the front's colours, RGB 960×4040 (3.1 texels per px where the box is largest, 820 frame px in a 3840
                 key; ≤ 4096 for phones): the paper #F8EEE4, the band #132A1C, the inks and golds as pipetted
  box-metal.png  the front's material, RGB 480×2020: G roughness (paper 0.70, ink and band 0.60, gold 0.28), B metalness
                 (gold 0.60)
usage: python3 -I make_textures.py <font dir with Rubik[wght].ttf, DejaVuSans-Bold.ttf> <out dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(HERE, '..', '..'))
REPO = os.path.normpath(os.path.join(SITE, '..'))
PACKSHOT = os.path.join(REPO, 'protocols', 'print', 'img', 'micro-boost-10.webp')
MONOGRAM = os.path.join(SITE, 'img', 'mitoderm-m-gold.png')

TW, TH = 960, 4040                                       # box-face.png (W/H 0.2376, square texels)
X0, XW = 0.87, 304.04                                    # the front on the packshot: left edge, width (photo px)
TOP, FOOT = (5.25, -0.01317), (1245.58, 0.01844)         # its top and foot: y = a + b·x
PAPER, BAND = '#F8EEE4', '#132A1C'
BAND_V = (0.2221, 0.3102)
# the lines: (units, weight, narrowing, cap height (H), baseline (v), colour); a unit is (glyphs, ink centre u): a
# pair the photo merges («AT», «.1», «fl») is set as one run with the font's kerning, its ink centred on the measure.
# Weight, narrowing, cap height and baseline of the four small lines are fitted by overlay on the photo (correlation
# of the ink on the photo's grid ×4: 0.79–0.92 → 0.91–0.94); the lower-case lines' cap height is what their x-height
# (0.0119 H) is in Rubik (0.75 of a cap): 0.0158
LINES = [
    ([('M', .1576), ('I', .2468), ('T', .3232), ('O', .4230), ('D', .5285), ('E', .6277), ('R', .7297), ('M', .8434)],
     500, 0.95, 0.0219, 0.1653, '#2E3829'),
    ([(c, u) for c, u in zip('BIOSPICULEPROFESSIONAL', (.1512, .1782, .2044, .2409, .2754, .3014, .3260, .3657, .3962, .4319,
                                                         .4810, .5187, .5565, .5888, .6233, .6600, .6954, .7203, .7462, .7851, .8236, .8544))],
     440, 0.97, 0.0102, 0.1843, '#0F0C03'),
    ([(c, u) for c, u in zip('MICROBOOST10%', (.0883, .1464, .1946, .2662, .3365, .4316, .5025, .5743, .6433, .7068, .7926, .8474, .9223))],
     500, 0.88, 0.0191, 0.2766, '#CEC296'),
    ([(c, u) for c, u in zip('SPICULESERUM', (.1351, .1965, .2457, .2915, .3639, .4218, .4862, .5801, .6382, .7064, .7781, .8555))],
     400, 0.925, 0.0185, 0.3748, '#0B0900'),
    ([(c, u) for c, u in zip('Concentrated', (.2562, .3105, .3602, .4084, .4564, .5065, .5488, .5812, .6245, .6644, .7045, .7574))],
     500, 0.875, 0.0158, 0.8004, '#222014'),
    ([(c, u) for c, u in zip('SpiculeSystem', (.2251, .2748, .3133, .3468, .3974, .4330, .4666, .5374, .5860, .6312, .6698, .7102, .7722))],
     500, 0.88, 0.0159, 0.8262, '#232217'),
    ([(c, u) for c, u in zip('PROFESSIONAL', (.1537, .1904, .2269, .2590, .2932, .3283, .3630, .3881, .4132, .4510, .4891, .5208))]
     + [('T', .5671), ('R', .6002), ('E', .6343), ('AT', .6843), ('M', .7394), ('E', .7773), ('N', .8146), ('T', .8508)],
     440, 0.865, 0.0108, 0.8917, '#191109'),
    ([('3', .3000), ('m', .3533), ('l', .3853), ('℮', .4319, 'sign'), ('0', .4943), ('.1', .5342), ('0', .5638), ('fl', .6125),
      ('.', .6370), ('o', .6601), ('z', .6901), ('.', .7127)],
     440, 0.89, 0.0108, 0.9508, '#1A1209'),
]
ESTIMATED_H = 0.0111                                     # «℮»'s ink height (H): as tall as the digits; its shape is the
# classic estimated sign of the photo (wide, thick and thin), DejaVu Sans Bold's, not Rubik's plain «e»
RULES = [((0.1121, 0.8914), 0.8700), ((0.1117, 0.8912), 0.9030)]   # (u from, to), axis v; 0.0016 H of the text's ink
RULE_T, RULE_C = 0.0016, '#191109'
FRAME = ((0.1339, 0.8682), (0.7697, 0.8394), 0.0026, '#CDB28C')    # centre lines u, v; line width (H); gold
M_BOX, M_MEDIAN = ((0.4040, 0.5807), (0.0430, 0.0873)), '#C3A271'  # the monogram's ink box (u, v), its gold's median
# the medallion: centre (u, v), outer radius (H); in photo px its centre (153.07, 647.22), half axes 131.2 × 127.7
MED_UV, MED_R = (0.5006, 0.5171), 0.10256
MED_PX, MED_AX = (153.07, 647.22), (131.2, 127.7)
# the medallion's zones, edges at the photo's half-contrast radii (of R; the angle-averaged radial gradient): the silver
# disc, its thin dark outline, the ring's darker inner band, its lighter outer band (a step between them), the paper
MED_EDGES = (0.826, 0.845, 0.930, 0.991)
DISC_EDGE = MED_EDGES[0]
STROKE_RHO = 0.77                                       # the strokes are traced inside this (of R)
STROKE, STROKE_L = '#243523', 140                       # the strokes' ink; lighter than that (mean RGB) is silver
WMAX, TIP, WK, MINLEN = 5.6, 2.2, 1.9, 15              # a stroke's widest (photo px); its spindle w(t) = w (1 − |2t − 1|^TIP);
# WK: the GPU averages light (mipmaps, filtering in linear light), so a thin dark line reduced in a key reads lighter than
# the photo's: drawn 1.9 × the ink measured across it (WMAX with it), the 3840 kit key's medallion at the photo's scale
# has the photo's share of dark pixels inside 0.78 R (L < 110 / 90 / 70: 0.250 / 0.220 / 0.185 against 0.247 / 0.221 /
# 0.189; at 1.35 it was 0.193 / 0.159 / 0.121);
# MINLEN: shorter pieces are a crossing's leftovers, not strokes (drawn, they read as leaves): left out
GOLD_ROUGH, GOLD_METAL, PAPER_ROUGH, INK_ROUGH = 0.28, 0.60, 0.70, 0.60


def hexrgb(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)


def photo_xy(u, v):   # a point of the front (u, v) → photo px (edge coordinates)
    x = X0 + XW * u
    top = TOP[0] + TOP[1] * x; foot = FOOT[0] + FOOT[1] * x
    return x, top + v * (foot - top)


def sample(img, x, y, order=1):   # an (H, W[, C]) array at photo edge coordinates (x, y); outside: edge values
    c = [y - 0.5, x - 0.5]
    if img.ndim == 2: return ndimage.map_coordinates(img, c, order=order, mode='nearest')
    return np.stack([ndimage.map_coordinates(img[..., k], c, order=order, mode='nearest') for k in range(img.shape[2])], -1)


def cover1(a, b, n):   # coverage of the texels 0…n−1 (texel i spans [i, i+1)) by the interval [a, b]
    i = np.arange(n, dtype=np.float32)
    return np.clip(np.minimum(b, i + 1) - np.maximum(a, i), 0, 1)


def over(rgb, a, col, y0=0, x0=0):   # paint colour `col` with coverage `a` (a patch at row y0, column x0)
    h, w = a.shape
    reg = rgb[y0:y0 + h, x0:x0 + w]
    reg += (np.asarray(col, np.float32) - reg) * a[..., None]


# ---- type
_fonts, _glyphs = {}, {}
FS = 400


def font(path, weight):
    k = (path, weight)
    if k not in _fonts:
        f = ImageFont.truetype(path, FS, layout_engine=ImageFont.Layout.BASIC)   # no ligatures: «fl» letter by letter
        if weight: f.set_variation_by_axes([weight])
        _fonts[k] = f
    return _fonts[k]


def glyph(path, text, weight):
    """`text` (one glyph or a kerned pair) at FS px: its alpha (float), the baseline row (edge y), the ink centre x
    (alpha-weighted, edge coordinates) and the cap height of the weight (an H's ink height)"""
    k = (path, text, weight)
    if k not in _glyphs:
        f = font(path, weight); P = FS
        im = Image.new('L', (FS * 3, FS * 2)); ImageDraw.Draw(im).text((P, int(FS * 1.4)), text, font=f, fill=255, anchor='ls')
        h = Image.new('L', (FS * 3, FS * 2)); ImageDraw.Draw(h).text((P, int(FS * 1.4)), 'H', font=f, fill=255, anchor='ls')
        a = np.asarray(im).astype(np.float32) / 255; hy = np.nonzero(np.asarray(h).max(1) > 127)[0]
        cx = (a.sum(0) * (np.arange(a.shape[1]) + 0.5)).sum() / a.sum()
        _glyphs[k] = (a, int(FS * 1.4), cx, hy[-1] + 1 - hy[0])
    return _glyphs[k]


def place(layer, path, text, weight, cu, base, cap, narrow, ink_h=None, T=(TW, TH)):
    """paints one unit's alpha into `layer` (H×W float): its ink centre at u = cu, its baseline at v = base, scaled to the
    cap height `cap` (fraction of H; or its own ink height to `ink_h`) and narrowed; exact sub-texel placement (the
    source box of a filtered resize)"""
    a, by, cx, gc = glyph(path, text, weight)
    ys, xs = np.nonzero(a > 0.002)
    if ink_h: gc = (ys.max() + 1 - ys.min()) * cap / ink_h
    W, H = T; sy = cap * H / gc; sx = sy * narrow    # texels per source px
    tx = lambda x: cu * W + (x - cx) * sx; ty = lambda y: base * H + (y - by) * sy
    X0_, X1_ = int(np.floor(tx(xs.min()))) - 2, int(np.ceil(tx(xs.max() + 1))) + 2
    Y0_, Y1_ = int(np.floor(ty(ys.min()))) - 2, int(np.ceil(ty(ys.max() + 1))) + 2
    sx0 = cx + (X0_ - cu * W) / sx; sx1 = cx + (X1_ - cu * W) / sx
    sy0 = by + (Y0_ - base * H) / sy; sy1 = by + (Y1_ - base * H) / sy
    g = Image.fromarray((a * 255).astype(np.uint8)).resize((X1_ - X0_, Y1_ - Y0_), Image.LANCZOS, box=(sx0, sy0, sx1, sy1))
    g = np.asarray(g).astype(np.float32) / 255
    y0, x0 = max(0, Y0_), max(0, X0_)
    g = g[y0 - Y0_:Y1_ - Y0_ - max(0, Y1_ - H), x0 - X0_:X1_ - X0_ - max(0, X1_ - W)]
    reg = layer[y0:y0 + g.shape[0], x0:x0 + g.shape[1]]
    np.maximum(reg, g, out=reg)


def typeset_line(fonts, line, W=TW, H=TH, layer=None):
    units, weight, narrow, cap, base, col = line
    layer = np.zeros((H, W), np.float32) if layer is None else layer
    for text, cu, *f in units:
        if f: place(layer, fonts[f[0]], text, None, cu, base, cap, 1.0, ink_h=ESTIMATED_H, T=(W, H))
        else: place(layer, fonts['rubik'], text, weight, cu, base, cap, narrow, T=(W, H))
    return layer


# ---- the medallion's strokes, traced: each a spindle (pointed at both ends) along a straight or gently bent centre line
def bilinear(img, x, y):   # photo array at edge coordinates, 0 outside
    return ndimage.map_coordinates(img, [np.asarray(y) - 0.5, np.asarray(x) - 0.5], order=1, mode='constant', cval=0.0)


def trace_strokes(D, limit=260):
    """greedy: the strongest line of the stroke map (a Hough vote weighted by darkness), its longest run along that line
    (gaps ≤ 6 px: a crossing stroke has been taken out there), its centre line refitted to the ink twice (straight),
    then bent (a parabola) where that fits better by > 0.2 px rms; its tips out to where the ridge fades; its width from
    the ink across its middle; then the stroke is taken out of the map and the next one found. Returns strokes in photo
    px: (origin, along, across, s0, s1, k, width, darkness): the centre line is origin + along·s + across·(k0 + k1 s +
    k2 s²) for s in [s0, s1]"""
    # each pixel's stroke direction (the structure tensor: the normal across a stroke, and how clearly there is one);
    # a pixel votes only for lines along its own stroke, and a line's run counts only pixels lying along it, so the
    # rows and columns through the dense middle (each crossing many strokes) are not taken for strokes
    g = ndimage.gaussian_filter(D, 0.7); gx, gy = ndimage.sobel(g, 1), ndimage.sobel(g, 0)
    jxx, jxy, jyy = (ndimage.gaussian_filter(a, 1.6) for a in (gx * gx, gx * gy, gy * gy))
    phi = 0.5 * np.arctan2(2 * jxy, jxx - jyy); coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / np.maximum(jxx + jyy, 1e-9)
    O = (np.cos(2 * phi) * coh, np.sin(2 * phi) * coh, coh)
    W = D.copy(); out = []
    TH_ = np.radians(np.arange(0, 180, 0.75)); C, S = np.cos(TH_), np.sin(TH_)
    ss = np.arange(-170, 170.01, 0.5); oo = np.arange(-2.5, 2.51, 0.25)
    for _ in range(limit):
        ys, xs = np.nonzero(W > 0.4)
        if len(xs) < 12: break
        w = W[ys, xs]; X, Y = xs + 0.5, ys + 0.5; ph = np.mod(phi[ys, xs], np.pi); ch = coh[ys, xs]
        rho = np.round(X[:, None] * C + Y[:, None] * S).astype(int); off = rho.min()
        dth = np.abs(np.angle(np.exp(2j * (TH_[None, :] - ph[:, None])))) / 2      # 0…π/2
        vote = w[:, None] * np.where(dth < np.radians(4), 1.0, 1 - ch[:, None]) * (dth < np.radians(30))
        acc = np.zeros((rho.max() - off + 1, len(TH_)))
        for j in range(len(TH_)): np.add.at(acc[:, j], rho[:, j] - off, vote[:, j])
        i, j = np.unravel_index(acc.argmax(), acc.shape)
        if acc[i, j] < 4: break
        n = np.array([C[j], S[j]]); d = np.array([-S[j], C[j]]); p0 = n * (i + off); k = np.zeros(3)
        p0 = p0 + d * ((np.array(MED_PX) - p0) @ d)   # the line's origin by the disc's centre
        prof = lambda p0, d, n, k: _profile(W, O, p0, d, n, ss, oo, k)
        pk, co = prof(p0, d, n, k); run = _best_run(ss, pk)
        for it in range(5):   # twice straight, then bent: the run grows along a bending stroke
            if run is None: break
            s0, s1 = run; m = (ss >= s0) & (ss <= s1) & (pk > 0.4)
            if m.sum() < 6: run = None; break
            sm, cm, wm = ss[m], co[m], pk[m]
            if it < 2:   # straight: rotate and shift the line onto the fit, its origin at the run's middle
                A1 = np.stack([np.ones_like(sm), sm], 1); k1 = np.linalg.lstsq(A1 * wm[:, None], cm * wm, rcond=None)[0]
                sc = (s0 + s1) / 2; ang = np.arctan(k1[1])
                p0 = p0 + d * sc + n * (k1[0] + k1[1] * sc)
                d, n = d * np.cos(ang) + n * np.sin(ang), n * np.cos(ang) - d * np.sin(ang)
            else:        # bent, if that fits clearly better
                A1 = np.stack([np.ones_like(sm), sm], 1); A2 = np.stack([np.ones_like(sm), sm, sm * sm], 1)
                k1 = np.linalg.lstsq(A1 * wm[:, None], cm * wm, rcond=None)[0]; k2 = np.linalg.lstsq(A2 * wm[:, None], cm * wm, rcond=None)[0]
                r1 = np.sqrt(np.average((A1 @ k1 - cm) ** 2, weights=wm)); r2 = np.sqrt(np.average((A2 @ k2 - cm) ** 2, weights=wm))
                half = (s1 - s0) / 2
                if r1 - r2 > 0.15 and abs(k2[2]) * half * half < 6: k = k2
            pk, co = prof(p0, d, n, k); run = _best_run(ss, pk)
        if run is None:   # nothing along it: weaken the voters of this line and go on
            o = np.abs(X * n[0] + Y * n[1] - p0 @ n); W[ys[o < 1.5], xs[o < 1.5]] *= 0.5; continue
        s0, s1 = run
        while s0 - 0.5 >= ss[0] and _at(ss, pk, s0 - 0.5) > 0.22: s0 -= 0.5   # the tips, while a little ink holds
        while s1 + 0.5 <= ss[-1] and _at(ss, pk, s1 + 0.5) > 0.22: s1 += 0.5
        m = (ss >= s0 + 0.3 * (s1 - s0)) & (ss <= s1 - 0.3 * (s1 - s0))
        if s1 - s0 < 10 or m.sum() < 3: _erase(W, p0, d, n, s0, s1, k, 1.6); continue
        integ = _integral(D, p0, d, n, ss[m], k)   # on the whole map: the pieces left between crossings are honest
        dark = float(np.clip(np.median(pk[m]), 0.45, 1.0))
        width = float(np.clip(WK * np.percentile(integ, 50) / dark, 1.3, WMAX))   # the ink across ÷ its darkness
        out.append((p0.copy(), d.copy(), n.copy(), float(s0), float(s1), k.copy(), width, dark))
        _erase(W, p0, d, n, s0, s1, k, width / 2 + 0.5)
    return merge_strokes(out)


def merge_strokes(st, ang=7.0, across=2.5, gap=40.0):
    """pieces of one stroke (cut where others cross it) joined: nearly the same direction, within `across` px of each
    other's line and `gap` px apart along it; the joined stroke is straight through both pieces' centre lines"""
    st = list(st); changed = True
    pts = lambda q: q[0][None] + q[1][None] * np.linspace(q[3], q[4], 9)[:, None] + q[2][None] * _off(np.linspace(q[3], q[4], 9), q[5])[:, None]
    while changed:
        changed = False
        for a in range(len(st)):
            for b in range(a + 1, len(st)):
                p, q = st[a], st[b]
                if abs(p[1] @ q[1]) < np.cos(np.radians(ang)): continue
                e = pts(q) - p[0][None]; o = e @ p[2] - _off(e @ p[1], p[5]); s = e @ p[1]
                if np.abs(o).max() > across + abs(p[5][2]) * 0: continue
                lo, hi = min(p[3], s.min()), max(p[4], s.max())
                if max(s.min() - p[4], p[3] - s.max()) > gap: continue
                P = np.concatenate([pts(p), pts(q)]); c = P.mean(0)
                w_, v_ = np.linalg.eigh(np.cov((P - c).T)); d = v_[:, 1] * np.sign(v_[:, 1] @ p[1]); n = np.array([-d[1], d[0]])
                sP = (P - c) @ d
                st[a] = (c, d, n, float(sP.min()), float(sP.max()), np.zeros(3), max(p[6], q[6]), max(p[7], q[7]))
                del st[b]; changed = True; break
            if changed: break
    return st


def _off(s, k): return k[0] + k[1] * s + k[2] * s * s


def _profile(W, O, p0, d, n, ss, oo, k):   # along the centre line: the ridge (max across ±2.5 px) of the ink lying
    off = _off(ss, k)                          # along it (where the strokes' direction is clear), the ink's centroid across
    P = p0[None, None, :] + d[None, None, :] * ss[:, None, None] + n[None, None, :] * (oo[None, :, None] + off[:, None, None])
    v = bilinear(W, P[..., 0], P[..., 1])
    c2, s2, ch = (bilinear(a, P[..., 0], P[..., 1]) for a in O)
    t2 = 2 * np.arctan2(n[1], n[0]); agree = (ch + c2 * np.cos(t2) + s2 * np.sin(t2)) / 2   # coh·(1 + cos 2Δ)/2
    v = v * np.clip(1 - ch + agree, 0, 1) ** 2
    pk = v.max(1); wv = np.maximum(v - 0.2, 0); co = (wv * oo[None, :]).sum(1) / np.maximum(wv.sum(1), 1e-6) + off
    return pk, co


def _best_run(ss, pk, gap=10.0, minlen=9.0):   # the run along the line with the most ink (gaps ≤ gap px)
    runs, s, last = [], None, None
    for q, on in zip(ss, pk > 0.36):
        if not on: continue
        if s is None or q - last > gap:
            if s is not None: runs.append((s, last))
            s = q
        last = q
    if s is not None: runs.append((s, last))
    runs = [r for r in runs if r[1] - r[0] >= minlen]
    return max(runs, key=lambda r: pk[(ss >= r[0]) & (ss <= r[1])].sum()) if runs else None


def _at(ss, pk, s): return float(np.interp(s, ss, pk))


def _integral(W, p0, d, n, s, k):   # the ink across the centre line (darkness × px)
    oo = np.arange(-3, 3.01, 0.25); off = _off(s, k)
    P = p0[None, None, :] + d[None, None, :] * s[:, None, None] + n[None, None, :] * (oo[None, :, None] + off[:, None, None])
    return bilinear(W, P[..., 0], P[..., 1]).clip(0, 1).sum(1) * 0.25


def _erase(W, p0, d, n, s0, s1, k, r):   # take a stroke out of the map (its pixels within r px of the centre line)
    ys, xs = np.nonzero(W > 0.02); X, Y = xs + 0.5 - p0[0], ys + 0.5 - p0[1]
    s = X * d[0] + Y * d[1]; o = X * n[0] + Y * n[1] - _off(s, k)
    m = (s >= s0 - 1) & (s <= s1 + 1) & (np.abs(o) < r + 0.8)
    W[ys[m], xs[m]] *= np.clip((np.abs(o[m]) - r) / 0.8, 0, 1)


# ---- the medallion: its fields synthesized (least-squares fits of the photo in polar coordinates, evaluated at the
# texture's own resolution with sharp edges), its strokes vectors
def _fourier(th, M):   # 1, cos θ, sin θ, … cos Mθ, sin Mθ
    cols = [np.ones_like(th)]
    for m in range(1, M + 1): cols += [np.cos(m * th), np.sin(m * th)]
    return cols


def _disc_basis(r, th):
    """the disc's field: polynomials regular at the centre (ρ^n cos mθ, n ≥ m, n − m even, n ≤ 10) and, for the shading
    by its edge (a lens's bevel: dark at the left, light at the upper right), powers of its outer part (ρ > 0.72 of the
    disc) times angles to 10θ"""
    rn = r / DISC_EDGE; cols = []
    for m in range(11):
        for n in range(m, 11, 2):
            if m == 0: cols.append(rn ** n)
            else: cols += [rn ** n * np.cos(m * th), rn ** n * np.sin(m * th)]
    F = _fourier(th, 10); o = np.clip((rn - 0.72) / 0.28, 0, None)
    for k in (2, 3, 4, 6): cols += [o ** k * f for f in F]
    return np.stack(cols, -1)


def _band_basis(r, th, a, b, deg):   # a ring's band [a, b]: Legendre polynomials across it times angles to 10θ
    t = (r - a) / (b - a) * 2 - 1; F = _fourier(th, 10); cols = []
    for d in range(deg + 1):
        P = np.polynomial.legendre.Legendre.basis(d)(t); cols += [P * f for f in F]
    return np.stack(cols, -1)


MED_ZONES = [('disc', 0.0, MED_EDGES[0], None), ('outline', MED_EDGES[0], MED_EDGES[1], 1),
             ('inner band', MED_EDGES[1], MED_EDGES[2], 2), ('outer band', MED_EDGES[2], MED_EDGES[3], 2)]


def medallion_fields(shot, strokes):
    """each zone's colour (R, G, B) as a smooth function of (ρ, θ), fitted to the photo's pixels inside it (0.6 px off its
    edges, the disc's dark strokes and a pixel round them left out): ≈ 60–150 numbers a channel per zone, no pixel of
    the photo kept"""
    cxp, cyp = MED_PX; rx, ry = MED_AX
    yy, xx = np.mgrid[0:shot.shape[0], 0:shot.shape[1]] + 0.5
    X, Y = (xx - cxp) / rx, (yy - cyp) / ry; rho, th = np.hypot(X, Y), np.arctan2(Y, X)
    mar = 0.6 / MED_AX[1]; out = {}
    for name, a, b, deg in MED_ZONES:
        m = (rho > (a + mar if a else -1)) & (rho < b - mar)
        if deg is None: m &= ~ndimage.binary_dilation(strokes, iterations=1)
        B = _disc_basis(rho[m], th[m]) if deg is None else _band_basis(rho[m], th[m], a, b, deg)
        out[name] = np.linalg.solve(B.T @ B + 1e-6 * m.sum() * np.eye(B.shape[1]), B.T @ shot[m].astype(np.float64))
    return out


def medallion(rgb, metal):
    shot = np.asarray(Image.open(PACKSHOT).convert('RGB')).astype(np.float32)
    L = shot.mean(2)
    cxp, cyp = MED_PX; rx, ry = MED_AX
    # the disc's dark strokes: darkness against the local silver, the silver read from the pixels round them (the
    # strokes are far darker than anything else on the disc: L < 140 against 150…250; the grey ghosts stay silver)
    keep = 1 - ndimage.binary_dilation(L < STROKE_L, iterations=1).astype(np.float32)
    norm = lambda a: ndimage.gaussian_filter(a * keep, 3) / np.maximum(ndimage.gaussian_filter(keep, 3), 1e-3)
    bg = norm(L)
    Ls = hexrgb(STROKE).mean()
    D = np.clip((bg - L) / np.maximum(bg - Ls, 20), 0, 1.2)
    yy, xx = np.mgrid[0:shot.shape[0], 0:shot.shape[1]] + 0.5
    rr = np.hypot((xx - cxp) / rx, (yy - cyp) / ry)
    D[rr > STROKE_RHO] = 0
    fields = medallion_fields(shot, ndimage.binary_dilation(D > 0.3, iterations=2))
    # the texture's medallion window (texture ρ = photo ρ: the front's mapping carries the photo's x stretch)
    R = MED_R * TH; cu, cv = MED_UV[0] * TW, MED_UV[1] * TH
    x0, x1, y0, y1 = int(cu - R - 4), int(cu + R + 5), int(cv - R - 4), int(cv + R + 5)
    ty, tx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
    d = np.hypot(tx - cu, ty - cv); rho = d / R
    th = np.arctan2(ty - cv, tx - cu)
    u, v = tx / TW, ty / TH; pxx, pyy = photo_xy(u, v)
    # the zones, each its fitted field, edges anti-aliased at the texture's scale; evaluated a band of rows at a time
    win = rgb[y0:y1, x0:x1]; gold = np.zeros(d.shape, np.float32); inner = np.zeros(d.shape, np.float32)
    acc = np.zeros(win.shape, np.float32); covs = np.zeros(d.shape, np.float32)   # Σ coverage × field, Σ coverage
    for name, a, b, deg in MED_ZONES:
        cov = np.clip(b * R - d + 0.5, 0, 1) - (np.clip(a * R - d + 0.5, 0, 1) if a else 0)
        for r0 in range(0, d.shape[0], 48):
            sl = slice(r0, r0 + 48); m = cov[sl] > 0
            if not m.any(): continue
            B = _disc_basis(rho[sl][m], th[sl][m]) if deg is None else _band_basis(rho[sl][m], th[sl][m], a, b, deg)
            acc[sl][m] += np.clip(B @ fields[name], 0, 255) * cov[sl][m][:, None]
        covs += cov
        if 'band' in name: gold += cov
        if deg is None: inner += cov
    win[:] = win * (1 - covs[..., None]) + acc
    # strokes: traced on the photo (trace_strokes), drawn as spindles at the texture's scale, edges anti-aliased by
    # their distance in texels (the photo's x and y scales differ: the normal's own scale)
    J = np.array([TW / XW, TH / (FOOT[0] - TOP[0] + (FOOT[1] - TOP[1]) * cxp)])
    keepa = np.ones(d.shape, np.float32)
    for p0, dd, nn, s0, s1, k, wd, dark in trace_strokes(D):
        if s1 - s0 < MINLEN: continue   # a crossing's leftover, not a stroke: drawn it reads as a leaf
        P = np.stack([pxx - p0[0], pyy - p0[1]], -1)
        sx = P @ dd; o = P @ nn - _off(sx, k)
        m = (sx > s0 - 1) & (sx < s1 + 1) & (np.abs(o) < wd)
        if not m.any(): continue
        t_ = np.clip((sx[m] - s0) / (s1 - s0), 0, 1); hw = wd / 2 * (1 - np.abs(2 * t_ - 1) ** TIP)
        a = np.clip(0.5 - (np.abs(o[m]) - hw) * np.linalg.norm(J * nn), 0, 1) * min(1.0, dark / 0.5)
        keepa[m] *= 1 - a
    cov = (1 - keepa) * np.clip((DISC_EDGE - 0.02) * R - d + 0.5, 0, 1)
    win += (hexrgb(STROKE) - win) * cov[..., None]
    m = metal[y0:y1, x0:x1]
    m[..., 1] = m[..., 1] * (1 - gold) + GOLD_ROUGH * gold
    m[..., 2] = np.maximum(m[..., 2], GOLD_METAL * gold)
    m[..., 1] = m[..., 1] * (1 - inner) + INK_ROUGH * inner   # the printed silver: no metal


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]; return x * x + y * y <= r * r + 0.5


# ---- the monogram
def monogram(rgb, metal):
    src = Image.open(MONOGRAM).convert('RGBA'); im = Image.new('RGBA', (src.width + 40, src.height + 40)); im.paste(src, (20, 20))
    a = np.asarray(im.getchannel('A'))
    ys, xs = np.nonzero(a > 8); bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    (u0, u1), (v0, v1) = M_BOX
    X0_, X1_, Y0_, Y1_ = u0 * TW, u1 * TW, v0 * TH, v1 * TH
    ix0, ix1, iy0, iy1 = int(np.floor(X0_)) - 1, int(np.ceil(X1_)) + 1, int(np.floor(Y0_)) - 1, int(np.ceil(Y1_)) + 1
    kx, ky = (bx1 - bx0) / (X1_ - X0_), (by1 - by0) / (Y1_ - Y0_)
    box = (bx0 + (ix0 - X0_) * kx, by0 + (iy0 - Y0_) * ky, bx0 + (ix1 - X0_) * kx, by0 + (iy1 - Y0_) * ky)
    # premultiplied reduction: colour weighted by alpha
    pre = np.asarray(im).astype(np.float32); pre[..., :3] *= pre[..., 3:] / 255
    chans = [np.asarray(Image.fromarray(pre[..., k]).resize((ix1 - ix0, iy1 - iy0), Image.LANCZOS, box=box)) for k in range(4)]
    al = np.clip(chans[3] / 255, 0, 1); col = np.stack(chans[:3], -1) / np.maximum(al[..., None], 1e-3)
    col = np.clip(col, 0, 255)
    # its gold's median pulled to the photo's (a gain per channel, in linear light)
    lin = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4
    srgb = lambda l: (1.055 * np.clip(l, 0, 1) ** (1 / 2.4) - 0.055) * 255
    solid = al > 0.9
    med = np.median(col[solid], 0); gain = lin(hexrgb(M_MEDIAN)) / lin(med)
    col = srgb(lin(col) * gain)
    reg = rgb[iy0:iy1, ix0:ix1]; reg += (col - reg) * al[..., None]
    m = metal[iy0:iy1, ix0:ix1]
    m[..., 1] = m[..., 1] * (1 - al) + GOLD_ROUGH * al; m[..., 2] = np.maximum(m[..., 2], GOLD_METAL * al)


def box_face(fonts):
    rgb = np.ones((TH, TW, 3), np.float32) * hexrgb(PAPER)
    metal = np.zeros((TH, TW, 3), np.float32); metal[..., 1] = PAPER_ROUGH
    full = np.ones(TW, np.float32)
    # the band (full width) and its gold name
    bv = cover1(BAND_V[0] * TH, BAND_V[1] * TH, TH)
    over(rgb, bv[:, None] * full[None, :], hexrgb(BAND)); metal[..., 1] -= (PAPER_ROUGH - INK_ROUGH) * bv[:, None]
    for line in LINES:
        a = typeset_line(fonts, line)
        over(rgb, a, hexrgb(line[5]))
        if line[5] == '#CEC296':   # the band's gold letters: foil
            metal[..., 1] = metal[..., 1] * (1 - a) + GOLD_ROUGH * a; metal[..., 2] = np.maximum(metal[..., 2], GOLD_METAL * a)
        else:
            metal[..., 1] = metal[..., 1] * (1 - a) + INK_ROUGH * a
    for (ua, ub), vv in RULES:
        a = cover1((vv - RULE_T / 2) * TH, (vv + RULE_T / 2) * TH, TH)[:, None] * cover1(ua * TW, ub * TW, TW)[None, :]
        over(rgb, a, hexrgb(RULE_C)); metal[..., 1] = metal[..., 1] * (1 - a) + INK_ROUGH * a
    (fu0, fu1), (fv0, fv1), ft, fc = FRAME; h = ft / 2 * TH
    cx = lambda a_, b_: cover1(a_, b_, TW)[None, :]; cy = lambda a_, b_: cover1(a_, b_, TH)[:, None]
    outer = cy(fv0 * TH - h, fv1 * TH + h) * cx(fu0 * TW - h, fu1 * TW + h)
    inner = cy(fv0 * TH + h, fv1 * TH - h) * cx(fu0 * TW + h, fu1 * TW - h)
    a = np.clip(outer - inner, 0, 1)
    over(rgb, a, hexrgb(fc))
    metal[..., 1] = metal[..., 1] * (1 - a) + GOLD_ROUGH * a; metal[..., 2] = np.maximum(metal[..., 2], GOLD_METAL * a)
    monogram(rgb, metal)
    medallion(rgb, metal)
    face = Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8))
    m = np.clip(metal * 255 + 0.5, 0, 255).astype(np.uint8)
    mat = Image.fromarray(m).resize((TW // 2, TH // 2), Image.BOX)
    return face, mat


if __name__ == '__main__':
    fdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
    face, mat = box_face({'rubik': os.path.join(fdir, 'Rubik[wght].ttf'), 'sign': os.path.join(fdir, 'DejaVuSans-Bold.ttf')})
    face.save(f'{out}/box-face.png', optimize=True); mat.save(f'{out}/box-metal.png', optimize=True)
    for n in ('box-face.png', 'box-metal.png'):
        im = Image.open(f'{out}/{n}'); print(n, im.size, im.mode, os.path.getsize(f'{out}/{n}') // 1024, 'KB')
