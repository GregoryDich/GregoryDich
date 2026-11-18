// Запись прокрутки страниц сайта в MP4 и 8 кадров на страницу — материал для галереи предпросмотра.
// node record.cjs <outDir> [часть имени]   имена: git-<slug>-desk|phone, live-<slug>-desk; главная = home.
// Версия из git должна быть поднята на 127.0.0.1:8787 (codex-site: pnpm build && pnpm start, на копии вне репозитория).
// Нужен NODE_PATH=$(npm root -g). Пути в data.json — относительно папки над <outDir>. Повторный запуск продолжает
// с места остановки (progress.jsonl). Видео и кадры в git не кладём.
const { chromium } = require('playwright');
const { proxyOpts } = require('./px.cjs');
const fs = require('fs'), path = require('path'), cp = require('child_process');
const OUT = path.resolve(process.argv[2] || 'new'), REL = path.basename(OUT), ONLY = process.argv[3] || '';
const LOCAL = process.env.LOCAL || 'http://127.0.0.1:8787', LIVE = 'https://mitoderm-cinematic.evenradish1.chatgpt.site';
const slugs = ['v-tech-system','exo-nad','exotech-gel','exocell-mask','exosignal-hair','exosignal-spray','micro-boost-10','cellular-age-defense-2-5','cell-renew-1-5','derma-recovery-cream','mitopen','mitoscan','mitotech-cell-booster'];
const phoneSlugs = ['v-tech-system','exo-nad','exosignal-hair','mitotech-cell-booster'];
const items = [];
const R = s => s === 'home' ? '/' : '/products/' + s;
for (const s of ['home', ...slugs]) items.push({ group:'git', slug:s, view:'desk', base:LOCAL });
for (const s of ['home', ...phoneSlugs]) items.push({ group:'git', slug:s, view:'phone', base:LOCAL });
for (const s of ['home','v-tech-system','exo-nad']) items.push({ group:'live', slug:s, view:'desk', base:LIVE });
fs.mkdirSync(OUT + '/videos', { recursive: true }); fs.mkdirSync(OUT + '/stills', { recursive: true });
const done = new Set(fs.existsSync(OUT+'/progress.jsonl') ? fs.readFileSync(OUT+'/progress.jsonl','utf8').split('\n').filter(Boolean).map(l=>JSON.parse(l).name) : []);
const data = fs.existsSync(OUT+'/data.json') ? JSON.parse(fs.readFileSync(OUT+'/data.json','utf8')) : [];
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function ctxFor(browser, it, rec, dir) {
  const phone = it.view === 'phone';
  const vp = phone ? { width:390, height:844 } : { width:1440, height:900 };
  const o = { viewport: vp, deviceScaleFactor: 1, locale: 'he-IL' };
  if (phone) { o.isMobile = true; o.hasTouch = true; }
  if (rec) o.recordVideo = { dir, size: phone ? { width:780, height:1688 } : vp };
  return { ctx: await browser.newContext(o), vp };
}
// Прогрев: пройти страницу по экрану, чтобы подгрузились картинки и ролики, и вернуться наверх.
async function warm(page, vp) {
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y <= h; y += vp.height) { await page.evaluate(y => window.scrollTo(0, y), y); await sleep(250); }
  await page.evaluate(() => window.scrollTo(0, 0)); await sleep(1500);
}
(async () => {
  const browser = await chromium.launch({ proxy: proxyOpts() });
  for (const it of items) {
    const name = `${it.group}-${it.slug}-${it.view}`;
    if (done.has(name) || (ONLY && !name.includes(ONLY))) continue;
    const entry = { group: it.group, title: `${it.slug} (${it.view})`, route: R(it.slug), view: it.view, video: null, sizeMB: 0, durationS: 0, pageHeightPx: 0, transferMB: 0, stills: [], note: '' };
    const errs = [];
    try {
      const dir = `${OUT}/tmp-${name}`; fs.mkdirSync(dir, { recursive: true });
      const { ctx, vp } = await ctxFor(browser, it, true, dir);
      const page = await ctx.newPage();
      let bytes = 0;
      const cdp = await ctx.newCDPSession(page); await cdp.send('Network.enable'); cdp.on('Network.loadingFinished', e => { bytes += e.encodedDataLength || 0; });
      page.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 120)); });
      page.on('pageerror', e => errs.push('pageerror ' + String(e).slice(0, 120)));
      const resp = await page.goto(it.base + R(it.slug), { waitUntil: 'domcontentloaded' });
      entry.note = 'status ' + (resp && resp.status());
      await sleep(5000);
      await warm(page, vp);
      const h = await page.evaluate(() => document.documentElement.scrollHeight);
      entry.pageHeightPx = h; entry.transferMB = +(bytes / 1048576).toFixed(1);
      // Скорость прокрутки 450/400 px в секунду, но не дольше 75 с на страницу.
      let speed = it.view === 'desk' ? 450 : 400;
      const max = h - vp.height;
      if (max / speed > 75) speed = max / 75;
      await page.evaluate(([max, speed]) => new Promise(res => { const t0 = performance.now(); (function f(t) { const y = Math.min(max, (t - t0) / 1000 * speed); window.scrollTo(0, y); if (y >= max) res(); else requestAnimationFrame(f); })(t0); }), [max, speed]);
      await sleep(1500);
      const vid = page.video();
      await ctx.close();
      const src = await vid.path();
      const mp4 = `${OUT}/videos/${name}.mp4`;
      const W = it.view === 'desk' ? 1280 : 780;
      // H.264 yuv420p с faststart играет во всех браузерах; ужимаем, пока ролик не станет легче 7 МБ.
      let ok = false;
      for (const [c, f] of [[27,24],[29,24],[31,24],[31,18]]) {
        cp.execFileSync('ffmpeg', ['-y','-loglevel','error','-i',src,'-vf',`scale=${W}:-2,fps=${f}`,'-c:v','libx264','-preset','medium','-crf',String(c),'-pix_fmt','yuv420p','-movflags','+faststart','-an',mp4]);
        if (fs.statSync(mp4).size <= 7*1048576) { ok = true; break; }
      }
      entry.video = `${REL}/videos/${name}.mp4`;
      entry.sizeMB = +(fs.statSync(mp4).size / 1048576).toFixed(2);
      entry.durationS = +parseFloat(cp.execFileSync('ffprobe', ['-v','error','-show_entries','format=duration','-of','csv=p=0',mp4]).toString()).toFixed(1);
      if (!ok) entry.note += '; >7MB';
      fs.rmSync(dir, { recursive: true, force: true });
      const c2 = await ctxFor(browser, it, false);
      const p2 = await c2.ctx.newPage();
      await p2.goto(it.base + R(it.slug), { waitUntil: 'domcontentloaded' }); await sleep(5000);
      await warm(p2, c2.vp);
      for (let i = 0; i < 8; i++) {
        await p2.evaluate(y => window.scrollTo(0, y), Math.round(max * i / 7)); await sleep(1200);
        await p2.screenshot({ path: `${OUT}/stills/${name}-${i + 1}.jpg`, type: 'jpeg', quality: 82 });
        entry.stills.push(`${REL}/stills/${name}-${i + 1}.jpg`);
      }
      await c2.ctx.close();
    } catch (e) { entry.note += '; FAIL ' + String(e).slice(0, 200); }
    if (errs.length) entry.note += '; console: ' + [...new Set(errs)].slice(0, 3).join(' | ');
    data.push(entry);
    fs.writeFileSync(OUT + '/data.json', JSON.stringify(data, null, 1));
    fs.appendFileSync(OUT + '/progress.jsonl', JSON.stringify({ name }) + '\n');
    console.log(name, entry.sizeMB + ' MB', entry.durationS + ' s', entry.note);
  }
  await browser.close();
})();
