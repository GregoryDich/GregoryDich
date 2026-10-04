// Print edition of the protocols in the catalogue's A5 landscape system (794 x 561 px, like the Figma frames).
// Usage: node mitoderm-catalog/protocols/print/build-print.mjs [he ru en]
// Needs playwright-core (resolvable via NODE_PATH or PLAYWRIGHT_CORE) and Chromium (CHROMIUM_PATH).
// QA_DIR=<dir> also writes a PNG of every page for review.
// press.py then trims the page box and writes a -press.pdf copy with 3 mm bleed (needs python3 + PyMuPDF).
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { esc, clean, tieRu, PRODUCT_RE } from '../src/page.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const CHROME = process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const DIMS = JSON.parse(readFileSync(join(here, 'img/dims.json'), 'utf8'));
const QA = process.env.QA_DIR;

// Section colour of each protocol (catalogue: bronze exosomes, green BIOSPICULE, graphite devices)
// and the packshots standing on its panel, with relative heights.
// fill: products named on the protocol's last page; they stand in the column the text leaves empty.
const SEC = {
  'vtech-mitopen': { sec: '#241C12', acc: '#9E661F', shelf: [['vtech-system', .82], ['mitopen', 1]], fill: [['exocell-mask', .72], ['derma-recovery', .86]] },
  'biospicule-vtech': { sec: '#1E4634', acc: '#294D3B', shelf: [['micro-boost-10', 1], ['vtech-system', .56]], fill: [['cell-renew-15', 1], ['derma-recovery', .7], ['exotech-gel', .4]] },
  'cell-booster': { sec: '#26262A', acc: '#9E661F', shelf: [['mitopen', 1], ['micro-boost-10', .84]] },
  'exosignal-hair': { sec: '#241C12', acc: '#9E661F', shelf: [['exosignal-hair', .5], ['mitopen', 1]], fill: [['exosignal-hair', .62]] },
  'exo-nad': { sec: '#241C12', acc: '#9E661F', shelf: [['exo-nad', .56]], fill: [['exo-nad', .62]] },
  'exocell-mask': { sec: '#241C12', acc: '#9E661F', shelf: [['exocell-mask', .7]] },
  'home': { sec: '#241C12', acc: '#9E661F' },
  'maintain': { sec: '#1E4634', acc: '#294D3B' },
};
// Sections of each standard protocol in the order of the source document.
const ORDER = {
  'vtech-mitopen': ['steps', 'aside:0', 'after:0', 'after:1', 'aside:1'],
  'biospicule-vtech': ['steps', 'after:0', 'aside:0', 'after:1'],
  'cell-booster': ['steps', 'after:0'],
  'exosignal-hair': ['steps', 'after:0', 'after:1', 'aside:0'],
};
const STEP = { he: 'שלב', ru: 'Шаг', en: 'Step' };
const NAMES = {
  'cell-renew-15': 'CELL RENEW 1.5%', 'cellular-age-25': 'CELLULAR AGE DEFENSE 2.5%', 'derma-recovery': 'DERMA RECOVERY CREAM',
  'exotech-gel': 'EXOTECH GEL', 'mitoscan': 'MITOSCAN',
};
const COLO = 'MITODERM | WHERE SCIENCE MEETS BEAUTY';

// Products standing on one line, bottom-aligned, scaled to fit the zone.
function shelf(items, zoneW, zoneH, gap = 14) {
  let sizes = items.map(([k, f]) => { const [w, h] = DIMS[k]; const H = zoneH * f; return [k, (H * w) / h, H]; });
  const free = zoneW - gap * (items.length - 1), sum = sizes.reduce((a, s) => a + s[1], 0);
  const sc = sum > free ? free / sum : 1;
  return sizes.map(([k, w, h]) => `<img src="img/${k}.webp" alt="" style="width:${(w * sc).toFixed(1)}px;height:${(h * sc).toFixed(1)}px">`).join('');
}

