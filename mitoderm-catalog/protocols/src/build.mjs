// Builds three self-contained pages: protocols.he.html, protocols.ru.html, protocols.en.html
// Usage: node mitoderm-catalog/protocols/src/build.mjs
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { render } from './page.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const read = p => readFileSync(join(root, p));
const ranges = JSON.parse(read('assets/fonts/unicode-ranges.json'));
const css = readFileSync(join(here, 'styles.css'), 'utf8');
const app = readFileSync(join(here, 'app.js'), 'utf8');
const motion = '/*! Motion 14.0.0 | MIT License | (c) Motion B.V. | motion.dev */\n' + read('assets/vendor/motion-14.0.0.min.js').toString('utf8').replace(/<\/script/gi, '<\\/script');

function webpSize(buf) {
  const chunk = buf.toString('ascii', 12, 16);
  if (chunk === 'VP8X') return [1 + buf.readUIntLE(24, 3), 1 + buf.readUIntLE(27, 3)];
  if (chunk === 'VP8L') { const b = buf.readUInt32LE(21); return [(b & 0x3fff) + 1, ((b >> 14) & 0x3fff) + 1]; }
  if (chunk === 'VP8 ') return [buf.readUInt16LE(26) & 0x3fff, buf.readUInt16LE(28) & 0x3fff];
  throw new Error('Unknown WebP layout');
}
const images = readdirSync(join(root, 'assets/img')).filter(f => f.endsWith('.webp'));
const imageCss = images.map(f => { const buf = read('assets/img/' + f); const [w, h] = webpSize(buf); return `.i-${f.replace('.webp', '')}{--ar:${w}/${h};background-image:url(data:image/webp;base64,${buf.toString('base64')})}`; }).join('\n');

for (const lang of ['he', 'ru', 'en']) {
  const C = (await import(`./content.${lang}.mjs`)).default;
  const fontFaces = C.fonts.map(s => `@font-face{font-family:Rubik;font-style:normal;font-weight:300 900;font-display:swap;src:url(data:font/woff2;base64,${read(`assets/fonts/rubik-${s}.woff2`).toString('base64')}) format("woff2");unicode-range:${ranges[s]}}`).join('\n');
  const html = render(C, { fontFaces, imageCss, css, app, motion });
  writeFileSync(join(root, `protocols.${lang}.html`), html);
  console.log(`protocols.${lang}.html`, (Buffer.byteLength(html) / 1024).toFixed(0) + ' KB');
}

