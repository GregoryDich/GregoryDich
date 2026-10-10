// Word document with the Hebrew texts of the v2 Story Scroll site.
//   NODE_PATH=<dir with docx> node he_docx.cjs <out.docx>
// Reads site/storyboard.he.json (new 7-block texts) and site/product-pages.he.json
// (catalogue-verified details: stats, protocol, actives, kit, indications).
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, HeadingLevel, AlignmentType, LevelFormat, Footer, PageNumber,
} = require('docx');

const SITE = path.join(__dirname, '..');
const load = (f) => JSON.parse(fs.readFileSync(path.join(SITE, f), 'utf8'));
const he = process.env.HE_JSON ? JSON.parse(fs.readFileSync(process.env.HE_JSON, 'utf8')) : load('storyboard.he.json');
const specEn = load('product-pages.json');
const specHe = load('product-pages.he.json');
const details = {};
specEn.forEach((s, i) => { details[s.slug] = specHe[i]; });

const ORDER = ['home', 'v-tech-system', 'exo-nad', 'exocell-mask', 'exosignal-hair', 'exosignal-spray',
  'exotech-gel', 'micro-boost-10', 'cell-renew-1-5', 'cellular-age-defense-2-5', 'derma-recovery-cream',
  'mitopen', 'mitoscan', 'about', 'synthetic-exosomes', 'biospicule'];
const KNOWLEDGE = new Set(['about', 'synthetic-exosomes', 'biospicule']);
const pages = Object.fromEntries(he.pages.map((p) => [p.slug, p]));
const homeItems = pages.home.items;
const navBlocks = (homeItems.find((i) => i.key === 'nav.blocks') || {}).he || '';
const BLOCK_HE = navBlocks.split(' · ');
const BLOCK_EN = ['Meet', 'Why', 'Inside', 'Feel it', 'Protocol', 'Kit & facts', 'Offer'];

const FONT = { ascii: 'Arial', hAnsi: 'Arial', cs: 'Arial' };
const GREEN = '1E4634', GREY = '6B6B6B', LINE = 'D9D4CC', FILL = 'F3EFE8';
const W = { field: 1500, he: 4300, en: 3838 }; // sums to 9638 = A4 minus 2 cm margins

const heRun = (text, o = {}) => new TextRun({ text, font: FONT, rightToLeft: true, size: 22, ...o });
const enRun = (text, o = {}) => new TextRun({ text, font: FONT, size: 18, color: GREY, ...o });
const hePara = (text, o = {}, p = {}) => new Paragraph({ bidirectional: true, spacing: { after: 60 }, ...p, children: [heRun(text, o)] });
const enPara = (text, o = {}, p = {}) => new Paragraph({ spacing: { after: 60 }, ...p, children: [enRun(text, o)] });

const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
const cell = (children, width, shade) => new TableCell({
  children, borders, width: { size: width, type: WidthType.DXA },
  margins: { top: 60, bottom: 60, left: 100, right: 100 },
  shading: shade ? { fill: shade, type: ShadingType.CLEAR, color: 'auto' } : undefined,
});
const lines = (s) => (s || '').split(' · ').filter(Boolean);

function row(fieldHe, heText, enText, opts = {}) {
  const heParas = (opts.split ? lines(heText) : [heText]).map((t) => hePara(t || '—', opts.bold ? { bold: true } : {}));
  const enParas = (opts.split ? lines(enText) : [enText]).map((t) => enPara(t || '—'));
  return new TableRow({ children: [
    cell([hePara(fieldHe, { bold: true, size: 20, color: GREEN })], W.field, FILL),
    cell(heParas.length ? heParas : [hePara('—')], W.he),
    cell(enParas.length ? enParas : [enPara('—')], W.en),
  ] });
}
function headRow() {
  return new TableRow({ tableHeader: true, children: [
    cell([hePara('שדה', { bold: true, size: 18, color: GREY })], W.field, FILL),
    cell([hePara('עברית', { bold: true, size: 18, color: GREY })], W.he, FILL),
    cell([enPara('English (source)', { bold: true })], W.en, FILL),
  ] });
}
const table = (rows) => new Table({
  visuallyRightToLeft: true, width: { size: W.field + W.he + W.en, type: WidthType.DXA },
  columnWidths: [W.field, W.he, W.en], rows: [headRow(), ...rows],
});
const h1 = (text, sub) => new Paragraph({ heading: HeadingLevel.HEADING_1, bidirectional: true, pageBreakBefore: true,
  children: [heRun(text, { size: 36, bold: true, color: GREEN }), ...(sub ? [heRun('   ' + sub, { size: 22, color: GREY })] : [])] });
