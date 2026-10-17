#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Грейды задника-видео рифа (Adobe Stock 188049047): «день» (Мальдивы) и «ночь»
(королевский синий LED). Генерирует 3D LUT (.cube) для ffmpeg lut3d.

Цепочка в make_media.sh (всё детерминировано):
  bilateral по U/V (блочная хрома H.264 на плоской воде) -> zscale 4K -> 2560x1440
  -> xfade (бесшовная петля) -> zscale (BT.709 limited -> float RGB)
  -> colorchannelmixer (PREMIX: сжатие гаммы; исходник далеко за sRGB: R<0 у ~54% пикселей,
     B>1 у ~16% — без него вода «рвётся» пятнами по границе среза)
  -> lut3d (этот файл: grade_day / grade_night над [0,1]^3; внутри делим на PREMIX_SCALE)
  -> zscale (-> BT.709 limited yuv420p, дизеринг error_diffusion)

Работа в OKLab/OKLCh: широкие гладкие окна по оттенку (cos^2) и вес по хроме — без
узких «попаданий» по оттенку, которые дают пятна; выход — мягкое сжатие хромы к границе гаммы.

Использование:
  python3.13 -I reef_grade.py cube day|night OUT.cube [N=65]
  python3.13 -I reef_grade.py premix          # печатает коэффициенты colorchannelmixer
  python3.13 -I reef_grade.py still day|night IN.raw OUT.png [W H]   # прототип на кадре
     IN.raw = gbrpf32le (planar G,B,R) из ffmpeg zscale
