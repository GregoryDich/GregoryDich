# water seen THROUGH the reef (lace holes, gaps between branches): water-like in every build frame
import numpy as np, glob
from PIL import Image
Bm = np.load('out/water_model_full.npy')
fs = ['out/median_full.png'] + sorted(glob.glob('frames/dfull_*.png'))
dmax = None
for f in fs:
    C = np.asarray(Image.open(f), np.float32) / 255
    dd = np.sqrt(((C - Bm) ** 2).sum(-1))
    dmax = dd if dmax is None else np.maximum(dmax, dd)
np.save('out/water_dmax.npy', dmax.astype(np.float32))
L = np.load('out/labels_full.npy')
for t in (0.03, 0.045, 0.06):
    h = (dmax < t) & ((L == 1) | (L == 2))
    print(t, int(h.sum()))
