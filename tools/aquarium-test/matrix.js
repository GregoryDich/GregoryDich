// Матрица мониторов: размер буфера холста и RS на типичных экранах Mac (гейт G0: ≤ 8.4 Мп).
//   node matrix.js [--http] [--seed 1] [--q ...] [--shots dir] [--limit 8.4] [--out matrix.json]
// --shots сохраняет уменьшенную копию кадра (ширина 1280) для каждого вида.
'use strict';
const fs = require('fs');
const path = require('path');
const L = require('./lib');

const VIEWPORTS = [
  { name: 'MacBook Air 13 / Pro 14 (1512×982@2)', width: 1512, height: 982, deviceScaleFactor: 2 },
  { name: 'MacBook Pro 16 (1728×1117@2)', width: 1728, height: 1117, deviceScaleFactor: 2 },
  { name: '4K «как 1920» (1920×1080@2)', width: 1920, height: 1080, deviceScaleFactor: 2 },
  { name: '5K / 4K «как 2560» (2560×1440@2)', width: 2560, height: 1440, deviceScaleFactor: 2 },
  { name: '6K XDR «как 3008» (3008×1692@2)', width: 3008, height: 1692, deviceScaleFactor: 2 },
  { name: '4K без HiDPI (3840×2160@1)', width: 3840, height: 2160, deviceScaleFactor: 1 },
];

(async () => {
  const o = L.parseArgs(process.argv.slice(2), { seed: 1, limit: 8.4, steps: 3, dt: 1 / 30 });
  const env = await L.openEngine(o, { viewport: VIEWPORTS[0] });
  const rows = [], allErrors = [];
  try {
    for (const vp of VIEWPORTS) {
      const { page, cap } = await L.newPage({ browser: env.browser, vp });
      await L.gotoReady(page, env.url);
      const s = await L.stepFrames(page, o.dt, o.steps | 0);
      const row = { name: vp.name, css: `${vp.width}×${vp.height}`, dpr: vp.deviceScaleFactor, RS: Math.round(s.RS * 10000) / 10000,
        backing: `${s.backing.w}×${s.backing.h}`, mp: Math.round(s.backing.mp * 1000) / 1000, pass: s.backing.mp <= o.limit,
        photo: s.photo, jsMs: Math.round(s.last.jsMs * 100) / 100, errors: cap.errors.length };
      if (o.shots) {
        const dir = L.ensureDir(path.resolve(String(o.shots)));
        const file = path.join(dir, `matrix_${vp.width}x${vp.height}@${vp.deviceScaleFactor}.png`);
        // scale: выход = width·scale (scale задаётся в CSS-пикселях относительно DPR страницы)
        await page.screenshot({ path: file, clip: { x: 0, y: 0, width: vp.width, height: vp.height, scale: 1280 / (vp.width * vp.deviceScaleFactor) } });
        row.shot = file;
      }
      rows.push(row);
      for (const e of cap.errors) allErrors.push(`[${row.css}@${row.dpr}] ${e}`);
      await page.close();
    }
  } finally { await L.finish(env); }
  const res = { url: env.url, mode: o.http ? 'http' : 'file', limitMP: o.limit, pass: rows.every((r) => r.pass), rows, errors: allErrors };
  console.log(JSON.stringify(res, null, 1));
  if (o.out) { const p = path.resolve(String(o.out)); L.ensureDir(path.dirname(p)); fs.writeFileSync(p, JSON.stringify(res, null, 1)); }
  if (!res.pass) process.exitCode = 3;
  L.report(allErrors, [], o['allow-errors']);
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
