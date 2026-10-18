// QA of the full V-TECH live page on pre-rendered Blender frames (site/proto/vtech-live.html, build-vtech.py): the page
// is served from a fake origin with its files (seq/, img/), wrapped in the same skeleton the artifact host adds, with
// the real fonts. Checks: the story position follows the scroll monotonically through all runs (60 px steps) and each
// screen holds its key frame while it is read; every frame of every run is fetched once; only a window of frames stays
// decoded; the 3D kit lands in the offer card and the fixed canvas is gone there; the exosome cells live in S2–S3,
// never over the copy (only faint bokeh) nor the S3 ampoules, none from S4 on; the copy keeps the right half; no
// horizontal scroll; headings below the sticky header; phone: the story in a stage under the header, the window, the stills
// in the slots, the offer in the order heading → card → text → buttons → contacts and the bottom bar off the card;
// reduced motion: key frames only; no JS: the first frame as a still; the lead form validates and completes; no
// console errors. With SYNTH=<2400×1500 RGBA webp> the same file is served for every frame at the 2400 tier, the CPU
// is slowed 4× and the story is scrolled down and up twice: memory window, long tasks, frame on time after a stop.
// Screenshots per screen, mid-run, during the landing. Any product page built by build-vtech.py: the kit callouts are
// expected when the card lists two kinds (V-TECH), and a home-care page («טיפוח ביתי», no .badge.pro on S1) must send
// every «איפה לקנות» to WhatsApp, not to the price form, with the offer's second button going to the specialists.
// usage: [SYNTH=<webp>] FONTDIR=<dir with Rubik[wght].ttf> NODE_PATH=$(npm root -g) node verify-live.cjs <page.html> <files dir> <out dir>
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [pagePath, filesDir, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
  + fs.readFileSync(pagePath, 'utf8') + '</body></html>';
const ORIGIN = 'https://live.test/';
const FONTDIR = process.env.FONTDIR || path.join(require('os').tmpdir(), 'mitoderm-fonts');
const SYNTH = process.env.SYNTH, SYNTH_TIER = 2400, RATE = +(process.env.SYNTH_RATE || 4);   // SYNTH_RATE: CPU slow-down (4 by default)
const FONTS = [['Rubik', 'Rubik[wght].ttf']];   // owner 17/10: Rubik in every role
const FONT_CSS = FONTS.map(([f], i) => `@font-face{font-family:'${f}';src:url(https://fonts.gstatic.com/local/${i}.ttf) format('truetype');font-weight:100 900;font-display:block}`).join('\n');
const STORY = ['meet', 'why', 'inside', 'feel', 'protocol', 'offer'];   // the anchors of the five runs
const checks = [];
const ok = (name, pass, info = '') => { checks.push({ name, pass, info }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (info ? '  ' + info : '')); };
const TYPES = { '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg' };
const MB = b => (b / 1e6).toFixed(1) + ' MB';

async function open(browser, w, h, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: opts.dpr || 1, reducedMotion: opts.reduce ? 'reduce' : 'no-preference', hasTouch: w < 500, javaScriptEnabled: !opts.nojs });
  const p = await ctx.newPage(); const errs = [], req = { seq: new Map(), cells: new Set(), helix: 0 };
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); });
  p.on('pageerror', e => errs.push('PAGEERROR ' + e.message.slice(0, 200)));
  if (opts.tier) await ctx.addInitScript(t => { window.__SEQ_TIER = t; }, opts.tier);
  await ctx.addInitScript(() => {   // long tasks, from the very start
    window.__lt = []; try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lt.push([e.startTime, e.duration]); }).observe({ type: 'longtask', buffered: true }); } catch (e) {}
  });
  await ctx.route('https://fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: FONT_CSS }));
  await ctx.route('https://fonts.gstatic.com/local/**', r => r.fulfill({ path: path.join(FONTDIR, FONTS[+r.request().url().match(/(\d+)\.ttf$/)[1]][1]), contentType: 'font/ttf' }));
  await ctx.route(ORIGIN + '**', r => {   // context-wide, so the frame worker's fetches are served (and counted) too
    const rel = decodeURIComponent(new URL(r.request().url()).pathname.slice(1));
    if (!rel || rel === 'index.html') return r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html });
    if (rel.startsWith('seq/')) req.seq.set(rel, (req.seq.get(rel) || 0) + 1);
    if (rel.startsWith('img/cells/')) req.cells.add(rel);
    if (rel === 'img/helix.webp') req.helix++;
    if (opts.synth && rel.startsWith('seq/')) return r.fulfill({ path: opts.synth, contentType: 'image/webp' });
    const f = path.join(filesDir, rel);
    return fs.existsSync(f) ? r.fulfill({ path: f, contentType: TYPES[path.extname(f)] || 'application/octet-stream' }) : r.fulfill({ status: 404, body: '' });
  });
  await p.goto(ORIGIN + 'index.html', { waitUntil: 'load' });
  if (!opts.nojs) await p.evaluate(() => document.fonts.ready);
  return { ctx, p, errs, req };
}
const seq = p => p.evaluate(() => window.__seq());
const scrollTo = (p, y) => p.evaluate(v => scrollTo(0, v), y);
const frame = s => s.run + s.want / (s.N - 1);                      // the wanted frame in run units (0 … R)
const shownAt = s => s.shown ? s.shown[0] + s.shown[1] / (s.Ns[s.shown[0]] - 1) : -1;
const near = s => s.shown && Math.abs(shownAt(s) - frame(s)) <= 1 / (s.N - 1) + 1e-6;   // within ±1 frame
// the offer's reading position: the card fully in view
const offerRead = p => p.evaluate(() => { const c = document.querySelector('.kitcard'); return Math.max(0, c.getBoundingClientRect().top + scrollY - Math.min(innerHeight * 0.2, innerHeight - c.offsetHeight - 24)); });

