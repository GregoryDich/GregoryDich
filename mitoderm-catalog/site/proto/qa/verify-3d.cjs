// Verification of the EXOCELL MASK 3D page: screenshots per block at 1440x900 and 390x844, console errors, horizontal
// overflow, dock highlight, text under fixed bars, the lead form (every price button, validation, loading, success,
// error, Esc, focus return), the specialists filter, the 800px dock, reduced motion and the no-WebGL fallback.
// usage: FONTDIR=<dir with the 4 TTFs> [ONLY=sections|phones|form|extra] node verify-3d.cjs <page.html> <outdir> <three.module.min.js> [label]
// fonts: curl -L -o '<dir>/<file>' https://raw.githubusercontent.com/google/fonts/main/ofl/<family>/<file> for
//   cormorantgaramond/CormorantGaramond[wght].ttf, jost/Jost[wght].ttf, frankruhllibre/FrankRuhlLibre[wght].ttf, heebo/Heebo[wght].ttf
//   (brackets URL-encoded as %5B %5D). three.js: npm i three@0.160.0 → node_modules/three/build/three.module.min.js.
// Chromium runs WebGL on SwiftShader; NODE_PATH must reach playwright.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [pagePath, out, threeFile, label = 'page'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const html = fs.readFileSync(pagePath, 'utf8');
const ORIGIN = 'https://exocell.test/';
// the page's real fonts (Google Fonts files from github.com/google/fonts), so line breaks and numerals are checked as shipped
const FONTDIR = process.env.FONTDIR || path.join(require('os').tmpdir(), 'mitoderm-fonts');
const FONTS = [['Cormorant Garamond', 'CormorantGaramond[wght].ttf'], ['Jost', 'Jost[wght].ttf'], ['Frank Ruhl Libre', 'FrankRuhlLibre[wght].ttf'], ['Heebo', 'Heebo[wght].ttf']];
const FONT_CSS = FONTS.map(([f, file], i) => `@font-face{font-family:'${f}';src:url(https://fonts.gstatic.com/local/${i}.ttf) format('truetype');font-weight:100 900;font-style:normal;font-display:block}`).join('\n');
const IDS = ['top', 'why', 'inside', 'feel', 'kit', 'protocol', 'offer', 'specialists'];
const report = { label, errors: {}, checks: [] };
const ok = (name, pass, info = '') => { report.checks.push({ name, pass, info }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (info ? '  ' + info : '')); };

async function newPage(browser, vw, vh, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 1, reducedMotion: opts.reduce ? 'reduce' : 'no-preference', hasTouch: vw < 500 });
  const p = await ctx.newPage();
  await p.addInitScript(() => { window.__snap = true; });
  await p.route('https://fonts.googleapis.com/**', r => r.fulfill({ status: 200, contentType: 'text/css', body: FONT_CSS }));
  await p.route('https://fonts.gstatic.com/local/**', r => r.fulfill({ path: path.join(FONTDIR, FONTS[+r.request().url().match(/(\d+)\.ttf$/)[1]][1]), contentType: 'font/ttf' }));
  await p.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', r => opts.noThree ? r.fulfill({ status: 404, body: '' }) : r.fulfill({ path: threeFile, contentType: 'application/javascript' }));
  await p.route(ORIGIN + '**', r => r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html }));
  const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 240)); });
  p.on('pageerror', e => errs.push('PAGEERROR ' + e.message.slice(0, 240)));
  await p.goto(ORIGIN + 'exocell.html', { waitUntil: 'load' });
  await p.evaluate(() => document.fonts.ready);
  return { ctx, p, errs };
}
// scroll to a block's anchor exactly as the page computes it (phone: the band between the header and the bottom bar)
const toAnchor = (p, id) => p.evaluate(id => {
  const el = document.getElementById(id), y = window.__anchorY ? window.__anchorY(+el.dataset.st) : null;
  const r = el.getBoundingClientRect();
  window.scrollTo(0, y != null ? y : r.top + scrollY + Math.min(0, (r.height - innerHeight) / 2));
}, id);
// wait until the copy on screen has revealed (SwiftShader frames are slow), then for its 0.6 s transition
async function settle(p, extra = 2500) {
  const t0 = Date.now();
  while (Date.now() - t0 < 8000) {
    const left = await p.evaluate(() => [...document.querySelectorAll('.rv:not(.in)')].filter(el => { const r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight - 80; }).length);
    if (!left) break;
    await p.waitForTimeout(250);
  }
  await p.waitForTimeout(extra);
}

