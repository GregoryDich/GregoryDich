// Saves the first frame of every product film as the page shows it: the film element alone, no captions.
// The frames are measured by first-frame-boxes.py: the place of the pack in the first frame is where the pack chosen on
// the home page comes down (codex-site/mitoderm/pilot/film-entry.ts). Run both again when a film gets a new first frame.
//
// Usage (site running on 8787):
//   NODE_PATH=$(npm root -g) USEPROXY=1 node first-frames.cjs <out dir> [base url]
// writes <slug>-desktop.png (1912x1080) and <slug>-mobile.png (540x960) and prints how each film is fitted.
const { chromium } = require('playwright');
const [out = '.', base = 'http://127.0.0.1:8787'] = process.argv.slice(2);
const SLUGS = ['exo-nad', 'exocell-mask', 'exotech-gel', 'exosignal-hair', 'exosignal-spray', 'micro-boost-10', 'cell-renew-1-5',
  'cellular-age-defense-2-5', 'derma-recovery-cream', 'mitopen', 'mitoscan', 'mitotech-cell-booster'];
function proxy() {
  const raw = process.env.HTTPS_PROXY || process.env.https_proxy;
  if (!process.env.USEPROXY || !raw) return undefined;
  const u = new URL(raw);
  const o = { server: `${u.protocol}//${u.host}`, bypass: '127.0.0.1,localhost' };
  if (u.username) { o.username = decodeURIComponent(u.username); o.password = decodeURIComponent(u.password); }
  return o;
}
(async () => {
  const p = proxy();
  const browser = await chromium.launch(p ? { proxy: p } : undefined);
  for (const [name, W, H] of [['desktop', 1912, 1080], ['mobile', 540, 960]]) {
    const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, ignoreHTTPSErrors: true });
    for (const slug of SLUGS) {
      const page = await context.newPage();
      try {
        await page.goto(`${base}/products/${slug}`, { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('video.pc-film.is-painted', { timeout: 45000 });
        await page.addStyleTag({ content: 'body *{visibility:hidden!important}video.pc-film{visibility:visible!important}' });
        await page.waitForTimeout(400);
        const info = await page.evaluate(() => {
          const v = document.querySelector('video.pc-film'); const r = v.getBoundingClientRect(); const cs = getComputedStyle(v);
          return { rect: [r.left, r.top, r.width, r.height], video: [v.videoWidth, v.videoHeight], fit: cs.objectFit, position: cs.objectPosition, time: v.currentTime };
        });
        await page.locator('video.pc-film').screenshot({ path: `${out}/${slug}-${name}.png` });
        console.log(JSON.stringify({ slug, name, ...info }));
      } catch (e) { console.log(JSON.stringify({ slug, name, error: String(e).slice(0, 160) })); }
      await page.close();
    }
    await context.close();
  }
  await browser.close();
})();