const layout = async (p, tag) => {
  const r = await p.evaluate(ids => {
    const hb = document.querySelector('.top').getBoundingClientRect().bottom;
    const scroller = e => { for (let a = e.parentElement; a; a = a.parentElement) if (/auto|scroll/.test(getComputedStyle(a).overflowX)) return true; return false; };
    const offscreen = [...document.querySelectorAll('main *')].filter(e => { const b = e.getBoundingClientRect(); return b.width && (b.left < -1 || b.right > innerWidth + 1) && !scroller(e); }).map(e => e.tagName + '.' + e.className).slice(0, 5);
    const copyLeft = Math.min(...ids.map(id => document.querySelector(`#${id} .copy`).getBoundingClientRect().left), document.querySelector('.offer-copy').getBoundingClientRect().left);
    const card = document.querySelector('.kitcard').getBoundingClientRect();
    return { sw: document.documentElement.scrollWidth, iw: innerWidth, hb, offscreen, copyLeft, cardRight: card.right };
  }, STORY.slice(0, 5));
  if (r.iw >= 900) {
    ok(`${tag}: the story copy stays in the right half, clear of the 3D`, r.copyLeft >= r.iw * 0.47, `copy left edge ${r.copyLeft.toFixed(0)} of ${r.iw}`);
    ok(`${tag}: the offer card sits on the left`, r.cardRight <= r.iw * 0.53, `card right edge ${r.cardRight.toFixed(0)}`);
  }
  ok(`${tag}: no horizontal scroll`, r.sw <= r.iw, `${r.sw}/${r.iw}`);
  ok(`${tag}: nothing outside the screen`, !r.offscreen.length, r.offscreen.join(' '));
  // every heading, scrolled to its reading position (its section at the top), sits below the sticky header
  const under = await p.evaluate(async () => {
    const bad = [], hb = () => document.querySelector('.top').getBoundingClientRect().bottom;
    for (const s of document.querySelectorAll('main section')) {
      s.scrollIntoView(); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const h = s.querySelector('h1, h2'); if (h && h.getBoundingClientRect().top < hb() - 1) bad.push(s.id || s.className);
    }
    scrollTo(0, 0); return bad;
  });
  ok(`${tag}: headings below the header`, !under.length, under.join(' '));
};

// the cells on screen: rects and opacities of every visible sprite, by layer
const cellsNow = p => p.evaluate(() => [...document.querySelectorAll('.cells img')].filter(i => i.style.visibility === 'visible' && +i.style.opacity > 0.004)
  .map(i => { const b = i.getBoundingClientRect(), sc = +(i.style.transform.match(/scale\(([\d.]+)\)/) || [0, 0])[1];
    return { front: i.parentElement.classList.contains('front'), o: +i.style.opacity, cx: (b.left + b.right) / 2, cy: (b.top + b.bottom) / 2, d: i.offsetWidth * sc }; }));
