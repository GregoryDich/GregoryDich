// Builds MITODERM-video-scenarios-HE-v3.docx from the v3 scenario markdown files (state/scenarios-v3/src).
// Usage: NODE_PATH=$(npm root -g) node build-docx.cjs <out.docx> [--src dir] [--mark] [--pages pages.json]
//   --src    source dir (default: ../src next to this file)
//   --mark   adds QQMARKpgNN to every part page and Heading 1 (first pass, to find start pages in the PDF)
//   --pages  JSON {"pg01": 3, ...} with the start page of every TOC entry (second pass prints TOC numbers)
// Writes <out.docx>.manifest.json: TOC entries in order [{bm, slug|null, title, part}] for verify.py.
// A missing source file is skipped with a console note; a part with no files is left out.
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, BorderStyle, Header, Footer, PageNumber, TabStopType, LevelFormat,
  TableOfContents, Bookmark, InternalHyperlink, Tab, TableLayoutType, PageOrientation,
} = require('docx');

const args = process.argv.slice(2);
const OUT = args[0];
const MARK = args.includes('--mark');
const pagesArg = args.indexOf('--pages');
const PAGES = pagesArg >= 0 ? JSON.parse(fs.readFileSync(args[pagesArg + 1], 'utf8')) : {};
const srcArg = args.indexOf('--src');
const SRC = srcArg >= 0 ? path.resolve(args[srcArg + 1]) : path.join(__dirname, '..', 'src');

// print order; format-v3.md is internal and never printed
const PARTS = [
  { title: 'הקונספט וההפקה', slugs: ['00-concept', '01-home', '02-production'] },
  { title: '13 פרקי מוצר', slugs: ['exo-nad', 'v-tech-system', 'exotech-gel', 'exocell-mask', 'exosignal-hair',
    'exosignal-spray', 'micro-boost-10', 'cellular-age-defense-2-5', 'cell-renew-1-5', 'derma-recovery-cream',
    'mitopen', 'mitoscan', 'mitotech-cell-booster'] },
  { title: 'נספחים', slugs: ['95-materials', '97-rules', '98-costs', '99-roadmap'] },
];

// ---------- page geometry (DXA) ----------
const PAGE_W = 11906, PAGE_H = 16838, MARGIN_LR = 1000;
const TEXT_W = PAGE_W - 2 * MARGIN_LR; // 9906
const TEXT_W_LAND = PAGE_H - 2 * MARGIN_LR; // 14838 (landscape sections for wide tables)
const WIDE_COLS = 8; // a ## section holding a table with this many columns or more is set in landscape
const FONT = { ascii: 'Arial', hAnsi: 'Arial', cs: 'Arial', eastAsia: 'Arial' };
const C = { gold: 'C9A24B', goldDark: '8A6A1F', ink: '1A1A1A', grey: '808080', code: '2F4F4F',
  head: 'E9E2CC', border: 'BFB8A5', box: 'F3F1EA', boxBorder: 'D6CFBC', sub: '6B6B6B' };
const SZ = { body: 20, table: 17, tagBody: 16, tagTable: 14, box: 18, tableWide: 15, tagWide: 13 };

// ---------- markdown parsing ----------
const indentOf = (l) => l.length - l.trimStart().length;
const isMarker = (l) => indentOf(l) === 0 && /^([-*]|\d+\.)\s+/.test(l);
const isFence = (l) => l.trimStart().startsWith('```');
const isHeading = (l) => indentOf(l) === 0 && /^#{1,6}\s/.test(l);
const isTable = (l) => indentOf(l) === 0 && l.startsWith('|');

function joinLines(lines) {
  return lines.reduce((acc, ln) => {
    if (!acc) return ln;
    if (/\p{L}-$/u.test(acc)) return acc + ln; // Hebrew prefix hyphen / word broken at "-"
    return acc + ' ' + ln;
  }, '');
}

