// three.js for the page map (qa/pagemap.cjs serves this module in place of three.module.min.js): the real three.js
// 0.160 re-exported whole, except WebGLRenderer.render(), which draws nothing. A render through a perspective camera
// records instead, per visible mesh, its world matrix, its material's opacity and kind (the material's program key) and
// the camera's projection, so the probe can project every mesh onto the canvas (window.__geoRead()); a full-screen pass
// (an orthographic camera: the scene's amber glow uA, its edge fades uW/uF/uFe/uE/uR) records its uniforms on the frame
// it follows. A render made from the scene's kit() (the offer card's picture: the same renderer and canvas) is kept
// apart and fills the kit's outline opaque, so the engine's alpha box of that picture (the flight into the card) is the
// kit's. The environment maps (PMREM) are not rendered: nothing reads their pixels here. No GPU work at all: a scroll
// step of the probe costs a layout and a frame, not a software render of seconds.
//
// window.__geo       { renders, envs, kits, main, kit }: counters and the last records (main: the story's frame)
// window.__geoRead(which = 'main') → { n, W, H, pr, cw, ch, glow, fade, items: [[top, key, j, op, flags, x0, y0, x1, y1, d0, d1]] }
//   top: the index of the mesh's top-level object in the scene; key: index into __geoKeys(); j: the mesh's userData.j;
//   op: the material's opacity (1 if not transparent); x0…y1: its projected outline in the canvas's CSS px (support
//   points of its geometry, 256 directions: within about a pixel of its silhouette's box); d0, d1: its nearest and
//   farthest depth in front of the camera; flags: 1 a depth-only proxy (colorWrite off; not listed), 2 fading with a
//   depth-only proxy round it (fades as a solid), 4 partly behind the camera's near plane (outline unbounded), 8 writes
//   no depth (glass, liquid), 16 clipped by a plane (its outline is an upper bound)
// window.__geoKeys() → the material keys by index
import * as T from './three.real.js';
export * from './three.real.js';

const G = { renders: 0, envs: 0, kits: 0, main: null, kit: null };
globalThis.__geo = G;
const KEYS = [], KID = new Map(), MKEY = new WeakMap(), SUP = new WeakMap();
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
function keyOf(m) {
  let id = MKEY.get(m);
  if (id === undefined) {
    let s; try { s = own(m, 'customProgramCacheKey') ? String(m.customProgramCacheKey()) : ''; } catch (e) { s = ''; }
    s = (s || m.name || m.type || 'material').slice(0, 80);
    if (!KID.has(s)) { KID.set(s, KEYS.length); KEYS.push(s); }
    id = KID.get(s); MKEY.set(m, id);
  }
  return id;
}
// the support points of a geometry: for 256 directions round the sphere its vertex farthest along each (the corners of a
// flat face are among them), so a projected outline is that of the geometry's hull within a fraction of a degree
const DIRS = (() => { const n = 256, d = new Float64Array(n * 3);
  for (let k = 0; k < n; k++) { const y = 1 - (2 * k + 1) / n, r = Math.sqrt(1 - y * y), a = k * 2.399963229728653; d[3 * k] = Math.cos(a) * r; d[3 * k + 1] = y; d[3 * k + 2] = Math.sin(a) * r; }
  return d; })();
