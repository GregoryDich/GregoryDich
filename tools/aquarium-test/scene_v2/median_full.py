import numpy as np, glob
from PIL import Image
fs = sorted(glob.glob('frames/dfull_*.png'))
# median in row strips to save memory
H, W = 1440, 2560
out = np.zeros((H, W, 3), np.uint8)
for y0 in range(0, H, 240):
    A = np.stack([np.asarray(Image.open(f))[y0:y0+240] for f in fs])
    out[y0:y0+240] = np.median(A, 0).astype(np.uint8)
Image.fromarray(out).save('out/median_full.png')
print('ok')
