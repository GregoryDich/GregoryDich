// The page map and its checks by numbers, for a live 3D product page (build-vtech.py --scene): in headless Chromium,
// with a three.js that draws nothing (qa/three-nodraw.mjs: each frame records where every mesh of the scene is instead),
// the page is scrolled in steps of 10 px on each screen; each step costs a layout and a frame, not a software render of
// seconds. At each step the probe records the story position, the canvas on the screen, every mesh's outline on the
// screen with its opacity, the scene's fades (edges, the dive's round fade, the amber glow), the header, dock and bar,
// the lines of text in view, every picture of the product in view (its drawn part), the kit card and the HD numbers.
// From these numbers alone it checks the owner's rules (CUT, UNDER_CHROME, UNDER_TEXT, TWO_PRODUCTS, GHOST, POP, EMPTY,
// RUN_SPAN, LAYOUT, HD: see analyse()), and writes the page map: per screen size the screens, the runs and their scroll
// spans, the poses, the product's outline per 10 px, the pictures, the texts, the flags. Pictures are needed only where
// a flag points, and for a last look at the key screens.
//
// usage (qa/pagemap.md: the tool's doc, the legend, the calibration):
//   NODE_PATH=$(npm root -g) THREE=<three.module.min.js> node qa/pagemap.cjs <page.html> <files dir> [--viewports all|key|<list>]
//       [--out <dir>] [--raw <dir>] [--three <file>] [--fonts <dir with Rubik[wght].ttf>] [--step 10] [--slug <slug>]
//       [--keys <dir of the key frames the build cut its pictures from>] [--build-cmd "<the build's command>"]
//       [--looked <spot.json of the last --spot run>]
//   node qa/pagemap.cjs --from-raw <raw dir> [--out <dir>]     the checks and the map again from a probe's raw data
//   node qa/pagemap.cjs --spot <map.json> <page.html> <files dir> [--viewports key|<list>] [--out <dir>]
//       [--classes CUT,EMPTY,…,colour]  the pictures the numbers ask for (real three.js): each flag's worst step (≤ 3 per
//       kind), the dive's light, the amber glass (spot())
// Timing (06/11, 4 CPUs, no GPU): the 15 modes of one build in about 2 minutes (7–10 s a screen, 3–5 s without 3D).
// <page.html>: the page as built (a body fragment: the host adds the document shell); <files dir>: the folder published
// with it (img/…). Viewports: WxH[@dpr][t] (t: touch, a phone or tablet), nojs-… (no JavaScript: the page's scripts
// removed), nogl-… (no WebGL: Chromium's --disable-3d-apis). all = the 11 screens of the page's QA and no JS / no WebGL at
// 1440x900 and 390x844; key = 1280x720 1440x900 1920x1080 390x844@3t. Out: <out>/<slug>.json (the map: slim, one screen
// a line, a legend inside), <slug>.md (a readable note; the part between <!-- notes --> and <!-- /notes --> of an existing
// one is kept) and README.md (the roadmap of the 13 pages); the 10 px track and the text boxes of every screen go to
// <raw>/<slug>.track.json.gz (or <tmp>/pagemap/ without --raw); raw: one gzipped JSON per screen (every step, every mesh),
// for --from-raw. Three.js: three@0.160.0's three.module.min.js (--three, $THREE or the one NODE_PATH resolves; e.g.
// `npm i --no-save three@0.160.0` in a scratch folder); the font: qa/fonts/Rubik[wght].ttf (the variable Rubik, OFL; or
// --fonts <dir>, $FONTDIR). Without the font or three.js the tool stops: a fallback font moves every line and the map.
'use strict';
const fs = require('fs'), path = require('path'), zlib = require('zlib'), crypto = require('crypto'), os = require('os');

const ARGV = process.argv.slice(2);
const opt = (k, d) => { const i = ARGV.indexOf(k); return i >= 0 ? ARGV[i + 1] : d; };
const POS = ARGV.filter((a, i) => !a.startsWith('--') && !(i > 0 && ARGV[i - 1].startsWith('--')));   // every option takes a value
const SETS = {
  key: ['1280x720', '1440x900', '1920x1080', '390x844@3t'],
  all: ['1280x720', '1366x768', '1440x900', '1920x1080', '2560x1080', '1024x768@2', '1180x820@2t',
    '390x844@3t', '360x780@3t', '820x1180@2t', '768x1024@2t', 'nojs-1440x900', 'nojs-390x844@3t', 'nogl-1440x900', 'nogl-390x844@3t'],
};
function parseVp(s) {
  const m = /^(?:(nojs|nogl)-)?(\d+)x(\d+)(?:@(\d+(?:\.\d+)?))?(t?)$/.exec(s);
  if (!m) throw new Error('bad viewport ' + s);
  return { id: s, kind: m[1] || 'live', w: +m[2], h: +m[3], dpr: +(m[4] || 1), touch: !!m[5] };
}

