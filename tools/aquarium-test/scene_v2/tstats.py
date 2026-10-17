import numpy as np, glob, sys
from PIL import Image
fs = sorted(glob.glob('frames/d720_*.png'))
A = np.stack([np.asarray(Image.open(f), dtype=np.float32) for f in fs])  # T,H,W,3
med = np.median(A, axis=0)
lum = A @ np.array([0.2126, 0.7152, 0.0722], np.float32)
std = lum.std(0)
rng = lum.max(0) - lum.min(0)
# mean abs dev from median, per pixel max over time
dev = np.abs(lum - np.median(lum, 0)).max(0)
np.savez_compressed('out/tstats720.npz', med=med.astype(np.float32), std=std, rng=rng, dev=dev)
Image.fromarray(np.clip(med, 0, 255).astype(np.uint8)).save('out/median720.png')
Image.fromarray(np.clip(std * 8, 0, 255).astype(np.uint8)).save('out/std720_x8.png')
Image.fromarray(np.clip(dev * 4, 0, 255).astype(np.uint8)).save('out/dev720_x4.png')
print('std pct', np.percentile(std, [50, 90, 99, 99.9]), 'dev pct', np.percentile(dev, [50, 90, 99, 99.9]))
