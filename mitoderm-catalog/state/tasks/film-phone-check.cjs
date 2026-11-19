// Browser check of a product film page (engine: codex-site/mitoderm/pilot/ProductCinema):
// scrolls the film, records which frames each scene shows, and saves one screenshot per scene
// together with the caption box, so captions can be compared against faces and the kit.
//
// Usage (site running on 8787):
//   NODE_PATH=$(npm root -g) USEPROXY=1 node film-phone-check.cjs <slug> <width>x<height> <out dir> [base url]
//   e.g. node film-phone-check.cjs exo-nad 390x664 /tmp/out
// Phone sizes worth checking: 390x664 (iPhone, toolbars shown), 360x640 (small Android), 390x844 (full screen).
const { chromium } = require('playwright');
const [slug = 'exo-nad', size = '390x664', out = '.', base = 'http://127.0.0.1:8787'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
const sleep = ms => new Promise(r => setTimeout(r, ms));

function proxy() {
  if (!process.env.USEPROXY) return undefined;
  const raw = process.env.HTTPS_PROXY || process.env.https_proxy;
  if (!raw) return undefined;
  const u = new URL(raw);
  const o = { server: `${u.protocol}//${u.host}`, bypass: '127.0.0.1,localhost' };
  if (u.username) { o.username = decodeURIComponent(u.username); o.password = decodeURIComponent(u.password); }
  return o;
}

(async () => {
  const p = proxy();
  const browser = await chromium.launch(p ? { proxy: p } : undefined);
  const phone = W < 861;
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, hasTouch: phone, isMobile: phone, locale: 'he-IL' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
  page.on('pageerror', e => errs.push('pageerror ' + String(e).slice(0, 160)));
  await page.goto(`${base}/products/${slug}`, { waitUntil: 'load' });
  await page.waitForFunction(() => { const v = document.querySelector('video.pc-film'); return v && v.readyState >= 2; }, null, { timeout: 120000 });
  const geo = await page.evaluate(() => { const r = document.getElementById('pc-story'); const b = r.getBoundingClientRect(); return { top: b.top + scrollY, height: b.height }; });
  const read = () => page.evaluate(() => {
    const v = document.querySelector('video.pc-film'); const st = document.getElementById('pc-story');
    const cap = [...document.querySelectorAll('.pc-caption')].find(c => getComputedStyle(c.closest('.pc-scene')).visibility === 'visible');
    const box = el => { if (!el) return null; const r = el.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; };
    return { shot: st.dataset.activeShot, frame: Math.round(v.currentTime * 24), painted: v.classList.contains('is-painted'),
      src: (v.currentSrc || '').split('/').pop().slice(0, 13), video: v.videoWidth + 'x' + v.videoHeight, film: box(v), caption: box(cap), hud: box(document.querySelector('.pc-hud')) };
  });
  const go = async (i, steps, wait) => { await page.evaluate(y => scrollTo({ top: y, behavior: 'instant' }), Math.round(geo.top + (geo.height - H) * i / steps)); await sleep(wait); };
  const steps = 64, seen = [];
  for (let i = 0; i <= steps; i++) { await go(i, steps, 450); seen.push({ i, ...(await read()) }); }
  const byShot = {};
  for (const o of seen) (byShot[o.shot] = byShot[o.shot] || []).push(o.i);
  const scenes = {};
  for (const [shot, idx] of Object.entries(byShot)) {
    await go(idx[Math.floor(idx.length / 2)], steps, 1200);
    const s = await read();
    await page.screenshot({ path: `${out}/${slug}-${size}-scene-${shot}.png` });
    scenes[shot] = { frames: [seen[idx[0]].frame, seen[idx[idx.length - 1]].frame], caption: s.caption, hud: s.hud };
  }
  await go(0, steps, 1200);
  const back = await read();
  console.log(JSON.stringify({ size, src: seen[10].src, video: seen[10].video, film: seen[10].film, painted: seen.filter(o => o.painted).length + '/' + seen.length, back: { shot: back.shot, frame: back.frame }, scenes, errs }));
  await browser.close();
})();