// ---------------------------------------------------------------------------------------------------------------------
// the probe, in the page (installed before the page's own scripts; with no JavaScript, the page's scripts are removed
// from its HTML, so the probe still runs): one record per scroll step
const PROBE = function () {
  if (window.__pm) return;
  const TXT = 'h1,h2,h3,h4,h5,h6,p,li,dt,dd,label,figcaption,blockquote,td,th,.chip,.btn,.kicker,.badge,.mark-line,.n';
  const PIC = 'img.stage-still,img.slot,.still img,.mt-step img,img.kc-pic,canvas.kc-live';
  const CHROME = ['.top', '.dock', '.bar'];
  const r1 = v => Math.round(v * 10) / 10, r3 = v => Math.round(v * 1000) / 1000;
  const owners = [], oid = new Map(), tinfo = [], pinfo = [], pid = new Map(), inks = new Map();
  let scanned = 0, picN = -1;
  const secOf = el => { const s = el.closest('section[id],.mt-prep,.kitcard,.foot,.related,.mt-step'); if (!s) return '';
    if (s.classList.contains('mt-step')) return 'step' + (Array.prototype.indexOf.call(s.parentElement.children, s) + 1);
    if (s.classList.contains('kitcard')) return 'kitcard'; if (s.classList.contains('mt-prep')) return 'prep';
    return s.id || s.className.split(' ')[0]; };
  const fixOf = el => { for (let e = el; e && e !== document.body; e = e.parentElement) { const p = getComputedStyle(e).position; if (p === 'sticky' || p === 'fixed') return p; } return ''; };
  function scanTexts() {   // the text nodes of the content (main, footer), each under its owner: the nearest text element
    scanned = 1;
    for (const base of document.querySelectorAll('main, footer')) {
      const tw = document.createTreeWalker(base, NodeFilter.SHOW_TEXT);
      for (let n = tw.nextNode(); n; n = tw.nextNode()) {
        if (!n.nodeValue.trim()) continue;
        const pe = n.parentElement; if (!pe || pe.closest('script,style,template,dialog,svg')) continue;
        const ow = pe.closest(TXT) || pe;
        if (!oid.has(ow)) { oid.set(ow, owners.length); owners.push({ el: ow, nodes: [] });
          tinfo.push({ tag: ow.tagName.toLowerCase(), cls: (ow.className && ow.className.baseVal === undefined ? ow.className : '').split(' ').filter(Boolean).slice(0, 2).join('.'),
            sec: secOf(ow), text: ow.textContent.replace(/\s+/g, ' ').trim().slice(0, 48), fix: fixOf(ow) }); }   // fix: sticky or fixed (it or an ancestor): its page box moves with the scroll
        owners[oid.get(ow)].nodes.push(n);
      }
    }
  }
  function inkOf(im) {   // the drawn part of a picture (alpha > 8) as fractions of its bitmap, measured once per file
    const key = im.currentSrc || im.src; if (inks.has(key)) return inks.get(key);
    if (!im.complete || !im.naturalWidth) return null;
    let r = [0, 0, 1, 1];
    try {
      const w = Math.min(256, im.naturalWidth), h = Math.max(1, Math.round(w * im.naturalHeight / im.naturalWidth)), c = document.createElement('canvas');
      c.width = w; c.height = h; const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(im, 0, 0, w, h);
      const d = x.getImageData(0, 0, w, h).data; let x0 = w, y0 = h, x1 = -1, y1 = -1;
      for (let y = 0; y < h; y++) for (let i = 0; i < w; i++) if (d[(y * w + i) * 4 + 3] > 8) { if (i < x0) x0 = i; if (i > x1) x1 = i; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      r = x1 < 0 ? null : [x0 / w, y0 / h, (x1 + 1) / w, (y1 + 1) / h];
    } catch (e) { r = [0, 0, 1, 1]; }
    inks.set(key, r); return r;
  }
  function canvasInk(cv) {   // a canvas's drawn part (the kit card's live picture), now
    try {
      if (!cv.width || !cv.height) return null;
      const w = Math.min(128, cv.width), h = Math.max(1, Math.round(w * cv.height / cv.width)), c = document.createElement('canvas');
      c.width = w; c.height = h; const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(cv, 0, 0, w, h);
      const d = x.getImageData(0, 0, w, h).data; let x0 = w, y0 = h, x1 = -1, y1 = -1;
      for (let y = 0; y < h; y++) for (let i = 0; i < w; i++) if (d[(y * w + i) * 4 + 3] > 8) { if (i < x0) x0 = i; if (i > x1) x1 = i; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      return x1 < 0 ? null : [x0 / w, y0 / h, (x1 + 1) / w, (y1 + 1) / h];
    } catch (e) { return [0, 0, 1, 1]; }
  }
  function contentBox(el, r) {   // the bitmap's box inside the element (object-fit), viewport px
    const cs = getComputedStyle(el), nw = el.naturalWidth || el.width, nh = el.naturalHeight || el.height, fit = cs.objectFit;
    if (!nw || !nh || fit === 'fill' || !fit) return [r.left, r.top, r.right, r.bottom];
    let s = fit === 'cover' ? Math.max(r.width / nw, r.height / nh) : Math.min(r.width / nw, r.height / nh);
    if (fit === 'none') s = 1; if (fit === 'scale-down') s = Math.min(1, Math.min(r.width / nw, r.height / nh));
    const w = nw * s, h = nh * s, pos = cs.objectPosition.split(' ').map(v => parseFloat(v) / 100);
    const px = isNaN(pos[0]) ? 0.5 : pos[0], py = isNaN(pos[1]) ? 0.5 : pos[1], x = r.left + (r.width - w) * px, y = r.top + (r.height - h) * py;
    return [x, y, x + w, y + h];
  }
  let cache = new Map();
  function eff(el) {   // effective opacity (0 when hidden), and the clip of overflowing ancestors (viewport px)
    let c = cache.get(el); if (c) return c;
    const cs = getComputedStyle(el);
    const parent = el.parentElement && el !== document.body ? eff(el.parentElement) : { op: 1, clip: null };
    let op = parent.op * (+cs.opacity), clip = parent.clip;
    if (cs.display === 'none') op = 0;
    // laid out but not drawn: a closed <details>'s content (content-visibility: hidden), and the like
    if (op > 0 && cs.display !== 'contents' && el.checkVisibility && !el.checkVisibility()) op = 0;   // (display: contents has no box of its own)
    if (el !== document.body && el !== document.documentElement && (cs.overflowX !== 'visible' || cs.overflowY !== 'visible')) {
      const r = el.getBoundingClientRect(), b = [r.left, r.top, r.right, r.bottom];
      clip = clip ? [Math.max(clip[0], b[0]), Math.max(clip[1], b[1]), Math.min(clip[2], b[2]), Math.min(clip[3], b[3])] : b;
    }
    c = { op, clip, vis: cs.visibility !== 'hidden' && cs.visibility !== 'collapse' };
    cache.set(el, c); return c;
  }
  const W = () => innerWidth, H = () => innerHeight;
  function texts(out) {
    const vw = W(), vh = H(), rg = document.createRange();
    for (let i = 0; i < owners.length; i++) {
      const o = owners[i], br = o.el.getBoundingClientRect();
      if (br.bottom < -50 || br.top > vh + 50 || (!br.width && !br.height)) continue;
      const e = eff(o.el); if (e.op < 0.05) continue;
      const lines = [];
      for (const n of o.nodes) {
        const pe = n.parentElement, pv = pe === o.el ? e : eff(pe); if (!pv.vis || pv.op < 0.05) continue;
        rg.selectNodeContents(n);
        for (const q of rg.getClientRects()) {
          if (q.width < 2 || q.height < 2) continue;
          let a = [q.left, q.top, q.right, q.bottom];
          const cl = pv.clip; if (cl) a = [Math.max(a[0], cl[0]), Math.max(a[1], cl[1]), Math.min(a[2], cl[2]), Math.min(a[3], cl[3])];
          if (a[2] - a[0] < 1 || a[3] - a[1] < 1 || a[3] < 0 || a[1] > vh || a[2] < 0 || a[0] > vw) continue;
          const L = lines.find(l => Math.abs(l[1] - a[1]) < 3 && Math.abs(l[3] - a[3]) < 3);
          if (L) { L[0] = Math.min(L[0], a[0]); L[2] = Math.max(L[2], a[2]); } else lines.push(a);
        }
      }
      for (const l of lines) out.push([i, r1(l[0]), r1(l[1]), r1(l[2]), r1(l[3]), r3(e.op)]);
    }
  }
  function scanPics() {
    const all = document.querySelectorAll(PIC);
    if (all.length === picN) return; picN = all.length;
    for (const el of all) if (!pid.has(el)) {
      pid.set(el, pinfo.length);
      const kind = el.classList.contains('stage-still') ? 'stage-still' : el.classList.contains('slot') ? 'slot' : el.closest('.still') ? 'still'
        : el.closest('.mt-step') ? 'step' : el.classList.contains('kc-live') ? 'kc-live' : 'kc-pic';
      pinfo.push({ kind, src: (el.getAttribute('src') || '').split('/').pop(), sec: secOf(el), nw: el.naturalWidth || el.width || 0, nh: el.naturalHeight || el.height || 0 });
    }
  }
  function pictures(out) {
    scanPics(); const vw = W(), vh = H();
    for (const [el, i] of pid) {
      if (!el.isConnected || !el.getClientRects().length) continue;
      const r = el.getBoundingClientRect(); if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw || r.width < 1 || r.height < 1) continue;
      const e = eff(el); if (!e.vis || e.op < 0.02) continue;
      let f = el.tagName === 'CANVAS' ? canvasInk(el) : inkOf(el);
      const loaded = el.tagName === 'CANVAS' ? 1 : el.complete && el.naturalWidth ? 1 : 0;
      if (!f) { out.push([i, r1(r.left), r1(r.top), r1(r.right), r1(r.bottom), 0, 0, 0, 0, r3(e.op), e.clip ? e.clip.map(r1) : 0, loaded, 0]); continue; }
      const c = contentBox(el, r), cw = c[2] - c[0], ch = c[3] - c[1];
      const nat = el.tagName === 'CANVAS' ? el.width : el.naturalWidth;
      out.push([i, r1(r.left), r1(r.top), r1(r.right), r1(r.bottom), r1(c[0] + f[0] * cw), r1(c[1] + f[1] * ch), r1(c[0] + f[2] * cw), r1(c[1] + f[3] * ch),
        r3(e.op), e.clip ? e.clip.map(r1) : 0, loaded, nat && cw ? r3(nat / cw) : 0]);
    }
  }
  function chrome(out) {
    CHROME.forEach((s, i) => { const el = document.querySelector(s); if (!el || !el.getClientRects().length) return;
      const e = eff(el); if (!e.vis || e.op < 0.02) return; const r = el.getBoundingClientRect();
      if (r.bottom <= 0 || r.top >= H() || r.width < 1) return;
      out.push([i, r1(r.left), r1(r.top), r1(r.right), r1(r.bottom), r3(e.op)]); });
  }
  function card() {
    const c = document.querySelector('.kitcard'); if (!c || !c.getClientRects().length) return null;
    const r = c.getBoundingClientRect(); if (r.bottom < 0 || r.top > H()) return [r1(r.left), r1(r.top), r1(r.right), r1(r.bottom)];
    const e = eff(c), cs = getComputedStyle(c), be = getComputedStyle(c, '::before');
    const pseudo = be.content && be.content !== 'none' && be.content !== 'normal';
    const bt = parseFloat(cs.getPropertyValue('--body-top')) || 0;
    // the card's body: its ::before (story desktop: under the picture, its own opacity) or the card's own background
    const bodyTop = pseudo ? r.top + (parseFloat(be.top) || bt) : r.top, bodyOp = pseudo ? e.op * (+be.opacity) : (cs.backgroundImage !== 'none' || !/rgba?\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor) ? e.op : 0);
    return [r1(r.left), r1(r.top), r1(r.right), r1(r.bottom), r1(bodyTop), r3(bodyOp), r3(e.op)];
  }
  function canvasRec() {
    const c = document.getElementById('seq'); if (!c) return null;
    const cs = getComputedStyle(c), r = c.getBoundingClientRect();
    const shown = cs.display !== 'none' && cs.visibility !== 'hidden' ? +cs.opacity : 0;
    return [r1(r.left), r1(r.top), r1(r.width), r1(r.height), r3(shown), r1(parseFloat(c.style.width) || r.width), r1(parseFloat(c.style.height) || r.height), c.width, c.height];
  }
  const CLS = ['js', 'story', 'flow', 'no-gl', 'mt-cards', 'mt-cards0', 'mt-land'];
  function step() {
    cache = new Map(); if (!scanned) scanTexts();
    const s = { y: Math.round(scrollY) };
    s.cls = CLS.reduce((a, c, i) => a | (document.documentElement.classList.contains(c) ? 1 << i : 0), 0);
    if (typeof window.__mtP === 'number') s.p = r3(window.__mtP);
    if (typeof window.__mtCards === 'number') s.cards = r3(window.__mtCards);
    const T0 = performance.now();
    try { if (window.__seq) { const q = window.__seq(); s.pos = r3(q.pos); s.mode = q.mode; s.sop = q.opacity;
      const ss = q.sceneState; if (ss) s.ss = { dp: ss.drawn, q: ss.quality, pr: ss.pixelRatio, w: ss.width, h: ss.height, kits: ss.kits, n: ss.renders,
        edge: ss.edge, aabb: ss.aabb, clash: ss.clash, box: ss.box && ss.box.o, B: ss.B && ss.B.o, P: ss.P && ss.P.o, dive: ss.dive, inside: ss.inside, round: ss.round }; } } catch (e) { s.err = String(e).slice(0, 80); }
    const T = [performance.now()]; if (window.__pmProfile) s.tseq = Math.round((T[0] - T0) * 100) / 100;
    s.cv = canvasRec();
    if (window.__geoRead) s.g = window.__geoRead('main');
    T.push(performance.now());
    s.ch = []; chrome(s.ch);
    s.tx = []; texts(s.tx);
    T.push(performance.now());
    s.pc = []; pictures(s.pc);
    T.push(performance.now());
    s.card = card();
    T.push(performance.now());
    if (window.__pmProfile) s.tm = T.slice(1).map((t, i) => Math.round((t - T[i]) * 100) / 100);
    const sw = document.documentElement.scrollWidth; if (sw > innerWidth + 1) s.sw = sw;
    s.docH = document.documentElement.scrollHeight;
    return s;
  }
  // a frame: a pixel's worth of change first, so the next frame comes at once (an unchanged page gets frames at 60 Hz only)
  let ticker = null, tk = 0, wasHidden = false;
  const frame = () => new Promise(r => {
    if (!ticker) { ticker = document.createElement('div'); ticker.setAttribute('aria-hidden', 'true');
      ticker.style.cssText = 'position:fixed;left:0;top:0;width:1px;height:1px;background:#000;opacity:.01;pointer-events:none;z-index:-1'; document.body.appendChild(ticker); }
    ticker.style.transform = 'translateX(' + (tk++ & 1) + 'px)'; requestAnimationFrame(() => r()); });
  async function sweep(ys, settle) {
    // settle: the frames to wait. The scroll event comes in the first frame after scrollTo and its handlers' frame
    // callbacks run in that frame after ours (the motion layer's, then the story's tick, which draws): the second is enough
    const out = [];
    for (const y of ys) {
      const t0 = performance.now(); scrollTo(0, y);
      for (let i = 0; i < settle; i++) await frame();
      // a live scene that draws now (shown, not stepped aside for the step cards): wait for a frame drawn after this scroll
      const cv = document.getElementById('seq'), de = document.documentElement;
      const shownNow = de.classList.contains('story') && !de.classList.contains('mt-cards0') && !!cv && cv.style.opacity !== '0';
      if (window.__geo && window.__geo.main && shownNow) {
        for (let k = 0; k < 4 && window.__geo.main.t < t0; k++) await frame();
        // coming back after the step cards: the engine draws it at once as it shows it, with that frame's cards value (the
        // pair still away); the pair's real state is in the next drawn frame
        if (wasHidden) { const tA = window.__geo.main.t; for (let k = 0; k < 6 && window.__geo.main.t <= tA; k++) await frame(); }
      }
      wasHidden = !shownNow;
      const t1 = performance.now(), rec = step(); if (window.__pmProfile) rec.tm.unshift(Math.round((t1 - t0) * 100) / 100); out.push(rec);
    }
    return out;
  }
  function statics() {   // the page's blocks in page coordinates, the opening's band, the step cards' layout
    const pg = el => { if (!el || !el.getClientRects().length) return null; const r = el.getBoundingClientRect(); return [r1(r.left), r1(r.top + scrollY), r1(r.right), r1(r.bottom + scrollY)]; };
    const q = s => document.querySelector(s), blocks = {};
    for (const s of ['#open', '#meet', '#why', '#inside', '#feel', '#protocol', '.mt-prep', '#offer', '.kitcard', '#specialists', '.related', '.foot']) blocks[s.replace(/^[#.]/, '')] = pg(q(s));
    // per screen: its heading group (heading, kicker, tagline, badges), its stage (a phone's block) and its body text
    const heads = {}, stages = {}, copies = {}, un = (a, b) => !a ? b : !b ? a : [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])];
    // (by document order: what comes before the stage is the heading group, what comes after it the body)
    for (const sec of document.querySelectorAll('main > section[id]')) {
      const stg = sec.querySelector('.stage'); let h = null, c = null;
      for (const e of sec.querySelectorAll('h1, h2, h3, p, li, .btn, .badges, .chip')) {
        if (e.closest('.kitcard, .mt-prep') || (e.parentElement && e.parentElement.closest('p, li, .badges, .btn'))) continue;
        const r = pg(e); if (!r || r[3] - r[1] < 1) continue;
        if (!stg) { h = un(h, r); continue; }
        if (stg.compareDocumentPosition(e) & Node.DOCUMENT_POSITION_PRECEDING) h = un(h, r); else c = un(c, r);
      }
      heads[sec.id] = h; stages[sec.id] = pg(stg); copies[sec.id] = c;
    }
    const steps = Array.prototype.map.call(document.querySelectorAll('.mt-step'), li => ({ fig: pg(li.querySelector('figure')), text: pg(li.querySelector('.mt-st')) }));
    // the step cards as a sideways scroller (a phone: overflow-x): how many stand on the screen without scrolling it
    const ms = q('.mt-steps'), stepsScroll = ms && ms.scrollWidth > ms.clientWidth + 1 ? { scrollW: ms.scrollWidth, clientW: ms.clientWidth, onScreen: steps.filter(s => s.fig && s.fig[0] >= -1 && s.fig[2] <= innerWidth + 1).length } : null;
    return { blocks, heads, stages, copies, steps, stepsScroll, band: window.__mtBand || null, docH: document.documentElement.scrollHeight, W: innerWidth, H: innerHeight, dpr: devicePixelRatio,
      cls: CLS.filter(c => document.documentElement.classList.contains(c)), scrollW: document.documentElement.scrollWidth };
  }
  window.__pm = { step, sweep, statics, tables: () => ({ texts: tinfo, pics: pinfo, chrome: CHROME, keys: window.__geoKeys ? window.__geoKeys() : [] }) };
};
const INIT = `(${PROBE.toString()})();
(() => {   // no transitions or animations (a step is read at once), every picture loaded (its drawn part is measured)
  const st = document.createElement('style');
  // and nothing that only costs paint (blur, shadows, the haze): a probe reads geometry, never pixels of the page
  st.textContent = '*,*::before,*::after{transition:none!important;animation:none!important;backdrop-filter:none!important;'
    + '-webkit-backdrop-filter:none!important;filter:none!important;box-shadow:none!important;text-shadow:none!important}'
    + 'html{scroll-behavior:auto!important}.mt-haze,.bg,.plate,.cells{visibility:hidden!important}';
  const add = () => { (document.head || document.documentElement).appendChild(st);
    document.querySelectorAll('img[loading="lazy"]').forEach(i => { i.loading = 'eager'; }); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
})();`;

// ---------------------------------------------------------------------------------------------------------------------
// one screen: load, wait until ready, sweep
async function probeViewport(browser, vp, page, opts) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: vp.dpr, isMobile: vp.touch, hasTouch: vp.touch,
    reducedMotion: 'no-preference' });
  const pg = await ctx.newPage(), log = { errs: [], fails: [] };
  pg.on('pageerror', e => log.errs.push('PAGEERROR ' + e.message.slice(0, 160)));
  pg.on('console', m => { if (m.type() === 'error') log.errs.push(m.text().slice(0, 160)); });
  pg.on('requestfailed', r => log.fails.push(r.url().slice(0, 120) + ' ' + ((r.failure() || {}).errorText || '')));
  await ctx.addInitScript(INIT);
  const FONT_CSS = "@font-face{font-family:'Rubik';src:url(https://fonts.gstatic.com/local/0.ttf) format('truetype');font-weight:100 900;font-display:block}";
  const CORS = { 'access-control-allow-origin': '*' };
  await ctx.route('**/*', r => {
    const u = new URL(r.request().url());
    if (u.host === 'fonts.googleapis.com') return r.fulfill({ status: 200, contentType: 'text/css', body: FONT_CSS, headers: CORS });
    if (u.host === 'fonts.gstatic.com') return fs.existsSync(opts.font) ? r.fulfill({ path: opts.font, contentType: 'font/ttf', headers: CORS }) : r.fulfill({ status: 404, body: '' });
    if (u.host === 'cdn.jsdelivr.net' && u.pathname.startsWith('/npm/three@0.160.0/')) {
      if (u.pathname.endsWith('/three.real.js')) return r.fulfill({ path: opts.three, contentType: 'application/javascript', headers: CORS });
      if (u.pathname.endsWith('/three.module.min.js')) return r.fulfill(vp.kind === 'live' ? { path: opts.nodraw, contentType: 'application/javascript', headers: CORS }
        : { path: opts.three, contentType: 'application/javascript', headers: CORS });
      return r.fulfill({ status: 404, body: '' });
    }
    if (u.host === 'pagemap.test') {
      const rel = decodeURIComponent(u.pathname.slice(1));
      if (!rel) return r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: vp.kind === 'nojs' ? page.htmlNoJs : page.html });
      const f = path.join(opts.files, rel);
      const T = { '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.js': 'application/javascript', '.json': 'application/json' };
      return f.startsWith(path.resolve(opts.files)) && fs.existsSync(f) && fs.statSync(f).isFile() ? r.fulfill({ path: f, contentType: T[path.extname(f)] || 'application/octet-stream' }) : r.fulfill({ status: 404, body: '' });
    }
    return r.abort();   // nothing else: no network
  });
  const t0 = Date.now();
  await pg.goto('https://pagemap.test/', { waitUntil: 'load', timeout: 90000 });
  if (vp.kind !== 'nojs') await pg.waitForFunction(() => window.__seq && (document.documentElement.classList.contains('story') || document.documentElement.classList.contains('no-gl')),
    null, { timeout: 60000 }).catch(() => log.errs.push('READY TIMEOUT'));
  await pg.waitForFunction(() => document.fonts.status === 'loaded' && Array.prototype.every.call(document.images, i => i.complete || !i.getAttribute('src')), null, { timeout: 30000 })
    .catch(() => log.errs.push('IMAGES TIMEOUT'));
  if (vp.kind === 'live') await pg.waitForFunction(() => { try { const s = window.__seq().sceneState; return !s || s.loaded >= 4; } catch (e) { return true; } }, null, { timeout: 30000 })
    .catch(() => log.errs.push('TEXTURES TIMEOUT'));
  await pg.evaluate(async () => { scrollTo(0, 0); for (let i = 0; i < 30; i++) await new Promise(r => requestAnimationFrame(r)); });
  await pg.waitForTimeout(400);
  const ready = Date.now() - t0;
  const statics = await pg.evaluate(() => window.__pm.statics());
  const settle = opts.settle || (vp.kind === 'nojs' ? 1 : 2), dy = opts.step, steps = [];
  if (opts.profile) await pg.evaluate(() => { window.__pmProfile = true; });
  let y = 0, maxY = statics.docH - vp.h;
  if (opts.ys) { steps.push(...await pg.evaluate(([ys, settle]) => window.__pm.sweep(ys, settle), [opts.ys, settle])); y = Infinity; }
  while (y <= maxY + dy - 1) {
    const ys = []; for (let k = 0; k < 60 && y <= maxY + dy - 1; k++, y += dy) ys.push(Math.min(y, maxY));
    const got = await pg.evaluate(([ys, settle]) => window.__pm.sweep(ys, settle), [ys, settle]);
    steps.push(...got);
    const last = got[got.length - 1]; if (last && last.docH) maxY = last.docH - vp.h;
  }
  const end = await pg.evaluate(() => ({ statics: window.__pm.statics(), tables: window.__pm.tables(), geo: window.__geo ? { renders: window.__geo.renders, kits: window.__geo.kits, envs: window.__geo.envs, kit: window.__geoRead('kit') } : null }));
  await ctx.close();
  return { vp, ready, ms: Date.now() - t0, statics, end, steps, log };
}

// ---------------------------------------------------------------------------------------------------------------------
module.exports = { PROBE, INIT, parseVp, SETS, probeViewport, analyse: (...a) => analyse(...a), readRaw: (...a) => readRaw(...a), TH: () => TH, PAGES: () => PAGES, RULE_CLS: () => RULE_CLS };

