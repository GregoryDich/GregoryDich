// «Равный метод» сравнения JS-времени кадра для ЛЮБОЙ версии движка (в т.ч. старой, без window.__aq):
// requestAnimationFrame подменяется до загрузки страницы, харнесс сам вызывает колбэк кадра
// с синтетическим временем (шаг dt) и мерит performance.now() вокруг ВСЕГО колбэка; между кадрами —
// настоящий rAF, чтобы кадр успел показаться. Тестовый режим (?test=1) НЕ включается — счётчиков нет.
//   node bench.js [--root dir] [--w 1920 --h 1200] [--frames 300 --warm 60 --dt 1/30 --runs 3]
//                 [--q "seed=1&nofilter=1&gov=0"] [--strip-filter] [--seed-math 1] [--wait 4000] [--out bench.json]
// --strip-filter  удаляет ctx.filter из прототипа до загрузки (старый движок тогда идёт по пути WebKit: без фильтров)
// --seed-math N   сидирует Math.random (для старого движка, где ГПСЧ ещё не было)
'use strict';
const fs = require('fs');
const path = require('path');
const L = require('./lib');

function inject(stripFilter, seedMath) {
  window.__bench = { cb: null };
  window.__origRAF = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => { window.__bench.cb = cb; return 1; };
  if (stripFilter) delete CanvasRenderingContext2D.prototype.filter;
  if (seedMath !== null) {
    let s = seedMath | 0;
    Math.random = () => { s = (s + 0x6D2B79F5) | 0; let q = s; q = Math.imul(q ^ (q >>> 15), q | 1); q ^= q + Math.imul(q ^ (q >>> 7), q | 61); return ((q ^ (q >>> 14)) >>> 0) / 4294967296; };
  }
}

(async () => {
  const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, frames: 300, warm: 60, dt: 1 / 30, runs: 3, wait: 4000,
    q: 'seed=1&nofilter=1&gov=0' });
  const runs = [];
  let errors = [];
  for (let run = 0; run < o.runs; run++) {
    const env = await L.openEngine(Object.assign({}, o, { nofilter: false, seed: false }), { test: false });
    try {
      const { page, cap } = await L.newPage(env, { inject: { fn: inject, args: [!!o['strip-filter'], o['seed-math'] === undefined ? null : +o['seed-math']] } });
      await page.goto(env.url, { waitUntil: 'load' });
      // у нового движка есть ready(); у старого — просто ждём загрузку картинок
      const hasReady = await page.evaluate(() => !!(window.__aq && window.__aq.ready));
      if (hasReady) await page.waitForFunction(() => window.__aq.ready(), { timeout: 30000, polling: 100 });
      else await new Promise((r) => setTimeout(r, o.wait));
      const times = await page.evaluate(async (frames, warm, dtMs) => {
        let now = performance.now();
        const out = [];
        for (let i = 0; i < warm + frames; i++) {
          const cb = window.__bench.cb; window.__bench.cb = null;
          if (!cb) throw new Error('кадр не запросил requestAnimationFrame');
          now += dtMs;
          const t0 = performance.now(); cb(now); const t1 = performance.now();
          if (i >= warm) out.push(t1 - t0);
          await new Promise((r) => window.__origRAF(() => r()));
        }
        return out;
      }, o.frames | 0, o.warm | 0, o.dt * 1000);
      const sorted = times.slice().sort((a, b) => a - b);
      const mean = times.reduce((a, b) => a + b, 0) / times.length;
      runs.push({ mean, median: sorted[sorted.length >> 1], p90: sorted[Math.floor(sorted.length * 0.9)] });
      errors = errors.concat(cap.errors.map((e) => `[run ${run}] ${e}`));
    } finally { await L.finish(env); }
  }
  const r3 = (x) => Math.round(x * 1000) / 1000;
  const means = runs.map((r) => r.mean).sort((a, b) => a - b);
  const res = { root: path.resolve(o.root || L.DEFAULT_ROOT), viewport: `${o.w}x${o.h}@${o.dpr}`, frames: o.frames, dt: o.dt, q: o.q,
    stripFilter: !!o['strip-filter'], runs: runs.map((r) => ({ mean: r3(r.mean), median: r3(r.median), p90: r3(r.p90) })),
    jsMsMedianOfMeans: r3(means[means.length >> 1]), errors };
  console.log(JSON.stringify(res, null, 1));
  if (o.out) { const p = path.resolve(String(o.out)); L.ensureDir(path.dirname(p)); fs.writeFileSync(p, JSON.stringify(res, null, 1)); }
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
