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
// stand, the probe in its cradle on the tablet's right (its black panel, two chrome buttons on its left, a dark one on
// its right, the ribbed tail), its cable laid on the table in three loops and led back to the stand's base, and the
// brushed aluminium cylinder in front (0.975 long, Ø 0.168, chrome ends, the perforated end, the badge).
// Nothing moves on the system: the probe stays in its cradle, the screen keeps its photographed print (the target,
// «Mitoscan», «By Mitoderm Ltd»), no part is lifted or opened. Only the camera moves (within what was photographed:
// az ≤ 26.4°, the probe's left side never shows while it is drawn, el ≤ 9°), and whole parts fade out and in.
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
      t.needsUpdate = true; if (++loaded === 6) { version++; if (onLoad) onLoad(); }
    });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const glassTex = tex('glass.png', true), panelTex = tex('panel.png', true), badgeTex = tex('badge.png', true);
  const grilleTex = tex('grille.png', true), brushTex = tex('brushed.png'), hazeTex = tex('haze.png');
  brushTex.wrapS = brushTex.wrapT = THREE.RepeatWrapping; brushTex.repeat.set(1, 6);

  // ---- materials, one set per part that fades on its own: T the tablet and its stand's top, C the cylinder and the
  // stand's base (behind it), H the probe, its cradle and tail, K the cable (its first stretch under the tail goes with H)
  // every surface fades out over the last 60 frame px before the canvas's edge (the scene box): a part passing it in a
  // transition is never cut hard (the glow and the haze too)
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
  const groups = { T: [], C: [], H: [], K: [], B: [] };   // B: the bracket between the tablet and the cradle (with both)
  const reg = (g, m, key) => { m.transparent = true; groups[g].push(m); return edgy(m, key); };
  // white plastic: the packshot's neutral greys hold in every pose (a fitted emissive floor, not tone mapped)
  const PLASTIC = { color: 0x8e8e8c, emissive: 0x9d9d9c, roughness: 0.42, clearcoat: 0.3, clearcoatRoughness: 0.28 };
  const plastic = (g, k = 1) => reg(g, new THREE.MeshPhysicalMaterial({ ...PLASTIC, color: new THREE.Color(PLASTIC.color).multiplyScalar(k),
    emissive: new THREE.Color(PLASTIC.emissive).multiplyScalar(k), toneMapped: false }));
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
  const mT = { body: plastic('T'), stand: plastic('T', 0.93), recess: plastic('T', 0.72), screen: reg('T', new THREE.MeshBasicMaterial({ map: glassTex, toneMapped: false })) };
  const mC = { alu: reg('C', metal(new THREE.MeshPhysicalMaterial({ color: 0xcfcfcf, metalness: 1, roughness: 0.26, emissive: 0x2a2a2a, roughnessMap: brushTex,
    bumpMap: brushTex, bumpScale: 0.0004, toneMapped: false }))), chrome: chrome('C'),
    grille: reg('C', new THREE.MeshPhysicalMaterial({ color: 0x9a9a9a, map: grilleTex, metalness: 0.5, roughness: 0.45, emissive: 0xffffff, emissiveMap: grilleTex, emissiveIntensity: 0.8, toneMapped: false })),
    badge: print('C', badgeTex), base: plastic('C', 0.97) };
  const mH = { body: plastic('H'), cradle: plastic('H', 1.22), chrome: chrome('H'), panel: print('H', panelTex),
    button: reg('H', new THREE.MeshPhysicalMaterial({ color: 0x3a3a3a, roughness: 0.4, toneMapped: false })) };
  const mB = plastic('B');
  // the cable: one tube from the tail to the stand; its alpha follows H near the tail and K further on (by arc length)
  const CAB = { uAH: { value: 1 }, uAK: { value: 1 } };
  const mK = new THREE.MeshPhysicalMaterial({ ...PLASTIC, color: 0xe6e7e4, emissive: 0x525351, roughness: 0.55, clearcoat: 0, toneMapped: false, transparent: true });
  mK.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, CAB);
    sh.vertexShader = 'attribute float arc; varying float vArc;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vArc = arc;');
    sh.fragmentShader = 'uniform float uAH, uAK; varying float vArc;\n' + sh.fragmentShader.replace('#include <alphamap_fragment>',
      '#include <alphamap_fragment>\n  diffuseColor.a *= mix(uAH, uAK, smoothstep(0.04, 0.22, vArc));');
  };
  edgy(mK, 'cable');

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
  const mesh = (g, m, parent, order = 0) => { const x = new THREE.Mesh(g, m); x.renderOrder = order; parent.add(x); return x; };

  // ---- the system
  const sys = new THREE.Group(); scene.add(sys);
  const TH = rad(25.56), TY = -0.46;               // the tablet's lean; the table
  const tab = new THREE.Group(); tab.rotation.x = -TH; sys.add(tab);   // the tablet's frame: x right, y up the glass, z out of it
  // the tablet: body 1.014 × 0.6425 × 0.030 (a 0.007 white rim round the glass), the glass on its front
  mesh(rbox(-0.507, 0.507, -0.32125, 0.32125, -0.030, 0, 0.003, 0.010), mT.body, tab);
  {
    const g = new THREE.PlaneGeometry(1.0, 0.6285).translate(0, 0, 0.0006);
    mesh(g, mT.screen, tab, 1);
  }
  // the stand's top, under the tablet (as photographed: a plate set back, the lighter block in front of it on the left,
  // the neck on the right; below them it goes behind the cylinder)
  mesh(rbox(-0.141, 0.261, -0.42, -0.32125, -0.032, -0.016, 0.002, 0.004), mT.recess, tab);
  mesh(rbox(-0.127, 0.126, -0.42, -0.3215, -0.026, -0.006, 0.003, 0.006), mT.stand, tab);
  mesh(rbox(0.174, 0.261, -0.44, -0.3215, -0.030, -0.012, 0.003, 0.005), mT.stand, tab);
  // the cylinder's hidden partner: the stand's base on the table (its front right corner shows right of the cylinder's
  // end: front face Z −0.12, right edge X 0.392, top Y −0.39), faded with the cylinder that hides the rest of it
  const baseM = mesh(rbox(-0.25, 0.392, TY, -0.39, -0.15, -0.12, 0.006, 0.008), mC.base, sys);

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
  const shapeOf = pts => { const s = new THREE.Shape(); s.moveTo(pts[0][0], pts[0][1]); for (const [x, y] of pts.slice(1)) s.lineTo(x, y); s.closePath(); return s; };
  {
    // the front face 0.122 wide; the body rounds 0.018 past it to its middle depth (the photo's silhouette, 0.158)
    const g = new THREE.ExtrudeGeometry(shapeOf(outline(0.012)), { depth: PD - 2 * BT, bevelEnabled: true, bevelThickness: BT, bevelSize: BS, bevelSegments: 10, curveSegments: 8 });
    mesh(g.translate(0, 0, -(PD - BT)), mH.body, prb);
  }
  // the panel: a black stadium u 1.058…1.166 × v 0.052…0.262 (0.108 × 0.210) on a raised white bezel, its ridge below
  const PCY = 0.354 - 0.157;
  mesh(rbox(-0.06, 0.06, PCY - 0.105 - 0.018, PCY + 0.105 + 0.006, -0.004, 0.004, 0.002, 0.06), mH.body, prb);
  {
    const s = rrect(0.108, 0.210, 0.054), g = new THREE.ShapeGeometry(s, 24), uv = g.attributes.uv, p = g.attributes.position;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, p.getX(i) / 0.108 + 0.5, p.getY(i) / 0.210 + 0.5);
    mesh(g.translate(0, PCY, 0.0045), mH.panel, prb, 2);
  }
  // the buttons: two chrome ovals on the left side (v 0.150–0.170, 0.2025–0.2275), a dark one on the right (v 0.25–0.295)
  const pill = (sx, sy, sz) => new THREE.SphereGeometry(1, 24, 16).scale(sx, sy, sz);
  mesh(pill(0.007, 0.010, 0.007).translate(-PW - 0.011, 0.354 - 0.160, -PD / 2), mH.chrome, prb);
  mesh(pill(0.007, 0.0125, 0.007).translate(-PW - 0.011, 0.354 - 0.215, -PD / 2), mH.chrome, prb);
  mesh(pill(0.004, 0.0225, 0.008).translate(PW + 0.0075, 0.354 - 0.2725, -PD / 2), mH.button, prb);
  // the cradle: two wings round the probe's lower part (v 0.30 → 0.645, joined behind it, never seen), their walls
  // 0.006 outside the probe, narrow lips over the front edges widening a little downward (left x −0.066 → −0.050,
  // right 0.070 → 0.054), tapering with the probe's rounded bottom
  {
    const TOP = 0.055, BOT = 0.354 - 0.645, out = outline(-0.012).filter(([, y]) => y <= TOP && y >= BOT);
    for (const [side, lip] of [[1, [0.070, 0.054]], [-1, [-0.066, -0.050]]]) {
      const edge = out.filter(([x]) => x * side > 0).sort((a, b) => b[1] - a[1]);   // the outer edge, top to bottom
      const pts = [[edge[0][0], TOP]].concat(edge);
      for (let i = 10; i >= 0; i--) { const t = i / 10; pts.push([lerp(lip[0], lip[1], t), lerp(TOP, BOT, t)]); }
      const g = new THREE.ExtrudeGeometry(shapeOf(pts), { depth: PD + 0.02 - 0.008, bevelEnabled: true, bevelThickness: 0.004, bevelSize: 0.003, bevelSegments: 4 });
      mesh(g.translate(0, 0, -PD - 0.014 + 0.004), mH.cradle, prb);
    }
  }
  // the bracket from the cradle's left wall to the tablet's right side (u 1.00…1.03, v 0.335…0.50)
  mesh(rbox(0.495, 0.535, 0.31425 - 0.50, 0.31425 - 0.335, -0.028, -0.008, 0.003, 0.004), mB, tab);   // shown only with both parts
  // the tail: ribbed, under the probe's bottom (5 ribs, 0.045 long, radius 0.014 → 0.012)
  const TAIL_L = 0.045;
  {
    const pts = [];
    for (let i = 0; i <= 60; i++) { const t = i / 60, r = lerp(0.0135, 0.0115, t) + 0.0012 * Math.pow(Math.sin(Math.PI * 5 * t), 2); pts.push(new THREE.Vector2(r, -t * TAIL_L)); }
    pts.unshift(new THREE.Vector2(0.0135, 0.01)); pts.push(new THREE.Vector2(0.0078, -TAIL_L - 0.004));
    mesh(new THREE.LatheGeometry(pts, 32).translate(0, PB + 0.006, -PD / 2), mH.body, prb);
  }

  // ---- the cylinder: along X from −0.461 to +0.514 at Y −0.3755, Z 0.2855, R 0.0839; chrome cap (rounded), brushed
  // aluminium, a chrome ring, the chrome sleeve narrowing to 0.93 R, its rounded lip and the perforated end recessed in it
  const CR = 0.0839, CL = 0.907, CX0 = -0.425, CY = TY + CR, CZ = 0.2855;
  const cyl = new THREE.Group(); cyl.position.set(CX0, CY, CZ); sys.add(cyl);
  const lathe = (pts, m) => {   // pts: [r/R, f of the length]; the lathe's axis turned onto +X
    const g = new THREE.LatheGeometry(pts.map(([r, f]) => new THREE.Vector2(r * CR, f * CL)), 128).rotateZ(-Math.PI / 2);
    return mesh(g, m, cyl);
  };
  lathe([[0, 0], [0.55, 0], [0.70, 0.002], [0.82, 0.006], [0.91, 0.012], [0.965, 0.019], [0.992, 0.026], [1.0, 0.032], [0.988, 0.0345], [0.988, 0.0365]], mC.chrome);
  lathe([[0.988, 0.0365], [1.0, 0.038], [1.0, 0.891]], mC.alu);
  lathe([[1.0, 0.891], [1.012, 0.892], [1.012, 0.897], [1.0, 0.899], [0.93, 0.955], [0.928, 0.975], [0.915, 0.988], [0.89, 0.995], [0.86, 0.997],
    [0.83, 0.995], [0.82, 0.990], [0.82, 0.986]], mC.chrome);
  mesh(new THREE.CircleGeometry(0.82 * CR, 96).rotateY(Math.PI / 2).translate(0.986 * CL, 0, 0), mC.grille, cyl);
  // the badge: a convex chrome-rimmed stadium 0.135 × 0.031 at X +0.014 (the cylinder's middle), 50° up from the front
  {
    const BWd = 0.135, BHd = 0.031, PHI = rad(50), XC = 0.044 - CX0;
    const patch = (w, h, off, bulge) => {   // a stadium patch on the cylinder: rows across the arc, each row the stadium's width
      const pos = [], uv = [], idx = [], NY = 16, NX = 60, rr = h / 2;
      for (let j = 0; j <= NY; j++) {
        const y = -h / 2 + h * j / NY, half = w / 2 - rr + Math.sqrt(Math.max(0, rr * rr - y * y));
        for (let i = 0; i <= NX; i++) {
          const x = -half + 2 * half * i / NX, a = PHI + y / CR, r = CR + off + bulge * (1 - (2 * y / h) ** 2) * Math.min(1, (w / 2 - Math.abs(x)) / rr);
          pos.push(XC + x, r * Math.sin(a), r * Math.cos(a)); uv.push(x / w + 0.5, y / h + 0.5);
          if (i < NX && j < NY) { const A = j * (NX + 1) + i, B = A + 1, C = A + NX + 1, D = C + 1; idx.push(A, B, C, B, D, C); }
        }
      }
      const g = new THREE.BufferGeometry(); g.setIndex(idx);
      g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
      g.computeVertexNormals(); return g;
    };
    mesh(patch(BWd + 0.007, BHd + 0.007, 0.0006, 0.0018), mC.chrome, cyl, 1);
    mesh(patch(BWd, BHd, 0.0016, 0.0016), mC.badge, cyl, 2);
  }

  // ---- the cable (Ø 0.015): from the tail down to the loops on the table (three loops, the lower ones wider, fitted on
  // the photo: centre X 0.735, Z 0.171, middle loop r 0.140, ±0.016, 0.012 apart), round them, then back to the stand's
  // base behind the cylinder's right end (its end is never seen). Points in S
  const CB = { x: 0.735, z: 0.171, r: 0.140, d: 0.0163, h: 0.0121, tr: 0.0075 };
  sys.updateMatrixWorld(true);
  const sOf = (local, out) => out.copy(local).applyMatrix4(prb.matrixWorld);   // probe → S (the system is at identity here)
  let cableMesh = null;
  {
    const P = [], tailEnd = sOf(new V3(0, PB + 0.006 - TAIL_L - 0.002, -PD / 2), new V3()), down = sOf(new V3(0, PB - 0.2, -PD / 2), new V3()).sub(tailEnd).normalize();
    P.push(tailEnd.clone(), tailEnd.clone().addScaledVector(down, 0.035));
    const loop = phi => {   // phi° round the loops (increasing from the stand's end), level 0 bottom … 2 top
      const lv = smooth(570, 630, phi) + smooth(930, 990, phi), r = CB.r + CB.d * (1 - lv), a = rad(phi);
      return new V3(CB.x + r * Math.cos(a), TY + CB.tr + CB.h * lv, CB.z + r * Math.sin(a));
    };
    const PHI0 = 240, PHI1 = 1190;
    const e = loop(PHI1);
    P.push(new V3(lerp(tailEnd.x, e.x, 0.25) - 0.01, lerp(tailEnd.y, e.y, 0.62), lerp(tailEnd.z, e.z, 0.45)));
    for (let phi = PHI1 - 0; phi >= PHI0; phi -= 12) P.push(loop(phi));
    P.push(new V3(0.62, -0.445, 0.035), new V3(0.565, -0.435, 0.008), new V3(0.50, -0.43, -0.022), new V3(0.44, -0.427, -0.06),
      new V3(0.40, -0.425, -0.115), new V3(0.37, -0.425, -0.17));
    const curve = new THREE.CatmullRomCurve3(P, false, 'centripetal');
    const N = 900, g = new THREE.TubeGeometry(curve, N, CB.tr, 12, false);
    const L = curve.getLength(), arc = new Float32Array(g.attributes.position.count);
    for (let i = 0; i <= N; i++) for (let j = 0; j <= 12; j++) arc[i * 13 + j] = L * i / N;
    g.setAttribute('arc', new THREE.BufferAttribute(arc, 1));
    cableMesh = mesh(g, mK, sys);
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

  // ---- poses: [G frame x, y (the glass's centre), S (frame px per gw there), az°, el° (the camera's direction seen
  // from the glass's centre, in S)]. p0: the packshot exactly; p1: the probe close (its front's middle at (690, 760));
  // p2: the screen close, the cylinder before it as photographed; p3: the whole system, nearer frontal; p4: back in the
  // depth over the protocol's steps; p5: the packshot again, a little larger (the kit card's picture)
  const ROLL0 = rad(0.378);   // the packshot's roll about the ray (its camera was level to the table)
  const POSE = [[590.5, 647.7, 648.9, 26.43, 7.48], null, [690, 690, 840, 12, 8], [590, 650, 640, 12, 8], [580, 690, 440, 18, 8], [585, 650, 670, 26.43, 7.48]];
  const ANCHOR = new V3(0, 0, 0);   // the probe's front middle, probe frame
  const camPos = new V3(), ray = new V3(), wR = new V3(), wU = new V3(), wB = new V3(), sR = new V3(), sU = new V3(), sB = new V3(), YAX = new V3(0, 1, 0);
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
  // the parts' opacities (T C H K), the haze, the glow's level and the sway per key
  const GLOW = [0.3, 0.12, 0.24, 0.32, 0.2, 0.3], SWAY = [1, 1, 0.4, 1, 0.6, 1];
  const ST = { pose: [0, 0, 0, 0, 0], a: { T: 1, C: 1, H: 1, K: 1 }, haze: 0, hazeOut: 0, glow: 0, glint: 0, sway: 1, down: 1 };
  function story(p) {
    const k = Math.min(4, Math.floor(p)), f = p - k, s = smooth(0, 1, f), st = ST, A = POSE[k], B = POSE[k + 1], P = st.pose, a = st.a;
    P[0] = lerp(A[0], B[0], s); P[1] = lerp(A[1], B[1], s); P[2] = A[2] * Math.pow(B[2] / A[2], s); P[3] = lerp(A[3], B[3], s); P[4] = lerp(A[4], B[4], s);
    a.T = a.C = a.H = a.K = 1; st.haze = st.hazeOut = st.glint = 0;
    st.glow = lerp(GLOW[k], GLOW[k + 1], s); st.sway = lerp(SWAY[k], SWAY[k + 1], s);
    st.down = 1 - smooth(0, 0.5, p) + smooth(4.5, 5, p);   // on the packshot's pose the sway only turns toward the front
    if (k === 0) {   // S1 → S2: close on the probe; the tablet, the cylinder and the cable go into the haze
      a.T = 1 - smooth(0.05, 0.5, f); a.C = 1 - smooth(0, 0.4, f); a.K = 1 - smooth(0.05, 0.45, f);
      st.haze = smooth(0.25, 0.85, f); st.glint = 1 - smooth(0, 0.3, f);
    } else if (k === 1) {   // S2 → S3: the haze thins and drifts apart, the screen and the cylinder come forward, the probe goes
      a.T = a.C = smooth(0.3, 0.7, f); a.H = 1 - smooth(0.35, 0.75, f); a.K = 0;
      st.haze = 1 - smooth(0.15, 0.65, f); st.hazeOut = smooth(0.1, 0.7, f);
    } else if (k === 2) {   // S3 → S4: back to the whole system; the probe and its cable return once left of the copy
      a.H = smooth(0.6, 0.9, f); a.K = smooth(0.74, 1, f);
      st.sway *= smooth(0.65, 1, f) * 0.6 + 0.4;
    } else if (k === 3) {   // S4 → S5: the system steps back; a white glint passes the probe (step 1: the scan)
      st.glint = 0.7 * smooth(0.6, 1, f);
    } else {   // S5 → kit: to the packshot's pose, everything live settles
      st.glint = 0.7 * (1 - smooth(0, 0.85, f)); st.glow *= 1 - smooth(0.6, 0.95, f);
    }
    return st;
  }

  // ---- applying a state
  const last = { G: [0, 0], S: 0, az: 0, el: 0, camX: 0, a: { T: 1, C: 1, H: 1, K: 1 }, haze: 0, glow: 0, glint: 0 };
  const setGroup = (g, a) => { for (const m of groups[g]) { m.opacity = a; m.visible = a > 0.004; } };
  const phone = matchMedia('(max-width: 899px)');
  function pose(p, t, still) {
    const st = story(p), live = still || qa ? 0 : 1 - smooth(4.85, 5, p), q = qa && qa.pose ? qa.pose : st.pose;
    const u = Math.sin(t * 0.45), sw = st.sway * live;
    const az = q[3] + 2.5 * sw * lerp(u, -(0.5 + 0.5 * u), st.down), gy = q[1] - 3 * Math.sin(t * 0.8) * sw;
    const D = place(q[0], gy, q[2], az, q[4]);
    const a = qa ? { T: 1, C: 1, H: 1, K: 1 } : st.a;
    setGroup('T', a.T); setGroup('C', a.C); setGroup('H', a.H); setGroup('B', Math.min(a.T, a.H));
    CAB.uAH.value = a.H; CAB.uAK.value = a.K; mK.visible = Math.max(a.H, a.K) > 0.004;
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
    const gA = live * st.glint * a.H, tt = t % 7;
    glint.intensity = tt < 1.8 ? 0.7 * gA * Math.sin(Math.PI * tt / 1.8) : 0;
    glint.position.set(0.05, lerp(0.30, -0.30, tt / 1.8), 0.10);
    const L = last; L.G[0] = q[0]; L.G[1] = gy; L.S = q[2]; L.az = az; L.el = q[4]; L.camX = D * Math.cos(rad(q[4])) * Math.sin(rad(az));
    Object.assign(L.a, a); L.haze = hz; L.glow = gl; L.glint = glint.intensity;
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
    for (const t of [glassTex, panelTex, badgeTex, grilleTex, brushTex, hazeTex, roomEnv, metalEnv]) t.dispose();
    renderer.dispose();
  }
  try { renderer.compile(scene, camera); } catch (e) { /* compiled on first draw instead */ }
  // QA: the last drawn pose and where its colour probes are in the frame
  const r1 = a => Math.round(a * 10) / 10, r2 = a => Math.round(a * 100) / 100, pv = new V3();
  const probe = (obj, x, y, z) => { pv.set(x, y, z).applyMatrix4(obj.matrixWorld); toFrame(pv, fr); return [r1(fr[0]), r1(fr[1])]; };
  function state() {
    const L = last;
    return { quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded, version, kits, lastP,
      G: [r1(L.G[0]), r1(L.G[1])], S: r1(L.S), az: r2(L.az), el: r2(L.el), camX: r2(L.camX), a: { T: r2(L.a.T), C: r2(L.a.C), H: r2(L.a.H), K: r2(L.a.K) },
      haze: r2(L.haze), glow: r2(L.glow), glint: r2(L.glint),
      probes: { probeFront: probe(prb, 0, 0.354 - 0.32, 0.0), panel: probe(prb, 0.03, 0.354 - 0.245, 0.0045), screen: probe(tab, -0.35, 0.194, 0.0006),
        bezelSide: probe(tab, 0.507, 0.10, -0.015), cylinder: probe(cyl, 0.25, Math.sin(rad(10)) * CR, Math.cos(rad(10)) * CR), anchor: probe(prb, 0, 0, 0),
        probeTop: probe(prb, 0, PT + 0.006, -0.03), probeBottom: probe(prb, 0, PB - 0.006, -0.03) } };
  }
  return { draw, kit, dispose, state, animated: true };
}
