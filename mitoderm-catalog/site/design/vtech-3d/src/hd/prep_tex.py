"""PBR maps for the Cycles V-TECH scene from the flat print textures.
Upscale x3, re-crisp ink/foil edges (smoothstep on the masks) so print reads sharp at HD,
replace baked gold gradients with flat foil colour (reflections come from the lights).
Matched to the packshot (protocols/assets/img/vtech-system.webp): pale champagne foil, "VM" in black ink and
~1.35x larger than in the flat trace, vial print redrawn as on the real vials (white V over V-TECH / SERUM,
graduation ticks on the right).
usage: python3 prep_tex.py <src dir> <out dir> <Jost[wght].ttf>"""
import sys, numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
SRC, OUT, JOST = sys.argv[1:4]
def up(img, k): return img.resize((img.width * k, img.height * k), Image.LANCZOS)
def ss(x, a, b): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def smooth(a, k):  # blur then re-threshold: stair-stepped pixel edges become clean vector-like contours
    im = Image.fromarray((a * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(k))
    return ss(np.asarray(im).astype(float) / 255, 0.42, 0.58)
def save(a, name, mode='RGB'):
    Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8), mode).save(f'{OUT}/{name}')
GOLD = np.array([0.94, 0.80, 0.50]); INK = np.array([0.02, 0.018, 0.016])  # packshot foil: hue ~43°, saturation ~0.45
def enlarge(img, box, f):
    """Scale the artwork inside box (x0, y0, x1, y1) by f about its centre (the flat trace drew "VM" too small)."""
    x0, y0, x1, y1 = box; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    part = img.crop(box); big = part.resize((round(part.width * f), round(part.height * f)), Image.LANCZOS)
    img.paste(big, (round(cx - big.width / 2), round(cy - big.height / 2))); return img
def fine_print(m):
    """Sachet: the traced 4-line description had broken into blobs (and a stray mark sat on the left edge).
    Redraw it as clean small-print rows in the same place; the real wording is not legible in the packshot either."""
    d = ImageDraw.Draw(m); GOLD_MR, INK_MR = (0, 51, 255), (0, 51, 0)
    d.rectangle([0, 436, 40, 515], fill=GOLD_MR); d.rectangle([314, 450, 648, 512], fill=GOLD_MR)
    seed = 11
    for y, h, frac in ((459, 5, 0.9), (472, 3, 0.97), (483, 3, 0.95), (494, 3, 0.72)):
        x, end = 481 - 160 * frac, 481 + 160 * frac
        while x < end:
            seed = seed * 16807 % 2147483647; w = 6 + seed % 30
            d.rectangle([x, y, min(x + w, end), y + h - 1], fill=INK_MR); x += w + 4
    return m
def bolder(metal, rows, k, px=5):
    """Thicken hairline print (SYSTEM, GEL MASK) inside source rows (y0, y1): it anti-aliased to grey on the foil."""
    y0, y1 = rows[0] * k, rows[1] * k
    band = Image.fromarray((metal[y0:y1] * 255).astype(np.uint8), 'L').filter(ImageFilter.MinFilter(px))
    metal[y0:y1] = np.asarray(band).astype(float) / 255; return metal
def foil(name, k, src, mr=None, blur=0.9, gold_rough=0.06, vm=None, fix=None, thin=None):
    t, m = Image.open(f'{SRC}/{src}').convert('RGB'), Image.open(f'{SRC}/{mr}').convert('RGB') if mr else None
    if vm: t, m = enlarge(t, vm, 1.35), enlarge(m, vm, 1.35)
    if fix: m = fix(m)
    t = np.asarray(up(t, k)).astype(float) / 255
    if m:
        metal = smooth(ss(np.asarray(up(m, k)).astype(float)[..., 2] / 255, 0.35, 0.65), k * blur)
    else:  # side panel: gold except the black ends
        metal = smooth(ss(t.max(-1), 0.25, 0.45), k * blur)
    mx, mn = t.max(-1), t.min(-1); sat = (mx - mn) / np.maximum(mx, 1e-3)
    if vm: metal = metal * (1 - ss(0.32 - sat, 0.0, 0.12) * (mx > 0.5))  # the pale "VM" letters are black ink on the carton
    for rows in thin or (): metal = bolder(metal, rows, k)
    alb = metal[..., None] * GOLD + (1 - metal)[..., None] * INK
    rough = metal * gold_rough + (1 - metal) * 0.6
    save(alb, f'{name}-albedo.png'); save(np.repeat(metal[..., None], 3, -1), f'{name}-metal.png'); save(np.repeat(rough[..., None], 3, -1), f'{name}-rough.png')
foil('box-front', 3, 'vtech-box-front.png', 'vtech-box-front-mr.png', vm=(330, 200, 504, 297), thin=((1470, 1540),))
foil('box-side', 3, 'vtech-box-side.png')
foil('sachet', 3, 'vtech-sachet-front.png', 'vtech-sachet-front-mr.png', blur=0.45, gold_rough=0.12, fix=fine_print, thin=((396, 432),))  # glossy foil; GEL MASK thickened  # light smoothing keeps the fine print

def vial_label(W=4096, H=1376, SS=2):
    """White print wrapped on the glass: u = 0 at the back, the block faces +z at u = 0.5; v spans y 0.06..0.40 of the vial."""
    im = Image.new('L', (W * SS, H * SS), 0); d = ImageDraw.Draw(im); px = 4040 * SS   # pixels per scene unit
    Y = lambda y: (0.40 - y) * px; cx = W * SS / 2
    w, h, top = 0.072 * px, 0.074 * px, Y(0.37)  # the V mark as on the carton: slim open V, solid triangle raised above the arms
    P = lambda x, y: (cx + (x - 0.5) * w, top + y * h)
    d.polygon([P(0, 0), P(0.2, 0), P(0.5, 0.66), P(0.8, 0), P(1, 0), P(0.5, 1)], fill=255)
    d.polygon([P(0.33, -0.2), P(0.67, -0.2), P(0.5, 0.2)], fill=255)
    def text(s, y, cap, wght, track):
        f = ImageFont.truetype(JOST, round(cap * px / 0.7)); f.set_variation_by_axes([wght])
        ws = [d.textlength(c, font=f) for c in s]; tw = sum(ws) + track * f.size * (len(s) - 1); x = cx - tw / 2
        for c, cw in zip(s, ws): d.text((x, Y(y)), c, font=f, fill=255, anchor='ls'); x += cw + track * f.size
    text('V-TECH', 0.256, 0.027, 520, 0.10)
    text('SERUM', 0.228, 0.0115, 420, 0.55)
    tx = cx + 0.11 * 4096 * SS   # graduation ticks ~40° to the right, where the camera still sees them
    for i in range(9):
        y = Y(0.11 + i * 0.028); L = (0.02 if i % 2 == 0 else 0.012) * px
        d.rectangle([tx, y - 0.0012 * px, tx + L, y + 0.0012 * px], fill=255)
    a = im.resize((W, H), Image.LANCZOS)
    Image.merge('RGBA', [Image.new('L', (W, H), 235)] * 3 + [a]).save(f'{OUT}/label.png')
vial_label()
print('ok')
