"""Transition clips (Kling: first frame → last frame) → the frame engine's full frames A_B_NNN.webp in RGBA, the input of
ingest_seq.py (crop boxes, tiers, runs.json). The clips start and end on the owner's Firefly key frames, shot on pure
black with the product in the left half (2400×1500): black is keyed to alpha by brightness and un-premultiplied, so no
dark fringe is left around the gold; dark parts of the product enclosed by its lit edges (the cube's black faces) stay
opaque. A black part with no lit outline keys out like the backdrop; on the page's near-black ground (#0a0a0b) that is
invisible, but the Firefly keys should keep a rim light on black surfaces. Keep the product ≥ 10% from the edges: a
16:9 clip is cover-cropped to 16:10. The first frame is key A and the last key B exactly (keyed the same way), and the
first and last EASE frames blend into them, so neighbouring runs meet without a jump, as the Blender runs do.
usage: python3 -I video_frames.py <clip.mp4 | -> <key A image> <key B image> <A name> <B name> <out dir> [n=40]
       clip '-': no clip yet, a cross-dissolve from A to B (temporary frames, the same files the clip will replace)"""
import os, sys
import numpy as np
from PIL import Image

W, H = 2400, 1500
LO, HI = 0.05, 0.16   # brightness (max of R, G, B) where the black backdrop ends and the product is fully opaque
EASE = 4              # frames at each end blended into the exact key
CLOSE = 32            # px: the product's lit parts are closed over gaps this size before its holes are filled
NEAR = 64             # px around the product's silhouette where dim light (glow, gel) is kept; beyond it is backdrop


def cover(im):   # any key or clip frame → 2400×1500, cover-fitted and centred
    im = im.convert('RGB'); k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def keyed(im):   # RGB on black → premultiplied RGBA as float arrays (colour·alpha, alpha)
    from scipy import ndimage
    rgb = np.asarray(cover(im)).astype(np.float32) / 255
    v = rgb.max(axis=2); t = np.clip((v - LO) / (HI - LO), 0, 1); a = t * t * (3 - 2 * t)
    # black parts of the product (the cube's black faces) are as dark as the backdrop. The product's silhouette is its lit
    # parts closed over gaps up to ~2·CLOSE px (thin, broken edge highlights) with the holes filled: everything inside
    # it is opaque, the backdrop and wider gaps between objects stay keyed. Computed at 1/4 size for speed.
    q = Image.fromarray(((v > HI) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BOX)
    lit = np.asarray(q) > 0; r = CLOSE // 4
    disk = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
    sil = ndimage.binary_fill_holes(ndimage.binary_closing(np.pad(lit, r), disk)[r:-r, r:-r])
    # a generated "black" backdrop is rarely pure black (a faint gradient, compression noise): away from the product it
    # is backdrop whatever its level, so alpha is kept only within NEAR px of the silhouette (glow, gel, soft edges)
    rn = NEAR // 4; near = ndimage.binary_dilation(sil, np.hypot(*np.mgrid[-rn:rn + 1, -rn:rn + 1]) <= rn)
    up = lambda m: np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
    a = np.maximum(a, np.clip((up(sil) - 0.5) * 4 + 0.5, 0, 1)) * up(near)
    return rgb * up(near)[..., None], a   # the source is product·alpha over black: its colour is already premultiplied


def to_image(pm, a):
    rgb = np.where(a[..., None] > 1 / 510, np.clip(pm / np.maximum(a[..., None], 1e-4), 0, 1), 0)   # black where a rounds to 0
    return Image.fromarray((np.dstack([rgb, a]) * 255 + 0.5).astype(np.uint8), 'RGBA')


def clip_frames(path, n):   # n frames evenly spaced over the clip, first and last included
    import imageio_ffmpeg
    reader = imageio_ffmpeg.read_frames(path); meta = next(reader); w, h = meta['size']
    allf = [Image.frombytes('RGB', (w, h), f) for f in reader]
    return [allf[round(i * (len(allf) - 1) / (n - 1))] for i in range(n)]


if __name__ == '__main__':
    clip, ka, kb, A, B, out = sys.argv[1:7]
    n = int(sys.argv[7]) if len(sys.argv) > 7 else 40
    os.makedirs(out, exist_ok=True)
    pa, aa = keyed(Image.open(ka)); pb, ab = keyed(Image.open(kb))
    for i, im in enumerate(clip_frames(clip, n) if clip != '-' else [None] * n):
        t = i / (n - 1)
        if im is None:   # cross-dissolve, eased
            s = t * t * (3 - 2 * t); pm, a = pa * (1 - s) + pb * s, aa * (1 - s) + ab * s
        else:
            pm, a = keyed(im)
            wa = max(0.0, 1 - i / EASE) if EASE else 0.0; wb = max(0.0, 1 - (n - 1 - i) / EASE) if EASE else 0.0
            if wa: pm, a = pm * (1 - wa) + pa * wa, a * (1 - wa) + aa * wa
            if wb: pm, a = pm * (1 - wb) + pb * wb, a * (1 - wb) + ab * wb
        to_image(pm, a).save(f'{out}/{A}_{B}_{i:03d}.webp', quality=92, alpha_quality=100, method=4)
    print(f'{A}>{B}: {n} frames', 'from ' + os.path.basename(clip) if clip != '-' else 'cross-dissolve')
