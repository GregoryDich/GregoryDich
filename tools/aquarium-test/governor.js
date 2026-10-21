// Регулятор качества v2 (P1.10) и режимы питания — без test-режима: rAF подменён, колбэки кадра приходят с
// синтетическими метками по vsync 60 Гц (__AQ_BOOT.screen.maxFps = 60, как от приложения), а «машина» — это стоимость
// растра нарисованного кадра c(ступень) = C0 × rsMul² × эффекты: пока растр занят, rAF не приходит (как на Mac
// владельца: JS ≈ 1 мс, интервал 35 мс). Интервалы показанных кадров получаются кратными vsync — как на настоящем экране.
//   node governor.js [--out /tmp/x/gov.json] [--w 480 --h 300] [--quick]
// Сценарии и гейты (все обязаны пройти; код 2 иначе; печатает JSON {scenarios, gates, allPass}):
//  settle     — 3 с тяжёлых кадров с запуска: ступень 0 (первые 3 с не считаются);
//  down       — нагрузка «нужна ступень 3» (C0 = 28 мс: 0–2 не влезают в vsync, 3 влезает): ступень 3 не позже чем
//               через 10 с после тишины (модель: ≈4 с), ровно 3 шага вниз, глубже 3 не уходит; первая проба вверх — через 5 с;
//  hold       — 40 с той же нагрузки: пробы вверх с удвоением ожидания (5 → 10 → 20 с): ≤ 3 шага вверх, в конце 3,
//               recover ≥ 20 — качелей нет;
//  recover    — нагрузка снята (5 мс): ступень 0 не позже чем через 60 с (удержавшаяся ступень возвращает ожидание 5 с);
//  extreme    — 200 мс: до последней ступени 7 (ровные 30 к/с, fpsTarget 30) не позже 15 с после тишины; снята → 0 за 60 с;
//  memory     — ступень пары «экран + питание» в localStorage: перезагрузка (тот же экран, high) начинается с неё ещё
//               до первого кадра; другой экран без памяти — из __AQ_BOOT.govLevel; ?govlevel=N сильнее всего;
//  power      — 'low' — своя пара (память пустая → 0), цель уже 30 → ступени 7 нет (max 6), 200 мс → 6; назад 'high' —
//               прежняя ступень из памяти;
//  paused     — ни одного кадра; low @60 Гц — ≈30 к/с; high — 60.
'use strict';
const fs = require('fs');
const path = require('path');
const L = require('./lib');

const o = L.parseArgs(process.argv.slice(2), { w: 480, h: 300, dpr: 1, seed: 3 });

// приложение: document-start WKUserScript; rAF подменён
function inject(boot) {
  window.__WALLPAPER = true;
  window.__AQ_POWER = boot.power;
  window.__AQ_BOOT = boot;
  window.__bench = { cb: null };
  window.requestAnimationFrame = (cb) => { window.__bench.cb = cb; return 1; };
}
const bootFor = (screenId, extra) => Object.assign({ power: 'high', hud: false, budget: null, screen: { id: screenId, w: o.w, h: o.h, scale: 1, maxFps: 60, main: true },
  crashes: 0, loadReason: 'launch', appVersion: 'governor.js', theme: 'day' }, extra || {});