async function main() {
  const fromRaw = opt('--from-raw');
  const out = path.resolve(opt('--out', '.'));
  if (fromRaw) return analyseAll(readRaw(fromRaw), out, path.resolve(fromRaw));
  if (opt('--spot')) return spot(opt('--spot'), POS[0], POS[1], out);
  if (POS.length < 2) { console.error('usage: node qa/pagemap.cjs <page.html> <files dir> [--viewports all|key|<list>] [--out dir] [--raw dir]'); process.exit(2); }
  const [pageFile, files] = POS;
  const { chromium } = require('playwright');
  const html0 = fs.readFileSync(pageFile, 'utf8');
  const shell = b => '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>' + b + '</body></html>';
  const page = { file: path.resolve(pageFile), md5: crypto.createHash('md5').update(html0).digest('hex'), html: shell(html0),
    htmlNoJs: shell(html0.replace(/<script\b[\s\S]*?<\/script>/gi, '')), slug: opt('--slug', path.basename(pageFile).replace(/-live\.html$|\.html$/, '')) };
  const three = threeFile(), font = fontFile();
  const opts = { files: path.resolve(files), three, nodraw: path.join(__dirname, 'three-nodraw.mjs'), font, step: +opt('--step', 10) };
  page.build = provenance(page, opts);
  const vlist = opt('--viewports', 'all'); const vps = (SETS[vlist] || vlist.split(',')).map(parseVp);
  const rawDir = opt('--raw') ? path.resolve(opt('--raw')) : null; if (rawDir) fs.mkdirSync(rawDir, { recursive: true });
  const runs = [], T0 = Date.now();
  let live = null, nogl = null;
  for (const vp of vps) {
    const b = vp.kind === 'nogl' ? (nogl = nogl || await chromium.launch({ args: ['--disable-3d-apis', '--disable-frame-rate-limit', '--disable-gpu-vsync'] }))
      : (live = live || await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-frame-rate-limit', '--disable-gpu-vsync'] }));
    const run = await probeViewport(b, vp, page, opts);
    run.page = { file: page.file, md5: page.md5, slug: page.slug, build: page.build };
    console.log(`${vp.id}: ${run.steps.length} steps in ${(run.ms / 1000).toFixed(1)} s (ready ${(run.ready / 1000).toFixed(1)} s), errors ${run.log.errs.length}`);
    if (rawDir) fs.writeFileSync(path.join(rawDir, vp.id + '.json.gz'), zlib.gzipSync(JSON.stringify(run)));
    runs.push(run);
  }
  if (live) await live.close(); if (nogl) await nogl.close();
  console.log(`probe: ${vps.length} screens in ${((Date.now() - T0) / 1000).toFixed(1)} s`);
  analyseAll(runs, out, rawDir);
}
function readRaw(dir) {
  return fs.readdirSync(dir).filter(f => f.endsWith('.json.gz') && !f.endsWith('.track.json.gz')).sort().map(f => JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(dir, f)))));
}
// the files the probe needs, or a stop: without three.js nothing is measured, and a fallback font moves every line of the
// page (the map's y's, the holds, the runs: 25 px on this page), so a missing one is an error, never a silent 404
const md5f = f => { try { return crypto.createHash('md5').update(fs.readFileSync(f)).digest('hex'); } catch (e) { return null; } };
function threeFile() {
  let three = opt('--three', process.env.THREE);
  if (!three) try { three = require.resolve('three/build/three.module.min.js'); } catch (e) { three = ''; }
  if (!three || !fs.existsSync(three)) { console.error('three.module.min.js (three@0.160.0) not found: --three <file>, $THREE, or NODE_PATH with three installed (npm i --no-save three@0.160.0)'); process.exit(2); }
  return path.resolve(three);
}
function fontFile() {
  const dir = opt('--fonts', process.env.FONTDIR || path.join(__dirname, 'fonts')), f = path.join(dir, 'Rubik[wght].ttf');
  if (!fs.existsSync(f)) { console.error('the page\'s font Rubik[wght].ttf (the variable Rubik, fonts.google.com, OFL) not found in ' + dir + ': qa/fonts/, --fonts <dir> or $FONTDIR'); process.exit(2); }
  return f;
}
// where the build came from: the repository's HEAD, the last commit of the page's sources, the build's command, the key
// frames its pictures were cut from (md5 of their list), the probe's own files
function provenance(page, opts) {
  const cfg = PAGES[page.slug] || {}, repo = path.resolve(__dirname, '..', '..', '..'), git = args => { try { return require('child_process').execFileSync('git', args, { cwd: repo, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); } catch (e) { return null; } };
  const b = { file: path.basename(page.file), md5: page.md5, rev: git(['rev-parse', '--short', 'HEAD']), sourcesRev: cfg.sources ? git(['log', '-1', '--format=%h', '--', ...cfg.sources]) : null,
    sources: cfg.sources || null, cmd: opt('--build-cmd', cfg.build || null) };
  const keys = opt('--keys'); if (keys && fs.existsSync(keys)) { const fl = fs.readdirSync(keys).filter(f => !f.startsWith('.')).sort(), lines = fl.map(f => f + ' ' + md5f(path.join(keys, f)));
    b.keys = { dir: path.basename(keys), n: fl.length, md5: crypto.createHash('md5').update(lines.join('\n')).digest('hex') }; }
  b.probe = { font: md5f(opts.font), three: md5f(opts.three), nodraw: md5f(opts.nodraw) };
  return b;
}

// ---------------------------------------------------------------------------------------------------------------------
// the checks, from the numbers alone. The thresholds were calibrated on the builds 7fa15f8 and fd91489 (their defects
// found by the pixel sweeps of 05–06/11) and on the current build: every known defect flagged, the current build clean
// but for the accepted design fades, which are listed apart (design), never as flags
const TH = {
  op: 0.05,                   // shown: opacity (the material's × the canvas's) at least this
  cutPx: 2,                   // past an edge by more than this many px (hard); within touchPx of it: touching (the silhouette's
  touchPx: 3,                 // edge on the canvas's edge reads as cut flat)
  bandDim: 0.25,              // a straight fade band dims the product by more than this
  cutResid: 0.25,             // a hard cut: more than this of the product left at the edge after the fades (1 − their weights)
  roundW: 0.75,               // the round fade (the dive) at least this: only round lines, no straight one
  softFrac: 0.15, softPx: 12, // a soft straight band across the product: past the edge by ≥ this share of its size and px
  overPx: 2,                  // under a panel or text: overlapping by at least this in both directions
  twoH: 20, twoArea: 1000,    // a product on the screen: at least this tall (px) and this large (px²), not under the header
  ghost: [0.05, 0.95], ghostArea: 50,   // a see-through solid part: its opacity in this range, overlapping ≥ this px²
  ghostPart: 400,             // … and at least this large (px²): a smaller part fading is listed apart (design)
  popDy: 30, popSize: 1.38, popMove: 1.5,   // a pop: per 30 px of scroll the size × more than this, or the middle moved > this × size
  popDy2: 60, popSize2: 1.75, // … and per 60 px: × more than this (a pop spread over two steps; the current build ≤ 1.57, the fd91489 dive 1.80)
  popHidden: 0.3,             // appearing or vanishing: a pop unless a nearer solid object covers at least this share of it
  frac: 0.002,                // a run in progress: the position's fraction in (frac, 1 − frac)
  emptyPx: 60,                // an empty stage for less scroll than this is a handover (design), not a flag
  dim: 0.4,                   // the dive's light or the product, whichever is stronger, at least this (else a dark frame)
  runMin: { desk: 500, flow: 300 },   // the scroll a run needs at least (px)
  hd: 0.95,                   // HD: the pixels it has ≥ this × CSS px × DPR (≤ 2 on a desktop, the screen's on a phone), as verify-hd.cjs
};
// per page: the scene's top-level objects by index (scene.children) and the parts that are its body (for its size: the
// cap lifting or the applicator coming on is not the vial growing); userData.j −1: the box's faces
const PAGES = {
  'mitotech-cell-booster': {
    title: 'MITOTECH CELL BOOSTER', link: 'https://claude.ai/artifact/G3tdcwusRsVdw4E5HeGM5s',
    objects: { 1: 'box', 2: 'k1', 3: 'k2', 4: 'k3', 5: 'k4', 6: 'k5', 7: 'k6', 8: 'k7', 9: 'k8', 10: 'B', 11: 'P' },
    body: [-1, 0, 6, 7],
    parts: { '-1': 'face', 0: 'glass', 1: 'cake', 2: 'liquid', 3: 'stopper', 4: 'ring', 5: 'cap', 6: 'glass', 7: 'label', 8: 'applicator', 9: 'applicator', 10: 'tip' },
    // the page's sources in the repository (their last commit goes into build.sourcesRev) and how it is built
    sources: ['site/proto/scenes/mitotech-cell-booster.js', 'site/proto/story-v2-motion.js', 'site/proto/story-v2.css', 'site/proto/engine/story.js',
      'site/proto/vtech-live-template.html', 'site/proto/build-vtech.py', 'site/proto/story_content.py'],
    build: 'cd site/proto && python3 build-vtech.py --product mitotech-cell-booster --scene --files <dir> --keys <keys> --links artifact; rm -rf __pycache__',
    pictures: 'step1–5, m1–m5, still, kit — `build-vtech.py` режет их из ключевых кадров сцены (`scenes/render-keys.cjs` → `--keys <dir>`: v0-open … v6-kit, step1–5)',
    texts: 'из `site/proto/story_content.py` (MITOTECH: `state/mitotech/canon-v2.md`, кадры каталога 941:2, 941:21, 956:2, 956:23) и UI-строки 12 страниц; строки, которых нет дословно у заказчика, — `state/mitotech/texts-for-approval.md`',
    textBlocks: ['open', 'meet', 'why', 'inside', 'feel', 'protocol', 'prep', 'step1', 'step2', 'step3', 'step4', 'step5', 'offer', 'kitcard'],   // the product's own blocks (the map lists these; the specialists, «see also», the footer are the site's)
    questions: { file: '../../../state/mitotech/texts-for-approval.md', section: 6, short: '§6: цвет раствора, аппликаторы в наборе, заголовок оффера, янтарь — стекло или жидкость',
      extra: ['§4: бейдж линейки `MITOTECH` — подтвердить имя (на коробке «MITOTECH®», в каталоге без ®)'] },
    // what waits for a decision besides what the checks find (the checks' own items are added from the data)
    pending: ['«ок» заказчика на образце карты (эта страница) — открывает карты остальных 12 страниц (PLAN: «карты остальных 12 — после «ок» на образце»)'],
    // a desktop (html.story): the poses held and the runs between them
    holds: ['открытие: имя над набором (коробка и 8 флаконов, R15), набор в свободной полосе экрана', 'S1 #meet: набор слева, текст справа',
      'S2 #why: коробка одна, отступила вглубь', 'S3 #inside: пара (порошок и бустер) крупно', 'S4 #feel: пара мала и низко',
      'S5 #protocol: приготовление R7 (пара); далее карточки шагов 01–05 (сцена скрыта)', 'оффер: набор на карточке «מה באריזה» (3D, затем картинка карточки)'],
    runs: ['камера въезжает в набор (открытие → S1)', 'восемь флаконов уходят за коробку, коробка отступает', 'пара выходит из-за левого края коробки и подходит к камере',
      'нырок в янтарь бустера и обратно (янтарный свет, круглое затухание)', 'приготовление R7: колпачки, пробки, переливание, пробка, аппликатор',
      'набор собирается; компьютер: летит на карточку «מה באריזה»; телефон: уходит вверх, карточка показывает картинку'],
    // a phone or tablet (html.flow): each block has its stage; run k plays in block k as the block comes up the screen
    flow: ['#open: наезд открытия (прогон 0), к концу блока поза 1 (набор)', '#meet: набор (поза 1) → прогон 1 → коробка одна (поза 2)',
      '#why: коробка (поза 2) → прогон 2 → пара крупно (поза 3)', '#inside: пара (поза 3) → прогон 3, нырок → пара (поза 4)',
      '#feel: пара (поза 4) → прогон 4, приготовление R7 → поза 5', '#protocol: начало прогона 5 (поза 5.58, пара готова) → прогон 5, набор собирается → набор (поза 6) у заголовка «אופן השימוש»; дальше карточки шагов (боковая лента) и картинка набора на карточке'],
  },
};
// the checks whose flag is a rule for the owner to decide, not a pixel defect on a frame (listed apart from the flags)
const RULE_CLS = { RUN_SPAN: 1 };
const CLEAR = /glass|liq|clr|thr|water|gel/;   // material keys of see-through matter (glass, liquids): never a ghost by itself
const CHROME_NAME = ['header', 'dock', 'bar'];
const isect = (a, b) => [Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.min(a[2], b[2]), Math.min(a[3], b[3])];
const area = r => r && r[2] > r[0] && r[3] > r[1] ? (r[2] - r[0]) * (r[3] - r[1]) : 0;
const uni = (a, b) => a ? [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])] : b.slice();
const inside = (a, b, t) => a[0] - t <= b[0] && a[1] - t <= b[1] && b[2] <= a[2] + t && b[3] <= a[3] + t;
const fr = v => v - Math.floor(v);
const R0 = v => Math.round(v), R1 = v => Math.round(v * 10) / 10, R2 = v => Math.round(v * 100) / 100;
const box4 = b => b.map(R0);

// what the scene's fades leave of the product at a screen point (0 … 1), from the passes' uniforms as drawn: the round
// fade (HEAD: an ellipse inscribed in uR), the old vignette (7fa15f8, fd91489: a band along the canvas's own edges) and the
// edge strips (uE: left, bottom, right, top, each over uFe of the canvas from uR's edge)
const smo = (a, b, v) => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
function fadeAt(d, x, y, part) {   // part: 'round' or 'straight' (the vignette and the strips) alone; default both
  const s = d.s, f = s.g && s.g.fade, cv = s.cv; if (!f || !cv || !cv[7] || !cv[8]) return 1;
  const bw = cv[7], bh = cv[8], kx = cv[2] / bw, ky = cv[3] / bh, gx = (x - cv[0]) / kx, gy = bh - (y - cv[1]) / ky;
  const m = Math.min(f.res ? f.res[0] : bw, f.res ? f.res[1] : bh);
  let base = 1;
  if (f.round && f.r && part !== 'straight') { const cx = (f.r[0] + f.r[2]) / 2, cy = (f.r[1] + f.r[3]) / 2;
    base = 1 - smo(f.f, 1, Math.hypot(2 * (gx - cx) / Math.max(1, f.r[2] - f.r[0]), 2 * (gy - cy) / Math.max(1, f.r[3] - f.r[1]))); }
  else if (!f.round && part !== 'round') { const v = smo(0, f.f * m, Math.min(gx, bw - gx)) * smo(0, f.f * m, Math.min(gy, bh - gy)); base = v * v; }
  let a = 1 + (base - 1) * f.w;
  if (f.e && f.r && part !== 'round') { const e = [gx - f.r[0], gy - f.r[1], f.r[2] - gx, f.r[3] - gy];
    for (let i = 0; i < 4; i++) { const t = smo(0, f.fe * m, e[i]); a *= 1 + (t * t - 1) * f.e[i]; } }
  return Math.max(0, Math.min(1, a));
}
function fadeMid(d) {   // the fades' middle on the screen (the round fade's centre, else the canvas's)
  const s = d.s, f = s.g && s.g.fade, cv = s.cv;
  if (f && f.r && cv && cv[7]) { const kx = cv[2] / cv[7], ky = cv[3] / cv[8]; return [cv[0] + (f.r[0] + f.r[2]) / 2 * kx, cv[1] + (cv[8] - (f.r[1] + f.r[3]) / 2) * ky]; }
  return cv ? [cv[0] + cv[2] / 2, cv[1] + cv[3] / 2] : [0, 0];
}
function fadeIn(d, r, part) {   // the most the fades leave anywhere in screen rect r: at its point nearest the fades' middle
  const s = d.s, f = s.g && s.g.fade, cv = s.cv; if (!f || !cv || !cv[7]) return 1;
  const [cx, cy] = fadeMid(d);
  return fadeAt(d, Math.min(r[2], Math.max(r[0], cx)), Math.min(r[3], Math.max(r[1], cy)), part);
}
function derive(run) {   // per step: the mode, the canvas on the screen, every mesh on the screen, the objects, the products in view
  const vp = run.vp, W = vp.w, H = vp.h, T = run.end.tables, keys = T.keys || [], cfg = PAGES[run.page.slug] || { objects: {}, body: null, parts: {} };
  const clear = keys.map(k => CLEAR.test(k)), view = [0, 0, W, H], BL = (run.end.statics || {}).blocks || {};
  const name = t => cfg.objects[t] || 'o' + t, part = (m) => cfg.parts[m.j] || (keys[m.key] || '').replace(/^mtcb-/, '').replace(/[0-9.,]+.*$/, '') || 'part';
  const out = run.steps.map(s => {
    const d = { y: s.y, s, mode: s.cls & 2 ? (s.cls & 4 ? 'flow' : 'desk') : 'still' };
    const cv = s.cv; d.cvop = cv ? cv[4] : 0;
    d.C = cv && cv[2] > 0 ? [cv[0], cv[1], cv[0] + cv[2], cv[1] + cv[3]] : null;
    d.V = d.C ? isect(d.C, view) : null;
    d.dp = d.mode === 'flow' && s.ss && s.ss.dp != null ? s.ss.dp : (s.pos != null ? s.pos : s.p);   // older builds draw the engine's position
    d.inView = !!(d.C && area(d.V) > 0 && d.cvop > 0);
    d.blk = null;   // a phone or tablet: the block holding the canvas (its centre, in page coordinates)
    if (d.mode === 'flow' && d.C) { const pc = (d.C[1] + d.C[3]) / 2 + s.y; for (const [k, b] of Object.entries(BL)) if (b && pc >= b[1] && pc < b[3]) { d.blk = k; break; } }
    d.running = d.mode === 'desk' && d.dp != null && d.dp < 6 && fr(d.dp) > TH.frac && fr(d.dp) < 1 - TH.frac;
    d.story = d.mode === 'desk' && d.dp != null && d.dp < 6;   // a desktop's story in progress: the product always on the screen
    const hd = s.ch.find(c => c[0] === 0), bar = s.ch.find(c => c[0] === 2);
    d.top = hd && hd[5] > 0.5 ? Math.max(0, hd[4]) : 0; d.foot = bar && bar[5] > 0.5 && bar[2] < H ? Math.min(H, bar[2]) : H;
    d.seen = [0, d.top, W, d.foot];   // what is not under the header or the phone's bar
    d.meshes = []; d.objs = {};
    if (s.g && d.C && d.cvop > 0 && s.g.W > 0) {
      const kx = cv[2] / s.g.W, ky = cv[3] / s.g.H;
      for (const it of s.g.items) {
        const [top, key, j, op, fl, x0, y0, x1, y1, d0, d1] = it;
        const m = { top, obj: name(top), key, j, op, fl, ope: op * d.cvop, clear: clear[key], d0, d1, near: !!(fl & 4),
          b: [cv[0] + x0 * kx, cv[1] + y0 * ky, cv[0] + x1 * kx, cv[1] + y1 * ky] };
        m.part = part(m); m.body = !cfg.body || cfg.body.includes(j);
        m.cb = isect(m.b, d.V); m.vis = m.ope >= TH.op && area(m.cb) > 0;
        d.meshes.push(m);
        const o = d.objs[m.obj] || (d.objs[m.obj] = { name: m.obj, b: null, body: null, cb: null, op: 0, solidOp: 0, d0: Infinity, near: false, n: 0, proxied: true });
        if (m.ope >= TH.op) { o.b = uni(o.b, m.b); o.op = Math.max(o.op, m.ope); o.d0 = Math.min(o.d0, d0); o.near = o.near || m.near; o.n++;
          if (m.body) o.body = uni(o.body, m.b);
          if (!m.clear) { o.solidOp = Math.max(o.solidOp, m.op); if (m.op < 0.999 && !(fl & 2)) o.proxied = false; }
          if (m.vis) o.cb = uni(o.cb, m.cb); }
      }
    }
    // the products in view: the 3D (its visible meshes, or the amber glow) and each picture's drawn part
    d.pres = [];
    if (d.cvop >= TH.op && d.V) {
      let u = null; for (const m of d.meshes) if (m.vis) { const q = isect(m.cb, d.seen); if (area(q) > 0) u = uni(u, q); }
      const g = s.g && s.g.glow >= TH.op;
      if ((u && u[3] - u[1] >= TH.twoH && area(u) >= TH.twoArea) || g) d.pres.push({ what: '3d', b: u || d.V, glow: !!g });
    }
    d.pics = [];
    for (const p of s.pc) {
      const [pid, l, t, r, b, il, it, ir, ib, op, clip] = p, info = T.pics[pid] || { kind: '?' };
      if (!(ir > il)) continue;
      let ink = isect([il, it, ir, ib], view); if (clip) ink = isect(ink, clip);
      const shown = isect(ink, d.seen);
      const pic = { pid, kind: info.kind, src: info.src, sec: info.sec, op, el: [l, t, r, b], ink, shown, nat: p[12] };
      d.pics.push(pic);
      if (op >= TH.op && shown[3] - shown[1] >= TH.twoH && area(shown) >= TH.twoArea) d.pres.push({ what: info.kind === 'step' ? 'steps' : info.kind + ':' + (info.src || pid), pic });
    }
    return d;
  });
  // a phone or tablet: a run plays while its block's pose moves with the scroll (a still pose scrolling with its block
  // is the page; run 5's start pose is 5.58, held until its block is up)
  out.forEach((d, i) => { if (d.mode !== 'flow') return;
    // (the pose drawn: sceneState.drawn; a build before it (no flowP) remapped the run inside the scene, so there the pose
    // itself is compared: the objects' outline in the frame and the pair's state)
    const pageTop = q => q.C ? q.C[1] + q.y : NaN;   // the block holding the canvas: its place in the page
    const sig = q => { const ss = q.s.ss; return ss ? [...(ss.aabb || [0, 0, 0, 0]), ss.box || 0, ss.B || 0, ss.P || 0, ss.dive || 0, ss.inside || 0] : null; };
    const moved = (q, r) => { if (r.s.ss && r.s.ss.dp != null && q.s.ss && q.s.ss.dp != null) return Math.abs(q.dp - r.dp) > 1e-4;
      const A = sig(q), B = sig(r); if (!A || !B) return false; return A.some((v, k) => Math.abs(v - B[k]) > (k < 4 ? 4 : 0.005)); };
    const a = out[i - 1], b = out[i + 1], mv = q => q && q.mode === 'flow' && q.inView && Math.abs(pageTop(q) - pageTop(d)) < 1 && moved(q, d);
    d.running = d.inView && d.dp != null && d.dp < 6 && (mv(a) || mv(b)); });
  return out;
}

