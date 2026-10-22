// Edge cases of the two three.js pages that the main checks do not reach (review of 19–21/10), in headless Chromium
// with software GL. A 3D-scene product page (build-vtech.py --scene, e.g. EXOTECH GEL):
//   switch      phone → desktop: the card turns live and the kit lands in it; the phone renders no kit picture
//   toolbar     phone, the browser's toolbar shows and hides (the large viewport pinned): stage, canvas, kit unchanged
//   reappear    reduced motion: the canvas comes back after a resize drawn in its new box, without another scroll
//   cdn         three.js stalled (no answer) or missing (404): no-gl, the still, the page script still works
// The MASK page (exocell-mask-3d.html):
//   toolbar     phone, toolbar shows and hides: the slot canvas keeps its size, the product does not move
//   rotation    390×844 → 740×360 → back: the view height follows the orientation
//   loops       three hide/show cycles: still one frame per vsync tick
//   restore     reduced motion: a lost and restored context redraws without a scroll
//   step-down   a steady 30 Hz (stubbed frame times) goes back to 2 and stops trying; DPR 1.5 never tries
//   drops       on the phone the drops are not transmissive (the transparent slot canvas made them milky)
//   offscreen   the phone's slot renderer draws nothing while its slot is off screen
// usage: FONTDIR=<dir with Rubik[wght].ttf> NODE_PATH=$(npm root -g) node verify-edges.cjs scene|mask <page.html> <files dir> <three.module.min.js>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [kind, pagePath, filesDir, threeFile] = process.argv.slice(2);
const FONTDIR = process.env.FONTDIR || path.join(require('os').tmpdir(), 'mitoderm-fonts');
const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
  + fs.readFileSync(pagePath, 'utf8') + '</body></html>';
const ORIGIN = 'https://edge.test/', TYPES = { '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg' };
const FONT_CSS = "@font-face{font-family:'Rubik';src:url(https://fonts.gstatic.com/local/0.ttf) format('truetype');font-weight:100 900;font-display:block}";
const checks = [];
const ok = (name, pass, info = '') => { checks.push({ name, pass }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (info ? '  ' + info : '')); };
const wait = (p, ms) => p.waitForTimeout(ms);

async function open(b, w, h, o = {}) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: o.dpr || 1, reducedMotion: o.reduce ? 'reduce' : 'no-preference', hasTouch: w < 500, isMobile: w < 500 });
  const p = await ctx.newPage(), errs = [];
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  if (o.init) await ctx.addInitScript(o.init);
  await ctx.route('https://fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: FONT_CSS }));
  await ctx.route('https://fonts.gstatic.com/local/**', r => r.fulfill({ path: path.join(FONTDIR, 'Rubik[wght].ttf'), contentType: 'font/ttf' }));
  await ctx.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => o.cdn === 'stall' ? undefined : o.cdn === '404' ? r.fulfill({ status: 404, body: '' })
    : r.fulfill({ path: threeFile, contentType: 'application/javascript' }));
  await ctx.route(ORIGIN + '**', r => {
    const rel = decodeURIComponent(new URL(r.request().url()).pathname.slice(1));
    if (!rel) return r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
    const f = path.join(filesDir, rel); return fs.existsSync(f) ? r.fulfill({ path: f, contentType: TYPES[path.extname(f)] || 'application/octet-stream' }) : r.fulfill({ status: 404, body: '' });
  });
  await p.goto(ORIGIN, { waitUntil: o.cdn === 'stall' ? 'domcontentloaded' : 'load' });
  return { ctx, p, errs };
}
const PIN = h => `.lvh-probe { height: ${h}px !important; }`;   // the large viewport, pinned: a toolbar then only changes innerHeight