// драйвер в странице: синтетический vsync, модель растра; run(seconds, C0) гонит кадры, возвращает сводку
function driverSrc() {
  const vs = 1000 / 60, RS = [1, 0.9, 0.8, 0.7, 0.6, 0.6, 0.6, 0.6], EFF = [1, 1, 1, 1, 1, 0.8, 0.75, 0.75];
  let now = performance.now();
  const lvl = () => window.__aq.perfState().level;
  const frames = () => window.__aq.perfState().frames;
  const tick = () => { const cb = window.__bench.cb; window.__bench.cb = null; now += vs; if (cb) cb(now); };
  window.__drv = {
    now: () => now,
    // C0 — мс растра нарисованного кадра на ступени 0 (масштабируется по ступени); растр занят → vsync без rAF
    async run(seconds, C0) {
      const end = now + seconds * 1000, t0 = now, levels = [lvl()], at = [0];
      let drawn = 0, i = 0;
      while (now < end) {
        const f0 = frames(), l0 = lvl();
        tick();
        if (frames() > f0) { drawn++; const c = C0 * RS[l0] * RS[l0] * EFF[l0]; now += (Math.ceil(c / vs) - 1) * vs; }
        const l1 = lvl();
        if (l1 !== l0) { levels.push(l1); at.push(Math.round(now - t0) / 1000); }
        if (++i % 60 === 0) await new Promise((r) => setTimeout(r, 0));   // таймеры страницы (budgetChanged, HUD)
      }
      const s = window.__aq.stats(), g = s.governor, p = window.__aq.perfState();
      return { level: p.level, levels, at, drawn, seconds, fpsTarget: p.fpsTarget, rs: +p.RS.toFixed(3), backing: p.backing,
        gov: { max: g.max, p50: +g.p50.toFixed(1), p90: +g.p90.toFixed(1), target: +g.target.toFixed(2), vsync: +g.vsync.toFixed(2), recover: g.recover,
          good: g.good, bad: g.bad, quiet: g.quiet, windows: g.windows, downs: g.downs, ups: g.ups, key: g.key, stored: g.stored } };
    },
    state() { const p = window.__aq.perfState(), g = window.__aq.stats().governor; return { level: p.level, fpsTarget: p.fpsTarget, max: g.max, key: g.key, stored: g.stored, frames: p.frames, rs: p.RS }; },
  };
}
const cheap = (page) => page.evaluate(() => { window.__aq.layers({ caustics: false, rays: false, glow: false, fishlight: false, groups: false, xReefC: false }); });

async function open(env, boot, q) {
  const { page, cap } = await L.newPage(env, { inject: { fn: inject, args: [boot] } });
  await page.goto(env.url + (q ? '&' + q : ''), { waitUntil: 'load' });
  try { await page.waitForFunction(() => window.__aq && window.__aq.ready(), { timeout: 120000, polling: 100 }); }
  catch (e) { throw new Error('page not ready: ' + e.message + '; errors: ' + JSON.stringify(cap.errors)); }
  await page.evaluate(driverSrc);
  await cheap(page);                                   // кадр дешевле (регулятору всё равно, что рисуется)
  return { page, cap };
}
const run = (page, s, c) => page.evaluate((s, c) => window.__drv.run(s, c), s, c);
const state = (page) => page.evaluate(() => window.__drv.state());
const lastLevelAt = (r, lv) => { const i = r.levels.lastIndexOf(lv); return i >= 0 ? r.at[i] : null; };