function analyse(run) {
  const vp = run.vp, W = vp.w, H = vp.h, dy = run.steps.length > 1 ? run.steps[1].y - run.steps[0].y : 10, T = run.end.tables;
  const steps = derive(run), hits = [], design = [];
  const hit = (cls, sub, key, d, v, sev) => hits.push({ cls, sub, key, y: d.y, v, sev: sev == null ? 1 : sev });
  const des = (cls, sub, key, d, v) => design.push({ cls, sub, key, y: d.y, v, sev: 1 });
  const GL = { l: 0, b: 1, r: 2, t: 3 };
  const textName = i => { const t = T.texts[i]; return t ? `${t.sec}:${t.tag}${t.cls ? '.' + t.cls : ''} «${t.text.slice(0, 24)}»` : 't' + i; };
  steps.forEach((d, i) => {
    const s = d.s, f = s.g && s.g.fade;
    // CUT: a product reaching (within TH.touchPx) or passing the edge of what shows it (the canvas; on a desktop also the
    // screen) and not faded there: a straight cut. Faded there by the round fade (the dive): round lines, design. Dimmed
    // by a straight band (the old vignette, an edge strip): a soft straight band across the product when it dims it over
    // ≥ TH.softFrac of its size (and ≥ TH.softPx), else a soft edge (design)
    if (d.mode !== 'still' && d.V) for (const o of Object.values(d.objs)) {
      if (!o.cb || o.op < TH.op || o.near) continue;
      const [mx, my] = fadeMid(d);
      for (const side of ['l', 't', 'r', 'b']) {
        const k = { l: 0, t: 1, r: 2, b: 3 }[side], sign = k < 2 ? -1 : 1, over = sign * (o.b[k] - d.V[k]), ext = k % 2 ? o.b[3] - o.b[1] : o.b[2] - o.b[0];
        const edge = Math.abs(d.V[k] - d.C[k]) < 0.6 ? 'canvas' : 'screen';
        if (d.mode === 'flow' && edge === 'screen') continue;   // a phone: the canvas scrolls with the page (the screen's edges: UNDER_CHROME while a run plays)
        // the object's outermost line on this side (within what shows it), at its point nearest the fades' middle, and the
        // direction inward
        const lim = k % 2 ? [Math.max(o.cb[0], d.V[0]), Math.min(o.cb[2], d.V[2])] : [Math.max(o.cb[1], d.V[1]), Math.min(o.cb[3], d.V[3])];
        if (lim[1] - lim[0] < 1) continue;
        const along = Math.min(lim[1], Math.max(lim[0], k % 2 ? mx : my)), at = over > 0 ? d.V[k] - sign : o.b[k] - sign;
        const pt = t => k % 2 ? [along, at - sign * t] : [at - sign * t, along];
        const straight = fadeAt(d, ...pt(0), 'straight'), round = fadeAt(d, ...pt(0), 'round'), left = straight * round;
        const fk = f && f.round && f.w >= TH.roundW ? 'round' : f && !f.round && f.w > 0.01 ? 'vignette' : f && f.e && f.e[GL[side]] > 0.01 ? 'strip' : 'none';
        const v = { obj: o.name, side, edge, over: R0(over), ext: R0(ext), left: R2(left), fade: fk, op: R2(o.op) };
        if (over > -TH.touchPx && left > TH.cutResid) { hit('CUT', over > TH.cutPx ? 'hard' : 'touch', o.name + ':' + side, d, v, over + TH.touchPx); continue; }
        if (straight >= 1 - TH.bandDim) { if (over > -TH.touchPx && round < 1) des('FADE', 'round-edge', o.name + ':' + side, d, v); continue; }
        if (round < TH.cutResid) { des('FADE', 'round-edge', o.name + ':' + side, d, v); continue; }   // the round fade hides it there anyway
        let depth = 0; while (depth < ext && fadeAt(d, ...pt(depth), 'straight') < 1 - TH.bandDim) depth += 2;   // how far in the band dims it
        v.dimmed = R0(depth + Math.max(0, over));
        if (v.dimmed >= Math.max(TH.softPx, TH.softFrac * ext)) hit('CUT', 'soft-band', o.name + ':' + side, d, v, v.dimmed);
        else des('FADE', 'edge-strip', o.name + ':' + side, d, v);
      }
    }
    // UNDER_CHROME: a product under the header, the dock, the bar or the kit card's body (a desktop: always; a phone or
    // tablet, whose canvas scrolls with the page: while a run plays — a held pose scrolling away under the header is the page)
    const panels = s.ch.filter(c => c[5] >= TH.op).map(c => ({ name: CHROME_NAME[c[0]], r: [c[1], c[2], c[3], c[4]] }));
    if (s.card && s.card.length > 4 && s.card[5] >= TH.op) panels.push({ name: 'card', r: [s.card[0], s.card[4], s.card[2], s.card[3]] });
    if (d.mode !== 'still' && (d.mode === 'desk' || d.running)) for (const pn of panels) {
      let worst = null, faded = false;
      for (const m of d.meshes) {
        if (!m.vis) continue; const q = isect(m.cb, pn.r);
        if (q[2] - q[0] < TH.overPx || q[3] - q[1] < TH.overPx) continue;
        const left = fadeIn(d, q) * m.ope; if (left <= TH.cutResid) { faded = true; continue; }   // faded out there by the scene
        if (!worst || q[3] - q[1] > worst.h) worst = { obj: m.obj, part: m.part, h: R0(q[3] - q[1]), w: R0(q[2] - q[0]), left: R2(left) };
      }
      if (worst) hit('UNDER_CHROME', pn.name, pn.name + ':' + worst.obj, d, Object.assign({ panel: pn.name }, worst), worst.h);
      else if (faded) des('FADE', 'faded-under-' + pn.name, pn.name, d, {});
    }
    // … and a picture of the product (its drawn part) under a panel, in every mode (no JS or WebGL too). On a desktop the
    // dock pill stands over the reading column and the card's body is the kit's own panel: flagged. Under the header, or
    // a phone's bar, a picture passes as the page scrolls by (and the dock there is the bar): listed apart as the page
    for (const pn of panels) for (const p of d.pics) {
      if (p.op < TH.op || (pn.name === 'card' && /^kc-/.test(p.kind))) continue;   // the card's own picture sits on the card
      const q = isect(p.ink, pn.r); if (q[2] - q[0] < TH.overPx || q[3] - q[1] < TH.overPx) continue;
      const v = { panel: pn.name, pic: p.kind + ' ' + p.src, h: R0(q[3] - q[1]), w: R0(q[2] - q[0]) };
      if (vp.w >= 900 && (pn.name === 'dock' || pn.name === 'card')) hit('UNDER_CHROME', pn.name, pn.name + ':' + p.kind + ':' + p.src, d, v, q[3] - q[1]);
      else des('SCROLL', 'under-' + pn.name, pn.name + ':' + p.kind + ':' + p.src, d, v);
    }
    if (d.mode === 'flow' && d.running) for (const o of Object.values(d.objs)) {   // past the screen's edge while it moves
      if (!o.cb) continue;
      const up = -o.b[1], dn = o.b[3] - H;
      if (up > TH.cutPx) hit('UNDER_CHROME', 'screen', 'screen:' + o.name, d, { panel: 'screen top', obj: o.name, h: R0(up) }, up);
      if (dn > TH.cutPx) hit('UNDER_CHROME', 'screen', 'screen:' + o.name, d, { panel: 'screen foot', obj: o.name, h: R0(dn) }, dn);
    }
    // UNDER_TEXT: a line of text over a product (the 3D's meshes, a picture's drawn part)
    const lines = s.tx.filter(t => t[5] >= TH.op);
    for (const t of lines) {
      const r = [t[1], t[2], t[3], t[4]];
      for (const m of d.meshes) {
        if (!m.vis) continue; const q = isect(m.cb, r);
        if (q[2] - q[0] < TH.overPx || q[3] - q[1] < TH.overPx || fadeIn(d, q) * m.ope <= TH.cutResid) continue;
        hit('UNDER_TEXT', '3d', m.obj + ':' + t[0], d, { obj: m.obj, part: m.part, text: textName(t[0]), w: R0(q[2] - q[0]), h: R0(q[3] - q[1]) }, area(q)); break;
      }
      for (const p of d.pics) {
        if (p.op < TH.op) continue; const q = isect(p.ink, r);
        if (q[2] - q[0] >= TH.overPx && q[3] - q[1] >= TH.overPx) hit('UNDER_TEXT', 'pic', p.kind + ':' + p.src + ':' + t[0], d, { pic: p.kind + ' ' + p.src, text: textName(t[0]), w: R0(q[2] - q[0]), h: R0(q[3] - q[1]) }, area(q));
      }
    }
    // TWO_PRODUCTS: the 3D and a picture of the product, or two pictures (the step cards are one series)
    const groups = [...new Set(d.pres.map(p => p.what))];
    if (groups.length >= 2) hit('TWO_PRODUCTS', groups.includes('3d') ? '3d+pic' : 'pics', groups.slice().sort().join('+'), d,
      { what: groups, h: d.pres.map(p => R0((p.pic ? p.pic.shown : p.b)[3] - (p.pic ? p.pic.shown : p.b)[1])) }, 1);
    // GHOST / SEE_THROUGH: a solid part at partial opacity without a depth copy round it (so what is behind shows through),
    // over another part behind it, or alone in mid-air; with a depth copy it fades as a solid: a design fade
    for (const m of d.meshes) {
      if (!m.vis || m.clear || m.op <= TH.ghost[0] || m.op >= TH.ghost[1]) continue;
      if (m.fl & 2) { des('FADE', 'solid', m.obj + ':' + m.part, d, { obj: m.obj, part: m.part, op: R2(m.op) }); continue; }
      const hidden = d.meshes.some(n => n !== m && !n.clear && n.vis && (n.op >= 0.999 || n.fl & 2) && n.d0 < m.d0 && inside(n.b, m.b, 2));
      if (hidden) continue;
      // a solid part coming on with the clear assembly it belongs to (the applicator's tip on its clear nozzle): a clear
      // mesh of the same object at the same opacity touches it, and nothing else is behind it — it reads as one clear
      // thing, not a ghost (a stopper or a cap fading alone, its glass at full opacity, is still one: fd91489 y4820–4900)
      const same = n => n !== m && n.clear && n.vis && n.obj === m.obj && Math.abs(n.op - m.op) <= 0.03;
      const over = d.meshes.filter(n => n !== m && n.vis && !same(n) && n.d1 > m.d0 && area(isect(isect(n.cb, m.cb), d.V)) >= TH.ghostArea);
      const sz = { w: R0(m.cb[2] - m.cb[0]), h: R0(m.cb[3] - m.cb[1]) }, small = area(m.cb) < TH.ghostPart;
      const v = Object.assign({ obj: m.obj, part: m.part, op: R2(m.op) }, sz, over.length ? { behind: [...new Set(over.map(n => n.obj + ':' + n.part))].slice(0, 4) } : {});
      const held = !over.length && d.meshes.find(n => same(n) && area(isect([n.b[0] - 2, n.b[1] - 2, n.b[2] + 2, n.b[3] + 2], m.b)) > 0);
      if (held) des('FADE', 'clear-assembly', m.obj + ':' + m.part, d, Object.assign(v, { with: held.part }));
      else if (small) des('FADE', 'small-part', m.obj + ':' + m.part, d, v);
      else hit('GHOST', over.length ? 'over' : 'air', m.obj + ':' + m.part, d, v, 1 - Math.abs(m.op - 0.5));
    }
    if (s.g && s.g.glow >= TH.op && d.cvop >= TH.op) des('FADE', 'amber-glow', 'glow', d, { glow: s.g.glow });
    // EMPTY: a run in progress and no product on the screen
    if ((d.story || d.running) && d.pres.length === 0) hit('EMPTY', d.mode, 'empty', d, { p: d.dp, canvas: R2(d.cvop), running: d.running }, 1);
    // … or nearly dark: in the dive the amber light must rise as the glass goes (the stronger of the two ≥ TH.dim), never
    // a black frame between (fd91489: 0.14–0.28 at the cross-fades)
    const lit = q => q.s.g && (q.story || q.running) && q.cvop >= TH.op ? [q.s.g.glow, q.meshes.reduce((a, m) => m.vis ? Math.max(a, m.ope) : a, 0)] : null;
    const L0 = lit(d);
    if (L0 && L0[0] > 0.005) {
      const bright = Math.max(L0[0], L0[1]);
      if (bright < TH.dim) hit('EMPTY', 'dim', 'dim', d, { glow: R2(L0[0]), product: R2(L0[1]) }, TH.dim - bright);
      else {   // a cross-fade inside one step (a fast dive): halfway to the next step, each moving in a straight line
        const L1 = steps[i + 1] && lit(steps[i + 1]);
        if (L1) { const mid = Math.max((L0[0] + L1[0]) / 2, (L0[1] + L1[1]) / 2);
          if (mid < TH.dim) hit('EMPTY', 'dim', 'dim', d, { glow: [R2(L0[0]), R2(L1[0])], product: [R2(L0[1]), R2(L1[1])], between: d.y + '–' + steps[i + 1].y }, TH.dim - mid); }
      }
    }
    // LAYOUT, desktop: the product left, the text right (a line beside the 3D on its left)
    if (d.mode === 'desk' && d.pres.some(p => p.what === '3d')) {
      const pb = d.pres.find(p => p.what === '3d').b, pc = (pb[0] + pb[2]) / 2;
      for (const t of lines) {
        const info = T.texts[t[0]] || {}; if (info.sec === 'open' || info.sec === 'kitcard') continue;
        if (t[4] > pb[1] && t[2] < pb[3] && (t[1] + t[3]) / 2 < pc && t[1] < pb[2]) { hit('LAYOUT', 'text-left', 'side:' + t[0], d, { text: textName(t[0]), x: R0(t[1]), product: box4(pb) }, 1); }
      }
    }
    // OFFSCREEN: a line of text or a picture's drawn part past the screen's side
    for (const t of lines) if (t[1] < -1 || t[3] > W + 1) hit('LAYOUT', 'offscreen', 'off:' + t[0], d, { text: textName(t[0]), x: [R0(t[1]), R0(t[3])] }, 1);
    for (const p of d.pics) if (p.op >= TH.op && area(p.ink) > 0 && (p.ink[0] < -1 || p.ink[2] > W + 1)) hit('LAYOUT', 'offscreen', 'off:' + p.kind + ':' + p.src, d, { pic: p.kind + ' ' + p.src, x: [R0(p.ink[0]), R0(p.ink[2])] }, 1);
    if (s.sw) hit('LAYOUT', 'hscroll', 'hscroll', d, { scrollWidth: s.sw }, 1);
    // HD: the canvas and the pictures in view against CSS px × DPR (≤ 2 on a desktop), as verify-hd.cjs
    const cap = Math.min(vp.dpr, d.mode === 'flow' || vp.w < 900 ? 3 : 2);
    if (d.mode !== 'still' && d.inView && s.cv[7]) {
      const need = s.cv[2] * cap, have = s.cv[7];   // the canvas as shown (the flight scales it) against its pixels
      if (have < TH.hd * need) hit('HD', 'canvas', 'canvas', d, { have, need: R0(need), css: R0(s.cv[2]), pr: s.g && s.g.pr }, need - have);
    }
    for (const p of d.pics) if (p.op >= TH.op && area(p.shown) > 0 && p.nat && p.nat < TH.hd * cap) hit('HD', 'pic', 'hd:' + p.kind + ':' + p.src, d, { pic: p.kind + ' ' + p.src, pxPerCss: p.nat, need: cap }, cap - p.nat);
  });
  // POP: an object's size or place jumping between steps 30 px apart; appearing or vanishing from one step to the next
  // in view, not behind a nearer solid object (a vial switched on or off while the box hides it is no pop)
  const names = new Set(steps.flatMap(d => Object.keys(d.objs))), rates = [];
  const sizeOf = b => Math.max(b[2] - b[0], b[3] - b[1]);
  for (const nm of names) for (const [popDy, popSize] of [[TH.popDy, TH.popSize], [TH.popDy2, TH.popSize2]]) {
    const k30 = Math.max(1, Math.round(popDy / dy));
    for (let i = 0; i + k30 < steps.length; i++) {
      const a = steps[i].objs[nm], b = steps[i + k30].objs[nm];
      if (!a || !b || !a.body || !b.body || a.near || b.near || a.op < 0.5 || b.op < 0.5 || !a.cb || !b.cb) continue;
      let ok = steps[i].mode === steps[i + k30].mode;
      for (let j = i + 1; j < i + k30 && ok; j++) { const c = steps[j].objs[nm]; if (!c || !c.body || c.op < 0.5) ok = false; }
      if (!ok || (steps[i].mode === 'flow' && Math.abs(steps[i].dp - steps[i + k30].dp) < 1e-4)) continue;   // a held pose scrolling with its block
      const sa = sizeOf(a.body), sb = sizeOf(b.body), ratio = sb / sa;
      const mv = Math.hypot((a.body[0] + a.body[2] - b.body[0] - b.body[2]) / 2, (a.body[1] + a.body[3] - b.body[1] - b.body[3]) / 2);
      // a desktop's flight into the card moves the whole canvas: its own motion, not the object's
      const cvMove = steps[i].C && steps[i + k30].C ? Math.hypot(steps[i].C[0] - steps[i + k30].C[0], steps[i].C[1] - steps[i + k30].C[1]) : 0;
      const rel = Math.max(0, mv - cvMove) / Math.max(sa, sb);
      rates.push({ obj: nm, y: steps[i].y, per: popDy, ratio, rel, mode: steps[i].mode });
      // going into the dark (shrinking while it fades out: the booster after the pour, the pair before the cards) is the
      // design's exit, listed apart; growing or shrinking at full opacity faster than popSize per popDy px is a pop
      if (Math.max(ratio, 1 / ratio) > popSize) {
        const v = { obj: nm, from: R0(sa), to: R0(sb), per: popDy, ratio: R2(ratio), op: [R2(a.op), R2(b.op)] };
        let dark = false;   // shrinking and fading out over the next 100 px (or gone): its exit into the dark
        if (ratio < 1) for (let j = i; j < Math.min(steps.length, i + k30 + Math.round(100 / dy)) && !dark; j++) { const c = steps[j].objs[nm]; dark = !c || c.op < a.op - 0.3; }
        if (dark) des('FADE', 'into-the-dark', nm, steps[i], v); else hit('POP', 'size', nm, steps[i], v, Math.abs(Math.log(ratio)));
      }
      else if (popDy === TH.popDy && rel > TH.popMove) hit('POP', 'move', nm, steps[i], { obj: nm, move: R0(mv), size: R0(Math.max(sa, sb)), rel: R2(rel) }, rel);
    }
    if (popDy === TH.popDy) for (let i = 0; i + 1 < steps.length; i++) {
      const a = steps[i].objs[nm], b = steps[i + 1].objs[nm], d = a && !b ? steps[i] : !a && b ? steps[i + 1] : null, o = a || b;
      if (!d || !o.cb || o.solidOp < 0.95 || o.near || steps[i].mode !== steps[i + 1].mode) continue;
      if (steps[i].mode === 'flow' && Math.abs(steps[i].dp - steps[i + 1].dp) < 1e-4) continue;
      if (steps[i].cvop < TH.op || steps[i + 1].cvop < TH.op) continue;   // the canvas itself shown or hidden: TWO_PRODUCTS / EMPTY
      // the share of it that a nearer solid object covers (the box it goes behind)
      let cov = 0; for (const q of Object.values(d.objs)) if (q !== o && q.body && q.proxied && q.solidOp >= 0.99 && q.d0 < o.d0) cov = Math.max(cov, area(isect(q.body, o.b)) / Math.max(1, area(o.b)));
      if (cov < TH.popHidden) hit('POP', a ? 'vanish' : 'appear', nm, d, { obj: nm, at: box4(o.cb), op: R2(o.op), covered: R2(cov) }, 1 - cov);
    }
  }
  // the story's screens and runs: holds (an integer position) and the scroll each run takes
  const pAt = d => d.mode === 'flow' ? (d.inView ? d.dp : null) : d.dp;
  const runs = [], screens = [];
  for (let k = 0; k <= 6; k++) {
    const ys = steps.filter(d => d.mode !== 'still' && pAt(d) != null && Math.abs(pAt(d) - k) < 1e-3).map(d => d.y);
    if (ys.length) screens.push({ p: k, y: [ys[0], ys[ys.length - 1]] });
    if (k === 6) break;
    // a phone or tablet: the steps where the pose moves (run 5's start pose 5.58 is held until its block is up)
    const yr = steps.filter(d => d.mode !== 'still' && pAt(d) != null && Math.floor(pAt(d)) === k && fr(pAt(d)) > TH.frac && fr(pAt(d)) < 1 - TH.frac
      && (d.mode === 'desk' || d.running)).map(d => d.y);
    if (yr.length) {
      const span = yr[yr.length - 1] - yr[0] + dy, mode = steps.find(d => d.y === yr[0]).mode;
      runs.push({ k, y: [yr[0], yr[yr.length - 1]], px: span });
      if (span < TH.runMin[mode]) hits.push({ cls: 'RUN_SPAN', sub: mode, key: 'run' + k, y: yr[0], y1: yr[yr.length - 1], v: { run: k, px: span, min: TH.runMin[mode] }, sev: TH.runMin[mode] - span });
    }
  }
  // what the screen shows inside each hold: the 3D, the step cards (the canvas stepped aside), the card's live picture
  // (the flight's end), the card's own picture, nothing — as ranges, each with its frame (the box at its middle)
  const what = d => d.pres.some(p => p.what === '3d') ? '3d' : (d.s.cls & 32) || d.pics.some(p => p.kind === 'step' && p.op >= TH.op && area(p.shown) > 0) ? 'cards'
    : d.pres.some(p => p.what === 'kc-live:') || d.pics.some(p => p.kind === 'kc-live' && p.op >= TH.op && area(p.shown) > 0) ? 'kc-live'
    : d.pics.some(p => p.kind === 'kc-pic' && p.op >= TH.op && area(p.shown) > 0) ? 'kc-pic' : 'none';
  const frameOf = d => { const p = d.pres.find(q => q.what === '3d'); if (p && !p.glow) return box4(p.b); if (p) return 'glow';
    const k = d.pics.find(q => /^kc-/.test(q.kind) && q.op >= TH.op && area(q.shown) > 0); return k ? box4(k.shown) : null; };
  const segments = (list, key) => { const out = []; for (const d of list) { const k = key(d), l = out[out.length - 1];
    if (l && l.what === k && d.y - l.y[1] <= 2 * dy) { l.y[1] = d.y; l.steps.push(d); } else out.push({ what: k, y: [d.y, d.y], steps: [d] }); } return out; };
  for (const sc of screens) {
    const inHold = steps.filter(d => d.mode !== 'still' && pAt(d) != null && Math.abs(pAt(d) - sc.p) < 1e-3 && d.y >= sc.y[0] && d.y <= sc.y[1]);
    sc.parts = segments(inHold, what).map(g => { const mid = g.steps[Math.floor(g.steps.length / 2)], fr = frameOf(mid); return Object.assign({ what: g.what, y: g.y }, fr ? { at: mid.y, box: fr } : {}); });
  }
  // a phone or tablet, block by block: the pose held as the block comes up, run k playing in block k, the pose held after,
  // and the frame at the first step where the whole stage stands between the header and the bar
  const flow = [], BLOCKS = ['open', 'meet', 'why', 'inside', 'feel', 'protocol'];
  if (steps.some(d => d.mode === 'flow')) BLOCKS.forEach((bk, k) => {
    const ss = steps.filter(d => d.mode === 'flow' && d.blk === bk && d.inView); if (!ss.length) return;
    const run = ss.filter(d => d.running && fr(d.dp) > TH.frac && fr(d.dp) < 1 - TH.frac), r0 = run.length ? run[0].y : Infinity, r1 = run.length ? run[run.length - 1].y : -Infinity;   // as runs[]
    const before = ss.filter(d => !d.running && d.y < r0), after = ss.filter(d => !d.running && d.y > r1);
    const full = ss.find(d => d.C[1] >= d.top - 0.5 && d.C[3] <= d.foot + 0.5 && frameOf(d)) || ss.find(d => frameOf(d));
    const pose = list => list.length ? { p: R2(list[0].dp), y: [list[0].y, list[list.length - 1].y] } : null;
    flow.push(Object.assign({ k, block: bk, y: [ss[0].y, ss[ss.length - 1].y], pose0: pose(before), run: run.length ? { y: [r0, r1], px: r1 - r0 + dy } : null, pose1: pose(after) },
      full ? { frame: { y: full.y, box: frameOf(full), full: full.C[1] >= full.top - 0.5 && full.C[3] <= full.foot + 0.5 } } : {}));
  });
  // LAYOUT from the page's blocks: the step cards (desktop: the picture left of its text), a phone's order (heading,
  // then its stage, then the text), the page wider than the screen
  const st = run.end.statics, mode0 = steps.find(d => d.mode !== 'still') ? steps.find(d => d.mode !== 'still').mode : 'still';
  if (vp.w >= 900) (st.steps || []).forEach((c, n) => { if (c.fig && c.text && (c.fig[0] + c.fig[2]) / 2 > (c.text[0] + c.text[2]) / 2)
    hits.push({ cls: 'LAYOUT', sub: 'card-picture-right', key: 'card' + (n + 1), y: Math.max(0, R0(c.fig[1] - H)), y1: R0(c.fig[3]), v: { card: n + 1, fig: box4(c.fig), text: box4(c.text) }, sev: 1 }); });
  if (mode0 === 'flow') for (const id of Object.keys(st.stages || {})) {
    const h = st.heads[id], g = st.stages[id], c = st.copies[id]; if (!g) continue;
    if (h && h[3] > g[1] + 2) hits.push({ cls: 'LAYOUT', sub: 'phone-order', key: id + ':head', y: R0(g[1] - H), y1: R0(g[3]), v: { section: id, head: box4(h), stage: box4(g) }, sev: 1 });
    if (c && c[1] < g[3] - 2) hits.push({ cls: 'LAYOUT', sub: 'phone-order', key: id + ':text', y: R0(g[1] - H), y1: R0(g[3]), v: { section: id, stage: box4(g), text: box4(c) }, sev: 1 });
  }
  if (st.scrollW > W + 1) hits.push({ cls: 'LAYOUT', sub: 'hscroll', key: 'hscroll', y: 0, y1: 0, v: { scrollWidth: st.scrollW }, sev: 1 });
  // EMPTY ranges shorter than TH.emptyPx: a handover between the 3D and a picture (one gives way as the other comes), design
  const merged = merge(hits, dy), short = merged.filter(f => f.cls === 'EMPTY' && f.sub !== 'dim' && f.y[1] - f.y[0] + dy < TH.emptyPx);
  for (const f of short) design.push({ cls: 'FADE', sub: 'handover', key: 'empty', y: f.y[0], y1: f.y[1], v: f.v, sev: 1 });
  return { steps, flags: merged.filter(f => !short.includes(f) && !RULE_CLS[f.cls]), rules: merged.filter(f => RULE_CLS[f.cls]), design: merge(design, dy), runs, screens, flow, dy, rates };
}
function merge(list, dy) {   // the steps of one kind and key into scroll ranges (neighbours ≤ 2 steps apart), with the worst step's numbers
  const by = new Map();
  for (const h of list) { const k = h.cls + '|' + h.sub + '|' + h.key; if (!by.has(k)) by.set(k, []); by.get(k).push(h); }
  const out = [];
  for (const arr of by.values()) {
    arr.sort((a, b) => a.y - b.y); let cur = null;
    for (const h of arr) {
      const y1 = h.y1 != null ? h.y1 : h.y;
      if (cur && h.y - cur.y[1] <= 2 * dy) { cur.y[1] = Math.max(cur.y[1], y1); cur.n++; if (h.sev > cur.sev) { cur.sev = h.sev; cur.v = h.v; cur.at = h.y; } }
      else { cur = { cls: h.cls, sub: h.sub, key: h.key, y: [h.y, y1], n: 1, sev: h.sev, v: h.v, at: h.y }; out.push(cur); }
    }
  }
  return out.sort((a, b) => a.cls.localeCompare(b.cls) || a.y[0] - b.y[0]);
}

