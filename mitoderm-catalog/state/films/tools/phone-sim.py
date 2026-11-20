#!/usr/bin/env python3
"""Simulate how frames of the phone film sit on the page: object-fit cover into the viewport, the site header
on top and the caption backdrop below (transparent to opaque over the 24 px above the caption top).

Usage: phone-sim.py <phone film.mp4> <out.jpg> <width>x<height> <header px> <frame>:<caption top px> [...]
The numbers come from film-phone-check.cjs (caption box top) and from a screenshot (header height).
"""
import subprocess, sys, tempfile, os

film, out, size, header = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
W, H = map(int, size.split('x'))
tmp = tempfile.mkdtemp(); files = []
for item in sys.argv[5:]:
    n, top = map(int, item.split(':'))
    raw = os.path.join(tmp, f'r{n}.png'); pic = os.path.join(tmp, f'p{n}.png')
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', film, '-vf',
                    f"select='eq(n,{n})',scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
                    '-frames:v', '1', raw], check=True)
    subprocess.run(['convert', raw,
                    '(', '-size', f'{W}x24', 'gradient:none-#0b0b0c', ')', '-geometry', f'+0+{top - 24}', '-composite',
                    '-fill', '#0b0b0c', '-draw', f'rectangle 0,{top} {W},{H}',
                    '-fill', '#0b0b0c', '-draw', f'rectangle 0,0 {W},{header}',
                    '-fill', '#d8b25a', '-pointsize', '12', '-annotate', f'+8+{H - 10}', f'frame {n}, caption from {top}',
                    pic], check=True)
    files.append(pic)
subprocess.run(['montage', *files, '-tile', f'{len(files)}x1', '-geometry', '+4+4', '-background', '#222', out], check=True)
subprocess.run(['rm', '-rf', tmp])
print(out)
