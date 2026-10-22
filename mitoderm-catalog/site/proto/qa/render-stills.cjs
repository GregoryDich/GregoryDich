// Render the buy-card kit picture (site/design/exocell-3d/kit-hd.png) and the no-WebGL still (still-hd.png) from the
// built page's own 3D scene, so they carry exactly the page's light and print colours (window.__renderStill).
// usage: node render-stills.cjs <exocell-mask-3d.html> <three.module.min.js> <outdir>   → <outdir>/kit.png, still.png
// then crop to the alpha box and save as site/design/exocell-3d/kit-hd.png and still-hd.png, and rebuild the page.
const { chromium } = require('playwright'); const fs = require('fs');
const [pagePath, threeFile, outDir] = process.argv.slice(2); const html = fs.readFileSync(pagePath, 'utf8');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: '' }));
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: threeFile, contentType: 'application/javascript' }));
  await p.route('https://x.test/**', r => r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html }));
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('https://x.test/a.html'); await p.waitForFunction(() => window.__glReady, null, { timeout: 60000 }); await p.waitForTimeout(1500);
  for (const [what, w, h] of [['kit', 1500, 1600], ['still', 1800, 1600]]) {
    const url = await p.evaluate(([a, w, h]) => window.__renderStill(a, w, h), [what, w, h]);
    fs.writeFileSync(`${outDir}/${what}.png`, Buffer.from(url.split(',')[1], 'base64')); console.log(what, 'ok');
  }
  await b.close();
})();
