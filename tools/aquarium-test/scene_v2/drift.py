import numpy as np, glob
from PIL import Image
from skimage.registration import phase_cross_correlation
fs = sorted(glob.glob('frames/dfull_*.png'))
def L(f): return np.asarray(Image.open(f).convert('L'), np.float32)
ref = L(fs[0])
regs = {'leftpillar': (slice(300, 1100), slice(100, 1100)), 'rightpillar': (slice(300, 1100), slice(1700, 2500)), 'canyonfloor': (slice(1000, 1400), slice(1000, 1600))}
for f in fs[1:]:
    im = L(f); out = []
    for k, (ys, xs) in regs.items():
        sh, err, _ = phase_cross_correlation(ref[ys, xs], im[ys, xs], upsample_factor=20)
        out.append(f'{k}:{sh[0]:+.2f},{sh[1]:+.2f}')
    print(f.split('/')[-1], ' '.join(out))
