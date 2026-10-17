// node abtime.js --a ROOT_A [--b ROOT_B = ../../aquarium] [--rounds 20 --block 20] — как stats.js (шаг + показ кадра),
// два движка блоками по очереди; по каждому кадру last.jsMs; печатает p25/медиану/среднее всех кадров.
// Под нагрузкой соседних процессов средние портят выбросы — сравнивать медиану и p25 (delta.*).
// Корень A — каталог с index.html и ссылками на assets/, fish/, scene/ (как work/e1/g0root).
'use strict';
const path = require('path');
const L = require('./lib');
(async () => {
  const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, seed: 1, dt: 1 / 30, rounds: 20, block: 20, b: L.DEFAULT_ROOT });
  if (!o.a) { console.error('нужен --a ROOT (например, копия движка предыдущего этапа)'); process.exit(1); }
  const env = await L.openEngine(Object.assign({}, o, { root: o.a }));
  try {
    const q = L.buildQuery(o);
    const urls = { A: `file://${path.resolve(o.a)}/index.html?${q}`, B: `file://${path.resolve(o.b)}/index.html?${q}` };
    const pages = {};
    for (const k of ['A', 'B']) { const { page } = await L.newPage(env); await L.gotoReady(page, urls[k]); await L.stepFrames(page, o.dt, 60); pages[k] = page; }
    const acc = { A: [], B: [] };
    for (let r = 0; r < o.rounds; r++) for (const k of (r % 2 ? ['B', 'A'] : ['A', 'B'])) {
      const p = pages[k];
      await p.bringToFront();
      const v = await p.evaluate(async (dt, n) => {
        const out = [];
        for (let i = 0; i < n; i++) { window.__aq.step(dt, 1); out.push(window.__aq.stats().last.jsMs); await new Promise((r) => requestAnimationFrame(() => r())); }
        return out;
      }, o.dt, o.block);
      acc[k].push(...v);
    }
    const qn = (a, p) => { const b = a.slice().sort((x, y) => x - y); return +b[Math.floor(p * (b.length - 1))].toFixed(3); };
    const out = {};
    for (const k in acc) out[k] = { root: k === 'A' ? o.a : o.b, n: acc[k].length, p25: qn(acc[k], 0.25), median: qn(acc[k], 0.5), mean: +(acc[k].reduce((a, b) => a + b, 0) / acc[k].length).toFixed(3) };
    out.delta = { p25: +(out.B.p25 - out.A.p25).toFixed(3), median: +(out.B.median - out.A.median).toFixed(3), mean: +(out.B.mean - out.A.mean).toFixed(3) };
    console.log(JSON.stringify(out, null, 1));
  } finally { await L.finish(env); }
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
