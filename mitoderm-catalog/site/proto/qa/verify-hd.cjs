// HD check of a live page: scrolls the whole page at a phone and two desktop sizes and, at every step, measures each
// visible picture against the screen: an <img> (its drawn box, after object-fit), a CSS background image, a canvas
// (three.js: its backing store), and the frame story's chosen tier (V-TECH frames: the full 16:10 frame's width).
// need = drawn CSS px × DPR (desktop DPR as the frame engine counts it, ≤ 2); have = the picture's own pixels.
// An element passes when have ≥ 0.95 × need at its worst moment. Blurred-by-design layers are listed apart (SOFT), not
// failed: the soft and bokeh cell sprites, the deep plate, the line's smoke (the full 3456 px source) and, on a phone,
// the MASK page's fixed canvas, which draws only the far smoke there (the product has its own canvas in the slot), and
// the smoke painted into the MASK form's panel. The reveals (.rv) are shown at once; the lead form is opened and measured too;
// a frame canvas is measured twice: its own pixels and the tier of the frames drawn into it (the phone at its full DPR).
// usage: FONTDIR=<dir with Rubik[wght].ttf> [THREE=<three.module.min.js>] NODE_PATH=$(npm root -g)
//        node verify-hd.cjs <page.html> <files dir | -> <out.json> [wrap=1: add the artifact skeleton]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [pagePath, filesDir, out, wrap = '1'] = process.argv.slice(2);
const body = fs.readFileSync(pagePath, 'utf8');
const html = wrap === '1' ? '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
  + body + '</body></html>' : body;
const ORIGIN = 'https://hd.test/';
const FONTDIR = process.env.FONTDIR || path.join(require('os').tmpdir(), 'mitoderm-fonts');
const FONT_CSS = "@font-face{font-family:'Rubik';src:url(https://fonts.gstatic.com/local/0.ttf) format('truetype');font-weight:100 900;font-display:block}";
const TYPES = { '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.json': 'application/json' };
const SIZES = [{ name: 'phone 390×844 @3', w: 390, h: 844, dpr: 3 }, { name: 'laptop 1440×900 @2', w: 1440, h: 900, dpr: 2 },
  { name: 'desktop 1920×1080 @2', w: 1920, h: 1080, dpr: 2 }];
const SOFT = (it, size) => /cells\/[cm]\d\d-[12]\.webp|plate\.webp|img\/bg\.webp/.test(it.src) || (size.w < 900 && it.el === 'canvas#gl')
  || /^canvas$/.test(it.el) && it.y === 'form';   // the form panel's smoke (MASK), painted small on purpose
// the frame story's crop boxes, as build-vtech.py wrote them into the page ({"runs": […], "tiers": …})
const RUNS = (() => { const i = html.indexOf('{"runs":'); if (i < 0) return [];
  for (let d = 0, j = i; j < html.length; j++) { d += html[j] === '{' ? 1 : html[j] === '}' ? -1 : 0; if (!d) return JSON.parse(html.slice(i, j + 1)).runs; } return []; })();

