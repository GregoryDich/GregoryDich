# PIL emulation of the engine's backdrop mapping (bgMap) + foreground corals + props, day/night posters.
#   python3.13 -I scripts/preview.py scene.json OUTPREFIX [aspects] [--debug]
import json, sys, math
import numpy as np
from PIL import Image, ImageDraw
REPO = '/home/user/GregoryDich/aquarium/'
sc = json.load(open(sys.argv[1])); outp = sys.argv[2]
aspects = [float(a) for a in (sys.argv[3].split(',') if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else ['1.54', '1.6', '1.78', '2.33'])]
DEBUG = '--debug' in sys.argv
import os
HCSS = int(os.environ.get("HCSS", "1000"))
B = sc['backdrop']; IW, IH = B['w'], B['h']
cat = {c['id']: c for c in sc['_catalog']}
_cache = {}
def load(path):
    if path not in _cache: _cache[path] = Image.open(REPO + path).convert('RGBA')
    return _cache[path]
def srgb2lin(x): return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
def lin2srgb(x): return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - 0.055)
def hexrgb(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
def layout(A):
    H = HCSS; W = int(round(A * H))
    s = max(W / IW, H / IH) * B.get('zoom', 1.0)
    dw, dh = IW * s, IH * s
    dx = (W - dw) / 2
    ay = B.get('anchorY', 1.0)
    dy = -(dh - H) * ay
    return W, H, dict(s=s, dw=dw, dh=dh, dx=dx, dy=dy)
def bg(m, bx, by): return m['dx'] + bx * m['dw'], m['dy'] + by * m['dh']
def grade(img, theme, g, glow=None):
    """Canvas-equivalent grade in sRGB-encoded values (canvas compositing is not linear):
       × shade (multiply), night: × coralMul (multiply) + glow·amt·glowK ('lighter' of the sprite tinted by glow),
       haze: mix toward the theme fog colour (source-atop fill at alpha haze·hazeK)."""
    a = np.asarray(img, np.float32) / 255
    rgb, al = a[..., :3], a[..., 3:4]
    th = sc['themes'][theme]
    sh = g.get('shade', 1)
    shade = np.array(sh if isinstance(sh, list) else [sh] * 3, np.float32)
    c = rgb * shade
    if theme == 'night':
        c = c * np.array(th.get('coralMul', [0.30, 0.42, 0.95]), np.float32)
        if glow is not None:
            c = c + rgb * np.array(glow['glow'], np.float32) * glow['amt'] * th.get('glowK', 0.4)
    hz = g.get('haze', 0.0) * th.get('hazeK', 1.0)
    c = c * (1 - hz) + hexrgb(th['fog']) * hz
    out = np.clip(c, 0, 1)
    return Image.fromarray((np.concatenate([out, al], -1) * 255 + 0.5).astype(np.uint8), 'RGBA')
def render(A, theme):
    W, H, m = layout(A)
    poster = Image.open(REPO + B[theme]['poster']).convert('RGB')
    canvas = poster.resize((int(round(m['dw'])), int(round(m['dh']))), Image.LANCZOS)
    out = Image.new('RGBA', (W, H)); out.paste(canvas, (int(round(m['dx'])), int(round(m['dy']))))
    items = []
    for c in sc.get('corals', []):
        e = cat[c['coral']]; items.append(('coral', c['z'], c, e))
    for p in sc.get('props', []):
        items.append(('prop', p['z'], p, None))
    items.sort(key=lambda t: -t[1])          # far to near
    for kind, z, d, e in items:
        if kind == 'coral':
            im = load(e['image'])
            h = d['scale'] * m['dh']; w = h * im.width / im.height
            u, v = e['base']
            if d.get('flip'): im = im.transpose(Image.FLIP_LEFT_RIGHT); u = 1 - u
            x, y = bg(m, d['bx'], d['byBase'])
            x0, y0 = x - u * w, y - v * h
            im2 = im.resize((max(1, int(round(w))), max(1, int(round(h)))), Image.LANCZOS)
            im2 = grade(im2, theme, d.get('grade', {}), e.get('night'))
        else:
            im = load(d['src'])
            w = d['bw'] * m['dw']; h = w * im.height / im.width
            x, y = bg(m, d['bx'], d['byBottom'])
            x0, y0 = x - w / 2, y - h
            im2 = im.resize((max(1, int(round(w))), max(1, int(round(h)))), Image.LANCZOS)
            t = d.get('tint')
            if t:
                a = np.asarray(im2, np.float32) / 255; rgb = a[..., :3]; tc = np.array(t['rgb'], np.float32) / 255
                if t['mode'] == 'multiply': rgb = rgb * (1 - t['a']) + rgb * tc * t['a']
                else:
                    lum = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
                    tl = tc @ np.array([0.299, 0.587, 0.114], np.float32)
                    rgb = rgb * (1 - t['a']) + np.clip(tc * lum / max(tl, 1e-3), 0, 1) * t['a']
                im2 = Image.fromarray((np.concatenate([rgb, a[..., 3:]], -1) * 255 + 0.5).astype(np.uint8), 'RGBA')
            im2 = grade(im2, theme, d.get('grade', {}), d.get('night'))
            # contact shadow (multiply ellipse) like the engine's drawFloorShadow
            sh = d.get('shadow')
            if sh:
                sw, shh = sh['w'] * w, sh['h'] * w
                cx, cy = x + sh.get('dx', 0) * w, y + sh.get('dy', 0) * w
                yy, xx = np.mgrid[0:H, 0:W]
                r2 = ((xx - cx) / (sw / 2)) ** 2 + ((yy - cy) / (shh / 2)) ** 2
                k = np.clip(1 - r2, 0, 1) ** 1.5 * sh['a']
                base = np.asarray(out, np.float32)
                base[..., :3] *= (1 - k[..., None] * (1 - np.array([10, 24, 48]) / 255))
                out = Image.fromarray(base.astype(np.uint8), 'RGBA')
            if d.get('layers') and d['layers'].get('front'):
                fr = load(d['layers']['front']).resize(im2.size, Image.LANCZOS)
                # back + front of the same frame == the whole anemone (front drawn on top later in engine)
        out.alpha_composite(im2, (int(round(x0)), int(round(y0))))
    if DEBUG:
        dr = ImageDraw.Draw(out)
        sx = B['safeX']; sy = B.get('safeY', [0, 1])
        for bx in sx: X, _ = bg(m, bx, 0); dr.line([(X, 0), (X, H)], fill=(255, 255, 0, 255), width=2)
        for by in sy: _, Y = bg(m, 0, by); dr.line([(0, Y), (W, Y)], fill=(255, 255, 0, 255), width=2)
        hb = sc['camera']['horizonBy']; _, Y = bg(m, 0, hb); dr.line([(0, Y), (W, Y)], fill=(0, 255, 255, 255), width=1)
        pts = [bg(m, bx, by) for bx, by in sc['floor']]; dr.line(pts, fill=(255, 128, 0, 255), width=3)
        cols = {'graze': (0, 255, 0), 'pick': (0, 200, 255), 'shelter': (255, 0, 255), 'peek': (255, 80, 200), 'home': (255, 160, 0), 'perch': (255, 255, 255)}
        for s in sc.get('spots', []):
            X, Y = bg(m, s['bx'], s['by']); r = s['r'] * m['dw']
            dr.ellipse([X - r, Y - r, X + r, Y + r], outline=cols.get(s['type'], (255, 255, 255)) + (255,), width=2)
            dr.text((X + r + 2, Y - 6), f"{s['id']} z{s['z']}", fill=(255, 255, 255, 255))
        for ln in sc.get('lanes', []):
            pts = [bg(m, p[0], p[1]) for p in ln['pts']]; dr.line(pts, fill=(120, 255, 120, 255), width=2)
            for p, q in zip(ln['pts'], pts): dr.text((q[0] + 3, q[1] + 3), f"{p[2]}", fill=(120, 255, 120, 255))
        for b in sc.get('bubbles', []):
            X, Y = bg(m, b['bx'], b['by']); dr.rectangle([X - 5, Y - 5, X + 5, Y + 5], outline=(200, 255, 255, 255), width=2)
            dr.text((X + 7, Y - 5), b['id'], fill=(200, 255, 255, 255))
        for c in sc.get('corals', []):
            X, Y = bg(m, c['bx'], c['byBase']); dr.ellipse([X - 4, Y - 4, X + 4, Y + 4], fill=(255, 0, 0, 255))
            dr.text((X + 5, Y - 14), f"{c['coral']} z{c['z']}", fill=(255, 200, 200, 255))
        for p in sc.get('props', []):
            X, Y = bg(m, p['bx'], p['byBottom']); dr.ellipse([X - 4, Y - 4, X + 4, Y + 4], fill=(255, 160, 0, 255))
            dr.text((X + 5, Y - 14), f"{p['id']} z{p['z']}", fill=(255, 220, 160, 255))
        for s in sc['light']['sources']:
            X, Y = bg(m, s['bx'], s['byAbove'])
            for k in range(s['streaks']):
                ang = math.radians((k / max(1, s['streaks'] - 1) - 0.5) * 2 * s['spread'] + s.get('tilt', 0))
                L = 3 * H
                dr.line([(X, Y), (X + math.sin(ang) * L, Y + math.cos(ang) * L)], fill=(255, 240, 160, 120), width=1)
    return out.convert('RGB')
res = {}
for theme in sys.argv[4].split(',') if len(sys.argv) > 4 and not sys.argv[4].startswith('--') else ['day', 'night']:
    for A in aspects:
        im = render(A, theme)
        fn = f'{outp}_{theme}_{A:.2f}{"_dbg" if DEBUG else ""}.png'
        im.save(fn); print(fn, im.size)