function html(C) {
  const rtl = C.dir === 'rtl';
  const T = C.lang === 'ru' ? tieRu : s => s;
  const L = s => (rtl && !/[֐-׿]/.test(s) ? `<bdi dir="ltr">${esc(clean(s))}</bdi>` : esc(T(clean(s))));
  const TT = s => L(s).replace(/MICRO BOOST 10%/g, 'MICRO\u00a0BOOST\u00a010%');
  const rich = s => esc(T(clean(s))).replace(PRODUCT_RE, m => (rtl && m.endsWith('™') ? `<bdi class="pn">${m}</bdi>` : `<span class="pn">${m}</span>`));
  const head = s => `<h4 class="b h kwn">${L(s)}</h4>`;
  const ul = items => `<ul class="b ul">${items.map(s => `<li>${rich(s)}</li>`).join('')}</ul>`;
  const item = it => {
    if (typeof it === 'string') return `<p class="b p${/:\s*$/.test(it) ? ' kwn' : ''}">${rich(it)}</p>`;
    if (it.list) return ul(it.list);
    if (it.products) return ul(it.products.map(([s]) => s));
    if (it.note) return `<p class="b note">${rich(it.note)}</p>`;
    if (it.chips) return `<p class="b p pipes">${it.chips.map(c => esc(T(clean(c)))).join('<span class="sep"> | </span>')}</p>`;
    if (it.options) return it.options.map(([l, t]) => `<div class="b opt"><span class="opt-l">${rich(l)}</span>${rich(t)}</div>`).join('');
    throw new Error('Unknown item ' + JSON.stringify(it));
  };
  const section = b => (b.title ? head(b.title) : '') + b.body.map(item).join('');
  const steps = list => {
    if (list.every(s => typeof s === 'string' || !s.title)) return ul(list.map(s => (typeof s === 'string' ? s : s.body[0])));
    return list.map((st, i) => head(`${STEP[C.lang]} ${i + 1} – ${st.title}`) + st.body.map(item).join('')
      + (st.figure ? `<figure class="b fig"><img src="img/${st.figure}.webp" alt=""><figcaption>${esc(NAMES[st.figure])}</figcaption></figure>` : '')).join('');
  };
  const vars = id => `--sec:${SEC[id].sec};--acc:${SEC[id].acc}`;

  const opener = (f, p, blocks) => `<template data-kind="opener" data-sec="${p.id}" data-cont="${esc(L(p.title))}">
<section class="page opener" style="${vars(p.id)}">
<div class="panel"><div class="pglow"></div><div class="pframe"></div><div class="pwm">MITODERM</div>
<div class="pshelf">${shelf(SEC[p.id].shelf, 236, 262)}</div><div class="pcolo"><bdi dir="ltr">${COLO}</bdi></div></div>
<div class="side"><div class="hdr"><p class="kicker">${L(f.title)}</p><h2 class="otitle">${TT(p.title)}</h2>${p.combo ? `<p class="combo">${L(p.combo)}</p>` : ''}${p.sub ? `<p class="osub">${L(p.sub)}</p>` : ''}<div class="hair"></div></div><div class="col"></div></div>
</section>
<div class="blocks">${blocks}</div>
</template>`;
  const cont = (id, title, blocks) => `<template data-kind="cont" data-sec="${id}" data-title="${esc(title)}" data-cont="${esc(title)}"><div class="blocks">${blocks}</div></template>`;

  const parts = [];
  // Cover
  parts.push(`<template data-kind="fixed"><section class="page cover"><div class="cglow"></div><div class="cframe"></div>
<img class="clogo" src="img/mitoderm-logo.webp" alt="MITODERM">
<div class="ctext">${C.hero.latin ? `<p class="ckick">${L(C.hero.latin)}</p>` : ''}<h1 class="ctitle1">${L(C.hero.title)}</h1><p class="csub">${L(C.hero.sub)}</p>
<ul class="cfams">${C.families.map(f => `<li><span class="fam">${L(f.title)}</span>${f.tile.links.map(([t]) => `<span class="prot">${L(t)}</span>`).join('')}</li>`).join('')}</ul></div>
<div class="cshelf">${shelf([['micro-boost-10', .86], ['vtech-system', .9], ['mitopen', 1], ['exo-nad', .5], ['exocell-mask', .64]], 384, 250, 10)}</div>
</section></template>`);
  for (const f of C.families) {
    for (const p of f.protocols) {
      if (p.layout === 'stages') { parts.push(opener(f, p, `<p class="b lead">${rich(p.lead)}</p>` + steps(p.steps) + p.after.map(section).join(''))); continue; }
      if (p.layout === 'mask') {
        parts.push(opener(f, p, head(p.use.title) + ul(p.use.steps) + p.blocks.map(section).join('')));
        parts.push(cont('home', L(p.home.title), p.home.cards.map(section).join('')));
        // Equal gaps between packshots; a caption may borrow half a gap on each side.
        const m = p.home.maintain, SH = 256, items = [['cell-renew-15', 1], ['cellular-age-25', 1], ['derma-recovery', .76], ['exotech-gel', .44]]
          .map(([k, f2]) => { const [w, h] = DIMS[k]; return [k, (SH * f2 * w) / h, SH * f2]; });
        const G = (686 - items.reduce((a, s2) => a + s2[1], 0)) / (items.length + 1);
        parts.push(`<template data-kind="fixed"><section class="page showcase" style="${vars('maintain')}"><div class="band"></div><div class="wm">MITODERM</div>
<h3 class="ctitle">${L(m.title)}</h3><div class="hair chair"></div><div class="sglow"></div>
<div class="srow" style="gap:${G.toFixed(1)}px">${items.map(([k, w, h]) => `<div class="sslot" style="width:${w.toFixed(1)}px"><div class="simg"><img src="img/${k}.webp" alt="" style="height:${h.toFixed(1)}px;width:${w.toFixed(1)}px"></div><span class="sname" style="width:${(w + G - 8).toFixed(1)}px">${L(NAMES[k])}</span></div>`).join('')}</div>
<div class="stext">${m.body.map(item).join('')}</div>
<div class="colo"><bdi dir="ltr">${COLO}</bdi></div></section></template>`);
        continue;
      }
      parts.push(opener(f, p, ORDER[p.id].map(k => (k === 'steps' ? steps(p.steps) : section(p[k.split(':')[0]][+k.split(':')[1]]))).join('')));
    }
  }
  parts.push(`<template data-kind="fixed"><section class="page back"><div class="cglow"></div><div class="cframe"></div><img class="blogo" src="img/mitoderm-logo.webp" alt="MITODERM"></section></template>`);

  return `<!doctype html>
<html lang="${C.lang}" dir="${C.dir}">
<head>
<meta charset="utf-8">
<title>${esc(C.title)}</title>
<style>
@font-face { font-family: Rubik; font-weight: 400; src: url(fonts/Rubik-400.ttf) format("truetype"); }
@font-face { font-family: Rubik; font-weight: 500; src: url(fonts/Rubik-500.ttf) format("truetype"); }
@font-face { font-family: Rubik; font-weight: 700; src: url(fonts/Rubik-700.ttf) format("truetype"); }
@page { size: 794px 561px; margin: 0; }
:root { --paper: #F8F3E8; --ink: #57524A; --gold: #9E661F; --card: #F1E8D7; --glow: #D4A853; --glow2: #E8C87E; --cream: #F8F3E8; --bronze: #241C12; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; }
body { font: 400 10px/15px Rubik, sans-serif; color: var(--ink); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
p, h1, h2, h3, h4, ul, figure { margin: 0; padding: 0; }
.page { position: relative; width: 794px; height: 561px; overflow: hidden; background: var(--paper); break-after: page; page-break-after: always; }
.pn { font-weight: 500; }
.hair { height: 1px; background: rgba(158, 102, 31, .35); }

/* Hero opener: section panel at the reading end, text column at the reading start */
.panel { position: absolute; top: 0; bottom: 0; inset-inline-end: 0; width: 300px; background: var(--sec); overflow: hidden; }
.pglow { position: absolute; left: 0; right: 0; top: 150px; height: 300px; background: radial-gradient(closest-side, rgba(212, 168, 83, .34), rgba(212, 168, 83, .12) 55%, rgba(212, 168, 83, 0)); }
.pframe { position: absolute; inset: 14px; border: 1px solid rgba(212, 168, 83, .45); }
.pwm { position: absolute; top: 26px; left: 0; right: 0; text-align: center; font: 700 12px/16px Rubik; letter-spacing: .08em; color: #fff; }
.pshelf { position: absolute; left: 32px; right: 32px; top: 74px; height: 262px; display: flex; align-items: flex-end; justify-content: center; gap: 14px; }
.pcolo { position: absolute; top: 527px; left: 0; right: 0; text-align: center; font: 400 10px/15px Rubik; color: #fff; }
.side { position: absolute; top: 24px; bottom: 41px; inset-inline-start: 54px; width: 400px; display: flex; flex-direction: column; }
.kicker { font: 500 10px/14px Rubik; letter-spacing: .1em; color: var(--acc); margin-bottom: 8px; }
.otitle { font: 700 30px/34px Rubik; color: var(--ink); text-wrap: balance; }
.combo { font: 500 14px/18px Rubik; letter-spacing: .04em; color: var(--acc); margin-top: 6px; }
.osub { font: 400 14px/18px Rubik; color: var(--ink); margin-top: 4px; }
.hdr .hair { margin-top: 12px; }
.side .col { position: relative; flex: 1; margin-top: 12px; overflow: hidden; }

/* Continuation page: band, wordmark and colophon on the outer edge; two columns, reading-first at the start */
.band { position: absolute; top: 0; bottom: 0; width: 18px; background: var(--sec); }
.wm { position: absolute; top: 24px; font: 700 11px/15px Rubik; color: var(--gold); }
.colo { position: absolute; top: 535px; font: 400 10px/15px Rubik; color: var(--ink); white-space: nowrap; }
.outer-left .band { left: 0; } .outer-right .band { right: 0; }
.outer-left .wm, .outer-left .colo { left: 54px; } .outer-right .wm, .outer-right .colo { right: 54px; }
.ctitle { position: absolute; top: 40px; inset-inline-start: 54px; width: 560px; font: 700 20px/24px Rubik; color: var(--ink); }
.chair { position: absolute; top: 74px; inset-inline-start: 54px; width: 686px; }
.cont .col { position: absolute; top: 90px; height: 430px; overflow: hidden; }
.cont .colA { inset-inline-start: 54px; width: 336px; }
.cont .colB { inset-inline-end: 54px; width: 336px; }

/* Text blocks */
.col > :first-child { margin-top: 0 !important; }
.h { font: 500 14px/18px Rubik; color: var(--acc); margin: 16px 0 4px; }
.p { margin: 0 0 6px; }
.lead { font-weight: 500; margin: 0 0 6px; }
.ul { list-style: none; margin: 0 0 6px; }
.ul li { position: relative; padding-inline-start: 12px; margin-bottom: 3px; }
.ul li::before { content: ""; position: absolute; inset-inline-start: 1px; top: 6px; width: 4px; height: 4px; border-radius: 50%; background: var(--acc); }
.note { position: relative; margin: 8px 0; padding-block: 7px; padding-inline: 16px 10px; background: var(--card); border-radius: 6px; font-weight: 500; }
.note::before { content: ""; position: absolute; inset-inline-start: 6px; top: 7px; bottom: 7px; width: 3px; border-radius: 2px; background: var(--gold); }
.pipes .sep { color: rgba(158, 102, 31, .55); }
.opt { margin: 6px 0; padding: 7px 10px; background: var(--card); border-radius: 6px; }
.opt-l { display: block; font-weight: 500; color: var(--acc); margin-bottom: 2px; }
.fig { margin: 4px 0 8px; text-align: center; }
.fig img { height: 96px; width: auto; }
.fig figcaption { font: 500 10px/14px Rubik; letter-spacing: .08em; color: var(--acc); }

/* Cover and back */
.cover, .back { background: var(--bronze); }
.cglow { position: absolute; left: 0; right: 0; bottom: -60px; height: 380px; background: radial-gradient(60% 55% at 62% 70%, rgba(212,168,83,.32), rgba(212,168,83,.1) 55%, rgba(212,168,83,0)); }
[dir="rtl"] .cglow { background: radial-gradient(60% 55% at 38% 70%, rgba(212,168,83,.32), rgba(212,168,83,.1) 55%, rgba(212,168,83,0)); }
.cframe { position: absolute; inset: 16px; border: 1px solid rgba(212, 168, 83, .5); }
.clogo { position: absolute; top: 46px; inset-inline-start: 54px; width: 190px; filter: brightness(0) invert(1); }
.ctext { position: absolute; top: 132px; inset-inline-start: 54px; width: 330px; color: var(--cream); }
.ckick { font: 500 10px/14px Rubik; letter-spacing: .16em; color: var(--glow); margin-bottom: 10px; }
.ctitle1 { font: 700 30px/34px Rubik; color: var(--cream); text-wrap: balance; }
.csub { font: 400 14px/18px Rubik; color: rgba(248, 243, 232, .85); margin-top: 10px; }
.cfams { list-style: none; width: 300px; margin-top: 24px; border-top: 1px solid rgba(212, 168, 83, .5); }
.cfams li { padding: 7px 0 8px; border-bottom: 1px solid rgba(212, 168, 83, .25); }
.cfams .fam { display: block; font: 500 10px/14px Rubik; letter-spacing: .1em; color: var(--glow); margin-bottom: 2px; }
.cfams .prot { display: block; font: 400 10px/14px Rubik; color: rgba(248, 243, 232, .85); }
.cshelf { position: absolute; bottom: 76px; inset-inline-end: 40px; width: 384px; height: 250px; display: flex; align-items: flex-end; justify-content: center; gap: 10px; }
.blogo { position: absolute; left: 50%; top: 50%; width: 300px; transform: translate(-50%, -50%); filter: brightness(0) invert(1); }

/* Showcase: home maintenance products standing on one line, captions under them, text below */
.sglow { position: absolute; left: 140px; right: 140px; top: 216px; height: 200px; background: radial-gradient(closest-side, rgba(212, 168, 83, .24), rgba(212, 168, 83, 0)); }
.srow { position: absolute; top: 98px; left: 54px; right: 54px; display: flex; justify-content: center; align-items: flex-start; }
.sslot { display: flex; flex-direction: column; align-items: center; }
.simg { height: 256px; display: flex; align-items: flex-end; }
.sname { margin-top: 12px; flex: none; font: 500 10px/14px Rubik; letter-spacing: .04em; color: var(--acc); text-align: center; text-wrap: balance; }
.stext { position: absolute; top: 428px; inset-inline-start: 54px; width: 686px; columns: 2; column-gap: 14px; }

/* Packshots closing a protocol in the column its text leaves empty */
.cfill { position: absolute; left: 0; right: 0; bottom: 0; }
.fglow { position: absolute; left: 0; right: 0; bottom: 0; height: 70%; background: radial-gradient(closest-side, rgba(212, 168, 83, .2), rgba(212, 168, 83, 0)); }
.fshelf { position: absolute; left: 0; right: 0; bottom: 22px; display: flex; align-items: flex-end; justify-content: center; gap: 14px; }
.stext .ul li { break-inside: avoid; }
</style>
</head>
<body>
<div id="book"></div>
<template id="tpl-cont"><section class="page cont"><div class="band"></div><div class="wm">MITODERM</div><h3 class="ctitle"></h3><div class="hair chair"></div><div class="col colA"></div><div class="col colB"></div><div class="colo"><bdi dir="ltr">${COLO}</bdi></div></section></template>
<div id="src">
${parts.join('\n')}
</div>
<script>
(async () => {
  await Promise.all(['400', '500', '700'].map(w => document.fonts.load(w + ' 10px Rubik', 'Aא Б')));
  await document.fonts.ready;
  const SECV = ${JSON.stringify(Object.fromEntries(Object.entries(SEC).map(([k, v]) => [k, { sec: v.sec, acc: v.acc, fill: v.fill }])))};
  const DIM = ${JSON.stringify(DIMS)};
  const book = document.getElementById('book');
  const report = { overflow: [], moved: 0, fills: [], balanced: 0 };
  const fits = col => col.scrollHeight <= col.clientHeight + 0.5;
  let cols = [], ci = 0;
  function newCont(title, sec) {
    const pg = document.getElementById('tpl-cont').content.firstElementChild.cloneNode(true);
    pg.style.setProperty('--sec', SECV[sec].sec); pg.style.setProperty('--acc', SECV[sec].acc);
    pg.querySelector('.ctitle').innerHTML = title;
    book.appendChild(pg); cols = [...pg.querySelectorAll('.col')]; ci = 0;
  }
  function nextCol(part) { ci++; if (ci >= cols.length) newCont(part.title, part.sec); }
  function place(block, part) {
    const col = cols[ci]; col.appendChild(block);
    if (fits(col)) return;
    if (block.matches('ul') && block.children.length >= 4) {
      const rest = block.cloneNode(false);
      while (block.children.length > 2 && (!fits(col) || rest.children.length < 2)) rest.insertBefore(block.lastElementChild, rest.firstChild);
      if (fits(col)) { nextCol(part); place(rest, part); return; }
      while (rest.firstChild) block.appendChild(rest.firstChild);
    }
    col.removeChild(block);
    const keep = [];
    while (col.lastElementChild && col.lastElementChild.classList.contains('kwn')) keep.unshift(col.removeChild(col.lastElementChild));
    nextCol(part); report.moved++;
    for (const k of keep) cols[ci].appendChild(k);
    cols[ci].appendChild(block);
    if (!fits(cols[ci])) report.overflow.push(block.textContent.slice(0, 60));
  }
  function balance() {
    const pg = cols[0].closest('.page');
    if (!pg.classList.contains('cont')) return;
    const [a, b] = cols, end = c => (c.lastElementChild ? c.lastElementChild.offsetTop + c.lastElementChild.offsetHeight : 0);
    for (;;) {
      const gap = Math.abs(end(a) - end(b)), moved = [];
      let k = a.lastElementChild;
      while (k && k.previousElementSibling && !k.classList.contains('kwn')) k = k.previousElementSibling;
      while (k && k.previousElementSibling && k.previousElementSibling.classList.contains('kwn')) k = k.previousElementSibling;
      if (!k || k === a.firstElementChild) return;
      while (a.lastElementChild && moved[0] !== k) moved.unshift(a.lastElementChild), a.removeChild(a.lastElementChild);
      b.prepend(...moved);
      if (fits(b) && Math.abs(end(a) - end(b)) < gap) { report.balanced++; continue; }
      for (const m of moved) b.removeChild(m);
      a.append(...moved); return;
    }
  }
  function fill(part) {
    const items = SECV[part.sec].fill, pg = cols[0].closest('.page');
    if (!items || !pg.classList.contains('cont')) return;
    const colB = pg.querySelector('.colB'), last = colB.lastElementChild;
    const zone = colB.clientHeight - (last ? last.offsetTop + last.offsetHeight + 24 : 0);
    if (zone < 180) return;
    const H = Math.min(zone - 50, 250), maxW = colB.clientWidth - 40;
    const sz = items.map(([k, f]) => [k, (H * f * DIM[k][0]) / DIM[k][1], H * f]);
    const sc = Math.min(1, (maxW - 14 * (sz.length - 1)) / sz.reduce((a, s) => a + s[1], 0));
    const d = document.createElement('div'); d.className = 'cfill'; d.style.height = zone + 'px';
    d.innerHTML = '<div class="fglow"></div><div class="fshelf">' + sz.map(([k, w, h]) => '<img src="img/' + k + '.webp" alt="" style="width:' + (w * sc).toFixed(1) + 'px;height:' + (h * sc).toFixed(1) + 'px">').join('') + '</div>';
    colB.appendChild(d); report.fills.push(part.sec);
  }
  for (const tpl of document.querySelectorAll('#src > template')) {
    const frag = tpl.content.cloneNode(true);
    if (tpl.dataset.kind === 'fixed') { book.appendChild(frag); continue; }
    const part = { sec: tpl.dataset.sec, title: tpl.dataset.cont };
    const holder = frag.querySelector('.blocks'); const blocks = [...holder.children]; holder.remove();
    if (tpl.dataset.kind === 'opener') { const pg = frag.querySelector('.page'); book.appendChild(pg); cols = [pg.querySelector('.col')]; ci = 0; }
    else newCont(tpl.dataset.title, part.sec);
    for (const b of blocks) place(b, part);
    if (SECV[part.sec].fill) fill(part); else balance();
  }
  document.getElementById('src').remove();
  const rtl = document.documentElement.dir === 'rtl';
  const pages = [...book.children];
  pages.forEach((p, i) => { const odd = i % 2 === 0; p.classList.add((rtl ? !odd : odd) ? 'outer-right' : 'outer-left'); });
  await document.fonts.ready;
  pages.forEach((pg, i) => pg.querySelectorAll('.col').forEach(c => {
    const bottom = c.getBoundingClientRect().bottom;
    for (const e of c.querySelectorAll('*')) if (!e.closest('.cfill') && e.getBoundingClientRect().bottom > bottom + 0.5) { report.overflow.push('page ' + (i + 1) + ': ' + e.textContent.slice(0, 40)); break; }
  }));
  report.pages = pages.length;
  report.emptyCols = [...document.querySelectorAll('.cont .col')].filter(c => !c.children.length).length;
  report.kinds = pages.map(p => p.className.replace('page ', '').split(' ')[0]).join(',');
  window.__report = report;
})();
</script>
</body>
</html>`;
}

