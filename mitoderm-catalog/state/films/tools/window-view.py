#!/usr/bin/env python3
"""Show where the phone window of vertical-from-horizontal.py lies on frames of the desktop film.

Usage: window-view.py <desktop film.mp4> <keys.json> <out.jpg> <frame> [<frame> ...]
Each frame is drawn 640 px wide with a ruler every 10% of the width and the window of that frame as a yellow
rectangle, so one can read off where faces and the pack are and whether the window holds them.
"""
import json, subprocess, sys, tempfile, os

film, keys_path, out = sys.argv[1:4]
frames = [int(f) for f in sys.argv[4:]]
keys = json.load(open(keys_path))['keys']

def at(n, col):
    v = keys[0][col]
    for a, b in zip(keys, keys[1:]):
        d = b[col] - a[col]
        if d == 0 or b[0] == a[0]:
            continue
        t = min(1.0, max(0.0, (n - a[0]) / (b[0] - a[0])))
        v += d * t * t * (3 - 2 * t)
    return v

W, H = 640, 360
tmp = tempfile.mkdtemp()
files = []
for n in frames:
    x0, ww = at(n, 1), at(n, 2)
    raw = os.path.join(tmp, f'r{n}.png'); pic = os.path.join(tmp, f'f{n}.png')
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', film, '-vf', f"select='eq(n,{n})',scale={W}:{H}",
                    '-frames:v', '1', raw], check=True)
    draw = []
    for p in range(10, 100, 10):
        x = round(W * p / 100)
        draw += ['-stroke', '#ffffff80', '-strokewidth', '1', '-draw', f'line {x},0 {x},{H}',
                 '-stroke', 'none', '-fill', 'white', '-pointsize', '11', '-annotate', f'+{x + 2}+11', str(p)]
    a, b = round(W * x0 / 100), round(W * (x0 + ww) / 100)
    draw += ['-stroke', '#ffd400', '-strokewidth', '2', '-fill', 'none', '-draw', f'rectangle {a},1 {b},{H - 2}',
             '-stroke', 'none', '-fill', '#ffd400', '-pointsize', '13', '-annotate', f'+{a + 4}+{H - 8}',
             f'frame {n}: {x0:.1f}..{x0 + ww:.1f}%']
    subprocess.run(['convert', raw, *draw, pic], check=True)
    files.append(pic)
cols = 4 if len(files) > 4 else len(files)
subprocess.run(['montage', *files, '-tile', f'{cols}x', '-geometry', '+3+3', '-background', '#222', out], check=True)
subprocess.run(['rm', '-rf', tmp])
print(out)