// Artifact entry page: one link that opens a chooser for the three versions.
// It is wrapped in the artifact's document skeleton at publish time, so it has no <html>/<head>/<body>.
// A plain #he, #ru or #en on the link opens that version directly.
{
  const shelfIds = ['vtech-system', 'mitopen', 'exo-nad', 'exocell-mask'];
  const heights = { 'micro-boost-10': '74%', 'vtech-system': '86%', 'mitopen': '96%', 'exo-nad': '56%', 'exocell-mask': '70%' };
  const css1 = id => { const buf = read(`assets/img/${id}.webp`); const [w, h] = webpSize(buf); return `.i-${id}{--ar:${w}/${h};background-image:url(data:image/webp;base64,${buf.toString('base64')})}`; };
  const faces = ['hebrew', 'cyrillic', 'latin'].map(s => `@font-face{font-family:Rubik;font-style:normal;font-weight:300 900;font-display:swap;src:url(data:font/woff2;base64,${read(`assets/fonts/rubik-${s}.woff2`).toString('base64')}) format("woff2");unicode-range:${ranges[s]}}`).join('\n');
  const versions = [
    ['he', 'עברית', 'פרוטוקולים מקצועיים לטיפולים בקליניקה', 'rtl'],
    ['ru', 'Русский', 'Профессиональные протоколы процедур', 'ltr'],
    ['en', 'English', 'Professional In-Clinic Treatment Protocols', 'ltr'],
  ];
  const page = `<title>MITODERM Professional Treatment Protocols</title>
<script>(function(){var h=(location.hash||'').slice(1);if(/^(he|ru|en)$/.test(h))location.replace('protocols.'+h+'.html');})();</script>
<style>
${faces}
/* Layout: the three language versions as a list beside a shelf of packshots standing on a gold glow line. */
:root {
  --paper: #F8F3E8;
  --green: #1E4634;
  --gold: #9E661F;
  --gold-ink: #8A5717;
  --ink: #57524A;
  --line: rgba(158, 102, 31, .32);
  --font: Rubik, system-ui, -apple-system, "Segoe UI", Arial, sans-serif;
  --ease: cubic-bezier(.16, 1, .3, 1);
  color-scheme: light;
}
${['mitoderm-wordmark', ...shelfIds].map(css1).join('\n')}
body { background: var(--paper); color: var(--ink); font: 400 1.0625rem/1.6 var(--font); -webkit-font-smoothing: antialiased; }
.page { max-width: 1120px; margin-inline: auto; padding-inline: clamp(16px, 4vw, 48px); padding-block: clamp(24px, 5vw, 56px); display: grid; gap: clamp(32px, 5vw, 56px); }
.wordmark { display: block; width: 170px; height: 36px; background-position: left center; background-size: contain; background-repeat: no-repeat; }
.layout { display: grid; gap: 40px 48px; align-items: center; }
.layout > * { min-width: 0; }
@media (min-width: 900px) { .layout { grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); } }
h1 { margin: 0; color: var(--green); font-weight: 700; font-size: clamp(2rem, 1.4rem + 2.4vw, 3.25rem); line-height: 1.1; letter-spacing: -.01em; text-wrap: balance; max-width: 15ch; }
.rule { display: block; width: 88px; height: 2px; margin-block: 22px 28px; background: var(--gold); }
.versions { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--line); }
.versions a { display: grid; justify-items: start; gap: 2px; padding-block: 18px; border-bottom: 1px solid var(--line); color: var(--ink); text-decoration: none; }
.v__lang { font-size: 1.375rem; font-weight: 700; color: var(--green); transition: color .15s var(--ease); }
.v__title { font-size: 1rem; }
.versions a:hover .v__lang { color: var(--gold-ink); }
.versions a:hover .v__title { text-decoration: underline; text-decoration-color: var(--line); text-underline-offset: .22em; }
.versions a:focus-visible { outline: 2px solid var(--gold); outline-offset: 4px; border-radius: 4px; }
.shelf { position: relative; display: flex; align-items: flex-end; justify-content: center; gap: 3%; height: clamp(190px, 26vw, 330px); padding-inline: 2%; isolation: isolate; }
.shelf::after { content: ""; position: absolute; z-index: -1; inset-inline: 0; bottom: 0; height: 1px; background: linear-gradient(90deg, transparent, var(--line), transparent); }
.glow { position: absolute; z-index: -1; inset-inline: 0; bottom: -12%; height: 42%; background: radial-gradient(50% 50% at 50% 70%, rgba(158, 102, 31, .22), transparent 74%); }
.pic { flex: 0 1 auto; min-width: 0; height: var(--h); aspect-ratio: var(--ar); max-width: 100%; background-position: center bottom; background-size: contain; background-repeat: no-repeat; filter: drop-shadow(0 14px 16px rgba(36, 28, 18, .16)); }
footer { font-size: .8125rem; font-weight: 500; letter-spacing: .14em; color: var(--gold-ink); }
@media (prefers-reduced-motion: no-preference) {
  .pic { animation: settle .9s var(--ease) both; animation-delay: calc(var(--i) * 60ms + 120ms); }
  .glow { animation: bloom 1s var(--ease) both .1s; }
}
@keyframes settle { from { transform: translateY(18px); } }
@keyframes bloom { from { transform: scaleX(.4); opacity: 0; } }
</style>
<div class="page">
<span class="wordmark i-mitoderm-wordmark" role="img" aria-label="MITODERM"></span>
<main class="layout">
<div>
<h1>Professional Treatment Protocols</h1>
<span class="rule" aria-hidden="true"></span>
<ul class="versions">
${versions.map(([code, name, title, dir]) => `<li><a href="protocols.${code}.html" hreflang="${code}" lang="${code}"><span class="v__lang" dir="${dir}">${name}</span><span class="v__title" dir="${dir}">${title}</span></a></li>`).join('\n')}
</ul>
</div>
<div class="shelf" aria-hidden="true"><span class="glow"></span>${shelfIds.map((id, i) => `<span class="pic i-${id}" style="--h:${heights[id]};--i:${i}"></span>`).join('')}</div>
</main>
<footer lang="en">MITODERM | WHERE SCIENCE MEETS BEAUTY</footer>
</div>
`;
  writeFileSync(join(root, 'artifact-index.html'), page);
  console.log('artifact-index.html', (Buffer.byteLength(page) / 1024).toFixed(0) + ' KB');
}
