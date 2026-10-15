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
GAIN = {'v4-feel': 1.15, 'v5-protocol': 0.85}   # smoke brightness per screen (S4 brightest)


def render(shot, out, width, samples, part=None):
    subprocess.run([BPY, f'{HERE}/vtech_scene.py', TEX, out, shot, str(width), str(samples)] + ([part] if part else []),
                   check=True, capture_output=True)


os.makedirs(OUT, exist_ok=True)
for shot, parts in PARTS.items():
    if ONLY and shot not in ONLY: continue
    phone = shot.startswith('m'); width = 780 if phone else 2800 if shot == 'kit-hd' else 2880
    full = f'{OUT}/{shot}.png'; render(shot, full, width, 384)
    if shot != 'kit-hd':   # the purchase card keeps its transparent ground
        bg = f'{D}/m7-bg.jpg' if phone else f'{D}/layers/vt-bg-wide.jpg'
        subprocess.run(['python3', f'{HERE}/compose.py', full, bg, f'{OUT}/{shot}.jpg', str(GAIN.get(shot, 1))], check=True, capture_output=True)
    layers = {}
    for part in parts:
        f = f'{OUT}/{shot}-{part}.png'; render(shot, f, width, 256, part)
        im = Image.open(f).convert('RGBA'); box = im.getchannel('A').point(lambda v: 255 if v > 2 else 0).getbbox()
        im.crop(box).save(f'{OUT}/{shot}-{part}.png', optimize=True)
        layers[f'{shot}-{part}'] = [box[0] / 2, box[1] / 2, (box[2] - box[0]) / 2, (box[3] - box[1]) / 2]
    json.dump(layers, open(f'{OUT}/{shot}-layers.json', 'w'), indent=1)
    print(shot, 'done', flush=True)
