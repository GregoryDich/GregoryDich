// Browser check of the V-TECH page layout at one window size (engine: codex-site/mitoderm/pilot/VTechStory):
// where the film stands on the stage, whether the pack's place (vtech-entry.ts) lies on the pack in the film, where
// each chapter's copy stands, and - with "entry" - whether the pack chosen on the home page lands on that place.
//
// Usage (site running on 8787):
//   NODE_PATH=$(npm root -g) USEPROXY=1 node vtech-layout-check.cjs <WxH> <out dir> [probe|entry] [base url]
//   probe (default): one screenshot per chapter (vtech-<size>-<n>.png) and a JSON line with the numbers:
//     stage, film = the film's box on the screen, place = the pack's place, expected = that place worked out here from
//     the film's box (the two must agree to a pixel), chapters = id, copy box and how far the copy reaches into the film
//     ("overFilm", px; the film's lower edge is soft for about 170 px on a tablet held sideways).
//   entry: opens the home page, chooses V-TECH in the banner, scrolls through the entry and prints how far the flying
//     pack ends from its place (off, px) and how well it fills it (fit, 1 = exactly); screenshots vtech-entry-<size>-<n>.png.
// Sizes worth checking: 1440x900, 1024x768, 1180x820, 1366x1024, 1272x800 (just under 16:10), 1024x1366, 390x664.
const { chromium } = require('playwright');
const [size = '1440x900', out = '.', mode = 'probe', base = 'http://127.0.0.1:8787'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const MEDIA = W <= 860 ? { width: 406, height: 720, box: { left: 104, top: 197, width: 193, height: 435 } }
  : { width: 1912, height: 1080, box: { left: 727, top: 31, width: 466, height: 1014 } };   // vtech-entry.ts

function proxy() {
  if (!process.env.USEPROXY) return undefined;
  const raw = process.env.HTTPS_PROXY || process.env.https_proxy;
  if (!raw) return undefined;
  const u = new URL(raw);
  const o = { server: `${u.protocol}//${u.host}`, bypass: '127.0.0.1,localhost' };
  if (u.username) { o.username = decodeURIComponent(u.username); o.password = decodeURIComponent(u.password); }
  return o;
}
const round = r => r && { left: Math.round(r.left), top: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height) };

(async () => {
  const p = proxy();
  const browser = await chromium.launch(p ? { proxy: p } : undefined);
  const phone = W < 861;
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, hasTouch: phone, isMobile: phone, locale: 'he-IL' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
  page.on('pageerror', e => errs.push('pageerror ' + String(e).slice(0, 160)));
  const box = sel => page.evaluate(s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { left: r.left, top: r.top, width: r.width, height: r.height }; }, sel);

  if (mode === 'entry') {
    await page.goto(base + '/', { waitUntil: 'load' });
    await sleep(2500);
    const sel = `[data-collection-frame="${phone ? 'mobile' : 'desktop'}"] .mc-photo-hotspot[data-product="v-tech-system"]`;
    const point = await page.evaluate(s => { const e = document.querySelector(s); if (!e) return null; e.scrollIntoView({ block: 'center' }); const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, sel);
    if (!point) { console.log(JSON.stringify({ size, mode, error: 'no V-TECH hotspot in the banner' })); await browser.close(); return; }
    await sleep(600);
    const at = await page.evaluate(s => { const r = document.querySelector(s).getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, sel);
    await page.mouse.click(at.x, at.y);
    await page.waitForURL('**/products/v-tech-system', { timeout: 20000 });
    await page.waitForSelector('.vc-product-flight[data-phase="awaiting-scroll"]', { timeout: 20000 });
    await sleep(800);
    const start = await page.evaluate(() => { const s = document.querySelector('[data-vtech-story]'); return { start: Number(s.dataset.entryStart) || 0, units: Number(s.dataset.entryUnits) || .9, stage: document.querySelector('[data-vtech-stage]').clientHeight }; });
    const distance = start.stage * start.units;
    let last = null;
    const steps = [0, .25, .5, .75, .9, .985];
    for (let k = 0; k < steps.length; k++) {
      await page.evaluate(y => scrollTo({ top: y, behavior: 'instant' }), Math.round(start.start + distance * steps[k]));
      await sleep(900);
      await page.screenshot({ path: `${out}/vtech-entry-${size}-${k}.png` });
      last = await box('.vc-flight-cutout');
    }
    const place = await box('[data-flight-target="v-tech-system"]'), film = await box('.vts-camera-media');
    const off = place && last ? Math.round(Math.hypot(last.left + last.width / 2 - place.left - place.width / 2, last.top + last.height / 2 - place.top - place.height / 2)) : null;
    const fit = place && last ? +(Math.min(last.width / place.width, last.height / place.height)).toFixed(3) : null;
    await page.evaluate(y => scrollTo({ top: y, behavior: 'instant' }), Math.round(start.start + distance + 40));
    await sleep(1200);
    await page.screenshot({ path: `${out}/vtech-entry-${size}-${steps.length}.png` });
    console.log(JSON.stringify({ size, mode, film: round(film), place: round(place), last: round(last), off, fit, flightGone: !(await page.$('.vc-product-flight')), errs }));
    await browser.close();
    return;
  }

  await page.goto(base + '/products/v-tech-system', { waitUntil: 'load' });
  await page.waitForFunction(() => { const v = document.querySelector('.vts-camera-media video'); return v && v.readyState >= 2; }, null, { timeout: 120000 });
  await sleep(1500);
  const stage = await box('[data-vtech-stage]'), film = await box('.vts-camera-media'), place = await box('[data-flight-target="v-tech-system"]');
  const scale = Math.max(film.width / MEDIA.width, film.height / MEDIA.height);
  const expected = { left: film.left + (film.width - MEDIA.width * scale) / 2 + MEDIA.box.left * scale, top: film.top + (film.height - MEDIA.height * scale) / 2 + MEDIA.box.top * scale, width: MEDIA.box.width * scale, height: MEDIA.box.height * scale };
  const scenes = await page.evaluate(() => { const s = document.querySelector('[data-vtech-story]'); const top = s.getBoundingClientRect().top + scrollY; const h = document.querySelector('[data-vtech-stage]').clientHeight; return [...document.querySelectorAll('.vts-scene')].map(a => ({ id: a.id, y: top + (Number(a.dataset.sceneStart) + Number(a.dataset.sceneWeight) * .5) * h })); });
  const chapters = [];
  for (let k = 0; k < scenes.length; k++) {
    await page.evaluate(y => scrollTo({ top: y, behavior: 'instant' }), Math.round(scenes[k].y));
    await sleep(1600);
    const copy = await page.evaluate(() => { const a = document.querySelector('.vts-scene[data-active=true]'); const c = a && a.querySelector('.vts-caption,.vc-story-evidence-panel,.vc-story-offer-copy'); if (!c) return null; const r = c.getBoundingClientRect(); return { id: a.id, left: r.left, top: r.top, width: r.width, height: r.height }; });
    await page.screenshot({ path: `${out}/vtech-${size}-${k}.png` });
    chapters.push(copy && { id: copy.id, copy: round(copy), overFilm: Math.max(0, Math.round(film.top + film.height - copy.top)) });
  }
  console.log(JSON.stringify({ size, mode, stage: round(stage), film: round(film), place: round(place), expected: round(expected), chapters, errs }));
  await browser.close();
})();
