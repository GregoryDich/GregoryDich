#!/usr/bin/env python3
"""Place the REAL packshot (true print, pixel for pixel) into a scene: black glass, teal light, reflection, contact shadow.
Generators garble small print, so the box is never generated for final frames — it is composited from the packshot file.

  python3 composite.py packshot.webp out.jpg [--bg plate.jpg] [--x 0.72] [--base 0.80] [--h 0.62] [--w 1920 --hh 1080]
--x: packshot centre as a fraction of width; --base: where the packshot stands (fraction of height); --h: packshot height fraction.
Without --bg a procedural studio plate is drawn: near-black room, black glass floor, soft teal glow behind the product.
"""
import argparse
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

def plate(W, H, horizon, glow_x, teal=(111, 183, 186)):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    bg = np.zeros((H, W, 3), np.float32) + np.array([7, 10, 11], np.float32)
    # soft teal glow behind the product and a faint key from the upper left
    d = np.sqrt(((x - glow_x) / (W * 0.30)) ** 2 + ((y - horizon * 0.80) / (H * 0.42)) ** 2)
    bg += np.array(teal, np.float32)[None, None, :] * (0.20 * np.exp(-d ** 2))[..., None]
    d2 = np.sqrt(((x - W * 0.12) / (W * 0.55)) ** 2 + ((y - H * 0.05) / (H * 0.65)) ** 2)
    bg += np.array(teal, np.float32)[None, None, :] * (0.07 * np.exp(-d2 ** 2))[..., None]
    # black glass: slightly lifted, with a thin horizon highlight
    g = y >= horizon
    bg[g] = bg[g] * 0.55 + np.array([4, 7, 8], np.float32)
    line = np.exp(-((y - horizon) / 1.6) ** 2) * np.exp(-((x - glow_x) / (W * 0.33)) ** 2)
    bg += np.array([60, 105, 108], np.float32)[None, None, :] * (0.35 * line)[..., None]
    return np.clip(bg, 0, 255)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('packshot'); ap.add_argument('out')
    ap.add_argument('--bg'); ap.add_argument('--x', type=float, default=0.72); ap.add_argument('--base', type=float, default=0.80)
    ap.add_argument('--h', type=float, default=0.62); ap.add_argument('--w', type=int, default=1920); ap.add_argument('--hh', type=int, default=1080)
    a = ap.parse_args()
    W, H = a.w, a.hh
    horizon = int(H * a.base)
    if a.bg:
        base = np.asarray(Image.open(a.bg).convert('RGB').resize((W, H), Image.LANCZOS), np.float32)
    else:
        base = plate(W, H, horizon, int(W * a.x))
    p = Image.open(a.packshot).convert('RGBA')
    # trim to the opaque bounding box, scale to the target height
    p = p.crop(p.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
    ph = int(H * a.h); pw = int(p.width * ph / p.height)
    p = p.resize((pw, ph), Image.LANCZOS)
    # integrate with the dark set: a touch darker and cooler, the print stays sharp
    rgb = ImageEnhance.Brightness(p.convert('RGB')).enhance(0.93)
    arr = np.asarray(rgb, np.float32); arr = arr * np.array([0.97, 1.0, 1.01]); rgb = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    p = Image.merge('RGBA', (*rgb.split(), p.getchannel('A')))
    x0 = int(W * a.x - pw / 2); y0 = horizon - ph
    out = Image.fromarray(base.astype(np.uint8)).convert('RGBA')
    # contact shadow
    sh = Image.new('L', (W, H), 0); sa = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    sa = 120 * np.exp(-(((xx - (x0 + pw / 2)) / (pw * 0.55)) ** 2 + ((yy - horizon) / (H * 0.012)) ** 2))
    shadow = Image.fromarray(sa.astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    out = Image.composite(Image.new('RGBA', (W, H), (0, 0, 0, 255)), out, shadow)
    # reflection in the glass: flipped, fading, slightly blurred
    refl = p.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(1.2))
    ra = np.asarray(refl.getchannel('A'), np.float32)
    fade = np.linspace(0.30, 0.0, ph)[:, None] ** 1.4
    ra = ra * np.clip(fade / 0.30 * 0.30, 0, 1)
    refl.putalpha(Image.fromarray(ra.astype(np.uint8)))
    out.alpha_composite(refl, (x0, horizon))
    out.alpha_composite(p, (x0, y0))
    out.convert('RGB').save(a.out, quality=90)
    print(a.out, W, H, 'packshot', pw, ph, 'at', x0, y0)

if __name__ == '__main__':
    main()
