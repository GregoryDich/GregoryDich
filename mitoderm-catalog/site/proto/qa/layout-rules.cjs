// layout-rules.cjs: the rules L1–L8 of layout-check.cjs, applied to the raw records it collects (one per page and
// viewport). Every check gives its VALUE, the tolerance and a verdict: pass, low (a few px off: seen only side by
// side; or a template decision the approved pages share), high (clearly visible). The tolerances and why: design-rules.md, «Сайт v2 — вёрстка по
// замерам (L1–L8)»; they were tuned so that the owner-approved pages (EXOTECH GEL, EXOCELL MASK) pass except where they
// have a real defect, which the report names.
// usage: node layout-check.cjs eval <raw dir> <out.json> <out.md> --target <slug> [--refs slug,slug] [--notes notes.json]
const fs = require('fs'), path = require('path');

// [pass up to, low up to] for "smaller is better"; [pass from, low from] for "larger is better"
const TOL = {
  L1: {
    fill: [0.4, 0.3],           // the product's height (or width, the tighter one) in its box: ≥ 0.4 passes, < 0.3 is high
    overfill: [1, 1.1],         // … and not larger than its box: ≤ 1 passes, ≤ 1.1 low (wider than its column: it leaves it)
    over: [4, 16],              // px of the product past its room (desktop: the screen's left half; phone: its block)
    grid: [16, 48],             // px of the product past the content grid's left edge (desktop: the .wrap, where the header's button starts)
    centreY: [0.15, 0.25],      // |gap above − gap below| / box height (desktop band, phone block)
    distortion: [0.01, 0.03],   // |drawn aspect / natural aspect − 1|
    seriesSize: [0.06, 0.2],    // (max − min) / median of the drawn product heights in a series
    seriesBase: [3, 12],        // px spread of the products' feet (bottom of the drawn pixels) in a series, relative to their boxes
    related: [0.9, 0.75],       // a related card's packshot fills its frame by height (design-rules 14/10: one height for all)
    card: [0.5, 0.25],          // the kit's drawn width / its card's painted width (GEL 0.52–0.65; MASK's tall picture 0.28–0.35: low)
    onCard: [0.9, 0.5],         // share of the card's drawn picture inside the card's painted body
    scale: [0.1, 0.2],          // a hold's drawn height / the cover scale s, (max − min) / median over the desktop screens
  },
  L2: {
    edge: [1, 6],               // px spread of the right (start) edges of a column's blocks
    colEdge: [1, 6],            // px spread of the column's right edge across the screens of a viewport
    cpl: [[28, 78], [22, 90]],  // characters per full line of running Hebrew text: pass band, low band
    widow: 0.4,                 // a heading of ≥ 3 words whose last line is one word narrower than this share of its widest line
    gap: [1, 4],                // px spread of the gaps between chips / buttons on a line, rows, and their tops
    rowLast: 0.5,               // a wrapped chip row whose last line is one chip under this share of the widest line (low)
    short: 2,                   // letters: a word this short left at a line's end as a new sentence's first word (low)
  },
  L3: {
    sym: [2, 8],                // |left margin − right margin| of a centred block, px
    size: [1, 4],               // px spread of the widths / heights of cards in a row
    gap: [1, 4],                // px spread of the gaps between cards in a row
    pad: [6, 12],               // px: a card's top and bottom padding against its side padding (inside its painted body)
    stack: [2, 24],             // px spread of the widths of buttons stacked one per line
    group: [96, 160],           // px: the visible gap between a card's drawn picture and its text (one group, not two islands)
  },
  L4: {
    pair: [2, 8],               // px spread of one kind of gap (heading → lead, …) across the screens of a viewport
    section: [24, 96],          // px spread of the space between sections (phone and tablet blocks, stacked pages)
  },
  L5: {
    dy: [0.1, 0.12],            // |product centre − copy centre| / screen height (desktop holds and dock landings)
    cx: [0.12, 0.25],           // |gap left − gap right| / column width (desktop) or stage width (phone)
    even: [24, 64],             // px: |space heading → product − space product → text| (phone blocks)
    band: [0.15, 0.25],         // |space above the copy − space below it| / the free band's height (desktop, beside the product)
    level: [0.08, 0.12],        // spread of the product's centre over the desktop holds / screen height (one level on every screen)
    empty: [0.25, 0.35],        // phone: the largest stretch of the screen with nothing on it / screen height
    others: 40,                 // px of another section's text inside the band at a reading position: a second screen (low)
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
    dockAir: [24, 8],           // px from the copy's foot to the dock's top at a reading position (larger is better)
  },
  L8: {
    pose: [0.8, 0.5],           // phone: overlap (IoU) of the pose drawn when a heading is read with that screen's key pose
    card: 0.9,                  // the kit card's body opacity when the kit lands on it
    haze: 0.3,                  // the line's glow opacity behind the sections after the product (specialists, related)
    shift: [2, 24],             // px a section moves once the page is shown in its layout (the engine's html.story / .flow)
    flash: 250,                 // ms: a move sooner than this after the layout is in is a flash (low), later a jump
  },
};
const RULES = {
  L1: 'Picture fit: the drawn product inside its box — fill, vertical centring, no distortion, inside the grid; a card holds its picture; a series: one size, one baseline',
  L2: 'Text grid: one right edge per column, across screens and in the bar; line length, no widows or stranded short words, chips on one line and on a grid',
  L3: 'Symmetry: centred blocks with equal margins; cards equal, evenly spaced and padded, the row centred; stacked buttons one width; picture and text one group',
  L4: 'Rhythm: each kind of vertical gap the same on every screen; even section spacing',
  L5: 'Balance: desktop — the copy centred in the band, the product level with it, at one level on every screen, centred in its column, one section per screen; phone — centred in its block, even space around, no empty stretch',
  L6: 'Type and touch: sizes on the scale, body not below the minimum, contrast ≥ 4.5:1, tap targets ≥ 44 px on touch screens',
  L7: 'Off-screen and overlap: nothing past the screen or the free band when read, air above the dock; no text on text, on the product or under the chrome',
  L8: 'Motion state where it is read: the key pose when a heading is read (phone), the card there when the kit lands, the line colour only around the product, no layout jump after the page is shown',
};

