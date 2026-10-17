# depth grid under each colony / prop footprint (alpha > 0.5), in backdrop space
import json, sys, numpy as np
from PIL import Image
sys.path.insert(0, 'scripts')
from probe import depthAtB
sc = json.load(open(sys.argv[1])); cat = {c['id']: c for c in sc['_catalog']}
R = '/home/user/GregoryDich/aquarium/'
IW, IH = 2560, 1440
def stats(img, x0, y0, w, h):
    a = np.asarray(img.resize((max(2, int(w * 64)), max(2, int(h * 64 * IH / IW)))).getchannel('A')) > 128
    ys, xs = np.nonzero(a)
    if not len(ys): return None
    bx = x0 + (xs + 0.5) / a.shape[1] * w; by = y0 + (ys + 0.5) / a.shape[0] * h
    ok = (by < 1.0) & (bx > 0) & (bx < 1)
    zz = np.array([depthAtB(x, y) for x, y in zip(bx[ok], by[ok])])
    return (round(float(zz.min()), 2), round(float(np.percentile(zz, 10)), 2), round(float(np.median(zz)), 2)) if len(zz) else None
for c in sc['corals']:
    e = cat[c['coral']]; im = Image.open(R + e['image'])
    h = c['scale']; w = h * im.width / im.height * IH / IW
    u, v = e['base']; u = 1 - u if c.get('flip') else u
    if c.get('flip'): im = im.transpose(Image.FLIP_LEFT_RIGHT)
    x0, y0 = c['bx'] - u * w, c['byBase'] - v * h
    print(f"{c['coral']:20s} z {c['z']:.2f}  grid min/p10/median under it: {stats(im, x0, y0, w, h)}  bbox bx {x0:.3f}..{x0+w:.3f} by {y0:.3f}..{y0+h:.3f}")
for p in sc['props']:
    im = Image.open(R + p['src']); w = p['bw']; h = w * im.height / im.width * IW / IH
    x0, y0 = p['bx'] - w / 2, p['byBottom'] - h
    print(f"{p['id']:20s} z {p['z']:.2f}  grid: {stats(im, x0, y0, w, h)}  bbox bx {x0:.3f}..{x0+w:.3f} by {y0:.3f}..{y0+h:.3f}")
