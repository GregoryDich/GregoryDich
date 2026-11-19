// Renders the EXO-NAD scene: six standard keys + extra reference views. The module is untouched; extra views use
// the view's cover/box (a crop of the 2400x1500 frame) and, for the 3/4 box and the open tray, a hook on the
// renderer's render() that adjusts the box group after the module's pose() and before drawing.
// usage: NODE_PATH=$(npm root -g) node render-nad.cjs <scene.js> <three.module.min.js> <out dir> [only,comma,list]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [sceneFile, threeFile, out, only] = process.argv.slice(2);
const W = 3840, H = 2400;
// jobs: name, p, crop [x0, y0, w] in frame px (h = w / 1.6), hook
const JOBS = [
  ['v1-meet', 0], ['v2-why', 1], ['v3-inside', 2], ['v4-feel', 3], ['v5-protocol', 4], ['v6-kit', 5],
  ['x-box-34', 0, [100, 250, 1400], 'box34'],
  ['x-tray-open', 5.000001, [269, 650, 896], 'trayopen'],
  ['x-kit-crop', 5.000002, [365, 760, 704]],
  ['x-label-peel', 2, [540, 690, 440]],
  ['x-label-ph', 2.000001, [378, 776, 384]],
  ['x-label-ls', 2.000002, [208, 776, 384]],
  ['x-row-3', 2.000003, [250, 600, 700]],
];
const page = `<!doctype html><html><body style="margin:0"><canvas id="c" style="width:${W}px;height:${H}px"></canvas>
<script type="module">
import * as T from '/three.js';
let hook = null, rend = null;
class R extends T.WebGLRenderer { constructor(o) { super(o); rend = this; const orig = this.render;
  this.render = (s, c) => { if (hook) hook(s, c, this); return orig.call(this, s, c); }; } }
const THREE = Object.assign({}, T, { WebGLRenderer: R });
import { createScene } from '/scene.js';
const sc = createScene(THREE, { canvas: document.getElementById('c'), base: location.origin + '/files/', onLoad: () => { window.__loaded = true; } });
const findBox = s => s.children.find(o => o.isGroup && o.children.some(c => c.isGroup));
const HOOKS = {
  box34: (s, cam) => { const b = findBox(s); if (!b || !b.visible) return;
    b.rotateY(T.MathUtils.degToRad(-32));
    const q = new T.Quaternion().setFromAxisAngle(new T.Vector3(1, 0, 0), T.MathUtils.degToRad(14)); b.quaternion.premultiply(q); b.updateMatrixWorld(true); },
  trayopen: (s, cam, r) => { const b = findBox(s); if (!b) return; b.children[0].visible = false;
    s.traverse(o => { const m = o.material; if (!m) return; const u = r.properties.get(m).uniforms; if (u && u.uLidY) u.uLidY.value = 10; }); },
};
window.__key = (p, crop, h) => {
  let cover = { x: 0, y: 0, w: ${W}, h: ${H} };
  if (crop) { const k = ${W} / crop[2]; cover = { x: -crop[0] * k, y: -crop[1] * k, w: 2400 * k, h: 1500 * k }; }
  const v = { cover, box: { x: 0, y: 0, w: ${W}, h: ${H} }, dpr: 1, t: 0, still: true };
  hook = h ? HOOKS[h] : null;
  if (h === 'trayopen') { hook = null; sc.draw(p + 0.0000005, v); hook = HOOKS[h]; }   // compile once so the uniforms exist
  sc.draw(p, v); hook = null;
  return document.getElementById('c').toDataURL('image/png');
};
</script></body></html>`;
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: W, height: H } }); const errs = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  const files = path.dirname(path.resolve(sceneFile)) + '/..';
  await p.route('http://keys.test/**', r => {
    const u = new URL(r.request().url()).pathname;
    if (u === '/') return r.fulfill({ body: page, contentType: 'text/html' });
    if (u === '/three.js') return r.fulfill({ path: threeFile, contentType: 'application/javascript' });
    if (u === '/scene.js') return r.fulfill({ path: sceneFile, contentType: 'application/javascript' });
    const f = path.join(files, u.replace(/^\/files\//, '')); return fs.existsSync(f) ? r.fulfill({ path: f }) : r.fulfill({ status: 404, body: '' });
  });
  await p.goto('http://keys.test/'); await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  const sel = only ? only.split(',') : null;
  for (const [name, pp, crop, hook] of JOBS) {
    if (sel && !sel.includes(name)) continue;
    const f = path.join(out, name + '.png'); if (!sel && fs.existsSync(f)) { console.log('skip', name); continue; }
    const url = await p.evaluate(([x, c, h]) => window.__key(x, c, h), [pp, crop || null, hook || null]);
    fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64')); console.log(name);
  }
  if (errs.length) { console.error(errs.join('\n')); process.exitCode = 1; }
  await b.close();
})();
