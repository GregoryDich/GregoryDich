"""Lay a transparent Cycles frame (vtech_scene.py) over the line's smoke background, same camera and aspect.
usage: python3 compose.py <frame.png> <layers/vt-bg-wide.jpg> <out.jpg|out.webp>"""
import sys
from PIL import Image
frame, bg, out = sys.argv[1:4]
fg = Image.open(frame).convert('RGBA')
base = Image.open(bg).convert('RGB').resize(fg.size, Image.LANCZOS).convert('RGBA')
im = Image.alpha_composite(base, fg).convert('RGB')
im.save(out, quality=92) if out.endswith('.jpg') else im.save(out, quality=90, method=6)
print(out, im.size)
