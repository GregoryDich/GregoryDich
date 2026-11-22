#!/usr/bin/env python3
"""Give the opening clip wider margins: the kit lower in the frame and a little smaller, so the open lid clears the
site header (it hides the top 10-13 % of the film on every screen) and the base clears the phone caption.

Nothing is redrawn. Every rendered frame of the clip is pasted into one still of the same shot that shows more field
(kit3d.py ... extend=left,right,top,bottom - the same camera, the frame's own picture stays where it was), and the
result is scaled to 1920x1080. Only a side whose border never changes during the clip may get extra field from a
still: here the top (the room) and the right (table and room). The left border carries the moving shadow of the lid
and stays the frame's own border; the bottom rows are cut. The script reports how much the clip changes inside the
seam band - it must stay near zero.

usage: extend-frames.py <extended still> <frames dir (o-0000.png ...)> <out dir (x-0000.png ...)> <left> <top> [feather px=6]
       (the film's clip: extend=0,240,151,-16, left 0, top 151 -> scale 0.889)
Needs numpy and Pillow (the bpy environment has both).
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

ext_path, src_dir, out_dir, left, top = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
feather = int(sys.argv[6]) if len(sys.argv) > 6 else 6
ext = np.asarray(Image.open(ext_path).convert('RGB'), np.float32)
H, W = ext.shape[:2]
frames = sorted(glob.glob(os.path.join(src_dir, 'o-*.png')))
first = np.asarray(Image.open(frames[0]).convert('RGB'), np.float32)
h, w = first.shape[:2]
rows, cols = min(h, H - top), min(w, W - left)          # the part of the frame that lies inside the still
# weight of the frame: 1 inside, falling to 0 over `feather` px - only towards a side that has extra field
wx, wy = np.ones(cols, np.float32), np.ones(rows, np.float32)
if left > 0:
    wx = np.minimum(wx, np.clip((np.arange(cols) + 0.5) / feather, 0, 1))
if left + w < W:
    wx = np.minimum(wx, np.clip((cols - np.arange(cols) - 0.5) / feather, 0, 1))
if top > 0:
    wy = np.minimum(wy, np.clip((np.arange(rows) + 0.5) / feather, 0, 1))
if top + h < H:
    wy = np.minimum(wy, np.clip((rows - np.arange(rows) - 0.5) / feather, 0, 1))
weight = np.minimum.outer(wy, wx)[..., None]
seam = weight[..., 0] < 1
moved = 0.0                                              # how much the clip changes where the still takes over
os.makedirs(out_dir, exist_ok=True)
for i, path in enumerate(frames):
    frame = np.asarray(Image.open(path).convert('RGB'), np.float32)[:rows, :cols]
    if seam.any():
        change = np.abs(frame - first[:rows, :cols]).mean(axis=2)
        moved = max(moved, float(np.percentile(change[seam], 99.9)))
    out = ext.copy()
    region = out[top:top + rows, left:left + cols]
    out[top:top + rows, left:left + cols] = frame * weight + region * (1 - weight)
    image = Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).resize((1920, 1080), Image.LANCZOS)
    image.save(os.path.join(out_dir, 'x-%04d.png' % i), compress_level=3)
print('frames', len(frames), '| still', W, 'x', H, '| frame part used', cols, 'x', rows, '| scale', round(1920 / W, 4),
      '| largest change of the clip inside the seam band (99.9th percentile, 0-255):', round(moved, 2))
