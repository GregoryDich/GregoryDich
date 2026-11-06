// layout-rules.cjs: the rules L1–L7 of layout-check.cjs, applied to the raw records it collects (one per page and
// viewport). Every check gives its VALUE, the tolerance and a verdict: pass, low (a few px off: seen only side by
// side), high (clearly visible). The tolerances and why they are what they are: design-rules.md, «Сайт v2 — вёрстка по
// замерам (L1–L7)»; they were tuned so that the owner-approved pages (EXOTECH GEL, EXOCELL MASK) pass except where they
// have a real defect, which the report names.
// usage: node layout-check.cjs eval <raw dir> <out.json> <out.md> --target <slug> [--refs slug,slug] [--notes notes.json]
const fs = require('fs'), path = require('path');

// [pass up to, low up to] for "smaller is better"; [pass from, low from] for "larger is better"
const TOL = {
  L1: {
    fill: [0.4, 0.3],           // the product's height (or width, the tighter one) in its box: ≥ 0.4 passes, < 0.3 is high
    overfill: [1, 1.1],         // … and not larger than its box: ≤ 1 passes, ≤ 1.1 low (wider than its column: it leaves it)
    over: [4, 16],              // px of the product past its room (desktop: the screen's left half; phone: its block)
    centreY: [0.15, 0.25],      // |gap above − gap below| / box height (desktop band, phone block)
    distortion: [0.01, 0.03],   // |drawn aspect / natural aspect − 1|
    seriesSize: [0.06, 0.2],    // (max − min) / median of the drawn product heights in a series
    seriesBase: [3, 12],        // px spread of the products' feet (bottom of the drawn pixels) in a series, relative to their boxes
    related: [0.9, 0.75],       // a related card's packshot fills its frame by height (design-rules 14/10: one height for all)
  },
  L2: {
    edge: [1, 6],               // px spread of the right (start) edges of a column's blocks
    colEdge: [1, 6],            // px spread of the column's right edge across the screens of a viewport
    cpl: [[28, 78], [22, 90]],  // characters per full line of running Hebrew text: pass band, low band
    widow: 0.4,                 // a heading of ≥ 3 words whose last line is one word narrower than this share of its widest line
    gap: [1, 4],                // px spread of the gaps between chips / buttons on a line, rows, and their tops
  },
  L3: {
    sym: [2, 8],                // |left margin − right margin| of a centred block, px
    size: [1, 4],               // px spread of the widths / heights of cards in a row
    gap: [1, 4],                // px spread of the gaps between cards in a row
  },
  L4: {
    pair: [2, 8],               // px spread of one kind of gap (heading → lead, …) across the screens of a viewport
    section: [24, 96],          // px spread of the space between sections (phone and tablet blocks, stacked pages)
  },
  L5: {
    dy: [0.1, 0.16],            // |product centre − copy centre| / screen height (desktop holds)
    cx: [0.12, 0.25],           // |gap left − gap right| / column width (desktop) or stage width (phone)
    even: [24, 64],             // px: |space heading → product − space product → text| (phone blocks)
  },
  L6: {
    scale: 0.26,                // px: a size counts as on the scale within this of a size the approved pages use here
    body: [15, 14],             // px: body copy (paragraphs of a screen, step and card bodies): pass ≥ 15, low ≥ 14
    any: [11, 10],              // px: any text
    contrast: [4.5, 3],         // WCAG 2 ratio for body-size text (large text: 3)
    tap: [44, 36],              // px: the smaller side of a tap target on a touch screen
  },
  L7: {
    out: [0.5, 4],              // px outside the screen's sides
    cut: [0, 8],                // px of the copy or the product outside the free band at its reading position
    cover: [0, 0.05],           // share of a text line covered by the product's drawn pixels
  },
};
const RULES = {
  L1: 'Picture fit: the drawn product inside its box — fill, vertical centring, no distortion; a series: one size, one baseline',
  L2: 'Text grid: one right edge per column and across screens, line length, no widows in headings, chips and buttons on a grid',
  L3: 'Symmetry: centred blocks with equal margins; cards in a row equal and evenly spaced, the row centred',
  L4: 'Rhythm: each kind of vertical gap the same on every screen; even section spacing',
  L5: 'Balance: desktop — the product level with the copy and centred in its column; phone — centred in its block, even space above and below',
  L6: 'Type and touch: sizes on the scale, body not below the minimum, contrast ≥ 4.5:1, tap targets ≥ 44 px on touch screens',
  L7: 'Off-screen and overlap: nothing past the screen or the free band when read; no text on text, on the product or under the chrome',
};

const RULES_RU = {
  L1: 'Картинка вписана в своё место: заполнение (0.4–1 места), центр по вертикали, без искажения; серия — один размер и одна линия донышек',
  L2: 'Текстовая сетка: один правый край у блоков колонки и на всех экранах, длина строки, без висячих слов в заголовках, чипы и кнопки на сетке',
  L3: 'Симметрия: центрированные блоки с равными полями; карточки в ряду равны, зазоры равны, ряд по центру',
  L4: 'Ритм: каждый вид зазора одинаков на всех экранах; ровные расстояния между экранами (телефон)',
  L5: 'Баланс: десктоп — продукт на уровне копии и по центру своей колонки; телефон — по центру блока, ровно над и под ним',
  L6: 'Шрифт и касание: кегли со шкалы, тело не мельче 15 px, контраст ≥ 4.5:1, цели касания ≥ 44 px',
  L7: 'За краем и наложения: ничего за экраном и свободной полосой в позиции чтения; текст не на тексте, не на продукте, не под шапкой и доком',
};
const r1 = v => v == null || isNaN(v) ? null : Math.round(v * 10) / 10, r3 = v => v == null || isNaN(v) ? null : Math.round(v * 1000) / 1000;
const lowIsGood = (v, [t, h]) => v == null || isNaN(v) ? null : v <= t + 1e-9 ? 'pass' : v <= h + 1e-9 ? 'low' : 'high';
const highIsGood = (v, [t, h]) => v == null || isNaN(v) ? null : v >= t - 1e-9 ? 'pass' : v >= h - 1e-9 ? 'low' : 'high';
const spread = a => a.length ? Math.max(...a) - Math.min(...a) : 0;
const fillSev = v => { const lo = highIsGood(v, TOL.L1.fill), hi = lowIsGood(v, TOL.L1.overfill); return [lo, hi].includes('high') ? 'high' : [lo, hi].includes('low') ? 'low' : lo; };
const FILL_TOL = () => TOL.L1.fill[0] + '–' + TOL.L1.overfill[0];
const median = a => { const s = a.slice().sort((x, y) => x - y); return s.length ? s[s.length >> 1] : null; };
const H = r => r[3] - r[1], Wd = r => r[2] - r[0];
const union = rs => rs.length ? [Math.min(...rs.map(r => r[0])), Math.min(...rs.map(r => r[1])), Math.max(...rs.map(r => r[2])), Math.max(...rs.map(r => r[3]))] : null;
const TEXT = new Set(['kicker', 'h1', 'h2', 'h3', 'tag', 'lead', 'note', 'num']);
const ROW_ITEMS = new Set(['badges', 'chips', 'pins', 'cta', 'filter', 'khead']);
const BOX_EDGE = new Set(['pill', 'details', 'contacts', 'legend', 'facts', 'chip', 'card']);
const rightEdge = b => BOX_EDGE.has(b.role) ? b.rect[2] : b.inkR;
const topOf = b => TEXT.has(b.role) ? b.inkT : b.rect[1], botOf = b => TEXT.has(b.role) ? b.inkB : b.rect[3];
function modeOf(raw) { const E = raw.env0; return E.adapter === 'mask' ? (E.phone ? 'mphone' : 'desk') : E.flow ? 'flow' : E.stageMode ? 'stage' : 'desk'; }
const label = b => b.role + (b.text ? ' «' + b.text.split(' / ')[0].slice(0, 24) + '»' : '');

