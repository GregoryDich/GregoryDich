// QA of a live page on pre-rendered Blender frames (site/proto/vtech-scroll-sample.html): the page is served from a
// fake origin with its files (frames, img/), wrapped in the same skeleton the artifact host adds, with the real fonts.
// Checks: the frame index follows the scroll monotonically (60 px steps) and every frame loads; no horizontal scroll;
// the heading is not under the sticky header; phone: no canvas, the stills sit in the slots; reduced motion: key frames
// only; no console errors. Screenshots per position.
// usage: FONTDIR=<dir with the 4 TTFs> node verify-scroll.cjs <page.html> <files dir> <out dir>   (NODE_PATH → playwright)
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [pagePath, filesDir, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
  + fs.readFileSync(pagePath, 'utf8') + '</body></html>';
const ORIGIN = 'https://scroll.test/';
const FONTDIR = process.env.FONTDIR || path.join(require('os').tmpdir(), 'mitoderm-fonts');
const FONTS = [['Cormorant Garamond', 'CormorantGaramond[wght].ttf'], ['Jost', 'Jost[wght].ttf'], ['Frank Ruhl Libre', 'FrankRuhlLibre[wght].ttf'], ['Heebo', 'Heebo[wght].ttf']];
const FONT_CSS = FONTS.map(([f], i) => `@font-face{font-family:'${f}';src:url(https://fonts.gstatic.com/local/${i}.ttf) format('truetype');font-weight:100 900;font-display:block}`).join('\n');
const checks = [];
const ok = (name, pass, info = '') => { checks.push({ name, pass, info }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (info ? '  ' + info : '')); };
const TYPES = { '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg' };

async function open(browser, w, h, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: opts.dpr || 1, reducedMotion: opts.reduce ? 'reduce' : 'no-preference', hasTouch: w < 500 });
  const p = await ctx.newPage(); const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); });
  p.on('pageerror', e => errs.push('PAGEERROR ' + e.message.slice(0, 200)));
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: FONT_CSS }));
  await p.route('https://fonts.gstatic.com/local/**', r => r.fulfill({ path: path.join(FONTDIR, FONTS[+r.request().url().match(/(\d+)\.ttf$/)[1]][1]), contentType: 'font/ttf' }));
  await p.route(ORIGIN + '**', r => {
    const rel = decodeURIComponent(new URL(r.request().url()).pathname.slice(1));
    if (!rel || rel === 'index.html') return r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
    const f = path.join(filesDir, rel);
    return fs.existsSync(f) ? r.fulfill({ path: f, contentType: TYPES[path.extname(f)] || 'application/octet-stream' }) : r.fulfill({ status: 404, body: '' });
  });
  await p.goto(ORIGIN + 'index.html', { waitUntil: 'load' });
  await p.evaluate(() => document.fonts.ready);
  return { ctx, p, errs };
}

const layout = async (p, tag) => {
  const r = await p.evaluate(() => {
    const hb = document.querySelector('.top').getBoundingClientRect().bottom, h1 = document.querySelector('h1').getBoundingClientRect();
    const offscreen = [...document.querySelectorAll('main *')].filter(e => { const b = e.getBoundingClientRect(); return b.width && (b.left < -1 || b.right > innerWidth + 1); }).map(e => e.tagName + '.' + e.className).slice(0, 5);
    return { sw: document.documentElement.scrollWidth, iw: innerWidth, hb, h1top: h1.top, offscreen };
  });
  ok(`${tag}: no horizontal scroll`, r.sw <= r.iw, `${r.sw}/${r.iw}`);
  ok(`${tag}: nothing outside the screen`, !r.offscreen.length, r.offscreen.join(' '));
  ok(`${tag}: heading below the header`, r.h1top >= r.hb, `h1 ${r.h1top.toFixed(0)} header ${r.hb.toFixed(0)}`);
};

