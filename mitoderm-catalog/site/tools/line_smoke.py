"""The smoke background of a line without its own render: the gold V-TECH smoke (design/vtech-3d/layers/vt-bg-wide.jpg)
recoloured to the line's colour from design-rules.md («Сайт v2 — палитра по линейкам»). Each pixel keeps the smoke's
brightness (Rec. 709 luma) and takes the line's hue: out = luma / luma(colour) × colour × 0.85, so the smoke weighs the
same on the page in every line and the dust specks stay where they were. Written to design/lines/<line>-smoke.jpg,
which build-vtech.py takes for that line's pages; the deep plate behind the exosome cells (vtech-3d/cells/plate.webp,
violet) the same way to <line>-plate.webp, for the pages with the owner's folded exosomes.
usage: python3 -I line_smoke.py   (all lines below)"""
import os
import numpy as np
from PIL import Image

SITE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
LINES = {'BIOSPICULE': (0x1E, 0x46, 0x34),   # green
         'PEELING': (0xD8, 0xC4, 0x8A),      # champagne gold
         'DEVICES': (0xD9, 0xD4, 0xCC)}      # silver (the devices' champagne metal is the products' own)
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)

os.makedirs(os.path.join(SITE, 'design/lines'), exist_ok=True)
for src_path, name, save in (('design/vtech-3d/layers/vt-bg-wide.jpg', 'smoke.jpg', dict(quality=90)),
                             ('design/vtech-3d/cells/plate.webp', 'plate.webp', dict(quality=82, method=6))):
    y = np.asarray(Image.open(os.path.join(SITE, src_path)).convert('RGB')).astype(np.float32) @ LUMA
    for line, rgb in LINES.items():
        c = np.array(rgb, np.float32)
        out = np.clip(y[..., None] / float(c @ LUMA) * c * 0.85, 0, 255).astype(np.uint8)
        path = os.path.join(SITE, 'design/lines', f'{line.lower()}-{name}')
        Image.fromarray(out).save(path, **save)
        print(path, out.shape[1], 'x', out.shape[0])
