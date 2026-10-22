"""Textures for the three.js EXOSIGNAL SPRAY scene (site/proto/scenes/exosignal-spray.js), sharp at any size: the print is
typeset, not cut from a picture. There is no studio packshot of the spray: places and sizes of the box's print are
measured on the only one, site/img/exosignal-spray.png (400×300, a render or an old mock-up: its bottle is opaque white
and carries an old label), in edge coordinates (a pixel i spans [i, i+1)), ink boxes at half their contrast:
  box   the front, photo y 1.5…298.6 (297.1 px), 118.2 px wide on average (117.1 at the top … 119.3 at the foot: the
        mock-up's slight perspective); x is read from the front's own middle on that row (CENTRE)
  bottle the real label, as the owner's photos show it (Figma 93:8081, photo #2: only a 59×83 thumbnail reaches the
        cloud) and as packaging-text.json lists it: placed in s (fraction of the body's height from the cap's edge
        down) × θ (degrees round the body, 0 facing the viewer, + to the right); temporary until the full photo
The box's logo is the EXOSIGNAL HAIR box's logo (design/exosignal-hair/make_textures.py, imported, not copied): its
letters' ink centres along the column, measured on the mock-up (±0.005 of its length), are the HAIR logo's own, and
its length is 10.31 of its cap height on both boxes; so it is that lockup scaled (0.3227) and turned a quarter
clockwise (read from the top down, the letters' tops to the right), as are «S P R A Y · H O M E» (Jost 420, each letter
on its measured centre, cap 0.43 of the logo's; «·» at mid-cap, as measured) beside it, left of the logo's baseline.
The VM monogram is the HAIR box's three polygons, scaled to the mock-up's (V 19.0 px tall, the legs 21.7 px across).
The lower block: «EXOSIGNAL SPRAY HOME» (Rubik 500, letter-spaced to its measured ink box); the four tiny lines, the
line under the monogram, the small boxed label and the line under it are unreadable (packaging-text: «[unreadable]»):
left out, as nothing is drawn that is not read there (no stand-in bars or plate). The lower block sits 2 px left of
the front's middle on the mock-up (the top block within 0.5 px of it): set as measured.
Colours: the paper #131417 and the seam #0d0e12 as the mock-up's palette has them; one foil for EXO, SIGNAL and
«S P R A Y · H O M E», the mock-up's own: its solid EXO pixels are two palette entries, #c6a62e (48 px) and #b59931
(70 px), set as the brighter one because the scene's foil renders about 5 % darker than its texture (SIGNAL and the
spaced line are hairlines there, mixed with the paper, but print the same foil); the light ink (VM, the lower block)
neutral #919496, as owner photo #34 shows the monogram (the mock-up's hairline VM reads darker, #727684,
from its small size). Both unverified until the owner's full-size photo: a question to the owner.
Writes into <out dir>:
  box-face.png     the front's colours, RGB 1024×2572 (2.1 texels per px where the front is largest, 760 frame px tall,
                   in a 3840 key): the paper with its light top edge and the dark seam band at 0.78 of the height, the
                   foil, the light ink
  box-metal.png    the front's material, RGB 512×1286: G roughness (paper 1 × 0.65, foil 0.43 × 0.65 = 0.28), B metalness
  bottle-print.png alpha of the bottle's black print, L 674×2158: θ −60…+60 × s 0.08…0.90 (4000 px per bottle height:
                   3.3 texels per px for the S3 close-up in a 3840 key)
  hair.webp        the EXOSIGNAL HAIR packshot (protocols/print/img, 1087×714) for S2 and S5: the same pixels, lossy
                   (q 86, alpha 92): the scene draws it at most 680 frame px wide
usage: python3 -I make_textures.py <font dir with Jost[wght].ttf, Rubik[wght].ttf> <out dir>"""
import importlib.util, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.dont_write_bytecode = True   # importing the HAIR script must leave no __pycache__ in the repository
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('hair_textures', os.path.join(HERE, '..', 'exosignal-hair', 'make_textures.py'))
HR = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(HR)

