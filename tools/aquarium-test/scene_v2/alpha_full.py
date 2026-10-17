# full-res occluder alphas: projection matte against the smooth water model, min over loop frames
import numpy as np, glob, sys
from PIL import Image
from scipy import ndimage as ndi
H, W = 1440, 2560
coef = np.load('out/water720.npz')['coef']
def basis(u, v, deg=4):
    cols = []
    for i in range(deg + 1):
        for j in range(deg + 1 - i):
            cols.append((u ** i) * (v ** j))
    return np.stack(cols, -1)
# 720p fit used u = x/(1279), v = y/(719); map full-res pixel centres to the same coordinates
ys = (np.arange(H) + 0.5) / 2 - 0.5; xs = (np.arange(W) + 0.5) / 2 - 0.5
U, V = np.meshgrid(xs / 1279, ys / 719)
Bm = (basis(U.ravel(), V.ravel()) @ coef).reshape(H, W, 3).astype(np.float32)
np.save('out/water_model_full.npy', Bm)
L720 = np.load('out/labels720.npy')
L = np.asarray(Image.fromarray(L720).resize((W, H), Image.NEAREST))
med = np.asarray(Image.open('out/median_full.png'), np.float32) / 255
frames = [med] + [np.asarray(Image.open(f), np.float32) / 255 for f in sorted(glob.glob('frames/dfull_*.png'))]
# water-likeness on the median at full res
dist_med = np.sqrt(((med - Bm) ** 2).sum(-1))
reef_lab = L > 0
# local reef colour F: normalized gaussian over "sure reef" (dist from water model > 0.10)
sure = (dist_med > 0.10) & reef_lab
def nblur(img, msk, s):
    w = ndi.gaussian_filter(msk.astype(np.float32), s)
    out = np.stack([ndi.gaussian_filter(img[..., c] * msk, s) for c in range(3)], -1)
    return out / np.maximum(w[..., None], 1e-4), w
F1, w1 = nblur(med, sure, 4)
F2, w2 = nblur(med, sure, 14)
F = np.where((w1 > 0.05)[..., None], F1, F2)
D = F - Bm
D2 = (D * D).sum(-1)
weak = D2 < 0.06 ** 2           # reef colour too close to water: projection unreliable
alphas = []
for C in frames:
    a = ((C - Bm) * D).sum(-1) / np.maximum(D2, 0.06 ** 2)
    alphas.append(np.clip(a, 0, 1).astype(np.float32))
A = np.stack(alphas)
amin = A.min(0); amed = np.median(A, 0)
np.save('out/alpha_min.npy', amin); np.save('out/alpha_med.npy', amed)
np.save('out/labels_full.npy', L)
np.save('out/weak.npy', weak)
# two-colour (water B -- reef F) fit on the median frame: projection + residual off the B-F line
am = ((med - Bm) * D).sum(-1) / np.maximum(D2, 0.06 ** 2)
res = np.sqrt((((med - Bm) - np.clip(am, 0, 1)[..., None] * D) ** 2).sum(-1))
np.save('out/a_med_proj.npy', np.clip(am, 0, 1).astype(np.float32)); np.save('out/res_med.npy', res.astype(np.float32))
print('done', amin.mean(), amed.mean(), weak.mean())
