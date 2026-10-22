// Renders a live scene's key poses (scenes/<slug>.js, positions 0…5: meet, why, inside, feel, protocol, kit) as
// transparent PNGs of the full 16:10 frame (3840×2400 by default: the no-WebGL still covers a 4K screen at DPR 2), named as the frame pipeline names its key frames (v1-meet.png …
// v6-kit.png): build-vtech.py --keys takes them for the phone stills, the offer card's picture and the no-WebGL still,
// so every picture of the product comes from the same 3D model. Headless Chromium with software GL (SwiftShader).
// usage: NODE_PATH=$(npm root -g) node render-keys.cjs <scene.js> <three.module.min.js (three@0.160.0)> <out dir> [width=3840]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [sceneFile, threeFile, out, width = '3840'] = process.argv.slice(2);
const KEYS = ['v1-meet', 'v2-why', 'v3-inside', 'v4-feel', 'v5-protocol', 'v6-kit'], W = +width, H = Math.round(W * 10 / 16);
const page = `<!doctype html><html><body style="margin:0"><canvas id="c" style="width:${W}px;height:${H}px"></canvas>
<script type="module">
import * as THREE from '/three.js';
import { createScene } from '/scene.js';
const sc = createScene(THREE, { canvas: document.getElementById('c'), base: location.origin + '/files/', onLoad: () => { window.__loaded = true; } });
const v = { cover: { x: 0, y: 0, w: ${W}, h: ${H} }, box: { x: 0, y: 0, w: ${W}, h: ${H} }, dpr: 1, t: 0, still: true };
window.__key = p => { sc.draw(p, v); return document.getElementById('c').toDataURL('image/png'); };
</script></body></html>`;
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: W, height: H } }); const errs = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  const files = path.dirname(path.resolve(sceneFile)) + '/..';   // the proto folder: img/<slug>-3d/
  await p.route('http://keys.test/**', r => {
    const u = new URL(r.request().url()).pathname;
    if (u === '/') return r.fulfill({ body: page, contentType: 'text/html' });
    if (u === '/three.js') return r.fulfill({ path: threeFile, contentType: 'application/javascript' });
    if (u === '/scene.js') return r.fulfill({ path: sceneFile, contentType: 'application/javascript' });
    const f = path.join(files, u.replace(/^\/files\//, '')); return fs.existsSync(f) ? r.fulfill({ path: f }) : r.fulfill({ status: 404, body: '' });
  });
  await p.goto('http://keys.test/'); await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
  for (const [i, k] of KEYS.entries()) {
    const url = await p.evaluate(x => window.__key(x), i);
    fs.writeFileSync(path.join(out, k + '.png'), Buffer.from(url.split(',')[1], 'base64'));
    console.log(k);
  }
  if (errs.length) { console.error(errs.join('\n')); process.exitCode = 1; }
  await b.close();
})();
