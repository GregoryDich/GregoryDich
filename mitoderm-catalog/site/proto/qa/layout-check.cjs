// Layout check of a product page (site v2 rules L1–L8, design-rules.md «Сайт v2 — вёрстка по замерам»): the values are
// computed from DOM geometry, computed styles, Range rects of the words and the alpha of the product pictures (image
// files at their natural size, 2D canvases, the WebGL canvas's kept drawing buffer), plus the engines' QA state
// (window.__seq().sceneState.aabb on the template pages, window.__objRects on MASK). No screenshots.
// Each screen is measured at its reading position: inside the engine's hold for that screen (the key pose shown) with the
// copy centred in the free band between the header and the dock (desktop), and again where the dock lands the reader
// when that is elsewhere («<id> @dock»); the anchor's landing (phone and tablet blocks: the block's key frame and the live
// canvas the reader sees there), MASK's own stage anchors; then the step cards, the kit card (read, and the moment the
// kit lands on it), the specialists and the related cards. A phone's page is also read whole as a stack (the largest
// empty stretch of the screen at any scroll), and the page logs its own load from the first frame (sections that jump
// after the layout is shown; a phone is loaded three times: the gaps between its blocks are a race).
//
// usage:
//   FONTDIR=<dir with Rubik[wght].ttf> THREE=<three.module.min.js of three@0.160.0> NODE_PATH=$(npm root -g) \
//     node layout-check.cjs run <slug> <page.html> <files dir> <raw dir> [viewports, e.g. 1440x900x1,390x844x3t]
//   node layout-check.cjs eval <raw dir> <out.json> <out.md> --target <slug> [--refs slug,slug] [--notes notes.json]
// A viewport is WxHxDPR, with a trailing t for a touch screen (isMobile + hasTouch). The raw file of a page and
// viewport is <raw dir>/<slug>__<viewport>.json; run skips the ones that exist (a restart goes on where it stopped).
// The refs (default exotech-gel, exocell-mask: the owner-approved pages) give the type scale; notes.json holds the
// verdicts on failures, keyed "<slug>|<rule>|<check>[|<where>[|<element>]]", "_summary" for the report's top and "_eye"
// (lines) for a section on an outside review's places.
// As a module (the page map): require('./layout-check.cjs') → install(context, { html, files }) before the page opens,
// measure(page) → the raw record of the page at this viewport (or page.evaluate(() => __LC.plan() / __LC.screen(id) /
// __LC.series(kind)) at its own scroll positions), evaluate(raws, { refs }) → values and verdicts, report(result).
const fs = require('fs'), path = require('path');
const PAGE_JS = path.join(__dirname, 'layout-page.js');
const ORIGIN = 'https://live.test/';
const VIEWPORTS = ['1280x720x1', '1366x768x1', '1440x900x1', '1920x1080x1', '2560x1080x1', '1024x768x2', '1180x820x2t',
  '390x844x3t', '360x780x3t', '820x1180x2t', '768x1024x2t'];
const parseVp = s => { const m = /^(\d+)x(\d+)x([\d.]+)(t?)$/.exec(s); if (!m) throw new Error('viewport ' + s); return { id: s, w: +m[1], h: +m[2], dpr: +m[3], touch: !!m[4] }; };
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.mjs': 'application/javascript', '.css': 'text/css', '.json': 'application/json',
  '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.glb': 'model/gltf-binary', '.ktx2': 'image/ktx2' };
const FONT_CSS = "@font-face{font-family:'Rubik';src:url(https://fonts.gstatic.com/local/0.ttf) format('truetype');font-weight:100 900;font-display:block}";
const wait = ms => new Promise(r => setTimeout(r, ms));

// the page's context: the collector before the page's scripts, the fonts, three.js and the page's files from disk
async function install(ctx, o) {
  await ctx.addInitScript({ path: PAGE_JS });
  const fontDir = o.fontDir || process.env.FONTDIR, three = o.three || process.env.THREE;
  if (fontDir) {
    await ctx.route('https://fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: FONT_CSS }));
    await ctx.route('https://fonts.gstatic.com/local/**', r => r.fulfill({ path: path.join(fontDir, 'Rubik[wght].ttf'), contentType: 'font/ttf' }));
  }
  if (three) await ctx.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => r.fulfill({ path: three, contentType: 'application/javascript' }));
  if (o.html) {
    const src = fs.readFileSync(o.html, 'utf8');
    const html = /^\s*(<!doctype|<html)/i.test(src) ? src : '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>' + src + '</body></html>';
    await ctx.route(ORIGIN + '**', r => {
      const rel = decodeURIComponent(new URL(r.request().url()).pathname.slice(1));
      if (!rel || rel === 'index.html') return r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
      const f = path.join(o.files || path.dirname(o.html), rel);
      return fs.existsSync(f) ? r.fulfill({ path: f, contentType: TYPES[path.extname(f).toLowerCase()] || 'application/octet-stream' }) : r.fulfill({ status: 404, body: '' });
    });
  }
}

