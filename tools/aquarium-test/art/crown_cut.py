# Передний «венец» актинии: щупальца ниже линии диска (y > 0.62) в эллипсе rx 0.30, ry 0.15 вокруг гнезда
# (nest 0.508, 0.723), без яркого центра диска (внутренний эллипс 0.07 × 0.035 — рыба не тонет в свечении),
# край растушёван, альфа × 0.85. Рыбы-клоуны держатся между задним слоем (z+0.03) и этим (z−0.03).
import sys
import numpy as np
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float32)
H, W = im.shape[:2]
y, x = np.mgrid[0:H, 0:W]
u, v = x / W, y / H
nx, ny = 0.508, 0.723
e = ((u - nx) / 0.42) ** 2 + ((v - ny) / 0.17) ** 2
ei = ((u - nx) / 0.07) ** 2 + ((v - ny) / 0.035) ** 2
sm = lambda a, b, t: np.clip((t - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((t - a) / (b - a), 0, 1))
k = (1 - sm(0.75, 1.0, e)) * sm(0.6, 1.4, ei) * sm(0.615, 0.66, v) * 0.85
out = im.copy(); out[..., 3] = im[..., 3] * k
Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), 'RGBA').save(dst, optimize=True)
a = out[..., 3] > 8
ys, xs = np.nonzero(a)
print('box', [round(xs.min() / W, 3), round(ys.min() / H, 3), round((xs.max() + 1) / W, 3), round((ys.max() + 1) / H, 3)])
# сетка занятости 16×16 (как frontGrid)
g = []
for r in range(16):
    row = ''
    for c in range(16):
        cell = out[r * H // 16:(r + 1) * H // 16, c * W // 16:(c + 1) * W // 16, 3]
        row += '#' if (cell > 40).mean() > 0.04 else '.'
    g.append(row)
print('grid', g)