async function scene(b) {
  const seq = p => p.evaluate(() => window.__seq());
  { // switch: phone, then desktop
    const { ctx, p, errs } = await open(b, 390, 844, { dpr: 2 });
    await p.waitForFunction(() => window.__seq && window.__seq().shown, null, { timeout: 60000 });
    await wait(p, 800);
    const ph = await p.evaluate(() => ({ live: document.querySelector('.kitcard').classList.contains('live'), kits: window.__seq().sceneState.kits }));
    await p.setViewportSize({ width: 1440, height: 900 }); await wait(p, 1500);
    const dk = await p.evaluate(() => ({ live: document.querySelector('.kitcard').classList.contains('live'), kits: window.__seq().sceneState.kits }));
    const ct = await p.evaluate(() => document.querySelector('.kitcard').getBoundingClientRect().top + scrollY);
    await p.evaluate(y => scrollTo(0, y), ct - 900 * 0.55); await wait(p, 1200);
    const mid = await p.evaluate(() => { const c = document.getElementById('seq'), k = document.querySelector('.kc-live').getBoundingClientRect(); return { tf: c.style.transform, z: c.style.zIndex, card: [k.left, k.top, k.right, k.bottom] }; });
    const end = await p.evaluate(() => { const c = document.querySelector('.kitcard'); return Math.max(0, c.getBoundingClientRect().top + scrollY - Math.min(innerHeight * 0.2, innerHeight - c.offsetHeight - 24)); });
    await p.evaluate(y => scrollTo(0, y), end); await wait(p, 1200);
    const landed = await p.evaluate(() => { const c = document.querySelector('.kc-live'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 20) n++; return { op: +document.getElementById('seq').style.opacity, filled: n / (c.width * c.height) }; });
    const s = /scale\(([\d.]+)\)/.exec(mid.tf);
    ok('scene switch: phone renders no kit picture, desktop then lands the kit in a live card',
      !ph.live && ph.kits === 0 && dk.live && dk.kits >= 1 && s && +s[1] < 1 && mid.z === '3' && landed.op === 0 && landed.filled > 0.15,
      `phone ${JSON.stringify(ph)}, desktop ${JSON.stringify(dk)}, mid ${mid.tf.slice(0, 50)} z${mid.z}, landed ${JSON.stringify(landed)}`);
    ok('scene switch: no console errors', !errs.length, errs.join(' | ').slice(0, 200));
    await ctx.close();
  }
  { // toolbar on the phone
    const { ctx, p } = await open(b, 390, 844, { dpr: 2, init: `document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = ${JSON.stringify(PIN(844))}; document.head.appendChild(s); });` });
    await p.waitForFunction(() => window.__seq && window.__seq().shown, null, { timeout: 60000 });
    await p.evaluate(() => scrollTo(0, document.getElementById('why').offsetTop)); await wait(p, 1000);
    const snap = () => p.evaluate(() => { const c = document.getElementById('seq'); return { sh: getComputedStyle(document.documentElement).getPropertyValue('--stage-h').trim(), w: c.width, h: c.height, css: c.style.width + 'x' + c.style.height, kits: window.__seq().sceneState.kits }; });
    const a = await snap(); await p.setViewportSize({ width: 390, height: 764 }); await wait(p, 900);
    const bb = await snap(); await p.setViewportSize({ width: 390, height: 844 }); await wait(p, 900);
    const c = await snap();
    ok('scene toolbar: stage, canvas and kit unchanged when the toolbar shows and hides', JSON.stringify(a) === JSON.stringify(bb) && JSON.stringify(a) === JSON.stringify(c), `${JSON.stringify(a)} | ${JSON.stringify(bb)}`);
    await ctx.close();
  }
  { // reappear under reduced motion
    const { ctx, p } = await open(b, 1440, 900, { reduce: true });
    await p.waitForFunction(() => window.__seq && window.__seq().shown, null, { timeout: 60000 });
    const end = await p.evaluate(() => document.documentElement.scrollHeight);
    await p.evaluate(y => scrollTo(0, y), end); await wait(p, 800);
    const hidden = await p.evaluate(() => +document.getElementById('seq').style.opacity);
    await p.setViewportSize({ width: 1300, height: 850 }); await wait(p, 800);
    const r0 = (await seq(p)).sceneState.renders;
    await p.evaluate(() => scrollTo(0, document.getElementById('why').offsetTop)); await wait(p, 900);
    const r = await p.evaluate(() => { const c = document.getElementById('seq').getBoundingClientRect(), s = window.__seq().sceneState; return { x: c.left, y: c.top, w: c.width, h: c.height, renders: s.renders, lastP: s.lastP }; });
    const cw = 1360, x0 = (1300 - cw) / 2, want = { x: x0 + 0.07 * cw, y: 0.19 * 850, w: 0.45 * cw, h: 0.62 * 850 };   // SCENE_BOX of the cover
    const near = ['x', 'y', 'w', 'h'].every(k => Math.abs(r[k] - want[k]) < 1.5);
    ok('scene reappear (reduced motion): drawn at once, in its new box', hidden === 0 && r.renders > r0 && r.lastP === 1 && near, `hidden ${hidden}, ${JSON.stringify(r)} vs ${JSON.stringify(want)}`);
    await ctx.close();
  }
  for (const cdn of ['404', 'stall']) { // three.js missing or stalled
    const { ctx, p, errs } = await open(b, 1440, 900, { cdn });
    await p.waitForFunction(() => document.documentElement.classList.contains('no-gl'), null, { timeout: 15000 }).catch(() => {});
    await p.evaluate(() => scrollTo(0, document.getElementById('inside').offsetTop)); await wait(p, 600);
    const v = await p.evaluate(() => ({ nogl: document.documentElement.classList.contains('no-gl'), still: getComputedStyle(document.querySelector('.still')).display,
      mode: window.__seq ? window.__seq().mode : null, dock: (document.querySelector('.dock a.on') || {}).textContent || '' }));
    ok(`scene cdn ${cdn}: no 3D, the still shows, the page script works`, v.nogl && v.still !== 'none' && v.mode === 'off' && !!v.dock, JSON.stringify(v));
    if (cdn === '404') ok('scene cdn 404: only the blocked file fails', errs.every(e => /404|Failed to load|three/i.test(e)), errs.join(' | ').slice(0, 200));
    await ctx.close();
  }
}