// after a scroll: the engine has drawn this place (its story position and drawn pose steady), the frame is shown,
// CSS transitions started by the scroll (the bar, the dock, the card) are over
async function settle(p, ms = 450) {
  let last = null, same = 0;
  for (let t = 0; t < 15000; t += 150) {
    await wait(150);
    const k = await p.evaluate(() => {
      const st = window.__seq && window.__seq(), ss = st && st.sceneState;
      const pos = typeof window.__mtP === 'number' ? window.__mtP : st ? st.pos : (window.__frames ? -1 : 0);
      return [Math.round(pos * 1e4), ss ? ss.drawn : '', Math.round(scrollY)].join('|');
    });
    if (k === last) { if (++same >= 3) break; } else { same = 0; last = k; }
  }
  await p.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  await wait(ms);
}
const storyPos = p => p.evaluate(() => { const st = window.__seq && window.__seq(); return { p: typeof window.__mtP === 'number' ? window.__mtP : st ? st.pos : null,
  drawn: st && st.sceneState ? st.sceneState.drawn : null, mask: window.__anchorY ? 1 : 0 }; });

// the page as it loads, untouched (before the reveal and the eager pictures): its height and its sections' tops sampled
// until the page is ready and nothing has moved for 4 s (≤ 30 s), and the browser's layout-shift entries; the rules
// compare the tops when it became ready with the final ones (a block that jumps after the reader can see the page)
async function loadTimeline(p, maxMs = 30000) {
  const t0 = Date.now(); let readyT = null, last = '', since = 0, s = null;
  while (Date.now() - t0 < maxMs) {   // the page keeps its own log from its start (layout-page.js); here: wait until it is ready and still
    s = await p.evaluate(() => window.__LC.load());
    const key = [s.h, s.cls, s.ready].concat(s.tops.map(x => x[1])).join('|');
    if (key !== last) { last = key; since = s.t; }
    if (s.ready && readyT == null) readyT = s.t;
    if (readyT != null && s.t - since >= 4000) break;
    await wait(150);
  }
  const samples = await p.evaluate(() => window.__LC.loadLog());
  const first = samples.find(x => x.ready);
  if (s) samples.push(s);   // the state now (the final one)
  return { readyT: first ? first.t : readyT, fcp: s && s.fcp, samples, shifts: await p.evaluate(() => window.__LC.shifts()) };
}

// one page at one viewport: every screen at its reading position, then the series; returns the raw record
async function measure(p, log = () => {}) {
  const t0 = Date.now(), errs = [];
  const load = await loadTimeline(p).catch(e => ({ err: String(e).slice(0, 160) }));
  await p.waitForFunction(() => {
    const h = document.documentElement;
    return (window.__seq && (h.classList.contains('story') || h.classList.contains('no-gl'))) || window.__glReady || h.classList.contains('nogl');
  }, null, { timeout: 120000 }).catch(() => errs.push('READY TIMEOUT'));
  await p.evaluate(() => document.fonts && document.fonts.ready);
  await p.evaluate(() => { window.__snap = true; return window.__LC.prepare(); });
  for (let t = 0; t < 20000; t += 400) { const n = await p.evaluate(() => window.__LC.pending().length); if (!n) break; await wait(400); }
  let last = '', same = 0;   // the page's height and its blocks settled (fonts, pictures, the phone's gaps)
  for (let t = 0; t < 30000; t += 400) {
    const k = await p.evaluate(() => [document.documentElement.scrollHeight].concat([...document.querySelectorAll('main section')].map(s => Math.round(s.getBoundingClientRect().top + scrollY))).join(','));
    if (k === last) { if (++same >= 3) break; } else { same = 0; last = k; }
    await wait(400);
  }
  await p.evaluate(() => scrollTo(0, 0)); await settle(p, 300);
  const plan = await p.evaluate(() => window.__LC.plan());
  const raw = { t: new Date().toISOString(), env0: plan.env, plan, screens: [], series: [], errs, load };
  raw.chrome = await p.evaluate(() => window.__LC.chrome());
  if (plan.env.flow || (plan.env.adapter === 'mask' && plan.env.phone)) raw.scan = await p.evaluate(() => window.__LC.scan());   // a phone's stack, at the top
  for (const s of plan.screens) {
    await p.evaluate(y => scrollTo(0, y), s.y); await settle(p);
    const pos = await storyPos(p);
    const m = await p.evaluate(id => window.__LC.screen(id), s.id);
    m.at = { y: s.y, hold: s.hold, expectP: s.expectP, p: pos.p, drawn: pos.drawn };
    if (s.via) m.via = s.via; if (s.dock) m.dock = true;
    raw.screens.push(m); log(`  ${s.id}${s.via ? ' @' + s.via : ''} y${s.y} p${pos.p == null ? '-' : (+pos.p).toFixed(3)}`);
  }
  const done = new Set();
  for (const s of plan.series) {
    const key = s.id + '@' + s.y; if (done.has(key)) continue; done.add(key);
    await p.evaluate(y => scrollTo(0, y), s.y); await settle(p);
    const m = await p.evaluate(k => window.__LC.series(k), s.id);
    m.at = { y: s.y, i: s.i == null ? null : s.i };
    if (s.id === 'kit-land' && !m.err) {   // the card's body after the landing: how much more scroll until it is there (≥ 0.9)
      const H = plan.env.H; m.after = [];
      for (let i = 1; i <= 12; i++) {
        const dy = Math.round(i * 0.01 * H);
        const o = await p.evaluate(async y => { scrollTo(0, y); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); await new Promise(r => setTimeout(r, 40));
          const c = document.querySelector('.kitcard'), b = c && Array.from(c.children).filter(e => !e.matches('.kc-fig, .kc-pic, .kc-live'));
          return b && b.length ? Math.min(...b.map(e => +getComputedStyle(e).opacity)) : null; }, s.y + dy);
        m.after.push([dy, o == null ? null : Math.round(o * 1000) / 1000]);
        if (o != null && o >= 0.9) break;
      }
    }
    raw.series.push(m); log(`  series ${s.id}${s.i == null ? '' : ' ' + s.i} y${s.y}`);
  }
  raw.page = await p.evaluate(() => window.__LC.pageLevel());
  raw.ms = Date.now() - t0;
  return raw;
}

