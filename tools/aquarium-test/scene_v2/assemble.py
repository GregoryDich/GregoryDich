# per-occluder alpha masks (full res) from labels + min projection alpha
import numpy as np, json
from PIL import Image
from scipy import ndimage as ndi
H, W = 1440, 2560
L = np.load('out/labels_full.npy')
amin = np.load('out/alpha_min.npy')
med = np.asarray(Image.open('out/median_full.png'), np.float32) / 255
yy, xx = np.mgrid[0:H, 0:W]; u = (xx + 0.5) / W; v = (yy + 0.5) / H
waterlab = L == 0
dw = ndi.distance_transform_edt(~waterlab)          # distance from the water label region
P = np.where(dw > 10, 1.0, amin).astype(np.float32)    # interior: solid; near water: projection matte
# see-through holes inside pillars (fire-coral lace, gaps between branches): on the water-reef colour line
# (residual < 0.05) and water-ish in the median AND in every build frame -> use the matte there too
a_mp = np.load('out/a_med_proj.npy'); r_mp = np.load('out/res_med.npy')
dmed = np.sqrt(((med - np.load('out/water_model_full.npy')) ** 2).sum(-1))
trust = (np.clip((0.07 - r_mp) / 0.03, 0, 1) * np.clip((0.10 - dmed) / 0.03, 0, 1)
         * ((L == 1) | (L == 2)) * (dw > 10) * (dw < 90)      # only near the open-water silhouette
         * (ndi.distance_transform_edt(L != 3) > 24))           # not where the far reef shows behind
trust = trust * ndi.binary_opening(trust > 0.5, iterations=1)     # no single-pixel specks
hole_a = np.maximum(a_mp, amin)
P0 = P.copy()
P = np.where(trust > 0, trust * hole_a + (1 - trust) * P, P).astype(np.float32)
# tiny 1px smoothing of the matte (soft 1-2 px edge), then a gentle contrast so edges stay 1-2 px
P = ndi.gaussian_filter(P, 0.6)
P = np.clip((P - 0.22) / 0.66, 0, 1)   # drop the 4:2:0 chroma-bleed rim (alpha 0.2-0.4 in water next to pale coral)
masks = {}
def soft(region, grow=6, feather=2.0):
    r = ndi.binary_dilation(region, iterations=grow) if grow else region
    s = ndi.gaussian_filter(r.astype(np.float32), feather)
    return np.clip((s - 0.5) * 2 + 0.5, 0, 1)   # ~ feather-wide ramp centred on the dilated edge
# left / right pillar: grow into water side only (the matte decides there); toward other reef labels: soft ramp
for k, name in [(1, 'left'), (2, 'right')]:
    reg = L == k
    toward_water = ndi.binary_dilation(reg, iterations=8) & waterlab
    S = soft(reg | toward_water, grow=0, feather=1.6)
    masks[name] = (S * P).astype(np.float32)
# far reef: matte against water; its base meets the bright rubble of the canyon floor along a ragged line:
# below by 0.72 the mask follows darkness (reef ~0.30-0.45 luma vs rubble 0.6-0.75), gone by by 0.88
lum = med @ np.array([0.2126, 0.7152, 0.0722], np.float32)
lm = ndi.gaussian_filter(lum, 8)
reg3 = (L == 3) | ((L == 4) & (v < 0.88) & (u > 0.44) & (u < 0.74))
tw3 = ndi.binary_dilation(L == 3, iterations=8) & waterlab
S3 = soft(reg3 | tw3, grow=0, feather=1.6)
bf = np.clip((0.56 - lm) / 0.12, 0, 1)
v0 = np.where(u < 0.50, 0.62, 0.72)                  # far floor left of the mound starts higher
active = v >= v0
bf = np.where(active, bf, 1.0) * np.clip((0.88 - v) / 0.03, 0, 1)
# close small bright-coral holes on the reef base (r 7 px), then soften
bb = ndi.binary_closing(bf > 0.5, structure=np.ones((15, 15), bool))
bf = np.where(active, np.maximum(bf, bb.astype(np.float32) * 0.0 + (bb & (bf <= 0.5)) * 1.0), bf)
bf = ndi.gaussian_filter(bf.astype(np.float32), 2.0)
S3 = S3 * bf
# reach a few px under the pillars (they are drawn on top, nearer): no seam where the two meet
pill = (L == 1) | (L == 2)
under = ndi.binary_dilation(L == 3, iterations=10) & pill
S3 = np.maximum(S3, ndi.gaussian_filter(under.astype(np.float32), 1.2) * (v < 0.78))
P0s = np.clip((ndi.gaussian_filter(P0, 0.6) - 0.22) / 0.66, 0, 1)
far = S3 * P0s
# under the pillars' soft edges the far reef stays solid unless that pixel is clearly water: no seam for a
# fish behind both (pillars are nearer and drawn on top anyway)
und = ndi.gaussian_filter(((under & (P0s > 0.3)) | (reg3 & (P0s > 0.3) & ndi.binary_dilation(pill, iterations=6))).astype(np.float32), 1.0) * (v < 0.78)
far = np.clip(np.maximum(far, und), 0, 1)
masks['far'] = far.astype(np.float32)
np.savez_compressed('out/masks_full.npz', **masks)
for k, m in masks.items():
    ys, xs = np.nonzero(m > 1 / 255)
    print(k, 'bbox', xs.min(), ys.min(), xs.max(), ys.max(), 'cover', float((m > 0.5).mean()))
    Image.fromarray((m * 255 + 0.5).astype(np.uint8)).save(f'out/mask_{k}_full.png')
# visual: show masks over the median, water dimmed
vis = med.copy()
cols = {'left': (1, 0.2, 0.2), 'right': (0.2, 1, 0.2), 'far': (0.3, 0.5, 1)}
for k, m in masks.items():
    vis = vis * (1 - 0.45 * m[..., None]) + np.array(cols[k]) * 0.45 * m[..., None]
Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).save('out/masks_vis_full.png')
Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).resize((1280, 720), Image.LANCZOS).save('out/masks_vis_720.png')
