// Проверка регулятора качества и режимов питания (без test-режима): rAF подменяется, колбэк кадра
// вызывается с синтетическими интервалами; читаем __aq.stats().quality/governor (?debug=1 → счётчики).
//   node governor.js     → таблица ступеней; ожидается: 5 с плохих кадров → ступень вниз, 30 с хороших → вверх,
//   «плохо» сразу после подъёма → recover ×2; paused → 0 кадров; low @60 Гц → 30 к/с; high → 60 к/с.
'use strict';
const L = require('./lib');
function inject() {
  window.__bench = { cb: null };
  window.__origRAF = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (cb) => { window.__bench.cb = cb; return 1; };
}
(async () => {
  const env = await L.openEngine({ w: 960, h: 600, q: 'debug=1&seed=3' }, { test: false });
  try {
    const { page, cap } = await L.newPage(env, { inject: { fn: inject } });
    await page.goto(env.url, { waitUntil: 'load' });
    await page.waitForFunction(() => window.__aq.ready(), { timeout: 30000 });
    const res = await page.evaluate(async () => {
      let now = performance.now();
      const log = [];
      const run = (intervalMs, seconds, tag) => {
        const n = Math.round(seconds * 1000 / intervalMs);
        for (let i = 0; i < n; i++) {
          now += intervalMs;
          const cb = window.__bench.cb; window.__bench.cb = null; cb(now);
        }
        const s = window.__aq.stats();
        log.push({ tag, level: s.quality.level, q: s.quality, p90: +s.governor.p90.toFixed(1), recover: s.governor.recover, frames: s.total, backing: s.backing });
      };
      run(16.7, 3, 'good 3s');
      run(30, 4, 'bad 4s (ещё нет 5 с)');
      run(30, 2, 'bad +2s → ступень 1');
      run(30, 5, 'bad +5s → ступень 2');
      run(30, 15, 'bad +15s → ступень 4 (RS×0.85)');
      run(16.7, 31, 'good 31s → ступень 3');
      run(30, 6, 'плохо сразу после подъёма → вниз и recover×2');
      // питание: paused — ни одного кадра; low — каждый 2-й vsync при 60 Гц
      window.aquariumSetPower('paused'); const f0 = window.__aq.stats().total; run(16.7, 1, 'paused 1s');
      const f1 = window.__aq.stats().total;
      window.aquariumSetPower('low'); run(16.7, 2, 'low 2s @60Hz vsync');
      const f2 = window.__aq.stats().total;
      window.aquariumSetPower('high'); run(16.7, 1, 'high 1s');
      const f3 = window.__aq.stats().total;
      return { log, pausedFrames: f1 - f0, lowFramesIn2s: f2 - f1, highFramesIn1s: f3 - f2 };
    });
    console.log(JSON.stringify(res, null, 1));
    L.report(cap.errors, cap.warnings, false);
  } finally { await L.finish(env); }
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