SS = 2                                                   # drawn at 2× and reduced: smooth edges
TOP, BOT, FW = 1.5, 298.6, 118.2                         # the front on the mock-up: top, foot, mean width
FH = BOT - TOP
TW, TH = 1024, round(1024 * FH / FW)                     # box-face.png, square texels
CENTRE = [(5, 171.71), (80, 171.36), (200, 171.0), (240, 170.68), (298, 170.5)]   # the front's middle (x) per row (y)
PAPER, RIM, SEAM, INK = (0x13, 0x14, 0x17), (0x20, 0x21, 0x25), (0x0d, 0x0e, 0x12), (0x91, 0x94, 0x96)
RIM_Y, SEAM_Y = 3.0, (231.6, 235.0)                      # the light top edge (row 2), the seam's dark band (rows 232–234)
FOIL = '#c6a62e'                                         # one foil, the mock-up's (see the notes above)
# the logo along its column: E's foot … L's end (y), its cap's middle (x); the HAIR logo's ink ends (photo px of that box)
LOGO_R0, LOGO_R1, LOGO_X = 72.82, 198.63, 170.99
HAIR_L0 = HR.LOGO[0][2] - HR.LOGO[0][3] / 2
HAIR_L1 = HR.LOGO[-1][2] + HR.LOGO[-1][3] / 2
KS = (LOGO_R1 - LOGO_R0) / (HAIR_L1 - HAIR_L0)           # mock-up px per HAIR photo px (0.3227)
CAP = (HR.BASE0 - HR.CAP0) * KS                          # the bold letters' cap height (12.2 px)
# «S P R A Y · H O M E»: each letter's ink centre along the column (y), the cap line (x), the cap height, Jost 420
SPRAY = [('S', 74.64), ('P', 89.10), ('R', 103.29), ('A', 118.00), ('Y', 132.78), ('·', 143.89), ('H', 154.27),
         ('O', 168.42), ('M', 183.24), ('E', 197.08)]
SPRAY_CAPX, SPRAY_CAP, SPRAY_W = 160.75, 0.4303 * CAP, 420
# the VM monogram: the HAIR polygons scaled (x, y) about its axis and its top
VM_AXIS, VM_TOP, VM_K = 171.94, 20.16, (0.366, 0.3506)
TITLE = ('EXOSIGNAL SPRAY HOME', 500, 142.3, 194.5, 246.2, 249.5, 0.03)   # text, weight, ink x0, x1, cap line, baseline, thinning


def lerp_table(t, y):
    ys, vs = zip(*t); return float(np.interp(y, ys, vs))


def column(letters, T):
    """letters set along a column read downward with their tops to the right (a line turned a quarter clockwise):
    letters (alpha, ink top below its cap line, ink middle along the line, place along the column, cap line's distance
    left of the reference x, colour index) in canvas px (T per photo px) → the turned alpha, its colour index and the
    patch's place: its top (photo y) and its left edge's distance left of the reference x"""
    r0 = min(r - a.shape[1] / T for a, top, mid, r, d, ci in letters) - 2
    r1 = max(r + a.shape[1] / T for a, top, mid, r, d, ci in letters) + 2
    d0 = min(d + top / T for a, top, mid, r, d, ci in letters) - 2
    d1 = max(d + (top + a.shape[0]) / T for a, top, mid, r, d, ci in letters) + 2
    W, H = int(np.ceil((r1 - r0) * T)), int(np.ceil((d1 - d0) * T))
    al = np.zeros((H, W), np.float32); idx = np.zeros((H, W), np.int8)
    for a, top, mid, r, d, ci in letters:
        x, y = (r - r0) * T - mid, (d - d0) * T + top
        HR.paste(al, a, x, y)
        h, w = a.shape; X0, Y0 = int(x), int(y)
        idx[Y0:Y0 + h + 2, X0:X0 + w + 2][np.pad(a, ((0, 2), (0, 2))) > 0.002] = ci
    idx = np.rot90(idx, -1); grown = np.zeros_like(idx)   # turned; each colour grown 2 px (the alpha's sub-pixel shift)
    for ci in np.unique(idx[idx > 0]): grown[HR.ndimage.binary_dilation(idx == ci, iterations=2)] = ci
    return np.rot90(al, -1).copy(), grown, r0, d0 + H / T   # rows along the column; the left edge's distance