function evalRaw(raw, scale) {
  const C = [], E = raw.env0, mode = modeOf(raw), W = E.W, Hh = E.H, touch = !!(raw.vp && raw.vp.touch);
  const add = (rule, check, where, el, value, tol, sev, extra) => { if (sev == null) return; C.push(Object.assign({ rule, check, where, el, value, tol, sev }, extra || {})); };
  const scr = raw.screens.filter(s => !s.err);
  const centred = s => s.id === 'open' || s.hero;   // a centred composition (the opening's name), not a column

  // ---------- per screen
  const colEdges = [], pairs = {}, secBounds = [];
  for (const s0 of scr) {
    const s = Object.assign({}, s0, { blocks: s0.blocks.slice().sort((a, b) => a.rect[1] - b.rect[1] || b.rect[2] - a.rect[2]) });
    const F = s.env.free, bl = s.blocks.filter(b => b.role !== 'stage'), at = s.env.scrollY;
    if (!bl.length) continue;
    const prod = s.product && !s.product.hidden ? s.product : null;
    const P = prod ? (prod.rect || prod.aabbRect) : null;
    const copyInk = [Math.min(...bl.map(b => b.inkL != null ? b.inkL : b.rect[0])), Math.min(...bl.map(topOf)), Math.max(...bl.map(b => b.rect[2])), Math.max(...bl.map(botOf))];
    secBounds.push({ id: s.id, top: Math.min(...s.blocks.map(b => b.rect[1]), s.wrap ? s.wrap[1] : 1e9) + at, bottom: Math.max(...s.blocks.map(b => b.rect[3]), s.wrap ? s.wrap[3] : -1e9) + at });

    // L1 + L5: the product at the hold
    if (mode === 'desk' && P && !(s.id === 'offer')) {
      const wrap = s.wrap || E.wrap, band = s.band;
      const box = centred(s) && band ? [Math.max(0.03 * W, 24), band.top, W - Math.max(0.03 * W, 24), band.bottom]
        : [wrap[0], F[0], (wrap[0] + wrap[2]) / 2, F[1]];
      const room = centred(s) ? box : [16, F[0], W / 2, F[1]];
      const fill = Math.max(H(P) / H(box), Wd(P) / Wd(box)), over = Math.max(0, room[0] - P[0], P[2] - room[2], room[1] - P[1], P[3] - room[3]);
      const cy = Math.abs((P[1] - box[1]) - (box[3] - P[3])) / H(box), cx = Math.abs((P[0] - box[0]) - (box[2] - P[2])) / Wd(box);
      const ex = { box: box.map(r1), product: P.map(r1), src: prod.src, p: prod.p }, back = s.stepCards > 0;   // behind the screen's step cards: a backdrop
      const judge = v => back && v !== 'pass' ? 'pass' : v, bx = back ? { note: 'backdrop behind the step cards: reported, not judged' } : {};
      add('L1', 'fill', s.id, 'product', r3(fill), FILL_TOL() + ' of its column (band) in height or width', judge(fillSev(fill)), Object.assign({ fillH: r3(H(P) / H(box)), fillW: r3(Wd(P) / Wd(box)) }, ex, bx));
      add('L1', 'inside box', s.id, 'product', r1(over), '≤ ' + TOL.L1.over[0] + ' px past the screen\'s left half (16 px from its edge, header to dock)', lowIsGood(over, TOL.L1.over), Object.assign({}, ex, { room: room.map(r1) }));
      add('L1', 'centre y', s.id, 'product', r3(cy), '≤ ' + TOL.L1.centreY[0] + ' (|gap above − below| / band)', judge(lowIsGood(cy, TOL.L1.centreY)), Object.assign({}, ex, bx));
      if (prod.pic) add('L1', 'distortion', s.id, 'product canvas', prod.pic.distortion, '≤ ' + TOL.L1.distortion[0], lowIsGood(prod.pic.distortion, TOL.L1.distortion));
      add('L5', 'centred in column', s.id, 'product', r3(cx), '≤ ' + TOL.L5.cx[0] + ' (|gap left − right| / column)', lowIsGood(cx, TOL.L5.cx), ex);
      if (!centred(s)) {
        const dy = ((P[1] + P[3]) / 2 - (copyInk[1] + copyInk[3]) / 2) / Hh;
        add('L5', 'level with copy', s.id, 'product vs copy', r3(Math.abs(dy)), '≤ ' + TOL.L5.dy[0] + ' × screen height', lowIsGood(Math.abs(dy), TOL.L5.dy),
          { dyPx: r1(dy * Hh), productCy: r1((P[1] + P[3]) / 2), copyCy: r1((copyInk[1] + copyInk[3]) / 2) });
      }
      // L7: the product within the screen's free band at its hold
      const cut = Math.max(0, F[0] - P[1], P[3] - F[1], -P[0], P[2] - W);
      add('L7', 'product on screen', s.id, 'product', r1(cut), '0 px past the header, the dock or the sides', lowIsGood(cut, TOL.L7.cut), ex);
    }
    if (mode === 'stage' && P && s.id !== 'offer' && s.env.stage) {   // the tablet stage under the header (GEL): the product in the stage
      const box = s.env.stage;
      const fill = Math.max(H(P) / H(box), Wd(P) / Wd(box)), cy = Math.abs((P[1] - box[1]) - (box[3] - P[3])) / H(box), cx = Math.abs((P[0] - box[0]) - (box[2] - P[2])) / Wd(box);
      const ex = { box: box.map(r1), product: P.map(r1) };
      add('L1', 'fill', s.id, 'product in stage', r3(fill), FILL_TOL(), fillSev(fill), ex);
      add('L1', 'centre y', s.id, 'product in stage', r3(cy), '≤ ' + TOL.L1.centreY[0], lowIsGood(cy, TOL.L1.centreY), ex);
      add('L5', 'centred in stage', s.id, 'product in stage', r3(cx), '≤ ' + TOL.L5.cx[0], lowIsGood(cx, TOL.L5.cx), ex);
    }
    if ((mode === 'flow' || mode === 'mphone') && s.stage) {   // the phone's block: its key frame (pose k), or the live canvas (the opening; MASK)
      const box = mode === 'mphone' && prod && prod.host ? prod.host : s.stage;
      let Pp = null, src = '';
      if (mode === 'flow') { if (s.id === 'open' && P) { Pp = P; src = 'canvas'; } else if (s.still && s.still.content) { Pp = s.still.content; src = 'still ' + (s.still.src || '').split('/').pop(); } }
      else if (P) { Pp = P; src = 'objRects'; }
      if (Pp) {
        const fill = Math.max(H(Pp) / H(box), Wd(Pp) / Wd(box)), cy = Math.abs((Pp[1] - box[1]) - (box[3] - Pp[3])) / H(box), cx = Math.abs((Pp[0] - box[0]) - (box[2] - Pp[2])) / Wd(box);
        const over = Math.max(0, box[0] - Pp[0], Pp[2] - box[2], box[1] - Pp[1], Pp[3] - box[3]);
        const ex = { box: box.map(r1), product: Pp.map(r1), src };
        add('L1', 'fill', s.id, 'product in block', r3(fill), FILL_TOL(), fillSev(fill), Object.assign({ fillH: r3(H(Pp) / H(box)), fillW: r3(Wd(Pp) / Wd(box)) }, ex));
        add('L1', 'inside box', s.id, 'product in block', r1(over), '≤ ' + TOL.L1.over[0] + ' px outside its block', lowIsGood(over, TOL.L1.over), ex);
        add('L1', 'centre y', s.id, 'product in block', r3(cy), '≤ ' + TOL.L1.centreY[0], lowIsGood(cy, TOL.L1.centreY), ex);
        if (s.still && mode === 'flow' && s.id !== 'open') add('L1', 'distortion', s.id, 'block still', s.still.distortion, '≤ ' + TOL.L1.distortion[0], lowIsGood(s.still.distortion, TOL.L1.distortion));
        add('L5', 'centred in block', s.id, 'product in block', r3(cx), '≤ ' + TOL.L5.cx[0], lowIsGood(cx, TOL.L5.cx), ex);
        // heading → product → text, evenly spaced (the block stacked under the heading; MASK's slot beside it: not this)
        const i = s.blocks.findIndex(b => b.role === 'stage'), hb = s.blocks[i - 1], nb = s.blocks[i + 1];
        const stacked = hb && nb && box[1] >= hb.rect[3] - 2 && box[3] <= nb.rect[1] + 2;
        if (stacked) {
          const a = Pp[1] - botOf(hb), b = topOf(nb) - Pp[3], d = Math.abs(a - b);
          add('L5', 'even around product', s.id, label(hb) + ' → product → ' + nb.role, r1(d), '≤ ' + TOL.L5.even[0] + ' px', lowIsGood(d, TOL.L5.even), { above: r1(a), below: r1(b), blockAbove: r1(box[1] - botOf(hb)), blockBelow: r1(topOf(nb) - box[3]) });
        }
      }
    }
    if (mode === 'desk' && !P && s.slotPic && s.slotPic.content) {   // no WebGL: the still beside the copy
      const c = s.slotPic.content, b = s.slotPic.box;
      add('L1', 'fill', s.id, 'still beside copy', r3(Math.max(H(c) / H(b), Wd(c) / Wd(b))), '≥ ' + TOL.L1.fill[0], highIsGood(Math.max(H(c) / H(b), Wd(c) / Wd(b)), TOL.L1.fill));
    }

    // L3: the opening's name and subtitle centred on the screen
    if (s.centred) for (const c of s.centred) if (c.ink) {
      const d = Math.abs(c.ink[0] - (W - c.ink[2]));
      add('L3', 'centred', s.id, c.sel.split(' > ').pop(), r1(d), '≤ ' + TOL.L3.sym[0] + ' px (|left − right margin|)', lowIsGood(d, TOL.L3.sym), { left: r1(c.ink[0]), right: r1(W - c.ink[2]) });
    }
    if (centred(s)) { for (const b of bl) widows(b, s.id); continue; }

    // L2: one right edge for the column's blocks
    const edges = bl.map(b => ({ b, x: rightEdge(b) })).filter(e => e.x != null);
    if (edges.length > 1) {
      const xs = edges.map(e => e.x), med = median(xs), sp = spread(xs), worst = edges.reduce((a, e) => Math.abs(e.x - med) > Math.abs(a.x - med) ? e : a, edges[0]);
      add('L2', 'right edge', s.id, 'column (' + edges.length + ' blocks)', r1(sp), '≤ ' + TOL.L2.edge[0] + ' px spread', lowIsGood(sp, TOL.L2.edge), { edges: edges.map(e => [e.b.role, r1(e.x)]), worst: label(worst.b) });
      colEdges.push({ id: s.id, x: med });
    }
    for (const b of bl) { lineLength(b, s.id); widows(b, s.id); rowGrid(b, s.id); }
    // L4: the gaps between consecutive blocks (never across the phone's product block)
    for (let i = 1; i < s.blocks.length; i++) {
      const a = s.blocks[i - 1], b = s.blocks[i];
      if (['stage', 'card', 'cards'].includes(a.role) || ['stage', 'card', 'cards'].includes(b.role)) continue;
      if (b.rect[1] < a.rect[3] - 2) continue;   // side by side (MASK's slot beside the heading)
      const k = a.role + '→' + b.role, g = topOf(b) - botOf(a);
      (pairs[k] = pairs[k] || []).push({ id: s.id, g, box: b.rect[1] - a.rect[3] });
    }
    // L7: the copy whole in the free band at its reading position (desktop and the tablet stage: a screen is read whole)
    if (mode === 'desk' || (mode === 'stage' && s.id !== 'offer')) {
      const top = Math.min(...bl.map(b => b.rect[1])), bot = Math.max(...bl.map(b => b.rect[3]));
      const cut = Math.max(0, F[0] - top, bot - F[1]);
      add('L7', 'copy on screen', s.id, 'copy', r1(cut), '0 px past the header / dock / stage', lowIsGood(cut, TOL.L7.cut), { copy: [r1(top), r1(bot)], free: F });
      for (const u of s.overlap.underChrome) add('L7', 'under chrome', s.id, u.role + ' under ' + u.chrome, r1(u.area), 'no text under the header / dock / bar', u.area > 400 ? 'high' : 'low', { rect: u.rect });
    } else {   // a phone: the heading lands under the header, not under it
      const f = s.blocks[0], hb = s.env.header ? s.env.header[3] : 0;   // the header only: on a phone the copy runs on under the bar, read by scrolling
      if (f && s.id !== 'open') { const cut = Math.max(0, hb - f.rect[1]); add('L7', 'heading below header', s.id, f.role, r1(cut), '0 px', lowIsGood(cut, TOL.L7.cut)); }
    }
    for (const o of s.overlap.textOnPicture) add('L7', 'text on product', s.id, o.role, o.cover, 'no product pixels under text (≤ ' + TOL.L7.cover[1] + ' of a line: low)', o.cover <= TOL.L7.cover[1] ? 'low' : 'high', { rect: o.rect, bbox: !!o.bbox });
    for (const o of s.overlap.textOnText) add('L7', 'text on text', s.id, o.roles.join(' / '), r1(o.area), 'none', 'high');
  }

  function lineLength(b, where) {   // L2: characters per full line of running text (the paragraph's last line is free)
    if (b.role !== 'lead' || !b.lines || b.lines.length < 1) return;
    const full = b.lines.length > 1 ? b.lines.slice(0, -1) : [];
    const longest = Math.max(...b.lines.map(l => l.chars));
    if (full.length) {
      const cpl = Math.max(...full.map(l => l.chars)), lo = median(full.map(l => l.chars));   // one short line before a long word is not the measure
      const sevHi = cpl <= TOL.L2.cpl[0][1] ? 'pass' : cpl <= TOL.L2.cpl[1][1] ? 'low' : 'high';
      const sevLo = lo >= TOL.L2.cpl[0][0] ? 'pass' : lo >= TOL.L2.cpl[1][0] ? 'low' : 'high';
      const sev = [sevHi, sevLo].includes('high') ? 'high' : [sevHi, sevLo].includes('low') ? 'low' : 'pass';
      add('L2', 'line length', where, label(b), cpl, TOL.L2.cpl[0].join('–') + ' chars per full line (longest; median ≥ ' + TOL.L2.cpl[0][0] + ')', sev, { median: lo, lines: b.lines.map(l => l.chars) });
    } else if (longest > TOL.L2.cpl[0][1]) add('L2', 'line length', where, label(b), longest, '≤ ' + TOL.L2.cpl[0][1] + ' chars', longest <= TOL.L2.cpl[1][1] ? 'low' : 'high');
  }
  function widows(b, where) {   // L2: no single short word on a heading's last line
    if (!['h1', 'h2', 'h3', 'tag'].includes(b.role) || !b.lines || b.lines.length < 2) return;
    const last = b.lines[b.lines.length - 1], wide = Math.max(...b.lines.slice(0, -1).map(l => l.r - l.l)), share = (last.r - last.l) / wide;
    const words = b.lines.reduce((a, l) => a + l.words, 0), widow = words >= 3 && last.words === 1 && share < TOL.L2.widow;
    add('L2', 'widow', where, label(b), r3(share), 'last line of one word ≥ ' + TOL.L2.widow + ' of the widest', widow ? 'high' : 'pass', { lines: b.lines.map(l => l.words + 'w/' + l.chars + 'c') });
  }
  function rowGrid(b, where) {   // L2: chips, pins, buttons: tops level on a line, equal gaps, rows at one start edge
    if (!ROW_ITEMS.has(b.role) || !b.items || b.items.length < 2) return;
    const ov = (a, b) => Math.min(a[3], b[3]) - Math.max(a[1], b[1]) > 0.5 * Math.min(a[3] - a[1], b[3] - b[1]);
    const rows = []; for (const it of b.items.slice().sort((x, y) => x[1] - y[1])) { const r = rows.find(r => ov(r[0], it)); if (r) r.push(it); else rows.push([it]); }
    const hg = [], tops = [], starts = [], lab = b.labelIdx != null ? b.items[b.labelIdx] : null;
    for (const r of rows) { r.sort((x, y) => y[2] - x[2]); starts.push(r[0][2]); for (let i = 1; i < r.length; i++) if (r[i - 1] !== lab && r[i] !== lab) hg.push(r[i - 1][0] - r[i][2]); tops.push(spread(r.filter(x => x !== lab).map(x => (x[1] + x[3]) / 2))); }
    const vg = []; for (let i = 1; i < rows.length; i++) vg.push(Math.min(...rows[i].map(x => x[1])) - Math.max(...rows[i - 1].map(x => x[3])));
    const sp = Math.max(spread(hg), spread(vg), Math.max(0, ...tops), rows.length > 1 && b.role !== 'cta' ? spread(starts) : 0);
    add('L2', 'row grid', where, b.role + ' (' + b.items.length + ')', r1(sp), '≤ ' + TOL.L2.gap[0] + ' px (gaps, levels, start edge)', lowIsGood(sp, TOL.L2.gap), { hGaps: hg.map(r1), vGaps: vg.map(r1), starts: starts.map(r1) });
  }

  // L2: the column's right edge, the same on every screen
  if (colEdges.length > 1) { const sp = spread(colEdges.map(c => c.x)); add('L2', 'column edge across screens', 'all screens', 'copy column', r1(sp), '≤ ' + TOL.L2.colEdge[0] + ' px', lowIsGood(sp, TOL.L2.colEdge), { edges: colEdges.map(c => [c.id, r1(c.x)]) }); }
  // L4: each kind of gap the same on every screen
  for (const [k, list] of Object.entries(pairs)) if (list.length > 1) {
    const sp = spread(list.map(x => x.g));
    add('L4', 'gap ' + k, 'all screens', k, r1(sp), '≤ ' + TOL.L4.pair[0] + ' px spread', lowIsGood(sp, TOL.L4.pair), { gaps: list.map(x => [x.id, r1(x.g)]), boxGaps: list.map(x => r1(x.box)) });
  }
  // L4: section spacing (stacked pages: phone and tablet blocks, MASK's phone)
  if (mode === 'flow' || mode === 'mphone') {
    const sb = secBounds.slice().sort((a, b) => a.top - b.top), g = [];
    for (let i = 1; i < sb.length; i++) g.push([sb[i - 1].id + '→' + sb[i].id, sb[i].top - sb[i - 1].bottom]);
    if (g.length > 1) { const sp = spread(g.map(x => x[1])); add('L4', 'section spacing', 'all screens', 'space between screens', r1(sp), '≤ ' + TOL.L4.section[0] + ' px spread', lowIsGood(sp, TOL.L4.section), { gaps: g.map(x => [x[0], r1(x[1])]) }); }
  }

  // ---------- series
  const firstOf = k => raw.series.find(x => x.kind === k && !x.err);
  const st = firstOf('steps');
  if (st && st.items && st.items.length) {
    if (st.layout === 'pictures') {
      const it = st.items.filter(i => i.pic && i.pic.content), hs = it.map(i => H(i.pic.content)), feet = it.map(i => i.pic.box[3] - i.pic.content[3]);
      it.forEach((i, n) => { const c = i.pic.content, b = i.pic.box, fill = Math.max(H(c) / H(b), Wd(c) / Wd(b));
        add('L1', 'fill', 'step ' + (n + 1), 'step picture', r3(fill), '≥ ' + TOL.L1.fill[0], highIsGood(fill, TOL.L1.fill), { fillH: r3(H(c) / H(b)), fillW: r3(Wd(c) / Wd(b)), content: c, box: b });
        add('L1', 'distortion', 'step ' + (n + 1), 'step picture', i.pic.distortion, '≤ ' + TOL.L1.distortion[0], lowIsGood(i.pic.distortion, TOL.L1.distortion)); });
      if (hs.length > 1) {
        const v = spread(hs) / median(hs);
        add('L1', 'series size', 'steps', 'step pictures (' + hs.length + ')', r3(v), '≤ ' + TOL.L1.seriesSize[0] + ' (spread / median of drawn heights)', lowIsGood(v, TOL.L1.seriesSize), { heights: hs.map(r1) });
        const fb = spread(feet);
        add('L1', 'series baseline', 'steps', 'step pictures (' + hs.length + ')', r1(fb), '≤ ' + TOL.L1.seriesBase[0] + ' px spread of the feet', lowIsGood(fb, TOL.L1.seriesBase), { feetAboveBox: feet.map(r1) });
      }
      // the step text column: one right edge with the screens' copy (desktop: the text beside the picture)
      if (!st.scroller || st.scroller === 'visible') {
        const ex = st.items.flatMap(i => i.blocks.map(b => rightEdge(b))).filter(x => x != null), heads = (st.head || []).map(rightEdge);
        const all = ex.concat(heads), base = colEdges.length ? median(colEdges.map(c => c.x)) : median(all);
        if (all.length) { const d = Math.max(...all.map(x => Math.abs(x - base))); add('L2', 'right edge', 'steps', 'step texts and heading', r1(d), '≤ ' + TOL.L2.edge[0] + ' px from the copy column', lowIsGood(d, TOL.L2.edge)); }
      }
      for (const i of st.items) for (const b of i.blocks) { lineLength(b, 'steps'); widows(b, 'steps'); }
      for (const b of st.head || []) widows(b, 'steps');
      // picture and text level in a desktop card
      if (!st.scroller || st.scroller === 'visible') {
        const d = Math.max(...it.map(i => Math.abs(((i.pic.content[1] + i.pic.content[3]) / 2) - ((i.text[1] + i.text[3]) / 2))));
        add('L5', 'picture level with text', 'steps', 'step cards', r1(d), '≤ ' + Math.round(TOL.L5.dy[0] * Hh) + ' px', lowIsGood(d / Hh, TOL.L5.dy));
      }
    } else {
      rowCards(st.items.map(i => i.rect), 'steps', 'step cards', st.cont, st.scroller && st.scroller !== 'visible');
      for (const i of st.items) for (const b of i.blocks) { lineLength(b, 'steps'); widows(b, 'steps'); }
    }
    const pov = raw.series.filter(x => x.kind === 'steps' && x.productOverItems).flatMap(x => x.productOverItems).filter(v => v > 0);
    if (pov.length) add('L7', 'product over step cards', 'steps', '3D product', r3(Math.max(...pov)), 'none', 'high');
  }
  const kit = firstOf('kit');
  if (kit && kit.card) {
    const c = kit.card, cell = kit.cell, pic = kit.pic;
    if (kit.pad) { const d = Math.abs(kit.pad[0] - kit.pad[2]); add('L3', 'padding', 'kit card', 'card padding left / right', r1(d), '≤ 1 px', lowIsGood(d, [1, 4])); }
    if (pic && pic.content) {
      const box = kit.fig || pic.box, P = pic.content, fill = Math.max(H(P) / H(box), Wd(P) / Wd(box));
      add('L1', 'fill', 'kit card', 'kit picture', r3(fill), '≥ ' + TOL.L1.fill[0], highIsGood(fill, TOL.L1.fill), { fillH: r3(H(P) / H(box)), fillW: r3(Wd(P) / Wd(box)), box, content: P, kind: pic.kind });
      add('L1', 'distortion', 'kit card', 'kit picture', pic.distortion, '≤ ' + TOL.L1.distortion[0], lowIsGood(pic.distortion, TOL.L1.distortion));
      const inner = [c[0] + (kit.pad ? kit.pad[0] : 0), c[2] - (kit.pad ? kit.pad[2] : 0)], d = Math.abs((P[0] - inner[0]) - (inner[1] - P[2]));
      add('L3', 'centred', 'kit card', 'kit picture in the card', r1(d), '≤ ' + TOL.L3.sym[0] + ' px', lowIsGood(d, TOL.L3.sym), { left: r1(P[0] - inner[0]), right: r1(inner[1] - P[2]) });
      if (kit.textOnPicture) add('L7', 'text on product', 'kit card', 'card text', kit.textOnPicture, 'none', 'high');
    }
    const edges = (kit.blocks || []).map(b => ({ b, x: rightEdge(b) })).filter(e => e.x != null);
    if (edges.length > 1) { const sp = spread(edges.map(e => e.x)); add('L2', 'right edge', 'kit card', 'card blocks (' + edges.length + ')', r1(sp), '≤ ' + TOL.L2.edge[0] + ' px', lowIsGood(sp, TOL.L2.edge), { edges: edges.map(e => [e.b.role, r1(e.x)]) }); }
    for (const b of kit.blocks || []) { widows(b, 'kit card'); rowGrid(b, 'kit card'); }
  }
  const sp = firstOf('specialists');
  if (sp && sp.items && sp.items.length) {
    rowCards(sp.items.map(i => i.rect), 'specialists', 'specialist cards', sp.cont, false);
    const av = sp.items.filter(i => i.av);
    if (av.length > 1) { const off = av.map(i => [i.av[0] - i.rect[0], i.av[1] - i.rect[1], i.av[2] - i.av[0], i.av[3] - i.av[1]]);
      const d = Math.max(spread(off.map(o => o[0])), spread(off.map(o => o[1])), spread(off.map(o => o[2])), spread(off.map(o => o[3])));
      add('L3', 'same place', 'specialists', 'monograms (' + av.length + ')', r1(d), '≤ ' + TOL.L3.size[0] + ' px (size and offset in the card)', lowIsGood(d, TOL.L3.size)); }
    const edges = (sp.head || []).map(b => ({ b, x: rightEdge(b) })).filter(e => e.x != null);
    if (edges.length > 1) { const s2 = spread(edges.map(e => e.x)); add('L2', 'right edge', 'specialists', 'heading blocks', r1(s2), '≤ ' + TOL.L2.edge[0] + ' px', lowIsGood(s2, TOL.L2.edge), { edges: edges.map(e => [e.b.role, r1(e.x)]) }); }
    for (const b of sp.head || []) { widows(b, 'specialists'); rowGrid(b, 'specialists'); }
  }
  const rel = firstOf('related');
  if (rel && rel.groups) rel.groups.forEach((g, gi) => {
    const where = 'related' + (rel.groups.length > 1 ? ' ' + (gi + 1) : '');
    rowCards(g.items.map(i => i.rect), where, 'cards', g.cont, false, g.cols);
    const it = g.items.filter(i => i.pic && i.pic.content);
    it.forEach((i, n) => { const c = i.pic.content, b = i.pic.box, f = H(c) / H(b);
      add('L1', 'fill', where + ' card ' + (n + 1), 'packshot (height)', r3(f), '≥ ' + TOL.L1.related[0] + ' (fills its frame by height)', highIsGood(f, TOL.L1.related), { content: c, box: b, src: i.pic.src && i.pic.src.split('/').pop() }); });
    if (it.length > 1) {
      const hs = it.map(i => H(i.pic.content)), v = spread(hs) / median(hs);
      add('L1', 'series size', where, 'packshots (' + it.length + ')', r3(v), '≤ ' + TOL.L1.seriesSize[0], lowIsGood(v, TOL.L1.seriesSize), { heights: hs.map(r1) });
      const feet = it.map(i => i.pic.content[3] - i.rect[1]), fb = spread(feet);
      add('L1', 'series baseline', where, 'packshots (' + it.length + ')', r1(fb), '≤ ' + TOL.L1.seriesBase[0] + ' px', lowIsGood(fb, TOL.L1.seriesBase), { feet: feet.map(r1) });
    }
    if (g.head) widows(g.head, where);
    for (const i of g.items) for (const b of i.blocks) { widows(b, where); }
  });
  function rowCards(rects, where, el, cont, scroller, cols) {   // L3: cards in a row — equal, evenly spaced, the row centred
    const rows = []; for (const r of rects.slice().sort((a, b) => a[1] - b[1])) { const row = rows.find(x => Math.abs(x[0][1] - r[1]) < 4); if (row) row.push(r); else rows.push([r]); }
    for (const row of rows) {
      row.sort((a, b) => a[0] - b[0]);
      if (row.length > 1) {
        const ws = spread(row.map(Wd)), hs = spread(row.map(H)), gaps = []; for (let i = 1; i < row.length; i++) gaps.push(row[i][0] - row[i - 1][2]);
        add('L3', 'equal cards', where, el + ' (' + row.length + ')', r1(Math.max(ws, hs)), '≤ ' + TOL.L3.size[0] + ' px width / height spread', lowIsGood(Math.max(ws, hs), TOL.L3.size), { widths: row.map(r => r1(Wd(r))), heights: row.map(r => r1(H(r))) });
        if (gaps.length > 1) add('L3', 'even gaps', where, el, r1(spread(gaps)), '≤ ' + TOL.L3.gap[0] + ' px', lowIsGood(spread(gaps), TOL.L3.gap), { gaps: gaps.map(r1) });
      }
      if (cont && !scroller) { const u = union(row), d = Math.abs((u[0] - cont[0]) - (cont[2] - u[2]));
        add('L3', 'row centred', where, el + ' (' + row.length + (cols ? ' in ' + cols + ' columns' : '') + ')', r1(d), '≤ ' + TOL.L3.sym[0] + ' px (|left − right margin|)', lowIsGood(d, TOL.L3.sym), { left: r1(u[0] - cont[0]), right: r1(cont[2] - u[2]) }); }
    }
  }

  // ---------- page level
  const pl = raw.page;
  if (pl) {
    if (pl.env.docW > W + 0.5) add('L7', 'horizontal scroll', 'page', 'document', pl.env.docW - W, 'page width = screen width', 'high');
    for (const o of pl.outside || []) { const d = Math.max(-o.l, o.r - W); add('L7', 'past the side', 'page', o.sel.split(' > ').slice(-2).join(' > '), r1(d), '≤ ' + TOL.L7.out[0] + ' px', lowIsGood(d, TOL.L7.out)); }
    if (E.dock) { const d = Math.abs(E.dock[0] - (W - E.dock[2])); add('L3', 'centred', 'dock', 'dock', r1(d), '≤ 1 px', lowIsGood(d, [1, 4])); }
    // L6 type: sizes on the approved pages' scale here, body copy, any text, contrast
    const sizes = scale && scale[raw.vp.id], off = new Map();
    for (const t of pl.texts) {
      if (sizes && !sizes.some(z => Math.abs(z - t.fs) <= TOL.L6.scale)) { const k = r1(t.fs); if (!off.has(k)) off.set(k, []); off.get(k).push(t.sel.split(' > ').slice(-2).join(' > ')); }
      const big = t.fs >= 24 || (t.fs >= 18.66 && +t.w >= 600), need = big ? 3 : TOL.L6.contrast[0];
      if (t.contrast < need) add('L6', 'contrast', 'page', t.sel.split(' > ').slice(-2).join(' > '), t.contrast, '≥ ' + need + ':1', t.contrast >= (big ? 2.2 : TOL.L6.contrast[1]) ? 'low' : 'high', { color: t.color });
      if (t.fs < TOL.L6.any[0]) add('L6', 'smallest text', 'page', t.sel.split(' > ').slice(-2).join(' > '), t.fs, '≥ ' + TOL.L6.any[0] + ' px', highIsGood(t.fs, TOL.L6.any));
    }
    for (const [fs, els] of off) add('L6', 'off the scale', 'page', [...new Set(els)].slice(0, 3).join(', ') + (els.length > 3 ? ' …' : ''), fs, 'a size the approved pages use at this screen', 'low', { nearest: sizes ? sizes.reduce((a, z) => Math.abs(z - fs) < Math.abs(a - fs) ? z : a, sizes[0]) : null });
    if (touch) for (const t of pl.targets) {
      if (t.logo) continue;   // the header logo: the known exception
      const m = Math.min(t.w, t.h); if (m < TOL.L6.tap[0]) add('L6', 'tap target', 'page', t.sel.split(' > ').slice(-2).join(' > ') + (t.text ? ' «' + t.text.slice(0, 20) + '»' : ''), m, '≥ ' + TOL.L6.tap[0] + ' px', highIsGood(m, TOL.L6.tap), { w: t.w, h: t.h });
    }
  }
  // L6 body: the copy's paragraphs, the step and card bodies
  const bodies = [];
  for (const s of scr) if (!centred(s)) for (const b of s.blocks) if (b.role === 'lead' && b.lines && b.lines.length) bodies.push([s.id, b]);
  if (st && st.items) for (const i of st.items) for (const b of i.blocks) if (b.role === 'lead') bodies.push(['steps', b]);
  const smallBody = bodies.filter(([, b]) => b.font.size < TOL.L6.body[0] - 0.01);
  if (bodies.length) add('L6', 'body size', 'all screens', smallBody.length ? smallBody.map(([w, b]) => w + ' ' + label(b)).slice(0, 3).join(', ') : 'paragraphs (' + bodies.length + ')',
    Math.min(...bodies.map(([, b]) => b.font.size)), '≥ ' + TOL.L6.body[0] + ' px', highIsGood(Math.min(...bodies.map(([, b]) => b.font.size)), TOL.L6.body));
  return C;
}

