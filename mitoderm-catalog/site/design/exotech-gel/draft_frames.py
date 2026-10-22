"""Temporary story frames for the EXOTECH GEL page (build-vtech.py --product exotech-gel) while the owner's Firefly key
frames and the Kling transitions are pending: the print packshot's two objects (the box; the jar, cut at its seam into
the lid with the whole lettering and the base) are laid out per screen in the left half and moved between screens, eased.
2D only, a stand-in for structure and copy; the real frames come from video_frames.py and replace these files one for one.
Writes the full 2400×1500 RGBA frames <A>_<B>_NNN.webp (the input of ingest_seq.py) and the transparent key frames
<key>.png that build-vtech.py --keys takes (phone stills, the kit card).
usage: python3 -I draft_frames.py <frames dir> <keys dir> [n=24]"""
import os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.normpath(os.path.join(HERE, '../../../protocols/print/img/exotech-gel.webp'))   # 1065×567, box | jar
W, H = 2400, 1500
JAR_X = 672                       # the jar's left edge in the packshot (its alpha component starts at x 675)
# the seam under «GEL» (y of packshot x): a quartic fitted to the traced line, within 0.4 px; 293 at the rims, 338 mid
SEAM = (-1.08374e-08, 3.76956e-05, -0.0498892, 29.7574, -6403.77)
GOLD = (201, 162, 75)             # #c9a24b, the line's gold: the light in the opened seam
# per screen: box (cx, cy, height, opacity), jar (cx, cy, height, opacity, lid lift as a share of the jar's height)
KEYS = {
    'v1-meet':     ((470, 760, 470, 1), (930, 800, 330, 1, 0)),      # as on the packshot
    'v2-why':      ((400, 700, 360, .3), (720, 780, 560, 1, 0)),     # the jar steps forward, the box in the dark
    'v3-inside':   ((360, 700, 300, 0), (640, 840, 560, 1, .16)),    # the lid lifts over the glowing seam
    'v4-feel':     ((360, 700, 300, 0), (690, 760, 520, 1, 0)),
    'v5-protocol': ((360, 700, 300, 0), (700, 780, 440, 1, 0)),
    'v6-kit':      ((470, 760, 500, 1), (950, 800, 350, 1, 0)),      # the kit, as on the packshot
}
ORDER = list(KEYS)


def sprites():
    im = Image.open(PACK).convert('RGBA'); a = np.asarray(im)
    box = Image.fromarray(np.where(np.arange(im.width)[None, :, None] < JAR_X, a, 0).astype(np.uint8)).crop((0, 0, JAR_X, im.height))
    jar = im.crop((JAR_X, 0, im.width, im.height)); j = np.asarray(jar)
    seam = np.polyval(SEAM, np.arange(jar.width) + JAR_X) + 1                   # per column, through the line's middle
    above = np.arange(jar.height)[:, None] < seam[None, :]
    lid = Image.fromarray(np.where(above[..., None], j, 0).astype(np.uint8))
    base = Image.fromarray(np.where(above[..., None], 0, j).astype(np.uint8))
    bb = jar.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()
    return [s.crop(bb) for s in (lid, base)] + [box.crop(box.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())], seam.max() - bb[1]


def place(canvas, im, cx, cy, h, op, dy=0):
    if op <= 0.002: return
    w = round(im.width * h / im.height); s = im.resize((w, round(h)), Image.LANCZOS)
    if op < 1: s.putalpha(s.getchannel('A').point(lambda v: round(v * op)))
    canvas.alpha_composite(s, (round(cx - w / 2), round(cy - h / 2 + dy)))


def glow(canvas, cx, y, w, h, op):   # the warm light in the opened seam: a soft ellipse
    if op <= 0.002: return
    yy, xx = np.mgrid[:round(h * 3), :round(w)]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h * 1.5) / (h * 1.5))
    al = (np.clip(1 - r, 0, 1) ** 0.8 * 255 * op).astype(np.uint8)
    g = Image.fromarray(np.dstack([np.full(al.shape, c, np.uint8) for c in GOLD] + [al]), 'RGBA')
    canvas.alpha_composite(g, (round(cx - w / 2), round(y - h * 1.5)))


def frame(st, lid, base, box, seam_y):
    (bx, by, bh, bo), (jx, jy, jh, jo, lift) = st
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    place(c, box, bx, by, bh, bo)
    k = jh / base.height   # frame px per packshot px (lid and base are cut from the same jar crop)
    place(c, base, jx, jy, jh, jo)
    gap = lift * jh   # the light fills the opened seam, its middle at the middle of the gap
    glow(c, jx, jy - jh / 2 + seam_y * k - gap * 0.45, base.width * k * 0.96, max(1, gap * 0.5), min(1, lift / 0.06) * jo)
    place(c, lid, jx, jy, jh, jo, -gap)
    return c


def mix(a, b, s):
    return tuple(tuple(x + (y - x) * s for x, y in zip(p, q)) for p, q in zip(a, b))


if __name__ == '__main__':
    out, kdir = sys.argv[1:3]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    os.makedirs(out, exist_ok=True); os.makedirs(kdir, exist_ok=True)
    (lid, base, box), seam_y = sprites()
    for key in ORDER: frame(KEYS[key], lid, base, box, seam_y).save(f'{kdir}/{key}.png')
    for a, b in zip(ORDER, ORDER[1:]):
        for i in range(n):
            t = i / (n - 1); s = t * t * (3 - 2 * t)
            frame(mix(KEYS[a], KEYS[b], s), lid, base, box, seam_y).save(f'{out}/{a}_{b}_{i:03d}.webp', quality=92, alpha_quality=100, method=4)
        print(f'{a}>{b}: {n} frames')
