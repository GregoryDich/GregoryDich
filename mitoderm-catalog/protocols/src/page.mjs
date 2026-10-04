// Renders one language version of the protocols page from its content file.
const NAMES = {
  'mitopen': 'MITOPEN', 'vtech-system': 'V-TECH SYSTEM', 'micro-boost-10': 'BIOSPICULE MICRO BOOST 10%',
  'exosignal-hair': 'EXOSIGNAL HAIR', 'mitoscan': 'MITOSCAN', 'exo-nad': 'EXO-NAD SKIN LONGEVITY PEEL',
  'exocell-mask': 'EXOCELL MASK', 'derma-recovery': 'DERMA RECOVERY CREAM', 'exotech-gel': 'EXOTECH GEL',
  'mitoderm-logo': 'MITODERM', 'mitoderm-wordmark': 'MITODERM',
};
const LANGS = [
  { code: 'he', label: 'עב', name: 'עברית' },
  { code: 'ru', label: 'RU', name: 'Русский' },
  { code: 'en', label: 'EN', name: 'English' },
];
const PRODUCTS = [
  'MICRO BOOST 10% BIOSPICULE™', 'V-TECH Serum', 'V-TECH Gel Mask', 'V-TECH SERUM', 'V-TECH GEL MASK',
  'EXOCELL MASK', 'DERMA RECOVERY CREAM', 'MICRO BOOST 10%', 'MITOTECH CELL BOOSTER', 'MITOTECH CELL BOOST',
  'CELL BOOSTER', 'LONGEVITY SERUM', 'EXOSIGNAL HAIR SERUM', 'EXOSIGNAL HAIR', 'EXO BIPHASIC PEEL', 'EXO PEEL',
  'pH NORMALIZER', 'EXOTECH GEL', 'BIOSPICULE™', 'BIOSPICULE', 'MITOPEN', 'MITOSCAN', 'Longevity', 'V-TECH', 'VTECH',
].sort((a, b) => b.length - a.length);
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const PRODUCT_RE = new RegExp('(?<![A-Za-z])(' + PRODUCTS.map(p => reEsc(esc(p))).join('|') + ')(?![A-Za-z])', 'g');

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
const clean = s => String(s).replace(/\s+/g, ' ').trim();
// Russian typesetting: a one- or two-letter preposition or conjunction never ends a line.
const tieRu = s => s.replace(/(^|[\s(])([вВиИсСкКоОуУаАяЯ]|на|На|по|По|до|До|не|Не|от|От|за|За|из|Из|во|Во|со|Со)\s/g, '$1$2\u00A0');

export function render(C, assets) {
  const rtl = C.dir === 'rtl';
  const T = C.lang === 'ru' ? tieRu : s => s;
  // Latin-only strings inside a right-to-left page keep their own reading order.
  const L = s => (rtl && !/[֐-׿]/.test(s) ? `<bdi dir="ltr">${esc(clean(s))}</bdi>` : esc(clean(s)));
  // Trademarked names end in a neutral sign (™); isolating them keeps the sign beside its word in Hebrew sentences.
  const rich = s => esc(T(clean(s))).replace(PRODUCT_RE, m => (rtl && m.endsWith('™') ? `<bdi class="pn">${m}</bdi>` : `<span class="pn">${m}</span>`));
  const pic = (id, cls = '') => `<span class="pic i-${id}${cls ? ' ' + cls : ''}" role="img" aria-label="${esc(NAMES[id])}"></span>`;

  const body = items => items.map(item => {
    if (typeof item === 'string') return `<p>${rich(item)}</p>`;
    if (item.list) return `<ul class="list">${item.list.map(li => `<li>${rich(li)}</li>`).join('')}</ul>`;
    if (item.note) return `<p class="note">${rich(item.note)}</p>`;
    if (item.chips) return `<ul class="chips">${item.chips.map(c => `<li>${esc(clean(c))}</li>`).join('')}</ul>`;
    if (item.products) return `<ul class="products">${item.products.map(([t, img]) =>
      `<li><span class="thumb${img ? '' : ' thumb--empty'}"${img ? '' : ' aria-hidden="true"'}>${img ? pic(img) : ''}</span><span>${rich(t)}</span></li>`).join('')}</ul>`;
    if (item.options) return `<div class="options">${item.options.map(([label, text]) =>
      `<div class="option"><p class="option__label">${rich(label)}</p><p>${rich(text)}</p></div>`).join('')}</div>`;
    throw new Error('Unknown body item: ' + JSON.stringify(item));
  }).join('');

  const block = (b, h = 'h4') => `<section class="block">${b.title ? `<${h} class="block__title">${L(b.title)}</${h}>` : ''}${body(b.body)}</section>`;

  const plate = (images, cls = '') => {
    const [main, ...subs] = images;
    return `<div class="plate${subs.length ? ' plate--duo' : ''}${cls ? ' ' + cls : ''}"><span class="glow" aria-hidden="true"></span>${pic(main, 'pic--main')}${subs.map((s, i) => pic(s, `pic--sub pic--sub${i + 1}`)).join('')}</div>`;
  };

  const steps = list => `<div class="steps-wrap"><span class="steps__bar" aria-hidden="true"></span><ol class="steps">${list.map(s => {
    const st = typeof s === 'string' ? { body: [s] } : s;
    const fig = st.figure ? `<figure class="step__figure">${pic(st.figure)}<figcaption>${esc(NAMES[st.figure])}</figcaption></figure>` : '';
    return `<li class="step"><div class="step__body">${st.title ? `<h4 class="step__title">${L(st.title)}</h4>` : ''}${fig}${body(st.body)}</div></li>`;
  }).join('')}</ol></div>`;

  const head = p => `<header class="protocol__head"><h3 class="protocol__title" id="t-${p.id}">${L(p.title)}</h3>${p.combo ? `<p class="protocol__combo">${L(p.combo)}</p>` : ''}${p.sub ? `<p class="protocol__sub">${esc(T(p.sub))}</p>` : ''}</header>`;

  const standard = p => `<article class="protocol" id="${p.id}" aria-labelledby="t-${p.id}">
${head(p)}
<div class="protocol__aside">${plate(p.images)}${(p.aside || []).map(b => block(b)).join('')}</div>
<div class="protocol__main">${steps(p.steps)}${(p.after || []).map(b => block(b)).join('')}</div>
</article>`;

  const stages = p => `<article class="protocol protocol--stages" id="${p.id}" aria-labelledby="t-${p.id}">
<div class="feature">${plate(p.images, 'plate--wide')}<div class="feature__text">${head(p)}<p class="lead">${rich(p.lead)}</p></div></div>
<div class="stages-wrap"><span class="stages__line" aria-hidden="true"></span><ol class="stages">${p.steps.map((s, i) =>
    `<li class="stage${i === 0 ? ' stage--wide' : ''}"><span class="stage__num" aria-hidden="true">${i + 1}</span><h4 class="stage__title">${L(s.title)}</h4>${body(s.body)}</li>`).join('')}</ol></div>
${(p.after || []).map(b => block(b)).join('')}
</article>`;

  const mask = p => `<article class="protocol protocol--mask" id="${p.id}" aria-labelledby="t-${p.id}">
<div class="feature">${plate(p.images, 'plate--wide')}<div class="feature__text">${head(p)}<section class="block"><h4 class="block__title">${L(p.use.title)}</h4>${steps(p.use.steps)}</section></div></div>
<div class="pair">${p.blocks.map(b => block(b)).join('')}</div>
<section class="home" aria-labelledby="home-${p.id}">
<h4 class="home__title" id="home-${p.id}">${esc(p.home.title)}</h4>
<div class="cards">${p.home.cards.map(c => `<section class="card"><h5 class="card__title">${L(c.title)}</h5>${body(c.body)}</section>`).join('')}</div>
<div class="maintain">${plate(p.home.maintain.images, 'plate--dark')}<div class="maintain__text"><h5 class="maintain__title">${esc(p.home.maintain.title)}</h5>${body(p.home.maintain.body)}</div></div>
</section>
</article>`;

  const protocol = p => (p.layout === 'stages' ? stages(p) : p.layout === 'mask' ? mask(p) : standard(p));

  const family = f => `<section class="family" id="${f.id}" data-section aria-labelledby="h-${f.id}">
<header class="band"><div class="wrap"><h2 class="band__title" id="h-${f.id}">${L(f.title)}</h2>${f.protocols.length > 1 ? `<ul class="band__links">${f.protocols.map(p => `<li><a href="#${p.id}">${L(p.title)}</a></li>`).join('')}</ul>` : ''}</div></header>
<div class="wrap">${f.protocols.map(protocol).join('\n')}</div>
</section>`;

  const shelf = (f, i) => `<div class="shelf__group${i === 0 ? ' shelf__group--lead' : ''}">
<a class="shelf__art" href="#${f.id}" tabindex="-1" aria-hidden="true"><span class="glow"></span>${f.tile.images.map(id => `<span class="pic i-${id}"></span>`).join('')}</a>
<a class="shelf__title" href="#${f.id}">${L(f.title)}</a>
<ul class="shelf__links">${f.tile.links.map(([t, id]) => `<li><a href="#${id}">${L(t)}</a></li>`).join('')}</ul>
</div>`;

  const langs = LANGS.map(l => `<a href="protocols.${l.code}.html" hreflang="${l.code}" lang="${l.code}" title="${l.name}" aria-label="${l.name}"${l.code === C.lang ? ' aria-current="page"' : ''}>${l.label}</a>`).join('');

  return `<!doctype html>
<html lang="${C.lang}" dir="${C.dir}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(C.title)}</title>
<meta name="description" content="${esc(C.description)}">
<meta name="theme-color" content="#F8F3E8">
${LANGS.filter(l => l.code !== C.lang).map(l => `<link rel="alternate" hreflang="${l.code}" href="protocols.${l.code}.html">`).join('\n')}
<script>document.documentElement.classList.add('js');setTimeout(function(){if(!window.__mdMotion)document.documentElement.classList.remove('js')},3000)</script>
<style>
${assets.fontFaces}
${assets.imageCss}
${assets.css}
</style>
</head>
<body>
<a class="skip" href="#main">${esc(C.ui.skip)}</a>
<span class="top-sentinel" aria-hidden="true"></span>
<header class="site-header">
<div class="wrap site-header__in">
<a class="brand" href="#top" aria-label="MITODERM"><span class="pic i-mitoderm-wordmark" aria-hidden="true"></span></a>
<nav class="nav" aria-label="${esc(C.ui.nav)}"><span class="nav__ind" aria-hidden="true"></span>${C.families.map(f => `<a href="#${f.id}" data-target="${f.id}">${esc(f.nav)}</a>`).join('')}</nav>
<nav class="langs" aria-label="${esc(C.ui.langs)}">${langs}</nav>
</div>
</header>
<main id="main">
<section class="hero wrap" id="top" data-hero>
<h1 class="hero__title">${esc(C.hero.title)}</h1>
<span class="hero__rule" aria-hidden="true"></span>
<p class="hero__sub">${esc(T(C.hero.sub))}</p>
${C.hero.latin ? `<p class="hero__latin" lang="en">${L(C.hero.latin)}</p>` : ''}
<div class="shelf">${C.families.map(shelf).join('')}</div>
</section>
${C.families.map(family).join('\n')}
</main>
<footer class="site-footer">
<div class="wrap site-footer__in">
<span class="pic i-mitoderm-logo footer-logo" role="img" aria-label="MITODERM"></span>
<p class="site-footer__line" lang="en">${L(C.footer)}</p>
<nav class="langs langs--footer" aria-label="${esc(C.ui.langs)}">${langs}</nav>
</div>
</footer>
<script>
${assets.motion}
</script>
<script>
${assets.app}
</script>
</body>
</html>
`;
}
