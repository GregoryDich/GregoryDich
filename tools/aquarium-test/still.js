// Детерминированный кадр: ?test=1&nofilter=1&seed=N, N шагов по dt через window.__aq.step → PNG.
//   node still.js --out shot.png [--w 1920 --h 1200 --dpr 1 --seed 1 --steps 90 --dt 1/30]
//                 [--q "debug=1&nobg=1"] [--http] [--root ../../aquarium] [--clip x,y,w,h] [--allow-errors]
// Печатает JSON-сводку (url, stats последнего кадра, scene) в stdout, ошибки — в stderr; код 2 при ошибках.
'use strict';
const path = require('path');
const L = require('./lib');

(async () => {
  const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, seed: 1, steps: 90, dt: 1 / 30, out: path.join(__dirname, 'out', 'still.png') });
  const env = await L.openEngine(o);
  try {
    const { page, cap } = await L.newPage(env);
    await L.gotoReady(page, env.url);
    // быстрый прогон без отрисовки, последний шаг — с отрисовкой
    await page.evaluate((dt, n) => window.__aq.step(dt, n, { render: 'last' }), o.dt, Math.max(1, o.steps | 0));
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => r())));
    const out = path.resolve(o.out); L.ensureDir(path.dirname(out));
    await page.screenshot({ path: out, clip: L.clipOpt(o) });
    const info = await page.evaluate(() => {
      const s = window.__aq.stats(), sc = window.__aq.scene();
      return { stats: { last: s.last, backing: s.backing, RS: s.RS, dpr: s.dpr, quality: s.quality.level, photo: s.photo,
        sceneFromFile: s.sceneFromFile, fish: s.fish, simT: s.simT },
        scene: { backdrop: sc.backdrop, bandH: sc.bandH, visibleBX: sc.visibleBX, visibleBY: sc.visibleBY, horizon: sc.horizon } };
    });
    console.log(JSON.stringify({ out, url: env.url, viewport: env.vp, steps: o.steps, dt: o.dt, ...info, errors: cap.errors }, null, 1));
    L.report(cap.errors, cap.warnings, o['allow-errors']);
  } finally { await L.finish(env); }
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
