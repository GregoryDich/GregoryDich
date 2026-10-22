// EXO-NAD live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D scene, as
// the approved sample EXOTECH GEL (scenes/exotech-gel.js) and the HAIR line's pages (exosignal-hair.js, exosignal-spray.js,
// whose light, print materials, edge fade, pace, state and dispose this module follows). The engine keeps the
// story geometry (the cover-fitted 16:10 frame, the run's box, the phone stage, the kit card); this module draws the pose
// for the story position into the box. Objects are placed by frame pixel (2400×1500), measured on the only packshot,
// protocols/print/img/exo-nad.webp (795×488): the brushed gold box seen square on (476 px), the square glass peel bottle
// with its gold cap and two phases, the pH Normalizer and Longevity Serum vials with silver crimp caps: clear glass, the
// amber-brown and the blue liquid filling about 70 % of them, dark against the black as photographed, the print small
// and quiet, as on the owner's photos of 22/10.
// The story (site/story3d.json; scratchpad spec pages/exo-nad/spec.md): S1 the closed box, champagne glow behind it;
// S2 the box deeper, its glow lower; S3 the three liquids come out from behind the box one by one and stand in a row,
// 1-2-3 right to left (peel, pH, serum), the box going away into the dark behind them; S3 → S4 a soft light rises
// behind them and a shapeless champagne haze; the three go small, low right, in a backlight; S4 → S5 the haze sinks,
// the three rise and grow in their row, each lit from behind in turn as its step is read; S6–S7 the box comes forward,
// its sleeve lifts straight up until its foot is at 57 % of the open kit's height (photo A of 22/10) and the camera
// steps in to the box as a hand-held photo is taken (wider, the box kept in place and size: the base's gold walls
// show their insides, the tray lies deep, the sleeve's edge shades it); the black tray shows the peel bottle and the
// rows of 5 + 5 vials, the pH caps under the sleeve's edge: the pose that flies into the offer card. Nothing else
// opens: no photo shows the caps off. The product keeps its print's colours
// (emissive ≈ 85 % + neutral shading, toneMapped off); the line's champagne (#d8c48a) lives only around it, as soft
// shapeless glow and haze. Only what exists is drawn (the owner, 22/10): the products and their packaging, the gold
// flakes inside the peel; no lines, rings, dots or particles of anything the kit does not hold. No text is drawn but the
// package's own print (design/exo-nad/make_textures.py, from the packshot and the owner's photos of 22/10). No exosomes.
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
  const facing = o => { toCam.copy(camera.position).sub(o.position).applyQuaternion(layInv); return Math.atan2(toCam.x, toCam.z); };

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
    old.forEach(t => t.dispose()); sizeW = -1; lastId = '';
    version++; if (onLoad) onLoad();
  };
  canvas.addEventListener('webglcontextrestored', restored);
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(-4, 7, 6); scene.add(key);
  // the key leaves no glint on the glass and the dark necks (a white dot or dash in the same place on every vial, a row of
  // specks across the tray, which the photos do not have): their highlights come from the studio's softboxes only
  const noGlint = sh => {
    sh.fragmentShader = sh.fragmentShader.replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
      reflectedLight.directSpecular = vec3(0.0); clearcoatSpecularDirect = vec3(0.0);`);
  };

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
  // and its gloss (the owner's photos: a glossy foil with soft reflections): a broad softbox behind the camera, up and to
  // the left, mirrored by the foil (the reflected view ray, in the camera's space: fixed to the studio, so it stays put as
  // the box moves and the sleeve slides through it). Faces turned away (the walls' insides) do not see it. Normalised to
  // 1 at the ΔE probe's reflection in every pose (S1 r ≈ (0.24, 0.04), the kit (0.25, 0.12)): it moves no print colour
  // (the face's own normal, not the brushing's: the brushing stays fine)
  const SHEEN = 'vec3 rv = uToLay * reflect(normalize(uEyeOff - vViewPosition), nonPerturbedNormal); float shn = rv.z > 0.0 ? exp(-pow((rv.x - 0.19) / 0.17, 2.0) - pow((rv.y - 0.08) / 0.13, 2.0)) : 0.0;\n'
    + '        gl_FragColor.rgb *= (1.0 + 0.45 * shn) / 1.36;';
  // the foil is lit and mirrors the studio as the story's camera sees it, also while the kit's lens (lens()) steps the
  // drawn camera in: its colour does not move with the lens (uEyeOff: the story camera's eye in the drawn camera's view)
  const EYE = { value: new V3() }, TOLAY = { value: new THREE.Matrix3() };
  const eyeFixed = sh => {
    sh.uniforms.uEyeOff = EYE; sh.uniforms.uToLay = TOLAY;
    sh.fragmentShader = 'uniform vec3 uEyeOff;\nuniform mat3 uToLay;\n' + sh.fragmentShader.replace('#include <lights_fragment_begin>',
      THREE.ShaderChunk.lights_fragment_begin.replace(/normalize\( vViewPosition \)/g, 'normalize( vViewPosition - uEyeOff )'));
  };
  // the faces that turn from the studio take less of it (the print's colour is emissive, so its own shading is slight):
  // the sleeve's rounded foot darkens toward its underside (the board's edge, as photographed: a light line over a dark
  // one), the base's walls' insides are in the walls' own shade (the left one turned from the key the more) and darken
  // into the tray, as the band's top edge does (part: 'sleeve', 'base'; the printed face has neither)
  const foilLight = (sh, part) => {
    edgeFade(sh); eyeFixed(sh);
    const IW = (WX - WALL).toFixed(4), YL = (yv(LIDV) + RLIP).toFixed(4), Z = (-REC).toFixed(4);
    sh.vertexShader = 'varying vec3 vBoxP;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vBoxP = position;');
    sh.fragmentShader = 'varying vec3 vBoxP;\n' + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float u = vBoxP.x + 0.5, v = 0.5 - vBoxP.y, du = (u - 0.36) / 0.38, dv = (v - 0.42) / 0.55;
        gl_FragColor.rgb *= (0.82 + 0.30 * exp(-(du * du + dv * dv))) * (v > 0.879 ? 0.86 : 1.0);
        ${part === 'sleeve' ? `if (vBoxP.y < ${YL} + 0.0001 && abs(vBoxP.x) < 0.499) {   // the rounded foot: 1 facing forward … 0 facing down
          float c = clamp(vBoxP.z / ${RLIP.toFixed(4)}, 0.0, 1.0);
          gl_FragColor.rgb *= mix(mix(0.3, 1.7, smoothstep(0.15, 0.7, c)), 1.0, smoothstep(0.88, 0.99, c)); }` : ''}
        ${part === 'base' ? `float deep = clamp(vBoxP.z / ${Z}, 0.0, 1.0);
        if (vBoxP.z < -0.0005 && abs(abs(vBoxP.x) - ${IW}) < 0.0008) gl_FragColor.rgb *= (vBoxP.x < 0.0 ? 0.62 : 0.8) * mix(1.0, 0.7, deep);
        else if (vBoxP.z < -0.0005 && abs(vBoxP.x) < ${IW}) gl_FragColor.rgb *= mix(1.08, 0.8, deep);` : ''}
        ${SHEEN} }`);
  };
  const lidMat = P(0xffffff, Object.assign({}, FOIL_OPTS, { color: new THREE.Color(SHADE, SHADE, SHADE), map: lidTex, emissiveMap: lidTex,
    metalnessMap: lidMetal, roughnessMap: lidMetal, roughness: 1, bumpMap: brush, bumpScale: 0.6 }), 'lid');
  const foilMats = part => { const m = P(FOIL, FOIL_OPTS, 'foil-' + part); m.onBeforeCompile = sh => foilLight(sh, part); return m; };
  lidMat.onBeforeCompile = sh => foilLight(sh);
  const velvet = () => P(0x1c1d1b, { roughness: 0.9, specularIntensity: 0.1, sheen: 0.4, sheenRoughness: 0.6, sheenColor: 0x3a3a38 }, 'velvet');
  const trayGold = () => { const m = P(FOIL, Object.assign({}, FOIL_OPTS, { alphaMap: trayInk, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }), 'traygold');
    m.onBeforeCompile = sh => { edgeFade(sh); eyeFixed(sh); sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { ${SHEEN} }`); }; return m; };   // the same foil, the same gloss
  // glass (HAIR's): no transmission (on a transparent canvas it cannot see the page's smoke, and a phone pays a pass for
  // it); its opacity follows Fresnel and its own highlights, so its edges and highlights read and the body stays clear
  function glassMat(side, a0, aF, aS, color = 0x0b0b0c, lit = null) {
    const m = new THREE.MeshPhysicalMaterial({ color, roughness: 0.04, ior: 1.5, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.6,
      envMap: glassEnv.texture, transparent: true, depthWrite: false, side, toneMapped: false });
    const k = [a0, aF, aS].map(v => v.toFixed(3));
    m.onBeforeCompile = sh => {
      edgeFade(sh); noGlint(sh);
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
  // the vials' liquids, clear and coloured as the owner's photos of 22/10 show them against the black tray and glove:
  // amber-brown and blue, dark where the black shows through them. The front colour where the body faces the camera
  // (within ±30° nothing changes: the ΔE probe), toward the right limb the light behind it comes through, brighter, the
  // left limb in shadow; lit through the foot, a little darker up the column; thinner toward the limbs, so what is
  // behind shows there (alpha 0.9 → 0.55); its surface (seen from a little above, a thin ellipse) and the meniscus light
  function liquidMat(hex, limb, shade) {
    const m = P(hex, { roughness: 0.5, specularIntensity: 0.2, depthWrite: false }, 'liq' + hex);
    const L = new THREE.Color(limb), S = new THREE.Color(shade);
    m.onBeforeCompile = sh => {
      edgeFade(sh);
      sh.uniforms.uLimb = { value: new V3(L.r, L.g, L.b) }; sh.uniforms.uShade = { value: new V3(S.r, S.g, S.b) };
      sh.vertexShader = 'varying float vLy;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vLy = position.y;');
      sh.fragmentShader = 'uniform vec3 uLimb, uShade;\nvarying float vLy;\n' + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float nx = normal.x, ax = abs(nx);
        gl_FragColor.rgb = mix(gl_FragColor.rgb, uLimb, 0.85 * smoothstep(0.55, 0.85, nx) * (1.0 - smoothstep(0.93, 1.0, nx)));
        gl_FragColor.rgb = mix(gl_FragColor.rgb, uShade, 0.8 * smoothstep(-0.55, -0.9, nx));
        gl_FragColor.rgb *= 1.0 + 0.3 * (1.0 - smoothstep(0.04, 0.14, vLy)) - 0.12 * smoothstep(0.16, ${(FILL - 0.03).toFixed(3)}, vLy);   // lit through the foot
        float top = smoothstep(${(FILL - 0.016).toFixed(3)}, ${(FILL - 0.001).toFixed(3)}, vLy);
        gl_FragColor.rgb = mix(gl_FragColor.rgb, mix(uLimb, vec3(1.0), 0.35), 0.55 * top);
        gl_FragColor.a *= mix(0.9, 0.55, smoothstep(0.5, 0.97, ax)) + 0.1 * top; }`);
    };
    return m;
  }
  // the metal caps: the peel's polished gold (vertical stripes from the softboxes), the vials' aluminium; a little of
  // their colour as emission (never black where they mirror the dark). Their reflection is turned with the object as it
  // faces the camera (uFace, as the spray's cap), so a cap reads the same anywhere in the frame
  const faceU = () => ({ value: new THREE.Matrix3() });
  function metalMat(hex, rough, emi, U, metal = 1) {   // metal 0: the vials' white plastic flip-off tops
    const m = new THREE.MeshPhysicalMaterial({ color: hex, metalness: metal, roughness: rough, emissive: hex, emissiveIntensity: emi,
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
  const neckMat = (hex, opts, key) => { const m = P(hex, opts, key); m.onBeforeCompile = sh => { edgeFade(sh); noGlint(sh); }; return m; };
  // the tray's light, on its contents and its print: the sleeve's foot shades what lies under it, the deeper the longer
  // (the studio's light comes from above and before it: the shade ends 0.7 × the depth under the edge, softer the deeper),
  // and the velvet darkens into the corners with the walls and the band it lies between. In the box's own units (uBoxInv:
  // world → box; uLidY: the sleeve's foot), also for the instanced vials
  const BOXINV = { value: new THREE.Matrix4() }, LIDY = { value: 0 };
  function trayLight(m, corners = false) {
    const ob = m.onBeforeCompile, key = m.customProgramCacheKey;
    m.onBeforeCompile = (sh, r) => {
      ob.call(m, sh, r); sh.uniforms.uBoxInv = BOXINV; sh.uniforms.uLidY = LIDY;
      sh.vertexShader = 'uniform mat4 uBoxInv;\nvarying vec3 vBoxL;\n' + sh.vertexShader.replace('#include <project_vertex>', `#include <project_vertex>
      { vec4 lp = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
        lp = instanceMatrix * lp;
        #endif
        vBoxL = (uBoxInv * modelMatrix * lp).xyz; }`);
      sh.fragmentShader = 'uniform float uLidY;\nvarying vec3 vBoxL;\n' + sh.fragmentShader.replace('#include <tonemapping_fragment>', `{
        float g = max(0.003 - vBoxL.z, 0.0), d = uLidY - vBoxL.y;
        float k = mix(0.42, 1.0, smoothstep(0.2 * g - 0.003, 1.2 * g + 0.003, d));
        ${corners ? `float e = min(${(WX - WALL).toFixed(4)} - abs(vBoxL.x), vBoxL.y - ${yv(BANDV).toFixed(4)});
        k *= mix(0.5, 1.0, smoothstep(0.0, 0.05, e));` : ''}
        gl_FragColor.rgb *= k; }
      #include <tonemapping_fragment>`);
    };
    m.customProgramCacheKey = () => key.call(m) + '-tray' + (corners ? 'c' : '');
    return m;
  }

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
  // the base: its front band (v 0.881…1), gold side walls up to the top (0.028 W: photo A shows them as gold strips either
  // side of the tray, their insides too), the black tray 0.09 deeper (the vials, 0.1 W across, lie half sunk in it) with
  // the peel bottle and the rows of five vials (photo 29: left the peel, centres u 0.129; the rows at u 0.317 + 0.139 k);
  // depth 0.28 W (unknown: an assumption, spec §5). The sleeve's face stands 0.006 before the base's, its foot's edge
  // rounded (r 0.006, the board's thickness: it catches the light above and goes dark below); between its foot (v 0.877)
  // and the band (0.881) the dark of the tray shows: the lid line
  const BD = 0.28, LIDV = 0.877, BANDV = 0.881, WALL = 0.028, WX = 0.494, REC = 0.09, RLIP = 0.006;
  const box = new THREE.Group(), sleeve = new THREE.Group(), trayG = new THREE.Group(); box.add(sleeve); box.add(trayG); scene.add(box);
  const yv = v => 0.5 - v;   // the front's v (0 top … 1 foot) → local y
  const foilBox = foilMats('base'), foilSleeve = foilMats('sleeve'), velvetMat = velvet(), trayGoldMat = trayGold();   // (their
  // geometry is in the box's own units: u, v)
  // the printed face down to the rounded edge (its texture spans v 0…0.877: the last 0.006, bare foil, goes round it)
  const faceGeo = plane(1, LIDV - RLIP), fuv = faceGeo.attributes.uv;
  for (let i = 0; i < fuv.count; i++) fuv.setY(i, RLIP / LIDV + fuv.getY(i) * (1 - RLIP / LIDV));
  mesh(faceGeo.translate(0, yv((LIDV - RLIP) / 2), 0.006), lidMat, sleeve, 101);
  // the lid line: the dark under the sleeve's lip between its foot (v 0.877) and the band (0.881); it goes as the sleeve lifts
  const lidLine = P(0x161617, { roughness: 0.9, specularIntensity: 0.1 }, 'lidline');
  const lidGap = mesh(plane(1, BANDV - LIDV).translate(0, yv((LIDV + BANDV) / 2), 0.003), lidLine, box, 101);
  mesh(merge([[plane(1, BD + 0.006), M(0, 0.5, (0.006 - BD) / 2, -Math.PI / 2)],                       // top
    [plane(BD + 0.006, LIDV), M(-0.5, yv(LIDV / 2), (0.006 - BD) / 2, 0, -Math.PI / 2)],                 // sides
    [plane(BD + 0.006, LIDV), M(0.5, yv(LIDV / 2), (0.006 - BD) / 2, 0, Math.PI / 2)],
    [plane(1, LIDV), M(0, yv(LIDV / 2), -BD, 0, Math.PI)],                                               // back
    [new THREE.CylinderGeometry(RLIP, RLIP, 1, 8, 1, true, 0, Math.PI / 2).rotateZ(-Math.PI / 2), M(0, yv(LIDV) + RLIP, 0.006 - RLIP)]]),   // the edge
    foilSleeve, sleeve, 100);
  const bandH = 1 - BANDV, wallH = BANDV;
  mesh(merge([[plane(1, bandH), M(0, yv(BANDV + bandH / 2), 0)],                                          // the band
    [plane(BD, bandH), M(-0.5, yv(BANDV + bandH / 2), -BD / 2, 0, -Math.PI / 2)], [plane(BD, bandH), M(0.5, yv(BANDV + bandH / 2), -BD / 2, 0, Math.PI / 2)],
    [plane(2 * (WX - WALL), REC), M(0, yv(BANDV), -REC / 2, -Math.PI / 2)],                              // the band's top edge
    [plane(0.5 - WX, BD), M(-(0.5 + WX) / 2, yv(BANDV), -BD / 2, -Math.PI / 2)],                         // its ledge either side,
    [plane(0.5 - WX, BD), M((0.5 + WX) / 2, yv(BANDV), -BD / 2, -Math.PI / 2)],                          // under the walls' outsides
    [plane(WALL, wallH), M(-WX + WALL / 2, yv(wallH / 2), 0)], [plane(WALL, wallH), M(WX - WALL / 2, yv(wallH / 2), 0)],   // walls: front edges
    [plane(BD, wallH), M(-WX, yv(wallH / 2), -BD / 2, 0, -Math.PI / 2)], [plane(BD, wallH), M(WX, yv(wallH / 2), -BD / 2, 0, Math.PI / 2)],   // outsides
    [plane(REC, wallH), M(-WX + WALL, yv(wallH / 2), -REC / 2, 0, Math.PI / 2)], [plane(REC, wallH), M(WX - WALL, yv(wallH / 2), -REC / 2, 0, -Math.PI / 2)]]),   // insides
    foilBox, box, 100);
  // the tray and its print belong to the contents (trayG): shown only once the sleeve lifts, never through a fading sleeve
  const tray = mesh(plane(2 * (WX - WALL), wallH), velvetMat, trayG, 102); tray.position.set(0, yv(wallH / 2), -REC);
  // its gold print (owner photos 22/10): the plane u 0.03…0.97 × v 0.03…0.88 = make_textures TRAY
  const trayPrint = mesh(plane(0.94, 0.85), trayGoldMat, trayG, 103); trayPrint.position.set(0, yv(0.455), -REC + 0.0005);
  const boxMats = [lidMat, foilSleeve, foilBox, velvetMat, trayGoldMat, lidLine];

  // ---- the peel bottle, height H_b = 1 (scaled per pose; origin its foot's centre): measured on the packshot (94 × 211
  // px): the square body W_b 0.4455 × 0.611, its corners rounded 0.05 W_b, 0.66 W_b deep (at least the cap's diameter);
  // the dark top glass 0.578…0.611, the liquid 0.123…0.578 (0.755 W_b wide, its two phases and gold in peel-liquid.png),
  // the thick glass foot and walls; the dark neck ring 0.630…0.678 (0.47 W_b), the polished gold cap 0.682…1 (0.638 W_b,
  // its top edge rounded 0.024); the label on the front as on the owner's photo (peel-print.png)
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
  // the thick foot and walls: clear glass, dark on the black page or tray as photographed, carrying the liquid's light
  // (the liquid's #e5d9ba, run through the glass by total internal reflection) in narrow lines: the walls' inner edge
  // beside the liquid and their outer edge, the foot's top under the liquid and its bottom edge; a breath of it between
  const f3 = v => v.toFixed(4);
  const slabLit = sh => {
    sh.vertexShader = 'varying vec3 vSlab;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vSlab = position;');
    sh.fragmentShader = 'varying vec3 vSlab;\n' + sh.fragmentShader.replace(/(gl_FragColor\.a = clamp\([^\n]*\n)/, `$1
      { float y = vSlab.y, ax = abs(vSlab.x), t = y < ${f3(LIQ0 - 0.002)}
          ? 0.06 + 0.25 * smoothstep(${f3(0.5 * LIQ0)}, ${f3(LIQ0)}, y) + 0.6 * exp(-pow((y - ${f3(LIQ0 - 0.01)}) / 0.01, 2.0)) + 0.45 * exp(-pow((y - 0.017) / 0.006, 2.0))
          : 0.06 + 0.55 * exp(-pow((ax - ${f3(LW / 2 + 0.005)}) / 0.008, 2.0)) + 0.45 * exp(-pow((ax - ${f3(WB / 2 - 0.009)}) / 0.004, 2.0));
        gl_FragColor.rgb += vec3(0.784, 0.694, 0.491) * 0.6 * t;   // added to the glass's own highlights
        gl_FragColor.a = max(gl_FragColor.a, 0.62 * t * opacity); }`);
  };
  const neckGeo = new THREE.CylinderGeometry(0.235 * WB, 0.235 * WB, 0.048, 64).translate(0, 0.654, 0);
  const RCAP = 0.319 * WB, RTOP = 0.024;
  const capGeo = new THREE.LatheGeometry([new THREE.Vector2(0, 0.682), new THREE.Vector2(RCAP - 0.004, 0.682), new THREE.Vector2(RCAP, 0.686)]
    .concat(Array.from({ length: 9 }, (_, i) => { const a = i / 8 * Math.PI / 2; return new THREE.Vector2(RCAP - RTOP + RTOP * Math.cos(a), 1 - RTOP + RTOP * Math.sin(a)); }))
    .concat([new THREE.Vector2(0, 1)]), 96);
  const PP = [-0.45 * WB, 0.45 * WB, 1 - 0.80, 1 - 0.525];   // the label plane: x, y (from the foot); = make_textures PEEL_PLANE
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
      slab: glassMat(THREE.FrontSide, 0.03, 0.45, 1.0, 0x0b0b0c, slabLit), top: glassMat(THREE.FrontSide, 0.45, 0.3, 0.6, 0x3b3b3c),
      liquid: P(0xffffff, { color: new THREE.Color(SHADE, SHADE, SHADE), map: peelLiq, emissiveMap: peelLiq, roughness: 0.45, specularIntensity: 0.25 }, 'peelliq'),
      flakes: P(0xd1b55d, { metalness: 0.7, roughness: 0.3, specularIntensity: 1, side: THREE.DoubleSide }, 'flake'),
      neck: neckMat(0x0c0c0d, { roughness: 0.2, specularIntensity: 1, envMapIntensity: 1.2 }, 'neck'),
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
  // 0.68 W_v at 0.754 rounding out to the body at 0.652, the body (R 0.2355) to 0.094, the rounded foot (0.78 W_v). Clear
  // glass, as the owner's photos of 22/10 show it: the liquid fills about 70 % of the body (to FILL, its meniscus climbing
  // the wall), the glass above it empty, the tray or the page seen through it; the print small and quiet (photo A), black
  // on the dark liquid, wrapped round the glass over the liquid's middle (VPR: 0.36 of the packshot's flat print, which
  // spans the whole front: the names a third of the body's width)
  const R = 0.2355, V2 = (r, y) => new THREE.Vector2(r, y), FILL = 0.54, VPR = [0.214, 0.365];
  const arc = (cx, cy, r, a0, a1, n) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return V2(cx + r * Math.cos(a), cy + r * Math.sin(a)); });
  const shoulder = new THREE.SplineCurve([V2(R, 0.652), V2(R - 0.004, 0.69), V2(R - 0.03, 0.725), V2(0.19, 0.745), V2(0.16, 0.754), V2(0.153, 0.762)]).getPoints(24);
  const vialGlass = new THREE.LatheGeometry([V2(0, 0), V2(0.1837, 0)].concat(arc(R - 0.052, 0.052, 0.052, -Math.PI / 2 + 0.25, 0, 8), shoulder, [V2(0.153, 0.86), V2(0, 0.86)]), 72);
  const RL = 0.94 * R;   // the liquid inside the wall; its top a meniscus 0.008 high at the glass
  const vialLiquid = new THREE.LatheGeometry([V2(0, 0.032), V2(0.17, 0.032)].concat(arc(RL - 0.04, 0.072, 0.04, -Math.PI / 2, 0, 6),
    [V2(RL, FILL + 0.008), V2(RL - 0.004, FILL + 0.003), V2(RL - 0.014, FILL + 0.0005), V2(RL - 0.03, FILL), V2(0, FILL)]), 72);
  const vialNeck = new THREE.CylinderGeometry(0.148, 0.148, 0.1, 48).translate(0, 0.805, 0);
  const RV = 0.2096, RT = 0.022;
  const vialCap = new THREE.LatheGeometry([V2(0, 0.852), V2(RV - 0.003, 0.852), V2(RV, 0.856)].concat(arc(RV - RT, 1 - RT, RT, 0, Math.PI / 2, 8), [V2(0, 1)]), 72);
  // the print wrapped round the glass (u by angle), its arc as wide as the texture's proportions (1024 × 913 / 924 for
  // 2R × 0.42) at the band's height: ±21° of the front
  const vialPrint = (() => {
    const h = VPR[1] - VPR[0], half = 0.5 * (2 * R / 0.42) * h / R;
    return new THREE.CylinderGeometry(R * 1.003, R * 1.003, h, 64, 1, true, -half, 2 * half).translate(0, (VPR[0] + VPR[1]) / 2, 0);
  })();
  // the vial's glass: clear, its edges and two soft tall reflections of the studio's softboxes (the key's left of the
  // axis, the fill's right: as on the photographed vials), never over the ΔE probe on the axis
  const vialLit = sh => {
    sh.vertexShader = 'varying float vVy;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vVy = position.y;');
    sh.fragmentShader = 'varying float vVy;\n' + sh.fragmentShader.replace(/(gl_FragColor\.a = clamp\([^\n]*\n)/, `$1
      { float nx = normal.x, body = smoothstep(0.05, 0.11, vVy) * (1.0 - smoothstep(0.70, 0.76, vVy));
        float s = body * (0.55 * exp(-pow((nx + 0.42) / 0.10, 2.0)) + 0.26 * exp(-pow((nx - 0.52) / 0.06, 2.0)));
        // its outline: the glass seen edge-on (the walls, the shoulder) catches the room's light, so clear glass on black reads
        float rim = 0.38 * pow(1.0 - clamp(abs(dot(nonPerturbedNormal, normalize(vViewPosition))), 0.0, 1.0), 3.0) * (1.0 - smoothstep(0.76, 0.80, vVy));
        s += rim; gl_FragColor.rgb += vec3(s); gl_FragColor.a = max(gl_FragColor.a, s * opacity); }`);
  };
  const LIQ = { ph: [0x8a5a18, 0xc8923a, 0x2e1c06], ls: [0x2f3f58, 0x8296b8, 0x121824] };   // front, lit limb, shaded limb
  function vialMats(kind, alU) {
    return { back: glassMat(THREE.BackSide, 0.02, 0.3, 0.7), front: glassMat(THREE.FrontSide, 0.03, 0.55, 1.0, 0x0b0b0c, vialLit),
      // as on the owner's top-down photo of the open kit (22/10): a clear golden amber and a pale clear blue over the black
      // tray (the packshot's bright opaque #b16b2c / #277e95 is a composite), as the scene renders them through the glass
      liquid: liquidMat(...LIQ[kind]),
      neck: neckMat(0x1d1f1f, { roughness: 0.3, specularIntensity: 0.8 }, 'vneck'), cap: metalMat(0xf1f0ec, 0.5, 0.35, alU, 0),   // white plastic flip-off tops, as photographed
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
  // the tray's vessels as the photos 26 and 32 measure them (spec §1.5: a vial ≈ 0.21 W tall; the peel 1.53 of it, as on
  // the packshot), lying half sunk in the tray (their axes 0.075 under the walls' edges): in the kit's pose (photo A) the
  // sleeve's foot (v 0.337) hides the pH caps only, so the empty glass over the amber shows; the serum row under them
  // whole, then the print. The peel's foot a little above the serum's, its cap's top (v 0.385) under the circled 1 that
  // shows below the sleeve's edge
  const VH = 0.215, VZ = -0.075, PH_FOOT = 0.518, LS_FOOT = 0.755;
  const PEEL_U = 0.129, PEEL_FOOT = 0.714, PEEL_K = 1.53 * VH, PEEL_PROBE = 0.165;
  trayPeel.g.position.set(PEEL_U - 0.5, yv(PEEL_FOOT), VZ); trayPeel.g.scale.setScalar(PEEL_K);
  // the rows of five: one instanced draw per part (the glass, neck and cap of all ten; each kind's liquid and print)
  const ROWS = [0.317, 0.456, 0.595, 0.734, 0.873];
  const tvm = vialMats('ph', trayU), tvLs = { liquid: liquidMat(...LIQ.ls), ink: ink(lsInk, 0x0a0908) };
  const trayMats = Object.values(trayPeel.mats).filter(m => m.isMaterial).concat(Object.values(tvm).filter(m => m.isMaterial), [tvLs.liquid, tvLs.ink]);
  for (const m of trayMats.concat([trayGoldMat])) trayLight(m);
  trayLight(velvetMat, true);
  const inst = (geo, mat, rows, order) => {
    const m = new THREE.InstancedMesh(geo, mat, rows.length * 5); m.renderOrder = order; m.frustumCulled = false; trayG.add(m); let i = 0;
    for (const r of rows) for (const u of ROWS) m.setMatrixAt(i++, m4.compose(tmpP.set(u - 0.5, yv(r ? LS_FOOT : PH_FOOT), VZ), tmpQ, tmpS.setScalar(VH)));
    return m;
  };
  const tmpP = new V3(), tmpQ = new THREE.Quaternion(), tmpS = new V3();
  [[vialGlass, tvm.back, [0, 1]], [vialLiquid, tvm.liquid, [0]], [vialLiquid, tvLs.liquid, [1]], [vialNeck, tvm.neck, [0, 1]], [vialCap, tvm.cap, [0, 1]],
    [vialGlass, tvm.front, [0, 1]], [vialPrint, tvm.ink, [0]], [vialPrint, tvLs.ink, [1]]].forEach(([g, m, rows], j) => inst(g, m, rows, 112 + j));

  // ---- the line's light, flat to the camera in frame pixels (a plane at a depth; local x = px − 1200, y = 750 − py),
  // always behind the products and drawn before them: soft shapeless glows, nothing drawn
  let pxU = 1;   // device px per frame px
  // the glows add their colour (× their alpha, premultiplied in the shader). Drawn for a picture read back (the keys, the
  // phone stills, the kit picture: `still`) they keep a true alpha (it adds too), which un-premultiplies to the glow's own
  // champagne, not to lemon. Live their alpha is 0: the page composites them as added light, exactly. With an alpha of a
  // level or two, a compositor that truncates (headless Chromium's does) takes up to a level off every channel of the
  // page behind the canvas: round a faint glow, a ring below the backdrop, warm where its blue (the least) is lost first
  const ADD = { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
    blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor };
  const place = (g, D) => { at(1200, 750, D, g.position); g.quaternion.copy(lay.quaternion); g.scale.setScalar(world(1, D)); };
  const fx = new THREE.Group(); scene.add(fx); place(fx, DIST + 8);
  const hex3 = h => new V3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  // each glow is a quad over its own extent only (uB: x0, y0, x1, y1 in frame px; nothing has alpha outside it), so a
  // glow shades only the pixels it lights
  const QUAD_V = `uniform vec4 uB; varying vec2 vP;
    void main() { vP = mix(uB.xy, uB.zw, position.xy * 0.5 + 0.5); gl_Position = projectionMatrix * modelViewMatrix * vec4(vP.x - 1200.0, 750.0 - vP.y, 0.0, 1.0); }`;
  const flat = (frag, uniforms, order) => {   // a shader in frame px (vP)
    const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial(Object.assign({ vertexShader: QUAD_V, fragmentShader: frag,
      uniforms: Object.assign({ uB: { value: new THREE.Vector4() } }, uniforms), transparent: true, depthWrite: false, side: THREE.DoubleSide }, ADD)));
    m.renderOrder = order; m.visible = false; m.frustumCulled = false; fx.add(m); return m;
  };
  // soft spots: the glow behind the box (S1–S2), the light behind the three on S3 → S4, the current step's on S5 and S4's
  // backlight; the haze (S3 → S5). A gaussian (exp(−k q²)) that fades out over the outer 40 % of its ellipse with no slope
  // at its end: no edge, no disc, no rim. It is dithered by half a level (interleaved gradient noise), so on the 8-bit
  // canvas a faint glow does not band into flat ellipses and its colour is right on average (unrounded, the red of its
  // champagne would come up a level before the green and blue: a warm fringe)
  const SPOT_F = `uniform vec4 uS; uniform float uA, uK, uT; uniform vec3 uC; varying vec2 vP;
    void main() { vec2 q = (vP - uS.xy) / uS.zw; float r = length(q), a = uA * exp(-uK * r * r) * (1.0 - smoothstep(0.6, 1.0, r));
      float n = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) - 0.5;
      gl_FragColor = a > 0.0 ? max(vec4(uC * a, a) + n / 255.0, 0.0) * vec4(1.0, 1.0, 1.0, uT) : vec4(0.0); }`;
  const TRUE_A = { value: 1 };   // 1: a true alpha (a picture read back); 0: live, added light only
  const spot = (c, order, k = 4) => flat(SPOT_F, { uS: { value: new THREE.Vector4() }, uA: { value: 0 }, uK: { value: k }, uT: TRUE_A, uC: { value: hex3(c) } }, order);
  const setSpot = (m, cx, cy, rx, ry, a) => {
    const u = m.material.uniforms; u.uS.value.set(cx, cy, rx, ry); u.uB.value.set(cx - rx, cy - ry, cx + rx, cy + ry); u.uA.value = a; m.visible = a > 0.004;
  };
  // the box's glow: a broad soft light behind it, off its centre up and left (toward the key), so it shows past the left
  // and top edges and not at all past the right one: it does not follow the box's outline (no lit frame)
  const boxGlow = spot(0xd8c48a, 3, 2.5);
  const vSpots = [0, 1, 2].map(() => spot(0xd8c48a, 2)), backGlow = spot(0xd8c48a, 2), haze = spot(0xd8c48a, 1);
  const HAZE = [690, 750, 470, 420];   // the haze's ellipse (frame px: centre, radii): it thins before the frame's edges
                                       // and stays out of the copy (x > 1128)

  // ---- poses (frame px). The box { cx, cy: its front's centre, W: the front's width, yaw° (+: toward the copy), lift
  // (of W), a, D: depth }; a vessel { x: its axis, y: its foot, H: its height, a, D } (0 peel, 1 pH, 2 serum)
  const B = (cx, cy, W, D, lift = 0) => ({ cx, cy, W, yaw: 4, lift, a: 1, D });
  // the kit (photo A, opened a little further at the owner's word of 22/10 so the top row shows whole with its caps): the
  // sleeve slid up until its foot is at 52 % of the open box's height (0.877 / (1 + LIFT)), the box all but square to
  // the camera (1.5° toward the copy: both walls show their insides)
  const LIFT = 0.68;
  // S2 → S3: the closed box goes far behind the row, upper right of the peel, and out into the dark as the last vessel
  // clears it (at its true size beside them it would fill the frame; small and still there it read as a miniature)
  const BOX = [B(760, 790, 660, DIST + 1), B(745, 805, 607, DIST + 1), B(1000, 815, 200, DIST + 8), null, null,
    B(720, 930, 500, DIST + 1, LIFT)];
  const BOX_IN = B(720, 850, 200, DIST + 6);   // S5 → kit: from the depth
  const VS = (x, y, H) => ({ x, y, H });
  const ROW2 = [VS(760, 1010, 350), VS(570, 1010, 229), VS(400, 1010, 229)];
  const ROW3 = [VS(1025, 1120, 210), VS(915, 1120, 137), VS(820, 1120, 137)];
  // S5: the three larger in their row, all above frame y 700 (the page's step cards come up over the scene's lower part
  // while S5 is read), the peel's cap just clear of the top edge's fade (frame y 340)
  const ROW4 = [VS(960, 640, 300), VS(760, 640, 196), VS(560, 640, 196)];
  const OUT = [[0.25, 0.65], [0.4, 0.8], [0.55, 0.95]];   // S2 → S3: each one's way out from behind the box (the box settles by 0.4)
  const SIDE = 0.45;   // of its way: sideways behind the box until clear of its left edge; then out, forward, down to the row
  const STEP = [0.15, 0.32, 0.5];     // S5 → kit, while the page's step cards pass: step 1 current to f 0.15, 2 to 0.32, 3 to 0.5
  // the state, written in place on every frame (nothing allocated per frame)
  const ves = () => ({ x: 0, y: 0, H: 1, a: 0, D: DIST, cur: 0 });
  const ST = { box: { cx: 0, cy: 0, W: 1, yaw: 4, lift: 0, a: 0, D: DIST + 1 }, v: [ves(), ves(), ves()], glow: 0,
    vglow: 0, back: 0, haze: 0, zoom: 0 };
  const setBox = (o, s, a = 1) => { o.cx = s.cx; o.cy = s.cy; o.W = s.W; o.yaw = s.yaw; o.lift = s.lift; o.D = s.D; o.a = a; return o; };
  const mixBox = (o, a, b, s) => { o.cx = lerp(a.cx, b.cx, s); o.cy = lerp(a.cy, b.cy, s); o.W = lerp(a.W, b.W, s); o.D = lerp(a.D, b.D, s); o.yaw = lerp(a.yaw, b.yaw, s); o.lift = lerp(a.lift, b.lift, s); return o; };
  const setV = (o, s, a = 1, D = DIST) => { o.x = s.x; o.y = s.y; o.H = s.H; o.a = a; o.D = D; o.cur = 0; return o; };
  const mixV = (o, a, b, s) => { o.x = lerp(a.x, b.x, s); o.y = lerp(a.y, b.y, s); o.H = lerp(a.H, b.H, s); return o; };
  const boxBack = b => b.D + world(b.W, b.D) * BD;   // the depth of the box's back

  function story(p) {   // the state at story position p
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST, b = st.box;
    setBox(b, BOX[0], 0); for (let i = 0; i < 3; i++) setV(st.v[i], ROW2[i], 0);
    st.glow = st.vglow = st.back = st.haze = st.zoom = 0;
    if (k === 0) {   // S1 → S2: the box steps back (0.92), still closed, its colours unchanged; the glow behind it to 40 %
      mixBox(b, BOX[0], BOX[1], smooth(0, 1, f)); b.a = 1;
      st.glow = 1 - 0.6 * smooth(0, 0.6, f);
    } else if (k === 1) {   // S2 → S3: the box goes deeper, to the right; the three come out from behind it one by one (not out of
      // it): each starts hidden behind the box's back and takes its opacity there, moves sideways (still behind) until its
      // silhouette clears the box's left edge, and only then comes forward and down to its place in the row: it never
      // crosses the box's front while inside the box's outline
      mixBox(b, BOX[1], BOX[2], smooth(0, 0.4, f)); b.a = 1 - smooth(0.75, 1, f);   // gone once the serum is clear of it
      st.glow = 0.4 * (1 - smooth(0, 0.4, f));
      const left = b.cx - b.W * 0.535 - 12;   // the box's silhouette (its left side shows: yaw, sway)
      for (let i = 0; i < 3; i++) {
        const s = smooth(OUT[i][0], OUT[i][1], f), o = st.v[i], e = ROW2[i], y0 = b.cy + b.W * 0.44;
        const Db = Math.max(boxBack(b) + 0.6, e.H * DIST / (0.86 * b.W));   // behind the box, deep enough to hide whole
        const xc = left - e.H * DIST / Db * H_W[i] / 2;   // its axis when its right edge is clear of the box (at Db)
        const sa = smooth(0, SIDE, s), sb = smooth(SIDE, 1, s);
        o.x = lerp(lerp(b.cx + 40 * (1 - i), xc, sa), e.x, sb); o.y = lerp(y0, e.y, sb) - 60 * Math.sin(Math.PI * sb);
        o.D = lerp(Db, DIST, sb); o.H = e.H; o.a = smooth(0, 0.15, s); o.cur = 0;   // H: its size at the row's depth
      }
    } else if (k === 2) {   // S3 → S4 (the line's light): a soft champagne light comes up behind the three (their colours stay)
      // and a shapeless haze; the three go small, low right, into a backlight (the box has gone)
      st.haze = smooth(0.4, 0.9, f);
      const g = smooth(0.45, 1, f);
      for (let i = 0; i < 3; i++) mixV(setV(st.v[i], ROW2[i]), ROW2[i], ROW3[i], g);
      st.vglow = smooth(0, 0.2, f) * (1 - smooth(0.6, 1, f)); st.back = smooth(0.45, 1, f);
    } else if (k === 3) {   // S4 → S5: the haze sinks; the three rise and grow in their row; the backlight goes
      st.haze = 1 - smooth(0.2, 0.5, f);
      const g = smooth(0.3, 0.8, f);
      for (let i = 0; i < 3; i++) mixV(setV(st.v[i], ROW3[i]), ROW3[i], ROW4[i], g);
      st.back = 1 - smooth(0.3, 0.6, f);
      st.v[0].cur = smooth(0.82, 1, f);   // step 1 is the current one as S5 settles
    } else {   // S5 → kit: the three hold while the page's step cards pass (to f ≈ 0.5), the current step lit from behind by
      // the line's light (1, 2, 3 in turn: the product itself is never dimmed); the closed box comes forward from the
      // depth; the three step back to its middle, behind it, and dissolve; the sleeve lifts straight up LIFT W (photos 26
      // and 32) as the camera steps in to the box (lens). No glow round the open box: the card's picture is cut to what
      // has alpha, and the kit is the product alone
      const g = smooth(0.5, 0.7, f); mixBox(b, BOX_IN, BOX[5], g); b.lift = LIFT * smooth(0.72, 0.95, f); b.a = smooth(0.5, 0.6, f);
      st.zoom = smooth(0.72, 0.95, f);
      const r = smooth(0.55, 0.75, f), Db = boxBack(b) + 0.4;
      for (let i = 0; i < 3; i++) {
        const o = setV(st.v[i], ROW4[i], 1 - r); o.x = lerp(ROW4[i].x, b.cx, r); o.y = lerp(ROW4[i].y, b.cy + b.W * 0.3, r); o.D = lerp(DIST, Db, r);
        o.cur = (i ? smooth(STEP[i - 1] - 0.03, STEP[i - 1] + 0.03, f) : 1) * (1 - smooth(STEP[i] - 0.03, STEP[i] + 0.03, f));
      }
    }
    if (p >= 5) {   // the kit: exactly the pose, nothing in flight
      setBox(b, BOX[5], 1); st.zoom = 1; for (let i = 0; i < 3; i++) st.v[i].a = 0;
    }
    return st;
  }

  // ---- the kit's camera (photo A was taken by hand, close to the kit): over the sleeve's lift it steps in along its line
  // of sight to the box, turns to stand square before it and widens (LENS_FOV), the box kept in place and size in the
  // frame (its front's scale; its centre's frame pixel, by shifting the picture as a shift lens does, so its edges stay
  // upright and square). The deeper parts then fall back in perspective: the base's walls show their insides either
  // side, the band's top edge below, the tray lies deep. The box faces the camera as before (on the same line), and the
  // foil keeps the light it had (eyeFixed). Only the box is drawn then (the glows are out, the three gone)
  const LENS_FOV = 50, ndc0 = new V3(), ndc1 = new V3(), rayL = new V3(), axC = new V3(), YAX = new V3(0, 1, 0);
  const qY = new THREE.Quaternion(), qI = new THREE.Quaternion();
  function lens(z, P0) {
    camera.position.copy(lay.position); camera.quaternion.copy(lay.quaternion); camera.fov = FOV;
    camera.updateProjectionMatrix(); camera.updateMatrixWorld();
    if (z > 1e-4) {
      ndc0.copy(P0).project(camera);
      toCam.copy(lay.position).sub(P0).applyQuaternion(layInv); const phi = Math.atan2(toCam.x, toCam.z);   // as facing()
      const d0 = rayL.copy(P0).sub(lay.position).dot(fwd), L = rayL.length(); rayL.divideScalar(L);
      const c1 = rayL.dot(axC.set(0, 0, -1).applyQuaternion(qY.setFromAxisAngle(YAX, phi).premultiply(lay.quaternion)));   // square to the box
      const s = lerp(L, d0 * TAN / (Math.tan(rad(LENS_FOV / 2)) * c1), z);   // its distance along the line of sight
      camera.quaternion.copy(lay.quaternion).multiply(qY.setFromAxisAngle(YAX, phi * z));
      camera.position.copy(P0).addScaledVector(rayL, -s);
      const c = rayL.dot(axC.set(0, 0, -1).applyQuaternion(camera.quaternion));
      camera.fov = 2 * THREE.MathUtils.radToDeg(Math.atan(d0 * TAN / (s * c)));
      camera.updateProjectionMatrix(); camera.updateMatrixWorld();
      ndc1.copy(P0).project(camera); const e = camera.projectionMatrix.elements;   // the shift: the box's centre back on its pixel
      e[8] -= ndc0.x - ndc1.x; e[9] -= ndc0.y - ndc1.y; camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
    }
    qI.copy(camera.quaternion).invert();
    EYE.value.copy(camera.position).sub(lay.position).applyQuaternion(qI);   // the story camera's eye, in the drawn camera's view
    TOLAY.value.setFromMatrix4(m4.makeRotationFromQuaternion(qY.copy(camera.quaternion).premultiply(layInv)));   // drawn view → story view
  }

  // ---- applying a state
  const tmp = new V3(), last = { t: 0 };
  const DEPTH = new Float32Array(3), RANK = [0, 1, 2], farFirst = (i, j) => DEPTH[j] - DEPTH[i];
  const GLOW_A = 0.5;   // the box's glow at its peak (hidden behind the box): S1; S2 at 40 % of it
  const SOLID = ['liquid', 'neck', 'cap'];   // the heroes' parts that write depth once opaque
  let lastW = 1;   // the box's front width drawn (with its breath): the ΔE probes (state()) are placed by it
  function pose(p, t, still) {
    const st = story(p), live = still ? 0 : 1 - smooth(4.85, 5, p), ph = phone.matches;
    TRUE_A.value = still ? 1 : 0;
    const b = st.box;
    // the box: its front parallel to the picture's vertical, turned to face the camera, then toward the copy (4°; the idle
    // sway ±1.5°: within 5.5°, its sides are not photographed); on S1 it breathes ±1.5 %
    box.visible = b.a > 0.004;
    const breathe = 1 + 0.015 * Math.sin(t * 0.9) * live * (1 - smooth(0.6, 1, p));
    if (box.visible) {
      const S = world(b.W, b.D) * breathe;
      at(b.cx, b.cy, b.D, box.position); box.scale.setScalar(S); box.quaternion.copy(lay.quaternion);
      lens(st.zoom, box.position);
      box.rotateY(facing(box) + rad(b.yaw + 1.5 * Math.sin(t * 0.4 + 1) * live));
      sleeve.position.y = b.lift; trayG.visible = b.lift > 0.004;   // the contents only once the sleeve lifts
      lidGap.visible = b.lift < 0.002;
      for (const m of boxMats) { m.opacity = b.a; m.depthWrite = b.a > 0.99 && m !== trayGoldMat; }
    } else lens(0);
    if (trayG.visible) {   // the tray's contents take the box's opacity; the sleeve's foot shades them (trayLight)
      for (const m of trayMats) m.opacity = b.a;
      capFaceSet(trayU, box); BOXINV.value.copy(box.matrixWorld).invert(); LIDY.value = yv(LIDV) + b.lift;
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
      flakeMin = 1.5 / Math.max(1, st.v[0].H * DIST / st.v[0].D * pxU);
      setFlakes(heroes[0].flakes, t, flakeMin); heroes[0].flakes.count = ph ? 460 : NF;
    }
    // the glows: behind everything shown
    let Dfar = 9;
    if (box.visible) Dfar = Math.max(Dfar, boxBack(b));
    for (let i = 0; i < 3; i++) if (heroes[i].g.visible) Dfar = Math.max(Dfar, st.v[i].D + 1);
    place(fx, Dfar + 1);
    const W = b.W * breathe; lastW = W;
    // the box's glow, live only as the haze (the keys and the phone stills are cut to what has alpha): its centre 0.1 W
    // left of the box's and 0.05 W above, its ellipse 0.65 × 0.6 W, so it ends short of the copy (S1: x ≤ 1123 < 1128)
    // and of the frame's top fade (y ≥ 361)
    setSpot(boxGlow, b.cx - 0.1 * W, b.cy - 0.05 * W, 0.65 * W, 0.6 * W, box.visible && !still ? GLOW_A * st.glow * b.a : 0);
    for (let i = 0; i < 3; i++) {   // the light behind the three (S3 → S4); the current step's, smaller, kept left of the copy (S5)
      const s = st.v[i];
      if (s.cur > 0.004) setSpot(vSpots[i], s.x, s.y - s.H * 0.45, s.H * H_W[i] * 1.15, s.H * 0.62, 0.4 * s.cur * s.a);
      else setSpot(vSpots[i], s.x, s.y - s.H * 0.5, s.H * H_W[i] * 1.6, s.H * 0.75, 0.45 * st.vglow * s.a);
    }
    setSpot(backGlow, 930, 1060, 230, 110, 0.5 * st.back);
    setSpot(haze, HAZE[0], HAZE[1], HAZE[2], HAZE[3], still ? 0 : 0.14 * st.haze);   // live only (the keys are cut to what has alpha)
    last.t = t;   // QA (state()): the flakes outside the liquid at this time
  }
  function probes() {   // QA: the probe points of the ΔE checks (frame px) in the last pose drawn (state() only: no garbage per frame)
    const b = ST.box, v = ST.v, W = lastW, tray = trayG.visible && b.lift > LIFT - 0.01;
    const pt = (o, fr) => (o.a > 0.99 ? [o.x, o.y - o.H * DIST / o.D * fr] : null);   // fr of its height above its foot
    return { foil: box.visible && b.a > 0.99 ? [b.cx, b.cy - W * (0.2 + b.lift)] : null,
      // the peel's on its clear liquid under the label's last line (0.205 from the foot with its descenders)
      peel: pt(v[0], PEEL_PROBE), ph: pt(v[1], 0.15), ls: pt(v[2], 0.15),
      // the tray's on the vessels' fronts, projected as drawn (the kit's lens)
      trayPeel: tray ? toFrame(PEEL_U - 0.5, yv(PEEL_FOOT) + PEEL_K * PEEL_PROBE, VZ + PEEL_K * DB / 2) : null,
      trayPh: tray ? toFrame(ROWS[2] - 0.5, yv(PH_FOOT) + 0.15 * VH, VZ + VH * R) : null,
      trayLs: tray ? toFrame(ROWS[2] - 0.5, yv(LS_FOOT) + 0.15 * VH, VZ + VH * R) : null };
  }
  const VO = [0, 0, 2400, 1500], pv = new V3();   // the canvas's box in frame px (fit())
  function toFrame(x, y, z) {   // a point in the box's units → frame px
    pv.set(x, y, z).applyMatrix4(box.matrixWorld).project(camera);
    return [r1(VO[0] + (pv.x + 1) / 2 * VO[2]), r1(VO[1] + (1 - pv.y) / 2 * VO[3])];
  }
  function capFaceSet(U, o) {   // a metal's reflection turned with the object as it faces the camera
    o.updateMatrixWorld(); tmp.setFromMatrixPosition(o.matrixWorld);
    toCam.copy(camera.position).sub(tmp).applyQuaternion(layInv);
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
    pxU = pr * view.cover.w / 2400;   // device px per frame px: the flakes keep ≥ 1.5 device px
    EDGE.value.set((view.box.y - view.cover.y) * 2400 / view.cover.w, canvas.height, pxU);   // the frame's top edge
    const k = 2400 / view.cover.w; VO[0] = (view.box.x - view.cover.x) * k; VO[1] = (view.box.y - view.cover.y) * k; VO[2] = view.box.w * k; VO[3] = view.box.h * k;
  }
  // the kit (from p 4.85, where the motion fades out, and every still) carries the small print: it draws at the screen's
  // full density whatever the pace's cap, and the pace takes no measure there. A pose that does not move (p ≥ 5, a
  // still) is drawn once: drawing it again would change nothing
  let lastId = '';
  function render(p, view) {
    const fixed = view.still || p >= 5, kitAt = fixed || p >= 4.85;
    pr = kitAt ? full(view) : Math.min(full(view), cap);
    const id = fixed ? [p, view.box.x, view.box.y, view.box.w, view.box.h, view.cover.x, view.cover.y, view.cover.w, pr, version].join() : '';
    if (id && id === lastId) return;
    lastId = id; fit(view, pr); pose(p, view.still ? 0 : view.t, view.still); renderer.render(scene, camera); renders++;
  }
  function draw(p, view) { pace(performance.now(), view.still || p >= 4.85); lastP = p; lastView = view; render(p, view); }
  let kits = 0;   // kit pictures rendered (QA: none on a phone, none for a toolbar)
  function kit(view) {   // the kit pose rendered once into a picture (the offer card, the flight into it), then the current pose again
    kits++;
    fit(view, view.dpr); pose(5, 0, true); renderer.render(scene, camera); lastId = '';
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
      haze: r2(haze.visible ? haze.material.uniforms.uA.value : 0),
      glow: r2(boxGlow.visible ? boxGlow.material.uniforms.uA.value : 0), flakes: { n: heroes[0].g.visible ? heroes[0].flakes.count : 0, outside: heroes[0].g.visible ? flakesOutside(last.t) : 0 },
      probes: probes() };
  };
  return { draw, kit, dispose, state, animated: true };
}
