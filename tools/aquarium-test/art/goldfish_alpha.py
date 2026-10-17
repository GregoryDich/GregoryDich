# Вуаль золотой рыбки: полупрозрачный хвост/плавники (α≈158) → почти непрозрачные (≥ 245 внутри), растушёвка
# только внешние ~4 px. Иначе перекрытия срезов (до 0.5 device px) удваивают α → светлые вертикальные «швы».
import sys
import numpy as np
from PIL import Image
from scipy import ndimage
src, dst = sys.argv[1], sys.argv[2]
im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float32)
a = im[..., 3]
mask = a > 24
dist = ndimage.distance_transform_edt(mask)
ramp = np.clip(dist / 4.0, 0, 1)
target = 247 * ramp
na = np.where(mask, np.maximum(a, target), a)
out = im.copy(); out[..., 3] = na
Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8), 'RGBA').save(dst, optimize=True)
W = a.shape[1]
for x0, x1 in [(0, 150), (150, 300), (300, 450)]:
    s = na[:, x0:x1]; m = s[s > 10]; print(x0, x1, 'median', float(np.median(m)), 'frac<240', round(float((m < 240).mean()), 2))
