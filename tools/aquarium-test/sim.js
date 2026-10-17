// Гейт G3 (этап E3, SPEC §5): 10-минутная детерминированная симуляция рыб шагами __aq.step(1/30).
// Всё считается внутри страницы (без пересылки кадров), отрисовка — каждый --renderEvery шаг (счётчики drawImage).
//   node sim.js [--minutes 10 --dt 1/30 --seed 1 --w 1920 --h 1200 --renderEvery 10 --out sim.json --q ...]
// Метрики (по видимым рыбам; «видима» = на экране, не за кадром и не за окклюдером):
//   • скачок за шаг: смещение центра рамки тела и опорной точки, max и доля > 3% W;
//   • ширина: min (x-протяжённость тела / экранная длина) — гейт ≥ 0.15;
//   • развороты: длительности (гейт 0.35–0.9 с);
//   • |рыскание| вне разворота (гейт ≤ 32°);
//   • скорость в CRUISE (не на развороте): доля шагов в 0.3–1.5 BL/s (гейт ≥ 95%);
//   • масштаб 1/z видимых: диапазон (гейт покрывает 0.45–1.0);
//   • видимость: средняя доля видимых рыб (≥ 70%), у каждой рыбы скрыто < 25% времени;
//   • сюжет: наибольший промежуток между битами режиссёра (≤ 60 с);
//   • drawImage рыб (CNT.e3Fish): среднее и максимум по отрисованным кадрам (≤ 420);
//   • «глубинные противоречия»: секунды, когда риф поправлял z рыбы напрямую (f.viol).
'use strict';
const fs = require('fs');
const path = require('path');
const L = require('./lib');

