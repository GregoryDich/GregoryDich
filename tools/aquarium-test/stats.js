// Статистика кадра из window.__aq.stats(), усреднённая по K шагам (каждый шаг рисуется и показывается).
//   node stats.js [--steps 300 --dt 1/30 --warm 60 --w 1920 --h 1200 --dpr 1 --seed 1] [--http] [--q ...] [--out stats.json]
// Гейты SPEC §5 мерятся так: 1920×1200, ?test=1&nofilter=1&seed=N, 300 шагов по 1/30 с.
// JS-мс — performance.now() вокруг тела кадра; в headless (программный растр) — только для СРАВНЕНИЯ.
'use strict';
const fs = require('fs');
const path = require('path');
const L = require('./lib');

(async () => {
  const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, seed: 1, steps: 300, dt: 1 / 30, warm: 60 });
  const env = await L.openEngine(o);
  let result;
  try {
    const { page, cap } = await L.newPage(env);
    await L.gotoReady(page, env.url);
    if (o.warm > 0) await L.stepFrames(page, o.dt, o.warm | 0);       // прогрев JIT и кэшей
    await page.evaluate(() => window.__aq.resetStats());
    const s = await L.stepFrames(page, o.dt, o.steps | 0);
    const r = (x) => Math.round(x * 1000) / 1000;
    const round = (obj) => Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, typeof v === 'number' ? r(v) : v]));
    result = { url: env.url, mode: o.http ? 'http' : 'file', viewport: env.vp, steps: o.steps, dt: o.dt, frames: s.frames,
      avg: round(s.avg), max: round(s.max), last: round(s.last), backing: s.backing, RS: r(s.RS), dpr: s.dpr,
      quality: s.quality, photo: s.photo, sceneFromFile: s.sceneFromFile, hasFilter: s.hasFilter,
      fish: s.fish, bubbles: s.bubbles, errors: cap.errors, warnings: cap.warnings };
    console.log(JSON.stringify(result, null, 1));
    if (o.out) { const p = path.resolve(String(o.out)); L.ensureDir(path.dirname(p)); fs.writeFileSync(p, JSON.stringify(result, null, 1)); }
    L.report(cap.errors, cap.warnings, o['allow-errors']);
  } finally { await L.finish(env); }
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
