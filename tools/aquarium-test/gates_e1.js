// Гейт G1 (этап E1 «свет и вода», SPEC §5): кадровые проверки каустики, лучей и счётчиков.
//   node gates_e1.js [--w 1920 --h 1200 --seed 1 --steps 150 --count 300] [--http] [--out DIR] [--q ...]
//   (--count — шагов для счётчиков drawImage; --count 1 — быстро, только кадровые проверки)
// Один и тот же момент симуляции рисуется несколько раз (__aq.render() без шага) с разными слоями
// (__aq.layers), кадры сравниваются попиксельно. Скриншоты декодируются в отдельной чистой вкладке
// (data: URL → холст → getImageData) — в самом движке пиксели не читаются никогда (SPEC F2).
// Проверки:
//   • каустика вне маски: средняя |Δ| (каустика вкл/выкл) по пикселям, где маска = 0, < 1/255;
//   • контраст нитей на песке: p95 − p5 яркости вклада каустики в окнах 48×48 полностью на песке
//     (маска ≥ 0.9, ниже линии пола): медиана по окнам ≥ 30 уровней;
//   • лучи: средняя яркость верхней половины кадра растёт не больше чем на 8%;
//   • drawImage света/воды за кадр (без пузырьков и частиц) — по __aq.stats() e1Light за 300 шагов;
//   • ctx.filter и getImageData в движке — 0.
// Печатает JSON; кадры (mask/on/no_caustics/no_rays и карта Δ) — в --out.
'use strict';
const fs = require('fs');
const path = require('path');
const L = require('./lib');