// the approved pages' type scale per viewport (the sizes they use there)
function scaleOf(raws, refs) {
  const out = {};
  for (const r of raws) if (refs.includes(r.slug) && r.page) { const s = out[r.vp.id] = out[r.vp.id] || new Set(); for (const t of r.page.texts) s.add(Math.round(t.fs * 100) / 100); }
  for (const k of Object.keys(out)) out[k] = [...out[k]].sort((a, b) => a - b);
  return out;
}

function evaluate(raws, o = {}) {
  const refs = o.refs || ['exotech-gel', 'exocell-mask'], scale = scaleOf(raws, refs);
  const pages = {};
  for (const raw of raws) {
    const checks = evalRaw(raw, scale);
    const p = pages[raw.slug] = pages[raw.slug] || { slug: raw.slug, viewports: {} };
    p.viewports[raw.vp.id] = { mode: modeOf(raw), ms: raw.wallMs, errs: raw.errs, checks,
      counts: { pass: checks.filter(c => c.sev === 'pass').length, low: checks.filter(c => c.sev === 'low').length, high: checks.filter(c => c.sev === 'high').length } };
  }
  for (const p of Object.values(pages)) {
    const fails = [];
    for (const [vp, v] of Object.entries(p.viewports)) for (const c of v.checks) if (c.sev !== 'pass') fails.push(Object.assign({ vp }, c));
    p.summary = { high: fails.filter(f => f.sev === 'high').length, low: fails.filter(f => f.sev === 'low').length, pass: Object.values(p.viewports).reduce((a, v) => a + v.counts.pass, 0),
      byRule: Object.fromEntries(Object.keys(RULES).map(k => [k, { high: fails.filter(f => f.rule === k && f.sev === 'high').length, low: fails.filter(f => f.rule === k && f.sev === 'low').length }])) };
    p.failures = fails;
  }
  return { generated: new Date().toISOString(), rules: RULES, tolerances: TOL, refs, scale, pages };
}

