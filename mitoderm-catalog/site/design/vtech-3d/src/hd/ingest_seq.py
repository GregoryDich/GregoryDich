"""Prepare scroll-sequence frames for the live page (vtech-live.html, its frame engine): for each run the union of the
3D across all its frames (alpha bounding box + a margin) is the run's crop box; every frame is cropped to it and saved
at each tier width (the width the FULL frame would have), plus runs.json with the boxes as fractions of the frame.
The same boxes, passed to render_mac.sh as VT_BORDER, let the Mac render only that region.
usage: python3 -I ingest_seq.py <dir of full frames A_B_NNN.webp> <page seq dir> [tier widths, default: source width]
       python3 -I ingest_seq.py --boxes <dir of full frames>   (print the boxes only, as VT_BORDER strings)
       VT_CROPPED='A:B x0,y0,x1,y1;…' python3 -I ingest_seq.py …   frames rendered with those VT_BORDER regions (render_mac.sh):
       already cropped, the boxes are taken as given"""
import json, os, re, sys
from PIL import Image

RUNS = [('v1-meet', 'v2-why'), ('v2-why', 'v3-inside'), ('v3-inside', 'v4-feel'), ('v4-feel', 'v5-protocol'), ('v5-protocol', 'v6-kit')]
MARGIN = 0.03   # of the frame, around the union: motion blur, DOF halos and the Mac's slightly different noise stay inside


def frames(src, a, b):
    return sorted(f for f in os.listdir(src) if re.fullmatch(rf'{re.escape(a)}_{re.escape(b)}_\d{{3}}\.webp', f))


def union_box(src, fs):
    W = H = None; x0 = y0 = 1e9; x1 = y1 = -1
    for f in fs:
        im = Image.open(f'{src}/{f}'); W, H = im.size
        bb = im.getchannel('A').point(lambda v: 255 if v > 3 else 0).getbbox()
        if bb: x0, y0, x1, y1 = min(x0, bb[0]), min(y0, bb[1]), max(x1, bb[2]), max(y1, bb[3])
    if x1 < 0: return [0, 0, 1, 1]
    return [max(0, x0 / W - MARGIN), max(0, y0 / H - MARGIN), min(1, x1 / W + MARGIN), min(1, y1 / H + MARGIN)]


if sys.argv[1] == '--boxes':
    src = sys.argv[2]
    for a, b in RUNS:
        fs = frames(src, a, b)
        if fs: print(f'{a}:{b}', ','.join(f'{v:.3f}' for v in union_box(src, fs)))
    sys.exit()
src, out = sys.argv[1:3]
GIVEN = {k: [float(v) for v in b.split(',')] for k, b in (x.split() for x in os.environ.get('VT_CROPPED', '').split(';') if x.strip())}
runs = []
for a, b in RUNS:
    fs = frames(src, a, b)
    if not fs: continue
    W, H = Image.open(f'{src}/{fs[0]}').size; box = GIVEN.get(f'{a}:{b}')
    if box: W, H = round(W / (box[2] - box[0])), round(H / (box[3] - box[1]))   # the full frame these crops come from
    else: box = union_box(src, fs)
    tiers = [int(t) for t in sys.argv[3:]] or [W]
    for t in tiers:
        os.makedirs(f'{out}/{t}', exist_ok=True); k = t / W
        for f in fs:
            im = Image.open(f'{src}/{f}').convert('RGBA')
            c = im if f'{a}:{b}' in GIVEN else im.crop((round(box[0] * W), round(box[1] * H), round(box[2] * W), round(box[3] * H)))
            if k != 1: c = c.resize((max(1, round(c.width * k)), max(1, round(c.height * k))), Image.LANCZOS)
            c.save(f'{out}/{t}/{f}', quality=80, alpha_quality=90, method=6)
    runs.append(dict(a=a, b=b, n=len(fs), box=[round(v, 4) for v in box]))
    print(f'{a}>{b}: {len(fs)} frames, box {box}')
json.dump(dict(runs=runs, frame=[W, H]), open(f'{out}/runs.json', 'w'), indent=1)