// ---------------------------------------------------------------------------------------------------------------------
// the map: <out>/<slug>.json (slim: one screen a line, a legend inside; the 10 px track and the texts' boxes for the key
// screens only) and <out>/<slug>.md (a readable working note, Russian, as the repo's notes); every screen's track and
// texts go to <raw>/<slug>.track.json.gz (they rebuild in two minutes: not for the repository)
const rle = (vals, enc) => {   // consecutive equal tokens as «token*n»
  const out = []; let prev = null, n = 0;
  for (const v of vals) { const t = enc(v); if (t === prev) n++; else { if (prev !== null) out.push(n > 1 ? prev + '*' + n : prev); prev = t; n = 1; } }
  if (prev !== null) out.push(n > 1 ? prev + '*' + n : prev);
  return out.join(' ');
};
const KEYVP = ['1280x720', '1440x900', '1920x1080', '390x844@3t'];
const LEGEND = {
  y: 'прокрутка страницы в px (scrollY) на данном экране; диапазоны [y0, y1] включительно, шаг tool.step',
  p: 'позиция истории: 0 открытие … 5 S5, 6 набор на карточке; дробь — доля прогона. Компьютер: __seq().pos = window.__mtP. Телефон/планшет: нарисованная поза sceneState.drawn (window.__mtP там — позиция по странице, не поза)',
  holds: '{p, y, parts: [{what, y, at, box}]}: удержание позы p и что на экране внутри него (3d, cards — карточки шагов при скрытой сцене, kc-live — живая картинка карточки, kc-pic — картинка карточки, none); box — рамка на экране x0,y0,x1,y1 в px на шаге at',
  runs: '{k, y, px}: прогон k→k+1 и его прокрутка',
  flow: 'телефон/планшет, по блокам: {k, block, y, pose0:{p,y}, run:{y,px}, pose1:{p,y}, frame:{y, box, full}} — поза до прогона, прогон k в блоке k, поза после; кадр на первом шаге, где сцена целиком между шапкой и панелью (full)',
  stepAside: 'компьютер: y, где сцена скрыта под карточки шагов (html.mt-cards0); landing: y посадки набора на карточку (html.mt-land)',
  track: 'только ключевые экраны (остальные — в <raw>/<slug>.track.json.gz): RLE «значение*n» по шагам от y0 через dy; p ×1000 («-» нет); box «x0,y0,x1,y1» до 2 px — рамка видимого продукта: детали с прозрачностью ≥ tool.thresholds.op (0.05) ниже шапки («g» янтарный свет, «-» ничего видимого: пусто или прозрачнее 5 %); canvas — прозрачность холста ×100',
  pictures: '{id, kind, src, sec, nat:[w,h] — пиксели файла, page:[x0,y0,x1,y1] — место на странице, где впервые видна, shown:[[y0,y1]…] — где показана}',
  texts: 'ключевые экраны: [id, x0, y0, x1, y1(, sticky|fixed)] в координатах страницы, где строка впервые видна; pinned: [id, y0, y1, x0, top, x1, bottom] — диапазон прокрутки, где прижатая (sticky/fixed) строка стоит на месте, и её место на экране; словарь texts: id → [блок, тег, начало текста]',
  flags: '{cls, sub, y:[y0,y1], at: худший шаг, n: шагов, v: числа худшего шага} — пиксельные дефекты по числам; rules — правила на решение заказчика (RUN_SPAN), не дефекты кадра; design — принятые затухания (FADE) и то, что даёт прокрутка страницы (SCROLL), по видам с диапазонами',
  errors: 'ошибки консоли страницы в пробе (errs — первые различные; без WebGL ожидаемы «WebGL context could not be created»)',
  build: '{file, md5, rev — HEAD репозитория при пробе, sourcesRev — последний коммит файлов страницы (sources), cmd — команда сборки, keys — папка ключевых кадров: число файлов и md5 их списка, probe — md5 шрифта, three.js и three-nodraw}',
};
const distinct = a => [...new Set(a)];
function viewportMap(run, a) {
  const vp = run.vp, st = run.end.statics, steps = a.steps, dy = a.dy, T = run.end.tables, key = KEYVP.includes(vp.id);
  const mode = (steps.find(d => d.mode !== 'still') || { mode: 'still' }).mode;
  const blocks = {}; for (const [k, v] of Object.entries(st.blocks || {})) if (v) blocks[k] = [R0(v[1]), R0(v[3])];
  // the product on the screen per step: the 3D's visible outline (or none), the canvas's opacity, the story position
  const prod = steps.map(d => { const p = d.pres.find(q => q.what === '3d'); return p && !p.glow ? box4(p.b) : p ? 'glow' : null; });
  const track = { y0: steps.length ? steps[0].y : 0, dy, n: steps.length,
    p: mode === 'still' ? '' : rle(steps.map(d => d.dp), v => v == null ? '-' : String(Math.round(v * 1000))),
    box: mode === 'still' ? '' : rle(prod, v => v == null ? '-' : v === 'glow' ? 'g' : v.map(x => 2 * Math.round(x / 2)).join(',')),   // px, to 2 px
    canvas: mode === 'still' ? '' : rle(steps.map(d => d.cvop), v => String(Math.round(v * 100))) };
  // pictures: where each is shown (y ranges), its place in the page, its file's pixels
  const pics = new Map();
  steps.forEach(d => { for (const p of d.pics) { if (p.op < TH.op || area(p.shown) <= 0) continue;
    const info = T.pics[p.pid] || {}, e = pics.get(p.pid) || { id: 'p' + p.pid, kind: p.kind, src: p.src, sec: p.sec, nat: [info.nw || 0, info.nh || 0], page: null, shown: [] };
    if (!e.page) e.page = [R0(p.el[0]), R0(p.el[1] + d.y), R0(p.el[2]), R0(p.el[3] + d.y)];
    const last = e.shown[e.shown.length - 1]; if (last && d.y - last[1] <= 2 * dy) last[1] = d.y; else e.shown.push([d.y, d.y]);
    pics.set(p.pid, e); } });
  // texts: each owner's lines in page coordinates (static content: once, where first seen); a sticky or fixed owner moves
  // with the scroll, so for it the scroll ranges where it stands still on the screen are kept too (pinned)
  const texts = new Map(), vb = new Map();
  steps.forEach(d => { for (const t of d.s.tx) { const k = t[0], r = [t[1], t[2] + d.y, t[3], t[4] + d.y];
    const e = texts.get(k); if (!e) texts.set(k, { y: d.y, r }); else if (e.y === d.y) e.r = uni(e.r, r);
    if (T.texts[k] && T.texts[k].fix) { const q = vb.get(k) || new Map(), b = q.get(d.y); q.set(d.y, b ? uni(b, [t[1], t[2], t[3], t[4]]) : [t[1], t[2], t[3], t[4]]); vb.set(k, q); } } });
  const pinned = [];
  for (const [k, q] of vb) { let cur = null;
    for (const [y, b] of q) { if (cur && y - cur.y1 <= dy && Math.abs(b[1] - cur.b[1]) < 0.6) { cur.y1 = y; cur.n++; } else { if (cur && cur.n >= 3) pinned.push(['t' + k, cur.y0, cur.y1, ...box4(cur.b)]); cur = { y0: y, y1: y, n: 1, b }; } }
    if (cur && cur.n >= 3) pinned.push(['t' + k, cur.y0, cur.y1, ...box4(cur.b)]); }
  const textsOut = [...texts.entries()].sort((x, y) => x[1].r[1] - y[1].r[1]).map(([k, e]) => ['t' + k, ...e.r.map(R0)].concat(T.texts[k] && T.texts[k].fix ? [T.texts[k].fix] : []));
  const cards = steps.filter(d => d.s.cls & 32).map(d => d.y), land = steps.filter(d => d.s.cls & 64).map(d => d.y);
  const count = {}; for (const f of a.flags) count[f.cls] = (count[f.cls] || 0) + 1;
  const flag = f => ({ cls: f.cls, sub: f.sub, key: f.key, y: f.y, at: f.at, n: f.n, v: f.v });
  const m = { id: vp.id, kind: vp.kind, mode, w: vp.w, h: vp.h, dpr: vp.dpr, touch: vp.touch, docH: st.docH, steps: steps.length, probe_s: R1(run.ms / 1000),
    errors: run.log.errs.length, errs: distinct(run.log.errs).slice(0, 3).map(s => s.slice(0, 120)), band: st.band || null, blocks,
    stepsScroll: st.stepsScroll ? Object.assign({ n: (st.steps || []).length }, st.stepsScroll) : null,
    holds: a.screens, runs: a.runs, flow: a.flow, stepAside: cards.length ? [cards[0], cards[cards.length - 1]] : null, landing: land.length ? [land[0], land[land.length - 1]] : null,
    pictures: [...pics.values()], flags: a.flags.map(flag), rules: a.rules.map(flag), design: summariseDesign(a.design), count };
  if (key) { m.track = track; m.texts = textsOut; m.pinned = pinned; }
  return { m, full: { id: vp.id, track, texts: textsOut, pinned } };
}
function summariseDesign(list) {   // the accepted fades by kind: their ranges, not every part
  const by = {};
  for (const f of list) { const k = f.cls + ':' + f.sub; (by[k] = by[k] || []).push(f.y); }
  return Object.entries(by).map(([k, ys]) => { ys.sort((a, b) => a[0] - b[0]); const m = [];
    for (const y of ys) { const l = m[m.length - 1]; if (l && y[0] <= l[1] + 20) l[1] = Math.max(l[1], y[1]); else m.push(y.slice()); }
    return { kind: k, y: m }; });
}
function layoutVerdict(out, slug) {   // the layout rules' map of the same page (qa/layout-check.cjs), when it lies beside
  const f = path.join(out, slug + '.layout.json'); if (!fs.existsSync(f)) return null;
  try { const j = JSON.parse(fs.readFileSync(f, 'utf8')), s = j.pages && j.pages[slug] && j.pages[slug].summary; if (!s) return null;
    return { file: slug + '.layout.md', generated: j.generated, high: s.high, low: s.low, pass: s.pass, byRule: s.byRule }; } catch (e) { return null; }
}
function lookedSummary(file) {   // the last --spot run (the pictures the numbers asked for, and the colour tests)
  try { const j = JSON.parse(fs.readFileSync(file, 'utf8')), st = fs.statSync(file);
    return { file: path.basename(path.dirname(path.resolve(file))) + '/' + path.basename(file), date: st.mtime.toISOString(), n: j.length, pass: j.filter(x => x.pass === true).length,
      fail: j.filter(x => x.pass === false).length, look: j.filter(x => x.pass == null).length, screens: distinct(j.map(x => x.screen)) }; } catch (e) { return { file, error: String(e).slice(0, 80) }; }
}
function analyseAll(runs, out, rawDir) {
  if (!runs.length) return;
  fs.mkdirSync(out, { recursive: true });
  const page = runs[0].page, slug = page.slug, cfg = PAGES[slug] || {}, dy = runs[0].steps.length > 1 ? runs[0].steps[1].y - runs[0].steps[0].y : 10;
  const map = { page: slug, build: page.build || { file: path.basename(page.file), md5: page.md5 }, date: new Date().toISOString(),
    tool: { script: 'site/proto/qa/pagemap.cjs', doc: 'site/proto/qa/pagemap.md', step: dy, thresholds: TH, probe: page.build && page.build.probe || null },
    timing: { total_s: R1(runs.reduce((s, r) => s + r.ms, 0) / 1000), per: Object.fromEntries(runs.map(r => [r.vp.id, R1(r.ms / 1000)])) },
    legend: LEGEND, texts: {}, screens: {} };
  const T = runs[0].end.tables, blocksOK = cfg.textBlocks || null;   // the texts' dictionary: the product's own blocks
  (T.texts || []).forEach((t, i) => { if (!blocksOK || blocksOK.includes(t.sec)) map.texts['t' + i] = [t.sec, t.tag + (t.cls ? '.' + t.cls : ''), t.text]; });
  const fulls = {};
  for (const run of runs) {
    const a = analyse(run), { m, full } = viewportMap(run, a); map.screens[run.vp.id] = m; fulls[run.vp.id] = full;
    console.log(`${run.vp.id}: ${m.mode}, flags ${a.flags.length}` + (a.flags.length ? ' — ' + Object.entries(m.count).map(([k, v]) => k + ' ' + v).join(', ') : '') + (a.rules.length ? `; rules ${a.rules.length}` : ''));
  }
  map.layout = layoutVerdict(out, slug);
  if (opt('--looked')) map.looked = lookedSummary(opt('--looked'));
  // the slim JSON: one screen a line, so a regeneration's diff reads screen by screen
  const jf = path.join(out, slug + '.json'), L = [];
  for (const [k, v] of Object.entries(map)) if (k !== 'screens') L.push(` ${JSON.stringify(k)}: ${JSON.stringify(v)}`);
  L.push(' "screens": {\n' + Object.entries(map.screens).map(([id, m]) => `  ${JSON.stringify(id)}: ${JSON.stringify(m)}`).join(',\n') + '\n }');
  fs.writeFileSync(jf, '{\n' + L.join(',\n') + '\n}\n');
  const tdir = rawDir || path.join(os.tmpdir(), 'pagemap'); fs.mkdirSync(tdir, { recursive: true });
  const tf = path.join(tdir, slug + '.track.json.gz');
  fs.writeFileSync(tf, zlib.gzipSync(JSON.stringify({ page: slug, md5: map.build.md5, date: map.date, legend: { track: LEGEND.track, texts: LEGEND.texts }, screens: fulls })));
  const mf = path.join(out, slug + '.md');
  fs.writeFileSync(mf, markdown(map, fs.existsSync(mf) ? fs.readFileSync(mf, 'utf8') : ''));
  writeReadme(out, map);
  console.log(`map: ${jf} (${(fs.statSync(jf).size / 1024).toFixed(0)} KB), ${mf}; track: ${tf} (${(fs.statSync(tf).size / 1024).toFixed(0)} KB)`);
  return map;
}

