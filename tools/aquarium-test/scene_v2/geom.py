# depth grid (48x27), floor polyline, occluder z, light (caustic) mask 640x360
import numpy as np, json
from PIL import Image
from scipy import ndimage as ndi
HB, FB = 0.58, 1.243             # horizon by, floor plane by at z = 1
ZMAX = 2.6
med = np.asarray(Image.open('out/median720.png'), np.float32) / 255
H, W, _ = med.shape
d = np.load('out/depth720.npy')
L = np.load('out/labels720.npy')
yy, xx = np.mgrid[0:H, 0:W]; u = (xx + 0.5) / W; v = (yy + 0.5) / H
zm = 1 / (0.0334 * np.maximum(d, 0) + 0.385)
zfloor = np.where(v > HB + 0.01, (FB - HB) / np.maximum(v - HB, 1e-3), ZMAX)
Z = np.full((H, W), ZMAX, np.float32)
for k in (1, 2, 3):
    Z[L == k] = zm[L == k]
Z[L == 4] = np.minimum(zfloor[L == 4], ZMAX)
Z = np.clip(Z, 1.0, ZMAX)
stats = {}
for k, n in [(1, 'left'), (2, 'right'), (3, 'far')]:
    zz = Z[L == k]
    stats[n] = [float(np.percentile(zz, p)) for p in (5, 50, 90, 95, 99)]
print('z percentiles 5/50/90/95/99', json.dumps(stats))
np.save('out/Z720.npy', Z)
# visual
cm = np.clip((Z - 1.0) / 1.6, 0, 1)
vis = np.stack([1 - cm, 0.4 + 0 * cm, cm], -1) * 0.6 + med * 0.4
Image.fromarray((vis * 255).astype(np.uint8)).save('out/Z720_vis.png')
# clamp occluder surfaces below their occluder z (engine reefZ: inside the silhouette g < o.z + 0.03)
OCCZ = {'left': 1.85, 'right': 1.83, 'far': 2.30}
Z[L == 1] = np.minimum(Z[L == 1], OCCZ['left'] - 0.03)
Z[L == 2] = np.minimum(Z[L == 2], OCCZ['right'] - 0.03)
Z[L == 3] = np.minimum(Z[L == 3], OCCZ['far'] - 0.03)
np.save('out/Z720.npy', Z)
C, R = 48, 27
grid = np.zeros((R, C), np.float32)
for r in range(R):
    for c in range(C):
        y0, y1 = int(r * H / R), int((r + 1) * H / R); x0, x1 = int(c * W / C), int((c + 1) * W / C)
        grid[r, c] = np.percentile(Z[y0:y1, x0:x1], 30)
grid = np.round(grid, 2)
np.save('out/depthgrid.npy', grid)
# floor polyline: top edge of visible canyon floor (label 4) per column; reef base below the frame elsewhere
fl = []
lum0 = med @ np.array([0.2126, 0.7152, 0.0722], np.float32)
lm0 = ndi.gaussian_filter(lum0, 4)
for bx in np.round(np.arange(0, 1.0001, 0.025), 3):
    x = min(W - 1, int(bx * W))
    # visible canyon floor: label 4 (or bright rubble under the far reef's base) below by 0.6
    colL = (L[:, max(0, x - 3):x + 4] == 4).mean(1) > 0.5
    colB = (L[:, x] == 3) & (lm0[:, x] > 0.55)
    ok = (colL | colB) & (v[:, 0] > 0.6)
    # first row from which the floor continues (at least 85% floor) to the bottom or to the reef base
    rows = np.nonzero(ok)[0]
    by = 1.03
    if len(rows):
        for r0 in rows:
            seg = ok[r0:min(H, r0 + 40)]
            if seg.mean() > 0.85: by = (r0 + 0.5) / H; break
    fl.append([float(bx), round(float(by), 3)])
json.dump({'grid': grid.tolist(), 'floor': fl, 'occz': OCCZ, 'HB': HB, 'FB': FB}, open('out/geom.json', 'w'))
print('floor', fl)
# caustic mask 640x360: canyon floor = 1 (a touch less far away), lit + upward-facing coral = 0.15..0.8, water = 0
lum = med @ np.array([0.2126, 0.7152, 0.0722], np.float32)
ls = ndi.gaussian_filter(lum, 1.5)
below = np.roll(ls, -6, axis=0)
up = np.clip(0.5 + (ls - below) * 5, 0, 1)
lit = np.clip((ls - 0.16) / 0.42, 0, 1)
reefm = lit * (0.30 + 0.70 * up) * (1.05 - 0.35 * v)
mask = np.zeros((H, W), np.float32)
mask[L == 1] = 0.85 * reefm[L == 1]
mask[L == 2] = 0.85 * reefm[L == 2]
mask[L == 3] = 0.35 * reefm[L == 3]
fz = np.clip(Z, 1, ZMAX)
mask[L == 4] = np.clip(1.15 - 0.25 * (fz[L == 4] - 1.5), 0.55, 1.0)
mask = ndi.gaussian_filter(mask, 0.8)
m640 = np.asarray(Image.fromarray(mask.astype(np.float32), 'F').resize((640, 360), Image.BILINEAR))
a = (np.clip(m640, 0, 1) * 255 + 0.5).astype(np.uint8)
rgba = np.zeros((360, 640, 4), np.uint8); rgba[..., :3] = 255; rgba[..., 3] = a
Image.fromarray(rgba, 'RGBA').save('out/light_mask_video.png', optimize=True)
Image.fromarray(a).save('out/light_mask_vis.png')
