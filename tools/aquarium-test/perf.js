// P1.1: HUD, снимок диагностики, зонд производительности, бюджет второго экрана, метки загрузки и видео-журнал.
//   node perf.js [--w 960 --h 600 --dpr 2] [--abw 1512 --abh 982 --abdpr 2] [--seed 1] [--out perf.json] [--shots DIR] [--full]
//                [--no-live] [--no-ab] [--configs asBefore,noRays]   (--configs — только эти конфигурации во второй части; отладка)
// Две части (обе без ?test=1 — как в приложении):
//  1) «живая» (настоящий rAF и видео MP4): window.__AQ_BOOT как у приложения → HUD с запуска; aquariumPerfSnapshot()
//     (валидный JSON < 6 КБ, нужные поля, метка загрузки); оборот петли видео (перемотка к концу → событие vloop с
//     длительностью перемотки и пропуском кадров по rVFC); сторож видео (currentTime «застыл» → пересоздание и
//     продолжение с того же времени, событие vstall); aquariumSetBudget({mp: 2, fps: 30}) и сброс; короткий зонд
//     (--full — полный ≈45 с) на настоящих кадрах: все конфигурации, после — всё как было.
//  2) «после зонда — как было» (rAF подменён, синтетические 16.67 мс, ?bgvideo=0): прогрев, симуляция на паузе
//     (__aq.pause — рыбы стоят, кадры рисуются), кадр «с нуля» в момент T0 (__aq.invalidate + render), короткий зонд
//     (все 11 конфигураций рисуются, часы идут), снова T0 и кадр «с нуля»: кадры совпадают, состояние (слои, бюджет, RS,
//     буфер, ритм, разнесение кэшей, регулятор) — как до зонда; потом симуляция идёт дальше.
//     Сравнивать с отдельной страницей без зонда нельзя: поведение рыб читает позы кораллов из кэша рифа, и другой
//     ритм его пересборок во время зонда уводит траектории (хаос, а не «след» зонда).
// Печатает JSON {live, ab, gates, allPass}; код 2, если гейт не прошёл или были ошибки страницы.
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const L = require('./lib');

const o = L.parseArgs(process.argv.slice(2), { w: 960, h: 600, dpr: 2, abw: 1512, abh: 982, abdpr: 2, seed: 1 });
const SHOTS = L.ensureDir(path.resolve(String(o.shots || path.join(__dirname, 'out', 'perf'))));

