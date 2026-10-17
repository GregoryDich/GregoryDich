# Ретушь жёлтых трубчатых губок: из «пластикового» лаймового с зелёной каймой → естественный охристо-жёлтый
# (тон ≈45°, насыщенность ≤0.4), свет сверху, тёмное основание; зелёная кайма — деспилл и эрозия 1 px.
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
src, dst = sys.argv[1], sys.argv[2]
im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float32) / 255.0
rgb, a = im[..., :3], im[..., 3]
H, W = a.shape
# HSV
mx, mn = rgb.max(-1), rgb.min(-1); d = mx - mn + 1e-6
r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
s = np.where(mx > 0, d / (mx + 1e-6), 0); v = mx
body = (h > 38) & (h < 150)                       # жёлто-зелёное тело и зелёная кайма; отверстия (бурые, h < 38) — как есть
h2 = np.where(body, np.clip(47 + 0.18 * (h - 70), 40, 54), h)
s2 = np.where(body, np.minimum(s * 0.8, 0.5), np.minimum(s, 0.55))
# свет сверху и тёмное основание (по высоте картинки; у основания −35%)
yy = (np.arange(H)[:, None] / (H - 1)) * np.ones((1, W))
light = 1.10 - 0.22 * yy - 0.25 * np.clip((yy - 0.82) / 0.18, 0, 1) ** 1.5
v2 = np.clip(v * np.where(body, light, 1.0), 0, 1)
# кайма: в 3 px от края альфы — чуть темнее и без зелени (деспилл), альфа — эрозия на 1 px
inner = ndimage.binary_erosion(a > 0.5, iterations=3)
rim = (a > 0.02) & ~inner
v2 = np.where(rim & body, v2 * 0.85, v2)
s2 = np.where(rim & body, s2 * 0.8, s2)
# HSV → RGB
c = v2 * s2; hp = h2 / 60; x = c * (1 - np.abs(hp % 2 - 1)); m = v2 - c
z = np.zeros_like(c)
sel = [(hp < 1, (c, x, z)), ((hp >= 1) & (hp < 2), (x, c, z)), ((hp >= 2) & (hp < 3), (z, c, x)), ((hp >= 3) & (hp < 4), (z, x, c)), ((hp >= 4) & (hp < 5), (x, z, c)), (hp >= 5, (c, z, x))]
out = np.zeros_like(rgb)
for msk, (rr, gg, bb) in sel:
    out[..., 0] = np.where(msk, rr + m, out[..., 0]); out[..., 1] = np.where(msk, gg + m, out[..., 1]); out[..., 2] = np.where(msk, bb + m, out[..., 2])
# деспилл: G не выше max(R, B)·1.0 на кайме (зелёный ореол)
gm = np.maximum(out[..., 0], out[..., 2])
out[..., 1] = np.where(rim, np.minimum(out[..., 1], gm), out[..., 1])
a2 = ndimage.grey_erosion(a, size=(3, 3))
a2 = np.where(a > 0.98, a, a2)                    # внутри — без изменений
res = np.dstack([np.clip(out, 0, 1), a2])
Image.fromarray((res * 255 + 0.5).astype(np.uint8), 'RGBA').save(dst, optimize=True)
o = res[..., :3][res[..., 3] > 0.8]
mxo, mno = o.max(-1), o.min(-1)
print('mean rgb', (o.mean(0) * 255).round(), 'sat', round(float(((mxo - mno) / (mxo + 1e-6)).mean()), 2))
