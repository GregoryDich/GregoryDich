"""Lay a transparent Cycles frame (vtech_scene.py) over the line's smoke background, same camera and aspect.
usage: python3 compose.py <frame.png> <layers/vt-bg-wide.jpg | m7-bg.jpg> <out.jpg|out.webp> [gain=1]
gain scales the smoke's brightness per screen, as the three.js `dim` did (S4 brightest, S5 calmer)."""
import sys
from PIL import Image, ImageEnhance
frame, bg, out = sys.argv[1:4]
gain = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
fg = Image.open(frame).convert('RGBA')
base = ImageEnhance.Brightness(Image.open(bg).convert('RGB')).enhance(gain).resize(fg.size, Image.LANCZOS).convert('RGBA')
im = Image.alpha_composite(base, fg).convert('RGB')
im.save(out, quality=92) if out.endswith('.jpg') else im.save(out, quality=90, method=6)
print(out, im.size)
