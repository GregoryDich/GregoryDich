// Гейт этапа V2 «сцена для видео-задника»: маски-окклюдеры колонн поверх живого кадра без рыб не меняют
// ни один пиксель больше чем на 2/255 — на 4 соотношениях сторон × RS 1/2, днём и ночью, на постере и на
// кадрах самого видео. Плюс: весь обязательный реквизит внутри видимого кадра на каждом соотношении.
//   node gates_v2.js [--out FILE.json] [--cases "1512x982@2,1728x1080@1,…"] [--times "1.0,12.3"]
// Раскладка — контракт scene.js v2 (не старый layoutBackdrop): cover × zoom на ВЕСЬ экран (bandH = 0),
//   dx = (W − dw)/2, dy = −(dh − H)·anchorY. Буфер floor(W·RS)×floor(H·RS), RS = min(dpr, √(8.3e6/(W·H))).
// Пути (всё по http с 127.0.0.1 — тот же origin, холсты не «пачкаются»; это тест, не движок):
//   • lit   — путь E1 captureLitBackdrop: копия уже нарисованного кадра под маской (copy), destination-in
//             маской, назад на округлённые device px — ГЕЙТ;
//   • direct — тот же прямоугольник источника (видео/постер) в отдельный холст, destination-in маской,
//             назад — справочно (пересэмплирование другого холста расходится на единицах уровней).
// Код выхода 2 — ошибки страницы или не пройден гейт.
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
    cases: '1512x982@1,1512x982@2,1728x1080@1,1728x1080@2,1920x1080@1,1920x1080@2,2520x1080@1,2520x1080@2,3440x1440@1',
    times: '1.0,12.3', out: path.join(__dirname, 'out', 'gates_v2.json') });
  const root = path.resolve(o.root || L.DEFAULT_ROOT);
  const scene = loadScene(root);
  const B = scene.backdrop;
  const occ = (scene.occluders || []).map((c) => ({ id: c.id, mask: c.mask, bx: c.bx, by: c.by, bw: c.bw, bh: c.bh, px: c.px }));
  const props = (scene.props || []).map((p) => ({ id: p.id, src: p.src, bx: p.bx, byBottom: p.byBottom, bw: p.bw }));
  const server = await L.serve(root);
  const browser = await puppeteer.launch({ executablePath: await chromium.executablePath(), headless: chromium.headless,
    args: [...chromium.args, '--force-color-profile=srgb', '--hide-scrollbars', '--autoplay-policy=no-user-gesture-required'],
    defaultViewport: { width: 800, height: 600 }, protocolTimeout: 900000 });
  const res = { root, scene: { version: scene.version, type: B.type, zoom: B.zoom, anchorY: B.anchorY, safeX: B.safeX, safeY: B.safeY },
    occluders: occ.map((c) => c.id), sources: [], cases: [], props: [], errors: [] };
  try {
    const page = await browser.newPage();
    const cap = L.captureErrors(page);
    await page.goto(server.base + '/scene/README.txt', { waitUntil: 'load' });
    res.sources = await page.evaluate(async (B, occ, times) => {
      const load = (s) => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => no(new Error('load ' + s)); im.src = '/' + s; });
      window.__masks = [];
      for (const c of occ) window.__masks.push({ c, img: await load(c.mask) });
      window.__src = [];
      for (const th of ['day', 'night']) {
        window.__src.push({ name: th + ' poster', el: await load(B[th].poster) });
        for (const t of times) {
          const v = document.createElement('video');
          v.muted = true; v.playsInline = true; v.preload = 'auto'; v.src = '/' + B[th].src;
          await new Promise((ok, no) => { v.onloadeddata = ok; v.onerror = () => no(new Error('video ' + B[th].src)); });
          await new Promise((ok) => { v.onseeked = ok; v.currentTime = t; });
          window.__src.push({ name: `${th} video t=${t}`, el: v });
        }
      }
      window.__diff = (A, Bd, w) => {
        let mx = 0, n1 = 0, n2 = 0, at = -1;
        for (let i = 0; i < A.length; i += 4) {
          const d = Math.max(Math.abs(A[i] - Bd[i]), Math.abs(A[i + 1] - Bd[i + 1]), Math.abs(A[i + 2] - Bd[i + 2]));
          if (d > 1) n1++; if (d > 2) n2++;
          if (d > mx) { mx = d; at = i >> 2; }
        }
        return { max: mx, over1: n1, over2: n2, at: at >= 0 ? [at % w, Math.floor(at / w)] : null };
      };
      return window.__src.map((s) => ({ name: s.name, w: s.el.videoWidth || s.el.naturalWidth, h: s.el.videoHeight || s.el.naturalHeight }));
    }, B, occ, String(o.times).split(',').map(Number));

    for (const cs of String(o.cases).split(',')) {
      const m = /^(\d+)x(\d+)@([\d.]+)$/.exec(cs.trim());
      if (!m) continue;
      const W = +m[1], H = +m[2], dpr = +m[3];
      const r = await page.evaluate((W, H, dpr, B) => {
        const iw = B.w, ih = B.h, RS = Math.min(dpr, Math.sqrt(8.3e6 / (W * H)));
        const sc = Math.max(W / iw, H / ih) * (B.zoom || 1), dw = iw * sc, dh = ih * sc, dx = (W - dw) / 2;
        const ay = B.anchorY != null ? B.anchorY : 1, dy = -(dh - H) * ay;
        const x0 = Math.max(0, dx), x1 = Math.min(W, dx + dw), y0 = Math.max(0, dy), y1 = Math.min(H, dy + dh);
        const cl = (v, a, b) => Math.min(b, Math.max(a, v));
        const sx = cl((x0 - dx) / sc, 0, iw), sy = cl((y0 - dy) / sc, 0, ih);
        const sw = Math.min(iw - sx, (x1 - x0) / sc), sh = Math.min(ih - sy, (y1 - y0) / sc);
        const cw = Math.max(1, Math.floor(W * RS)), ch = Math.max(1, Math.floor(H * RS));
        const c = document.createElement('canvas'); c.width = cw; c.height = ch;
        const g = c.getContext('2d', { willReadFrequently: true });
        g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'low';
        const out = document.createElement('canvas'), og = out.getContext('2d');
        const rects = window.__masks.map((mk) => {
          const x = dx + mk.c.bx * dw, y = dy + mk.c.by * dh, w = mk.c.bw * dw, h = mk.c.bh * dh;
          return { mk, x, y, w, h, pw: Math.max(1, Math.ceil(w * RS)), ph: Math.max(1, Math.ceil(h * RS)), sx: Math.round(x * RS), sy: Math.round(y * RS) };
        });
        const drawBg = (el) => { g.setTransform(RS, 0, 0, RS, 0, 0); g.globalCompositeOperation = 'source-over'; g.fillStyle = '#000'; g.fillRect(0, 0, W, H); g.drawImage(el, sx, sy, sw, sh, x0, y0, x1 - x0, y1 - y0); };
        const lit = (r) => {           // = captureLitBackdrop + рисование на своём z
          out.width = r.pw; out.height = r.ph;
          og.setTransform(1, 0, 0, 1, 0, 0); og.globalCompositeOperation = 'copy';
          const cx0 = Math.max(0, r.sx), cy0 = Math.max(0, r.sy), cx1 = Math.min(cw, r.sx + r.pw), cy1 = Math.min(ch, r.sy + r.ph);
          if (cx1 > cx0 && cy1 > cy0) og.drawImage(c, cx0, cy0, cx1 - cx0, cy1 - cy0, cx0 - r.sx, cy0 - r.sy, cx1 - cx0, cy1 - cy0);
          og.globalCompositeOperation = 'destination-in'; og.drawImage(r.mk.img, 0, 0, r.pw, r.ph);
          g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over';
          g.drawImage(out, r.sx, r.sy);
        };
        const direct = (r, el) => {    // кадр источника → свой холст → маска (справочно)
          out.width = r.pw; out.height = r.ph;
          og.setTransform(1, 0, 0, 1, 0, 0); og.globalCompositeOperation = 'copy';
          const k = iw / r.mk.c.bw / iw;   // доли кадра → px источника
          og.drawImage(el, r.mk.c.bx * iw, r.mk.c.by * ih, r.mk.c.bw * iw, r.mk.c.bh * ih, (r.x * RS - r.sx), (r.y * RS - r.sy), r.w * RS, r.h * RS);
          og.globalCompositeOperation = 'destination-in'; og.drawImage(r.mk.img, 0, 0, r.pw, r.ph);
          g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over';
          g.drawImage(out, r.sx, r.sy);
        };
        const per = [];
        for (const s of window.__src) {
          for (let k = 0; k < 2; k++) { drawBg(s.el); for (const r of rects) lit(r); }       // прогрев
          drawBg(s.el);
          const A = g.getImageData(0, 0, cw, ch).data;
          for (const r of rects) lit(r);
          const Bl = g.getImageData(0, 0, cw, ch).data;
          const dl = window.__diff(A, Bl, cw);
          drawBg(s.el);
          for (const r of rects) direct(r, s.el);
          const Bd = g.getImageData(0, 0, cw, ch).data;
          const dd = window.__diff(A, Bd, cw);
          per.push({ src: s.name, lit: dl, direct: { max: dd.max, over2: dd.over2, fracOver2: +(dd.over2 / (cw * ch)).toFixed(5) } });
        }
        return { RS: +RS.toFixed(4), backing: [cw, ch], visibleBX: [+((0 - dx) / dw).toFixed(4), +((W - dx) / dw).toFixed(4)],
          visibleBY: [+((0 - dy) / dh).toFixed(4), +((H - dy) / dh).toFixed(4)], per };
      }, W, H, dpr, B);
      res.cases.push(Object.assign({ case: cs, aspect: +(W / H).toFixed(3) }, r));
    }
    // реквизит в видимом кадре (по прямоугольнику картинки: доля видимой площади и центр/основание внутри safe)
    const sizes = await page.evaluate(async (props) => {
      const load = (s) => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => no(new Error(s)); im.src = '/' + s; });
      const out = {};
      for (const p of props) { const im = await load(p.src); out[p.id] = [im.naturalWidth, im.naturalHeight]; }
      return out;
    }, props);
    for (const p of props) {
      const [iw, ih] = sizes[p.id];
      const hFrac = (p.bw * B.w * ih / iw) / B.h;          // высота картинки в долях высоты кадра
      const rect = [p.bx - p.bw / 2, p.byBottom - hFrac, p.bx + p.bw / 2, p.byBottom];
      const per = res.cases.map((c) => {
        const vx0 = c.visibleBX[0], vx1 = c.visibleBX[1], vy0 = c.visibleBY[0], vy1 = c.visibleBY[1];
        const ix = Math.max(0, Math.min(rect[2], vx1) - Math.max(rect[0], vx0)), iy = Math.max(0, Math.min(rect[3], vy1) - Math.max(rect[1], vy0));
        const vis = (ix * iy) / ((rect[2] - rect[0]) * (rect[3] - rect[1]));
        const anchorIn = p.bx >= vx0 && p.bx <= vx1;
        return { case: c.case, visibleFrac: +vis.toFixed(3), centerInside: anchorIn };
      });
      const minVis = Math.min(...per.map((q) => q.visibleFrac));
      const inSafeX = rect[0] >= B.safeX[0] - 1e-9 && rect[2] <= B.safeX[1] + 1e-9;
      res.props.push({ id: p.id, rect: rect.map((v) => +v.toFixed(4)), inSafeX, minVisibleFrac: minVis, per });
    }
    // <video> отменяет первый запрос и перезапрашивает диапазонами — 'requestfailed … .mp4 net::ERR_ABORTED' не ошибка
    res.mediaAborts = cap.errors.filter((e) => /\.mp4 net::ERR_ABORTED/.test(String(e))).length;
    res.errors.push(...cap.errors.filter((e) => !/\.mp4 net::ERR_ABORTED/.test(String(e))));
    await page.close();
  } finally {
    await browser.close();
    await server.close();
  }
  const litWorst = Math.max(0, ...res.cases.flatMap((c) => c.per.map((p) => p.lit.max)));
  const dirWorst = Math.max(0, ...res.cases.flatMap((c) => c.per.map((p) => p.direct.max)));
  const dirFrac = Math.max(0, ...res.cases.flatMap((c) => c.per.map((p) => p.direct.fracOver2)));
  // реквизит: прямоугольник внутри safeX, а видимая доля картинки ≥ 0.6 на каждом экране (низ может уходить за
  // кадр — основание актинии и губок нарочно ниже кадра)
  const propsOk = res.props.every((p) => p.inSafeX && p.per.every((q) => q.centerInside) && p.minVisibleFrac >= 0.6);
  res.gate = { target: '<= 2/255 (lit path); props inside safeX and >= 60% visible at every aspect',
    lit: { worst: litWorst, pass: litWorst <= 2 },
    direct: { worst: dirWorst, maxFracOver2: dirFrac, note: 'informational' },
    props: { pass: propsOk }, errors: res.errors.length };
  res.gate.pass = res.gate.lit.pass && propsOk && res.errors.length === 0;
  const json = JSON.stringify(res, null, 1);
  fs.mkdirSync(path.dirname(path.resolve(String(o.out))), { recursive: true });
  fs.writeFileSync(path.resolve(String(o.out)), json);
  console.log(JSON.stringify(res.gate, null, 1));
  L.report(res.errors, [], false);
  if (!res.gate.pass) process.exitCode = 2;
})().catch((e) => { console.error(e); process.exit(1); });