// text elements of the visible block that sit under the fixed header, dock or bar, or under the kit caption
// (a block taller than the screen scrolls under the bottom dock/bar by design, so those only count for blocks that fit)
const overlaps = (p, id) => p.evaluate((id) => {
  const sec = document.getElementById(id), phone = innerWidth <= 760;
  const band = innerHeight - (phone ? document.querySelector('.top').offsetHeight + document.querySelector('.bar').offsetHeight : 0);
  const tall = sec.getBoundingClientRect().height > band + 1;
  const vis = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.05; };
  const bars = (tall ? ['.top .wrap'] : ['.top .wrap', '.dock', '.bar']).map(s => document.querySelector(s)).filter(el => el && vis(el)).map(el => [el.className, el.getBoundingClientRect()]);
  const dbl = document.querySelector('.dbl.on');
  if (dbl) bars.push(['dbl', dbl.getBoundingClientRect()]);
  const texts = [...sec.querySelectorAll('h1, h2, h3, p:not(.dbl), .chip, .btn, .mark, .fact, .step, .fchip, .contacts a, .kitcard, .spec')]
    .filter(el => vis(el) && !el.closest('[hidden]'));
  const hit = [];
  for (const el of texts) {
    const r = el.getBoundingClientRect();
    if (r.bottom <= 0 || r.top >= innerHeight || r.width === 0) continue;
    for (const [n, b] of bars) {
      const ix = Math.min(r.right, b.right) - Math.max(r.left, b.left), iy = Math.min(r.bottom, b.bottom) - Math.max(r.top, b.top);
      if (ix > 2 && iy > 2) hit.push(`${n.split(' ')[0]}×${el.tagName.toLowerCase()}.${(el.className || '').toString().split(' ')[0]} "${el.textContent.trim().slice(0, 24)}"`);
    }
  }
  return hit;
}, id);