(async () => {
  const env = await L.openEngine(Object.assign({}, o, { test: false, q: 'debug=1&bgvideo=0' + (o.q ? '&' + o.q : '') }), { test: false });
  const out = { url: env.url, viewport: env.vp, scenarios: {}, gates: {} };
  const S = out.scenarios, G = out.gates, errors = [];
  try {
    // A: тишина → вниз → удержание → восстановление (экран 1, high)
    const A = await open(env, bootFor(1));
    S.start = await state(A.page);
    S.settle = await run(A.page, 3, 28);
    G.settle = S.settle.level === 0 && S.settle.levels.length === 1;
    S.down = await run(A.page, 10, 28);
    // ступень 3 — за ≤ 10 с, ровно три шага вниз без перелёта; через 5 с хороших окон регулятор уже пробует ступень 2
    // (первая проба восстановления) — к концу окна допустимы 3 или 2
    const t3 = lastLevelAt(S.down, 3);
    G.downFast = (S.down.level === 3 || S.down.level === 2) && t3 != null && t3 <= 10 && S.down.levels.slice(0, 4).join(',') === '0,1,2,3' &&
      Math.max(...S.down.levels) === 3 && S.down.gov.downs === 3;
    S.hold = await run(A.page, 40, 28);
    G.hold = S.hold.level === 3 && S.hold.gov.ups <= 3 && S.hold.gov.ups >= 1 && Math.max(...S.hold.levels) === 3 && S.hold.gov.recover >= 20;
    S.recover = await run(A.page, 60, 5);
    const t0r = lastLevelAt(S.recover, 0);
    G.recover = S.recover.level === 0 && t0r != null && t0r <= 60 && Math.min(...S.recover.levels) === 0;
    // питание: paused — ни одного кадра; low @60 Гц — ≈30 к/с; high — 60 (как раньше)
    const fA = await state(A.page);
    await A.page.evaluate(() => window.aquariumSetPower('paused'));
    S.paused = await run(A.page, 1, 5);
    await A.page.evaluate(() => window.aquariumSetPower('low'));
    S.low = await run(A.page, 2, 5);
    await A.page.evaluate(() => window.aquariumSetPower('high'));
    S.high = await run(A.page, 1, 5);
    G.paused = S.paused.drawn === 0;
    G.low30 = S.low.drawn >= 55 && S.low.drawn <= 65 && S.low.fpsTarget === 30;
    G.high60 = S.high.drawn >= 57 && S.high.drawn <= 62 && S.high.fpsTarget === 60;
    S.powerKeys = { before: fA.key, afterHigh: S.high.gov.key };
    errors.push(...A.cap.errors);
    await A.page.close();

    // B: предельная нагрузка — до ступени 7 (30 к/с), память пары = 7; на батарее ступени 7 нет
    const B = await open(env, bootFor(1));
    S.extremeStart = await state(B.page);               // память A после восстановления — 0
    S.extreme = await run(B.page, 18, 200);
    const t7 = lastLevelAt(S.extreme, 7);
    G.extreme = S.extreme.level === 7 && t7 != null && t7 <= 15 && S.extreme.fpsTarget === 30 && S.extreme.gov.stored === 7 && S.extreme.gov.max === 7;
    await B.page.evaluate(() => window.aquariumSetPower('low'));
    S.lowStart = await state(B.page);
    S.lowExtreme = await run(B.page, 16, 200);
    G.powerLow = S.lowStart.level === 0 && S.lowStart.max === 6 && S.lowStart.key.endsWith('.low') && S.lowExtreme.level === 6 && S.lowExtreme.fpsTarget === 30 && S.lowExtreme.gov.stored === 6;
    await B.page.evaluate(() => window.aquariumSetPower('high'));
    S.backHigh = await state(B.page);
    G.powerBack = S.backHigh.level === 7 && S.backHigh.key.endsWith('.high') && S.backHigh.fpsTarget === 30;
    S.extremeRecover = await run(B.page, 60, 5);
    const t0e = lastLevelAt(S.extremeRecover, 0);
    G.extremeRecover = S.extremeRecover.level === 0 && t0e != null && t0e <= 60 && S.extremeRecover.fpsTarget === 60;
    // память: ступень 7 снова (ниже проверка старта с неё), чтобы перезагрузка начиналась не с 0
    S.extremeAgain = await run(B.page, 14, 200);
    errors.push(...B.cap.errors);
    await B.page.close();

    // C: старт с памяти пары (экран 1, high → 7) — до первого кадра; другой экран — из __AQ_BOOT.govLevel; ?govlevel сильнее
    const C1 = await open(env, bootFor(1));
    S.memorySame = await state(C1.page);
    errors.push(...C1.cap.errors); await C1.page.close();
    const C2 = await open(env, bootFor(2, { govLevel: 2 }));
    S.memoryBoot = await state(C2.page);
    errors.push(...C2.cap.errors); await C2.page.close();
    const C3 = await open(env, bootFor(1), 'govlevel=1');
    S.memoryUrl = await state(C3.page);
    errors.push(...C3.cap.errors); await C3.page.close();
    G.memory = S.extremeAgain.level === 7 && S.memorySame.level === 7 && S.memorySame.frames === 0 && S.memorySame.fpsTarget === 30 &&
      S.memoryBoot.level === 2 && S.memoryBoot.key.startsWith('aq.gov.2.') && S.memoryUrl.level === 1;
    G.noErrors = errors.length === 0;
  } catch (e) { out.fail = String(e && e.message || e); G.noFail = false; }   // частичный результат всё равно печатается
  finally { await L.finish(env); }
  out.errors = errors;
  out.allPass = Object.keys(G).every((k) => G[k]);
  const s = JSON.stringify(out, null, 1);
  if (o.out) { L.ensureDir(path.dirname(path.resolve(o.out))); fs.writeFileSync(path.resolve(o.out), s); }
  console.log(s);
  console.error('gates: ' + Object.keys(G).map((k) => k + '=' + (G[k] ? 'ok' : 'FAIL')).join(' '));
  L.report(errors, [], false);
  if (!out.allPass) process.exitCode = 2;
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
