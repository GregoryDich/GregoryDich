import numpy as np, sys
from PIL import Image
m = np.load('out/masks_full.npz')
M = 1 - (1 - m['left']) * (1 - m['right']) * (1 - m['far'])
fr = np.asarray(Image.open(sys.argv[1]), np.float32) / 255
bg = np.zeros_like(fr); bg[...] = (1.0, 0.0, 1.0)
# checker so it reads as "a fish behind"
yy, xx = np.mgrid[0:fr.shape[0], 0:fr.shape[1]]
chk = ((yy // 16 + xx // 16) % 2).astype(np.float32)
bg = bg * (0.6 + 0.4 * chk[..., None])
out = M[..., None] * fr + (1 - M[..., None]) * bg
crops = [(1060, 380, 600, 500), (1600, 120, 600, 420), (2050, 100, 510, 420), (1350, 330, 520, 420), (500, 0, 640, 380), (1020, 860, 640, 580)]
tiles = []
for (x, y, w, h) in crops:
    a = (np.clip(out[y:y+h, x:x+w], 0, 1) * 255).astype(np.uint8)
    b = (np.clip(fr[y:y+h, x:x+w], 0, 1) * 255).astype(np.uint8)
    t = np.concatenate([b, a], 1)
    tiles.append(Image.fromarray(t))
Wt = max(t.width for t in tiles); Ht = sum(t.height for t in tiles) + 8 * len(tiles)
sheet = Image.new('RGB', (Wt, Ht), (20, 20, 20)); y = 0
for t in tiles: sheet.paste(t, (0, y)); y += t.height + 8
sheet.save(sys.argv[2])
