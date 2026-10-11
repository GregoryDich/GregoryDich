"""PBR maps for the Cycles V-TECH scene from the flat print textures.
Upscale x3, re-crisp ink/foil edges (smoothstep on the masks) so print reads sharp at HD,
replace baked gold gradients with flat foil colour (reflections come from the lights)."""
import sys, numpy as np
from PIL import Image, ImageFilter
SRC, OUT = sys.argv[1], sys.argv[2]
def up(img, k): return img.resize((img.width * k, img.height * k), Image.LANCZOS)
def ss(x, a, b): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def smooth(a, k):  # blur then re-threshold: stair-stepped pixel edges become clean vector-like contours
    im = Image.fromarray((a * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(k * 0.9))
    return ss(np.asarray(im).astype(float) / 255, 0.42, 0.58)
def save(a, name, mode='RGB'):
    Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8), mode).save(f'{OUT}/{name}')
GOLD = np.array([0.93, 0.76, 0.45]); SILVER = np.array([0.86, 0.86, 0.85]); INK = np.array([0.025, 0.022, 0.02])
def foil(name, k, src, mr=None):
    t = np.asarray(up(Image.open(f'{SRC}/{src}').convert('RGB'), k)).astype(float) / 255
    if mr:
        m = np.asarray(up(Image.open(f'{SRC}/{mr}').convert('RGB'), k)).astype(float) / 255
        metal = smooth(ss(m[..., 2], 0.35, 0.65), k)
    else:  # side panel: gold except the black ends
        metal = smooth(ss(t.max(-1), 0.25, 0.45), k)
    mx, mn = t.max(-1), t.min(-1); sat = (mx - mn) / np.maximum(mx, 1e-3)
    silver = metal * ss(0.32 - sat, 0.0, 0.12)
    goldm = metal - silver
    alb = goldm[..., None] * GOLD + silver[..., None] * SILVER + (1 - metal)[..., None] * INK
    rough = goldm * 0.13 + silver * 0.24 + (1 - metal) * 0.5
    save(alb, f'{name}-albedo.png'); save(np.repeat(metal[..., None], 3, -1), f'{name}-metal.png'); save(np.repeat(rough[..., None], 3, -1), f'{name}-rough.png')
foil('box-front', 3, 'vtech-box-front.png', 'vtech-box-front-mr.png')
foil('box-side', 3, 'vtech-box-side.png')
foil('sachet', 3, 'vtech-sachet-front.png', 'vtech-sachet-front-mr.png')
# vial label: white screen print on glass, alpha re-crisped
l = up(Image.open(f'{SRC}/vtech-vial-label.png').convert('RGBA'), 4)
a = np.asarray(l).astype(float) / 255
al = smooth(a[..., 3], 4)
rgb = np.ones(a.shape[:2] + (3,)) * 0.92
Image.fromarray(np.dstack([rgb, al[..., None]]).__mul__(255).astype(np.uint8), 'RGBA').save(f'{OUT}/label.png')
print('ok')
