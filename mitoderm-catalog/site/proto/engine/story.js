// The V-TECH frame story engine, as one ES module: the scroll story on pre-rendered frames that build-vtech.py pages
// use, and that a React (or any) app mounts the same way. Nothing runs at import (safe to import during server
// rendering); createFrameStory() runs in the browser only, after the elements exist (React: in useEffect).
// Scroll story on pre-rendered Blender frames: between two neighbouring screens their run plays (frame = share of the
// scroll from the first screen, once it has been read, to the next one); on a screen its key frame holds. The last run
// builds the kit while the offer copy arrives; then the card rises and the 3D kit flies into its picture. Memory: only frames −4…+8 around the wanted one
// (ahead = the scroll direction) and the runs' end frames stay decoded, every other bitmap is closed; a worker
// fetches and decodes off the main thread (WebKit would decode on the main thread at drawImage) and keeps the
// compressed files, so the whole story downloads once. Cells: a field of exosome sprites the camera flies through
// from S1 to S3 (far ones behind the product, near ones in front of it but never over the copy or the S3 hero).
//
// createFrameStory({
//   config,        // what build-vtech.py writes: { runs: [{ a, b, n, box }], tiers: [480, …], cells: ['c01', …], mols, helix }
//   base,          // the folder that holds seq/ and img/, absolute or relative to the page ('/v-tech/'; default: the page's own)
//   canvas,        // the fixed canvas the frames are drawn on (#seq)
//   sections,      // the story screens in order, runs.length + 1 of them (meet, why, inside, feel, protocol, offer);
//                  // each one's .wrap (or the section itself) ends its copy
//   header,        // the sticky header: on a phone the stage starts under it
//   card, cardCanvas,           // the offer card and its canvas: the kit lands there (optional)
//   bg, plate, helix,           // the smoke layer, the deep plate behind S2–S3, the DNA helix <img> (optional)
//   cellLayers: [back, front],  // the two cell layers, behind and in front of the canvas (optional)
//   root,          // gets the class .story and --stage-top / --stage-h / --push (default: <html>)
//   phoneQuery,    // default '(max-width: 899px)'
//   observe,       // the element whose size changes re-measure the page (default: the sections' parent)
//   tier, noWorker // QA: force a frame tier / decode on the main thread
// }) → { measure(), destroy(), state() }
export function createFrameStory(o) {
  const CFG = o.config, BASE = new URL(o.base || '', document.baseURI).href;   // base may be relative ('/v-tech/')
  let destroyed = false;
  const RUNS = CFG.runs, R = RUNS.length, NS = RUNS.map(r => r.n), TIERS = CFG.tiers.slice().sort((a, b) => a - b), SPRITES = CFG.cells, MOLS = CFG.mols || [];
  const OFF = NS.map((n, k) => NS.slice(0, k).reduce((a, b) => a + b, 0)), TOTAL = OFF[R - 1] + NS[R - 1];
  const BACK = 4, AHEAD = 8, FLIGHT = 4, WARM = 2;              // decode window and fetch concurrency
  const HOLD0 = 0.04, HOLD = 0.15, READ = 0.85, END = 0.12;      // a screen holds its key frame until it has been read
  const LAND0 = 0.85, LAND1 = 0.25;   // the last run ends as the offer card's top reaches 85% of the screen; the kit lands by 25%
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  const canvas = o.canvas, ctx = canvas.getContext('2d');
  const bg = o.bg || null, plate = o.plate || null;
  const card = o.card || null, cardCv = o.cardCanvas || (card && card.querySelector('.kc-live')), cardCtx = cardCv && cardCv.getContext('2d');
  const secs = o.sections, header = o.header || null, root = o.root || document.documentElement;   // sections: the screens in story order, one more than the runs
  const phone = matchMedia(o.phoneQuery || '(max-width: 899px)'), calm = matchMedia('(prefers-reduced-motion: reduce)');
  const U = RUNS.reduce((u, r) => [Math.min(u[0], r.box[0]), Math.min(u[1], r.box[1]), Math.max(u[2], r.box[2]), Math.max(u[3], r.box[3])], [1, 1, 0, 0]);   // all runs' boxes
  let stage = null, push = 0, lastPush = -1;   // phone: the stage rect under the header that the runs' union fits into
  const nav = navigator, saveData = !!(nav.connection && nav.connection.saveData);
  const capped = (nav.maxTouchPoints > 1 && /Macintosh/.test(nav.userAgent)) || (nav.deviceMemory > 0 && nav.deviceMemory <= 4);   // iPad, small RAM: ≤ 1600
  const key = (r, i) => r * 1000 + i, rOf = k => Math.floor(k / 1000), iOf = k => k % 1000, gOf = k => OFF[rOf(k)] + iOf(k);
  const kOfG = g => { let r = 0; while (r < R - 1 && g >= OFF[r + 1]) r++; return key(r, g - OFF[r]); };
  const KIT = key(R - 1, NS[R - 1] - 1);
  const ENDS = RUNS.flatMap((x, r) => [key(r, 0), key(r, NS[r] - 1)]);              // the runs' end frames, kept decoded
  const SCREENS = RUNS.map((x, r) => key(r, 0)).concat(KIT);                        // reduced motion / Save-Data: these only
  const ladder = n => { const o = [0, n - 1], q = [[0, n - 1]]; while (q.length) { const [a, b] = q.shift(), m = (a + b) >> 1; if (m > a && m < b) { o.push(m); q.push([a, m], [m, b]); } } for (let i = 0; i < n; i++) if (!o.includes(i)) o.push(i); return o; };
  const LADDER = NS.map(ladder);                                                    // coarse to fine: 0, 39, 19, 9, 29, …

  let mode = 'off', tier = 0, dpr = 1, W = 0, H = 0, cover = { x: 0, y: 0, w: 0, h: 0 }, geo = [], cardTop = 0, lastTf = '';
  let want = key(0, 0), wantG = 0, dir = 1, lastY = -1, pos = 0, shown = -1, dirty = true, misses = 0, missAt = -1, want0 = -1;
  let stride = 1, vel = 0, wantT = 0;   // scroll speed in frames per second → how sparse the window ahead is
  let raf = 0, needPump = true, lastOp = -1, lastBg = '', lastPlate = -1, keep = new Set(), warmPlan = [], planFor = '';
  const bm = new Map(), flight = new Map(), warmFlight = new Map(), pending = new Map(), warmed = new Set(), missing = new Set(), fails = new Map();
  const peak = { n: 0, bytes: 0 }, stats = { n: 0, fetch: 0, decode: 0, maxDecode: 0 };   // stats: the worker's timings, for QA
  const url = k => new URL(`seq/${tier}/${RUNS[rOf(k)].a}_${RUNS[rOf(k)].b}_${String(iOf(k)).padStart(3, '0')}.webp`, BASE).href;

  // decoding: an inline worker (fetch → blob, kept compressed → createImageBitmap, transferred); without one (old
  // Safari, a CSP without blob: workers) <img> + decode() on the main thread
  const WORKER = `const cache = new Map(), ctl = new Map(), ready = [], inprog = new Map(); let bytes = 0, busy = 0; const CAP = 64e6, DEC = 2;
const abortErr = () => Object.assign(new Error('abort'), { name: 'AbortError' });
function get(u, sig) {   // the compressed file: from the cache, or one fetch shared by every request for it
  const b = cache.get(u); if (b) { cache.delete(u); cache.set(u, b); return Promise.resolve(b); }
  let f = inprog.get(u);
  if (!f) {
    const c = new AbortController();
    f = { c, refs: 0, p: fetch(u, { signal: c.signal }).then(r => { if (!r.ok) throw Object.assign(new Error('http'), { status: r.status }); return r.blob(); })
      .then(b => { cache.set(u, b); bytes += b.size; for (const [k, x] of cache) { if (bytes <= CAP) break; if (k !== u) { cache.delete(k); bytes -= x.size; } } return b; })
      .finally(() => inprog.delete(u)) };
    inprog.set(u, f);
  }
  f.refs++;
  return new Promise((res, rej) => {
    const off = () => { if (--f.refs === 0) f.c.abort(); rej(abortErr()); };   // the last one out cancels the download
    if (sig.aborted) return off();
    sig.addEventListener('abort', off, { once: true });
    f.p.then(b => { sig.removeEventListener('abort', off); f.refs--; res(b); }, e => { sig.removeEventListener('abort', off); f.refs--; rej(e); });
  });
}
function next() {   // decode the most urgent fetched frame, two at a time, so a stop never waits behind a queue
  while (busy < DEC && ready.length) {
    ready.sort((a, b) => a.c.p - b.c.p); const j = ready.shift();
    if (j.c.signal.aborted) { ctl.delete(j.id); postMessage({ id: j.id, err: 'abort' }); continue; }
    busy++; const t1 = performance.now();
    createImageBitmap(j.b, { premultiplyAlpha: 'premultiply', colorSpaceConversion: 'none' })   // sRGB frames: no conversion, ready to upload
      .then(bmp => postMessage({ id: j.id, bmp, ft: j.ft, dt: performance.now() - t1 }, [bmp]), () => postMessage({ id: j.id, err: 'http' }))
      .finally(() => { busy--; ctl.delete(j.id); next(); });
  }
}
onmessage = async e => {
  const m = e.data;
  if (m.abort) { const c = ctl.get(m.abort); if (c) c.abort(); return; }
  if (m.prio) { for (const [id, p, w] of m.prio) { const c = ctl.get(id); if (c) { c.p = p; if (w === 0) c.warm = false; } } next(); return; }   // w 0: a fetch now wanted decoded
  const c = new AbortController(); c.warm = m.warm; c.p = m.p; ctl.set(m.id, c);
  try {
    const t0 = performance.now(), b = await get(m.url, c.signal), ft = performance.now() - t0;
    if (c.warm) { ctl.delete(m.id); postMessage({ id: m.id, warm: 1 }); return; }
    if (c.signal.aborted) throw abortErr();
    ready.push({ id: m.id, b, c, ft }); next();
  } catch (err) { ctl.delete(m.id); postMessage({ id: m.id, err: err.name === 'AbortError' ? 'abort' : err.status ? 'http' : 'net' }); }
};`;
  let worker = null, reqId = 0, okOnce = false, workerUrl = '';
  try {
    if (window.Worker && window.createImageBitmap && !o.noWorker) {
      workerUrl = URL.createObjectURL(new Blob([WORKER], { type: 'text/javascript' })); worker = new Worker(workerUrl);
      worker.onmessage = e => done(e.data); worker.onerror = () => fallback();
    }
  } catch (e) { worker = null; }
  function fallback() {   // the worker could not run or fetch here: everything again on the main thread
    if (!worker) return; worker.terminate(); worker = null;
    pending.clear(); flight.clear(); warmFlight.clear(); needPump = true; kick();
  }
  function request(k, warm, p = 0) {
    const id = ++reqId, u = url(k); pending.set(id, { k, warm, t: tier }); (warm ? warmFlight : flight).set(k, id);
    if (worker) { worker.postMessage({ id, url: u, warm, p }); return; }
    const im = new Image(); im.decoding = 'async'; im.src = u;
    if (warm) { im.onload = () => done({ id, warm: 1 }); im.onerror = () => done({ id, err: 'http' }); }
    else im.decode().then(() => done({ id, img: im }), () => done({ id, err: 'http' }));
  }
  function cancel(id) { pending.delete(id); if (worker) worker.postMessage({ abort: id }); }
  const release = e => { if (e.im.close) e.im.close(); else e.im.removeAttribute('src'); };
  function done(m) {
    const p = pending.get(m.id);
    if (!p) { if (m.bmp) m.bmp.close(); return; }   // cancelled meanwhile
    pending.delete(m.id); const map = p.warm ? warmFlight : flight; if (map.get(p.k) === m.id) map.delete(p.k);
    needPump = true; kick();
    if (p.t !== tier) { if (m.bmp) m.bmp.close(); return; }
    if (m.err) {
      if (m.err === 'net' && worker && !okOnce) { fallback(); return; }
      if (m.err !== 'abort') { const f = (fails.get(p.k) || 0) + 1; fails.set(p.k, f); if (m.err === 'http' || f >= 3) missing.add(p.k); }
      if (p.k === KIT && missing.has(KIT) && card) card.classList.remove('live');   // no kit frame: the card keeps its picture
      return;
    }
    okOnce = true; warmed.add(p.k);
    if (m.warm) { if (!p.warm && keep.has(p.k)) request(p.k, false); return; }   // upgraded too late: decode from the worker's cache
    const im = m.bmp || m.img;
    if (!keep.has(p.k)) { release({ im }); return; }   // scrolled away while it decoded
    if (m.dt != null) { stats.n++; stats.fetch += m.ft; stats.decode += m.dt; stats.maxDecode = Math.max(stats.maxDecode, m.dt); }
    const w = im.width || im.naturalWidth, h = im.height || im.naturalHeight, old = bm.get(p.k);
    if (old) release(old);
    bm.set(p.k, { im, w, h, bytes: w * h * 4 });
    let n = 0, b = 0; for (const e of bm.values()) { n++; b += e.bytes; }
    peak.n = Math.max(peak.n, n); peak.bytes = Math.max(peak.bytes, b);
    if (p.k === KIT) drawCard();
    if (p.k === want || shown < 0 || Math.abs(gOf(p.k) - wantG) < Math.abs(gOf(shown) - wantG)) dirty = true;
  }

  function desired() {   // the frames to keep decoded, most urgent first
    const ends = (mode === 'full' ? ENDS : SCREENS).slice().sort((a, b) => Math.abs(gOf(a) - wantG) - Math.abs(gOf(b) - wantG));
    const out = [want];   // then its two neighbours, then the two nearest end frames (a stop always has a key frame close by)
    if (mode === 'full') for (const g of [wantG - dir, wantG + dir]) if (g >= 0 && g < TOTAL) out.push(kOfG(g));
    out.push(...ends.slice(0, 2));
    // ahead every stride-th frame on a fixed grid (a fast scroll: the targets stay put until passed, so they finish
    // decoding instead of being dropped every step), behind every one
    const g0 = dir > 0 ? Math.floor(wantG / stride) * stride : Math.ceil(wantG / stride) * stride;
    if (mode === 'full') for (let d = 1; d <= AHEAD; d++) {
      const a = g0 + d * stride * dir, b = wantG - d * dir;
      if (a >= 0 && a < TOTAL) out.push(kOfG(a));
      if (d <= BACK && b >= 0 && b < TOTAL) out.push(kOfG(b));
    }
    return [...new Set(out.concat(ends))];
  }
  function warmList() {   // the rest of the story, fetched (not decoded): this run, then the next ones in the scroll direction
    const r = rOf(want), id = r + ':' + dir;
    if (planFor !== id) {
      const order = [r, r + dir, r - dir]; for (let d = 2; d < R; d++) order.push(r + d * dir, r - d * dir);
      warmPlan = order.filter(x => x >= 0 && x < R).flatMap(x => LADDER[x].map(i => key(x, i))); planFor = id;
    }
    return warmPlan;
  }
  function pump() {
    needPump = false;
    if (mode === 'off' || document.hidden) return;
    const D = desired(), r = rOf(want), rank = new Map(D.map((k, i) => [k, i])), prio = []; keep = new Set(D);
    for (const [k, id] of flight) if (!keep.has(k)) { flight.delete(k); cancel(id); } else prio.push([id, rank.get(k)]);   // passed by: drop
    for (const [k, id] of warmFlight) if (Math.abs(rOf(k) - r) >= 2) { warmFlight.delete(k); cancel(id); }   // runs two or more away
    for (const [k, e] of bm) if (!keep.has(k) && k !== shown) { release(e); bm.delete(k); }
    for (const [i, k] of D.entries()) {
      if (worker && warmFlight.has(k)) {   // already on its way: decode it when it arrives
        const id = warmFlight.get(k); warmFlight.delete(k); flight.set(k, id); pending.get(id).warm = false; prio.push([id, i, 0]); continue;
      }
      if (i < 3 && !bm.has(k) && !flight.has(k) && !missing.has(k) && flight.size + warmFlight.size >= FLIGHT) {   // the most urgent take a slot
        let worst = null, wr = -1;
        for (const [x, id] of warmFlight) { worst = [x, id, warmFlight]; wr = 1e9; break; }
        if (!worst) for (const [x, id] of flight) if (rank.get(x) > wr && rank.get(x) > i) { wr = rank.get(x); worst = [x, id, flight]; }
        if (worst) { worst[2].delete(worst[0]); cancel(worst[1]); }
      }
      if (flight.size + warmFlight.size >= FLIGHT) break;
      if (!bm.has(k) && !flight.has(k) && !missing.has(k)) request(k, false, i);
    }
    if (worker && prio.length) worker.postMessage({ prio });   // the worker decodes in this order
    if (mode === 'full') for (const k of warmList()) {
      if (warmFlight.size >= WARM || flight.size + warmFlight.size >= FLIGHT) break;
      if (!warmed.has(k) && !bm.has(k) && !flight.has(k) && !warmFlight.has(k) && !missing.has(k)) request(k, true);
    }
  }

  function pick() {   // the wanted frame, or the nearest decoded one
    if (bm.has(want)) return want;
    let best = -1, bd = 1e9;
    for (const k of bm.keys()) { const d = Math.abs(gOf(k) - wantG) + (rOf(k) === rOf(want) ? 0 : 0.5); if (d < bd) { bd = d; best = k; } }
    return best;
  }
  let placed = '', shownBox = null;
  const boxRect = r => { const b = RUNS[r].box; return { x: cover.x + b[0] * cover.w, y: cover.y + b[1] * cover.h, w: (b[2] - b[0]) * cover.w, h: (b[3] - b[1]) * cover.h }; };
  function draw() {
    if (mode === 'off') return;
    const k = pick();
    if (k !== want && want !== missAt) { misses++; missAt = want; }
    if (k < 0 || (k === shown && !dirty)) return;
    // the canvas is the frame's own size, drawn 1:1, and the compositor scales it into the run's box: no resampling on
    // the main thread and never a viewport-sized (5K) backing store
    const e = bm.get(k), B = boxRect(rOf(k)), id = B.w.toFixed(2) + 'x' + B.h.toFixed(2);
    if (canvas.width !== e.w || canvas.height !== e.h) { canvas.width = e.w; canvas.height = e.h; } else ctx.clearRect(0, 0, e.w, e.h);
    ctx.drawImage(e.im, 0, 0);
    if (id !== placed) { canvas.style.width = B.w + 'px'; canvas.style.height = B.h + 'px'; placed = id; }
    shownBox = B;
    const was = shown; shown = k; dirty = false;
    if (was >= 0 && was !== k && !keep.has(was) && bm.has(was)) { release(bm.get(was)); bm.delete(was); }
  }

  // the offer card: the last frame of the kit run, cropped to what it shows
  let kitCrop = null;
  function drawCard() {
    const e = bm.get(KIT); if (!cardCtx || !e || !cardCv.width) return;
    if (!kitCrop || kitCrop.im !== e.im) kitCrop = { im: e.im, r: alphaBox(e), w: e.w, h: e.h };
    const [sx, sy, sw, sh] = kitCrop.r, cw = cardCv.width, ch = cardCv.height, s = Math.min(cw / sw, ch / sh), w = sw * s, h = sh * s;
    cardCtx.clearRect(0, 0, cw, ch); cardCtx.imageSmoothingQuality = 'high';
    cardCtx.drawImage(e.im, sx, sy, sw, sh, (cw - w) / 2, (ch - h) / 2, w, h);
    card.classList.add('drawn');
  }
  function alphaBox(e) {
    try {
      const s = Math.min(1, 320 / e.w), w = Math.max(1, Math.round(e.w * s)), h = Math.max(1, Math.round(e.h * s));
      const c = document.createElement('canvas'); c.width = w; c.height = h;
      const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(e.im, 0, 0, w, h);
      const d = x.getImageData(0, 0, w, h).data; let x0 = w, y0 = h, x1 = -1, y1 = -1;
      for (let y = 0; y < h; y++) for (let i = 0; i < w; i++) if (d[(y * w + i) * 4 + 3] > 24) { if (i < x0) x0 = i; if (i > x1) x1 = i; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      if (x1 < 0) return [0, 0, e.w, e.h];
      const p = 0.04 * Math.max(x1 - x0, y1 - y0);
      x0 = Math.max(0, (x0 - p) / s); y0 = Math.max(0, (y0 - p) / s); x1 = Math.min(e.w, (x1 + 1 + p) / s); y1 = Math.min(e.h, (y1 + 1 + p) / s);
      return [x0, y0, x1 - x0, y1 - y0];
    } catch (err) { return [0, 0, e.w, e.h]; }
  }

  function pickTier() {
    if (typeof o.tier === 'number') return o.tier;   // QA: force a tier
    let list = TIERS;
    if (capped) { const low = list.filter(t => t <= 1600); list = low.length ? low : [list[0]]; }
    const need = cover.w * dpr;   // the frame's tier width that covers the drawn rect in device pixels (same for every box)
    return list.find(t => t >= need) || list[list.length - 1];
  }
  function reset(m, t) {
    for (const e of bm.values()) release(e); bm.clear();
    for (const id of [...pending.keys()]) cancel(id); flight.clear(); warmFlight.clear();
    warmed.clear(); missing.clear(); fails.clear(); planFor = ''; shown = -1; kitCrop = null; mode = m; tier = t;
    root.classList.toggle('story', m !== 'off');
    if (card) { card.classList.toggle('live', m !== 'off' && !stage); if (m !== 'off' && !stage) card.classList.remove('rv'); }   // no reveal shift: the kit lands on it; phone: the card keeps its HD picture
    ctx.clearRect(0, 0, canvas.width, canvas.height); needPump = true;
  }
  function measure() {
    dpr = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight;
    const s = Math.max(W / 16, H / 10); cover = { w: 16 * s, h: 10 * s, x: (W - 16 * s) / 2, y: (H - 10 * s) / 2 };
    stage = null;
    if (phone.matches) {   // the union of the runs' boxes fits the stage: the same scale for every run, so the motion carries on
      const top = Math.round(header ? header.getBoundingClientRect().bottom : 0), sh = Math.round(0.46 * H);
      const uw = U[2] - U[0], uh = U[3] - U[1], k = Math.min(0.98 * W / (uw * 16), 0.96 * sh / (uh * 10));
      cover = { w: 16 * k, h: 10 * k }; cover.x = (W - uw * cover.w) / 2 - U[0] * cover.w; cover.y = top + (sh - uh * cover.h) / 2 - U[1] * cover.h;
      stage = { top, h: sh }; root.style.setProperty('--stage-top', top + 'px'); root.style.setProperty('--stage-h', sh + 'px');
    }
    const m = !TIERS.length ? 'off' : calm.matches || saveData ? 'keys' : 'full', t = m === 'off' ? 0 : pickTier();
    if (m !== mode || t !== tier) reset(m, t);
    placed = '';
    geo = secs.map(s => ({ top: s.offsetTop, h: s.offsetHeight, cont: (s.querySelector('.wrap') || s).getBoundingClientRect().bottom + scrollY - s.offsetTop }));
    cardTop = card && m !== 'off' ? card.getBoundingClientRect().top + scrollY : geo[R].top + 0.3 * H;
    if (cardCv && m !== 'off') {
      const r = cardCv.getBoundingClientRect(), w = Math.round(r.width * dpr), h = Math.round(r.height * dpr);
      if (w && (cardCv.width !== w || cardCv.height !== h)) { cardCv.width = w; cardCv.height = h; drawCard(); }
    }
    if (cellEls) layoutCells();
    dirty = true; needPump = true; kick();
  }
  function position(y) {   // 0 … R: run index + its progress
    let p = 0;
    const sb = stage ? stage.top + stage.h : 0;   // phone: a run plays once its copy has passed under the stage and ends as
    for (let k = 0; k < R; k++) {                 // the next section reaches the stage's foot
      const a = stage ? geo[k].top + geo[k].cont - sb + 0.02 * H : geo[k].top + Math.max(k ? HOLD * H : HOLD0 * H, geo[k].h - READ * H);
      const b = stage ? geo[k + 1].top - sb : k === R - 1 ? cardTop - LAND0 * H : geo[k + 1].top - END * H;
      if (y >= a) p = k + Math.min(1, (y - a) / Math.max(1, b - a));
    }
    return p;
  }

  // ---- exosome cells: [sprite, x, y (screen heights from the vanishing point), depth, size, front layer, drift in depth, spin]
  const FIELD = [
    [0, -0.42, -0.30, 3.0, 0.26, 0, 0, 30], [1, 0.16, 0.36, 3.9, 0.22, 0, 0, -40], [2, -0.78, 0.16, 4.6, 0.36, 0, 0, 25],
    [3, 0.06, -0.42, 2.6, 0.24, 0, 4.0, -20],   // these two recede as the page scrolls
    [5, 0.22, -0.16, 3.4, 0.18, 0, 2.2, -30],
    [4, -0.24, 0.10, 6.6, 0.30, 0, 0, 35], [6, -0.62, -0.10, 7.4, 0.28, 0, 0, 20], [7, 0.18, 0.52, 5.4, 0.20, 0, 0, -25],
    [8, -0.40, 0.34, 2.5, 0.30, 1, 0, 40], [9, -0.36, -0.44, 3.2, 0.24, 1, 0, -35], [2, 0.40, 0.46, 3.9, 0.20, 1, 0, 30],
    [5, -0.62, 0.04, 4.6, 0.34, 1, 0, -20],
    // PDRN molecules ('m' + index into MOLS) among the cells, smaller and mostly far
    ['m0', -0.56, -0.40, 4.2, 0.20, 0, 0, 18], ['m1', 0.12, 0.24, 5.8, 0.17, 0, 0, -22], ['m2', -0.30, 0.50, 3.6, 0.15, 1, 0, 26],
    ['m3', -0.88, -0.02, 6.2, 0.21, 0, 1.5, -15]];
  const VP = [0.26, 0.52], ZC = 4.2, FAR = 9, FRONT_IN = [1.9, 2.7];
  const HERO = [[2, [0.12, 0.25, 0.40, 0.85]]];   // [screen, viewport box]: no near cell over the S3 ampoules
  let cellEls = null, cellsOn = false;
  function buildCells() {
    if (cellEls || !SPRITES.length || mode === 'off' || saveData || stage || !(o.cellLayers && o.cellLayers[0] && o.cellLayers[1])) return;   // phone: no field yet (the stage clips it)
    const layers = o.cellLayers;
    if (plate) plate.style.backgroundImage = `url(${new URL('img/plate.webp', BASE).href})`;
    cellEls = FIELD.filter(f => typeof f[0] === 'number' || MOLS.length).map((f, n) => {
      const id = typeof f[0] === 'number' ? SPRITES[f[0] % SPRITES.length] : MOLS[+f[0].slice(1) % MOLS.length], layer = layers[f[5]];
      const imgs = [0, 1, 2].map(s => { const im = new Image(); im.decoding = 'async'; im.alt = ''; im.src = new URL(`img/cells/${id}-${s}.webp`, BASE).href; layer.appendChild(im); return im; });
      const dust = [0, 1, 2, 3, 4].map(j => { const d = document.createElement('i'); layer.appendChild(d); return { el: d, a: n * 2.4 + j * 1.31, f: 0.35 + ((n * 7 + j * 3) % 5) / 8 }; });
      return { f, imgs, dust, st: ['', '', ''], ph: n * 1.7 };
    });
  }
  function layoutCells() { for (const c of cellEls) c.st = ['', '', '']; }
  const set = (el, o, tf) => { el.style.opacity = o.toFixed(3); el.style.visibility = o > 0.004 ? 'visible' : 'hidden'; if (tf) el.style.transform = tf; };
  function zoneCap(cx, cy, r, b, front) {   // r: the cell's disc (≈ 0.44 of its sprite)
    let c = 1;
    const over = clamp((cx + r - 0.5 * W) / (0.3 * r) + 1);   // 1 once the disc reaches the copy half; only faint bokeh may
    if (over > 0) { const faint = b >= 1.4 ? (front ? 0.2 : 0.35) : 0; c = Math.min(c, 1 - over * (1 - faint)); }
    if (front) for (const [at, bx] of HERO) {
      const w = 1 - smooth(0.5, 0.95, Math.abs(pos - at)); if (w <= 0) continue;
      const dx = Math.max(bx[0] * W - cx, 0, cx - bx[2] * W), dy = Math.max(bx[1] * H - cy, 0, cy - bx[3] * H);
      c = Math.min(c, 1 - w * clamp((r - Math.hypot(dx, dy)) / (0.4 * r)));
    }
    return c;
  }
  function cells(t, y) {   // returns true while the field is on screen (it keeps drifting)
    if (!cellEls) return false;
    const o0 = smooth(0.08, 0.8, pos) * (pos < 3 ? 1 : 0), dis = smooth(2.1, 2.9, pos);
    if (o0 <= 0 || dis >= 1) {
      if (cellsOn) { for (const c of cellEls) { c.imgs.forEach(im => set(im, 0)); c.dust.forEach(d => set(d.el, 0)); c.st = ['', '', '']; } cellsOn = false; }
      return false;
    }
    cellsOn = true;
    const still = calm.matches, c01 = still ? 0.5 : clamp((y - geo[0].top) / Math.max(1, geo[3].top - geo[0].top));
    const zc = c01 * ZC, focus = 3.0 - 0.9 * c01, tt = still ? 0 : t / 1000;
    for (const c of cellEls) {
      const [, x, yw, z, size, front, vz, spin] = c.f, d = z - zc + vz * c01;
      let o = o0 * smooth(0.22, 0.5, d) * (1 - smooth(FAR - 2.5, FAR, d)) * (front ? 1 - smooth(FRONT_IN[0], FRONT_IN[1], d) : 1);
      const k = 1 / Math.max(d, 0.05), D = size * k * H, dx = 0.012 * Math.sin(tt * 0.21 + c.ph), dy = 0.010 * Math.cos(tt * 0.17 + c.ph * 1.3);
      const cx = VP[0] * W + (x + dx) * k * H, cy = VP[1] * H + (yw + dy) * k * H;
      if (d <= 0.2 || cx + D / 2 < 0 || cx - D / 2 > W || cy + D / 2 < 0 || cy - D / 2 > H) o = 0;
      const b = clamp(Math.abs(d - focus) * 0.85, 0, 2);
      if (o > 0) o *= zoneCap(cx, cy, D * 0.44, b, front);
      const oc = o * (1 - dis), tf = o > 0 ? `translate3d(${(cx - 128).toFixed(1)}px,${(cy - 128).toFixed(1)}px,0) scale(${(D / 256).toFixed(4)}) rotate(${(spin * c01 + tt * 2 + c.ph * 40).toFixed(1)}deg)` : '';
      const wts = [clamp(1 - b), clamp(1 - Math.abs(b - 1)), clamp(b - 1)];
      c.imgs.forEach((im, s) => { const v = oc * wts[s], st = v > 0.004 ? v.toFixed(3) + tf : '0'; if (st !== c.st[s]) { set(im, v, v > 0.004 ? tf : ''); c.st[s] = st; } });
      const dO = o * Math.sin(Math.PI * dis) * 0.95;   // R3: the cells give way to gold dust
      for (const p of c.dust) {
        if (dO <= 0.004) { if (p.on) { set(p.el, 0); p.on = false; } continue; }
        const rr = D / 2 * (0.2 + p.f * 1.4 * dis), px = cx + Math.cos(p.a) * rr, py = cy + Math.sin(p.a) * rr - dis * 0.04 * H, sc = 0.6 + D / 260;
        set(p.el, dO * (0.6 + 0.4 * p.f), `translate3d(${(px - 4).toFixed(1)}px,${(py - 4).toFixed(1)}px,0) scale(${sc.toFixed(2)})`); p.on = true;
      }
    }
    return !still;
  }

  function tick(t) {
    raf = 0; if (destroyed) return;
    const y = scrollY;
    if (y !== lastY) { if (lastY >= 0) dir = y > lastY ? 1 : -1; lastY = y; }
    pos = position(y);
    const p = mode === 'keys' ? Math.round(pos) : pos, r = Math.min(R - 1, Math.floor(p)), k = key(r, Math.round((p - r) * (NS[r] - 1)));
    const now = performance.now();
    if (k !== want) { vel = 0.6 * vel + 0.4 * Math.abs(gOf(k) - wantG) * 1000 / Math.max(16, now - wantT); wantT = now; want = k; wantG = gOf(k); needPump = true; }
    else if (now - wantT > 120) vel *= 0.5;   // stopped
    const rate = 2000 / (stats.n ? stats.decode / stats.n : 40), st = Math.max(1, Math.min(6, Math.round(vel / rate)));   // frames the worker decodes per second
    if (st !== stride) { stride = st; needPump = true; }
    if (needPump) pump();
    draw();
    land(y);
    const tf = `translate3d(0, ${(-y * 0.02).toFixed(1)}px, 0)`;
    if (tf !== lastBg) { if (bg) bg.style.transform = tf; if (plate) plate.style.transform = tf; lastBg = tf; }
    const po = cellEls || (stage && SPRITES.length) ? smooth(0.05, 0.85, pos) * (1 - smooth(2.1, 2.9, pos)) : 0;   // phone: the plate without the field
    if (plate && Math.abs(po - lastPlate) > 0.002) { plate.style.opacity = po.toFixed(3); lastPlate = po; }
    if (!cellEls && mode !== 'off' && (pos > 0.01 || shown >= 0)) buildCells();
    if (cells(t, y) && !document.hidden) kick();
    helix();
  }
  // ---- the DNA helix behind S3: fetched only when the story nears S3 on a desktop, eased in and out around it
  const hx = o.helix || null;
  let hxOn = false, lastHx = -1;
  function helix() {
    if (!CFG.helix || !hx || stage || mode === 'off' || saveData || calm.matches) return;
    if (!hxOn) { if (pos < 1.1) return; hx.src = new URL('img/helix.webp', BASE).href; hxOn = true; }
    const o = 0.38 * smooth(1.35, 1.95, pos) * (1 - smooth(2.45, 2.95, pos));
    if (Math.abs(o - lastHx) < 0.002) return;
    lastHx = o; hx.style.opacity = o.toFixed(3); hx.style.visibility = o > 0.004 ? 'visible' : 'hidden';
    hx.style.transform = `translate3d(0, ${((2 - pos) * 6).toFixed(2)}vh, 0)`;
  }
  function kick() { if (!raf && !destroyed) raf = requestAnimationFrame(tick); }
  function land(y) {   // the card rises: the 3D kit flies from its place in the frame into the card's picture, then hands over
    const l = clamp((LAND0 * H - (cardTop - y)) / ((LAND0 - LAND1) * H)), e = l * l * (3 - 2 * l);
    const swap = smooth(0.88, 1, l), op = mode === 'off' ? 0 : mode === 'keys' ? 1 - l : 1 - swap;
    if (stage) {   // phone: no flight; the offer section pushes the stage (smoke, plate, 3D) up and away, the card shows the kit
      push = clamp(stage.top + stage.h - (geo[R].top - y), 0, stage.top + stage.h + 40);
      if (push !== lastPush) { root.style.setProperty('--push', push.toFixed(1)); lastPush = push; }
      const B = shownBox, tfp = B ? `translate3d(${B.x.toFixed(2)}px,${(B.y - push).toFixed(2)}px,0)` : '', o = mode === 'off' || push >= stage.top + stage.h + 40 ? 0 : 1;
      if (tfp !== lastTf) { canvas.style.transform = tfp; canvas.style.zIndex = ''; lastTf = tfp; }
      if (o !== lastOp) { canvas.style.opacity = String(o); canvas.style.visibility = o > 0 ? '' : 'hidden'; lastOp = o; }
      if (cardCv && mode !== 'off') cardCv.style.opacity = '1';
      return;
    }
    const B = shownBox; let tf = B ? `translate3d(${B.x.toFixed(2)}px,${B.y.toFixed(2)}px,0)` : '', fly = false;
    if (mode === 'full' && l > 0 && op > 0 && shown === KIT && kitCrop && cardCv && B) {
      const [sx, sy, sw, sh] = kitCrop.r, fx = B.w / kitCrop.w, fy = B.h / kitCrop.h, k = { x: sx * fx, y: sy * fy, w: sw * fx };   // the kit in the canvas
      const c = cardCv.getBoundingClientRect(), s = Math.min(c.width / sw, c.height / sh);
      const T = { x: c.left + (c.width - sw * s) / 2, y: c.top + (c.height - sh * s) / 2, w: sw * s };   // where the card draws it
      const sc = 1 + (T.w / k.w - 1) * e, X = B.x + k.x + (T.x - B.x - k.x) * e, Y = B.y + k.y + (T.y - B.y - k.y) * e;
      tf = `translate3d(${(X - k.x * sc).toFixed(2)}px,${(Y - k.y * sc).toFixed(2)}px,0) scale(${sc.toFixed(5)})`; fly = true;
    }
    if (tf !== lastTf) { canvas.style.transform = tf; canvas.style.zIndex = fly ? '3' : ''; lastTf = tf; }   // above the card while it flies
    if (op !== lastOp) { canvas.style.opacity = String(op); canvas.style.visibility = op > 0 ? '' : 'hidden'; lastOp = op; }
    if (cardCv && mode !== 'off') cardCv.style.opacity = String(mode === 'keys' ? l : swap);
  }

  const onVisibility = () => {   // hidden: keep only the frame on screen
    if (document.hidden) {
      for (const [k, e] of bm) if (k !== shown) { release(e); bm.delete(k); }
      for (const id of [...pending.keys()]) cancel(id); flight.clear(); warmFlight.clear();
    } else { needPump = true; kick(); }
  };
  const ro = window.ResizeObserver ? new ResizeObserver(() => measure()) : null;
  document.addEventListener('visibilitychange', onVisibility);
  addEventListener('scroll', kick, { passive: true });
  addEventListener('resize', measure);
  phone.addEventListener('change', measure); calm.addEventListener('change', measure);
  if (ro) ro.observe(o.observe || secs[0].parentElement);
  addEventListener('load', measure);
  measure();

  function destroy() {   // unmount: every listener, the worker, the decoded frames and the cells it added; the page's
    if (destroyed) return; // own elements stay (React may mount again on them, as StrictMode does in development)
    destroyed = true; if (raf) cancelAnimationFrame(raf); raf = 0;
    document.removeEventListener('visibilitychange', onVisibility);
    removeEventListener('scroll', kick); removeEventListener('resize', measure); removeEventListener('load', measure);
    phone.removeEventListener('change', measure); calm.removeEventListener('change', measure);
    if (ro) ro.disconnect();
    for (const id of [...pending.keys()]) cancel(id); flight.clear(); warmFlight.clear();
    if (worker) { worker.terminate(); worker = null; }
    if (workerUrl) URL.revokeObjectURL(workerUrl);
    for (const e of bm.values()) release(e); bm.clear(); shown = -1; kitCrop = null;
    if (cellEls) for (const c of cellEls) { c.imgs.forEach(im => im.remove()); c.dust.forEach(d => d.el.remove()); }
    cellEls = null;
    root.classList.remove('story'); for (const v of ['--stage-top', '--stage-h', '--push']) root.style.removeProperty(v);
  }
  function state() {   // for QA and debugging
    let bytes = 0; for (const e of bm.values()) bytes += e.bytes;
    return { run: rOf(want), want: iOf(want), g: rOf(want) + iOf(want) / (NS[rOf(want)] - 1), shown: shown < 0 ? null : [rOf(shown), iOf(shown)],
      decoded: bm.size, decodedBytes: bytes, inflight: flight.size + warmFlight.size, misses, N: NS[rOf(want)], Ns: NS, R,
      opacity: +canvas.style.opacity, tier, mode, worker: !!worker, win: BACK + AHEAD + 1, keys: (mode === 'full' ? ENDS : SCREENS).length,
      peak: Object.assign({}, peak), warmed: warmed.size, fetchMs: stats.n ? +(stats.fetch / stats.n).toFixed(1) : 0,
      decodeMs: stats.n ? +(stats.decode / stats.n).toFixed(1) : 0, maxDecodeMs: +stats.maxDecode.toFixed(1), missing: missing.size, pos,
      cells: cellEls ? cellEls.length : 0, cellsVisible: cellEls ? cellEls.filter(c => c.imgs.some(im => im.style.visibility === 'visible')).length : 0,
      card: card ? card.className : '', destroyed };
  }
  return { measure, destroy, state };
}
