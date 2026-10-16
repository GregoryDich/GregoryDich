// Клип в «шаговом» режиме: N кадров ровно по dt через window.__aq.step → PNG-кадры → ffmpeg H.264 MP4
// (+ необязательный GIF через palettegen/paletteuse). Реальное время headless тут не участвует (SPEC F11).
//   node clip.js --out clip.mp4 [--frames 150 --dt 1/30 --warm 30 --fps 30 --w 1920 --h 1200 --seed 1]
//                [--gif clip.gif --gifw 960 --giffps 15] [--clip x,y,w,h] [--keep framesDir] [--q ...] [--http]
//                [--format png|jpeg] (jpeg q95 — кадры заметно быстрее; png — без потерь, по умолчанию)
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const L = require('./lib');

(async () => {
  const o = L.parseArgs(process.argv.slice(2), { w: 1920, h: 1200, dpr: 1, seed: 1, frames: 150, dt: 1 / 30, warm: 30, fps: 30,
    out: path.join(__dirname, 'out', 'clip.mp4'), gifw: 960, giffps: 15, crf: 18, format: 'png' });
  const ext = o.format === 'jpeg' || o.format === 'jpg' ? 'jpg' : 'png';
  const out = path.resolve(o.out); L.ensureDir(path.dirname(out));
  const dir = o.keep ? L.ensureDir(path.resolve(String(o.keep))) : fs.mkdtempSync(path.join(os.tmpdir(), 'aqclip-'));
  const env = await L.openEngine(o);
  let errors = [], warnings = [];
  try {
    const { page, cap } = await L.newPage(env);
    errors = cap.errors; warnings = cap.warnings;
    await L.gotoReady(page, env.url);
    if (o.warm > 0) await page.evaluate((dt, n) => window.__aq.step(dt, n, { render: 'last' }), o.dt, o.warm | 0);
    const clip = L.clipOpt(o);
    const t0 = Date.now();
    for (let i = 0; i < (o.frames | 0); i++) {
      await page.evaluate((dt) => { window.__aq.step(dt, 1); return new Promise((r) => requestAnimationFrame(() => r())); }, o.dt);
      await page.screenshot({ path: path.join(dir, `f_${String(i).padStart(5, '0')}.${ext}`), clip, optimizeForSpeed: true,
        ...(ext === 'jpg' ? { type: 'jpeg', quality: 95 } : {}) });
      if (i % 30 === 29) process.stderr.write(`  frame ${i + 1}/${o.frames} (${((Date.now() - t0) / 1000).toFixed(0)} s)\n`);
    }
  } finally { await L.finish(env); }
  // H.264, yuv420p (чётные размеры), faststart — играет везде, включая Telegram/QuickTime
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(o.fps), '-i', path.join(dir, `f_%05d.${ext}`),
    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', String(o.crf),
    '-preset', 'medium', '-movflags', '+faststart', out], { stdio: 'inherit' });
  const res = { out, frames: o.frames, dt: o.dt, fps: o.fps, url: env.url, framesDir: o.keep ? dir : null };
  if (o.gif) {
    const gif = path.resolve(String(o.gif));
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', out, '-vf',
      `fps=${o.giffps},scale=${o.gifw}:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a`, gif], { stdio: 'inherit' });
    res.gif = gif;
  }
  if (!o.keep) fs.rmSync(dir, { recursive: true, force: true });
  console.log(JSON.stringify({ ...res, errors }, null, 1));
  L.report(errors, warnings, o['allow-errors']);
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