// grouped failures: the same check on the same element over several viewports reads as one line
function groups(fails) {
  const m = new Map();
  for (const f of fails) {
    const k = [f.rule, f.check, f.where, f.el].join('|');
    if (!m.has(k)) m.set(k, { rule: f.rule, check: f.check, where: f.where, el: f.el, tol: f.tol, sev: f.sev, items: [] });
    const g = m.get(k); g.items.push(f); if (f.sev === 'high') g.sev = 'high';
  }
  return [...m.values()].sort((a, b) => (a.sev === b.sev ? 0 : a.sev === 'high' ? -1 : 1) || a.rule.localeCompare(b.rule) || b.items.length - a.items.length);
}
const fmtV = f => {
  const v = typeof f.value === 'number' ? f.value : JSON.stringify(f.value);
  const x = [];
  for (const k of ['fillH', 'fillW', 'dyPx', 'above', 'below', 'left', 'right', 'median', 'nearest', 'w', 'h']) if (f[k] != null) x.push(k + ' ' + f[k]);
  if (f.heights) x.push('heights ' + f.heights.join('/')); if (f.feetAboveBox) x.push('feet ' + f.feetAboveBox.join('/')); if (f.feet) x.push('feet ' + f.feet.join('/'));
  if (f.gaps && typeof f.gaps[0] !== 'object') x.push('gaps ' + f.gaps.join('/'));
  if (f.gaps && typeof f.gaps[0] === 'object') x.push(f.gaps.map(g => g.join(' ')).join(', '));
  if (f.lines && typeof f.lines[0] === 'string') x.push(f.lines.join(' | '));
  if (f.edges && f.check !== 'column edge across screens') x.push(f.edges.map(e => e.join(' ')).join(', '));
  if (f.edges && f.check === 'column edge across screens') x.push(f.edges.map(e => e.join(' ')).join(', '));
  if (f.hGaps && f.hGaps.length) x.push('h-gaps ' + f.hGaps.join('/')); if (f.vGaps && f.vGaps.length) x.push('v-gaps ' + f.vGaps.join('/'));
  if (f.product && f.box) x.push('product ' + f.product.join(',') + ' in ' + f.box.join(','));
  return v + (x.length ? ' (' + x.join('; ') + ')' : '');
};