async function measure(browser, size) {
  const ctx = await browser.newContext({ viewport: { width: size.w, height: size.h }, deviceScaleFactor: size.dpr, hasTouch: size.w < 500 });
  const p = await ctx.newPage(); const errs = [];
  await ctx.addInitScript(r => { window.__cfgRuns = r; }, RUNS);
  p.on('pageerror', e => errs.push(e.message.slice(0, 160)));
  await ctx.route('https://fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: FONT_CSS }));
  await ctx.route('https://fonts.gstatic.com/local/**', r => r.fulfill({ path: path.join(FONTDIR, 'Rubik[wght].ttf'), contentType: 'font/ttf' }));
  if (process.env.THREE) await ctx.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: process.env.THREE, contentType: 'application/javascript' }));
  await ctx.route(ORIGIN + '**', r => {
    const rel = decodeURIComponent(new URL(r.request().url()).pathname.slice(1));
    if (!rel || rel === 'index.html') return r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
    const f = filesDir === '-' ? '' : path.join(filesDir, rel);
    return f && fs.existsSync(f) ? r.fulfill({ path: f, contentType: TYPES[path.extname(f)] || 'application/octet-stream' }) : r.fulfill({ status: 404, body: '' });
  });
  await p.goto(ORIGIN + 'index.html', { waitUntil: 'load' });
  await p.evaluate(() => document.fonts.ready);
  await p.waitForFunction(() => window.__seq || document.documentElement.classList.contains('no-gl') || document.querySelector('canvas'), null, { timeout: 20000 }).catch(() => {});
  await p.waitForTimeout(1500);
  // the scroll reveals (.rv) end at full opacity: shown at once, so a slow software-GL page is measured as it is read
  await p.addStyleTag({ content: '.rv{opacity:1!important;transform:none!important;transition:none!important}' });
  await p.evaluate(() => document.querySelectorAll('.rv').forEach(e => e.classList.add('in')));
  const worst = new Map();
  const step = async y => {
    await p.waitForTimeout(350);
    await p.waitForFunction(() => [...document.images].every(i => i.complete || !i.checkVisibility()), null, { timeout: 4000 }).catch(() => {});
    const rows = await p.evaluate(async ({ dpr, w }) => {
      const D = w < 900 ? dpr : Math.min(dpr, 2), vw = innerWidth, vh = innerHeight, res = [];
      const seen = el => { const b = el.getBoundingClientRect(); return b.width > 2 && b.height > 2 && b.bottom > 0 && b.top < vh && b.right > 0 && b.left < vw
        && el.checkVisibility({ opacityProperty: true, visibilityProperty: true }) && +getComputedStyle(el).opacity > 0.02 ? b : null; };
      const name = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/).join('.') : '');
      const box = (el, b) => {   // the element's own drawn size: a rotated one by its layout size × its transform's scale
        const t = getComputedStyle(el).transform;
        if (!t || t === 'none' || !el.offsetWidth) return [b.width, b.height];
        const m = new DOMMatrix(t); return [el.offsetWidth * Math.hypot(m.a, m.b), el.offsetHeight * Math.hypot(m.c, m.d)];
      };
      const fit = (mode, nw, nh, bw, bh) => {   // the drawn size (CSS px) of an nw×nh picture in a bw×bh box
        if (mode === 'contain' || mode === 'scale-down') { const s = Math.min(bw / nw, bh / nh, mode === 'scale-down' ? 1 : Infinity); return [nw * s, nh * s]; }
        if (mode === 'cover') { const s = Math.max(bw / nw, bh / nh); return [nw * s, nh * s]; }
        if (mode === 'none') return [nw, nh];
        return [bw, bh];
      };
      const cache = window.__sizeCache || (window.__sizeCache = {});   // the file's own pixels (srcset densities aside)
      const natural = url => cache[url] || (cache[url] = new Promise(r => { const i = new Image(); i.onload = () => r([i.naturalWidth, i.naturalHeight]); i.onerror = () => r([0, 0]); i.src = url; }));
      const label = (url, nw, nh) => url.startsWith('data:') ? 'data:' + nw + '×' + nh : url;
      for (const im of document.images) {
        const b = seen(im); if (!b || !im.naturalWidth) continue;
        const url = im.currentSrc || im.src, [nw, nh] = await natural(url); if (!nw) continue;
        const [bw, bh] = box(im, b), [dw, dh] = fit(getComputedStyle(im).objectFit, nw, nh, bw, bh);
        res.push({ el: name(im), src: label(url, nw, nh), have: [nw, nh], need: [Math.round(dw * D), Math.round(dh * D)] });
      }
      const split = v => { const out = []; let d = 0, s = ''; for (const ch of v) { if (ch === '(') d++; if (ch === ')') d--; if (ch === ',' && !d) { out.push(s.trim()); s = ''; } else s += ch; } out.push(s.trim()); return out; };
      for (const el of document.querySelectorAll('body *')) {
        const cs = getComputedStyle(el); if (!cs.backgroundImage.includes('url(')) continue;
        const b = seen(el); if (!b) continue;
        const layers = split(cs.backgroundImage), sizes = split(cs.backgroundSize);
        for (const [k, layer] of layers.entries()) {   // each url() layer with its own background-size
          const m = layer.match(/^url\("?([^")]+)"?\)$/); if (!m) continue;
          const [nw, nh] = await natural(m[1]); if (!nw) continue;
          const bs = sizes[k % sizes.length]; let dw, dh;
          if (bs === 'cover' || bs === 'contain') [dw, dh] = fit(bs, nw, nh, b.width, b.height);
          else {
            const [a = 'auto', c = 'auto'] = bs.split(' '), len = (v, full) => v.endsWith('px') ? parseFloat(v) : v.endsWith('%') ? full * parseFloat(v) / 100 : null;
            dw = len(a, b.width); dh = len(c, b.height);
            if (dw == null && dh == null) [dw, dh] = [nw, nh]; else if (dw == null) dw = dh * nw / nh; else if (dh == null) dh = dw * nh / nw;
          }
          res.push({ el: name(el), src: label(m[1], nw, nh), have: [nw, nh], need: [Math.round(dw * D), Math.round(dh * D)] });
        }
      }
      const st = window.__seq ? window.__seq() : null;
      for (const cv of document.querySelectorAll('canvas')) {
        const b = seen(cv); if (!b) continue;
        res.push({ el: name(cv), src: 'canvas', have: [cv.width, cv.height], need: [Math.round(b.width * D), Math.round(b.height * D)] });
        if (st && !st.scene && cv.id === 'seq' && st.tier) {   // the frames: the full 16:10 frame's width, as engine/story.js measure()
          const runs = window.__cfgRuns || [], sh = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--stage-h'));
          let F = Math.max(vw / 16, vh / 10) * 16;
          if (w < 900 && sh && runs.length) {   // the phone stage: the union of the crop boxes fits the stage
            const U = runs.reduce((u, r) => [Math.min(u[0], r.box[0]), Math.min(u[1], r.box[1]), Math.max(u[2], r.box[2]), Math.max(u[3], r.box[3])], [1, 1, 0, 0]);
            F = 16 * Math.min(0.98 * vw / ((U[2] - U[0]) * 16), 0.96 * sh / ((U[3] - U[1]) * 10));
          }
          res.push({ el: 'frames (tier ' + st.tier + ', ' + st.mode + ')', src: 'seq/' + st.tier, have: [st.tier, Math.round(st.tier / 1.6)], need: [Math.round(F * D), Math.round(F * D / 1.6)] });
        }
      }
      return res;
    }, { dpr: size.dpr, w: size.w });
    for (const r of rows) {
      const ratio = Math.min(r.have[0] / r.need[0], r.have[1] / r.need[1]);
      const key = r.el + ' ' + r.src;
      if (!worst.has(key) || ratio < worst.get(key).ratio) worst.set(key, { ...r, ratio: +ratio.toFixed(2), y });
    }
  };
  const height = await p.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y <= height; y += Math.round(size.h * 0.5)) { await p.evaluate(v => scrollTo(0, v), y); await step(y); }
  // the lead form's dialog (its panel picture and background), opened from the first price button
  if (await p.evaluate(() => { const a = document.querySelector('[data-lead]'); if (!a) return false; a.click(); return true; })) {
    await p.waitForTimeout(600); await step('form'); await p.keyboard.press('Escape');
  }
  await ctx.close();
  return { size: size.name, errs, items: [...worst.values()].sort((a, b) => a.ratio - b.ratio) };
}

(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const report = [];
  for (const s of SIZES) {
    const r = await measure(browser, s); report.push(r);
    console.log(`\n== ${r.size}` + (r.errs.length ? `  page errors: ${r.errs.join(' | ')}` : ''));
    for (const it of r.items) {
      const soft = SOFT(it, s);
      it.verdict = it.ratio >= 0.95 ? 'PASS' : soft ? 'SOFT' : 'FAIL';
      console.log(`${it.verdict} ${String(it.ratio).padStart(5)}  have ${it.have.join('×')}  need ${it.need.join('×')}  ${it.el}  ${String(it.src).replace(ORIGIN, '').slice(0, 70)}`);
    }
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(report, null, 1));
  const fails = report.flatMap(r => r.items.filter(i => i.verdict === 'FAIL').map(i => r.size + ': ' + i.el + ' ' + String(i.src).replace(ORIGIN, '')));
  console.log(`\n${fails.length ? fails.length + ' below HD' : 'all HD'} (${report.reduce((n, r) => n + r.items.length, 0)} pictures measured)`);
})();