const langs = process.argv.slice(2).length ? process.argv.slice(2) : ['he', 'ru', 'en'];
const pdfs = [];
const browser = await chromium.launch({ executablePath: CHROME });
for (const lang of langs) {
  const C = (await import(`../src/content.${lang}.mjs`)).default;
  const file = join(here, `protocols-print.${lang}.html`);
  writeFileSync(file, html(C));
  const page = await browser.newPage({ viewport: { width: 900, height: 700 }, deviceScaleFactor: 2 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(pathToFileURL(file).href);
  await page.waitForFunction(() => window.__report, null, { timeout: 30000 });
  const report = await page.evaluate(() => window.__report);
  if (QA) {
    mkdirSync(QA, { recursive: true });
    const pages = await page.$$('.page');
    for (let i = 0; i < pages.length; i++) await pages[i].screenshot({ path: join(QA, `${lang}-${String(i + 1).padStart(2, '0')}.png`) });
  }
  const pdf = join(here, `MITODERM-Protocols-${lang.toUpperCase()}.pdf`);
  await page.pdf({ path: pdf, printBackground: true, preferCSSPageSize: true });
  pdfs.push(pdf);
  console.log(lang, JSON.stringify({ ...report, errors }));
  await page.close();
}
await browser.close();
execFileSync('python3', [join(here, 'press.py'), ...pdfs], { stdio: 'inherit' });