const h2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, bidirectional: true, spacing: { before: 240, after: 120 },
  children: [heRun(text, { size: 26, bold: true, color: GREEN })] });
const h3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, bidirectional: true, spacing: { before: 160, after: 80 },
  children: [heRun(text, { size: 22, bold: true })] });
const bullet = (text) => new Paragraph({ bidirectional: true, numbering: { reference: 'dots', level: 0 }, children: [heRun(text)] });
const numbered = (text, ref) => new Paragraph({ bidirectional: true, numbering: { reference: ref, level: 0 }, children: [heRun(text)] });

function storyPage(p) {
  const by = Object.fromEntries(p.items.map((i) => [i.key, i]));
  const out = [h1(p.name, KNOWLEDGE.has(p.slug) ? 'עמוד מידע' : 'עמוד מוצר')];
  out.push(table([row('הצעת ערך', by.vp.he, by.vp.en)]));
  for (let n = 0; n < 7; n++) {
    out.push(h2(`${n} · ${BLOCK_HE[n] || BLOCK_EN[n]}  (${BLOCK_EN[n]})`));
    const labels = p.items.filter((i) => i.key.startsWith(`b${n}.label`));
    const cta = by[`b${n}.cta`];
    out.push(table([
      row('כותרת', by[`b${n}.title`].he, by[`b${n}.title`].en, { bold: true }),
      row('משפט', by[`b${n}.line`].he, by[`b${n}.line`].en),
      row('תגיות', labels.map((l) => l.he).join(' · '), labels.map((l) => l.en).join(' · '), { split: true }),
      row('כפתורים וקישורים', cta.he, cta.en, { split: true }),
    ]));
  }
  return out.concat(detailsSection(p.slug));
}

let numRefs = 0;
const numberingConfig = [{ reference: 'dots', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•',
  alignment: AlignmentType.START, style: { paragraph: { indent: { start: 540, hanging: 270 } } } }] }];
function newNumbering() {
  const reference = `steps-${++numRefs}`;
  numberingConfig.push({ reference, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.',
    alignment: AlignmentType.START, style: { paragraph: { indent: { start: 540, hanging: 270 } } } }] });
  return reference;
}

function detailsSection(slug) {
  const d = details[slug];
  if (!d) return [];
  const out = [h2('פרטים לעמוד — מהקטלוג (טקסט מאושר)')];
  out.push(h3('נתונים'));
  d.stats.forEach(([num, label]) => out.push(hePara(`${num} — ${label}`)));
  if (d.benefits && d.benefits.length) {
    out.push(h3(d.s01 ? d.s01.join(' · ') : 'יתרונות'));
    d.benefits.forEach(([t, txt]) => out.push(bullet(`${t}: ${txt}`)));
  }
  if (d.steps && d.steps.length) {
    out.push(h3(d.s02 ? d.s02.join(' · ') : 'פרוטוקול'));
    const ref = newNumbering();
    d.steps.forEach(([t, txt]) => out.push(numbered(`${t}: ${txt}`, ref)));
  }
  if (d.ingredients && d.ingredients.length) {
    out.push(h3(d.s03 ? d.s03.join(' · ') : 'רכיבים פעילים'));
    d.ingredients.forEach((t) => out.push(bullet(t)));
  }
  if (d.kit && d.kit.length) {
    out.push(h3(d.s04 ? d.s04.join(' · ') : 'תכולת האריזה'));
    d.kit.forEach((k) => out.push(bullet((Array.isArray(k) ? k : [k]).filter(Boolean).join(' — '))));
  }
  if (d.chips && d.chips.length) {
    out.push(h3(d.s05 ? d.s05.join(' · ') : 'אינדיקציות'));
    out.push(hePara(d.chips.join(' · ')));
  }
  return out;
}

