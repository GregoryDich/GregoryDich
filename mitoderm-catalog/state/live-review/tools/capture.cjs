// node capture.cjs <route> <WxH[@dsf][t][m][r]> <stepPx> <outDir> [startY] [endY]
//   t = touch, m = mobile UA/viewport, r = prefers-reduced-motion. Saves JPEG frames + info.json. Never submits forms.
const fs = require('fs'); const { open } = require('./px.cjs');
(async () => {
  const [route, v, stepS, out, sY, eY] = process.argv.slice(2);
  const m = /^(\d+)x(\d+)(?:@(\d(?:\.\d)?))?([tmr]*)$/.exec(v); if (!m) throw new Error('bad view ' + v);
  const view = { width: +m[1], height: +m[2], dsf: +(m[3] || 1), touch: m[4].includes('t'), mobile: m[4].includes('m'), reduced: m[4].includes('r') };
  const base = process.env.BASE || 'https://mitoderm-cinematic.evenradish1.chatgpt.site'; fs.mkdirSync(out, { recursive: true });
  const { browser, page, log } = await open(view);
  const t0 = Date.now();
  await page.goto(base + route, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(5000);
  const H = await page.evaluate(() => document.documentElement.scrollHeight);
  const step = +stepS, start = +(sY || 0), end = Math.min(+(eY || H), H - view.height);
  const frames = [];
  for (let y = start, i = 0; y <= end + step - 1; y += step, i++) {
    const yy = Math.min(y, Math.max(0, H - view.height));
    await page.evaluate(val => window.scrollTo({ top: val, behavior: 'instant' }), yy); await page.waitForTimeout(800);
    const file = `f-${String(i).padStart(3, '0')}-y${yy}.jpg`;
    await page.screenshot({ path: `${out}/${file}`, type: 'jpeg', quality: 62 });
    frames.push({ i, y: yy, file }); if (yy >= H - view.height) break;
  }
  const state = await page.evaluate(() => ({
    scrollW: document.documentElement.scrollWidth, innerW: innerWidth,
    videos: [...document.querySelectorAll('video')].map(x => ({ rs: x.readyState, err: x.error ? x.error.code : 0, w: x.videoWidth, h: x.videoHeight, dur: +(x.duration || 0).toFixed(1) })),
    sections: [...document.querySelectorAll('section')].map(s => ({ id: s.id, top: Math.round(s.getBoundingClientRect().top + scrollY), h: Math.round(s.getBoundingClientRect().height) })) }));
  fs.writeFileSync(`${out}/info.json`, JSON.stringify({ route, view, pageHeight: H, loadMs: Date.now() - t0, transferMB: +(log.bytes / 1e6).toFixed(1), requests: log.requests,
    consoleErrors: log.console, failed: log.failed.filter(f => !/ERR_ABORTED/.test(f)), aborted: log.failed.filter(f => /ERR_ABORTED/.test(f)).length, ...state, frames }, null, 1));
  console.log(route, v, 'H', H, 'frames', frames.length, 'MB', (log.bytes / 1e6).toFixed(1), 'errors', log.console.length, 'failed', log.failed.filter(f => !/ERR_ABORTED/.test(f)).length, '->', out);
  await browser.close();
})().catch(e => { console.error('CAPTURE FAILED', String(e).slice(0, 300)); process.exit(1); });
