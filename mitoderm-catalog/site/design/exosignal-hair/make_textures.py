"""Textures for the three.js EXOSIGNAL HAIR scene (site/proto/scenes/exosignal-hair.js), sharp at any size: the print is
typeset, not cut from the photo. Places and sizes are measured on the only packshot, protocols/print/img/exosignal-hair.webp
(1087×714: the box's front seen square on, five ampoules before its lower right corner), in edge coordinates (a pixel i
spans [i, i+1)), glyph ink boxes at half their contrast:
  box  the front face, photo x 2.4…941.9, y 2.1…639.6; positions below in photo px
  amp  the ampoule's label unwrapped onto θ (degrees round the body: 0 = the big word's axis, + to the right as it is
       read) × h (fraction of the ampoule's height from its foot), measured on A4 (axis x 1019, radius 42 px)
Typefaces (SIL OFL, github.com/google/fonts): Jost for the logo «EXOSIGNAL» («EXO» 700, «SIGNAL» 280 with the print's
stencil cuts — E's middle arm free, X's upper right arm cut off — and its «signal» steps in S, I, N and A: I and N
measured ×8, S and A fitted ×16 by overlay on the photo), «H A I R» 420 and «VM corporation» (Jost 300 small capitals
«VM», «corporation» 150); Rubik for the grey block (the original is a grotesque like Roboto: each line fitted to its
measured ink box, the title letter-spaced); «℮» from DejaVu Sans Bold. The VM monogram is three polygons fitted to the
photo's edges (threshold 90), symmetric about its axis. Ink boxes ±0.5 px (thin letters' tops ±1) with the face reduced
to the photo's scale; the grey lines' weights and thinning are set on the rendered key (see BLOCK). The packaging's
vector file would replace all of it one for one.
Writes into <out dir>:
  box-face.png   the front's colours, RGB 2048×1390 (1.48 texels per px where the front is largest in a 3840 key, 1.11
                 on a 5120 cover): the black paper with its lighter top rim and darker foot band, the warm grey ink
                 (#aaa29b, as photographed), the foil in its photographed colour per letter
  box-metal.png  the front's material, RGB 1024×695: G roughness (paper 1 × 0.65, foil 0.43 × 0.65 = 0.28), B metalness
  amp-print.png  alpha of the ampoule's black print, L 491×1024: θ −14…+96 × h 0.10…0.50 (row 0 at h 0.50); the
                 two lines of the small block the photo does not resolve are left out (no stand-in bars)
  mitoscan.webp, mitopen.webp   S5's devices: protocols/print/img's packshots, the same pixels in lossy WebP (q 86,
                 alpha 92; 60 + 18 KB instead of 655 + 104 lossless): the scene shows them only dimmed, at most 637 px wide
usage: python3 -I make_textures.py <font dir with Jost[wght].ttf, Rubik[wght].ttf, DejaVuSans-Bold.ttf> <out dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

SS = 2                                                             # drawn at 2× and reduced: smooth edges
FX0, FY0, FW, FH = 2.4, 2.1, 939.5, 637.5                          # the front on the photo
TW, TH = 2048, 1390                                                # box-face.png: 1.48 texels per px at its largest in a 3840 key
PAPER, RIM, FOOT, INK = (0x16, 0x15, 0x16), (0x26, 0x25, 0x24), (0x0e, 0x0e, 0x0e), (0xaa, 0xa2, 0x9b)
# the logo: (letter, weight, ink centre x, ink width, colour); cap line and baseline: «EXO» 261.5 / 299.3, «SIGNAL»
# 262.4 / 299.6 (its flat stroke ends stop short of the bold letters' by 0.6 px top and bottom). Colours:
# the photographed foil (bold letters by their plateau; thin ones lose contrast to their size and are lifted to what
# their plateau reads once reduced to the photo's scale, keeping its slope: lemon in the middle, paler to the right)
CAP0, BASE0, THIN = 261.5, 299.3, (262.4, 299.6)
LOGO = [('E', 700, 292.70, 24.06, '#d4b16b'), ('X', 700, 339.98, 34.9, '#f1c46b'), ('O', 700, 390.86, 39.14, '#fae06e'),
        ('S', 280, 436.54, 21.0, '#fae676'), ('I', 280, 469.10, 0, '#eedd75'), ('G', 280, 510.14, 34.1, '#f2dc72'),
        ('N', 280, 565.15, 30.9, '#e5d06d'), ('A', 280, 615.67, 33.1, '#eed285'), ('L', 300, 660.64, 19.9, '#ecd9a8')]
HAIR = [('H', 554.53, 10.7, '#e6cc70'), ('A', 594.75, 10.5, '#e4c86e'), ('I', 630.87, 0, '#f6e0a0'), ('R', 666.48, 9.3, '#fff8c6')]
CAP1, BASE1, HAIR_W = 315.0, 328.9, 420                            # «H A I R», Jost 420
# the grey block, Rubik: (text, weight, ink box x0, x1, cap line, baseline, thinning: each edge moved in by that part
# of the cap height); «℮» set apart (DejaVu). Weights and thinning are set on the rendered 3840 key, not on this
# texture: the GPU, like the camera, averages light rather than sRGB values, so a thin line renders brighter than an
# sRGB reduction of the texture shows. Each line's ink energy (mean lightness above the paper) in the v1 key is 0.98…1.12
# of the photo's, the monogram's (a large shape) 1.13 (the key's light on the front, measured as the photo's)
BLOCK = [('EXOSIGNAL HAIR', 500, 407.0, 528.0, 489.9, 500.0, 0.03),   # letter-spaced (the others fitted by narrowing);
         # the photo reads «SÉRUM» in both lines (×12; packaging-text.json's Spanish line was fixed to match, 24/10)
         ('SIERO NUTRIENTE PER IL CUOIO CAPELLUTO', 400, 357.0, 578.0, 512.0, 520.2, 0.023),
         ('NOURISHING SCALP SERUM', 300, 411.0, 524.0, 523.8, 530.2, 0.0195),
         ('SÉRUM NOURRISSANT CUIR CHEVELU', 300, 391.0, 543.0, 533.9, 540.4, 0.0205),
         ('SÉRUM NUTRITIVO PARA EL CUERO CABELLUDO', 300, 370.0, 564.0, 543.9, 550.4, 0.0195),
         ('Net 5 x 5 ml ℮ 5 x 0.17 fl.oz.', 300, 404.0, 530.0, 572.9, 581.0, 0.003)]   # barely: «℮» is hairline
VMCORP = (438.4, 504.6, 111.0, 116.0)   # «VM corporation»: ink x, x-height line, baseline («VM» small capitals)
VM_STYLE = (300, 150, 0.0065)            # Jost weights of «VM» and «corporation», thinning (of the x-height)
# the VM monogram (photo px): axis, the V (top line, outer/inner half widths there and their slopes), the legs
VM_AXIS, VM_TOP = 472.4, 50.3
VM_V = ((22.1, 0.407), (14.37, 0.38))   # half width at the top, its loss per px down: outer edges, inner edges
VM_LEG = (25.0, 66.3, 19.3, 77.4, 94.6, 0.132)   # outer half width at its top y, inner half width at the cut's foot y, foot y, lean


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.BASIC)   # no ligatures: «fl» letter by letter
    if weight: f.set_variation_by_axes([weight])
    return f


def ink(img, thr=127):   # the ink box of an L image: x0, y0, x1, y1
    a = np.asarray(img) > thr; ys, xs = np.nonzero(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def run(parts, size, track=0.0):   # a line of (text, font path, weight, scale) on its baseline, one image; with `track`
    fonts = [(t, font(p, size * k, w)) for t, p, w, k in parts]   # px between letters, set letter by letter
    m = int(np.ceil(size)); width = int(sum(f.getlength(t) + track * len(t) for t, f in fonts)) + m * 2
    im = Image.new('L', (width, m * 3)); d = ImageDraw.Draw(im); x = m
    for t, f in fonts:
        for piece in (t if track else [t]):
            d.text((x, m * 2), piece, font=f, fill=255, anchor='ls'); x += f.getlength(piece) + track
    return im, m * 2


def cap_of(path, weight, size=400):   # the H's ink height at this size
    im, _ = run([('H', path, weight, 1)], size); x0, y0, x1, y1 = ink(im); return (y1 - y0) / size


def glyph(path, ch, weight, cap):   # one letter at cap height `cap` px: its ink (L), the ink's top relative to the cap line
    size = cap / cap_of(path, weight)
    im, base = run([(ch, path, weight, 1)], round(size * 4) / 4 or 1)
    x0, y0, x1, y1 = ink(im, 0)
    return np.asarray(im.crop((x0, y0, x1, y1))).astype(np.float32) / 255, y0 - (base - cap)


def shift_rows(a, y0, y1, d, x0=0, x1=None, ramp=0.0):
    """moves the ink of rows y0…y1 (and only between columns x0…x1) right by d px; with a ramp the step is drawn over
    `ramp` rows; pixels pushed past x1 join what is there (a stem)"""
    x1 = a.shape[1] if x1 is None else x1
    out = a.copy(); xs = np.arange(a.shape[1], dtype=np.float32)
    for y in range(max(0, int(y0)), min(a.shape[0], int(np.ceil(y1)))):
        k = d * (min(1.0, (y - y0) / ramp) if ramp else 1.0)
        row = a[y].copy(); win = (xs >= x0) & (xs < x1)
        src = np.where(win, row, 0); out[y][win] = 0
        moved = np.interp(xs - k, xs, src, left=0, right=0)
        out[y] = np.maximum(out[y], moved)
    return out


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def slit(a, top, c, xc, yc, phi, move, r0, r1):
    """the S's step: a slit through (xc of the ink width, yc cap below the cap line), its normal phi° from the x axis
    (down +); the side left of it slides by `move` (cap; x right, y down), the other side the opposite way, in full
    within r0 cap of the slit's centre and not at all beyond r1 (the bowls and terminals stay as they are)"""
    h, w = a.shape; cols = np.nonzero(a.max(0) > 0.5)[0]
    X, Y = cols.min() + xc * (cols.max() + 1 - cols.min()), yc * c - top
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); t = np.radians(phi)
    sd = (xx - X) * np.cos(t) + (yy - Y) * np.sin(t); left = np.clip(0.5 - sd, 0, 1)
    k = 1 - smooth(r0 * c, r1 * c, np.hypot(xx - X, yy - Y)); dx, dy = move[0] * c * k, move[1] * c * k
    A = ndimage.map_coordinates(a, [yy - dy, xx - dx], order=1, cval=0)
    B = ndimage.map_coordinates(a, [yy + dy, xx + dx], order=1, cval=0)
    return left * A + (1 - left) * B


