# coarse labels at 720p: 0 water, 1 left pillar, 2 right pillar, 3 far reef, 4 floor
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
im = np.asarray(Image.open('out/median720.png'), np.float32) / 255
H, W, _ = im.shape
d = np.load('out/depth720.npy')
water = np.load('out/water720.npz')['water']
yy, xx = np.mgrid[0:H, 0:W]; u = xx / W; v = yy / H
near = d > 3.9
lab, n = ndi.label(near)
L = np.zeros((H, W), np.uint8)
# components touching left / right borders
left_ids = set(np.unique(lab[:, :3])) - {0}
right_ids = set(np.unique(lab[:, -3:])) - {0}
for i in range(1, n + 1):
    comp = lab == i
    if i in left_ids and i not in right_ids: L[comp] = 1
    elif i in right_ids: L[comp] = 2
    else:
        cx = xx[comp].mean(); print('stray comp', i, comp.sum(), cx / W, yy[comp].mean() / H)
        L[comp] = 1 if cx < W / 2 else 2
# grow pillar labels into adjacent non-water pixels (fine edges the blurry depth misses) up to 14 px
reef = ~water
for k in (1, 2):
    pass
dist_to = {}
for k in (1, 2):
    dist_to[k] = ndi.distance_transform_edt(L != k)
grow = 14
cand = reef & (L == 0)
g1 = cand & (dist_to[1] <= grow) & (dist_to[1] < dist_to[2])
g2 = cand & (dist_to[2] <= grow) & (dist_to[2] <= dist_to[1])
# but don't grow into the canyon floor / far reef where depth is clearly far (d < 2.6)
g1 &= (d > 2.6) | (dist_to[1] <= 4)
g2 &= (d > 2.6) | (dist_to[2] <= 4)
L[g1] = 1; L[g2] = 2
# remaining reef: far reef (above floor line) vs floor
rest = reef & (L == 0)
far = rest & (v < 0.80) & (u > 0.44) & (u < 0.76)
L[far] = 3
L[rest & (L == 0)] = 4
# far reef: keep largest component only, rest -> floor
lab3, n3 = ndi.label(L == 3)
if n3 > 1:
    sizes = ndi.sum(np.ones_like(lab3), lab3, range(1, n3 + 1)); big = 1 + int(np.argmax(sizes))
    L[(lab3 > 0) & (lab3 != big)] = 4
# remove reef pixels inside pillars that are water-classified (holes) -> keep as water (0)
# far reef vs canyon floor: rubble is bright (smoothed luma > 0.55), the reef mound dark; the far floor
# left of the mound starts at by 0.62, under the mound at by 0.72; below by 0.84 everything in the box is floor
lum = im @ np.array([0.2126, 0.7152, 0.0722], np.float32)
lm = ndi.gaussian_filter(lum, 4)
v0 = np.where(u < 0.50, 0.62, 0.72)
tofloor = (L == 3) & (((v >= v0) & (lm > 0.55)) | (v >= 0.84))
L[tofloor] = 4
fromfloor = (L == 4) & (u > 0.44) & (u < 0.74) & (v >= v0) & (v < 0.84) & (lm < 0.45)
L[fromfloor] = 3
L3 = ndi.binary_opening(L == 3, iterations=2); L[(L == 3) & ~L3] = 4
np.save('out/labels720.npy', L)
cols = np.array([[0, 0, 0], [1, 0.3, 0.3], [0.3, 1, 0.3], [0.3, 0.5, 1], [1, 1, 0.2]], np.float32)
vis = im * 0.55 + cols[L] * 0.45
vis[L == 0] = im[L == 0]
Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).save('out/labels720.png')
print({k: float((L == k).mean()) for k in range(5)})
