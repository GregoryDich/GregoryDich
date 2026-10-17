"""The V-TECH SERUM ampoule label as on the real vials (owner's photos, About page, 17/10): a transparent film with
white print — the V mark on the left, «V-TECH» over a spaced «SERUM», four lines of the product name in four
languages and the Arabic line under them. Writes label.png: white, alpha = ink (the scene lays it on a clear film).
The map wraps the vial body: u = 0 at the back, the print block faces +z at u = 0.5; v spans the label, y 0.05..0.43
of the vial (vtech_scene.py LABEL_Y).
usage: python3 prep_label.py <out dir> <Jost[wght].ttf> <Heebo[wght].ttf> <font with Arabic glyphs, e.g. DejaVuSans-Bold.ttf>"""
import sys
from PIL import Image, ImageDraw, ImageFont

OUT, JOST, HEEBO, ARABIC = sys.argv[1:5]
Y0, Y1, R = 0.05, 0.43, 0.1615                 # label band on the vial and the sleeve radius (scene units)
W, SS = 4096, 2                                # map width = the whole circumference; supersampled ×2
PX = W / (2 * 3.141592653589793 * R)           # map pixels per scene unit
H = round((Y1 - Y0) * PX)
im = Image.new('L', (W * SS, H * SS), 0); d = ImageDraw.Draw(im); px = PX * SS
Y = lambda y: (Y1 - y) * px                    # scene height on the vial → map row
cx = W * SS / 2


def font(path, cap, wght=None, **kw):          # size from the cap height (Jost/Heebo caps ≈ 0.7 em)
    f = ImageFont.truetype(path, max(1, round(cap * px / 0.7)), **kw)
    if wght: f.set_variation_by_axes([wght])
    return f


def run(s, f, track):                          # a tracked line on its own layer: (layer, width)
    ws = [d.textlength(c, font=f) for c in s]; tw = sum(ws) + track * f.size * (len(s) - 1)
    lay = Image.new('L', (round(tw) + 8, round(f.size * 1.4)), 0); ld = ImageDraw.Draw(lay); x = 4
    for c, cw in zip(s, ws): ld.text((x, f.size * 1.05), c, font=f, fill=255, anchor='ls'); x += cw + track * f.size
    return lay, tw


def put(lay, x, base, f, shear=0.0, sx=1.0):   # paste a line with its left edge at x and baseline at row `base`
    if sx != 1: lay = lay.resize((max(1, round(lay.width * sx)), lay.height), Image.LANCZOS)
    if shear: lay = lay.transform(lay.size, Image.AFFINE, (1, shear, -shear * f.size * 1.05, 0, 1, 0), Image.BICUBIC)
    im.paste(255, (round(x - 4 * sx), round(base - f.size * 1.05)), lay)


# the block: the V mark, then «V-TECH» / «SERUM» to its right; centred on the front of the vial
vw, vh, gap, tw_ = 0.064 * px, 0.084 * px, 0.022 * px, 0.150 * px
left = cx - (vw + gap + tw_) / 2; top = Y(0.392) + 0.2 * vh
P = lambda x, y: (left + x * vw, top + y * vh)
d.polygon([P(0, 0), P(0.24, 0), P(0.5, 0.66), P(0.86, 0), P(1, 0), P(0.5, 1)], fill=255)   # heavy left arm, slim right arm
d.polygon([P(0.30, -0.24), P(0.66, -0.24), P(0.48, 0.10)], fill=255)                      # the solid triangle over the V
tx = left + vw + gap
f1 = font(JOST, 0.029, 520); l1, w1 = run('V-TECH', f1, 0.06); put(l1, tx, Y(0.335), f1, sx=tw_ / w1)
f2 = font(JOST, 0.0172, 430); l2, w2 = run('SERUM', f2, 0.62); put(l2, tx + 0.006 * px, Y(0.302), f2, shear=0.16, sx=(tw_ - 0.006 * px) / w2)
# four lines of the name, bold and narrow, as wide as the front; then the Arabic line, right-aligned under them
LINES = ['Skin moisturizing cosmetic serum', 'Siero cosmetico idratante per la pelle',
         'Sérum cosmétique hydratant pour la peau', 'Sérum cosmético hidratante para la piel']
f3 = font(HEEBO, 0.0118, 700); runs = [run(s, f3, 0.0) for s in LINES]
k = 0.292 * px / max(w for _, w in runs)       # the longest line spans 0.29 units, as on the photo
for i, (lay, w) in enumerate(runs):
    put(lay, cx - w * k / 2, Y(0.258 - i * 0.0225), f3, sx=k)
fa = font(ARABIC, 0.0105, layout_engine=ImageFont.Layout.RAQM)
s = 'مصل لترطيب البشرة'; wa = d.textlength(s, font=fa, direction='rtl', language='ar')
d.text((cx + 0.12 * px - wa, Y(0.163)), s, font=fa, fill=255, anchor='ls', direction='rtl', language='ar')
a = im.resize((W, H), Image.LANCZOS)
a.paste(48, (0, 0, W, 3)); a.paste(48, (0, H - 3, W, H))   # the film's cut edges catch a little light, as on the photos
Image.merge('RGBA', [Image.new('L', (W, H), 240)] * 3 + [a]).save(f'{OUT}/label.png', optimize=True)
print('label.png', W, H)
