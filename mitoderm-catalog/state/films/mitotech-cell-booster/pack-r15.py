#!/usr/bin/env python3
"""Put the owner's current box print (R15) on the box picture the site already uses, keeping that picture's box,
angle and light.

Why: the site's picture of the MITOTECH CELL BOOSTER box is a render with an early print ("Advanced transdermal
delivery system", "for aged skin", "Advanced transdermal technology"); the owner's later prints say "skin to cell"
(R7) and "for skin rejuvenation" (R15). Nothing is redrawn here: the front face of the same render gets the R15
print, placed by the two mint plates that all three prints share, and shaded by the render's own light.

How:
  1. the corners of the two mint plates are found in the print (flat) and in the picture (in perspective) - eight
     point pairs give the homography print -> picture;
  2. the light of the render is measured as picture / R7 print, apart for the dark green and for the light inks,
     each smoothed over a wide neighbourhood so that no letter of the old text survives in it;
  3. the R15 print is warped into the picture and multiplied by that light, inside the front face only.

usage: pack-r15.py <site picture.webp> <print R7.png> <print R15.png> <out.webp> [check.png]
       (the prints: pdftoppm -r 200 -png -singlefile BOX_FRONT_PRINT_R7.pdf r7, the same for R15)
Needs numpy and Pillow (the bpy environment has both).
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

picture_path, r7_path, r15_path, out_path = sys.argv[1:5]
check_path = sys.argv[5] if len(sys.argv) > 5 else None


def mint(rgb):
    r, g, b = [rgb[..., i].astype(float) for i in range(3)]
    return (g > 150) & (b > 120) & (g - r > 45) & (r > 60) & (r < 215)


def components(mask, least):
    """Connected regions of a mask as lists of (ys, xs), the large ones only (a plain flood fill on a small copy)."""
    step = 2
    small = mask[::step, ::step]
    seen = np.zeros(small.shape, bool)
    found = []
    height, width = small.shape
    for y0, x0 in zip(*np.nonzero(small)):
        if seen[y0, x0]:
            continue
        stack, ys, xs = [(y0, x0)], [], []
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            ys.append(y)
            xs.append(x)
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < height and 0 <= nx < width and small[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(ys) * step * step >= least:
            found.append((np.array(ys) * step, np.array(xs) * step))
    return found


def corners(ys, xs):
    """Top left, top right, bottom right, bottom left of a nearly upright quadrilateral."""
    s, d = xs + ys, xs - ys
    return [(xs[i], ys[i]) for i in (np.argmin(s), np.argmax(d), np.argmax(s), np.argmin(d))]


def plates(rgb, least):
    """The two wide mint plates (the claim band and the facts band), upper first."""
    wide = []
    for ys, xs in components(mint(rgb), least):
        w, h = xs.max() - xs.min(), ys.max() - ys.min()
        if w > 3.5 * h:
            wide.append((len(ys), ys.mean(), ys, xs))
    wide = sorted(sorted(wide, reverse=True)[:2], key=lambda item: item[1])
    assert len(wide) == 2, 'the two mint plates were not found'
    return [corners(ys, xs) for _, _, ys, xs in wide]


def homography(src, dst):
    rows = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    return np.linalg.svd(np.array(rows, float))[2][-1].reshape(3, 3)


def warp(image, matrix, size):
    """The print seen through the homography print -> picture, as a float RGB array of the picture's size."""
    width, height = size
    inverse = np.linalg.inv(matrix)
    data = (inverse[0, 0], inverse[0, 1], inverse[0, 2], inverse[1, 0], inverse[1, 1], inverse[1, 2], inverse[2, 0], inverse[2, 1])
    scale = inverse[2, 2]
    data = tuple(v / scale for v in data)
    return np.asarray(image.transform((width, height), Image.PERSPECTIVE, data, Image.BICUBIC), float)


def blur(array, sigma):
    """A gaussian blur of a float array (Pillow's own works on 8-bit pictures only): rows, then columns."""
    radius = int(3 * sigma)
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    padded = np.pad(array, radius, mode='edge')
    rows = np.stack([np.convolve(line, kernel, mode='valid') for line in padded])
    return np.stack([np.convolve(line, kernel, mode='valid') for line in rows.T]).T