function report(res, o = {}) {
  const target = o.target || 'mitotech-cell-booster', notes = o.notes || {}, L = [];
  const pg = res.pages[target];
  L.push(`# Вёрстка по замерам (L1–L7): ${target}`, '');
  L.push(`Сгенерировано ${res.generated.slice(0, 16).replace('T', ' ')} UTC скриптом \`site/proto/qa/layout-check.cjs\` (замеры DOM, Range-строк и альфы картинок, без скриншотов). ` +
    `Эталоны: ${res.refs.join(', ')}. Правила и допуски — \`design-rules.md\`, раздел «Сайт v2 — вёрстка по замерам (L1–L7)». Полные значения — \`${target}.layout.json\`.`, '');
  if (notes._summary) L.push(notes._summary, '');
  L.push('## Сводка', '', '| Страница | экраны | проверок | pass | low | high | L1 | L2 | L3 | L4 | L5 | L6 | L7 |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|');
  for (const p of Object.values(res.pages)) {
    const vps = Object.keys(p.viewports).length, n = p.summary.pass + p.summary.low + p.summary.high;
    L.push(`| ${p.slug} | ${vps} | ${n} | ${p.summary.pass} | ${p.summary.low} | ${p.summary.high} | ` + Object.keys(RULES).map(k => `${p.summary.byRule[k].high}/${p.summary.byRule[k].low}`).join(' | ') + ' |');
  }
  L.push('', 'В колонках L1–L7: high/low.', '');
  L.push('## Правила и допуски', '');
  for (const k of Object.keys(RULES)) L.push(`- **${k}** — ${RULES_RU[k]}. Допуски [pass, low]: \`${JSON.stringify(res.tolerances[k])}\``);
  L.push('');
  // the values: the main measures of the target page, screen by screen, on every viewport (✓ pass, · low, ✗ high)
  if (pg) {
    const vps = Object.keys(pg.viewports), KEYS = [['L1', 'fill'], ['L1', 'centre y'], ['L5', 'centred in column'], ['L5', 'centred in block'], ['L5', 'centred in stage'], ['L5', 'level with copy'], ['L5', 'even around product'], ['L7', 'copy on screen'], ['L7', 'product on screen'], ['L2', 'right edge'], ['L1', 'series size'], ['L1', 'series baseline'], ['L3', 'row centred']];
    const rows = new Map(), mark = v => v === 'pass' ? '✓' : v === 'low' ? '·' : '✗';
    for (const v of vps) for (const c of pg.viewports[v].checks) {
      if (!KEYS.some(([r, k]) => r === c.rule && k === c.check)) continue;
      const k = [c.rule, c.check, c.where].join(' | '); if (!rows.has(k)) rows.set(k, {}); rows.get(k)[v] = (typeof c.value === 'number' ? c.value : '') + mark(c.sev);
    }
    L.push('## Значения: ' + target + ' по экранам', '', '✓ pass, · low, ✗ high. Заполнение и центровка — доли места, зазоры и края — px.', '');
    L.push('| Проверка | ' + vps.join(' | ') + ' |', '|---|' + vps.map(() => '---').join('|') + '|');
    for (const [k, r] of rows) L.push('| ' + k + ' | ' + vps.map(v => r[v] || '—').join(' | ') + ' |');
    L.push('');
  }
  const section = (slug, title) => {
    const p = res.pages[slug]; if (!p) return;
    L.push(`## ${title}`, '');
    for (const g of groups(p.failures)) {
      const vps = g.items.map(i => i.vp), vals = g.items.slice(0, 4).map(i => `${i.vp}: ${fmtV(i)}`).join('; ') + (g.items.length > 4 ? `; … ещё ${g.items.length - 4}` : '');
      const n = notes[slug + '|' + [g.rule, g.check, g.where, g.el].join('|')] || notes[slug + '|' + [g.rule, g.check, g.where].join('|')] || notes[slug + '|' + [g.rule, g.check].join('|')];
      L.push(`- **${g.sev}** ${g.rule} ${g.check} — ${g.where} — ${g.el}. ${vps.length === Object.keys(p.viewports).length ? 'все экраны' : vps.join(', ')}. Допуск: ${g.tol}. Значения: ${vals}` + (n ? `\n  - ${n}` : ''));
    }
    if (!p.failures.length) L.push('Нарушений нет.');
    L.push('');
  };
  section(target, `${target}: нарушения (сначала high)`);
  for (const r of res.refs) section(r, `Эталон ${r}: где он не проходит`);
  L.push('## По экранам (pass / low / high)', '', '| Экран | ' + Object.keys(res.pages).join(' | ') + ' |', '|---|' + Object.keys(res.pages).map(() => '---').join('|') + '|');
  const vpIds = [...new Set(Object.values(res.pages).flatMap(p => Object.keys(p.viewports)))];
  for (const v of vpIds) L.push(`| ${v} | ` + Object.values(res.pages).map(p => { const x = p.viewports[v]; return x ? `${x.mode}: ${x.counts.pass}/${x.counts.low}/${x.counts.high}, ${Math.round((x.ms || 0) / 1000)} с` : '—'; }).join(' | ') + ' |');
  L.push('');
  return L.join('\n');
}

