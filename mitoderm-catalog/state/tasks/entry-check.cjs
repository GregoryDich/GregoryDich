// Browser check of the entry from the home page into a product (codex-site/mitoderm/pilot/ProductEntry.tsx):
// chooses a product in the banner (or in the list under it), takes screenshots while the pack lifts off, the
// product page opens and the pack comes down, and prints where the browser landed, how far the pack ended from its
// place in the first frame of the film (codex-site/mitoderm/pilot/film-entry.ts) and any errors.
//
// Usage (site running on 8787):
//   NODE_PATH=$(npm root -g) USEPROXY=1 node entry-check.cjs <out dir> <WxH> <slug> [hotspot|card] [base url]
// "land": place = the pack's place in the film on the screen, last = the pack in its last frame (the box around it,
// so a turned pen reads wider), off = distance between their middles in px, fit = how the last box fills the place
// (1 = exactly; a cut-out fitted inside a window of the phone photograph reads larger).
const { chromium } = require('playwright');
const fs = require('fs');
const pathLib = require('path');
const [out = '.', size = '1440x900', slug = 'derma-recovery-cream', source = 'hotspot', base = 'http://127.0.0.1:8787'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
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
  const phone = W <= 900;
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, hasTouch: phone, isMobile: phone, locale: 'he-IL' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
  page.on('pageerror', e => errs.push('pageerror ' + String(e).slice(0, 160)));
  await page.goto(base + '/', { waitUntil: 'load' });
  await page.waitForTimeout(2000);
  const selector = source === 'card' ? `.mc-collection-card[data-product="${slug}"]`
    : `[data-collection-frame="${phone ? 'mobile' : 'desktop'}"] .mc-photo-hotspot[data-product="${slug}"]`;
  // The banner breathes, so its links are never "stable" for Playwright: scroll and press by coordinates.
  const point = await page.evaluate(sel => {
    const element = document.querySelector(sel);
    if (!element) return null;
    const first = element.getBoundingClientRect();
    if (first.top < 80 || first.bottom > innerHeight - 20) element.scrollIntoView({ block: 'center', behavior: 'instant' });
    const r = element.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }, selector);
  if (!point) { console.log(JSON.stringify({ slug, size, source, error: 'no element ' + selector })); await browser.close(); return; }
  await page.waitForTimeout(400);
  // Every frame of the flight is written down in the page: the box around the pack and how visible it is.
  await page.evaluate(() => {
    window.__entry = [];
    let shown = false;
    const tick = () => {
      const pack = document.querySelector('.pe-pack'), root = document.querySelector('.pe-entry');
      if (pack) {
        shown = true;
        const r = pack.getBoundingClientRect();
        window.__entry.push({ t: Math.round(performance.now()), path: location.pathname, phase: root ? root.dataset.phase : null,
          rect: [r.left, r.top, r.width, r.height], opacity: +getComputedStyle(pack).opacity });
      }
      if (shown && !pack || window.__entry.length >= 6000) clearInterval(timer);
    };
    // A timer, not animation frames: while screenshots are taken the browser draws few frames, and the last
    // ones of the flight are the ones that count. Reading the box brings the animation up to date.
    const timer = setInterval(tick, 8);
  });
  const started = Date.now();
  if (phone) await page.touchscreen.tap(point.x, point.y); else await page.mouse.click(point.x, point.y);
  const seen = [];
  const shot = async name => {
    const state = await page.evaluate(() => ({ path: location.pathname, overlay: !!document.querySelector('.pe-entry'), phase: document.querySelector('.pe-entry')?.dataset.phase || null,
      film: (() => { const v = document.querySelector('video.pc-film'); return v ? v.readyState : null; })(), scroll: Math.round(scrollY) }));
    await page.screenshot({ path: `${out}/entry-${slug}-${size}-${source}-${name}.png` });
    seen.push({ shot: name, ms: Date.now() - started, ...state });
  };
  for (const mark of [120, 420, 800]) {
    const wait = mark - (Date.now() - started);
    if (wait > 0) await page.waitForTimeout(wait);
    await shot(String(mark).padStart(4, '0'));
  }
  // The pack comes down when the film of the product is ready: wait for that, then look at the way down.
  await page.waitForFunction(() => document.querySelector('.pe-entry')?.dataset.phase === 'landing' || !document.querySelector('.pe-entry'), null, { timeout: 9000 }).catch(() => {});
  const down = Date.now();
  for (const [name, mark] of [['land-a', 200], ['land-b', 430], ['land-c', 640]]) {
    const wait = mark - (Date.now() - down);
    if (wait > 0) await page.waitForTimeout(wait);
    await shot(name);
  }
  await page.waitForFunction(() => !document.querySelector('.pe-entry'), null, { timeout: 4000 }).catch(() => {});
  await page.waitForTimeout(250);
  await shot('after');
  const flight = await page.evaluate(() => {
    const v = document.querySelector('video.pc-film');
    const r = v ? v.getBoundingClientRect() : null;
    return { samples: window.__entry || [], film: v ? { rect: [r.left, r.top, r.width, r.height], video: [v.videoWidth, v.videoHeight], position: getComputedStyle(v).objectPosition } : null };
  });
  // The place of the pack in the film, by the same rule as film-entry.ts (its table is read from the source).
  // On a static copy of the site the product opens by a full page load and the record of the flight goes with the
  // page: then "land" stays null.
  let land = null;
  const table = fs.readFileSync(pathLib.join(__dirname, '..', '..', 'codex-site', 'mitoderm', 'pilot', 'film-entry.ts'), 'utf8');
  const row = table.match(new RegExp(`'${slug}':\\{desktop:\\[([^\\]]+)\\],mobile:\\[([^\\]]+)\\]`));
  const last = flight.samples.filter(s => s.phase === 'landing').pop();
  if (row && flight.film && flight.film.video[0] && last) {
    const [fw, fh] = flight.film.video, [l, tp, w, h] = flight.film.rect;
    const box = (fw < fh ? row[2] : row[1]).split(',').map(Number);
    const scale = Math.max(w / fw, h / fh), dw = fw * scale, dh = fh * scale;
    const [px, py] = flight.film.position.split(' ').map(v => v.endsWith('%') ? parseFloat(v) / 100 : 0.5);
    const x0 = l + (w - dw) * px, y0 = tp + (h - dh) * py;
    const place = [x0 + box[0] * dw, y0 + box[1] * dh, (box[2] - box[0]) * dw, (box[3] - box[1]) * dh];
    const off = [last.rect[0] + last.rect[2] / 2 - (place[0] + place[2] / 2), last.rect[1] + last.rect[3] / 2 - (place[1] + place[3] / 2)];
    land = { place: place.map(Math.round), last: last.rect.map(Math.round), opacity: last.opacity, off: off.map(v => Math.round(v * 10) / 10),
      fit: Math.round(Math.max(last.rect[2] / place[2], last.rect[3] / place[3]) * 100) / 100, frames: flight.samples.length };
  }
  console.log(JSON.stringify({ slug, size, source, seen, land, errs }));
  await browser.close();
})();
