// EXOSIGNAL HAIR live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D
// scene, as the approved sample EXOTECH GEL (scenes/exotech-gel.js). The engine keeps the story geometry (the cover-fitted
// 16:10 frame, the run's box, the phone stage, the kit card); this module draws the pose for the story position into the
// box. Objects are placed by frame pixel (2400×1500), measured on the only packshot, protocols/print/img/exosignal-hair.webp:
// the matte black box seen square on and five glass ampoules before its lower right corner, 1 + 2 + 2 (scale 0.885, the
// photo's origin at (215, 435)). The story (site/story3d.json, as revised for the page): S1 the packshot; S2 the left
// ampoule steps out, a gold measuring target (the MITOSCAN screen's mark) over faint falling hairs, a hair that crosses
// it flashes gold; S3 the ampoule close, turned to its small print (the page draws the exosomes, PDRN and the DNA helix);
// S4 a gold scalp line, four strands grow from it, the fourth tallest; S5 the line becomes the protocol's: MITOSCAN and
// MITOPEN (their packshots, dimmed, neutral) and the ampoule on it with the line's gold under it; S6–S7 the box comes back,
// the five ampoules stand in a row before it, then one by one go back into the packshot's pose (the kit card's picture).
// Nothing is opened: the photos show no ampoule opened (story3d's open question). The product keeps its print's colours
// (emissive ≈ 85 % + neutral shading, toneMapped off); the line's gold lives only around it (target, hairs, strands,
// line, glows). No text is drawn but the package's own print (design/exosignal-hair/make_textures.py).
//
// createScene(THREE, { canvas, base, onLoad }) → { draw(p, view), kit(view) → canvas, animated, state(), dispose() }
//   p: the story position 0…5 (run index + progress); view: { cover, box, dpr, t, still } from the engine
export function createScene(THREE, { canvas, base, onLoad }) {
  const V3 = THREE.Vector3, rad = THREE.MathUtils.degToRad;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  const lerp = (a, b, s) => a + (b - a) * s;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  const scene = new THREE.Scene();

  // the camera looks down 4° (the box's top edge at eye level: its top face never shows); `lay` is the same camera
  // without the box's view offset, for placing objects by their frame pixels
  const FOV = 20, EL = rad(4), DIST = 14;
  const camera = new THREE.PerspectiveCamera(FOV, 1.6, 1, 80);
  camera.position.set(0, Math.sin(EL) * DIST, Math.cos(EL) * DIST); camera.lookAt(0, 0, 0);
  const lay = camera.clone(); lay.updateMatrixWorld(); lay.updateProjectionMatrix();
  const fwd = new V3(); lay.getWorldDirection(fwd);
  const ray = new V3(), TAN = Math.tan(rad(FOV / 2));
  function at(cx, cy, depth, out) {   // the point seen at frame pixel (cx, cy), `depth` in front of the camera
    ray.set(cx / 1200 - 1, 1 - cy / 750, 0.5).unproject(lay).sub(lay.position).normalize();
    return out.copy(lay.position).addScaledVector(ray, depth / ray.dot(fwd));
  }
  const world = (px, depth) => px / 1500 * 2 * depth * TAN;   // frame pixels → world units at that depth

  // ---- light: a neutral studio for reflections (PMREM): dark above and below, an even horizon, two tall narrow
  // softboxes either side of the camera, rims behind. The glass has its own room without the two front softboxes: in the
  // packshot an ampoule's body is clear over its label, bright only at its edges (the rims) and at the liquid's surface
  function makeEnv(glass) {
    const pm = new THREE.PMREMGenerator(renderer), room = new THREE.Scene();
    const dome = new THREE.SphereGeometry(30, 48, 32), col = [], c = new THREE.Color();
    for (let i = 0; i < dome.attributes.position.count; i++) {
      const y = dome.attributes.position.getY(i) / 30;   // −1 floor … 1 ceiling
      c.setRGB(1, 1, 1.02).multiplyScalar(0.05 + 0.18 * Math.exp(-(y * y) / 0.06)); col.push(c.r, c.g, c.b);
    }
    dome.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    room.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const panel = (i, x, y, z, w, h) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(i, i, i), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, y, 0); room.add(m);
    };
    if (!glass) { panel(5, -5.7, 1, 8.2, 2.4, 9); panel(2.5, 6.4, 1, 7.7, 1.6, 9); }   // ±35–40° from the camera, the left one the key
    else panel(0.4, 0, 1, 12, 24, 12);   // the glass: a broad dim wall behind the camera instead (the body a little lighter)
    panel(2.5, -9, 1.5, -7, 2.5, 9); panel(2, 9, 2, -7, 2.5, 9);     // rims from behind
    const rt = pm.fromScene(room, 0.02); pm.dispose();
    room.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    return rt;   // its target: disposing that frees the framebuffer too, not only the texture
  }
  let roomEnv = makeEnv(false), glassEnvRT = makeEnv(true), glassEnv = glassEnvRT.texture;
  scene.environment = roomEnv.texture;
  // after a lost context three.js restores image textures, not the rendered environments: rebuild them, and have the
  // engine redraw (the kit picture too), also under reduced motion
  const restored = () => {
    const old = [roomEnv, glassEnvRT];
    roomEnv = makeEnv(false); glassEnvRT = makeEnv(true); glassEnv = glassEnvRT.texture; scene.environment = roomEnv.texture;
    old.forEach(t => t.dispose()); size = '';
    for (const a of amps) for (const k of ['back', 'front', 'liquid']) a.m[k].envMap = glassEnv;
    version++; if (onLoad) onLoad();
  };
  canvas.addEventListener('webglcontextrestored', restored);
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(4, 6, 6); scene.add(key);   // top right: the
  // packshot's front is lighter there

  // ---- textures: the typeset print (make_textures.py) and the two devices' packshots (S5), as they are
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy();
  const tex = (name, srgb) => {
    const t = new THREE.TextureLoader().load(new URL(`img/exosignal-hair-3d/${name}`, base).href, () => {
      t.needsUpdate = true; if (++loaded === 5) { version++; if (onLoad) onLoad(); }   // the engine redraws the kit picture
    });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const faceTex = tex('box-face.png', true), metalTex = tex('box-metal.png'), printTex = tex('amp-print.png');
  const scanTex = tex('mitoscan.webp', true), penTex = tex('mitopen.webp', true);

  // ---- materials. The product in its print's colours: emissive 0.85 of the colour plus a neutral shading (a diffuse
  // 0.2 of it under the key and the room, ≈ 0.15 of the colour lit), not tone mapped; the foil a satin metal (roughness
  // 0.28) whose reflection gives the rest. Nothing on the product is dimmed or masked: it comes and goes by opacity only
  const SHADE = 0.2;
  const P = (hex, opts = {}) => new THREE.MeshPhysicalMaterial(Object.assign({ color: new THREE.Color(hex).multiplyScalar(SHADE), emissive: hex,
    emissiveIntensity: 0.85, roughness: 0.7, specularIntensity: 0.3, toneMapped: false, transparent: true }, opts));
  const facade = P(0xffffff, { color: 0xffffff, map: faceTex, emissiveMap: faceTex, metalnessMap: metalTex,   // the foil's
    roughnessMap: metalTex, metalness: 1, roughness: 0.65, specularIntensity: 0.08, envMapIntensity: 0.7 });  // F0 its colour
  // the front's paper and ink take the packshot's light: lighter toward the right and the top right (the key from there),
  // measured on its bare paper as F = lightness / the reference patch's (u 0.15–0.25, v 0.30–0.40), smoothed (rms 0.06):
  // F 0.88 top left … 1.0 at the patch … 1.6–1.9 top right. Emissive (0.85) and the room's faint reflection give the
  // colour itself (1.0, measured in the key), the diffuse the rest: LIT = 1 / its share of the colour per unit (0.56,
  // measured), so the patch keeps #161516; the foil (metal) has no diffuse
  const LIT = 1.79;
  facade.onBeforeCompile = sh => {
    sh.fragmentShader = sh.fragmentShader.replace('#include <lights_physical_fragment>', `#include <lights_physical_fragment>
      { float u = vMapUv.x, v = 1.0 - vMapUv.y;   // u right, v down: as on the photo
        float F = clamp(0.816 + 0.4046 * u + 0.9017 * u * u + 0.2115 * v + 0.2952 * u * v - 1.3075 * u * u * v, 0.88, 1.9);
        material.diffuseColor *= ${LIT.toFixed(3)} * max(F - 1.0, 0.0); }`);
  };
  const paper = P(0x161516, { specularIntensity: 0.08 });   // the box's other sides: the same black paper, no print
  const boxMats = [facade, paper];
  // glass: no transmission (on a transparent canvas it cannot see the page's smoke, and a phone pays a pass for it):
  // its opacity follows Fresnel and its own highlights, so edges and highlights read and the body stays clear
  function glassMat(side, a0, aF, aS) {
    const m = new THREE.MeshPhysicalMaterial({ color: 0x0b0b0c, roughness: 0.04, ior: 1.5, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.6,
      envMap: glassEnv, transparent: true, depthWrite: false, side });
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
    m.customProgramCacheKey = () => 'glass' + k.join();
    return m;
  }

  // ---- the ampoule, height 1 (scaled by HW): a lathe of the profile measured on the photo (fractions of the height
  // from the foot: r 0.100 body to h 0.523, the shoulder, a waist, a bulb, the neck under the white ring at 0.708–0.725,
  // the head tube r 0.042, a flattened dome), the colourless liquid to h 0.41, its surface (a bright filled ellipse seen at a
  // grazing angle, as in the packshot, and a bright front edge), the ring, the black print
  const V2 = (r, h) => new THREE.Vector2(r, h);
  const neck = new THREE.SplineCurve([V2(0.1, 0.523), V2(0.088, 0.542), V2(0.067, 0.558), V2(0.06, 0.583), V2(0.064, 0.628), V2(0.058, 0.653),
    V2(0.05, 0.675), V2(0.0445, 0.693), V2(0.0445, 0.708)]).getPoints(48);
  const PROFILE = [V2(0, 0), V2(0.07, 0), V2(0.085, 0.002), V2(0.093, 0.008), V2(0.098, 0.017), V2(0.1, 0.031)].concat(neck,
    [V2(0.0445, 0.725), V2(0.042, 0.733), V2(0.042, 0.976)], [0.25, 0.5, 0.75, 0.9, 1].map(s => V2(0.042 * Math.cos(s * Math.PI / 2), 0.976 + 0.024 * Math.sin(s * Math.PI / 2))));
  const LIQ = 0.41;
  const glassGeo = new THREE.LatheGeometry(PROFILE, 96);
  const liquidGeo = new THREE.LatheGeometry([V2(0, 0.006), V2(0.079, 0.006), V2(0.09, 0.012), V2(0.093, 0.03), V2(0.093, LIQ), V2(0, LIQ)], 96);
  const surfaceGeo = new THREE.CircleGeometry(0.0925, 96).rotateX(-Math.PI / 2).translate(0, LIQ, 0);
  const meniscusGeo = new THREE.CylinderGeometry(0.0935, 0.0935, 0.012, 96, 1, true).translate(0, LIQ - 0.004, 0);
  const ringGeo = new THREE.CylinderGeometry(0.0452, 0.0452, 0.017, 96, 1, true).translate(0, 0.7165, 0);
  const printGeo = new THREE.CylinderGeometry(0.1002, 0.1002, 0.4, 160, 1, true, rad(-14), rad(110)).translate(0, 0.3, 0);   // θ −14…+96, h 0.10…0.50
  const HW = 1.2, KH = HW * 750 / TAN;   // the ampoule's height in world units; an ampoule H px tall stands at depth KH / H
  const SURF = 0.4, MEN = 0.6;   // the liquid's surface and its front edge: opacities
  const amps = [0, 1, 2, 3, 4].map(() => {
    const g = new THREE.Group(); g.rotation.order = 'XZY'; g.scale.setScalar(HW); scene.add(g);
    const m = {
      back: glassMat(THREE.BackSide, 0.02, 0.3, 0.7), front: glassMat(THREE.FrontSide, 0.04, 0.55, 1.0), liquid: glassMat(THREE.FrontSide, 0.04, 0.45, 0.6),
      surface: new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: SURF, depthWrite: false, toneMapped: false }),
      meniscus: new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: MEN, depthWrite: false, toneMapped: false }),   // its front arc
      ring: P(0xf1ece8, { roughness: 0.4, side: THREE.DoubleSide, forceSinglePass: true }),   // one pass: its back half shows through
      print: P(0x232021, { alphaMap: printTex, depthWrite: false, roughness: 0.45, polygonOffset: true, polygonOffsetFactor: -2 }),
    };
    // drawn in this order (renderOrder rank × 10 + layer): back of the glass, liquid, its surface and edge, ring, front of
    // the glass, the print over it (it is on the glass's outside)
    const layer = [[glassGeo, m.back], [liquidGeo, m.liquid], [surfaceGeo, m.surface], [meniscusGeo, m.meniscus], [ringGeo, m.ring], [glassGeo, m.front], [printGeo, m.print]]
      .map(([geo, mat]) => { const x = new THREE.Mesh(geo, mat); g.add(x); return x; });
    return { g, m, layer };
  });

  // ---- the box: the front 1.474 : 1 (as photographed), its depth unknown: a thin flat box, 0.16 of the width
  const BWr = 1.474, BD = 0.16 * BWr, box = new THREE.Group(); scene.add(box);
  const face = (geo, mat, x, y, z, rx, ry) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, 0); m.renderOrder = 2; box.add(m); return m; };
  face(new THREE.PlaneGeometry(BWr, 1), facade, 0, 0, 0, 0, 0).renderOrder = 3;
  face(new THREE.PlaneGeometry(BWr, BD), paper, 0, 0.5, -BD / 2, -Math.PI / 2, 0);
  face(new THREE.PlaneGeometry(BWr, BD), paper, 0, -0.5, -BD / 2, Math.PI / 2, 0);
  face(new THREE.PlaneGeometry(BD, 1), paper, -BWr / 2, 0, -BD / 2, 0, -Math.PI / 2);
  face(new THREE.PlaneGeometry(BD, 1), paper, BWr / 2, 0, -BD / 2, 0, Math.PI / 2);
  face(new THREE.PlaneGeometry(BWr, 1), paper, 0, 0, -BD, 0, Math.PI);
  const FH0 = 564.2, KF = FH0 * (DIST + 1.2), FHW = world(FH0, DIST + 1.2);   // the front FH0 px tall stands at DIST + 1.2
  box.scale.setScalar(FHW);

  // ---- the line's graphics, flat to the camera in frame pixels (a plane at a depth; local x = px − 1200, y = 750 − py):
  // strokes with a soft edge, at least 1.5 device px wide, drawn up to a time (uDraw); gold of the HAIR line only
  const pxU = { value: 1 };   // device px per frame px
  const plane = D => { const g = new THREE.Group(); scene.add(g); place(g, D); return g; };
  const place = (g, D) => { at(1200, 750, D, g.position); g.quaternion.copy(lay.quaternion); g.scale.setScalar(world(1, D)); };
  const hex3 = h => new THREE.Vector3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  const STROKE_V = `attribute float aSide, aHalf, aCore, aT, aU; uniform float uSway;
    varying float vSide, vHalf, vCore, vT, vU, vPx;
    void main() { vSide = aSide; vHalf = aHalf; vCore = aCore; vT = aT; vU = aU; vec3 p = position; p.x += uSway * aU * aU; vPx = p.x + 1200.0;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }`;
  const STROKE_F = `uniform vec3 uA, uB, uCreamCol; uniform float uOpacity, uDraw, uPx, uGlow, uGlowA, uXL, uSplit, uCream;
    varying float vSide, vHalf, vCore, vT, vU, vPx;
    void main() {
      float d = abs(vSide) * vHalf, c = max(vCore * uPx, 0.75);
      float a = clamp(c + 0.5 - d * uPx, 0.0, 1.0);
      if (uGlow > 0.0) a = max(a, uGlowA * exp(-(d * d) / (uGlow * uGlow)));
      a *= clamp((uDraw - vT) * 60.0, 0.0, 1.0) * uOpacity;
      vec3 col = mix(uA, uB, vU);
      #ifdef LINE
      a *= smoothstep(uXL, uXL + 24.0, vPx) * (1.0 - smoothstep(1170.0, 1200.0, vPx));
      float cr = uCream * smoothstep(uSplit - 50.0, uSplit + 50.0, vPx);
      col = mix(col, uCreamCol, cr); a *= mix(1.0, 0.35, cr);
      #endif
      gl_FragColor = vec4(col, a);
    }`;
  function strokeMat(a, b, o = {}) {
    return new THREE.ShaderMaterial({ vertexShader: STROKE_V, fragmentShader: STROKE_F, transparent: true, depthWrite: false, side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending, defines: o.line ? { LINE: 1 } : {},
      uniforms: { uA: { value: hex3(a) }, uB: { value: hex3(b) }, uCreamCol: { value: hex3(0xf6f3ec) }, uOpacity: { value: 1 }, uDraw: { value: 1 },
        uPx: pxU, uGlow: { value: o.glow || 0 }, uGlowA: { value: o.glowA || 0 }, uXL: { value: 0 }, uSplit: { value: 600 }, uCream: { value: 0 }, uSway: { value: 0 } } });
  }
  function strokes(list) {   // [{ pts: [[x, y] frame px], core: s → half width px, t: s → draw time, ext: geometry half width }]
    const pos = [], side = [], half = [], core = [], tt = [], uu = [], idx = [];
    for (const s of list) {
      const n = s.pts.length, b0 = pos.length / 3;
      for (let i = 0; i < n; i++) {
        const [x, y] = s.pts[i], [xa, ya] = s.pts[Math.max(0, i - 1)], [xb, yb] = s.pts[Math.min(n - 1, i + 1)];
        const l = Math.hypot(xb - xa, yb - ya) || 1, nx = -(yb - ya) / l, ny = (xb - xa) / l, u = i / (n - 1);
        for (const sd of [-1, 1]) { pos.push(x + nx * s.ext * sd - 1200, 750 - (y + ny * s.ext * sd), 0); side.push(sd); half.push(s.ext); core.push(s.core(u)); tt.push(s.t(u)); uu.push(u); }
        if (i) { const a = b0 + (i - 1) * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
      }
    }
    const g = new THREE.BufferGeometry(); g.setIndex(idx);
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    for (const [k, v] of [['aSide', side], ['aHalf', half], ['aCore', core], ['aT', tt], ['aU', uu]]) g.setAttribute(k, new THREE.Float32BufferAttribute(v, 1));
    return g;
  }
  const SPOT_F = `uniform vec3 uC; uniform float uOpacity; varying vec2 vUv;
    void main() { vec2 q = vUv * 2.0 - 1.0; float r2 = dot(q, q); gl_FragColor = vec4(uC, uOpacity * exp(-3.0 * r2) * (1.0 - smoothstep(0.5, 1.0, r2))); }`;
  const spotMat = c => new THREE.ShaderMaterial({ vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: SPOT_F, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, uniforms: { uC: { value: hex3(c) }, uOpacity: { value: 0 } } });
  const spot = (parent, c, cx, cy, rx, ry, order) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), spotMat(c)); m.position.set(cx - 1200, 750 - cy, 0); m.scale.set(rx, ry, 1); m.renderOrder = order; parent.add(m); return m; };

  // S2: the measuring target (the MITOSCAN screen's mark: three rings, a cross through them with gaps at the rings, a dot;
  // 72 ticks every 5° round the outer ring, every fourth longer), drawn rings first by angle, then ticks, then the arms
  // out from the centre; over it faint hairs fall, and one whose middle enters the inner circle flashes gold for 0.4 s.
  // S2 stands right in the 3D box: the page's exosome field fills its left part there (measured on the built page at
  // 1440×900, 1512×982 and 1920×1080 while S2 is read: no cell over the target, none over the hero's head)
  const TX = 1000, TY = 760, TR = 170, D_FX = 11;
  const fx = plane(D_FX);
  const tlist = [];
  [1, 0.74, 0.55].forEach((k, j) => {
    const r = TR * k, ga = 0.04 * TR / r;
    for (let q = 0; q < 4; q++) {
      const a0 = q * Math.PI / 2 + ga, a1 = (q + 1) * Math.PI / 2 - ga, pts = [];
      for (let i = 0; i <= 24; i++) { const a = a0 + (a1 - a0) * i / 24; pts.push([TX + Math.cos(a) * r, TY - Math.sin(a) * r]); }
      tlist.push({ pts, core: () => 1.1, ext: 5, t: u => 0.03 * j + 0.42 * (a0 + (a1 - a0) * u) / (2 * Math.PI) });
    }
  });
  for (let i = 0; i < 72; i++) {
    if (i % 18 === 0) continue;   // not under the arms
    const a = i * Math.PI / 36, L = i % 4 === 0 ? 16 : 8, r0 = TR + 6;
    tlist.push({ pts: [[TX + Math.cos(a) * r0, TY - Math.sin(a) * r0], [TX + Math.cos(a) * (r0 + L), TY - Math.sin(a) * (r0 + L)]], core: () => 0.8, ext: 4, t: () => 0.5 + 0.25 * i / 72 });
  }
  for (let q = 0; q < 4; q++) {
    const c = Math.cos(q * Math.PI / 2), s = Math.sin(q * Math.PI / 2);
    for (const [r0, r1] of [[0.08, 0.51], [0.59, 0.70], [0.78, 0.96], [1.04, 1.18]]) {
      const pts = [0, 1, 2, 3, 4].map(i => { const r = TR * (r0 + (r1 - r0) * i / 4); return [TX + c * r, TY - s * r]; });
      tlist.push({ pts, core: () => (r0 < 0.3 ? 1.3 : 1.1), ext: 5, t: u => 0.75 + 0.25 * (r0 + (r1 - r0) * u) / 1.18 });
    }
  }
  const dot = []; for (let i = 0; i <= 24; i++) dot.push([TX + 3 * Math.cos(i * Math.PI / 12), TY + 3 * Math.sin(i * Math.PI / 12)]);
  tlist.push({ pts: dot, core: () => 3, ext: 6, t: () => 0.75 });
  const targetMat = strokeMat(0xd8bd7e, 0xc9a24b);
  const target = new THREE.Mesh(strokes(tlist), targetMat); target.renderOrder = 7; fx.add(target);
  // the hairs: one instanced strip, all motion in the vertex shader (no matrices on the CPU); a seeded field
  const NT = 36, TB = [800, 1200, 320, 1180], SPEED = 60;
  const rng = (s => () => { s |= 0; s = s + 0x6d2b79f5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; })(20261021);
  const hairs = [];
  for (let i = 0; i < NT; i++) hairs.push([TB[0] + ((i * 0.618034) % 1) * (TB[1] - TB[0]), rng(), 40 + 70 * rng(), rng() * 2 - 1, SPEED * (0.85 + 0.3 * rng()), rng() * 6.283]);
  const hg = new THREE.InstancedBufferGeometry(), hs = [], hidx = [];
  for (let i = 0; i <= 12; i++) { hs.push(i / 12, -1, i / 12, 1); if (i) hidx.push((i - 1) * 2, (i - 1) * 2 + 1, i * 2, (i - 1) * 2 + 1, i * 2 + 1, i * 2); }
  hg.setIndex(hidx); hg.setAttribute('position', new THREE.Float32BufferAttribute(new Array(26 * 3).fill(0), 3));
  hg.setAttribute('aS', new THREE.Float32BufferAttribute(hs, 2));
  hg.setAttribute('aI', new THREE.InstancedBufferAttribute(new Float32Array(hairs.flatMap(h => h.slice(0, 4))), 4));
  hg.setAttribute('aJ', new THREE.InstancedBufferAttribute(new Float32Array(hairs.flatMap(h => h.slice(4))), 2));
  hg.instanceCount = NT;
  const hairMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { uTime: { value: 0 }, uPx: pxU, uT: { value: new V3(TX, TY, 0.55 * TR) }, uOpacity: { value: 0 }, uFlashOn: { value: 0 } },
    vertexShader: `attribute vec2 aS; attribute vec4 aI; attribute vec2 aJ; uniform float uTime, uPx; uniform vec3 uT;
      varying float vSide, vHalf, vA, vFlash;
      void main() {
        float span = ${TB[3] - TB[2]}.0 + aI.z, head = ${TB[2]}.0 - aI.z + mod(aI.y * span + uTime * aJ.x, span);
        float y = head + aS.x * aI.z, hw = 0.8 + 2.0 / max(uPx, 0.3);
        float x = aI.x + aI.w * 8.0 * sin(3.14159 * aS.x) + 4.0 * sin(uTime * 0.7 + aJ.y) * aS.x + aS.y * hw;
        vSide = aS.y; vHalf = hw; vA = smoothstep(${TB[2]}.0, ${TB[2] + 60}.0, y) * (1.0 - smoothstep(${TB[3] - 60}.0, ${TB[3]}.0, y));
        float dx = aI.x - uT.x, f = 0.0;
        if (abs(dx) < uT.z) { float ts = (head + 0.5 * aI.z - (uT.y - sqrt(uT.z * uT.z - dx * dx))) / aJ.x; f = ts >= 0.0 && ts < 0.4 ? 1.0 - ts / 0.4 : 0.0; }
        vFlash = f;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(x - 1200.0, 750.0 - y, 0.0, 1.0);
      }`,
    fragmentShader: `uniform float uOpacity, uPx, uFlashOn; varying float vSide, vHalf, vA, vFlash;
      void main() {
        float a = clamp(max(0.8 * uPx, 0.75) + 0.5 - abs(vSide) * vHalf * uPx, 0.0, 1.0) * vA, fl = vFlash * uFlashOn;
        gl_FragColor = vec4(mix(vec3(0.965, 0.953, 0.925), vec3(0.847, 0.741, 0.494), fl), a * mix(0.3, 0.9, fl) * uOpacity);
      }` });
  const hairMesh = new THREE.Mesh(hg, hairMat); hairMesh.frustumCulled = false; hairMesh.renderOrder = 6; fx.add(hairMesh);
  let seenN = 0, flashN = 0;
  function hairCount(t) {   // what the shader draws, counted for QA: hairs in the band, hairs flashing
    seenN = flashN = 0; const n = phone.matches ? NT / 2 : NT, r = 0.55 * TR;
    for (let i = 0; i < n; i++) {
      const h = hairs[i], x = h[0], len = h[2], sp = h[4], span = TB[3] - TB[2] + len, head = TB[2] - len + ((h[1] * span + t * sp) % span + span) % span;
      if (head + len > TB[2] + 30 && head < TB[3] - 30) seenN++;
      const dx = x - TX; if (Math.abs(dx) < r) { const ts = (head + len / 2 - (TY - Math.sqrt(r * r - dx * dx))) / sp; if (ts >= 0 && ts < 0.4) flashN++; }
    }
  }

  // S4–S5: the scalp line (core 2.4 px, a soft glow ±9 px, drawn right to left), four strands growing from it (the
  // fourth, left, tallest: the longer anagen phase), the roots' points; on S5 the same line is the protocol's, gold under
  // the ampoule and cream toward the devices; MITOPEN and MITOSCAN on it (their packshots, dimmed to about 40 % as seen,
  // no gold; MITOPEN, photographed diagonally with its needle lowest, floats a little above the line)
  const LY = 975, D_LINE = 12.4, ln = plane(D_LINE);   // (the page's three step cards on S5 start at frame y ≈ 1050)
  const lineMat = strokeMat(0xe0c98c, 0xd8bd7e, { line: true, glow: 4.5, glowA: 0.35 });
  const lpts = []; for (let i = 0; i <= 90; i++) lpts.push([1200 - 900 * i / 90, LY]);
  const line = new THREE.Mesh(strokes([{ pts: lpts, core: () => 1.2, ext: 16, t: () => 0 }]), lineMat); line.renderOrder = 8; ln.add(line);
  const SX = [1110, 950, 790, 630], SH = [300, 330, 360, 460];
  const strands = SX.map((x, i) => {
    const pts = [], b = i % 2 ? 1 : -1; for (let k = 0; k <= 48; k++) { const s = k / 48; pts.push([x + b * SH[i] * 0.06 * Math.sin(Math.PI * s * 1.1), LY - s * SH[i]]); }
    const m = new THREE.Mesh(strokes([{ pts, core: s => 1.5 - s, ext: 6, t: s => s }]), strokeMat(0x9c7a2f, 0xd8bd7e)); m.renderOrder = 7; ln.add(m); return m;
  });
  const roots = SX.map(x => spot(ln, 0xd8bd7e, x, LY, 14, 14, 7));
  const heroSpot = spot(ln, 0xc9a24b, 440, LY + 2, 140, 35, 6);   // the line's gold under the ampoule (S5)
  const DIM = new THREE.Color().setRGB(0.4, 0.4, 0.4, THREE.SRGBColorSpace);   // 0.4 as seen (0.13 in linear light)
  const board = (map, w, h, cx, lift) => {   // a device's packshot over the line, bottom centre at (cx, LY − lift)
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h).translate(0, h / 2, 0), new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false, toneMapped: false, color: DIM }));
    m.position.set(cx - 1200, 750 - LY + lift, 0); m.renderOrder = 5; ln.add(m); return m;
  };
  const scan = board(scanTex, 398, 270, 1010, 0), pen = board(penTex, 400 * 273 / 891, 400, 680, 24);
  // the box's glow (S1 alive, mid-way to the kit): its own plane just behind the box, never in a key picture
  const gb = plane(DIST + 2), glowBox = spot(gb, 0xc9a24b, 0, 0, 1, 1, 1);

  // ---- poses (frame px): ampoules { x: axis at the foot, y: the foot, H: height, yaw° (0: the big word faces the
  // camera, − turns it left), lean° (head right), pitch° (top toward the viewer), a: opacity }; the box { cx, cy: its
  // front's centre, h: the front's height, yaw°, a }
  const A = (x, y, H, yaw = 0, lean = 0, pitch = 0) => ({ x, y, H, yaw, lean, pitch, a: 1 });
  // the packshot ×0.885 + (215, 435): its feet are the lowest point of each ampoule's outline (the front of the base,
  // seen from above) and its heights tip to there; the pose's foot is the base's centre: 0.0097 H higher (fitted on A4)
  const photoA = (x, y, H, yaw, lean) => A(x, y - 0.0097 * H, H * 0.9927, yaw, lean);
  const PACK = [photoA(958.8, 1039.0, 365.1, 2, 0), photoA(1023.0, 1056.7, 376.1, -26, 0.6), photoA(1038.9, 1039.5, 364.2, -20, 2.5),
    photoA(1116.4, 1065.1, 377.9, -18, 0.9), photoA(1137.2, 1048.3, 369.0, -20, 1.2)];
  const BOX0 = { cx: 632.5, cy: 718.7, h: FH0, yaw: 0, a: 1 };
  const KC = [695, 750], KS = 1.04;   // the kit: the packshot 1.04× round the composition's centre
  const KIT = PACK.map(a => ({ ...a, x: KC[0] + (a.x - KC[0]) * KS, y: KC[1] + (a.y - KC[1]) * KS, H: a.H * KS }));
  const BOX5 = { ...BOX0, cx: KC[0] + (BOX0.cx - KC[0]) * KS, cy: KC[1] + (BOX0.cy - KC[1]) * KS, h: BOX0.h * KS };
  const BOX1 = { cx: 950, cy: 520, h: 282, yaw: 0, a: 0 };
  // S2 and S3 stand clear of the page's own layers there (measured on the built page at 1440×900, 1512×982 and
  // 1920×1080): on S2 the exosome field fills the left of the 3D box, so the hero and the target stand right of it; on S3
  // the DNA helix crosses the left of the box from low left to high right, so the hero stands right of it and below,
  // and the helix passes behind its neck, not its label. A phone has neither layer: there S3's hero fills the stage
  const HERO = [PACK[0], A(440, 1050, 500), A(960, 1172, 680, -26, 0, 6), A(330, LY, 600), A(440, LY, 420), KIT[0]];   // S4, S5 on the line
  const HERO2_PHONE = A(708, 1168, 820, -26, 0, 6);
  const ROW = [440, 535, 630, 725, 820].map(x => A(x, 1075, 375));   // S6: five sessions in a row before the box
  const SWAY = [0, 2, 4, 6, 2, 0];   // the hero's slow idle turn per screen, ± degrees (within ±30° of the photographed)
  // S6: the row stands whole f 0.50–0.60; then the five go into the packshot one at a time from the right (A5, A4, A3,
  // A2, A1): each goes right, to a place right of the ones still standing and left of the ones already placed, so none
  // passes through another (each arcs forward on its way)
  const DEPART = [4, 3, 2, 1, 0], PACK_W = 0.15, PACK_STEP = 0.055, PACK_T0 = 0.6;
  // the state, written in place on every frame (nothing allocated per frame)
  const amp = () => ({ x: 0, y: 0, H: 1, yaw: 0, lean: 0, pitch: 0, a: 0 });
  const ST = { box: { cx: 0, cy: 0, h: 1, yaw: 0, a: 0 }, amps: [amp(), amp(), amp(), amp(), amp()], glowBox: 0, target: 0, targetA: 0,
    hairs: 0, lineXL: 1200, lineA: 0, cream: 0, grow: [0, 0, 0, 0], roots: 0, pen: 0, scan: 0, back: 0, spot: 0 };
  const setA = (o, s, a = s.a) => { o.x = s.x; o.y = s.y; o.H = s.H; o.yaw = s.yaw; o.lean = s.lean; o.pitch = s.pitch; o.a = a; return o; };
  const mixA = (o, a, b, s) => { o.x = lerp(a.x, b.x, s); o.y = lerp(a.y, b.y, s); o.H = lerp(a.H, b.H, s); o.yaw = lerp(a.yaw, b.yaw, s);
    o.lean = lerp(a.lean, b.lean, s); o.pitch = lerp(a.pitch, b.pitch, s); o.a = lerp(a.a, b.a, s); return o; };
  const toPack = (o, from, to, m) => {   // into its packshot place, passing in front of the others (a forward arc in depth)
    mixA(o, from, to, m); o.H = KH / (KH / o.H - 1.0 * Math.sin(Math.PI * m)); return o;
  };

  function story(p) {   // the state at story position p
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST, b = st.box, H2 = phone.matches ? HERO2_PHONE : HERO[2];
    b.cx = BOX0.cx; b.cy = BOX0.cy; b.h = BOX0.h; b.yaw = 0; b.a = 0;
    for (let i = 0; i < 5; i++) setA(st.amps[i], PACK[i], 0);
    st.glowBox = st.target = st.targetA = st.hairs = st.lineA = st.cream = st.roots = st.pen = st.scan = st.back = st.spot = 0; st.lineXL = 1200;
    st.grow[0] = st.grow[1] = st.grow[2] = st.grow[3] = 0;
    if (k === 0) {   // S1 → S2: the box and four ampoules recede and fade; the left ampoule rises and arcs to its place
      const g = smooth(0.05, 0.7, f), al = 1 - smooth(0.1, 0.65, f);
      b.cx = lerp(BOX0.cx, BOX1.cx, g); b.cy = lerp(BOX0.cy, BOX1.cy, g); b.h = lerp(BOX0.h, BOX1.h, g); b.a = al;
      const s = b.h / BOX0.h;
      for (let i = 1; i < 5; i++) { const a = PACK[i], o = setA(st.amps[i], a, al); o.x = b.cx + (a.x - BOX0.cx) * s; o.y = b.cy + (a.y - BOX0.cy) * s; o.H = a.H * s; }
      const m = smooth(0, 0.85, f), S = PACK[0], E = HERO[1], q = smooth(0.15, 0.85, f), o = st.amps[0];
      o.x = (1 - m) ** 2 * S.x + 2 * m * (1 - m) * 880 + m * m * E.x; o.y = (1 - m) ** 2 * S.y + 2 * m * (1 - m) * 880 + m * m * E.y;
      o.H = lerp(S.H, E.H, q); o.yaw = lerp(S.yaw, E.yaw, q); o.lean = o.pitch = 0; o.a = 1;
      // the glow behind the box goes while the box is still whole (through a fading box it would tint the box), the
      // hairs come once the box has nearly gone
      st.glowBox = 0.6 * (1 - smooth(0, 0.08, f));
      st.hairs = smooth(0.5, 0.85, f); st.target = smooth(0.55, 1, f); st.targetA = 1;
    } else if (k === 1) {   // S2 → S3: the target and the hairs go, the ampoule comes close and turns to its small print
      st.hairs = 1 - smooth(0, 0.4, f); st.target = 1; st.targetA = 1 - smooth(0, 0.4, f);
      mixA(st.amps[0], HERO[1], H2, smooth(0.2, 1, f));
    } else if (k === 2) {   // S3 → S4: the line drawn right to left, the roots light, the strands grow one by one
      mixA(st.amps[0], H2, HERO[3], smooth(0, 0.6, f));
      st.lineXL = lerp(1200, 470, smooth(0.2, 0.6, f)); st.lineA = 1;
      st.roots = smooth(0.45, 0.6, f); for (let i = 0; i < 4; i++) st.grow[i] = smooth(0.5 + i * 0.0833, 0.75 + i * 0.0833, f);
    } else if (k === 3) {   // S4 → S5: the strands go back into the line, it runs on to the left and turns cream toward
      const g = 1 - smooth(0, 0.35, f);   // the devices; the ampoule steps onto it; MITOPEN, then MITOSCAN come forward
      st.grow[0] = st.grow[1] = st.grow[2] = st.grow[3] = g; st.roots = 1 - smooth(0.2, 0.4, f);
      st.lineXL = lerp(470, 300, smooth(0.1, 0.4, f)); st.lineA = 1; st.cream = smooth(0.1, 0.4, f);
      mixA(st.amps[0], HERO[3], HERO[4], smooth(0.2, 0.7, f));
      st.pen = smooth(0.35, 0.8, f); st.scan = smooth(0.45, 0.9, f); st.spot = smooth(0.6, 1, f);
    } else {   // S5 → kit: the protocol goes back; the box comes from the depth; the ampoules stand in a row before it (the
      // four from behind its right edge: no room left of it), then one by one go into the packshot's places
      const out = 1 - smooth(0, 0.3, f);
      st.lineXL = 300; st.lineA = out; st.cream = 1; st.pen = st.scan = st.spot = out; st.back = 1 - out;
      const g = smooth(0.05, 0.38, f);
      b.cx = BOX5.cx; b.cy = lerp(BOX5.cy - 40, BOX5.cy, g); b.h = lerp(BOX5.h * 0.5, BOX5.h, g); b.a = smooth(0.05, 0.33, f);
      st.glowBox = 0.6 * smooth(0.38, 0.55, f) * (1 - smooth(0.7, 0.95, f));   // only behind a whole box
      const Drow = KH / ROW[0].H, Dstart = KF / BOX5.h + 0.3;
      for (let i = 0; i < 5; i++) {
        const o = st.amps[i], w0 = PACK_T0 + DEPART.indexOf(i) * PACK_STEP, m = smooth(w0, w0 + PACK_W, f);
        if (m > 0) { toPack(o, ROW[i], KIT[i], m); continue; }
        if (i === 0) { mixA(o, HERO[4], ROW[0], smooth(0.15, 0.45, f)); continue; }
        // from behind the box's right edge: first forward (still beside the box), then left to its slot; whole by f 0.50
        const u = clamp((f - 0.12 - 0.06 * (i - 1)) / 0.2);
        setA(o, ROW[i], smooth(0, 0.25, u)); o.x = lerp(1125, ROW[i].x, smooth(0.25, 1, u)); o.H = KH / lerp(Dstart, Drow, smooth(0, 0.25, u));
      }
    }
    return st;
  }

  // ---- applying a state
  const camAt = new V3(), DEPTH = new Float32Array(5), RANK = [0, 1, 2, 3, 4], farFirst = (i, j) => DEPTH[j] - DEPTH[i];
  const last = { hx: 0, hy: 0, hH: 0, hyaw: 0, threads: 0, flashes: 0, strands: 0, inPlace: 0, glow: 0 };   // for QA
  function pose(p, t, still) {
    const st = story(p), live = still ? 0 : 1 - smooth(4.85, 5, p);
    const k = Math.min(4, Math.floor(p)), sw = lerp(SWAY[k], SWAY[k + 1], p - k) * Math.sin(t * 0.45) * live, h0 = st.amps[0];
    h0.yaw += sw; h0.y -= 3 * Math.sin(t * 0.8) * live * smooth(0.5, 1, p) * (1 - smooth(4, 4.5, p));
    camAt.copy(camera.position);
    // the box
    const b = st.box; box.visible = b.a > 0.004;
    if (box.visible) {
      const D = KF / b.h; at(b.cx, b.cy, D, box.position); box.scale.setScalar(FHW);
      box.quaternion.copy(lay.quaternion); box.rotateY(rad(b.yaw + Math.sin(t * 0.4 + 1) * live));   // its front parallel to the
      // picture, as photographed (a rectangle within 1–3 px; facing the eye instead skews it and the camera's 4° tilt slants it)
      for (const m of boxMats) { m.opacity = b.a; m.depthWrite = b.a > 0.99; }
    }
    // the ampoules, drawn back to front
    for (let i = 0; i < 5; i++) {
      const s = st.amps[i], a = amps[i], g = a.g, m = a.m; g.visible = s.a > 0.004; DEPTH[i] = KH / s.H; if (!g.visible) continue;
      at(s.x, s.y, DEPTH[i], g.position);
      g.rotation.set(rad(s.pitch), Math.atan2(camAt.x - g.position.x, camAt.z - g.position.z) + rad(s.yaw), -rad(s.lean));
      m.back.opacity = m.front.opacity = m.liquid.opacity = m.ring.opacity = m.print.opacity = s.a; m.surface.opacity = SURF * s.a; m.meniscus.opacity = MEN * s.a;
    }
    RANK.sort(farFirst);
    for (let r = 0; r < 5; r++) { const L = amps[RANK[r]].layer; for (let j = 0; j < L.length; j++) L[j].renderOrder = 100 + r * 10 + j; }
    // the graphics
    targetMat.uniforms.uDraw.value = st.target; targetMat.uniforms.uOpacity.value = st.targetA; target.visible = st.target > 0 && st.targetA > 0.004;
    hairMat.uniforms.uOpacity.value = st.hairs; hairMat.uniforms.uTime.value = t; hairMesh.visible = st.hairs > 0.004;
    hairMat.uniforms.uFlashOn.value = smooth(0.8, 1, st.target) * st.targetA; hg.instanceCount = phone.matches ? NT / 2 : NT;
    const lu = lineMat.uniforms; lu.uXL.value = st.lineXL; lu.uCream.value = st.cream; lu.uOpacity.value = st.lineA; line.visible = st.lineA > 0.004 && st.lineXL < 1190;
    for (let i = 0; i < 4; i++) { const m = strands[i]; m.visible = st.grow[i] > 0.002; m.material.uniforms.uDraw.value = st.grow[i]; m.material.uniforms.uSway.value = 6 * Math.sin(t * 0.6 + i * 1.7) * live; }
    for (const m of roots) { m.material.uniforms.uOpacity.value = 0.8 * st.roots; m.visible = st.roots > 0.004; }
    heroSpot.material.uniforms.uOpacity.value = 0.55 * st.spot; heroSpot.visible = st.spot > 0.004;
    pen.visible = st.pen > 0.004; pen.material.opacity = st.pen; pen.scale.setScalar(lerp(0.6, 1, Math.min(1, st.pen + st.back)) * (1 - 0.2 * st.back));
    scan.visible = st.scan > 0.004; scan.material.opacity = st.scan; scan.scale.setScalar(lerp(0.6, 1, Math.min(1, st.scan + st.back)) * (1 - 0.2 * st.back));
    const gl = still ? 0 : st.glowBox; glowBox.visible = gl > 0.004;
    if (glowBox.visible) {   // just behind the box, a little right of its centre (the canvas edge is 49 px left of the box)
      place(gb, KF / b.h + 0.5); const s = b.h / FH0;
      glowBox.position.set(b.cx + 60 * s - 1200, 750 - b.cy, 0); glowBox.scale.set(500 * s, 400 * s, 1); glowBox.material.uniforms.uOpacity.value = gl;
    }
    if (st.hairs > 0.004) hairCount(t); else seenN = flashN = 0;
    last.hx = h0.x; last.hy = h0.y - h0.H / 2; last.hH = h0.H; last.hyaw = h0.yaw; last.threads = seenN;
    last.flashes = hairMat.uniforms.uFlashOn.value > 0.5 ? flashN : 0; last.strands = (st.grow[0] + st.grow[1] + st.grow[2] + st.grow[3]) / 4;
    last.inPlace = 0; for (let i = 0; i < 5; i++) { const s = st.amps[i]; if (Math.abs(s.x - KIT[i].x) + Math.abs(s.H - KIT[i].H) < 0.5 && s.a > 0.99) last.inPlace++; }
    last.glow = gl;
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
  function fit(view, pr) {
    const id = `${view.box.w}x${view.box.h}@${pr}`;
    if (id !== size) { renderer.setPixelRatio(pr); renderer.setSize(view.box.w, view.box.h, false); size = id; }
    camera.aspect = view.cover.w / view.cover.h;
    camera.setViewOffset(view.cover.w, view.cover.h, view.box.x - view.cover.x, view.box.y - view.cover.y, view.box.w, view.box.h);
    camera.updateProjectionMatrix();
    pxU.value = pr * view.cover.w / 2400;   // device px per frame px: the strokes keep ≥ 1.5 device px
  }
  function render(p, view) { pr = Math.min(full(view), cap); fit(view, pr); pose(p, view.still ? 0 : view.t, view.still); renderer.render(scene, camera); renders++; }
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
    for (const t of [faceTex, metalTex, printTex, scanTex, penTex, roomEnv, glassEnvRT]) t.dispose();
    renderer.dispose();
  }
  const r1 = v => Math.round(v * 10) / 10, r2 = v => Math.round(v * 100) / 100;
  const state = () => ({ quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded,
    version, kits, lastP, hero: { x: r1(last.hx), y: r1(last.hy), H: r1(last.hH), yaw: r1(last.hyaw) }, threads: last.threads,
    flashes: last.flashes, strands: r2(last.strands), inPlace: last.inPlace, glow: r2(last.glow) });
  return { draw, kit, dispose, state, animated: true };
}
