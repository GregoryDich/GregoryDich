// MITOSCAN live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D scene,
// as the approved sample EXOTECH GEL (scenes/exotech-gel.js) and the DEVICES page before it (scenes/mitopen.js, whose
// neutral studio, lens-shifted camera, pace, fit, restore and dispose this module follows). The engine keeps the story
// geometry (the cover-fitted 16:10 frame, the run's box, the phone stage, the kit card); this module draws the pose
// for the story position into the box, objects placed by frame pixel (2400×1500).
// The system is modelled from the largest packshot (protocols/print/img/mitoscan.webp, 1145×777; scratchpad spec of
// 22/10): its camera was reconstructed from the glass's vanishing points (f 3210 px, the photo seen from 26.4° right of
// the screen's normal and 7.5° above, 3.86 glass widths away), and every part is placed in the system's own frame S
// (glass widths, gw: the glass centre at the origin, X along the tablet's bottom edge, Y up from the table, Z toward
// the viewer): the tablet (glass 1.000 × 0.6285, leaning back 25.56°, a white rim and body 0.030 thick) on its white
// stand, the probe in its cradle on the tablet's right (a moulded shell, its front crowned below the black panel, two
// chrome buttons on its left, a dark one on its right, the ribbed tail; the cradle's rounded lips over its edges), its
// cable led down from the tail into the top of three stacked loops on the table and back to the stand's base, and the
// brushed aluminium cylinder in front (0.975 long, Ø 0.168, the chrome cap, the short chrome collar narrowing to the
// perforated end, the chrome-framed badge).
// Nothing moves on the system: the probe stays in its cradle and in the picture on every screen, the screen keeps its
// photographed print (the target, «Mitoscan», «By Mitoderm Ltd»), no part is lifted or opened. Only the camera moves
// (within what was photographed: az ≤ 26.4°, the probe's left side never shows, el ≤ 9°); the tablet with its stand and
// the cylinder fade out and in as one body (a depth pre-pass: a fading part never shows its own back or what it
// hides), and only while all of it is inside the scene box (a part never slides across the box's edge while seen);
// the cable fades the same way.
// The print is typeset (design/mitoscan/make_textures.py) and lit as print: emissive ≈ 85 % + a neutral shading, not
// tone mapped; the screen is light (100 %). The white plastics, the aluminium and the chrome keep the packshot's
// neutral tones in a neutral white studio (MITOPEN's). The line's silver (#d9d4cc) lives only round the system: a soft
// shapeless glow behind it (live only) and the silver haze of S2, where the tablet was.
// Left out (spec §6 and the owner's rule of 22/10, «only what exists», stronger than the story spec): the ring of
// clarity, the blue glow round the screen, the callout lines, ×50 / ×200 pictures and any screen UI, people, the
// handset lifted or turned, an exploded view.
//
// createScene(THREE, { canvas, base, onLoad }) → { draw(p, view), kit(view) → canvas, animated, state(), dispose() }
//   p: the story position 0…5 (run index + progress); view: { cover, box, dpr, t, still } from the engine
//   (qa: { pose: [Gx, Gy, S, az, el], mask, lean, dz } — measuring only: one fixed pose, no glow; mask: flat white)
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

  // ---- the camera: the packshot's own (focal 2504 frame px = 3210 photo px × 0.78; FOV 33.4°), its principal point
  // where the photo's centre lands in the frame (687, 750), by a lens shift: the full image is wider than the cover, the
  // cover offset in it (as MITOPEN's). It stays at the origin looking down −z; the system turns to the ray that sees it
  const F = 2503.7, PPX = 686.55, FW = 2 * (2400 - PPX), OFF = FW / 2 - PPX;
  const camera = new THREE.PerspectiveCamera(deg(2 * Math.atan(750 / F)), FW / 1500, 0.05, 60);
  const toFrame = (v, o) => { o[0] = PPX + F * v.x / -v.z; o[1] = 750 - F * v.y / -v.z; return o; };

  // ---- light: MITOPEN's studio (PMREM, no lamps), neutral white throughout: a soft ceiling, a dim wall behind the
  // camera, a leaning softbox on the left, a rim behind right, a light floor in front. The DEVICES pages share it
  const ENV = { base: 0.27, front: 0.26, left: 1.25, rim: 0.5, back: 0.15, up: 0.8, down: 0.18, floor: 0.4 };
  const plateau = (v, a, b, s) => smooth(a - s, a + s, v) * (1 - smooth(b - s, b + s, v));
  function makeEnv() {
    const pm = new THREE.PMREMGenerator(renderer), room = new THREE.Scene();
    const dome = new THREE.SphereGeometry(30, 96, 48), col = [], c = new THREE.Color(), q = dome.attributes.position;
    for (let i = 0; i < q.count; i++) {
      const x = q.getX(i) / 30, y = q.getY(i) / 30, z = q.getZ(i) / 30;   // the camera looks from +z
      const az = deg(Math.atan2(x, z)), el = deg(Math.asin(clamp(y, -1, 1)));   // az 0: behind the camera, −90: left
      const band = plateau(el, -25, 55, 12), sx = az + 55 + 0.46 * (el - 20);
      let v = ENV.base + band * (ENV.front * plateau(az, -32, 8, 8) + ENV.left * smooth(-29, -15, sx) * (1 - smooth(22, 38, sx))
        + ENV.back * (plateau(az, -200, -122, 10) + plateau(az, 168, 200, 10))) + ENV.rim * plateau(az, 70, 110, 10) * plateau(el, 0, 55, 10);
      v = lerp(v, el > 0 ? ENV.up * (1 - 0.35 * smooth(10, 80, az)) : ENV.down + ENV.floor * plateau(az, -35, 35, 15), el > 0 ? smooth(45, 70, el) : smooth(-20, -50, el));
      c.setRGB(v, v, v); col.push(c.r, c.g, c.b);
    }
    dome.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    room.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const rt = pm.fromScene(room, 0.02); pm.dispose();
    room.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    return rt;
  }
  // the cylinder's metals see the same neutral studio with the packshot's contrast, fitted on its pose (the aluminium's
  // bands at x 450: highlight at 0.15–0.25 of its height, dark at 0.5, light at 0.65–0.8, dark at the bottom edge; the
  // reflections there come from the front left, 50–90° from the camera): a bright ceiling, a darker band at the table's
  // horizon, a light floor, darker below behind; behind the camera a dark wall (the chrome's black facets)
  const lin = (T, x) => { if (x <= T[0][0]) return T[0][1]; for (let i = 1; i < T.length; i++) if (x <= T[i][0]) return lerp(T[i - 1][1], T[i][1], (x - T[i - 1][0]) / (T[i][0] - T[i - 1][0])); return T[T.length - 1][1]; };
  const METAL_EL = [[-90, 0.5], [-60, 0.95], [-45, 1.0], [-27, 1.0], [-13, 0.72], [2, 0.4], [17, 0.6], [33, 0.95], [48, 1.45], [65, 1.6], [90, 1.3]];
  function makeMetalEnv() {
    const pm = new THREE.PMREMGenerator(renderer), room = new THREE.Scene();
    const dome = new THREE.SphereGeometry(30, 96, 48), col = [], c = new THREE.Color(), q = dome.attributes.position;
    for (let i = 0; i < q.count; i++) {
      const x = q.getX(i) / 30, y = q.getY(i) / 30, z = q.getZ(i) / 30;
      const az = Math.abs(deg(Math.atan2(x, z))), el = deg(Math.asin(clamp(y, -1, 1)));
      let v = lin(METAL_EL, el);
      v *= lerp(1, 0.4 + 0.6 * smooth(15, 35, az), plateau(el, -35, 40, 10));     // the dimmer wall behind the camera
      v *= 1 - 0.65 * smooth(-25, -40, el) * smooth(95, 130, az);              // darker below, behind the system
      v *= lerp(1, 0.06, plateau(el, -25, 25, 10) * smooth(70, 100, az));   // dark sides and back at eye level (the chrome's black)
      c.setRGB(v, v, v); col.push(c.r, c.g, c.b);
    }
    dome.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    room.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const rt = pm.fromScene(room, 0.02); pm.dispose();
    room.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    return rt;
  }
  let roomEnv = makeEnv(), metalEnv = makeMetalEnv();
  scene.environment = roomEnv.texture;
  const metals = [];   // materials that reflect the metal studio (set below)
  const restored = () => {   // a lost context: three.js restores image textures, not the rendered environment
    const old = [roomEnv, metalEnv]; roomEnv = makeEnv(); metalEnv = makeMetalEnv(); scene.environment = roomEnv.texture;
    for (const m of metals) { m.envMap = metalEnv.texture; m.needsUpdate = true; }
    for (const o of old) o.dispose(); size = '';
    version++; if (onLoad) onLoad();
  };
  canvas.addEventListener('webglcontextrestored', restored);

  // ---- textures (design/mitoscan/make_textures.py)
  let loaded = 0, version = 0;
  const ANISO = renderer.capabilities.getMaxAnisotropy();
  const tex = (name, srgb) => {
    const t = new THREE.TextureLoader().load(new URL(`img/mitoscan-3d/${name}`, base).href, () => {
      t.needsUpdate = true; if (++loaded === 5) { version++; if (onLoad) onLoad(); }
    });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const glassTex = tex('glass.png', true), panelTex = tex('panel.png', true), badgeTex = tex('badge.png', true);
  const grilleTex = tex('grille.png', true), hazeTex = tex('haze.png');

  // ---- materials, one set per layer that fades on its own: S the system's body (the tablet, its stand, the bracket to
  // the cradle, the cylinder and the stand's base behind it), H the probe in its cradle (never faded), K the cable.
  // Every surface fades out over the last 60 frame px before the canvas's edge (the scene box): a part passing it is
  // never cut hard (the glow and the haze too)
  const EDGE = { uRes: { value: new THREE.Vector2(1, 1) }, uFade: { value: 60 } };
  const EDGE_F = 'uniform vec2 uRes; uniform float uFade; float edgeFade() { vec2 q = gl_FragCoord.xy; float e = min(min(q.x, uRes.x - q.x), min(q.y, uRes.y - q.y)); return smoothstep(0.12 * uFade, uFade, e); }';
  const edgy = (m, key = 'plain') => {
    const prev = m.onBeforeCompile;
    m.onBeforeCompile = (sh, r) => {
      prev.call(m, sh, r); Object.assign(sh.uniforms, EDGE);
      sh.fragmentShader = sh.fragmentShader.replace('void main() {', EDGE_F + '\nvoid main() {').replace('#include <opaque_fragment>', '#include <opaque_fragment>\n  gl_FragColor.a *= edgeFade();');
    };
    m.customProgramCacheKey = () => 'mitoscan-' + key; return m;
  };
  const groups = { S: [], H: [], K: [] }, layerOf = new Map();
  const reg = (g, m, key) => { m.transparent = true; groups[g].push(m); layerOf.set(m, g); return edgy(m, key); };
  // white plastic: the packshot's neutral greys hold in every pose (a fitted emissive floor, not tone mapped)
  const PLASTIC = { color: 0x8e8e8c, emissive: 0x9d9d9c, roughness: 0.42, clearcoat: 0.3, clearcoatRoughness: 0.28 };
  const plastic = (g, k = 1, key) => reg(g, new THREE.MeshPhysicalMaterial({ ...PLASTIC, color: new THREE.Color(PLASTIC.color).multiplyScalar(k),
    emissive: new THREE.Color(PLASTIC.emissive).multiplyScalar(k), toneMapped: false }), key);
  // the moulded probe and cradle: the same plastic, darkened by a vertex colour where one part shades the other (the
  // gap under the cradle's lips, its parting groove): the photo's dark seams, no drawn line
  const shaded = (g, k) => {
    const m = plastic(g, k, 'shaded'); m.vertexColors = true;
    const prev = m.onBeforeCompile;
    m.onBeforeCompile = (sh, r) => { prev.call(m, sh, r); sh.fragmentShader = sh.fragmentShader.replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n  totalEmissiveRadiance *= vColor;'); };
    return m;
  };
  const metal = m => { m.envMap = metalEnv.texture; metals.push(m); return m; };
  // chrome: a mirror of the soft studio reads grey; the packshot's chrome is black and white, so its reflection's
  // contrast is raised (dark stays dark, the light clips white), its colour neutral
  const chrome = g => {
    const m = metal(new THREE.MeshPhysicalMaterial({ color: 0xf2f2f2, metalness: 1, roughness: 0.12, toneMapped: false }));
    m.onBeforeCompile = sh => { sh.fragmentShader = sh.fragmentShader.replace('#include <lights_fragment_maps>', '#include <lights_fragment_maps>\n  radiance = smoothstep(vec3(0.5), vec3(1.45), radiance) * 1.3;'); };
    return reg(g, m, 'chrome');
  };
  const SHADE = 0.2;
  const print = (g, map, extra = {}) => reg(g, new THREE.MeshPhysicalMaterial({ color: new THREE.Color(1, 1, 1).multiplyScalar(SHADE), map,
    emissive: 0xffffff, emissiveMap: map, emissiveIntensity: 0.85, roughness: 0.35, specularIntensity: 0.08, toneMapped: false, depthWrite: false,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, ...extra }));
  const mT = { body: plastic('S'), stand: plastic('S', 0.93), recess: plastic('S', 0.72), screen: reg('S', new THREE.MeshBasicMaterial({ map: glassTex, toneMapped: false })) };
  // the aluminium: no grain (the packshot's shows none); its roughness the mean of the grain map it had (0.26 × 0.5)
  const mC = { alu: reg('S', metal(new THREE.MeshPhysicalMaterial({ color: 0xcfcfcf, metalness: 1, roughness: 0.13, emissive: 0x2a2a2a, toneMapped: false }))), chrome: chrome('S'),
    grille: reg('S', new THREE.MeshPhysicalMaterial({ color: 0x9a9a9a, map: grilleTex, metalness: 0.5, roughness: 0.45, emissive: 0xffffff, emissiveMap: grilleTex, emissiveIntensity: 0.8, toneMapped: false })),
    badge: print('S', badgeTex), base: plastic('S', 0.97) };
  const mH = { body: plastic('H'), shell: shaded('H', 1), cradle: shaded('H', 1.22), chrome: chrome('H'), panel: print('H', panelTex),
    button: reg('H', new THREE.MeshPhysicalMaterial({ color: 0x3a3a3a, roughness: 0.4, toneMapped: false })) };
  const mB = plastic('S');
  // the cable: one tube from the tail to the stand; its alpha is the probe's (1) near the tail and K's further on
  const CAB = { uAH: { value: 1 }, uAK: { value: 1 } };
  const mK = new THREE.MeshPhysicalMaterial({ ...PLASTIC, color: 0xe6e7e4, emissive: 0x525351, roughness: 0.55, clearcoat: 0, toneMapped: false, transparent: true });
  mK.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, CAB);
    sh.vertexShader = 'attribute float arc; varying float vArc;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vArc = arc;');
    sh.fragmentShader = 'uniform float uAH, uAK; varying float vArc;\n' + sh.fragmentShader.replace('#include <alphamap_fragment>',
      '#include <alphamap_fragment>\n  diffuseColor.a *= mix(uAH, uAK, smoothstep(0.04, 0.22, vArc));');
  };
  edgy(mK, 'cable'); groups.K.push(mK); layerOf.set(mK, 'K');
  // a fading layer is drawn as one body: first its depth alone (pushed back a hair), then its colour, which keeps only
  // the surface nearest the camera; the probe (opaque) first, then the system, then the cable
  const ORDER = { H: 10, S: 21, K: 31 };
  const DEPTH = {};
  for (const L of ['S', 'K']) DEPTH[L] = new THREE.MeshBasicMaterial({ colorWrite: false, transparent: true, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });

  // ---- geometry helpers (gw)
  function rrect(w, h, r) {   // a rounded rectangle centred on the origin
    const s = new THREE.Shape(), x = w / 2, y = h / 2;
    s.moveTo(-x + r, -y); s.lineTo(x - r, -y); s.absarc(x - r, -y + r, r, -Math.PI / 2, 0); s.lineTo(x, y - r);
    s.absarc(x - r, y - r, r, 0, Math.PI / 2); s.lineTo(-x + r, y); s.absarc(-x + r, y - r, r, Math.PI / 2, Math.PI);
    s.lineTo(-x, -y + r); s.absarc(-x + r, -y + r, r, Math.PI, Math.PI * 1.5); return s;
  }
  function rbox(x0, x1, y0, y1, z0, z1, b = 0.003, r = 0.004) {   // a box with rounded edges, from its extents
    const w = x1 - x0, h = y1 - y0, d = z1 - z0;
    const g = new THREE.ExtrudeGeometry(rrect(w - 2 * b, h - 2 * b, Math.max(0.0005, r - b)), { depth: Math.max(0.0005, d - 2 * b), bevelEnabled: true,
      bevelThickness: b, bevelSize: b, bevelSegments: 3, curveSegments: 6 });
    return g.translate((x0 + x1) / 2, (y0 + y1) / 2, z0 + b);
  }
  const mesh = (g, m, parent, order = 0) => { const x = new THREE.Mesh(g, m); x.renderOrder = ORDER[layerOf.get(m)] + order; parent.add(x); return x; };
  // an indexed grid (rows × columns of points, columns closing round when `wrap`) with smooth normals and a vertex
  // colour (the shade): rows[r][c] = [x, y, z, shade]
  function grid(rows, wrap) {
    const R = rows.length, C = rows[0].length, pos = [], col = [], idx = [];
    for (const row of rows) for (const [x, y, z, s] of row) { pos.push(x, y, z); col.push(s, s, s); }
    for (let r = 0; r < R - 1; r++) for (let c = 0; c < (wrap ? C : C - 1); c++) {
      const c1 = (c + 1) % C, a = r * C + c, b = r * C + c1, d = (r + 1) * C + c, e = (r + 1) * C + c1;
      idx.push(a, b, d, b, e, d);   // rows outward, columns clockwise seen from outside: normals outward
    }
    const g = new THREE.BufferGeometry(); g.setIndex(idx);
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.computeVertexNormals(); return g;
  }

  // ---- the system
  const sys = new THREE.Group(); scene.add(sys);
  const TH = rad(25.56), TY = -0.46;               // the tablet's lean; the table
  const tab = new THREE.Group(); tab.rotation.x = -TH; sys.add(tab);   // the tablet's frame: x right, y up the glass, z out of it
  // the tablet: body 1.014 × 0.6425 × 0.030 (a 0.007 white rim round the glass), the glass on its front
  mesh(rbox(-0.507, 0.507, -0.32125, 0.32125, -0.030, 0, 0.003, 0.010), mT.body, tab);
  mesh(new THREE.PlaneGeometry(1.0, 0.6285).translate(0, 0, 0.0006), mT.screen, tab);
  // the stand's top, under the tablet (as photographed: a plate set back, the lighter block in front of it on the left,
  // the neck on the right; below them it goes behind the cylinder)
  mesh(rbox(-0.141, 0.261, -0.42, -0.32125, -0.032, -0.016, 0.002, 0.004), mT.recess, tab);
  mesh(rbox(-0.127, 0.126, -0.42, -0.3215, -0.026, -0.006, 0.003, 0.006), mT.stand, tab);
  mesh(rbox(0.174, 0.261, -0.44, -0.3215, -0.030, -0.012, 0.003, 0.005), mT.stand, tab);
  // the cylinder's hidden partner: the stand's base on the table (its front right corner shows right of the cylinder's
  // end: front face Z −0.12, right edge X 0.392, top Y −0.39), faded with the cylinder that hides the rest of it
  mesh(rbox(-0.25, 0.392, TY, -0.39, -0.15, -0.12, 0.006, 0.008), mC.base, sys);

  // the probe: its frame in the tablet's, the front face's middle at (u 1.112, v 0.354) of the glass, DZ in front of it,
  // leaning back LEAN (the tablet 25.56°)
  const LEAN = rad(qa && qa.lean != null ? qa.lean : 23), DZ = qa && qa.dz != null ? qa.dz : 0.0;
  const PX = qa && qa.px != null ? qa.px : 0.622, PY = qa && qa.py != null ? qa.py : 0.31425 - 0.354;
  const prb = new THREE.Group(); prb.position.set(PX, PY, DZ); prb.rotation.x = TH - LEAN; tab.add(prb);
  // its front outline (half width by height; y from the anchor, top 0.307, bottom −0.306): round top r 0.073, straight
  // sides to y −0.146, narrowing to 0.060 at −0.266, a round bottom
  const PT = 0.301, PB = -0.300, PW = 0.073, BS = 0.018, BT = 0.032, PD = 0.09;
  function outline(inset) {   // the right half's points, top to bottom, then mirrored: a closed shape
    const pts = [], hw = PW - inset, top = PT - inset, bot = PB + inset;
    for (let i = 0; i <= 24; i++) { const a = Math.PI / 2 * (1 - i / 24); pts.push([hw * Math.cos(a), top - hw + hw * Math.sin(a)]); }
    const yS = -0.146, yN = -0.266, wN = 0.060 - inset;
    for (let i = 1; i <= 12; i++) { const t = i / 12, s = t * t * (3 - 2 * t); pts.push([lerp(hw, wN, s), lerp(yS, yN, t)]); }
    for (let i = 1; i <= 20; i++) { const a = -Math.PI / 2 * i / 20; pts.push([wN * Math.cos(a), yN + (yN - bot) * Math.sin(a)]); }
    const all = pts.concat(pts.slice(0, -1).reverse().map(([x, y]) => [-x, y]).slice(1));
    return all;
  }
  // the body: a moulded shell round the front cap's edge (outline 0.012, points every 0.006 gw, clockwise from the top):
  // the front crowned below the panel (CROWN at the middle, 0 at the cap's edge, rising from the panel's bezel down),
  // the rounded edge (BS out, BT back; it starts on the crown's own slope, so the front turns into the side without a
  // crease), the straight side, the rounded back. Across the cap the rows close onto x = 0 between the centres of the
  // round top and bottom (Y_HI, Y_LO); where the cradle's lips lie over it, the shade darkens (their gap)
  const CROWN = 0.007, Y_HI = PT - PW, Y_LO = -0.266, KBT = BT / BS;
  const crownAt = y => CROWN * smooth(0.074, 0.0, y);
  const CAP = (() => {
    const pts = outline(0.012), out = [];
    for (let i = 0; i < pts.length; i++) {
      const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length], n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 0.006));
      for (let k = 0; k < n; k++) out.push([lerp(x0, x1, k / n), lerp(y0, y1, k / n)]);
    }
    return out.map(([x, y], i, A) => {   // each with its ring centre m, its distance hw to it, its outward normal n, its bevel's start
      const m = [0, clamp(y, Y_LO, Y_HI)], hw = Math.hypot(x - m[0], y - m[1]);
      const [xa, ya] = A[(i + A.length - 1) % A.length], [xb, yb] = A[(i + 1) % A.length];
      let nx = yb - ya, ny = -(xb - xa); const l = Math.hypot(nx, ny); nx /= l; ny /= l;
      if (nx * (x - m[0]) + ny * (y - m[1]) < 0) { nx = -nx; ny = -ny; }
      const sl = 2 * crownAt(y) / hw, s0 = sl / (KBT - sl);   // the crown's slope at the edge → sin of the bevel's start
      return { x, y, m, hw, nx, ny, s0 };
    });
  })();
  // the front surface's profile across the edge at a cap point, by the offset o from the cap's edge (o < 0 on the cap,
  // 0…BS on the rounded edge): [x, y, z]
  function front(c, o) {
    if (o <= 0) {
      const t = Math.min(1, -o / c.hw), x = lerp(c.x, c.m[0], t), y = lerp(c.y, c.m[1], t);
      return [x, y, crownAt(y) * t * (2 - t)];
    }
    const sp = Math.min(1, c.s0 + o * (1 - c.s0) / BS), cp = Math.sqrt(1 - sp * sp), c0 = Math.sqrt(1 - c.s0 * c.s0);
    return [c.x + c.nx * o, c.y + c.ny * o, -BT * (c0 - cp) / c0];
  }
  // the cradle: a shell round the probe's lower part (from y TOP on the right, round the bottom, to TOP on the left),
  // TH_C thick, GAP off the probe's side, its lip lying over the probe's edge at the photographed line (right x 0.070
  // → 0.054, left −0.066 → −0.050 between TOP and BOT, across the bottom between them), the lip and the corners
  // rounded; on its side, near the back, a parting groove (the photo's dark line along the cradle's right side), the
  // shell behind it a little greyer
  const TOP = 0.055, BOT = 0.354 - 0.645, GAP = 0.0022, TH_C = 0.008, GROOVE = { z: -0.078, w: 0.008, d: 0.0035 };
  const lipOff = (() => {   // the lip's offset from the cap's edge at each cap point inside the cradle (else null)
    const o = CAP.map(c => {
      if (c.y > TOP) return null;
      if (c.y < Y_LO) return undefined;   // the round bottom: filled below
      const t = (TOP - c.y) / (TOP - BOT), x = c.x > 0 ? lerp(0.070, 0.054, t) : -lerp(0.066, 0.050, t);
      return Math.abs(x) - Math.abs(c.x);
    });
    let a = -1, b = -1;
    for (let i = 0; i < o.length; i++) if (o[i] === undefined) { if (a < 0) a = i; b = i; }
    for (let i = a; i <= b; i++) o[i] = lerp(o[a - 1], o[b + 1], (i - a + 1) / (b - a + 2));
    return o;
  })();
  {
    // the body: rows from the front's spine out over the cap, the rounded edge, the side, the back's edge and the back
    const rows = [], NR = 14, NB = 12, shadeAt = (i, o, y) => {   // darker just inside a lip, dark under it
      const L = lipOff[i]; if (L == null) return 1;
      const k = smooth(TOP + 0.012, TOP - 0.004, y);
      return 1 - k * (o > L ? 0.45 : 0.35 * smooth(-0.008, 0, o - L));
    };
    for (let j = 0; j <= NR; j++) {   // the cap: t from 1 (the spine) to 0 (the edge), finer toward the edge
      const t = 1 - Math.pow(j / NR, 0.8);
      rows.push(CAP.map((c, i) => { const o = -t * c.hw, [x, y, z] = front(c, o); return [x, y, z, shadeAt(i, o, y)]; }));
    }
    for (let j = 1; j <= NB; j++) {   // the rounded edge: even steps of its angle
      rows.push(CAP.map((c, i) => {
        const p0 = Math.asin(c.s0), p = lerp(p0, Math.PI / 2, j / NB), o = BS * (Math.sin(p) - c.s0) / (1 - c.s0);
        const [x, y, z] = front(c, o); return [x, y, z, shadeAt(i, o, y)];
      }));
    }
    for (let j = 0; j <= 6; j++) {   // the side's back end, then the back's rounded edge (never seen: coarse)
      const p = Math.PI / 2 * (1 + j / 6), zs = -(PD - BT) + BT * Math.cos(p);
      rows.push(CAP.map((c, i) => { const o = BS * Math.sin(p); return [c.x + c.nx * o, c.y + c.ny * o, zs, shadeAt(i, BS, c.y)]; }));
    }
    rows.push(CAP.map(c => [lerp(c.x, c.m[0], 0.5), lerp(c.y, c.m[1], 0.5), -PD, 1]), CAP.map(c => [c.m[0], c.m[1], -PD, 1]));
    const g = grid(rows, true), nrm = g.attributes.normal;
    for (let i = 0; i < CAP.length; i++) {   // the spines: the crown's own normal there (it slopes only along y)
      const y = CAP[i].m[1], dh = (crownAt(y + 1e-4) - crownAt(y - 1e-4)) / 2e-4, l = Math.hypot(dh, 1);
      nrm.setXYZ(i, 0, -dh / l, 1 / l); nrm.setXYZ(nrm.count - 1 - i, 0, 0, -1);
    }
    mesh(g, mH.shell, prb);
  }
  {
    // the cradle's columns: the cap points inside it. Its section in each column's plane (o: out from the cap's edge
    // along its normal, z: depth): a front face standing over the probe's edge from the lip outward, a rounded corner,
    // the side straight back (the groove in it) to ZB, a rounded back corner, the back; the inner face th under all of
    // it; the lip a half round between the two. Thinner round the bottom (it hugs the probe's round end there)
    const cols = [];
    for (let i = 0; i < CAP.length; i++) if (lipOff[i] != null) cols.push(i);
    const inner = [], lip = [], outer = [], NL = 6, RC = 0.015, RB = 0.009, ZB = -0.104;
    for (const i of cols) {
      const c = CAP[i], L = lipOff[i], th = lerp(TH_C, 0.0045, smooth(Y_LO + 0.02, Y_LO - 0.015, c.y));
      const zf = th + 0.0015 + Math.max(0, front(c, L)[2]), os = BS + GAP + th;   // the front clears the crown under the lip
      const sec = [];   // [o outside, z, normal o, normal z, shade, o of the section without the groove]
      for (let k = 0; k <= 4; k++) { const o = lerp(L, os - RC, k / 4); sec.push([o, zf, 0, 1, 1, o]); }
      for (let k = 1; k <= 6; k++) {
        const a = Math.PI / 2 * (1 - k / 6), o = os - RC + RC * Math.cos(a);
        sec.push([o, zf - RC + RC * Math.sin(a), Math.cos(a), Math.sin(a), 1, o]);
      }
      for (const z of [-0.03, -0.045, -0.058, -0.066, GROOVE.z + GROOVE.w * 0.9, GROOVE.z + GROOVE.w * 0.5, GROOVE.z, GROOVE.z - GROOVE.w * 0.5, GROOVE.z - GROOVE.w * 0.9, ZB + RB]) {
        const dz = Math.abs(z - GROOVE.z);
        sec.push([os - GROOVE.d * smooth(GROOVE.w * 0.8, GROOVE.w * 0.3, dz), z, 1, 0, dz < GROOVE.w * 0.6 ? 0.08 : z < GROOVE.z ? 0.86 : 1, os]);
      }
      for (let k = 1; k <= 4; k++) {
        const a = -Math.PI / 2 * k / 4, o = os - RB + RB * Math.cos(a);
        sec.push([o, ZB + RB + RB * Math.sin(a), Math.cos(a), Math.sin(a), 0.86, o]);
      }
      sec.push([-0.01, ZB, 0, -1, 0.86, -0.01]);
      const at = (o, z) => [c.x + c.nx * o, c.y + c.ny * o, z];
      outer.push(sec.map(([o, z, , , sh]) => [...at(o, z), sh]));
      inner.push(sec.map(([, z, no, nz, , ob]) => [...at(ob - no * th, z - nz * th), 0.45]).reverse());
      // the lip: half a turn from the inner face over the free edge (facing the probe's middle) to the outer face
      const row = [];
      for (let k = 1; k < NL; k++) {
        const a = Math.PI * k / NL;
        row.push([...at(L - th / 2 * Math.sin(a), zf - th / 2 - th / 2 * Math.cos(a)), lerp(0.45, 1, smooth(0.25, 0.75, k / NL))]);
      }
      lip.push(row);
    }
    // rows: inner (back → lip), lip, outer (lip → back); columns: the cradle's points
    const NRI = inner[0].length, rows = [];
    for (let r = 0; r < NRI; r++) rows.push(inner.map(col => col[r]));
    for (let r = 0; r < NL - 1; r++) rows.push(lip.map(col => col[r]));
    for (let r = 0; r < outer[0].length; r++) rows.push(outer.map(col => col[r]));
    mesh(grid(rows, false), mH.cradle, prb);
    // its two ends (at TOP): the strip between the inner and the outer face, and the lip's half disc
    for (const ci of [0, cols.length - 1]) {   // both windings (which side faces out differs at the two ends)
      const s = p => [p[0], p[1], p[2], 0.85], I = inner[ci].slice().reverse().map(s), O = outer[ci].map(s);   // both lip → back
      const arc = [I[0], ...lip[ci].map(s), O[0]], mid = [0, 1, 2].map(j => (I[0][j] + O[0][j]) / 2).concat(0.85);
      for (const rows of [[I, O], [arc.map(() => mid), arc]]) { mesh(grid(rows, false), mH.cradle, prb); mesh(grid(rows.slice().reverse(), false), mH.cradle, prb); }
    }
  }
  // the panel: a black stadium u 1.058…1.166 × v 0.052…0.262 (0.108 × 0.210) on a raised white bezel, its ridge below
  const PCY = 0.354 - 0.157;
  mesh(rbox(-0.06, 0.06, PCY - 0.105 - 0.018, PCY + 0.105 + 0.006, -0.004, 0.004, 0.002, 0.06), mH.body, prb);
  {
    const s = rrect(0.108, 0.210, 0.054), g = new THREE.ShapeGeometry(s, 24), uv = g.attributes.uv, p = g.attributes.position;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, p.getX(i) / 0.108 + 0.5, p.getY(i) / 0.210 + 0.5);
    mesh(g.translate(0, PCY, 0.0045), mH.panel, prb, 1);
  }
  // the buttons: two chrome ovals on the left side (v 0.150–0.170, 0.2025–0.2275), a dark one on the right (v 0.25–0.295)
  const pill = (sx, sy, sz) => new THREE.SphereGeometry(1, 24, 16).scale(sx, sy, sz);
  mesh(pill(0.007, 0.010, 0.007).translate(-PW - 0.011, 0.354 - 0.160, -PD / 2), mH.chrome, prb);
  mesh(pill(0.007, 0.0125, 0.007).translate(-PW - 0.011, 0.354 - 0.215, -PD / 2), mH.chrome, prb);
  mesh(pill(0.004, 0.0225, 0.008).translate(PW + 0.0075, 0.354 - 0.2725, -PD / 2), mH.button, prb);
  // the bracket from the cradle's left wall to the tablet's right side (u 1.00…1.03, v 0.335…0.50), with the tablet
  mesh(rbox(0.495, 0.527, 0.31425 - 0.50, 0.31425 - 0.335, -0.028, -0.008, 0.003, 0.004), mB, tab);   // ends short of the cradle's wall
  // the tail: ribbed, under the probe's bottom, out through the cradle's (5 ribs, 0.045 long, radius 0.014 → 0.012)
  const TAIL_L = 0.045;
  {
    const pts = [];
    for (let i = 0; i <= 60; i++) { const t = i / 60, r = lerp(0.0135, 0.0115, t) + 0.0012 * Math.pow(Math.sin(Math.PI * 5 * t), 2); pts.push(new THREE.Vector2(r, -t * TAIL_L)); }
    pts.unshift(new THREE.Vector2(0.0135, 0.01)); pts.push(new THREE.Vector2(0.0078, -TAIL_L - 0.004));
    mesh(new THREE.LatheGeometry(pts, 32).translate(0, PB + 0.006, -PD / 2), mH.body, prb);
  }

  // ---- the cylinder: along X from −0.425 to +0.482 at Y −0.3761, Z 0.2855, R 0.0839; chrome cap (rounded), brushed
  // aluminium, the short chrome collar (from 0.945 of the length, narrowing straight to its rounded lip at 0.81 R) and
  // the perforated end just inside the lip
  const CR = 0.0839, CL = 0.907, CX0 = -0.425, CY = TY + CR, CZ = 0.2855;
  const cyl = new THREE.Group(); cyl.position.set(CX0, CY, CZ); sys.add(cyl);
  const lathe = (pts, m) => {   // pts: [r/R, f of the length]; the lathe's axis turned onto +X
    const g = new THREE.LatheGeometry(pts.map(([r, f]) => new THREE.Vector2(r * CR, f * CL)), 128).rotateZ(-Math.PI / 2);
    return mesh(g, m, cyl);
  };
  lathe([[0, 0], [0.55, 0], [0.70, 0.002], [0.82, 0.006], [0.91, 0.012], [0.965, 0.019], [0.992, 0.026], [1.0, 0.032], [0.988, 0.0345], [0.988, 0.0365]], mC.chrome);
  lathe([[0.988, 0.0365], [1.0, 0.038], [1.0, 0.945]], mC.alu);
  lathe([[1.0, 0.945], [0.996, 0.948], [0.986, 0.953], [0.862, 0.980], [0.85, 0.9835], [0.838, 0.9868], [0.824, 0.9890], [0.812, 0.9892], [0.803, 0.9878],
    [0.80, 0.9862]], mC.chrome);
  mesh(new THREE.CircleGeometry(0.80 * CR, 96).rotateY(Math.PI / 2).translate(0.9862 * CL, 0, 0), mC.grille, cyl);
  // the badge: a convex stadium 0.137 × 0.034 at X +0.044 (the cylinder's middle), 55.5° up from the front: a chrome
  // frame 0.0055 wide (rounded across, so it shows the chrome's dark and light, as photographed) round the white face
  // (the print, 0.128 × 0.025, under the frame's inner edge)
  {
    const BO = [0.137, 0.034], RIM = 0.0055, FACE = [0.128, 0.025], PHI = rad(55.5), XC = 0.044 - CX0;
    const wrap = (x, y, h) => { const a = PHI + y / CR, r = CR + h; return [XC + x, r * Math.sin(a), r * Math.cos(a)]; };
    const patch = (w, h, off, bulge) => {   // a stadium patch on the cylinder: rows across the arc, each row the stadium's width
      const pos = [], uv = [], idx = [], NY = 16, NX = 60, rr = h / 2;
      for (let j = 0; j <= NY; j++) {
        const y = -h / 2 + h * j / NY, half = w / 2 - rr + Math.sqrt(Math.max(0, rr * rr - y * y));
        for (let i = 0; i <= NX; i++) {
          const x = -half + 2 * half * i / NX;
          pos.push(...wrap(x, y, off + bulge * (1 - (2 * y / h) ** 2) * Math.min(1, (w / 2 - Math.abs(x)) / rr))); uv.push(x / w + 0.5, y / h + 0.5);
          if (i < NX && j < NY) { const A = j * (NX + 1) + i, B = A + 1, C = A + NX + 1, D = C + 1; idx.push(A, B, C, B, D, C); }
        }
      }
      const g = new THREE.BufferGeometry(); g.setIndex(idx);
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
      g.computeVertexNormals(); return g;
    };
    // the frame: round a stadium (a segment ±A offset by ρ), from ρ = BO/2 − RIM (inside) to BO/2; its height above
    // the aluminium rises from the face's edge to a rounded top and falls to the aluminium at the outside
    const A = (BO[0] - BO[1]) / 2, NS = 200, rows = [];
    const at = u => {   // the segment point and the outward direction at u ∈ [0, 1) round the stadium
      const Ls = 2 * A, La = Math.PI * BO[1] / 2, tot = 2 * Ls + 2 * La; let s = u * tot;
      if (s < Ls) return [-A + s, 0, 0, 1]; s -= Ls;
      if (s < La) { const a = Math.PI / 2 - Math.PI * s / La; return [A, 0, Math.cos(a), Math.sin(a)]; } s -= La;
      if (s < Ls) return [A - s, 0, 0, -1]; s -= Ls;
      const a = -Math.PI / 2 - Math.PI * s / La; return [-A, 0, Math.cos(a), Math.sin(a)];
    };
    for (let j = 0; j <= 8; j++) {
      const v = j / 8, rho = BO[1] / 2 - RIM * (1 - v), h = lerp(0.0021, 0.0003, v) + 0.0017 * Math.sin(Math.PI * Math.pow(v, 0.8));
      const row = [];
      for (let i = 0; i < NS; i++) { const [cx, cy, dx, dy] = at(i / NS); row.push([...wrap(cx + dx * rho, cy + dy * rho, h), 1]); }
      rows.push(row);
    }
    const ring = grid(rows, true); ring.deleteAttribute('color');
    mesh(ring, mC.chrome, cyl);
    mesh(patch(FACE[0], FACE[1], 0.0016, 0.0016), mC.badge, cyl, 1);
  }

  // ---- the cable (Ø 0.015): from the tail down into the top of three stacked loops on the table (fitted on the photo:
  // centre X 0.735, Z 0.171, middle loop r 0.146, the lower ones 0.0105 wider, each lying on the one below), round
  // them, then back to the stand's base behind the cylinder's right end (its end is never seen). Points in S. The lead
  // leaves the tail heading down and meets the top loop along it (a cubic with both ends' directions: no kink)
  const CB = { x: 0.735, z: 0.171, r: 0.1458, d: 0.0105, h: 0.0105, tr: 0.0075 };   // neighbours' centres 0.0148 apart: touching
  sys.updateMatrixWorld(true);
  const sOf = (local, out) => out.copy(local).applyMatrix4(prb.matrixWorld);   // probe → S (the system is at identity here)
  const loop = phi => {   // phi° round the loops (increasing from the stand's end), level 0 bottom … 2 top
    const lv = smooth(570, 630, phi) + smooth(930, 990, phi), r = CB.r + CB.d * (1 - lv), a = rad(phi);
    return new V3(CB.x + r * Math.cos(a), TY + CB.tr + CB.h * lv, CB.z + r * Math.sin(a));
  };
  {
    const P = [], tailEnd = sOf(new V3(0, PB + 0.006 - TAIL_L - 0.002, -PD / 2), new V3()), down = sOf(new V3(0, PB - 0.2, -PD / 2), new V3()).sub(tailEnd).normalize();
    const q0 = tailEnd.clone().addScaledVector(down, 0.03);
    P.push(tailEnd.clone(), q0);
    const PHI0 = 240, PHI1 = 1190;
    const e = loop(PHI1), te = loop(PHI1 - 1).sub(loop(PHI1 + 1)).normalize(), L = q0.distanceTo(e);
    const m0 = down.clone().multiplyScalar(L * 1.0), m1 = te.clone().multiplyScalar(L * 1.2);
    for (let i = 1; i < 10; i++) {
      const u = i / 10, u2 = u * u, u3 = u2 * u;
      P.push(q0.clone().multiplyScalar(2 * u3 - 3 * u2 + 1).addScaledVector(m0, u3 - 2 * u2 + u).addScaledVector(e, -2 * u3 + 3 * u2).addScaledVector(m1, u3 - u2));
    }
    for (let phi = PHI1; phi >= PHI0; phi -= 12) P.push(loop(phi));
    P.push(new V3(0.62, -0.445, 0.035), new V3(0.565, -0.435, 0.008), new V3(0.50, -0.43, -0.022), new V3(0.44, -0.427, -0.06),
      new V3(0.40, -0.425, -0.115), new V3(0.37, -0.425, -0.17));
    const curve = new THREE.CatmullRomCurve3(P, false, 'centripetal');
    const N = 900, NS = 16, g = new THREE.TubeGeometry(curve, N, CB.tr, NS, false);
    const Lc = curve.getLength(), arc = new Float32Array(g.attributes.position.count);
    for (let i = 0; i <= N; i++) for (let j = 0; j <= NS; j++) arc[i * (NS + 1) + j] = Lc * i / N;
    g.setAttribute('arc', new THREE.BufferAttribute(arc, 1));
    mesh(g, mK, sys);
  }
  // the depth pre-pass twins of the fading layers (the same geometry, drawn just before their colour)
  {
    const twins = [];
    scene.traverse(o => { if (o.isMesh && (layerOf.get(o.material) === 'S' || o.material === mK)) twins.push(o); });
    for (const o of twins) {
      const L = layerOf.get(o.material), t = new THREE.Mesh(o.geometry, DEPTH[L]);
      t.position.copy(o.position); t.quaternion.copy(o.quaternion); t.scale.copy(o.scale); t.renderOrder = ORDER[L] - 1; o.parent.add(t);
    }
  }

  // ---- the line's silver round the system (live only): a soft shapeless glow behind it, the haze of S2. Flat to the
  // camera in frame px (a plane at a depth; local x = px − PPX… as placed), faded toward the canvas's edges
  // (their fade toward the canvas's edges is wider, 240 frame px: soft light never shows the box's straight edges)
  const hex3 = h => new V3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);
  const SILVER = 0xd9d4cc, SOFT = { uRes: EDGE.uRes, uFade: { value: 240 } };
  const SOFT_F = 'uniform vec2 uRes; uniform float uFade; float edgeFade() { vec2 q = gl_FragCoord.xy; float e = min(min(q.x, uRes.x - q.x), min(q.y, uRes.y - q.y)) / uFade; return smoothstep(0.0, 1.0, e); }';
  const VS = 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }';
  const glowMat = new THREE.ShaderMaterial({ vertexShader: VS, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { ...SOFT, uC: { value: hex3(SILVER) }, uOpacity: { value: 0 } },
    fragmentShader: `uniform vec3 uC; uniform float uOpacity; varying vec2 vUv; ${SOFT_F}
      void main() { vec2 q = vUv * 2.0 - 1.0; float r2 = dot(q, q); gl_FragColor = vec4(uC, uOpacity * exp(-3.0 * r2) * (1.0 - smoothstep(0.5, 1.0, r2)) * edgeFade()); }` });
  const hazeMat = new THREE.ShaderMaterial({ vertexShader: VS, transparent: true, depthWrite: false,
    uniforms: { ...SOFT, uMap: { value: hazeTex }, uC: { value: hex3(SILVER) }, uOpacity: { value: 0 } },
    fragmentShader: `uniform sampler2D uMap; uniform vec3 uC; uniform float uOpacity; varying vec2 vUv; ${SOFT_F}
      void main() { float a = texture2D(uMap, vUv).a; gl_FragColor = vec4(uC, uOpacity * a * edgeFade()); }` });
  const quad = new THREE.PlaneGeometry(1, 1);
  const glow = new THREE.Mesh(quad, glowMat); glow.renderOrder = -2; scene.add(glow);
  // the haze: clubs where the tablet was and round the probe's foot on S2, behind the probe (its front stays clear);
  // [frame x, y, size px, drift phase]; a phone draws the first three
  const HAZE = [[450, 660, 700, 0], [560, 500, 560, 1.7], [480, 930, 640, 3.1], [360, 800, 520, 4.4], [720, 1060, 540, 2.2], [880, 960, 480, 5.3]];
  const hazes = HAZE.map(() => { const m = new THREE.Mesh(quad, hazeMat.clone()); m.material.uniforms = { ...SOFT, uMap: { value: hazeTex }, uC: { value: hex3(SILVER) }, uOpacity: { value: 0 } }; m.renderOrder = -1; scene.add(m); return m; });
  const flat = (m, cx, cy, D, w, h) => {   // a camera-facing quad at depth D whose centre shows at frame (cx, cy), w × h frame px
    m.position.set((cx - PPX) / F * D, -(cy - 750) / F * D, -D); m.scale.set(w / F * D, h / F * D, 1);
  };
  // the glint (S1, toward S5): a white point light passing down the probe's front, never in a key or the kit picture
  const glint = new THREE.PointLight(0xffffff, 0, 0.6, 0); prb.add(glint);

  // ---- where each layer reaches in the frame: points that bound it (local to their part)
  const BOUND = { S: [], H: [], K: [] };
  for (const x of [-0.507, 0.507]) for (const y of [-0.32125, 0.32125]) BOUND.S.push([tab, new V3(x, y, 0)]);
  for (const f of [0, 1]) for (let a = 0; a < 360; a += 30) BOUND.S.push([cyl, new V3(f * CL, CR * Math.cos(rad(a)), CR * Math.sin(rad(a)))]);
  for (const [x, y] of outline(-0.022)) for (const z of [0.01, -0.1]) BOUND.H.push([prb, new V3(x, y, z)]);
  BOUND.H.push([prb, new V3(0, PB - TAIL_L - 0.01, -PD / 2)]);
  for (let a = 0; a < 360; a += 20) BOUND.K.push([sys, new V3(CB.x + (CB.r + CB.d + CB.tr) * Math.cos(rad(a)), TY, CB.z + (CB.r + CB.d + CB.tr) * Math.sin(rad(a)))]);
  const bv = new V3(), bf = [0, 0];
  const reach = (L, out) => {   // [x0, x1, y0, y1] in frame px
    out[0] = out[2] = 1e9; out[1] = out[3] = -1e9;
    for (const [o, v] of BOUND[L]) { bv.copy(v).applyMatrix4(o.matrixWorld); toFrame(bv, bf); out[0] = Math.min(out[0], bf[0]); out[1] = Math.max(out[1], bf[0]); out[2] = Math.min(out[2], bf[1]); out[3] = Math.max(out[3], bf[1]); }
    return out;
  };
  // a fading layer is shown only while it is inside the box: its alpha falls to 0 as its outermost point enters the
  // last 36 frame px before an edge (the edge fade has already softened that point), so it never slides across the edge
  const BOX = { l: 0, t: 0, r: 2400, b: 1500 }, FD = 60;
  const inside = e => smooth(0.15 * FD, 0.6 * FD, e[0] - BOX.l) * smooth(0.15 * FD, 0.6 * FD, BOX.r - e[1]) * smooth(0.15 * FD, 0.6 * FD, e[2] - BOX.t) * smooth(0.15 * FD, 0.6 * FD, BOX.b - e[3]);

  // ---- poses: [G frame x, y (the glass's centre), S (frame px per gw there), az°, el° (the camera's direction seen
  // from the glass's centre, in S)]. p0: the packshot exactly; p1: the probe close (its front's middle at (690, 760));
  // p2: the screen close, the whole system in the box (the probe at its right, the cylinder before the stand as
  // photographed); p3: the whole system, nearer frontal; p4: back in the depth over the protocol's steps; p5: the
  // packshot again, a little larger (the kit card's picture)
  const ROLL0 = rad(0.378);   // the packshot's roll about the ray (its camera was level to the table)
  const POSE = [[590.5, 647.7, 648.9, 26.43, 7.48], null, [620, 690, 755, 13, 8], [590, 650, 640, 12, 8], [580, 690, 440, 18, 8], [585, 650, 670, 26.43, 7.48]];
  const ANCHOR = new V3(0, 0, 0);   // the probe's front middle, probe frame
  const ray = new V3(), wR = new V3(), wU = new V3(), wB = new V3(), sR = new V3(), sU = new V3(), sB = new V3(), YAX = new V3(0, 1, 0);
  const mW = new THREE.Matrix4(), mS = new THREE.Matrix4(), fr = [0, 0], tv = new V3();
  function place(gx, gy, S, az, el) {   // the system: its glass centre at frame (gx, gy), S px/gw, seen from (az, el)
    const D = F / S; ray.set((gx - PPX) / F, -(gy - 750) / F, -1).normalize();
    sys.position.copy(ray).multiplyScalar(D);
    wB.copy(ray).negate(); wR.crossVectors(YAX, wB).normalize(); wU.crossVectors(wB, wR);
    const c = Math.cos(ROLL0), s = Math.sin(ROLL0); tv.copy(wR).multiplyScalar(c).addScaledVector(wU, s); wU.multiplyScalar(c).addScaledVector(wR, -s); wR.copy(tv);
    sB.set(Math.cos(rad(el)) * Math.sin(rad(az)), Math.sin(rad(el)), Math.cos(rad(el)) * Math.cos(rad(az))); sR.crossVectors(YAX, sB).normalize(); sU.crossVectors(sB, sR);
    mW.makeBasis(wR, wU, wB); mS.makeBasis(sR, sU, sB).transpose();
    sys.quaternion.setFromRotationMatrix(mW.multiply(mS)); sys.updateMatrixWorld(true);
    return D;
  }
  // p1: the glass centre that puts the probe's anchor at (690, 760) with S 980, az 16, el 7.5 (solved once)
  {
    const want = [690, 760], P1 = [690, 760, 980, 16, 7.5];
    for (let it = 0; it < 30; it++) {
      place(...P1); toFrame(tv.copy(ANCHOR).applyMatrix4(prb.matrixWorld), fr);
      P1[0] += want[0] - fr[0]; P1[1] += want[1] - fr[1];
    }
    POSE[1] = P1;
  }
  // S2 → S3 goes through MID at its middle (a quadratic in the pose, the scale in log): the camera draws back from the
  // probe until the whole system is in the box, there the tablet and the cylinder come out of the haze, then it closes
  // on the screen. Its control point:
  const MID = [700, 700, 560, 14.5, 7.8], CTRL = MID.map((v, i) => i === 2 ? Math.exp(2 * Math.log(v) - 0.5 * (Math.log(POSE[1][2]) + Math.log(POSE[2][2]))) : 2 * v - 0.5 * (POSE[1][i] + POSE[2][i]));
  // the layers' opacities (S, K; the probe is always there), the haze, the glow's level and the sway per key
  const GLOW = [0.3, 0.12, 0.24, 0.32, 0.2, 0.3], SWAY = [1, 1, 0.4, 1, 0.6, 1];
  const ST = { pose: [0, 0, 0, 0, 0], a: { S: 1, H: 1, K: 1 }, haze: 0, hazeOut: 0, glow: 0, glint: 0, sway: 1, down: 1 };
  function story(p) {
    const k = Math.min(4, Math.floor(p)), f = p - k, s = smooth(0, 1, f), st = ST, A = POSE[k], B = POSE[k + 1], P = st.pose, a = st.a;
    if (k === 1) {
      const w0 = (1 - s) * (1 - s), w1 = 2 * s * (1 - s), w2 = s * s;
      for (let i = 0; i < 5; i++) P[i] = i === 2 ? Math.exp(w0 * Math.log(A[2]) + w1 * Math.log(CTRL[2]) + w2 * Math.log(B[2])) : w0 * A[i] + w1 * CTRL[i] + w2 * B[i];
    } else {
      P[0] = lerp(A[0], B[0], s); P[1] = lerp(A[1], B[1], s); P[2] = A[2] * Math.pow(B[2] / A[2], s); P[3] = lerp(A[3], B[3], s); P[4] = lerp(A[4], B[4], s);
    }
    a.S = a.H = a.K = 1; st.haze = st.hazeOut = st.glint = 0;
    st.glow = lerp(GLOW[k], GLOW[k + 1], s); st.sway = lerp(SWAY[k], SWAY[k + 1], s);
    st.down = 1 - smooth(0, 0.5, p) + smooth(4.5, 5, p);   // on the packshot's pose the sway only turns toward the front
    if (k === 0) {   // S1 → S2: close on the probe; the tablet, the cylinder and the cable go into the haze (the body at
      // once: on the packshot's pose the cylinder's left end is 60 px inside the box, the first step toward the probe
      // takes it there)
      a.S = 1 - smooth(0.0, 0.17, f); a.K = 1 - smooth(0.0, 0.35, f);
      st.haze = smooth(0.0, 0.5, f); st.glint = 1 - smooth(0, 0.3, f);
    } else if (k === 1) {   // S2 → S3: the haze thins and drifts apart, the tablet and the cylinder come out of it
      a.S = smooth(0.38, 0.8, f); a.K = 0;
      st.haze = 1 - smooth(0.3, 0.85, f); st.hazeOut = smooth(0.25, 0.9, f);
    } else if (k === 2) {   // S3 → S4: back to the whole system; the cable returns
      a.K = smooth(0.55, 0.95, f);
      st.sway = lerp(SWAY[2], SWAY[3], smooth(0.65, 1, f));
    } else if (k === 3) {   // S4 → S5: the system steps back; a white glint passes the probe (step 1: the scan)
      st.glint = 0.7 * smooth(0.6, 1, f);
    } else {   // S5 → kit: to the packshot's pose, everything live settles
      st.glint = 0.7 * (1 - smooth(0, 0.85, f)); st.glow *= 1 - smooth(0.6, 0.95, f);
    }
    return st;
  }

  // ---- applying a state
  const last = { G: [0, 0], S: 0, az: 0, el: 0, camX: 0, a: { S: 1, H: 1, K: 1 }, gate: { S: 1, K: 1 }, haze: 0, glow: 0, glint: 0 };
  const setLayer = (g, a) => { for (const m of groups[g]) { m.opacity = a; m.visible = a > 0.004; } };
  const phone = matchMedia('(max-width: 899px)');
  const eS = [0, 0, 0, 0], eK = [0, 0, 0, 0];
  function pose(p, t, still) {
    const st = story(p), live = still || qa ? 0 : 1 - smooth(4.85, 5, p), q = qa && qa.pose ? qa.pose : st.pose;
    const u = Math.sin(t * 0.45), sw = st.sway * live;
    const az = q[3] + 2.5 * sw * lerp(u, -(0.5 + 0.5 * u), st.down), gy = q[1] - 3 * Math.sin(t * 0.8) * sw;
    const D = place(q[0], gy, q[2], az, q[4]);
    const gS = qa ? 1 : inside(reach('S', eS)), gK = qa ? 1 : inside(reach('K', eK));
    const aS = qa ? 1 : st.a.S * gS, aK = qa ? 1 : st.a.K * gK;
    setLayer('S', aS); DEPTH.S.visible = aS > 0.004 && aS < 0.999;
    CAB.uAH.value = 1; CAB.uAK.value = aK; mK.opacity = 1; DEPTH.K.visible = aK < 0.999;
    // the glow behind the system (live only)
    const gl = live * st.glow; glow.visible = gl > 0.004;
    if (glow.visible) { flat(glow, q[0] + 0.25 * q[2], q[1] + 0.05 * q[2], D + 0.8, 2.0 * q[2], 1.4 * q[2]); glowMat.uniforms.uOpacity.value = gl; }
    // the haze (S2): clubs drift slowly; leaving, they move out from the screen's centre and thin
    const hz = live * st.haze, n = phone.matches ? 3 : HAZE.length;
    hazes.forEach((m, i) => {
      const H = HAZE[i], on = i < n && hz > 0.004; m.visible = on; if (!on) return;
      const dx = H[0] - POSE[2][0], dy = H[1] - POSE[2][1], l = Math.hypot(dx, dy) || 1, out = 180 * st.hazeOut;
      const x = H[0] + dx / l * out + 24 * Math.sin(t * 0.17 + H[3]), y = H[1] + dy / l * out + 10 * Math.sin(t * 0.23 + 2 * H[3]);
      flat(m, x, y, D + 0.35, H[2], H[2]); m.material.uniforms.uOpacity.value = 0.26 * hz;
    });
    // the glint: down the probe's front every 7 s
    const gA = live * st.glint, tt = t % 7;
    glint.intensity = tt < 1.8 ? 0.7 * gA * Math.sin(Math.PI * tt / 1.8) : 0;
    glint.position.set(0.05, lerp(0.30, -0.30, tt / 1.8), 0.10);
    const L = last; L.G[0] = q[0]; L.G[1] = gy; L.S = q[2]; L.az = az; L.el = q[4]; L.camX = D * Math.cos(rad(q[4])) * Math.sin(rad(az));
    L.a.S = aS; L.a.H = 1; L.a.K = aK; L.gate.S = gS; L.gate.K = gK; L.haze = hz; L.glow = gl; L.glint = glint.intensity;
  }

  // ---- drawing into the engine's box
  const full = view => (phone.matches ? Math.min(3, devicePixelRatio || 1) : view.dpr);
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
    EDGE.uRes.value.set(canvas.width, canvas.height); EDGE.uFade.value = 60 * k * pr; SOFT.uFade.value = 240 * k * pr;
    BOX.l = (view.box.x - view.cover.x) / k; BOX.t = (view.box.y - view.cover.y) / k; BOX.r = BOX.l + view.box.w / k; BOX.b = BOX.t + view.box.h / k;
  }
  let maskMat = null;
  function render(p, view) {
    pr = Math.min(full(view), cap); fit(view, pr); pose(p, view.still ? 0 : view.t, view.still);
    if (qa && qa.mask) { maskMat = maskMat || new THREE.MeshBasicMaterial({ color: 0xffffff }); scene.overrideMaterial = maskMat; }
    renderer.render(scene, camera); scene.overrideMaterial = null; renders++;
  }
  function draw(p, view) { pace(performance.now(), view.still); lastP = p; lastView = view; render(p, view); }
  let kits = 0;
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
    for (const t of [glassTex, panelTex, badgeTex, grilleTex, hazeTex, roomEnv, metalEnv]) t.dispose();
    renderer.dispose();
  }
  try { renderer.compile(scene, camera); } catch (e) { /* compiled on first draw instead */ }
  // QA: the last drawn pose, where its colour probes are in the frame, where each layer reaches
  const r1 = a => Math.round(a * 10) / 10, r2 = a => Math.round(a * 100) / 100, pv = new V3();
  const probe = (obj, x, y, z) => { pv.set(x, y, z).applyMatrix4(obj.matrixWorld); toFrame(pv, fr); return [r1(fr[0]), r1(fr[1])]; };
  function state() {
    const L = last, eH = reach('H', [0, 0, 0, 0]);
    return { quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded, version, kits, lastP,
      G: [r1(L.G[0]), r1(L.G[1])], S: r1(L.S), az: r2(L.az), el: r2(L.el), camX: r2(L.camX), a: { S: r2(L.a.S), H: 1, K: r2(L.a.K) }, gate: { S: r2(L.gate.S), K: r2(L.gate.K) },
      haze: r2(L.haze), glow: r2(L.glow), glint: r2(L.glint),
      reach: { S: reach('S', [0, 0, 0, 0]).map(Math.round), H: eH.map(Math.round), K: reach('K', [0, 0, 0, 0]).map(Math.round), box: [BOX.l, BOX.r, BOX.t, BOX.b].map(Math.round) },
      probes: { probeFront: probe(prb, 0, 0.354 - 0.32, crownAt(0.354 - 0.32)), panel: probe(prb, 0.03, 0.354 - 0.245, 0.0045), screen: probe(tab, -0.35, 0.194, 0.0006),
        bezelSide: probe(tab, 0.507, 0.10, -0.015), cylinder: probe(cyl, 0.25, Math.sin(rad(10)) * CR, Math.cos(rad(10)) * CR), anchor: probe(prb, 0, 0, 0),
        probeTop: probe(prb, 0, PT + 0.006, -0.03), probeBottom: probe(prb, 0, PB - 0.006, -0.03) } };
  }
  return { draw, kit, dispose, state, animated: true };
}