// sprite discs (a cell fills ~84% of its square sprite): how far into the copy half, and into the S3 hero box
const cellRules = (cs, W, H, hero) => {
  const bad = [];
  for (const c of cs) {
    const { cx, cy } = c, rad = c.d * 0.42;
    if (cx + rad * 0.75 > W * 0.5 + 2 && c.o > (c.front ? 0.2 : 0.35) + 0.01) bad.push(`over copy o=${c.o.toFixed(2)} x=${cx.toFixed(0)}`);
    if (hero && c.front && c.o > 0.05) {
      const dx = Math.max(hero[0] * W - cx, 0, cx - hero[2] * W), dy = Math.max(hero[1] * H - cy, 0, cy - hero[3] * H);
      if (Math.hypot(dx, dy) < rad * 0.5) bad.push(`over hero o=${c.o.toFixed(2)}`);
    }
  }
  return bad;
};

async function synthRun(browser, tag, assert) {
  const { ctx, p, errs } = await open(browser, 1440, 900, { dpr: 2, synth: SYNTH, tier: SYNTH_TIER });
  const cdp = await ctx.newCDPSession(p); await cdp.send('Emulation.setCPUThrottlingRate', { rate: RATE });
  await p.waitForFunction(() => window.__seq().shown, null, { timeout: 30000 }).catch(() => {});
  const st0 = await seq(p), end = await offerRead(p), frameBytes = 2400 * 1500 * 4, cap = (st0.win + st0.keys + 1) * frameBytes;
  let maxDec = 0, maxBytes = 0; const late = [], windows = [], lat = [];
  const sample = async () => { const s = await seq(p); maxDec = Math.max(maxDec, s.decoded); maxBytes = Math.max(maxBytes, s.decodedBytes); return s; };
  const stops = new Set(); for (let k = 1; k <= 8; k++) stops.add(Math.round(end * k / 9 / 80) * 80);
  const now = () => p.evaluate(() => performance.now());
  for (let pass = 0; pass < 2; pass++) for (const down of [true, false]) {   // ~2500 px/s, down and up, twice
    let t0 = await now();
    for (let i = 0; i <= Math.ceil(end / 80); i++) {
      const y = down ? Math.min(end, i * 80) : Math.max(0, end - i * 80);
      await scrollTo(p, y); await p.waitForTimeout(32);
      if (i % 4 === 0) await sample();
      if (pass === 0 && stops.has(y)) {   // a stop: 300 ms later the frame on screen is the wanted one (±1)
        windows.push([t0, await now()]);
        await p.waitForTimeout(300); const s = await sample(); if (!near(s)) late.push(`${y}:${frame(s).toFixed(3)}/${shownAt(s).toFixed(3)}`);
        let ms = 300; while (!near(await seq(p)) && ms < 4000) { await p.waitForTimeout(50); ms += 50; }   // and when it is
        lat.push(ms);
        t0 = await now();
      }
    }
    windows.push([t0, await now()]);
  }
  const tasks = await p.evaluate(() => window.__lt), during = tasks.filter(([t]) => windows.some(([a, b]) => t >= a && t <= b));
  const s = await sample(), lt = during.length, longest = during.reduce((m, [, d]) => Math.max(m, d), 0);
  const line = `${lt} long tasks while scrolling (longest ${longest.toFixed(0)} ms), ${tasks.length} in all`;
  if (assert) {
    ok(`${tag}: tier ${s.tier}, decoded count within the window`, s.tier === SYNTH_TIER && maxDec <= st0.win + st0.keys + 1 && s.peak.n <= st0.win + st0.keys + 1,
      `max ${maxDec} decoded (peak ${s.peak.n}) of ${st0.win} + ${st0.keys} + 1`);
    ok(`${tag}: decoded bytes under the cap`, s.peak.bytes <= cap, `peak ${MB(s.peak.bytes)}, cap ${MB(cap)} = ${st0.win + st0.keys + 1} frames × ${MB(frameBytes)}`);
    ok(`${tag}, CPU ${RATE}× slower: at most 3 long tasks while scrolling`, lt <= 3, line);
    ok(`${tag}: 300 ms after a stop the frame on screen is the wanted one (±1)`, !late.length, `${stops.size} stops` + (late.length ? '; late ' + late.join(' ') : ''));
    ok(`${tag}: no console errors`, !errs.length, errs.join(' | '));
  }
  console.log(`${assert ? '' : 'INFO '}${tag}: tier ${s.tier}, peak ${s.peak.n} frames / ${MB(s.peak.bytes)}, misses ${s.misses}, ${line}, late after stops ${late.length}/${stops.size}; `
    + `on screen after a stop within ${lat.sort((a, b) => a - b).map(v => v <= 300 ? '≤300' : v).join('/')} ms; `
    + `worker per frame: fetch ${s.fetchMs} ms, decode ${s.decodeMs} ms (max ${s.maxDecodeMs}); load average ${require('os').loadavg()[0].toFixed(1)} on ${require('os').cpus().length} cores`);
  await ctx.close();
}