(async () => {
  const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, seed: 1, minutes: 10, dt: 1 / 30, renderEvery: 10,
    out: path.join(__dirname, 'out', 'sim.json') });
  const out = path.resolve(o.out); L.ensureDir(path.dirname(out));
  const env = await L.openEngine(o);
  let errors = [], warnings = [], res = null;
  try {
    const { page, cap } = await L.newPage(env);
    errors = cap.errors; warnings = cap.warnings;
    await L.gotoReady(page, env.url, 60000);
    const steps = Math.round((o.minutes * 60) / o.dt);
    const t0 = Date.now();
    // кусками, чтобы не упереться в таймаут протокола и печатать прогресс
    await page.evaluate((dt, steps, renderEvery) => {
      const A = window.__aq, S = A.states, N = A.fish().length, W = innerWidth;
      const iCruise = S.indexOf('CRUISE');
      window.__sim = {
        dt, steps, renderEvery, done: 0, W, N, iCruise,
        prev: null, jumpMaxC: 0, jumpMaxP: 0, jumpsOver: 0, jumpSamples: 0, jumpWorst: null,
        widthMin: 9, widthUnder: 0, widthSamples: 0, widthWorst: null,
        turnStart: new Float64Array(N).fill(-1), turns: [], turnsCut: 0, turnByState: {}, turnByFish: new Float64Array(N),
        yawMax: 0, yawOver: 0, yawSamples: 0,
        cruiseIn: 0, cruiseN: 0, cruiseLow: 0, cruiseHigh: 0, shoalIn: 0, shoalN: 0,
        scaleMin: 9, scaleMax: 0, scaleHist: new Float64Array(24),
        visSum: 0, visSteps: 0, hiddenSteps: new Float64Array(N), stateSteps: {},
        di: [], diFog: [], diLit: [], diAll: [], jsMs: [],
        viol: null,
      };
    }, o.dt, steps, o.renderEvery);
    const chunk = 1500;
    for (let done = 0; done < steps; done += chunk) {
      await page.evaluate((n) => {
        const A = window.__aq, s = window.__sim, S = A.states;
        for (let q = 0; q < n && s.done < s.steps; q++, s.done++) {
          const render = s.done % s.renderEvery === 0;
          A.step(s.dt, 1, { render });
          if (render) { const st = A.stats(); s.di.push(st.last.e3Fish); s.diFog.push(st.last.e3Fog); s.diLit.push(st.last.e3Lit); s.diAll.push(st.last.drawImage); s.jsMs.push(st.last.jsMs); }
          const g = A.fishGeom(), N = s.N, K = 14, t = (s.done + 1) * s.dt;
          let vis = 0;
          for (let i = 0; i < N; i++) {
            const k = i * K, visible = g[k] > 0.5, turning = g[k + 6] > 0.5, state = g[k + 9] | 0, z = g[k + 10];
            const sn = S[state]; s.stateSteps[sn] = (s.stateSteps[sn] || 0) + 1;
            if (visible) vis++; else s.hiddenSteps[i]++;
            // скачки: только если рыба была видна и в прошлом шаге
            if (s.prev && visible && s.prev[k] > 0.5) {
              const dc = Math.hypot(g[k + 3] - s.prev[k + 3], g[k + 4] - s.prev[k + 4]);
              const dp = Math.hypot(g[k + 1] - s.prev[k + 1], g[k + 2] - s.prev[k + 2]);
              s.jumpSamples++;
              if (dc > s.jumpMaxC) { s.jumpMaxC = dc; s.jumpWorst = { t, i, state: sn, dc, dp }; }
              if (dp > s.jumpMaxP) s.jumpMaxP = dp;
              if (Math.max(dc, dp) > 0.03 * s.W) s.jumpsOver++;
            }
            if (visible) {
              const wf = g[k + 5];
              s.widthSamples++;
              if (wf < s.widthMin) { s.widthMin = wf; s.widthWorst = { t, i, state: sn, turning, wf }; }
              if (wf < 0.15) s.widthUnder++;
              const sc = 1 / z;
              if (sc < s.scaleMin) s.scaleMin = sc; if (sc > s.scaleMax) s.scaleMax = sc;
              s.scaleHist[Math.min(23, Math.max(0, Math.floor((sc - 0.3) / 0.05)))]++;
            }
            // развороты
            if (turning && s.turnStart[i] < 0) { s.turnByState[sn] = (s.turnByState[sn] || 0) + 1; s.turnByFish[i]++; s.turnStart[i] = t; }
            if (!turning && s.turnStart[i] >= 0) { if (g[k + 11] > 0.5) s.turnsCut++; else s.turns.push(t - s.turnStart[i]); s.turnStart[i] = -1; }   // оборван уходом за кадр — не в счёт
            if (!turning && g[k + 11] < 0.5) {
              const y = Math.abs(g[k + 7]);
              s.yawSamples++; if (y > s.yawMax) s.yawMax = y; if (y > 32) s.yawOver++;
            }
            if (!turning && state === s.iCruise && visible) {
              const v = g[k + 8]; s.cruiseN++;
              if (v >= 0.3 && v <= 1.5) s.cruiseIn++; else if (v < 0.3) s.cruiseLow++; else s.cruiseHigh++;
            }
            if (!turning && sn === 'SHOAL' && visible) { const v = g[k + 8]; s.shoalN++; if (v >= 0.3 && v <= 1.5) s.shoalIn++; }
          }
          s.visSum += vis / N; s.visSteps++;
          s.prev = g;
          if (s.done + 1 === s.steps) s.viol = Array.from({ length: N }, (_, i) => g[i * K + 13]);
        }
      }, chunk);
      process.stderr.write(`  ${Math.min(steps, done + chunk)}/${steps} steps (${((Date.now() - t0) / 1000).toFixed(0)} s)\n`);
    }
    res = await page.evaluate(() => {
      const s = window.__sim, A = window.__aq, fish = A.fish(), dir = A.director();
      const q = (a, p) => { if (!a.length) return 0; const b = a.slice().sort((x, y) => x - y); return b[Math.min(b.length - 1, Math.floor(p * b.length))]; };
      const avg = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
      const T = s.steps * s.dt;
      const beats = dir.log.map((b) => b.t);
      let gap = beats.length ? beats[0] : T, gapAt = 0;
      for (let i = 1; i < beats.length; i++) if (beats[i] - beats[i - 1] > gap) { gap = beats[i] - beats[i - 1]; gapAt = beats[i - 1]; }
      if (beats.length && T - beats[beats.length - 1] > gap) { gap = T - beats[beats.length - 1]; gapAt = beats[beats.length - 1]; }
      const hidden = Array.from(s.hiddenSteps, (h) => h / s.steps);
      const perFish = fish.map((f, i) => ({ i, id: f.id, hidden: +hidden[i].toFixed(3), viol: +(s.viol[i] || 0).toFixed(2), state: f.state }));
      const counts = {}; for (const b of dir.log) counts[b.id] = (counts[b.id] || 0) + 1;
      return {
        simSeconds: T, fish: s.N,
        jump: { maxCenterPx: +s.jumpMaxC.toFixed(2), maxPivotPx: +s.jumpMaxP.toFixed(2), limitPx: +(0.03 * s.W).toFixed(1), over: s.jumpsOver, samples: s.jumpSamples, worst: s.jumpWorst },
        width: { min: +s.widthMin.toFixed(3), under15: s.widthUnder, samples: s.widthSamples, worst: s.widthWorst },
        turns: { n: s.turns.length, min: +Math.min(...s.turns).toFixed(3), max: +Math.max(...s.turns).toFixed(3), p05: +q(s.turns, 0.05).toFixed(3), p95: +q(s.turns, 0.95).toFixed(3),
                 outside: s.turns.filter((d) => d < 0.35 - 1e-6 || d > 0.9 + 1e-6).length, perMinutePerFish: +(s.turns.length / (T / 60) / s.N).toFixed(2), cutByOffstage: s.turnsCut,
                 byState: s.turnByState, byFish: fish.map((f, i) => f.id + ':' + s.turnByFish[i]) },
        yaw: { maxDeg: +s.yawMax.toFixed(2), over32: s.yawOver, samples: s.yawSamples },
        cruise: { inRangeFrac: +(s.cruiseIn / Math.max(1, s.cruiseN)).toFixed(4), samples: s.cruiseN, low: s.cruiseLow, high: s.cruiseHigh,
                  shoalInRangeFrac: +(s.shoalIn / Math.max(1, s.shoalN)).toFixed(4) },
        scale: { min: +s.scaleMin.toFixed(3), max: +s.scaleMax.toFixed(3), hist03to15: Array.from(s.scaleHist).map((v) => Math.round(v)) },
        visibility: { avgVisibleFrac: +(s.visSum / s.visSteps).toFixed(4), maxHiddenFrac: +Math.max(...hidden).toFixed(4), perFish },
        story: { beats: dir.log.length, maxGapS: +gap.toFixed(1), maxGapAfter: gapAt, counts, feed: dir.feed, log: dir.log },
        drawImage: { fishAvg: +avg(s.di).toFixed(1), fishMax: Math.max(...s.di), fishP95: q(s.di, 0.95), totalAvg: +avg(s.diAll).toFixed(1), totalMax: Math.max(...s.diAll), frames: s.di.length,
                     fogAvg: +avg(s.diFog).toFixed(1), fogMax: Math.max(...s.diFog), litAvg: +avg(s.diLit).toFixed(1), litMax: Math.max(...s.diLit) },
        jsMsRenderedAvg: +avg(s.jsMs).toFixed(3),
        stateShare: Object.fromEntries(Object.entries(s.stateSteps).map(([k, v]) => [k, +(v / (s.steps * s.N)).toFixed(4)])),
        violSecondsTotal: +s.viol.reduce((a, b) => a + b, 0).toFixed(2),
      };
    });
    res.gates = {
      jump3pctW: res.jump.over === 0,
      width15: res.width.under15 === 0,
      turns035to09: res.turns.outside === 0 && res.turns.n > 0,
      yaw32: res.yaw.over32 === 0,
      cruise95: res.cruise.inRangeFrac >= 0.95,
      scale045to1: res.scale.min <= 0.45 && res.scale.max >= 1.0,
      visible70: res.visibility.avgVisibleFrac >= 0.7,
      hiddenEach25: res.visibility.maxHiddenFrac < 0.25,
      beatEvery60: res.story.maxGapS <= 60,
      fishDrawImage420: res.drawImage.fishMax <= 420,
    };
    res.allPass = Object.values(res.gates).every(Boolean);
    res.url = env.url; res.wallMs = Date.now() - t0;
  } finally { await L.finish(env); }
  res.errors = errors;
  fs.writeFileSync(out, JSON.stringify(res, null, 1));
  const brief = Object.assign({}, res); delete brief.story; delete brief.visibility;
  console.log(JSON.stringify({ out, gates: res.gates, allPass: res.allPass, jump: res.jump, width: res.width, turns: res.turns, yaw: res.yaw, cruise: res.cruise,
    scale: { min: res.scale.min, max: res.scale.max }, visibility: { avg: res.visibility.avgVisibleFrac, maxHidden: res.visibility.maxHiddenFrac },
    story: { beats: res.story.beats, maxGapS: res.story.maxGapS, counts: res.story.counts, feed: res.story.feed }, drawImage: res.drawImage,
    stateShare: res.stateShare, violSecondsTotal: res.violSecondsTotal, errors }, null, 1));
  L.report(errors, warnings, o['allow-errors']);
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
