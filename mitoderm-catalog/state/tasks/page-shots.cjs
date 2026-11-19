// Viewport screenshots down any page of the test site, evenly spaced from top to bottom.
// Works for plain pages and for scroll-driven film pages alike.
//
// Usage (site running on 8787):
//   NODE_PATH=$(npm root -g) USEPROXY=1 node page-shots.cjs <path> <width>x<height> <out dir> [count] [base url]
//   e.g. node page-shots.cjs /products/mitopen 1440x900 /tmp/out 12
// Sizes worth checking: 1440x900 (desktop), 390x664 (iPhone, toolbars shown), 360x640 (small Android).
const { chromium } = require('playwright');
const [path = '/', size = '1440x900', out = '.', count = '10', base = 'http://127.0.0.1:8787'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
const N = Math.max(2, Number(count));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const name = (path.replace(/^\/+|\/+$/g, '').replace(/[^a-z0-9]+/gi, '-') || 'home') + '-' + size;

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
  const errs = [], failed = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
  page.on('pageerror', e => errs.push('pageerror ' + String(e).slice(0, 160)));
  page.on('response', r => { if (r.status() >= 400) failed.push(r.status() + ' ' + r.url().slice(0, 120)); });
  await page.goto(base + path, { waitUntil: 'load' });
  await sleep(3000);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const shots = [];
  for (let i = 0; i < N; i++) {
    const y = Math.round((height - H) * i / (N - 1));
    await page.evaluate(top => scrollTo({ top, behavior: 'instant' }), Math.max(0, y));
    await sleep(1100);
    const file = `${out}/${name}-${String(i).padStart(2, '0')}.png`;
    await page.screenshot({ path: file });
    shots.push({ i, y: Math.max(0, y), file });
  }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  console.log(JSON.stringify({ path, size, height, horizontalOverflowPx: overflow, shots, errs: errs.slice(0, 8), failed: failed.slice(0, 8) }));
  await browser.close();
})();