def a_bar(a, top, c, ycut, yb, tb, gap, rf, S4=4):
    """the A's step: the left leg stops at ycut (cap below the cap line); the crossbar (centre yb, thickness tb) stops
    `gap` short of the right leg and bends down into the lower left leg in a round corner (rf along each arm)"""
    h, w = a.shape; left, inner = {}, {}
    for y in range(h):   # rows where the legs are two runs: the left leg's centre, the right leg's inner edge
        r = np.flatnonzero(np.diff(np.r_[0, (a[y] > 0.5).astype(int), 0]))
        if len(r) == 4: left[y] = (r[0] + r[1]) / 2; inner[y] = r[2]
    ys = np.array(sorted(left)); kl = np.polyfit(ys, [left[y] for y in ys], 1); kr = np.polyfit(ys, [inner[y] for y in ys], 1)
    Yc, Yb = ycut * c - top, yb * c - top
    out = a.copy()
    for y in range(max(0, int(Yc)), min(h, int(np.ceil(Yb + (rf + tb) * c)))):   # the old bar and the leg's middle go
        x1 = int(np.polyval(kr, y) - 0.5); out[y, :x1] = a[y, :x1] * (Yc - y if y < Yc else 0)
    P1 = np.array([np.polyval(kl, Yb), Yb]); d = rf * c
    leg = np.array([kl[0], 1.0]); leg /= np.hypot(*leg)   # down the left leg
    P0, P2 = P1 + leg * d, P1 + np.array([d, 0])
    pts = [P0 + leg * tb * c * 1.5] + [(1 - t) ** 2 * P0 + 2 * t * (1 - t) * P1 + t * t * P2 for t in np.linspace(0, 1, 24)]
    pts.append(np.array([np.polyval(kr, Yb) - gap * c, Yb]))
    im = Image.new('L', (w * S4, h * S4))
    ImageDraw.Draw(im).line([(x * S4, y * S4) for x, y in pts], fill=255, width=max(1, round(tb * c * S4)), joint='curve')
    return np.maximum(out, np.asarray(im.resize((w, h), Image.BOX)).astype(np.float32) / 255)