def logo_letters(T, kscale, capd):
    """the EXOSIGNAL lockup (the HAIR letters, cuts and all) at `kscale` canvas px per HAIR photo px, as column letters
    whose cap line is `capd` left of the reference x; and «EXO» / «SIGNAL» colour indices 1 / 2"""
    out = []
    for ch, weight, cx, wd, col in HR.LOGO:
        cap, base = (HR.CAP0, HR.BASE0) if weight > 500 else HR.THIN
        a, top, mid = HR.logo_letter(ch, weight, wd * kscale, (base - cap) * kscale)
        r = (cx - HAIR_L0) * kscale / T                    # along the column, from the logo's start (canvas → photo px)
        out.append((a, top + (cap - HR.CAP0) * kscale, mid, r, capd, 1 if weight > 500 else 2))
    return out


def spray_letters(T, cap, capd, places):
    """«S P R A Y · H O M E» (Jost 420) at cap height `cap` (canvas px), each letter's ink middle at its place; the
    dot's ink centred at mid-cap, as measured"""
    out = []
    for (ch, r) in places:
        a, top, mid = HR.logo_letter(ch, SPRAY_W, 0, cap, cuts=False)
        if ch == '·': top = cap / 2 - a.shape[0] / 2
        out.append((a, top, mid, r, capd, 2))
    return out


def place_text(canvas, parts, x0, x1, base, size=200, cap=None, value=1.0):
    """a line of text runs (HAIR's `run` parts) fitted to the ink width x0…x1 with its baseline at `base` (canvas px):
    uniformly scaled to the width, or, with `cap` (canvas px), at that cap height and letter-spaced to the width"""
    im, b = HR.run(parts, size); ix0, _, ix1, _ = HR.ink(im)
    if cap:
        k = cap / (HR.cap_of(parts[0][1], parts[0][2]) * size); n = sum(len(t) for t, *_ in parts)
        im, b = HR.run(parts, size, ((x1 - x0) / k - (ix1 - ix0)) / (n - 1)); ix0, _, ix1, _ = HR.ink(im)
    k = (x1 - x0) / (ix1 - ix0)
    a = np.asarray(im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)).astype(np.float32) / 255
    HR.paste(canvas, a, x0 - ix0 * k, base - b * k, value)