async function mask(b) {
  { // toolbar on the phone (reduced motion: no idle float, so any movement is the toolbar's), then the drops
    const { ctx, p, errs } = await open(b, 390, 844, { dpr: 3, reduce: true, init: `document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style'); s.textContent = ${JSON.stringify(PIN(844))}; document.head.appendChild(s); });` });
    await p.waitForFunction(() => window.__glReady, null, { timeout: 60000 });
    await p.evaluate(() => scrollTo(0, window.__anchorY(1))); await wait(p, 1500);
    const snap = () => p.evaluate(() => { const c = document.querySelector('.ph-gl'), s = c.parentElement.getBoundingClientRect(), r = window.__objRects()[0];
      return { w: c.width, h: c.height, r: [r[0] - s.left, r[1] - s.top, r[2] - s.left, r[3] - s.top].map(v => Math.round(v)), v: window.__view() }; });   // the product in its slot
    const a = await snap(); await p.setViewportSize({ width: 390, height: 764 }); await wait(p, 1200);
    const bb = await snap(); await p.setViewportSize({ width: 390, height: 844 }); await wait(p, 1200);
    const c = await snap();
    const moved = Math.max(...a.r.map((v, i) => Math.abs(v - bb.r[i])), ...a.r.map((v, i) => Math.abs(v - c.r[i])));
    ok('mask toolbar: slot canvas keeps its size, the product stays put in its slot', a.w === bb.w && a.h === bb.h && a.w === c.w && a.h === c.h && moved <= 2, `${a.w}x${a.h} → ${bb.w}x${bb.h} → ${c.w}x${c.h}, moved ${moved}px, FH ${a.v.FH}/${bb.v.FH}`);
    const drops = await p.evaluate(() => window.__drops());
    ok('mask drops: not transmissive on the phone', drops.transmission === 0 && drops.depthWrite === false, JSON.stringify(drops));
    ok('mask phone: no console errors', !errs.length, errs.join(' | ').slice(0, 200));
    await ctx.close();
  }
  { // the slot renderer off screen: a scroll position where the slot holding the product is far out of view
    const { ctx, p } = await open(b, 390, 844, { dpr: 2 });
    await p.waitForFunction(() => window.__glReady, null, { timeout: 60000 });
    const max = await p.evaluate(() => document.documentElement.scrollHeight - innerHeight);
    let found = null;
    for (let y = 0; y <= max && !found; y += 160) {
      await p.evaluate(v => scrollTo(0, v), y); await wait(p, 250);
      const r = await p.evaluate(() => { const c = document.querySelector('.ph-gl'); if (!c || !c.parentElement) return null; const s = c.parentElement.getBoundingClientRect(); return [s.top, s.bottom]; });
      if (r && (r[1] < -200 || r[0] > 844 + 200)) found = { y, r };
    }
    let c1 = 0, c2 = 0, c3 = 0;
    if (found) {
      await wait(p, 600); c1 = await p.evaluate(() => window.__slotRenders()); await wait(p, 1500); c2 = await p.evaluate(() => window.__slotRenders());
      await p.evaluate(() => scrollTo(0, window.__anchorY(1))); await wait(p, 1500); c3 = await p.evaluate(() => window.__slotRenders());
    }
    ok('mask offscreen: no slot renders while the slot is off screen, again once back', !!found && c2 === c1 && c3 > c2,
      found ? `at y ${found.y} (slot ${found.r.map(Math.round).join('..')}): ${c1} → ${c2}, back at why → ${c3}` : 'no scroll position with the slot off screen');
    await ctx.close();
  }
  { // rotation
    const { ctx, p } = await open(b, 390, 844);
    await p.waitForFunction(() => window.__glReady, null, { timeout: 60000 });
    const vs = [await p.evaluate(() => window.__view())];
    await p.setViewportSize({ width: 740, height: 360 }); await wait(p, 1000); vs.push(await p.evaluate(() => window.__view()));
    await p.setViewportSize({ width: 390, height: 844 }); await wait(p, 1000); vs.push(await p.evaluate(() => window.__view()));
    ok('mask rotation: the view height follows the orientation', vs[0].FH === 844 && vs[1].FH === 360 && vs[1].FW === 740 && vs[2].FH === 844, vs.map(v => `${v.FW}x${v.FH}`).join(' → '));
    await ctx.close();
  }
  { // loops: three hide/show cycles
    const { ctx, p } = await open(b, 1440, 900);
    await p.waitForFunction(() => window.__glReady, null, { timeout: 60000 }); await wait(p, 800);
    const rate = () => p.evaluate(() => new Promise(res => { let ticks = 0; const f0 = window.__frames(), t0 = performance.now();
      const tick = () => { ticks++; if (performance.now() - t0 < 2500) requestAnimationFrame(tick); else res((window.__frames() - f0) / ticks); }; requestAnimationFrame(tick); }));
    const before = await rate();
    for (let i = 0; i < 3; i++) await p.evaluate(() => new Promise(res => {
      const set = v => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => v }); document.dispatchEvent(new Event('visibilitychange')); };
      set(true); setTimeout(() => { set(false); setTimeout(res, 200); }, 150); }));
    const after = await rate();
    ok('mask loops: one frame per tick after three hide/show cycles', after <= 1.15 && before <= 1.15, `frames per tick ${before.toFixed(2)} → ${after.toFixed(2)}`);
    await ctx.close();
  }
  { // restore under reduced motion
    const { ctx, p } = await open(b, 1440, 900, { reduce: true });
    await p.waitForFunction(() => window.__glReady, null, { timeout: 60000 }); await wait(p, 800);
    const f = await p.evaluate(() => new Promise(res => {
      const c = document.getElementById('gl'), gl = c.getContext('webgl2'), ext = gl.getExtension('WEBGL_lose_context'), f0 = window.__frames();
      c.addEventListener('webglcontextlost', () => setTimeout(() => ext.restoreContext(), 50), { once: true });
      c.addEventListener('webglcontextrestored', () => setTimeout(() => res({ f0, f1: window.__frames() }), 800), { once: true });
      ext.loseContext();
    }));
    ok('mask restore (reduced motion): redrawn without a scroll', f.f1 > f.f0, JSON.stringify(f));
    await ctx.close();
  }
  for (const [dpr, want] of [[2, 'back to 2, capped'], [1.5, 'never tries']]) { // step-down on stubbed 30 Hz frame times
    const { ctx, p } = await open(b, 1000, 700, { dpr, init: `(() => { const raf = window.requestAnimationFrame.bind(window); let fake = 0;
      window.requestAnimationFrame = cb => raf(() => { fake += 33.4; cb(fake); }); })();` });
    await p.waitForFunction(() => window.__glReady, null, { timeout: 60000 });
    await p.waitForFunction(() => window.__frames() > 300, null, { timeout: 240000 }).catch(() => {});
    const q = await p.evaluate(() => Object.assign(window.__quality(), { frames: window.__frames() }));
    ok(`mask step-down, DPR ${dpr}, steady 30 Hz: ${want}`, dpr === 2 ? q.quality === 2 && q.capped : q.quality === 2 && !q.capped, JSON.stringify(q));
    await ctx.close();
  }
}

(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  if (kind === 'scene') await scene(b); else await mask(b);
  await b.close();
  console.log(`\n${checks.filter(c => c.pass).length}/${checks.length} checks passed`);
})();
