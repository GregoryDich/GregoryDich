"""Textures for the three.js EXOTECH GEL scene (site/proto/scenes/exotech-gel.js), sharp at any size: the print is
typeset, not cut from the photo (the only packshot, protocols/print/img/exotech-gel.webp, is 1065 px wide, its jar
lettering ~25 px tall and half of «EXO» lost in a highlight). Glyph places and sizes are measured on the packshot:
  jar  the photo's sphere fitted (silhouette: centre (870, 299.5), radius 197; the seam line: seen from 17.8° above,
       the seam at latitude 6.4°, 0.5 px rms), the letters unwrapped onto longitude × latitude;
  box  the front face rectified (a homography of its four corners), the letters in fractions of the face.
Typeface: Jost (SIL OFL, a Futura revival, github.com/google/fonts ofl/jost), narrowed to the print's proportions:
«EXO» 700, «TECH» 300, «G E L» italic 500, as on the packaging (and the owner's photos of 19/10). Exact artwork
(the packaging's vector file) would replace these measurements one for one.
Writes into <out dir>:
  jar-print.png   alpha of the lid's lettering, longitude LON × latitude LAT (row 0 at the top), 2048 px wide;
  box-print.png   alpha of the front face's lettering, the face's width × the band BAND of its height;
  foil.jpg        the box foil's relief (bump and roughness): soft, mostly horizontal ripples, tiling.
usage: python3 -I make_textures.py <font dir with Jost[wght].ttf and Jost-Italic[wght].ttf> <out dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

LON, LAT = (-42, 42), (7.0, 27.0)     # the jar decal, degrees; longitude 0 faces the camera, the seam is at 6.4°
BAND = (0.40, 0.60)                   # the box decal: this band of the front face's height (top 0)
# lines: (glyphs, weight, italic, narrowing, baseline, cap height, glyph centres). Jar: degrees of latitude/longitude;
# box: fractions of the face's height/width (centred on the measured line's middle)
JAR = [('EXO', 700, 0, .86, 17.15, 7.4, (-32.05, -20.9, -9.9)), ('TECH', 300, 0, .88, 17.15, 7.4, (-0.65, 8.45, 18.95, 31.5)),
       ('GEL', 500, 1, .82, 8.9, 5.0, (-8.55, 1.05, 9.35))]
BOX = [('EXO', 700, 0, .86, .4955, .0555, (.3067, .3740, .4458)), ('TECH', 300, 0, .88, .4955, .0555, (.5078, .5694, .6387, .7163)),
       ('GEL', 500, 1, .82, .5605, .0430, (.4448, .5210, .5874))]
BOX_MID, ASPECT = .5127, 1 / 1.13     # the measured lines' middle (the print is centred on the face); face width/height


def glyph(fonts, ch, weight, italic):   # one glyph's alpha cropped to its ink, its top relative to the cap line, cap px
    f = ImageFont.truetype(fonts[italic], 400); f.set_variation_by_axes([weight])
    im = Image.new('L', (900, 900)); ImageDraw.Draw(im).text((250, 150), ch, font=f, fill=255)
    h = Image.new('L', (900, 900)); ImageDraw.Draw(h).text((250, 150), 'H', font=f, fill=255)
    hy = np.nonzero(np.asarray(h).max(1))[0]; ys, xs = np.nonzero(np.asarray(im))
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)), ys.min() - hy[0], hy[-1] + 1 - hy[0]


def typeset(fonts, lines, w, h, to_px):   # to_px(x, baseline, cap) → (px, py baseline, cap px, horizontal factor)
    out = Image.new('L', (w, h))
    for text, weight, italic, narrow, base, cap, centres in lines:
        for ch, cx in zip(text, centres):
            x, y, c, hx = to_px(cx, base, cap)
            g, top, gc = glyph(fonts, ch, weight, italic); s = c / gc   # the cap height (an H's) is c px; O and G overshoot it
            g = g.resize((max(1, round(g.width * s * narrow * hx)), max(1, round(g.height * s))), Image.LANCZOS)
            out.paste(255, (round(x - g.width / 2), round(y - c + top * s)), g)
    return out


def jar_print(fonts, w=2048):
    k = w / (LON[1] - LON[0]); h = round(k * (LAT[1] - LAT[0]))
    # a degree of longitude is cos(latitude) as long as one of latitude: the glyphs are widened by 1/cos to stay true
    to = lambda lon, base, cap: ((lon - LON[0]) * k, (LAT[1] - base) * k, cap * k, 1 / np.cos(np.radians(base + cap / 2)))
    return typeset(fonts, JAR, w, h, to)


def box_print(fonts, w=2048):
    fh = w / ASPECT; h = round(fh * (BAND[1] - BAND[0]))
    to = lambda x, base, cap: ((x - BOX_MID + .5) * w, (base - BAND[0]) * fh, cap * fh, 1)
    return typeset(fonts, BOX, w, h, to)


def foil(n=512, seed=7):   # tileable relief: low ripples stretched along the width, a little fine grain
    r = np.random.default_rng(seed)
    a = ndimage.gaussian_filter(r.standard_normal((n, n)), (n / 90, n / 14), mode='wrap')
    b = ndimage.gaussian_filter(r.standard_normal((n, n)), (n / 400, n / 60), mode='wrap')
    c = ndimage.gaussian_filter(r.standard_normal((n, n)), 1.2, mode='wrap')
    v = a / a.std() + 0.5 * b / b.std() + 0.15 * c / c.std()
    return Image.fromarray(np.clip(128 + v * 34, 0, 255).astype(np.uint8))


if __name__ == '__main__':
    fdir, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
    fonts = [os.path.join(fdir, 'Jost[wght].ttf'), os.path.join(fdir, 'Jost-Italic[wght].ttf')]
    jar_print(fonts).save(f'{out}/jar-print.png', optimize=True)
    box_print(fonts).save(f'{out}/box-print.png', optimize=True)
    foil().save(f'{out}/foil.jpg', quality=88)
    for n in ('jar-print.png', 'box-print.png', 'foil.jpg'):
        im = Image.open(f'{out}/{n}'); print(n, im.size, os.path.getsize(f'{out}/{n}') // 1024, 'KB')
