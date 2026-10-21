// P1.9: гейт «задник слоями против холста» — ОДИН И ТОТ ЖЕ момент симуляции двумя путями движка:
//   A — ?vlayer=0 (видео/постер, затемнение, K и лучи рисуются в холст), B — ?vlayer=1 (CSS-слои над <video>,
//   прозрачный холст, лучи слоем 'screen'); снимается страница целиком (page.screenshot — композитор), PSNR ≥ --min (45 дБ).
//   node layers_psnr.js [--cases "1512x982@2,2560x1440@1"] [--themes day,night,fade] [--steps 150] [--seed 1] [--min 45]
//                       [--q "bgvideo=intra"] [--shots DIR] [--out psnr.json] [--rootB DIR [--rootA DIR] --vlayerA 0 --vlayerB 0]
// Одна страница на случай: --steps шагов по 1/30 с (по умолчанию 150 = 5 с: первые 2 с — заселение и проявление — не
// сравниваются), затем кадр A в режиме холста и кадр B в режиме слоёв (__aq.setVlayer(true) — переключение на ходу, как у зонда)
// при ТОМ ЖЕ simT: симуляция общая, сравниваются только пути отрисовки. Перед A режим переключается туда и обратно, чтобы
// оба кадра были «после пересборки буфера» (первая пересборка после запуска меняет каустику на ≤ 22/255 — см. perf.js).
// «fade» — день, на шаге --fadeAt setTheme('night') и ещё --fadeSteps шагов: середина перехода (k ≈ 0.5: оба задника,
// подкраска и оба набора лучей с весами). Две отдельные страницы (--rootB: другой движок, например HEAD, с --vlayerA/--vlayerB)
// — только для сравнения движков; там рыбы могут отличаться шумом загрузки (litMax от порядка асинхронных загрузок),
// а совпадение бит-в-бит (psnr Infinity) — доказательство.
// Печатает JSON {cases: [{case, theme, psnr, differFrac, maxDiff, …}], allPass}; код 2, если гейт не прошёл или были ошибки.
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const L = require('./lib');

const o = L.parseArgs(process.argv.slice(2), { cases: '1512x982@2,2560x1440@1', themes: 'day,night,fade', steps: 150, seed: 1, min: 45,
  vlayerA: 0, vlayerB: 1, fadeAt: 60, fadeSteps: 45, eq: 1 });
// --eq 1 (по умолчанию): оба пути при РАВНОМ разрешении задника — budget=8.3&vidcap=0, RS = DPR. При отгружаемом бюджете
// (--eq 0) холст на Retina рисует задник в RS ≈ 1.56 px устройства на CSS px и растягивается браузером до 2, а слой видео
// показан в родных 2 — слои резче, и разница с холстом на фактуре рифа ≈ 38 дБ: это выигрыш P1.9, а не ошибка смешивания.
if (+o.eq) o.q = 'budget=8.3&vidcap=0' + (o.q ? '&' + o.q : '');
const SHOTS = L.ensureDir(path.resolve(String(o.shots || path.join(__dirname, 'out', 'layers'))));
const rootA = path.resolve(o.rootA ? String(o.rootA) : L.DEFAULT_ROOT), rootB = o.rootB ? path.resolve(String(o.rootB)) : null;

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
// simT = 5 до прихода постера: одинаковая расстановка рыб при сравнении двух страниц (perf.js injectMock)
function injectTime() {
  let aq;
  Object.defineProperty(window, '__aq', { configurable: true, get() { return aq; }, set(v) { aq = v; try { v.setTime(5); } catch (e) { /* нет */ } } });
}
function parseCase(s) {
  const m = /^(\d+)x(\d+)(?:@(\d+(?:\.\d+)?))?$/.exec(s.trim());
  if (!m) throw new Error('bad case ' + s);
  return { w: +m[1], h: +m[2], dpr: m[3] ? +m[3] : 1, name: s.trim() };
}
const rafWait = (page) => page.evaluate(() => new Promise((res) => requestAnimationFrame(() => res())));
const info = (page) => page.evaluate(() => {
  const A = window.__aq, s = A.stats(), th = A.theme(), vl = A.vlayer ? A.vlayer() : {};
  return { simT: s.simT, k: th.k, vlayer: !!s.vlayer, drawImage: s.last.drawImage, jsMs: +s.last.jsMs.toFixed(2), backing: s.backing, RS: s.RS, rays: vl.rays || null, raysScale: vl.raysScale || null };
});
async function openCase(env, root, vlayer, cs, theme) {
  const { page, cap } = await L.newPage(env, { inject: { fn: injectTime } });
  await page.setViewport({ width: cs.w, height: cs.h, deviceScaleFactor: cs.dpr });
  const q = L.buildQuery(Object.assign({}, o, { vlayer, q: 'theme=' + (theme === 'fade' ? 'day' : theme) + (o.q ? '&' + o.q : '') }));
  await L.gotoReady(page, 'file://' + root + '/index.html?' + q, 90000);
  await page.evaluate(async (steps, theme, fadeAt, fadeSteps) => {
    const A = window.__aq;
    if (theme === 'fade') { await A.step(1 / 30, fadeAt, { render: false }); A.setTheme('night', false); await A.step(1 / 30, fadeSteps, { render: 'last' }); }
    else await A.step(1 / 30, steps, { render: 'last' });
  }, Math.max(1, o.steps | 0), theme, o.fadeAt | 0, o.fadeSteps | 0);
  return { page, cap };
}
// одна страница: A (холст) и B (слои) в один момент; оба — после пересборки буфера
async function captureBoth(env, cs, theme, shotA, shotB) {
  const { page, cap } = await openCase(env, rootA, 0, cs, theme);
  const tog = await page.evaluate(() => { const A = window.__aq; const on = A.setVlayer(true), off = A.setVlayer(false); return [on, off]; });
  await rafWait(page);
  const a = await info(page);
  await page.screenshot({ path: shotA });
  const on = await page.evaluate(() => window.__aq.setVlayer(true));
  await rafWait(page);
  const b = await info(page);
  await page.screenshot({ path: shotB });
  await page.close();
  return { a, b, toggled: tog[0] === true && tog[1] === false && on === true, errors: cap.errors };
}
// две страницы (другой корень движка): A и B — по своему пути каждая
async function captureTwo(env, cs, theme, shotA, shotB) {
  const pa = await openCase(env, rootA, o.vlayerA, cs, theme);
  await rafWait(pa.page); const a = await info(pa.page); await pa.page.screenshot({ path: shotA }); await pa.page.close();
  const pb = await openCase(env, rootB, o.vlayerB, cs, theme);
  await rafWait(pb.page); const b = await info(pb.page); await pb.page.screenshot({ path: shotB }); await pb.page.close();
  return { a, b, toggled: null, errors: pa.cap.errors.concat(pb.cap.errors) };
}