// приложение: document-start WKUserScript (WallpaperWindow.bootSource)
function injectBoot(w, h) {
  window.__WALLPAPER = true;
  window.__AQ_POWER = 'high';
  window.__AQ_BOOT = { power: 'high', hud: true, budget: null, screen: { id: 1, w, h, scale: 1, maxFps: 60, main: true },
    crashes: 0, loadReason: 'launch', appVersion: 'perf.js' };
}
// rAF подменён (как bench.js/governor.js) + simT = 5 до прихода постера: без пересева рыб по сцене, который зависит
// от порядка асинхронных загрузок (иначе два запуска одного движка расставляют рыб по-разному)
function injectMock() {
  window.__bench = { cb: null };
  window.requestAnimationFrame = (cb) => { window.__bench.cb = cb; return 1; };
  let aq;
  Object.defineProperty(window, '__aq', { configurable: true, get() { return aq; }, set(v) { aq = v; try { v.setTime(5); } catch (e) { /* нет */ } } });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rawRGB = (p) => execFileSync('ffmpeg', ['-v', 'error', '-i', p, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], { maxBuffer: 1 << 30 });
function imgDiff(a, b) {
  const x = rawRGB(a), y = rawRGB(b);
  if (x.length !== y.length) return { sizeMismatch: true };
  let n = 0, max = 0, se = 0;
  for (let i = 0; i < x.length; i++) { const d = Math.abs(x[i] - y[i]); if (d) { se += d * d; if (d > max) max = d; } }
  for (let i = 0; i < x.length; i += 3) if (x[i] !== y[i] || x[i + 1] !== y[i + 1] || x[i + 2] !== y[i + 2]) n++;
  const mse = se / x.length;
  return { pixels: x.length / 3, differ: n, differFrac: +(n / (x.length / 3)).toFixed(5), maxDiff: max, psnr: mse ? +(10 * Math.log10((255 * 255) / mse)).toFixed(2) : Infinity };
}

async function livePart(env) {
  const { page, cap } = await L.newPage(env, { inject: { fn: injectBoot, args: [o.w, o.h] } });
  await page.goto(env.url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__aq && window.__aq.ready(), { timeout: 60000, polling: 200 });
  await sleep(6000);                                         // настоящие кадры: кольца, vsync, видео
  const r = {};
  r.hud = await page.evaluate(() => { const el = document.getElementById('aqhud'); return el ? { shown: el.style.display !== 'none', lines: el.textContent.split('\n').length, text: el.textContent } : null; });
  const snapStr = await page.evaluate(() => JSON.stringify(window.aquariumPerfSnapshot()));
  const snap = JSON.parse(snapStr);
  r.snapshotBytes = Buffer.byteLength(snapStr);
  r.snapshot = snap;
  // HUD выключается
  r.hudOff = await page.evaluate(() => { window.aquariumSetDebug(false); const el = document.getElementById('aqhud'); return el ? el.style.display : 'none'; });
  // оборот петли: дневное видео (активная тема) — к концу; ждём перемотку в начало
  r.loop = await page.evaluate(async () => {
    const v = document.querySelector('video');
    if (!v || !(v.duration > 0)) return { skipped: 'no playing video', readyState: v ? v.readyState : null };
    v.currentTime = Math.max(0, v.duration - 0.6);
    const t0 = performance.now();
    while (performance.now() - t0 < 6000) {
      await new Promise((res) => setTimeout(res, 200));
      const ev = window.aquariumPerfSnapshot().events.filter((e) => e.e === 'vloop');
      if (ev.length) return { event: ev[ev.length - 1], t: v.currentTime };
    }
    return { timeout: true, t: v.currentTime, paused: v.paused };
  });
  // сторож: currentTime «застыл» на 7.5 с → через > 2 с видео пересоздаётся и продолжает с 7.5
  r.watchdog = await page.evaluate(async () => {
    const v = document.querySelector('video');
    if (!v) return { skipped: 'no video' };
    Object.defineProperty(v, 'currentTime', { configurable: true, get: () => 7.5, set() {} });
    const t0 = performance.now();
    while (performance.now() - t0 < 8000) {
      await new Promise((res) => setTimeout(res, 200));
      const nv = document.querySelector('video');
      if (nv && nv !== v && nv.readyState >= 2 && !nv.seeking) {
        await new Promise((res) => setTimeout(res, 300));
        const ev = window.aquariumPerfSnapshot().events.filter((e) => e.e === 'vstall');
        return { recreated: true, newTime: nv.currentTime, event: ev[ev.length - 1] || null, stalls: window.aquariumPerfSnapshot().video.day.stalls };
      }
    }
    return { timeout: true };
  });
  // бюджет второго экрана: 2 Мп / 30 к/с (буфер — через ≤ 3 с, как смена питания), затем сброс
  r.budget = await page.evaluate(async () => {
    const before = window.__aq.perfState();
    const ret = window.aquariumSetBudget({ mp: 2, fps: 30 });
    await new Promise((res) => setTimeout(res, 3600));
    const mid = window.__aq.perfState();
    window.aquariumSetBudget({ mp: null, fps: null });
    await new Promise((res) => setTimeout(res, 3600));
    const after = window.__aq.perfState();
    return { ret, before: { mp: before.budgetMp, fps: before.fpsTarget, backing: before.backing }, mid: { mp: mid.budgetMp, src: mid.budgetSrc, fps: mid.fpsTarget, backing: mid.backing },
      after: { mp: after.budgetMp, src: after.budgetSrc, fps: after.fpsTarget, backing: after.backing } };
  });
  // зонд на настоящих кадрах
  const full = !!o.full;
  r.probe = await page.evaluate(async (full) => {
    const s0 = window.__aq.perfState();
    const res = await window.aquariumPerfProbe(full ? undefined : { warmMs: 250, measureMs: 500 });
    const s1 = window.__aq.perfState();
    return { res, s0, s1 };
  }, full);
  r.snapshotAfter = await page.evaluate(() => { const s = window.aquariumPerfSnapshot(); return { bytes: JSON.stringify(s).length, events: s.events.map((e) => e.e) }; });
  await page.screenshot({ path: path.join(SHOTS, 'live.png') });
  r.errors = cap.errors; r.warnings = cap.warnings.length;
  await page.close();
  return r;
}

// одна страница: прогрев → симуляция на паузе → кадр A0 «с нуля» в момент T0 → короткий зонд (кадры рисуются во всех
// конфигурациях, часы идут) → снова T0 → кадр A1 «с нуля»; A0 и A1 должны совпасть (зонд ничего не оставил), состояние — тоже
async function restorePage(env, { k0, shot0, shot1 }) {
  const { page, cap } = await L.newPage(env, { inject: { fn: injectMock } });
  await page.goto(env.url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__aq && window.__aq.ready(), { timeout: 60000, polling: 100 });
  await page.evaluate(() => { window.__now = performance.now(); window.__pump = async (n) => { for (let i = 0; i < n; i++) { window.__now += 1000 / 60; const cb = window.__bench.cb; window.__bench.cb = null; cb(window.__now); if (i % 8 === 7) await 0; } }; });
  const pre = await page.evaluate(async (k0) => {
    await window.__pump(k0);
    // одна пересборка буфера заранее: первая после запуска меняет каустику на ≤ 22/255 (так и в HEAD — ступень регулятора
    // RS ×0.85 туда и обратно); эталон — состояние «после пересборки», как и после зонда
    const lv = window.__aq.perfState().level;
    window.__aq.setQuality(4); await window.__pump(4); window.__aq.setQuality(lv); await window.__pump(4);
    window.__aq.pause(true);
    await window.__pump(3);
    const T0 = window.__aq.stats().simT;
    window.__aq.invalidate(); window.__aq.render();
    return { T0, state: window.__aq.perfState() };
  }, k0);
  await page.screenshot({ path: shot0 });
  const mid = await page.evaluate(async (T0, configs) => {
    let done = null, n = 0;
    window.aquariumPerfProbe({ warmMs: 100, measureMs: 200, configs }).then((r) => { done = r; });
    while (!done && n < 5000) { await window.__pump(1); n++; await 0; await 0; }
    const state = window.__aq.perfState();
    window.__aq.setTime(T0); window.__aq.invalidate(); window.__aq.render();
    return { probe: done, frames: n, state };
  }, pre.T0, o.configs ? String(o.configs).split(',') : undefined);
  await page.screenshot({ path: shot1 });
  const post = await page.evaluate(async () => {           // дальше живёт как обычно
    window.__aq.pause(false);
    const f0 = window.__aq.perfState().frames;
    await window.__pump(30);
    return { framesAfter: window.__aq.perfState().frames - f0, snapBytes: JSON.stringify(window.aquariumPerfSnapshot()).length };
  });
  await page.close();
  return { T0: pre.T0, before: pre.state, after: mid.state, probe: mid.probe, probeFrames: mid.frames, post, errors: cap.errors };
}

(async () => {
  const out = { viewport: { live: [o.w, o.h, o.dpr], restore: [o.abw, o.abh, o.abdpr] }, gates: {} };
  const G = out.gates;
  // 1) живая часть
  if (o.live !== false) {
    const env = await L.openEngine(Object.assign({}, o, { wallpaper: false, test: false }), { test: false });
    try {
      const r = await livePart(env);
      out.live = r;
      const s = r.snapshot;
      G.liveNoErrors = r.errors.length === 0;
      G.hudAtBoot = !!(r.hud && r.hud.shown && r.hud.lines >= 6);
      G.hudOff = r.hudOff === 'none';
      G.snapshotSize = r.snapshotBytes < 6144;
      G.snapshotFields = !!(s && s.fps && s.fps.target === 60 && s.fps.frames > 0 && s.fps.p50 > 0 && s.canvas && s.canvas.mp > 0 && s.gov &&
        s.vsync && s.since && s.since.frames > 0 && Array.isArray(s.events) && s.page && s.page.boots >= 1 && typeof s.page.nav === 'string' &&
        s.boot && s.boot.loadReason === 'launch' && s.boot.screen && s.boot.screen.maxFps === 60 && s.theme && s.fish > 0);
      G.snapshotVideo = !!(s && (s.bg !== 'video' || (s.video && s.video.day && s.video.day.st === 2)));
      G.loopLogged = !!(r.loop && r.loop.event && r.loop.event.seekMs != null);
      G.watchdogResume = !!(r.watchdog && r.watchdog.recreated && r.watchdog.newTime >= 7.3 && r.watchdog.newTime < 12 && r.watchdog.event);
      G.budgetApp = !!(r.budget && r.budget.mid.mp === 2 && r.budget.mid.src === 'app' && r.budget.mid.fps === 30 &&
        r.budget.mid.backing[0] * r.budget.mid.backing[1] <= 2.0e6 + 1 && r.budget.after.src !== 'app' && r.budget.after.fps === 60 &&
        r.budget.after.backing[0] === r.budget.before.backing[0] && r.budget.after.backing[1] === r.budget.before.backing[1]);
      const p = r.probe;
      G.probeLiveAllConfigs = !!(p && p.res && !p.res.aborted && p.res.configs.length === 11 && p.res.configs.every((c) => c.frames > 0 && c.p50 > 0));
      G.probeLiveRestores = !!(p && JSON.stringify(Object.assign({}, p.s0, { frames: 0 })) === JSON.stringify(Object.assign({}, p.s1, { frames: 0 })));
    } finally { await L.finish(env); }
  }
  // 2) зонд не оставляет следов: тот же момент «с нуля» до и после зонда
  if (o.ab !== false) {
    const env = await L.openEngine(Object.assign({}, o, { w: o.abw, h: o.abh, dpr: o.abdpr, q: 'bgvideo=0' + (o.q ? '&' + o.q : '') }), { test: false });
    try {
      const s0 = path.join(SHOTS, 'restore_before.png'), s1 = path.join(SHOTS, 'restore_after.png');
      const R = await restorePage(env, { k0: 60, shot0: s0, shot1: s1 });
      const d = imgDiff(s0, s1);
      out.ab = Object.assign(R, { diff: d });
      G.abNoErrors = R.errors.length === 0;
      G.abAllConfigs = !!(R.probe && !R.probe.aborted && R.probe.configs.length === (o.configs ? String(o.configs).split(',').length : 11) && R.probe.configs.every((c) => c.frames > 0));
      G.abStateRestored = JSON.stringify(Object.assign({}, R.before, { frames: 0 })) === JSON.stringify(Object.assign({}, R.after, { frames: 0 }));
      // тот же кадр: допуск — шум самого метода (скачок часов назад: лучи/частицы чуть иначе; без зонда ≈ 1000 px, ≤ 4/255)
      G.abFrameIdentical = d.differ === 0 || d.psnr >= 60;
      G.abRunsAfter = R.post.framesAfter >= 28;              // первый интервал после зонда не считается
      G.abRsExercised = R.probe ? new Set(R.probe.configs.map((c) => c.rs)).size > 1 : false;   // зонд менял буфер и вернул его
    } finally { await L.finish(env); }
  }
  out.allPass = Object.values(G).every(Boolean);
  const txt = JSON.stringify(out, null, 1);
  console.log(txt);
  if (o.out) { const p = path.resolve(String(o.out)); L.ensureDir(path.dirname(p)); fs.writeFileSync(p, txt); }
  const errs = [].concat(out.live ? out.live.errors : [], out.ab ? out.ab.errors : []);
  L.report(errs, [], false);
  if (!out.allPass) process.exitCode = 2;
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
