// CELLULAR AGE DEFENSE 2.5% live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a
// real 3D scene, as the approved sample EXOTECH GEL (scenes/exotech-gel.js) and the later pages (exo-nad.js: the line's
// light as soft shapeless glows; micro-boost-10.js: the print as one typeset face texture). The engine
// keeps the story geometry (the cover-fitted 16:10 frame, the run's box, the phone stage, the kit card); this module draws
// the pose for the story position into the box. Objects are placed by frame pixel (2400×1500) inside the page's scene box
// (x 168…1248, y 285…1215: the scene left, the copy right), measured on the largest packshot,
// protocols/print/img/cellular-age-25.webp (308×1023, never upscaled): the tall ivory box seen from a little below its top
// (the packshot's horizon at 0.34 of the box from the top: neither its top nor its foot shows), its right side a plain
// strip, the front seen 10° off square (the side shows 0.175 of the front); true proportions W : H : D = 0.26 : 1 : 0.26
// (the depth unknown: D = W, which gives the photo's side at 10°).
// The story (site/story3d.json; scratchpad spec pages/cellular-age-defense-2-5/spec.md, BIOSPICULE line), as far as the
// owner's rule of 22/10 lets it («only what exists»):
//   S1 meet     the box as on the packshot, a soft green light behind it
//   S2 why      CELL RENEW 1.5% (its own packshot, the same box) comes in lower left; the 2.5% box higher right
//   S3 inside   the 1.5% box goes; the camera nears the 2.5% box's medallion, the box fades and its spicules leave the
//               print: a shapeless cloud of spicules (site/img/spicules-macro.png's needles in the medallion's dark green)
//               turning slowly in a green haze
//   S4 feel     the 2.5% box comes back from the dark on the left, the cloud drifts back to its right, smaller (no drop,
//               no skin, no people)
//   S5 protocol the cloud goes; the 2.5% box (step 1, lower left) and DERMA RECOVERY CREAM (its packshot; step 2, higher
//               right), the routine's two products, above the page's step cards; on a phone the pair centred and larger.
//               On a desktop both go back into the dark as the cards scroll up over the scene, and the 2.5% comes forward
//               again in the kit's pose once they have passed
//   S6–S7 kit   the 2.5% box alone in the packshot's pose, the green light behind it: the picture that flies into the
//               offer card
// Left out from the spec (the owner's rule overrides it): the steps and their gold edges, the blurred floating M, the
// contact shadow, the enlarged medallion ring and the milky disc behind the field, the five gold peptide threads and the
// two light particles, the warm surface, the sparks and the ring wave, the drop of serum (none is photographed: the
// spec's own colour note says the product has no drop of its own). The boxes never open and turn only as far as the
// packshots show their sides (the 2.5% and 1.5%: their right side, the view angle never above the packshot's 10°;
// DERMA faces the camera, ≤ 0.5°); their tops stay above the horizon (frame y 601.5) and their feet below it in every
// frame, so no unphotographed face shows. The products keep their print's colours (emissive ≈ 85 % + neutral shading,
// toneMapped off); the line's green (#1E4634, lighter #2F6A50 at a glow's heart) lives only in the glows and the haze.
// No text is drawn but the packages' own print (design/cellular-age-defense-2-5/make_textures.py).
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

  // the camera looks down 2° (the packshot's horizon at 0.34 of the box from its top where the box stands); the boxes
  // stand upright in the world, so the horizon is frame y 601.5 for all of them. `lay` is the same camera without the
  // box's view offset, for placing objects by their frame pixels
  const FOV = 20, EL = rad(2), DIST = 14;
  const camera = new THREE.PerspectiveCamera(FOV, 1.6, 1, 80);
  camera.position.set(0, Math.sin(EL) * DIST, Math.cos(EL) * DIST); camera.lookAt(0, 0, 0);
  const lay = camera.clone(); lay.updateMatrixWorld(); lay.updateProjectionMatrix();
  const fwd = new V3(); lay.getWorldDirection(fwd);
  const RIGHT = new V3(1, 0, 0).applyQuaternion(lay.quaternion), UP = new V3(0, 1, 0).applyQuaternion(lay.quaternion), BACK = fwd.clone().negate();
  const ray = new V3(), TAN = Math.tan(rad(FOV / 2));
  function at(cx, cy, depth, out) {   // the point seen at frame pixel (cx, cy), `depth` in front of the camera
    ray.set(cx / 1200 - 1, 1 - cy / 750, 0.5).unproject(lay).sub(lay.position).normalize();
    return out.copy(lay.position).addScaledVector(ray, depth / ray.dot(fwd));
  }
  const world = (px, depth) => px / 1500 * 2 * depth * TAN;   // frame pixels → world units at that depth
  const pj = new V3();
  const frameOf = (v, out) => { pj.copy(v).project(lay); out[0] = (pj.x + 1) * 1200; out[1] = (1 - pj.y) * 750; return out; };
  const HORIZON = 750 - 750 * Math.tan(EL) / TAN;   // 601.5: a box's top above it and its foot below it hide both
  const D_BOX = DIST + 1.2, D_FIELD = DIST;

  // ---- light: a neutral studio for reflections (PMREM), as the HAIR and EXO-NAD scenes': dark above and below, an even
  // horizon, two tall narrow softboxes either side of the camera, rims behind; a white key from the top left, in front
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
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(i, i, i), side: THREE.DoubleSide }));
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
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(-4, 7, 6); scene.add(key);

  // ---- textures (make_textures.py): the typeset front, the plain side, the two neighbours' fronts as photographed
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy(), NTEX = 4;
  const tex = name => {
    const t = new THREE.TextureLoader().load(new URL(`img/cellular-age-defense-2-5-3d/${name}`, base).href, () => {
      t.needsUpdate = true; renderer.initTexture(t);   // uploaded now, not on the first scroll
      if (++loaded === NTEX) { version++; if (onLoad) onLoad(); }   // the engine redraws the kit picture
    });
    t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const faceTex = tex('box-face.webp'), sideTex = tex('box-side.png'), renewTex = tex('renew-face.webp'), dermaTex = tex('derma-face.webp');
  const TEXS = [faceTex, sideTex, renewTex, dermaTex];

  // ---- materials. The products in their print's colours: emissive 0.85 of the colour plus a neutral shading (a diffuse
  // 0.2 of it under the key and the room), not tone mapped; a dense glossy paper (roughness 0.5, a soft highlight). They
  // come and go by opacity only, never dimmed or tinted
  const SHADE = 0.2;
  const P = (hex, opts = {}) => new THREE.MeshPhysicalMaterial(Object.assign({ color: new THREE.Color(hex).multiplyScalar(SHADE), emissive: hex,
    emissiveIntensity: 0.85, roughness: 0.5, specularIntensity: 0.3, toneMapped: false, transparent: true }, opts));
  const printed = (map, k = 1) => P(new THREE.Color(k, k, k), { color: new THREE.Color(SHADE * k, SHADE * k, SHADE * k), map, emissiveMap: map });
  // the right side: the packshot's side as pipetted (#C0AF99 → #BCA790 → #AE9A83, in box-side.png), raised by what the
  // shading takes off it facing away from the key (×1.06 in linear light), so the side drawn reads as the photo's
  const SIDE_K = 1.06;

  // ---- a box W × 1 × D (scaled per pose), its origin the front's middle (it turns about that upright): the front a plane
  // with the print, the right side the plain strip; the left, the back, the top and the foot closed for any transition's
  // frame but never seen. Front and side are drawn first (they write depth), the closed faces after them: through a
  // fading front nothing behind it shows
  const mkBox = (front, side, hidden, W, D) => {
    const g = new THREE.Group(); scene.add(g); g.visible = false;
    const face = (geo, mat, x, y, z, rx, ry, order) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, 0); m.renderOrder = order; g.add(m); return m; };
    face(new THREE.PlaneGeometry(W, 1), front, 0, 0, 0, 0, 0, 100);
    face(new THREE.PlaneGeometry(D, 1), side, W / 2, 0, -D / 2, 0, Math.PI / 2, 100);
    face(new THREE.PlaneGeometry(D, 1), hidden, -W / 2, 0, -D / 2, 0, -Math.PI / 2, 101);
    face(new THREE.PlaneGeometry(W, 1), hidden, 0, 0, -D, 0, Math.PI, 101);
    face(new THREE.PlaneGeometry(W, D), hidden, 0, 0.5, -D / 2, -Math.PI / 2, 0, 101);
    face(new THREE.PlaneGeometry(W, D), hidden, 0, -0.5, -D / 2, Math.PI / 2, 0, 101);
    return { g, W, D, mats: [front, side, hidden], a: 0, x: 0, y: 0, H: 0, yaw: 0, view: 0 };
  };
  const BW = 1060 / 4076;   // the front's true W : H (the texture's: the photo's front is seen 10° off square)
  const hero = mkBox(printed(faceTex), printed(sideTex, SIDE_K), P(new THREE.Color(0xbca790).multiplyScalar(0.7)), BW, BW);
  // CELL RENEW 1.5%: the same box (both 30 ml, one series; its packshot's front W : H 0.260 too); its side as the 2.5%'s
  const renew = mkBox(printed(renewTex), printed(sideTex, SIDE_K), P(new THREE.Color(0xbca790).multiplyScalar(0.7)), BW, BW);
  // DERMA RECOVERY CREAM: the front 612 × 974 (W : H 0.629), a square base (assumed: no photo of its sides)
  const derma = mkBox(printed(dermaTex), P(0xc9beb2), P(new THREE.Color(0xc9beb2).multiplyScalar(0.7)), 612.4 / 974.1, 612.4 / 974.1);
  const BOXES = [hero, renew, derma];
  const MED = [131.38 / 261.8, 619.99 / 1019, 93.37 / 1019];   // the medallion on the front: u, v of its centre, its radius / H

  // ---- the spicules (BIOSPICULE: the catalogue's needles of a marine sponge, as site/img/spicules-macro.png): glassy
  // spindles pointed at both ends (length : width 18), dark green in their core, light and clear at their rims, the
  // studio's highlights on their glaze. One instanced draw; every instance's place, axis and size set per frame
  const spiGeo = (() => {
    const pts = []; for (let i = 0; i <= 12; i++) { const t = i / 12; pts.push(new THREE.Vector2(0.5 * Math.pow(Math.sin(Math.PI * t), 0.85), t - 0.5)); }
    return new THREE.LatheGeometry(pts, 10);
  })();
  const spiMat = new THREE.MeshPhysicalMaterial({ color: 0x1b2911, roughness: 0.32, metalness: 0, clearcoat: 0.7, clearcoatRoughness: 0.12,
    envMapIntensity: 1.1, transparent: true, toneMapped: false });
  spiMat.onBeforeCompile = sh => {   // the medallion's dark green (#283825 as printed) in the body; a thin lighter rim
    sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float F = pow(1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0), 4.0);
        gl_FragColor.rgb = mix(gl_FragColor.rgb + vec3(0.004, 0.010, 0.002), vec3(0.30, 0.35, 0.25), 0.45 * F); }`);
  };
  spiMat.customProgramCacheKey = () => 'cad25-spicule';
  const NS = 180, NS_PH = 90;   // all, on a phone
  const spicules = new THREE.InstancedMesh(spiGeo, spiMat, NS);
  spicules.instanceMatrix.setUsage(THREE.DynamicDrawUsage); spicules.renderOrder = 30; spicules.frustumCulled = false; spicules.visible = false;
  scene.add(spicules);
  // their seeds: a soft uneven cloud (four overlapping gaussian lobes, cut within 280 px across and 255 px up and down:
  // no figure, no edge), an axis leaning into the picture's plane so the length reads, a length 70…220 px (more short
  // than long), a lag
  const rng = (s => () => { s |= 0; s = s + 0x6d2b79f5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; })(20261022);
  const gau = () => Math.sqrt(-2 * Math.log(Math.max(1e-6, rng()))) * Math.cos(2 * Math.PI * rng());
  const unit = (zk) => { let x, y, z, n; do { x = gau(); y = gau(); z = gau() * zk; n = Math.hypot(x, y, z); } while (n < 1e-3 || Math.abs(z) > 0.6 * n); return [x / n, y / n, z / n]; };
  const LOBES = [[-130, 50, -30, 95], [100, -70, 40, 105], [40, 110, 0, 90], [-40, -120, 60, 80]];   // a drift, not a ball
  const SEED = Array.from({ length: NS }, () => {
    let o; do { const c = LOBES[Math.floor(rng() * LOBES.length)]; o = [c[0] + gau() * c[3], c[1] + gau() * c[3] * 0.9, c[2] + gau() * c[3] * 0.8]; }
    while (Math.hypot(o[0], o[2]) > 280 || Math.abs(o[1]) > 255);
    const L = 70 + 150 * Math.pow(rng(), 1.6);
    return { o, d: unit(0.4), L, lag: rng() * 0.4, ph: rng() * 6.283,
      m: [Math.sqrt(rng()) * 0.62, rng() * 6.283, rng() * 6.283, 0.6 + 0.4 * rng()] };   // m: on the medallion: r, angle, axis angle, length
  });
  // the cloud's centre (frame px) and scale: S3 close in the middle, S4 back to the right of the box
  const FIELD = [680, 750, 1], FIELD4 = [870, 690, 0.6];

  // ---- the line's light, flat to the camera in frame pixels (a plane far behind; local x = px − 1200, y = 750 − py),
  // drawn first: soft shapeless glows, nothing drawn. Each glow adds its colour (× its alpha) and keeps a true alpha, a
  // gaussian reaching 0 at its ellipse with a slope of 2 % of its peak (no edge, no disc), lighter at its heart; it fades
  // out over the scene box's last 48 px
  const ADD = { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.SrcAlphaFactor, blendDst: THREE.OneFactor,
    blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor };
  const fx = new THREE.Group(); scene.add(fx);
  at(1200, 750, DIST + 9, fx.position); fx.quaternion.copy(lay.quaternion); fx.scale.setScalar(world(1, DIST + 9));
  const hex3 = h => new V3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  const QUAD_V = `uniform vec4 uB; varying vec2 vP;
    void main() { vP = mix(uB.xy, uB.zw, position.xy * 0.5 + 0.5); gl_Position = projectionMatrix * modelViewMatrix * vec4(vP.x - 1200.0, 750.0 - vP.y, 0.0, 1.0); }`;
  const SPOT_F = `uniform vec4 uS; uniform float uA; uniform vec3 uC, uE; varying vec2 vP;
    void main() { vec2 q = (vP - uS.xy) / uS.zw; float g = max((exp(-4.0 * dot(q, q)) - 0.018316) / 0.981684, 0.0);
      float e = smoothstep(168.0, 216.0, vP.x) * (1.0 - smoothstep(1200.0, 1248.0, vP.x)) * smoothstep(285.0, 333.0, vP.y) * (1.0 - smoothstep(1167.0, 1215.0, vP.y));
      gl_FragColor = vec4(mix(uE, uC, g), uA * g * e); }`;
  const spot = order => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial(Object.assign({ vertexShader: QUAD_V, fragmentShader: SPOT_F,
      uniforms: { uB: { value: new THREE.Vector4() }, uS: { value: new THREE.Vector4() }, uA: { value: 0 }, uC: { value: hex3(0x2f6a50) }, uE: { value: hex3(0x1e4634) } },
      transparent: true, depthWrite: false, side: THREE.DoubleSide, forceSinglePass: true }, ADD)));   // one pass (QUAD_V mirrors it)
    m.renderOrder = order; m.visible = false; m.frustumCulled = false; fx.add(m); return m;
  };
  const setSpot = (m, cx, cy, rx, ry, a) => {
    const u = m.material.uniforms; u.uS.value.set(cx, cy, rx, ry); u.uB.value.set(cx - rx, cy - ry, cx + rx, cy + ry); u.uA.value = a; m.visible = a > 0.004;
  };
  const glows = [spot(1), spot(1), spot(1)];   // behind each box shown (the 2.5%, the 1.5%, DERMA)
  const haze = spot(2);                        // behind the spicules' cloud

  // ---- poses (frame px). A box [cx, cy: its front's middle, H: its front's height]; every top above the horizon
  // (601.5) and every foot below it in every frame (the poses and their straight mixes keep them so). Where the 2.5%
  // box stands opaque its front is at most 637 frame px tall: 1019 px in a 3840 key (a 1920 px wide screen at DPR 2),
  // the packshot's own front, so its medallion (the print's picture, from the photo) is never drawn above the photo's
  // pixels; a larger box waits for the packaging's print file
  const HERO = [[660, 700, 637], [800, 700, 560], null, [440, 700, 600], [420, 555, 430], [680, 740, 637]];
  // S5, the routine's two products: the 2.5% (step 1) lower left, DERMA (step 2) higher right, its foot 0.17 of the
  // 2.5%'s height above the 2.5%'s foot. DERMA: 0.65 of the 2.5% box's height (assumed)
  const RENEW = [450, 810, 560], DERMA = [700, 555, 280];
  // a phone's stage shows the scene box at ~0.35 css px per frame px: S5 the pair centred in it and larger (the 2.5%
  // 0.8 of the box's height, ~260 css px, the same step up for DERMA); at most ~1.06 device px per frame px there, so
  // the medallion stays under the photo's pixels
  const HERO4_PH = [500, 750, 740], DERMA_PH = [861, 753, 481];
  const TH_PK = rad(10), TH_DERMA = rad(0.5);              // the view angles photographed
  // the kit's glow (S6–S7 and the offer card's picture, which is cut to what has alpha): within the box's height, about
  // twice its width, so the card's picture is the box in its light, not a narrow strip in an empty card
  const KIT_GLOW = 0.6;
  const ST = { hero: [0, 0, 0, 0], renew: [0, 0, 0, 0], derma: [0, 0, 0, 0], mode: 0, e: 0, o: 0, cloud: [0, 0, 1],
    glow: [0, 0, 0], haze: 0, hazeAt: [0, 0, 0, 0] };   // mode: 0 none, 1 leaving the medallion (e), 2 the cloud (at `cloud`: x, y, scale)
  const set4 = (o, x, y, H, a) => { o[0] = x; o[1] = y; o[2] = H; o[3] = a; return o; };
  const mixPose = (o, A, B, s, a) => set4(o, lerp(A[0], B[0], s), lerp(A[1], B[1], s), lerp(A[2], B[2], s), a);
  const setCloud = (A, B, s) => { const c = ST.cloud; for (let i = 0; i < 3; i++) c[i] = lerp(A[i], B[i], s); return c; };
  function story(p, ph) {
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST, H4 = ph ? HERO4_PH : HERO[4], DM = ph ? DERMA_PH : DERMA;
    set4(st.hero, 0, 0, 1, 0); set4(st.renew, 0, 0, 1, 0); set4(st.derma, 0, 0, 1, 0); setCloud(FIELD, FIELD, 0);
    st.mode = 0; st.e = st.o = 0; st.glow[0] = st.glow[1] = st.glow[2] = 0; st.haze = 0;
    if (p >= 5) { mixPose(st.hero, HERO[5], HERO[5], 0, 1); st.glow[0] = KIT_GLOW; return st; }   // the kit: exactly the pose
    if (k === 0) {   // S1 → S2: the 2.5% box steps back and up right; the 1.5% comes in from the left, from the dark
      mixPose(st.hero, HERO[0], HERO[1], smooth(0.05, 0.8, f), 1);
      const s = smooth(0.3, 0.85, f); set4(st.renew, RENEW[0] - 120 * (1 - s), RENEW[1], RENEW[2], s);
      st.glow[0] = lerp(0.8, 0.55, smooth(0.1, 0.8, f)); st.glow[1] = 0.55 * s;
    } else if (k === 1) {   // S2 → S3: the 1.5% recedes and goes; the camera nears the 2.5%'s medallion (its centre to the
      // cloud's, ×1.3), the box fades; its spicules leave the print and spread into the cloud
      const s = smooth(0, 0.3, f); set4(st.renew, RENEW[0], RENEW[1], RENEW[2] * (1 - 0.15 * s), 1 - s);
      const z = smooth(0, 0.55, f), H = HERO[1][2] * (1 + 0.3 * z);
      const m0x = HERO[1][0] + (MED[0] - 0.5) * BW * HERO[1][2], m0y = HERO[1][1] + (MED[1] - 0.5) * HERO[1][2];
      const mx = lerp(m0x, FIELD[0], z), my = lerp(m0y, FIELD[1], z);
      set4(st.hero, mx - (MED[0] - 0.5) * BW * H, my - (MED[1] - 0.5) * H, H, 1 - smooth(0.25, 0.6, f));
      st.mode = 1; st.e = clamp((f - 0.12) / 0.7); st.o = st.e > 0 ? 1 : 0;   // they leave while the box is still there
      st.glow[0] = 0.55 * (1 - smooth(0, 0.4, f)); st.glow[1] = 0.55 * (1 - s);
      st.haze = 0.75 * smooth(0.35, 1, f); set4(st.hazeAt, FIELD[0], FIELD[1], 480, 450);
    } else if (k === 2) {   // S3 → S4: the cloud drifts back to the right, smaller; then the 2.5% box comes back from the
      // dark on its left (clear of the cloud: the box enters once the cloud has moved)
      const s = smooth(0, 0.6, f), h = smooth(0.4, 0.9, f), c = setCloud(FIELD, FIELD4, s);
      st.mode = 2; st.o = 1;
      set4(st.hero, HERO[3][0] - 100 * (1 - h), HERO[3][1], HERO[3][2], h); st.glow[0] = 0.6 * h;
      st.haze = lerp(0.75, 0.5, s); set4(st.hazeAt, c[0], c[1], 480 * c[2], 450 * c[2]);
    } else if (k === 3) {   // S4 → S5: the cloud fades where it is; the 2.5% box takes step 1 and DERMA comes in from the dark
      const s = smooth(0, 0.35, f), d = smooth(0.45, 0.8, f), c = setCloud(FIELD4, FIELD4, 0);
      st.mode = 2; st.o = 1 - s;
      st.haze = 0.5 * (1 - s); set4(st.hazeAt, c[0], c[1], 480 * c[2], 450 * c[2]);
      const m = smooth(0.1, 0.7, f); mixPose(st.hero, HERO[3], H4, m, 1);
      set4(st.derma, DM[0], DM[1], DM[2] * (0.9 + 0.1 * d), d);
      st.glow[0] = lerp(0.6, 0.5, m); st.glow[2] = 0.5 * smooth(0.6, 1, f);
    } else if (ph) {   // S5 → kit on a phone (the copy scrolls under the stage): both hold, DERMA goes, the 2.5% comes forward
      const d = smooth(0.45, 0.7, f); set4(st.derma, DM[0], DM[1], DM[2] * (1 - 0.1 * d), 1 - d);
      mixPose(st.hero, H4, HERO[5], smooth(0.5, 1, f), 1);
      st.glow[0] = 0.5 * (1 - smooth(0.4, 0.6, f)) + KIT_GLOW * smooth(0.75, 1, f); st.glow[2] = 0.5 * (1 - d);
    } else {   // S5 → kit on a desktop: the page's three step cards scroll up over the scene's whole width. Their top meets
      // the boxes' feet as the hold at p = 4 ends (1920×1080) or by f ≈ 0.05 (1440×900), 0.15 (960×600); their foot clears
      // the kit's top (frame y 421) at f ≈ 0.42, 0.5, 0.63. So both products go back into the dark as the cards come
      // (none of them under a card), and the 2.5% comes forward again in the kit's pose once the cards have passed
      const out = smooth(0, 0.06, f), back = smooth(0.64, 0.85, f);
      if (f < 0.3) set4(st.hero, H4[0], H4[1], H4[2] * (1 - 0.06 * out), 1 - out);
      else set4(st.hero, HERO[5][0], HERO[5][1], HERO[5][2] * (0.94 + 0.06 * back), back);
      set4(st.derma, DM[0], DM[1], DM[2] * (1 - 0.06 * out), 1 - out);
      st.glow[0] = f < 0.3 ? 0.5 : KIT_GLOW; st.glow[2] = 0.5;   // × each box's opacity (pose)
    }
    return st;
  }

  // ---- applying a state (in place: nothing allocated per frame)
  const tmp = new V3(), tmp2 = new V3(), toCam = new V3();
  function placeBox(B, s, th, D) {   // s: [cx, cy, H, a]; th: the view angle (+: the right side shows)
    B.g.visible = s[3] > 0.004; B.a = s[3];   // placed even when hidden: the spicules leave its medallion as it fades
    at(s[0], s[1], D, B.g.position); B.g.scale.setScalar(world(s[2], D));
    toCam.copy(lay.position).sub(B.g.position);
    B.yaw = Math.atan2(toCam.x, toCam.z) - th; B.g.rotation.set(0, B.yaw, 0); B.g.updateMatrixWorld(true);
    B.x = s[0]; B.y = s[1]; B.H = s[2]; B.view = th;
    for (const m of B.mats) m.opacity = s[3];
  }
  const local = (B, x, y, z, out) => frameOf(tmp.set(x, y, z).applyMatrix4(B.g.matrixWorld), out);
  // the instances: a spindle's matrix from its middle, its axis (unit), its length and width (world units)
  const qa = new THREE.Quaternion(), Y = new V3(0, 1, 0), sc = new V3(), mat4 = new THREE.Matrix4();
  const pos = new V3(), dir = new V3(), p0 = new V3(), d0 = new V3(), p1 = new V3(), d1 = new V3(), mq = new THREE.Quaternion();
  function inField(s, phi, t, live, P, Dv) {   // a spicule in the cloud, turning about the upright through its centre
    const C = ST.cloud, c = Math.cos(phi), sn = Math.sin(phi), u = world(1, D_FIELD) * C[2], bob = 4 * Math.sin(t * 0.7 + s.ph) * live;
    const ox = s.o[0] * c + s.o[2] * sn, oz = -s.o[0] * sn + s.o[2] * c;
    at(C[0], C[1], D_FIELD, P); P.addScaledVector(RIGHT, ox * u).addScaledVector(UP, -(s.o[1] + bob) * u).addScaledVector(BACK, oz * u);
    const dx = s.d[0] * c + s.d[2] * sn, dz = -s.d[0] * sn + s.d[2] * c;
    Dv.set(0, 0, 0).addScaledVector(RIGHT, dx).addScaledVector(UP, -s.d[1]).addScaledVector(BACK, dz).normalize();
    return s.L * u;
  }
  function onPrint(s, P, Dv) {   // a spicule lying on the 2.5% box's medallion, as printed
    const r = s.m[0] * MED[2], x = (MED[0] - 0.5) * BW + r * Math.cos(s.m[1]), y = (0.5 - MED[1]) + r * Math.sin(s.m[1]);
    P.set(x, y, 0.012).applyMatrix4(hero.g.matrixWorld);
    Dv.set(Math.cos(s.m[2]), Math.sin(s.m[2]), 0).applyQuaternion(hero.g.quaternion).normalize();
    return 1.9 * MED[2] * s.m[3] * hero.g.scale.x * 0.5;
  }
  function pose(p, t, still) {
    const ph = phone.matches, st = story(p, ph), live = still ? 0 : 1 - smooth(4.85, 5, p);
    // the boxes: the 2.5% and the 1.5% at the packshot's view angle, swaying toward the front (0…3°, 9 s) while they live:
    // never more of the side than photographed; DERMA square to the camera
    const sway = rad(1.5) * (1 - Math.cos(t * 2 * Math.PI / 9)) * live;
    placeBox(hero, st.hero, TH_PK - sway, D_BOX); placeBox(renew, st.renew, TH_PK - sway, D_BOX); placeBox(derma, st.derma, TH_DERMA, D_BOX);
    // the glows behind the boxes: 1.9 × the front's width either side, 0.62 of its height up and down
    for (let i = 0; i < 3; i++) {
      const B = BOXES[i], a = st.glow[i] * B.a;
      if (a > 0.004 && B.g.visible) setSpot(glows[i], B.x, B.y, 1.9 * B.W * B.H, 0.62 * B.H, a); else glows[i].visible = false;
    }
    setSpot(haze, st.hazeAt[0], st.hazeAt[1], st.hazeAt[2], st.hazeAt[3], st.haze);
    // the spicules
    spicules.visible = st.mode > 0 && st.o > 0.004;
    if (spicules.visible) {
      const n = ph ? NS_PH : NS, phi = live * t * 2 * Math.PI / 90;
      spiMat.opacity = st.o; spicules.count = n;
      for (let i = 0; i < n; i++) {
        const s = SEED[i];
        let L, vis = 1;
        if (st.mode === 1) {
          const q = smooth(0, 1, (st.e - s.lag) / 0.6);
          const La = onPrint(s, p0, d0), Lb = inField(s, phi, t, live, p1, d1);
          pos.lerpVectors(p0, p1, q); dir.lerpVectors(d0, d1, q).normalize(); L = lerp(La, Lb, q); vis = smooth(0, 0.12, q);
        } else L = inField(s, phi, t, live, pos, dir);
        L *= vis;
        if (L < 1e-5) { mat4.makeScale(0, 0, 0); spicules.setMatrixAt(i, mat4); continue; }
        qa.setFromUnitVectors(Y, dir); sc.set(L / 18, L, L / 18); mat4.compose(pos, qa, sc); spicules.setMatrixAt(i, mat4);
      }
      spicules.instanceMatrix.needsUpdate = true;
    }
    last.t = t; last.n = spicules.visible ? spicules.count : 0;
  }
  const last = { t: 0, n: 0 };
  function cloudBox() {   // QA: the projected tips of the spicules drawn last (frame px)
    if (!spicules.visible) return null;
    const b = [Infinity, Infinity, -Infinity, -Infinity], o = [0, 0];
    for (let i = 0; i < spicules.count; i++) {
      spicules.getMatrixAt(i, mat4); mat4.decompose(pos, mq, sc); if (sc.y < 1e-5) continue;
      dir.set(0, 1, 0).applyQuaternion(mq);
      for (const k of [-0.5, 0.5]) { frameOf(tmp2.copy(pos).addScaledVector(dir, k * sc.y), o); b[0] = Math.min(b[0], o[0]); b[1] = Math.min(b[1], o[1]); b[2] = Math.max(b[2], o[0]); b[3] = Math.max(b[3], o[1]); }
    }
    return b.map(Math.round);
  }
  // QA: where to pipette (frame px rectangles) in the pose drawn last: the front's empty paper and the band, the side
  function probes(B, paper, band) {
    if (!B.g.visible || B.a < 0.99) return null;
    const rect = (u0, u1, v0, v1) => { const a = local(B, (u0 - 0.5) * B.W, 0.5 - v0, 0, [0, 0]), b = local(B, (u1 - 0.5) * B.W, 0.5 - v1, 0, [0, 0]);
      return [Math.round(Math.min(a[0], b[0])), Math.round(Math.min(a[1], b[1])), Math.round(Math.max(a[0], b[0])), Math.round(Math.max(a[1], b[1]))]; };
    const s0 = local(B, B.W / 2, 0.05, -0.3 * B.D, [0, 0]), s1 = local(B, B.W / 2, -0.05, -0.7 * B.D, [0, 0]);
    return { paper: rect(...paper), band: rect(...band), side: B === derma ? null : [s0[0], s0[1], s1[0], s1[1]].map(Math.round),
      top: Math.round(local(B, 0, 0.5, 0, [0, 0])[1]), foot: Math.round(local(B, 0, -0.5, 0, [0, 0])[1]) };
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
  }
  function warm() {   // every program before the first frame shows (all objects on for the compile, then as they were)
    const was = []; scene.traverse(o => { was.push(o.visible); o.visible = true; });
    renderer.compile(scene, camera);
    let i = 0; scene.traverse(o => { o.visible = was[i++]; }); compiled = true;
  }
  function render(p, view) {
    pr = Math.min(full(view), cap); fit(view, pr); pose(p, view.still ? 0 : view.t, view.still);
    if (!compiled) warm();
    renderer.render(scene, camera); renders++;
  }
  function draw(p, view) { pace(performance.now(), view.still); lastP = p; lastView = view; render(p, view); }
  let kits = 0;   // kit pictures rendered (QA: none on a phone, none for a toolbar)
  function kit(view) {   // the kit pose rendered once into a picture (the offer card, the flight into it), then the current pose again
    kits++;
    fit(view, view.dpr); pose(5, 0, true); if (!compiled) warm(); renderer.render(scene, camera);
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
    spicules.dispose();   // its instance matrix's buffer (not freed with the geometry)
    for (const t of TEXS.concat([roomEnv])) t.dispose();
    renderer.dispose();
  }
  const r1 = v => Math.round(v * 10) / 10, r2 = v => Math.round(v * 100) / 100;
  const boxState = B => (B.g.visible ? { x: r1(B.x), y: r1(B.y), H: r1(B.H), yaw: r1(deg(B.yaw)), view: r1(deg(B.view)), a: r2(B.a) } : null);
  const state = () => ({ quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded,
    version, kits, lastP, horizon: r1(HORIZON), hero: boxState(hero), renew: boxState(renew), derma: boxState(derma),
    field: { n: last.n, o: r2(spicules.visible ? spiMat.opacity : 0), bbox: cloudBox() },
    glow: glows.map(g => r2(g.visible ? g.material.uniforms.uA.value : 0)), haze: r2(haze.visible ? haze.material.uniforms.uA.value : 0),
    probes: { hero: probes(hero, [0.30, 0.70, 0.47, 0.505], [0.10, 0.90, 0.335, 0.352]), renew: probes(renew, [0.30, 0.70, 0.485, 0.51], [0.06, 0.20, 0.30, 0.34]),
      derma: probes(derma, [0.05, 0.25, 0.58, 0.72], [0.03, 0.11, 0.37, 0.46]) } });
  return { draw, kit, dispose, state, animated: true };
}