function cli(args) {
  const [rawDir, outJson, outMd, ...rest] = args, opt = {};
  for (let i = 0; i < rest.length; i += 2) opt[rest[i].replace(/^--/, '')] = rest[i + 1];
  const raws = fs.readdirSync(rawDir).filter(f => /__.+\.json$/.test(f)).map(f => JSON.parse(fs.readFileSync(path.join(rawDir, f), 'utf8')));
  const refs = opt.refs ? opt.refs.split(',') : undefined, target = opt.target || 'mitotech-cell-booster';
  const res = evaluate(raws, { refs });
  const notes = opt.notes && fs.existsSync(opt.notes) ? JSON.parse(fs.readFileSync(opt.notes, 'utf8')) : {};
  res.notes = notes;
  fs.mkdirSync(path.dirname(outJson), { recursive: true });
  const out = Object.assign({}, res, { target, tool: 'site/proto/qa/layout-check.cjs', pages: {} });
  for (const [k, p] of Object.entries(res.pages)) out.pages[k] = k === target ? p
    : { slug: k, summary: p.summary, failures: p.failures, viewports: Object.fromEntries(Object.entries(p.viewports).map(([v, x]) => [v, { mode: x.mode, ms: x.ms, errs: x.errs, counts: x.counts }])) };
  fs.writeFileSync(outJson, JSON.stringify(out));
  fs.writeFileSync(outMd, report(res, { target, notes }));
  for (const p of Object.values(res.pages)) console.log(p.slug, 'viewports', Object.keys(p.viewports).length, 'pass', p.summary.pass, 'low', p.summary.low, 'high', p.summary.high);
}

module.exports = { TOL, RULES, RULES_RU, evaluate, evalRaw, report, groups, scaleOf, cli };
