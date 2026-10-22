// MICRO BOOST 10% live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D
// scene, as the approved sample EXOTECH GEL (scenes/exotech-gel.js) and the later pages (exosignal-spray.js: the print
// as one face texture with a metal map, the edge fade). The engine keeps the story geometry (the
// cover-fitted 16:10 frame, the run's box, the phone stage, the kit card); this module draws the pose for the story
// position into the box. Objects are placed by frame pixel (2400×1500) inside the page's scene box (x 168…1248,
// y 285…1215: the scene left, the copy right), measured on the largest packshot, protocols/print/img/micro-boost-10.webp
// (385×1252): the tall ivory box seen from the camera's height (its horizon at 0.42 of the box from the top, so neither
// its top nor its foot shows), its right side a narrow plain strip; true proportions H : W : D = 4.21 : 1 : 1.21.
// The story (site/story3d.json; scratchpad spec pages/micro-boost-10/spec.md, BIOSPICULE line). The scene shows only
// what exists (the owner's rule, 22/10, stronger than the spec): the box as photographed, the serum's spicules as a
// loose swarm and a soft glow of the line's green; no lines, rings, circles, cuts, marks or props:
//   S1 meet     the box; a loose swarm of spicules drifts beside it
//   S2 why      the box smaller on the left, the swarm drifting on the right
//   S3 inside   the box goes; the spicules come close, loose in the middle of the scene
//   S4 feel     (no people: the owner's rule) the box alone on the left, the swarm loose beside it
//   S5 protocol the box small and high (the step cards pass below), a few spicules beside it
//   S6–S7 kit   the box alone in the packshot's pose: the picture that flies into the offer card
// The syringe and a drop of the serum have never been photographed (spec §10.1): neither is drawn. The box never opens
// and turns only as far as the packshot shows its side (the side's width ≤ 0.263 of the front's). The product keeps its
// print's colours (emissive ≈ 85 % + neutral shading, toneMapped off); the line's green lives in the page's smoke and
// the kit's soft glow. No text is drawn but the package's own print (design/micro-boost-10/make_textures.py).
//
// createScene(THREE, { canvas, base, onLoad }) → { draw(p, view), kit(view) → canvas, animated, state(), dispose() }
//   p: the story position 0…5 (run index + progress); view: { cover, box, dpr, t, still } from the engine
export function createScene(THREE, { canvas, base, onLoad }) {
  const V3 = THREE.Vector3, rad = THREE.MathUtils.degToRad, deg = THREE.MathUtils.radToDeg;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  const lerp = (a, b, s) => a + (b - a) * s;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  const scene = new THREE.Scene();
  const phone = matchMedia('(max-width: 899px)');

  // the camera level (the packshot's verticals are parallel: no tilt); `lay` is the same camera without the box's view
  // offset, for placing objects by their frame pixels
  const FOV = 20, DIST = 14;
  const camera = new THREE.PerspectiveCamera(FOV, 1.6, 1, 80);
  camera.position.set(0, 0, DIST); camera.lookAt(0, 0, 0);
  const lay = camera.clone(); lay.updateMatrixWorld(); lay.updateProjectionMatrix();
  const fwd = new V3(); lay.getWorldDirection(fwd);
  const ray = new V3(), TAN = Math.tan(rad(FOV / 2)), TANX = 1.6 * TAN;
  function at(cx, cy, depth, out) {   // the point seen at frame pixel (cx, cy), `depth` in front of the camera
    ray.set(cx / 1200 - 1, 1 - cy / 750, 0.5).unproject(lay).sub(lay.position).normalize();
    return out.copy(lay.position).addScaledVector(ray, depth / ray.dot(fwd));
  }
  const world = (px, depth) => px / 1500 * 2 * depth * TAN;   // frame pixels → world units at that depth
  const pj = new V3();
  const frameOf = (v, out) => { pj.copy(v).project(lay); out[0] = (pj.x + 1) * 1200; out[1] = (1 - pj.y) * 750; return out; };
  const D_BOX = DIST + 1.2;

  // ---- light: a neutral studio for reflections (PMREM), as the HAIR scenes': dark above and below, an even horizon,
  // two tall narrow softboxes either side of the camera, rims behind; a white key from the top left, in front
  function makeEnv() {
    const pm = new THREE.PMREMGenerator(renderer), room = new THREE.Scene();
    const dome = new THREE.SphereGeometry(30, 48, 32), col = [], c = new THREE.Color();
    for (let i = 0; i < dome.attributes.position.count; i++) {
      const y = dome.attributes.position.getY(i) / 30;   // −1 floor … 1 ceiling
      c.setRGB(1, 1, 1).multiplyScalar(0.05 + 0.18 * Math.exp(-(y * y) / 0.06)); col.push(c.r, c.g, c.b);
    }
    dome.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    room.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const panel = (i, x, y, z, w, h) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 1, 1).multiplyScalar(i), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, y, 0); room.add(m);
    };
    panel(5, -5.7, 1, 8.2, 2.4, 9); panel(2.5, 6.4, 1, 7.7, 1.6, 9);   // ±35–40° from the camera, the left one the key
    panel(2.5, -9, 1.5, -7, 2.5, 9); panel(2, 9, 2, -7, 2.5, 9);       // rims from behind
    const rt = pm.fromScene(room, 0.02); pm.dispose();
    room.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    return rt;   // its target: disposing that frees the framebuffer too, not only the texture
  }
  let roomEnv = makeEnv();
  scene.environment = roomEnv.texture;
  // after a lost context three.js restores image textures, not the rendered environment: rebuild it, and have the
  // engine redraw (the kit picture too), also under reduced motion
  const restored = () => {
    const old = roomEnv; roomEnv = makeEnv(); scene.environment = roomEnv.texture; old.dispose(); sizeW = -1; compiled = false;
    version++; if (onLoad) onLoad();
  };
  canvas.addEventListener('webglcontextrestored', restored);
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(-4, 6, 6); scene.add(key);

  // ---- textures: the typeset print (make_textures.py): the front's colours and its material (G roughness, B metal)
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy();
  const tex = (name, srgb) => {
    const t = new THREE.TextureLoader().load(new URL(`img/micro-boost-10-3d/${name}`, base).href, () => {
      t.needsUpdate = true; renderer.initTexture(t);   // uploaded now, not on the first scroll
      if (++loaded === 2) { version++; if (onLoad) onLoad(); }   // the engine redraws the kit picture
    });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const faceTex = tex('box-face.png', true), metalTex = tex('box-metal.png');

  // ---- the scene box's edges: a spicule crossing them fades over their last 48 px (by its frame px)
  const BOXF = [168, 285, 1248, 1215], FADE = 48;
  const EDGE_GLSL = `float edgeFade(vec2 f) { return smoothstep(${BOXF[0]}.0, ${BOXF[0] + FADE}.0, f.x) * (1.0 - smoothstep(${BOXF[2] - FADE}.0, ${BOXF[2]}.0, f.x))
      * smoothstep(${BOXF[1]}.0, ${BOXF[1] + FADE}.0, f.y) * (1.0 - smoothstep(${BOXF[3] - FADE}.0, ${BOXF[3]}.0, f.y)); }`;

  // ---- materials. The product in its print's colours: emissive 0.85 of the colour plus a neutral shading (a diffuse
  // 0.2 of it under the key and the room), not tone mapped; the gold a satin metal (roughness 0.28, metalness 0.6: it
  // catches a little of the softboxes as the box turns). It comes and goes by opacity only, never dimmed
  const SHADE = 0.2;
  const P = (hex, opts = {}) => new THREE.MeshPhysicalMaterial(Object.assign({ color: new THREE.Color(hex).multiplyScalar(SHADE), emissive: hex,
    emissiveIntensity: 0.85, roughness: 0.7, specularIntensity: 0.15, toneMapped: false, transparent: true }, opts));
  const facade = P(0xffffff, { color: new THREE.Color(SHADE, SHADE, SHADE), map: faceTex, emissiveMap: faceTex, metalnessMap: metalTex,
    roughnessMap: metalTex, metalness: 1, roughness: 1, envMapIntensity: 0.35 });
  // the right side: no print reaches it; its colour is the packshot's side as pipetted there (5×5 medians ≈ #BEAD99 at
  // the front probe's height), raised by what the shading takes off it in this light (≈ 0.9 in linear light at θmax), so
  // the side drawn reads as the photo's (the owner's rule: every flat face of the product within ΔE 8 of its packshot).
  // The faces never seen: the paper, darker
  const SIDE = 0xc8b6a0;
  const side = P(SIDE);
  const hidden = P(new THREE.Color(0xf8eee4).multiplyScalar(0.7));
  const boxMats = [facade, side, hidden];

  // ---- the box, W 1 × H 4.21 × D 1.21: its origin at the front's middle (it turns about that upright), the front a
  // plane with the print, the right side the plain strip; the rest closed for any transition's frame
  const BW = 1, BH = 4.21, BD = 1.21, box = new THREE.Group(); scene.add(box);
  const face = (geo, mat, x, y, z, rx, ry, order) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, 0); m.renderOrder = order; box.add(m); return m; };
  face(new THREE.PlaneGeometry(BW, BH), facade, 0, 0, 0, 0, 0, 1);
  face(new THREE.PlaneGeometry(BD, BH), side, BW / 2, 0, -BD / 2, 0, Math.PI / 2, 1);
  face(new THREE.PlaneGeometry(BD, BH), hidden, -BW / 2, 0, -BD / 2, 0, -Math.PI / 2, 2);
  face(new THREE.PlaneGeometry(BW, BH), hidden, 0, 0, -BD, 0, Math.PI, 2);
  face(new THREE.PlaneGeometry(BW, BD), hidden, 0, BH / 2, -BD / 2, -Math.PI / 2, 0, 2);
  face(new THREE.PlaneGeometry(BW, BD), hidden, 0, -BH / 2, -BD / 2, Math.PI / 2, 0, 2);
  // the box's pose: [cx, h, k] the front's middle at frame x cx, its height h px, the horizon at k of it from the top;
  // θ the angle between the front's normal and the camera's ray to it (the side shows on the right, as photographed)
  const alphaOf = cx => Math.atan((1200 - cx) / 1200 * TANX);
  const tv = new V3(), out2 = [0, 0], o3 = [0, 0], o4 = [0, 0];
  function placeBox(cx, h, k, th) {
    at(cx, 750 + (0.5 - k) * h, D_BOX, box.position);
    box.scale.setScalar(world(h, D_BOX) / BH);
    box.rotation.set(0, alphaOf(cx) - th, 0); box.updateMatrixWorld(true);
  }
  const local = (x, y, z, out) => frameOf(tv.set(x, y, z).applyMatrix4(box.matrixWorld), out);
  function sideRatio() {   // the side's width over the front's, on the horizon (as measured on the packshot: 80 / 304)
    const yh = -box.position.y / box.scale.y;
    const fl = local(-BW / 2, yh, 0, out2)[0], fr = local(BW / 2, yh, 0, o3)[0], br = local(BW / 2, yh, -BD, o4)[0];
    return Math.max(0, br - fr) / (fr - fl);
  }
  const SIDE_MAX = 0.263;   // the packshot's: no more of the side than was photographed
  function thetaMax(cx, h, k) {   // the angle at which the side is the packshot's 0.263 of the front, in this camera
    let a = 0, b = rad(25);
    for (let i = 0; i < 22; i++) { const m = (a + b) / 2; placeBox(cx, h, k, m); if (sideRatio() > SIDE_MAX) b = m; else a = m; }
    return a;
  }

  // ---- the swarm and the glow, flat to the camera in frame pixels (a plane: local x = px − 1200, y = 750 − py), drawn
  // over the box by order (they never pass behind it)
  const pxU = { value: 1 };   // device px per frame px
  const fx = new THREE.Group(); scene.add(fx);
  at(1200, 750, DIST, fx.position); fx.scale.setScalar(world(1, DIST));
  const hex3 = h => new THREE.Vector3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  const QUAD_V = 'varying vec2 vF; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vF = vec2(position.x + 1200.0, 750.0 - position.y); gl_Position = projectionMatrix * viewMatrix * w; }';

  // the kit's backlight: a soft glow of the line's green behind the box (S6–S7 and the offer card's picture), its
  // ellipse within the box's height (the card's picture, cut to what has alpha, keeps the box's size); no ring
  const GL = { uC: { value: hex3(0x24573f) }, uA: { value: 0 }, uR: { value: new THREE.Vector4(600, 812, 330, 360) } };
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(BOXF[2] - BOXF[0], BOXF[3] - BOXF[1]).translate((BOXF[0] + BOXF[2]) / 2 - 1200, 750 - (BOXF[1] + BOXF[3]) / 2, 0),
    new THREE.ShaderMaterial({ uniforms: GL, transparent: true, depthTest: false, depthWrite: false, vertexShader: QUAD_V,
      fragmentShader: `uniform vec3 uC; uniform float uA; uniform vec4 uR; varying vec2 vF;
        void main() { vec2 q = (vF - uR.xy) / uR.zw; float r2 = dot(q, q); gl_FragColor = vec4(uC, uA * exp(-3.0 * r2) * (1.0 - smoothstep(0.6, 1.0, r2))); }` }));
  glow.renderOrder = 0; glow.frustumCulled = false; glow.visible = false; fx.add(glow);

  // the spicules: instanced quads (one draw), every instance's place, angle, length and opacity set on the CPU per frame
  // and uploaded at once. A spicule: a spindle, dark green as on the medallion (#243523), a light glassy rim (#D7E4D0,
  // α 0.55) so it reads on the green smoke; ≥ 1.5 device px wide, soft-edged
  const SPI_V = `attribute vec4 iA; attribute vec2 iB; uniform float uPx; varying vec2 vQ, vF; varying float vHw, vLen, vA;
    void main() {
      float L = max(iA.w, 0.5), hw = max(iB.y * 0.5, 0.75 / uPx), pad = 1.5 / uPx;
      vec2 ax = vec2(cos(iA.z), sin(iA.z)), nr = vec2(-ax.y, ax.x);
      vQ = vec2(position.x * (L * 0.5 + pad), position.y * (hw + pad));
      vec2 p = iA.xy + ax * vQ.x + nr * vQ.y;
      vHw = hw; vLen = L; vA = iB.x; vF = p;
      gl_Position = iB.x > 0.003 ? projectionMatrix * modelViewMatrix * vec4(p.x - 1200.0, 750.0 - p.y, 0.0, 1.0) : vec4(2.0, 2.0, 2.0, 1.0);
    }`;
  const SPI_F = `uniform float uPx; varying vec2 vQ, vF; varying float vHw, vLen, vA;
    ${EDGE_GLSL}
    void main() {
      float t = vQ.x / (vLen * 0.5), h = vHw * max(1.0 - t * t, 0.0), d = abs(vQ.y);
      float cov = clamp((h - d) * uPx + 0.5, 0.0, 1.0) * step(abs(t), 1.0);
      if (cov < 0.004) discard;
      float r = clamp(d / max(h, 1e-3), 0.0, 1.0), rim = smoothstep(0.35, 0.95, r);   // a still rim: no light runs along it
      vec3 col = mix(vec3(0.141, 0.208, 0.137), vec3(0.843, 0.894, 0.816), rim);
      gl_FragColor = vec4(col, cov * vA * mix(1.0, 0.55, rim) * edgeFade(vF));
    }`;
  const NS = 600, NS_PH = 360;
  const SA = new Float32Array(NS * 4), SB = new Float32Array(NS * 2);
  const swGeo = new THREE.InstancedBufferGeometry();
  swGeo.setIndex([0, 1, 2, 0, 2, 3]); swGeo.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
  swGeo.setAttribute('iA', new THREE.InstancedBufferAttribute(SA, 4).setUsage(THREE.DynamicDrawUsage));
  swGeo.setAttribute('iB', new THREE.InstancedBufferAttribute(SB, 2).setUsage(THREE.DynamicDrawUsage));
  swGeo.instanceCount = NS;
  const swU = { uPx: pxU };
  const swarm = new THREE.Mesh(swGeo, new THREE.ShaderMaterial({ uniforms: swU, vertexShader: SPI_V, fragmentShader: SPI_F,
    transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide }));
  swarm.renderOrder = 40; swarm.frustumCulled = false; fx.add(swarm);

  // each spicule's seeds: its kind (40 : 60 short : long by count — a picture of the catalogue's 40 % / 60 %, not a
  // measured ratio), its rank (the layouts show fewer of them later: those ranked under the layout's share), its place
  // in the swarm (g0, g1), its own angle, its phase
  const rng = (s => () => { s |= 0; s = s + 0x6d2b79f5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; })(20261022);
  const gau = () => { const r = Math.sqrt(-2 * Math.log(Math.max(1e-6, rng()))); return r * Math.cos(2 * Math.PI * rng()); };
  const SEED = Array.from({ length: NS }, () => ({ u: rng(), w: rng(), g0: gau(), g1: gau(), ph: rng(), lag: rng() * 0.25, a: rng() * Math.PI }));
  const perm = Array.from({ length: NS }, (_, i) => i); for (let i = NS - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; }
  SEED.forEach((s, i) => { s.rank = perm[i] / NS; s.long = s.u >= 0.4; });
  const SHORT = 0.27;   // the short ones' length: 90 / 330 µm (b2.label1–2)

  // ---- poses (frame px). The box [cx, h, opacity, k]: k the horizon's place on it from the top (0.42 as on the
  // packshot; its top and foot never show while both stay ≥ 5 % of its height off the horizon: k ≤ 0.95), θ always the
  // packshot's angle (θmax, the sway aside). S3 has no box (the spicules close), S4 the box alone on the left.
  // S5 keeps above the page's three step cards: while the story holds there they come up to frame y ≈ 925 on a 16:10
  // screen and ≈ 800 on 1920×1080, so the box stands high on its horizon (k 0.94: its foot at 775) and the swarm is high
  const BOX = [[540, 780, 1, 0.42], [380, 560, 1, 0.42], [380, 560, 0, 0.42], [420, 780, 1, 0.42], [420, 420, 1, 0.94], [600, 780, 1, 0.42]];

  // the layouts of the spicules: [x, y, angle, length, opacity] of spicule i at time t (still: t 0). Each layout is one
  // loose swarm, [x, y of its middle, σx, σy, a long spicule's length] (frame px), clear of the box's print: S1 right of
  // the box, S2 right of it, S3 close up in the middle of the scene (longer, wider apart), S4 right of the box, S5 right
  // of it and above the step cards. Every spicule keeps its place in each (its seeds g0, g1, held within 2.2 σ) and its
  // own angle, and drifts a little while it lives
  const CLOUD = [[925, 640, 95, 120, 44], [860, 820, 120, 95, 80], [708, 750, 190, 140, 140], [870, 760, 120, 130, 70], [780, 560, 90, 60, 44]];
  const LS = [0.4, 0.12, 0.25, 0.10, 0.07, 0];   // the share of the spicules each layout shows (a phone draws 360 of 600)
  const held = g => 2.2 * Math.tanh(g / 2.2);
  function layout(k, i, t, still, o) {
    const s = SEED[i], C = CLOUD[k], tt = still ? 0 : t;
    o[0] = C[0] + C[2] * held(s.g0) + 8 * Math.sin(tt * 0.23 + s.ph * 6.28);
    o[1] = C[1] + C[3] * held(s.g1) + 8 * Math.cos(tt * 0.19 + s.w * 6.28);
    o[2] = s.a + 0.2 * Math.sin(tt * 0.3 + s.ph * 9); o[3] = (s.long ? C[4] : C[4] * SHORT) * (0.85 + 0.3 * s.w); o[4] = 0.95;
    return o;
  }

  // ---- the story's state at position p, written in place (nothing allocated per frame)
  const ST = { box: [0, 0, 0, 0], glow: 0, sw: [0, 0, 0, 0, 0] };   // sw: layout k → k1, its blend window [a, b], f
  const mixA = (o, a, b, s) => { for (let i = 0; i < o.length; i++) o[i] = lerp(a[i], b[i], s); return o; };
  const setSw = (st, ka, kb, wa, wb, f) => { const w = st.sw; w[0] = ka; w[1] = kb; w[2] = wa; w[3] = wb; w[4] = f; };
  function story(p) {
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST;
    st.glow = 0; mixA(st.box, BOX[k], BOX[k + 1], smooth(0, 1, f));
    if (k === 0) {   // S1 → S2: the box recedes left and smaller; the swarm drifts over to its right
      setSw(st, 0, 1, 0.1, 0.9, f);
    } else if (k === 1) {   // S2 → S3: the box goes; the spicules come close into the middle of the scene
      setSw(st, 1, 2, 0.25, 1, f);
      st.box[2] = 1 - smooth(0, 0.35, f);
    } else if (k === 2) {   // S3 → S4: the box comes back on the left, the swarm drifts out beside it
      setSw(st, 2, 3, 0.2, 1, f);
      for (let i = 0; i < 4; i++) st.box[i] = BOX[3][i];
      st.box[2] = smooth(0.55, 0.95, f);   // as the spicules clear its place
    } else if (k === 3) {   // S4 → S5: the box steps back small and high
      setSw(st, 3, 4, 0.1, 0.9, f);
      mixA(st.box, BOX[3], BOX[4], smooth(0, 0.6, f));   // there before the step cards come up
    } else {   // S5 → kit: the box comes forward into the packshot's pose
      setSw(st, 4, 5, 0, 0.5, f);
      st.glow = smooth(0.5, 1, f);   // the backlight comes up as the box arrives
      mixA(st.box, BOX[4], BOX[5], smooth(0.45, 1, f));   // it waits for the step cards to pass over the scene
    }
    return st;
  }

  // ---- applying a state (in place: no garbage per frame; the QA probes are worked out in state() only)
  const Lk = [0, 0, 0, 0, 0], Lk1 = [0, 0, 0, 0, 0], thC = [NaN, NaN, NaN, 0];   // thC: θmax's last pose and value
  const last = { th: 0, ratio: 0, top: 0, bottom: 0, swarm: 0, t: 0 };
  function pose(p, t, still) {
    const st = story(p), live = still ? 0 : 1 - smooth(4.85, 5, p), ph = phone.matches;
    // the box: θ the packshot's at rest, swaying toward 4° and back (9 s) while it lives; the side never wider than photographed
    const cx = st.box[0], h = st.box[1], bo = st.box[2], kh = st.box[3];
    box.visible = bo > 0.004;
    if (cx !== thC[0] || h !== thC[1] || kh !== thC[2]) { thC[0] = cx; thC[1] = h; thC[2] = kh; thC[3] = thetaMax(cx, h, kh); }
    const thm = thC[3], th = thm - (thm - rad(4)) * (0.5 - 0.5 * Math.cos(t * 2 * Math.PI / 9)) * live;
    placeBox(cx, h, kh, th);
    for (let i = 0; i < boxMats.length; i++) boxMats[i].opacity = bo;
    last.th = th; last.ratio = sideRatio();
    glow.visible = st.glow > 0.004 && box.visible;
    if (glow.visible) {   // centred on the box (front and side), 0.92 of its half height, 1.6 × its width either side
      const l = local(-BW / 2, 0, 0, out2)[0], r = local(BW / 2, 0, -BD, o3)[0], c = local(0, 0, 0, o4);
      GL.uR.value.set((l + r) / 2, c[1], 1.6 * (r - l), 0.46 * h); GL.uA.value = 0.55 * st.glow;
    }
    last.top = local(0, BH / 2, 0, out2)[1]; last.bottom = local(0, -BH / 2, 0, out2)[1];
    // the spicules: each one's place in the two layouts of this transition, mixed (weighted by its opacity in each, so a
    // spicule only in one fades where it is, one in both flows between them), each a little late or early; a layout whose
    // weight is nil is not worked out
    const n = ph ? NS_PH : NS, ka = st.sw[0], kb = st.sw[1], fw = clamp((st.sw[4] - st.sw[2]) / (st.sw[3] - st.sw[2]));
    let shown = 0;
    for (let i = 0; i < n; i++) {
      const s = SEED[i], q = smooth(0, 1, clamp((fw - s.lag) / 0.75));
      if (q < 1 && s.rank < LS[ka]) layout(ka, i, t, still, Lk); else Lk[4] = 0;
      if (q > 0 && s.rank < LS[kb]) layout(kb, i, t, still, Lk1); else Lk1[4] = 0;
      const A = (1 - q) * Lk[4], B = q * Lk1[4], W = A + B;
      const j = i * 4, jb = i * 2;
      if (W < 0.003) { SB[jb] = 0; continue; }
      SA[j] = (A * Lk[0] + B * Lk1[0]) / W; SA[j + 1] = (A * Lk[1] + B * Lk1[1]) / W;
      SA[j + 2] = 0.5 * Math.atan2(A * Math.sin(2 * Lk[2]) + B * Math.sin(2 * Lk1[2]), A * Math.cos(2 * Lk[2]) + B * Math.cos(2 * Lk1[2]));
      if (B > A ? Math.cos(SA[j + 2] - Lk1[2]) < 0 : Math.cos(SA[j + 2] - Lk[2]) < 0) SA[j + 2] += Math.PI;   // keep its heading
      SA[j + 3] = (A * Lk[3] + B * Lk1[3]) / W;
      SB[jb] = Math.min(1, W); SB[jb + 1] = SA[j + 3] / 28;
      if (W > 0.02) shown++;
    }
    swarm.geometry.instanceCount = n; swarm.geometry.attributes.iA.needsUpdate = swarm.geometry.attributes.iB.needsUpdate = true;
    swarm.visible = shown > 0; last.swarm = shown;
    last.t = t;
  }
  // QA: where to pipette the print (frame px) in the pose drawn last: the front's empty paper (u .50 / .25, v .70), the
  // band (u .50, v .30), the side; the front's corners TL TR BR BL
  function probe() {
    if (!box.visible) return null;
    const pt = (x, y, z) => local(x, y, z, [0, 0]).map(Math.round);
    return { face: pt(0, (0.5 - 0.70) * BH, 0), face2: pt(-0.25 * BW, (0.5 - 0.70) * BH, 0), band: pt(0, (0.5 - 0.30) * BH, 0),
      side: pt(BW / 2, (0.5 - 0.70) * BH, -BD / 2),
      front: [[-1, 1], [1, 1], [1, -1], [-1, -1]].map(([x, y]) => local(x * BW / 2, y * BH / 2, 0, [0, 0]).map(v => Math.round(v * 10) / 10)) };
  }

  // ---- drawing into the engine's box: the full frame is the cover; the canvas shows the box's part of it
  // the density drawn: a phone's stage is small, so it draws at the screen's full density (≤ 3, as the MASK page), a
  // desktop at the engine's (≤ 2); long frames lower it under a cap (pace), which a rotation keeps
  const full = view => (phone.matches ? Math.min(3, devicePixelRatio || 1) : view.dpr);
  let cap = Infinity, pr = 0, sizeW = -1, sizeH = -1, sizePr = -1, renders = 0, lastT = 0, lastP = 0, lastView = null, trial = null, capped = false, compiled = false;
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
  function fit(view, pr) {
    if (view.box.w !== sizeW || view.box.h !== sizeH || pr !== sizePr) {
      renderer.setPixelRatio(pr); renderer.setSize(view.box.w, view.box.h, false); sizeW = view.box.w; sizeH = view.box.h; sizePr = pr;
    }
    camera.aspect = view.cover.w / view.cover.h;
    camera.setViewOffset(view.cover.w, view.cover.h, view.box.x - view.cover.x, view.box.y - view.cover.y, view.box.w, view.box.h);
    camera.updateProjectionMatrix();
    pxU.value = pr * view.cover.w / 2400;   // device px per frame px: the spicules keep ≥ 1.5 device px
  }
  function render(p, view) {
    pr = Math.min(full(view), cap); fit(view, pr); pose(p, view.still ? 0 : view.t, view.still);
    if (!compiled) { renderer.compile(scene, camera); compiled = true; }   // every program before the first frame shows
    renderer.render(scene, camera); renders++;
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
    const mats = new Set(), geos = new Set();
    scene.traverse(o => { if (o.geometry) geos.add(o.geometry); if (o.material) mats.add(o.material); });
    for (const g of geos) g.dispose();
    for (const m of mats) m.dispose();
    for (const t of [faceTex, metalTex, roomEnv]) t.dispose();
    renderer.dispose();
  }
  const r1 = v => Math.round(v * 10) / 10, r3 = v => Math.round(v * 1000) / 1000;
  const state = () => ({ quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded,
    version, kits, lastP, yawEff: r1(deg(last.th)), sideRatio: r3(last.ratio), boxTop: r1(last.top), boxBottom: r1(last.bottom), boxOp: r3(boxMats[0].opacity * (box.visible ? 1 : 0)),
    swarm: last.swarm, probe: probe() });
  return { draw, kit, dispose, state, animated: true };
}