const RULES_RU = {
  L1: 'Картинка вписана в своё место: заполнение (0.4–1 места), центр по вертикали, без искажения, внутри сетки; карточка держит свою картинку; серия — один размер и одна линия донышек',
  L2: 'Текстовая сетка: один правый край у блоков колонки, на всех экранах и в нижней панели; длина строки, без висячих слов и коротких слов в конце строки, чип в одну строку, чипы и кнопки на сетке',
  L3: 'Симметрия: центрированные блоки с равными полями; карточки равны, зазоры и поля ровные, ряд по центру; кнопки стопкой одной ширины; картинка и текст карточки — одна группа',
  L4: 'Ритм: каждый вид зазора одинаков на всех экранах; ровные расстояния между экранами (телефон)',
  L5: 'Баланс: десктоп — копия по центру полосы, продукт на её уровне и на одной высоте на всех экранах, по центру своей колонки, один раздел на экране; телефон — по центру блока, ровно вокруг, без пустых полос',
  L6: 'Шрифт и касание: кегли со шкалы, тело не мельче 15 px, контраст ≥ 4.5:1, цели касания ≥ 44 px',
  L7: 'За краем и наложения: ничего за экраном и свободной полосой в позиции чтения, воздух над доком; текст не на тексте, не на продукте, не под шапкой и доком',
  L8: 'Состояние движения в позиции чтения: ключевая поза, когда читают заголовок (телефон), карточка на месте, когда набор садится, цвет линейки только вокруг продукта, страница не прыгает после показа',
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
const inter = (a, b) => Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])) * Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]));
const IoU = (a, b) => { const i = inter(a, b), u = Wd(a) * H(a) + Wd(b) * H(b) - i; return u > 0 ? i / u : 0; };
const letters = w => (String(w).match(/[\p{L}\p{N}]/gu) || []).length;
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

  // ---------- per screen (a screen read a second time at the dock's landing: its balance only, «<id> @dock»)
  const colEdges = [], pairs = {}, secBounds = [], holds = [];
  for (const s0 of scr) {
    const s = Object.assign({}, s0, { blocks: s0.blocks.slice().sort((a, b) => a.rect[1] - b.rect[1] || b.rect[2] - a.rect[2]) });
    const F = s.env.free, bl = s.blocks.filter(b => b.role !== 'stage'), at = s.env.scrollY, dup = !!s0.via, where = s.id + (dup ? ' @' + s0.via : '');
    if (!bl.length) continue;
    const prod = s.product && !s.product.hidden ? s.product : null;
    const P = prod ? (prod.rect || prod.aabbRect) : null;
    const copyInk = [Math.min(...bl.map(b => b.inkL != null ? b.inkL : b.rect[0])), Math.min(...bl.map(topOf)), Math.max(...bl.map(b => b.rect[2])), Math.max(...bl.map(botOf))];
    if (!dup) secBounds.push({ id: s.id, top: Math.min(...s.blocks.map(b => b.rect[1]), s.wrap ? s.wrap[1] : 1e9) + at, bottom: Math.max(...s.blocks.map(b => b.rect[3]), s.wrap ? s.wrap[3] : -1e9) + at });
    const back = s.stepCards > 0;   // the step cards on the screen (GEL, MASK protocol): the product is their backdrop
    const judge = v => back && v !== 'pass' ? 'pass' : v, bx = back ? { note: 'backdrop behind the step cards: reported, not judged' } : {};

    // L1 + L5: the product at the hold
    if (mode === 'desk' && P && !(s.id === 'offer')) {
      const wrap = s.wrap || E.wrap, band = s.band;
      const box = centred(s) && band ? [Math.max(0.03 * W, 24), band.top, W - Math.max(0.03 * W, 24), band.bottom]
        : [wrap[0], F[0], (wrap[0] + wrap[2]) / 2, F[1]];
      const room = centred(s) ? box : [16, F[0], W / 2, F[1]];
      const fill = Math.max(H(P) / H(box), Wd(P) / Wd(box)), over = Math.max(0, room[0] - P[0], P[2] - room[2], room[1] - P[1], P[3] - room[3]);
      const cy = Math.abs((P[1] - box[1]) - (box[3] - P[3])) / H(box), cx = Math.abs((P[0] - box[0]) - (box[2] - P[2])) / Wd(box);
      const ex = { box: box.map(r1), product: P.map(r1), src: prod.src, p: prod.p };
      if (!dup) {   // the product's own fit is the hold's (the dock's landing: its pose against the hold's, L8 below)
        add('L1', 'fill', where, 'product', r3(fill), FILL_TOL() + ' of its column (band) in height or width', judge(fillSev(fill)), Object.assign({ fillH: r3(H(P) / H(box)), fillW: r3(Wd(P) / Wd(box)) }, ex, bx));
        add('L1', 'inside box', where, 'product', r1(over), '≤ ' + TOL.L1.over[0] + ' px past the screen\'s left half (16 px from its edge, header to dock)', lowIsGood(over, TOL.L1.over), Object.assign({}, ex, { room: room.map(r1) }));
        if (!centred(s)) { const g = Math.max(0, wrap[0] - P[0]);
          add('L1', 'inside grid', where, 'product', r1(g), '≤ ' + TOL.L1.grid[0] + ' px past the content grid\'s left edge (' + r1(wrap[0]) + ')', lowIsGood(g, TOL.L1.grid), Object.assign({ gridLeft: r1(wrap[0]), left: r1(P[0]), copyMargin: r1(W - wrap[2]), productMargin: r1(P[0]) }, ex)); }
        add('L1', 'centre y', where, 'product', r3(cy), '≤ ' + TOL.L1.centreY[0] + ' (|gap above − below| / band)', judge(lowIsGood(cy, TOL.L1.centreY)), Object.assign({}, ex, bx));
        if (prod.pic) add('L1', 'distortion', where, 'product canvas', prod.pic.distortion, '≤ ' + TOL.L1.distortion[0], lowIsGood(prod.pic.distortion, TOL.L1.distortion));
        add('L5', 'centred in column', where, 'product', r3(cx), '≤ ' + TOL.L5.cx[0] + ' (|gap left − right| / column)', lowIsGood(cx, TOL.L5.cx), ex);
      }
      if (!centred(s)) {
        const dy = ((P[1] + P[3]) / 2 - (copyInk[1] + copyInk[3]) / 2) / Hh;
        add('L5', 'level with copy', where, 'product vs copy', r3(Math.abs(dy)), '≤ ' + TOL.L5.dy[0] + ' × screen height', judge(lowIsGood(Math.abs(dy), TOL.L5.dy)),
          Object.assign({ dyPx: r1(dy * Hh), productCy: r1((P[1] + P[3]) / 2), copyCy: r1((copyInk[1] + copyInk[3]) / 2) }, bx));
        if (!dup && !back) holds.push({ id: s.id, cy: (P[1] + P[3]) / 2 - (F[0] + F[1]) / 2, h: H(P) });
      }
      // L7: the product within the screen's free band at its hold
      const cut = Math.max(0, F[0] - P[1], P[3] - F[1], -P[0], P[2] - W);
      if (!dup) add('L7', 'product on screen', where, 'product', r1(cut), '0 px past the header, the dock or the sides', lowIsGood(cut, TOL.L7.cut), ex);
    }
    // L5: the copy beside the product centred in the free band (its space above and below even) where it is read
    if (mode === 'desk' && !centred(s) && s.id !== 'offer') {
      const up = copyInk[1] - F[0], dn = F[1] - copyInk[3], v = Math.abs(up - dn) / (F[1] - F[0]);
      add('L5', 'copy centred in band', where, 'copy', r3(v), '≤ ' + TOL.L5.band[0] + ' (|space above − below| / band)', judge(lowIsGood(v, TOL.L5.band)), Object.assign({ above: r1(up), below: r1(dn), copy: [r1(copyInk[1]), r1(copyInk[3])], free: F }, bx));
    }
    if (mode === 'desk' && s.others && s.others.length) {   // another section's text on the same screen (a line entering at the edge is scrolling, not a second screen)
      const o = s.others.reduce((a, x) => x.px > a.px ? x : a, s.others[0]);
      if (o.px >= TOL.L5.others) add('L5', 'one section per screen', where, 'next section on screen: ' + s.others.map(x => x.id).join(', '), r1(o.px), '< ' + TOL.L5.others + ' px of another section\'s text between the header and the dock', 'low', { others: s.others });
    }
    if (mode === 'stage' && P && s.id !== 'offer' && s.env.stage && !dup) {   // the tablet stage under the header (GEL): the product in the stage
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
      // what the block shows when its heading is read (the anchor's landing): the live canvas, if it is in this block
      if (mode === 'flow' && s.id !== 'open' && prod && prod.pic && prod.pic.elBox && P) {
        const cv = prod.pic.elBox, inBlock = inter(cv, box) > 0.5 * Wd(cv) * H(cv);
        if (inBlock) {
          const A = prod.aabbRect || P, over = Math.max(0, box[0] - A[0], A[2] - box[2], box[1] - A[1], A[3] - box[3]);
          const k = s.at && s.at.expectP != null ? s.at.expectP : null, drawn = prod.drawnP != null ? prod.drawnP : prod.p;
          const ex = { box: box.map(r1), live: P.map(r1), outline: A.map(r1), drawn: drawn == null ? null : r3(drawn), f: drawn == null ? null : r3(drawn - Math.floor(drawn + 1e-6)) };
          add('L1', 'inside box (live)', s.id, 'the 3D in its block when the heading is read', r1(over), '≤ ' + TOL.L1.over[0] + ' px of the scene\'s outline past its block', lowIsGood(over, TOL.L1.over),
            Object.assign({ past: { left: r1(box[0] - A[0]), top: r1(box[1] - A[1]), right: r1(A[2] - box[2]), bottom: r1(A[3] - box[3]) } }, ex));
          if (s.still && s.still.content) {
            const iou = IoU(P, s.still.content);
            add('L8', 'key pose at landing', s.id, 'pose drawn vs the screen\'s key pose (its still)', r3(iou), '≥ ' + TOL.L8.pose[0] + ' overlap of the drawn product with the key pose', highIsGood(iou, TOL.L8.pose), Object.assign({ key: s.still.content.map(r1) }, ex));
          }
        }
      }
    }
    if (mode === 'desk' && !P && s.slotPic && s.slotPic.content) {   // no WebGL: the still beside the copy
      const c = s.slotPic.content, b = s.slotPic.box;
      add('L1', 'fill', where, 'still beside copy', r3(Math.max(H(c) / H(b), Wd(c) / Wd(b))), '≥ ' + TOL.L1.fill[0], highIsGood(Math.max(H(c) / H(b), Wd(c) / Wd(b)), TOL.L1.fill));
    }

    // L3: the opening's name and subtitle centred on the screen
    if (s.centred && !dup) for (const c of s.centred) if (c.ink) {
      const d = Math.abs(c.ink[0] - (W - c.ink[2]));
      add('L3', 'centred', s.id, c.sel.split(' > ').pop(), r1(d), '≤ ' + TOL.L3.sym[0] + ' px (|left − right margin|)', lowIsGood(d, TOL.L3.sym), { left: r1(c.ink[0]), right: r1(W - c.ink[2]) });
    }
    if (centred(s)) { if (!dup) for (const b of bl) widows(b, s.id); continue; }

    if (!dup) {
      // L2: one right edge for the column's blocks
      const edges = bl.map(b => ({ b, x: rightEdge(b) })).filter(e => e.x != null);
      if (edges.length > 1) {
        const xs = edges.map(e => e.x), med = median(xs), sp = spread(xs), worst = edges.reduce((a, e) => Math.abs(e.x - med) > Math.abs(a.x - med) ? e : a, edges[0]);
        add('L2', 'right edge', s.id, 'column (' + edges.length + ' blocks)', r1(sp), '≤ ' + TOL.L2.edge[0] + ' px spread', lowIsGood(sp, TOL.L2.edge), { edges: edges.map(e => [e.b.role, r1(e.x)]), worst: label(worst.b) });
        colEdges.push({ id: s.id, x: med });
      }
      for (const b of bl) { lineLength(b, s.id); widows(b, s.id); rowGrid(b, s.id); chipLines(b, s.id); bodyTails(b, s.id); }
      // L4: the gaps between consecutive blocks (never across the phone's product block)
      for (let i = 1; i < s.blocks.length; i++) {
        const a = s.blocks[i - 1], b = s.blocks[i];
        if (['stage', 'card', 'cards'].includes(a.role) || ['stage', 'card', 'cards'].includes(b.role)) continue;
        if (b.rect[1] < a.rect[3] - 2) continue;   // side by side (MASK's slot beside the heading)
        const k = a.role + '→' + b.role, g = topOf(b) - botOf(a);
        (pairs[k] = pairs[k] || []).push({ id: s.id, g, box: b.rect[1] - a.rect[3] });
      }
    }
    // L7: the copy whole in the free band at its reading position (desktop and the tablet stage: a screen is read whole)
    if (mode === 'desk' || (mode === 'stage' && s.id !== 'offer')) {
      const top = Math.min(...bl.map(b => b.rect[1])), bot = Math.max(...bl.map(b => b.rect[3]));
      const cut = Math.max(0, F[0] - top, bot - F[1]);
      add('L7', 'copy on screen', where, 'copy', r1(cut), '0 px past the header / dock / stage', lowIsGood(cut, TOL.L7.cut), { copy: [r1(top), r1(bot)], free: F });
      if (mode === 'desk' && s.env.dock && bot <= F[1]) { const air = F[1] - bot;
        add('L7', 'air above dock', where, 'copy foot → dock', r1(air), '≥ ' + TOL.L7.dockAir[0] + ' px', highIsGood(air, TOL.L7.dockAir), { copyFoot: r1(bot), dockTop: F[1] }); }
      for (const u of s.overlap.underChrome) add('L7', 'under chrome', where, u.role + ' under ' + u.chrome, r1(u.area), 'no text under the header / dock / bar', u.area > 400 ? 'high' : 'low', { rect: u.rect });
    } else if (!dup) {   // a phone: the heading lands under the header, not under it
      const f = s.blocks[0], hb = s.env.header ? s.env.header[3] : 0;   // the header only: on a phone the copy runs on under the bar, read by scrolling
      if (f && s.id !== 'open') { const cut = Math.max(0, hb - f.rect[1]); add('L7', 'heading below header', s.id, f.role, r1(cut), '0 px', lowIsGood(cut, TOL.L7.cut)); }
    }
    for (const o of s.overlap.textOnPicture) add('L7', 'text on product', where, o.role, o.cover, 'no product pixels under text (≤ ' + TOL.L7.cover[1] + ' of a line: low)', o.cover <= TOL.L7.cover[1] ? 'low' : 'high', { rect: o.rect, bbox: !!o.bbox });
    for (const o of s.overlap.textOnText) add('L7', 'text on text', where, o.roles.join(' / '), r1(o.area), 'none', 'high');
  }
  // L8: the dock's landing shows the hold's key pose (desktop): the product there against the one at its place in the hold
  if (mode === 'desk') for (const d of scr.filter(x => x.via === 'dock')) {
    const h = scr.find(x => x.id === d.id && !x.via), Pd = d.product && !d.product.hidden ? (d.product.rect || d.product.aabbRect) : null, Ph = h && h.product && !h.product.hidden ? (h.product.rect || h.product.aabbRect) : null;
    if (!Pd || !Ph || d.id === 'offer') continue;
    const iou = IoU(Pd, Ph);
    add('L8', 'key pose at landing', d.id + ' @dock', 'the product at the dock\'s landing vs the hold\'s key pose', r3(iou), '≥ ' + TOL.L8.pose[0] + ' overlap with the pose in the hold', highIsGood(iou, TOL.L8.pose),
      { key: Ph.map(r1), live: Pd.map(r1), size: [r1(Wd(Pd)), r1(H(Pd))], keySize: [r1(Wd(Ph)), r1(H(Ph))], cls: (d.env.cls || '').split(/\s+/).filter(c => /^mt-/.test(c)).join(' ') });
  }
  // L5: the product at one height on every desktop hold (the eye reads the screens one after another)
  if (holds.length > 2) {
    const ys = holds.map(h => h.cy), sp = spread(ys) / Hh, med = median(ys);
    add('L5', 'level across screens', 'all screens', 'product centre on the holds (' + holds.length + ')', r3(sp), '≤ ' + TOL.L5.level[0] + ' × screen height spread', lowIsGood(sp, TOL.L5.level),
      { spreadPx: r1(spread(ys)), offsets: holds.map(h => [h.id, r1(h.cy)]), fromMedian: holds.map(h => [h.id, r1(h.cy - med)]) });
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
    // L2: a wrapped row whose last line is one item under half the widest line (3 + 1)
    if (rows.length > 1 && b.role !== 'cta') {
      const rw = rows.map(r => Math.max(...r.map(x => x[2])) - Math.min(...r.map(x => x[0]))), share = rw[rw.length - 1] / Math.max(...rw);
      const lone = rows[rows.length - 1].filter(x => x !== lab).length === 1 && rows[rows.length - 2].filter(x => x !== lab).length >= 2 && share < TOL.L2.rowLast;
      add('L2', 'row balance', where, b.role + ' (' + b.items.length + ')', r3(share), 'a wrapped row: its last line not one item under ' + TOL.L2.rowLast + ' of the widest', lone ? 'low' : 'pass', { perRow: rows.map(r => r.length), rowWidths: rw.map(r1) });
    }
    // L3: buttons stacked one per line: one width (a ragged edge under the copy otherwise)
    if (b.role === 'cta' && rows.length > 1 && rows.every(r => r.length === 1)) {
      const ws = rows.map(r => Wd(r[0])), d = spread(ws);
      add('L3', 'stacked buttons', where, 'cta (' + rows.length + ' stacked)', r1(d), '≤ ' + TOL.L3.stack[0] + ' px width spread', lowIsGood(d, TOL.L3.stack), { widths: ws.map(r1) });
    }
  }
  function chipLines(b, where) {   // L2: a chip (a pill) holds one line; a wrapped one, worst with a lone word on its last line, reads as a broken button
    if (!['chips', 'badges'].includes(b.role) || !b.itemText || !b.itemText.length || b.itemText[0].lastWords == null) return;
    const wrapped = b.itemText.filter(t => t.lines > 1), lone = wrapped.filter(t => t.lastWords === 1);
    add('L2', 'chip on one line', where, b.role + ' (' + b.itemText.length + ')', wrapped.length, 'every chip on one line (a lone word on a chip\'s second line: high)', !wrapped.length ? 'pass' : lone.length ? 'high' : 'low',
      { lines: b.itemText.map(t => t.lines), lone: lone.map(t => t.lastText) });
  }
  function bodyTails(b, where) {   // L2: running text — no short word opening a sentence at a line's end, no one-word last line
    if (!['lead', 'note'].includes(b.role) || !b.lines || b.lines.length < 2 || !b.lines[0].tail) return;
    const dang = [];
    for (const L of b.lines.slice(0, -1)) { const t = L.tail, w = t[t.length - 1], pv = t.length > 1 ? t[0] : '';
      if (w && letters(w) <= TOL.L2.short && /[.!?:;]["'»”)]?$/.test(pv)) dang.push(pv + ' ' + w); }
    add('L2', 'short word at line end', where, label(b), dang.length, 'no word of ≤ ' + TOL.L2.short + ' letters opening a sentence at a line\'s end', dang.length ? 'low' : 'pass', dang.length ? { words: dang } : undefined);
    const last = b.lines[b.lines.length - 1], wide = Math.max(...b.lines.slice(0, -1).map(l => l.r - l.l));
    add('L2', 'one word on the last line', where, label(b), r3((last.r - last.l) / wide), 'a paragraph\'s last line: more than one word', last.words === 1 ? 'low' : 'pass', last.words === 1 ? { last: b.lastText } : undefined);
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
      for (const i of st.items) for (const b of i.blocks) { lineLength(b, 'steps'); widows(b, 'steps'); bodyTails(b, 'steps'); }
      for (const b of st.head || []) widows(b, 'steps');
      // L3: a desktop card's drawn picture and its text read as one group: the visible gap between them (drawn pixels to text ink)
      if (!st.scroller || st.scroller === 'visible') it.forEach((i, n) => {
        const c = i.pic.content, ink = i.blocks.length ? [Math.min(...i.blocks.map(b => b.inkL != null ? b.inkL : b.rect[0])), Math.max(...i.blocks.map(b => b.rect[2]))] : [i.text[0], i.text[2]];
        const textRight = ink[0] >= c[2], gap = textRight ? ink[0] - c[2] : c[0] >= ink[1] ? c[0] - ink[1] : 0, cont = st.cont || i.rect;
        add('L3', 'picture and text one group', 'step ' + (n + 1), 'drawn picture ↔ text', r1(gap), '≤ ' + TOL.L3.group[0] + ' px visible gap', lowIsGood(gap, TOL.L3.group),
          { outerMargin: r1(textRight ? c[0] - cont[0] : cont[2] - c[2]), slotW: r1(Wd(i.pic.box)), drawnW: r1(Wd(c)), widthShare: r3(Wd(c) / Wd(i.pic.box)) });
      });
      // picture and text level in a desktop card
      if (!st.scroller || st.scroller === 'visible') {
        const d = Math.max(...it.map(i => Math.abs(((i.pic.content[1] + i.pic.content[3]) / 2) - ((i.text[1] + i.text[3]) / 2))));
        add('L5', 'picture level with text', 'steps', 'step cards', r1(d), '≤ ' + Math.round(TOL.L5.dy[0] * Hh) + ' px', lowIsGood(d / Hh, TOL.L5.dy));
      }
    } else {
      rowCards(st.items.map(i => i.rect), 'steps', 'step cards', st.cont, st.scroller && st.scroller !== 'visible');
      for (const i of st.items) for (const b of i.blocks) { lineLength(b, 'steps'); widows(b, 'steps'); bodyTails(b, 'steps'); }
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
    // L1: the card holds its picture — the kit as wide as a good part of the card, and on the card's painted body
    const pb = kit.painted && kit.painted.rect;
    if (pic && pic.content && pb) {
      const P = pic.content, share = Wd(P) / Wd(pb), on = Math.max(0, Math.min(P[3], pb[3]) - Math.max(P[1], pb[1])) / H(P);
      add('L1', 'share of its card', 'kit card', 'kit picture width / card width', r3(share), '≥ ' + TOL.L1.card[0], highIsGood(share, TOL.L1.card), { drawnW: r1(Wd(P)), cardW: r1(Wd(pb)), drawnH: r1(H(P)) });
      add('L1', 'on its card', 'kit card', 'drawn picture on the card\'s painted body', r3(on), '≥ ' + TOL.L1.onCard[0], highIsGood(on, TOL.L1.onCard), { painted: pb, layer: kit.painted.layer, picture: P });
    }
    // L3: the card's padding — top and bottom like its sides, inside its painted body
    if (pb && kit.pad) {
      const inside = (kit.blocks || []).map(b => b.rect).concat(pic && pic.box ? [kit.fig || pic.box] : []).filter(r => r[1] >= pb[1] - 1 && r[3] <= pb[3] + 1);
      if (inside.length) {
        const top = Math.min(...inside.map(r => r[1])) - pb[1], bot = pb[3] - Math.max(...inside.map(r => r[3])), side = (kit.pad[0] + kit.pad[2]) / 2;
        const d = Math.max(Math.abs(top - side), Math.abs(bot - side));
        add('L3', 'card padding', 'kit card', 'top / bottom vs side padding', r1(d), '≤ ' + TOL.L3.pad[0] + ' px', lowIsGood(d, TOL.L3.pad), { top: r1(top), bottom: r1(bot), side: r1(side) });
      }
    }
    // (another section beside the card: read on the offer's screen, the same place)
  }
  // L8: the card is there when the kit lands on it (desktop: the card's top at 25 % of the screen)
  const kl = firstOf('kit-land');
  if (kl && kl.card && kl.bodyOp != null) {
    const shown = (kl.after || []).find(x => x[1] != null && x[1] >= TOL.L8.card);
    add('L8', 'card at landing', 'kit card', 'the card\'s body when the kit lands', kl.bodyOp, '≥ ' + TOL.L8.card + ' opacity', kl.bodyOp >= TOL.L8.card - 1e-9 ? 'pass' : 'low',
      { shownAfterPx: shown ? shown[0] : null, samples: kl.after });
  }
  // L8: the line's colour stays with the product's screens
  for (const k of ['specialists', 'related']) { const x = firstOf(k); if (x && x.haze)
    add('L8', 'line colour after the product', k, 'the line\'s glow behind the section', x.haze.glow, '≤ ' + TOL.L8.haze + ' opacity', x.haze.glow <= TOL.L8.haze + 1e-9 ? 'pass' : 'low', { layers: x.haze.layers }); }
  // L2: the bottom bar's label (name and purpose) on one right edge
  const bar = raw.chrome && raw.chrome.barLabel;
  if (bar && bar.lines && bar.lines.length > 1) { const d = spread(bar.lines.map(l => l.r));
    add('L2', 'right edge', 'bottom bar', 'name + purpose (' + bar.lines.length + ' lines)', r1(d), '≤ ' + TOL.L2.edge[0] + ' px spread of the lines\' right edges', lowIsGood(d, TOL.L2.edge), { edges: bar.lines.map(l => [l.text, r1(l.r)]) }); }
  // L5: a phone's screen never mostly empty — the largest stretch of the free band (header → bar) with nothing on it at any scroll
  if (raw.scan && raw.scan.gaps) {
    const E2 = raw.scan.env, top = E2.header ? E2.header[3] : 0, foot = E2.bar ? E2.bar[1] : E2.H, win = foot - top;
    const g = raw.scan.gaps.map(x => Object.assign({}, x, { shown: Math.min(x.px, win) }));
    const first = raw.scan.firstScreen ? raw.scan.firstScreen.px : null;
    if (g.length) { const w = g.reduce((a, x) => x.shown > a.shown ? x : a, g[0]), v = w.shown / Hh;
      add('L5', 'empty band', 'page', 'largest empty stretch: ' + w.above + ' → ' + w.below, r3(v), '≤ ' + TOL.L5.empty[0] + ' × screen height', lowIsGood(v, TOL.L5.empty),
        { px: r1(w.shown), at: [w.from, w.to], window: r1(win), firstScreenPx: r1(first), gaps: g.slice(0, 5).map(x => [x.from, x.to, r1(x.shown), x.above + ' → ' + x.below]) }); }
    if (raw.scan.firstScreen) { const f = raw.scan.firstScreen, v = f.px / Hh;   // the first screen, as it is at the page's top
      add('L5', 'empty band (first screen)', 'page', 'the first screen\'s largest empty stretch', r3(v), '≤ ' + TOL.L5.empty[0] + ' × screen height', lowIsGood(v, TOL.L5.empty), { px: f.px, at: [f.from, f.to] }); }
  }
  // L8: the page does not jump once it is shown in its own layout (the engine's mode set: html.story / .flow): sections that
  // move after that, by how much and how late (the phone's gaps between blocks written after the blocks are shown)
  const loads = [raw.load].concat(raw.loadRuns || []).filter(l => l && l.samples && l.samples.length && l.readyT != null).map(l => {
    const S = l.samples, i0 = S.findIndex(x => x.ready), ref = S[Math.max(0, i0)], m = new Map(ref.tops);
    const moved = x => Math.max(0, ...x.tops.map(([id, y]) => m.has(id) ? Math.abs(y - m.get(id)) : 0));
    let late = 0, lateMs = 0, flash = 0, flashMs = 0, prev = ref;
    for (const x of S.slice(Math.max(0, i0) + 1)) {   // each change after the layout is in: how far the sections have gone, and when
      const same = x.h === prev.h && x.tops.every(([id, y], k) => prev.tops[k] && prev.tops[k][1] === y); prev = x; if (same) continue;
      const d = moved(x), dt = x.t - ref.t;
      if (dt >= TOL.L8.flash) { if (d > late) { late = d; lateMs = dt; } } else if (d > flash) { flash = d; flashMs = dt; }
    }
    const fin = S[S.length - 1];
    return { late, lateMs, flash, flashMs, readyMs: ref.t, moves: fin.tops.filter(([id, y]) => m.has(id) && Math.abs(y - m.get(id)) > 0.5).map(([id, y]) => [id, r1(y - m.get(id))]), heights: [ref.h, fin.h] };
  });
  if (loads.length) {
    const w = loads.reduce((a, x) => x.late > a.late ? x : a, loads[0]), fl = loads.reduce((a, x) => x.flash > a.flash ? x : a, loads[0]);
    const sev = w.late > 0 ? lowIsGood(w.late, TOL.L8.shift) : fl.flash > TOL.L8.shift[0] ? 'low' : 'pass';   // a jump within a few frames of the layout: a flash (low)
    add('L8', 'late layout shift', 'page', 'sections moving after the page is shown in its layout (worst of ' + loads.length + ' load' + (loads.length > 1 ? 's' : '') + ')', r1(w.late > 0 ? w.late : fl.flash),
      '≤ ' + TOL.L8.shift[0] + ' px ' + TOL.L8.flash + ' ms or more after the engine\'s layout is in (sooner: a flash, low)', sev,
      { lateMs: w.late > 0 ? w.lateMs : null, flashMs: w.late > 0 ? null : fl.flashMs, runs: loads.map(x => [r1(x.late), x.lateMs, r1(x.flash), x.flashMs]), moves: (w.late > 0 ? w : fl).moves, heights: (w.late > 0 ? w : fl).heights });
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
    for (const i of g.items) for (const b of i.blocks) { widows(b, where); bodyTails(b, where); }
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
        const part = row.length < (cols || rows[0].length), sev = lowIsGood(d, TOL.L3.sym);   // an incomplete row: the grid leaves its columns at the start (RTL: right)
        add('L3', 'row centred', where, el + ' (' + row.length + (cols ? ' in ' + cols + ' columns' : '') + ')', r1(d), '≤ ' + TOL.L3.sym[0] + ' px (|left − right margin|)', part && sev === 'high' ? 'low' : sev,
          Object.assign({ left: r1(u[0] - cont[0]), right: r1(cont[2] - u[2]) }, part ? { note: 'an incomplete row (fewer cards than columns): the template, the same on the approved pages' } : {})); }
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
  // L1 across the desktop screens of a page: each hold's product grows with the screen as the engine's cover does
  // (s = max(W/16, H/10)): its drawn height / s the same on every desktop viewport (the template's 3D; MASK has its own)
  for (const p of Object.values(pages)) {
    const per = {};
    for (const raw of raws.filter(r => r.slug === p.slug && modeOf(r) === 'desk' && r.env0.adapter === 'story')) {
      const s = Math.max(raw.env0.W / 16, raw.env0.H / 10);
      for (const sc of raw.screens) { if (sc.err || sc.via || sc.id === 'offer' || sc.id === 'open' || sc.hero || !sc.product || sc.product.hidden || sc.stepCards > 0) continue;   // the opening: framed in its band, not by the cover
        const P = sc.product.rect || sc.product.aabbRect; if (!P) continue; (per[sc.id] = per[sc.id] || []).push([raw.vp.id, (P[3] - P[1]) / s]); }
    }
    p.cross = [];
    for (const [id, l] of Object.entries(per)) if (l.length > 2) {
      const v = l.map(x => x[1]), d = spread(v) / median(v);
      p.cross.push({ rule: 'L1', check: 'scales with the screen', where: id, el: 'drawn height / cover scale (' + l.length + ' desktop screens)', value: r3(d),
        tol: '≤ ' + TOL.L1.scale[0] + ' (spread / median)', sev: lowIsGood(d, TOL.L1.scale), perScreen: l.map(x => [x[0], r3(x[1])]) });
    }
  }
  for (const p of Object.values(pages)) {
    const fails = [];
    for (const [vp, v] of Object.entries(p.viewports)) for (const c of v.checks) if (c.sev !== 'pass') fails.push(Object.assign({ vp }, c));
    for (const c of p.cross || []) if (c.sev !== 'pass') fails.push(Object.assign({ vp: 'all' }, c));
    p.summary = { high: fails.filter(f => f.sev === 'high').length, low: fails.filter(f => f.sev === 'low').length, pass: Object.values(p.viewports).reduce((a, v) => a + v.counts.pass, 0) + (p.cross || []).filter(c => c.sev === 'pass').length,
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
  for (const k of ['fillH', 'fillW', 'dyPx', 'above', 'below', 'left', 'right', 'median', 'nearest', 'w', 'h', 'px', 'firstScreenPx', 'gridLeft', 'outerMargin', 'widthShare',
    'drawnW', 'cardW', 'top', 'bottom', 'side', 'drawn', 'f', 'shownAfterPx', 'spreadPx', 'readyMs', 'lateMs', 'flashMs']) if (f[k] != null && typeof f[k] !== 'object') x.push(k + ' ' + f[k]);
  if (f.past) x.push('past ' + Object.entries(f.past).filter(e => e[1] > 0).map(e => e[0] + ' ' + e[1]).join(', '));
  if (f.fromMedian) x.push(f.fromMedian.map(e => e.join(' ')).join(', '));
  if (f.moves && f.moves.length) x.push('moved ' + f.moves.map(e => e.join(' ')).join(', '));
  if (f.runs && f.check === 'late layout shift') x.push('loads: ' + f.runs.map(r => r[0] ? r[0] + ' px at ' + r[1] + ' ms' : r[2] ? 'flash ' + r[2] + ' px at ' + r[3] + ' ms' : '0').join(', '));
  if (f.widths) x.push('widths ' + f.widths.join('/'));
  if (f.size && f.keySize) x.push('size ' + f.size.join('×') + ' vs ' + f.keySize.join('×') + (f.cls ? ' (' + f.cls + ')' : ''));
  if (f.heights && f.check === 'late layout shift') x.push('page ' + f.heights.join(' → ') + ' px');
  if (f.perRow) x.push('per row ' + f.perRow.join('+') + (f.rowWidths ? ' (' + f.rowWidths.join('/') + ' px)' : ''));
  if (f.lone && f.lone.length) x.push('lone: ' + f.lone.join(' | ')); else if (f.lines && typeof f.lines[0] === 'number') x.push('lines ' + f.lines.join('/'));
  if (f.words) x.push(f.words.join(' | ')); if (f.last) x.push('«' + f.last + '»');
  if (f.others) x.push(f.others.map(o => o.id + ' ' + o.top + '…' + o.bottom).join(', '));
  if (f.perScreen) x.push(f.perScreen.map(e => e.join(' ')).join(', '));
  if (f.gaps && f.check === 'empty band') x.push(f.gaps.slice(0, 3).map(g => g[0] + '…' + g[1] + ' (' + g[2] + ' px: ' + g[3] + ')').join('; '));
  if (f.heights && f.check !== 'late layout shift') x.push('heights ' + f.heights.join('/')); if (f.feetAboveBox) x.push('feet ' + f.feetAboveBox.join('/')); if (f.feet) x.push('feet ' + f.feet.join('/'));
  if (f.gaps && typeof f.gaps[0] !== 'object') x.push('gaps ' + f.gaps.join('/'));
  if (f.gaps && typeof f.gaps[0] === 'object' && f.check !== 'empty band') x.push(f.gaps.map(g => g.join(' ')).join(', '));
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
  L.push(`# Вёрстка по замерам (L1–L8): ${target}`, '');
  L.push(`Сгенерировано ${res.generated.slice(0, 16).replace('T', ' ')} UTC скриптом \`site/proto/qa/layout-check.cjs\` (замеры DOM, Range-строк и альфы картинок, без скриншотов). ` +
    `Эталоны: ${res.refs.join(', ')}. Правила и допуски — \`design-rules.md\`, раздел «Сайт v2 — вёрстка по замерам (L1–L8)». Полные значения — \`${target}.layout.json\`.`, '');
  if (notes._summary) L.push(notes._summary, '');
  if (Array.isArray(notes._eye) && notes._eye.length) L.push('## Взгляд со стороны: чем ловится каждое место', '', ...notes._eye, '');
  L.push('## Сводка', '', '| Страница | экраны | проверок | pass | low | high | L1 | L2 | L3 | L4 | L5 | L6 | L7 |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|');
  for (const p of Object.values(res.pages)) {
    const vps = Object.keys(p.viewports).length, n = p.summary.pass + p.summary.low + p.summary.high;
    L.push(`| ${p.slug} | ${vps} | ${n} | ${p.summary.pass} | ${p.summary.low} | ${p.summary.high} | ` + Object.keys(RULES).map(k => `${p.summary.byRule[k].high}/${p.summary.byRule[k].low}`).join(' | ') + ' |');
  }
  L.push('', 'В колонках L1–L8: high/low.', '');
  L.push('## Правила и допуски', '');
  for (const k of Object.keys(RULES)) L.push(`- **${k}** — ${RULES_RU[k]}. Допуски [pass, low]: \`${JSON.stringify(res.tolerances[k])}\``);
  L.push('');
  // the values: the main measures of the target page, screen by screen, on every viewport (✓ pass, · low, ✗ high)
  if (pg) {
    const vps = Object.keys(pg.viewports), KEYS = [['L1', 'fill'], ['L1', 'centre y'], ['L1', 'inside grid'], ['L5', 'centred in column'], ['L5', 'centred in block'], ['L5', 'centred in stage'], ['L5', 'level with copy'],
      ['L5', 'copy centred in band'], ['L5', 'level across screens'], ['L5', 'even around product'], ['L5', 'empty band'], ['L5', 'empty band (first screen)'], ['L1', 'inside box (live)'], ['L8', 'key pose at landing'], ['L7', 'copy on screen'], ['L7', 'air above dock'],
      ['L7', 'product on screen'], ['L2', 'right edge'], ['L1', 'series size'], ['L1', 'series baseline'], ['L3', 'picture and text one group'], ['L1', 'share of its card'], ['L1', 'on its card'], ['L3', 'card padding'],
      ['L3', 'stacked buttons'], ['L2', 'chip on one line'], ['L3', 'row centred'], ['L8', 'card at landing'], ['L8', 'line colour after the product'], ['L8', 'late layout shift']];
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