async function sections(browser, vw, vh, tag) {
  const { ctx, p, errs } = await newPage(browser, vw, vh);
  await p.waitForTimeout(2500);
  const m0 = await p.evaluate(() => ({ gl: !!window.__glReady, glOn: document.documentElement.classList.contains('gl-on'), fb: getComputedStyle(document.querySelector('.still-fallback')).visibility }));
  ok(`${tag} 3D ready, fallback hidden`, m0.gl && m0.glOn && m0.fb === 'hidden', JSON.stringify(m0));
  for (let i = 0; i < IDS.length; i++) {
    await toAnchor(p, IDS[i]);
    await settle(p);
    const st = await p.evaluate(() => {
      const on = document.querySelector('.dock a.on');
      return { sw: document.scrollingElement.scrollWidth, iw: innerWidth, dock: on ? +on.dataset.i : null, dockVisible: getComputedStyle(document.querySelector('.dock')).display !== 'none' };
    });
    ok(`${tag} ${IDS[i]}: no horizontal scroll`, st.sw <= st.iw, `scrollWidth ${st.sw} / ${st.iw}`);
    if (st.dockVisible) ok(`${tag} ${IDS[i]}: dock lit on item ${i}`, st.dock === i, `lit ${st.dock}`);
    const obj = await p.evaluate((id) => {
      const rects = window.__objRects ? window.__objRects() : [];
      const vis = el => { const s = getComputedStyle(el); return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.05; };
      const sec = document.getElementById(id);
      const copy = [...sec.querySelectorAll('h1, h2, p, .kicker, .chip, .btn, .mark, .fact, .step, .badges, .contacts a, .kitcard, .shot')].filter(el => vis(el) && !el.closest('[hidden]') && !el.classList.contains('dbl'))
        .map(el => { const r = el.getBoundingClientRect(); return ['copy ' + el.tagName.toLowerCase() + '.' + (el.className || '').toString().split(' ')[0], r]; });
      const fixed = [['header logo', document.querySelector('.top .logo')], ['header button', document.querySelector('.top .btn')], ['dock', document.querySelector('.dock')], ['bar', document.querySelector('.bar')]]
        .filter(([n, el]) => el && vis(el)).map(([n, el]) => [n, el.getBoundingClientRect()]);
      if (innerWidth <= 760) fixed.push(['header', document.querySelector('.top').getBoundingClientRect()]);
      const hit = [];
      for (const o of rects) for (const [n, r] of copy.concat(fixed)) {
        const ix = Math.min(o[2], r.right) - Math.max(o[0], r.left), iy = Math.min(o[3], r.bottom) - Math.max(o[1], r.top);
        if (ix > 4 && iy > 4 && r.bottom > 0 && r.top < innerHeight) hit.push(`${n} ${Math.round(ix)}x${Math.round(iy)}`);
      }
      const fl = document.querySelector('.dbl.fl.on'), inflow = document.querySelector('.kit .dbl');
      let capInfo = null;
      if (fl) {
        const c = fl.getBoundingClientRect();
        const inside = c.left >= 0 && c.right <= innerWidth && c.top >= 0 && c.bottom <= innerHeight;
        const onObj = rects.filter(o => Math.min(o[2], c.right) - Math.max(o[0], c.left) > 0 && Math.min(o[3], c.bottom) - Math.max(o[1], c.top) > 0).length;
        const onCopy = copy.filter(([n, r]) => Math.min(r.right, c.right) - Math.max(r.left, c.left) > 0 && Math.min(r.bottom, c.bottom) - Math.max(r.top, c.top) > 0).length;
        capInfo = { floating: true, inside, onObj, onCopy, x: Math.round(c.left), y: Math.round(c.top), w: Math.round(c.width) };
      } else if (id === 'kit') capInfo = { floating: false, inflowVisible: getComputedStyle(inflow).visibility === 'visible' };
      return { hit, capInfo, n: rects.length };
    }, IDS[i]);
    ok(`${tag} ${IDS[i]}: 3D objects clear of copy, header and dock`, obj.hit.length === 0, `${obj.n} objects; ` + obj.hit.slice(0, 5).join('; '));
    if (obj.capInfo) ok(`${tag} ${IDS[i]}: double-mask caption ${obj.capInfo.floating ? 'floats in free space inside the screen' : 'shown in the copy'}`,
      obj.capInfo.floating ? (obj.capInfo.inside && obj.capInfo.onObj === 0 && obj.capInfo.onCopy === 0) : obj.capInfo.inflowVisible, JSON.stringify(obj.capInfo));
    const extra = await p.evaluate((id) => {
      const sec = document.getElementById(id), st = +sec.dataset.st, rects = window.__objRects();
      const slot = sec.querySelector('.ph-slot'), sr = slot && slot.offsetParent ? slot.getBoundingClientRect() : null;
      let slotInfo = null;
      if (sr && rects.length) {
        const u = [Math.min(...rects.map(r => r[0])), Math.min(...rects.map(r => r[1])), Math.max(...rects.map(r => r[2])), Math.max(...rects.map(r => r[3]))];
        const out = Math.max(sr.left - u[0], sr.top - u[1], u[2] - sr.right, u[3] - sr.bottom);
        slotInfo = { out: Math.round(out), dx: Math.round((u[0] + u[2]) / 2 - (sr.left + sr.right) / 2), dy: Math.round((u[1] + u[3]) / 2 - (sr.top + sr.bottom) / 2) };
      }
      const boxVisible = window.__objRects && rects.length && [0, 1, 2, 4, 5].includes(st);
      return { st, slotInfo, front: boxVisible ? window.__frontPixel() : null, sach: window.__sachetInfo() };
    }, IDS[i]);
    if (extra.slotInfo) ok(`${tag} ${IDS[i]}: product inside its slot beside the copy`, extra.slotInfo.out <= 14 && Math.abs(extra.slotInfo.dx) <= 20 && Math.abs(extra.slotInfo.dy) <= 24, JSON.stringify(extra.slotInfo));
    if (extra.front) report.front = (report.front || []).concat([{ tag, id: IDS[i], rgb: extra.front.rgb }]);
    if (['inside', 'kit'].includes(IDS[i])) {
      const ms = await p.evaluate(() => window.__maskState ? window.__maskState() : []);
      const shown = ms.filter(m => m.visible && m.o > 0.05);
      ok(`${tag} ${IDS[i]}: masks fully opaque`, shown.length > 0 && shown.every(m => m.o >= 0.999 && !m.transparent), JSON.stringify(ms));
    }
    if (IDS[i] === 'kit') {
      const blue = await p.evaluate(() => window.__maskPixel ? window.__maskPixel(1) : null), white = await p.evaluate(() => window.__maskPixel ? window.__maskPixel(0) : null);
      report.masks = (report.masks || []).concat([{ tag, blue: blue && blue.rgb, white: white && white.rgb }]);
    }
    if (IDS[i] === 'kit') {
      const S = extra.sach.filter(x => x.sachet), minW = Math.min(...S.map(x => x.rect[2] - x.rect[0]));
      const covered = S.filter(a => extra.sach.some(b => b !== a && b.z > a.z + 0.01 && Math.min(a.band[2], b.rect[2]) - Math.max(a.band[0], b.rect[0]) > 3 && Math.min(a.band[3], b.rect[3]) - Math.max(a.band[1], b.rect[1]) > 3)).length;
      const maxAng = Math.max(...S.map(x => x.angle));
      ok(`${tag} kit: 5 sachets, each ≥ ${vw <= 760 ? 100 : 150}px wide, wordmark uncovered, facing the camera (≤ 0.3 rad)`, S.length === 5 && minW >= (vw <= 760 ? 100 : 150) && covered === 0 && maxAng <= 0.3,
        `n ${S.length}, min width ${Math.round(minW)}, covered ${covered}, max angle ${maxAng.toFixed(2)}`);
    }
    const hits = await overlaps(p, IDS[i]);
    ok(`${tag} ${IDS[i]}: no text under header/dock/bar/caption`, hits.length === 0, hits.slice(0, 4).join('; '));
    await p.screenshot({ path: `${out}/${tag}-${i}-${IDS[i]}.jpg`, quality: 78 });
  }
  const lay = await p.evaluate(() => {
    const rel = [...document.querySelectorAll('.related .card')].map(c => { const i = c.querySelector('.pic img').getBoundingClientRect(), pic = c.querySelector('.pic').getBoundingClientRect(), t = c.querySelector('.body').getBoundingClientRect(); return i.bottom <= t.top + 1 && i.top >= pic.top - 1 && i.bottom <= pic.bottom + 1; });
    const lines = el => { const ys = [...el.getClientRects()].map(r => (r.top + r.bottom) / 2).sort((a, b) => a - b); let n = 0, last = -1e9; for (const y of ys) { if (y - last > 8) n++; last = y; } return n; };
    const whole = [...document.querySelectorAll('main .nw')].filter(el => el.offsetParent).map(lines);
    return { relOk: rel.every(Boolean), rel: rel.length, nwBroken: whole.filter(n => n > 1).length, nw: whole.length };
  });
  ok(`${tag} related cards: packshots above the text, contained`, lay.relOk, `${lay.rel} cards`);
  // colour of the plain print: true to the print photo (#60a7ac) and the same at every pose
  const F = (report.front || []).filter(f => f.tag === tag), lab = ([r, g, b]) => {
    const f = c => { c /= 255; c = c > 0.04045 ? ((c + 0.055) / 1.055) ** 2.4 : c / 12.92; return c; };
    const R = f(r), G = f(g), B = f(b), X = (R * .4124 + G * .3576 + B * .1805) / .95047, Y = R * .2126 + G * .7152 + B * .0722, Z = (R * .0193 + G * .1192 + B * .9505) / 1.08883;
    const t = v => v > 0.008856 ? Math.cbrt(v) : 7.787 * v + 16 / 116; return [116 * t(Y) - 16, 500 * (t(X) - t(Y)), 200 * (t(Y) - t(Z))]; };
  const dE = (a, b) => { const A = lab(a), B = lab(b); return Math.hypot(A[0] - B[0], A[1] - B[1], A[2] - B[2]); };
  const toPrint = Math.max(...F.map(f => dE(f.rgb, [96, 167, 172]))), spread = Math.max(...F.flatMap(a => F.map(b => dE(a.rgb, b.rgb))));
  ok(`${tag} carton print colour true (ΔE ≤ 8 to the print) and constant (ΔE ≤ 5 between poses)`, F.length >= 3 && toPrint <= 8 && spread <= 5,
    F.map(f => f.id + ' ' + f.rgb.join(',')).join(' | ') + ` → ΔE print ${toPrint.toFixed(1)}, spread ${spread.toFixed(1)}`);
  const MK = (report.masks || []).filter(m => m.tag === tag)[0];
  if (MK) ok(`${tag} kit: blue layer true to #3a62b0 (ΔE ≤ 8), white layer white`, MK.blue && dE(MK.blue, [58, 98, 176]) <= 8 && MK.white && Math.min(...MK.white) >= 215 && Math.max(...MK.white) - Math.min(...MK.white) <= 12,
    `blue ${MK.blue} ΔE ${MK.blue ? dE(MK.blue, [58, 98, 176]).toFixed(1) : '-'}, white ${MK.white}`);
  // phone: between blocks the product never travels over the copy (every 60 px from the top to the protocol)
  if (vw <= 760) {
    const trav = await p.evaluate(async () => {
      const end = window.__anchorY(5) + 10, hits = [];
      for (let y = 0; y <= end; y += 60) {
        scrollTo(0, y); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
        const rects = window.__objRects();
        const copy = [...document.querySelectorAll('main h1, main h2, main p, main .chip, main .btn, main .fact, main .step, main .mark, main .kicker, main .badges, main .shot')]
          .filter(el => el.offsetParent && !el.classList.contains('dbl')).map(el => el.getBoundingClientRect()).filter(r => r.bottom > 0 && r.top < innerHeight);
        for (const o of rects) for (const r of copy) {
          const ix = Math.min(o[2], r.right) - Math.max(o[0], r.left), iy = Math.min(o[3], r.bottom) - Math.max(o[1], r.top);
          if (ix > 6 && iy > 6) { hits.push(y); break; }
        }
      }
      return [...new Set(hits)];
    });
    ok(`${tag} product never slides over the copy while scrolling (60 px steps)`, trav.length === 0, 'at ' + trav.slice(0, 8).join(','));
  }
  // scroll density: every 120 px down to the specialists, the visible band holds copy (or the product, large)
  const dens = await p.evaluate(async () => {
    const phone = innerWidth <= 760, hdr = phone ? document.querySelector('.top').offsetHeight : 0, low = phone ? document.querySelector('.bar').offsetHeight : 0;
    const end = document.getElementById('specialists').getBoundingClientRect().top + scrollY, empty = [];
    for (let y = 0; y < end; y += 120) {
      scrollTo(0, y); await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const text = [...document.querySelectorAll('main h1, main h2, main p, main .chip, main .btn, main .fact, main .step, main .mark, main .shot, main .kitcard')]
        .some(el => { const r = el.getBoundingClientRect(); return el.offsetParent && r.bottom > hdr + 40 && r.top < innerHeight - low - 40; });
      const big = window.__objRects().some(r => r[3] - r[1] >= 120);
      if (!text && !big) empty.push(y);
    }
    return { height: document.scrollingElement.scrollHeight, empty };
  });
  report.height = Object.assign(report.height || {}, { [tag]: dens.height });
  ok(`${tag} no empty screen while scrolling (copy or the product always in view)`, dens.empty.length === 0, `page ${dens.height}px; empty at ${dens.empty.slice(0, 6).join(',')}`);
  // related cards: one picture height, the packshot fills its frame (one side full), no backing plate
  await p.evaluate(async () => { document.querySelector('.related').scrollIntoView(); await Promise.all([...document.querySelectorAll('.related img')].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }))); });
  await p.waitForTimeout(400);
  const cards = await p.evaluate(() => [...document.querySelectorAll('.related .card')].map(c => {
    const pic = c.querySelector('.pic'), img = pic.querySelector('img'), b = img.getBoundingClientRect(), ar = img.naturalWidth / img.naturalHeight;
    const dw = Math.min(b.width, b.height * ar), dh = Math.min(b.height, b.width / ar), cs = getComputedStyle(pic);
    return { h: Math.round(b.height), fill: Math.max(dw / b.width, dh / b.height), plate: cs.backgroundImage !== 'none' || !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor) };
  }));
  ok(`${tag} related cards: same picture height, packshot fills its frame, no backing plate`, cards.length >= 5 && Math.max(...cards.map(c => c.h)) - Math.min(...cards.map(c => c.h)) <= 2 && cards.every(c => c.fill >= 0.97 && !c.plate), JSON.stringify(cards));
  ok(`${tag} Latin names never broken across lines`, lay.nwBroken === 0, `${lay.nw} kept groups, ${lay.nwBroken} broken`);
  // related block and footer
  await p.evaluate(() => window.scrollTo(0, document.scrollingElement.scrollHeight));
  await p.waitForTimeout(1500);
  await p.screenshot({ path: `${out}/${tag}-8-related-footer.jpg`, quality: 78 });
  const sw = await p.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth);
  ok(`${tag} footer: no horizontal scroll`, sw);
  report.errors[tag + '-sections'] = errs.slice();
  ok(`${tag} sections: 0 console errors`, errs.length === 0, errs.slice(0, 3).join(' | '));
  await ctx.close();
}

