// «Чёрный ящик» движка (freeze / white-screen forensics): запись в sessionStorage, prevSession после перезагрузки,
// событие 'stall' на долгой задаче главного потока, фаза, в которой страница «умерла».
//   node blackbox.js [--w 640 --h 400 --dpr 1] [--q "bgvideo=0"] [--out bb.json] [--no-crash] [--root <движок>]
// Без ?test=1 — как в приложении (настоящий rAF и видео; window.__AQ_BOOT с HUD, loadReason 'launch'); браузер —
// не одним процессом (--multiprocess в lib.openEngine), чтобы процесс рендера можно было убить, как WebContent в WebKit:
//  1) загрузка → ≈6.5 с настоящих кадров: в 'aq.blackbox' — валидный JSON ≤ 8 КБ (boot 1, окно 30 с, RS, бюджет,
//     питание, тема, регулятор, видео, журнал); первая загрузка — prevSession нет;
//  2) busy-wait 1.5 с через page.evaluate (вне движка) → событие 'stall' (ms ≥ 1500, js — мс прошлого колбэка) и
//     немедленная запись ящика (why 'stall');
//  3) __aq.setQuality(4) (смена буфера холста — фаза 'rs') + busy-wait 1.2 с в той же задаче → 'stall' с ph 'rs …';
//  4) 40 событий (aquariumSetBudget туда-обратно; журнал — по кругу 40) → page.reload(): prevSession есть, ≤ 8 КБ,
//     boot 1, gone (pagehide), оба застоя — в lastStalls/worst; 'aq.blackbox.prev' в sessionStorage; HUD и
//     prevSummary — «прошлый сеанс №1 …»;
//  5) (--no-crash — пропустить) __aq.busy(60000, 'theme') — страница «повисла» в фазе сборки темы → процессы рендера
//     убиты SIGKILL → page.reload(): prevSession.diedIn = 'theme@…', boot 2, gone false, 'aq.phase' снят.
// Свои застои ищутся по времени (t события — сразу после busy-wait): программный растр headless медленный (3–7 к/с),
// и «естественные» застои (растр > 1 с при js ≈ 10 мс, без тяжёлых фаз) тоже бывают — их движок пишет так же.
// Печатает JSON {steps, gates, allPass}; код 2, если гейт не прошёл или были ошибки страницы.
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const L = require('./lib');

const o = L.parseArgs(process.argv.slice(2), { w: 640, h: 400, dpr: 1, seed: 1 });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// приложение: document-start WKUserScript (WallpaperWindow.bootSource); переживает page.reload() (evaluateOnNewDocument)
function injectBoot(w, h) {
  window.__WALLPAPER = true;
  window.__AQ_POWER = 'high';
  window.__AQ_BOOT = { power: 'high', hud: true, budget: null, screen: { id: 1, w, h, scale: 1, maxFps: 60, main: true },
    crashes: 0, loadReason: 'launch', appVersion: 'blackbox.js' };
}
const readBox = () => {
  const k = (n) => { try { return sessionStorage.getItem(n); } catch (e) { return 'ERR ' + e.message; } };
  return { box: k('aq.blackbox'), prev: k('aq.blackbox.prev'), phase: k('aq.phase'), boots: k('aqBoots') };
};
const parse = (s) => { try { return s ? JSON.parse(s) : null; } catch (e) { return { parseError: String(e) }; } };
const evs = (box, e) => (box && Array.isArray(box.events) ? box.events.filter((x) => x.e === e) : []);
const snap = (page) => page.evaluate(() => window.aquariumPerfSnapshot());
const hudText = (page) => page.evaluate(() => { const el = document.getElementById('aqhud'); return el ? el.textContent : null; });
const ready = (page) => page.waitForFunction(() => window.__aq && window.__aq.ready(), { timeout: 90000, polling: 200 });
// застой, замеченный первым колбэком rAF после busy-wait, закончившегося в end (мс, часы страницы): из 4 последних
// (snapshot.blackbox.last — всегда по одному; в журнале застои без фаз подряд сливаются в одну запись с n и t2)
const inWin = (t, end) => t >= end / 1000 - 0.05 && t <= end / 1000 + 4;
const ourStall = (s, end) => (s.blackbox.last || []).find((x) => inWin(x.t, end)) || null;
const stallInLog = (s, end) => s.events.some((e) => e.e === 'stall' && (inWin(e.t, end) || (e.t2 != null && inWin(e.t2, end))));
// busy-wait в странице: [начало, конец] по её часам
const busyWait = (page, ms, before) => page.evaluate((ms, before) => {
  if (before === 'rs4') window.__aq.setQuality(4);         // смена буфера холста (applyBacking — фаза 'rs') в той же задаче
  const t0 = performance.now();
  while (performance.now() - t0 < ms) { /* занято */ }
  return [t0, performance.now()];
}, ms, before || null);