// Figma layer of the Home frame -> field name for the editor.
const HOME_FIELD = [
  [/^nav\//, 'תפריט'], [/^eb\//, 'כותרת־על'], [/^Where science/, 'כותרת ראשית'], [/^lead/, 'פתיח'],
  [/^b\d\//, 'כפתור'], [/^s\/(IL|IT|100|4)/, 'נתון'], [/^s\//, 'כיתוב לנתון'], [/^sl\//, 'שם המדור'],
  [/^h2/, 'כותרת המדור'], [/^tg\//, 'תווית'], [/^sd\//, 'סטטוס'], [/^card\/desc/, 'תיאור בכרטיס'],
  [/^card\/link/, 'קישור בכרטיס'], [/^card\//, 'שם בכרטיס'], [/^st\/desc/, 'תיאור העיקרון'], [/^st\//, 'עיקרון'],
  [/^cta\/h/, 'קריאה לפעולה'], [/^cta\/p/, 'טקסט לקריאה'], [/^Footer\/copy/, 'זכויות'], [/^Footer\//, 'תחתית'],
];
function homeField(kind) {
  const layer = kind.replace(/^Home page, layer /, '').replace(/ at y=\d+$/, '');
  const hit = HOME_FIELD.find(([re]) => re.test(layer));
  return hit ? hit[1] : layer;
}
function homePage(p) {
  const rows = p.items.filter((i) => i.key !== 'nav.blocks').map((i) => row(homeField(i.kind), i.he, i.en));
  const blocks = p.items.find((i) => i.key === 'nav.blocks');
  if (blocks) rows.push(row('שמות הבלוקים', blocks.he, blocks.en, { split: true }));
  return [h1('עמוד הבית', 'Home'), table(rows)];
}

const cover = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 2400, after: 200 },
    children: [new TextRun({ text: 'MITODERM', font: FONT, size: 64, bold: true, color: GREEN, characterSpacing: 120 })] }),
  new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [heRun('טקסטים לאתר בעברית — גרסה 2', { size: 36, bold: true })] }),
  new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER, spacing: { after: 600 },
    children: [heRun('עמוד הבית ו־15 עמודים · 10.10.2026', { size: 24, color: GREY })] }),
  hePara('כל עמוד בנוי משבעה בלוקים: היכרות, למה, מה בפנים, התחושה, פרוטוקול, באריזה, הצעה. ' +
    'לכל בלוק: כותרת, משפט אחד, תגיות וכפתורים. בעמודה הימנית — הטקסט בעברית, בשמאלית — המקור באנגלית לבדיקה.'),
  hePara('בסוף כל עמוד מוצר: פרטים מהקטלוג (נתונים, פרוטוקול, רכיבים, תכולת האריזה, אינדיקציות) — הטקסט המאושר מהקטלוג, ללא שינוי.'),
  hePara('שמות המוצרים, הרכיבים והמכשירים נשארים באותיות לטיניות, כמו בקטלוג.'),
  h2('תוכן'),
  ...ORDER.map((s, i) => hePara(`${i === 0 ? '' : i + '. '}${s === 'home' ? 'עמוד הבית' : pages[s].name}${KNOWLEDGE.has(s) ? ' (עמוד מידע)' : ''}`)),
];

const body = [...cover];
for (const s of ORDER) body.push(...(s === 'home' ? homePage(pages[s]) : storyPage(pages[s])));

const doc = new Document({
  creator: 'MITODERM', title: 'MITODERM — טקסטים לאתר בעברית',
  styles: { default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: 'Arial', color: GREEN }, paragraph: { spacing: { before: 0, after: 240 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: 'Arial', color: GREEN }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 22, bold: true, font: 'Arial' }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ] },
  numbering: { config: numberingConfig },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER, children: [
      heRun('MITODERM · טקסטים לאתר · עמוד ', { size: 16, color: GREY }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: GREY })] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(process.argv[2], buf); console.log('wrote', process.argv[2], buf.length); });
