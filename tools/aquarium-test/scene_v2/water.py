# water model + coarse reef/water classification on the 720p median
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
im = np.asarray(Image.open('out/median720.png'), np.float32) / 255
H, W, _ = im.shape
yy, xx = np.mgrid[0:H, 0:W]
u = xx / (W - 1); v = yy / (H - 1)
lum = im @ np.array([0.2126, 0.7152, 0.0722], np.float32)
m = ndi.uniform_filter(lum, 7); m2 = ndi.uniform_filter(lum * lum, 7)
tex = np.sqrt(np.maximum(m2 - m * m, 0))
def basis(u, v, deg=4):
    cols = []
    for i in range(deg + 1):
        for j in range(deg + 1 - i):
            cols.append((u ** i) * (v ** j))
    return np.stack(cols, -1)
B = basis(u.ravel(), v.ravel())
seed = ((v < 0.22) & (u > 0.3) & (u < 0.75)) | ((v < 0.38) & (u > 0.52) & (u < 0.62))
water = seed.copy()
for it in range(6):
    idx = water.ravel()
    coef, *_ = np.linalg.lstsq(B[idx], im.reshape(-1, 3)[idx], rcond=None)
    model = (B @ coef).reshape(H, W, 3)
    dist = np.sqrt(((im - model) ** 2).sum(-1))
    water = (dist < 0.045) & (tex < 0.018)
    # keep only components connected to the seed
    lab, n = ndi.label(water)
    keep = np.unique(lab[seed & water]); keep = keep[keep > 0]
    water = np.isin(lab, keep)
    print(it, water.mean(), np.percentile(dist[water], [50, 95]))
np.savez_compressed('out/water720.npz', coef=coef, water=water, dist=dist, tex=tex)
vis = im.copy(); vis[water] = vis[water] * 0.4 + np.array([1, 0, 0]) * 0.6
Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).save('out/water720_vis.png')
Image.fromarray((np.clip(model, 0, 1) * 255).astype(np.uint8)).save('out/water_model720.png')
Image.fromarray((np.clip(dist * 6, 0, 1) * 255).astype(np.uint8)).save('out/water_dist720.png')