(async () => {
  const browser = await chromium.launch();
  if (process.env.ONLY !== 'synth') {   // ONLY=synth: the synthetic run alone
  { // desktop: the story
    const { ctx, p, errs, req } = await open(browser, 1440, 900, { dpr: 2 });
    await layout(p, 'desktop 1440');
    const st0 = await seq(p); const R = st0.R;
    ok('desktop: worker decoding, tier picked', st0.worker && st0.tier > 0, `worker ${st0.worker}, tier ${st0.tier}, mode ${st0.mode}`);
    const end = await offerRead(p);
    const seen = []; let mono = true, prev = -1, maxDec = 0, maxBytes = 0, cellsSeen = { s2: 0, s3: 0, after: 0 }, cellBad = [];
    for (let y = 0; y <= end; y += 60) {
      await scrollTo(p, y); await p.waitForTimeout(25);
      const s = await seq(p); const g = frame(s); seen.push(+g.toFixed(3));
      if (g < prev - 1e-9) mono = false; prev = g;
      maxDec = Math.max(maxDec, s.decoded); maxBytes = Math.max(maxBytes, s.decodedBytes);
      if (y % 180 === 0) { const cs = await cellsNow(p); cellBad.push(...cellRules(cs, 1440, 900, Math.abs(s.pos - 2) < 0.5 ? [0.12, 0.25, 0.40, 0.85] : null));
        if (s.pos >= 3) cellsSeen.after = Math.max(cellsSeen.after, cs.length); }
    }
    ok('desktop: story position follows the scroll monotonically', mono, seen.filter((g, i) => i % 6 === 0).map(g => g.toFixed(2)).join(','));
    ok('desktop: the story runs from S1 to the offer', seen[0] === 0 && Math.abs(seen[seen.length - 1] - R) < 1e-6, `${seen[0]}..${seen[seen.length - 1]} of ${R}`);
    await p.waitForFunction(() => window.__seq().warmed >= window.__seq().Ns.reduce((a, b) => a + b, 0), null, { timeout: 60000 }).catch(() => {});
    const total = st0.Ns.reduce((a, b) => a + b, 0), fetched = [...req.seq.keys()].length, dup = [...req.seq.values()].reduce((a, b) => a + b, 0) - fetched;
    ok('desktop: every frame of every run is fetched', fetched === total, `${fetched}/${total} files, ${dup} fetched twice`);
    const keysN = (await seq(p)).keys, cap = st0.win + keysN + 1;
    ok('desktop: only the window and the end frames stay decoded', maxDec <= cap, `max ${maxDec} decoded (window ${st0.win} + ${keysN} end frames + the one on screen = ${cap}), max ${MB(maxBytes)}`);
    // each screen at its reading position (section top at the top of the screen): its key frame, shown
    const holds = [], cellsAt = {}, plateAt = {}, hxAt = {}, molsAt = {};
    for (let k = 0; k < STORY.length - 1; k++) {
      await p.evaluate(id => scrollTo(0, document.getElementById(id).offsetTop), STORY[k]);
      await p.waitForFunction(k => { const s = window.__seq(); return s.shown && s.shown[0] === k && s.shown[1] === 0; }, k, { timeout: 3000 }).catch(() => {});
      await p.waitForTimeout(400);
      const s = await seq(p); holds.push(`${STORY[k]}:${frame(s).toFixed(2)}/${shownAt(s).toFixed(2)}`); if (frame(s) !== k || shownAt(s) !== k) holds.push('!');
      const cs = await cellsNow(p); cellsAt[STORY[k]] = cs.length; plateAt[STORY[k]] = await p.evaluate(() => +document.querySelector('.plate').style.opacity);
      const hx = await p.evaluate(() => { const h = document.querySelector('.helix'), b = h.getBoundingClientRect(); return { o: +h.style.opacity || 0, right: b.right, loaded: h.complete && h.naturalWidth > 0 }; });
      hxAt[STORY[k]] = hx; molsAt[STORY[k]] = await p.evaluate(() => [...document.querySelectorAll('.cells img')].filter(i => /\/m\d\d-/.test(i.src) && i.style.visibility === 'visible').length);
      cellBad.push(...cellRules(cs, 1440, 900, k === 2 ? [0.12, 0.25, 0.40, 0.85] : null));
      await p.screenshot({ path: `${out}/desk-s${k + 1}.jpg`, type: 'jpeg', quality: 82 });
    }
    ok('desktop: each screen holds its key frame while read', !holds.includes('!'), holds.join(' '));
    ok('desktop: exosome cells float in S2–S3, none from S4 on', cellsAt.why >= 4 && cellsAt.inside >= 4 && !cellsAt.feel && !cellsAt.protocol && !cellsSeen.after,
      Object.entries(cellsAt).map(([k, v]) => `${k}:${v}`).join(' ') + ` · after S4 max ${cellsSeen.after}`);
    ok('desktop: the deep plate behind S2–S3 only', plateAt.why > 0.95 && plateAt.inside > 0.95 && plateAt.meet < 0.05 && plateAt.feel < 0.05,
      Object.entries(plateAt).map(([k, v]) => `${k}:${v.toFixed(2)}`).join(' '));
    ok('desktop: cells never over the copy (faint bokeh only) nor the S3 ampoules', !cellBad.length, cellBad.slice(0, 4).join(' | '));
    ok('desktop: PDRN molecules float with the cells in S2–S3', molsAt.why + molsAt.inside >= 2 && !molsAt.feel && !molsAt.protocol,
      Object.entries(molsAt).map(([k, v]) => `${k}:${v}`).join(' '));
    ok('desktop: the DNA helix shows behind S3 only, in the 3D half', hxAt.inside.o > 0.3 && hxAt.inside.loaded && hxAt.inside.right <= 1440 * 0.5 && hxAt.meet.o === 0 && hxAt.feel.o < 0.05 && hxAt.protocol.o === 0,
      Object.entries(hxAt).map(([k, v]) => `${k}:${v.o.toFixed(2)}`).join(' ') + ` · right edge ${hxAt.inside.right.toFixed(0)}`);
    const legend = await p.evaluate(() => { const l = document.querySelector('#inside .legend'); return l && l.textContent.trim(); });
    ok('desktop: S3 legend for the cells', legend === 'אקסוזומים סינתטיים — המחשה', legend);
    for (let k = 0; k < R; k++) {   // mid-run frames, to look at
      const y = await p.evaluate(([a, b, last]) => last ? (document.getElementById(a).offsetTop + document.querySelector('.kitcard').getBoundingClientRect().top + scrollY - innerHeight * 0.85) / 2 + innerHeight * 0.1
        : (document.getElementById(a).offsetTop + document.getElementById(b).offsetTop) / 2 + innerHeight * 0.05, [STORY[k], STORY[k + 1], k === R - 1]);
      await scrollTo(p, y); await p.waitForTimeout(400);
      await p.screenshot({ path: `${out}/desk-run${k + 1}.jpg`, type: 'jpeg', quality: 82 });
    }
    // the landing: the card rises, the 3D kit flies into its picture and the fixed canvas hands over
    const ct = await p.evaluate(() => document.querySelector('.kitcard').getBoundingClientRect().top + scrollY);
    await scrollTo(p, ct - 900 * 0.55); await p.waitForTimeout(300);
    const mid = await p.evaluate(() => ({ tf: document.getElementById('seq').style.transform, z: document.getElementById('seq').style.zIndex }));
    await p.screenshot({ path: `${out}/desk-landing.jpg`, type: 'jpeg', quality: 82 });
    await scrollTo(p, end); await p.waitForTimeout(400);
    const landed = await p.evaluate(() => {
      const c = document.querySelector('.kc-live'), x = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
      for (let i = 3; i < x.length; i += 4) if (x[i] > 20) n++;
      return { op: +document.getElementById('seq').style.opacity, card: +c.style.opacity, px: n / (c.width * c.height), cls: document.querySelector('.kitcard').className };
    });
    ok('desktop: the kit flies into the offer card and the fixed canvas is gone there', /scale\(0\.\d/.test(mid.tf) && mid.z === '3' && landed.op === 0 && landed.card === 1 && landed.px > 0.15 && /live/.test(landed.cls),
      `mid-flight ${mid.tf.slice(0, 60)}, at rest canvas ${landed.op}, card picture ${landed.card} (${(landed.px * 100).toFixed(0)}% filled)`);
    await p.screenshot({ path: `${out}/desk-s7-offer.jpg`, type: 'jpeg', quality: 82 });
    await p.evaluate(() => document.getElementById('specialists').scrollIntoView()); await p.waitForTimeout(300); await p.screenshot({ path: `${out}/desk-s8.jpg`, type: 'jpeg', quality: 82 });
    await p.evaluate(() => document.querySelector('.related').scrollIntoView()); await p.waitForTimeout(300);
    await p.screenshot({ path: `${out}/desk-s9.jpg`, type: 'jpeg', quality: 82 });
    const dock = await p.evaluate(() => ({ items: [...document.querySelectorAll('.dock a')].map(a => a.textContent), kit: !!document.getElementById('kit') }));
    ok('desktop: 7 dock items, no «ערכה ועובדות», no #kit screen', dock.items.length === 7 && !dock.items.includes('ערכה ועובדות') && !dock.kit, dock.items.join(' · '));
    const cyr = await p.evaluate(() => (document.body.innerText.match(/[Ѐ-ӿ]+/g) || []).slice(0, 5));
    ok('desktop: no Cyrillic in the page text', !cyr.length, cyr.join(' '));
    // the lead form: opens from the price button, validates, completes
    const home = await p.evaluate(() => !document.querySelector('#meet .badge.pro'));
    if (home) {   // home care: «איפה לקנות» opens WhatsApp everywhere, the lead form only for professionals (join)
      const b = await p.evaluate(() => ['.top .btn', '#meet .cta .btn.primary', '#offer .cta .btn.primary', '.bar .btn', '#offer .cta .btn.ghost'].map(q => {
        const a = document.querySelector(q); return { h: a.getAttribute('href'), lead: a.hasAttribute('data-lead'), t: a.textContent.trim() }; }));
      ok('desktop: home care, «איפה לקנות» opens WhatsApp (not the form), the second offer button the specialists',
        b.slice(0, 4).every(x => /^https:\/\/wa\.me\/\d+\?text=/.test(x.h) && !x.lead && x.t === b[0].t) && b[4].h === '#specialists' && !b[4].lead, JSON.stringify(b.map(x => x.t + ' → ' + x.h.slice(0, 24))));
    }
    await scrollTo(p, 0); await p.click('[data-lead]');   // the first in the page: the header (pro) or the join button (home)
    const opened = await p.evaluate(() => document.getElementById('lead').open);
    await p.click('#lead .submit'); const errsShown = await p.evaluate(() => [...document.querySelectorAll('#lead .err')].filter(e => e.textContent).length);
    await p.screenshot({ path: `${out}/desk-form-errors.jpg`, type: 'jpeg', quality: 80 });
    await p.fill('[name=name]', 'בדיקה בדיקה'); await p.fill('[name=profession]', 'קוסמטיקאית'); await p.fill('[name=email]', 'test@example.com'); await p.fill('[name=phone]', '0541234567');
    await p.check('[name=consent]'); await p.click('#lead .submit'); await p.waitForTimeout(1600);
    const doneShown = await p.evaluate(() => !document.querySelector('.lead-done').hidden);
    ok('desktop: the lead form opens, validates and completes', opened && errsShown === 5 && doneShown, `open ${opened}, ${errsShown} errors on empty, done ${doneShown}`);
    ok('desktop: no console errors', !errs.length, errs.join(' | '));
    await ctx.close();
  }
  { // a narrow desktop: the copy still in the right half
    const { ctx, p } = await open(browser, 960, 720);
    await layout(p, 'desktop 960'); await ctx.close();
  }
  for (const [w, h] of [[390, 844], [360, 780]]) { // phone (owner 17/10: it moves too): the story in a stage under the header
    const { ctx, p, errs, req } = await open(browser, w, h, { dpr: 2 });
    await layout(p, `phone ${w}`);
    const r = await p.evaluate(() => ({ canvas: getComputedStyle(document.getElementById('seq')).display, seq: window.__seq(),
      st: getComputedStyle(document.documentElement).getPropertyValue('--stage-h'), top: getComputedStyle(document.documentElement).getPropertyValue('--stage-top') }));
    ok(`phone ${w}: the story plays in the stage`, r.canvas !== 'none' && r.seq.mode === 'full' && r.seq.tier > 0, `canvas ${r.canvas}, mode ${r.seq.mode}, tier ${r.seq.tier}, stage ${r.top.trim()} + ${r.st.trim()}`);
    let maxDec = 0; const held = [];
    for (const [n, id] of [...STORY, 'specialists'].entries()) {   // each heading just under the stage, as it is read
      await p.evaluate(i => { const s = document.getElementById(i), hd = s.querySelector('h1, h2'), cs = getComputedStyle(document.documentElement);
        const below = parseFloat(cs.getPropertyValue('--stage-top')) + parseFloat(cs.getPropertyValue('--stage-h')) + 14;
        scrollTo(0, Math.max(0, hd.getBoundingClientRect().top + scrollY - below)); }, id);
      await p.waitForTimeout(900);
      const q = await p.evaluate(() => window.__seq()); maxDec = Math.max(maxDec, q.decoded);
      if (n < STORY.length - 1) held.push(`${STORY[n]}:${q.shown ? q.shown.join('.') : '-'}`);
      await p.screenshot({ path: `${out}/phone${w}-${id}.jpg`, type: 'jpeg', quality: 82 });
    }
    const q = await p.evaluate(() => window.__seq());
    ok(`phone ${w}: only the window and the end frames stay decoded`, maxDec <= q.win + q.keys + 1, `max ${maxDec} decoded (window ${q.win} + ${q.keys} end frames + 1)`);
    ok(`phone ${w}: each screen shows its own run`, held.every((v, i) => +v.split(':')[1].split('.')[0] === Math.min(i, q.R - 1) || +v.split(':')[1].split('.')[0] === i - 1), held.join(' '));
    await p.evaluate(() => document.querySelector('.related').scrollIntoView()); await p.waitForTimeout(300);
    const seqReq = [...req.seq.values()].reduce((a, b) => a + b, 0), gone = await p.evaluate(() => ({ o: +document.getElementById('seq').style.opacity, push: +getComputedStyle(document.documentElement).getPropertyValue('--push') }));
    ok(`phone ${w}: frames fetched, not the whole story at once`, seqReq > 0, `${seqReq} requests`);
    ok(`phone ${w}: the DNA helix is never fetched`, !req.helix, `${req.helix} requests`);
    ok(`phone ${w}: the offer pushes the stage away`, gone.o === 0 && gone.push > 0, `canvas opacity ${gone.o}, push ${gone.push}px`);
    const order = await p.evaluate(() => ['#offer h2', '#offer .kitcard', '#offer .lead', '#offer .cta', '#offer .contacts'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().top + scrollY)));
    const kinds = await p.evaluate(() => document.querySelectorAll('#offer .kc-qty').length);
    const calls = await p.evaluate(() => { const c = document.querySelector('#offer .kitcard').getBoundingClientRect(), pic = document.querySelector('#offer .kc-pic, #offer .kitcard.live .kc-live');
      const pr = [...document.querySelectorAll('#offer .kc-pic, #offer .kc-live')].map(e => e.getBoundingClientRect()).find(r => r.height > 0);
      return [...document.querySelectorAll('#offer .kc-call')].map(e => { const r = e.getBoundingClientRect(); return { t: e.textContent.trim(), in: r.left >= c.left && r.right <= c.right, top: r.bottom <= pr.top + 1, bot: r.top >= pr.bottom - 1 }; }); });
    if (kinds === 2) ok(`phone ${w}: the kit's callouts name what is in it, above and below the picture`, calls.length === 2 && calls[0].in && calls[1].in && calls[0].top && calls[1].bot && /5×/.test(calls[0].t) && /5×/.test(calls[1].t), JSON.stringify(calls.map(c => c.t)));
    else ok(`phone ${w}: one kind in the box, no callouts`, !calls.length, JSON.stringify(calls.map(c => c.t)));
    ok(`phone ${w}: offer reads heading → card → text → buttons → contacts`, order.every((v, i) => !i || v > order[i - 1]), order.join(' < '));
    const cover = await p.evaluate(async () => {   // the card's foot at the bottom of the screen: the bar is not over it
      const c = document.querySelector('#offer .kitcard'); scrollTo(0, c.getBoundingClientRect().bottom + scrollY - innerHeight + 8);
      await new Promise(r => setTimeout(r, 600));
      const a = c.getBoundingClientRect(), b = document.querySelector('.bar'), bb = b.getBoundingClientRect(), vis = getComputedStyle(b).visibility !== 'hidden';
      return { overlap: vis && bb.top < a.bottom && bb.bottom > a.top ? Math.round(a.bottom - bb.top) : 0, away: b.classList.contains('away') };
    });
    await p.screenshot({ path: `${out}/phone${w}-offer-card.jpg`, type: 'jpeg', quality: 82 });
    ok(`phone ${w}: the bottom bar never covers the offer card`, !cover.overlap, `bar ${cover.away ? 'away' : 'shown'}, overlap ${cover.overlap}px`);
    ok(`phone ${w}: no console errors`, !errs.length, errs.join(' | '));
    await ctx.close();
  }
  { // reduced motion: only the key frames
    const { ctx, p } = await open(browser, 1440, 900, { reduce: true });
    const end = await offerRead(p); const set = new Set(); let maxDec = 0;
    for (let y = 0; y <= end; y += 90) { await scrollTo(p, y); await p.waitForTimeout(20); const s = await seq(p); set.add(s.want); maxDec = Math.max(maxDec, s.decoded); }
    const s = await seq(p);
    ok('reduced motion: key frames only', [...set].every(v => v === 0 || v === s.N - 1) && maxDec <= s.keys + 1, `frames ${[...set].join(',')}, max ${maxDec} decoded, mode ${s.mode}`);
    await ctx.close();
  }
  { // no JavaScript: the first key frame as a still, the copy visible
    const { ctx, p } = await open(browser, 1440, 900, { nojs: true }); await p.waitForTimeout(300);
    const v = await p.evaluate(() => { const s = document.querySelector('.still img'); return { d: getComputedStyle(document.querySelector('.still')).display, w: s.naturalWidth, h1: getComputedStyle(document.querySelector('h1')).opacity }; });
    ok('no JS: first key frame shown, copy visible', v.d !== 'none' && v.w > 0 && v.h1 === '1', JSON.stringify(v));
    await p.screenshot({ path: `${out}/desk-nojs.jpg`, type: 'jpeg', quality: 80 });
    await ctx.close();
  }
  }
  if (SYNTH) {   // memory and smoothness with full-size frames on a slowed CPU
    // Asserted on Chromium with a GPU-backed canvas (SwiftShader), as on every Mac, iPad and phone: the headless shell
    // has no GPU, so there every canvas draw rasterizes on the main thread, which no target device does. Its count is
    // printed for information.
    const gpu = await chromium.launch({ channel: 'chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
    await synthRun(gpu, 'synthetic (GPU canvas)', true); await gpu.close();
    await synthRun(browser, 'synthetic (headless shell, software canvas)', false);
  }
  await browser.close();
  const fails = checks.filter(c => !c.pass);
  console.log(`\n${checks.length - fails.length}/${checks.length} checks passed`);
  fs.writeFileSync(`${out}/report.json`, JSON.stringify(checks, null, 1));
})();
