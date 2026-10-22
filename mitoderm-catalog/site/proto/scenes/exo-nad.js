// EXO-NAD live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D scene, as
// the approved sample EXOTECH GEL (scenes/exotech-gel.js) and the HAIR line's pages (exosignal-hair.js, exosignal-spray.js,
// whose light, print materials, strokes, edge fade, pace, state and dispose this module follows). The engine keeps the
// story geometry (the cover-fitted 16:10 frame, the run's box, the phone stage, the kit card); this module draws the pose
// for the story position into the box. Objects are placed by frame pixel (2400×1500), measured on the only packshot,
// protocols/print/img/exo-nad.webp (795×488): the brushed gold box seen square on (476 px), the square glass peel bottle
// with its gold cap and two phases, the amber pH Normalizer and teal Longevity Serum vials with silver crimp caps.
// The story (site/story3d.json; scratchpad spec pages/exo-nad/spec.md): S1 the closed box, champagne glow behind it,
// rare sparks far behind; S2 the box deeper, the sparks dull to grey dust that settles; S3 the three liquids come out
// from behind the box one by one and stand in a row, 1-2-3 right to left (peel, pH, serum); S3 → S4 a soft light rises
// behind them and a wave runs through the dust, which turns into an even champagne veil; the three go small, low right,
// in a backlight; S4 → S5 the veil sinks and draws into one gold line, the three step onto it, markers under them, a
// finish ring, a circle of the 3–4 week rhythm; S6–S7 the box comes forward and its sleeve lifts straight up 0.60 of
// its width (owner photos 26 and 32), the black tray shows the peel bottle and the rows of 5 + 5 vials (photo 29): the
// pose that flies into the offer card. Nothing else opens: no photo shows the caps off. The product keeps its print's
// colours (emissive ≈ 85 % + neutral shading, toneMapped off); the line's champagne (#d8c48a) and the brand gold live
// only around it (sparks, dust, veil, glows, strokes). No text is drawn but the package's own print
// (design/exo-nad/make_textures.py). No exosomes: the story shows none in the scene.
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

  // the camera all but level (the packshot shows neither the box's top nor its sides, the caps without an ellipse: 1°);
  // `lay` is the same camera without the box's view offset, for placing objects by their frame pixels
  const FOV = 20, EL = rad(1), DIST = 14;
  const camera = new THREE.PerspectiveCamera(FOV, 1.6, 1, 80);
  camera.position.set(0, Math.sin(EL) * DIST, Math.cos(EL) * DIST); camera.lookAt(0, 0, 0);
  const lay = camera.clone(); lay.updateMatrixWorld(); lay.updateProjectionMatrix();
  const fwd = new V3(); lay.getWorldDirection(fwd);
  const layInv = lay.quaternion.clone().invert();
  const ray = new V3(), TAN = Math.tan(rad(FOV / 2));
  function at(cx, cy, depth, out) {   // the point seen at frame pixel (cx, cy), `depth` in front of the camera
    ray.set(cx / 1200 - 1, 1 - cy / 750, 0.5).unproject(lay).sub(lay.position).normalize();
    return out.copy(lay.position).addScaledVector(ray, depth / ray.dot(fwd));
  }
  const world = (px, depth) => px / 1500 * 2 * depth * TAN;   // frame pixels → world units at that depth
  const toCam = new V3();
  const facing = o => { toCam.copy(lay.position).sub(o.position).applyQuaternion(layInv); return Math.atan2(toCam.x, toCam.z); };

  // ---- light: a neutral studio for reflections (PMREM), as the HAIR scenes': dark above and below, an even horizon, two
  // tall narrow softboxes either side of the camera, rims behind; the glass has its own room without the front softboxes
  // (a clear body over its liquid, bright at its edges). The key from the top left: the packshot's foil is lightest left
  // of its middle
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
    else panel(0.4, 0, 1, 12, 24, 12);   // the glass: a broad dim wall behind the camera instead
    panel(2.5, -9, 1.5, -7, 2.5, 9); panel(2, 9, 2, -7, 2.5, 9);     // rims from behind
    const rt = pm.fromScene(room, 0.02); pm.dispose();
    room.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    return rt;   // its target: disposing that frees the framebuffer too, not only the texture
  }
  let roomEnv = makeEnv(false), glassEnv = makeEnv(true);
  scene.environment = roomEnv.texture;
  const glassMats = [];   // the materials that see the glass room (rebuilt after a lost context)
  // after a lost context three.js restores image textures, not the rendered environments: rebuild them, and have the
  // engine redraw (the kit picture too), also under reduced motion
  const restored = () => {
    const old = [roomEnv, glassEnv]; roomEnv = makeEnv(false); glassEnv = makeEnv(true); scene.environment = roomEnv.texture;
    for (const m of glassMats) m.envMap = glassEnv.texture;
    old.forEach(t => t.dispose()); sizeW = -1;
    version++; if (onLoad) onLoad();
  };
  canvas.addEventListener('webglcontextrestored', restored);
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(-4, 7, 6); scene.add(key);

  // ---- textures: the typeset print and the material maps (make_textures.py)
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy(), NTEX = 8;
  const tex = (name, srgb) => {
    const t = new THREE.TextureLoader().load(new URL(`img/exo-nad-3d/${name}`, base).href, () => {
      t.needsUpdate = true; if (++loaded === NTEX) { version++; if (onLoad) onLoad(); }   // the engine redraws the kit picture
    });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const lidTex = tex('lid-face.png', true), lidMetal = tex('lid-metal.png'), brush = tex('foil-brush.jpg'), peelInk = tex('peel-print.png');
  const peelLiq = tex('peel-liquid.png', true), phInk = tex('vial-ph.png'), lsInk = tex('vial-ls.png'), trayInk = tex('tray-print.png');
  brush.wrapS = brush.wrapT = THREE.RepeatWrapping; brush.repeat.set(2, 3);
  const TEXS = [lidTex, lidMetal, brush, peelInk, peelLiq, phInk, lsInk, trayInk];

  // ---- materials. The product in its print's colours: emissive 0.85 of the colour plus a neutral shading (a diffuse
  // 0.2 of it under the key and the room), not tone mapped; the foil a satin metal. Nothing on the product is dimmed
  // or tinted: it comes and goes by opacity only
  const SHADE = 0.2;
  // the scene box's top edge: the canvas ends at frame y 285 on the page; anything that comes near it fades over
  // 292…340 (the frame y of a fragment: the canvas top's frame y + its buffer row / device px per frame px; set in fit())
  const EDGE = { value: new THREE.Vector3(0, 1, 1) }, EDGE_Y0 = 292, EDGE_Y1 = 340;
  const edgeFade = sh => {
    sh.uniforms.uEdge = EDGE;
    sh.fragmentShader = 'uniform vec3 uEdge;\n' + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      gl_FragColor.a *= smoothstep(${EDGE_Y0}.0, ${EDGE_Y1}.0, uEdge.x + (uEdge.y - gl_FragCoord.y) / uEdge.z);`);
  };
  const P = (hex, opts = {}, key = 'p') => {
    const m = new THREE.MeshPhysicalMaterial(Object.assign({ color: new THREE.Color(hex).multiplyScalar(SHADE), emissive: hex,
      emissiveIntensity: 0.85, roughness: 0.7, specularIntensity: 0.3, toneMapped: false, transparent: true }, opts));
    m.onBeforeCompile = edgeFade; m.customProgramCacheKey = () => 'exonad-' + key; return m;
  };
  // the foil: one colour for the sleeve's printed front (its texture) and every bare side; a satin metal (roughness
  // 0.30, lesson of V-TECH: never below 0.12) whose reflection adds a soft sheen, brushed finely along x
  const FOIL = 0xf2d28f;   // = make_textures.py FOIL: renders as the packshot's #e4c381
  const FOIL_OPTS = { metalness: 1, roughness: 0.3, specularIntensity: 1, envMapIntensity: 0.6 };
  // the studio's light across the foil, neutral (a factor on its colour, in linear light), fixed to the box so it is the
  // same in every pose: a broad soft highlight left of the middle, falling off to the right (the packshot's lemon to
  // bronze, at a third of its strength: there the right edge is 0.1–0.3 of the middle's luminance), the band under the
  // lid line in the sleeve's shadow (the packshot's band is darker: #a48957). The ΔE probe (u 0.5, v 0.30) sits at 1.07
  const foilLight = sh => {
    edgeFade(sh);
    sh.vertexShader = 'varying vec3 vBoxP;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vBoxP = position;');
    sh.fragmentShader = 'varying vec3 vBoxP;\n' + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float u = vBoxP.x + 0.5, v = 0.5 - vBoxP.y, du = (u - 0.36) / 0.38, dv = (v - 0.42) / 0.55;
        gl_FragColor.rgb *= (0.82 + 0.30 * exp(-(du * du + dv * dv))) * (v > 0.879 ? 0.86 : 1.0); }`);
  };
  const lidMat = P(0xffffff, Object.assign({}, FOIL_OPTS, { color: new THREE.Color(SHADE, SHADE, SHADE), map: lidTex, emissiveMap: lidTex,
    metalnessMap: lidMetal, roughnessMap: lidMetal, roughness: 1, bumpMap: brush, bumpScale: 0.6 }), 'lid');
  const foilMats = () => P(FOIL, FOIL_OPTS, 'foil');
  lidMat.onBeforeCompile = foilLight;
  const velvet = () => P(0x1c1d1b, { roughness: 0.9, specularIntensity: 0.1, sheen: 0.4, sheenRoughness: 0.6, sheenColor: 0x3a3a38 }, 'velvet');
  const trayGold = () => P(FOIL, Object.assign({}, FOIL_OPTS, { alphaMap: trayInk, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }), 'traygold');
  // glass (HAIR's): no transmission (on a transparent canvas it cannot see the page's smoke, and a phone pays a pass for
  // it); its opacity follows Fresnel and its own highlights, so its edges and highlights read and the body stays clear
  function glassMat(side, a0, aF, aS, color = 0x0b0b0c, lit = null) {
    const m = new THREE.MeshPhysicalMaterial({ color, roughness: 0.04, ior: 1.5, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.6,
      envMap: glassEnv.texture, transparent: true, depthWrite: false, side, toneMapped: false });
    const k = [a0, aF, aS].map(v => v.toFixed(3));
    m.onBeforeCompile = sh => {
      edgeFade(sh);
      sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float F = pow(1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0), 5.0);
        vec3 sp = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
        #ifdef USE_CLEARCOAT
        sp += (clearcoatSpecularDirect + clearcoatSpecularIndirect) * material.clearcoat;
        #endif
        gl_FragColor.a = clamp(${k[0]} + ${k[1]} * F + dot(sp, vec3(0.2126, 0.7152, 0.0722)) * ${k[2]}, 0.0, 1.0) * opacity; }`);
      if (lit) lit(sh);
    };
    m.customProgramCacheKey = () => 'exonad-glass' + k.join() + color + (lit ? 'lit' : ''); glassMats.push(m);
    return m;
  }
  // the vials' liquids: the packshot's front colour where the body faces the camera (within ±35° nothing changes: the
  // ΔE probe), toward the right limb the light behind it shines through (#f18535 / #41dee1), the left limb in shadow
  function liquidMat(hex, limb, shade) {
    const m = P(hex, { roughness: 0.5, specularIntensity: 0.2 }, 'liq' + hex);
    const L = new THREE.Color(limb), S = new THREE.Color(shade);
    m.onBeforeCompile = sh => {
      edgeFade(sh);
      sh.uniforms.uLimb = { value: new V3(L.r, L.g, L.b) }; sh.uniforms.uShade = { value: new V3(S.r, S.g, S.b) };
      sh.fragmentShader = 'uniform vec3 uLimb, uShade;\n' + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float nx = normal.x;
        gl_FragColor.rgb = mix(gl_FragColor.rgb, uLimb, 0.85 * smoothstep(0.55, 0.85, nx) * (1.0 - smoothstep(0.93, 1.0, nx)));
        gl_FragColor.rgb = mix(gl_FragColor.rgb, uShade, 0.8 * smoothstep(-0.55, -0.9, nx)); }`);
    };
    return m;
  }
  // the metal caps: the peel's polished gold (vertical stripes from the softboxes), the vials' aluminium; a little of
  // their colour as emission (never black where they mirror the dark). Their reflection is turned with the object as it
  // faces the camera (uFace, as the spray's cap), so a cap reads the same anywhere in the frame
  const faceU = () => ({ value: new THREE.Matrix3() });
  function metalMat(hex, rough, emi, U) {
    const m = new THREE.MeshPhysicalMaterial({ color: hex, metalness: 1, roughness: rough, emissive: hex, emissiveIntensity: emi,
      envMapIntensity: 1, toneMapped: false, transparent: true });
    m.onBeforeCompile = sh => {
      edgeFade(sh); sh.uniforms.uFace = U;
      sh.fragmentShader = 'uniform mat3 uFace;\n' + sh.fragmentShader.replace('#include <envmap_physical_pars_fragment>', THREE.ShaderChunk.envmap_physical_pars_fragment
        .replace('reflectVec = inverseTransformDirection( reflectVec, viewMatrix );', 'reflectVec = uFace * inverseTransformDirection( reflectVec, viewMatrix );'));
    };
    m.customProgramCacheKey = () => 'exonad-metal' + hex; return m;
  }
  const upL = new V3(0, 1, 0).applyQuaternion(lay.quaternion), m4 = new THREE.Matrix4();
  const ink = (map, hex = 0x070707) => P(hex, { alphaMap: map, depthWrite: false, roughness: 0.45, polygonOffset: true, polygonOffsetFactor: -2 }, 'ink');

  // one geometry out of several parts (each [geometry, matrix]): fewer draws for the box's flat faces
  const M = (x, y, z, rx = 0, ry = 0) => new THREE.Matrix4().compose(new V3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, 0)), new V3(1, 1, 1));
  function merge(parts) {
    const pos = [], nor = [], uv = [], nm = new THREE.Matrix3(), v = new V3();
    for (const [g0, m] of parts) {
      const g = g0.index ? g0.toNonIndexed() : g0; nm.getNormalMatrix(m);
      const A = g.attributes.position, N = g.attributes.normal, U = g.attributes.uv;
      for (let i = 0; i < A.count; i++) {
        v.fromBufferAttribute(A, i).applyMatrix4(m); pos.push(v.x, v.y, v.z);
        v.fromBufferAttribute(N, i).applyMatrix3(nm).normalize(); nor.push(v.x, v.y, v.z); uv.push(U.getX(i), U.getY(i));
      }
      if (g !== g0) g.dispose(); g0.dispose();
    }
    const out = new THREE.BufferGeometry();
    out.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); out.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    out.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); return out;
  }
  const plane = (w, h) => new THREE.PlaneGeometry(w, h);
  const mesh = (g, m, parent, order) => { const x = new THREE.Mesh(g, m); x.renderOrder = order; parent.add(x); return x; };

  // ---- the box, its front W × W (W = 1, scaled per pose; origin the front's centre, y up, the front at z 0): a sleeve
  // over the top 0.877 (the packshot's lid line) that lifts straight up, as in the owner's photos 26 and 32; under it
  // the base: its front band (v 0.881…1), gold side walls up to the top, the black tray 0.05 deeper with the peel bottle
  // and the rows of five vials (photo 29: left the peel, centres u 0.125; the rows at u 0.317 + 0.139 k, their feet at
  // v 0.470 and 0.740); depth 0.28 W (unknown: an assumption, spec §5). The sleeve's face stands 0.006 before the base's;
  // between its foot (v 0.877) and the band (0.881) the dark of the tray shows: the lid line
  const BD = 0.28, LIDV = 0.877, BANDV = 0.881, WALL = 0.02, WX = 0.494, REC = 0.05;
  const box = new THREE.Group(), sleeve = new THREE.Group(), trayG = new THREE.Group(); box.add(sleeve); box.add(trayG); scene.add(box);
  const yv = v => 0.5 - v;   // the front's v (0 top … 1 foot) → local y
  const foilBox = foilMats(), foilSleeve = foilMats(), velvetMat = velvet(), trayGoldMat = trayGold();
  foilBox.onBeforeCompile = foilSleeve.onBeforeCompile = foilLight;   // (their geometry is in the box's own units: u, v)
  mesh(plane(1, LIDV).translate(0, yv(LIDV / 2), 0.006), lidMat, sleeve, 101);
  // the lid line: the dark under the sleeve's lip between its foot (v 0.877) and the band (0.881); it goes as the sleeve lifts
  const lidLine = P(0x161617, { roughness: 0.9, specularIntensity: 0.1 }, 'lidline');
  const lidGap = mesh(plane(1, BANDV - LIDV).translate(0, yv((LIDV + BANDV) / 2), 0.003), lidLine, box, 101);
  mesh(merge([[plane(1, BD + 0.006), M(0, 0.5, (0.006 - BD) / 2, -Math.PI / 2)],                       // top
    [plane(BD + 0.006, LIDV), M(-0.5, yv(LIDV / 2), (0.006 - BD) / 2, 0, -Math.PI / 2)],                 // sides
    [plane(BD + 0.006, LIDV), M(0.5, yv(LIDV / 2), (0.006 - BD) / 2, 0, Math.PI / 2)],
    [plane(1, LIDV), M(0, yv(LIDV / 2), -BD, 0, Math.PI)],                                               // back
    [plane(1, 0.006), M(0, yv(LIDV), 0.003, Math.PI / 2)]]), foilSleeve, sleeve, 100);                   // the lip
  const bandH = 1 - BANDV, wallH = BANDV;
  mesh(merge([[plane(1, bandH), M(0, yv(BANDV + bandH / 2), 0)],                                          // the band
    [plane(BD, bandH), M(-0.5, yv(BANDV + bandH / 2), -BD / 2, 0, -Math.PI / 2)], [plane(BD, bandH), M(0.5, yv(BANDV + bandH / 2), -BD / 2, 0, Math.PI / 2)],
    [plane(2 * (WX - WALL), REC), M(0, yv(BANDV), -REC / 2, -Math.PI / 2)],                              // the band's top edge
    [plane(WALL, wallH), M(-WX + WALL / 2, yv(wallH / 2), 0)], [plane(WALL, wallH), M(WX - WALL / 2, yv(wallH / 2), 0)],   // walls: front edges
    [plane(BD, wallH), M(-WX, yv(wallH / 2), -BD / 2, 0, -Math.PI / 2)], [plane(BD, wallH), M(WX, yv(wallH / 2), -BD / 2, 0, Math.PI / 2)],   // outsides
    [plane(REC, wallH), M(-WX + WALL, yv(wallH / 2), -REC / 2, 0, Math.PI / 2)], [plane(REC, wallH), M(WX - WALL, yv(wallH / 2), -REC / 2, 0, -Math.PI / 2)]]),   // insides
    foilBox, box, 100);
  // the tray and its print belong to the contents (trayG): shown only once the sleeve lifts, never through a fading sleeve
  const tray = mesh(plane(2 * (WX - WALL), wallH), velvetMat, trayG, 102); tray.position.set(0, yv(wallH / 2), -REC);
  const trayPrint = mesh(plane(0.40, 0.10), trayGoldMat, trayG, 103); trayPrint.position.set(0, yv(0.82), -REC + 0.0005);
  const boxMats = [lidMat, foilSleeve, foilBox, velvetMat, trayGoldMat, lidLine];

  // ---- the peel bottle, height H_b = 1 (scaled per pose; origin its foot's centre): measured on the packshot (94 × 211
  // px): the square body W_b 0.4455 × 0.611, its corners rounded 0.05 W_b, 0.66 W_b deep (at least the cap's diameter);
  // the dark top glass 0.578…0.611, the liquid 0.123…0.578 (0.755 W_b wide, its two phases and gold in peel-liquid.png),
  // the thick glass foot and walls; the dark neck ring 0.630…0.678 (0.47 W_b), the polished gold cap 0.682…1 (0.638 W_b,
  // its top edge rounded 0.024); the label on the front, the lid's lockup ×0.255 (peel-print.png)
  const WB = 0.4455, DB = 0.66 * WB, RB = 0.05 * WB, LIQ0 = 0.123, LIQ1 = 0.578, LW = 0.755 * WB, LD = DB - 0.2 * WB;
  const bodyGeo = (() => {   // the outline inset by RB (corners 0.004), extruded along y; the bevel (RB out, RB high) gives
    // the full outline with its corners rounded RB, the foot and the shoulder rounded too
    const s = new THREE.Shape(), rc = 0.004, w = WB / 2 - RB - rc, d = DB / 2 - RB - rc;
    s.moveTo(-w, -d - rc); s.lineTo(w, -d - rc); s.absarc(w, -d, rc, -Math.PI / 2, 0); s.lineTo(w + rc, d); s.absarc(w, d, rc, 0, Math.PI / 2);
    s.lineTo(-w, d + rc); s.absarc(-w, d, rc, Math.PI / 2, Math.PI); s.lineTo(-w - rc, -d); s.absarc(-w, -d, rc, Math.PI, Math.PI * 1.5);
    const g = new THREE.ExtrudeGeometry(s, { depth: 0.611 - 2 * RB, bevelEnabled: true, bevelThickness: RB, bevelSize: RB, bevelSegments: 6, curveSegments: 4 });
    g.rotateX(-Math.PI / 2).translate(0, RB, 0); g.computeVertexNormals(); return g;
  })();
  const liquidGeo = new THREE.BoxGeometry(LW, LIQ1 - LIQ0, LD).translate(0, (LIQ0 + LIQ1) / 2, 0);
  const slabGeo = merge([[new THREE.BoxGeometry(WB - 0.03 * WB, LIQ0 - 0.012, DB - 0.03 * WB), M(0, (LIQ0 + 0.012) / 2, 0)],   // the thick foot
    [new THREE.BoxGeometry((WB - LW) / 2 - 0.02 * WB, LIQ1 - LIQ0, DB - 0.03 * WB), M(-(LW + (WB - LW) / 2) / 2, (LIQ0 + LIQ1) / 2, 0)],   // the walls
    [new THREE.BoxGeometry((WB - LW) / 2 - 0.02 * WB, LIQ1 - LIQ0, DB - 0.03 * WB), M((LW + (WB - LW) / 2) / 2, (LIQ0 + LIQ1) / 2, 0)]]);
  const topGeo = new THREE.BoxGeometry(WB - 0.03 * WB, 0.611 - LIQ1 - 0.006, DB - 0.03 * WB).translate(0, (LIQ1 + 0.605) / 2, 0);
  // the thick foot and walls carry the liquid's light (it runs through the glass by total internal reflection): a cream
  // (the liquid's #e5d9ba) rising toward the liquid, the foot's bottom edge lit too; dark glass away from it, so on the
  // black page the bottle reads as clear glass round a lit liquid, and the label's E (half on the wall, as photographed)
  // keeps its contrast
  const f3 = v => v.toFixed(4);
  const slabLit = sh => {
    sh.vertexShader = 'varying vec3 vSlab;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vSlab = position;');
    sh.fragmentShader = 'varying vec3 vSlab;\n' + sh.fragmentShader.replace(/(gl_FragColor\.a = clamp\([^\n]*\n)/, `$1
      { float tw = 1.0 - smoothstep(${f3(LW / 2)}, ${f3(WB / 2)}, abs(vSlab.x));
        float t = vSlab.y < ${f3(LIQ0 - 0.002)} ? smoothstep(0.0, ${f3(LIQ0)}, vSlab.y) * (0.55 + 0.45 * tw) + 0.35 * (1.0 - smoothstep(0.0, 0.03, vSlab.y)) : tw;
        gl_FragColor.rgb += vec3(0.784, 0.694, 0.491) * (0.10 + 0.50 * t);   // added to the glass's own highlights
        gl_FragColor.a = max(gl_FragColor.a, (0.16 + 0.52 * t) * opacity); }`);
  };
  const neckGeo = new THREE.CylinderGeometry(0.235 * WB, 0.235 * WB, 0.048, 64).translate(0, 0.654, 0);
  const RCAP = 0.319 * WB, RTOP = 0.024;
  const capGeo = new THREE.LatheGeometry([new THREE.Vector2(0, 0.682), new THREE.Vector2(RCAP - 0.004, 0.682), new THREE.Vector2(RCAP, 0.686)]
    .concat(Array.from({ length: 9 }, (_, i) => { const a = i / 8 * Math.PI / 2; return new THREE.Vector2(RCAP - RTOP + RTOP * Math.cos(a), 1 - RTOP + RTOP * Math.sin(a)); }))
    .concat([new THREE.Vector2(0, 1)]), 96);
  const PP = [-0.45 * WB, 0.45 * WB, 1 - 0.70, 1 - 0.585];   // the label plane: x, y (from the foot); = make_textures PEEL_PLANE
  const labelGeo = new THREE.PlaneGeometry(PP[1] - PP[0], PP[3] - PP[2]).translate(0, (PP[2] + PP[3]) / 2, DB / 2 + 0.0008);
  // the gold flakes: discs 0.010…0.034 W_b (most small) in a thin layer just before the liquid's front, in a cloud down
  // the middle as photographed (the packshot's gold is densest a little left of the axis, through the middle of the
  // column: there they are larger); the hero's settle 0.02 of the column a second and come back at the top (shrinking
  // in and out), never outside the liquid, never under 1.5 device px; the tray's copy holds them as they are at t = 0
  const NF = 760, FL = new Float32Array(NF * 6);
  const rng = (s => () => { s |= 0; s = s + 0x6d2b79f5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; })(20261022);
  const gauss = () => Math.sqrt(-2 * Math.log(Math.max(1e-6, rng()))) * Math.cos(2 * Math.PI * rng());
  for (let i = 0; i < NF; i++) {
    FL[i * 6] = clamp(0.47 + 0.17 * gauss(), 0.04, 0.96); FL[i * 6 + 1] = rng(); FL[i * 6 + 2] = rng();   // x (of the width), phase, depth
    const r = rng(); FL[i * 6 + 3] = (0.010 + 0.024 * r * r) * WB; FL[i * 6 + 4] = rng() * Math.PI; FL[i * 6 + 5] = rng() * Math.PI;   // size, tilts
  }
  const flakeGeo = new THREE.CircleGeometry(0.5, 6);
  const fq = new THREE.Quaternion(), fe = new THREE.Euler(), fp = new V3(), fs = new V3();
  const FALL = 0.02;   // of the column per second
  let flakeMin = 0;    // the smallest disc drawn (bottle units): 1.5 device px at the hero's size (set per frame)
  function flakeAt(i, t, out, min = 0) {   // a flake's place (in the bottle) and size; its column fraction h (0 top … 1 foot)
    const h = (FL[i * 6 + 1] + t * FALL) % 1, x = (FL[i * 6] - 0.5) * (LW - 0.02 * WB), y = LIQ1 - 0.006 - h * (LIQ1 - LIQ0 - 0.012);
    const z = LD / 2 + 0.002 + FL[i * 6 + 2] * 0.008, k = smooth(0, 0.04, h) * (1 - smooth(0.94, 1, h));
    // larger in the cloud, smaller toward the foot (the packshot's gold by tenths of the column, top → foot:
    // 16 36 26 12 8 15 18 25 3 0 %)
    const dh = (h - 0.6) / 0.25, dx = (FL[i * 6] - 0.47) / 0.25, c = (0.55 + 0.5 * Math.exp(-dh * dh - dx * dx)) * (1 - 0.8 * smooth(0.8, 0.9, h));
    out.set(x, y, z); return Math.max(FL[i * 6 + 3] * c, min) * k;
  }
  function setFlakes(im, t, min = 0) {
    for (let i = 0; i < NF; i++) {
      const s = flakeAt(i, t, fp, min); fs.setScalar(Math.max(s, 1e-5));
      fe.set(FL[i * 6 + 4] - Math.PI / 2, FL[i * 6 + 5], 0); fq.setFromEuler(fe); m4.compose(fp, fq, fs); im.setMatrixAt(i, m4);
    }
    im.instanceMatrix.needsUpdate = true;
  }
  function peelMats(capU) {
    return { back: glassMat(THREE.BackSide, 0.02, 0.3, 0.7), front: glassMat(THREE.FrontSide, 0.04, 0.55, 1.0),
      slab: glassMat(THREE.FrontSide, 0.07, 0.6, 1.2, 0xa4a8ac, slabLit), top: glassMat(THREE.FrontSide, 0.72, 0.3, 0.6, 0x3b3b3c),
      liquid: P(0xffffff, { color: new THREE.Color(SHADE, SHADE, SHADE), map: peelLiq, emissiveMap: peelLiq, roughness: 0.45, specularIntensity: 0.25 }, 'peelliq'),
      flakes: P(0xd1b55d, { metalness: 0.7, roughness: 0.3, specularIntensity: 1, side: THREE.DoubleSide }, 'flake'),
      neck: P(0x0c0c0d, { roughness: 0.2, specularIntensity: 1, envMapIntensity: 1.2 }, 'neck'),
      cap: metalMat(0xe0b768, 0.14, 0.1, capU), ink: ink(peelInk), U: capU };
  }
  function makePeel(parent, mats, base) {   // drawn in this order: the back of the glass, the solid inside, the front, the label
    const g = new THREE.Group(); parent.add(g);
    const parts = [[bodyGeo, mats.back], [slabGeo, mats.slab], [topGeo, mats.top], [liquidGeo, mats.liquid], [neckGeo, mats.neck], [capGeo, mats.cap],
      [bodyGeo, mats.front], [labelGeo, mats.ink]].map(([geo, mat], j) => mesh(geo, mat, g, base + j));
    const fl = new THREE.InstancedMesh(flakeGeo, mats.flakes, NF); fl.renderOrder = base + 3.5; fl.frustumCulled = false; g.add(fl); setFlakes(fl, 0);
    return { g, mats, parts: parts.concat([fl]), flakes: fl };
  }

  // ---- the 5 ml vial, height H_v = 1 (origin its foot's centre): a lathe of the packshot's profile (65 × 138 px): the
  // crimp cap 0.855…1 (0.89 W_v, its top rounded), the dark neck and stopper 0.76…0.848 (0.65 W_v), the shoulder from
  // 0.68 W_v at 0.754 rounding out to the body at 0.652, the body (R 0.2355) to 0.094, the rounded foot (0.78 W_v); the
  // liquid fills it from the shoulder; the print a band ±75° round the front, mapped flat as the packshot prints it
  const R = 0.2355, V2 = (r, y) => new THREE.Vector2(r, y);
  const arc = (cx, cy, r, a0, a1, n) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return V2(cx + r * Math.cos(a), cy + r * Math.sin(a)); });
  const shoulder = new THREE.SplineCurve([V2(R, 0.652), V2(R - 0.004, 0.69), V2(R - 0.03, 0.725), V2(0.19, 0.745), V2(0.16, 0.754), V2(0.153, 0.762)]).getPoints(24);
  const vialGlass = new THREE.LatheGeometry([V2(0, 0), V2(0.1837, 0)].concat(arc(R - 0.052, 0.052, 0.052, -Math.PI / 2 + 0.25, 0, 8), shoulder, [V2(0.153, 0.86), V2(0, 0.86)]), 72);
  const vialLiquid = new THREE.LatheGeometry([V2(0, 0.032), V2(0.17, 0.032)].concat(arc(0.94 * R - 0.04, 0.072, 0.04, -Math.PI / 2, 0, 6),
    shoulder.filter(p => p.y < 0.75).map(p => V2(p.x * 0.94, p.y)), [V2(0, 0.748)]), 72);
  const vialNeck = new THREE.CylinderGeometry(0.148, 0.148, 0.1, 48).translate(0, 0.805, 0);
  const RV = 0.2096, RT = 0.022;
  const vialCap = new THREE.LatheGeometry([V2(0, 0.852), V2(RV - 0.003, 0.852), V2(RV, 0.856)].concat(arc(RV - RT, 1 - RT, RT, 0, Math.PI / 2, 8), [V2(0, 1)]), 72);
  const vialPrint = (() => {   // ±75°, h 0.28…0.70; u = x / 2R + 0.5 (flat, as seen from the front)
    const g = new THREE.CylinderGeometry(R * 1.002, R * 1.002, 0.42, 120, 1, true, rad(-75), rad(150)).translate(0, 0.49, 0);
    const p = g.attributes.position, uv = g.attributes.uv;
    for (let i = 0; i < p.count; i++) uv.setX(i, 0.5 + p.getX(i) / (2 * R * 1.002));
    return g;
  })();
  function vialMats(kind, alU) {
    return { back: glassMat(THREE.BackSide, 0.02, 0.3, 0.7), front: glassMat(THREE.FrontSide, 0.04, 0.55, 1.0),
      // the packshot's #b16b2c and #277e95, as the scene renders them (its light and glass take a little: calibrated on the keys)
      liquid: kind === 'ph' ? liquidMat(0xbd6f28, 0xf18535, 0x7c4d27) : liquidMat(0x23859f, 0x41dee1, 0x365b6f),
      neck: P(0x1d1f1f, { roughness: 0.3, specularIntensity: 0.8 }, 'vneck'), cap: metalMat(0xd9d7d3, 0.25, 0.12, alU),
      ink: ink(kind === 'ph' ? phInk : lsInk, 0x0a0908), U: alU };
  }
  function makeVial(parent, mats, base) {
    const g = new THREE.Group(); parent.add(g);
    const parts = [[vialGlass, mats.back], [vialLiquid, mats.liquid], [vialNeck, mats.neck], [vialCap, mats.cap], [vialGlass, mats.front], [vialPrint, mats.ink]]
      .map(([geo, mat], j) => mesh(geo, mat, g, base + j));
    return { g, mats, parts };
  }

  // ---- the three heroes (S3–S5) and the tray's contents (S6–S7: in the box, seen as the sleeve lifts)
  const heroes = [makePeel(scene, peelMats(faceU()), 0), makeVial(scene, vialMats('ph', faceU()), 0), makeVial(scene, vialMats('ls', faceU()), 0)];
  const H_W = [WB, 2 * R, 2 * R];   // width of each hero per unit height
  const trayU = faceU(), trayPeel = makePeel(trayG, peelMats(trayU), 104);
  trayPeel.g.position.set(0.125 - 0.5, yv(0.732), -0.07); trayPeel.g.scale.setScalar(0.41);
  // the rows of five: one instanced draw per part (the glass, neck and cap of all ten; each kind's liquid and print)
  const ROWS = [0.317, 0.456, 0.595, 0.734, 0.873], VH = 0.265;
  const tvm = vialMats('ph', trayU), tvLs = { liquid: liquidMat(0x23859f, 0x41dee1, 0x365b6f), ink: ink(lsInk, 0x0a0908) };
  const trayMats = Object.values(trayPeel.mats).filter(m => m.isMaterial).concat(Object.values(tvm).filter(m => m.isMaterial), [tvLs.liquid, tvLs.ink]);
  const inst = (geo, mat, rows, order) => {
    const m = new THREE.InstancedMesh(geo, mat, rows.length * 5); m.renderOrder = order; m.frustumCulled = false; trayG.add(m); let i = 0;
    for (const r of rows) for (const u of ROWS) m.setMatrixAt(i++, m4.compose(tmpP.set(u - 0.5, yv(r ? 0.740 : 0.470), -0.07), tmpQ, tmpS.setScalar(VH)));
    return m;
  };
  const tmpP = new V3(), tmpQ = new THREE.Quaternion(), tmpS = new V3();
  [[vialGlass, tvm.back, [0, 1]], [vialLiquid, tvm.liquid, [0]], [vialLiquid, tvLs.liquid, [1]], [vialNeck, tvm.neck, [0, 1]], [vialCap, tvm.cap, [0, 1]],
    [vialGlass, tvm.front, [0, 1]], [vialPrint, tvm.ink, [0]], [vialPrint, tvLs.ink, [1]]].forEach(([g, m, rows], j) => inst(g, m, rows, 112 + j));

  // ---- the line's graphics, flat to the camera in frame pixels (a plane at a depth; local x = px − 1200, y = 750 − py),
  // always behind the products and drawn before them; the spray's strokes (a soft edge, ≥ 1.5 device px) and glows
  const pxU = { value: 1 };   // device px per frame px
  // the glows add their colour (× their alpha) and keep a true alpha (it adds too): a picture read back (the keys, the
  // phone stills, the kit picture) un-premultiplies to the glow's own champagne, not to lemon
  const ADD = { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.SrcAlphaFactor, blendDst: THREE.OneFactor,
    blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor };
  const place = (g, D) => { at(1200, 750, D, g.position); g.quaternion.copy(lay.quaternion); g.scale.setScalar(world(1, D)); };
  const fx = new THREE.Group(); scene.add(fx); place(fx, DIST + 8);
  const hex3 = h => new V3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  // each glow is a quad over its own extent only (uB: x0, y0, x1, y1 in frame px; nothing has alpha outside it), so a
  // glow shades only the pixels it lights
  const QUAD_V = `uniform vec4 uB; varying vec2 vP;
    void main() { vP = mix(uB.xy, uB.zw, position.xy * 0.5 + 0.5); gl_Position = projectionMatrix * modelViewMatrix * vec4(vP.x - 1200.0, 750.0 - vP.y, 0.0, 1.0); }`;
  const flat = (frag, uniforms, order, vert = QUAD_V, geo = new THREE.PlaneGeometry(2, 2)) => {   // a shader in frame px (vP)
    const m = new THREE.Mesh(geo, new THREE.ShaderMaterial(Object.assign({ vertexShader: vert, fragmentShader: frag,
      uniforms: Object.assign({ uB: { value: new THREE.Vector4() } }, uniforms), transparent: true, depthWrite: false, side: THREE.DoubleSide }, ADD)));
    m.renderOrder = order; m.visible = false; m.frustumCulled = false; fx.add(m); return m;
  };
  // the box's halo: champagne round the box's outline (a rounded rectangle), nothing beyond `ext` px from it (alpha
  // < 8/255 past 0.08 W on S1; 0.035 W on the kit pose, so the card's picture, cut to what has alpha, keeps its size)
  const halo = flat(`uniform vec4 uR; uniform float uExt, uA; uniform vec3 uC; varying vec2 vP;
    void main() { vec2 q = abs(vP - uR.xy) - uR.zw; float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0);
      float a = d < 0.0 ? 1.0 : exp(-3.5 * d / uExt) * (1.0 - smoothstep(0.6 * uExt, uExt, d));
      gl_FragColor = vec4(uC, uA * a); }`, { uR: { value: new THREE.Vector4() }, uExt: { value: 40 }, uA: { value: 0 }, uC: { value: hex3(0xd8c48a) } }, 3);
  // soft spots: the light behind the three on S3 → S4, the current step's on S5 and S4's backlight; the veil's even glow
  const SPOT_F = `uniform vec4 uS; uniform float uA; uniform vec3 uC; varying vec2 vP;
    void main() { vec2 q = (vP - uS.xy) / uS.zw; float r2 = dot(q, q); gl_FragColor = vec4(uC, uA * exp(-3.0 * r2) * (1.0 - smoothstep(0.5, 1.0, r2))); }`;
  const spot = (c, order) => flat(SPOT_F, { uS: { value: new THREE.Vector4() }, uA: { value: 0 }, uC: { value: hex3(c) } }, order);
  const setSpot = (m, cx, cy, rx, ry, a) => {
    const u = m.material.uniforms; u.uS.value.set(cx, cy, rx, ry); u.uB.value.set(cx - rx, cy - ry, cx + rx, cy + ry); u.uA.value = a; m.visible = a > 0.004;
  };
  const vSpots = [0, 1, 2].map(() => spot(0xd8c48a, 2)), backGlow = spot(0xd8c48a, 2), veilGlow = spot(0xd8c48a, 1);
  // the wave's front: a thin light ring from the row's middle (590, 900), inside the far layer's ellipse; drawn as an
  // annulus ±32 px round its radius (its light is nothing past ±25 px)
  const C0 = [690, 750], AX = [470, 420], WC = [590, 900], RING_N = 160;
  const ringGeo = (() => {
    const g = new THREE.BufferGeometry(), pos = [], ang = [], sd = [], idx = [];
    for (let i = 0; i <= RING_N; i++) for (const s of [-1, 1]) { pos.push(0, 0, 0); ang.push(i / RING_N * 2 * Math.PI); sd.push(s); }
    for (let i = 0; i < RING_N; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    g.setIndex(idx); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('aAng', new THREE.Float32BufferAttribute(ang, 1)); g.setAttribute('aSide', new THREE.Float32BufferAttribute(sd, 1)); return g;
  })();
  const ring = flat(`uniform float uR, uA; varying vec2 vP;
    void main() { float d = length(vP - vec2(${WC[0]}.0, ${WC[1]}.0)), e = length((vP - vec2(${C0[0]}.0, ${C0[1]}.0)) / vec2(${AX[0]}.0, ${AX[1]}.0));
      gl_FragColor = vec4(0.95, 0.91, 0.78, uA * exp(-(d - uR) * (d - uR) / 50.0) * (1.0 - smoothstep(0.6, 1.0, e))); }`, { uR: { value: 0 }, uA: { value: 0 } }, 4,
    `attribute float aAng, aSide; uniform float uR; varying vec2 vP;
    void main() { vP = vec2(${WC[0]}.0, ${WC[1]}.0) + max(0.0, uR + 32.0 * aSide) / cos(${(Math.PI / RING_N).toFixed(6)}) * vec2(cos(aAng), sin(aAng));
      gl_Position = projectionMatrix * modelViewMatrix * vec4(vP.x - 1200.0, 750.0 - vP.y, 0.0, 1.0); }`, ringGeo);

  // the far layer: one instanced quad per particle, all motion in the vertex shader (the spray's mist): sparks (S1) →
  // matte grey-beige dust settling (S2–S3) → past the wave's front an even champagne veil (S4) → drawn down into the
  // protocol's line (S4 → S5). Inside the ellipse (690, 750) 470 × 420 (fading from 0.6 of it out), so it thins before
  // the frame's edges and stays out of the copy (x > 1128); at least 1.5 device px; live only (the keys, the phone
  // stills and the kit picture are cut to what has alpha); a phone draws half
  const NPT = 900, PS = new Float32Array(NPT * 4), PG = new Float32Array(NPT * 2), PZ = new Float32Array(NPT);
  for (let i = 0; i < NPT; i++) { for (let j = 0; j < 4; j++) PS[i * 4 + j] = rng(); PG[i * 2] = rng() * 6.283; PG[i * 2 + 1] = rng() * 6.283; PZ[i] = rng(); }
  const pg = new THREE.InstancedBufferGeometry();
  pg.setIndex([0, 1, 2, 0, 2, 3]); pg.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3)); pg.instanceCount = NPT;
  pg.setAttribute('aS', new THREE.InstancedBufferAttribute(PS, 4)); pg.setAttribute('aG', new THREE.InstancedBufferAttribute(PG, 2)); pg.setAttribute('aZ', new THREE.InstancedBufferAttribute(PZ, 1));
  const PU = { uTime: { value: 0 }, uPx: pxU, uDust: { value: 0 }, uFade: { value: 0 }, uWave: { value: 0 }, uLine: { value: 0 }, uAlpha: { value: 1 } };
  const v2 = a => `vec2(${a[0].toFixed(1)}, ${a[1].toFixed(1)})`;
  const PART_V = `attribute vec4 aS; attribute vec2 aG; attribute float aZ;
    uniform float uTime, uPx, uDust, uFade, uWave, uLine, uAlpha;
    varying vec2 vQ; varying float vA, vSoft; varying vec3 vC;
    void main() {
      float ang = aS.x * 6.28318, rr = sqrt(aS.y);
      vec2 P0 = ${v2(C0)} + ${v2(AX)} * rr * vec2(cos(ang), sin(ang));
      vec2 wob = vec2(sin(uTime * 0.21 + aG.x), cos(uTime * 0.17 + aG.y));
      vec2 ps = P0 + 6.0 * wob;                                                  // sparks drift
      float fall = fract(aS.z + uTime * (0.004 + 0.006 * aS.w));                 // dust settles, the frame's height in 2–4 min
      vec2 pd = vec2(P0.x + 3.0 * wob.x, ${C0[1] - AX[1]}.0 + fall * ${2 * AX[1]}.0);
      float dw = smoothstep(0.0, 0.06, fall) * (1.0 - smoothstep(0.92, 1.0, fall));
      vec2 p = mix(ps, pd, uDust);
      float dv = length(P0 - ${v2(WC)}), kv = 1.0 - smoothstep(uWave - 60.0, uWave, dv);   // past the wave: the veil
      vec2 pv = P0 + 9.0 * wob;
      p = mix(p, pv, kv);
      float k = smoothstep(0.0, 1.0, clamp(uLine * 1.3 - aS.z * 0.3, 0.0, 1.0));            // drawn into the line
      p = mix(p, vec2(mix(330.0, 1090.0, aS.y), 640.0 + 2.0 * wob.y), k);
      float vis = aS.w < 0.25 ? 1.0 : smoothstep(0.3 + 0.3 * aS.z, 0.6 + 0.3 * aS.z, uFade);   // S1: a quarter, rare sparks
      float spark = vis * (0.55 + 0.45 * sin(uTime * 1.1 + aG.x * 3.0)), dust = vis * dw;
      float veil = 0.24 * (0.7 + 0.3 * sin(P0.x * 0.006 + P0.y * 0.004 - uTime * 0.35));   // a slow shimmer runs across it
      float a = mix(mix(0.8 * spark, 0.5 * dust, uDust), veil, kv);
      a += 0.5 * exp(-(dv - uWave) * (dv - uWave) / 400.0) * step(1.0, uWave) * (1.0 - step(899.0, uWave));   // the front
      float e = length((p - ${v2(C0)}) / ${v2(AX)});
      vA = a * (1.0 - smoothstep(0.6, 1.0, e)) * uAlpha;
      vC = mix(mix(vec3(0.847, 0.769, 0.541), vec3(0.478, 0.455, 0.416), uDust), vec3(0.88, 0.80, 0.58), kv);
      float dev = mix(mix(1.5 + 1.5 * aZ, 2.0 + 2.0 * aZ, uDust), (6.0 + 10.0 * aZ) * uPx, kv);   // device px across
      float r = max(dev, 1.5) * 0.5 / uPx; vSoft = kv; vQ = position.xy;
      vec2 q = p + position.xy * r;
      gl_Position = vA > 0.002 ? projectionMatrix * modelViewMatrix * vec4(q.x - 1200.0, 750.0 - q.y, 0.0, 1.0) : vec4(2.0, 2.0, 2.0, 1.0);
    }`;
  const PART_F = `varying vec2 vQ; varying float vA, vSoft; varying vec3 vC;
    void main() { float r = length(vQ); if (r > 1.0) discard;
      gl_FragColor = vec4(vC, vA * mix(1.0 - smoothstep(0.55, 1.0, r), exp(-3.0 * r * r), vSoft)); }`;
  const partMat = new THREE.ShaderMaterial(Object.assign({ vertexShader: PART_V, fragmentShader: PART_F, uniforms: PU, transparent: true, depthWrite: false, side: THREE.DoubleSide }, ADD));
  const parts = new THREE.Mesh(pg, partMat); parts.frustumCulled = false; parts.renderOrder = 5; parts.visible = false; fx.add(parts);

  // the protocol (S5): the steps' line (core 1.2 px, a soft glow ±4.5 px, drawn right to left from step 1), the markers
  // under the three (dots, r 6) and the finish (an empty ring, r 11) lighting in turn, the circle of the rhythm (every
  // 3–4 weeks: drawn clockwise from its top, closing at p = 4); brand gold #d8bd7e → #c9a24b. All of S5 stays above
  // frame y 700: the page's step cards come up over the scene's lower part while S5 is read
  const STROKE_V = `attribute float aSide, aHalf, aCore, aT, aU;
    varying float vSide, vHalf, vCore, vT, vU;
    void main() { vSide = aSide; vHalf = aHalf; vCore = aCore; vT = aT; vU = aU; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
  const STROKE_F = `uniform vec3 uA, uB; uniform float uOpacity, uDraw, uPx, uGlow, uGlowA;
    varying float vSide, vHalf, vCore, vT, vU;
    void main() {
      float d = abs(vSide) * vHalf, c = max(vCore * uPx, 0.75);
      float a = clamp(c + 0.5 - d * uPx, 0.0, 1.0);
      if (uGlow > 0.0) a = max(a, uGlowA * exp(-(d * d) / (uGlow * uGlow)));
      a *= clamp((uDraw - vT) * 60.0, 0.0, 1.0) * uOpacity;
      gl_FragColor = vec4(mix(uA, uB, vU), a);
    }`;
  const strokeMat = (a, b, o = {}) => new THREE.ShaderMaterial(Object.assign({ vertexShader: STROKE_V, fragmentShader: STROKE_F, transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { uA: { value: hex3(a) }, uB: { value: hex3(b) }, uOpacity: { value: 0 }, uDraw: { value: 1 }, uPx: pxU, uGlow: { value: o.glow || 0 }, uGlowA: { value: o.glowA || 0 } } }, ADD));
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
  const LY = 640, LX0 = 330, LX1 = 1090, CIRC = [760, 480, 160], FIN = [380, 11];
  const circlePts = (cx, cy, r, n) => Array.from({ length: n + 1 }, (_, i) => { const a = i / n * 2 * Math.PI; return [cx + r * Math.sin(a), cy - r * Math.cos(a)]; });
  const lineM = new THREE.Mesh(strokes([{ pts: Array.from({ length: 91 }, (_, i) => [LX1 - (LX1 - LX0) * i / 90, LY]), core: () => 1.2, ext: 16, t: u => u }]),
    strokeMat(0xe0c98c, 0xd8bd7e, { glow: 4.5, glowA: 0.35 }));
  const MARK_X = [960, 760, 560], MARK_Y = LY + 14;   // under step 1, 2, 3, just below their feet (whole); then the finish ring
  const markM = new THREE.Mesh(strokes(MARK_X.map((x, i) => ({ pts: circlePts(x, MARK_Y, 3, 24), core: () => 3, ext: 7, t: () => i / 4 }))
    .concat([{ pts: circlePts(FIN[0], LY, FIN[1], 72), core: () => 1.2, ext: 7, t: () => 0.75 }])), strokeMat(0xd8bd7e, 0xd8bd7e, { glow: 3, glowA: 0.3 }));
  const circM = new THREE.Mesh(strokes([{ pts: circlePts(CIRC[0], CIRC[1], CIRC[2], 180), core: () => 1.0, ext: 12, t: u => u }]), strokeMat(0xd8bd7e, 0xc9a24b, { glow: 4, glowA: 0.25 }));
  for (const [m, o] of [[circM, 6], [lineM, 7], [markM, 8]]) { m.renderOrder = o; m.visible = false; fx.add(m); }

  // ---- poses (frame px). The box { cx, cy: its front's centre, W: the front's width, yaw° (+: toward the copy), lift
  // (of W), a, D: depth }; a vessel { x: its axis, y: its foot, H: its height, a, D } (0 peel, 1 pH, 2 serum)
  const B = (cx, cy, W, D, lift = 0) => ({ cx, cy, W, yaw: 4, lift, a: 1, D });
  // S3: the closed box far behind the row, small, upper right of the peel with a gap (its left edge 900, the peel's right 838)
  const BOX = [B(760, 790, 660, DIST + 1), B(745, 805, 607, DIST + 1), B(1000, 815, 200, DIST + 8), null, null, B(720, 900, 500, DIST + 1, 0.6)];
  const BOX_IN = B(720, 850, 200, DIST + 6);   // S5 → kit: from the depth
  const VS = (x, y, H) => ({ x, y, H });
  const ROW2 = [VS(760, 1010, 350), VS(570, 1010, 229), VS(400, 1010, 229)];
  const ROW3 = [VS(1025, 1120, 210), VS(915, 1120, 137), VS(820, 1120, 137)];
  const ROW4 = [VS(960, LY, 300), VS(760, LY, 196), VS(560, LY, 196)];
  const OUT = [[0.25, 0.65], [0.4, 0.8], [0.55, 0.95]];   // S2 → S3: each one's way out from behind the box (the box settles by 0.4)
  const SIDE = 0.45;   // of its way: sideways behind the box until clear of its left edge; then out, forward, down to the row
  const ARRIVE = [0.62, 0.7, 0.78];   // S4 → S5: its marker lights as it stands
  const STEP = [0.15, 0.32, 0.5];     // S5 → kit, while the page's step cards pass: step 1 current to f 0.15, 2 to 0.32, 3 to 0.5
  // the state, written in place on every frame (nothing allocated per frame)
  const ves = () => ({ x: 0, y: 0, H: 1, a: 0, D: DIST, cur: 0 });
  const ST = { box: { cx: 0, cy: 0, W: 1, yaw: 4, lift: 0, a: 0, D: DIST + 1 }, v: [ves(), ves(), ves()], halo: 0, haloExt: 0.08,
    dust: 0, fade: 0, wave: 0, line: 0, pa: 0, vglow: 0, back: 0, veil: 0, draw: 0, marks: 0, circ: 0, strokesA: 0 };
  const setBox = (o, s, a = 1) => { o.cx = s.cx; o.cy = s.cy; o.W = s.W; o.yaw = s.yaw; o.lift = s.lift; o.D = s.D; o.a = a; return o; };
  const mixBox = (o, a, b, s) => { o.cx = lerp(a.cx, b.cx, s); o.cy = lerp(a.cy, b.cy, s); o.W = lerp(a.W, b.W, s); o.D = lerp(a.D, b.D, s); o.yaw = lerp(a.yaw, b.yaw, s); o.lift = lerp(a.lift, b.lift, s); return o; };
  const setV = (o, s, a = 1, D = DIST) => { o.x = s.x; o.y = s.y; o.H = s.H; o.a = a; o.D = D; o.cur = 0; return o; };
  const mixV = (o, a, b, s) => { o.x = lerp(a.x, b.x, s); o.y = lerp(a.y, b.y, s); o.H = lerp(a.H, b.H, s); return o; };
  const boxBack = b => b.D + world(b.W, b.D) * BD;   // the depth of the box's back

  function story(p) {   // the state at story position p
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST, b = st.box;
    setBox(b, BOX[0], 0); for (let i = 0; i < 3; i++) setV(st.v[i], ROW2[i], 0);
    st.halo = st.dust = st.fade = st.wave = st.line = st.vglow = st.back = st.veil = st.draw = st.marks = st.circ = st.strokesA = 0;
    st.pa = 0; st.haloExt = 0.08;
    if (k === 0) {   // S1 → S2: the box steps back (0.92), still closed, its colours unchanged; the glow behind it to 40 %; the
      // sparks dull to grey dust and begin to settle; the rest of the dust comes in
      mixBox(b, BOX[0], BOX[1], smooth(0, 1, f)); b.a = 1;
      st.halo = 1 - 0.6 * smooth(0, 0.6, f); st.dust = smooth(0.2, 0.8, f); st.fade = f; st.pa = 1;
    } else if (k === 1) {   // S2 → S3: the box goes deeper, to the right; the three come out from behind it one by one (not out of
      // it): each starts hidden behind the box's back and takes its opacity there, moves sideways (still behind) until its
      // silhouette clears the box's left edge, and only then comes forward and down to its place in the row: it never
      // crosses the box's front while inside the box's outline
      mixBox(b, BOX[1], BOX[2], smooth(0, 0.4, f)); b.a = 1;
      st.halo = 0.4 * (1 - smooth(0, 0.4, f)); st.dust = 1; st.fade = 1; st.pa = 1;
      const left = b.cx - b.W * 0.535 - 12;   // the box's silhouette (its left side shows: yaw, sway)
      for (let i = 0; i < 3; i++) {
        const s = smooth(OUT[i][0], OUT[i][1], f), o = st.v[i], e = ROW2[i], y0 = b.cy + b.W * 0.44;
        const Db = Math.max(boxBack(b) + 0.6, e.H * DIST / (0.86 * b.W));   // behind the box, deep enough to hide whole
        const xc = left - e.H * DIST / Db * H_W[i] / 2;   // its axis when its right edge is clear of the box (at Db)
        const sa = smooth(0, SIDE, s), sb = smooth(SIDE, 1, s);
        o.x = lerp(lerp(b.cx + 40 * (1 - i), xc, sa), e.x, sb); o.y = lerp(y0, e.y, sb) - 60 * Math.sin(Math.PI * sb);
        o.D = lerp(Db, DIST, sb); o.H = e.H; o.a = smooth(0, 0.15, s); o.cur = 0;   // H: its size at the row's depth
      }
    } else if (k === 2) {   // S3 → S4 (the line's light): a soft champagne light comes up behind the three (their colours stay);
      // a wave from the row runs out through the dust and turns it into an even veil; the box goes; the three go small,
      // low right, into a backlight
      setBox(b, BOX[2], 1 - smooth(0, 0.35, f));
      st.dust = 1; st.fade = 1; st.pa = 1; st.wave = 900 * smooth(0.15, 0.75, f); st.veil = smooth(0.4, 0.9, f);
      const g = smooth(0.45, 1, f);
      for (let i = 0; i < 3; i++) mixV(setV(st.v[i], ROW2[i]), ROW2[i], ROW3[i], g);
      st.vglow = smooth(0, 0.2, f) * (1 - smooth(0.6, 1, f)); st.back = smooth(0.45, 1, f);
    } else if (k === 3) {   // S4 → S5: the veil sinks and draws into one gold line, drawn right to left from step 1; the three
      // rise onto it and grow; each marker lights as its vessel stands; the finish ring; the rhythm's circle
      st.dust = 1; st.fade = 1; st.wave = 2000; st.veil = 1 - smooth(0.2, 0.5, f);
      st.line = smooth(0.05, 0.45, f); st.pa = 1 - smooth(0.3, 0.55, f);
      const g = smooth(0.3, 0.8, f);
      for (let i = 0; i < 3; i++) mixV(setV(st.v[i], ROW3[i]), ROW3[i], ROW4[i], g);
      st.back = 1 - smooth(0.3, 0.6, f); st.strokesA = 1; st.draw = 1.02 * smooth(0.25, 0.6, f);   // (past 1: the ends whole)
      st.marks = 0.26 * smooth(ARRIVE[0] - 0.02, ARRIVE[0], f) + 0.25 * smooth(ARRIVE[1] - 0.02, ARRIVE[1], f)
        + 0.25 * smooth(ARRIVE[2] - 0.02, ARRIVE[2], f) + 0.25 * smooth(0.78, 0.8, f);   // the dots (aT 0, ¼, ½), the ring (¾)
      st.circ = 1.02 * smooth(0.55, 1, f);
      st.v[0].cur = smooth(0.82, 1, f);   // step 1 is the current one as S5 settles
    } else {   // S5 → kit: the three hold while the page's step cards pass (to f ≈ 0.5), the current step lit from behind by
      // the line's light (1, 2, 3 in turn: the product itself is never dimmed); the protocol stays under them till they
      // go; the closed box comes forward from the depth; the three step back to its middle, behind it, and dissolve; the
      // sleeve lifts straight up 0.60 W (photos 26 and 32); the champagne round the box grows (S7: the page's strongest)
      st.strokesA = 1 - smooth(0.5, 0.65, f); st.draw = 1.02; st.marks = 1.01; st.circ = 1.02;
      const g = smooth(0.5, 0.7, f); mixBox(b, BOX_IN, BOX[5], g); b.lift = 0.6 * smooth(0.72, 0.95, f); b.a = smooth(0.5, 0.6, f);
      const r = smooth(0.55, 0.75, f), Db = boxBack(b) + 0.4;
      for (let i = 0; i < 3; i++) {
        const o = setV(st.v[i], ROW4[i], 1 - r); o.x = lerp(ROW4[i].x, b.cx, r); o.y = lerp(ROW4[i].y, b.cy + b.W * 0.3, r); o.D = lerp(DIST, Db, r);
        o.cur = (i ? smooth(STEP[i - 1] - 0.03, STEP[i - 1] + 0.03, f) : 1) * (1 - smooth(STEP[i] - 0.03, STEP[i] + 0.03, f));
      }
      st.halo = smooth(0.75, 1, f); st.haloExt = 0.035;
    }
    if (p >= 5) {   // the kit: exactly the pose, nothing in flight
      setBox(b, BOX[5], 1); for (let i = 0; i < 3; i++) st.v[i].a = 0; st.halo = 1; st.haloExt = 0.035; st.strokesA = 0;
    }
    return st;
  }

  // ---- applying a state
  const tmp = new V3(), last = { t: 0 };
  const DEPTH = new Float32Array(3), RANK = [0, 1, 2], farFirst = (i, j) => DEPTH[j] - DEPTH[i];
  const HALO_A = [0.6, 0.8];   // the halo's strength: S1 (S2 at 40 % of it), the kit
  const SOLID = ['liquid', 'neck', 'cap'];   // the heroes' parts that write depth once opaque
  let lastW = 1;   // the box's front width drawn (with its breath): the ΔE probes (state()) are placed by it
  function pose(p, t, still) {
    const st = story(p), live = still ? 0 : 1 - smooth(4.85, 5, p), ph = phone.matches;
    const b = st.box;
    // the box: its front parallel to the picture's vertical, turned to face the camera, then toward the copy (4°; the idle
    // sway ±1.5°: within 5.5°, its sides are not photographed); on S1 it breathes ±1.5 %
    box.visible = b.a > 0.004;
    const breathe = 1 + 0.015 * Math.sin(t * 0.9) * live * (1 - smooth(0.6, 1, p));
    if (box.visible) {
      const S = world(b.W, b.D) * breathe;
      at(b.cx, b.cy, b.D, box.position); box.scale.setScalar(S); box.quaternion.copy(lay.quaternion);
      box.rotateY(facing(box) + rad(b.yaw + 1.5 * Math.sin(t * 0.4 + 1) * live));
      sleeve.position.y = b.lift; trayG.visible = b.lift > 0.004;   // the contents only once the sleeve lifts
      lidGap.visible = b.lift < 0.002;
      for (const m of boxMats) { m.opacity = b.a; m.depthWrite = b.a > 0.99 && m !== trayGoldMat; }
    }
    if (trayG.visible) {   // the tray's contents take the box's opacity
      for (const m of trayMats) m.opacity = b.a;
      capFaceSet(trayU, box);
    }
    // the three, drawn back to front; each faces the camera, swaying ±3° (the peel is square: its sides barely show)
    for (let i = 0; i < 3; i++) {
      const s = st.v[i], h = heroes[i], g = h.g; g.visible = s.a > 0.004; DEPTH[i] = s.D; if (!g.visible) continue;
      at(s.x, s.y, s.D, g.position); g.scale.setScalar(world(s.H, DIST));   // its size in the world: s.H px tall at the row's depth
      g.quaternion.copy(lay.quaternion); g.rotateY(facing(g) + rad(3 * Math.sin(t * 0.45 + i * 2.1) * live));
      for (const k in h.mats) if (h.mats[k].isMaterial) h.mats[k].opacity = s.a;
      capFaceSet(h.mats.U, g);
      for (const k of SOLID) if (h.mats[k]) h.mats[k].depthWrite = s.a > 0.99;
    }
    RANK.sort(farFirst);
    for (let r = 0; r < 3; r++) { const L = heroes[RANK[r]].parts; for (let j = 0; j < L.length; j++) L[j].renderOrder = 120 + r * 10 + (L[j].isInstancedMesh ? 3.5 : j); }
    if (heroes[0].g.visible) {   // ≥ 1.5 device px: the bottle is st.v[0].H frame px tall at the row's depth
      flakeMin = 1.5 / Math.max(1, st.v[0].H * DIST / st.v[0].D * pxU.value);
      setFlakes(heroes[0].flakes, t, flakeMin); heroes[0].flakes.count = ph ? 460 : NF;
    }
    // the graphics: the far layer behind everything shown
    let Dfar = 9;
    if (box.visible) Dfar = Math.max(Dfar, boxBack(b));
    for (let i = 0; i < 3; i++) if (heroes[i].g.visible) Dfar = Math.max(Dfar, st.v[i].D + 1);
    place(fx, Dfar + 1);
    const W = b.W * breathe; lastW = W;
    const ha = st.halo * (st.haloExt < 0.05 ? HALO_A[1] : HALO_A[0]);
    if (ha > 0.004 && box.visible) {   // round the box's outline; on the kit round the sleeve lifted too
      const top = b.cy - W / 2 - b.lift * W, bot = b.cy + W / 2, e = st.haloExt * W, u = halo.material.uniforms;
      u.uR.value.set(b.cx, (top + bot) / 2, W / 2, (bot - top) / 2); u.uExt.value = e; u.uB.value.set(b.cx - W / 2 - e, top - e, b.cx + W / 2 + e, bot + e);
      u.uA.value = ha * b.a; halo.visible = true;
    } else halo.visible = false;
    for (let i = 0; i < 3; i++) {   // the light behind the three (S3 → S4); the current step's, smaller, kept left of the copy (S5)
      const s = st.v[i];
      if (s.cur > 0.004) setSpot(vSpots[i], s.x, s.y - s.H * 0.45, s.H * H_W[i] * 1.15, s.H * 0.62, 0.4 * s.cur * s.a);
      else setSpot(vSpots[i], s.x, s.y - s.H * 0.5, s.H * H_W[i] * 1.6, s.H * 0.75, 0.45 * st.vglow * s.a);
    }
    setSpot(backGlow, 930, 1060, 230, 110, 0.5 * st.back);
    setSpot(veilGlow, C0[0], C0[1], AX[0], AX[1], still ? 0 : 0.14 * st.veil);
    ring.material.uniforms.uR.value = st.wave; ring.material.uniforms.uA.value = 0.25; ring.visible = !still && st.wave > 1 && st.wave < 899;   // (an annulus: no uB)
    PU.uTime.value = t; PU.uDust.value = st.dust; PU.uFade.value = st.fade; PU.uWave.value = st.wave; PU.uLine.value = st.line; PU.uAlpha.value = st.pa;
    parts.visible = !still && st.pa > 0.004; pg.instanceCount = ph ? NPT / 2 : NPT;
    lineM.material.uniforms.uDraw.value = st.draw; lineM.material.uniforms.uOpacity.value = st.strokesA; lineM.visible = st.strokesA > 0.004 && st.draw > 0.002;
    markM.material.uniforms.uDraw.value = st.marks; markM.material.uniforms.uOpacity.value = st.strokesA; markM.visible = st.strokesA > 0.004 && st.marks > 0.002;
    circM.material.uniforms.uDraw.value = st.circ; circM.material.uniforms.uOpacity.value = st.strokesA * 0.8; circM.visible = st.strokesA > 0.004 && st.circ > 0.002;
    last.t = t;   // QA (state()): the flakes outside the liquid at this time
  }
  function probes() {   // QA: the probe points of the ΔE checks (frame px) in the last pose drawn (state() only: no garbage per frame)
    const b = ST.box, v = ST.v, W = lastW, tray = trayG.visible && b.lift > 0.59;
    const pt = (o, fr) => (o.a > 0.99 ? [o.x, o.y - o.H * DIST / o.D * fr] : null);   // fr of its height above its foot
    return { foil: box.visible && b.a > 0.99 ? [b.cx, b.cy - W * (0.2 + b.lift)] : null,
      peel: pt(v[0], LIQ1 - 0.8 * (LIQ1 - LIQ0)), ph: pt(v[1], 0.25), ls: pt(v[2], 0.25),
      trayPeel: tray ? [b.cx + (0.125 - 0.5) * W, b.cy + (0.732 - 0.41 * (LIQ1 - 0.8 * (LIQ1 - LIQ0)) - 0.5) * W] : null,
      trayPh: tray ? [b.cx + (ROWS[2] - 0.5) * W, b.cy + (0.470 - 0.25 * VH - 0.5) * W] : null,
      trayLs: tray ? [b.cx + (ROWS[2] - 0.5) * W, b.cy + (0.740 - 0.25 * VH - 0.5) * W] : null };
  }
  function capFaceSet(U, o) {   // a metal's reflection turned with the object as it faces the camera
    o.updateMatrixWorld(); tmp.setFromMatrixPosition(o.matrixWorld);
    toCam.copy(lay.position).sub(tmp).applyQuaternion(layInv);
    U.value.setFromMatrix4(m4.makeRotationAxis(upL, -Math.atan2(toCam.x, toCam.z)));
  }
  function flakesOutside(t) {   // QA: flakes whose disc leaves the liquid's front (x, y) or its layer (z)
    let n = 0;
    for (let i = 0; i < NF; i++) {
      const s = flakeAt(i, t, fp, flakeMin) / 2;
      if (Math.abs(fp.x) + s > LW / 2 || fp.y - s < LIQ0 || fp.y + s > LIQ1 || fp.z < LD / 2 || fp.z > DB / 2) n++;
    }
    return n;
  }

  // ---- drawing into the engine's box: the full frame is the cover; the canvas shows the box's part of it
  // the density drawn: a phone's stage is small, so it draws at the screen's full density (≤ 3, as the MASK page), a
  // desktop at the engine's (≤ 2); long frames lower it under a cap (pace), which a rotation keeps
  const phone = matchMedia('(max-width: 899px)'), full = view => (phone.matches ? Math.min(3, devicePixelRatio || 1) : view.dpr);
  let cap = Infinity, pr = 0, sizeW = -1, sizeH = -1, sizePr = -1, renders = 0, lastT = 0, lastP = 0, lastView = null, trial = null, capped = false;
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
    pxU.value = pr * view.cover.w / 2400;   // device px per frame px: the strokes and particles keep ≥ 1.5 device px
    EDGE.value.set((view.box.y - view.cover.y) * 2400 / view.cover.w, canvas.height, pxU.value);   // the frame's top edge
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
    const mats = new Set(), geos = new Set();
    scene.traverse(o => { if (o.geometry) geos.add(o.geometry); if (o.material) mats.add(o.material); });
    for (const g of geos) g.dispose();
    for (const m of mats) m.dispose();
    scene.traverse(o => { if (o.isInstancedMesh) o.dispose(); });   // their instance matrices' buffers (not freed with the geometry)
    for (const t of TEXS.concat([roomEnv, glassEnv])) t.dispose();
    renderer.dispose();
  }
  const r1 = v => Math.round(v * 10) / 10, r2 = v => Math.round(v * 100) / 100;
  const state = () => {
    const st = ST, b = st.box;
    return { quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded, version, kits, lastP,
      box: { x: r1(b.cx), y: r1(b.cy), W: r1(b.W), yaw: r1(b.yaw), lift: r2(b.lift), o: r2(b.a) },
      vessels: st.v.map(v => ({ x: r1(v.x), y: r1(v.y), H: r1(v.H), o: r2(v.a), D: r2(v.D), cur: r2(v.cur) })), boxD: r2(b.D),
      far: { n: parts.visible ? pg.instanceCount : 0, mode: st.wave >= 899 ? (st.line > 0 ? 'line' : 'veil') : st.wave > 0 ? 'wave' : st.dust > 0.5 ? 'dust' : 'sparks', wave: r1(st.wave) },
      lines: { line: r2(lineM.visible ? st.draw * st.strokesA : 0), circle: r2(circM.visible ? st.circ * st.strokesA : 0), ring: r2(markM.visible && st.marks > 0.75 ? st.strokesA : 0) },
      glow: r2(halo.visible ? halo.material.uniforms.uA.value : 0), flakes: { n: heroes[0].g.visible ? heroes[0].flakes.count : 0, outside: heroes[0].g.visible ? flakesOutside(last.t) : 0 },
      probes: probes() };
  };
  return { draw, kit, dispose, state, animated: true };
}