(async () => {
  const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, seed: 1, steps: 150, dt: 1 / 30, count: 300,
    out: path.join(__dirname, 'out', 'gates_e1') });
  const outDir = L.ensureDir(path.resolve(String(o.out)));
  const env = await L.openEngine(o);
  const res = { url: env.url, viewport: env.vp, steps: o.steps };
  try {
    const { page, cap } = await L.newPage(env);
    await L.gotoReady(page, env.url);
    await page.evaluate((dt, n) => window.__aq.step(dt, n, { render: 'last' }), o.dt, Math.max(1, o.steps | 0));
    const frame = async (name, layers, mask) => {
      await page.evaluate((layers, mask) => {
        window.__aq.layers(Object.assign({ caustics: true, rays: true, band: true, bubbles: true, particles: true, glow: true, shadows: true }, layers));
        if (mask) window.__aq.showMask(); else window.__aq.render();
      }, layers || {}, !!mask);
      await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => r())));
      const buf = await page.screenshot({ type: 'png' });
      fs.writeFileSync(path.join(outDir, name + '.png'), buf);
      return buf;
    };
    const bMask = await frame('mask', {}, true);
    const bOn = await frame('on', {});
    const bOn2 = await frame('on_again', {});
    const bNoC = await frame('no_caustics', { caustics: false });
    const bNoR = await frame('no_rays', { rays: false });
    await frame('on_final', {});
    const geo = await page.evaluate(() => {
      const s = window.__aq.scene(), W = innerWidth, fl = [];
      for (let x = 0; x <= W; x += 8) fl.push(window.__aq.floorYAt(x));
      return { bandH: s.bandH, floor: fl };
    });
    // счётчики за 300 шагов
    await page.evaluate(() => window.__aq.resetStats());
    const st = await L.stepFrames(page, o.dt, Math.max(1, o.count | 0));
    res.counters = { avg: { e1Light: st.avg.e1Light, e1Bubbles: st.avg.e1Bubbles, e1Particles: st.avg.e1Particles, drawImage: st.avg.drawImage,
      setTransform: st.avg.setTransform, gradients: st.avg.gradients, patterns: st.avg.patterns, jsMs: st.avg.jsMs },
      max: { e1Light: st.max.e1Light, e1Bubbles: st.max.e1Bubbles, e1Particles: st.max.e1Particles, drawImage: st.max.drawImage,
        gradients: st.max.gradients, patterns: st.max.patterns, filter: st.max.filter, getImageData: st.max.getImageData } };
    res.light = st.light;
    res.errors = cap.errors;

    // анализ в чистой вкладке: декодирование и счёт целиком внутри (наружу — только числа)
    const ap = await env.browser.newPage();
    await ap.goto('about:blank');
    const pngs = { mask: bMask, on: bOn, on2: bOn2, noC: bNoC, noR: bNoR };
    for (const k in pngs) pngs[k] = Buffer.from(pngs[k]).toString('base64');   // puppeteer ≥22: Uint8Array
    const an = await ap.evaluate(async (pngs, geo, cssW) => {
      const dec = async (b64) => {
        const bin = atob(b64), u8 = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
        const im = await createImageBitmap(new Blob([u8], { type: 'image/png' }));
        const c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
        const g = c.getContext('2d'); g.drawImage(im, 0, 0);
        return { w: c.width, h: c.height, d: g.getImageData(0, 0, c.width, c.height).data };
      };
      const M = await dec(pngs.mask), A = await dec(pngs.on), A2 = await dec(pngs.on2), C = await dec(pngs.noC), R = await dec(pngs.noR);
      const Wd = A.w, Hd = A.h, N = Wd * Hd, sx = Wd / cssW;
      const lum = (d, i) => 0.2126 * d[i * 4] + 0.7152 * d[i * 4 + 1] + 0.0722 * d[i * 4 + 2];
      const pct = (arr, p) => { const a = Float64Array.from(arr).sort(); return a.length ? a[Math.min(a.length - 1, Math.floor(p * a.length))] : NaN; };
      let diff = 0;
      for (let i = 0; i < A.d.length; i++) if (A.d[i] !== A2.d[i]) diff++;
      // 1) вне маски / внутри
      let outN = 0, outSum = 0, outMax = 0, inN = 0, inSum = 0;
      for (let i = 0; i < N; i++) {
        const y = Math.floor(i / Wd) / sx;
        if (y < geo.bandH + 1) continue;                           // полоса поверхности — не задник
        const dd = (Math.abs(A.d[i * 4] - C.d[i * 4]) + Math.abs(A.d[i * 4 + 1] - C.d[i * 4 + 1]) + Math.abs(A.d[i * 4 + 2] - C.d[i * 4 + 2])) / 3;
        if (M.d[i * 4] < 1) { outN++; outSum += dd; if (dd > outMax) outMax = dd; } else { inN++; inSum += dd; }
      }
      // 2) контраст нитей на песке: окна 48×48 CSS px целиком в маске ≥ 0.9 и ниже линии пола
      const win = Math.round(48 * sx), conts = [];
      for (let y0 = 0; y0 + win <= Hd; y0 += win) for (let x0 = 0; x0 + win <= Wd; x0 += win) {
        let ok = true; const vals = [];
        for (let y = y0; y < y0 + win && ok; y++) for (let x = x0; x < x0 + win; x++) {
          const i = y * Wd + x, fy = geo.floor[Math.min(geo.floor.length - 1, Math.round(x / sx / 8))];
          if (M.d[i * 4] < 0.9 * 255 || y / sx < fy + 4) { ok = false; break; }
          vals.push(lum(A.d, i) - lum(C.d, i));
        }
        if (ok && vals.length) conts.push({ x: Math.round(x0 / sx), y: Math.round(y0 / sx), c: pct(vals, 0.95) - pct(vals, 0.05) });
      }
      conts.sort((a, b) => a.c - b.c);
      // 3) лучи: верхняя половина
      let on = 0, off = 0, n2 = 0;
      for (let y = 0; y < Hd / 2; y++) for (let x = 0; x < Wd; x++) { const i = y * Wd + x; on += lum(A.d, i); off += lum(R.d, i); n2++; }
      // карта вклада каустики ×3
      const c = document.createElement('canvas'); c.width = Wd; c.height = Hd;
      const g = c.getContext('2d'), id = g.createImageData(Wd, Hd);
      for (let i = 0; i < N; i++) { const v = Math.max(0, Math.min(255, Math.round((lum(A.d, i) - lum(C.d, i)) * 3))); id.data[i * 4] = v; id.data[i * 4 + 1] = v; id.data[i * 4 + 2] = v; id.data[i * 4 + 3] = 255; }
      g.putImageData(id, 0, 0);
      return { diff, outN, outMean: outSum / Math.max(1, outN), outMax, inN, inMean: inSum / Math.max(1, inN),
        conts, on: on / n2, off: off / n2, png: c.toDataURL('image/png').split(',')[1] };
    }, pngs, geo, o.w);
    fs.writeFileSync(path.join(outDir, 'caustic_contribution_x3.png'), Buffer.from(an.png, 'base64'));
    res.rerenderIdentical = an.diff === 0;
    res.outsideMask = { pixels: an.outN, meanAbsDiff: an.outMean, maxAbsDiff: an.outMax, target: '< 1 level (1/255)', pass: an.outMean < 1 };
    res.insideMask = { pixels: an.inN, meanAbsDiff: an.inMean };
    const cs = an.conts, med = cs.length ? cs[Math.floor(cs.length / 2)].c : NaN;
    res.sandContrast = { windows: cs.length, median: med, p10: cs.length ? cs[Math.floor(cs.length * 0.1)].c : NaN,
      max: cs.length ? cs[cs.length - 1].c : NaN, target: '>= 30 levels (median 48px window on sand)', pass: med >= 30 };
    res.raysTopHalf = { meanOn: an.on, meanOff: an.off, increasePct: ((an.on - an.off) / an.off) * 100, target: '<= 8%', pass: (an.on - an.off) / an.off <= 0.08 };
    res.drawImageLight = { avg: res.counters.avg.e1Light, max: res.counters.max.e1Light, target: '<= 60', pass: res.counters.max.e1Light <= 60 };
    res.noFilter = { filter: res.counters.max.filter, getImageData: res.counters.max.getImageData, pass: res.counters.max.filter === 0 && res.counters.max.getImageData === 0 };
    res.pass = res.outsideMask.pass && res.sandContrast.pass && res.raysTopHalf.pass && res.drawImageLight.pass && res.noFilter.pass && !cap.errors.length;
    console.log(JSON.stringify(res, null, 1));
    fs.writeFileSync(path.join(outDir, 'gates_e1.json'), JSON.stringify(res, null, 1));
    L.report(cap.errors, cap.warnings, o['allow-errors']);
  } finally { await L.finish(env); }
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
