// Records a scroll-through of a page of the test site as a video file, so the owner can watch a finished page
// by a plain link while the site itself is not published anywhere.
// It scrolls from top to bottom in even steps, takes a screenshot per step and joins them with ffmpeg.
//
// Usage (site running on 8787):
//   NODE_PATH=$(npm root -g) USEPROXY=1 node page-record.cjs <path> <width>x<height> <out.mp4> [seconds=50] [fps=20] [scale=1]
//   e.g. node page-record.cjs /products/exo-nad 1440x900 /tmp/out/exo-nad-desktop.mp4 55
// scale 2 records a phone viewport at double density (390x664 -> 780x1328).
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const pathLib = require('path');

const [route = '/', size = '1440x900', out = 'page.mp4', seconds = '50', fps = '20', scale = '1', base = 'http://127.0.0.1:8787'] = process.argv.slice(2);
const [W, H] = size.split('x').map(Number);
const FPS = Number(fps), N = Math.max(2, Math.round(Number(seconds) * FPS)), DSF = Number(scale);
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
  const frames = fs.mkdtempSync(pathLib.join(os.tmpdir(), 'page-record-'));
  const p = proxy();
  const browser = await chromium.launch(p ? { proxy: p } : undefined);
  const phone = W < 861;
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DSF, hasTouch: phone, isMobile: phone, locale: 'he-IL' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 160)));
  await page.goto(base + route, { waitUntil: 'load' });
  await sleep(6000); // let the scroll film load its first frames
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const span = Math.max(0, height - H);
  for (let i = 0; i < N; i++) {
    const y = Math.round(span * i / (N - 1));
    await page.evaluate(top => scrollTo({ top, behavior: 'instant' }), y);
    await sleep(90); // the film seeks to the frame of this scroll position
    await page.screenshot({ path: pathLib.join(frames, String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 92 });
  }
  await browser.close();
  fs.mkdirSync(pathLib.dirname(pathLib.resolve(out)), { recursive: true });
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-framerate', String(FPS), '-i', pathLib.join(frames, '%05d.jpg'),
    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart', out]);
  fs.rmSync(frames, { recursive: true, force: true });
  console.log(JSON.stringify({ route, size, pageHeight: height, frames: N, fps: FPS, out, bytes: fs.statSync(out).size, errs: errs.slice(0, 5) }));
})();
