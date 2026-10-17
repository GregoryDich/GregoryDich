// QA of the full V-TECH live page on pre-rendered Blender frames (site/proto/vtech-live.html, build-vtech.py): the page
// is served from a fake origin with its files (seq/, img/), wrapped in the same skeleton the artifact host adds, with
// the real fonts. Checks: the story position follows the scroll monotonically through all runs (60 px steps) and each
// screen holds its key frame while it is read; every frame of every run loads; the frames fade out at the offer; the
// copy keeps the left half; no horizontal scroll; headings below the sticky header; phone: no canvas, the stills sit in
// the slots; reduced motion: key frames only; no JS: the first frame as a still; the lead form validates and completes;
// no console errors. Screenshots per screen and mid-run.
// usage: FONTDIR=<dir with the 4 TTFs> NODE_PATH=$(npm root -g) node verify-live.cjs <page.html> <files dir> <out dir>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [pagePath, filesDir, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
  + fs.readFileSync(pagePath, 'utf8') + '</body></html>';
const ORIGIN = 'https://live.test/';
const FONTDIR = process.env.FONTDIR || path.join(require('os').tmpdir(), 'mitoderm-fonts');
const FONTS = [['Cormorant Garamond', 'CormorantGaramond[wght].ttf'], ['Jost', 'Jost[wght].ttf'], ['Frank Ruhl Libre', 'FrankRuhlLibre[wght].ttf'], ['Heebo', 'Heebo[wght].ttf']];
const FONT_CSS = FONTS.map(([f], i) => `@font-face{font-family:'${f}';src:url(https://fonts.gstatic.com/local/${i}.ttf) format('truetype');font-weight:100 900;font-display:block}`).join('\n');
const STORY = ['meet', 'why', 'inside', 'feel', 'protocol', 'kit'];
const checks = [];
const ok = (name, pass, info = '') => { checks.push({ name, pass, info }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (info ? '  ' + info : '')); };
const TYPES = { '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg' };

async function open(browser, w, h, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: opts.dpr || 1, reducedMotion: opts.reduce ? 'reduce' : 'no-preference', hasTouch: w < 500, javaScriptEnabled: !opts.nojs });
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
  if (!opts.nojs) await p.evaluate(() => document.fonts.ready);
  return { ctx, p, errs };
}

const layout = async (p, tag) => {
  const r = await p.evaluate(ids => {
    const hb = document.querySelector('.top').getBoundingClientRect().bottom;
    const scroller = e => { for (let a = e.parentElement; a; a = a.parentElement) if (/auto|scroll/.test(getComputedStyle(a).overflowX)) return true; return false; };
    const offscreen = [...document.querySelectorAll('main *')].filter(e => { const b = e.getBoundingClientRect(); return b.width && (b.left < -1 || b.right > innerWidth + 1) && !scroller(e); }).map(e => e.tagName + '.' + e.className).slice(0, 5);
    const copyRight = Math.max(...ids.map(id => document.querySelector(`#${id} .copy`).getBoundingClientRect().right));
    const heads = [...document.querySelectorAll('main h1, main h2')].map(h => { const y = h.getBoundingClientRect().top + scrollY; return { y, h }; });
    return { sw: document.documentElement.scrollWidth, iw: innerWidth, hb, offscreen, copyRight, heads: heads.length };
  }, STORY);
  if (r.iw >= 900) ok(`${tag}: the story copy stays in the left half, clear of the 3D`, r.copyRight <= r.iw * 0.53, `copy right edge ${r.copyRight.toFixed(0)} of ${r.iw}`);
  ok(`${tag}: no horizontal scroll`, r.sw <= r.iw, `${r.sw}/${r.iw}`);
  ok(`${tag}: nothing outside the screen`, !r.offscreen.length, r.offscreen.join(' '));
  // every heading, scrolled to its reading position (its section at the top), sits below the sticky header
  const under = await p.evaluate(async () => {
    const bad = [], hb = () => document.querySelector('.top').getBoundingClientRect().bottom;
    for (const s of document.querySelectorAll('main section')) {
      s.scrollIntoView(); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const h = s.querySelector('h1, h2'); if (h && h.getBoundingClientRect().top < hb() - 1) bad.push(s.id || s.className);
    }
    scrollTo(0, 0); return bad;
  });
  ok(`${tag}: headings below the header`, !under.length, under.join(' '));
};

