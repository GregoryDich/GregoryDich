// Гейт этапа A2 «геометрия сцены» (SPEC §5): окклюдеры поверх задника без рыб не меняют пиксели > 2/255.
//   node gates_a2.js [--out FILE.json] [--cases "1512x982@1,1512x982@2,1920x1200@1,…"] [--engine 1]
// Проверки (всё по http с 127.0.0.1 — тот же origin, холсты не «пачкаются»; движок здесь пиксели не читает):
//   • native  — задник 2560×1355 1:1, окклюдеры в своих px; max |Δ| по каналам;
//   • bgMap   — для каждого вьюпорта: буфер floor(W·RS)×floor(H·RS), RS = min(dpr, √(8.3e6/(W·H))),
//               задник через ту же раскладку, что layoutBackdrop() движка (cover × zoom, якорь — низ,
//               полоса bandH сверху, клип источника), затем окклюдеры drawImage(img, bgX(bx), bgY(by), bw·dw, bh·dh);
//               imageSmoothingQuality "low" (как главный холст движка) и "high"; картинки сначала «прогреваются»
//               (2 прохода) — первый drawImage свежезагруженной картинки в Chromium фильтрует иначе (до ~20/255),
//               а движок рисует задник и окклюдеры каждый кадр;
//   • engine  — в самом движке (?test=1): кадр, затем __aq.occluderRoundTrip() (путь E1 captureLitBackdrop:
//               альфа окклюдера × освещённый холст) для каждого окклюдера; max |Δ| кадра до/после.
// Печатает JSON; код выхода 2 — ошибки страницы или не пройдены native/engine (direct — справочно, см. gate.direct).
'use strict';
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');
const chromiumMod = require('@sparticuz/chromium');
const chromium = chromiumMod.default || chromiumMod;
const L = require('./lib');

function loadScene(root) {
  const code = fs.readFileSync(path.join(root, 'scene', 'scene.js'), 'utf8');
  const window = {};
  new Function('window', code)(window);
  return window.AQUARIUM_SCENE;
}