"""
import sys
import numpy as np

# ---------- сжатие гаммы перед LUT (линейная операция в кодированных значениях) ----------
# x' = SCALE * (Y + K*(x - Y)) ; Y — яркость BT.709. Делает это colorchannelmixer.
PREMIX_K = 0.82
PREMIX_SCALE = 0.80  # B воды до ~1.3: после сжатия <= 1, без среза; LUT делит обратно

LUMA = np.array([0.2126, 0.7152, 0.0722])


def premix_matrix():
    k, s = PREMIX_K, PREMIX_SCALE
    m = np.outer(np.ones(3), LUMA) * (1 - k) + np.eye(3) * k
    return m * s


def premix(rgb):
    return np.clip(rgb @ premix_matrix().T, 0.0, 1.0)


# ---------- цветовые пространства ----------
def s2l(x):
    x = np.maximum(x, 0.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
               [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
               [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]])
M1i = np.linalg.inv(M1)
M2i = np.linalg.inv(M2)


def lin2lab(l):
    return np.cbrt(l @ M1.T) @ M2.T


def lab2lin(lab):
    return (lab @ M2i.T) ** 3 @ M1i.T


def lch(lab):
    L = lab[..., 0]
    C = np.hypot(lab[..., 1], lab[..., 2])
    h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360.0
    return L, C, h


def from_lch(L, C, h):
    r = np.radians(h)
    return np.stack([L, C * np.cos(r), C * np.sin(r)], axis=-1)


def hdist(h, c):
    """Знаковое расстояние по кругу h - c, в (-180, 180]."""
    return (h - c + 180.0) % 360.0 - 180.0


def win(h, c, half):
    """Гладкое окно cos^2 по оттенку, ширина +-half градусов."""
    d = np.clip(np.abs(hdist(h, c)) / half, 0.0, 1.0)
    return np.cos(d * np.pi / 2) ** 2


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def cmax_of(L, h, iters=20):
    """Максимальная хрома внутри [0,1] linear для данных L, h (бисекция)."""
    lo = np.zeros_like(L)
    hi = np.full_like(L, 0.5)
    for _ in range(iters):
        mid = (lo + hi) / 2
        lm = lab2lin(from_lch(L, mid, h))
        good = np.all((lm >= -1e-7) & (lm <= 1 + 1e-7), axis=-1)
        lo = np.where(good, mid, lo)
        hi = np.where(good, hi, mid)
    return lo


def gamut_map(L, C, h, knee=0.82):
    """Мягкое сжатие хромы к границе гаммы (без среза и без «ступеньки» у границы):
    до knee*Cmax — без изменений, выше — плавный tanh-подход к Cmax. L и h сохраняются."""
    cm = cmax_of(L, h)
    k = knee * cm
    span = np.maximum(cm - k, 1e-6)
    over = C > k
    Cf = np.where(over, k + span * np.tanh((C - k) / span), C)
    return np.clip(lab2lin(from_lch(L, Cf, h)), 0.0, 1.0)


def shoulder(x, knee, top=1.0):
    """Мягкое плечо: линейно до knee, далее плавно стремится к top."""
    y = x.copy()
    m = x > knee
    s = top - knee
    y[m] = knee + s * (1 - np.exp(-(x[m] - knee) / s))
    return y


# ---------- ДЕНЬ: «Мальдивы» ----------
def _prep(rgb):
    """Вход LUT -> исходные значения (без сжатия), linear, OKLCh."""
    x = rgb / PREMIX_SCALE
    lin = s2l(x)
    L, C, h = lch(lin2lab(lin))
    return L, C, h


def grade_day(rgb):
    L, C, h = _prep(rgb)
    # вес «вода»: насыщенная лазурь (C ~0.15, h ~242..248); дальний риф ~0.5
    wW = win(h, 244.0, 70.0) * smooth(C, 0.06, 0.13)
    hiC = smooth(C, 0.01, 0.05)

    # 1) тон: подъём теней (рассеянный солнечный свет), светлее середины
    om = np.clip(1 - L, 0.0, 1.0)
    L1 = L + 0.17 * L * om ** 1.6 + 0.07 * om * smooth(L, 0.0, 0.25)
    L1 = L1 + 0.05 * wW * smooth(L, 0.45, 0.75)          # вода у поверхности светлее
    L1 = shoulder(L1, 0.86, 0.99)

    # 2) лазурь -> бирюза (244 -> ~214), сохраняя насыщенность
    h1 = h - 27.0 * win(h, 244.0, 95.0) * hiC
    C1 = C * (1.0 - 0.15 * wW)

    # 3) кораллы/камень (низкая хрома, не вода): тёплый солнечный свет + живость
    coral = (1 - wW)
    C1 = C1 * (1.0 + 0.45 * coral * (1 - smooth(C, 0.06, 0.12)))
    warm = coral * smooth(L1, 0.12, 0.50)
    a = C1 * np.cos(np.radians(h1)) + 0.016 * warm
    b = C1 * np.sin(np.radians(h1)) + 0.020 * warm

    # 4) тени не «ночные»: синеву в тенях -> к бирюзово-зелёной толще
    sh = 1 - smooth(L, 0.10, 0.40)
    a = a - 0.010 * sh
    b = b + 0.012 * sh

    # 5) светлый песок/риф в бирюзе -> белее (солнце на песке)
    sand = smooth(L1, 0.52, 0.76) * win(h1, 205.0, 50.0) * (1 - smooth(C, 0.11, 0.15))
    a = a * (1 - 0.55 * sand)
    b = b * (1 - 0.55 * sand)
    L1 = L1 + 0.07 * sand

    L2, C2, h2 = lch(np.stack([L1, a, b], axis=-1))
    out = gamut_map(np.clip(L2, 0, 0.995), C2, h2)
    return l2s(out)


# ---------- НОЧЬ: королевский синий LED ----------
def grade_night(rgb):
    L, C, h = _prep(rgb)
    wW = win(h, 244.0, 70.0) * smooth(C, 0.06, 0.13)
    hiC = smooth(C, 0.01, 0.05)
    coral = 1 - wW

    # 1) тон: темнее, глубже; блики кораллов остаются яркими («свечение»)
    L1 = 0.88 * L ** 1.15
    L1 = L1 * (1 - 0.22 * wW)                       # толща воды — глубокий синий
    L1 = L1 + 0.10 * coral * smooth(L, 0.55, 0.90)  # светлые кораллы светятся
    L1 = shoulder(L1, 0.82, 0.97)

    # 2) вода -> королевский синий (244 -> ~262)
    h1 = h + 13.0 * win(h, 240.0, 95.0) * hiC
    # песок/дальний риф в бирюзе (h~205..230) -> тоже в синий, без «дневного» циана
    h1 = h1 + 20.0 * win(h, 216.0, 38.0) * hiC
    C1 = C * (1.0 + 0.08 * wW)

    # 3) флуоресценция: тёплые/жёлтые -> ярче (оранж/лимон), пурпур -> маджента
    fl = coral * smooth(L, 0.25, 0.60) * (1 - 0.45 * smooth(L, 0.78, 0.95))
    C1 = C1 * (1.0 + 1.1 * fl * win(h, 95.0, 70.0))          # жёлто-оливковые
    h1 = h1 + 28.0 * fl * win(h, 320.0, 50.0)                # лиловые -> розовые
    C1 = C1 * (1.0 + 2.4 * fl * win(h, 320.0, 60.0) * smooth(C, 0.015, 0.04))
    C1 = C1 * (1.0 + 1.0 * fl * win(h, 140.0, 45.0))         # зелёные

    # 4) нейтральный камень под актиником: синий с лёгким фиолетом
    neutral = coral * (1 - smooth(C1, 0.03, 0.09))
    a = C1 * np.cos(np.radians(h1)) + 0.006 * neutral
    b = C1 * np.sin(np.radians(h1)) - 0.045 * neutral * smooth(L1, 0.05, 0.4)

    L2, C2, h2 = lch(np.stack([L1, a, b], axis=-1))
    out = gamut_map(np.clip(L2, 0, 0.99), C2, h2)
    return l2s(out)


GRADES = {'day': grade_day, 'night': grade_night}


def write_cube(path, fn, n=65):
    g = np.linspace(0.0, 1.0, n)
    # порядок .cube: R меняется быстрее всех
    b, gg, r = np.meshgrid(g, g, g, indexing='ij')
    rgb = np.stack([r, gg, b], axis=-1).reshape(-1, 3)
    out = np.clip(fn(rgb), 0.0, 1.0)
    with open(path, 'w') as f:
        f.write('TITLE "reef %s"\n' % fn.__name__)
        f.write('LUT_3D_SIZE %d\n' % n)
        f.write('DOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
        for v in out:
            f.write('%.6f %.6f %.6f\n' % (v[0], v[1], v[2]))


def load_raw(path, w=2560, h=1440):
    a = np.fromfile(path, dtype=np.float32).reshape(3, h, w)
    g, b, r = a
    return np.stack([r, g, b], axis=-1).astype(np.float64)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'cube':
        write_cube(sys.argv[3], GRADES[sys.argv[2]], int(sys.argv[4]) if len(sys.argv) > 4 else 65)
    elif cmd == 'premix':
        m = premix_matrix()
        names = 'rgb'
        print(':'.join('%s%s=%.6f' % (names[i], names[j], m[i, j]) for i in range(3) for j in range(3)))
    elif cmd == 'still':
        from PIL import Image
        w = int(sys.argv[5]) if len(sys.argv) > 5 else 2560
        hh = int(sys.argv[6]) if len(sys.argv) > 6 else 1440
        rgb = premix(load_raw(sys.argv[3], w, hh))
        fn = GRADES.get(sys.argv[2])
        out = rgb if fn is None else fn(rgb.reshape(-1, 3)).reshape(rgb.shape)
        Image.fromarray(np.round(np.clip(out, 0, 1) * 255).astype(np.uint8)).save(sys.argv[4])