def vm(canvas, X, Y, axis, top, kx, ky, value=1.0):
    """the VM monogram (the HAIR box's polygons, HR.VM_*) with its axis at `axis` and its top at `top` (canvas px of
    the target, X / Y map the HAIR photo px offsets × (kx, ky)), drawn at 4× in its own region and reduced"""
    (ho, so), (hi, si) = HR.VM_V; t = HR.VM_TOP
    out0, ytop, in0, ycut, yfoot, lean = HR.VM_LEG
    dout = lambda y: out0 + lean * (y - ytop); din = lambda y: in0 + lean * (y - ycut)
    apex_o, apex_i = t + ho / so, t + hi / si
    S4 = 4; half = dout(yfoot) * kx * X + 4; ox, oy = axis - half, top - 4
    reg = Image.new('L', (int(2 * half) * S4, int((apex_o - t) * ky * Y + 8) * S4)); d = ImageDraw.Draw(reg)
    P = lambda dx, y: ((axis + dx * kx * X - ox) * S4, (top + (y - t) * ky * Y - oy) * S4)
    d.polygon([P(-ho, t), P(-hi, t), P(0, apex_i), P(hi, t), P(ho, t), P(0, apex_o)], fill=255)
    for s in (-1, 1):
        d.polygon([P(s * dout(ytop), ytop), P(s * din(ycut), ycut), P(s * din(yfoot), yfoot), P(s * dout(yfoot), yfoot)], fill=255)
    reg = reg.resize((reg.width // S4, reg.height // S4), Image.BOX)
    HR.paste(canvas, np.asarray(reg).astype(np.float32) / 255, ox, oy, value)


def box_face():
    T = TW * SS / FW                                             # canvas px per photo px
    X = lambda x, y: (0.5 + (x - lerp_table(CENTRE, y)) / FW) * TW * SS
    Y = lambda y: (y - TOP) / FH * TH * SS
    W, H = TW * SS, TH * SS
    ink_a = np.zeros((H, W), np.float32); foil_a = np.zeros((H, W), np.float32); foil_c = np.zeros((H, W, 3), np.float32)
    # the logo and «S P R A Y · H O M E» on one column, turned; the reference x: the logo's cap line
    ymid = (LOGO_R0 + LOGO_R1) / 2; capx = LOGO_X + CAP / 2
    letters = logo_letters(T, KS * T, 0.0)
    letters = [(a, top, mid, LOGO_R0 + r, d, ci) for a, top, mid, r, d, ci in letters]
    letters += spray_letters(T, SPRAY_CAP * T, capx - SPRAY_CAPX, SPRAY)
    al, idx, r0, d1 = column(letters, T)
    x, y = X(capx - d1, ymid), Y(r0)
    HR.paste(foil_a, al, x, y)
    h, w = al.shape; X0, Y0 = int(x), int(y)
    foil_c[Y0:Y0 + h, X0:X0 + w][idx > 0] = [int(FOIL[i:i + 2], 16) for i in (1, 3, 5)]
    # the monogram
    vm(ink_a, T, T, X(VM_AXIS, 30), Y(VM_TOP), *VM_K)
    # the lower block: the title
    text, weight, x0, x1, top, base, thin = TITLE
    a, ox, oy = HR.fit_line([(text, RUBIK, weight, 1)], (X(x0, base), X(x1, base), Y(top), Y(base)), spaced=True, thin=thin)
    HR.paste(ink_a, a, ox, oy)
    # the paper: its light top edge, the seam's dark band
    yy = TOP + (np.arange(H, dtype=np.float32) + 0.5) / H * FH
    paper = np.array(PAPER, np.float32)[None, :] * np.ones((H, 1), np.float32)
    rim = np.clip((RIM_Y - yy) / 0.6, 0, 1)[:, None]
    paper = paper + (np.array(RIM, np.float32) - PAPER)[None, :] * rim
    seam = (np.clip((yy - SEAM_Y[0]) / 0.5, 0, 1) * np.clip((SEAM_Y[1] - yy) / 0.5, 0, 1))[:, None]
    paper = paper + (np.array(SEAM, np.float32) - paper) * seam
    rgb = paper[:, None, :] * np.ones((1, W, 1), np.float32)
    rgb = rgb + (np.array(INK, np.float32) - rgb) * ink_a[..., None]
    rgb = rgb + (foil_c - rgb) * foil_a[..., None]
    face = Image.fromarray(np.clip(rgb + 0.5, 0, 255).astype(np.uint8)).resize((TW, TH), Image.LANCZOS)
    m = np.asarray(Image.fromarray((foil_a * 255).astype(np.uint8)).resize((TW // 2, TH // 2), Image.BOX)).astype(np.float32) / 255
    mat = np.stack([np.zeros_like(m), 255 * (1 - m * (1 - 0.28 / 0.65)), 255 * m], -1)
    return face, Image.fromarray(np.clip(mat + 0.5, 0, 255).astype(np.uint8))


# ---- the bottle's label: θ (−60…+60°) × s (0.08…0.90 of the body from the cap's edge down), in bottle heights (u):
# the body's radius 0.0804 and height 0.658 (the mock-up's silhouette: 243.5 px tall, 39.15 wide, the cap 0.342 of it)
BT0, BT1, BS0, BS1 = -60.0, 60.0, 0.08, 0.90
RB, BODY, PXB = 0.0804, 0.658, 4000
BW, BH = round(np.radians(BT1 - BT0) * RB * PXB), round((BS1 - BS0) * BODY * PXB)
# measured on the photo's thumbnail (s ± 0.02): the monogram s 0.130 (its V 0.055 of the body tall), the line under it;
# the logo s 0.255…0.600, its cap's middle at θ +6°, «S P R A Y · H O M E» beside it as on the box; «EXOSIGNAL SPRAY
# HOME» across ±42° at s 0.695, «Deep nourishing scalp serum» (Rubik 300) ±33° at 0.728; «HOME USE» (Rubik 700) ±24°
# at 0.866. The line under the monogram and the three under «Deep nourishing…» are unreadable: left out (no stand-in bars)
B_VM, B_LOGO, B_LOGO_T = (0.130, 0.055), (0.255, 0.600), 6.0
B_TITLE, B_DEEP, B_HOME = (0.695, 42.0), (0.728, 33.0), (0.866, 24.0)


def bottle_print():
    T = PXB * SS                                          # canvas px per bottle height (u)
    Xt = lambda deg: (np.radians(deg - BT0) * RB) * T       # θ → canvas x (arc length)
    Ys = lambda s: (s - BS0) * BODY * T                     # s → canvas y
    W, H = BW * SS, BH * SS
    a = np.zeros((H, W), np.float32)
    # the logo and «S P R A Y · H O M E», as on the box, scaled to the logo's measured length; the reference: its cap
    # line (θ), the column measured in s; positions in «photo px» of the box mapped onto u
    L = (B_LOGO[1] - B_LOGO[0]) * BODY                      # the logo's length (u)
    k = L / (LOGO_R1 - LOGO_R0)                             # u per box photo px
    Tb = k * T                                              # canvas px per box photo px
    capx_deg = B_LOGO_T + np.degrees(CAP * k / 2 / RB)      # the cap line (θ)
    letters = logo_letters(Tb, KS * Tb, 0.0)
    places = [(ch, r - LOGO_R0) for ch, r in SPRAY]
    capd = (LOGO_X + CAP / 2) - SPRAY_CAPX                  # the box's gap, in box px
    letters += spray_letters(Tb, SPRAY_CAP * Tb, capd, places)
    al, idx, r0, d1 = column(letters, Tb)
    HR.paste(a, al, Xt(capx_deg) - d1 * Tb, Ys(B_LOGO[0]) + r0 * Tb)
    # the monogram (the box's proportions)
    vh = B_VM[1] * BODY * T                                 # its V's height, canvas px
    ky = vh / (HR.VM_TOP + HR.VM_V[0][0] / HR.VM_V[0][1] - HR.VM_TOP); kx = ky * VM_K[0] / VM_K[1]
    vm(a, 1, 1, Xt(0), Ys(B_VM[0]), kx, ky)
    # the horizontal block: the title at the box title's proportions (its ink 16.0 caps long), the rest by width
    rub = RUBIK
    s, half = B_TITLE; w = np.radians(2 * half) * RB * T; cap = w / 16.0
    place_text(a, [('EXOSIGNAL SPRAY HOME', rub, 500, 1)], Xt(-half), Xt(half), Ys(s) + cap / 2, cap=cap)
    s, half = B_DEEP; im, b = HR.run([('Deep nourishing scalp serum', rub, 300, 1)], 200); ix0, _, ix1, _ = HR.ink(im)
    capd = np.radians(2 * half) * RB * T / (ix1 - ix0) * HR.cap_of(rub, 300) * 200
    place_text(a, [('Deep nourishing scalp serum', rub, 300, 1)], Xt(-half), Xt(half), Ys(s) + capd / 2)
    s, half = B_HOME; im, b = HR.run([('HOME USE', rub, 700, 1)], 200); ix0, _, ix1, _ = HR.ink(im)
    caph = np.radians(2 * half) * RB * T / (ix1 - ix0) * HR.cap_of(rub, 700) * 200
    place_text(a, [('HOME USE', rub, 700, 1)], Xt(-half), Xt(half), Ys(s) + caph / 2)
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((BW, BH), Image.LANCZOS)


if __name__ == '__main__':
    fdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
    HR.JOST = os.path.join(fdir, 'Jost[wght].ttf'); RUBIK = os.path.join(fdir, 'Rubik[wght].ttf')
    face, metal = box_face()
    face.save(f'{out}/box-face.png', optimize=True); metal.save(f'{out}/box-metal.png', optimize=True)
    bottle_print().save(f'{out}/bottle-print.png', optimize=True)
    shots = os.path.normpath(os.path.join(HERE, '../../../protocols/print/img'))
    Image.open(f'{shots}/exosignal-hair.webp').save(f'{out}/hair.webp', quality=86, alpha_quality=92, method=6)
    for n in ('box-face.png', 'box-metal.png', 'bottle-print.png', 'hair.webp'):
        im = Image.open(f'{out}/{n}'); print(n, im.size, im.mode, os.path.getsize(f'{out}/{n}') // 1024, 'KB')
