#!/usr/bin/env python3
"""Change the print on the pack inside a clip that was shot from a frame with the pack placed by place-pack.py.

Why: the first clip of the MITOTECH film (T1: the box in the clinic, the focus goes to the two women) was shot
from the frame C1, where the box carried an early print. The owner chose the current print (R15, 23/11). The box
does not move in the clip - only its focus changes - so the print can be changed in every frame without a re-shoot:
nothing is generated, the clip keeps its people, its light and its focus pull.

How, per frame:
  1. the frame's box is the placed box seen through a blur and a gain: both are measured against the frame built
     with the OLD cut-out (C1-old), the blur on a grid, the gain by least squares; the blur is smoothed over time;
  2. the difference "new print minus old print" (C1-new - C1-old, zero outside the box and its mirror image) is
     blurred and gained the same way and added to the frame;
  3. where letters changed, the clip's own fine rendering of the OLD letters would stay as a ghost: there the fine
     detail of the frame is replaced by the model's (the smooth part of the frame's light is kept).

usage: pack-print-in-clip.py <frames dir (f-001.png ...)> <C1 old.png> <C1 new.png> <out dir> at=X,Y height=H
       (the two C1 frames: place-pack.py <plate> <cut-out> C1.png at=X,Y height=H plate_blur=9 with the old and the
        new cut-out; at and height as given to place-pack.py, in the pixels of the C1 frames)
Prints the blur and gain found for every tenth frame. Needs numpy and Pillow (the bpy environment has both).
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

frames_dir, old_path, new_path, out_dir = sys.argv[1:5]
ARG = dict(a.split('=', 1) for a in sys.argv[5:])
AT = [int(v) for v in ARG['at'].split(',')]
HEIGHT = int(ARG['height'])
frames = sorted(glob.glob(os.path.join(frames_dir, 'f-*.png')))
first = Image.open(frames[0])
W, H = first.size
old_full, new_full = Image.open(old_path).convert('RGB'), Image.open(new_path).convert('RGB')
sx, sy = W / old_full.size[0], H / old_full.size[1]


def blur(array, sigma):
    """A gaussian blur of a float array (rows, then columns), edges repeated."""
    if sigma <= 0.05:
        return array
    radius = max(1, int(3 * sigma + 0.5))
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2).astype(np.float32)
    kernel /= kernel.sum()
    padded = np.pad(array, ((radius, radius), (radius, radius)) + ((0, 0),) * (array.ndim - 2), mode='edge')
    rows = sum(k * padded[:, i:i + array.shape[1]] for i, k in enumerate(kernel))
    return sum(k * rows[i:i + array.shape[0]] for i, k in enumerate(kernel))


old = np.asarray(old_full.resize((W, H), Image.LANCZOS), np.float32)
new = np.asarray(new_full.resize((W, H), Image.LANCZOS), np.float32)
diff_full = new - old
changed = np.abs(diff_full).max(axis=2) > 6
ys, xs = np.nonzero(changed)
PAD = 40                                                  # room for the blur around everything that changes
x0, x1 = max(0, xs.min() - PAD), min(W, xs.max() + 1 + PAD)
y0, y1 = max(0, ys.min() - PAD), min(H, ys.max() + 1 + PAD)
old_c, diff_c = old[y0:y1, x0:x1], diff_full[y0:y1, x0:x1]
# the box's own face, for measuring: well inside the placed cut-out
bx0, by0 = int(AT[0] * sx) - x0, int(AT[1] * sy) - y0
bh = int(HEIGHT * sy)
bw = int(bh * (xs.max() - xs.min()) / max(1, (ys.max() - ys.min())))
inner = (slice(max(0, by0 + 22), by0 + bh - 22), slice(max(0, bx0 + 22), min(x1 - x0, bx0 + bw) - 22))
GRID = [0.0, 0.4, 0.6, 0.8, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5, 4.75, 5.0, 5.25, 5.5, 6.0, 6.5]
old_blurred = {s: blur(old_c, s) for s in GRID}

crops, fits = [], []
for path in frames:
    crop = np.asarray(Image.open(path).convert('RGB').crop((x0, y0, x1, y1)), np.float32)
    best = None
    for s in GRID:
        a, t = old_blurred[s][inner], crop[inner]
        gain = float((a * t).sum() / (a * a).sum())
        rms = float(np.sqrt(((gain * a - t) ** 2).mean()))
        if best is None or rms < best[0]:
            best = (rms, s, gain)
    crops.append(crop)
    fits.append(best)
sigmas = np.array([f[1] for f in fits])
gains = np.array([f[2] for f in fits])
# the focus pull is smooth: a running median, then a short running mean, take out the steps of the grid
smooth = np.array([np.median(sigmas[max(0, i - 2):i + 3]) for i in range(len(sigmas))])
smooth = np.array([smooth[max(0, i - 2):i + 3].mean() for i in range(len(smooth))])
gain_s = np.array([np.median(gains[max(0, i - 3):i + 4]) for i in range(len(gains))])

# where letters changed: the fine detail of the frame gives way to the model's
letters = (np.abs(diff_c).max(axis=2) > 10).astype(np.float32)
mask = np.clip(blur((blur(letters, 2.0) > 0.08).astype(np.float32), 1.5), 0, 1)[..., None]

os.makedirs(out_dir, exist_ok=True)
for i, path in enumerate(frames):
    s, g = float(smooth[i]), float(gain_s[i])
    crop = crops[i]
    model_old = g * blur(old_c, s)
    added = g * blur(diff_c, s)
    residual = crop - model_old
    fine = residual - blur(residual, 5.0)
    out = crop + added - mask * fine
    frame = np.asarray(Image.open(path).convert('RGB')).copy()
    frame[y0:y1, x0:x1] = np.clip(out + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(frame).save(os.path.join(out_dir, os.path.basename(path)), compress_level=3)
    if i % 10 == 0 or i == len(frames) - 1:
        print('frame %3d  blur %.2f (measured %.2f)  gain %.3f  rms %.2f' % (i + 1, s, sigmas[i], g, fits[i][0]))
print('frames', len(frames), '| changed area x %d-%d, y %d-%d of %dx%d' % (x0, x1, y0, y1, W, H))
