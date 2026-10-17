"""Print maps for the opened V-TECH box (owner's photo 17/10, images/43): the gold sleeve's V and triangle are a die-cut
window onto the black box, and the black box's lid carries the print in grey ink on matte black with a spot-gloss V.
Writes, next to the carton maps it reads (box-front-metal.png, prep_tex.py):
  sleeve-window.png  L, 255 = cut out (the carton front's ink inside the V band), the carton front's UV
  lid-albedo.png, lid-rough.png, lid-metal.png  the lid front, the same UV as the carton front (u across, v up)
The lid repeats the carton's «VM» and «V-TECH SYSTEM» (grey; the triangle over V-TECH's V gold), a gloss V a little wider
than the window it shows through, and the small print read from the photo (Latin, not translated).
usage: python3 prep_kit.py <tex dir> <Rubik[wght].ttf> <font with ℮, e.g. DejaVuSans.ttf>"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

TEX, RUBIK, SYM = sys.argv[1:4]
ink = np.asarray(Image.open(f'{TEX}/box-front-metal.png').convert('L')) < 128
H, W = ink.shape
band = lambda a, b: (round(a * H), round(b * H))   # rows from the top of the carton front (prep_tex.py layout)
V0, V1 = band(0.198, 0.512)   # the V and the triangle over it
win = np.zeros_like(ink); win[V0:V1] = ink[V0:V1]
w2 = Image.fromarray((win * 255).astype(np.uint8)).resize((W // 2, H // 2), Image.LANCZOS)
w2.point(lambda v: 255 if v > 127 else 0).save(f'{TEX}/sleeve-window.png', optimize=True)

# the lid: matte black, grey ink, the gloss V, a gold triangle
LW, LH = 1200, round(1200 * H / W)
alb = np.zeros((LH, LW, 3)) + 0.018; rough = np.zeros((LH, LW)) + 0.62; metal = np.zeros((LH, LW))   # charcoal, as on the photo
s = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((LW, LH), Image.LANCZOS)).astype(float) / 255


def moved(mask, a, b, dv):   # the carton ink of rows a..b (fractions), moved up by dv of the height
    out = np.zeros_like(mask); r0, r1 = band(a, b); d = round(dv * H); out[r0 - d:r1 - d] = mask[r0:r1]; return out


vm, vt = s(moved(ink, 0.096, 0.148, 0.027)), s(moved(ink, 0.671, 0.739, 0.017))
cols = slice(round(0.17 * W), round(0.24 * W)); r0, r1 = band(0.671, 0.716)   # the triangle over V-TECH's V: the run above
rows = ink[r0:r1, cols].any(1); tri_end = r0 + int(np.argmin(rows[np.argmax(rows):]) + np.argmax(rows))   # the first gap
tri = np.zeros_like(ink); tri[r0:tri_end, cols] = ink[r0:tri_end, cols]; tri = s(moved(tri, 0.66, 0.72, 0.017))
gloss = np.asarray(Image.fromarray((win * 255).astype(np.uint8)).resize((LW, LH), Image.LANCZOS)
                   .filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(2))).astype(float) / 255
GREY, GOLD = np.array([0.42, 0.42, 0.43]), np.array([0.87, 0.66, 0.25])
grey = np.clip(vm + vt - tri, 0, 1)
alb = alb * (1 - grey[..., None]) + GREY * grey[..., None]; rough = rough * (1 - grey) + 0.42 * grey
alb = alb * (1 - tri[..., None]) + GOLD * tri[..., None]; metal = np.maximum(metal, tri); rough = rough * (1 - tri) + 0.25 * tri
rough = rough * (1 - gloss) + 0.1 * gloss   # spot-UV varnish: the same black, a mirror finish

# the small print (photo: the lid's lower third), centred, white then grey; positions as fractions from the top
txt = Image.new('L', (LW, LH), 0); d = ImageDraw.Draw(txt)
def font(path, px, wght=None):
    f = ImageFont.truetype(path, px)
    if wght: f.set_variation_by_axes([wght])
    return f
def line(s_, y, px, wght, fill, path=RUBIK):
    f = font(path, px, wght); w = d.textlength(s_, font=f); d.text(((LW - w) / 2, y * LH), s_, font=f, fill=fill, anchor='lm')
line('Professional antiaging cosmetic kit for the face and body', 0.770, 29, 600, 235)
for i, s_ in enumerate(['Kit cosmetico professionale antietà per viso e corpo', 'Kit cosmétique anti-âge professionnel pour le visage et le corps',
                        'Kit de cosmética profesional antiedad para rostro y cuerpo']):
    line(s_, 0.785 + 0.0118 * i, 25, 400, 160)
for i, (lab, rest) in enumerate([('V-TECH SERUM: ', '5 x 5ml ℮ 5 x 0.17 fl. oz.'), ('V-TECH GEL MASK: ', '5 x 5 ml ℮ 5 x 0.17 fl. oz.')]):
    fb, fr = font(RUBIK, 24, 600), font(RUBIK, 24, 400)
    wb, wr = d.textlength(lab, font=fb), d.textlength(rest.replace('℮', 'e'), font=fr)
    x = (LW - wb - wr) / 2; y = (0.879 + 0.0125 * i) * LH
    d.text((x, y), lab, font=fb, fill=225, anchor='lm'); x += wb
    parts = rest.split('℮')
    for j, part in enumerate(parts):   # ℮ from a font that has it
        d.text((x, y), part, font=fr, fill=175, anchor='lm'); x += d.textlength(part, font=fr)
        if j < len(parts) - 1:
            fs = font(SYM, 24); d.text((x, y), '℮', font=fs, fill=175, anchor='lm'); x += d.textlength('℮', font=fs)
t = np.asarray(txt).astype(float) / 255
alb = alb * (1 - t[..., None]) + 0.8 * t[..., None]; rough = rough * (1 - t) + 0.45 * t

Image.fromarray((np.clip(alb, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)).save(f'{TEX}/lid-albedo.png', optimize=True)
for name, a in (('lid-rough', rough), ('lid-metal', metal)):
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(f'{TEX}/{name}.png', optimize=True)
print('sleeve-window.png', w2.size, 'lid maps', (LW, LH))
