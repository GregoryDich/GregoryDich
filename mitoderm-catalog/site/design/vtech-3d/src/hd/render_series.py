"""Render the V-TECH keyframe series with vtech_scene.py: each shot as a full frame composed on the line's smoke, plus
its Figma layers (one part each, cropped to alpha; positions in <shot>-layers.json, CSS px of the 1440x900 screen).
usage: python3 render_series.py <python with bpy> <tex dir> <out dir> [shot ...]"""
import json, os, subprocess, sys
from PIL import Image

BPY, TEX, OUT = sys.argv[1:4]; ONLY = sys.argv[4:]
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.dirname(os.path.dirname(HERE))   # site/design/vtech-3d
PARTS = {'v1-meet': ['box'], 'v2-why': ['box', 'skin'], 'v3-inside': ['box', 'tray', 'vials', 'drops'],
         'v4-feel': ['box', 'skin', 'pouches'], 'v5-protocol': ['skin', 'vials', 'drops', 'pouches'],
         'v6-kit': ['box', 'tray', 'vials', 'pouches'], 'kit-hd': [], 'm1-meet': [], 'm4-feel': []}
GAIN = {'v4-feel': 1.3}   # smoke brightness per screen: S4 the brightest gold of the page (storyboard); S5 at the series level


def render(shot, out, width, samples, part=None):
    subprocess.run([BPY, f'{HERE}/vtech_scene.py', TEX, out, shot, str(width), str(samples)] + ([part] if part else []),
                   check=True, capture_output=True)


os.makedirs(OUT, exist_ok=True)
for shot, parts in PARTS.items():   # resumable: a finished frame or layer is kept (a run may be stopped at its time limit)
    if ONLY and shot not in ONLY: continue
    phone = shot.startswith('m'); width = 780 if phone else 2800 if shot == 'kit-hd' else 2880
    full = f'{OUT}/{shot}.png'
    if not os.path.exists(full): render(shot, full + '.tmp.png', width, 256); os.replace(full + '.tmp.png', full)   # OIDN: 256 is clean
    if shot != 'kit-hd':   # the purchase card keeps its transparent ground; a phone frame takes a portrait slice of the plume
        subprocess.run(['python3', f'{HERE}/compose.py', full, f'{D}/layers/vt-bg-wide.jpg', f'{OUT}/{shot}.jpg', str(GAIN.get(shot, 1)),
                        '0.74,0.5' if phone else '0.5,0.5'], check=True, capture_output=True)
    lj = f'{OUT}/{shot}-layers.json'; layers = json.load(open(lj)) if os.path.exists(lj) else {}
    for part in parts:
        key, f = f'{shot}-{part}', f'{OUT}/{shot}-{part}.png'
        if key in layers and os.path.exists(f): continue
        render(shot, f, width, 160, part)
        im = Image.open(f).convert('RGBA'); box = im.getchannel('A').point(lambda v: 255 if v > 2 else 0).getbbox()
        im.crop(box).save(f, optimize=True)
        layers[key] = [box[0] / 2, box[1] / 2, (box[2] - box[0]) / 2, (box[3] - box[1]) / 2]
        json.dump(layers, open(lj, 'w'), indent=1)   # after every layer, so a stopped run keeps its positions
    json.dump(layers, open(lj, 'w'), indent=1)
    print(shot, 'done', flush=True)
