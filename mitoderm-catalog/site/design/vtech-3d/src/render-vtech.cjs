// Renders each storyboard shot of render-vtech.html (served from a fake https origin so ES modules load) to PNG at 2x.
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const dir = __dirname, out = path.join(dir, 'renders');
const shots = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  for (const name of shots) {
    const ctx = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
    const p = await ctx.newPage();
    await p.route('https://render.local/**', r => {
      let rel = r.request().url().replace('https://render.local/', '').split('#')[0];
      if (rel.startsWith('three/')) rel = 'node_modules/' + rel;
      const f = path.join(dir, rel || 'render-vtech.html');
      const type = f.endsWith('.js') ? 'application/javascript' : f.endsWith('.html') ? 'text/html' : f.endsWith('.jpg') ? 'image/jpeg' : f.endsWith('.png') ? 'image/png' : 'application/octet-stream';
      r.fulfill({ path: f, contentType: type });
    });
    const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    await p.goto('https://render.local/render-vtech.html#' + name);
    await p.waitForFunction(() => window.__done === true, null, { timeout: 120000 });
    const data = await p.evaluate(() => document.getElementById('c').toDataURL('image/png'));
    fs.writeFileSync(path.join(out, name + '.png'), Buffer.from(data.split(',')[1], 'base64'));
    console.log(name, 'ok', errs.length ? errs.slice(0, 3) : '');
    await ctx.close();
  }
  await browser.close();
})();
