#!/usr/bin/env python3
"""Build the phone (9:16) film from the desktop (16:9) film with a moving window.

The desktop frames keep both people and the pack in the left 60% (the right third is left free for the
caption), so a window about half the frame wide holds everything that matters. The window is scaled to the
full phone width and placed in the upper part of a 1080x1920 canvas. Above and below it lies a blurred mirror
image of the window itself, so the fill continues what is at the window's edge (the table, a sweater, the wall);
on the page the fill sits under the site header and under the caption backdrop, and on tall phones a strip of it
shows between the window and the caption.

Sizes: the window of width w% is 31.77/(w/100) percent of the canvas high (44.5% -> 71.4%, 48% -> 66.2%,
54% -> 58.8%, 58% -> 54.8%). On the page the header hides the canvas down to about 13% (390x664) and the caption
starts at 78% (64-71% in the first and the last chapter), see phone-sim.py.

Usage: vertical-from-horizontal.py <desktop film.mp4> <output.mp4> <keys.json> [--frames N]
keys.json: {"keys": [[frame, x0_percent, width_percent, top_percent], ...]}  (frame order; eased in between)
"""
import json, subprocess, sys

src, out, keys_path = sys.argv[1:4]
limit = int(sys.argv[sys.argv.index('--frames') + 1]) if '--frames' in sys.argv else None
keys = json.load(open(keys_path))['keys']
SW, SH, OW, OH = 1912, 1080, 1080, 1920

def curve(col):
    """v0 + sum of eased steps between consecutive keys, as an ffmpeg expression in n."""
    expr = f'{keys[0][col]}'
    for (a, *va), (b, *vb) in zip(keys, keys[1:]):
        d = vb[col - 1] - va[col - 1]
        if abs(d) < 1e-9 or b == a:
            continue
        t = f'clip((n-{a})/{b - a},0,1)'
        expr += f'+({d})*({t}*{t}*(3-2*{t}))'
    return expr

X0 = f'(({curve(1)})*{SW}/100)'      # window left edge, source px
WW = f'(({curve(2)})*{SW}/100)'      # window width, source px
YT = f'(({curve(3)})*{OH}/100)'      # top of the window on the canvas, px
S = f'({OW}/{WW})'                   # scale factor source -> canvas
mask = out + '.mask.png'
subprocess.run(['convert', '-size', f'{SW}x{SH}', 'xc:white',
                '(', '-size', f'{SW}x36', 'gradient:black-white', ')', '-gravity', 'north', '-composite',
                '(', '-size', f'{SW}x36', 'gradient:white-black', ')', '-gravity', 'south', '-composite',
                mask], check=True)
scale = f"scale=w='2*trunc(iw*{S}/2)':h='2*trunc(ih*{S}/2)':eval=frame:flags=lanczos"
place = f"x='-{X0}*{S}'"
graph = (
    f"[0:v]split=4[a][b][c][d];color=c=black:s={OW}x{OH}:r=24[k];"
    # the fill: the window itself, with a mirrored copy above and below it, strongly blurred
    f"[b]{scale}[bs];[c]vflip,{scale}[f1];[d]vflip,{scale}[f2];"
    f"[k][bs]overlay={place}:y='{YT}':eval=frame:shortest=1[k1];"
    f"[k1][f1]overlay={place}:y='{YT}-h':eval=frame:shortest=1[k2];"
    f"[k2][f2]overlay={place}:y='{YT}+h':eval=frame:shortest=1[k3];"
    f"[k3]scale={OW // 8}:{OH // 8},boxblur=10:3,scale={OW}:{OH}:flags=bicubic,eq=brightness=-0.02[bg];"
    # the window, sharp, with soft top and bottom edges
    f"[1:v]format=gray[m];[a][m]alphamerge[fa];[fa]{scale}[fg];"
    f"[bg][fg]overlay={place}:y='{YT}':eval=frame:shortest=1,format=yuv420p,setsar=1[v]"
)
cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', src, '-loop', '1', '-framerate', '24', '-i', mask,
       '-filter_complex', graph, '-map', '[v]']
if limit:
    cmd += ['-frames:v', str(limit)]
cmd += ['-an', '-c:v', 'libx264', '-preset', 'slower', '-tune', 'film', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
        '-crf', '22', '-r', '24', '-g', '12', '-keyint_min', '12', '-sc_threshold', '0', '-movflags', '+faststart', out]
subprocess.run(cmd, check=True)
subprocess.run(['rm', '-f', mask])
n = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries',
                    'stream=nb_read_frames,width,height', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout.strip()
print('width,height,frames =', n)