def logo_letter(ch, weight, width, cap, cuts=True):   # a logo letter (with the print's cuts and steps), in canvas px;
    a, top = glyph(JOST, ch, weight, cap)                 # its ink (L), the ink's top below the cap line, its ink centre
    if width:   # narrowed (or widened) to the measured ink width
        im = Image.fromarray((a * 255).astype(np.uint8)).resize((max(1, round(width)), a.shape[0]), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32) / 255
    h, w = a.shape; c = cap
    if not cuts: pass
    elif ch == 'E':   # the middle arm stands free of the stem: a gap 0.116 cap wide
        stem = int(np.argmax(a[int(h * 0.27)] < 0.5))   # the stem's right edge, between the top and middle arms
        rows = np.nonzero(a[:, stem + int(0.2 * c)] > 0.5)[0]; mid = rows[(rows > h * 0.3) & (rows < h * 0.7)]
        a[max(0, mid.min() - 2):mid.max() + 3, stem:stem + round(0.116 * c)] = 0
    elif ch == 'X':   # the upper right arm cut off along the main stroke: a band 0.13 cap wide right of its right edge
        ys = np.arange(round(0.02 * c), round(0.18 * c))
        edge = [np.nonzero(a[y] > 0.5)[0] for y in ys]
        edge = np.array([e[np.argmax(np.diff(e) > 1)] + 1 if (np.diff(e) > 1).any() else e.max() + 1 for e in edge], float)
        k, b = np.polyfit(ys, edge, 1)   # the main stroke's right edge, x = k y + b
        for y in range(0, round(0.5 * c)):
            x0 = k * y + b; xs = np.arange(w)
            a[y][(xs >= x0) & (xs < x0 + 0.13 * c)] = 0
    elif ch == 'I':   # cut at half height, the lower half 0.066 cap to the right (a short slanted step)
        a = np.pad(a, ((0, 0), (0, round(0.08 * c))))
        a = shift_rows(a, 0.495 * c - top, h, 0.066 * c, ramp=0.04 * c)
    elif ch == 'S':   # the spine split by a slit through its middle, leaning 16° (foot right): the upper bowl's side
        # slides right and up, the other left and down, so the halves meet in a pinch (fitted ×16 on the photo)
        a = slit(a, top, c, 0.538, 0.375, -16.3, (0.0247, -0.0322), 0.2, 0.32)
    elif ch == 'N':   # the diagonal broken at 0.44 of the height, its lower part 0.09 cap to the right (into the stem)
        row = a[round(0.8 * h)] > 0.5; runs = np.flatnonzero(np.diff(np.r_[0, row.astype(int), 0]))
        left_stem_r, right_stem_l = runs[1], runs[-2]
        a = shift_rows(a, 0.442 * c - top, h, 0.09 * c, left_stem_r + 1, right_stem_l, ramp=0.02 * c)
    elif ch == 'A':   # the left leg stops above the crossbar; the thin bar bends down into the lower leg and stands
        # free of the right leg (fitted ×16 on the photo)
        a = a_bar(a, top, c, 0.564, 0.643, 0.0414, 0.05, 0.149)
    cols = np.nonzero(a.max(0) > 0.5)[0]
    return a, top, (cols.min() + cols.max() + 1) / 2