// the readable note (Russian, as the repo's working notes): generated from the map; the part between <!-- notes --> and
// <!-- /notes --> of the existing note (remarks by hand) is kept as it is. The tool's own matter (method, calibration,
// thresholds, legend) is qa/pagemap.md, one for every page
const CLS_RU = { CUT: 'срез', UNDER_CHROME: 'под шапкой/панелью', UNDER_TEXT: 'под текстом', TWO_PRODUCTS: 'два продукта', GHOST: 'просвечивает',
  POP: 'скачок', EMPTY: 'пустая сцена', RUN_SPAN: 'короткий прогон', LAYOUT: 'вёрстка', HD: 'HD' };
const DES_RU = { solid: 'деталь гаснет целиком', 'round-edge': 'круглое затухание края', 'amber-glow': 'янтарный свет', handover: 'передача 3D ↔ картинка',
  'into-the-dark': 'уход в темноту', 'small-part': 'малая деталь гаснет', 'edge-strip': 'мягкий край', 'faded-under-dock': 'погашено под док-панелью',
  'faded-under-header': 'погашено под шапкой', 'faded-under-bar': 'погашено под панелью', 'faded-under-card': 'погашено под карточкой',
  'clear-assembly': 'прозрачный узел (носик)', 'under-header': 'картинка под шапкой при прокрутке', 'under-bar': 'картинка под нижней панелью при прокрутке',
  'under-dock': 'картинка под док-панелью при прокрутке (телефон)' };
