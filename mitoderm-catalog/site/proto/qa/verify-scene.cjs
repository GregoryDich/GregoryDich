// Checks of a live three.js scene module (scenes/<slug>.js) on its own, in headless Chromium with software GL: the
// scene draws the full 16:10 frame at fixed story positions and the checks read its pixels and its state():
//   seam       a closed jar's seam reads as a dark line (not the silver shoulder behind it);
//   pearls     gel pearls only once the lid is up (never through or above a closed lid);
//   kit        the live kit pose at p = 5, mid idle sway, is the picture kit() gives the offer card (no double image);
//   restore    after a lost and restored WebGL context the gold is not black (the environment is rebuilt);
//   step-down  on a fake clock: a steady 30 Hz (a low-power cap) steps down once, finds no gain, goes back to 2 and
//              stops trying; slow frames that get faster at the lower ratio keep it, also when vsync steps hide the gain
//              from a median.
// usage: NODE_PATH=$(npm root -g) node verify-scene.cjs <scene.js> <three.module.min.js (three@0.160.0)>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [sceneFile, threeFile] = process.argv.slice(2);
const W = 1200, H = 750, files = path.join(path.dirname(path.resolve(sceneFile)), '..');
const page = `<!doctype html><html><body style="margin:0;background:#0b0a09"><canvas id="c" style="width:${W}px;height:${H}px"></canvas>
<script>let fake = 1000; window.__clock = v => { fake = v; }; const real = performance.now.bind(performance); window.__fakeTime = on => { performance.now = on ? () => fake : real; };</script>
<script type="module">
import * as THREE from '/three.js';
import { createScene } from '/scene.js';
const c = document.getElementById('c');
const make = () => createScene(THREE, { canvas: c, base: location.origin + '/files/', onLoad: () => { window.__loaded = true; } });
let sc = make();
const view = (t, still) => ({ cover: { x: 0, y: 0, w: ${W}, h: ${H} }, box: { x: 0, y: 0, w: ${W}, h: ${H} }, dpr: 1, t, still });
const grab = () => { const o = document.createElement('canvas'); o.width = c.width; o.height = c.height; o.getContext('2d').drawImage(c, 0, 0); return o; };
const pix = (cv) => cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
window.__draw = (p, t = 0, still = true) => { sc.draw(p, view(t, still)); return sc.state(); };
window.__frame = (p, t = 0) => { sc.draw(p, view(t, true)); return Array.from(pix(grab())); };
window.__column = (p, x, y0, y1) => { sc.draw(p, view(0, true)); const d = pix(grab()), out = [];
  for (let y = y0; y <= y1; y++) { const i = (y * c.width + x) * 4; out.push(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]); } return out; };
window.__kitVsLive = () => {   // the card's picture and the live pose at p = 5 mid-sway, pixel by pixel
  const k = pix(sc.kit(view(0, true))); sc.draw(5, view(7.3, false)); const l = pix(grab()); let diff = 0, n = 0;
  for (let i = 0; i < k.length; i += 4) { if (k[i + 3] > 8 || l[i + 3] > 8) { n++; diff += Math.abs(k[i] - l[i]) + Math.abs(k[i + 1] - l[i + 1]) + Math.abs(k[i + 2] - l[i + 2]); } }
  return { meanDiff: diff / Math.max(1, n) / 3, pixels: n };
};
window.__lose = () => new Promise(res => {   // lose and restore the context, then draw
  const gl = c.getContext('webgl2'), ext = gl.getExtension('WEBGL_lose_context');
  c.addEventListener('webglcontextrestored', () => setTimeout(() => res(true), 50), { once: true });
  c.addEventListener('webglcontextlost', () => setTimeout(() => ext.restoreContext(), 50), { once: true });
  ext.loseContext();
});
window.__fresh = () => { sc.dispose(); sc = make(); };
</script></body></html>`;
const checks = [];
const ok = (name, pass, info = '') => { checks.push({ name, pass }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (info ? '  ' + info : '')); };
const lum = (d, x, y) => { const i = (y * W + x) * 4; return 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]; };
(async () => {
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: W, height: H } }); const errs = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.route('http://scene.test/**', r => {
    const u = new URL(r.request().url()).pathname;
    if (u === '/') return r.fulfill({ body: page, contentType: 'text/html' });
    if (u === '/three.js') return r.fulfill({ path: threeFile, contentType: 'application/javascript' });
    if (u === '/scene.js') return r.fulfill({ path: sceneFile, contentType: 'application/javascript' });
    const f = path.join(files, u.replace(/^\/files\//, '')); return fs.existsSync(f) ? r.fulfill({ path: f }) : r.fulfill({ status: 404, body: '' });
  });
  await p.goto('http://scene.test/'); await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });

  // seam: the darkest pixel down a column of the big 'why' jar (560 px high in the 2400 frame, centre x 720) that is
  // clear of the lettering (left of «EXOTECH»), around the seam, against the gold of the base under it
  const col = await p.evaluate(() => window.__column(1, 270, 370, 470));
  const darkest = Math.min(...col.slice(0, 60)), gold = col.slice(65).sort((a, b) => a - b)[17];
  ok('seam: a dark line across the closed jar', darkest < 0.45 * gold, `darkest ${darkest.toFixed(0)} vs gold ${gold.toFixed(0)}`);

  // pearls only with the lid up
  const bad = [];
  for (let x = 1; x <= 3.001; x += 0.05) for (const t of [0.3, 2.1, 5.7]) {
    const s = await p.evaluate(([x, t]) => window.__draw(x, t, false), [x, t]);
    if (s.pearlsOn && s.lidUp < 0.5) bad.push(`${x.toFixed(2)}@${t}:${s.pearlsOn}/${s.lidUp.toFixed(2)}`);
  }
  ok('pearls: only once the lid is up', !bad.length, bad.slice(0, 6).join(' '));

  // kit: the card's picture equals the live pose at p = 5 (the sway has settled)
  const kv = await p.evaluate(() => window.__kitVsLive());
  ok('kit: the live pose at p = 5 is the card picture (no double image)', kv.meanDiff < 1.5 && kv.pixels > 1000, `mean diff ${kv.meanDiff.toFixed(2)} over ${kv.pixels} px`);

  // context lost and restored: the gold is still gold
  const before = await p.evaluate(() => window.__frame(0));
  await p.evaluate(() => window.__lose());
  const after = await p.evaluate(() => window.__frame(0));
  const jx = Math.round(930 / 2400 * W), jy = Math.round(760 / 1500 * H);
  const lb = lum(before, jx, jy), la = lum(after, jx, jy);
  ok('restore: the jar is not black after a lost context', la > 0.7 * lb && la > 40, `jar centre ${lb.toFixed(0)} → ${la.toFixed(0)}`);

  // step-down on a fake clock
  const run = (steps) => p.evaluate(async steps => {
    window.__fresh(); window.__fakeTime(true); let t = 1000, q = [];
    for (const [ms, n] of steps) for (let i = 0; i < n; i++) { t += ms; window.__clock(t); q.push(window.__draw(1, t / 1000, false).quality); }
    window.__fakeTime(false); const s = window.__draw(1, 0, true); return { q: [...new Set(q)], quality: s.quality, capped: s.capped };
  }, steps);
  const cap = await run([[33.4, 400]]);
  ok('step-down: a steady 30 Hz (a cap) goes back to 2 and stops trying', cap.quality === 2 && cap.capped, JSON.stringify(cap));
  const slow = await run([[30, 90], [16.7, 200]]);
  ok('step-down: slow frames that get faster at 1.5 keep 1.5', slow.quality === 1.5 && !slow.capped, JSON.stringify(slow));
  // 30 → 18 ms behind 60 Hz vsync: 1.5 is kept (the mean fell), the next rung tried and, with no further gain, undone
  const vsync = await run([[33.4, 90]].concat(Array.from({ length: 200 }, () => [[16.7, 1], [33.4, 1]]).flat()));
  ok('step-down: a gain hidden by vsync steps (33 → 17/33 ms) keeps 1.5', vsync.quality === 1.5, JSON.stringify(vsync));
  const fast = await run([[16.7, 400]]);
  ok('step-down: 60 Hz stays at 2', fast.quality === 2 && fast.q.length === 1, JSON.stringify(fast));

  ok('no page errors', !errs.filter(e => !/Context Lost|Context Restored/.test(e)).length, errs.join(' | ').slice(0, 300));
  await b.close();
  console.log(`\n${checks.filter(c => c.pass).length}/${checks.length} checks passed`);
})();