async function runCli(argv) {
  const [slug, html, files, rawDir, vps] = argv;
  const { chromium } = require('playwright');
  fs.mkdirSync(rawDir, { recursive: true });
  const list = (vps ? vps.split(',') : VIEWPORTS).map(parseVp);
  const launch = () => chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-sandbox'] });
  let browser = await launch();
  const prog = path.join(rawDir, 'progress.jsonl');
  for (const vp of list) {
    const f = path.join(rawDir, `${slug}__${vp.id}.json`);
    if (fs.existsSync(f)) { console.log(slug, vp.id, 'done before'); continue; }
    const t0 = Date.now();
    if (!browser.isConnected()) { console.log('the browser has gone: a new one'); browser = await launch(); }   // a crash (the GPU process) ends one viewport, not the run
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: vp.dpr, isMobile: vp.touch, hasTouch: vp.touch });
    await install(ctx, { html, files });
    const p = await ctx.newPage(), errs = [];
    p.on('pageerror', e => errs.push('PAGEERROR ' + e.message.slice(0, 160)));
    p.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)); });
    try {
      await p.goto(ORIGIN, { waitUntil: 'load', timeout: 120000 });
      const raw = await measure(p, s => console.log(s));
      // a phone's blocks: the gaps between them are written by script after the blocks are shown (a race that depends on the
      // load's timing): two more loads, the cache warm, each logged from its start; the rules take the worst of the three
      if (raw.env0.flow || (raw.env0.adapter === 'mask' && raw.env0.phone)) {
        raw.loadRuns = [];
        for (let i = 0; i < 2; i++) { await p.reload({ waitUntil: 'load', timeout: 120000 }); raw.loadRuns.push(await loadTimeline(p).catch(e => ({ err: String(e).slice(0, 160) }))); }
      }
      raw.slug = slug; raw.vp = vp; raw.errs = raw.errs.concat(errs); raw.wallMs = Date.now() - t0;
      fs.writeFileSync(f, JSON.stringify(raw));
      fs.appendFileSync(prog, JSON.stringify({ t: new Date().toISOString(), slug, vp: vp.id, ms: raw.wallMs, screens: raw.screens.length, series: raw.series.length, errs: raw.errs.length }) + '\n');
      console.log(slug, vp.id, 'ok', Math.round(raw.wallMs / 1000) + ' s', raw.errs.length ? 'errs ' + raw.errs.join(' | ').slice(0, 200) : '');
    } catch (e) {
      console.log(slug, vp.id, 'FAILED', e.message.slice(0, 300));
      fs.appendFileSync(prog, JSON.stringify({ t: new Date().toISOString(), slug, vp: vp.id, fail: e.message.slice(0, 200) }) + '\n');
    }
    await ctx.close().catch(() => {});
  }
  await browser.close().catch(() => {});
}

module.exports = { VIEWPORTS, parseVp, install, measure, settle, ORIGIN, PAGE_JS };
Object.assign(module.exports, require('./layout-rules.cjs'));

if (require.main === module) {
  const [cmd, ...rest] = process.argv.slice(2);
  if (cmd === 'run') runCli(rest).catch(e => { console.error(e); process.exit(1); });
  else if (cmd === 'eval') require('./layout-rules.cjs').cli(rest);
  else { console.log(fs.readFileSync(__filename, 'utf8').split('\n').slice(0, 20).join('\n')); process.exit(cmd ? 1 : 0); }
}