const WHAT_RU = { '3d': '3D', cards: 'карточки шагов, сцена скрыта', 'kc-live': 'картинка карточки (живой холст)', 'kc-pic': 'картинка карточки', none: 'пусто' };
function fmtV(v) { return Object.entries(v || {}).map(([k, x]) => k + ' ' + (Array.isArray(x) ? x.join('/') : typeof x === 'object' && x ? JSON.stringify(x) : x)).join(', '); }
const yr = y => y ? (y[0] === y[1] ? String(y[0]) : y[0] + '–' + y[1]) : '—';
const bx = b => Array.isArray(b) ? `${b[0]},${b[1]}–${b[2]},${b[3]}` : b === 'glow' ? 'янтарный свет' : '';
const whenRu = d => new Date(d).toLocaleString('ru-RU', { timeZone: 'Asia/Jerusalem', dateStyle: 'short', timeStyle: 'short' });
function markdown(map, old) {
  const cfg = PAGES[map.page] || {}, sc = map.screens, ids = Object.keys(sc), live = ids.filter(id => sc[id].mode !== 'still'), dy = map.tool.step;
  const deskKey = KEYVP.filter(k => sc[k] && sc[k].mode === 'desk'), flowIds = ids.filter(id => sc[id].mode === 'flow'), stillIds = ids.filter(id => sc[id].mode === 'still');
  const notes = (/<!-- notes -->[\s\S]*?<!-- \/notes -->/.exec(old) || ['<!-- notes -->\n\n<!-- /notes -->'])[0];
  const L = [], b = map.build, when = whenRu(map.date);
  const nFlags = ids.reduce((a, id) => a + sc[id].flags.length, 0), nLive = live.reduce((a, id) => a + sc[id].flags.length, 0), nRules = ids.reduce((a, id) => a + sc[id].rules.length, 0);
  const byCls = list => { const c = {}; for (const id of list) for (const f of sc[id].flags) c[f.cls] = (c[f.cls] || 0) + 1; return Object.entries(c).map(([k, v]) => `${k} ${v}`).join(', '); };
  L.push(`# ${cfg.title || map.page} — карта страницы`, '',
    `Рабочая заметка (генерирует \`site/proto/qa/pagemap.cjs\`; данные — \`${map.page}.json\` рядом, легенда внутри JSON и в \`site/proto/qa/pagemap.md\`). Сборка \`${b.file}\` · md5 \`${b.md5}\``
    + (b.rev ? ` · репозиторий ${b.rev}` : '') + (b.sourcesRev ? `, файлы страницы последний раз менялись в ${b.sourcesRev}` : '') + (b.keys ? ` · ключевые кадры \`${b.keys.dir}\`: ${b.keys.n} файлов, md5 списка \`${b.keys.md5.slice(0, 8)}\`` : '')
    + ` · проверка ${when} · шаг ${dy} px · ${ids.length} режимов за ${map.timing.total_s} с` + (cfg.link ? ` · ссылка ${cfg.link}` : '') + '.', '');
  if (b.cmd) L.push(`Сборка: \`${b.cmd}\`.`, '');
  L.push('**Итог.** ' + (nLive ? `По пикселям на живых экранах — ${nLive} флагов (${byCls(live)}): к исправлению, см. ниже.` : 'По пикселям на живых экранах (компьютер, телефоны и планшеты с 3D) — чисто.')
    + (stillIds.some(id => sc[id].flags.length) ? ` Без JS / без WebGL — ${stillIds.reduce((a, id) => a + sc[id].flags.length, 0)} флагов (${byCls(stillIds)}): реальные, малые, только без JS или WebGL — решение заказчика.` : '')
    + (nRules ? ` Правила на решение заказчика — ${nRules} (${distinct(ids.flatMap(id => sc[id].rules.map(r => r.cls))).join(', ')}).` : '')
    + (map.layout ? ` Вёрстка L1–L8 (\`${map.layout.file}\`, ${whenRu(map.layout.generated)}): ${map.layout.high} high, ${map.layout.low} low, ${map.layout.pass} pass.` : ' Карта вёрстки L1–L8 рядом не найдена.')
    + (map.looked ? ` Финальный взгляд картинками (\`--spot\`, ${whenRu(map.looked.date)}): ${map.looked.n} картинок на ${map.looked.screens.length} экранах — ${map.looked.pass} PASS, ${map.looked.fail} FAIL, ${map.looked.look} на глаз (${map.looked.file}).` : ' Финальный взгляд картинками (`--spot`) для этой сборки не записан (`--looked <spot.json>`).'), '');
  L.push('Как читать: y — прокрутка страницы в px (scrollY) на данном экране, диапазоны включительно; p — позиция истории (0 открытие … 5 S5, 6 набор на карточке; дробная часть — доля прогона). На компьютере p = `__seq().pos` = `window.__mtP`; на телефоне и планшете p — нарисованная поза (`sceneState.drawn`): там `window.__mtP` — позиция по странице, не поза, и прогон k играет в блоке k, пока блок идёт вверх по экрану. Рамки — x0,y0–x1,y1 в px экрана.', '',
    'Пересобрать карту (около 2 мин на 15 режимов): `cd site/proto && NODE_PATH=$(npm root -g) THREE=<three@0.160.0/build/three.module.min.js> node qa/pagemap.cjs <dir>/' + b.file + ' <dir> --out ../pagemap --raw <scratch>/raw --keys <keys> --build-cmd "…"`; шрифт — `qa/fonts/Rubik[wght].ttf` (без него и без three.js инструмент останавливается); только проверки по сохранённым данным — `--from-raw <raw dir>`; картинки по флагам и цвету — `--spot ../pagemap/' + map.page + '.json <page> <dir> --out <scratch>`.', '');
  // 1. the result
  L.push('## Итог проверки', '', '| экран | режим | шагов | с | флаги (пиксели) | правила | принятые затухания и прокрутка (дизайн, страница) |', '|---|---|---|---|---|---|---|');
  for (const id of ids) { const m = sc[id];
    L.push(`| ${id} | ${m.mode}${m.kind !== 'live' ? ' (' + m.kind + ')' : ''} | ${m.steps} | ${m.probe_s} | ${m.flags.length ? Object.entries(m.count).map(([k, v]) => `${k} ${v}`).join(', ') : 'нет'} | ${m.rules.length ? m.rules.map(r => r.cls).join(', ') : '—'} | ${m.design.map(x => DES_RU[x.kind.split(':')[1]] || x.kind).join(', ') || '—'} |`); }
  L.push('');
  const flagged = ids.filter(id => sc[id].flags.length);
  if (flagged.length) {   // one line per flag (class, kind, what), its ranges screen by screen, the worst step's numbers once
    L.push('### Флаги по диапазонам (к исправлению)', '', 'Одна строка на флаг (класс, вид, что именно); по экранам — диапазон y, число шагов, худший шаг; числа — худшего шага первого экрана.', '');
    const by = new Map();
    for (const id of flagged) for (const f of sc[id].flags) { const k = `${f.cls}|${f.sub}|${f.key || ''}`; if (!by.has(k)) by.set(k, { f, at: [] }); by.get(k).at.push(`${id} y ${yr(f.y)}${/LAYOUT/.test(f.cls) ? '' : ` (${f.n} шаг., худший y${f.at})`}`); }
    for (const { f, at } of by.values()) L.push(`- ${f.cls} (${CLS_RU[f.cls] || ''}${f.sub ? ', ' + f.sub : ''}) ${f.key ? '`' + f.key + '`' : ''}: ${at.join(' · ')} — ${fmtV(f.v)}`);
    L.push('');
  }
  const ruled = ids.filter(id => sc[id].rules.length);
  if (ruled.length) {
    L.push('### Правила на решение заказчика (не пиксельные дефекты)', '');
    for (const id of ruled) for (const f of sc[id].rules) L.push(`- ${id}: ${f.cls} (${CLS_RU[f.cls] || ''}, ${f.sub}) y ${yr(f.y)}: ${fmtV(f.v)}`);
    L.push('');
  }
  const errd = ids.filter(id => sc[id].errors);
  if (errd.length) L.push('Ошибки консоли в пробе: ' + errd.map(id => `${id} — ${sc[id].errors} (${sc[id].errs.map(e => `«${e.slice(0, 60)}»`).join('; ')})`).join('; ') + '.', '');
  // 2. what is where: a desktop
  if (deskKey.length) {
    L.push('## Что где: компьютер (html.story, сцена слева, текст справа)', '', `Удержание позы p — диапазон y на ключевых экранах и что на экране внутри него: 3D с рамкой (x0,y0–x1,y1 px на шаге at), карточки шагов при скрытой сцене, картинка карточки, пусто.`, '',
      '| p | экран | ' + deskKey.join(' | ') + ' |', '|---|---|' + deskKey.map(() => '---|').join(''));
    for (let k = 0; k <= 6; k++) {
      const cells = deskKey.map(id => { const h = (sc[id].holds || []).find(x => x.p === k); if (!h) return '—';
        const parts = h.parts || []; if (parts.length === 1 && parts[0].what === '3d') return `${yr(h.y)} · ${bx(parts[0].box)}`;
        return `${yr(h.y)}: ` + parts.map(p => `${WHAT_RU[p.what] || p.what} ${yr(p.y)}${p.box ? ' (' + bx(p.box) + (p.at != null ? ' @' + p.at : '') + ')' : ''}`).join(' · '); });
      L.push(`| ${k} | ${(cfg.holds || [])[k] || ''} | ${cells.join(' | ')} |`);
    }
    L.push('');
    // run 5, the step cards and the landing, from the numbers of each key screen
    for (const id of deskKey) { const m = sc[id], h5 = (m.holds || []).find(x => x.p === 5), r5 = (m.runs || []).find(x => x.k === 5), h6 = (m.holds || []).find(x => x.p === 6), sa = m.stepAside;
      if (!sa || !r5 || !h5) continue;
      const hid = Math.max(0, Math.min(sa[1], r5.y[1]) - r5.y[0] + dy), share = Math.round(100 * hid / r5.px), vis3 = (h5.parts || []).filter(p => p.what === '3d').map(p => yr(p.y)).join(', ');
      L.push(`- ${id}: карточки шагов (сцена скрыта) ${yr(sa)} = конец удержания S5 (пара видна ${vis3 || '—'}) + первые ${share} % прогона 5 (${r5.y[0]}–${Math.min(sa[1], r5.y[1])} из ${yr(r5.y)}); видимый прогон 5 — ${Math.max(r5.y[0], sa[1] + dy)}–${r5.y[1]}` + (m.landing ? `; посадка на карточку ${yr(m.landing)}` : '') + (h6 ? `; удержание 6: ${(h6.parts || []).map(p => `${WHAT_RU[p.what] || p.what} ${yr(p.y)}`).join(', ')}` : '') + '.'); }
    L.push('');
  }
  // 3. what is where: a phone or tablet, block by block
  if (flowIds.length) {
    L.push('## Что где: телефон и планшет (html.flow, у каждого блока своя сцена)', '', 'Сцена переезжает из блока в блок; прогон k играет в блоке k, пока блок идёт вверх. В ячейке: поза до прогона (y) → прогон (y, px) → поза после (y) · кадр — рамка 3D на первом шаге, где сцена целиком между шапкой и нижней панелью (иначе «частично»). В середине удержания продукта на экране может не быть (сцена ушла под шапку, кадр соседнего блока ещё под панелью) — это страница, не дефект.', '',
      '| блок | что | ' + flowIds.join(' | ') + ' |', '|---|---|' + flowIds.map(() => '---|').join(''));
    const BLOCKS = ['open', 'meet', 'why', 'inside', 'feel', 'protocol'];
    BLOCKS.forEach((bk, k) => {
      const cells = flowIds.map(id => { const f = (sc[id].flow || []).find(x => x.block === bk); if (!f) return '—';
        const seg = [];
        if (f.pose0) seg.push(`поза ${f.pose0.p} ${yr(f.pose0.y)}`);
        if (f.run) seg.push(`прогон ${k} ${yr(f.run.y)} (${f.run.px} px)`);
        if (f.pose1) seg.push(`поза ${f.pose1.p} ${yr(f.pose1.y)}`);
        return seg.join(' → ') + (f.frame ? ` · кадр y${f.frame.y}: ${bx(f.frame.box)}${f.frame.full ? '' : ' (частично)'}` : ' · кадра нет'); });
      L.push(`| #${bk} | ${(cfg.flow || [])[k] || ''} | ${cells.join(' | ')} |`);
    });
    const picRow = (kind, label) => '| ' + label + ' | — | ' + flowIds.map(id => { const ps = sc[id].pictures.filter(p => p.kind === kind); return ps.length ? ps.map(p => `${p.src || ''} ${p.shown.map(yr).join(', ')}`).join('; ') : '—'; }).join(' | ') + ' |';
    L.push(picRow('step', 'карточки шагов (картинки)'), picRow('kc-pic', 'картинка набора на карточке'), '');
    const scr = flowIds.map(id => sc[id].stepsScroll ? `${id}: целиком на экране ${sc[id].stepsScroll.onScreen} из ${sc[id].stepsScroll.n} (лента ${sc[id].stepsScroll.scrollW} px при ширине ${sc[id].stepsScroll.clientW})` : null).filter(Boolean);
    if (scr.length) L.push(`Карточки шагов на телефоне — боковая лента (\`.mt-steps\`, overflow-x): без её прокрутки видны не все (${scr.join('; ')}); проба страницу вбок не листает, поэтому шаги за правым краем в таблицах телефона не показаны.`, '');
  }
  // 4. the runs
  L.push('## Прогоны', '', '| прогон | что происходит | ' + live.join(' | ') + ' |', '|---|---|' + live.map(() => '---|').join(''));
  for (let k = 0; k < 6; k++) L.push(`| ${k}→${k + 1} | ${(cfg.runs || [])[k] || ''} | ` + live.map(id => { const r = (sc[id].runs || []).find(x => x.k === k); return r ? `${r.px} px (${yr(r.y)})` : '—'; }).join(' | ') + ' |');
  L.push('');
  // 5. the pictures
  L.push('## Картинки продукта', '', '| картинка | файл | пиксели | где | показана (y) на ключевых экранах и без JS/WebGL |', '|---|---|---|---|---|');
  const pics = new Map();
  for (const id of ids) for (const p of sc[id].pictures) { const k = p.kind + '|' + p.src + '|' + p.sec; if (!pics.has(k)) pics.set(k, { p, at: [] }); if (KEYVP.includes(id) || sc[id].kind !== 'live') pics.get(k).at.push(`${id}: ${p.shown.map(yr).join(', ')}`); }
  for (const { p, at } of pics.values()) L.push(`| ${p.kind} | ${p.src || '(canvas)'} | ${p.nat && p.nat[0] ? p.nat.join('×') : '—'} | ${p.sec || '—'} | ${at.join('; ') || '—'} |`);
  L.push('', 'Источник картинок: ' + (cfg.pictures || '—') + '.', '');
  // 6. the texts
  L.push('## Тексты (блоки продукта) и источники', '', 'Тексты страницы — ' + (cfg.texts || '—') + '. Позиции строк по ключевым экранам — в JSON (`screens.<экран>.texts`: id, x0, y0, x1, y1 в координатах страницы, где строка впервые видна; прижатые строки (sticky: на компьютере копия оффера, `.offer-copy`) помечены и перечислены в `pinned` с диапазоном прокрутки, где они стоят на месте). Строки специалистов, «смотрите также» и подвала — общие для сайта, в карту не входят.', '');
  const bySec = {}; for (const [id, t] of Object.entries(map.texts)) (bySec[t[0] || '—'] = bySec[t[0] || '—'] || []).push([id, t]);
  for (const [sec, arr] of Object.entries(bySec)) L.push(`- **${sec}**: ` + arr.slice(0, 14).map(([id, t]) => `${id} ${t[1].split('.')[0]} «${t[2]}»`).join(' · ') + (arr.length > 14 ? ` · … (${arr.length})` : ''));
  const pin = deskKey.map(id => ({ id, p: sc[id].pinned || [] })).filter(x => x.p.length);
  if (pin.length) L.push('', 'Прижатые строки: ' + pin.map(({ id, p }) => `${id} — ${p.map(e => `${e[0]} y ${e[1]}–${e[2]} на экране x${e[3]},y${e[4]}–${e[5]},${e[6]}`).join('; ')}`).join('. ') + '.');
  // 7. waiting for a decision
  L.push('', '## Ждёт решения', '');
  for (const s of cfg.pending || []) L.push('- ' + s);
  if (nRules) { const rs = ids.flatMap(id => sc[id].rules.map(r => ({ id, r }))); for (const cls of distinct(rs.map(x => x.r.cls)))
    L.push(`- ${cls} (${CLS_RU[cls] || ''}): ` + rs.filter(x => x.r.cls === cls).map(x => `${x.id} ${fmtV(x.r.v)}`).join('; ') + (cls === 'RUN_SPAN' ? ' — правило, не кадр: прогон начинается с верха страницы и кончается у шапки, длиннее станет только при более высоком блоке открытия; принять или удлинить' : '')); }
  if (stillIds.some(id => sc[id].flags.length)) L.push(`- Без JS / без WebGL: ${stillIds.filter(id => sc[id].flags.length).map(id => `${id} — ${Object.entries(sc[id].count).map(([k, v]) => `${k} ${v}`).join(', ')}`).join('; ')} (кадры-картинки входят снизу, пока предыдущий ещё на экране; кадры m1–m5 показаны мельче 3× CSS): исправлять (полосы между кадрами, кадры ≥ 3×) или принять.`);
  if (nLive) L.push(`- К исправлению на живых экранах: ${byCls(live)} — после правки страницы карту пересобрать.`);
  if (map.layout) L.push(`- Вёрстка L1–L8: ${map.layout.high} high, ${map.layout.low} low (\`${map.layout.file}\`) — правки файлов страницы.`);
  if (cfg.questions) L.push(`- Тексты: \`${path.posix.normalize(cfg.questions.file).replace(/^(\.\.\/)+/, '')}\` ${cfg.questions.short || ''}` + (cfg.questions.extra || []).map(e => '; ' + e).join(''));
  L.push(map.looked ? `- Финальный взгляд картинками на ${map.looked.screens.join(', ')} (${whenRu(map.looked.date)}): ${map.looked.pass} PASS, ${map.looked.fail} FAIL, ${map.looked.look} на глаз — картинки в рабочей папке (${map.looked.file}), в репозиторий не идут.`
    : '- Финальный взгляд картинками (`--spot`) для этой сборки не записан.');
  // 8. notes (kept) and the questions
  L.push('', '## Заметки по странице', '', 'Метод, калибровка на старых сборках, пороги и то, что числами не ловится, — `site/proto/qa/pagemap.md` (один документ на все страницы).', '', notes, '');
  L.push('## Открытые вопросы заказчику', '');
  try { const q = fs.readFileSync(path.join(__dirname, cfg.questions.file), 'utf8'), sec = cfg.questions.section, m = new RegExp('## ' + sec + '\\.[^\\n]*\\n([\\s\\S]*?)(?:\\n## |\\s*$)').exec(q);
    const items = m ? m[1].split(/\n(?=\d+\. )/).map(x => x.trim()).filter(x => /^\d+\./.test(x)) : [];
    for (const it of items) {   // the question's first sentence (and its «Вопрос: …» one, or a second when the first is short)
      const t = it.replace(/^\d+\.\s*/, '').replace(/\s*\n\s*/g, ' '), ss = t.split(/(?<=[.?!])\s+/);
      const qq = ss.find((x, k) => k > 0 && /^Вопрос/.test(x)), out = [ss[0]].concat(qq ? [qq] : ss[0].length < 120 && ss[1] ? [ss[1]] : []).join(' ');
      L.push('- ' + (out.length > 420 ? out.slice(0, 400) + '…' : out));
    }
    for (const e of cfg.questions.extra || []) L.push('- ' + e);
    L.push('', `Полный список — \`${path.posix.normalize(cfg.questions.file).replace(/^(\.\.\/)+/, '')}\` (§${sec} и новые строки на «ок»).`);
  } catch (e) { L.push('— (файл вопросов не найден)'); }
  return L.join('\n') + '\n';
}

