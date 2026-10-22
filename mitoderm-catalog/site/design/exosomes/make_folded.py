"""The owner's folded exosome (22/10, ref-folded-2210.webp, 1024 px with alpha) as cell sprites f01…f04 next to the
glassy c01…c10 in design/vtech-3d/cells: mirrored and turned so the four differ, then the same three focus levels as
the glassy cells (sharp, soft, bokeh) by cells_scene.py post. build-vtech.py mixes them into the exosome field.
usage: python3 make_folded.py"""
import os, subprocess, sys, tempfile
from PIL import Image

H = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = os.path.join(H, 'ref-folded-2210.webp'), os.path.normpath(os.path.join(H, '..', 'vtech-3d', 'cells'))
POST = os.path.normpath(os.path.join(H, '..', 'vtech-3d', 'src', 'hd', 'cells_scene.py'))
VARIANTS = {'f01': (False, 0), 'f02': (True, -28), 'f03': (False, 35), 'f04': (True, 62)}   # mirror, turn (degrees)

ref = Image.open(SRC).convert('RGBA')
with tempfile.TemporaryDirectory() as tmp:
    for name, (mirror, turn) in VARIANTS.items():
        im = ref.transpose(Image.FLIP_LEFT_RIGHT) if mirror else ref
        if turn: im = im.rotate(turn, resample=Image.BICUBIC)   # the sphere stays inside the square at any turn
        src = os.path.join(tmp, name + '.png'); im.save(src)
        k = Image.new('RGBA', im.size, (0, 0, 0, 255)); k.alpha_composite(im); k.convert('RGB').save(os.path.join(tmp, name + '-k.png'))
        subprocess.run([sys.executable, POST, 'post', src, os.path.join(OUT, name)], check=True)
