# final occluder masks: grey+alpha PNGs (grey = 255, alpha = mask) cropped to the 8-px aligned bounding box
import numpy as np, json
from PIL import Image
m = np.load('out/masks_full.npz')
H, W = 1440, 2560
meta = {}
for k in ('left', 'right', 'far'):
    a = np.clip(m[k], 0, 1)
    a8 = (a * 255 + 0.5).astype(np.uint8)
    ys, xs = np.nonzero(a8 > 0)
    x0 = max(0, (xs.min() - 2) // 8 * 8); y0 = max(0, (ys.min() - 2) // 8 * 8)
    x1 = min(W, -(-(xs.max() + 3) // 8) * 8); y1 = min(H, -(-(ys.max() + 3) // 8) * 8)
    crop = a8[y0:y1, x0:x1]
    la = np.stack([np.full_like(crop, 255), crop], -1)
    Image.fromarray(la, 'LA').save(f'final/mask_{k}.png', optimize=True)
    meta[k] = {'px': [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
               'bx': x0 / W, 'by': y0 / H, 'bw': (x1 - x0) / W, 'bh': (y1 - y0) / H}
    print(k, meta[k]['px'])
json.dump(meta, open('final/masks_meta.json', 'w'), indent=1)