// ---------------------------------------------------------------------------------------------------------------------
// --spot <map.json> <page.html> <files dir>: the pictures the numbers ask for, drawn by the real three.js (software GL,
// 1–2 s a frame): each flag's worst step on the key screens, and what only colour shows: the dive's amber light at its
// peak (not a black frame: the brightest 1 % of the canvas ≥ 100 of 255 (the black dips of fd91489 read 48–55); no lit
// panel: the canvas's 2 px rim no brighter than the page just outside it + 12) and the booster's amber glass at S3 (its probe
// point, CIE76 ΔE against R15's #9b6630 ≤ 15). Writes <out>/spot/*.png and <out>/spot.json
async function spot(mapFile, pageFile, files, out) {
  const { chromium } = require('playwright');
  const map = JSON.parse(fs.readFileSync(mapFile, 'utf8')), html0 = fs.readFileSync(pageFile, 'utf8');
  const shell = b => '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>' + b + '</body></html>';
  const three = threeFile(), font = fontFile();
  const vids = (opt('--viewports', 'key') === 'key' ? KEYVP : opt('--viewports').split(',')).filter(v => map.screens[v]);
  const dir = path.join(out, 'spot'); fs.mkdirSync(dir, { recursive: true });
  const lab = (r, g, b) => { const f = c => { c /= 255; c = c > 0.04045 ? ((c + 0.055) / 1.055) ** 2.4 : c / 12.92; return c; };
    const R = f(r), G = f(g), B = f(b), X = (0.4124 * R + 0.3576 * G + 0.1805 * B) / 0.95047, Y = 0.2126 * R + 0.7152 * G + 0.0722 * B, Z = (0.0193 * R + 0.1192 * G + 0.9505 * B) / 1.08883;
    const h = t => t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116; return [116 * h(Y) - 16, 500 * (h(X) - h(Y)), 200 * (h(Y) - h(Z))]; };
  const AMBER = lab(0x9b, 0x66, 0x30), res = [];
  const live = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  let nogl = null;
  for (const id of vids) {
    const m = map.screens[id], vp = parseVp(id), jobs = [];
    const b = vp.kind === 'nogl' ? (nogl = nogl || await chromium.launch({ args: ['--disable-3d-apis'] })) : live;
    // a flag's worst step (a span, a resolution, a static layout need no picture); at most 3 per kind (--classes: only these)
    const only = opt('--classes') ? opt('--classes').split(',') : null, per = {};
    for (const f of m.flags.slice().sort((x, y) => (y.v && y.v.h || 0) - (x.v && x.v.h || 0))) {
      if (/RUN_SPAN|HD|LAYOUT/.test(f.cls) || (only && !only.includes(f.cls))) continue;
      const k = f.cls + '/' + f.sub; if ((per[k] = (per[k] || 0) + 1) > 3) continue;
      jobs.push({ why: k, y: f.at != null ? f.at : f.y[0], test: f.sub === 'dim' ? 'dive' : null });
    }
    const colour = !only || only.includes('colour'), glow = colour && (m.design.find(x => x.kind === 'FADE:amber-glow') || {}).y;
    if (glow && glow[0]) for (const t of [0.25, 0.5, 0.75]) jobs.push({ why: 'dive-light-' + t * 100, y: Math.round(glow[0][0] + t * (glow[0][1] - glow[0][0])), test: 'dive' });
    const s3 = colour && (m.holds || []).find(h => h.p === 3);   // a phone's block holds its pose while it scrolls away: its start
    if (s3) jobs.push({ why: 'amber-glass', y: m.mode === 'flow' ? s3.y[0] : Math.round((s3.y[0] + s3.y[1]) / 2), test: 'amber' });
    if (!jobs.length) continue;
    const ctx = await b.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: vp.dpr, isMobile: vp.touch, hasTouch: vp.touch });
    await ctx.route('**/*', r => { const u = new URL(r.request().url());
      if (u.host === 'fonts.googleapis.com') return r.fulfill({ body: "@font-face{font-family:'Rubik';src:url(https://fonts.gstatic.com/local/0.ttf) format('truetype');font-weight:100 900;font-display:block}", contentType: 'text/css' });
      if (u.host === 'fonts.gstatic.com') return fs.existsSync(font) ? r.fulfill({ path: font, contentType: 'font/ttf' }) : r.fulfill({ status: 404, body: '' });
      if (u.host === 'cdn.jsdelivr.net') return r.fulfill({ path: three, contentType: 'application/javascript', headers: { 'access-control-allow-origin': '*' } });
      if (u.host === 'pagemap.test') { const rel = decodeURIComponent(u.pathname.slice(1));
        if (!rel) return r.fulfill({ body: shell(vp.kind === 'nojs' ? html0.replace(/<script\b[\s\S]*?<\/script>/gi, '') : html0), contentType: 'text/html; charset=utf-8' });
        const f = path.join(files, rel); return fs.existsSync(f) ? r.fulfill({ path: f }) : r.fulfill({ status: 404, body: '' }); }
      return r.abort(); });
    const p = await ctx.newPage(); await p.goto('https://pagemap.test/', { waitUntil: 'load' });
    if (vp.kind !== 'nojs') await p.waitForFunction(() => window.__seq && /\b(story|no-gl)\b/.test(document.documentElement.className), null, { timeout: 90000 }).catch(() => {});
    await p.evaluate(() => document.querySelectorAll('img[loading="lazy"]').forEach(i => { i.loading = 'eager'; }));
    await p.waitForTimeout(2000);
    for (const j of jobs) {
      await p.evaluate(y => scrollTo(0, y), j.y);
      let last = ''; for (let k = 0; k < 40; k++) { await p.waitForTimeout(300); const v = await p.evaluate(() => String(window.__mtP) + document.documentElement.className); if (v === last && k > 2) break; last = v; }
      await p.waitForTimeout(600);
      const png = await p.screenshot({ scale: 'css' }), file = path.join(dir, `${id}-y${j.y}-${j.why.replace(/\W+/g, '_')}.png`);
      fs.writeFileSync(file, png);
      const info = await p.evaluate(async ([b64, test]) => {
        const im = new Image(); im.src = 'data:image/png;base64,' + b64; await im.decode();
        const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d'); x.drawImage(im, 0, 0);
        const cv = document.getElementById('seq') ? document.getElementById('seq').getBoundingClientRect() : { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }, r = [Math.max(0, cv.left), Math.max(0, cv.top), Math.min(innerWidth, cv.right), Math.min(innerHeight, cv.bottom)].map(Math.round);
        const L = (d, i) => 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
        const out = { canvas: r };
        if (test === 'dive' && r[2] > r[0] && r[3] > r[1]) {
          const d = x.getImageData(r[0], r[1], r[2] - r[0], r[3] - r[1]).data, ls = []; for (let i = 0; i < d.length; i += 16) ls.push(L(d, i)); ls.sort((a, b) => b - a);
          out.top1 = Math.round(ls[Math.floor(ls.length / 100)]);
          // the canvas's 2 px rim against the page just outside it (3–6 px out, where the canvas does not reach): a lit panel
          // shows as a rim brighter than what surrounds it
          const W2 = c.width, H2 = c.height, all = x.getImageData(0, 0, W2, H2).data, rim = [], outside = [];
          const at = (px, py) => (px >= 0 && py >= 0 && px < W2 && py < H2) ? L(all, (py * W2 + px) * 4) : null;
          for (let px = r[0]; px < r[2]; px += 2) for (const [a, o] of [[r[1] + 1, r[1] - 4], [r[3] - 2, r[3] + 3]]) { const u = at(px, a), v = at(px, o); if (u != null && v != null) { rim.push(u); outside.push(v); } }
          for (let py = r[1]; py < r[3]; py += 2) for (const [a, o] of [[r[0] + 1, r[0] - 4], [r[2] - 2, r[2] + 3]]) { const u = at(a, py), v = at(o, py); if (u != null && v != null) { rim.push(u); outside.push(v); } }
          const q = a => { a.sort((m, n) => n - m); return a.length ? Math.round(a[Math.floor(a.length / 50)]) : 0; };
          out.rim = q(rim); out.page = q(outside);
        }
        if (test === 'amber') { const st = window.__seq().sceneState, a = st && st.probes && st.probes.amber;
          if (a) { const fx = r => r; const X = cv.left + (a[0] - 168) / 1080 * cv.width, Y = cv.top + (a[1] - 285) / 930 * cv.height;
            const d = x.getImageData(Math.round(X) - 2, Math.round(Y) - 2, 5, 5).data; let R = 0, G = 0, B = 0; for (let i = 0; i < d.length; i += 4) { R += d[i]; G += d[i + 1]; B += d[i + 2]; }
            out.amber = [R / 25, G / 25, B / 25].map(Math.round); out.at = [Math.round(X), Math.round(Y)]; } }
        return out; }, [png.toString('base64'), j.test]);
      if (info.amber) { const l = lab(...info.amber); info.dE = Math.round(Math.hypot(l[0] - AMBER[0], l[1] - AMBER[1], l[2] - AMBER[2])); }
      const ok = j.test === 'dive' ? info.top1 >= 100 && info.rim <= info.page + 12 : j.test === 'amber' ? info.dE != null && info.dE <= 15 : null;
      res.push(Object.assign({ screen: id, y: j.y, why: j.why, file: path.relative(out, file), pass: ok }, info));
      console.log(id, j.why, 'y', j.y, ok === null ? 'look' : ok ? 'PASS' : 'FAIL', JSON.stringify(info));
    }
    await ctx.close();
  }
  await live.close(); if (nogl) await nogl.close();
  fs.writeFileSync(path.join(out, 'spot.json'), JSON.stringify(res, null, 1));
}


// <out>/README.md: the roadmap of the 13 pages, regenerated whole: per page its kind, build, whether PAGES has its
// configuration, what the map needs first, and the last map's facts (read from <out>/<slug>.json when it exists)
const ALL13 = [['v-tech-system', 'V-TECH SYSTEM', 'https://claude.ai/artifact/NdQezU5bikrsuaWVVW5TBK'], ['exocell-mask', 'EXOCELL MASK', 'https://claude.ai/artifact/FA5ySxGihnDAmjQPvDftzn'],
  ['exotech-gel', 'EXOTECH GEL', 'https://claude.ai/artifact/LsJVky9GDssBuW1eQkLaTe'], ['exosignal-hair', 'EXOSIGNAL HAIR', 'https://claude.ai/artifact/2ws7qr1xL7Y7wp5xdbE1jh'],
  ['exosignal-spray', 'EXOSIGNAL SPRAY', 'https://claude.ai/artifact/GAUwhjxzqdk7jEg7JgSBJz'], ['exo-nad', 'EXO-NAD', 'https://claude.ai/artifact/NcP4v3p7KAdvqZGTnoGK8S'],
  ['micro-boost-10', 'MICRO BOOST 10%', 'https://claude.ai/artifact/3hwRLR8RxjcQV2oGTynari'], ['cellular-age-defense-2-5', 'CELLULAR AGE DEFENSE 2.5%', 'https://claude.ai/artifact/RhFJsLyLDinq2HcizL1hvq'],
  ['mitopen', 'MITOPEN', 'https://claude.ai/artifact/KAn13gS9E2on2ZikQSz4eW'], ['cell-renew-1-5', 'CELL RENEW 1.5%', 'https://claude.ai/artifact/2rVvsAFJ9NRUjymZDmANup'],
  ['mitoscan', 'MITOSCAN', 'https://claude.ai/artifact/KD3L1gfgVA8twY7HBvYofp'], ['derma-recovery-cream', 'DERMA RECOVERY CREAM', 'https://claude.ai/artifact/7a3EpTpcTbYMWjTypNk2pV'],
  ['mitotech-cell-booster', 'MITOTECH CELL BOOSTER', 'https://claude.ai/artifact/G3tdcwusRsVdw4E5HeGM5s']];
// what each page is built from (site/proto): the kind decides what the probe can measure
const ROADMAP = {
  'v-tech-system': { kind: 'кадры Blender, история v1', build: 'cd site/proto && python3 build-vtech.py --files <dir> --keys <keys>',
    needs: 'проба для движка кадров (рамки продукта по alpha-box кадров `seq/runs.json`, не three-nodraw); хуки `__seq` есть' },
  'exocell-mask': { kind: 'EXOCELL 3D, свой шаблон `exocell-3d-template.html`', build: 'cd site/proto && python3 build-exocell.py 3d --out <dir>',
    needs: 'хуки пробы в шаблоне (нет `window.__seq`) — только вместе со следующей публикацией страницы; конфиг PAGES' },
  'mitotech-cell-booster': { kind: 'сцена three.js, история v2 (`story_content.V2`)' },
};
const SCENE_V1 = { kind: 'сцена three.js, история v1', build: 'cd site/proto && python3 build-vtech.py --product <slug> --scene --files <dir> --keys <keys> --links artifact',
  needs: 'PAGES[<slug>] в pagemap.cjs: объекты по индексу `scene.children`, детали тела, подписи удержаний, прогонов и блоков; у v1 нет `__mtP`/`__mtCards`/`.mt-step` — поза берётся из `__seq().pos` (проба это уже умеет)' };
const OPEN12 = { 'exosignal-spray': 'пакшот SPRAY', 'exo-nad': 'фото EXO-NAD в полном размере', 'derma-recovery-cream': 'банка DERMA в HD', 'mitopen': 'данные MITOPEN',
  'mitoscan': 'данные MITOSCAN', 'exotech-gel': 'цвет геля', 'exocell-mask': 'кадр зеркала MASK ≥ 1196 px', 'cell-renew-1-5': '«ок» телефонного образца (T1)' };
function writeReadme(out, map) {
  const f = path.join(out, 'README.md');
  const row = (sl, name, link) => {
    const rm = ROADMAP[sl] || SCENE_V1, cfg = PAGES[sl], jf = path.join(out, sl + '.json');
    let m = sl === map.page ? map : null; if (!m && fs.existsSync(jf)) try { m = JSON.parse(fs.readFileSync(jf, 'utf8')); } catch (e) { m = null; }
    const kind = rm.kind, build = '`' + (cfg && cfg.build || rm.build || '—').replace(/<slug>/g, sl) + '`', has = cfg ? 'есть' : 'нет', needs = rm.needs || (cfg ? '—' : SCENE_V1.needs);
    if (!m || !m.screens) return `| ${name} | \`${sl}\` | ${link} | ${kind} | ${build} | ${has} | ${needs} | — | карта ещё не построена | — | — | ${OPEN12[sl] ? OPEN12[sl] + '; ' : ''}размеры коробки в мм; см. \`HANDOFF-session.md\` «Ждёт заказчика» |`;
    const ids = Object.keys(m.screens), live = ids.filter(id => m.screens[id].mode !== 'still'), still = ids.filter(id => m.screens[id].mode === 'still');
    const cnt = list => { const c = {}; for (const id of list) for (const fl of m.screens[id].flags) c[fl.cls] = (c[fl.cls] || 0) + 1; return Object.entries(c).map(([k, v]) => `${k} ${v}`).join(', '); };
    const nl = live.reduce((a, id) => a + m.screens[id].flags.length, 0), ns = still.reduce((a, id) => a + m.screens[id].flags.length, 0), nr = ids.reduce((a, id) => a + (m.screens[id].rules || []).length, 0);
    const flags = [nl ? `живые экраны: ${cnt(live)}` : 'живые экраны: чисто', ns ? `без JS/WebGL: ${cnt(still)}` : null, nr ? `правила: ${distinct(ids.flatMap(id => (m.screens[id].rules || []).map(r => r.cls))).join(', ')}` : null].filter(Boolean).join('; ');
    const lay = m.layout ? `L1–L8: ${m.layout.high} high, ${m.layout.low} low (\`${m.layout.file}\`)` : '—';
    const pend = [].concat(cfg && cfg.pending ? ['«ок» на образце'] : [], nr ? ['длина прогона 0 на телефонах'] : [], ns ? ['кадры без JS/WebGL: править или принять'] : [],
      cfg && cfg.questions ? [cfg.questions.short ? 'тексты ' + cfg.questions.short : 'тексты'] : [], cfg && cfg.questions && cfg.questions.extra ? cfg.questions.extra.map(e => e.split(' — ')[0]) : [],
      [m.looked ? `взгляд картинками ${whenRu(m.looked.date)}: ${m.looked.fail ? m.looked.fail + ' FAIL' : 'PASS'}` : 'взгляд картинками не записан']);
    return `| ${name} | \`${sl}\` | ${link} | ${kind} | ${build} | ${has} | ${needs} | md5 \`${m.build.md5.slice(0, 8)}\`${m.build.rev ? ' (' + m.build.rev + ')' : ''} | ${whenRu(m.date)}, ${ids.length} режимов за ${m.timing.total_s} с | ${flags} (\`${sl}.md\`) | ${lay} | ${pend.join('; ')} |`;
  };
  const txt = ['# Карты страниц сайта — дорожная карта', '',
    'Карта страницы — машиночитаемое описание того, что где на странице на каждом экране (`<slug>.json`, легенда внутри) и рабочая заметка по ней (`<slug>.md`):',
    'экраны и диапазоны прокрутки, прогоны и их длина, позиции истории p, удержания и что в них видно, рамка продукта через каждые 10 px (ключевые экраны), картинки, тексты, флаги проверок.',
    'Строит её `site/proto/qa/pagemap.cjs` (three.js без рисования: секунды на экран вместо часов рендера) после каждой сборки страницы;',
    'проверки правил заказчика идут по числам, картинки — только там, где числа нашли подозрение (`--spot`), и финальный взгляд на 4 экрана.',
    'Инструмент, легенда, пороги и калибровка — `site/proto/qa/pagemap.md`; правила вёрстки L1–L8 — `site/proto/qa/layout-check.cjs` (`<slug>.layout.{json,md}`, `design-rules.md`).',
    'Ссылки страниц — `site/HANDOFF-dev.he.md` и `HANDOFF-session.md`. Пути в таблице — от `mitoderm-catalog/`.', '',
    '**Как пересобрать карту** (около 2 мин на 15 режимов, 4 CPU без GPU): `cd site/proto && NODE_PATH=$(npm root -g) THREE=<three@0.160.0/build/three.module.min.js> node qa/pagemap.cjs <dir>/<slug>-live.html <dir> --out ../pagemap --raw <scratch>/raw --keys <keys> --build-cmd "<команда сборки>" [--looked <spot.json>]`.',
    'three.js: `npm i --no-save three@0.160.0` в рабочей папке (или `--three <file>`); шрифт — `qa/fonts/Rubik[wght].ttf` (в репозитории); без них инструмент останавливается. Сборки и ключевые кадры — вне репозитория (рабочая папка сессии); опубликованные сборки опознаются по md5 и ревизии файлов страницы в `build`.', '',
    '**Порядок и ворота.** Карты остальных 12 страниц — после «ок» заказчика на образце MITOTECH (PLAN). Затем по одной: 1) 10 страниц-сцен истории v1 (одинаковый шаблон и движок: конфиг `PAGES[<slug>]` → карта → `--spot` → взгляд на 4 экрана), начиная с EXOTECH GEL и EXOCELL-подобных эталонов вёрстки; 2) EXOCELL MASK — хуки пробы в её шаблоне вместе со следующей публикацией; 3) V-TECH — проба для движка кадров. Опубликованные 12 страниц при этом не меняются: карта читает сборку, какая она есть.', '',
    '| страница | slug | ссылка | тип | сборка | PAGES | что нужно до карты | последняя сборка | последняя проверка | флаги | вёрстка | ждёт решения |', '|---|---|---|---|---|---|---|---|---|---|---|---|',
    ...ALL13.map(([sl, name, link]) => row(sl, name, link)), ''].join('\n');
  fs.writeFileSync(f, txt);
}

// run last: every const above is initialised
if (require.main === module) main().catch(e => { console.error(e); process.exit(1); });
