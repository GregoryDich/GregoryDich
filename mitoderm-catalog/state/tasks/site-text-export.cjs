// Collects every text of the test site as a visitor meets it, page by page and block by block, into one JSON file.
// The rendered pages are the source: what is in the DOM after the page has loaded and been scrolled through, on a
// computer, on a phone and with "reduce motion" on (a text that only one of them shows is kept too). site-text-xlsx.py turns the JSON into
// the owner's Excel file.
//
// Usage (site running on 8787):
//   NODE_PATH=$(npm root -g) node site-text-export.cjs <out.json> [base url=http://127.0.0.1:8787]
// Per page: the browser title and the search description, then one row per block of text in page order:
//   area (which part of the page), tag, kind (heading, paragraph, button, ...), the text itself; attributes that
//   are read aloud or shown as hints (alt, aria-label, placeholder, title) come as rows of their own.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const [out = 'site-texts.json', base = 'http://127.0.0.1:8787'] = process.argv.slice(2);
const APP = path.resolve(__dirname, '../../codex-site');
const registry = JSON.parse(fs.readFileSync(path.join(APP, 'production/page-bible/REGISTRY.json'), 'utf8'));
const slugs = [];
(function walk(o) {
  if (Array.isArray(o)) o.forEach(walk);
  else if (o && typeof o === 'object') { if (typeof o.slug === 'string' && !slugs.includes(o.slug)) slugs.push(o.slug); Object.values(o).forEach(walk); }
})(registry);
const routes = [
  { route: '/', kind: 'home' },
  { route: '/catalog', kind: 'catalog' },
  ...slugs.map(slug => ({ route: '/products/' + slug, kind: 'product', slug })),
  { route: '/privacy', kind: 'privacy' },
  { route: '/no-such-page', kind: 'notfound' },
];
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Runs in the page: one row per block of text, in document order.
function collect() {
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'svg', 'SVG', 'HEAD', 'IFRAME', 'VIDEO', 'CANVAS']);
  const AREAS = [                                   // first match up the ancestors names the part of the page
    ['a.mitoderm-skip', 'skip'], ['header.site-header', 'header'], ['footer.site-footer', 'footer'],
    ['#contact', 'contact'],
    ['nav.vc-section-nav', 'vt-nav'], ['nav.vts-chapter-nav', 'vt-chapters'], ['a.vc-floating-inquiry', 'vt-floating'],
    ['article.pc-scene', 'film'], ['article.vts-scene', 'film'], ['.pc-hud', 'film-hud'],
    ['.pc-questions', 'faq'], ['.vc-faq', 'faq'], ['[class*="faq"]', 'faq'],
    ['#pc-evidence', 'evidence'], ['#pc-offer', 'offer'], ['#pc-training', 'training'], ['#pc-related', 'related'],
    ['#pc-story', 'film-frame'], ['#vtech-intro', 'film-frame'],
    ['#vtech-training', 'training'], ['#vtech-related', 'related'],
    ['article.catalog-product', 'catalog-card'], ['#catalog', 'catalog'],
    ['#home', 'home-hero'], ['#products', 'home-collection'], ['#support', 'home-support'],
    ['main.privacy-page', 'privacy'], ['main.source-fallback', 'notfound'],
    ['dialog', 'dialog'], ['[role="dialog"]', 'dialog'], ['main', 'main'],
  ];
  const norm = t => (t || '').replace(/ /g, ' ').replace(/[ \t\r\n]+/g, ' ').trim();
  function areaOf(el) {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      for (const [sel, key] of AREAS) {
        let hit = false;
        try { hit = n.matches(sel); } catch (e) { hit = false; }
        if (!hit) continue;
        const a = { key, id: n.id || '' };
        if (key === 'film') {
          const all = [...document.querySelectorAll('article.pc-scene, article.vts-scene')];
          a.scene = all.indexOf(n) + 1;
        }
        if (key === 'catalog-card') { const h = n.querySelector('h1,h2,h3,h4,bdi,strong'); a.name = norm(h && h.textContent); }
        return a;
      }
    }
    return { key: 'body', id: '' };
  }
  const inlineDisplay = d => d === 'inline' || d === 'inline-block' || d === 'inline-flex' || d === 'contents' || d === 'inline-grid';
  const hasText = el => norm(el.textContent).length > 0;
  function blockChildWithText(el) {                 // does a child (through inline wrappers) stand as a block of its own?
    for (const c of el.children) {
      if (SKIP.has(c.tagName) || !hasText(c)) continue;
      const d = getComputedStyle(c).display;
      if (c.tagName === 'BR') continue;
      if (!inlineDisplay(d)) return true;
      if (blockChildWithText(c)) return true;
    }
    return false;
  }
  function textOf(el) {                             // text with <br> as a line break and hidden helper spans kept
    let s = '';
    for (const n of el.childNodes) {
      if (n.nodeType === 3) s += n.nodeValue;
      else if (n.nodeType === 1) {
        if (SKIP.has(n.tagName)) continue;
        if (n.tagName === 'BR') s += '\n'; else s += textOf(n);
      }
    }
    return s;
  }
  const clean = t => t.replace(/ /g, ' ').split('\n').map(l => l.replace(/[ \t\r]+/g, ' ').trim()).filter(Boolean).join('\n');
  const rows = [];
  function shown(el) {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (n.hidden || cs.display === 'none') return false;
    }
    return true;
  }
  function kindOf(el) {
    const tag = el.tagName;
    const within = el.closest('button, a, summary, label, option, li, figcaption, h1, h2, h3, h4, h5, h6, dt, dd, th, td, p');
    const t = within ? within.tagName : tag;
    if (el.closest('button')) return 'button';
    if (el.closest('a')) return 'link';
    if (/^H1$/.test(t)) return 'h1';
    if (/^H[2-6]$/.test(t)) return 'heading';
    if (t === 'SUMMARY') return 'summary';
    if (t === 'LABEL') return 'label';
    if (t === 'OPTION') return 'option';
    if (t === 'LI') return 'item';
    if (t === 'FIGCAPTION') return 'caption';
    if (t === 'DT' || t === 'TH') return 'term';
    if (t === 'DD' || t === 'TD') return 'value';
    if (t === 'P') return 'paragraph';
    return 'short';
  }
  function push(el, kind, text, attr) {
    const t = clean(text);
    if (!t) return;
    rows.push({ area: areaOf(el), tag: el.tagName.toLowerCase(), cls: (el.getAttribute('class') || '').split(/\s+/).filter(Boolean).slice(0, 2).join('.'),
      kind, attr: attr || '', text: t, shown: shown(el) });
  }
  // words that are read aloud or shown as a hint - also on a picture, a film, a canvas or a drawing
  function hints(c) {
    for (const [name, kind] of [['aria-label', 'aria'], ['alt', 'alt'], ['placeholder', 'placeholder'], ['title', 'title']]) {
      const v = c.getAttribute(name);
      if (v && norm(v)) push(c, kind, v, name);
    }
  }
  function walk(el) {
    for (const c of el.children) {
      if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'HEAD'].includes(c.tagName)) continue;
      hints(c);
      if (SKIP.has(c.tagName)) continue;
      if (c.tagName === 'INPUT' && ['submit', 'button'].includes(c.type) && c.value) push(c, 'button', c.value, 'value');
      if (!hasText(c)) { walk(c); continue; }             // no text of its own: only the hints of what is inside (pictures)
      if (c.tagName === 'SELECT') { for (const o of c.options) push(o, 'option', o.textContent); continue; }
      if (blockChildWithText(c)) {
        // own loose text between block children (rare) is kept as rows of its own
        for (const n of c.childNodes) if (n.nodeType === 3 && norm(n.nodeValue)) push(c, kindOf(c), n.nodeValue);
        walk(c);
      } else {
        for (const inner of c.querySelectorAll('*')) hints(inner);   // a picture or a labelled mark inside a line of text
        push(c, kindOf(c), textOf(c));
      }
    }
  }
  walk(document.body);
  const meta = name => { const m = document.querySelector(`meta[name="${name}"], meta[property="${name}"]`); return m ? norm(m.getAttribute('content')) : ''; };
  return { title: norm(document.title), description: meta('description'), ogTitle: meta('og:title'), ogDescription: meta('og:description'),
    lang: document.documentElement.lang, dir: document.documentElement.dir, rows };
}

