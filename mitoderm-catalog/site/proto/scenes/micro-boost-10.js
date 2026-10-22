// MICRO BOOST 10% live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D
// scene, as the approved sample EXOTECH GEL (scenes/exotech-gel.js) and the later pages (exosignal-spray.js: the print
// as one face texture with a metal map, the strokes, the edge fade). The engine keeps the story geometry (the
// cover-fitted 16:10 frame, the run's box, the phone stage, the kit card); this module draws the pose for the story
// position into the box. Objects are placed by frame pixel (2400×1500) inside the page's scene box (x 168…1248,
// y 285…1215: the scene left, the copy right), measured on the largest packshot, protocols/print/img/micro-boost-10.webp
// (385×1252): the tall ivory box seen from the camera's height (its horizon at 0.42 of the box from the top, so neither
// its top nor its foot shows), its right side a narrow plain strip; true proportions H : W : D = 4.21 : 1 : 1.21.
// The story (site/story3d.json; scratchpad spec pages/micro-boost-10/spec.md, BIOSPICULE line):
//   S1 meet     a stream of spicules flows from the medallion on the box up, over and down into the tip of a 3 ml
//               syringe and on into its barrel, where it gathers and fades
//   S2 why      the box and the syringe smaller on the left; a gold skin line: a flat glint slides along it and stops
//               on it (a peel works on the surface), then the spicules pass through it and stand under it, short ones
//               shallow, long ones deeper, thin gold channels left under the line
//   S3 inside   the syringe turns level, a drop swells at its nozzle and grows into the scene: inside it the spicules
//               sort into two rows, short above, long below
//   S4 feel     (no people: the owner's rule) a schematic cut of the epidermis rises, frosted, two layers, the short
//               spicules in the upper one, the long ones reaching the lower; gold sparks run in small circles on its
//               surface (the massage) and fade
//   S5 protocol the cut small on the right with gold micro-channels pulsing through its upper layer; box and syringe back
//   S6–S7 kit   the box alone in the packshot's pose: the picture that flies into the offer card
// The syringe has never been photographed: a neutral clear silhouette without print, scale, needle or cap, its
// plunger still (SYRINGE below: false takes it out, the stream then gathers into a small drop instead). The box never
// opens and turns only as far as the packshot shows its side (the side's width ≤ 0.263 of the front's). The product
// keeps its print's colours (emissive ≈ 85 % + neutral shading, toneMapped off); the line's green lives in the page's
// smoke, the brand's gold in the strokes, sparks and channels. No text is drawn but the package's own print
// (design/micro-boost-10/make_textures.py).
//
// createScene(THREE, { canvas, base, onLoad }) → { draw(p, view), kit(view) → canvas, animated, state(), dispose() }
//   p: the story position 0…5 (run index + progress); view: { cover, box, dpr, t, still } from the engine
export function createScene(THREE, { canvas, base, onLoad }) {
  const SYRINGE = true;   // the syringe's neutral silhouette (no photo of it yet): false leaves it out everywhere
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
  const D_BOX = DIST + 1.2, D_SYR = DIST + 0.4, D_DROP = DIST;

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

  // ---- the scene box's edges: anything crossing them (the syringe leaving to the left in S2 → S3) fades over their last
  // 48 px; the frame px of a fragment from its buffer pixel (set in fit())
  const BOXF = [168, 285, 1248, 1215], FADE = 48;
  const EDGE = { value: new THREE.Vector4(0, 0, 1, 1) };   // frame x, y of the canvas's top left; device px per frame px; canvas height
  const EDGE_GLSL = `float edgeFade(vec2 f) { return smoothstep(${BOXF[0]}.0, ${BOXF[0] + FADE}.0, f.x) * (1.0 - smoothstep(${BOXF[2] - FADE}.0, ${BOXF[2]}.0, f.x))
      * smoothstep(${BOXF[1]}.0, ${BOXF[1] + FADE}.0, f.y) * (1.0 - smoothstep(${BOXF[3] - FADE}.0, ${BOXF[3]}.0, f.y)); }`;
  const fragFrame = 'vec2(uEdge.x + gl_FragCoord.x / uEdge.z, uEdge.y + (uEdge.w - gl_FragCoord.y) / uEdge.z)';

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

  // the syringe and the drop: a clear glass without transmission (on the transparent canvas it would not see the page's
  // smoke; a phone pays a pass for it): no diffuse, its reflections of the studio and a Fresnel rim are its whole look
  const glass = (base0, rim, cc) => {
    const u = { uFade: { value: 1 }, uBase: { value: base0 }, uRim: { value: rim } };
    const m = new THREE.MeshPhysicalMaterial({ color: 0x000000, metalness: 0, roughness: 0.1, specularIntensity: 1, clearcoat: cc, clearcoatRoughness: 0.08,
      envMapIntensity: 1.25, transparent: true, depthWrite: false, toneMapped: false });
    m.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, u, { uEdge: EDGE });
      sh.fragmentShader = `uniform float uFade, uBase, uRim; uniform vec4 uEdge;\n${EDGE_GLSL}\n` + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
        { float c = clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0), F = pow(1.0 - c, 3.0);
          vec3 spec = gl_FragColor.rgb; float body = uBase + uRim * F;   // the reflection; the glass's own whiteness
          float a = clamp(body + 0.9 * max(max(spec.r, spec.g), spec.b), 0.0, 0.95);
          gl_FragColor = vec4((spec + vec3(0.93, 0.95, 0.94) * body) / max(a, 1e-3), a * uFade * edgeFade(${fragFrame})); }`);
    };
    m.customProgramCacheKey = () => 'mb10-glass'; m.userData.u = u; return m;
  };
  const glassBack = glass(0.05, 0.35, 0), glassFront = glass(0.07, 0.55, 0.6);
  glassBack.side = THREE.BackSide; glassFront.side = THREE.FrontSide;
  const rodMat = new THREE.MeshPhysicalMaterial({ color: new THREE.Color(0xd9d9d6).multiplyScalar(0.3), emissive: 0xd9d9d6, emissiveIntensity: 0.6, roughness: 0.35,
    transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false });   // a light grey plastic, its colour unknown
  rodMat.onBeforeCompile = sh => {
    sh.uniforms.uEdge = EDGE;
    sh.fragmentShader = `uniform vec4 uEdge;\n${EDGE_GLSL}\n` + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      gl_FragColor.a *= edgeFade(${fragFrame});`);
  };
  rodMat.customProgramCacheKey = () => 'mb10-rod';
  const dropBack = glass(0.04, 0.3, 0), dropFront = glass(0.06, 0.6, 0.5);
  dropBack.side = THREE.BackSide; dropFront.side = THREE.FrontSide;

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
  const MED = [0.5006, 0.5171];   // the medallion's centre on the front (u, v)
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

  // ---- the syringe, 3 ml, a neutral silhouette (length 1, its axis +y from the thumb pad to the nozzle): the barrel
  // OD 0.10 × 0.62, a luer nozzle 0.08 × Ø 0.04 (no needle, no cap), the finger flange 0.22 × 0.10 × 0.02, the plunger
  // out 0.25 with its cross-section rod and a pad Ø 0.18; the stopper inside the barrel. No print, no scale, no colour
  const syr = new THREE.Group(); scene.add(syr); syr.visible = SYRINGE;
  const V2 = (r, y) => new THREE.Vector2(r, y);
  const barrel = new THREE.LatheGeometry([V2(0.05, 0.25), V2(0.05, 0.868), V2(0.047, 0.882), V2(0.035, 0.898), V2(0.022, 0.915),
    V2(0.02, 0.922), V2(0.02, 0.995), V2(0.016, 1.0), V2(0.009, 1.0)], 64);
  const flange = new THREE.CylinderGeometry(1, 1, 0.02, 48).scale(0.11, 1, 0.05).translate(0, 0.26, 0);
  const syrParts = [];
  const sPart = (g, m, order) => { const x = new THREE.Mesh(g, m); x.renderOrder = order; syr.add(x); syrParts.push(x); return x; };
  sPart(barrel, glassBack, 30); sPart(flange, glassBack, 30);
  sPart(new THREE.BoxGeometry(0.07, 0.29, 0.012).translate(0, 0.165, 0), rodMat, 31);
  sPart(new THREE.BoxGeometry(0.012, 0.29, 0.07).translate(0, 0.165, 0), rodMat, 31);
  sPart(new THREE.CylinderGeometry(0.09, 0.09, 0.02, 48).translate(0, 0.01, 0), rodMat, 31);
  sPart(new THREE.CylinderGeometry(0.047, 0.047, 0.04, 48).translate(0, 0.31, 0), rodMat, 31);
  sPart(barrel, glassFront, 60); sPart(flange, glassFront, 60);

  // ---- the drop: a clear sphere (S2 → S3 on the nozzle, then the scene's container for the two rows)
  const dropGeo = new THREE.SphereGeometry(1, 64, 48);
  const dropB = new THREE.Mesh(dropGeo, dropBack), dropF = new THREE.Mesh(dropGeo, dropFront);
  dropB.renderOrder = 20; dropF.renderOrder = 50; scene.add(dropB, dropF);

  // ---- the line's graphics, flat to the camera in frame pixels (a plane: local x = px − 1200, y = 750 − py), drawn
  // over the box by order (they never pass behind it): strokes ≥ 1.5 device px wide with a soft edge
  const pxU = { value: 1 };   // device px per frame px
  const fx = new THREE.Group(); scene.add(fx);
  at(1200, 750, DIST, fx.position); fx.scale.setScalar(world(1, DIST));
  const hex3 = h => new THREE.Vector3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  const ADD = { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.SrcAlphaFactor, blendDst: THREE.OneFactor,
    blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor };   // a glow adds its colour and keeps a true alpha
  const QUAD_V = 'varying vec2 vF; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vF = vec2(position.x + 1200.0, 750.0 - position.y); gl_Position = projectionMatrix * viewMatrix * w; }';

  // the skin: S2's gold line with a faint surface going back from it (seen from above: the line is under the horizon);
  // S4–S5 the cut of the epidermis grown from it: a frosted warm white (#EFE6DC) top seen at a slant and a front of two
  // layers (0.3 / 0.7), its surface the gold line, the layers' boundary a gold hairline; no dermis, no labels
  const SK = { uPx: pxU, uE: { value: new THREE.Vector4(600, 1235, 1010, 0) }, uT: { value: new THREE.Vector4(60, 0, 0, 0) },
    uL: { value: new THREE.Vector4(0, 1, 2.5, 0) }, uO: { value: 1 } };
  const skinMat = new THREE.ShaderMaterial({ uniforms: SK, transparent: true, depthTest: false, depthWrite: false, vertexShader: QUAD_V,
    fragmentShader: `uniform float uPx, uO; uniform vec4 uE, uT, uL; varying vec2 vF;
      ${EDGE_GLSL}
      vec4 over(vec4 d, vec3 c, float a) { float o = a + d.a * (1.0 - a); return vec4((c * a + d.rgb * d.a * (1.0 - a)) / max(o, 1e-4), o); }
      float band(float v, float a, float b) { return clamp((v - a) * uPx + 0.5, 0.0, 1.0) * clamp((b - v) * uPx + 0.5, 0.0, 1.0); }
      void main() {
        float x = vF.x, y = vF.y, x0 = uE.x, x1 = uE.y, ye = uE.z, hs = uE.w, dt = uT.x;
        float inX = band(x, x0, x1);
        vec3 skin = vec3(0.937, 0.902, 0.863), lit = vec3(0.98, 0.965, 0.94);
        vec4 c = vec4(0.0);
        // the top, going back from the edge: fainter toward the back
        float top = band(y, ye - dt, ye) * inX * uT.y * mix(0.25, 1.0, clamp((y - ye + dt) / max(dt, 1.0), 0.0, 1.0));
        c = over(c, lit, top);
        // the front: two layers, its rims a little lighter (the frosted glass's edges)
        float sec = band(y, ye, ye + hs) * inX, k = (y - ye) / max(hs, 1.0);
        float rimD = min(min(x - x0, x1 - x), ye + hs - y), rim = 1.0 - smoothstep(0.0, 12.0, rimD);
        c = over(c, mix(skin, lit, rim), sec * uT.z * (k < 0.3 ? 1.0 : 0.82) * (1.0 + 0.9 * rim));
        // the gold: the surface line (drawn left to right to uL.y), the boundary of the layers
        vec3 gold = mix(vec3(0.788, 0.635, 0.294), vec3(0.847, 0.741, 0.494), smoothstep(x0, x1, x) * 0.6 + 0.2);
        float xd = mix(x0, x1, uL.y), hwl = max(uL.z * 0.5, 0.75 / uPx);
        float line = clamp((hwl - abs(y - ye)) * uPx + 0.5, 0.0, 1.0) * inX * clamp((xd - x) * uPx + 0.5, 0.0, 1.0) * uL.x;
        float hair = clamp((max(0.5, 0.6 / uPx) - abs(y - ye - 0.3 * hs)) * uPx + 0.5, 0.0, 1.0) * sec * uL.w;
        c = over(c, gold, hair); c = over(c, gold, line);
        gl_FragColor = vec4(c.rgb, c.a * uO * edgeFade(vF));
      }` });
  const skin = new THREE.Mesh(new THREE.PlaneGeometry(BOXF[2] - BOXF[0], BOXF[3] - BOXF[1]).translate((BOXF[0] + BOXF[2]) / 2 - 1200, 750 - (BOXF[1] + BOXF[3]) / 2, 0), skinMat);
  skin.renderOrder = 10; skin.frustumCulled = false; fx.add(skin);
  // the kit's backlight: a soft glow of the line's green behind the box (S6–S7 and the offer card's picture), its
  // ellipse within the box's height (the card's picture, cut to what has alpha, keeps the box's size); no ring
  const GL = { uC: { value: hex3(0x24573f) }, uA: { value: 0 }, uR: { value: new THREE.Vector4(600, 812, 330, 360) } };
  const glow = new THREE.Mesh(new THREE.PlaneGeometry(BOXF[2] - BOXF[0], BOXF[3] - BOXF[1]).translate((BOXF[0] + BOXF[2]) / 2 - 1200, 750 - (BOXF[1] + BOXF[3]) / 2, 0),
    new THREE.ShaderMaterial({ uniforms: GL, transparent: true, depthTest: false, depthWrite: false, vertexShader: QUAD_V,
      fragmentShader: `uniform vec3 uC; uniform float uA; uniform vec4 uR; varying vec2 vF;
        void main() { vec2 q = (vF - uR.xy) / uR.zw; float r2 = dot(q, q); gl_FragColor = vec4(uC, uA * exp(-3.0 * r2) * (1.0 - smoothstep(0.6, 1.0, r2))); }` }));
  glow.renderOrder = 0; glow.frustumCulled = false; glow.visible = false; fx.add(glow);

  // the spicules and the gold: instanced ribbons (one draw each), every instance's place, angle, length and opacity
  // set on the CPU per frame and uploaded at once. A spicule: a spindle, dark green as on the medallion (#243523), a light
  // glassy rim (#D7E4D0, α 0.55) so it reads on the green smoke, a gold glint on about one in eight; ≥ 1.5 device px
  // wide, soft-edged. The gold (additive): ribbons (channels, tails), spots (sparks, the glint)
  const RIB_V = `attribute vec4 iA, iB; uniform float uPx; varying vec2 vQ, vF; varying float vHw, vLen, vA, vK, vPh;
    void main() {
      float L = max(iA.w, 0.5), hw = max(iB.y * 0.5, 0.75 / uPx), pad = 1.5 / uPx;
      vec2 ax = vec2(cos(iA.z), sin(iA.z)), nr = vec2(-ax.y, ax.x);
      vQ = vec2(position.x * (L * 0.5 + pad), position.y * (hw + pad));
      vec2 p = iA.xy + ax * vQ.x + nr * vQ.y;
      vHw = hw; vLen = L; vA = iB.x; vK = iB.z; vPh = iB.w; vF = p;
      gl_Position = iB.x > 0.003 ? projectionMatrix * modelViewMatrix * vec4(p.x - 1200.0, 750.0 - p.y, 0.0, 1.0) : vec4(2.0, 2.0, 2.0, 1.0);
    }`;
  const SPI_F = `uniform float uPx, uTime, uSpin; varying vec2 vQ, vF; varying float vHw, vLen, vA, vK, vPh;
    ${EDGE_GLSL}
    void main() {
      float t = vQ.x / (vLen * 0.5), h = vHw * max(1.0 - t * t, 0.0), d = abs(vQ.y);
      float cov = clamp((h - d) * uPx + 0.5, 0.0, 1.0) * step(abs(t), 1.0);
      if (cov < 0.004) discard;
      float r = clamp(d / max(h, 1e-3), 0.0, 1.0), rim = smoothstep(0.35, 0.95, r) * (1.0 - uSpin * 0.5 * (1.0 + sin(t * 4.0 - uTime * 2.2 + vPh * 6.0)));
      vec3 col = mix(vec3(0.141, 0.208, 0.137), vec3(0.843, 0.894, 0.816), rim);
      float g = vK * exp(-pow((t - 0.6 * sin(uTime * 0.7 + vPh * 6.0)) / 0.3, 2.0)) * (0.55 + 0.45 * sin(uTime * 3.0 + vPh * 40.0));
      col = mix(col, vec3(0.847, 0.741, 0.494), clamp(g, 0.0, 1.0));
      gl_FragColor = vec4(col, cov * vA * mix(1.0, 0.55, rim) * edgeFade(vF));
    }`;
  const GOLD_F = `uniform float uPx; varying vec2 vQ, vF; varying float vHw, vLen, vA, vK, vPh;
    ${EDGE_GLSL}
    void main() {
      float t = vQ.x / (vLen * 0.5), d = abs(vQ.y), a;
      if (vK < 0.5) {        // a ribbon, its ends rounded off
        a = clamp((vHw - d) * uPx + 0.5, 0.0, 1.0) * (1.0 - smoothstep(0.85, 1.0, abs(t)));
      } else if (vK < 1.5) { // a spot: a soft ellipse (len × width)
        vec2 q = vec2(t, d / max(vHw, 1e-3)); float r2 = dot(q, q); a = exp(-3.0 * r2) * (1.0 - smoothstep(0.6, 1.0, r2));
      } else {               // a tail: fading back from its head (+t)
        a = clamp((vHw - d) * uPx + 0.5, 0.0, 1.0) * smoothstep(-1.0, 1.0, t) * (1.0 - smoothstep(0.92, 1.0, t));
      }
      vec3 col = mix(vec3(0.788, 0.635, 0.294), vec3(0.847, 0.741, 0.494), 0.6 + 0.4 * sin(vPh * 9.0));
      gl_FragColor = vec4(col, a * vA * edgeFade(vF));
    }`;
  const quad = (n, A, B) => {
    const g = new THREE.InstancedBufferGeometry();
    g.setIndex([0, 1, 2, 0, 2, 3]); g.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
    g.setAttribute('iA', new THREE.InstancedBufferAttribute(A, 4).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('iB', new THREE.InstancedBufferAttribute(B, 4).setUsage(THREE.DynamicDrawUsage));
    g.instanceCount = n; return g;
  };
  const NS = 600, NS_PH = 360, NG = 64;
  const SA = new Float32Array(NS * 4), SB = new Float32Array(NS * 4), GA = new Float32Array(NG * 4), GB = new Float32Array(NG * 4);
  const swU = { uPx: pxU, uTime: { value: 0 }, uSpin: { value: 0 } };
  const swarm = new THREE.Mesh(quad(NS, SA, SB), new THREE.ShaderMaterial({ uniforms: swU, vertexShader: RIB_V, fragmentShader: SPI_F,
    transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide }));
  const goldFx = new THREE.Mesh(quad(NG, GA, GB), new THREE.ShaderMaterial(Object.assign({ uniforms: { uPx: pxU }, vertexShader: RIB_V, fragmentShader: GOLD_F,
    transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide }, ADD)));
  swarm.renderOrder = 40; goldFx.renderOrder = 41; swarm.frustumCulled = goldFx.frustumCulled = false; fx.add(swarm, goldFx);

  // each spicule's seeds: its kind (40 : 60 short : long by count — a picture of the catalogue's 40 % / 60 %, not a
  // measured ratio), its rank (the layouts show fewer of them later: those ranked under the layout's share), its phase
  const rng = (s => () => { s |= 0; s = s + 0x6d2b79f5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; })(20261022);
  const gau = () => { const r = Math.sqrt(-2 * Math.log(Math.max(1e-6, rng()))); return r * Math.cos(2 * Math.PI * rng()); };
  const SEED = Array.from({ length: NS }, () => ({ u: rng(), w: rng(), g0: gau(), g1: gau(), ph: rng(), lag: rng() * 0.25, glint: rng() < 0.12 ? 1 : 0 }));
  const perm = Array.from({ length: NS }, (_, i) => i); for (let i = NS - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; }
  SEED.forEach((s, i) => { s.rank = perm[i] / NS; s.long = s.u >= 0.4; });
  const SHORT = 0.27;   // the short ones' length: 90 / 330 µm (b2.label1–2)

  // ---- poses (frame px). The box [cx, h, opacity, k]: k the horizon's place on it from the top (0.42 as on the
  // packshot; its top and foot never show while both stay ≥ 5 % of its height off the horizon: k ≤ 0.95), θ always the
  // packshot's angle (θmax, the sway aside); the syringe [x, y of its middle, angle° (0 nozzle up, 90 nozzle right),
  // length px, opacity]: its length is 0.758 of the box's height in the world (it is nearer: 0.8 of the box's px height
  // where both stand).
  // S5 keeps above the page's three step cards: while the story holds there they come up to frame y ≈ 925 on a 16:10
  // screen and ≈ 800 on 1920×1080, so the box stands high on its horizon (k 0.94: its foot at 775, the syringe's pad at
  // 772) and the cut is high
  const BOX = [[520, 780, 1, 0.42], [330, 560, 1, 0.42], [330, 560, 0, 0.42], [330, 560, 0, 0.42], [360, 420, 1, 0.94], [600, 780, 1, 0.42]];
  const SYR = [[790, 883, 0, 624, 1], [480, 841, 0, 448, 1], [60, 750, 90, 448, 0], [60, 750, 90, 448, 0], [530, 604, 0, 336, 1], [530, 604, 0, 336, 0]];
  // S2's line and S4–S5's cut: [x0, x1, edge y, height, top's depth px]
  const LINE = [600, 1235, 1010], CUT3 = [278, 1138, 790, 230, 100], CUT4 = [700, 1220, 560, 150, 64];
  const DROP = [708, 750, 300];

  // the layouts of the spicules: [x, y, angle, length, opacity] of spicule i at time t (still: the cycle's last state)
  const LS = [1, 0.12, 0.25, 0.10, 0.07, 0];   // the share of the spicules each layout shows (S1 all; a phone 360 of 600)
  const bez = (a, c, b, s, o) => { const u = 1 - s; o[0] = u * u * a[0] + 2 * u * s * c[0] + s * s * b[0]; o[1] = u * u * a[1] + 2 * u * s * c[1] + s * s * b[1]; return o; };
  const bezT = (a, c, b, s) => Math.atan2(2 * (1 - s) * (c[1] - a[1]) + 2 * s * (b[1] - c[1]), 2 * (1 - s) * (c[0] - a[0]) + 2 * s * (b[0] - c[0]));
  const bez3 = (a, b, c, d, s, o) => { const u = 1 - s, A = u * u * u, B = 3 * u * u * s, C = 3 * u * s * s, D = s * s * s;
    o[0] = A * a[0] + B * b[0] + C * c[0] + D * d[0]; o[1] = A * a[1] + B * b[1] + C * c[1] + D * d[1]; return o; };
  // S1's stream, laid out in the S1 poses' frame px: it leaves the medallion to the right, level (its spread inside the
  // disc; over the front it keeps ≥ 35 px below «SPICULE SERUM»), turns up only past the box's side, rises in the gap
  // left of the syringe to an apex 126 px above the nozzle, comes straight down into it and on into the barrel (behind its
  // front glass), where it gathers and fades: story3d screen 1, «собирается в нём». Sampled by run time: a spicule's speed
  // goes as 1 / the stream's width^0.8 (a narrowing stream runs faster), so spicules spread evenly in time never pile up
  // at the tip. Per frame the path is moved onto the medallion and the nozzle as they are then (S1 → S2 both move);
  // without the syringe it ends at the tip, where the small drop gathers it
  const M0 = [0, 0], T0 = [SYR[0][0], SYR[0][1] - SYR[0][3] / 2];   // the S1 medallion, the S1 nozzle's mouth
  placeBox(BOX[0][0], BOX[0][1], BOX[0][3], thetaMax(BOX[0][0], BOX[0][1], BOX[0][3]));
  local((MED[0] - 0.5) * BW, (0.5 - MED[1]) * BH, 0, M0);
  const PN = 256, PX_ = new Float32Array(PN), PY_ = new Float32Array(PN), PA_ = new Float32Array(PN), PW_ = new Float32Array(PN), PO_ = new Float32Array(PN);
  {
    const R = 0.10256 * BOX[0][1], T = (dx, dy) => [T0[0] + dx, T0[1] + dy];   // the medallion's radius (the texture's MED_R)
    const segs = [[M0, [M0[0] + 120, M0[1] - 5], T(-122, 149), T(-90, 39)], [T(-90, 39), T(-66, -46), T(-55, -126), T(-15, -126)],
      [T(-15, -126), T(3, -126), T(0, -71), T(0, 0)]];
    if (SYRINGE) segs.push([T(0, 0), T(0, 40), T(0, 85), T(0, 130)]);   // down the nozzle into the barrel
    // per segment, its half width and opacity along it (u 0…1): 0.55 R at the disc, 4.5 px down the nozzle (its bore
    // ≈ 12 px), a little wider again in the barrel, fading there (or at the tip, without the syringe)
    const wOf = (k, u) => k === 0 ? lerp(0.55 * R, 30, smooth(0, 1, u)) : k === 1 ? lerp(30, 16, u) : k === 2 ? lerp(16, 4.5, u) : lerp(4.5, 13, smooth(0.3, 1, u));
    const oOf = (k, u) => k === 0 ? smooth(0, 0.08, u) : k === 1 ? 1 : k === 2 ? (SYRINGE ? 1 : 1 - smooth(0.6, 1, u)) : 1 - smooth(0.3, 1, u);
    const raw = [], q = [0, 0], q1 = [0, 0]; let run = 0;
    segs.forEach((g, k) => { bez3(g[0], g[1], g[2], g[3], 0, q1); for (let i = 1; i <= 400; i++) {
      const u = i / 400; bez3(g[0], g[1], g[2], g[3], u, q); const ds = Math.hypot(q[0] - q1[0], q[1] - q1[1]), w = wOf(k, u);
      run += ds * Math.pow(w, 0.8); raw.push([q[0], q[1], Math.atan2(q[1] - q1[1], q[0] - q1[0]), w, oOf(k, u), run]); q1[0] = q[0]; q1[1] = q[1]; } });
    for (let j = 0, r = 0; j < PN; j++) {   // resampled evenly in run time
      const tt = j / (PN - 1) * run; while (r < raw.length - 2 && raw[r + 1][5] < tt) r++;
      const a = raw[r], b = raw[r + 1], u = clamp((tt - a[5]) / Math.max(b[5] - a[5], 1e-9));
      PX_[j] = lerp(a[0], b[0], u); PY_[j] = lerp(a[1], b[1], u); PA_[j] = lerp(a[2], b[2], u); PW_[j] = lerp(a[3], b[3], u); PO_[j] = lerp(a[4], b[4], u);
    }
  }
  // where the stream's ends are now (pose() sets them each frame): the medallion of the box drawn, the syringe's nozzle;
  // S1's path is moved and stretched onto them (x and y apart: the syringe stays upright)
  const MC = [0, 0], TC = [0, 0], PM = [1, 1, 1];   // PM: x scale, y scale, length scale
  const E1 = [0, 0], C1 = [0, 0], bp = [0, 0];   // layout 1's scratch: its end and control points, the point on it
  function layout(k, i, t, still, o) {
    const s = SEED[i]; o[4] = 0;
    if (k === 0) {   // S1: down the stream, each spicule at its own phase
      const tau = still ? s.ph : (s.ph + t * 0.11) % 1, fj = tau * (PN - 1), j = Math.min(PN - 2, fj | 0), u = fj - j;
      const a = lerp(PA_[j], PA_[j + 1], u), w = lerp(PW_[j], PW_[j + 1], u), b0 = Math.tanh(0.55 * s.g0), b1 = Math.tanh(0.55 * s.g1);
      const ca = Math.cos(a), sa = Math.sin(a), x = lerp(PX_[j], PX_[j + 1], u) - sa * b0 * w + ca * b1 * 6, y = lerp(PY_[j], PY_[j + 1], u) + ca * b0 * w + sa * b1 * 6;
      const aj = a + b1 * 0.5 * (1 - tau) * (1 - tau);   // a little astray at the start, in line by the nozzle
      o[0] = MC[0] + (x - M0[0]) * PM[0]; o[1] = MC[1] + (y - M0[1]) * PM[1]; o[2] = Math.atan2(Math.sin(aj) * PM[1], Math.cos(aj) * PM[0]);
      o[3] = (s.long ? 44 : 44 * SHORT) * (0.85 + 0.3 * s.w) * PM[2]; o[4] = lerp(PO_[j], PO_[j + 1], u) * 0.95;
    } else if (k === 1) {   // S2: through the line, then standing under it: short ones shallow, long ones deeper
      const tau = still ? 6 : t % 7, x = 700 + 450 * s.w, L = (s.long ? 80 : 80 * SHORT) * (0.85 + 0.3 * s.ph);
      const q = still ? 1 : smooth(2.5 + s.lag * 4, 4.6 + s.lag * 4, tau);
      E1[0] = x + 6 * s.g1; E1[1] = LINE[2] + L / 2 + 1; C1[0] = (MC[0] + x) / 2; C1[1] = 700 + 40 * s.g0;
      const lean = rad(90 + clamp(s.g1, -1.8, 1.8) * 9);   // standing under it, leaning as it went in
      bez(MC, C1, E1, q, bp); const a = q < 1 ? lerp(bezT(MC, C1, E1, q), lean, smooth(0.8, 1, q)) : lean;
      o[0] = bp[0]; o[1] = bp[1]; o[2] = a; o[3] = L;
      // those still on their way go with the box when it fades (S2 → S3): none leave a medallion no longer there; the
      // ones standing under the line stay and flow on into the drop
      o[4] = smooth(0, 0.04, q) * (1 - smooth(6.0, 6.8, tau)) * 0.95 * lerp(ST.box[2], 1, smooth(0.7, 1, q));
    } else if (k === 2) {   // S3: in the drop, two rows: short above, long below, nearly level
      const L = s.long ? 150 : 150 * SHORT, sw = still ? 0 : Math.sin(t * 0.4 + s.ph * 6.28);
      o[0] = s.long ? 520 + 376 * s.w : 530 + 356 * s.w; o[1] = (s.long ? 840 : 660) + 35 * (2 * s.ph - 1) + 3 * sw;
      o[2] = rad(clamp(s.g0, -1.5, 1.5) * 10) + 0.05 * sw; o[3] = L; o[4] = 0.95;
    } else if (k === 3 || k === 4) {   // S4 / S5: grown into the cut from its surface, short ones in the upper layer; they
      // ride in the cut as it is now (rising, shrinking, sinking)
      const C = ST.cut, hs = C[3], L = s.long ? hs * 0.78 : hs * 0.78 * SHORT;
      const a = rad(90 + clamp(s.g0, -1.6, 1.6) * 22), x = C[0] + 24 + (C[1] - C[0] - 48) * s.w;
      o[0] = x + Math.cos(a) * L / 2; o[1] = C[2] + 3 + Math.sin(a) * L / 2; o[2] = a; o[3] = L; o[4] = 0.95;
    }
    return o;
  }

  // ---- the story's state at position p, written in place (nothing allocated per frame)
  const ST = { box: [0, 0, 0, 0], syr: [0, 0, 0, 0, 0], drop: [0, 0, 0, 0], cut: [0, 0, 0, 0, 0], top: 0, sec: 0, line: 0, draw: 1, hair: 0, cutO: 0, glow: 0,
    sw: [0, 0, 0, 0, 0], glint: 0, chan1: 0, sparks: 0, chan4: 0 };   // sw: layout k → k1, its blend window [a, b], f
  const mixA = (o, a, b, s) => { for (let i = 0; i < o.length; i++) o[i] = lerp(a[i], b[i], s); return o; };
  const setSw = (st, ka, kb, wa, wb, f) => { const w = st.sw; w[0] = ka; w[1] = kb; w[2] = wa; w[3] = wb; w[4] = f; };
  const setCut = (st, x0, x1, y, hs, dt) => { const c = st.cut; c[0] = x0; c[1] = x1; c[2] = y; c[3] = hs; c[4] = dt; };
  function story(p) {
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST;
    st.top = st.sec = st.line = st.hair = st.cutO = st.glint = st.chan1 = st.sparks = st.chan4 = st.glow = 0; st.draw = 1;
    st.drop[3] = 0; mixA(st.box, BOX[k], BOX[k + 1], smooth(0, 1, f)); mixA(st.syr, SYR[k], SYR[k + 1], smooth(0, 1, f));
    if (k === 0) {   // S1 → S2: the pair recedes left and smaller; the stream turns from the nozzle to the line, drawn left to right
      setSw(st, 0, 1, 0.1, 0.9, f);
      st.line = 1; st.draw = smooth(0.3, 1, f); st.top = 0.04 * st.draw; setCut(st, LINE[0], LINE[1], LINE[2], 0, 60);
      st.glint = st.chan1 = smooth(0.6, 1, f); st.cutO = 1;
      if (!SYRINGE) { st.drop[0] = T0[0]; st.drop[1] = T0[1]; st.drop[2] = 18 * (1 - smooth(0, 0.5, f)); st.drop[3] = 1; }
    } else if (k === 1) {   // S2 → S3: the line goes, the box goes; the syringe turns level and rises, a drop swells at its
      // nozzle and grows into the scene (the camera goes into it), the syringe leaves left; the spicules gather in two rows
      setSw(st, 1, 2, 0.5, 1, f);   // the rows gather as the drop grows round them (0.5–0.9)
      st.line = 1 - smooth(0, 0.3, f); st.top = 0.04 * st.line; setCut(st, LINE[0], LINE[1], LINE[2], 0, 60); st.cutO = 1;
      st.glint = st.chan1 = 1 - smooth(0, 0.3, f);
      st.box[2] = 1 - smooth(0, 0.35, f);
      const turn = smooth(0, 0.4, f), away = smooth(0.5, 0.85, f);
      st.syr[0] = lerp(SYR[1][0], SYR[2][0], away); st.syr[1] = lerp(SYR[1][1], 750, turn); st.syr[2] = 90 * turn; st.syr[3] = SYR[1][3]; st.syr[4] = 1 - away;
      const tipX = st.syr[0] + Math.sin(rad(st.syr[2])) * st.syr[3] / 2, tipY = st.syr[1] - Math.cos(rad(st.syr[2])) * st.syr[3] / 2;
      const r0 = 40 * smooth(0.25, 0.5, f), grow = smooth(0.5, 0.9, f);
      const nx = SYRINGE ? tipX + r0 * 0.8 : DROP[0], ny = SYRINGE ? tipY : DROP[1];
      st.drop[0] = lerp(nx, DROP[0], grow); st.drop[1] = lerp(ny, DROP[1], grow);
      st.drop[2] = SYRINGE ? lerp(r0, DROP[2], grow) : DROP[2] * smooth(0.3, 0.9, f); st.drop[3] = 1;
    } else if (k === 2) {   // S3 → S4: the cut rises from below; the rows run down and right into it; the drop widens and goes
      setSw(st, 2, 3, 0.2, 1, f);
      const up = smooth(0, 0.6, f); setCut(st, CUT3[0], CUT3[1], CUT3[2] + 260 * (1 - up), CUT3[3], CUT3[4]);
      st.cutO = up; st.top = 0.10; st.sec = 0.16; st.line = 1; st.hair = 0.4;
      const gone = smooth(0.3, 0.7, f); st.drop[0] = DROP[0]; st.drop[1] = DROP[1]; st.drop[2] = DROP[2] * (1 + 0.15 * gone); st.drop[3] = 1 - gone;
      st.sparks = smooth(0.7, 1, f);
    } else if (k === 3) {   // S4 → S5: the cut shrinks and moves right, its channels light; box and syringe come back left
      setSw(st, 3, 4, 0.1, 0.9, f);
      mixA(st.cut, CUT3, CUT4, smooth(0, 0.6, f)); st.cutO = 1; st.top = 0.10; st.sec = 0.16; st.line = 1; st.hair = 0.4;
      st.sparks = 1 - smooth(0, 0.3, f); st.chan4 = smooth(0.5, 1, f);   // (the cut clears the left before the pair comes)
      const back = smooth(0.45, 0.9, f);
      for (let i = 0; i < 4; i++) { st.box[i] = BOX[4][i]; st.syr[i] = SYR[4][i]; }
      st.box[2] = back; st.syr[4] = back;
    } else {   // S5 → kit: the cut sinks and goes, the syringe goes; the box comes forward into the packshot's pose
      setSw(st, 4, 5, 0, 0.5, f);
      const down = smooth(0, 0.5, f); setCut(st, CUT4[0], CUT4[1], CUT4[2] + 200 * down, CUT4[3], CUT4[4]);
      st.cutO = 1 - down; st.top = 0.10; st.sec = 0.16; st.line = 1; st.hair = 0.4; st.chan4 = 1 - smooth(0, 0.4, f);
      st.syr[4] = 1 - smooth(0, 0.4, f); st.glow = smooth(0.5, 1, f);   // the backlight comes up as the box arrives
      mixA(st.box, BOX[4], BOX[5], smooth(0.45, 1, f));   // it waits for the step cards to pass over the scene
    }
    if (!SYRINGE) st.syr[4] = 0;
    return st;
  }

  // ---- applying a state (in place: no garbage per frame; the QA probes are worked out in state() only)
  const Lk = [0, 0, 0, 0, 0], Lk1 = [0, 0, 0, 0, 0], thC = [NaN, NaN, NaN, 0];   // thC: θmax's last pose and value
  const last = { th: 0, ratio: 0, top: 0, bottom: 0, swarm: 0, glints: 0, t: 0, drop: 0, cut: 0 };
  let gN = 0;   // the gold instances written this frame
  function put(x, y, a, len, w, al, kind, phs) {
    if (gN >= NG || al < 0.003) return;
    const j = gN * 4; GA[j] = x; GA[j + 1] = y; GA[j + 2] = a; GA[j + 3] = len; GB[j] = al; GB[j + 1] = w; GB[j + 2] = kind; GB[j + 3] = phs; gN++;
  }
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
    // the stream's ends as they are now: the medallion of the box as placed, the syringe's nozzle; S1's path onto them
    local((MED[0] - 0.5) * BW, (0.5 - MED[1]) * BH, 0, MC);
    const sx = st.syr[0], sy = st.syr[1], sa = st.syr[2], sl = st.syr[3], so = st.syr[4];
    TC[0] = sx + Math.sin(rad(sa)) * sl / 2; TC[1] = sy - Math.cos(rad(sa)) * sl / 2;
    PM[0] = (TC[0] - MC[0]) / (T0[0] - M0[0]); PM[1] = (TC[1] - MC[1]) / (T0[1] - M0[1]); PM[2] = Math.sqrt(Math.abs(PM[0] * PM[1]));
    // the syringe: its middle at (x, y), turned in the picture's plane
    syr.visible = SYRINGE && so > 0.004;
    if (syr.visible) {
      at(sx, sy, D_SYR, syr.position); const L = world(sl, D_SYR); syr.scale.setScalar(L);
      syr.rotation.set(0, 0, -rad(sa)); syr.translateY(-0.5 * L);   // its middle, not its pad, at (x, y)
      glassBack.userData.u.uFade.value = glassFront.userData.u.uFade.value = so; rodMat.opacity = 0.55 * so;
      glassFront.clearcoat = ph ? 0 : 0.6;
    }
    // the drop
    const dx = st.drop[0], dy = st.drop[1], dr = st.drop[2], dop = st.drop[3];
    dropB.visible = dropF.visible = dr > 0.5 && dop > 0.004;
    if (dropB.visible) {
      at(dx, dy, D_DROP, dropB.position); dropF.position.copy(dropB.position); dropB.scale.setScalar(world(dr, D_DROP)); dropF.scale.copy(dropB.scale);
      dropBack.userData.u.uFade.value = dropFront.userData.u.uFade.value = dop * (1 + 0.02 * Math.sin(t * 0.8) * live);
      dropFront.clearcoat = ph ? 0 : 0.5;
    }
    // the skin: the line, the cut; drawn only when it shows something (S1 holds it with the line not yet drawn)
    SK.uE.value.set(st.cut[0], st.cut[1], st.cut[2], st.cut[3]); SK.uT.value.set(st.cut[4], st.top, st.sec, 0);
    SK.uL.value.set(st.line, st.draw, 2.5, st.hair); SK.uO.value = st.cutO;
    skin.visible = st.cutO > 0.004 && (st.line * st.draw > 0.004 || st.top > 0.004 || st.sec > 0.004 || st.hair > 0.004);
    // the spicules: each one's place in the two layouts of this transition, mixed (weighted by its opacity in each, so a
    // spicule only in one fades where it is, one in both flows between them), each a little late or early; a layout whose
    // weight is nil is not worked out
    const n = ph ? NS_PH : NS, ka = st.sw[0], kb = st.sw[1], fw = clamp((st.sw[4] - st.sw[2]) / (st.sw[3] - st.sw[2]));
    swU.uTime.value = t; swU.uSpin.value = (ka === 2 ? 1 - fw : kb === 2 ? fw : 0) * (still ? 0 : 1);
    let shown = 0;
    for (let i = 0; i < n; i++) {
      const s = SEED[i], q = smooth(0, 1, clamp((fw - s.lag) / 0.75));
      if (q < 1 && s.rank < LS[ka]) layout(ka, i, t, still, Lk); else Lk[4] = 0;
      if (q > 0 && s.rank < LS[kb]) layout(kb, i, t, still, Lk1); else Lk1[4] = 0;
      const A = (1 - q) * Lk[4], B = q * Lk1[4], W = A + B;
      const j = i * 4;
      if (W < 0.003) { SB[j] = 0; continue; }
      SA[j] = (A * Lk[0] + B * Lk1[0]) / W; SA[j + 1] = (A * Lk[1] + B * Lk1[1]) / W;
      SA[j + 2] = 0.5 * Math.atan2(A * Math.sin(2 * Lk[2]) + B * Math.sin(2 * Lk1[2]), A * Math.cos(2 * Lk[2]) + B * Math.cos(2 * Lk1[2]));
      if (B > A ? Math.cos(SA[j + 2] - Lk1[2]) < 0 : Math.cos(SA[j + 2] - Lk[2]) < 0) SA[j + 2] += Math.PI;   // keep its heading
      SA[j + 3] = (A * Lk[3] + B * Lk1[3]) / W;
      SB[j] = Math.min(1, W); SB[j + 1] = SA[j + 3] / 28; SB[j + 2] = s.glint; SB[j + 3] = s.ph;
      if (W > 0.02) shown++;
    }
    swarm.geometry.instanceCount = n; swarm.geometry.attributes.iA.needsUpdate = swarm.geometry.attributes.iB.needsUpdate = true;
    swarm.visible = shown > 0; last.swarm = shown;
    // the gold: S2's glint and channels, S4's sparks, S5's micro-channels
    gN = 0;
    if (st.glint > 0.004) {   // the peel: a flat glint slides along the line and stops on it (0–2 s of the 7 s beat)
      const tau = still ? 6 : t % 7, gx = lerp(620, 900, smooth(0, 2, tau)), ga = smooth(0, 0.3, tau) * (1 - smooth(6.2, 6.9, tau));
      put(gx, LINE[2], 0, 120, 9, 0.9 * ga * st.glint, 1, 0.1);
      for (let c = 0; c < 16; c++) {   // the channels under the line where the spicules went through (1.5 px, α 0.6)
        const s = SEED[c * 7], x = 712 + c * 27 + 8 * s.g1, L = s.long ? 80 : 80 * SHORT;
        const on = still ? 1 : smooth(3.2 + c * 0.12, 4.4 + c * 0.12, tau) * (1 - smooth(6.0, 6.8, tau));
        put(x, LINE[2] + 2 + L / 2, rad(90 + 6 * s.g0), L, 1.5, 0.6 * on * st.chan1, 0, s.ph);
      }
    }
    if (st.sparks > 0.004 && !still) {   // the massage: sparks running on small circles over the cut's top, fading through 8 s
      const C = CUT3, tau = t % 8, fade = smooth(0, 0.6, tau) * (1 - smooth(3.5, 7.5, tau)), N = ph ? 12 : 16;
      for (let c = 0; c < N; c++) {
        const ring = c % 4, ox = lerp(C[0], C[1], 0.2 + 0.2 * ring), oy = C[2] - C[4] * 0.45, w = 1.1 * (ring % 2 ? 1 : -1);
        const a = w * t + (c >> 2) * Math.PI / 2 + ring, x = ox + 90 * Math.cos(a), y = oy + 30 * Math.sin(a), dir = Math.atan2(30 * Math.cos(a) * w, -90 * Math.sin(a) * w);
        put(x, y, 0, 13, 13, 0.85 * fade * st.sparks, 1, c * 0.13);
        put(x - Math.cos(dir) * 15, y - Math.sin(dir) * 15, dir, 30, 2.2, 0.55 * fade * st.sparks, 2, c * 0.13);
      }
    }
    if (st.chan4 > 0.004) {   // the protocol: micro-channels open through the upper layer, pulsing softly (4 s)
      const C = st.cut, N = 10;
      for (let c = 0; c < N; c++) {
        const s = SEED[c * 11 + 3], x = lerp(C[0] + 40, C[1] - 40, (c + 0.5) / N) + 6 * s.g1, L = C[3] * 0.34;
        const pulse = still ? 0.75 : 0.5 + 0.35 * Math.sin(t * Math.PI / 2 + c * 0.9);
        put(x, C[2] + 2 + L / 2, rad(90 + 8 * s.g0), L, 1.6, pulse * st.chan4 * st.cutO, 0, s.ph);
      }
    }
    goldFx.geometry.instanceCount = gN; goldFx.visible = gN > 0; goldFx.geometry.attributes.iA.needsUpdate = goldFx.geometry.attributes.iB.needsUpdate = true;
    last.glints = gN; last.t = t; last.drop = dropB.visible ? dr : 0; last.cut = skin.visible && st.sec > 0.004 ? st.cutO : 0;
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
    pxU.value = pr * view.cover.w / 2400;   // device px per frame px: the strokes keep ≥ 1.5 device px
    EDGE.value.set((view.box.x - view.cover.x) * 2400 / view.cover.w, (view.box.y - view.cover.y) * 2400 / view.cover.w, pxU.value, canvas.height);
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
    syringeOn: syr.visible, swarm: last.swarm, dropR: r1(last.drop || 0), slabOn: r3(last.cut || 0), glints: last.glints, probe: probe() });
  return { draw, kit, dispose, state, animated: true };
}
