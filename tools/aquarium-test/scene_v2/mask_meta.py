# per-mask profile (topHi/topLo per 8-px column, backdrop fractions) and a 32x32 occupancy grid
import numpy as np, json
from PIL import Image
meta = json.load(open('final/masks_meta.json'))
H, W = 1440, 2560
for k in ('left', 'right', 'far'):
    im = np.asarray(Image.open(f'final/mask_{k}.png').convert('LA'))[..., 1].astype(np.float32) / 255
    x0, y0, w, h = meta[k]['px']
    step = 8
    hi, lo = [], []
    for c in range(0, w, step):
        col = im[:, c:c + step].max(1)
        rows = np.nonzero(col > 0.05)[0]
        if not len(rows): hi.append(2); lo.append(2); continue
        hi.append(round((y0 + max(0, rows[0] - 2)) / H, 4))
        solid = im[:, c:c + step].min(1) > 0.95
        r = None
        for rr in range(rows[0], h - 16):
            if solid[rr:rr + 16].all(): r = rr; break
        lo.append(round((y0 + (r if r is not None else rows[0])) / H, 4) if r is not None else 2)
    G = 32
    grid = []
    for r in range(G):
        row = ''
        for c in range(G):
            blk = im[int(r * h / G):int((r + 1) * h / G), int(c * w / G):int((c + 1) * w / G)]
            row += '#' if (blk > 0.5).mean() > 0.25 else '.'
        grid.append(row)
    meta[k]['profile'] = {'step': step, 'topHi': hi, 'topLo': lo}
    meta[k]['grid'] = grid
    print(k, len(hi), 'cols', ''.join('#' if x < 2 else '.' for x in hi)[:80])
json.dump(meta, open('final/masks_meta.json', 'w'))
