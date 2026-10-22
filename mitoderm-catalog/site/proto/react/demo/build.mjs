// Builds the React demo into dist/: demo.js (main.jsx bundled by esbuild) and index.html with the prototype's CSS and
// story config (from ../../vtech-live.html) and short copy (../../vtech-he-figma.json). The demo reads seq/ and img/
// from site/proto: run `npm install && npm run build` here, then `python3 serve-local.py` in site/proto and open
// http://localhost:8000/react/demo/dist/index.html
import { build } from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url)), proto = path.resolve(here, '../..');
const page = fs.readFileSync(path.join(proto, 'vtech-live.html'), 'utf8');
const css = page.match(/<style>[\s\S]*?<\/style>/)[0];
const config = JSON.parse(page.match(/config: (\{.*?\}), canvas:/)[1]);
const v = JSON.parse(fs.readFileSync(path.join(proto, 'vtech-he-figma.json'), 'utf8'));
const screens = [[v.s1.h1, v.s1.lead], [v.s2.h2, v.s2.p], [v.s3.h2, v.s3.p], [v.s4.h2, v.s4.p], [v.s5.h2, v.s5.p]].map(([title, text]) => ({ title, text }));
const offer = { title: v.s7.h2, text: v.s7.p, kitAlt: v.s1.h1, relatedTitle: v.s9.line_h };
fs.mkdirSync(path.join(here, 'dist'), { recursive: true });
await build({ entryPoints: [path.join(here, 'main.jsx')], bundle: true, format: 'iife', jsx: 'automatic', minify: true,
  nodePaths: [path.join(here, 'node_modules')],   // ../StoryPage.jsx and ../useFrameStory.js import react from here
  outfile: path.join(here, 'dist/demo.js'), define: { 'process.env.NODE_ENV': '"development"' } });   // development: StrictMode mounts twice
const data = JSON.stringify({ config, screens, offer }).replace(/</g, '\\u003c');
fs.writeFileSync(path.join(here, 'dist/index.html'), '<!doctype html><html lang="he" dir="rtl" class="js"><head><meta charset="utf-8">'
  + '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><base href="../../../"><title>Frame story — React demo</title>'
  + '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600&display=swap">' + css + '</head><body>'
  + `<div id="root"></div><script>window.__DEMO__ = ${data};</script><script src="react/demo/dist/demo.js"></script></body></html>`);
console.log('dist/index.html, dist/demo.js');
