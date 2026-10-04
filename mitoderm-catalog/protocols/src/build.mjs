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
