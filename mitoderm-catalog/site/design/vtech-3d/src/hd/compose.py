"""Lay a transparent Cycles frame (vtech_scene.py) over the line's smoke background.
usage: python3 compose.py <frame.png> <layers/vt-bg-wide.jpg> <out.jpg|out.webp> [gain=1] [focus=0.5,0.5]
gain scales the smoke's brightness per screen, as the three.js `dim` did (S4 brightest, S5 calmer); the smoke is cut to
the frame's aspect (cover) around focus (fractions of the background): a phone frame takes a portrait slice around the
plume (0.74,0.5), not a dark corner, and its lower part fades toward black for the copy."""
import sys
from PIL import Image, ImageEnhance
frame, bg, out = sys.argv[1:4]
gain = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
fx, fy = (float(v) for v in sys.argv[5].split(',')) if len(sys.argv) > 5 else (0.5, 0.5)
fg = Image.open(frame).convert('RGBA')
smoke = Image.open(bg).convert('RGB'); W, H = smoke.size; a = fg.width / fg.height
cw, ch = (round(H * a), H) if W / H > a else (W, round(W / a))
x0 = min(max(round(fx * W - cw / 2), 0), W - cw); y0 = min(max(round(fy * H - ch / 2), 0), H - ch)
base = ImageEnhance.Brightness(smoke.crop((x0, y0, x0 + cw, y0 + ch))).enhance(gain).resize(fg.size, Image.LANCZOS)
if fg.height > fg.width:   # phone: the plume stays around the object at the top, the copy below sits on near-black as on S1
    ramp = Image.linear_gradient('L').resize(fg.size).point(lambda v: round(255 * (1 - 0.65 * min(1, max(0, (v / 255 - 0.35) / 0.45)) ** 2)))
    base = Image.composite(base, Image.new('RGB', fg.size, (0, 0, 0)), ramp)
base = base.convert('RGBA')
im = Image.alpha_composite(base, fg).convert('RGB')
im.save(out, quality=92) if out.endswith('.jpg') else im.save(out, quality=90, method=6)
print(out, im.size)
