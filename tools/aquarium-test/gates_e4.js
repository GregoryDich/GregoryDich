// Гейт G4 (этап E4 «интеграция», SPEC §5): одним прогоном — всё, кроме JS-времени (его меряют stats.js /
// abtime.js попеременно с прошлым движком, см. README):
//   • ошибки консоли/запросов: file:// и http, кадр с ?debug=2 и фолбэк ?nobg=1;
//   • drawImage / setTransform за 300 шагов (обычно) и за 450 шагов во время автокормёжки (пик — корм);
//   • оценка памяти на один экран при буфере 3840×2160: все холсты (кроме главного) + декодированные
//     картинки (сцена, задник, маска; исходники рыб после запекания отпускаются — отдельной строкой) и
//     отдельно — главный холст (×2: буфер + копия композитора);
//   • первый полный кадр: от начала навигации до ready() + отрисовка кадра (test-режим) и в обычном
//     режиме (настоящий rAF): первый кадр после ready().
//   node gates_e4.js --out DIR [--w 1920 --h 1200 --dpr 1 --seed 1] [--skip-mem] [--skip-http]
// Пишет DIR/gates_e4.json; выход 2 — если провален хоть один гейт или были ошибки страницы.
'use strict';
const fs = require('fs');
const path = require('path');
const L = require('./lib');

// счёт холстов и картинок (до загрузки страницы)
function memHook() {
  window.__cv = []; window.__im = [];
  const ce = Document.prototype.createElement;
  Document.prototype.createElement = function (n) { const el = ce.apply(this, arguments); if (String(n).toLowerCase() === 'canvas') window.__cv.push(el); return el; };
  const OI = window.Image;
  window.Image = function (w, h) { const im = arguments.length ? new OI(w, h) : new OI(); window.__im.push(im); return im; };
  window.Image.prototype = OI.prototype;
}

async function countsRun(o, label, feed) {
  const env = await L.openEngine(o);
  try {
    const { page, cap } = await L.newPage(env);
    await L.gotoReady(page, env.url);
    await page.evaluate(() => window.__aq.step(1 / 30, 60, { render: 'last' }));
    if (feed) await page.evaluate(() => { window.__aq.feed(); window.__aq.step(1 / 30, 60, { render: 'last' }); });
    await page.evaluate(() => window.__aq.resetStats());
    const n = feed ? 450 : 300;
    const st = await L.stepFrames(page, 1 / 30, n);
    const extra = await page.evaluate(() => ({ flakes: window.__aq.stats().flakes, groups: window.__aq.groups().length }));
    return { label, frames: n, avg: st.avg, max: st.max, extra, errors: cap.errors };
  } finally { await L.finish(env); }
}