async function formTests(browser, vw, vh, tag, buttons) {
  const { ctx, p, errs } = await newPage(browser, vw, vh);
  await p.waitForTimeout(2000);
  const state = () => p.evaluate(() => {
    const d = document.getElementById('lead'), a = document.activeElement;
    return { open: d.open, active: a ? (a.name || a.className || a.tagName) : null, formOpen: document.documentElement.classList.contains('form-open') };
  });
  for (const sel of buttons) {
    const loc = p.locator(sel).first();
    await loc.scrollIntoViewIfNeeded();
    await p.waitForTimeout(300);
    await loc.click();
    await p.waitForTimeout(400);
    const s1 = await state();
    ok(`${tag} form opens from ${sel}`, s1.open && s1.active === 'name' && s1.formOpen, JSON.stringify(s1));
    await p.keyboard.press('Escape');
    await p.waitForTimeout(300);
    const s2 = await state();
    const back = await loc.evaluate(el => document.activeElement === el);
    ok(`${tag} Esc closes, focus back on ${sel}`, !s2.open && !s2.formOpen && back, JSON.stringify(s2));
  }
  // validation on an empty submit
  const opener = p.locator(buttons[0]).first();
  await opener.scrollIntoViewIfNeeded(); await opener.click(); await p.waitForTimeout(400);
  await p.screenshot({ path: `${out}/${tag}-form-0-open.jpg`, quality: 80 });
  await p.click('#lead .submit');
  await p.waitForTimeout(300);
  const v = await p.evaluate(() => ({
    errs: [...document.querySelectorAll('#lead .err')].map(e => e.textContent).filter(Boolean),
    invalid: [...document.querySelectorAll('#lead [aria-invalid="true"]')].map(e => e.name),
    active: document.activeElement.name
  }));
  ok(`${tag} empty submit shows 5 messages (incl. consent), 5 fields flagged`, v.errs.length === 5 && v.invalid.length === 5 && v.active === 'name', JSON.stringify(v));
  await p.screenshot({ path: `${out}/${tag}-form-1-errors.jpg`, quality: 80 });
  // tab trap: 40 tabs never leave the dialog
  let escaped = 0;
  for (let i = 0; i < 40; i++) { await p.keyboard.press('Tab'); if (!(await p.evaluate(() => document.getElementById('lead').contains(document.activeElement)))) escaped++; }
  ok(`${tag} focus stays in the dialog (40 Tabs)`, escaped === 0, `left ${escaped} times`);
  // phone rule
  const phoneCase = async (val) => { await p.fill('#lead [name=phone]', val); return p.evaluate(() => document.getElementById('e-phone').textContent === ''); };
  const pc = { '12345': await phoneCase('12345'), '054-326-2182': await phoneCase('054-326-2182'), '+972543262182': await phoneCase('+972543262182'), '03-1234567': await phoneCase('03-1234567'), '5432621820': await phoneCase('5432621820') };
  ok(`${tag} phone rule (0 + 8–9 digits or +972)`, !pc['12345'] && pc['054-326-2182'] && pc['+972543262182'] && pc['03-1234567'] && !pc['5432621820'], JSON.stringify(pc));
  // valid data: loading, then success
  await p.fill('#lead [name=name]', 'Test Name'); await p.fill('#lead [name=profession]', 'Cosmetologist');
  await p.fill('#lead [name=email]', 'test@example.com'); await p.fill('#lead [name=phone]', '054-326-2182');
  await p.check('#lead [name=consent]');
  await p.click('#lead .submit');
  await p.waitForTimeout(250);
  const busy = await p.evaluate(() => { const f = document.querySelector('#lead form'); return { busy: f.classList.contains('busy'), disabled: f.querySelector('.submit').disabled, ariaBusy: f.getAttribute('aria-busy') }; });
  ok(`${tag} submit → loading (dimmed, spinner, button disabled)`, busy.busy && busy.disabled && busy.ariaBusy === 'true', JSON.stringify(busy));
  await p.waitForTimeout(450);
  await p.screenshot({ path: `${out}/${tag}-form-2-loading.jpg`, quality: 80 });
  await p.waitForTimeout(1000);
  const done = await p.evaluate(() => ({ done: !document.querySelector('#lead .lead-done').hidden, body: !document.querySelector('#lead .lead-body').hidden, text: document.querySelector('#lead .lead-done').innerText.replace(/\s+/g, ' ') }));
  ok(`${tag} → success state`, done.done && !done.body, done.text);
  await p.screenshot({ path: `${out}/${tag}-form-3-success.jpg`, quality: 80 });
  await p.click('#lead .lead-done [data-close]');
  await p.waitForTimeout(300);
  ok(`${tag} «למידע נוסף» closes`, !(await p.evaluate(() => document.getElementById('lead').open)));
  // error state: keeps values, WhatsApp way out, submit enabled again
  await p.evaluate(() => { window.__leadFail = true; });
  await opener.click(); await p.waitForTimeout(400);
  const fresh = await p.evaluate(() => document.querySelector('#lead [name=name]').value === '' && !document.querySelector('#lead .lead-body').hidden);
  ok(`${tag} reopened after success: fresh form`, fresh);
  await p.fill('#lead [name=name]', 'Test Name'); await p.fill('#lead [name=profession]', 'Cosmetologist');
  await p.fill('#lead [name=email]', 'test@example.com'); await p.fill('#lead [name=phone]', '+972543262182');
  await p.check('#lead [name=consent]');
  await p.click('#lead .submit'); await p.waitForTimeout(1500);
  const fail = await p.evaluate(() => ({ fail: !document.querySelector('#lead .lead-fail').hidden, msg: document.querySelector('#lead .fail-msg').textContent, kept: document.querySelector('#lead [name=email]').value, enabled: !document.querySelector('#lead .submit').disabled, wa: document.querySelector('#lead .lead-fail a').href.startsWith('https://wa.me/') }));
  ok(`${tag} error state: WhatsApp button, values kept, submit enabled`, fail.fail && fail.msg.length > 10 && fail.kept === 'test@example.com' && fail.enabled && fail.wa, JSON.stringify(fail));
  await p.screenshot({ path: `${out}/${tag}-form-4-error.jpg`, quality: 80 });
  await p.click('#lead .lead-x'); await p.waitForTimeout(300);
  ok(`${tag} close button closes`, !(await p.evaluate(() => document.getElementById('lead').open)));
  // the payload the production call would send
  const payloadOk = await p.evaluate(() => document.querySelector('#lead form').dataset.endpoint === '/api/leads');
  ok(`${tag} data-endpoint="/api/leads"`, payloadOk);
  report.errors[tag + '-form'] = errs.slice();
  ok(`${tag} form: 0 console errors`, errs.length === 0, errs.slice(0, 3).join(' | '));
  await ctx.close();
}

