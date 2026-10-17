import numpy as np
from PIL import Image
from scipy import ndimage as ndi
im = np.asarray(Image.open('out/median720.png'), np.float32) / 255
H, W, _ = im.shape
d = np.load('out/depth_rel.npy')
d = np.asarray(Image.fromarray(d.astype(np.float32), 'F').resize((W, H), Image.BICUBIC))
np.save('out/depth720.npy', d)
wz = np.load('out/water720.npz'); water = wz['water']
reef = ~water
vis = im * 0.6
for t, col in [(2.5, (1, 1, 0)), (3.9, (1, 0, 0)), (6, (0, 1, 0)), (10, (1, 0, 1))]:
    e = (d > t) ^ ndi.binary_erosion(d > t)
    vis[e] = col
Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).save('out/depth_contours.png')
