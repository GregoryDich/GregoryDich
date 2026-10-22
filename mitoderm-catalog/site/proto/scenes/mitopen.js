// MITOPEN live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D scene,
// as the approved sample EXOTECH GEL (scenes/exotech-gel.js). The engine keeps the story geometry (the cover-fitted
// 16:10 frame, the run's box, the phone stage, the kit card); this module draws the pose for the story position into
// the box, objects placed by frame pixel (2400×1500). The only packshot (protocols/print/img/mitopen.webp, 273×891) is
// far too small to show, so the pen is a model built from its measurements (scratchpad spec of 22/10): a lathe of the
// silhouette (its axis 12.49° from vertical, seen from 11° right of the button and 9° below the axis), the rose-gold
// ring with 15 almond scallops, the button and the dark dot above it, the engraved V, two milled flats on the nose, the
// clear cartridge with the champagne hub, the needle plate (the needles themselves are not drawn: story3d) and the print
// «MITOPEN» typeset (design/mitopen/make_textures.py). Nothing moves on the pen: the ring does not turn, the button and
// the dot do not light, the needles do not come out, the cartridge stays on — only what the photo shows.
// The product keeps its own colours (pipetted on the packshot: champagne metal #b8af95, never the line's #d8c48a; rose
// gold #d8bba6 / #dcb49c; white print #f3f2ea), lit by a neutral studio like the packshot's; the camera rolls with the
// pen, so the studio's light keeps its place on the pen in every pose. The DEVICES line's silver (#d9d4cc) and champagne
// (#d8c48a) live only round it: the microchannel dots (S3, S5), a soft silver glow behind the pen (live only).
// Story (story3d S1–S7, as the template places it: the scene left, the copy right): S1 the packshot's pose; S2 the pen
// stands upright; S3 the grid of microchannels thickens in five steps under its tip; S4 the working tilt, quiet; S5 three
// even passes over the plane leave the grid, V-TECH SYSTEM (right) and EXOSIGNAL HAIR (left) rise as their packshots, a
// clear drop falls into the grid and a wave lights it; S6–S7 the pen lies across, its print upright (the kit card).
// Left out (spec §6): the zone outlines (people), the depth scale and the speed dial (numbers: the scene draws no text
// but the pen's own print), the procedure photo, a pedestal (not in the kit), any mechanism.
//
// createScene(THREE, { canvas, base, onLoad }) → { draw(p, view), kit(view) → canvas, animated, state(), dispose() }
//   p: the story position 0…5 (run index + progress); view: { cover, box, dpr, t, still } from the engine
//   (qa: { pose: [cx, cy, Lp, roll, az, el], mask } — measuring only: one fixed pose, no graphics; mask: flat white)
export function createScene(THREE, { canvas, base, onLoad, qa = null }) {
  const V3 = THREE.Vector3, rad = THREE.MathUtils.degToRad, deg = THREE.MathUtils.radToDeg;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  const lerp = (a, b, s) => a + (b - a) * s;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  const scene = new THREE.Scene();

  // ---- the camera: a long lens, as the packshot's (its rings open 7° at the cartridge and 11° at the cone: ±2° round
  // the 9° in the middle, the pen seen from 13.5 lengths away on S1; FOV 7°), level, its principal point at the packshot pose's centre (frame 708, 750) by a lens shift (the
  // MITOSCAN page's camera: the full image is wider than the cover, the cover offset in it), so the pen on S1 is seen
  // on axis as photographed; elsewhere the pen turns to the ray that sees it. The camera rolls about its axis with the
  // pen's roll in the picture: the pen itself stays upright in the studio, so its light never moves on it.
  // `lay`: the same camera without the engine's box, for placing by frame pixel
  const FOV = 7, DIST = 40, PPX = 708, FW = 2 * (2400 - PPX), OFF = FW / 2 - PPX;
  const camera = new THREE.PerspectiveCamera(FOV, FW / 1500, 1, 120); camera.position.set(0, 0, DIST);
  const lay = new THREE.PerspectiveCamera(FOV, FW / 1500, 1, 120); lay.position.copy(camera.position);
  lay.setViewOffset(FW, 1500, OFF, 0, 2400, 1500);
  const ZAX = new V3(0, 0, 1), TAN = Math.tan(rad(FOV / 2)), KPX = 750 / TAN;   // a world unit at depth D spans KPX / D frame px
  function roll(phi) {   // phi°, clockwise on screen
    camera.quaternion.setFromAxisAngle(ZAX, rad(phi)); lay.quaternion.copy(camera.quaternion);
    camera.updateMatrixWorld(); lay.updateMatrixWorld();
  }
  roll(0);
  const ray = new V3();
  function at(cx, cy, depth, out) {   // the point seen at frame pixel (cx, cy), `depth` in front of the camera
    ray.set(cx / 1200 - 1, 1 - cy / 750, 0.5).unproject(lay).sub(lay.position).normalize();
    return out.copy(lay.position).addScaledVector(ray, depth / -ray.z);
  }
  const world = (px, depth) => px * depth / KPX;   // frame pixels → world units at that depth
  const fp = new V3();
  const toFrame = (v, out) => { fp.copy(v).project(lay); out[0] = (fp.x + 1) * 1200; out[1] = (1 - fp.y) * 750; return out; };

  // ---- light: the packshot's studio for the pen (PMREM; no lamps), fitted on the packshot's pose so its bands come back:
  // the body reflects the room at twice its own angle, so its lit left third (#e4ddc3) is a bright left wall (−32…−118°
  // from the camera), its middle (#aba48b) the dim wall behind the camera, its shadow side (#958e77) a darker right, its
  // light right edge a rim behind right; above, a soft ceiling (the cone's upper side). Neutral white throughout.
  // The cartridge has its own room, as the HAIR ampoules: clear over what is inside it, bright at its edges and highlights
  const ENV = { right: 0.33, front: 0.2, left: 0.92, rim: 0.6, back: 0.25, up: 0.8, down: 0.18 };
  const plateau = (v, a, b, s) => smooth(a - s, a + s, v) * (1 - smooth(b - s, b + s, v));
  function makeEnv(glass) {
    const pm = new THREE.PMREMGenerator(renderer), room = new THREE.Scene();
    const dome = new THREE.SphereGeometry(30, 96, 48), col = [], c = new THREE.Color(), q = dome.attributes.position;
    for (let i = 0; i < q.count; i++) {
      const x = q.getX(i) / 30, y = q.getY(i) / 30, z = q.getZ(i) / 30;   // the camera looks from +z
      let v;
      if (glass) v = 0.05 + 0.18 * Math.exp(-(y * y) / 0.06);
      else {
        const az = deg(Math.atan2(x, z)), el = deg(Math.asin(clamp(y, -1, 1)));   // az 0: behind the camera, −90: left
        const band = plateau(el, -25, 55, 12);
        v = ENV.right + band * (ENV.front * plateau(az, -32, 22, 6) + ENV.left * plateau(az, -118, -32, 7) + ENV.rim * plateau(az, 125, 168, 10)
          + ENV.back * (plateau(az, -200, -118, 10) + plateau(az, 168, 200, 10)));
        v = lerp(v, el > 0 ? ENV.up : ENV.down, el > 0 ? smooth(45, 70, el) : smooth(-20, -50, el));
      }
      c.setRGB(v, v, v); col.push(c.r, c.g, c.b);
    }
    dome.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    room.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const panel = (i, x, y, z, w, h, ty = y) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(i, i, i), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, ty, 0); room.add(m);
    };
    if (glass) {
      panel(0.4, 0, 1, 12, 24, 12);                  // a broad dim wall behind the camera
      panel(2.5, -9, 1.5, -7, 2.5, 9); panel(2, 9, 2, -7, 2.5, 9);   // rims from behind
      panel(2.2, -7.7, 1, 6.4, 1.2, 12);             // a tall strip left of the camera: the clear tube's long highlight
    }
    const rt = pm.fromScene(room, 0.02); pm.dispose();
    room.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    return rt;   // its target: disposing that frees the framebuffer too
  }
  let roomEnv = makeEnv(false), glassEnvRT = makeEnv(true);
  scene.environment = roomEnv.texture;
  const glassMats = [];
  // after a lost context three.js restores image textures, not the rendered environments: rebuild them, and have the
  // engine redraw (the kit picture too), also under reduced motion
  const restored = () => {
    const old = [roomEnv, glassEnvRT];
    roomEnv = makeEnv(false); glassEnvRT = makeEnv(true); scene.environment = roomEnv.texture;
    for (const m of glassMats) m.envMap = glassEnvRT.texture;
    old.forEach(t => t.dispose()); size = '';
    version++; if (onLoad) onLoad();
  };
  canvas.addEventListener('webglcontextrestored', restored);

  // ---- textures: the typeset print, the V's relief, the two partners' packshots (S5)
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy();
  const tex = (name, srgb) => {
    const t = new THREE.TextureLoader().load(new URL(`img/mitopen-3d/${name}`, base).href, () => {
      t.needsUpdate = true; if (++loaded === 4) { version++; if (onLoad) onLoad(); }
    });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const printTex = tex('print.png'), vTex = tex('vmark.png'), vtechTex = tex('vtech-system.webp', true), hairTex = tex('exosignal-hair.webp', true);

  // ---- the pen's measurements (packshot px; u along the axis from the silhouette's top, the top end's plane at u 4.3,
  // the cartridge's end at 902; r the radius). World: the pen 1 long (908.9 px true length), its axis +y, the button's
  // meridian (α 0) toward +z, α + toward +x (the right flat, the photo's right)
  // Along the axis the photo is a perspective view (the top end 1.2 % farther than the bottom): a plane measured at u
  // stands where this camera, in the packshot's pose, shows it at u (the model's middle ≈ 2.6 px lower than linear)
  const PXW = 908.9, KAX = 1 / Math.cos(rad(9));
  const PB = Math.sin(rad(9)) / (KPX * Math.cos(rad(9)) / 897.7), pj = s => s / (1 + s * PB);
  const Y = u => { const P = lerp(pj(0.5), pj(-0.5), (u - 4.3) / 897.7); return P / (1 - P * PB); }, YT = Y(4.3), YB = Y(902);
  function pchip(P) {   // a monotone cubic through the points: smooth, no overshoot
    const n = P.length, x = P.map(p => p[0]), y = P.map(p => p[1]), h = [], d = [], m = [];
    for (let i = 0; i < n - 1; i++) { h[i] = x[i + 1] - x[i]; d[i] = (y[i + 1] - y[i]) / h[i]; }
    m[0] = d[0]; m[n - 1] = d[n - 2];
    for (let i = 1; i < n - 1; i++) {
      if (d[i - 1] * d[i] <= 0) m[i] = 0;
      else { const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1]; m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]); }
    }
    return u => {
      if (u <= x[0]) return y[0]; if (u >= x[n - 1]) return y[n - 1];
      let lo = 0, hi = n - 1; while (hi - lo > 1) { const md = (lo + hi) >> 1; if (x[md] <= u) lo = md; else hi = md; }
      const t = (u - x[lo]) / h[lo], t2 = t * t, t3 = t2 * t;
      return (2 * t3 - 3 * t2 + 1) * y[lo] + (t3 - 2 * t2 + t) * h[lo] * m[lo] + (-2 * t3 + 3 * t2) * y[lo + 1] + (t3 - t2) * h[lo] * m[lo + 1];
    };
  }
  // the silhouette: cone (straight, fitted), its sharp rim, the undercut, a groove, a band; the body fitted with two
  // cubics (rms 0.22 px); the ring's envelope over its ridges; the nose (fitted), its neck and collar
  const R = pchip([[4.3, 22.6], [4.5, 24.1], [5.0, 25.2], [5.8, 26.2], [9, 28.35], [20, 34.35], [30, 39.8], [40, 45.25], [50, 50.7], [57, 54.5],
    [60, 56.2], [63, 57.9], [66, 59.3], [68, 59.8], [70, 59.4], [72, 57.9], [74, 55.8], [76, 53.3], [78, 50.1], [80, 48.1], [82, 48.1], [84, 49.7],
    [86, 50.3], [91, 50.3], [94, 49.8], [98, 49.01], [104, 48.09], [110, 47.09], [116, 46.05], [122, 44.98], [128, 43.92], [134, 42.88],
    [140, 41.89], [146, 40.97], [152, 40.15], [158, 39.44], [164, 38.88], [170, 38.49], [176, 38.29], [182, 38.3], [188, 38.56], [194, 39.14],
    [200, 39.86], [206, 40.48], [212, 41.09], [218, 41.7], [224, 42.32], [230, 42.93], [236, 43.53], [242, 44.14], [248, 44.75], [254, 45.35],
    [260, 45.95], [266, 46.55], [272, 47.15], [278, 47.74], [284, 48.33], [290, 48.93], [296, 49.52], [302, 50.11], [308, 50.69], [314, 51.28],
    [320, 51.86], [326, 52.44], [332, 53.02], [338, 53.6], [344, 54.18], [350, 54.75], [356, 55.32], [362, 55.89], [368, 56.46], [374, 57.03],
    [380, 57.6], [386, 58.16], [392, 58.72], [398, 59.28], [404, 59.84], [410, 60.4], [416, 60.95], [422, 61.51], [428, 62.06], [434, 62.61],
    [440, 63.15], [446, 63.7], [452, 64.25], [458, 64.79], [464, 65.33], [470, 65.87], [476, 66.41], [482, 66.94], [488, 67.47], [494, 68.01],
    [500, 68.54], [506, 69.07], [510, 69.3], [514, 69.65], [520, 70.2], [524, 70.7], [526, 70.3], [530, 68.5], [540, 64.5], [550, 61.4], [560, 60.0],
    [567, 58.9], [591, 58.9], [594, 57.3], [600, 55.8], [603, 54.3], [606, 52.8], [609, 50.1], [612, 49.67], [620, 48.32], [640, 45.04],
    [660, 41.92], [680, 38.95], [700, 36.12], [705, 36.0], [710, 36.2], [716, 36.9], [720, 37.4], [724, 38.5], [726, 38.85], [729, 38.85],
    [732, 37.9], [735, 36.4], [738, 35.4], [741, 34.8], [745, 33.6]]);
  const dR = u => (R(u + 0.2) - R(u - 0.2)) / 0.4;
  const RING = [510, 606], NOSE = [606, 745];
  // the ring: 15 scallops, 24° apart, a scallop's centre on the button's meridian (its ridges at ±12° + 24°k): long
  // circular-cut grooves with pointed (gothic) ends, nearly the full pitch wide, the ridges between them narrow
  const SC0 = 525, SC1 = 591, SW_A = 11.2, SRHO = 1.7, SEDGE = rad(40);
  function scallopW(u, r) {   // the scallop's half width (px of arc) at u: straight in the middle, a pointed arch at each end
    const W = rad(SW_A) * r, rho = SRHO * W, Le = Math.sqrt(rho * rho - (rho - W) ** 2), y = Math.max(0, Le - Math.min(u - SC0, SC1 - u));
    return y >= Le ? 0 : Math.sqrt(rho * rho - y * y) - (rho - W);
  }
  function ringR(u, a) {
    const e = R(u); if (u <= SC0 || u >= SC1) return e;
    const w = scallopW(u, e); if (w <= 0) return e;
    let da = ((a % 24) + 24) % 24; if (da > 12) da -= 24;
    const x = Math.abs(rad(da) * e / w), rc = w / Math.sin(SEDGE);   // a circular cut: its walls meet the envelope at
    // SEDGE, ≈ 4.4 px deep where widest; past its edge the wall's tangent, so a soft fillet (0.6 px) rounds each ridge
    // (the photo's ridges catch the light)
    const d = x < 1 ? Math.sqrt(rc * rc - x * x * w * w) - rc * Math.cos(SEDGE) : -(x - 1) * w * Math.tan(SEDGE);
    return e - 0.6 * Math.log1p(Math.exp(d / 0.6)) * smooth(0, 0.3, w / (rad(SW_A) * e));
  }
  // the nose: two milled flats at α ±53°, inclined to the axis (their distance from it d(u) = 40.2 − 0.2 (u − 650)),
  // each ending in a rounded wall (a semicircle of the flat's half-width) at u 610 and 711
  const FL = [53, -53], FU0 = 610, FU1 = 711, dF = u => 40.2 - 0.2 * (u - 650), wF = u => Math.sqrt(Math.max(0, R(u) ** 2 - dF(u) ** 2));
  const capR = (u0, s) => { let r = 10; for (let i = 0; i < 20; i++) r = wF(u0 + s * r); return r; };
  const RT = capR(FU0, 1), RB = capR(FU1, -1), CT = FU0 + RT, CB = FU1 - RB;
  function noseR(u, a) {
    let r = R(u);
    if (u < FU0 - 1 || u > FU1 + 1) return r;
    for (const f of FL) {
      let da = a - f; da = ((da + 540) % 360) - 180; if (Math.abs(da) > 70) continue;
      const c = Math.cos(rad(da)), d = dF(u), rf = d / c; if (rf >= r) continue;
      const w = d * Math.tan(rad(da));   // across the flat, px
      let m = 1;
      if (u < CT) m = smooth(RT + 0.6, RT - 0.6, Math.hypot(u - CT, w));
      else if (u > CB) m = smooth(RB + 0.6, RB - 0.6, Math.hypot(u - CB, w));
      r = lerp(r, rf, m);
    }
    return r;
  }
  // a surface of revolution r(u, α) on a grid (rows u, columns α in degrees, closed): positions in the pen's space,
  // normals from the surface's own derivatives (crisp scallop ridges and flat edges)
  function surface(us, as, rf) {
    const nu = us.length, na = as.length, pos = new Float32Array(nu * na * 3), nor = new Float32Array(nu * na * 3), idx = [];
    for (let j = 0; j < nu; j++) for (let i = 0; i < na; i++) {
      const u = us[j], a = as[i], ar = rad(a), s = Math.sin(ar), c = Math.cos(ar), r = rf(u, a);
      const ru = (rf(u + 0.15, a) - rf(u - 0.15, a)) / 0.3, ra = (rf(u, a + 0.08) - rf(u, a - 0.08)) / rad(0.16);
      const ux = ru * s, uy = -KAX, uz = ru * c, ax = ra * s + r * c, az = ra * c - r * s;
      let nx = uy * az, ny = uz * ax - ux * az, nz = -uy * ax; const l = Math.hypot(nx, ny, nz) || 1;
      const k = (j * na + i) * 3;
      pos[k] = r * s / PXW; pos[k + 1] = Y(u); pos[k + 2] = r * c / PXW; nor[k] = nx / l; nor[k + 1] = ny / l; nor[k + 2] = nz / l;
    }
    for (let j = 0; j < nu - 1; j++) for (let i = 0; i < na - 1; i++) {
      const A = j * na + i, B = A + 1, C = A + na, D = C + 1; idx.push(A, C, B, B, C, D);
    }
    const g = new THREE.BufferGeometry(); g.setIndex(idx);
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
    return g;
  }
  const range = (a, b, st) => { const o = []; for (let v = a; v < b - 1e-6; v += st) o.push(v); o.push(b); return o; };
  // a patch on the body (a decal): u0…u1, α from aw(u) = [lo, hi], `off` px above the surface, uv(u, α) → [x, y]
  function patch(u0, u1, nu, aw, na, off, uv) {
    const pos = [], nor = [], uvs = [], idx = [];
    for (let j = 0; j <= nu; j++) {
      const u = lerp(u0, u1, j / nu), [lo, hi] = aw(u), r = R(u) + off, ru = dR(u), nl = Math.hypot(ru, KAX);
      for (let i = 0; i <= na; i++) {
        const a = lerp(lo, hi, i / na), ar = rad(a), s = Math.sin(ar), c = Math.cos(ar);
        pos.push(r * s / PXW, Y(u), r * c / PXW); nor.push(KAX * s / nl, ru / nl, KAX * c / nl); uvs.push(...uv(u, a));
        if (i < na && j < nu) { const A = j * (na + 1) + i, B = A + 1, C = A + na + 1, D = C + 1; idx.push(A, C, B, B, C, D); }
      }
    }
    const g = new THREE.BufferGeometry(); g.setIndex(idx);
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    return g;
  }
  // a small round mark lying on the body at (u, α), radius rr px (true size), `off` px above it
  function dot(u0, a0, rr, off, r0 = 0) {   // r0 > 0: a ring from r0 to rr
    const pos = [], nor = [], idx = [], NR = 6, NT = 40;
    const put = (b, s) => {   // b along the axis (true px, + toward the cone), s along the arc
      const u = u0 - b / KAX, r = R(u) + off, a = rad(a0) + s / r, ru = dR(u), nl = Math.hypot(ru, KAX);
      pos.push(r * Math.sin(a) / PXW, Y(u), r * Math.cos(a) / PXW); nor.push(KAX * Math.sin(a) / nl, ru / nl, KAX * Math.cos(a) / nl);
    };
    put(0, 0);
    for (let k = 1; k <= NR; k++) for (let i = 0; i < NT; i++) { const t = 2 * Math.PI * i / NT, q = r0 ? lerp(r0, rr, (k - 1) / (NR - 1)) : rr * k / NR; put(q * Math.sin(t), q * Math.cos(t)); }
    if (!r0) for (let i = 0; i < NT; i++) idx.push(0, 1 + i, 1 + (i + 1) % NT);
    for (let k = 1; k < NR; k++) for (let i = 0; i < NT; i++) {
      const A = 1 + (k - 1) * NT + i, B = 1 + (k - 1) * NT + (i + 1) % NT, C = A + NT, D = B + NT; idx.push(A, C, B, B, C, D);
    }
    const g = new THREE.BufferGeometry(); g.setIndex(idx);
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    return g;
  }
  const lathe = (pts, seg) => new THREE.LatheGeometry(pts.map(([r, u]) => new THREE.Vector2(r / PXW, Y(u))), seg);

  // ---- materials. The metal and the rose gold: satin metals (roughness ≈ 0.3, as the photo's soft band) whose F0 and a
  // small emissive floor were fitted so that the packshot pose shows the packshot's colours (lit band, middle, shadow);
  // not tone mapped. The print: emissive 0.85 of its colour plus a neutral shading, not tone mapped (the 14/10 rule)
  const SW = { uSweepY: { value: 9 }, uSweepA: { value: 0 }, uRingFlash: { value: 0 } };   // the light sweep (S1, S3, S7)
  function penPatch(m, kind) {
    m.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, SW);
      sh.vertexShader = 'varying float vPenY;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vPenY = position.y;');
      let f = 'uniform float uSweepY, uSweepA, uRingFlash; varying float vPenY;\n' + sh.fragmentShader;
      if (kind === 'v') f = f.replace('#include <alphamap_fragment>', '#include <alphamap_fragment>\n  float cav = texture2D( alphaMap, vAlphaMapUv ).b;\n  diffuseColor.rgb *= 1.0 - 0.55 * cav;');
      f = f.replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n  { float q = (vPenY - uSweepY) / 0.03; totalEmissiveRadiance += vec3(uSweepA * exp(-q * q)); }'
        + (kind === 'ring' ? '\n  totalEmissiveRadiance *= 1.0 + uRingFlash;' : '') + (kind === 'v' ? '\n  totalEmissiveRadiance *= 1.0 - 0.55 * cav;' : ''));
      sh.fragmentShader = f;
    };
    m.customProgramCacheKey = () => 'mitopen-' + kind;
    return m;
  }
  const MET = { color: 0xd4ccb1, emissive: 0x4a4639, roughness: 0.3 };
  const metal = penPatch(new THREE.MeshPhysicalMaterial({ color: MET.color, metalness: 1, roughness: MET.roughness, emissive: MET.emissive, toneMapped: false }), 'metal');
  const ringMat = penPatch(new THREE.MeshPhysicalMaterial({ color: 0xe6bfa6, metalness: 1, roughness: 0.24, emissive: 0x140e0a, toneMapped: false }), 'ring');
  const buttonMat = penPatch(new THREE.MeshPhysicalMaterial({ color: 0xe6cbb7, metalness: 1, roughness: 0.25, emissive: 0x8e7764, toneMapped: false }), 'button');
  const dotMat = new THREE.MeshPhysicalMaterial({ color: 0x6c6f69, roughness: 0.15, clearcoat: 1, clearcoatRoughness: 0.05, toneMapped: false, polygonOffset: true, polygonOffsetFactor: -2 });
  const gapMat = new THREE.MeshStandardMaterial({ color: 0x47443b, roughness: 0.6, toneMapped: false, polygonOffset: true, polygonOffsetFactor: -2 });
  const markMat = new THREE.MeshStandardMaterial({ color: 0x3a3a36, roughness: 0.8, toneMapped: false, polygonOffset: true, polygonOffsetFactor: -2 });
  const plateMat = new THREE.MeshPhysicalMaterial({ color: 0xc9c6b8, metalness: 1, roughness: 0.35, emissive: 0x3a3934, toneMapped: false });
  const SHADE = 0.2;
  const printMat = penPatch(new THREE.MeshPhysicalMaterial({ color: new THREE.Color(0xf3f2ea).multiplyScalar(SHADE), emissive: 0xf3f2ea, emissiveIntensity: 0.85,
    roughness: 0.7, specularIntensity: 0.3, toneMapped: false, alphaMap: printTex, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 }), 'print');
  const vMat = penPatch(new THREE.MeshPhysicalMaterial({ color: MET.color, metalness: 1, roughness: MET.roughness, emissive: MET.emissive, toneMapped: false,
    bumpMap: vTex, bumpScale: 0.0006, alphaMap: vTex, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 }), 'v');
  // glass: no transmission (on a transparent canvas it cannot see the page's smoke, and a phone pays a pass for it): its
  // opacity follows Fresnel and its own highlights (as the HAIR ampoules)
  function glassMat(side, a0, aF, aS) {
    const m = new THREE.MeshPhysicalMaterial({ color: 0x0b0b0c, roughness: 0.04, ior: 1.5, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.6,
      envMap: glassEnvRT.texture, transparent: true, depthWrite: false, side });
    const k = [a0, aF, aS].map(v => v.toFixed(3));
    m.onBeforeCompile = sh => {
      sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float F = pow(1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0), 5.0);
        vec3 sp = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
        #ifdef USE_CLEARCOAT
        sp += (clearcoatSpecularDirect + clearcoatSpecularIndirect) * material.clearcoat;
        #endif
        gl_FragColor.a = clamp(${k[0]} + ${k[1]} * F + dot(sp, vec3(0.2126, 0.7152, 0.0722)) * ${k[2]}, 0.0, 1.0) * opacity; }`);
    };
    m.customProgramCacheKey = () => 'glass' + k.join() + side;
    glassMats.push(m); return m;
  }
  const glassBack = glassMat(THREE.BackSide, 0.02, 0.3, 0.7), glassFront = glassMat(THREE.FrontSide, 0.03, 0.5, 1.0);
  const stemMat = glassMat(THREE.DoubleSide, 0.02, 0.35, 0.6), dropMat = glassMat(THREE.FrontSide, 0.05, 0.6, 1.0);

  // ---- the pen
  const pen = new THREE.Group(); scene.add(pen);
  const add = (g, m, order = 0) => { const x = new THREE.Mesh(g, m); x.renderOrder = order; pen.add(x); return x; };
  {   // the body from the top end to the ring: a lathe, dense where the profile turns
    const us = [4.5, 5.0, 5.8].concat(range(6.5, 100, 0.5), range(101.5, 510, 3));
    add(lathe(us.slice().reverse().map(u => [R(u), u]).concat([[22.6, 4.3], [0, 4.3]]), 128), metal);
  }
  add(surface(range(RING[0], RING[1], 1), range(0, 360, 0.6), ringR), ringMat);
  {   // the nose: dense columns round the two flats
    const as = [];
    for (let a = -180; a < 180 - 1e-6;) { as.push(a); const f = Math.min(Math.abs(Math.abs(a) - 53), 99); a += f < 36 ? 0.5 : 2; }
    as.push(180);
    add(surface(range(NOSE[0], NOSE[1], 1), as, noseR), metal);
    const end = new THREE.RingGeometry(23 / PXW, R(NOSE[1]) / PXW, 96).rotateX(Math.PI / 2).translate(0, Y(NOSE[1]), 0);
    add(end, metal);   // the nose's end round the hub (seen through the cartridge)
  }
  // the button: a disc Ø 28 px standing 1.5 px proud, a 2 px chamfer (its dark rim), on the button's meridian at u 167
  {
    const u = 167, r = R(u), n = new V3(0, dR(u), KAX).normalize();
    const g = new THREE.LatheGeometry([[14, -4], [14, 0], [13.6, 0.5], [12.6, 1.3], [12, 1.5], [0, 1.5]].map(([x, y]) => new THREE.Vector2(x / PXW, y / PXW)), 64);
    g.applyMatrix4(new THREE.Matrix4().compose(new V3(0, Y(u), r / PXW), new THREE.Quaternion().setFromUnitVectors(new V3(0, 1, 0), n), new V3(1, 1, 1)));
    add(g, buttonMat);
    add(dot(u, 0, 15.0, 0.06, 13.9), gapMat, 1);   // the hairline gap round it
  }
  add(dot(135.5, 0, 5.5, 0.12), dotMat, 1);        // the dark dot above it (glass, flush; it does not light)
  add(dot(741, 0, 0.8, 0.1), markMat, 1);          // a tiny mark on the nose's collar, on the same meridian
  // the print: x along the axis (u 432 → 286), y across (arc −13.7 … +13.7 px round its centre line α 7.35°)
  const PU0 = 432, PU1 = 286, PS0 = -13.7, PS1 = 13.7, PAC = 7.35;
  add(patch(PU1, PU0, 146, u => [PAC + deg(PS0 / R(u)), PAC + deg(PS1 / R(u))], 24, 0.15,
    (u, a) => [(PU0 - u) / (PU0 - PU1), 1 - (rad(a - PAC) * R(u) - PS0) / (PS1 - PS0)]), printMat, 20);
  // the engraved V: α −22…+18°, u 78…122
  add(patch(78, 122, 88, () => [-22, 18], 80, 0.1, (u, a) => [(a + 22) / 40, 1 - (u - 78) / 44]), vMat, 20);
  // the cartridge: a clear tube (its wall, the flange with its snaps left smooth, the open end), inside it the hub of
  // the pen (champagne metal; a flat window on its front left, a small boss on its right), two faint rings of the
  // stem, the needle plate with its ribbed edge. The needles are not drawn (story3d: not readable on the packshot)
  {
    const tube = lathe([[30.2, 745], [30.2, 901.2], [30.7, 902], [31.3, 902], [31.8, 901.2], [31.8, 791], [33, 789.8], [33, 771.8], [31.5, 770.5],
      [31.5, 750.5], [32.4, 747.5], [33, 745.5], [30.2, 745]], 96);
    add(tube, glassBack, 10); add(tube, glassFront, 12);
    const hubR = (u, a) => {
      let r = 24 - 1.4 * smooth(751.2, 752.4, u) * (1 - smooth(755.6, 756.8, u));
      let da = ((a + 14 + 540) % 360) - 180;
      if (Math.abs(da) < 60) { const m = smooth(743, 744, u) * (1 - smooth(759, 760, u)); r = Math.min(r, lerp(r, 20.5 / Math.cos(rad(da)), m)); }
      return r;
    };
    add(surface(range(744, 770, 0.5), range(-180, 180, 1.5), hubR), metal);
    add(new THREE.CircleGeometry(24 / PXW, 64).rotateX(Math.PI / 2).translate(0, Y(770), 0), metal);
    const boss = new THREE.SphereGeometry(2.6 / PXW, 16, 12), ab = rad(63);
    boss.translate(Math.sin(ab) * 23.6 / PXW, Y(751), Math.cos(ab) * 23.6 / PXW); add(boss, metal);
    for (const u of [795, 835]) add(new THREE.CylinderGeometry(18 / PXW, 18 / PXW, 2.5 / PXW, 64, 1, true).translate(0, Y(u), 0), stemMat, 11);
    const rib = [];
    for (let u = 843.5; u <= 866.501; u += 0.5) rib.push([21.3 + 0.8 * Math.abs(Math.sin(Math.PI * (u - 843) / 3)), u]);
    add(lathe([[0, 867], [21.3, 867]].concat(rib.reverse()).concat([[21.3, 843], [0, 843]]), 64), plateMat);
  }

  // ---- the line's graphics, flat to the camera in frame pixels (a plane at a depth; local x = px − 1200, y = 750 − py)
  const pxU = { value: 1 };   // device px per frame px
  const plane = () => { const g = new THREE.Group(); scene.add(g); return g; };
  const place = (g, D) => { at(1200, 750, D, g.position); g.quaternion.copy(lay.quaternion); g.scale.setScalar(world(1, D)); };
  const hex3 = h => new V3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  const SPOT_F = `uniform vec3 uC; uniform float uOpacity; varying vec2 vUv;
    void main() { vec2 q = vUv * 2.0 - 1.0; float r2 = dot(q, q); gl_FragColor = vec4(uC, uOpacity * exp(-3.0 * r2) * (1.0 - smoothstep(0.5, 1.0, r2))); }`;
  const spotMat = c => new THREE.ShaderMaterial({ vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: SPOT_F, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, uniforms: { uC: { value: hex3(c) }, uOpacity: { value: 0 } } });
  const spot = (parent, c, cx, cy, rx, ry, order) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), spotMat(c)); m.position.set(cx - 1200, 750 - cy, 0); m.scale.set(rx, ry, 1); m.renderOrder = order; parent.add(m); return m; };
  const SILVER = 0xd9d4cc, CHAMP = 0xd8c48a;

  // the microchannels: one instanced quad, all motion in the vertex shader. S3: 17×8 every 24 px, shown by a 4×4 Bayer
  // threshold as the density steps 1 → 5 (b2.line: five speeds). S5: 14×6 every 28 px, each dot born as the tip passes it
  // (three even passes, right to left, left to right, right to left), then the delivery wave from where the drop lands
  const D_DOT = 34, dp = plane();
  const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
  const PASS = [[0.25, 870, 490, 788], [0.43, 490, 870, 844], [0.61, 870, 490, 900]], PD = 0.14, TURN = 0.04, DROP = [682, 844];
  const DOTS = [];
  for (let j = 0; j < 8; j++) for (let i = 0; i < 17; i++) DOTS.push([500 + 24 * i, 1000 + 24 * j, (BAYER[(j % 4) * 4 + i % 4] + 0.5) / 16, 0, 0, 0]);
  for (let j = 0; j < 6; j++) for (let i = 0; i < 14; i++) {
    const x = 500 + 28 * i, y = 774 + 28 * j, [f0, xa, xb] = PASS[j >> 1];
    DOTS.push([x, y, 0, f0 + PD * (x - xa) / (xb - xa), 1, Math.hypot(x - DROP[0], y - DROP[1])]);
  }
  const dg = new THREE.InstancedBufferGeometry();
  dg.setIndex([0, 1, 2, 0, 2, 3]); dg.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
  dg.setAttribute('aP', new THREE.InstancedBufferAttribute(new Float32Array(DOTS.flatMap(d => d.slice(0, 2))), 2));
  dg.setAttribute('aT', new THREE.InstancedBufferAttribute(new Float32Array(DOTS.flatMap(d => d.slice(2))), 4));
  dg.instanceCount = DOTS.length;
  const DU = { uD: { value: 0 }, uA3: { value: 0 }, uY3: { value: 0 }, uF5: { value: 0 }, uA5: { value: 0 }, uY5: { value: 0 }, uWave: { value: -1e4 },
    uTime: { value: 0 }, uShim: { value: 0 }, uPx: pxU, uS: { value: hex3(SILVER) }, uC: { value: hex3(CHAMP) } };
  const dotsMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: DU,
    vertexShader: `attribute vec2 aP; attribute vec4 aT; uniform float uD, uA3, uY3, uF5, uA5, uY5, uWave, uTime, uShim, uPx;
      varying vec2 vQ; varying float vA, vFl, vR;
      void main() {
        vec2 c = aP; float g, fl, a;
        if (aT.z < 0.5) {   // S3: shown once the density passes its threshold; a slow diagonal shimmer while held
          g = clamp((uD - aT.x) / 0.04, 0.0, 1.0); fl = g * (1.0 - clamp((uD - aT.x - 0.04) / 0.1, 0.0, 1.0));
          a = uA3 * (1.0 + uShim * 0.14 * sin((aP.x + aP.y) * 0.02 - uTime * 2.094)); c.y += uY3;
        } else {            // S5: born as the tip passes; lit again as the delivery wave goes over it
          g = clamp((uF5 - aT.y) / 0.02, 0.0, 1.0); fl = g * (1.0 - clamp((uF5 - aT.y - 0.02) / 0.05, 0.0, 1.0));
          float w = (uWave - aT.w) / 26.0; fl = max(fl, g * exp(-w * w)); a = uA5; c.y += uY5;
        }
        vR = 3.5 * (0.35 + 0.65 * g); vA = a * step(0.001, g); vFl = fl;
        float h = vR + 1.5 / max(uPx, 0.3); vQ = position.xy * h;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(c.x - 1200.0 + vQ.x, 750.0 - c.y + vQ.y, 0.0, 1.0);
      }`,
    fragmentShader: `uniform float uPx; uniform vec3 uS, uC; varying vec2 vQ; varying float vA, vFl, vR;
      void main() {
        float e = 0.75 / max(uPx, 0.3), d = length(vQ), m = 1.0 - smoothstep(vR - e, vR + e, d);
        gl_FragColor = vec4(mix(uS, uC, vFl), m * vA * (0.7 + 0.3 * vFl));
      }` });
  const dotsMesh = new THREE.Mesh(dg, dotsMat); dotsMesh.frustumCulled = false; dotsMesh.renderOrder = 3; dp.add(dotsMesh);
  const haze3 = spot(dp, SILVER, 692, 1084, 230, 120, 2), haze5 = spot(dp, SILVER, 682, 844, 220, 110, 2);   // faint silver under the dots
  // the partners (S5): their packshots as they are (no dimming, no tint), rising; V-TECH SYSTEM right, EXOSIGNAL HAIR left
  const D_PART = 31, pp = plane();
  const board = (map, h, aspect, cx, by) => {
    const w = h * aspect, m = new THREE.Mesh(new THREE.PlaneGeometry(w, h).translate(0, h / 2, 0), new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false, toneMapped: false }));
    m.userData = { x: cx - 1200, y: 750 - by }; m.renderOrder = 4; pp.add(m); return m;
  };
  const vtech = board(vtechTex, 270, 1047 / 960, 1030, 960), hair = board(hairTex, 200, 1087 / 714, 330, 960);
  // the drop (S5): clear, no colour, falls into the grid's middle and is gone as it lands
  const drop = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), dropMat); drop.renderOrder = 5; scene.add(drop);
  // the glow behind the pen (live only, never in a key or the kit picture): the line's silver
  const gp = plane(), glow = spot(gp, SILVER, 0, 0, 1, 1, 1);

  // ---- poses: [cx, cy, Lp (px between the ends' centres), roll° (clockwise), az° (the camera's angle from the button's
  // meridian), el° (the camera below the axis)]; within what was photographed: az −4…+26° with the sway, el 9°
  const POSE = [[708, 750, 820, 12.5, 11, 9], [860, 740, 840, 0, 0, 9], [960, 690, 720, 8, 6, 9], [720, 740, 780, 35, 0, 9],
    [674, 662, 480, 40, 6, 9], [708, 750, 900, 78, 0, 9]];
  const fromTip = (x, y, Lp, r, az = 3, el = 9) => [x + 0.5 * Lp * Math.sin(rad(r)), y - 0.5 * Lp * Math.cos(rad(r)), Lp, r, az, el];
  const mixP = (a, b, s, o) => { for (let i = 0; i < 6; i++) o[i] = lerp(a[i], b[i], s); return o; };
  const PASS_IN = fromTip(PASS[0][1], PASS[0][3], 480, 30), PASS_OUT = fromTip(PASS[2][2], PASS[2][3], 480, 30);
  function tipAt(f, out) {   // the tip over the grid: three even passes, a short arc at each turn
    for (let k = 0; k < 3; k++) {
      const [f0, xa, xb, y] = PASS[k];
      if (f <= f0 + PD || k === 2) { const s = clamp((f - f0) / PD); out[0] = lerp(xa, xb, s); out[1] = y; return out; }
      if (f < f0 + PD + TURN) { const s = (f - f0 - PD) / TURN; out[0] = xb + Math.sign(xb - xa) * 28 * Math.sin(Math.PI * s); out[1] = y + 28 * (1 - Math.cos(Math.PI * s)); return out; }
    }
    return out;
  }
  const SWAY = [1, 1, 0.6, 0.25, 0.5, 1], GLOW = [0.3, 0.35, 0.25, 0.18, 0.25, 0.4];
  const ST = { pose: [0, 0, 0, 0, 0, 0], sway: 0, glow: 0, glowOff: 0, D: 1, a3: 0, y3: 0, f5: 0, a5: 0, y5: 0, wave: -1e4, vtech: 0, vtechY: 0, hair: 0, hairY: 0, drop: 0, dropY: 0, shim: 0 };
  const tip = [0, 0];
  function story(p) {   // the state at story position p
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST, P = st.pose;
    st.D = 1; st.a3 = st.y3 = st.f5 = st.a5 = st.y5 = st.vtech = st.vtechY = st.hair = st.hairY = st.drop = st.glowOff = 0; st.wave = -1e4;
    st.sway = lerp(SWAY[k], SWAY[k + 1], smooth(0, 1, f));
    if (k === 0) {   // S1 → S2: the pen stands upright; the glow sinks toward the cartridge («the smoke thickens at the tip»)
      mixP(POSE[0], POSE[1], smooth(0, 0.85, f), P);
      st.glow = lerp(GLOW[0], GLOW[1], smooth(0, 1, f)); st.glowOff = 260 * smooth(0.3, 1, f);
    } else if (k === 1) {   // S2 → S3: the grid comes under the tip and thickens in five steps
      mixP(POSE[1], POSE[2], smooth(0.05, 0.6, f), P);
      st.glow = lerp(GLOW[1], GLOW[2], smooth(0, 0.6, f)); st.glowOff = 260 * (1 - smooth(0.05, 0.6, f));
      st.a3 = smooth(0.35, 0.5, f); st.D = 1; for (let i = 0; i < 4; i++) st.D += smooth(0.45 + 0.1 * i, 0.5 + 0.1 * i, f);
    } else if (k === 2) {   // S3 → S4: the grid sinks into the smoke and dissolves; the working tilt, quiet
      mixP(POSE[2], POSE[3], smooth(0.2, 0.9, f), P);
      st.glow = lerp(GLOW[2], GLOW[3], smooth(0.2, 0.9, f)); st.D = 5;
      st.a3 = 1 - smooth(0.05, 0.45, f); st.y3 = 120 * smooth(0, 0.45, f);
    } else if (k === 3) {   // S4 → S5: over the plane, three passes leave the grid; the partners rise; the drop, the wave
      if (f < 0.25) mixP(POSE[3], PASS_IN, smooth(0, 0.25, f), P);
      else if (f < 0.75) { tipAt(f, tip); const q = fromTip(tip[0], tip[1], 480, 30); for (let i = 0; i < 6; i++) P[i] = q[i]; }
      else mixP(PASS_OUT, POSE[4], smooth(0.75, 0.9, f), P);
      st.sway *= 1 - smooth(0.15, 0.25, f) * (1 - smooth(0.75, 0.9, f));
      st.glow = lerp(GLOW[3], GLOW[4], smooth(0.75, 0.95, f));
      st.f5 = f; st.a5 = smooth(0.2, 0.3, f);
      st.vtech = smooth(0.7, 0.9, f); st.vtechY = -60 * (1 - st.vtech); st.hair = smooth(0.76, 0.96, f); st.hairY = -60 * (1 - st.hair);
      st.drop = f > 0.8 && f < 0.88 ? smooth(0.8, 0.815, f) : 0; st.dropY = 690 + (DROP[1] - 690) * ((f - 0.8) / 0.08) ** 2;
      if (f > 0.86) st.wave = (f - 0.86) / 0.14 * 280;
    } else {   // S5 → kit: the grid and the partners go down into the smoke; the pen lies across, its print upright
      const out = 1 - smooth(0, 0.3, f);
      mixP(POSE[4], POSE[5], smooth(0.1, 0.7, f), P);
      st.glow = lerp(GLOW[4], GLOW[5], smooth(0.5, 0.9, f));
      st.f5 = 1; st.a5 = out; st.y5 = 80 * (1 - out); st.vtech = st.hair = out; st.vtechY = st.hairY = 80 * (1 - out);
    }
    return st;
  }

  // ---- applying a state
  const camPos = new V3(), qRay = new THREE.Quaternion(), qTilt = new THREE.Quaternion(), qAz = new THREE.Quaternion(), XAX = new V3(1, 0, 0), YAX = new V3(0, 1, 0), MZ = new V3(0, 0, -1);
  const vT = new V3(0, YT, 0), vB = new V3(0, YB, 0), w1 = new V3(), w2 = new V3(), f1 = [0, 0], f2 = [0, 0];
  const last = { pen: null, probes: null, dots: 0, level: 1, vtech: 0, hair: 0, sweep: 0, glow: 0 };
  function placePen(cx, cy, Lp, phi, az, el) {
    roll(phi); camPos.copy(camera.position);
    qTilt.setFromAxisAngle(XAX, -rad(el)); qAz.setFromAxisAngle(YAX, -rad(az));
    let D = KPX * Math.cos(rad(el)) / Lp, tx = cx, ty = cy;
    for (let it = 0; it < 4; it++) {   // the ends' centres land on their pixels: place, project, correct
      at(tx, ty, D, pen.position);
      ray.copy(pen.position).sub(camPos).normalize(); qRay.setFromUnitVectors(MZ, ray);
      pen.quaternion.copy(qRay).multiply(qTilt).multiply(qAz); pen.updateMatrixWorld();
      toFrame(w1.copy(vT).applyMatrix4(pen.matrixWorld), f1); toFrame(w2.copy(vB).applyMatrix4(pen.matrixWorld), f2);
      tx += cx - (f1[0] + f2[0]) / 2; ty += cy - (f1[1] + f2[1]) / 2; D *= Math.hypot(f1[0] - f2[0], f1[1] - f2[1]) / Lp;
    }
    return D;
  }
  const pw = new V3(), pr2 = [0, 0];
  const probe = (u, a, off) => { const r = R(u) + off, ar = rad(a); pw.set(r * Math.sin(ar) / PXW, Y(u), r * Math.cos(ar) / PXW).applyMatrix4(pen.matrixWorld); toFrame(pw, pr2); return [Math.round(pr2[0] * 10) / 10, Math.round(pr2[1] * 10) / 10]; };
  function pose(p, t, still) {
    const st = story(p), live = still ? 0 : 1 - smooth(4.85, 5, p), P = st.pose;
    const sw = qa ? 0 : st.sway * live;
    const q = qa ? qa.pose : P;
    const az = q[4] + 4 * Math.sin(t * 0.45) * sw, phi = q[3] + 0.8 * Math.sin(t * 0.37 + 1) * sw, cy = q[1] - 3 * Math.sin(t * 0.8) * sw;
    const D = placePen(q[0], cy, q[2], phi, az, q[5]);
    const g = qa ? null : st;
    // the sweep: a soft white band runs down the body from the cone to the cartridge, every 6.5 s (S1–S3, S7); on S1 the
    // ring flashes as it passes
    const act = still || qa ? 0 : clamp(1 - smooth(2.2, 2.4, p) + smooth(4.5, 4.7, p));
    const tt = t % 6.5, sy = 0.55 - tt;
    SW.uSweepY.value = sy; SW.uSweepA.value = tt < 1.1 ? 0.3 * act * smooth(0, 0.15, tt) * (1 - smooth(0.95, 1.1, tt)) : 0;
    SW.uRingFlash.value = SW.uSweepA.value > 0 ? 0.35 * Math.exp(-(((sy - Y(558)) / 0.05) ** 2)) * (1 - smooth(0.4, 0.9, p)) : 0;
    // the grid
    place(dp, D_DOT);
    const showDots = g && (g.a3 > 0.004 || g.a5 > 0.004);
    dotsMesh.visible = !!showDots;
    if (g) {
      DU.uD.value = g.D / 5; DU.uA3.value = g.a3; DU.uY3.value = g.y3; DU.uF5.value = g.f5; DU.uA5.value = g.a5; DU.uY5.value = g.y5;
      DU.uTime.value = t; DU.uShim.value = still ? 0 : 1 - smooth(0, 0.05, Math.abs(p - 2));
      let wave = g.wave;
      if (!still && Math.abs(p - 4) < 0.05) wave = Math.max(wave, (t % 5) * 220 - 40);   // held on S5: the delivery again
      DU.uWave.value = wave;
      haze3.material.uniforms.uOpacity.value = 0.08 * g.a3; haze3.position.y = 750 - 1084 - g.y3; haze3.visible = g.a3 > 0.004;
      haze5.material.uniforms.uOpacity.value = 0.08 * g.a5; haze5.position.y = 750 - 844 - g.y5; haze5.visible = g.a5 > 0.004;
      let n = 0;
      for (const d of DOTS) n += d[4] < 0.5 ? (g.a3 > 0.004 && g.D / 5 > d[2] ? 1 : 0) : (g.a5 > 0.004 && g.f5 > d[3] ? 1 : 0);
      last.dots = n; last.level = Math.round(g.D * 100) / 100;
    } else { haze3.visible = haze5.visible = false; last.dots = 0; }
    // the partners
    place(pp, D_PART);
    for (const [m, a, dy] of [[vtech, g ? g.vtech : 0, g ? g.vtechY : 0], [hair, g ? g.hair : 0, g ? g.hairY : 0]]) {
      m.visible = a > 0.004; m.material.opacity = a; m.position.set(m.userData.x, m.userData.y - dy, 0);
    }
    last.vtech = g ? g.vtech : 0; last.hair = g ? g.hair : 0;
    // the drop
    drop.visible = !!g && g.drop > 0.004;
    if (drop.visible) { at(DROP[0], g.dropY, D_DOT - 0.8, drop.position); drop.scale.setScalar(world(13, D_DOT - 0.8)); dropMat.opacity = g.drop; }
    // the glow (live only), along the pen, a little toward the cartridge on S2
    const gl = still || !g ? 0 : g.glow; glow.visible = gl > 0.004;
    if (glow.visible) {
      place(gp, D + 2); const a = rad(phi);
      glow.position.set(q[0] - Math.sin(a) * g.glowOff - 1200, 750 - (q[1] + Math.cos(a) * g.glowOff), 0);
      glow.rotation.z = -a; glow.scale.set(130, 0.31 * q[2], 1); glow.material.uniforms.uOpacity.value = gl;
    }
    last.glow = gl; last.sweep = SW.uSweepA.value;
    // QA: where the pen's ends and the colour probes are in the frame
    const rp = a => Math.round(a * 10) / 10;
    last.pen = { cx: rp(q[0]), cy: rp(cy), Lp: rp(q[2]), roll: rp(phi), az: rp(az), top: [rp(f1[0]), rp(f1[1])], tip: [rp(f2[0]), rp(f2[1])] };
    const ia = PAC, iu = (398.83 + 395.77) / 2, ri = R(iu);
    last.probes = { button: probe(167, 0, 1.5), text: [-7.5, -5, -2.5, 0, 2.5, 5, 7.5].map(s => probe(iu, ia + deg(s / ri), 0.15)),
      body: probe(450, az, 0), ring: probe(560, 12 + 24 * Math.round((az - 12) / 24), 0) };
  }

  // ---- drawing into the engine's box: the full frame is the cover; the canvas shows the box's part of it
  // the density drawn: a phone's stage is small, so it draws at the screen's full density (≤ 3, as the MASK page), a
  // desktop at the engine's (≤ 2); long frames lower it under a cap (pace), which a rotation keeps
  const phone = matchMedia('(max-width: 899px)'), full = view => (phone.matches ? Math.min(3, devicePixelRatio || 1) : view.dpr);
  let cap = Infinity, pr = 0, size = '', renders = 0, lastT = 0, lastP = 0, lastView = null, trial = null, capped = false;
  const LADDER = [2, 1.5, 1.25], win = [];
  function pace(now, still) {   // fewer pixels when frames run long: a 90-frame median over 24 ms tries the next cap that
    if (still || capped) { lastT = now; return; }   // cuts ≥ 20 % of the pixels; the next window keeps it only if frames got
    const dt = lastT ? now - lastT : 0; lastT = now;   // ≥ 20 % shorter; if not, the rate is a cap (low-power 30 Hz), not
    if (!dt || dt > 400) return;   // the GPU: back, no more tries. A gap over 400 ms is a pause (hidden, idle), not a frame
    win.push(dt); if (win.length < 90) return;
    const m = win.slice().sort((a, b) => a - b)[45], mean = win.reduce((a, v) => a + Math.min(v, 100), 0) / win.length; win.length = 0;
    if (trial) { if (mean > trial.mean * 0.8) { cap = trial.cap; capped = true; } trial = null; return; }   // the mean: vsync-
    const next = LADDER.find(q => (q / pr) ** 2 <= 0.8);   // quantised medians would hide a 30 → 18 ms gain
    if (m > 24 && next) { trial = { cap, mean }; cap = next; }
  }
  function fit(view, pr) {   // the engine's box of the cover, through the shifted lens (the cover sits OFF into the full image)
    const id = `${view.box.w}x${view.box.h}@${pr}`;
    if (id !== size) { renderer.setPixelRatio(pr); renderer.setSize(view.box.w, view.box.h, false); size = id; }
    const k = view.cover.w / 2400;
    camera.aspect = FW / 1500;
    camera.setViewOffset(FW * k, 1500 * k, OFF * k + view.box.x - view.cover.x, view.box.y - view.cover.y, view.box.w, view.box.h);
    camera.updateProjectionMatrix();
    pxU.value = pr * k;   // device px per frame px: the dots keep a soft edge of ≥ 1.5 device px
  }
  let maskMat = null;
  function render(p, view) {
    pr = Math.min(full(view), cap); fit(view, pr); pose(p, view.still ? 0 : view.t, view.still);
    if (qa && qa.mask) { maskMat = maskMat || new THREE.MeshBasicMaterial({ color: 0xffffff }); scene.overrideMaterial = maskMat; }
    renderer.render(scene, camera); scene.overrideMaterial = null; renders++;
  }
  function draw(p, view) { pace(performance.now(), view.still); lastP = p; lastView = view; render(p, view); }
  let kits = 0;   // kit pictures rendered (QA: none on a phone, none for a toolbar)
  function kit(view) {   // the kit pose rendered once into a picture (the offer card, the flight into it), then the current pose again
    kits++;
    fit(view, view.dpr); pose(5, 0, true); renderer.render(scene, camera);
    const c = document.createElement('canvas'); c.width = canvas.width; c.height = canvas.height; c.getContext('2d').drawImage(canvas, 0, 0);
    if (lastView) render(lastP, lastView);
    return c;
  }
  function dispose() {
    canvas.removeEventListener('webglcontextrestored', restored);
    const mats = new Set();
    scene.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) mats.add(o.material); });
    for (const m of mats) m.dispose();
    if (maskMat) maskMat.dispose();
    for (const t of [printTex, vTex, vtechTex, hairTex, roomEnv, glassEnvRT]) t.dispose();
    renderer.dispose();
  }
  // compile every program now (nothing visible yet): the first scroll does not stall on a shader
  try { renderer.compile(scene, camera); } catch (e) { /* compiled on first draw instead */ }
  const state = () => ({ quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded,
    version, kits, lastP, pen: last.pen, probes: last.probes, dots: { shown: last.dots, level: last.level }, partners: { vtech: Math.round(last.vtech * 100) / 100, hair: Math.round(last.hair * 100) / 100 },
    sweep: Math.round(last.sweep * 100) / 100, glow: Math.round(last.glow * 100) / 100 });
  return { draw, kit, dispose, state, animated: true };
}