async function filterTest(browser) {
  const { ctx, p, errs } = await newPage(browser, 1440, 900);
  await toAnchor(p, 'specialists'); await p.waitForTimeout(800);
  const count = () => p.evaluate(() => [...document.querySelectorAll('.spec')].filter(c => !c.hidden).length);
  const pressed = () => p.evaluate(() => [...document.querySelectorAll('.fchip')].map(c => c.getAttribute('aria-pressed')).join(','));
  const r = { initial: [await count(), await pressed()] };
  const chips = p.locator('.fchip');
  await chips.nth(2).click(); r.scalp = [await count(), await pressed()];
  r.emptyShown = await p.evaluate(() => !document.querySelector('.spec-empty').hidden);
  await chips.nth(0).click(); r.all = [await count(), await pressed()];
  await chips.nth(1).click(); r.face = [await count(), await pressed()];
  r.emptyMsg = await p.evaluate(() => { const e = document.querySelector('.spec-empty'); return e ? [e.hidden, e.textContent.length] : null; });
  ok('filter chips: פנים 3 · קרקפת 0 · הכל 3 (aria-pressed follows)', r.initial[0] === 3 && r.scalp[0] === 0 && r.emptyShown && r.all[0] === 3 && r.face[0] === 3 && r.initial[1] === 'false,true,false,false' && r.scalp[1] === 'false,false,true,false', JSON.stringify(r));
  const h = await p.evaluate(() => Math.min(...[...document.querySelectorAll('.fchip')].map(c => c.getBoundingClientRect().height)));
  ok('filter chips ≥ 44 px', h >= 44, h + 'px');
  await ctx.close();
}

