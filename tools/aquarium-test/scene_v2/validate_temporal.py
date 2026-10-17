# hold-out check of the static masks against loop frames NOT used to build them (n = 20 mod 40), day and night
import numpy as np, glob, json, sys
from PIL import Image
from scipy import ndimage as ndi
Bm = np.load('out/water_model_full.npy')
m = np.load('out/masks_full.npz')
med = np.asarray(Image.open('out/median_full.png'), np.float32) / 255
L = np.load('out/labels_full.npy')
dist_med = np.sqrt(((med - Bm) ** 2).sum(-1))
sure = (dist_med > 0.10) & (L > 0)
def nblur(img, msk, s):
    w = ndi.gaussian_filter(msk.astype(np.float32), s)
    out = np.stack([ndi.gaussian_filter(img[..., c] * msk, s) for c in range(3)], -1)
    return out / np.maximum(w[..., None], 1e-4), w
F1, w1 = nblur(med, sure, 4); F2, _ = nblur(med, sure, 14)
F = np.where((w1 > 0.05)[..., None], F1, F2); D = F - Bm; D2 = np.maximum((D * D).sum(-1), 0.06 ** 2)
waterlab = L == 0
band = ndi.distance_transform_edt(~waterlab) <= 10      # where the matte (not the solid core) decides
res = {}
for k in ('left', 'right', 'far'):
    M = m[k]
    edge = band & (M > 0.02) | (band & ndi.binary_dilation(M > 0.5, iterations=3))
    res[k] = {'edge_px': int(edge.sum()), 'frames': []}
fs = sorted(glob.glob('frames/dhold_*.png'))
prev = None
for f in fs:
    C = np.asarray(Image.open(f), np.float32) / 255
    a = np.clip(((C - Bm) * D).sum(-1) / D2, 0, 1)
    for k in ('left', 'right', 'far'):
        M = m[k]
        edge = band & ((M > 0.02) | ndi.binary_dilation(M > 0.5, iterations=3))
        ghost = edge & (M > 0.5) & (a < 0.2)          # mask covers what is water in this frame
        miss = edge & (M < 0.2) & (a > 0.8)           # coral in this frame outside the mask
        res[k]['frames'].append({'f': f.split('/')[-1], 'ghost_px': int(ghost.sum()), 'miss_px': int(miss.sum())})
    if prev is not None:
        dd = np.abs(C - prev).max(-1) * 255
        for k in ('left', 'right', 'far'):
            core = m[k] > 0.98
            res[k].setdefault('content_diff', []).append([float(np.percentile(dd[core], 50)), float(np.percentile(dd[core], 99)), float(dd[core].max())])
    prev = C
for k in res:
    g = [x['ghost_px'] for x in res[k]['frames']]; mi = [x['miss_px'] for x in res[k]['frames']]
    res[k]['ghost_max_px'] = max(g); res[k]['ghost_mean_px'] = float(np.mean(g))
    res[k]['ghost_frac_of_edge'] = max(g) / max(1, res[k]['edge_px'])
    res[k]['miss_max_px'] = max(mi); res[k]['miss_frac_of_edge'] = max(mi) / max(1, res[k]['edge_px'])
    print(k, 'edge px', res[k]['edge_px'], 'ghost max', max(g), f"({res[k]['ghost_frac_of_edge']*100:.3f}% of edge)", 'miss max', max(mi), f"({res[k]['miss_frac_of_edge']*100:.2f}%)", 'content diff p50/p99/max (frames 40 apart):', np.round(np.max(res[k]['content_diff'], 0), 1))
json.dump(res, open('out/temporal_check.json', 'w'), indent=1)
