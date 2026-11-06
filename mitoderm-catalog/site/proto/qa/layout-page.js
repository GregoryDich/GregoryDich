// layout-page.js: the in-page half of layout-check.cjs (installed with context.addInitScript, before the page's own
// scripts). It only reads the page: DOM geometry, computed styles, Range rects of the words, the alpha of the product
// pictures (image files at their natural size, 2D canvases, and the WebGL canvas, whose drawing buffer is kept for
// that) and the engines' QA state (window.__seq().sceneState.aabb on the template pages, window.__objRects on MASK).
// No screenshots. Everything is in CSS px of the viewport unless a name says otherwise; rects are [left, top, right, bottom].
(() => {
  if (window.__LC) return;
  // keep the WebGL drawing buffer after a frame is shown, so the product's drawn pixels can be read later (no visual change)
  const gc = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, attrs) {
    if (/webgl/i.test(String(type))) attrs = Object.assign({}, attrs || {}, { preserveDrawingBuffer: true });
    return gc.call(this, type, attrs);
  };
  const LC = window.__LC = { version: 1 };
  const r1 = v => Math.round(v * 10) / 10, r3 = v => Math.round(v * 1000) / 1000;
  const R = r => [r1(r.left), r1(r.top), r1(r.right), r1(r.bottom)];
  const q = (s, el = document) => el.querySelector(s), qa = (s, el = document) => Array.from(el.querySelectorAll(s));
  const cs = el => getComputedStyle(el);
  const shown = el => {
    if (!el || !el.getClientRects().length) return false;
    if (el.checkVisibility && !el.checkVisibility({ visibilityProperty: true, contentVisibilityAuto: true })) return false;   // a closed <details>' content too
    const s = cs(el); if (s.visibility === 'hidden' || s.display === 'none') return false;
    const r = el.getBoundingClientRect(); return r.width > 0.5 && r.height > 0.5;
  };
  const opac = el => { let o = 1; for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= +cs(e).opacity; return o; };
  const sig = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (typeof el.className === 'string' && el.className.trim() ? '.' + el.className.trim().split(/\s+/).join('.') : '');
  const path = el => { const p = []; for (let e = el; e && e !== document.body && p.length < 4; e = e.parentElement) p.unshift(sig(e)); return p.join(' > '); };
  const union = rs => rs.length ? [Math.min(...rs.map(r => r[0])), Math.min(...rs.map(r => r[1])), Math.max(...rs.map(r => r[2])), Math.max(...rs.map(r => r[3]))] : null;

  // ---------- colours and contrast (WCAG 2.x) on the page's colour tokens
  const parseColor = s => { const m = String(s).match(/rgba?\(([^)]+)\)/); if (!m) return null; const v = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
  const over = (top, bot) => { const a = top[3] + bot[3] * (1 - top[3]); if (a <= 0) return [0, 0, 0, 0]; return [0, 1, 2].map(i => (top[i] * top[3] + bot[i] * bot[3] * (1 - top[3])) / a).concat(a); };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const contrast = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const gradColors = img => (String(img).match(/rgba?\([^)]+\)/g) || []).map(parseColor);
  function background(el) {   // the colour under el's text: its own and its ancestors' backgrounds over the page's base
    const layers = [];
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const s = cs(e), c = parseColor(s.backgroundColor), g = s.backgroundImage !== 'none' ? gradColors(s.backgroundImage) : [];
      if (g.length) layers.push({ g }); else if (c && c[3] > 0) layers.push({ c });
      if ((c && c[3] >= 0.999) || (g.length && g.every(x => x[3] >= 0.999))) break;
    }
    const base = parseColor(cs(document.body).backgroundColor) || [10, 10, 11, 1];
    // a gradient: every stop is a candidate (the worst one counts)
    let cands = [[...base]];
    for (const L of layers.reverse()) {
      if (L.c) cands = cands.map(b => over(L.c, b));
      else cands = cands.flatMap(b => L.g.map(g => over(g, b)));
    }
    return cands;
  }
  function textContrast(el) {
    const fg = parseColor(cs(el).color) || [255, 255, 255, 1], o = opac(el), bgs = background(el);
    let worst = 99, wbg = null;
    for (const b of bgs) { const f = over([fg[0], fg[1], fg[2], fg[3] * o], b); const k = contrast(f, b); if (k < worst) { worst = k; wbg = b; } }
    return { ratio: Math.round(worst * 100) / 100, fg: fg.map(v => Math.round(v * 1000) / 1000), bg: wbg && wbg.map(v => Math.round(v)) };
  }

  // ---------- text: words → lines (Range rects), baselines and ink from the font's own metrics (canvas measureText)
  const mctx = document.createElement('canvas').getContext('2d'), mcache = new Map();
  function metrics(fontCss, text) {
    const k = fontCss + '|' + text; let m = mcache.get(k);
    if (!m) { mctx.font = fontCss; const t = mctx.measureText(text); m = { fa: t.fontBoundingBoxAscent, fd: t.fontBoundingBoxDescent, ia: t.actualBoundingBoxAscent, id: t.actualBoundingBoxDescent }; mcache.set(k, m); }
    return m;
  }
  const fontOf = s => `${s.fontStyle === 'italic' ? 'italic ' : ''}${s.fontWeight} ${s.fontSize} ${s.fontFamily}`;
  const textShown = n => { const p = n.parentElement; if (!p || !p.getClientRects().length) return false; const s = cs(p); return s.visibility !== 'hidden' && s.display !== 'none'; };
  function lines(el) {
    const words = [], tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n; (n = tw.nextNode());) {
      if (!/\S/.test(n.data) || !textShown(n)) continue;
      const s = cs(n.parentElement), font = fontOf(s), re = /\S+/g; let m;
      while ((m = re.exec(n.data))) {
        const rg = document.createRange(); rg.setStart(n, m.index); rg.setEnd(n, m.index + m[0].length);
        const rs = Array.from(rg.getClientRects()).filter(x => x.width > 0.2 && x.height > 0.2);
        rs.forEach((x, i) => { const mt = metrics(font, m[0]), base = x.top + mt.fa;
          words.push({ l: x.left, t: x.top, r: x.right, b: x.bottom, s: m[0], n: i ? 0 : m[0].length, base, he: /[\u0590-\u05FF]/.test(m[0]),
            capHe: base - metrics(font, '\u05D4').ia, capLa: base - metrics(font, 'H').ia, inkB: base + mt.id, fs: parseFloat(s.fontSize) }); });
      }
    }
    const out = [];
    words.sort((a, b) => a.base - b.base);
    for (const w of words) {
      let L = out.find(L => Math.abs(L.base - w.base) < 0.45 * Math.max(L.fs, w.fs) || (w.t < L.b - 0.3 * (L.b - L.t) && w.b > L.t + 0.3 * (L.b - L.t)));
      if (!L) { L = { l: w.l, t: w.t, r: w.r, b: w.b, base: w.base, inkB: w.inkB, fs: w.fs, ws: [] }; out.push(L); }
      L.l = Math.min(L.l, w.l); L.r = Math.max(L.r, w.r); L.t = Math.min(L.t, w.t); L.b = Math.max(L.b, w.b);
      L.inkB = Math.max(L.inkB, w.inkB);
      if (w.fs > L.fs) { L.fs = w.fs; L.base = w.base; }
      L.ws.push(w);
    }
    out.sort((a, b) => a.t - b.t);
    for (const L of out) { const he = L.ws.some(w => w.he); L.inkT = Math.min(...L.ws.map(w => he ? w.capHe : w.capLa)); }
    return out.map(L => ({ l: r1(L.l), t: r1(L.t), r: r1(L.r), b: r1(L.b), base: r1(L.base), inkT: r1(L.inkT), inkB: r1(L.inkB), fs: L.fs,
      words: L.ws.filter(w => w.n).length, chars: L.ws.reduce((a, w) => a + w.n, 0) + Math.max(0, L.ws.filter(w => w.n).length - 1),
      text: L.ws.slice().sort((a, b) => b.r - a.r).map(w => w.s).join(' ').slice(0, 120) }));
  }

  // ---------- picture content: the alpha box of an image at its natural size (cached), mapped through object-fit
  const acache = new Map();
  function alphaOf(src, w, h, draw) {   // { bbox:[x0,y0,x1,y1] in source px, w, h, mask (a coarse grid) }
    const key = src && src.length > 200 ? src.length + ':' + src.slice(0, 64) + src.slice(-64) : src;
    if (key && acache.has(key)) return acache.get(key);
    let res = null;
    try {
      const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d', { willReadFrequently: true });
      draw(x); const d = x.getImageData(0, 0, w, h).data;
      let x0 = w, y0 = h, x1 = -1, y1 = -1; const G = 96, gw = Math.max(1, Math.ceil(w / G)), gh = Math.max(1, Math.ceil(h / G)), mask = new Uint8Array(G * G);
      for (let y = 0; y < h; y++) for (let i = 0; i < w; i++) if (d[(y * w + i) * 4 + 3] > 24) {
        if (i < x0) x0 = i; if (i > x1) x1 = i; if (y < y0) y0 = y; if (y > y1) y1 = y;
        mask[Math.min(G - 1, Math.floor(y / gh)) * G + Math.min(G - 1, Math.floor(i / gw))] = 1;
      }
      res = { w, h, bbox: x1 < 0 ? null : [x0, y0, x1 + 1, y1 + 1], mask, G, gw, gh };
    } catch (e) { res = { w, h, bbox: null, err: String(e).slice(0, 80) }; }
    if (key) acache.set(key, res);
    return res;
  }
  const imgAlpha = im => im.complete && im.naturalWidth ? alphaOf(im.currentSrc || im.src, im.naturalWidth, im.naturalHeight, x => x.drawImage(im, 0, 0)) : null;
  function canvasAlpha(cv) {   // a 2D canvas, or a WebGL one (its kept drawing buffer); never cached (it changes)
    if (!cv.width || !cv.height) return null;
    const k = Math.min(1, 1400 / Math.max(cv.width, cv.height)), w = Math.max(1, Math.round(cv.width * k)), h = Math.max(1, Math.round(cv.height * k));
    const a = alphaOf(null, w, h, x => x.drawImage(cv, 0, 0, w, h));
    return a && Object.assign(a, { sx: cv.width / w, sy: cv.height / h });
  }
  function objectBox(el, nw, nh) {   // where an image's pixels land in el's content box: [x, y, w, h], css px
    const r = el.getBoundingClientRect(), s = cs(el);
    const bl = parseFloat(s.borderLeftWidth) + parseFloat(s.paddingLeft), bt = parseFloat(s.borderTopWidth) + parseFloat(s.paddingTop);
    const bw = r.width - bl - parseFloat(s.borderRightWidth) - parseFloat(s.paddingRight), bh = r.height - bt - parseFloat(s.borderBottomWidth) - parseFloat(s.paddingBottom);
    const fit = s.objectFit || 'fill', pos = (s.objectPosition || '50% 50%').split(' ');
    const pct = (v, free) => /%$/.test(v) ? parseFloat(v) / 100 * free : v === 'left' || v === 'top' ? 0 : v === 'right' || v === 'bottom' ? free : v === 'center' ? free / 2 : parseFloat(v) || 0;
    let w = bw, h = bh;
    if (fit === 'contain' || fit === 'scale-down') { const k = Math.min(bw / nw, bh / nh, fit === 'scale-down' ? 1 : Infinity); w = nw * k; h = nh * k; }
    else if (fit === 'cover') { const k = Math.max(bw / nw, bh / nh); w = nw * k; h = nh * k; }
    else if (fit === 'none') { w = nw; h = nh; }
    return { x: r.left + bl + pct(pos[0], bw - w), y: r.top + bt + pct(pos[1] || '50%', bh - h), w, h, box: [r.left + bl, r.top + bt, r.left + bl + bw, r.top + bt + bh], fit };
  }
  function pictureOf(el, laidOut) {   // an <img> or a canvas: its box, the drawn content rect, distortion, and a mask for overlap tests
    if (!el || !(laidOut ? el.getClientRects().length && cs(el).display !== 'none' : shown(el))) return null;
    const out = { sel: path(el), op: r3(opac(el)) };
    if (el.tagName === 'IMG') {
      const a = imgAlpha(el); if (!a) return Object.assign(out, { err: 'not loaded' });
      const o = objectBox(el, el.naturalWidth, el.naturalHeight), kx = o.w / el.naturalWidth, ky = o.h / el.naturalHeight;
      Object.assign(out, { kind: 'img', src: (el.currentSrc || el.src).replace(/^data:([^;,]+)[^]*$/, 'data:$1'), nat: [el.naturalWidth, el.naturalHeight], fit: o.fit,
        elBox: R(el.getBoundingClientRect()), box: o.box.map(r1), drawn: [o.x, o.y, o.x + o.w, o.y + o.h].map(r1),
        distortion: r3(Math.abs((o.w / o.h) / (el.naturalWidth / el.naturalHeight) - 1)) });
      if (a.bbox) { const b = a.bbox, c = [o.x + b[0] * kx, o.y + b[1] * ky, o.x + b[2] * kx, o.y + b[3] * ky];
        // clipped by the box (object-fit: cover, overflow)
        out.content = [Math.max(c[0], o.box[0]), Math.max(c[1], o.box[1]), Math.min(c[2], o.box[2]), Math.min(c[3], o.box[3])].map(r1); }
      out._map = { a, x: o.x, y: o.y, kx, ky };
      return out;
    }
    if (el.tagName === 'CANVAS') {
      const r = el.getBoundingClientRect(), a = canvasAlpha(el); if (!a) return Object.assign(out, { err: 'empty canvas' });
      const kx = r.width / el.width * a.sx, ky = r.height / el.height * a.sy;
      Object.assign(out, { kind: 'canvas', px: [el.width, el.height], elBox: R(r), box: R(r), distortion: r3(Math.abs((r.width / r.height) / (el.width / el.height) - 1)) });
      if (a.bbox) out.content = [r.left + a.bbox[0] * kx, r.top + a.bbox[1] * ky, r.left + a.bbox[2] * kx, r.top + a.bbox[3] * ky].map(r1);
      out._map = { a, x: r.left, y: r.top, kx, ky };
      return out;
    }
    return null;
  }
  // share of a rect covered by a picture's drawn pixels (its coarse alpha grid; 0 when none)
  function coverage(pic, rc) {
    if (!pic || !pic._map || !pic._map.a || !pic._map.a.mask) return pic && pic.content ? (inter(pic.content, rc) > 0 ? 1 : 0) : 0;
    const { a, x, y, kx, ky } = pic._map, G = a.G; let hit = 0, all = 0;
    const gx0 = Math.max(0, Math.floor((rc[0] - x) / kx / a.gw)), gx1 = Math.min(G - 1, Math.floor((rc[2] - x) / kx / a.gw));
    const gy0 = Math.max(0, Math.floor((rc[1] - y) / ky / a.gh)), gy1 = Math.min(G - 1, Math.floor((rc[3] - y) / ky / a.gh));
    for (let gy = gy0; gy <= gy1; gy++) for (let gx = gx0; gx <= gx1; gx++) { all++; hit += a.mask[gy * G + gx]; }
    return all ? r3(hit / all) : 0;
  }
  const inter = (a, b) => Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])) * Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]));
  LC.coverage = coverage;

  // ---------- page chrome and adapter
  function env() {
    const W = innerWidth, H = innerHeight, html = document.documentElement, cls = html.className;
    const top = q('.top'), dock = q('.dock'), bar = q('.bar');
    const hb = top && shown(top) ? top.getBoundingClientRect().bottom : 0;
    const dk = dock && shown(dock) ? R(dock.getBoundingClientRect()) : null;
    const br = bar && shown(bar) && !bar.classList.contains('away') ? R(bar.getBoundingClientRect()) : null;
    const story = !!window.__seq, mask = !!window.__anchorY;
    const flow = html.classList.contains('flow'), nogl = html.classList.contains('no-gl') || html.classList.contains('nogl');
    const stageMode = story && !flow && html.classList.contains('story') && matchMedia('(max-width: 899px)').matches;
    let stage = null;
    if (stageMode) { const st = parseFloat(html.style.getPropertyValue('--stage-top')) || hb, sh = parseFloat(html.style.getPropertyValue('--stage-h')) || 0.46 * H, push = parseFloat(html.style.getPropertyValue('--push')) || 0;
      if (push < st + sh) stage = [0, r1(st - push), W, r1(st + sh - push)]; }
    const freeTop = Math.max(hb, stage ? stage[3] : 0), freeBot = Math.min(H, dk ? dk[1] : H, br ? br[1] : H);
    const wrap = q('main .sec:not(.open):not(.hero) > .wrap') || q('main .sec .wrap') || q('.wrap');
    return { W, H, dpr: devicePixelRatio, cls, adapter: story ? 'story' : mask ? 'mask' : 'plain', flow, nogl, stageMode, stage,
      phone: mask ? matchMedia('(max-width: 760px)').matches : matchMedia('(max-width: 899px)').matches,
      header: top && shown(top) ? R(top.getBoundingClientRect()) : null, dock: dk, bar: br, free: [r1(freeTop), r1(freeBot)],
      wrap: wrap ? R(wrap.getBoundingClientRect()) : null, docW: html.scrollWidth, docH: html.scrollHeight, scrollY: r1(scrollY) };
  }
  LC.env = env;

  // the story screens of a page, in story order
  const STORY_IDS = ['open', 'meet', 'why', 'inside', 'feel', 'protocol', 'offer'];
  function screens() {
    if (window.__anchorY) return qa('main [data-st]').filter(s => s.matches('.sec') && !s.matches('.spec-sec')).map(s => ({ id: s.id, el: s, st: +s.dataset.st }));
    const st = window.__seq ? window.__seq() : null, n = st ? st.R + 1 : 6;
    let ids = STORY_IDS.filter(id => { const e = document.getElementById(id); return e && e.matches('section'); });
    if (ids.length > n) ids = ids.slice(ids.length - n);   // a page without the opening (#open hidden or absent)
    return ids.map(id => ({ id, el: document.getElementById(id) }));
  }
  // the copy column of a screen and its blocks, top to bottom (display: contents wrappers are opened)
  function column(sec) {
    const c = q(':scope > .wrap > .copy', sec) || q(':scope > .wrap > .offer-copy', sec) || q(':scope .copy', sec) || q(':scope .offer-copy', sec)
      || q(':scope .split > .col', sec) || q(':scope > .wrap', sec) || sec;
    return cs(c).display === 'contents' ? c.parentElement : c;
  }
  function role(el) {
    const m = s => el.matches(s);
    if (m('.stage, .ph-slot, img.slot')) return 'stage';
    if (m('.badges')) return 'badges'; if (m('.kicker')) return 'kicker'; if (m('h1')) return 'h1'; if (m('h2')) return 'h2'; if (m('h3, h4')) return 'h3';
    if (m('.tag')) return 'tag'; if (m('.chips')) return 'chips'; if (m('.pins')) return 'pins'; if (m('.cta')) return 'cta'; if (m('details')) return 'details';
    if (m('.pill, .dbl')) return 'pill'; if (m('.contacts')) return 'contacts'; if (m('.note, .hours')) return 'note'; if (m('.facts')) return 'facts';
    if (m('.filter')) return 'filter'; if (m('.legend')) return 'legend'; if (m('.kc-head')) return 'khead'; if (m('.n')) return 'num'; if (m('.chip')) return 'chip';
    if (m('.kitcard')) return 'card'; if (m('.steps, .mt-prep')) return 'cards'; if (m('p')) return 'lead';
    return el.tagName.toLowerCase();
  }
  const BOXY = new Set(['badges', 'chips', 'pins', 'cta', 'details', 'pill', 'contacts', 'facts', 'filter', 'stage', 'khead', 'chip', 'card', 'cards']);
  function blocksOf(col) {
    const out = [];
    const walk = p => { for (const c of p.children) {
      if (cs(c).display === 'contents' || c.matches('.head')) { walk(c); continue; }
      if (c.matches('.stage') && !shown(c)) continue;
      if (!shown(c) || opac(c) < 0.05) continue;
      if (c.matches('.slot') && !c.matches('.stage')) continue;   // the template's still beside the heading: a picture, not copy
      out.push(c);
    } };
    walk(col);
    return out;
  }
  function block(el) {
    const rl = role(el), r = el.getBoundingClientRect(), s = cs(el);
    const b = { role: rl, sel: path(el), rect: R(r), font: { size: parseFloat(s.fontSize), weight: s.fontWeight, lh: s.lineHeight, ls: s.letterSpacing } };
    if (rl === 'stage') return b;
    if (BOXY.has(rl)) {
      const items = rl === 'card' || rl === 'cards' || rl === 'chip' ? [] : Array.from(el.children).filter(shown);   // a filter's label is its row's first item
      b.items = items.map(c => R(c.getBoundingClientRect()));
      const li = items.findIndex(c => c.matches('.lbl')); if (li >= 0) b.labelIdx = li;
      b.inkT = r1(r.top); b.inkB = r1(r.bottom); b.inkL = r1(r.left); b.inkR = b.items.length ? Math.max(...b.items.map(x => x[2])) : r1(r.right);
      if (rl === 'details') { b.inkR = r1(r.right); }
      if (rl === 'chips' || rl === 'pins' || rl === 'pill' || rl === 'badges') {   // their text: lines per item (contrast and line length)
        const it = el.matches('.pill, .dbl') ? [el] : Array.from(el.children).filter(shown);
        b.itemText = it.map(c => ({ chars: (c.textContent || '').trim().length, lines: lines(c).length, contrast: textContrast(c).ratio, fs: parseFloat(cs(c).fontSize) }));
      }
      return b;
    }
    const L = lines(el);
    b.lines = L.map(({ text, ...x }) => x); b.text = L.map(x => x.text).join(' / ').slice(0, 200);
    if (L.length) { b.inkT = L[0].inkT; b.inkB = L[L.length - 1].base; b.inkL = Math.min(...L.map(x => x.l)); b.inkR = Math.max(...L.map(x => x.r)); }
    else { b.inkT = r1(r.top); b.inkB = r1(r.bottom); b.inkL = r1(r.left); b.inkR = r1(r.right); }
    b.contrast = textContrast(el);
    return b;
  }
  LC.blocksOf = col => blocksOf(col).map(block);

  // ---------- the product on a screen
  function storyBox(p) {   // the run's box in the 16:10 frame (the engine draws the pose for p into it)
    const st = window.__seq(), k = Math.max(0, Math.min(st.R - 1, Math.floor(p + 1e-6)));
    let cfg = null;
    if (Array.isArray(window.__mtCfg)) cfg = window.__mtCfg[matchMedia('(max-width: 899px)').matches ? 0 : 1];
    const box = cfg && cfg.runs[k] ? cfg.runs[k].box : (k === 0 && document.getElementById('open') ? [0, 0, 1, 1] : [0.07, 0.19, 0.52, 0.81]);
    return { k, box };
  }
  function storyProduct() {
    const cv = q('#seq'), st = window.__seq && window.__seq(); if (!cv || !st) return null;
    const s = cs(cv), op = +s.opacity;
    if (s.display === 'none' || s.visibility === 'hidden' || op < 0.05 || document.documentElement.classList.contains('mt-cards0')) return { hidden: true, op };
    const pic = pictureOf(cv); if (!pic) return { hidden: true };
    const ss = st.sceneState, p = typeof window.__mtP === 'number' ? window.__mtP : st.pos;
    const out = { src: 'canvas-alpha', p: r3(p), drawnP: ss && ss.drawn, pic, rect: pic.content || null };
    if (ss && ss.aabb) {   // the scene's outline in frame px, mapped by the cover: the canvas's rect = the run's box of the cover
      const r = cv.getBoundingClientRect(), { box } = storyBox(ss.drawn != null ? ss.drawn : p);
      const cw = r.width / (box[2] - box[0]), ch = r.height / (box[3] - box[1]), cx = r.left - box[0] * cw, cy = r.top - box[1] * ch;
      const a = ss.aabb; out.aabb = a; out.aabbRect = [cx + a[0] / 2400 * cw, cy + a[1] / 1500 * ch, cx + a[2] / 2400 * cw, cy + a[3] / 1500 * ch].map(r1);
      if (!document.documentElement.classList.contains('flow') && !matchMedia('(max-width: 899px)').matches) {   // desktop: the engine's cover s = max(W/16, H/10)
        const S = Math.max(innerWidth / 16, innerHeight / 10), X = (innerWidth - 16 * S) / 2, Y = (innerHeight - 10 * S) / 2;
        out.coverRect = [X + a[0] / 2400 * 16 * S, Y + a[1] / 1500 * 10 * S, X + a[2] / 2400 * 16 * S, Y + a[3] / 1500 * 10 * S].map(r1);
      }
      out.edge = ss.edge;
    }
    return out;
  }
  function maskProduct() {
    let rs = []; try { rs = (window.__objRects && window.__objRects()) || []; } catch (e) {}
    if (!rs.length) return { hidden: true };
    const host = q('.ph-gl') && q('.ph-gl').closest('.ph-slot');
    return { src: 'objRects', rect: union(rs).map(r1), parts: rs.map(r => r.map(r1)), host: host ? R(host.getBoundingClientRect()) : null };
  }
  LC.product = () => window.__seq ? storyProduct() : window.__anchorY ? maskProduct() : null;

  // ---------- one screen at the current scroll
  LC.screen = function (id) {
    const E = env(), sec = document.getElementById(id) || q(id); if (!sec) return { id, err: 'no section' };
    const col = column(sec), els = blocksOf(col), blocks = els.map(block);
    const wr = q(':scope > .wrap', sec) || sec;
    const stepCards = qa('.steps > .step', sec).filter(shown).filter(e => { const r = e.getBoundingClientRect(); return r.bottom > 0 && r.top < innerHeight; }).length;
    const out = { id, env: E, col: R(col.getBoundingClientRect()), colSel: path(col), wrap: R(wr.getBoundingClientRect()), stepCards, blocks };
    // the product: the live 3D (desktop, the tablet stage, the phone block holding the canvas) and, on a phone, the stills
    const prod = LC.product(); if (prod) { const { pic, ...rest } = prod; out.product = rest; if (pic) { const { _map, ...pp } = pic; out.product.pic = pp; } }
    const stage = els.find(e => e.matches('.stage, .ph-slot'));
    if (stage) {
      out.stage = R(stage.getBoundingClientRect());
      // the block's key frame (pose k at its place in the block; hidden while the canvas holds this block: measured anyway)
      const still = q('.stage-still', stage) || q('.ph-still', stage);
      const pic = still && pictureOf(still, true);
      if (pic) { const { _map, ...x } = pic; out.still = Object.assign(x, { hiddenStill: cs(still).visibility === 'hidden' || +cs(still).opacity < 0.05 }); }
    }
    // no live 3D: a still beside the copy (no WebGL, desktop) or in the section
    if (!out.product || out.product.hidden) { const sl = qa('img.slot', sec).find(shown); if (sl) { const pic = pictureOf(sl); if (pic) { const { _map, ...x } = pic; out.slotPic = x; } } }
    if (id === 'open' || sec.matches('#open')) {
      const nm = q('.open-name', sec), sub = q('.open-sub', sec);
      out.centred = [nm, sub].filter(shown).map(e => { const L = lines(e); return { sel: path(e), rect: R(e.getBoundingClientRect()), ink: L.length ? [Math.min(...L.map(x => x.l)), L[0].inkT, Math.max(...L.map(x => x.r)), L[L.length - 1].base] : null, lines: L.length }; });
      out.band = window.__mtBand || null;
    }
    if (sec.matches('.hero')) out.hero = true;
    out.overlap = overlaps(sec, blocks, prod);
    return out;
  };

  // text lines of the screen against the product's pixels, each other and the fixed chrome
  function overlaps(sec, blocks, prod) {
    const E = env(), res = { textOnPicture: [], textOnText: [], underChrome: [] }, pic = prod && prod.pic;
    const chrome = [['header', E.header], ['dock', E.dock], ['bar', E.bar]].filter(x => x[1]);
    if (E.stage) chrome.push(['stage', E.stage]);
    const rows = [];
    blocks.forEach((b, i) => { if (b.lines) b.lines.forEach(L => rows.push({ i, role: b.role, r: [L.l, L.inkT, L.r, L.base] })); else if (b.items) b.items.forEach(it => rows.push({ i, role: b.role, r: it, box: true })); });
    for (const x of rows) {
      if (x.r[3] < 0 || x.r[1] > E.H) continue;   // off screen: not read here
      if (pic) { const c = coverage(pic, x.r); if (c > 0) res.textOnPicture.push({ role: x.role, block: x.i, rect: x.r.map(r1), cover: c }); }
      else if (prod && prod.rect && inter(prod.rect, x.r) > 0) res.textOnPicture.push({ role: x.role, block: x.i, rect: x.r.map(r1), cover: 1, bbox: true });
      for (const [n, c] of chrome) { const a = inter(c, x.r); if (a > 0) res.underChrome.push({ role: x.role, block: x.i, chrome: n, rect: x.r.map(r1), area: r1(a) }); }
    }
    for (let a = 0; a < rows.length; a++) for (let b = a + 1; b < rows.length; b++) {
      if (rows[a].i === rows[b].i) continue;
      const ar = inter(rows[a].r, rows[b].r); if (ar > 1) res.textOnText.push({ a: rows[a].i, b: rows[b].i, roles: [rows[a].role, rows[b].role], area: r1(ar) });
    }
    return res;
  }

  // ---------- series and cards (step cards, the kit card, specialists, related)
  LC.series = function (kind) {
    const E = env(), out = { kind, env: E };
    if (kind === 'steps') {
      const it = qa('.mt-steps > .mt-step').filter(shown);
      if (it.length) {
        out.layout = 'pictures';
        out.cont = R(q('.mt-steps').getBoundingClientRect());
        out.items = it.map(li => { const im = q('img', li), fig = q('figure', li), st = q('.mt-st', li), pic = pictureOf(im);
          return { rect: R(li.getBoundingClientRect()), fig: fig && R(fig.getBoundingClientRect()), pic: pic && (({ _map, ...x }) => x)(pic), text: st && R(st.getBoundingClientRect()),
            blocks: st ? Array.from(st.children).filter(shown).map(block) : [] }; });
        const h = q('.mt-prep-h'), note = q('.mt-prep > .note');
        out.head = [h, note].filter(shown).map(block);
        out.scroller = cs(q('.mt-steps')).overflowX;
      } else {
        const st = qa('.steps > .step').filter(shown);
        out.layout = 'cards'; out.cont = st.length ? R(q('.steps').getBoundingClientRect()) : null;
        out.items = st.map(li => ({ rect: R(li.getBoundingClientRect()), blocks: Array.from(li.children).filter(shown).map(block) }));
        out.scroller = st.length ? cs(q('.steps')).overflowX : null;
      }
      const prod = LC.product(); if (prod && !prod.hidden) out.product = (({ pic, ...x }) => x)(prod);
      if (prod && prod.pic && out.items) out.productOverItems = out.items.map(i => coverage(prod.pic, i.rect));
    }
    if (kind === 'kit') {
      const c = q('.kitcard'); if (!c || !shown(c)) return Object.assign(out, { err: 'no kit card' });
      const s = cs(c), col = c.parentElement;
      out.card = R(c.getBoundingClientRect()); out.pad = [s.paddingLeft, s.paddingTop, s.paddingRight, s.paddingBottom].map(parseFloat);
      out.cell = R(col.getBoundingClientRect());
      // its grid cell: the offer's second column on a desktop (the card is centred in it)
      if (cs(col).display === 'grid') { const cols = cs(col).gridTemplateColumns.split(' ').map(parseFloat), g = parseFloat(cs(col).columnGap) || 0, cr = col.getBoundingClientRect();
        out.gridCols = cols; if (cols.length === 2) { const rtl = cs(col).direction === 'rtl', w0 = cols[0];
          out.cell = rtl ? [r1(cr.left), r1(cr.top), r1(cr.right - w0 - g), r1(cr.bottom)] : [r1(cr.left + w0 + g), r1(cr.top), r1(cr.right), r1(cr.bottom)]; } }
      const live = q('.kc-live', c), img = q('.kc-pic', c), fig = q('.kc-fig', c);
      const pic = live && shown(live) ? pictureOf(live) : pictureOf(img);
      out.pic = pic && (({ _map, ...x }) => x)(pic); out.fig = fig ? R(fig.getBoundingClientRect()) : out.pic && out.pic.box;
      out.blocks = Array.from(c.children).filter(shown).filter(e => !e.matches('.kc-fig, .kc-pic, .kc-live')).map(block);
      out.copy = q('.offer-copy') ? R(q('.offer-copy').getBoundingClientRect()) : (q('.offer .col') ? R(q('.offer .col').getBoundingClientRect()) : null);
      const prod = LC.product(); if (prod && !prod.hidden) out.product = (({ pic, ...x }) => x)(prod);
      if (out.pic) { const rows = []; out.blocks.forEach((b, i) => (b.lines || []).forEach(L => rows.push([L.l, L.inkT, L.r, L.base])));
        out.textOnPicture = rows.filter(rr => pic && coverage(pic, rr) > 0).length; }
    }
    if (kind === 'specialists') {
      const sec = q('#specialists'); if (!sec) return Object.assign(out, { err: 'none' });
      out.head = Array.from(q('.wrap', sec).children).filter(shown).filter(e => !e.matches('.specs, .spec-foot, .spec-empty')).map(block);
      const cards = qa('.specs > .spec', sec).filter(shown);
      out.cont = q('.specs', sec) ? R(q('.specs', sec).getBoundingClientRect()) : null;
      out.items = cards.map(c => { const av = q('.av', c), ph = q('.pic img', c);
        return { rect: R(c.getBoundingClientRect()), av: av && shown(av) ? R(av.getBoundingClientRect()) : null, photo: ph ? (({ _map, ...x }) => x)(pictureOf(ph) || {}) : null,
          blocks: qa('.sb > *', c).filter(shown).map(block) }; });
      const ft = q('.spec-foot', sec); if (ft && shown(ft)) out.foot = { rect: R(ft.getBoundingClientRect()), items: qa('.btn, .join > span', ft).filter(shown).map(e => R(e.getBoundingClientRect())) };
    }
    if (kind === 'related') {
      const sec = q('.related'); if (!sec) return Object.assign(out, { err: 'none' });
      out.groups = qa('.cards', sec).filter(shown).map(g => {
        const h = g.previousElementSibling && g.previousElementSibling.matches('h2') ? g.previousElementSibling : null;
        return { head: h ? block(h) : null, cont: R(g.getBoundingClientRect()), cols: cs(g).gridTemplateColumns.split(' ').length, gap: parseFloat(cs(g).columnGap) || 0,
          items: qa(':scope > .card', g).filter(shown).map(c => { const pic = q('.pic', c), im = q('.pic img', c), pp = pictureOf(im);
            return { rect: R(c.getBoundingClientRect()), picBox: pic && R(pic.getBoundingClientRect()), pic: pp && (({ _map, ...x }) => x)(pp), blocks: qa('.body > *', c).filter(shown).map(block) }; }) };
      });
      out.wrap = R(q('.wrap', sec).getBoundingClientRect());
    }
    return out;
  };

  // ---------- page level: type scale, tap targets, things outside the screen
  LC.pageLevel = function () {
    const E = env(), W = E.W, texts = [], seen = new Set();
    const roots = [q('main'), q('.top'), q('.foot'), q('.dock'), q('.bar')].filter(Boolean);
    for (const root of roots) {
      const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let n; (n = tw.nextNode());) {
        const el = n.parentElement; if (!/\S/.test(n.data) || seen.has(el) || !textShown(n)) continue;
        if (el.closest('dialog, [hidden], .sr-only, svg')) continue;
        seen.add(el); const s = cs(el), words = (el.textContent || '').trim().split(/\s+/).length;
        texts.push({ sel: path(el), fs: parseFloat(s.fontSize), w: s.fontWeight, lh: s.lineHeight, words, inP: !!el.closest('p, li, .lead, .note'),
          contrast: textContrast(el).ratio, color: s.color });
      }
    }
    const targets = qa('a[href], button, summary, input:not([type=hidden]), select, textarea, [role=button], [tabindex]:not([tabindex="-1"])')
      .filter(e => !e.closest('dialog') && shown(e))
      .map(e => { const r = e.getBoundingClientRect(); return { sel: path(e), w: r1(r.width), h: r1(r.height), logo: e.matches('.logo') || !!e.closest('.top .logo'), text: (e.textContent || e.getAttribute('aria-label') || '').trim().slice(0, 40) }; });
    // elements wider than the screen or past its sides (decorative fixed layers and the insides of side scrollers aside)
    const out = [], deco = '.bg, .plate, .mt-haze, .cells, .helix, .still, #seq, #gl, .still-fallback, .lvh-probe, dialog, .ph-gl';
    for (const e of qa('main *, .top *, .foot *, .dock, .bar')) {
      if (e.closest(deco) || !shown(e)) continue;
      let sc = false; for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const o = cs(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') { sc = true; break; } }
      if (sc) continue;
      const r = e.getBoundingClientRect(); if (r.left < -0.5 || r.right > W + 0.5) out.push({ sel: path(e), l: r1(r.left), r: r1(r.right) });
    }
    return { env: E, texts, targets, outside: out.slice(0, 40), outsideN: out.length };
  };

  // ---------- the scroll plan: each screen's hold (the engine's own windows) and where it is read
  LC.plan = function () {
    const E = env(), H = E.H, list = screens(), html = document.documentElement, plan = [];
    const ink = sec => { const col = column(sec), bl = blocksOf(col).filter(e => !e.matches('.stage, .ph-slot')); if (!bl.length) return null;
      const rs = bl.map(e => e.getBoundingClientRect()); return [Math.min(...rs.map(r => r.top)) + scrollY, Math.max(...rs.map(r => r.bottom)) + scrollY]; };
    const fc = (E.free[0] + E.free[1]) / 2;
    if (window.__seq) {
      const st = window.__seq(), Rn = st.R, geo = list.map(s => ({ top: s.el.offsetTop, h: s.el.offsetHeight }));
      const card = q('.kitcard'), cardTop = card && shown(card) ? card.getBoundingClientRect().top + scrollY : (geo[Rn] ? geo[Rn].top + 0.3 * H : 0);
      if (!E.flow && !E.stageMode) {   // desktop: engine/story.js position() without a stage
        const a = k => geo[k].top + Math.max(k ? 0.15 * H : 0.04 * H, geo[k].h - 0.85 * H), b = k => k === Rn - 1 ? cardTop - 0.85 * H : geo[k + 1].top - 0.12 * H;
        list.forEach((s, k) => {
          const h0 = k === 0 ? 0 : b(k - 1), h1 = k === Rn ? Infinity : a(k), c = ink(s.el);
          let y = c ? (c[0] + c[1]) / 2 - fc : h0;
          if (s.id === 'open') y = 0;
          if (s.id === 'offer') { const sm = parseFloat(cs(s.el).scrollMarginTop) || 0; y = s.el.getBoundingClientRect().top + scrollY - sm; }   // the dock's «הצעה»: the kit landed in the card
          else y = Math.max(h0, Math.min(h1 - 1, y));
          plan.push({ id: s.id, y: Math.max(0, Math.round(y)), hold: [Math.round(h0), h1 === Infinity ? null : Math.round(h1)], expectP: k });
        });
      } else if (E.stageMode) {   // tablet stage: a screen is read with its copy under the stage (the anchor), p = k there
        const sb = E.stage[3];
        list.forEach((s, k) => { const c = ink(s.el), y0 = k === 0 ? 0 : s.el.getBoundingClientRect().top + scrollY - sb;
          let y = c ? (c[0] + c[1]) / 2 - fc : y0; y = Math.max(y0, Math.min(y0 + 0.3 * H, y));
          plan.push({ id: s.id, y: Math.max(0, Math.round(y)), hold: [Math.round(y0), null], expectP: k }); });
      } else {   // flow: the heading under the header (an anchor's landing)
        list.forEach((s, k) => { const sm = parseFloat(cs(s.el).scrollMarginTop) || 0;
          plan.push({ id: s.id, y: s.id === 'open' ? 0 : Math.max(0, Math.round(s.el.getBoundingClientRect().top + scrollY - sm)), hold: null, expectP: null }); });
      }
    } else if (window.__anchorY) {
      list.forEach(s => { const y = window.__anchorY(s.st); plan.push({ id: s.id, y: Math.max(0, Math.round(y || 0)), hold: null, expectP: s.st }); });
    }
    // series views: their top just under the header (the free band's top) with a little air
    const ser = [];
    const at = (sel, k) => { const e = q(sel); if (e && shown(e)) ser.push({ id: k, y: Math.max(0, Math.round(e.getBoundingClientRect().top + scrollY - E.free[0] - 24)) }); };
    const steps = qa('.mt-steps > .mt-step').filter(shown);
    if (steps.length) steps.forEach((li, i) => { const r = li.getBoundingClientRect(); ser.push({ id: 'steps', i, y: Math.max(0, Math.round(r.top + scrollY + r.height / 2 - fc)) }); });
    else at('.steps', 'steps');
    const kc = q('.kitcard');
    if (kc && shown(kc)) { const off = plan.find(p => p.id === 'offer'); const r = kc.getBoundingClientRect();
      ser.push({ id: 'kit', y: off && !E.flow && !E.phone ? off.y : Math.max(0, Math.round(r.top + scrollY + r.height / 2 - fc)) }); }
    at('#specialists .specs', 'specialists'); at('.related .cards', 'related');
    return { env: E, screens: plan, series: ser };
  };

  // reveal everything at once (the reveal is an entrance, not layout) and load every picture now
  LC.prepare = function () {
    qa('.rv').forEach(e => e.classList.add('in'));
    qa('img[loading="lazy"]').forEach(e => { e.loading = 'eager'; });
    return qa('img').filter(e => !e.complete).length;
  };
  LC.pending = () => qa('img').filter(e => shown(e) && !(e.complete && e.naturalWidth)).map(e => (e.currentSrc || e.src).slice(-40));
})();
