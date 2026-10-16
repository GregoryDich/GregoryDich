"""Render a scroll sequence between two screens with vtech_scene.py ('A>B@t' frames), as alpha WebP for the live page.
usage: python3 render_seq.py <python with bpy> <tex dir> <out dir> <A> <B> [frames=40] [width=1600] [samples=128]
Frames are <out>/<A>_<B>_000.webp … (the page lays them over the smoke background)."""
import os, subprocess, sys
from PIL import Image

BPY, TEX, OUT, A, B = sys.argv[1:6]
N = int(sys.argv[6]) if len(sys.argv) > 6 else 40
W = int(sys.argv[7]) if len(sys.argv) > 7 else 1600
SPP = int(sys.argv[8]) if len(sys.argv) > 8 else 128
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(OUT, exist_ok=True)
for i in range(N):
    f = f'{OUT}/{A}_{B}_{i:03d}'
    if os.path.exists(f + '.webp'): continue   # resumable: the container may restart mid-run
    subprocess.run([BPY, f'{HERE}/vtech_scene.py', TEX, f + '.png', f'{A}>{B}@{i / (N - 1):.4f}', str(W), str(SPP)], check=True, capture_output=True)
    Image.open(f + '.png').convert('RGBA').save(f + '.webp', quality=86, method=6)
    os.remove(f + '.png'); print(i, flush=True)
