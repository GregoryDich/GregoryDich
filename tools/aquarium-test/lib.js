// Общие помощники харнесса аквариума (headless Chromium через puppeteer-core + @sparticuz/chromium).
//  • запуск браузера с нужным viewport/DPR;
//  • движок по file:// (как в macOS-приложении) или через встроенный http-сервер (--http);
//  • перехват ошибок: pageerror, console.error, requestfailed и http-ответы >= 400;
//  • ожидание готовности ассетов (window.__aq.ready()).
// Флаг --allow-file-access-from-files НЕ передаётся по умолчанию: с ним Chromium перестаёт
// «пачкать» холст картинками с file://, и запрещённый getImageData не упадёт (SPEC F2).
'use strict';
const path = require('path');
const fs = require('fs');
const http = require('http');
const puppeteer = require('puppeteer-core');
const chromiumMod = require('@sparticuz/chromium');
const chromium = chromiumMod.default || chromiumMod;

const DEFAULT_ROOT = path.resolve(__dirname, '../../aquarium');

// --key value | --key=value | --flag ; числа приводятся; "1/30" → 0.0333…
function parseArgs(argv, defaults) {
  const o = Object.assign({}, defaults || {}), pos = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { pos.push(a); continue; }
    let k = a.slice(2), v;
    const eq = k.indexOf('=');
    if (eq >= 0) { v = k.slice(eq + 1); k = k.slice(0, eq); }
    else if (i + 1 < argv.length && !argv[i + 1].startsWith('--')) v = argv[++i];
    else v = true;
    if (k.startsWith('no-') && v === true) { o[k.slice(3)] = false; continue; }
    o[k] = typeof v === 'string' ? num(v) : v;
  }
  o._ = pos;
  return o;
}
function num(v) {
  if (/^-?\d+(\.\d+)?$/.test(v)) return +v;
  const m = /^(-?\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)$/.exec(v);
  if (m) return +m[1] / +m[2];
  return v;
}

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json',
  '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.svg': 'image/svg+xml', '.gif': 'image/gif', '.txt': 'text/plain; charset=utf-8', '.md': 'text/plain; charset=utf-8' };

// крошечный статический сервер (только 127.0.0.1, без выхода за корень)
function serve(root) {
  root = path.resolve(root);
  return new Promise((resolve, reject) => {
    const srv = http.createServer((req, res) => {
      try {
        const u = new URL(req.url, 'http://x');
        let p = path.resolve(root, '.' + decodeURIComponent(u.pathname));
        if (p !== root && !p.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
        if (fs.existsSync(p) && fs.statSync(p).isDirectory()) p = path.join(p, 'index.html');
        if (!fs.existsSync(p)) { res.writeHead(404); res.end('not found'); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(p).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-store' });
        fs.createReadStream(p).pipe(res);
      } catch (e) { res.writeHead(500); res.end(String(e)); }
    });
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => resolve({ base: `http://127.0.0.1:${srv.address().port}`, close: () => new Promise((r) => srv.close(r)) }));
  });
}

// строка запроса: test/wallpaper/nofilter/seed по умолчанию (--no-wallpaper, --no-nofilter, --no-test отключают)
// + дополнительные флаги из --q "debug=1&nobg=1"
function buildQuery(o, { test = true } = {}) {
  const q = new URLSearchParams();
  if (test && o.test !== false) q.set('test', '1');
  if (o.wallpaper !== false) q.set('wallpaper', '1');      // как в macOS-приложении: без подсказки и курсора
  if (o.nofilter !== false) q.set('nofilter', '1');
  if (o.seed !== undefined && o.seed !== false) q.set('seed', String(o.seed));
  if (o.q) for (const [k, v] of new URLSearchParams(String(o.q))) q.set(k, v);
  return q.toString();
}

async function openEngine(o, { test = true, viewport } = {}) {
  const root = path.resolve(o.root || DEFAULT_ROOT);
  const server = o.http ? await serve(root) : null;
  const base = server ? server.base : 'file://' + root;
  const url = `${base}/index.html?${buildQuery(o, { test })}`;
  const vp = viewport || { width: o.w || 1920, height: o.h || 1200, deviceScaleFactor: o.dpr || 1 };
  let args = [...chromium.args, '--force-color-profile=srgb', '--hide-scrollbars'];
  if (o['file-access']) args.push('--allow-file-access-from-files');
  // процесс рендера отдельно (blackbox.js убивает его, как WebKit — WebContent); по умолчанию — один процесс
  if (o.multiprocess) args = args.filter((a) => a !== '--single-process');
  const browser = await puppeteer.launch({ executablePath: await chromium.executablePath(), headless: chromium.headless,
    args, defaultViewport: vp, protocolTimeout: 600000 });
  return { browser, server, url, root, vp };
}

function captureErrors(page) {
  const errors = [], warnings = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push('console.error: ' + m.text());
    else if (m.type() === 'warn' || m.type() === 'warning') warnings.push('console.warn: ' + m.text());
  });
  page.on('requestfailed', (r) => {
    const why = (r.failure() && r.failure().errorText) || '';
    // <video>: Chromium отменяет первый запрос медиа и перезапрашивает его кусками — это не ошибка
    if (why === 'net::ERR_ABORTED' && /\.(mp4|webm|mov)(\?|#|$)/i.test(r.url())) { warnings.push('media request restarted: ' + r.url()); return; }
    errors.push('requestfailed: ' + r.url() + ' ' + why);
  });
  page.on('response', (r) => { if (r.status() >= 400) errors.push(`http ${r.status()}: ${r.url()}`); });
  return { errors, warnings };
}

async function newPage(env, { inject } = {}) {
  const page = await env.browser.newPage();
  if (env.vp) await page.setViewport(env.vp);
  const cap = captureErrors(page);
  if (inject) await page.evaluateOnNewDocument(inject.fn, ...(inject.args || []));
  return { page, cap };
}

async function gotoReady(page, url, timeout = 30000) {
  await page.goto(url, { waitUntil: 'load', timeout });
  await page.waitForFunction(() => window.__aq && window.__aq.ready(), { timeout, polling: 100 });
}

// шаг движка по одному кадру с уступкой rAF между кадрами (кадр успевает показаться — честнее для замеров)
async function stepFrames(page, dt, n, render = true) {
  return page.evaluate(async (dt, n, render) => {
    for (let i = 0; i < n; i++) {
      await window.__aq.step(dt, 1, { render });     // тест с видео (?bgvideo=…) — step возвращает Promise
      await new Promise((r) => requestAnimationFrame(() => r()));
    }
    return window.__aq.stats();
  }, dt, n, render);
}

// screenshot с необязательным кадрированием --clip x,y,w,h (CSS-пиксели)
function clipOpt(o) {
  if (!o.clip) return undefined;
  const [x, y, width, height] = String(o.clip).split(',').map(Number);
  return { x, y, width, height };
}

async function finish(env) {
  try { await env.browser.close(); } catch (e) { /* уже закрыт */ }
  if (env.server) await env.server.close();
}

function report(errors, warnings, allow) {
  console.error(errors.length ? 'ERRORS (' + errors.length + '):\n  ' + errors.join('\n  ') : 'errors: none');
  if (warnings && warnings.length) console.error('warnings:\n  ' + warnings.join('\n  '));
  if (errors.length && !allow) process.exitCode = 2;
}

function ensureDir(p) { fs.mkdirSync(p, { recursive: true }); return p; }

module.exports = { DEFAULT_ROOT, parseArgs, serve, buildQuery, openEngine, newPage, gotoReady, stepFrames, clipOpt, finish, report, ensureDir, captureErrors };