picture = Image.open(picture_path).convert('RGBA')
A = np.asarray(picture, float)
r7, r15 = Image.open(r7_path).convert('RGB'), Image.open(r15_path).convert('RGB')
src = [p for plate in plates(np.asarray(r15), 40000) for p in plate]
dst = [p for plate in plates(A[..., :3], 4000) for p in plate]
H = homography(src, dst)
size = picture.size
W7, W15 = warp(r7, H, size), warp(r15, H, size)

# the front face: the print's sheet shows through the face's own window. Its edges are where the render's front
# ends - found as the rectangle of the print whose projection the picture's opaque area still holds on all sides
alpha = A[..., 3] > 200


def inside(x0, y0, x1, y1):
    quad = []
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        u, v, w = H @ np.array([x, y, 1.0])
        quad.append((u / w, v / w))
    return quad


pw, ph = r15.size
face = [0.139 * pw, 0.178 * ph, 0.849 * pw, 0.855 * ph]      # the face's window on the print sheet (make_textures.py)
quad = inside(*face)
mask_image = Image.new('L', size, 0)
ImageDraw.Draw(mask_image).polygon(quad, fill=255)
mask = np.asarray(mask_image.filter(ImageFilter.GaussianBlur(1.2)), float) / 255 * alpha

# the render's light, measured apart for the three inks (dark green, mint, white), and only where the picture and
# the R7 print show the same ink: the picture's own text is older than R7 and differs from it in places, and a
# letter that stands in one and not in the other would otherwise leave its ghost in the light
def inks(rgb):
    lum = rgb.mean(axis=2)
    dark = lum < 115
    white = (rgb.min(axis=2) > 180) & ~dark
    return dark, ~dark & ~white, white


def light_of(same, sigmas):
    """picture / print for one ink, smooth; where the ink is rare nearby, a wider neighbourhood answers."""
    fields = []
    for channel in range(3):
        value, sure = None, None
        for sigma in sigmas:
            weight = blur(same, sigma)
            ratio = blur(A[..., channel] * same, sigma) / np.maximum(blur(W7[..., channel] * same, sigma), 1e-6)
            if value is None:
                value, sure = ratio, weight > 0.04
            else:
                value = np.where(sure, value, ratio)
                sure = sure | (weight > 0.01)
        total = (A[..., channel] * same).sum() / max((W7[..., channel] * same).sum(), 1e-6)
        fields.append(np.where(sure, value, total))
    return np.stack(fields, axis=2)


whole = mask > 0.99
picture_inks, print_inks = inks(A[..., :3]), inks(W7)
lights = [light_of((a & b & whole).astype(float), sigmas)
          for a, b, sigmas in zip(picture_inks, print_inks, ((30, 90), (14, 45), (14, 45, 120)))]
dark15, mint15, white15 = inks(W15)
soft = np.clip((W15.mean(axis=2) - 60) / 110, 0, 1)[..., None]            # letter edges: between the inks
light_ink = np.where(white15[..., None], lights[2], lights[1])
result = np.clip(W15 * (lights[0] * (1 - soft) + light_ink * soft), 0, 255)

out = A.copy()
out[..., :3] = A[..., :3] * (1 - mask[..., None]) + result * mask[..., None]
Image.fromarray(out.astype(np.uint8), 'RGBA').save(out_path, lossless=True)
if check_path:
    both = Image.new('RGB', (size[0] * 2 + 20, size[1]), 'white')
    both.paste(picture.convert('RGB'), (0, 0), picture.split()[3])
    new = Image.fromarray(out.astype(np.uint8), 'RGBA')
    both.paste(new.convert('RGB'), (size[0] + 20, 0), new.split()[3])
    both.save(check_path)
print('plates in the print:', [tuple(int(v) for v in p) for p in src])
print('plates in the picture:', [tuple(int(v) for v in p) for p in dst])
print('face in the picture:', [tuple(round(v) for v in p) for p in quad])
