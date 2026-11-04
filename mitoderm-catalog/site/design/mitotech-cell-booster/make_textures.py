"""Textures for the three.js MITOTECH CELL BOOSTER scene (site/proto/scenes/mitotech-cell-booster.js), from the owner's
print files (design/mitotech/print/, vector, text in outlines): rasterised here with pdftoppm at twice the texture's
size and reduced, so every letter is the print's own and sharp at any size. No text of ours, no fonts.

The box's front: the R15 render (design/mitotech/packshot-kit-r15.png) shows the same print as BOX_FRONT_PRINT_R15.pdf,
undistorted, with smaller margins than the PDF's trim (≈ 2 % of the face instead of ≈ 9 %). The crop below was found by
a homography from the print's mint features (the two plates' corners, «MITODERM»'s box) to the render's front: the face
spans print px@400 x 790…4840, y 800…3840 (W : H = 1.332; «MITODERM» 2.2 % from the left edge and 4.6 % from the top,
the plates' right ends 2.1 % from the right, as on the render). No dieline, no size in mm: the box's proportions are
taken from the render (an assumption, see the scene's header).

Writes into <out dir> (default site/proto/img/mitotech-cell-booster-3d/):
  box-front.webp   the front's print, sRGB 4096×3075, lossless WebP (738 KB; PNG would be 1.35 MB)
  box-metal.png    the front's material, 1024×768: G roughness (0.24 foil / 0.6 ink), B metalness (1 on the bare green
                   foil, 0 under the mint and white inks), as three.js reads roughnessMap (G) and metalnessMap (B)
  label-powder.webp, label-booster.webp   the vials' labels (CONCENTRATED_POWDER_PRINT2.pdf, BOOSTING_AMPOULE_PRINT2.pdf,
                   trim 71 × 30 mm), sRGB 2048×865 lossless WebP, wrapped round 74 % of the glass (the largest vial, a
                   step card's 1760 px in a 3840 key, shows ≈ 1.6 texels per px across its front)
usage: python3 -I make_textures.py [out dir]"""
import os, subprocess, sys, tempfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PRINT = os.path.join(HERE, '..', 'mitotech', 'print')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'proto', 'img', 'mitotech-cell-booster-3d')
FACE = (790, 800, 4840, 3840)            # the front's crop, print px at 400 dpi (top left = 0)
FRONT_W = 4096
FRONT_H = round(FRONT_W * (FACE[3] - FACE[1]) / (FACE[2] - FACE[0]))
LABEL_TRIM = (8.5, 8.5, 209.76, 93.54)   # pt, from the bottom left (pdfinfo -box): 71.0 × 30.0 mm
LABEL_W = 2048
GREEN = np.array([0x15, 0x47, 0x34], float)   # the print's green (its dominant colour)


def raster(pdf, dpi, x, y, w, h, tmp):
    """pdftoppm of the region (x, y, w, h) in px at `dpi` (top left = 0), RGB"""
    base = os.path.join(tmp, 'r')
    subprocess.run(['pdftoppm', '-r', str(dpi), '-x', str(x), '-y', str(y), '-W', str(w), '-H', str(h), '-png', '-singlefile',
                    pdf, base], check=True)
    return Image.open(base + '.png').convert('RGB')


def main():
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        # the front: 2 × the texture's size, then reduced (Lanczos)
        k = 2 * FRONT_W / (FACE[2] - FACE[0])
        dpi = 400 * k
        x0, y0 = round(FACE[0] * k), round(FACE[1] * k)
        img = raster(os.path.join(PRINT, 'BOX_FRONT_PRINT_R15.pdf'), round(dpi, 3), x0, y0, 2 * FRONT_W, 2 * FRONT_H, tmp)
        front = img.resize((FRONT_W, FRONT_H), Image.LANCZOS)
        front.save(os.path.join(OUT, 'box-front.webp'), lossless=True, method=6)
        # the foil's mask: how far each texel is from the bare green (ink coverage), at a quarter size
        a = np.asarray(front.resize((FRONT_W // 4, FRONT_H // 4), Image.BOX)).astype(float)
        d = np.linalg.norm(a - GREEN, axis=-1)
        ink = np.clip((d - 10) / 40, 0, 1)
        metal = (1 - ink) * 255
        rough = (0.24 + (0.6 - 0.24) * ink) * 255
        Image.fromarray(np.stack([np.zeros_like(metal), rough, metal], -1).round().astype(np.uint8)).save(
            os.path.join(OUT, 'box-metal.png'), optimize=True)
        # the labels: their trim box
        for src, name in (('CONCENTRATED_POWDER_PRINT2.pdf', 'label-powder.webp'), ('BOOSTING_AMPOULE_PRINT2.pdf', 'label-booster.webp')):
            pdf = os.path.join(PRINT, src)
            media_h = 102.05   # pt (both labels' MediaBox)
            tw, th = LABEL_TRIM[2] - LABEL_TRIM[0], LABEL_TRIM[3] - LABEL_TRIM[1]
            lw, lh = 2 * LABEL_W, round(2 * LABEL_W * th / tw)
            dpi = lw / tw * 72
            x0 = round(LABEL_TRIM[0] / 72 * dpi); y0 = round((media_h - LABEL_TRIM[3]) / 72 * dpi)
            img = raster(pdf, round(dpi, 3), x0, y0, lw, lh, tmp)
            img.resize((LABEL_W, lh // 2), Image.LANCZOS).save(os.path.join(OUT, name), lossless=True, method=6)
    for f in ('box-front.png', 'label-powder.png', 'label-booster.png'):   # earlier names
        if os.path.exists(os.path.join(OUT, f)): os.remove(os.path.join(OUT, f))
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f); print(f, Image.open(p).size, os.path.getsize(p) // 1024, 'KB')


if __name__ == '__main__':
    main()
