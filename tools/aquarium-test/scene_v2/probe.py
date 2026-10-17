# depth grid (bilinear like engine depthAtB) + mask alpha at given backdrop points
import json, sys, numpy as np
from PIL import Image
g = json.load(open('out/geom.json')); G = np.array(g['grid']); R, C = G.shape
M = np.load('out/masks_full.npz')
def depthAtB(bx, by):
    x = bx * C - 0.5; y = by * R - 0.5
    x0 = int(np.clip(np.floor(x), 0, C - 1)); y0 = int(np.clip(np.floor(y), 0, R - 1))
    x1 = min(C - 1, x0 + 1); y1 = min(R - 1, y0 + 1); fx = np.clip(x - x0, 0, 1); fy = np.clip(y - y0, 0, 1)
    return (G[y0, x0] * (1 - fx) * (1 - fy) + G[y0, x1] * fx * (1 - fy) + G[y1, x0] * (1 - fx) * fy + G[y1, x1] * fx * fy)
def alpha(bx, by):
    x = int(np.clip(bx * 2560, 0, 2559)); y = int(np.clip(by * 1440, 0, 1439))
    return {k: round(float(M[k][y, x]), 2) for k in ('left', 'right', 'far')}
if __name__ == '__main__':
    for a in sys.argv[1:]:
        bx, by = map(float, a.split(','))
        print(a, 'grid %.2f' % depthAtB(bx, by), alpha(bx, by))