def paste(canvas, a, x, y, value=1.0):   # max-composite an alpha patch (float) at canvas px (x, y), sub-pixel by resampling
    ix, iy = int(np.floor(x)), int(np.floor(y)); fx, fy = x - ix, y - iy
    if fx or fy:   # bilinear shift
        p = np.pad(a, ((1, 1), (1, 1)))
        a = (p[1:, 1:] * (1 - fx) * (1 - fy) + p[1:, :-1] * fx * (1 - fy) + p[:-1, 1:] * (1 - fx) * fy + p[:-1, :-1] * fx * fy)
    h, w = a.shape; H, W = canvas.shape
    X0, Y0, X1, Y1 = max(0, ix), max(0, iy), min(W, ix + w), min(H, iy + h)
    if X1 <= X0 or Y1 <= Y0: return
    sub = a[Y0 - iy:Y1 - iy, X0 - ix:X1 - ix] * value
    canvas[Y0:Y1, X0:X1] = np.maximum(canvas[Y0:Y1, X0:X1], sub)


def erode(im, e):   # thinner strokes: each edge moved in by e px (an L image drawn large; the result is hard-edged)
    if e <= 0: return im
    d = ndimage.distance_transform_edt(np.asarray(im) > 127)
    return Image.fromarray((np.clip(d - e, 0, 1) * 255).astype(np.uint8))


