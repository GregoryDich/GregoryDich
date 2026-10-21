# R2c: два производных ассета для видео-сцены (детерминированно; исходники не меняются).
#   1. scene/props/starfish_floor.png — звезда «лёжа на дне» из starfish.png (262×225): сжатие по вертикали до 0.56
#      (262×126) и перспектива — дальний (верхний) край на 8% уже ближнего; PIL PERSPECTIVE, бикубика, по
#      премультиплицированной альфе (без тёмной каймы). starfish.png не трогать — его берёт фото-сцена.
#   2. scene/corals/tube_sponges_yellow.png — жёлтые трубчатые губки: перекраска tube_sponges_lilac.png по яркости
#      L = 0.2126 R + 0.7152 G + 0.0722 B через кусочно-линейную рампу (охра → жёлтый → сливочный); альфа как есть.
#      (multiply grade.shade по лиловой губке не годится: синие трубки становятся зелёными.)
# usage: python3.13 -I tools/aquarium-test/art/r2c_assets.py aquarium
import sys
import numpy as np
from PIL import Image

root = sys.argv[1] if len(sys.argv) > 1 else 'aquarium'


def perspective_coeffs(out_pts, in_pts):
    # коэффициенты PIL PERSPECTIVE: точка ВЫХОДА (x, y) → точка ВХОДА (a x + b y + c)/(g x + h y + 1), …
    A, B = [], []
    for (x, y), (u, v) in zip(out_pts, in_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def starfish_floor(src, dst, squash=0.56, narrow=0.08):
    im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float64) / 255.0
    h, w = im.shape[:2]
    h2 = int(round(h * squash))
    # премультипликация: каналы RGB·α, каждый — отдельным float-изображением (режим 'F')
    pm = np.dstack([im[..., :3] * im[..., 3:4], im[..., 3:4]])
    d = narrow / 2 * w
    co = perspective_coeffs([(d, 0), (w - d, 0), (w, h2), (0, h2)], [(0, 0), (w, 0), (w, h), (0, h)])
    ch = [np.asarray(Image.fromarray(pm[..., k].astype(np.float32), 'F')
                     .transform((w, h2), Image.PERSPECTIVE, co, Image.BICUBIC)) for k in range(4)]
    a = np.clip(ch[3], 0, 1)
    rgb = np.dstack(ch[:3]) / np.maximum(a, 1e-6)[..., None]
    rgb = np.where(a[..., None] > 1e-4, np.clip(rgb, 0, 1), 0)
    out = np.dstack([rgb, a])
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA').save(dst, optimize=True)
    return (w, h2)


RAMP = [(0.00, (25, 18, 6)), (0.15, (70, 50, 12)), (0.35, (150, 110, 25)),
        (0.55, (210, 165, 45)), (0.75, (238, 205, 90)), (1.00, (252, 240, 170))]


def tube_sponges_yellow(src, dst):
    im = np.asarray(Image.open(src).convert('RGBA'))
    rgb = im[..., :3].astype(np.float64) / 255.0
    L = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    xs = [s for s, _ in RAMP]
    out = np.dstack([np.interp(L, xs, [c[k] for _, c in RAMP]) for k in range(3)])
    res = np.dstack([np.clip(out + 0.5, 0, 255).astype(np.uint8), im[..., 3]])
    Image.fromarray(res, 'RGBA').save(dst, optimize=True)
    return im.shape[1], im.shape[0]


if __name__ == '__main__':
    print('starfish_floor', starfish_floor(f'{root}/scene/props/starfish.png', f'{root}/scene/props/starfish_floor.png'))
    print('tube_sponges_yellow', tube_sponges_yellow(f'{root}/scene/corals/tube_sponges_lilac.png',
                                                     f'{root}/scene/corals/tube_sponges_yellow.png'))