(async () => {
  const o = L.parseArgs(process.argv.slice(2), {
    cases: '1512x982@1,1512x982@2,1920x1200@1,1920x1200@2,1920x1080@1,1920x1080@2,2560x1097@1,2560x1097@2',
    engine: 1, out: path.join(__dirname, 'out', 'gates_a2.json') });
  const root = path.resolve(o.root || L.DEFAULT_ROOT);
  const scene = loadScene(root);
  const occ = (scene.occluders || []).map((c) => ({ id: c.id, src: c.src, bx: c.bx, by: c.by, bw: c.bw, bh: c.bh, px: c.px }));
  const server = await L.serve(root);
  const browser = await puppeteer.launch({ executablePath: await chromium.executablePath(), headless: chromium.headless,
    args: [...chromium.args, '--force-color-profile=srgb', '--hide-scrollbars'], defaultViewport: { width: 800, height: 600 },
    protocolTimeout: 600000 });
  const res = { root, occluders: occ.map((c) => c.id), cases: [], native: null, engine: [], errors: [] };
  try {
    // ---- чистая страница того же origin ----
    const page = await browser.newPage();
    const cap = L.captureErrors(page);
    await page.goto(server.base + '/scene/README.txt', { waitUntil: 'load' });
    const prep = await page.evaluate(async (bgSrc, occ) => {
      const load = (s) => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => no(new Error('load ' + s)); im.src = '/' + s; });
      window.__bg = await load(bgSrc);
      window.__occ = [];
      for (const c of occ) window.__occ.push({ c, img: await load(c.src) });
      // сравнение двух ImageData: max |Δ| по каналам RGB, число пикселей с Δ > 1 / > 2, место максимума
      window.__diff = (A, B, w) => {
        let mx = 0, n1 = 0, n2 = 0, at = -1;
        for (let i = 0; i < A.length; i += 4) {
          const d = Math.max(Math.abs(A[i] - B[i]), Math.abs(A[i + 1] - B[i + 1]), Math.abs(A[i + 2] - B[i + 2]));
          if (d > 1) n1++; if (d > 2) n2++;
          if (d > mx) { mx = d; at = i >> 2; }
        }
        return { max: mx, over1: n1, over2: n2, at: at >= 0 ? [at % w, Math.floor(at / w)] : null };
      };
      return { bw: window.__bg.naturalWidth, bh: window.__bg.naturalHeight, occ: window.__occ.map((o) => [o.img.naturalWidth, o.img.naturalHeight]) };
    }, scene.backdrop.src, occ);
    res.images = prep;

    // native 1:1
    res.native = await page.evaluate(() => {
      const bg = window.__bg, W = bg.naturalWidth, H = bg.naturalHeight;
      const c = document.createElement('canvas'); c.width = W; c.height = H;
      const g = c.getContext('2d');
      for (let k = 0; k < 2; k++) { g.drawImage(bg, 0, 0); for (const o of window.__occ) g.drawImage(o.img, o.c.px[0], o.c.px[1]); }
      g.drawImage(bg, 0, 0);
      const A = g.getImageData(0, 0, W, H).data;
      for (const o of window.__occ) g.drawImage(o.img, o.c.px[0], o.c.px[1]);
      const B = g.getImageData(0, 0, W, H).data;
      return window.__diff(A, B, W);
    });

    // bgMap на вьюпортах
    for (const cs of String(o.cases).split(',')) {
      const m = /^(\d+)x(\d+)@([\d.]+)$/.exec(cs.trim());
      if (!m) continue;
      const W = +m[1], H = +m[2], dpr = +m[3];
      for (const q of ['low', 'high']) {
        const r = await page.evaluate((W, H, dpr, q, B0) => {
          const bg = window.__bg, iw = bg.naturalWidth, ih = bg.naturalHeight;
          const RS = Math.min(dpr, Math.sqrt(8.3e6 / (W * H)));
          // = layoutBackdrop() движка
          const bandH = Math.round(H * B0.bandHf * RS) / RS, ph = Math.max(1, H - bandH);
          const sc = Math.max(W / iw, ph / ih) * B0.zoom, dw = iw * sc, dh = ih * sc, dx = (W - dw) / 2, dy = H - dh;
          const x0 = Math.max(0, dx), x1 = Math.min(W, dx + dw), y0 = Math.max(bandH, dy), y1 = Math.min(H, dy + dh);
          const cl = (v, a, b) => Math.min(b, Math.max(a, v));
          const sx = cl((x0 - dx) / sc, 0, iw), sy = cl((y0 - dy) / sc, 0, ih);
          const sw = Math.max(1e-3, Math.min(iw - sx, (x1 - x0) / sc)), sh = Math.max(1e-3, Math.min(ih - sy, (y1 - y0) / sc));
          const cw = Math.max(1, Math.floor(W * RS)), ch = Math.max(1, Math.floor(H * RS));
          const c = document.createElement('canvas'); c.width = cw; c.height = ch;
          const g = c.getContext('2d');
          g.imageSmoothingEnabled = true; g.imageSmoothingQuality = q;
          g.setTransform(RS, 0, 0, RS, 0, 0);
          // прогрев: первый drawImage только что загруженной картинки в Chromium идёт другим путём
          // декодирования/кэша (сдвиг фильтра до ~20/255); движок рисует их каждый кадр — меряем «устоявшийся» кадр
          for (let k = 0; k < 2; k++) {
            g.drawImage(bg, sx, sy, sw, sh, x0, y0, x1 - x0, y1 - y0);
            for (const o of window.__occ) g.drawImage(o.img, dx + o.c.bx * dw, dy + o.c.by * dh, o.c.bw * dw, o.c.bh * dh);
          }
          g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
          g.drawImage(bg, sx, sy, sw, sh, x0, y0, x1 - x0, y1 - y0);
          const A = g.getImageData(0, 0, cw, ch).data;
          for (const o of window.__occ) g.drawImage(o.img, dx + o.c.bx * dw, dy + o.c.by * dh, o.c.bw * dw, o.c.bh * dh);
          const Bd = g.getImageData(0, 0, cw, ch).data;
          const d = window.__diff(A, Bd, cw);
          return Object.assign({ RS: +RS.toFixed(4), backing: [cw, ch], visibleBX: [(0 - dx) / dw, (W - dx) / dw] }, d);
        }, W, H, dpr, q, { bandHf: scene.surface.bandH, zoom: scene.backdrop.zoom || 1 });
        res.cases.push(Object.assign({ case: cs, smoothing: q }, r));
      }
    }
    res.errors.push(...cap.errors);
    await page.close();

    // путь движка: captureLitBackdrop (через __aq.occluderRoundTrip)
    if (o.engine) {
      for (const cs of ['1512x982@2', '1920x1200@1', '2560x1097@1']) {
        const m = /^(\d+)x(\d+)@([\d.]+)$/.exec(cs);
        const pg = await browser.newPage();
        await pg.setViewport({ width: +m[1], height: +m[2], deviceScaleFactor: +m[3] });
        const cp = L.captureErrors(pg);
        await L.gotoReady(pg, `${server.base}/index.html?test=1&wallpaper=1&nofilter=1&seed=1`);
        const r = await pg.evaluate(async (occ) => {
          window.__aq.step(1 / 30, 60, { render: 'last' });
          const cv = document.querySelector('canvas'), g = cv.getContext('2d');
          const load = (s) => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => no(new Error(s)); im.src = s; });
          const A = g.getImageData(0, 0, cv.width, cv.height).data;
          for (const c of occ) {
            const img = await load(c.src);
            const p = window.__aq.bgMap(c.bx, c.by), q = window.__aq.bgMap(c.bx + c.bw, c.by + c.bh);
            window.__aq.occluderRoundTrip(img, p[0], p[1], q[0] - p[0], q[1] - p[1]);
          }
          const B = g.getImageData(0, 0, cv.width, cv.height).data;
          let mx = 0, n2 = 0;
          for (let i = 0; i < A.length; i += 4) {
            const d = Math.max(Math.abs(A[i] - B[i]), Math.abs(A[i + 1] - B[i + 1]), Math.abs(A[i + 2] - B[i + 2]));
            if (d > 2) n2++; if (d > mx) mx = d;
          }
          return { backing: [cv.width, cv.height], max: mx, over2: n2, sceneFromFile: window.__aq.stats().sceneFromFile };
        }, occ);
        res.engine.push(Object.assign({ case: cs }, r));
        res.errors.push(...cp.errors);
        await pg.close();
      }
    }
  } finally {
    await browser.close();
    await server.close();
  }
  // вердикты раздельно: native и путь движка (captureLitBackdrop — им и рисовать окклюдеры, E4) — гейт;
  // прямой drawImage PNG под bgMap — справочно: в headless Chromium (SwiftShader) фильтр PNG с альфой
  // расходится с фильтром JPEG-задника на единичных пикселях контрастной текстуры (медиана 3, max ≈ 15–20)
  const nat = res.native ? res.native.max : 0, eng = Math.max(0, ...res.engine.map((c) => c.max));
  const dir = Math.max(0, ...res.cases.map((c) => c.max));
  const frac = Math.max(0, ...res.cases.map((c) => c.over2 / (c.backing[0] * c.backing[1])));
  res.gate = { target: '<= 2/255',
    native: { worst: nat, pass: nat <= 2 },
    engine: { worst: eng, pass: res.engine.length > 0 && eng <= 2 },
    direct: { worst: dir, maxFracOver2: +frac.toFixed(5), pass: dir <= 2, note: 'informational: draw occluders via captureLitBackdrop' },
    errors: res.errors.length };
  res.gate.pass = res.gate.native.pass && (res.gate.engine.pass || !o.engine) && res.errors.length === 0;
  const json = JSON.stringify(res, null, 1);
  fs.mkdirSync(path.dirname(path.resolve(String(o.out))), { recursive: true });
  fs.writeFileSync(path.resolve(String(o.out)), json);
  console.log(json);
  L.report(res.errors, [], false);
  if (!res.gate.pass) process.exitCode = 2;
})().catch((e) => { console.error(e); process.exit(1); });