(async () => {
  const browser = await chromium.launch();
  const result = { base, made: new Date().toISOString(), pages: [] };
  for (const r of routes) {
    const entry = { ...r, views: {} };
    // three ways a visitor may get the page: a computer, a phone, and a computer set to "reduce motion" (the film
    // is replaced by still pictures with their descriptions and the page reads top to bottom)
    for (const [view, size] of [['desktop', { width: 1440, height: 900 }], ['phone', { width: 390, height: 664 }], ['calm', { width: 1440, height: 900 }]]) {
      const phone = view === 'phone';
      const ctx = await browser.newContext({ viewport: size, deviceScaleFactor: 1, hasTouch: phone, isMobile: phone, locale: 'he-IL',
        reducedMotion: view === 'calm' ? 'reduce' : 'no-preference' });
      const page = await ctx.newPage();
      const resp = await page.goto(base + r.route, { waitUntil: 'load' });
      entry.status = resp ? resp.status() : 0;
      await sleep(1200);
      // scroll through the page so that parts mounted on approach are in the DOM, then return to the top
      const height = await page.evaluate(() => document.documentElement.scrollHeight);
      for (let y = 0; y <= height; y += size.height * 2) { await page.evaluate(v => window.scrollTo(0, v), y); await sleep(60); }
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight)); await sleep(300);
      await page.evaluate(() => window.scrollTo(0, 0)); await sleep(300);
      entry.views[view] = await page.evaluate(collect);
      await ctx.close();
    }
    result.pages.push(entry);
    process.stderr.write(`${r.route} ${entry.status} desktop ${entry.views.desktop.rows.length} phone ${entry.views.phone.rows.length} calm ${entry.views.calm.rows.length}\n`);
  }
  await browser.close();
  fs.writeFileSync(out, JSON.stringify(result, null, 1));
  console.log(JSON.stringify({ pages: result.pages.length, out }));
})();
