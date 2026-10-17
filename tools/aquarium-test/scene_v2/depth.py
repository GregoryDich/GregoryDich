import numpy as np, onnxruntime as ort
from PIL import Image
import sys
# модель: Depth Anything (ViT-S/14) в ONNX — github.com/fabio-sim/Depth-Anything-ONNX, релиз v1.0.0, depth_anything_vits14.onnx
m = sys.argv[1] if len(sys.argv) > 1 else 'models/da_vits14.onnx'
s = ort.InferenceSession(m, providers=['CPUExecutionProvider'])
for i in s.get_inputs(): print('in', i.name, i.shape, i.type)
for o in s.get_outputs(): print('out', o.name, o.shape)
im = Image.open('out/median720.png').convert('RGB')
W, H = 518 * 16 // 9 // 14 * 14, 518  # keep aspect, multiple of 14
shp = s.get_inputs()[0].shape
if isinstance(shp[2], int): H, W = shp[2], shp[3]
x = np.asarray(im.resize((W, H), Image.BICUBIC), np.float32) / 255
x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
x = x.transpose(2, 0, 1)[None].astype(np.float32)
d = s.run(None, {s.get_inputs()[0].name: x})[0].squeeze()
print(d.shape, d.min(), d.max())
np.save('out/depth_rel.npy', d)
v = (d - d.min()) / (d.max() - d.min())
Image.fromarray((v * 255).astype(np.uint8)).resize((1280, 720), Image.BICUBIC).save('out/depth_rel.png')
