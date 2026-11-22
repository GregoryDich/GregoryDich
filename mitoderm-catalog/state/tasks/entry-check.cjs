// Browser check of the entry from the home page into a product (codex-site/mitoderm/pilot/ProductEntry.tsx):
// chooses a product in the banner (or in the list under it), takes screenshots while the pack lifts off and the
// product page opens, and prints where the browser landed and any errors.
//
// Usage (site running on 8787):
//   NODE_PATH=$(npm root -g) USEPROXY=1 node entry-check.cjs <out dir> <WxH> <slug> [hotspot|card] [base url]
const { chromium } = require('playwright');
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
  const started = Date.now();
  if (phone) await page.touchscreen.tap(point.x, point.y); else await page.mouse.click(point.x, point.y);
  const marks = [120, 420, 800, 1300, 2000, 3200];
  const seen = [];
  for (const mark of marks) {
    const wait = mark - (Date.now() - started);
    if (wait > 0) await page.waitForTimeout(wait);
    const state = await page.evaluate(() => ({ path: location.pathname, overlay: !!document.querySelector('.pe-entry'), phase: document.querySelector('.pe-entry')?.dataset.phase || null,
      film: (() => { const v = document.querySelector('video.pc-film'); return v ? v.readyState : null; })(), scroll: Math.round(scrollY) }));
    await page.screenshot({ path: `${out}/entry-${slug}-${size}-${source}-${String(mark).padStart(4, '0')}.png` });
    seen.push({ ms: Date.now() - started, ...state });
  }
  console.log(JSON.stringify({ slug, size, source, seen, errs }));
  await browser.close();
})();