async function memRun(o) {
  const vo = Object.assign({}, o, { w: 3840, h: 2160, dpr: 1 });
  const env = await L.openEngine(vo);
  try {
    const { page, cap } = await L.newPage(env, { inject: { fn: memHook } });
    await L.gotoReady(page, env.url);
    await page.evaluate(() => { window.__aq.step(1 / 30, 120, { render: true }); window.__aq.feed(); window.__aq.step(1 / 30, 240, { render: true }); });
    const m = await page.evaluate(() => {
      const main = document.getElementById('tank');
      let cv = 0, ncv = 0, big = [];
      for (const c of window.__cv) { if (c === main) continue; const b = c.width * c.height * 4; cv += b; ncv++; if (b > 2e6) big.push([c.width, c.height]); }
      let im = 0, imFish = 0, nim = 0;
      for (const i of window.__im) {
        if (!(i.complete && i.naturalWidth > 0)) continue;
        const b = i.naturalWidth * i.naturalHeight * 4, src = String(i.currentSrc || i.src);
        if (/\/fish\//.test(src)) imFish += b; else { im += b; nim++; }
      }
      return { mainW: main.width, mainH: main.height, mainBytes: main.width * main.height * 4, canvases: ncv, canvasBytes: cv, bigCanvases: big,
        images: nim, imageBytes: im, fishSourceBytes: imFish };
    });
    const MB = (b) => Math.round((b / 1048576) * 10) / 10;
    const off = m.canvasBytes + m.imageBytes;
    return { viewport: '3840x2160@1', backing: [m.mainW, m.mainH], canvases: m.canvases, canvasMB: MB(m.canvasBytes), bigCanvases: m.bigCanvases,
      images: m.images, imageMB: MB(m.imageBytes), fishSourceMB_released: MB(m.fishSourceBytes),
      offscreenMB: MB(off), mainBuffersMB: MB(2 * m.mainBytes), totalMB: MB(off + 2 * m.mainBytes),
      totalWithFishSourcesMB: MB(off + 2 * m.mainBytes + m.fishSourceBytes), errors: cap.errors };
  } finally { await L.finish(env); }
}

async function firstFrame(o) {
  const res = {};
  { // test-режим: ready + один кадр
    const env = await L.openEngine(o);
    try {
      const { page, cap } = await L.newPage(env);
      await page.goto(env.url, { waitUntil: 'load' });
      await page.waitForFunction(() => window.__aq && window.__aq.ready(), { timeout: 30000, polling: 5 });
      res.test = await page.evaluate(() => { const t0 = performance.now(); window.__aq.render(); const t1 = performance.now(); return { readyMs: t0, renderMs: t1 - t0, firstFrameMs: t1 }; });
      res.testErrors = cap.errors;
    } finally { await L.finish(env); }
  }
  { // обычный режим (rAF): первый кадр после ready()
    const env = await L.openEngine(Object.assign({}, o, { test: false }), { test: false });
    try {
      const { page, cap } = await L.newPage(env, { inject: { fn: () => {
        const raf = window.requestAnimationFrame.bind(window);
        window.__ff = null;
        window.requestAnimationFrame = (cb) => raf((ts) => { const ready = window.__aq && window.__aq.ready && window.__aq.ready(); cb(ts); if (ready && window.__ff === null) window.__ff = performance.now(); });
      } } });
      await page.goto(env.url, { waitUntil: 'load' });
      await page.waitForFunction(() => window.__ff !== null, { timeout: 30000, polling: 10 });
      res.raf = { firstFrameMs: await page.evaluate(() => window.__ff) };
      res.rafErrors = cap.errors;
    } finally { await L.finish(env); }
  }
  return res;
}

async function errorsRun(o, extraQ, http) {
  const oo = Object.assign({}, o, { http, q: extraQ });
  const env = await L.openEngine(oo);
  try {
    const { page, cap } = await L.newPage(env);
    await L.gotoReady(page, env.url);
    await page.evaluate(() => window.__aq.step(1 / 30, 90, { render: 'last' }));
    const info = await page.evaluate(() => ({ photo: window.__aq.stats().photo, items: window.__aq.sceneItems().length }));
    return { q: extraQ || '', http: !!http, info, errors: cap.errors };
  } finally { await L.finish(env); }
}

(async () => {
  const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, seed: 1, out: path.join(__dirname, 'out', 'g4') });
  const outDir = L.ensureDir(path.resolve(String(o.out)));
  const r = { viewport: `${o.w}x${o.h}@${o.dpr}`, seed: o.seed };
  r.errorRuns = [];
  for (const http of o['skip-http'] ? [false] : [false, true]) {
    for (const q of ['debug=2', 'nobg=1', '']) r.errorRuns.push(await errorsRun(o, q, http));
  }
  r.normal = await countsRun(o, 'normal', false);
  r.feeding = await countsRun(o, 'feeding', true);
  if (!o['skip-mem']) r.memory = await memRun(o);
  r.firstFrame = await firstFrame(o);
  const allErr = [].concat(...r.errorRuns.map((e) => e.errors), r.normal.errors, r.feeding.errors, r.memory ? r.memory.errors : [],
    r.firstFrame.testErrors || [], r.firstFrame.rafErrors || []);
  const g = (name, target, measured, pass) => ({ name, target, measured, pass });
  r.gates = [
    g('errors (file:// + http, debug=2, nobg, counts, memory, first frame)', '0', String(allErr.length), allErr.length === 0),
    g('drawImage typical (avg / max, 300 steps)', '<= 850', `${r.normal.avg.drawImage.toFixed(1)} / ${r.normal.max.drawImage}`, r.normal.avg.drawImage <= 850),
    g('drawImage while feeding (max, 450 steps)', '<= 1100', `${r.feeding.max.drawImage} (avg ${r.feeding.avg.drawImage.toFixed(1)})`, r.feeding.max.drawImage <= 1100),
    g('setTransform (max normal / feeding)', '<= 700', `${r.normal.max.setTransform} / ${r.feeding.max.setTransform}`, Math.max(r.normal.max.setTransform, r.feeding.max.setTransform) <= 700),
    g('gradients / patterns / getImageData / filter per frame (max)', '0', [r.normal.max.gradients, r.normal.max.patterns, r.normal.max.getImageData, r.normal.max.filter].join('/'),
      !r.normal.max.gradients && !r.normal.max.patterns && !r.normal.max.getImageData && !r.normal.max.filter),
  ];
  if (r.memory) r.gates.push(g('memory per view at 3840x2160 (offscreens+images / incl. main buffers)', '<= 120 / <= 250 MB',
    `${r.memory.offscreenMB} / ${r.memory.totalMB} MB`, r.memory.offscreenMB <= 120 && r.memory.totalMB <= 250));
  r.gates.push(g('first complete frame (test: ready+render / rAF)', '<= 1500 ms',
    `${r.firstFrame.test.firstFrameMs.toFixed(0)} / ${r.firstFrame.raf.firstFrameMs.toFixed(0)} ms`, Math.max(r.firstFrame.test.firstFrameMs, r.firstFrame.raf.firstFrameMs) <= 1500));
  r.allPass = r.gates.every((x) => x.pass);
  r.errors = allErr;
  fs.writeFileSync(path.join(outDir, 'gates_e4.json'), JSON.stringify(r, null, 1));
  console.log(JSON.stringify({ gates: r.gates, allPass: r.allPass, memory: r.memory, firstFrame: r.firstFrame }, null, 1));
  L.report(allErr, [], true);
  if (!r.allPass) process.exitCode = 2;
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