(async () => {
  const browser = await chromium.launch();
  { // desktop: the story
    const { ctx, p, errs } = await open(browser, 1440, 900, { dpr: 2 });
    await layout(p, 'desktop 1440');
    const st0 = await p.evaluate(() => window.__seq()); const N = st0.N, R = st0.R, M = N - 1;
    const end = await p.evaluate(() => document.getElementById('offer').offsetTop);
    const seen = []; let mono = true, prev = -1;
    for (let y = 0; y <= end; y += 60) {
      await p.evaluate(v => scrollTo(0, v), y); await p.waitForTimeout(25);
      const s = await p.evaluate(() => window.__seq()); const g = s.run * M + s.want; seen.push(g);
      if (g < prev) mono = false; prev = g;
    }
    ok('desktop: story position follows the scroll monotonically', mono, seen.filter((g, i) => i % 4 === 0).join(','));
    ok('desktop: the story runs from S1 to S6', seen[0] === 0 && seen[seen.length - 1] === R * M, `${seen[0]}..${seen[seen.length - 1]} of ${R * M}`);
    await p.waitForFunction(R => window.__seq().loaded.every(n => n === 40), R, { timeout: 120000 }).catch(() => {});
    const ld = (await p.evaluate(() => window.__seq())).loaded;
    ok('desktop: every frame of every run loads', ld.every(n => n === N), ld.join('/'));
    // each screen at its reading position (section top at the top of the screen): its key frame, shown
    const holds = [];
    for (let k = 0; k < STORY.length; k++) {
      await p.evaluate(id => scrollTo(0, document.getElementById(id).offsetTop), STORY[k]); await p.waitForTimeout(250);
      const s = await p.evaluate(() => window.__seq()); const g = s.run * M + s.want, sg = s.shown ? s.shown[0] * M + s.shown[1] : -1;
      holds.push(`${STORY[k]}:${g}/${sg}`); if (g !== k * M || sg !== k * M) holds.push('!');
      await p.screenshot({ path: `${out}/desk-s${k + 1}.jpg`, type: 'jpeg', quality: 80 });
    }
    ok('desktop: each screen holds its key frame while read', !holds.includes('!'), holds.join(' '));
    for (let k = 0; k < R; k++) {   // mid-run frames, to look at
      const y = await p.evaluate(([a, b]) => (document.getElementById(a).offsetTop + document.getElementById(b).offsetTop) / 2 + innerHeight * 0.05, [STORY[k], STORY[k + 1]]);
      await p.evaluate(v => scrollTo(0, v), y); await p.waitForTimeout(250);
      await p.screenshot({ path: `${out}/desk-run${k + 1}.jpg`, type: 'jpeg', quality: 80 });
    }
    await p.evaluate(() => scrollTo(0, document.getElementById('offer').offsetTop)); await p.waitForTimeout(250);
    const op = (await p.evaluate(() => window.__seq())).opacity;
    ok('desktop: the frames fade out at the offer', op === 0, `opacity ${op}`);
    await p.screenshot({ path: `${out}/desk-s7-offer.jpg`, type: 'jpeg', quality: 80 });
    for (const id of ['specialists']) { await p.evaluate(i => document.getElementById(i).scrollIntoView(), id); await p.waitForTimeout(300); await p.screenshot({ path: `${out}/desk-s8.jpg`, type: 'jpeg', quality: 80 }); }
    await p.evaluate(() => document.querySelector('.related').scrollIntoView()); await p.waitForTimeout(300);
    await p.screenshot({ path: `${out}/desk-s9.jpg`, type: 'jpeg', quality: 80 });
    // the lead form: opens from the price button, validates, completes
    await p.evaluate(() => scrollTo(0, 0)); await p.click('.top [data-lead]');
    const opened = await p.evaluate(() => document.getElementById('lead').open);
    await p.click('#lead .submit'); const errsShown = await p.evaluate(() => [...document.querySelectorAll('#lead .err')].filter(e => e.textContent).length);
    await p.screenshot({ path: `${out}/desk-form-errors.jpg`, type: 'jpeg', quality: 80 });
    await p.fill('[name=name]', 'בדיקה בדיקה'); await p.fill('[name=profession]', 'קוסמטיקאית'); await p.fill('[name=email]', 'test@example.com'); await p.fill('[name=phone]', '0541234567');
    await p.check('[name=consent]'); await p.click('#lead .submit'); await p.waitForTimeout(1600);
    const doneShown = await p.evaluate(() => !document.querySelector('.lead-done').hidden);
    await p.screenshot({ path: `${out}/desk-form-done.jpg`, type: 'jpeg', quality: 80 });
    ok('desktop: the lead form opens, validates and completes', opened && errsShown === 5 && doneShown, `open ${opened}, ${errsShown} errors on empty, done ${doneShown}`);
    ok('desktop: no console errors', !errs.length, errs.join(' | '));
    await ctx.close();
  }
  for (const [w, h] of [[390, 844], [360, 780]]) { // phone: stills in the slots
    const { ctx, p, errs } = await open(browser, w, h, { dpr: 2 });
    await layout(p, `phone ${w}`);
    const r = await p.evaluate(() => ({ canvas: getComputedStyle(document.getElementById('seq')).display,
      slots: [...document.querySelectorAll('.slot')].map(i => ({ w: i.getBoundingClientRect().width, nat: i.naturalWidth, vis: getComputedStyle(i).display !== 'none' })) }));
    ok(`phone ${w}: no canvas`, r.canvas === 'none', r.canvas);
    ok(`phone ${w}: stills visible in the slots`, r.slots.length === 6 && r.slots.every(s => s.vis && s.nat > 0 && s.w > 80), JSON.stringify(r.slots.map(s => [Math.round(s.w), s.nat])));
    ok(`phone ${w}: slot stills sharp at 2x`, r.slots.every(s => s.nat >= s.w * 2 * 0.95), r.slots.map(s => `${s.nat}px for ${s.w.toFixed(0)}`).join(', '));
    const seqReq = await p.evaluate(() => performance.getEntriesByType('resource').filter(e => e.name.includes('/seq/')).length);
    ok(`phone ${w}: no sequence frames downloaded`, seqReq === 0, `${seqReq} requests`);
    for (const id of [...STORY, 'offer', 'specialists']) {
      await p.evaluate(i => document.getElementById(i).scrollIntoView(), id); await p.waitForTimeout(150);
      await p.screenshot({ path: `${out}/phone${w}-${id}.jpg`, type: 'jpeg', quality: 80 });
    }
    ok(`phone ${w}: no console errors`, !errs.length, errs.join(' | '));
    await ctx.close();
  }
  { // reduced motion: only the key frames
    const { ctx, p } = await open(browser, 1440, 900, { reduce: true });
    const end = await p.evaluate(() => document.getElementById('offer').offsetTop); const set = new Set();
    for (let y = 0; y <= end; y += 90) { await p.evaluate(v => scrollTo(0, v), y); await p.waitForTimeout(20); set.add(await p.evaluate(() => window.__seq().want)); }
    const N = await p.evaluate(() => window.__seq().N);
    ok('reduced motion: key frames only', [...set].every(v => v === 0 || v === N - 1), [...set].join(','));
    await ctx.close();
  }
  { // no JavaScript: the first key frame as a still, the copy visible
    const { ctx, p } = await open(browser, 1440, 900, { nojs: true }); await p.waitForTimeout(300);
    const v = await p.evaluate(() => { const s = document.querySelector('.still'); return { d: getComputedStyle(s).display, w: s.naturalWidth, h1: getComputedStyle(document.querySelector('h1')).opacity }; });
    ok('no JS: first key frame shown, copy visible', v.d !== 'none' && v.w > 0 && v.h1 === '1', JSON.stringify(v));
    await ctx.close();
  }
  await browser.close();
  const fails = checks.filter(c => !c.pass);
  console.log(`\n${checks.length - fails.length}/${checks.length} checks passed`);
  fs.writeFileSync(`${out}/report.json`, JSON.stringify(checks, null, 1));
})();