(async () => {
  const browser = await chromium.launch();
  { // desktop: the scrub
    const { ctx, p, errs } = await open(browser, 1440, 900, { dpr: 2 });
    await p.waitForFunction(() => window.__seq && window.__seq().loaded === window.__seq().N, null, { timeout: 60000 }).catch(() => {});
    const st = await p.evaluate(() => window.__seq());
    ok('desktop: every frame loads', st.loaded === st.N, `${st.loaded}/${st.N}`);
    await layout(p, 'desktop 1440');
    const end = await p.evaluate(() => document.getElementById('why').offsetTop);
    const seen = []; let mono = true, prev = -1, lag = 0;
    for (let y = 0; y <= end + 60; y += 60) {
      await p.evaluate(v => scrollTo(0, v), y); await p.waitForTimeout(40);
      const s = await p.evaluate(() => window.__seq()); seen.push(s.want);
      if (s.want < prev) mono = false; prev = s.want; if (s.shown !== s.want) lag++;
    }
    ok('desktop: frame follows the scroll monotonically', mono, seen.join(','));
    ok('desktop: the run goes from the first to the last frame', seen[0] === 0 && seen[seen.length - 1] === st.N - 1, `${seen[0]}..${seen[seen.length - 1]}`);
    ok('desktop: shown frame equals the wanted frame', lag === 0, `${lag} lagging steps`);
    for (const f of [0, 0.25, 0.5, 0.75, 1]) {
      await p.evaluate(v => scrollTo(0, v), Math.round(end * f)); await p.waitForTimeout(120);
      await p.screenshot({ path: `${out}/desk-${Math.round(f * 100)}.jpg`, type: 'jpeg', quality: 80 });
    }
    ok('desktop: no console errors', !errs.length, errs.join(' | '));
    await ctx.close();
  }
  for (const [w, h] of [[390, 844], [360, 780]]) { // phone: stills in the slots
    const { ctx, p, errs } = await open(browser, w, h, { dpr: 2 });
    await layout(p, `phone ${w}`);
    const r = await p.evaluate(() => ({ canvas: getComputedStyle(document.getElementById('seq')).display,
      slots: [...document.querySelectorAll('.slot')].map(i => ({ w: i.getBoundingClientRect().width, nat: i.naturalWidth, vis: getComputedStyle(i).display !== 'none' })) }));
    ok(`phone ${w}: no canvas`, r.canvas === 'none', r.canvas);
    ok(`phone ${w}: stills visible in the slots`, r.slots.every(s => s.vis && s.nat > 0 && s.w > 80), JSON.stringify(r.slots));
    ok(`phone ${w}: slot stills sharp at 2x`, r.slots.every(s => s.nat >= s.w * 2 * 0.95), r.slots.map(s => `${s.nat}px for ${s.w.toFixed(0)}`).join(', '));
    await p.screenshot({ path: `${out}/phone${w}-top.jpg`, type: 'jpeg', quality: 80 });
    await p.evaluate(() => document.getElementById('why').scrollIntoView()); await p.waitForTimeout(80);
    await p.screenshot({ path: `${out}/phone${w}-why.jpg`, type: 'jpeg', quality: 80 });
    ok(`phone ${w}: no console errors`, !errs.length, errs.join(' | '));
    await ctx.close();
  }
  { // reduced motion: only the two key frames
    const { ctx, p } = await open(browser, 1440, 900, { reduce: true });
    const end = await p.evaluate(() => document.getElementById('why').offsetTop); const set = new Set();
    for (let y = 0; y <= end; y += 90) { await p.evaluate(v => scrollTo(0, v), y); await p.waitForTimeout(30); set.add(await p.evaluate(() => window.__seq().want)); }
    const N = await p.evaluate(() => window.__seq().N);
    ok('reduced motion: key frames only', [...set].every(v => v === 0 || v === N - 1), [...set].join(','));
    await ctx.close();
  }
  { // no JavaScript: the first key frame is shown as a still
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false }); const p = await ctx.newPage();
    await p.route(ORIGIN + '**', r => { const rel = new URL(r.request().url()).pathname.slice(1); const f = path.join(filesDir, rel);
      return rel === 'index.html' ? r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html }) : fs.existsSync(f) ? r.fulfill({ path: f }) : r.fulfill({ status: 404, body: '' }); });
    await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: '' }));
    await p.goto(ORIGIN + 'index.html'); await p.waitForTimeout(300);
    const v = await p.evaluate(() => { const s = document.querySelector('.still'); return { d: getComputedStyle(s).display, w: s.naturalWidth }; });
    ok('no JS: first key frame shown', v.d !== 'none' && v.w > 0, JSON.stringify(v));
    await ctx.close();
  }
  await browser.close();
  const fails = checks.filter(c => !c.pass);
  console.log(`\n${checks.length - fails.length}/${checks.length} checks passed`);
  fs.writeFileSync(`${out}/report.json`, JSON.stringify(checks, null, 1));
})();
