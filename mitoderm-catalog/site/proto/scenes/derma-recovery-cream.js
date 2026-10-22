// DERMA RECOVERY CREAM live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real
// 3D scene, as the approved sample EXOTECH GEL (scenes/exotech-gel.js) and the line's sibling pages built before it
// (scenes/cell-renew-1-5.js, cellular-age-defense-2-5.js, micro-boost-10.js): the same camera, light, box model and
// material, so the BIOSPICULE pages match. The engine keeps the story geometry (the cover-fitted 16:10 frame, the run's
// box, the phone stage, the kit card); this module draws the pose for the story position into the box. Objects are
// placed by frame pixel (2400×1500) inside the page's scene box (x 168…1248, y 285…1215: the scene left, the copy
// right). The products: the box (its current print, typeset from protocols/assets/img/derma-recovery.webp: W : H : D =
// 0.632 : 1 : 0.632, the depth assumed) and the 50 ml jar (no packshot: the owner's two small photos, Figma photo 1 the
// closed jar, photo 73 the open jar with its lid beside it; Ø : H 1 : 1.31 with the lid, a white body, a black collar
// and a frosted lid over a white top).
// The DERMA box's width: canonical is this page's W : H = 615.8 : 974.2 = 0.6321 (the front on the assets packshot at
// half alpha, the dark rounded right edge's last 2 px left out so the print's own axis is the front's middle; the typeset
// print fits it within 0.5 photo px). The sibling pages' S5 (cell-renew-1-5.js, cellular-age-defense-2-5.js) draw the
// same box at 612.4 : 974.1 = 0.6287, 0.5 % narrower, from the same packshot: theirs to align to this one.
// The story (site/story3d.json; scratchpad spec pages/derma-recovery-cream/spec.md), as far as the owner's rule of 22/10
// lets it («only what exists»):
//   S1 meet     the box as on the packshot, a soft green light behind it, turning a little toward its left side (the
//               side the old ¾ packshot shows: plain board)
//   S2 why      no package: a few spicules (the line's ingredient, drawn as on the sibling pages) drift loose in the
//               dark, far back, scattered with no figure among them
//   S3 inside   the jar comes from the dark; its lid lifts straight up and comes to rest beside it, as on photo 73;
//               under it the jar's plain white top (nothing drawn inside: the photos show no cream)
//   S4 feel     (no people: the owner's rule) the lid back on, the jar alone in an even, wider light
//   S5 protocol the line's green haze; the home branch, CELL RENEW 1.5% and CELLULAR AGE DEFENSE 2.5% taking turns on one
//               place («או»: one goes fully out before the other comes in, never two prints at once), the clinic's
//               MICRO BOOST 10% beside it, and the DERMA box a step nearer: their packshots'
//               fronts and sides as photographed. On a desktop all go back into the dark as the step cards scroll up
//               over the scene
//   S6–S7 kit   the box and the closed jar side by side, the green light behind them: the picture that flies into the
//               offer card
// Left out from the spec (the owner's rule overrides it): the cream ribbon and its satin layer, the dry flakes and their
// points of light, the gold lines of S5 and the floating gold M, the pearls, the arcs, the opened flap and the jar
// rising from the box (never photographed), the mirror and any person. The products keep their print's colours
// (emissive ≈ 85 % + neutral shading, toneMapped off); the line's green (#1E4634, DERMA's sage #9AA889 at a glow's
// heart) lives only in the glows and the haze. No text is drawn but the packages' own print
// (design/derma-recovery-cream/make_textures.py).
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

  // the camera looks down 2°, as on the sibling pages; the boxes stand upright in the world, so the horizon is frame
  // y 601.5 for all of them. `lay` is the same camera without the box's view offset, for placing objects by their frame
  // pixels
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
  const D_BOX = DIST + 1.2, D_JAR = DIST + 0.4, D_NEXT = DIST + 2.4, D_FIELD = DIST + 2;   // the S5 neighbours deeper

  // ---- light: a neutral studio for reflections (PMREM), as the siblings': dark above and below, an even horizon, two
  // tall narrow softboxes either side of the camera, rims behind; a white key from the top left, in front
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

  // ---- textures (make_textures.py): the typeset front and the plain side of the box, the jar's print, the three
  // neighbours' fronts and sides as photographed
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy(), NTEX = 6;
  const tex = name => {
    const t = new THREE.TextureLoader().load(new URL(`img/derma-recovery-cream-3d/${name}`, base).href, () => {
      t.needsUpdate = true; renderer.initTexture(t);   // uploaded now, not on the first scroll
      if (++loaded === NTEX) { version++; if (onLoad) onLoad(); }   // the engine redraws the kit picture
    });
    t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const faceTex = tex('box-face.webp'), sideTex = tex('box-side.png'), labelTex = tex('jar-label.png');
  const renewTex = tex('renew.webp'), cadTex = tex('cad.webp'), mbTex = tex('mb.webp');
  const TEXS = [faceTex, sideTex, labelTex, renewTex, cadTex, mbTex];

  // ---- materials. The products in their print's colours: emissive 0.85 of the colour plus a neutral shading (a diffuse
  // 0.2 of it under the key and the room), not tone mapped; a dense glossy paper (roughness 0.5, a soft highlight). They
  // come and go by opacity only, never dimmed or tinted. A printed face (the boxes, the jar's print) keeps only a trace
  // of the highlight (specular 0.05): on the paper it never showed (0.3 level), on black ink a specular of 0.3 lifted
  // the letters' cores by 8–10 levels (the v1 key at 3840)
  const SHADE = 0.2;
  const P = (hex, opts = {}) => new THREE.MeshPhysicalMaterial(Object.assign({ color: new THREE.Color(hex).multiplyScalar(SHADE), emissive: hex,
    emissiveIntensity: 0.85, roughness: 0.5, specularIntensity: 0.3, toneMapped: false, transparent: true }, opts));
  const printed = (map, k = 1, opts = {}) => P(new THREE.Color(k, k, k), Object.assign({ color: new THREE.Color(SHADE * k, SHADE * k, SHADE * k), map, emissiveMap: map,
    specularIntensity: 0.05 }, opts));
  const uvSpan = (geo, u0, u1) => {   // a plane's u from u0 to u1 (a part of a picture holding the front and the side)
    const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setX(i, u0 + uv.getX(i) * (u1 - u0)); return geo;
  };

  // ---- the boxes, W × 1 × D (scaled per pose), their origin the front's middle (they turn about that upright). DERMA:
  // the typeset front, its left side the plain board (the side the old ¾ packshot shows); the right side, the back, the
  // top and the foot closed for any transition's frame but never seen. Front and side are drawn first (they write
  // depth), the closed faces after them: through a fading front nothing behind it shows
  const BW = 615.8 / 974.2, BD = BW;
  const mkGroup = () => { const g = new THREE.Group(); g.visible = false; scene.add(g); return g; };
  const addFace = (g, geo, mat, x, y, z, rx, ry, o) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, 0); m.renderOrder = o; g.add(m); return m; };
  const heroMats = [printed(faceTex), printed(sideTex), P(new THREE.Color(0xf3e9df).multiplyScalar(0.7))];
  const hero = { g: mkGroup(), W: BW, D: BD, mats: heroMats, a: 0, x: 0, y: 0, H: 0, yaw: 0, view: 0 };
  {
    const g = hero.g, [front, left, hid] = heroMats;
    addFace(g, new THREE.PlaneGeometry(BW, 1), front, 0, 0, 0, 0, 0, 100);
    const lg = new THREE.PlaneGeometry(BD, 1); uvSpan(lg, 1, 0);   // the texture's u 0 is the front edge
    addFace(g, lg, left, -BW / 2, 0, -BD / 2, 0, -Math.PI / 2, 100);
    addFace(g, new THREE.PlaneGeometry(BD, 1), hid, BW / 2, 0, -BD / 2, 0, Math.PI / 2, 101);
    addFace(g, new THREE.PlaneGeometry(BW, 1), hid, 0, 0, -BD, 0, Math.PI, 101);
    addFace(g, new THREE.PlaneGeometry(BW, BD), hid, 0, 0.5, -BD / 2, -Math.PI / 2, 0, 101);
    addFace(g, new THREE.PlaneGeometry(BW, BD), hid, 0, -0.5, -BD / 2, Math.PI / 2, 0, 101);
  }
  // the neighbours (S5): their front and right side as photographed, one picture each (u: the front 0…f, the side f…1);
  // W : H and D as their own pages measured them; only these two faces exist (the views never reach the others)
  const mkNext = (map, f, W, D, order) => {
    const mats = [printed(map), printed(map)], g = mkGroup();
    addFace(g, uvSpan(new THREE.PlaneGeometry(W, 1), 0, f), mats[0], 0, 0, 0, 0, 0, order);
    addFace(g, uvSpan(new THREE.PlaneGeometry(D, 1), f, 1), mats[1], W / 2, 0, -D / 2, 0, Math.PI / 2, order);
    return { g, W, D, mats, a: 0, x: 0, y: 0, H: 0, yaw: 0, view: 0 };
  };
  const renew = mkNext(renewTex, 0.8506, 1048 / 4032, 1048 / 4032, 92);
  const cad = mkNext(cadTex, 0.8534, 0.26, 0.26, 90);
  const mb = mkNext(mbTex, 0.7937, 0.2376, 0.2376 * 1.21, 91);
  const NEXT = [renew, cad, mb];
  // the side's share of the front on their packshots (their side's width : their front's, half alpha)
  const R_SIDE = [45.6 / 261.75, 44.9 / 261.8, 78.6 / 304.04];

  // ---- the jar, Ø 1 (scaled per pose), its origin the foot's middle: a white body (to 0.77), the black collar (to 0.99)
  // and its neck under the lid (r 0.478, to 1.13), the plain white top; the print on the body's front (φ −50…+34°);
  // the frosted lid (r 0.495, 0.32 tall) over the neck. The lid is a child of the jar's rig: it lifts straight up,
  // clears the neck and comes to rest beside the jar, on the jar's own ground, as on photo 73
  const SEG = 128;
  const jar = new THREE.Group(); jar.visible = false; scene.add(jar);
  const lathe = (pts, m, parent, o) => { const x = new THREE.Mesh(new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), SEG), m); x.renderOrder = o; parent.add(x); return x; };
  const jBody = P(0xe3e3e3, { roughness: 0.55, clearcoat: 0.15, clearcoatRoughness: 0.4 });
  const jCollar = P(0x121212, { roughness: 0.32, specularIntensity: 0.6 });
  const jTop = P(0xefefef, { roughness: 0.6 });
  const jPrint = printed(labelTex, 1, { depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, roughness: 0.55 });
  lathe([[0, 0], [0.486, 0], [0.496, 0.004], [0.5, 0.014], [0.5, 0.77]], jBody, jar, 110);
  lathe([[0.5, 0.77], [0.5, 0.982], [0.497, 0.99], [0.48, 0.99], [0.478, 0.996], [0.478, 1.122], [0.474, 1.13], [0.468, 1.13]], jCollar, jar, 110);
  { const top = new THREE.Mesh(new THREE.CircleGeometry(0.469, SEG).rotateX(-Math.PI / 2), jTop); top.position.y = 1.1295; top.renderOrder = 110; jar.add(top); }
  { const LB = [rad(-50), rad(34)], m = new THREE.Mesh(new THREE.CylinderGeometry(0.5006, 0.5006, 0.72, 96, 1, true, LB[0], LB[1] - LB[0]), jPrint);
    m.position.y = 0.4; m.renderOrder = 111; jar.add(m); }
  // the lid: frosted, its colour and opacity solved from photo 1's composite tones (the wall over the black collar
  // ≈ #444444, over the white top ≈ #D6D6D6: α 0.34 of #A5A5A5); its top, lit from above, lighter and denser (α 0.85 of
  // #D8D8D8; photo 73: a light ellipse, 200–208; photo 1: 203–227 over the white top); at grazing angles the frost
  // thickens (lighter, denser
  // rim); the far wall's inner face, lit through the frost and by the white top under it, light and dense (the photo's
  // band over the white top reads #D6D6D6; on a dark page only this keeps the lid frosted white, not dark glass). Drawn
  // after the jar (no depth write): the far wall's inside, the near wall, the top
  const frost = (hex, a, side) => {
    const m = P(hex, { opacity: a, depthWrite: false, side, roughness: 0.6, specularIntensity: 0.4 });
    m.onBeforeCompile = sh => { sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float F = pow(1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0), 2.0);
        gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(0.72), 0.35 * F); gl_FragColor.a = min(1.0, gl_FragColor.a * (1.0 + 1.2 * F)); }`); };
    m.customProgramCacheKey = () => 'derma-frost'; m.userData.a = a; return m;
  };
  const jLid = frost(0xa5a5a5, 0.34, THREE.FrontSide), jLidIn = frost(0xe6e6e6, 0.85, THREE.BackSide), jLidTop = frost(0xd8d8d8, 0.85, THREE.FrontSide);
  const lid = new THREE.Group(); jar.add(lid);
  { const inner = new THREE.Mesh(new THREE.CylinderGeometry(0.481, 0.481, 0.3, SEG, 1, true), jLidIn); inner.position.y = 0.15; inner.renderOrder = 115; lid.add(inner);
    const wall = new THREE.Mesh(new THREE.CylinderGeometry(0.495, 0.495, 0.32, SEG, 1, true), jLid); wall.position.y = 0.16; wall.renderOrder = 116; lid.add(wall);
    const cap = new THREE.Mesh(new THREE.CircleGeometry(0.495, SEG).rotateX(-Math.PI / 2), jLidTop); cap.position.y = 0.32; cap.renderOrder = 117; lid.add(cap); }
  const JAR_MATS = [jBody, jCollar, jTop, jPrint], LID_MATS = [jLid, jLidIn, jLidTop];
  const LID0 = 0.99;   // the lid's foot on the closed jar

  // ---- the spicules (S2: BIOSPICULE, the catalogue's needles of a marine sponge, as site/img/spicules-macro.png): the
  // line's spicule as its sibling pages draw it (scenes/cell-renew-1-5.js, cellular-age-defense-2-5.js: the same
  // geometry and material, so the ingredient looks the same on every BIOSPICULE page): glassy spindles pointed at both
  // ends (length : width 18), dark green in their core, light and clear at their rims, the studio's highlights on their
  // glaze. Here they are alone in the dark, so two things are added: each one's depth thins it (its alpha 0.55 far …
  // 1 near: the short ones are the far ones), and all fade out over the scene box's last 48 px as they come and go. One
  // instanced draw; every instance's place, axis and size set per frame
  const spiGeo = (() => {
    const pts = []; for (let i = 0; i <= 12; i++) { const t = i / 12; pts.push(new THREE.Vector2(0.5 * Math.pow(Math.sin(Math.PI * t), 0.85), t - 0.5)); }
    return new THREE.LatheGeometry(pts, 10);
  })();
  const NS = 14, NS_PH = 7;   // a phone: half of them
  const spiNear = new THREE.InstancedBufferAttribute(new Float32Array(NS).fill(1), 1); spiGeo.setAttribute('aNear', spiNear);
  const spiMat = new THREE.MeshPhysicalMaterial({ color: 0x1b2911, roughness: 0.32, metalness: 0, clearcoat: 0.7, clearcoatRoughness: 0.12,
    envMapIntensity: 1.1, transparent: true, toneMapped: false });
  // the frame position of every fragment (the camera without the box's offset), for the scene box's soft edge
  const layVP = new THREE.Matrix4().multiplyMatrices(lay.projectionMatrix, lay.matrixWorldInverse);
  spiMat.onBeforeCompile = sh => {   // as the siblings': a thin lighter rim; then the depth's alpha and the edge fade
    sh.uniforms.uLayVP = { value: layVP };
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute float aNear; varying float vNear; varying vec2 vFr; uniform mat4 uLayVP;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvNear = aNear;')
      .replace('#include <worldpos_vertex>', `#include <worldpos_vertex>
        { vec4 lp = uLayVP * modelMatrix * instanceMatrix * vec4(transformed, 1.0); vFr = vec2((lp.x / lp.w + 1.0) * 1200.0, (1.0 - lp.y / lp.w) * 750.0); }`);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vNear; varying vec2 vFr;').replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float F = pow(1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0), 4.0);
        gl_FragColor.rgb = mix(gl_FragColor.rgb + vec3(0.004, 0.010, 0.002), vec3(0.30, 0.35, 0.25), 0.45 * F);
        gl_FragColor.a *= vNear * smoothstep(168.0, 216.0, vFr.x) * (1.0 - smoothstep(1200.0, 1248.0, vFr.x)) * smoothstep(285.0, 333.0, vFr.y) * (1.0 - smoothstep(1167.0, 1215.0, vFr.y)); }`);
  };
  spiMat.customProgramCacheKey = () => 'derma-spicule';
  const spicules = new THREE.InstancedMesh(spiGeo, spiMat, NS);
  spicules.instanceMatrix.setUsage(THREE.DynamicDrawUsage); spicules.renderOrder = 30; spicules.frustumCulled = false; spicules.visible = false;
  scene.add(spicules);
  // their places (frame px), each with its axis's angle in the picture (−: rising to the right; −1.45…+0.24 rad), its
  // tilt into depth, its length (95…340 px), its depth behind the field's (the long ones near: −1, the short ones far:
  // +3.5), its phase. Scattered by annealing against the owner's rule (22/10: particles never gather into a line, row,
  // grid, ring or figure), measured on this table: no three centres nearer than 36.8 px to one straight line over a
  // span under 800 px (the 40 px asked for is past what 14 needles allow here with the rules below; over the longer
  // spans, 826…985 px across most of the box, the thinnest is 21 px), the phone's seven (the even ones) ≥ 55 px; no
  // three in a 60 px band across or up (no row, no column); no centre within 49 px of the axis line of another within
  // 450 px (no dashed line); neighbours under 400 px apart turned ≥ 0.2 rad from each other (no hatching); no empty
  // circle over 204 px among them (no hollow, no ring); centres ≥ 191 px apart; spindles ≥ 80 px clear of each other at
  // rest (their drift included) and ≥ 50 px all the way in and out (none crossing into an X, + or T); the tips ≥ 60 px
  // inside the scene box
  const SPI = [[801, 361, -0.22, 0.37, 105, 3.3, 0.5], [973, 1080, -0.72, 0.23, 171, 2.1, 2.6],
    [377, 404, -0.26, 0.46, 230, 1.0, 5.3], [1176, 968, -1.45, -0.43, 141, 2.7, 1.2],
    [911, 649, -1.44, -0.26, 189, 1.8, 3.5], [1111, 783, -0.33, -0.31, 116, 3.1, 6.0],
    [569, 798, 0.24, 0.34, 279, 0.1, 2.3], [264, 856, -1.08, 0.37, 95, 3.5, 4.8],
    [539, 544, -0.02, 0.23, 128, 2.9, 0.7], [351, 1026, -0.62, -0.17, 253, 0.6, 2.8],
    [744, 965, -0.34, 0.33, 340, -1.0, 5.7], [258, 632, -1.34, -0.37, 208, 1.4, 1.6],
    [1142, 439, -1.15, -0.32, 155, 2.4, 3.7], [509, 1153, -0.01, -0.22, 308, -0.4, 0.2]];
  const NEAR = dz => 1 - 0.45 * clamp((dz + 1) / 4.5);   // depth −1 (the longest, near) → 1 … +3.5 (the shortest, far) → 0.55

  // ---- the line's light, flat to the camera in frame pixels (a plane far behind; local x = px − 1200, y = 750 − py),
  // drawn first: soft shapeless glows, nothing drawn. A glow adds its colour (× its alpha) and keeps a true alpha, a
  // gaussian reaching 0 at its ellipse with a slope of 2 % of its peak (no edge, no disc), DERMA's sage at its heart; the
  // haze of S5 lays the line's green over the smoke (normal blending). Both fade out over the scene box's last 48 px
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
  const spot = (order, heart, edge, blend) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial(Object.assign({ vertexShader: QUAD_V, fragmentShader: SPOT_F,
      uniforms: { uB: { value: new THREE.Vector4() }, uS: { value: new THREE.Vector4() }, uA: { value: 0 }, uC: { value: hex3(heart) }, uE: { value: hex3(edge) } },
      transparent: true, depthWrite: false, side: THREE.DoubleSide, forceSinglePass: true }, blend)));   // one pass (QUAD_V mirrors it)
    m.renderOrder = order; m.visible = false; m.frustumCulled = false; fx.add(m); return m;
  };
  const setSpot = (m, cx, cy, rx, ry, a) => {
    const u = m.material.uniforms; u.uS.value.set(cx, cy, rx, ry); u.uB.value.set(cx - rx, cy - ry, cx + rx, cy + ry); u.uA.value = a; m.visible = a > 0.004;
  };
  const GLOW_HEART = 0x9aa889, GLOW_EDGE = 0x1e4634;
  const veil = spot(1, 0x1e4634, 0x1e4634, { blending: THREE.NormalBlending });
  const glows = [spot(2, GLOW_HEART, GLOW_EDGE, ADD), spot(2, GLOW_HEART, GLOW_EDGE, ADD), spot(2, 0x2f6a50, GLOW_EDGE, ADD), spot(2, 0x2f6a50, GLOW_EDGE, ADD)];
  // glows[0] behind the box, [1] behind the jar, [2] behind the home branch, [3] behind MICRO BOOST

  // ---- poses (frame px). The box [cx, cy: its front's middle, H: its front's height]: its top above the horizon
  // (601.5) and its foot below it in every frame, so neither shows; where it stands opaque its front is at most 600 px
  // tall (960 px in a 3840 key, under the packshot's 974): the illustration, the photo's own picture, is never drawn
  // above its pixels. The jar [x: its axis, y: its foot, Ø px, tilt toward the camera (deg), lid 0 on … 1 beside]: the
  // closed jar seen as on photo 1 (from ≈ 6° above: the camera's 2° and a tilt of 4–5°), the open one as on photo 73
  // (≈ 17° above: a tilt of 14°); turned at most ±4° about its axis (its back was never photographed)
  const HERO = [[700, 735, 600], [700, 700, 470], null, null, [900, 640, 470], [600, 720, 600]];
  const JAR = [null, [640, 1000, 290, 0, 0], [580, 1035, 360, 14, 1], [700, 1060, 400, 5, 0], [820, 985, 300, 5, 0], [985, 1030, 330, 4, 0]];
  const HOME = [400, 600, 380], CLINIC = [600, 612, 400];   // S5: the home branch's place (CELL RENEW ↔ 2.5%), MICRO BOOST
  const HOME_PH = [380, 620, 420], CLINIC_PH = [600, 630, 440], HERO4_PH = [920, 660, 500];   // a phone: a little larger
  const KIT_GLOW = 0.7;   // the kit's light behind the pair
  const JAR5_IN = [JAR[5][0], JAR[5][1], JAR[5][2] * 0.94, 4, 0];   // the kit's jar as it comes in (a step back, closed)
  const ST = { hero: [0, 0, 0, 0], jar: [0, 0, 0, 0, 0, 0], next: [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], spi: 0, sd: 0, glow: [0, 0, 0, 0], veil: 0, kitGlow: 0 };
  const set4 = (o, x, y, H, a) => { o[0] = x; o[1] = y; o[2] = H; o[3] = a; return o; };
  const mixPose = (o, A, B, s, a) => set4(o, lerp(A[0], B[0], s), lerp(A[1], B[1], s), lerp(A[2], B[2], s), a);
  const setJar = (o, A, B, s, a, lidS) => { for (let i = 0; i < 4; i++) o[i] = lerp(A[i], B[i], s); o[4] = a; o[5] = lidS === undefined ? lerp(A[4], B[4], s) : lidS; return o; };
  // the home branch: CELL RENEW 1.5% and the 2.5% take turns on one place (7 s). One goes fully out (0.5 s) before the
  // other comes in (0.5 s): the place stands empty for a moment, in the haze, and the two prints are never on screen
  // together (theirs differ in layout: a crossfade showed both). A still frame (the key, reduced motion) shows CELL RENEW
  const SWAP = [1, 0];   // [CELL RENEW, the 2.5%]: their share of the routine's opacity
  function swap(t, live) {
    const c = live ? (t % 7 + 7) % 7 : 0;
    SWAP[0] = c < 2.5 ? 1 : c < 3 ? 1 - smooth(2.5, 3, c) : c < 6.5 ? 0 : smooth(6.5, 7, c);
    SWAP[1] = c < 3 ? 0 : c < 3.5 ? smooth(3, 3.5, c) : c < 6 ? 1 : c < 6.5 ? 1 - smooth(6, 6.5, c) : 0;
    return SWAP;
  }
  function s5(st, a, ga, HM, CL, t, live) {   // the routine at S5, all × a: the haze, the home branch (taking turns), MICRO BOOST
    const w = swap(t, live);
    set4(st.next[0], HM[0], HM[1], HM[2], a * w[0]); set4(st.next[1], HM[0], HM[1], HM[2], a * w[1]); set4(st.next[2], CL[0], CL[1], CL[2], a);
    st.veil = 0.5 * ga; st.glow[2] = 0.45 * ga; st.glow[3] = 0.45 * ga;
  }
  function story(p, ph, t, live) {
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST;
    set4(st.hero, 0, 0, 1, 0); st.jar[4] = 0; for (const n of st.next) set4(n, 0, 0, 1, 0);
    st.spi = 0; st.sd = 0; st.glow[0] = st.glow[1] = st.glow[2] = st.glow[3] = 0; st.veil = 0; st.kitGlow = 0;
    const HM = ph ? HOME_PH : HOME, CL = ph ? CLINIC_PH : CLINIC, H4 = ph ? HERO4_PH : HERO[4];
    if (p >= 5) {   // the kit: exactly the pose
      mixPose(st.hero, HERO[5], HERO[5], 0, 1); setJar(st.jar, JAR[5], JAR[5], 0, 1); st.kitGlow = KIT_GLOW; return st;
    }
    if (k === 0) {   // S1 → S2: the box steps back into the dark; the spicules come in from far back
      const b = smooth(0.05, 0.5, f); mixPose(st.hero, HERO[0], HERO[1], b, 1 - b);
      st.glow[0] = 0.8 * (1 - smooth(0, 0.4, f));
      st.spi = smooth(0.35, 0.8, f); st.sd = -(1 - st.spi);
    } else if (k === 1) {   // S2 → S3: the spicules go on their way and fade; the jar comes from the dark, closed and square
      // on, tips toward the camera, and its lid lifts and comes to rest beside it
      st.spi = 1 - smooth(0, 0.35, f); st.sd = smooth(0, 0.35, f);
      const a = smooth(0.2, 0.6, f), m = smooth(0.2, 0.65, f);
      setJar(st.jar, JAR[1], JAR[2], m, a, smooth(0.6, 1, f));
      st.jar[3] = 14 * smooth(0.45, 0.75, f);
      st.glow[1] = 0.6 * smooth(0.4, 0.8, f);
    } else if (k === 2) {   // S3 → S4: the lid goes back the way it came, the jar straightens and steps forward; the light
      // evens and widens
      setJar(st.jar, JAR[2], JAR[3], smooth(0.2, 0.7, f), 1, 1 - smooth(0, 0.4, f));
      st.jar[3] = lerp(14, 5, smooth(0.1, 0.5, f));
      st.glow[1] = lerp(0.6, 0.75, smooth(0.6, 1, f));
    } else if (k === 3) {   // S4 → S5: the jar steps back to the right and fades; the line's haze, the home branch, MICRO
      // BOOST and the DERMA box come in from the dark
      const j = smooth(0, 0.35, f); setJar(st.jar, JAR[3], JAR[4], j, 1 - j);
      st.glow[1] = 0.75 * (1 - smooth(0, 0.3, f));
      s5(st, smooth(0.4, 0.75, f), smooth(0.2, 0.6, f), HM, CL, t, live);
      for (const n of st.next) n[2] *= 0.9 + 0.1 * smooth(0.4, 0.75, f);
      const d = smooth(0.45, 0.85, f); set4(st.hero, H4[0], H4[1], H4[2] * (0.9 + 0.1 * d), d); st.glow[0] = 0.6 * d;
    } else if (ph) {   // S5 → kit on a phone (the copy scrolls under the stage): the routine goes, DERMA steps to the kit's
      // place and the jar comes in beside it
      const o = smooth(0.1, 0.45, f); s5(st, 1 - o, 1 - o, HM, CL, t, live);
      mixPose(st.hero, H4, HERO[5], smooth(0.35, 0.85, f), 1); st.glow[0] = 0.6 * (1 - smooth(0.3, 0.6, f));
      const j = smooth(0.7, 0.95, f); setJar(st.jar, JAR5_IN, JAR[5], j, j);   // after the box has passed
      st.kitGlow = KIT_GLOW * smooth(0.6, 1, f);
    } else {   // S5 → kit on a desktop: the page's three step cards scroll up over the scene's whole width (their top meets
      // the boxes' feet as the hold at p = 4 ends at 1920×1080, by f ≈ 0.05 at 1440×900; their foot clears the kit's top
      // by f ≈ 0.42–0.63, as on the sibling pages). So all go back into the dark as the cards come, and the kit (the box
      // and the closed jar) comes forward once the cards have passed
      const out = smooth(0, 0.06, f), back = smooth(0.64, 0.85, f);
      s5(st, 1 - out, 1 - out, HM, CL, t, live); for (const n of st.next) n[2] *= 1 - 0.06 * out;
      if (f < 0.3) { set4(st.hero, H4[0], H4[1], H4[2] * (1 - 0.06 * out), 1 - out); st.glow[0] = 0.6 * (1 - out); }
      else {
        set4(st.hero, HERO[5][0], HERO[5][1], HERO[5][2] * (0.94 + 0.06 * back), back);
        setJar(st.jar, JAR5_IN, JAR[5], back, back);
        st.kitGlow = KIT_GLOW * back;
      }
    }
    return st;
  }

  // ---- applying a state (in place: nothing allocated per frame)
  const tmp = new V3(), tmp2 = new V3(), toCam = new V3();
  const local = (B, x, y, z, out) => frameOf(tmp.set(x, y, z).applyMatrix4(B.g.matrixWorld), out);
  // a neighbour's side as drawn: its projected width : the front's, at the front's middle height (frame px). The
  // perspective makes it differ with the place and the size, so each box's view angle is solved for its packshot's
  // share where it stands: the share grows near linearly with the angle over 8…14°, and one secant step lands close
  const TA = rad(8), TB = rad(14), fa = [0, 0], fb = [0, 0], fc = [0, 0];
  function sideShare(B, yaw) {
    B.g.rotation.set(0, yaw, 0); B.g.updateMatrixWorld(true);
    const l = local(B, -B.W / 2, 0, 0, fa)[0], r = local(B, B.W / 2, 0, 0, fb)[0];
    return (local(B, B.W / 2, 0, -B.D, fc)[0] - r) / (r - l);
  }
  function placeBox(B, s, D, R, th) {   // s: [cx, cy, H, a]; R: the right side's share to show; th (no R): the turn
    B.g.visible = s[3] > 0.004; B.a = s[3];   // toward the left side (radians, ≥ 0)
    if (!B.g.visible) return;
    at(s[0], s[1], D, B.g.position); B.g.scale.setScalar(world(s[2], D));
    toCam.copy(lay.position).sub(B.g.position);
    const base = Math.atan2(toCam.x, toCam.z);   // square on to the camera
    if (R) { const a = sideShare(B, base - TA), b = sideShare(B, base - TB); th = -(TA + (R - a) * (TB - TA) / (b - a)); }
    B.yaw = base + th; B.g.rotation.set(0, B.yaw, 0); B.g.updateMatrixWorld(true);
    B.x = s[0]; B.y = s[1]; B.H = s[2]; B.view = th;
    for (const m of B.mats) m.opacity = s[3];
  }
  const J = { x: 0, y: 0, D: 0, tilt: 0, yaw: 0, lid: 0, a: 0 };
  function placeJar(s, t, live) {   // s: [x, foot y, Ø px, tilt°, a, lid]
    jar.visible = s[4] > 0.004; J.a = s[4];
    if (!jar.visible) return;
    at(s[0], s[1], D_JAR, jar.position); jar.scale.setScalar(world(s[2], D_JAR));
    toCam.copy(lay.position).sub(jar.position);
    const yaw = Math.atan2(toCam.x, toCam.z) + rad(3.5) * Math.sin(t * 2 * Math.PI / 11) * live;   // ≤ ±4°: the front only
    jar.rotation.set(rad(s[3]), yaw, 0, 'YXZ'); jar.updateMatrixWorld(true);
    // the lid: up 0.32 Ø (its foot clears the neck), aside 1.22 Ø to the right, down to the jar's ground (photo 73)
    const o = s[5], up = smooth(0, 0.4, o), side = smooth(0.3, 0.75, o), down = smooth(0.65, 1, o);
    lid.position.set(1.22 * side, LID0 + 0.34 * up - (LID0 + 0.34) * down, 0.04 * side);
    for (const m of JAR_MATS) m.opacity = s[4];
    for (const m of LID_MATS) m.opacity = m.userData.a * s[4];
    J.x = s[0]; J.y = s[1]; J.D = s[2]; J.tilt = s[3]; J.yaw = deg(yaw); J.lid = o;
  }
  // the instances: a spindle's matrix from its middle, its axis (unit), its length and width (world units)
  const qa = new THREE.Quaternion(), Y = new V3(0, 1, 0), sc = new V3(), mat4 = new THREE.Matrix4();
  const pos = new V3(), dir = new V3(), mq = new THREE.Quaternion();
  let spiPh = null;   // the set whose depths the instances hold (a phone keeps the even ones)
  function placeSpicules(st, ph, t, live) {
    spicules.visible = st.spi > 0.004;
    if (!spicules.visible) return;
    const n = ph ? NS_PH : NS; spicules.count = n; spiMat.opacity = st.spi;
    if (spiPh !== ph) { for (let j = 0; j < n; j++) spiNear.array[j] = NEAR(SPI[ph ? j * 2 : j][5]); spiNear.needsUpdate = true; spiPh = ph; }
    for (let j = 0; j < n; j++) {
      const s = SPI[ph ? j * 2 : j], D = D_FIELD + s[5], u = world(1, D);
      // a slow drift along its own axis while the page lives; on the way in and out 140 px further along it
      const dr = 140 * st.sd + 18 * Math.sin(t * 0.21 + s[6]) * live, a = s[2] + 0.05 * Math.sin(t * 0.17 + s[6] * 1.7) * live;
      const cx = s[0] + Math.cos(a) * dr, cy = s[1] + Math.sin(a) * dr;
      at(cx, cy, D, pos);
      dir.set(0, 0, 0).addScaledVector(RIGHT, Math.cos(a)).addScaledVector(UP, -Math.sin(a)).addScaledVector(BACK, s[3]).normalize();
      const L = s[4] * u * Math.hypot(1, s[3]);   // its length in the picture stays s[4] px whatever its tilt
      qa.setFromUnitVectors(Y, dir); sc.set(L / 18, L, L / 18); mat4.compose(pos, qa, sc); spicules.setMatrixAt(j, mat4);
    }
    spicules.instanceMatrix.needsUpdate = true;
  }
  function pose(p, t, still) {
    const ph = phone.matches, live = still ? 0 : 1 - smooth(4.85, 5, p), st = story(p, ph, t, live);
    // the box: square on, turning toward its left side 0…5° (9 s) and breathing ±0.6 % of its height while it lives
    const hs = st.hero, sway = rad(2.5) * (1 - Math.cos(t * 2 * Math.PI / 9)) * live;
    hs[1] += 0.006 * hs[2] * Math.sin(t * 2 * Math.PI / 6) * live;
    placeBox(hero, hs, D_BOX, 0, sway);
    for (let i = 0; i < 3; i++) placeBox(NEXT[i], st.next[i], D_NEXT, R_SIDE[i]);   // the home branch's two never at once
    placeJar(st.jar, t, live);
    placeSpicules(st, ph, t, live);
    // the light: behind the box (its front's width and more either side, 0.62 of its height), the jar, the routine;
    // the kit's: one glow behind the pair, within its height (the card's picture is cut to what has alpha)
    if (hero.g.visible && st.glow[0] > 0) setSpot(glows[0], hero.x, hero.y, 0.85 * hero.H, 0.62 * hero.H, st.glow[0] * hero.a); else glows[0].visible = false;
    if (jar.visible && st.glow[1] > 0) setSpot(glows[1], J.x, J.y - 0.62 * J.D, 1.05 * J.D, 0.78 * J.D, st.glow[1] * J.a); else glows[1].visible = false;
    if (st.glow[2] > 0) setSpot(glows[2], ST.next[0][0], ST.next[0][1], 0.55 * ST.next[0][2], 0.6 * ST.next[0][2], st.glow[2]); else glows[2].visible = false;
    if (st.glow[3] > 0) setSpot(glows[3], ST.next[2][0], ST.next[2][1], 0.55 * ST.next[2][2], 0.6 * ST.next[2][2], st.glow[3]); else glows[3].visible = false;
    if (st.kitGlow > 0) setSpot(glows[0], 790, 735, 470, 330, st.kitGlow);
    setSpot(veil, 700, 640, 560, 400, st.veil);
  }
  // QA: the projected tips of the spicules drawn last (frame px)
  function fieldBox() {
    if (!spicules.visible) return null;
    const b = [Infinity, Infinity, -Infinity, -Infinity], o = [0, 0];
    for (let i = 0; i < spicules.count; i++) {
      spicules.getMatrixAt(i, mat4); mat4.decompose(pos, mq, sc); if (sc.y < 1e-5) continue;
      dir.set(0, 1, 0).applyQuaternion(mq);
      for (const k of [-0.5, 0.5]) { frameOf(tmp2.copy(pos).addScaledVector(dir, k * sc.y), o); b[0] = Math.min(b[0], o[0]); b[1] = Math.min(b[1], o[1]); b[2] = Math.max(b[2], o[0]); b[3] = Math.max(b[3], o[1]); }
    }
    return b.map(Math.round);
  }
  // QA: where to pipette (frame px rectangles) in the pose drawn last: the box's empty paper and band (left of the
  // print), its left side; the jar's body above the M (φ −5…+5°, y 0.705…0.75), its collar (φ −8…+8°, y 0.82…0.95)
  const rectOf = pts => [Math.round(Math.min(...pts.map(q => q[0]))), Math.round(Math.min(...pts.map(q => q[1]))), Math.round(Math.max(...pts.map(q => q[0]))), Math.round(Math.max(...pts.map(q => q[1])))];
  function boxProbes(B) {
    if (!B.g.visible || B.a < 0.99) return null;
    const r = (u0, u1, v0, v1) => rectOf([local(B, (u0 - 0.5) * B.W, 0.5 - v0, 0, [0, 0]), local(B, (u1 - 0.5) * B.W, 0.5 - v1, 0, [0, 0])]);
    return { paper: r(0.03, 0.14, 0.58, 0.72), band: r(0.02, 0.12, 0.37, 0.45), top: Math.round(local(B, 0, 0.5, 0, [0, 0])[1]), foot: Math.round(local(B, 0, -0.5, 0, [0, 0])[1]) };
  }
  const onJar = (phi, y, out) => frameOf(tmp.set(0.5 * Math.sin(rad(phi)), y, 0.5 * Math.cos(rad(phi))).applyMatrix4(jar.matrixWorld), out);
  function jarProbes() {
    if (!jar.visible || J.a < 0.99) return null;
    const r = (p0, p1, y0, y1) => rectOf([onJar(p0, y0, [0, 0]), onJar(p1, y1, [0, 0]), onJar(p0, y1, [0, 0]), onJar(p1, y0, [0, 0])]);
    return { body: r(-5, 5, 0.705, 0.75), body22: r(18, 26, 0.5, 0.6), collar: r(-8, 8, 0.82, 0.95) };
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
  const boxState = B => (B.g.visible ? { x: r1(B.x), y: r1(B.y), H: r1(B.H), yaw: r1(deg(B.yaw)), view: r2(deg(B.view)), a: r2(B.a) } : null);
  const state = () => ({ quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded,
    version, kits, lastP, horizon: r1(HORIZON), box: boxState(hero), renew: boxState(renew), cad: boxState(cad), mb: boxState(mb),
    jar: jar.visible ? { x: r1(J.x), y: r1(J.y), D: r1(J.D), tilt: r1(J.tilt), yaw: r1(J.yaw), lid: r2(J.lid), a: r2(J.a) } : null,
    spicules: { n: spicules.visible ? spicules.count : 0, o: r2(spicules.visible ? spiMat.opacity : 0), bbox: fieldBox() },
    glow: glows.map(g => r2(g.visible ? g.material.uniforms.uA.value : 0)), veil: r2(veil.visible ? veil.material.uniforms.uA.value : 0),
    probes: { box: boxProbes(hero), jar: jarProbes() } });
  return { draw, kit, dispose, state, animated: true };
}
