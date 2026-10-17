# depth-sorted demo at 1:1 (2560x1440, aspect 1.78): fish behind pillar edges / far reef / inside the tree crown
import json, sys, numpy as np
from PIL import Image
sys.path.insert(0, 'scripts')
R = '/home/user/GregoryDich/aquarium/'
sc = json.load(open(sys.argv[1])); theme = sys.argv[3] if len(sys.argv) > 3 else 'day'
cat = {c['id']: c for c in sc['_catalog']}
W, H = 2560, 1440
poster = Image.open(R + sc['backdrop'][theme]['poster']).convert('RGBA')
fog = np.array([int(sc['themes'][theme]['fog'][i:i + 2], 16) for i in (1, 3, 5)], np.float32)
fogK = sc['camera']['fogSigma']
HB, CX = sc['camera']['horizonBy'] * H, sc['camera']['horizonBx'] * W
def fish_img(fid, Lpx, z, flip=False):
    im = Image.open(R + f'fish/{fid}.png').convert('RGBA')
    L = Lpx / z; im = im.resize((int(L), int(L * im.height / im.width)), Image.LANCZOS)
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    a = np.asarray(im, np.float32); fa = 0.85 * (1 - np.exp(-fogK * (z - 1)))
    a[..., :3] = a[..., :3] * (1 - fa) + fog * fa
    return Image.fromarray(a.astype(np.uint8), 'RGBA')
# fish: (id, bx, by of centre, z, length px at z=1, flip)
FISH = [('regal_angelfish', 0.470, 0.560, 2.00, 190, True),   # half behind the fire-coral edge of the left pillar
        ('moorish_idol', 0.585, 0.392, 2.42, 260, False),     # drifting behind the far reef's top
        ('flame_angel', 0.688, 0.415, 1.95, 170, False),      # behind the right pillar's spur
        ('yellow_tang', 0.22, 0.73, 1.14, 190, True),         # inside the soft-tree crown (behind the tree, in front of the fan)
        ('goldfish', 0.36, 0.42, 1.30, 230, False),           # open water in front of the left pillar (not hidden)
        ]
items = []
for f in FISH: items.append(('fish', f[3], f))
for o in sc['occluders']: items.append(('occ', o['z'], o))
for c in sc['corals']: items.append(('coral', c['z'], c))
items.sort(key=lambda t: -t[1])
canvas = poster.copy()
P = np.asarray(poster, np.float32)
for kind, z, d in items:
    if kind == 'fish':
        fid, bx, by, zz, Lp, fl = d
        im = fish_img(fid, Lp, zz, fl)
        canvas.alpha_composite(im, (int(bx * W - im.width / 2), int(by * H - im.height / 2)))
    elif kind == 'occ':
        m = np.asarray(Image.open(R + d['mask']).convert('LA'), np.float32)[..., 1] / 255
        x, y, w, h = d['px']
        C = np.asarray(canvas, np.float32)
        C[y:y + h, x:x + w, :3] = m[..., None] * P[y:y + h, x:x + w, :3] + (1 - m[..., None]) * C[y:y + h, x:x + w, :3]
        canvas = Image.fromarray(C.astype(np.uint8), 'RGBA')
    else:
        e = cat[d['coral']]; im = Image.open(R + e['image']).convert('RGBA')
        hh = d['scale'] * H; ww = hh * im.width / im.height; u, v = e['base']
        if d.get('flip'): im = im.transpose(Image.FLIP_LEFT_RIGHT); u = 1 - u
        im = im.resize((int(ww), int(hh)), Image.LANCZOS)
        a = np.asarray(im, np.float32); g = d.get('grade', {}); a[..., :3] *= g.get('shade', 1); hz = g.get('haze', 0)
        a[..., :3] = a[..., :3] * (1 - hz) + fog * hz
        canvas.alpha_composite(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'), (int(d['bx'] * W - u * ww), int(d['byBase'] * H - v * hh)))
canvas = canvas.convert('RGB'); canvas.save(sys.argv[2] + '_full.png')
crops = [(1000, 640, 520, 360), (1300, 500, 520, 360), (1580, 480, 440, 300), (330, 860, 520, 360), (720, 450, 520, 300)]
tiles = [canvas.crop((x, y, x + w, y + h)).resize((w, h)) for x, y, w, h in crops]
sheet = Image.new('RGB', (sum(t.width for t in tiles[:3]) + 20, max(t.height for t in tiles[:3]) * 2 + 10), (20, 20, 20))
x = 0
for t in tiles[:3]: sheet.paste(t, (x, 0)); x += t.width + 10
x = 0
for t in tiles[3:]: sheet.paste(t, (x, 370)); x += t.width + 10
sheet.save(sys.argv[2] + '_crops.png'); print('ok')
