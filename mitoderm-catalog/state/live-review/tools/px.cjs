// Shared launcher: Chromium through the agent proxy (credentials parsed from HTTPS_PROXY, never printed).
const { chromium, devices } = require('playwright');
function proxyOpts() {
  const raw = process.env.HTTPS_PROXY || process.env.https_proxy; if (!raw) return undefined;
  const u = new URL(raw); const o = { server: `${u.protocol}//${u.host}` };
  if (u.username) { o.username = decodeURIComponent(u.username); o.password = decodeURIComponent(u.password); }
  return o;
}
async function open(view) {            // view: {width,height,dsf?,touch?,mobile?}
  const browser = await chromium.launch({ proxy: proxyOpts() });
  const ctx = await browser.newContext({ viewport: { width: view.width, height: view.height }, deviceScaleFactor: view.dsf || 1,
    hasTouch: !!view.touch, isMobile: !!view.mobile, locale: 'he-IL', reducedMotion: view.reduced ? 'reduce' : 'no-preference' });
  const page = await ctx.newPage();
  const log = { console: [], failed: [], requests: 0, bytes: 0 };
  page.on('console', m => { if (m.type() === 'error') log.console.push(m.text().slice(0, 200)); });
  page.on('requestfailed', r => log.failed.push(r.url().slice(0, 140) + ' :: ' + (r.failure() || {}).errorText));
  page.on('response', async r => { log.requests++; const l = r.headers()['content-length']; if (l) log.bytes += +l; });
  return { browser, ctx, page, log };
}
module.exports = { open, proxyOpts };