def fit_line(parts, box, size=200, measure=None, spaced=False, thin=0.0):
    """a line of text runs fitted to its measured ink box (x0, x1, cap line, baseline) in canvas px: the ink box of
    `measure` (the same line without accents, which stand above the cap line) is scaled onto it; `spaced`: its
    letters keep their proportions and the line is letter-spaced to its width instead; `thin`: its strokes thinned
    by that fraction of the cap height on each side"""
    x0, x1, top, base = box; track = 0.0
    if spaced:
        ref, rb = run(measure or parts, size); ix0, iy0, ix1, iy1 = ink(ref)
        s = (base - top) / (iy1 - iy0); n = sum(len(t) for t, *_ in parts)
        track = ((x1 - x0) / s - (ix1 - ix0)) / (n - 1)
    im, b = run(parts, size, track); ref, rb = run(measure or parts, size, track)
    _, iy0, _, iy1 = ink(ref); e = thin * (iy1 - iy0); im, ref = erode(im, e), erode(ref, e)
    ix0, iy0, ix1, iy1 = ink(ref)
    sx, sy = (x1 - x0) / (ix1 - ix0), (base - top) / (iy1 - iy0)
    w, h = max(1, round(im.width * sx)), max(1, round(im.height * sy))
    a = np.asarray(im.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255
    return a, x0 - ix0 * sx, top - iy0 * sy


def box_face(fdir):
    K = TW * SS / FW
    X = lambda x: (x - FX0) * K
    Y = lambda y: (y - FY0) * K
    W, H = TW * SS, TH * SS
    ink_a = np.zeros((H, W), np.float32)
    foil_a = np.zeros((H, W), np.float32); foil_c = np.zeros((H, W, 3), np.float32)
    # the logo and «H A I R»: each letter's ink centred on its measured centre, its colour where its ink is
    letters = [(ch, weight, cx, wd, col) + ((CAP0, BASE0) if weight > 500 else THIN) + (True,) for ch, weight, cx, wd, col in LOGO] \
        + [(ch, HAIR_W, cx, wd, col, CAP1, BASE1, False) for ch, cx, wd, col in HAIR]
    for ch, weight, cx, wd, col, cap, base, cuts in letters:
        a, top, mid = logo_letter(ch, weight, wd * K, (base - cap) * K, cuts)
        x, y = X(cx) - mid, Y(cap) + top
        paste(foil_a, a, x, y)
        h, w = a.shape; X0, Y0 = int(x), int(y)
        foil_c[Y0:Y0 + h + 2, X0:X0 + w + 2][np.pad(a, ((0, 2), (0, 2))) > 0.002] = [int(col[i:i + 2], 16) for i in (1, 3, 5)]
    # the grey block
    rub = os.path.join(fdir, 'Rubik[wght].ttf')
    for text, weight, x0, x1, top, base, thin in BLOCK:
        box = (X(x0), X(x1), Y(top), Y(base))
        if '℮' in text:   # «℮» from DejaVu Sans Bold, its height that of the Rubik capitals around it
            a_, b_ = text.split('℮'); k = cap_of(rub, weight) / cap_of(DEJAVU, None)   # DEJAVU: set in __main__
            parts = [(a_, rub, weight, 1), ('℮', DEJAVU, None, k), (b_, rub, weight, 1)]
            a, ox, oy = fit_line(parts, box, thin=thin)
        else:
            plain = text.replace('É', 'E')
            a, ox, oy = fit_line([(text, rub, weight, 1)], box, measure=[(plain, rub, weight, 1)], spaced=text == BLOCK[0][0], thin=thin)
        paste(ink_a, a, ox, oy)
    # «VM corporation»: «VM» small capitals at the x-height of «corporation» (Jost, VM_STYLE)
    x0, x1, xh, base = VMCORP; jost = JOST; size = 200; vw, cw, thin = VM_STYLE
    im, b = run([('x', jost, cw, 1)], size); _, xy0, _, xy1 = ink(im); xh_k = (xy1 - xy0) / size   # x-height per size
    k = xh_k / cap_of(jost, vw)   # «VM» at that height
    parts = [('VM', jost, vw, k), (' corporation', jost, cw, 1)]
    e = thin * xh_k * size; im, b = run(parts, size); im = erode(im, e); ix0, iy0, ix1, iy1 = ink(im)
    sx = (X(x1) - X(x0)) / (ix1 - ix0); sy = (Y(base) - Y(xh)) / (xh_k * size - 2 * e)
    a = np.asarray(im.resize((round(im.width * sx), round(im.height * sy)), Image.LANCZOS)).astype(np.float32) / 255
    paste(ink_a, a, X(x0) - ix0 * sx, Y(base) - (b - e) * sy)
    # the VM monogram: three polygons, drawn at 4× the canvas and reduced
    S4 = 4; reg = Image.new('L', (int(X(520) - X(420)) * S4, int(Y(110) - Y(40)) * S4))   # only its region
    ox, oy = X(420), Y(40)
    P = lambda x, y: ((X(x) - ox) * S4, (Y(y) - oy) * S4)
    (ho, so), (hi, si) = VM_V; t = VM_TOP
    apex_o = t + ho / so; apex_i = t + hi / si
    d = ImageDraw.Draw(reg)
    d.polygon([P(VM_AXIS - ho, t), P(VM_AXIS - hi, t), P(VM_AXIS, apex_i), P(VM_AXIS + hi, t), P(VM_AXIS + ho, t), P(VM_AXIS, apex_o)], fill=255)
    out0, ytop, in0, ycut, yfoot, lean = VM_LEG
    dout = lambda y: out0 + lean * (y - ytop); din = lambda y: in0 + lean * (y - ycut)
    for s in (-1, 1):
        d.polygon([P(VM_AXIS + s * dout(ytop), ytop), P(VM_AXIS + s * din(ycut), ycut), P(VM_AXIS + s * din(yfoot), yfoot),
                   P(VM_AXIS + s * dout(yfoot), yfoot)], fill=255)
    reg = reg.resize((reg.width // S4, reg.height // S4), Image.BOX)
    paste(ink_a, np.asarray(reg).astype(np.float32) / 255, ox, oy)
    # the paper: its lighter top rim (v 0…0.03), the darker band at its foot (v 0.9795…0.992) and the foot's edge
    v = (np.arange(H, dtype=np.float32) + 0.5) / H
    paper = np.array(PAPER, np.float32)[None, None, :] * np.ones((H, 1, 1), np.float32)
    rim = np.clip(1 - v / 0.03, 0, 1)[:, None, None]
    paper = paper + (np.array(RIM, np.float32) - PAPER)[None, None, :] * rim
    foot = (np.clip((v - 0.9795) / 0.002, 0, 1) * np.clip((0.992 - v) / 0.004, 0, 1))[:, None, None]
    paper = paper + (np.array(FOOT, np.float32) - PAPER)[None, None, :] * foot
    edge = np.clip((v - 0.992) / 0.008, 0, 1)[:, None, None]
    paper = paper + (np.array(RIM, np.float32) - paper) * edge
    rgb = paper * np.ones((1, W, 1), np.float32)
    rgb = rgb + (np.array(INK, np.float32) - rgb) * ink_a[..., None]
    rgb = rgb + (foil_c - rgb) * foil_a[..., None]
    face = Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8)).resize((TW, TH), Image.LANCZOS)
    # the material: roughness (G) and metalness (B) of the foil, at a third of the size (the foil's colour draws its edges)
    foil = Image.fromarray((foil_a * 255).astype(np.uint8)).resize((1024, 695), Image.BOX)
    m = np.asarray(foil).astype(np.float32) / 255
    mat = np.stack([np.zeros_like(m), 255 * (1 - m * (1 - 0.28 / 0.65)), 255 * m], -1)
    return face, Image.fromarray(np.clip(mat + 0.5, 0, 255).astype(np.uint8))


# ---- the ampoule's label: θ (−14…+96°) × h (0.10…0.50), 5120 px per ampoule height; typeset along h (as it is read,
# from the foot up, the letters' tops toward −θ) on a canvas X = h, Y = θ, then turned a quarter left
TH0, TH1, H0, H1 = -14.0, 96.0, 0.10, 0.50
PX = 2560                                  # px per ampoule height (2.3 texels per px for the S3 close-up in a 3840 key)
R = 0.1
AW = round(PX * R * np.radians(TH1 - TH0)); AH = round(PX * (H1 - H0))
# the lockup as on the box (same proportions): its ink from h 0.130 (E's foot) to 0.466 (L's end), cap 19.2° round
# the body (0.0335 of the height), centred on θ 0; «H A I R» under the word's end, from N's left edge to L's right edge,
# its baseline 0.78 cap below the lockup's; the small block (θ of each line's middle, h of its ends, cap in degrees: the
# photo's 0.010 / 0.008 of the height (5.7° / 4.6°, ±1°) a little up, so that the lines need little letter-spacing to fill
# their measured length): «EXOSIGNAL HAIR» (Rubik 600), «Siero nutriente per il cuoio capelluto» (Rubik 400); the two
# lines under them (θ 77° and 89.5°) the photo does not resolve: left out, as nothing is drawn that is not read there
AMP_LOCKUP = (0.130, 0.466, -9.6, 9.6)
AMP_SMALL = [('EXOSIGNAL HAIR', 600, 51.0, 0.21, 0.365, 6.4), ('Siero nutriente per il cuoio capelluto', 400, 64.0, 0.13, 0.44, 5.6)]


def amp_print(fdir):
    Xh = lambda h: (h - H0) * PX * SS                              # canvas: X along h
    Yt = lambda t: (t - TH0) / (TH1 - TH0) * AW * SS               # Y along θ (down = +θ)
    deg = PX * SS * R * np.pi / 180                                # canvas px per degree of θ
    W, H = AH * SS, AW * SS
    a = np.zeros((H, W), np.float32)
    # the lockup: the box logo's letters, scaled from the box (centres and widths in cap units)
    h0, h1, t0, t1 = AMP_LOCKUP
    cap = (t1 - t0) * deg
    first, last = LOGO[0], LOGO[-1]
    left0, right0 = first[2] - first[3] / 2, last[2] + last[3] / 2   # the box logo's ink ends (photo px)
    k = (Xh(h1) - Xh(h0)) / (right0 - left0)                       # canvas px per box photo px
    ky = cap / (BASE0 - CAP0)
    for ch, weight, cx, wd, col in LOGO:
        g, top, mid = logo_letter(ch, weight, wd * k, cap)
        paste(a, g, Xh(h0) + (cx - left0) * k - mid, Yt(t0) + top)
    for ch, cx, wd, col in HAIR:
        g, top, mid = logo_letter(ch, HAIR_W, wd * k, (BASE1 - CAP1) * ky, False)
        paste(a, g, Xh(h0) + (cx - left0) * k - mid, Yt(t0) + (CAP1 - CAP0) * ky + top)
    rub = os.path.join(fdir, 'Rubik[wght].ttf')
    for text, weight, t, ha, hb, capd in AMP_SMALL:   # at the measured cap height, letter-spaced to the measured length
        size = 200; im, b = run([(text, rub, weight, 1)], size); ix0, _, ix1, _ = ink(im)
        sc = capd * deg / (cap_of(rub, weight) * size)
        im, b = run([(text, rub, weight, 1)], size, ((Xh(hb) - Xh(ha)) / sc - (ix1 - ix0)) / (len(text) - 1))
        ix0, _, ix1, _ = ink(im)
        g = np.asarray(im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)).astype(np.float32) / 255
        paste(a, g, Xh(ha) - ix0 * sc, Yt(t) + capd * deg / 2 - b * sc)   # the line's middle on θ: baseline half a cap below
    img = Image.fromarray((a * 255).astype(np.uint8))
    return img.resize((AH, AW), Image.LANCZOS).transpose(Image.Transpose.ROTATE_90)


if __name__ == '__main__':
    fdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
    JOST, DEJAVU = os.path.join(fdir, 'Jost[wght].ttf'), os.path.join(fdir, 'DejaVuSans-Bold.ttf')
    face, metal = box_face(fdir)
    face.save(f'{out}/box-face.png', optimize=True); metal.save(f'{out}/box-metal.png', optimize=True)
    amp_print(fdir).save(f'{out}/amp-print.png', optimize=True)
    # S5's two devices: their packshots as they are (same pixels), lossy (q 86, alpha 92): seen only dimmed on S5
    shots = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../protocols/print/img'))
    for n in ('mitoscan', 'mitopen'):
        Image.open(f'{shots}/{n}.webp').save(f'{out}/{n}.webp', quality=86, alpha_quality=92, method=6)
    for n in ('box-face.png', 'box-metal.png', 'amp-print.png', 'mitoscan.webp', 'mitopen.webp'):
        im = Image.open(f'{out}/{n}'); print(n, im.size, im.mode, os.path.getsize(f'{out}/{n}') // 1024, 'KB')