function parseMd(src) {
  const L = src.replace(/\r/g, '').split('\n');
  const blocks = [];
  let i = 0;
  while (i < L.length) {
    const l = L[i];
    if (!l.trim()) { i++; continue; }
    if (isHeading(l)) {
      const m = l.match(/^(#+)\s+(.*)$/);
      blocks.push({ type: 'h', level: m[1].length, text: m[2].trim() });
      i++; continue;
    }
    if (isFence(l)) {
      const lines = []; i++;
      while (i < L.length && !isFence(L[i])) { lines.push(L[i].trim()); i++; }
      i++; blocks.push({ type: 'code', lines }); continue;
    }
    if (isTable(l)) {
      const rows = [];
      while (i < L.length && isTable(L[i])) { rows.push(L[i]); i++; }
      // split on unescaped pipes; "\|" inside a cell prints as "|"
      const cells = (r) => r.trim().replace(/^\|/, '').replace(/\|$/, '').split(/(?<!\\)\|/).map((c) => c.trim().replace(/\\\|/g, '|'));
      blocks.push({ type: 'table', header: cells(rows[0]), rows: rows.slice(2).map(cells) });
      continue;
    }
    if (isMarker(l)) {
      const m = l.match(/^([-*]|(\d+)\.)\s+(.*)$/);
      const item = { type: 'li', ordered: !!m[2], num: m[2] ? +m[2] : null, parts: [] };
      let cur = [m[3].trim()]; i++;
      const flush = () => { if (cur.length) { item.parts.push({ t: 'text', s: joinLines(cur) }); cur = []; } };
      while (i < L.length) {
        const x = L[i];
        if (!x.trim()) {
          let j = i + 1; while (j < L.length && !L[j].trim()) j++;
          if (j < L.length && indentOf(L[j]) > 0) { flush(); i = j; continue; }
          break;
        }
        if (indentOf(x) === 0 && (isMarker(x) || isHeading(x) || isTable(x) || isFence(x))) break;
        if (isFence(x)) {
          flush(); const lines = []; i++;
          while (i < L.length && !isFence(L[i])) { lines.push(L[i].trim()); i++; }
          i++; item.parts.push({ t: 'code', lines }); continue;
        }
        cur.push(x.trim()); i++;
      }
      flush(); blocks.push(item); continue;
    }
    const cur = [l.trim()]; i++;
    while (i < L.length && L[i].trim() && !isMarker(L[i]) && !isHeading(L[i]) && !isTable(L[i]) && !isFence(L[i])) {
      cur.push(L[i].trim()); i++;
    }
    blocks.push({ type: 'p', text: joinLines(cur) });
  }
  return blocks;
}

// code block -> paragraphs (hard-wrapped lines joined; "Negative:" starts a new paragraph)
function codeParagraphs(lines) {
  const groups = [];
  for (const ln of lines) {
    if (!ln) continue;
    if (!groups.length || /^Negative:/.test(ln)) groups.push([ln]); else groups[groups.length - 1].push(ln);
  }
  return groups.map(joinLines);
}

// ---------- inline parsing ----------
function inlineSegs(s) {
  const segs = []; let buf = '', code = false, bold = false, tag = 0;
  const push = () => { if (buf) { segs.push({ text: buf, code, bold, tag: tag > 0 }); buf = ''; } };
  for (let k = 0; k < s.length; k++) {
    const c = s[k];
    if (c === '`') { push(); code = !code; continue; }
    if (code) { buf += c; continue; }
    if (c === '*' && s[k + 1] === '*') { push(); bold = !bold; k++; continue; }
    if (c === '[') { if (tag === 0) push(); tag++; buf += c; continue; }
    if (c === ']' && tag > 0) {
      buf += c; tag--;
      if (tag === 0) { segs.push({ text: buf, code: false, bold, tag: true }); buf = ''; }
      continue;
    }
    buf += c;
  }
  push();
  // Latin code spans (paths, hex, ids) are wrapped in LRI…PDI (U+2066/U+2069) so they read left to right inside the
  // RTL line. v2.1 used separate LRM runs; LibreOffice then broke words like «#0a0a0b» at the line end.
  // (a code span with Hebrew in it is left to the normal bidi resolution)
  const out = [];
  for (const sg of segs) {
    if (sg.code && HEB.test(sg.text)) sg.code = 'he';
    // a zero-width space after each "/" gives LibreOffice a break point in long paths (else it cuts mid-name)
    if (sg.code === true) out.push({ ...sg, text: '\u2066' + sg.text.replace(/\/(?=.)/g, '/\u200B') + '\u2069' });
    else out.push(sg);
  }
  return out;
}

const HEB = /[\u0590-\u05FF\uFB1D-\uFB4F]/;

// mini Unicode bidi resolution (paragraph level RTL) -> per char 'L' | 'R'
function resolveDirs(chars, forced) {
  const cls = chars.map((ch, i) => {
    if (forced[i]) return 'L';
    if (/[֐-׿יִ-ﭏ‏]/.test(ch)) return 'R';
    if (ch === '‎' || /\p{L}/u.test(ch)) return 'L';
    if (/[0-9]/.test(ch)) return 'EN';
    if (/[+\-]/.test(ch)) return 'ES';
    if (/[#$%°±‰′″℮€£¥¢]/.test(ch)) return 'ET';
    if (/[.,:\/ ]/.test(ch)) return 'CS';
    return 'N';
  });
  const n = cls.length;
  for (let i = 1; i < n - 1; i++) { // W4
    if (cls[i - 1] === 'EN' && cls[i + 1] === 'EN' && (cls[i] === 'ES' || cls[i] === 'CS')) cls[i] = 'EN';
  }
  for (let i = 0; i < n; i++) { // W5
    if (cls[i] !== 'ET') continue;
    let j = i; while (j < n && cls[j] === 'ET') j++;
    if ((i > 0 && cls[i - 1] === 'EN') || (j < n && cls[j] === 'EN')) for (let k = i; k < j; k++) cls[k] = 'EN';
    i = j - 1;
  }
  for (let i = 0; i < n; i++) if (cls[i] === 'ES' || cls[i] === 'ET' || cls[i] === 'CS') cls[i] = 'N'; // W6
  let lastStrong = 'R'; // W7, sos = R
  for (let i = 0; i < n; i++) {
    if (cls[i] === 'L' || cls[i] === 'R') lastStrong = cls[i];
    else if (cls[i] === 'EN' && lastStrong === 'L') cls[i] = 'L';
  }
  const res = cls.slice();
  for (let i = 0; i < n; i++) { // N1/N2
    if (cls[i] !== 'N') continue;
    let j = i; while (j < n && cls[j] === 'N') j++;
    const prev = i > 0 ? (cls[i - 1] === 'L' ? 'L' : 'R') : 'R';
    const next = j < n ? (cls[j] === 'L' ? 'L' : 'R') : 'R';
    const d = prev === next ? prev : 'R';
    for (let k = i; k < j; k++) res[k] = d;
    i = j - 1;
  }
  return res.map((c) => (c === 'L' ? 'L' : 'R'));
}

// text with inline markdown -> TextRuns for an RTL paragraph
function rtlRuns(s, ctx = {}) {
  const segs = inlineSegs(s);
  const chars = [], forced = [], owner = [];
  segs.forEach((sg, si) => {
    for (const ch of sg.text) { chars.push(ch); forced.push(sg.code === true || !!sg.lrm); owner.push(si); }
  });
  const dirs = resolveDirs(chars, forced);
  const runs = [];
  let k = 0;
  segs.forEach((sg, si) => {
    const arr = [...sg.text];
    let start = 0;
    while (start < arr.length) {
      const d = dirs[k + start];
      let end = start; while (end < arr.length && dirs[k + end] === d) end++;
      const text = arr.slice(start, end).join('');
      const size = sg.tag ? (ctx.wide ? SZ.tagWide : ctx.table ? SZ.tagTable : SZ.tagBody)
        : (ctx.size || (ctx.wide ? SZ.tableWide : ctx.table ? SZ.table : SZ.body));
      const color = sg.tag ? C.grey : (sg.code ? C.code : (ctx.color || undefined));
      runs.push(new TextRun({
        text, bold: !!(sg.bold || ctx.bold), size, color, font: FONT,
        ...(d === 'R' ? { rightToLeft: true } : {}),
      }));
      start = end;
    }
    k += arr.length;
  });
  return runs;
}

const rtlPara = (s, opts = {}, ctx = {}) => new Paragraph({ bidirectional: true, children: rtlRuns(s, ctx), ...opts });

// split a text at long inline code spans (English prompts / commands) -> [{t:'text'|'box', s}]
function splitLongCode(s) {
  const out = []; let last = 0;
  const re = /`([^`]+)`/g; let m;
  while ((m = re.exec(s))) {
    if (m[1].length >= 70 && /\s/.test(m[1])) {
      out.push({ t: 'text', s: s.slice(last, m.index) });
      out.push({ t: 'box', s: m[1].trim() });
      last = re.lastIndex;
    }
  }
  out.push({ t: 'text', s: s.slice(last) });
  return out.map((p, i) => {
    if (p.t !== 'text') return p;
    let t = p.s.trim();
    if (i > 0) t = t.replace(/^[;,.]\s*/, '');
    return { t: 'text', s: t };
  }).filter((p) => p.t === 'box' || /[\p{L}\p{N}]/u.test(p.s));
}

// ---------- building blocks ----------
const boxBorder = { style: BorderStyle.SINGLE, size: 4, color: C.boxBorder, space: 4 };
function boxParas(texts, indentRight = 0) {
  return texts.map((t, i) => new Paragraph({
    bidirectional: false,
    alignment: AlignmentType.LEFT,
    shading: { type: ShadingType.CLEAR, color: 'auto', fill: C.box },
    border: { top: boxBorder, bottom: boxBorder, left: boxBorder, right: boxBorder },
    indent: { left: 80, right: indentRight + 80 },
    spacing: { before: i === 0 ? 60 : 0, after: i === texts.length - 1 ? 140 : 60, line: 264 },
    keepLines: false,
    children: [new TextRun({ text: t, size: SZ.box, font: FONT, color: '222222' })],
  }));
}

const tBorder = { style: BorderStyle.SINGLE, size: 4, color: C.border };
const tBorders = { top: tBorder, bottom: tBorder, left: tBorder, right: tBorder };
function makeTable(header, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (txt, w, isHead) => new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: tBorders,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    shading: isHead ? { type: ShadingType.CLEAR, color: 'auto', fill: C.head } : undefined,
    // keepNext on the header row: LibreOffice drops the body rows when a repeated header lands alone at a page foot
    children: [new Paragraph({ bidirectional: true, spacing: { after: 0, line: 252 }, keepNext: isHead,
      children: rtlRuns(txt, { table: true, wide: !!opts.wide, bold: isHead }) })],
  });
  const trs = [new TableRow({ tableHeader: true, cantSplit: true, children: header.map((h, i) => cell(h, widths[i], true)) })];
  for (const r of rows) {
    trs.push(new TableRow({ cantSplit: !!opts.cantSplit, children: widths.map((w, i) => cell(r[i] || '', w, false)) }));
  }
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    visuallyRightToLeft: true, rows: trs,
  });
}

// column widths from the content: a floor that fits the longest unbreakable token, the rest by text length^0.65
function tableWidths(header, rows, total, size) {
  const n = header.length;
  const plain = (t) => (t || '').replace(/\*\*|`/g, '');
  const charW = size * 6; // DXA per Latin char, Arial, generous
  const floor = [], weight = [];
  for (let i = 0; i < n; i++) {
    const col = [header[i], ...rows.map((r) => r[i])].map(plain);
    // LibreOffice breaks at spaces, after "-" and after the zero-width space put after "/" in code spans
    const longest = Math.max(...col.map((t) => Math.max(0, ...t.split(/[\s\/]+|(?<=-)/).map((w) => w.length))));
    floor.push(Math.min(Math.max(longest * charW + 220, 650), total / 3));
    const mean = rows.length ? rows.reduce((a, r) => a + plain(r[i]).length, 0) / rows.length : plain(header[i]).length;
    weight.push(Math.pow(Math.max(mean, plain(header[i]).length, 4), 0.65));
  }
  let w = floor.slice();
  let rest = total - w.reduce((a, b) => a + b, 0);
  if (rest < 0) { const k = total / (total - rest); w = w.map((x) => x * k); rest = 0; }
  const ws = weight.reduce((a, b) => a + b, 0);
  w = w.map((x, i) => Math.floor(x + rest * weight[i] / ws));
  w[n - 1] += total - w.reduce((a, b) => a + b, 0);
  return w;
}

// ---------- document ----------
// sections: [{land, children}] — a new section only where the orientation changes
const sections = [{ land: false, children: [] }];
let children = sections[0].children;
const setLand = (land) => {
  if (sections[sections.length - 1].land === land) return;
  sections.push({ land, children: [] }); children = sections[sections.length - 1].children;
};
const tocEntries = []; // {bm, slug, title, part}
const included = [], missing = [];
let listInstance = 0, bmCount = 0;
const nextBm = () => 'pg' + String(++bmCount).padStart(2, '0');
const markRun = (bm) => new TextRun({ text: ' QQMARK' + bm, size: 16 });

// which ## sections hold a wide table -> landscape
function wideSections(blocks) {
  const wide = new Set();
  let h2 = -1;
  blocks.forEach((b, bi) => {
    if (b.type === 'h' && b.level <= 2) h2 = b.level === 2 ? bi : -1;
    if (b.type === 'table' && b.header.length >= WIDE_COLS && h2 >= 0) wide.add(h2);
  });
  return wide;
}

function addPartPage(part, pn) {
  setLand(false);
  const bm = nextBm();
  tocEntries.push({ bm, slug: null, title: `חלק ${pn} · ${part.title}`, part: pn });
  const runs = rtlRuns(part.title, { size: 56, bold: true, color: C.ink });
  if (MARK) runs.push(markRun(bm));
  children.push(new Paragraph({ pageBreakBefore: true, spacing: { before: 4200, after: 200 }, alignment: AlignmentType.CENTER,
    bidirectional: true, children: rtlRuns(`חלק ${pn}`, { size: 28, color: C.goldDark }) }));
  children.push(new Paragraph({ alignment: AlignmentType.CENTER, bidirectional: true, border: goldRule, spacing: { after: 400 },
    children: [new Bookmark({ id: bm, children: runs })] }));
  return bm;
}

function addChapter(slug, partNo) {
  const file = path.join(SRC, slug + '.md');
  const blocks = parseMd(fs.readFileSync(file, 'utf8'));
  const wide = wideSections(blocks);
  let prevList = null; // {ordered}
  blocks.forEach((b, bi) => {
    if (b.type !== 'li') prevList = null;
    if (b.type === 'h' && b.level <= 2) setLand(b.level === 2 && wide.has(bi));
    if (b.type === 'h' && b.level === 1) {
      const bm = nextBm();
      let title = b.text, sub = '';
      const parts = b.text.split(' — ');
      if (parts.length > 1) { title = parts[0]; sub = parts.slice(1).join(' — '); }
      tocEntries.push({ bm, slug, title, part: partNo });
      const runs = rtlRuns(title, { size: 44, bold: true, color: C.ink });
      if (MARK) runs.push(markRun(bm));
      children.push(new Paragraph({
        heading: HeadingLevel.HEADING_1, bidirectional: true, pageBreakBefore: true,
        children: [new Bookmark({ id: bm, children: runs })],
      }));
      if (sub) children.push(rtlPara(sub, { spacing: { after: 240 } }, { size: 24, color: C.sub }));
      return;
    }
    if (b.type === 'h') {
      const lvl = b.level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3;
      const size = b.level === 2 ? 28 : 23;
      children.push(new Paragraph({ heading: lvl, bidirectional: true,
        children: rtlRuns(b.text, { size, bold: true, color: b.level === 2 ? C.goldDark : C.ink }) }));
      return;
    }
    if (b.type === 'p') {
      for (const p of splitLongCode(b.text)) {
        if (p.t === 'box') children.push(...boxParas([p.s]));
        else children.push(rtlPara(p.s, { spacing: { after: 120 } }));
      }
      return;
    }
    if (b.type === 'code') { children.push(...boxParas(codeParagraphs(b.lines))); return; }
    if (b.type === 'table') {
      const land = sections[sections.length - 1].land;
      const isWide = b.header.length >= WIDE_COLS;
      const total = land ? TEXT_W_LAND : TEXT_W;
      const size = isWide ? SZ.tableWide : SZ.table;
      children.push(makeTable(b.header, b.rows, tableWidths(b.header, b.rows, total, size), { cantSplit: true, wide: isWide }));
      children.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
      return;
    }
    if (b.type === 'li') {
      if (!prevList || prevList.ordered !== b.ordered) { listInstance++; prevList = { ordered: b.ordered, inst: listInstance }; }
      const numbering = { reference: b.ordered ? 'num' : 'bul', level: 0, instance: prevList.inst };
      let first = true;
      for (const part of b.parts) {
        if (part.t === 'code') { children.push(...boxParas(codeParagraphs(part.lines), 360)); continue; }
        for (const p of splitLongCode(part.s)) {
          if (p.t === 'box') { children.push(...boxParas([p.s], 360)); continue; }
          const keepNext = b.parts.length > 1 || /`[^`]{70,}`/.test(part.s);
          if (first) children.push(rtlPara(p.s, { numbering, spacing: { after: 80 }, keepNext }));
          else children.push(rtlPara(p.s, { indent: { left: 360 }, spacing: { after: 80 }, keepNext }));
          first = false;
        }
      }
      return;
    }
  });
  setLand(false);
}

const goldRule = { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.gold, space: 8 } };
PARTS.forEach((part, pi) => {
  const present = part.slugs.filter((slug) => {
    const ok = fs.existsSync(path.join(SRC, slug + '.md'));
    if (!ok) { missing.push(slug); console.error(`note: ${slug}.md not found in ${SRC} — skipped`); }
    return ok;
  });
  if (!present.length) { console.error(`note: part ${pi + 1} «${part.title}» has no files — left out`); return; }
  addPartPage(part, pi + 1);
  for (const slug of present) { included.push(slug); addChapter(slug, pi + 1); }
});

// ---------- title page + TOC ----------
const COVER_TITLE = 'תסריטי וידאו לדפי MITODERM — מהיכרות לאהבה';
const COVER_SUB = 'גרסה 3.0 · 07/11/2026 · סרט בקליניקה · סולם המודעות · טופס מהבלוק הראשון';
const titlePage = [
  new Paragraph({ spacing: { before: 3600 }, children: [] }),
  new Paragraph({ alignment: AlignmentType.CENTER, bidirectional: true, border: goldRule, spacing: { after: 480 },
    children: rtlRuns(COVER_TITLE, { size: 52, bold: true, color: C.ink }) }),
  new Paragraph({ alignment: AlignmentType.CENTER, bidirectional: true,
    children: rtlRuns(COVER_SUB, { size: 24, color: C.sub }) }),
];

const tocParas = tocEntries.map((e) => new Paragraph({
  bidirectional: true,
  tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W, leader: 'dot' }],
  spacing: { before: e.slug ? 0 : 200, after: e.slug ? 70 : 100 },
  indent: e.slug ? { left: 0, right: 360 } : undefined,
  keepNext: !e.slug,
  children: [
    new InternalHyperlink({ anchor: e.bm, children: rtlRuns(e.title, { size: e.slug ? 21 : 23, bold: !e.slug, color: e.slug ? undefined : C.goldDark }) }),
    new TextRun({ children: [new Tab(), String(PAGES[e.bm] || '00')], size: e.slug ? 21 : 23, bold: !e.slug, font: FONT, rightToLeft: true }),
  ],
}));
const tocBlock = [
  new Paragraph({ pageBreakBefore: true, bidirectional: true, spacing: { after: 240 },
    children: rtlRuns('תוכן העניינים', { size: 36, bold: true, color: C.ink }) }),
  new TableOfContents('תוכן העניינים', { hyperlink: true, headingStyleRange: '1-1', contentChildren: tocParas }),
];
sections[0].children.unshift(...titlePage, ...tocBlock);

const headerP = () => new Paragraph({ bidirectional: true, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.border, space: 4 } },
  children: rtlRuns('MITODERM | תסריטי וידאו · גרסה 3.0', { size: 16, color: C.sub }) });
const footerP = () => new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: ['עמוד ', PageNumber.CURRENT, ' מתוך ', PageNumber.TOTAL_PAGES], size: 16, color: C.sub, font: FONT, rightToLeft: true })] });

const heading = (size, color, before, after, outline, extra = {}) => ({
  run: { size, bold: true, color, font: FONT },
  paragraph: { spacing: { before, after }, keepNext: true, keepLines: true, outlineLevel: outline, ...extra },
});

const margin = { top: 1300, bottom: 1200, left: MARGIN_LR, right: MARGIN_LR, header: 600, footer: 600 };
const doc = new Document({
  creator: 'MITODERM', title: COVER_TITLE, description: COVER_SUB,
  features: { updateFields: false },
  styles: {
    default: { document: { run: { font: FONT, size: SZ.body, language: { value: 'en-US', bidirectional: 'he-IL' } },
      paragraph: { spacing: { after: 100, line: 276 } } },
      heading1: heading(44, C.ink, 0, 80, 0, { border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.gold, space: 6 } } }),
      heading2: heading(28, C.goldDark, 300, 120, 1),
      heading3: heading(23, C.ink, 240, 80, 2),
    },
    paragraphStyles: [
      { id: 'TOC1', name: 'toc 1', basedOn: 'Normal', next: 'Normal', run: { size: 22, font: FONT },
        paragraph: { spacing: { after: 100 }, tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W, leader: 'dot' }] } },
    ],
  },
  numbering: { config: [
    { reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.START,
      style: { paragraph: { indent: { left: 360, hanging: 260 } }, run: { font: FONT } } }] },
    { reference: 'num', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.START,
      style: { paragraph: { indent: { left: 400, hanging: 340 } }, run: { font: FONT } } }] },
  ] },
  sections: sections.filter((sec, i) => i === 0 || sec.children.length).map((sec, i) => ({
    properties: {
      ...(i === 0 ? { titlePage: true } : {}),
      page: { size: { width: PAGE_W, height: PAGE_H, ...(sec.land ? { orientation: PageOrientation.LANDSCAPE } : {}) }, margin },
    },
    headers: { default: new Header({ children: [headerP()] }), ...(i === 0 ? { first: new Header({ children: [new Paragraph({ children: [] })] }) } : {}) },
    footers: { default: new Footer({ children: [footerP()] }), ...(i === 0 ? { first: new Footer({ children: [new Paragraph({ children: [] })] }) } : {}) },
    children: sec.children,
  })),
});

Packer.toBuffer(doc).then((buf) => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, buf);
  fs.writeFileSync(OUT + '.manifest.json', JSON.stringify({ src: SRC, included, missing, toc: tocEntries }, null, 1));
  console.log(JSON.stringify({ out: OUT, included, missing, sections: sections.length, toc: tocEntries.map((e) => e.bm) }));
});