function support(geo) {
  let s = SUP.get(geo); if (s) return s;
  const pa = geo.attributes.position, n = pa.count, pick = new Set();
  const flat = !pa.isInterleavedBufferAttribute && pa.itemSize === 3 ? pa.array : null;
  const X = i => flat ? flat[3 * i] : pa.getX(i), Y = i => flat ? flat[3 * i + 1] : pa.getY(i), Z = i => flat ? flat[3 * i + 2] : pa.getZ(i);
  for (let k = 0; k < DIRS.length; k += 3) {
    const a = DIRS[k], b = DIRS[k + 1], c = DIRS[k + 2]; let best = -Infinity, bi = 0;
    for (let i = 0; i < n; i++) { const v = X(i) * a + Y(i) * b + Z(i) * c; if (v > best) { best = v; bi = i; } }
    pick.add(bi);
  }
  s = new Float64Array(pick.size * 3); let j = 0;
  for (const i of pick) { s[j++] = X(i); s[j++] = Y(i); s[j++] = Z(i); }
  SUP.set(geo, s); return s;
}
function walk(o, top, rec) {
  if (!o.visible) return;
  if (o.isMesh && o.geometry && o.geometry.attributes && o.geometry.attributes.position) {
    const m = Array.isArray(o.material) ? o.material.find(x => x && x.visible !== false) : o.material;
    if (m && m.visible !== false) rec.items.push({ g: o.geometry, M: o.matrixWorld.clone(), top, op: m.transparent ? m.opacity : 1,
      cw: m.colorWrite !== false, dw: m.depthWrite !== false, key: keyOf(m), j: o.userData && typeof o.userData.j === 'number' ? o.userData.j : -1,
      clip: !!(m.clippingPlanes && m.clippingPlanes.length) });
  }
  const c = o.children; for (let i = 0; i < c.length; i++) walk(c[i], top, rec);
}
function snap(r, scene, camera, kind) {
  if (scene.matrixWorldAutoUpdate !== false) scene.updateMatrixWorld();
  if (camera.parent === null && camera.matrixWorldAutoUpdate !== false) camera.updateMatrixWorld();
  const sz = r.getSize(new T.Vector2());
  const rec = { kind, n: G.renders, t: performance.now(), W: sz.x, H: sz.y, pr: r.getPixelRatio(), cw: r.domElement.width, ch: r.domElement.height,
    near: camera.near, PV: new T.Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse), items: [], glow: 0, fade: null, P: null };
  const ch = scene.children; for (let i = 0; i < ch.length; i++) walk(ch[i], i, rec);
  return rec;
}
const MM = new T.Matrix4();
function project(rec, it) {   // → [x0, y0, x1, y1, d0, d1, near, ax0, ay0, az0, ax1, ay1, az1]
  const s = support(it.g), e = MM.multiplyMatrices(rec.PV, it.M).elements, w = it.M.elements, W = rec.W, H = rec.H;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, d0 = Infinity, d1 = -Infinity, near = 0;
  let a0 = Infinity, b0 = Infinity, c0 = Infinity, a1 = -Infinity, b1 = -Infinity, c1 = -Infinity;
  for (let i = 0; i < s.length; i += 3) {
    const x = s[i], y = s[i + 1], z = s[i + 2];
    const wx = w[0] * x + w[4] * y + w[8] * z + w[12], wy = w[1] * x + w[5] * y + w[9] * z + w[13], wz = w[2] * x + w[6] * y + w[10] * z + w[14];
    if (wx < a0) a0 = wx; if (wx > a1) a1 = wx; if (wy < b0) b0 = wy; if (wy > b1) b1 = wy; if (wz < c0) c0 = wz; if (wz > c1) c1 = wz;
    const cw = e[3] * x + e[7] * y + e[11] * z + e[15];
    if (cw < rec.near) { near = 1; continue; }
    const px = ((e[0] * x + e[4] * y + e[8] * z + e[12]) / cw + 1) / 2 * W, py = (1 - (e[1] * x + e[5] * y + e[9] * z + e[13]) / cw) / 2 * H;
    if (px < x0) x0 = px; if (px > x1) x1 = px; if (py < y0) y0 = py; if (py > y1) y1 = py; if (cw < d0) d0 = cw; if (cw > d1) d1 = cw;
  }
  if (near) { x0 = Math.min(x0, -1e5); y0 = Math.min(y0, -1e5); x1 = Math.max(x1, 1e5); y1 = Math.max(y1, 1e5); d0 = Math.min(d0, 0); }
  return [x0, y0, x1, y1, d0, d1, near, a0, b0, c0, a1, b1, c1];
}
const inside = (a, b) => {   // world box b within box a (a hair of tolerance: a proxy sits a little inside the faces)
  const t = 0.01 * Math.hypot(b[10] - b[7], b[11] - b[8], b[12] - b[9]) + 0.004;
  return a[7] - t <= b[7] && a[8] - t <= b[8] && a[9] - t <= b[9] && b[10] <= a[10] + t && b[11] <= a[11] + t && b[12] <= a[12] + t;
};
function projected(rec) {
  if (!rec.P) rec.P = rec.items.map(it => project(rec, it));
  return rec.P;
}
function fillKit(r, rec) {   // the kit's outline opaque in the canvas, for the drawImage that kit() makes next
  const P = projected(rec); let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  rec.items.forEach((it, i) => { if (!it.cw || it.op < 0.02 || P[i][6]) return; const b = P[i];
    x0 = Math.min(x0, b[0]); y0 = Math.min(y0, b[1]); x1 = Math.max(x1, b[2]); y1 = Math.max(y1, b[3]); });
  if (!(x1 > x0)) return;
  const W = rec.W, H = rec.H, X0 = Math.max(0, Math.floor(x0)), X1 = Math.min(W, Math.ceil(x1)), Y0 = Math.max(0, Math.floor(y0)), Y1 = Math.min(H, Math.ceil(y1));
  if (X1 <= X0 || Y1 <= Y0) return;
  const cc = r.getClearColor(new T.Color()), ca = r.getClearAlpha(), ac = r.autoClear;
  r.setClearColor(0x000000, 0); r.clear(true, true, true);
  r.setScissorTest(true); r.setScissor(X0, H - Y1, X1 - X0, Y1 - Y0); r.setClearColor(0xffffff, 1); r.clear(true, false, false);
  r.setScissorTest(false); r.setClearColor(cc, ca); r.autoClear = ac;
  rec.fill = [X0, Y0, X1, Y1];
}
function record(r, scene, camera) {
  G.renders++;
  if (camera.isOrthographicCamera) {   // a full-screen pass after the frame: the glow, the edge fades
    const m0 = scene.children[0], mat = m0 && m0.material, u = mat && mat.uniforms;
    if (!u || !G.main) return;
    if (u.uW) G.main.fade = { round: /length\s*\(/.test(mat.fragmentShader || ''), w: u.uW.value, f: u.uF ? u.uF.value : 0, fe: u.uFe ? u.uFe.value : 0,
      e: u.uE ? u.uE.value.toArray() : null, r: u.uR ? u.uR.value.toArray() : null, res: u.uRes ? u.uRes.value.toArray() : null };
    else if (u.uA) G.main.glow = u.uA.value;
    return;
  }
  if (!camera.isPerspectiveCamera) return;
  const st = new Error().stack || '';
  if (/_sceneToCubeUV|fromScene|PMREM/.test(st)) { G.envs++; return; }   // an environment map: not drawn
  const kind = /at (?:Object\.)?kit \(/.test(st) ? 'kit' : 'main';
  const rec = snap(r, scene, camera, kind);
  if (kind === 'kit') { G.kits++; G.kit = rec; fillKit(r, rec); } else G.main = rec;
}
export class WebGLRenderer extends T.WebGLRenderer {
  constructor(p) { super(p); this.render = (scene, camera) => record(this, scene, camera); }
}
const r1 = v => Math.round(v * 10) / 10, r3 = v => Math.round(v * 1000) / 1000;
globalThis.__geoKeys = () => KEYS.slice();
globalThis.__geoRead = (which = 'main') => {
  const rec = G[which]; if (!rec) return null;
  const P = projected(rec), prox = [], items = [];
  rec.items.forEach((it, i) => { if (!it.cw) prox.push(P[i]); });
  rec.items.forEach((it, i) => {
    if (!it.cw) return;
    const b = P[i]; let fl = 0;
    if (it.op > 0.004 && it.op < 0.999 && prox.some(a => inside(a, b))) fl |= 2;
    if (b[6]) fl |= 4; if (!it.dw) fl |= 8; if (it.clip) fl |= 16;
    items.push([it.top, it.key, it.j, r3(it.op), fl, r1(b[0]), r1(b[1]), r1(b[2]), r1(b[3]), r3(b[4]), r3(b[5])]);
  });
  const f = rec.fade;
  return { kind: rec.kind, n: rec.n, t: Math.round(rec.t), W: r1(rec.W), H: r1(rec.H), pr: rec.pr, cw: rec.cw, ch: rec.ch, glow: r3(rec.glow),
    fade: f ? { round: f.round, w: r3(f.w), f: r3(f.f), fe: r3(f.fe), e: f.e && f.e.map(r3), r: f.r && f.r.map(r1), res: f.res } : null,
    fill: rec.fill || null, items, proxies: prox.length };
};
