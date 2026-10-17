# Сетки занятости альфы колоний (32×32) и рамки альфы — в ориентации ЭКРАНА (с учётом flip) для scene.corals.
# usage: python3.13 -I coral_grids.py /home/user/GregoryDich/aquarium  [--write]
import sys, re, json
import numpy as np
from PIL import Image
root = sys.argv[1]; write = '--write' in sys.argv
p = root + '/scene/scene.js'
s = open(p, encoding='utf-8').read()
G = 32
def grid_of(a):
    h, w = a.shape
    rows = []
    for j in range(G):
        r = ''
        for i in range(G):
            c = a[j*h//G:(j+1)*h//G, i*w//G:(i+1)*w//G]
            # ячейка «занята», если ≥ 6% пикселей с альфой ≥ 0.5 (тонкие веточки — не стена)
            r += '#' if (c >= 128).mean() >= 0.06 else '.'
        rows.append(r)
    return rows
out = []
def fix(m):
    line = m.group(0)
    cid = re.search(r'coral: "([a-z_]+)"', line).group(1)
    flip = re.search(r'flip: (true|false)', line).group(1) == 'true'
    a = np.asarray(Image.open(f'{root}/scene/corals/{cid}.png').convert('RGBA'))[:, :, 3]
    if flip: a = a[:, ::-1]
    ys, xs = np.nonzero(a >= 24)
    h, w = a.shape
    box = [round(float(xs.min())/w, 4), round(float(ys.min())/h, 4), round(float(xs.max()+1)/w, 4), round(float(ys.max()+1)/h, 4)]
    g = grid_of(a)
    occ = sum(r.count('#') for r in g) / (G*G)
    out.append((cid, flip, box, round(occ, 3)))
    line = re.sub(r', box: \[[^\]]*\], grid: \[[^\]]*\]', '', line)
    return line[:-2].rstrip() + ', box: ' + json.dumps(box) + ', grid: ' + json.dumps(g, separators=(', ', ': ')) + ' },'
s2 = re.sub(r'^\s*\{ coral: "[a-z_]+".*\},$', fix, s, flags=re.M)
for o in out: print(*o)
if write:
    open(p, 'w', encoding='utf-8').write(s2); print('written')
