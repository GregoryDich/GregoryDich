#!/usr/bin/env python3
"""Finds the pack in the first frame of every product film and draws it on a sheet with a 10 % grid.

Why: on the home page a chosen product lifts off the collection and comes down onto its own place in the first
frame of its film (codex-site/mitoderm/pilot/film-entry.ts holds those places as fractions of the frame). In a first
frame the pack is sharp and the room behind it is soft, so the pack is the largest patch of fine detail.

usage: first-frame-boxes.py <dir with the frames of first-frames.cjs> <desktop|mobile> <out sheet.jpg>
prints {slug: [left, top, right, bottom]} and writes the same next to the sheet (<out sheet.jpg>.json).
The sheet must be looked at: a group (a box with ampoules), a table edge or the edge of the phone window can widen
the found box - then read the box off the grid. For a film cut from the wide one by a window
(state/films/<slug>/vertical-keys.json, first key [frame, left %, width %, top %]) the phone box follows from the
desktop box: x = (X - left) / width, y = top + Y * 0.3177 / width. Needs ImageMagick.
"""
import json, os, re, subprocess, sys, tempfile
d, kind, out = sys.argv[1:4]
SLUGS = ['exo-nad', 'exocell-mask', 'exotech-gel', 'exosignal-hair', 'exosignal-spray', 'micro-boost-10', 'cell-renew-1-5',
         'cellular-age-defense-2-5', 'derma-recovery-cream', 'mitopen', 'mitoscan', 'mitotech-cell-booster']
cols, cell_w = (4, 640) if kind == 'desktop' else (6, 330)
work = tempfile.mkdtemp(prefix='detect-')
def run(*a):
    return subprocess.run([str(x) for x in a], capture_output=True, text=True, check=True).stdout
found, cells = {}, []
for slug in SLUGS:
    src = os.path.join(d, '%s-%s.png' % (slug, kind))
    W, H = map(int, run('identify', '-format', '%w %h', src).split())
    w, h = W // 4, H // 4
    text = run('convert', src, '-colorspace', 'Gray', '-resize', '%dx%d!' % (w, h), '-edge', '1', '-blur', '0x1.5',
               '-threshold', '11%', '-shave', '3x3', '-bordercolor', 'black', '-border', '3',
               '-morphology', 'Close', 'Disk:5', '-define', 'connected-components:verbose=true',
               '-define', 'connected-components:area-threshold=40', '-connected-components', '8', 'null:')
    best = None
    for line in text.splitlines():
        m = re.match(r'\s*\d+: (\d+)x(\d+)\+(\d+)\+(\d+) [\d.,]+ (\d+) (.*)', line)
        if not m:
            continue
        bw, bh, bx, by, area, colour = int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), m[6]
        if 'white' not in colour and '255' not in colour:
            continue
        if best is None or area > best[4]:
            best = (bx, by, bw, bh, area)
    box = (best[0] / w, best[1] / h, (best[0] + best[2]) / w, (best[1] + best[3]) / h) if best else (0, 0, 1, 1)
    found[slug] = [round(v, 4) for v in box]
    cw, ch = cell_w, round(cell_w * H / W)
    draw = []
    for i in range(1, 10):
        colour = 'yellow' if i == 5 else 'white'
        draw += ['-stroke', colour, '-strokewidth', '1', '-draw', 'line %d,0 %d,%d' % (cw * i / 10, cw * i / 10, ch),
                 '-draw', 'line 0,%d %d,%d' % (ch * i / 10, cw, ch * i / 10)]
    draw += ['-fill', 'none', '-stroke', '#ff003c', '-strokewidth', '3', '-draw',
             'rectangle %d,%d %d,%d' % (box[0] * cw, box[1] * ch, box[2] * cw, box[3] * ch)]
    cell = os.path.join(work, slug + '.png')
    run('convert', src, '-resize', '%dx%d!' % (cw, ch), *draw, '-stroke', 'none', '-fill', 'white', '-undercolor', '#000c',
        '-pointsize', '13', '-gravity', 'south', '-annotate', '+0+2', ' %s %s ' % (slug, found[slug]), cell)
    cells.append(cell)
run('montage', *cells, '-tile', '%dx' % cols, '-geometry', '+3+3', '-background', '#141414', out)
json.dump(found, open(out + '.json', 'w'), indent=1)
print(json.dumps(found))
for name in os.listdir(work):
    os.remove(os.path.join(work, name))
os.rmdir(work)