async function extra(browser) {
  // 800 px: the dock is shown and fits
  {
    const { ctx, p, errs } = await newPage(browser, 800, 900);
    await p.waitForTimeout(1500);
    const d = await p.evaluate(() => { const el = document.querySelector('.dock'), r = el.getBoundingClientRect(); return { shown: getComputedStyle(el).display !== 'none', left: r.left, right: r.right, fits: el.scrollWidth <= el.clientWidth + 1, iw: innerWidth, h: Math.min(...[...el.querySelectorAll('a')].map(a => a.getBoundingClientRect().height)) }; });
    ok('800px: dock shown, inside the viewport, no clipping', d.shown && d.left >= 0 && d.right <= d.iw && d.fits, JSON.stringify(d));
    await toAnchor(p, 'kit'); await p.waitForTimeout(2500);
    await p.screenshot({ path: `${out}/w800-kit.jpg`, quality: 75 });
    ok('800px: 0 console errors', errs.length === 0, errs.join(' | '));
    await ctx.close();
  }
  for (const [vw, vh] of [[800, 900], [1024, 768], [1280, 800], [1920, 1080]]) {
    const { ctx, p, errs } = await newPage(browser, vw, vh);
    await p.waitForTimeout(1500);
    const hint = await p.evaluate(() => { const h = document.querySelector('.hint').getBoundingClientRect(); return [...document.querySelectorAll('.hero .btn')].every(b => { const r = b.getBoundingClientRect(); return Math.min(r.right, h.right) - Math.max(r.left, h.left) <= 0 || Math.min(r.bottom, h.bottom) - Math.max(r.top, h.top) <= 0; }); });
    ok(`${vw}x${vh}: scroll hint clear of the hero buttons`, hint);
    for (const id of ['inside', 'kit']) {
      await toAnchor(p, id); await settle(p, 2200);
      const r = await p.evaluate(() => {
        const rects = window.__objRects(), d = document.querySelector('.dock').getBoundingClientRect(), copy = [...document.querySelectorAll('main h2, main p, main .fact, main .kicker')].filter(el => el.offsetParent && getComputedStyle(el).opacity > 0.05).map(el => el.getBoundingClientRect());
        const hitDock = rects.filter(o => Math.min(o[2], d.right) - Math.max(o[0], d.left) > 4 && Math.min(o[3], d.bottom) - Math.max(o[1], d.top) > 4).length;
        const hitCopy = rects.filter(o => copy.some(c => c.bottom > 0 && c.top < innerHeight && Math.min(o[2], c.right) - Math.max(o[0], c.left) > 4 && Math.min(o[3], c.bottom) - Math.max(o[1], c.top) > 4)).length;
        const fl = document.querySelector('.dbl.fl.on'); let cap = null;
        if (fl) { const c = fl.getBoundingClientRect(); cap = { inside: c.left >= 0 && c.right <= innerWidth && c.top >= 0 && c.bottom <= innerHeight, onObj: rects.filter(o => Math.min(o[2], c.right) - Math.max(o[0], c.left) > 0 && Math.min(o[3], c.bottom) - Math.max(o[1], c.top) > 0).length }; }
        else cap = { inflow: getComputedStyle(document.querySelector('.kit .dbl')).visibility };
        return { hitDock, hitCopy, cap, sw: document.scrollingElement.scrollWidth };
      });
      ok(`${vw}x${vh} ${id}: objects clear of dock and copy, no overflow`, r.hitDock === 0 && r.hitCopy === 0 && r.sw <= vw, JSON.stringify(r));
      if (id === 'kit') ok(`${vw}x${vh} kit: caption in free space inside the screen, or in the copy`, r.cap.inside ? r.cap.onObj === 0 : r.cap.inflow === 'visible', JSON.stringify(r.cap));
      await p.screenshot({ path: `${out}/size-${vw}x${vh}-${id}.jpg`, quality: 75 });
    }
    ok(`${vw}x${vh}: 0 console errors`, errs.length === 0, errs.join(' | '));
    await ctx.close();
  }
  // reduced motion: whole stages, page still renders, fallback still fades
  {
    const { ctx, p, errs } = await newPage(browser, 1440, 900, { reduce: true });
    await p.waitForTimeout(2000);
    await toAnchor(p, 'inside'); await p.waitForTimeout(1500);
    const g = await p.evaluate(() => ({ glOn: document.documentElement.classList.contains('gl-on'), rv: [...document.querySelectorAll('.rv')].every(e => e.classList.contains('in')) }));
    ok('reduced motion: 3D on, all copy shown', g.glOn && g.rv, JSON.stringify(g));
    await p.screenshot({ path: `${out}/reduced-inside.jpg`, quality: 75 });
    await p.setViewportSize({ width: 1200, height: 800 }); await p.waitForTimeout(800);
    await p.screenshot({ path: `${out}/reduced-inside-resized.jpg`, quality: 75 });
    ok('reduced motion: 0 console errors', errs.length === 0, errs.join(' | '));
    await ctx.close();
  }
  // no three.js: the still packshot stays
  for (const [vw, vh] of [[1440, 900], [390, 844]]) {
    const { ctx, p, errs } = await newPage(browser, vw, vh, { noThree: true });
    await p.waitForTimeout(2500);
    const f = await p.evaluate(() => ({ glOn: document.documentElement.classList.contains('gl-on'), fb: getComputedStyle(document.querySelector('.still-fallback')).opacity, dbl: getComputedStyle(document.querySelector('.dbl')).position }));
    ok(`no WebGL ${vw}: packshot shown, caption in flow`, !f.glOn && f.fb === '1' && f.dbl !== 'fixed', JSON.stringify(f));
    await p.screenshot({ path: `${out}/nogl-${vw}-hero.jpg`, quality: 75 });
    await toAnchor(p, 'kit'); await p.waitForTimeout(600);
    await p.screenshot({ path: `${out}/nogl-${vw}-kit.jpg`, quality: 75 });
    ok(`no WebGL ${vw}: only the blocked script fails`, errs.every(e => /three|module|404|Failed to load/i.test(e)), errs.length + ' ' + errs.join(' | ').slice(0, 200));
    await ctx.close();
  }
}

(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const only = process.env.ONLY || 'all';
  if (only === 'all' || only === 'sections') { await sections(browser, 1440, 900, 'desk'); await sections(browser, 390, 844, 'phone'); }
  if (only === 'all' || only === 'phones') { await sections(browser, 430, 932, 'phone430'); await sections(browser, 360, 780, 'phone360'); }
  if (only === 'all' || only === 'form') {
    await formTests(browser, 1440, 900, 'desk', ['.top .btn[data-lead]', '.hero .btn.primary[data-lead]', '.offer .btn.primary[data-lead]', '.spec-foot .join [data-lead]']);
    await formTests(browser, 390, 844, 'phone', ['.hero .btn.primary[data-lead]', '.offer .btn.primary[data-lead]', '.bar .btn[data-lead]']);
    await filterTest(browser);
  }
  if (only === 'all' || only === 'extra') await extra(browser);
  await browser.close();
  const fails = report.checks.filter(c => !c.pass);
  console.log(`\n${label}: ${report.checks.length - fails.length}/${report.checks.length} checks passed`);
  fs.writeFileSync(`${out}/report-${label}.json`, JSON.stringify(report, null, 1));
})();