(async () => {
  const env = await L.openEngine(Object.assign({}, o, { test: false, multiprocess: true }), { test: false });
  const out = { url: env.url, viewport: env.vp, steps: {}, gates: {} };
  const S = out.steps, G = out.gates;
  let cap;
  try {
    const np = await L.newPage(env, { inject: { fn: injectBoot, args: [o.w, o.h] } });
    const page = np.page; cap = np.cap;
    let crashed = false;
    page.on('error', () => { crashed = true; });              // процесс рендера убит → «Page crashed!»

    // 1) первая загрузка
    await page.goto(env.url, { waitUntil: 'load' });
    await ready(page);
    await sleep(6500);
    const r1 = await page.evaluate(readBox);
    const b1 = parse(r1.box), s1 = await snap(page);
    S.first = { bytes: r1.box ? Buffer.byteLength(r1.box) : 0, why: b1 && b1.why, boot: b1 && b1.boot, up: b1 && b1.up, writes: b1 && b1.writes,
      win: b1 && b1.win, since: b1 && b1.since, video: b1 && b1.video, rs: b1 && b1.rs, mp: b1 && b1.mp, budget: b1 && b1.budget,
      budgetSrc: b1 && b1.budgetSrc, power: b1 && b1.power, theme: b1 && b1.theme, gov: b1 && b1.gov,
      events: b1 && b1.events ? b1.events.map((e) => e.e) : null, prevSession: s1.prevSession, boots: s1.page.boots, nav: s1.page.nav,
      blackbox: s1.blackbox, naturalStalls: s1.events.filter((e) => e.e === 'stall') };
    G.boxWritten = !!(b1 && b1.v === 1 && b1.boot === 1 && b1.writes >= 2 && S.first.bytes > 0 && S.first.bytes <= 8192);
    G.boxFields = !!(b1 && b1.win && b1.win.s === 30 && b1.win.n > 0 && b1.win.p50 > 0 && b1.win.p95 >= b1.win.p50 && b1.win.max >= b1.win.p95 &&
      b1.win.maxAt != null && b1.since && b1.since.frames >= b1.win.n && b1.rs > 0 && b1.budget > 0 && typeof b1.budgetSrc === 'string' &&
      b1.power === 'high' && typeof b1.theme === 'string' && typeof b1.gov === 'number' && b1.up > 0 && typeof b1.at === 'string' &&
      b1.reason === 'launch' && b1.nav === 'navigate' && b1.gone === false && evs(b1, 'boot').length === 1 &&
      (b1.bg !== 'video' || !!(b1.video && b1.video.th && b1.video.st >= 1 && 't' in b1.video)));
    G.firstNoPrev = s1.prevSession === null && s1.prevSummary === null && r1.prev === null && s1.page.boots === 1;
    // фазы сбалансированы (каждая открытая закрыта; метка редкой фазы снята): между колбэками rAF глубина 0
    const ph1 = await page.evaluate(() => { const b = window.__aq.blackbox(); return { depth: b.depth, marked: b.marked, phase: sessionStorage.getItem('aq.phase') }; });
    S.first.phases = ph1;

    // 2) долгая задача вне движка: busy-wait 1.5 с → 'stall'
    const [, end2] = await busyWait(page, 1500);
    await sleep(1500);
    const s2 = await snap(page), e2 = ourStall(s2, end2);
    const b2 = parse((await page.evaluate(readBox)).box);
    S.stall = { event: e2, boxWhy: b2 && b2.why, boxLastStalls: b2 && b2.lastStalls, worst: s2.blackbox.worst, stallsTotal: s2.blackbox.stalls };
    G.stallLogged = !!(e2 && e2.ms >= 1500 && e2.ms < 6000 && e2.js < 500 && !(e2.ph && /(^|, )(theme|coralVar|rs|resize) /.test(e2.ph)) && stallInLog(s2, end2));
    G.stallPersisted = !!(b2 && e2 && b2.stalls >= 1 && Array.isArray(b2.lastStalls) && b2.lastStalls.some((x) => x.t === e2.t && x.ms === e2.ms));

    // 3) застой с тяжёлой фазой движка: смена буфера холста (setQuality → applyBacking — 'rs') + 1.2 с в той же задаче
    const q0 = await page.evaluate(() => window.__aq.perfState().level);
    const [, end3] = await busyWait(page, 1200, 'rs4');
    await sleep(1500);
    await page.evaluate((q) => window.__aq.setQuality(q), q0);
    const s3 = await snap(page), e3 = ourStall(s3, end3);
    S.stallPhase = { event: e3, rsEvents: s3.events.filter((e) => e.e === 'rs').slice(-2) };
    G.stallPhase = !!(e3 && e3.ms >= 1200 && typeof e3.ph === 'string' && /(^|, )rs \d+/.test(e3.ph) && stallInLog(s3, end3));

    // 4) журнал полон (40 записей) → перезагрузка; запись ≤ 8 КБ, видна как prevSession
    await page.evaluate(() => { for (let i = 0; i < 20; i++) { window.aquariumSetBudget({ mp: 2, fps: 30 }); window.aquariumSetBudget({ mp: null, fps: null }); } });
    await sleep(300);
    await page.reload({ waitUntil: 'load' });
    await ready(page);
    await sleep(1500);                                        // HUD — 2 раза в секунду
    const r4 = await page.evaluate(readBox), s4 = await snap(page), h4 = await hudText(page);
    const ph4 = await page.evaluate(() => { const b = window.__aq.blackbox(); return { depth: b.depth, marked: b.marked }; });
    G.phasesBalanced = ph1.depth === 0 && !ph1.marked && ph1.phase === null && ph4.depth === 0 && !ph4.marked && r4.phase === null;
    const p4 = s4.prevSession, p4s = p4 ? JSON.stringify(p4) : '';
    const hasStall = (p, e) => !!(p && e && Array.isArray(p.lastStalls) && p.lastStalls.some((x) => x.t === e.t && x.ms === e.ms));
    S.reload = { boots: s4.page.boots, nav: s4.page.nav, prevBytes: Buffer.byteLength(p4s), prevStoredBytes: r4.prev ? Buffer.byteLength(r4.prev) : 0,
      prevWhy: p4 && p4.why, prevGone: p4 && p4.gone, prevBoot: p4 && p4.boot, prevUp: p4 && p4.up, prevStalls: p4 && p4.stalls,
      prevLastStalls: p4 && p4.lastStalls, prevWorst: p4 && p4.worst, prevEvents: p4 && p4.events ? p4.events.length : 0, prevWin: p4 && p4.win,
      prevSummary: s4.prevSummary, hudLine: h4 ? (h4.split('\n').find((l) => l.startsWith('прошлый сеанс')) || null) : null,
      prevEvent: s4.events.find((e) => e.e === 'prev') || null, curBoxBoot: parse(r4.box) && parse(r4.box).boot, snapshotBytes: Buffer.byteLength(JSON.stringify(s4)) };
    G.reloadDetected = s4.page.boots === 2 && s4.page.nav === 'reload';
    G.prevPresent = !!(p4 && p4.v === 1 && p4.boot === 1 && p4.gone === true && !p4.diedIn && p4.stalls >= 2 && hasStall(p4, e2) && hasStall(p4, e3) &&
      p4.worst && p4.worst.ms >= Math.min(e2 ? e2.ms : 0, e3 ? e3.ms : 0));
    G.prevUnder8KB = S.reload.prevBytes > 0 && S.reload.prevBytes <= 8192 && S.reload.prevStoredBytes <= 8192;
    G.prevFullLog = S.reload.prevEvents >= 30 && evs(p4, 'budget').length >= 20;   // журнал полон, урезается только до ≤ 8 КБ
    G.prevStored = !!(r4.prev && parse(r4.prev).boot === 1) && S.reload.curBoxBoot === 2;
    G.prevSummary = typeof s4.prevSummary === 'string' && s4.prevSummary.startsWith('прошлый сеанс №1: работал') &&
      / до ухода/.test(s4.prevSummary) && S.reload.hudLine === s4.prevSummary && !!S.reload.prevEvent && S.reload.prevEvent.boot === 1;

    // 5) «смерть» в фазе: страница повисла в сборке темы → процессы рендера убиты → перезагрузка
    if (o.crash !== false) {
      await sleep(5600);                                      // хотя бы одна запись по таймеру в этом сеансе
      const hang = page.evaluate(() => window.__aq.busy(60000, 'theme')).catch((e) => 'evaluate: ' + String(e && e.message).slice(0, 60));
      await sleep(700);
      // процессы рендера браузера (страница и пустая вкладка по умолчанию) — SIGKILL; браузер остаётся
      let crashErr = null, killed = 0;
      try {
        const ps = execFileSync('ps', ['-o', 'pid=,args=', '--ppid', String(env.browser.process().pid)]).toString().split('\n');
        for (const l of ps) if (/--type=renderer/.test(l)) { process.kill(+l.trim().split(/\s+/)[0], 'SIGKILL'); killed++; }
      } catch (e) { crashErr = String(e && e.message).slice(0, 80); }
      const t0 = Date.now();
      while (!crashed && Date.now() - t0 < 10000) await sleep(100);
      const hangRes = await Promise.race([hang, sleep(3000).then(() => 'pending')]);
      await page.reload({ waitUntil: 'load' });
      await ready(page);
      await sleep(1500);
      const s5 = await snap(page), p5 = s5.prevSession, r5 = await page.evaluate(readBox);
      S.crash = { crashed, killed, crashErr, hang: typeof hangRes === 'string' ? hangRes : 'returned', boots: s5.page.boots, nav: s5.page.nav,
        prevBoot: p5 && p5.boot, prevWhy: p5 && p5.why, prevGone: p5 && p5.gone, diedIn: p5 && p5.diedIn,
        prevBytes: p5 ? Buffer.byteLength(JSON.stringify(p5)) : 0, prevSummary: s5.prevSummary, phaseKeyAfter: r5.phase };
      G.crashDiedIn = !!(crashed && p5 && p5.boot === 2 && typeof p5.diedIn === 'string' && /^theme@\d/.test(p5.diedIn) && p5.gone === false &&
        s5.page.boots === 3 && r5.phase === null && /оборвался в фазе theme@/.test(s5.prevSummary || '') && / до перезапуска|ровные/.test(s5.prevSummary || ''));
    }
    await page.close();
  } finally { await L.finish(env); }

  // убитый процесс рендера: отменённые запросы видео — не ошибки страницы
  const errors = cap ? cap.errors.filter((e) => !/requestfailed: .*\.(mp4|webm)\b/.test(e)) : ['no page'];
  G.noErrors = errors.length === 0;
  out.allPass = Object.values(G).every(Boolean);
  const txt = JSON.stringify(out, null, 1);
  console.log(txt);
  if (o.out) { const p = path.resolve(String(o.out)); L.ensureDir(path.dirname(p)); fs.writeFileSync(p, txt); }
  L.report(errors, cap ? cap.warnings : [], false);
  if (!out.allPass) process.exitCode = 2;
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
