// V5: пересечения рыб — обе метрики ревью за один прогон (шаг 10 × 1/30 с, 4 мин по умолчанию)
//  vis: доля сэмплов с парой (не стая, не anthias, не пара HOME) перекрытие ≥ 50% меньшей рамки и |dz| < 0.1
//  rob: доля сэмплов с парой (не одна стая одного вида) перекрытие > 40% и |dz|·D < 0.25·min(L0); + самая долгая пара (с)
//  clown: доля сэмплов, где оба клоуна HOME и перекрытие > 40%
'use strict';
const L = require('./lib');
const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, seed: 1, minutes: 4, every: 10 });
(async () => {
  const env = await L.openEngine(o);
  const { page, cap } = await L.newPage(env);
  await L.gotoReady(page, env.url, 90000);
  const res = await page.evaluate(async (minutes, every) => {
    const A = window.__aq, D = A.camera().D, N = Math.round((minutes * 60 * 30) / every), dtS = every / 30;
    const out = { samples: N, vis50: 0, vis30: 0, rob: 0, clownBoth: 0, clownOv: 0, pairsVis: {}, pairsRob: {}, longest: { s: 0, k: '' }, worst: [] };
    const run = {};
    for (let s = 0; s < N; s++) {
      const r = A.step(1 / 30, every, { render: false }); if (r && r.then) await r;
      const F = A.fish().filter((f) => f.visible && f.onScreen && f.state !== 'OFFSTAGE' && f.bbox);
      let v50 = false, v30 = false, rb = false; const seen = {};
      const clowns = F.filter((f) => f.id === 'clownfish' && f.state === 'HOME');
      for (let i = 0; i < F.length; i++) for (let j = i + 1; j < F.length; j++) {
        const a = F[i], b = F[j];
        const ix = Math.min(a.bbox[2], b.bbox[2]) - Math.max(a.bbox[0], b.bbox[0]), iy = Math.min(a.bbox[3], b.bbox[3]) - Math.max(a.bbox[1], b.bbox[1]);
        if (ix <= 0 || iy <= 0) continue;
        const sa = Math.max(1, Math.min((a.bbox[2] - a.bbox[0]) * (a.bbox[3] - a.bbox[1]), (b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1])));
        const fr = (ix * iy) / sa, dz = Math.abs(a.z - b.z), k = [a.id, b.id].sort().join('+');
        const sameSchool = a.school && b.school && a.id === b.id;
        const homePair = a.state === 'HOME' && b.state === 'HOME';
        if (!sameSchool && !homePair && a.id !== 'anthias' && b.id !== 'anthias' && dz < 0.1) {
          if (fr > 0.3) v30 = true;
          if (fr >= 0.5) { v50 = true; out.pairsVis[k] = (out.pairsVis[k] || 0) + 1; if (out.worst.length < 20 && fr > 0.6) out.worst.push({ t: +A.stats().simT.toFixed(1), k, fr: +fr.toFixed(2), dz: +dz.toFixed(3), sa: a.state, sb: b.state }); }
        }
        if (!sameSchool && fr > 0.4 && dz * D < 0.25 * Math.min(a.L0, b.L0)) {
          rb = true; out.pairsRob[k] = (out.pairsRob[k] || 0) + 1; seen[k] = 1;
          run[k] = (run[k] || 0) + dtS; if (run[k] > out.longest.s) out.longest = { s: +run[k].toFixed(2), k, t: +A.stats().simT.toFixed(1) };
        }
      }
      for (const k in run) if (!seen[k]) run[k] = 0;
      if (clowns.length === 2) {
        out.clownBoth++;
        const a = clowns[0], b = clowns[1];
        const ix = Math.min(a.bbox[2], b.bbox[2]) - Math.max(a.bbox[0], b.bbox[0]), iy = Math.min(a.bbox[3], b.bbox[3]) - Math.max(a.bbox[1], b.bbox[1]);
        const sa = Math.max(1, Math.min((a.bbox[2] - a.bbox[0]) * (a.bbox[3] - a.bbox[1]), (b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1])));
        if (ix > 0 && iy > 0 && (ix * iy) / sa > 0.4) out.clownOv++;
      }
      if (v50) out.vis50++; if (v30) out.vis30++; if (rb) out.rob++;
    }
    out.vis50Frac = +(out.vis50 / N).toFixed(3); out.vis30Frac = +(out.vis30 / N).toFixed(3); out.robFrac = +(out.rob / N).toFixed(3);
    out.clownOvFrac = +(out.clownOv / N).toFixed(3); out.clownOvOfBoth = +(out.clownOv / Math.max(1, out.clownBoth)).toFixed(3);
    return out;
  }, o.minutes, o.every);
  console.log(JSON.stringify(res, null, 1));
  L.report(cap.errors, cap.warnings, true);
  await L.finish(env);
})().catch((e) => { console.error(e); process.exit(1); });