(async () => {
  const cases = String(o.cases).split(',').map(parseCase), themes = String(o.themes).split(',').map((s) => s.trim()).filter(Boolean);
  const env = await L.openEngine(Object.assign({}, o, { w: cases[0].w, h: cases[0].h, dpr: cases[0].dpr }));
  const out = { mode: rootB ? 'two-pages' : 'one-page', min: +o.min, steps: o.steps, seed: o.seed, eq: !!+o.eq, q: o.q || null, rootA, rootB, vlayerA: rootB ? o.vlayerA : 0, vlayerB: rootB ? o.vlayerB : 1, cases: [] };
  const errors = [];
  try {
    for (const cs of cases) for (const theme of themes) {
      const tag = cs.name.replace('@', 'x') + '_' + theme, sa = path.join(SHOTS, tag + '_A.png'), sb = path.join(SHOTS, tag + '_B.png');
      const r = rootB ? await captureTwo(env, cs, theme, sa, sb) : await captureBoth(env, cs, theme, sa, sb);
      const d = imgDiff(sa, sb);
      errors.push(...r.errors.map((e) => tag + ': ' + e));
      const row = { case: cs.name, theme, simT: r.a.simT, k: +(+r.a.k).toFixed(3), psnr: d.psnr, differFrac: d.differFrac, maxDiff: d.maxDiff, sizeMismatch: !!d.sizeMismatch,
        toggled: r.toggled, A: { vlayer: r.a.vlayer, drawImage: r.a.drawImage, jsMs: r.a.jsMs, backing: r.a.backing, RS: r.a.RS },
        B: { vlayer: r.b.vlayer, drawImage: r.b.drawImage, jsMs: r.b.jsMs, backing: r.b.backing, RS: r.b.RS, rays: r.b.rays, raysScale: r.b.raysScale },
        pass: !d.sizeMismatch && d.psnr >= +o.min && r.toggled !== false && r.a.simT === r.b.simT };
      out.cases.push(row);
      console.error(`${tag}: psnr ${d.psnr} dB  differ ${(100 * d.differFrac).toFixed(1)}%  max ${d.maxDiff}  drawImage ${r.a.drawImage} → ${r.b.drawImage}  ${row.pass ? 'ok' : 'FAIL'}`);
    }
  } finally { await L.finish(env); }
  out.allPass = out.cases.length > 0 && out.cases.every((c) => c.pass) && errors.length === 0;
  const txt = JSON.stringify(out, null, 1);
  console.log(txt);
  if (o.out) { const p = path.resolve(String(o.out)); L.ensureDir(path.dirname(p)); fs.writeFileSync(p, txt); }
  L.report(errors, [], false);
  if (!out.allPass) process.exitCode = 2;
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
