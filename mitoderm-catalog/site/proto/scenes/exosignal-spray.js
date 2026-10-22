// EXOSIGNAL SPRAY live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D
// scene, as the approved sample EXOTECH GEL (scenes/exotech-gel.js) and its line's EXOSIGNAL HAIR (scenes/exosignal-hair.js).
// The engine keeps the story geometry (the cover-fitted 16:10 frame, the run's box, the phone stage, the kit card); this
// module draws the pose for the story position into the box. Objects are placed by frame pixel (2400×1500); the only
// packshot, site/img/exosignal-spray.png (400×300, a mock-up), gives the box and the bottle's silhouettes and the kit's
// composition: the tall matte black box seen square on, the bottle right of it with a gap of 0.184 of the box's width.
// The story (site/story3d.json, as specified for the page, under the owner's rule of 22/10: the scene shows only what
// exists — the products as photographed, the spray's mist as loose clouds of droplets, a soft shapeless glow; no thread,
// flashes, lines, rings or other drawn shapes): S1 the packshot, a still thin mist far behind the pair (one soft cloud),
// none near the cap; S1 → S2 the camera comes close, the bottle's top leaves the frame's top edge and a cloud comes in
// from there and opens into a loose cloud low behind the bottle, which stands by the EXOSIGNAL HAIR packshot (the
// line's sign; on a phone the packshot on top, the bottle and its cloud below it); S3 close again, the top over the
// edge: one cloud comes in through it, drifts down and left and parts into three; S4 the three settle into a soft haze,
// a few drops in it melting; S5 the bottle passes right to left and back with its top cut by the edge, small clouds fall
// from beyond the edge behind it and melt where they come to rest; the box and the HAIR packshot stand far behind, all
// above the page's step cards; S6–S7 once the cards have gone the box comes forward, the bottle turns once to +30° and
// back and stands by it: the packshot's pose (the kit card), a warm gold backlight behind the pair.
// Nothing is opened: no photo shows the sprayer under the cap, so the cap stays on and the mist always comes from
// beyond the frame's edge. The scene's frame is the page's scene box (frame y 285 at its top: the canvas ends there),
// so the bottle leaves it by fading over the edge's last 48 px, as the mist does. The product keeps its print's colours
// (emissive ≈ 85 % + neutral shading, toneMapped off); the line's gold lives only around it (the droplets' rims, the
// kit's glow). No text is drawn but the package's own print (design/exosignal-spray/make_textures.py).
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

  // the camera looks down 3° (the packshot shows the front square on: neither the box's top nor its foot); `lay` is the
  // same camera without the box's view offset, for placing objects by their frame pixels
  const FOV = 20, EL = rad(3), DIST = 14;
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

  // ---- light: a neutral studio for reflections (PMREM), as the HAIR scene's: dark above and below, an even horizon,
  // two tall narrow softboxes either side of the camera, rims behind; the key from the top left (the packshot's cap is
  // lighter on its left)
  function makeEnv(cap) {
    const pm = new THREE.PMREMGenerator(renderer), room = new THREE.Scene();
    const dome = new THREE.SphereGeometry(30, 48, 32), col = [], c = new THREE.Color();
    for (let i = 0; i < dome.attributes.position.count; i++) {
      const y = dome.attributes.position.getY(i) / 30;   // −1 floor … 1 ceiling
      c.setRGB(1, 1, 1.02).multiplyScalar(0.05 + 0.18 * Math.exp(-(y * y) / 0.06)); col.push(c.r, c.g, c.b);
    }
    dome.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    room.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const panel = (i, x, y, z, w, h, tint = [1, 1, 1]) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(...tint).multiplyScalar(i), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, y, 0); room.add(m);
    };
    if (!cap) {
      panel(5, -5.7, 1, 8.2, 2.4, 9); panel(2.5, 6.4, 1, 7.7, 1.6, 9);   // ±35–40° from the camera, the left one the key
      panel(2.5, -9, 1.5, -7, 2.5, 9); panel(2, 9, 2, -7, 2.5, 9);       // rims from behind
    } else {   // the cap's own room, as its packshot shows it lit: a broad light front (its middle the brightest), a softer
      panel(1.1, 0, 1, 12, 13, 14); panel(0.85, -11, 1, 1, 9, 14);     // one on the left (its left third light), the right dark
      panel(0.25, 8, 1.5, -8, 3, 10);                                   // a faint rim behind right
      panel(0.24, 10.5, 1, 4.5, 8, 14, [1, 0.55, 0.28]);                // a dim warm bounce at 50–85° right: the shadow third
    }                                                                   // bronze (#815c2f on the packshot), not olive
    const rt = pm.fromScene(room, 0.02); pm.dispose();
    room.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    return rt;   // its target: disposing that frees the framebuffer too, not only the texture
  }
  let roomEnv = makeEnv(false), capEnv = makeEnv(true);
  scene.environment = roomEnv.texture;
  // after a lost context three.js restores image textures, not the rendered environment: rebuild it, and have the
  // engine redraw (the kit picture too), also under reduced motion
  const restored = () => {
    const old = [roomEnv, capEnv]; roomEnv = makeEnv(false); capEnv = makeEnv(true); scene.environment = roomEnv.texture;
    capMat.envMap = capEnv.texture; old.forEach(t => t.dispose()); sizeW = -1;
    version++; if (onLoad) onLoad();
  };
  canvas.addEventListener('webglcontextrestored', restored);
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(-4, 6, 6); scene.add(key);

  // ---- textures: the typeset print (make_textures.py) and the EXOSIGNAL HAIR packshot (S2, S5), as it is
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy();
  const tex = (name, srgb) => {
    const t = new THREE.TextureLoader().load(new URL(`img/exosignal-spray-3d/${name}`, base).href, () => {
      t.needsUpdate = true; if (++loaded === 4) { version++; if (onLoad) onLoad(); }   // the engine redraws the kit picture
    });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const faceTex = tex('box-face.png', true), metalTex = tex('box-metal.png'), printTex = tex('bottle-print.png'), hairTex = tex('hair.webp', true);

  // ---- materials. The product in its print's colours: emissive 0.85 of the colour plus a neutral shading (a diffuse
  // 0.2 of it under the key and the room), not tone mapped; the foil a satin metal (roughness 0.28). Nothing on the
  // product is dimmed or masked: it comes and goes by opacity only
  const SHADE = 0.2;
  const P = (hex, opts = {}) => new THREE.MeshPhysicalMaterial(Object.assign({ color: new THREE.Color(hex).multiplyScalar(SHADE), emissive: hex,
    emissiveIntensity: 0.85, roughness: 0.7, specularIntensity: 0.3, toneMapped: false, transparent: true }, opts));
  const facade = P(0xffffff, { color: new THREE.Color(SHADE, SHADE, SHADE), map: faceTex, emissiveMap: faceTex, metalnessMap: metalTex,
    roughnessMap: metalTex, metalness: 1, roughness: 0.65, specularIntensity: 0.08, envMapIntensity: 0.7 });   // the foil's F0 its colour
  const paper = P(0x131417, { specularIntensity: 0.08 });   // the box's other sides: the same black paper, no print
  // the scene box's top edge: the canvas ends at frame y 285 on the page, so where the story brings the camera close
  // (S1 → S2, S3, the S5 passes) the bottle leaves the frame there, fading over 292…340 as the mist does (the frame y
  // of a fragment: the canvas top's frame y + its buffer row / device px per frame px; set in fit())
  const EDGE = { value: new THREE.Vector3(0, 1, 1) }, EDGE_Y0 = 292, EDGE_Y1 = 340;
  const edgeFade = sh => {
    sh.uniforms.uEdge = EDGE;
    sh.fragmentShader = 'uniform vec3 uEdge;\n' + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      gl_FragColor.a *= smoothstep(${EDGE_Y0}.0, ${EDGE_Y1}.0, uEdge.x + (uEdge.y - gl_FragCoord.y) / uEdge.z);`);
  };
  // the frosted glass: as photographed on black (#a9a7a5) where it faces the camera, opaque there; toward the limb it
  // darkens (≈ 12 % on the key's side, 22 % on the shadow side, as owner photo #2 falls off) under a thin lighter edge
  // (the glass's thickness); the rounded foot and the shoulder are thick glass: a little lighter and more translucent;
  // Fresnel lets its rim show the page a little (no transmission: on a transparent canvas it would not see the page's
  // smoke, and a phone pays a pass for it). Facing the camera within 35° nothing changes (ΔE target: θ −35°, s 0.45)
  const glass = P(0xa9a7a5, { roughness: 0.6, specularIntensity: 0.25 });
  glass.onBeforeCompile = sh => {
    edgeFade(sh);
    sh.vertexShader = 'varying float vBy;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vBy = position.y;');
    sh.fragmentShader = 'varying float vBy;\n' + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float c = clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0), F = pow(1.0 - c, 5.0);
        float limb = smoothstep(0.82, 0.10, c) * mix(0.12, 0.22, smoothstep(-0.3, 0.6, normal.x));
        float rim = 0.15 * smoothstep(0.36, 0.06, c);
        float band = max(1.0 - smoothstep(0.004, 0.03, vBy), smoothstep(0.618, 0.65, vBy));
        gl_FragColor.rgb *= pow((1.0 - limb) * (1.0 + 0.12 * band) + rim, 2.2);   // an sRGB factor, in linear light
        gl_FragColor.a *= (1.0 - 0.25 * F) * (1.0 - 0.06 * band); }`);
  };
  glass.customProgramCacheKey = () => 'spray-glass';
  const ink = P(0x0d0e12, { alphaMap: printTex, depthWrite: false, roughness: 0.45, polygonOffset: true, polygonOffsetFactor: -2 });
  ink.onBeforeCompile = edgeFade; ink.customProgramCacheKey = () => 'spray-ink';
  // the cap: polished gold metal (the packshot's thirds: #c1a35d left, #d1b76e middle, #77542b right), its ribs in the
  // geometry, in its own room (makeEnv(true)); its reflection is turned with the bottle as it faces the camera (uFace),
  // so it reads the same anywhere in the frame (a little of its colour as emission: never black where it mirrors the dark)
  const CAPC = 0xe0c27a, capFace = { value: new THREE.Matrix3() };
  const capMat = new THREE.MeshPhysicalMaterial({ color: CAPC, metalness: 1, roughness: 0.26, emissive: CAPC, emissiveIntensity: 0.08,
    envMap: capEnv.texture, envMapIntensity: 1, toneMapped: false, transparent: true });
  capMat.onBeforeCompile = sh => {
    edgeFade(sh); sh.uniforms.uFace = capFace;
    sh.fragmentShader = 'uniform mat3 uFace;\n' + sh.fragmentShader.replace('#include <envmap_physical_pars_fragment>', THREE.ShaderChunk.envmap_physical_pars_fragment
      .replace('reflectVec = inverseTransformDirection( reflectVec, viewMatrix );', 'reflectVec = uFace * inverseTransformDirection( reflectVec, viewMatrix );'));
  };
  capMat.customProgramCacheKey = () => 'spray-cap';
  const upL = new V3(0, 1, 0).applyQuaternion(lay.quaternion), m4 = new THREE.Matrix4();

  // ---- the bottle, height 1 (scaled by HB): a lathe of the mock-up's silhouette (243.5 px tall, 39.15 wide: radius
  // 0.0804; the cap 0.342 of the height, 0.907 of the body's width, flat on top, rounded 0.008; the body's foot
  // rounded 0.012); the print a cylinder band just outside the glass (θ −60…+60°, s 0.08…0.90 of the body)
  const V2 = (r, h) => new THREE.Vector2(r, h);
  const R = 0.0804, RC = 0.0729, BODY = 0.658, HB = 1.2, RW = R * HB;
  const arc = (cx, cy, r, a0, a1, n) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return V2(cx + r * Math.cos(a), cy + r * Math.sin(a)); });
  const bodyGeo = new THREE.LatheGeometry([V2(0, 0)].concat(arc(R - 0.012, 0.012, 0.012, -Math.PI / 2, 0, 8),
    arc(R - 0.003, BODY - 0.003, 0.003, 0, Math.PI / 2, 4), [V2(RC * 0.97, BODY)]), 128);
  const capProfile = [V2(RC * 0.97, BODY), V2(RC, BODY + 0.002)].concat(arc(RC - 0.008, 1 - 0.008, 0.008, 0, Math.PI / 2, 8), [V2(0, 1)]);
  const capGeo = new THREE.LatheGeometry(capProfile, 360, Math.PI);   // the seam behind
  {   // the ribs: about 60 round the cap (their count is not on any photo), a ripple of the radius on its wall
    const p = capGeo.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), z = p.getZ(i), y = p.getY(i), r = Math.hypot(x, z);
      if (r < RC * 0.99 || y > 1 - 0.008 || y < BODY + 0.002) continue;
      const k = 1 + 0.0035 * Math.cos(60 * Math.atan2(x, z)); p.setX(i, x * k); p.setZ(i, z * k);
    }
    capGeo.computeVertexNormals();
  }
  const S0 = 0.08, S1 = 0.90, RP = R + 0.0004;
  const printGeo = new THREE.CylinderGeometry(RP, RP, (S1 - S0) * BODY, 160, 1, true, rad(-60), rad(120)).translate(0, BODY * (1 - (S0 + S1) / 2), 0);
  const bottle = new THREE.Group(); scene.add(bottle); bottle.scale.setScalar(HB);
  const bParts = [[bodyGeo, glass], [printGeo, ink], [capGeo, capMat]].map(([g, m]) => { const x = new THREE.Mesh(g, m); bottle.add(x); return x; });
  const bottleMats = [glass, ink, capMat];
  const KB = HB * 750 / TAN;   // the bottle's silhouette H px tall stands at depth KB / H

  // ---- the box: the front 118.2 : 297.1 (as on the mock-up), its depth unknown: square in section
  const BWr = 118.2 / 297.1, BD = BWr, box = new THREE.Group(); scene.add(box);
  const bxParts = [];
  const face = (geo, mat, x, y, z, rx, ry, layer) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, 0); m.userData.layer = layer; box.add(m); bxParts.push(m); return m; };
  face(new THREE.PlaneGeometry(BWr, BD), paper, 0, 0.5, -BD / 2, -Math.PI / 2, 0, 0);
  face(new THREE.PlaneGeometry(BWr, BD), paper, 0, -0.5, -BD / 2, Math.PI / 2, 0, 0);
  face(new THREE.PlaneGeometry(BD, 1), paper, -BWr / 2, 0, -BD / 2, 0, -Math.PI / 2, 0);
  face(new THREE.PlaneGeometry(BD, 1), paper, BWr / 2, 0, -BD / 2, 0, Math.PI / 2, 0);
  face(new THREE.PlaneGeometry(BWr, 1), paper, 0, 0, -BD, 0, Math.PI, 0);
  face(new THREE.PlaneGeometry(BWr, 1), facade, 0, 0, 0, 0, 0, 1);
  const boxMats = [facade, paper];
  const HX = HB / 0.8195, KX = HX * 750 / TAN;   // the bottle is 0.8195 of the box's height; the front h px tall at KX / h
  box.scale.setScalar(HX);

  // ---- flat to the camera in frame pixels (a plane at a depth; local x = px − 1200, y = 750 − py), always behind the
  // products and drawn before them: the mist, the HAIR packshot, the kit's glow (gold of the HAIR line only)
  const pxU = { value: 1 };   // device px per frame px
  // the glow adds its colour (× its alpha) and keeps a true alpha (it adds too): a picture read back (the keys, the
  // phone stills, the kit picture) un-premultiplies to the glow's own gold, where one-factor alpha (a²) clipped to lemon
  const ADD = { blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.SrcAlphaFactor, blendDst: THREE.OneFactor,
    blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor };
  const place = (g, D) => { at(1200, 750, D, g.position); g.quaternion.copy(lay.quaternion); g.scale.setScalar(world(1, D)); };
  const plane = D => { const g = new THREE.Group(); scene.add(g); place(g, D); return g; };
  const hex3 = h => new THREE.Vector3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  const SPOT_F = `uniform vec3 uC; uniform float uOpacity; varying vec2 vUv;
    void main() { vec2 q = vUv * 2.0 - 1.0; float r2 = dot(q, q); gl_FragColor = vec4(uC, uOpacity * exp(-3.0 * r2) * (1.0 - smoothstep(0.5, 1.0, r2))); }`;
  const spotMat = c => new THREE.ShaderMaterial(Object.assign({ vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: SPOT_F, transparent: true, depthWrite: false, side: THREE.DoubleSide, uniforms: { uC: { value: hex3(c) }, uOpacity: { value: 0 } } }, ADD));
  const spot = (parent, c, order) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), spotMat(c)); m.renderOrder = order; m.visible = false; parent.add(m); return m; };
  const setSpot = (m, cx, cy, rx, ry, a) => { m.position.set(cx - 1200, 750 - cy, 0); m.scale.set(rx, ry, 1); m.material.uniforms.uOpacity.value = a; m.visible = a > 0.004; };

  // the planes, placed every frame behind the farthest product: the HAIR packshot, the mist; the kit's glow just behind
  // the box
  const hp = plane(DIST), fx = plane(DIST), gb = plane(DIST);
  const glowBox = spot(gb, 0xc9a24b, 3);
  const hairBoard = new THREE.Mesh(new THREE.PlaneGeometry(1, 714 / 1087).translate(0, 357 / 1087, 0),
    new THREE.MeshBasicMaterial({ map: hairTex, transparent: true, depthWrite: false, toneMapped: false }));
  hairBoard.renderOrder = 2; hp.add(hairBoard);

  // S2: the loose cloud low behind the bottle (centre, spread px); on a phone (story3d's mobile layout) the HAIR packshot
  // is 60 % of the stage's width on top (its words readable), the bottle and its cloud below it at the right
  const HAZE2 = [700, 900, 190, 95], HAZE2_PH = [990, 860, 115, 150];
  // S5 keeps above the page's three step cards ("along the bottom") while p = 4 is held: their top edge comes up to
  // frame y ≈ 830 on 1440×900 and ≈ 720 on 1920×1080 (any 16:9 screen) before the story moves on (1050 / 920 at the
  // reading position), so everything of S5 stays above y 700: the bottle's feet on its passes (P1, P2), the small clouds
  const P1 = 600, P2 = 680;

  // The kit is the packshot (box x 111.1…230.4 mean 171.1, y 1.5…298.6; the bottle's axis 271.75, foot 296.24, 243.46
  // tall) scaled ×2.558 (the box 760 px) round the composition's centre to (700, 750); S1 the same ×2.356 (the box 700
  // px), its foot at 1140
  const PK = { bx: 171.1, by0: 1.5, bh: 297.1, ax: 271.75, af: 296.24, ah: 243.46, x0: 112.0, x1: 291.32 };
  const packPose = (h, cx, cy) => {   // the packshot at box height h, the composition's centre at (cx, cy)
    const k = h / PK.bh, mx = (PK.x0 + PK.x1) / 2, my = PK.by0 + PK.bh / 2;
    return [{ cx: cx + (PK.bx - mx) * k, cy, h, a: 1 }, { x: cx + (PK.ax - mx) * k, y: cy + (PK.af - my) * k, H: PK.ah * k, yaw: 0, a: 1 }];
  };
  const [BOX5, BOT5] = packPose(760, 700, 750);
  const [BOX0, BOT0] = (() => { const [b, o] = packPose(700, 0, 0), dx = 620 - b.cx, dy = 790 - b.cy; return [{ ...b, cx: 620, cy: 790 }, { ...o, x: o.x + dx, y: o.y + dy }]; })();
  const capBox = o => { const W = o.H / 6.22, top = o.y - o.H; return [o.x - W * 0.46, top, o.x + W * 0.46, top + 0.342 * o.H]; };   // QA's cap frame
  const CAP0 = capBox(BOT0);   // S1's cap, for the S1 mist (and its JS twin)

  // ---- the mist: one instanced quad per droplet, all motion in the vertex shader (no matrices on the CPU): each
  // droplet's place is a mix of six layouts, weighted by the story and by its own opacity in each (so a droplet only
  // in one layout fades where it is, one in two flies between them): 0 the still mist of S1, 1 the cloud coming in from
  // above, 2 the loose cloud of S2, 3 the cloud parting into three, 4 the haze of S4 with its melting drops, 5 the small
  // clouds falling in S5. Every layout is a loose cloud: Gaussian, its spread varied per droplet (no edge, no line or
  // ring). Each layout uses its own share of the droplets (by seed); a phone draws half
  const NM = 1400, rng = (s => () => { s |= 0; s = s + 0x6d2b79f5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; })(20261022);
  const SEED = new Float32Array(NM * 4), GAU = new Float32Array(NM * 2), SZ = new Float32Array(NM * 2);
  for (let i = 0; i < NM; i++) {
    for (let j = 0; j < 4; j++) SEED[i * 4 + j] = rng();
    const r = Math.sqrt(-2 * Math.log(Math.max(1e-6, rng()))), a = 2 * Math.PI * rng(); GAU[i * 2] = r * Math.cos(a); GAU[i * 2 + 1] = r * Math.sin(a);
    const z = rng(); SZ[i * 2] = 2.5 + 4.5 * z * z; SZ[i * 2 + 1] = rng() * 6.283;
  }
  const quad = (g, n) => {
    g.setIndex([0, 1, 2, 0, 2, 3]); g.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3)); g.instanceCount = n; return g;
  };
  const mg = quad(new THREE.InstancedBufferGeometry(), NM);
  mg.setAttribute('aS', new THREE.InstancedBufferAttribute(SEED, 4)); mg.setAttribute('aG', new THREE.InstancedBufferAttribute(GAU, 2));
  mg.setAttribute('aZ', new THREE.InstancedBufferAttribute(SZ, 2));
  // S5: where the nine small clouds come to rest, scattered round the far box and HAIR packshot (not over them) and
  // above y 700: five fall as the bottle passes right to left (x 470…985: each has fallen before it stops at 330), four
  // as it passes back (x 410…930: fallen before it stops at 1060)
  const REST = [[985, 630], [890, 350], [800, 590], [610, 650], [470, 615], [410, 395], [545, 345], [740, 430], [930, 480]];
  const MU = { uTime: { value: 0 }, uPx: pxU, uW: { value: [0, 0, 0, 0, 0, 0] }, uCloud: { value: new THREE.Vector4(690, 180, 90, 70) },
    uHaze: { value: new THREE.Vector4(...HAZE2) }, uSplit: { value: 0 }, uEnter: { value: 0 }, uMelt: { value: 0 },
    uBx1: { value: 1300 }, uBx2: { value: 0 }, uAbsorb: { value: 0 }, uRest: { value: REST.map(([x, y]) => new THREE.Vector2(x, y)) } };
  // S1's cloud: three Gaussian lobes (centre, spread): behind the box, at its upper left, low behind the bottle
  const S1C = [[650, 820], [470, 610], [980, 1010]], S1S = [[230, 200], [110, 120], [150, 70]];
  const v2 = a => `vec2(${a[0].toFixed(1)}, ${a[1].toFixed(1)})`;
  // the layouts, written once for the shader and once (dropAt below) for QA: keep the two the same
  const MIST_V = `attribute vec4 aS; attribute vec2 aG, aZ;
    uniform float uTime, uPx, uW[6], uSplit, uEnter, uMelt, uBx1, uBx2, uAbsorb;
    uniform vec4 uCloud, uHaze; uniform vec2 uRest[9];
    varying vec2 vQ; varying float vA;
    vec2 wob(float k) { return vec2(sin(uTime * 0.3 * k + aZ.y), cos(uTime * 0.27 * k + aZ.y * 1.3)); }
    vec4 L0() {   // S1: a still thin mist far behind the pair, one soft cloud (no edges: its density falls off as a
      // Gaussian), thinning out between 150 and 220 px from the cap's frame
      vec2 C = aS.x < 0.45 ? ${v2(S1C[0])} : (aS.x < 0.72 ? ${v2(S1C[1])} : ${v2(S1C[2])});
      vec2 S = aS.x < 0.45 ? ${v2(S1S[0])} : (aS.x < 0.72 ? ${v2(S1S[1])} : ${v2(S1S[2])});
      vec2 p = C + aG * S, d = max(max(${v2(CAP0)} - p, p - ${v2(CAP0.slice(2))}), 0.0);   // (as QA's margin: a square one)
      return vec4(p + 1.5 * wob(1.0), aS.w > 0.83 && aS.w < 0.99 ? 0.7 * smoothstep(150.0, 220.0, max(d.x, d.y)) : 0.0, 1.0);
    }
    vec4 L1() {   // the cloud coming in from above: born over the frame's edge, its opacity growing from y 300 to 420
      vec2 p = uCloud.xy + aG * uCloud.zw * 0.5 + 3.0 * wob(2.3);
      return vec4(p, aS.w < 0.45 ? 0.7 * smoothstep(300.0, 420.0, p.y) : 0.0, 1.0);
    }
    vec4 L2() {   // S2: the loose cloud low behind the bottle (uHaze: centre, spread)
      vec2 p = uHaze.xy + aG * uHaze.zw * (0.55 + 0.9 * aS.y) + 4.0 * wob(1.2);
      return vec4(p, aS.w < 0.45 ? 0.5 : 0.0, 1.0);
    }
    vec4 L3() {   // one cloud enters from above, through the top edge by the bottle's cut top, drifts down and left and
      // parts into three (b2.label1–3); some droplets melt as one looks (b2.label4)
      float k = floor(aS.x * 3.0);
      vec2 C = k < 0.5 ? vec2(420.0, 560.0) : (k < 1.5 ? vec2(650.0, 760.0) : vec2(440.0, 960.0)), w = 4.0 * wob(1.4);
      vec2 one = vec2(800.0, 520.0) + aG * vec2(115.0, 95.0) * (0.6 + 0.8 * aS.z) + w, cl = C + aG * 48.0 + w;
      vec2 p = mix(one, cl, uSplit); p.y -= (1.0 - uEnter) * 460.0;
      float melt = aS.z > 0.82 ? 0.5 + 0.5 * sin(uTime * 0.9 + aZ.y * 3.0) : 1.0;
      return vec4(p, aS.w < 0.64 ? 0.7 * melt * smoothstep(300.0, 420.0, p.y) : 0.0, 1.0);
    }
    vec4 L4() {   // S4: the three settle into a soft haze; a few larger drops in it melt, each at its own stage
      vec2 p = vec2(700.0, 840.0) + aG * vec2(190.0, 95.0) * (0.55 + 0.9 * aS.y) + 5.0 * wob(1.0);
      bool drop = aS.w < 0.05;
      float a = drop ? mix(0.55, 0.85 * (1.0 - 0.8 * aS.z), uMelt) : (aS.w < 0.3 ? 0.22 : 0.0);
      return vec4(p, a, drop ? mix(1.0, 1.0 - 0.6 * aS.z, uMelt) : 1.0);
    }
    vec4 L5() {   // S5: nine small clouds fall from beyond the top edge just behind the bottle, five as it passes right to
      // left, four as it passes back, come to rest as loose clouds (uRest) and melt (b4.label3)
      float k = floor(aS.x * 9.0); bool one = k < 4.5; vec2 r = uRest[int(k)];
      float fall = one ? smoothstep(r.x + 40.0, r.x - 120.0, uBx1) : smoothstep(r.x - 40.0, r.x + 120.0, uBx2);
      vec2 rest = r + aG * 22.0 * (0.6 + 0.8 * aS.y), sky = vec2(r.x + 20.0 + aG.x * 9.0, 230.0 + aG.y * 14.0);
      float a = smoothstep(0.0, 0.05, fall) * 0.8 * (1.0 - 0.7 * uAbsorb * aS.z);
      return vec4(mix(sky, rest, fall), aS.w < 0.12 ? a : 0.0, 1.0 - 0.5 * uAbsorb * aS.z);
    }
    void main() {
      vec4 l[6]; l[0] = L0(); l[1] = L1(); l[2] = L2(); l[3] = L3(); l[4] = L4(); l[5] = L5();
      float s = 0.0, k = 0.0; vec2 p = vec2(0.0);
      for (int i = 0; i < 6; i++) { float w = uW[i] * l[i].z; s += w; p += w * l[i].xy; k += w * l[i].w; }
      p /= max(s, 1e-4); k /= max(s, 1e-4);
      vA = min(s, 1.0) * smoothstep(175.0, 235.0, p.x) * (1.0 - smoothstep(1165.0, 1240.0, p.x)) * smoothstep(290.0, 330.0, p.y) * (1.0 - smoothstep(1170.0, 1212.0, p.y));
      float r = max(aZ.x * k * 0.5, 0.75 / uPx); vQ = position.xy;
      vec2 q = p + position.xy * r;
      gl_Position = vA > 0.002 ? projectionMatrix * modelViewMatrix * vec4(q.x - 1200.0, 750.0 - q.y, 0.0, 1.0) : vec4(2.0, 2.0, 2.0, 1.0);
    }`;
  const DROP_F = `varying vec2 vQ; varying float vA;
    void main() { float r = length(vQ); if (r > 1.0) discard;
      float rim = smoothstep(0.35, 1.0, r) * smoothstep(-0.2, 0.7, vQ.y);   // its gold edge toward the light behind, above
      gl_FragColor = vec4(mix(vec3(0.965, 0.953, 0.925), vec3(0.847, 0.741, 0.494), rim), vA * 0.65 * smoothstep(1.0, 0.55, r)); }`;
  const mistMat = new THREE.ShaderMaterial({ vertexShader: MIST_V, fragmentShader: DROP_F, uniforms: MU, transparent: true, depthWrite: false, side: THREE.DoubleSide });
  const mist = new THREE.Mesh(mg, mistMat); mist.frustumCulled = false; mist.renderOrder = 8; fx.add(mist);
  // the same layouts in JS, for QA only (state()): how many droplets show, how many come within 150 px of the cap
  function dropAt(i, u, t) {
    const s = SEED.subarray(i * 4, i * 4 + 4), g = GAU.subarray(i * 2, i * 2 + 2), ph = SZ[i * 2 + 1];
    const wob = k => [Math.sin(t * 0.3 * k + ph), Math.cos(t * 0.27 * k + ph * 1.3)], mx = (a, b, k) => a + (b - a) * k;
    const L = [];
    { const w = wob(1), lo = s[0] < 0.45 ? 0 : s[0] < 0.72 ? 1 : 2, x = S1C[lo][0] + g[0] * S1S[lo][0], y = S1C[lo][1] + g[1] * S1S[lo][1];
      const d = Math.max(CAP0[0] - x, x - CAP0[2], CAP0[1] - y, y - CAP0[3], 0);
      L.push([x + 1.5 * w[0], y + 1.5 * w[1], s[3] > 0.83 && s[3] < 0.99 ? 0.7 * smooth(150, 220, d) : 0]); }
    { const c = u.uCloud.value, w = wob(2.3), x = c.x + g[0] * c.z * 0.5 + 3 * w[0], y = c.y + g[1] * c.w * 0.5 + 3 * w[1]; L.push([x, y, s[3] < 0.45 ? 0.7 * smooth(300, 420, y) : 0]); }
    { const h = u.uHaze.value, w = wob(1.2), sp = 0.55 + 0.9 * s[1]; L.push([h.x + g[0] * h.z * sp + 4 * w[0], h.y + g[1] * h.w * sp + 4 * w[1], s[3] < 0.45 ? 0.5 : 0]); }
    { const k = Math.floor(s[0] * 3), C = k < 0.5 ? [420, 560] : k < 1.5 ? [650, 760] : [440, 960], w = wob(1.4), sp = 0.6 + 0.8 * s[2];
      const one = [800 + g[0] * 115 * sp + 4 * w[0], 520 + g[1] * 95 * sp + 4 * w[1]], cl = [C[0] + g[0] * 48 + 4 * w[0], C[1] + g[1] * 48 + 4 * w[1]];
      const x = mx(one[0], cl[0], u.uSplit.value), y = mx(one[1], cl[1], u.uSplit.value) - (1 - u.uEnter.value) * 460;
      const melt = s[2] > 0.82 ? 0.5 + 0.5 * Math.sin(t * 0.9 + ph * 3) : 1;
      L.push([x, y, s[3] < 0.64 ? 0.7 * melt * smooth(300, 420, y) : 0]); }
    { const w = wob(1), sp = 0.55 + 0.9 * s[1], drop = s[3] < 0.05, m = u.uMelt.value;
      L.push([700 + g[0] * 190 * sp + 5 * w[0], 840 + g[1] * 95 * sp + 5 * w[1], drop ? mx(0.55, 0.85 * (1 - 0.8 * s[2]), m) : s[3] < 0.3 ? 0.22 : 0]); }
    { const k = Math.floor(s[0] * 9), one = k < 4.5, [rx, ry] = REST[k], sp = 0.6 + 0.8 * s[1];
      const fall = one ? smooth(rx + 40, rx - 120, u.uBx1.value) : smooth(rx - 40, rx + 120, u.uBx2.value);
      const rest = [rx + g[0] * 22 * sp, ry + g[1] * 22 * sp], sky = [rx + 20 + g[0] * 9, 230 + g[1] * 14];
      L.push([mx(sky[0], rest[0], fall), mx(sky[1], rest[1], fall), s[3] < 0.12 ? smooth(0, 0.05, fall) * 0.8 * (1 - 0.7 * u.uAbsorb.value * s[2]) : 0]); }
    let S = 0, X = 0, Y = 0;
    for (let j = 0; j < 6; j++) { const w = u.uW.value[j] * L[j][2]; S += w; X += w * L[j][0]; Y += w * L[j][1]; }
    if (S < 1e-4) return null;
    X /= S; Y /= S;
    const a = Math.min(S, 1) * smooth(175, 235, X) * (1 - smooth(1165, 1240, X)) * smooth(290, 330, Y) * (1 - smooth(1170, 1212, Y));
    return a > 0.02 ? [X, Y] : null;
  }

  // ---- poses (frame px): the bottle { x: its axis, y: the foot of its silhouette, H: its height, yaw° (0: the print
  // faces the camera), a: opacity }; the box { cx, cy: its front's centre, h: the front's height, a }. The kit and S1's
  // packshot poses first (the S1 mist keeps clear of that cap); the rest below the effects
  // S3 (p 2) close on the bottle: its top with the cap over the frame's top edge (cut through the cap: it stays on)
  const BOT = [BOT0, { x: 790, y: 928, H: 500 }, { x: 1000, y: 1150, H: 1050 }, { x: 1090, y: 930, H: 340 }, { x: 1060, y: P2, H: 330 }, BOT5];
  const BOT1_PH = { x: 1040, y: 800, H: 430 };   // the phone's S2: below the HAIR packshot, at the right
  const ZOOM = { x: 905, y: 1185, H: 1150 };     // S1 → S2: the camera close on the bottle, its top over the edge
  const PASS1 = { x: 1060, y: P1, H: 380 }, PASS2 = { x: 330, y: P2, H: 450 };   // S5's passes: the top cut by the edge
  const BOX4 = { cx: 640, cy: 450, h: 250 };   // S5: deeper than the bottle, in its own colours
  const HAIR1 = { x0: 236, x1: 716, by: 760 }, HAIR1_PH = { x0: 190, x1: 838, by: 735 }, HAIR4 = { x0: 300, x1: 500, by: 575 };
  const GLOW = { dx: 178, dy: -110, rx: 125, ry: 265, a: 0.8 };   // the kit's backlight round the box (box 760 px): see pose()
  const SWAY = [10, 4, 3, 3, 2, 0];   // the bottle's slow idle turn per screen, ± degrees (within ±30° of the photographed front)
  // the state, written in place on every frame (nothing allocated per frame)
  const ST = { box: { cx: 0, cy: 0, h: 1, a: 0 }, bot: { x: 0, y: 0, H: 1, yaw: 0, a: 1 }, hair: { x0: 0, x1: 1, by: 0, a: 0 }, w: [0, 0, 0, 0, 0, 0],
    cloud: [690, 180], split: 0, enter: 0, melt: 0, bx1: 1300, bx2: 0, absorb: 0, glow: 0 };
  const setB = (o, s, a = 1) => { o.x = s.x; o.y = s.y; o.H = s.H; o.yaw = s.yaw || 0; o.a = a; return o; };
  const mixB = (o, a, b, s) => { o.x = lerp(a.x, b.x, s); o.y = lerp(a.y, b.y, s); o.H = lerp(a.H, b.H, s); o.yaw = lerp(a.yaw || 0, b.yaw || 0, s); return o; };
  const setX = (o, s, a) => { o.cx = s.cx; o.cy = s.cy; o.h = s.h; o.a = a; return o; };
  const XT = { cx: 0, cy: 0, h: 1 }, xt = (cx, cy, h) => { XT.cx = cx; XT.cy = cy; XT.h = h; return XT; };   // a box pose, in place

  function story(p) {   // the state at story position p
    const k = Math.min(4, Math.floor(p)), f = p - k, st = ST, ph = phone.matches, B1 = ph ? BOT1_PH : BOT[1];
    const b = st.box, o = st.bot, w = st.w;
    setX(b, BOX0, 0); setB(o, BOT[Math.min(5, Math.round(p))]); st.hair.a = 0;
    w.fill(0); st.split = st.enter = st.melt = st.absorb = st.glow = 0;
    st.bx1 = 1300; st.bx2 = 0;
    if (k === 0) {   // S1 → S2, the first scroll as the «press»: the still mist goes; the camera comes close to the bottle,
      // its top with the cap leaves the frame's top edge and a cloud comes in from there, beside it, and opens into a
      // loose cloud low behind the bottle; the box recedes and fades; the camera pulls back; the HAIR packshot comes
      const g = smooth(0, 0.6, f), h = lerp(700, 520, g);
      setX(b, xt(lerp(620, 600, g), lerp(1140, 1000, g) - h / 2, h), 1 - smooth(0.1, 0.6, f));
      const zi = smooth(0, 0.3, f), zo = smooth(0.42, 0.85, f);
      o.x = lerp(lerp(BOT0.x, ZOOM.x, zi), B1.x, zo); o.y = lerp(lerp(BOT0.y, ZOOM.y, zi), B1.y, zo); o.H = lerp(lerp(BOT0.H, ZOOM.H, zi), B1.H, zo); o.yaw = 0;
      w[0] = 1 - smooth(0, 0.25, f);
      const c = smooth(0.08, 0.42, f); st.cloud[0] = lerp(770, 650, c); st.cloud[1] = lerp(150, 400, c);
      w[1] = smooth(0.06, 0.16, f) * (1 - smooth(0.32, 0.72, f)); w[2] = smooth(0.32, 0.72, f);
      st.hair.a = smooth(0.65, 1, f);
    } else if (k === 1) {   // S2 → S3: the cloud thins out and goes, the HAIR packshot dissolves; the camera comes close:
      // the bottle grows, moves right and its top leaves the frame; a new cloud comes in through that edge beside it,
      // drifts down and left and parts into three
      w[2] = 1 - smooth(0.05, 0.45, f); st.hair.a = 1 - smooth(0, 0.45, f);
      mixB(o, B1, BOT[2], smooth(0.1, 0.7, f));
      w[3] = smooth(0.55, 0.7, f); st.enter = smooth(0.55, 0.85, f); st.split = smooth(0.7, 1, f);
    } else if (k === 2) {   // S3 → S4: the three settle into a soft haze; the bottle steps back to the right, in its
      // colours; a few drops in the haze melt
      w[3] = 1 - smooth(0, 0.4, f); w[4] = smooth(0, 0.4, f); st.enter = st.split = 1; st.melt = smooth(0.6, 1, f);
      mixB(o, BOT[2], BOT[3], smooth(0.1, 0.6, f));
    } else if (k === 3) {   // S4 → S5, the protocol's three steps: the haze goes; the bottle, its top cut by the frame's
      // edge, passes right to left as small clouds fall from beyond the edge behind it; it passes back as more fall; it
      // steps back whole; the clouds melt where they rest; far behind, the HAIR packshot and the box come in (by opacity)
      w[4] = 1 - smooth(0, 0.1, f); st.melt = 1;
      if (f < 0.25) mixB(o, BOT[3], PASS1, smooth(0, 0.25, f));
      else if (f < 0.5) { setB(o, PASS1); o.x = lerp(PASS1.x, PASS2.x, smooth(0.25, 0.5, f)); }
      else if (f < 0.6) { mixB(o, PASS1, PASS2, smooth(0.5, 0.6, f)); o.x = PASS2.x; }
      else if (f < 0.82) { setB(o, PASS2); o.x = lerp(PASS2.x, BOT[4].x, smooth(0.6, 0.82, f)); }
      else { mixB(o, PASS2, BOT[4], smooth(0.82, 0.95, f)); o.x = BOT[4].x; }
      st.bx1 = f < 0.25 ? 1300 : f < 0.5 ? o.x : 0; st.bx2 = f < 0.6 ? 0 : f < 0.82 ? o.x : 1300;
      w[5] = smooth(0.2, 0.25, f); st.absorb = smooth(0.8, 1, f);
      Object.assign(st.hair, HAIR4); st.hair.a = smooth(0.7, 1, f);
      setX(b, BOX4, smooth(0.82, 1, f));
    } else {   // S5 → kit: the protocol goes; the box and the bottle hold while the page's step cards scroll up over the
      // scene (their foot clears the kit's top, frame y 370, at f ≈ 0.54 on 1440×900 and 0.47 on 1920×1080); then the box
      // comes forward from the depth, the bottle straightens, turns once to +30° and back (S6) and stands by the box with
      // the packshot's gap; a warm gold backlight comes up behind the pair and stays (S7: the page's brightest)
      const out = 1 - smooth(0, 0.3, f);
      w[5] = out; st.bx1 = 0; st.bx2 = 1300; st.absorb = 1;
      Object.assign(st.hair, HAIR4); st.hair.a = out;
      const g = smooth(0.54, 0.85, f); setX(b, xt(lerp(BOX4.cx, BOX5.cx, g), lerp(BOX4.cy, BOX5.cy, g), lerp(BOX4.h, BOX5.h, g)), 1);
      mixB(o, BOT[4], BOT5, smooth(0.56, 0.9, f)); o.yaw = 30 * Math.sin(Math.PI * smooth(0.6, 0.95, f));
      st.glow = smooth(0.72, 0.97, f);   // behind the whole box; at p = 5 in the live pose and in kit() alike
    }
    if (k <= 1) Object.assign(st.hair, ph ? HAIR1_PH : HAIR1);   // (its opacity set above)
    return st;
  }

  // ---- applying a state
  const tmp = new V3();
  const last = { x: 0, y: 0, H: 0, yaw: 0, glow: 0, t: 0 };   // for QA
  function pose(p, t, still) {
    const st = story(p), live = still ? 0 : 1 - smooth(4.85, 5, p), ph = phone.matches;
    const k = Math.min(4, Math.floor(p)), o = st.bot, b = st.box;
    // the idle sway on top of the scripted turn, the sum within ±30° of the photographed front (S6's limit)
    o.yaw = clamp(o.yaw + lerp(SWAY[k], SWAY[k + 1], p - k) * Math.sin(t * 0.45) * live, -30, 30);
    // the bottle: the nearest points of its foot and top (the silhouette's ends) at depth KB / H, so the foot keeps its
    // frame y; its axis RW behind them, seen at the frame x (its sides, which make the silhouette, are at the axis's
    // depth); turned so the print faces the camera
    bottle.visible = o.a > 0.004;
    const Db = KB / o.H;
    at(o.x, o.y, Db, tmp); at(o.x, o.y, Db + RW, bottle.position);
    bottle.position.addScaledVector(upL, tmp.sub(bottle.position).dot(upL));
    const face = facing(bottle); bottle.quaternion.copy(lay.quaternion); bottle.rotateY(face + rad(o.yaw));
    capFace.value.setFromMatrix4(m4.makeRotationAxis(upL, -face));
    for (const m of bottleMats) m.opacity = o.a;
    glass.depthWrite = capMat.depthWrite = o.a > 0.99;
    // the box: its front parallel to the picture's vertical, turned to face the camera (so neither side shows)
    box.visible = b.a > 0.004;
    const Dx = KX / b.h;
    if (box.visible) {
      at(b.cx, b.cy, Dx, box.position); box.quaternion.copy(lay.quaternion);
      box.rotateY(facing(box) + rad(0.5 * Math.sin(t * 0.4 + 1) * live));
      for (const m of boxMats) { m.opacity = b.a; m.depthWrite = b.a > 0.99; }
    }
    // drawn last, far first (renderOrder 100+: after every graphic, which stands behind them)
    const boxFirst = !box.visible || Dx >= Db + RW;
    for (let j = 0; j < bParts.length; j++) bParts[j].renderOrder = (boxFirst ? 110 : 100) + j;
    for (const m of bxParts) m.renderOrder = (boxFirst ? 100 : 110) + m.userData.layer;
    // the planes, behind the farthest product shown
    const Dfar = Math.max(bottle.visible ? Db + RW : 0, box.visible ? Dx + BD * HX : 0, 9);
    place(fx, Dfar + 1); place(hp, Dfar + 2);
    // the HAIR packshot (S2, S5), as it is, facing the picture
    const hr = st.hair; hairBoard.visible = hr.a > 0.004;
    if (hairBoard.visible) { const wpx = hr.x1 - hr.x0; hairBoard.position.set((hr.x0 + hr.x1) / 2 - 1200, 750 - hr.by, 0); hairBoard.scale.set(wpx, wpx, 1); hairBoard.material.opacity = hr.a; }
    // the mist
    const hz = ph ? HAZE2_PH : HAZE2; MU.uHaze.value.set(hz[0], hz[1], hz[2], hz[3]);
    MU.uTime.value = t; for (let i = 0; i < 6; i++) MU.uW.value[i] = st.w[i];
    MU.uCloud.value.x = st.cloud[0]; MU.uCloud.value.y = st.cloud[1];
    MU.uSplit.value = st.split; MU.uEnter.value = st.enter; MU.uMelt.value = st.melt;
    MU.uBx1.value = st.bx1; MU.uBx2.value = st.bx2; MU.uAbsorb.value = st.absorb;
    mist.visible = false; for (let i = 0; i < 6; i++) if (st.w[i] > 0.004) mist.visible = true;
    mg.instanceCount = ph ? NM / 2 : NM;
    // the kit's backlight, on its own plane just behind the box, in the live pose, the keys and kit() alike: brightest in
    // the gap between the box and the bottle, round the bottle's cap and the box's right edge; its ellipse ends inside the
    // pair's outline (alpha 0 outside it), so the offer card's picture and kit.webp, cut to what has alpha, keep their size
    const gl = st.glow;
    if (gl > 0.004 && box.visible) { place(gb, Dx + BD * HX + 0.3); const s = b.h / 760; setSpot(glowBox, b.cx + GLOW.dx * s, b.cy + GLOW.dy * s, GLOW.rx * s, GLOW.ry * s, GLOW.a * gl); }
    else glowBox.visible = false;
    last.x = o.x; last.y = o.y; last.H = o.H; last.yaw = o.yaw; last.glow = gl; last.t = t;
  }
  function mistCount() {   // QA: the droplets shown now, those within 150 px of the cap's box
    if (!mist.visible) return { n: 0, nearCap: 0 };
    const o = ST.bot, W = o.H / 6.22, top = o.y - o.H, cx0 = o.x - W * 0.46 - 150, cx1 = o.x + W * 0.46 + 150, cy0 = top - 150, cy1 = top + 0.342 * o.H + 150;
    let n = 0, near = 0; const N = phone.matches ? NM / 2 : NM;
    for (let i = 0; i < N; i++) { const q = dropAt(i, MU, last.t); if (!q) continue; n++; if (q[0] > cx0 && q[0] < cx1 && q[1] > cy0 && q[1] < cy1) near++; }
    return { n, nearCap: near };
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
    pxU.value = pr * view.cover.w / 2400;   // device px per frame px: the strokes and droplets keep ≥ 1.5 device px
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
    const mats = new Set();
    scene.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) mats.add(o.material); });
    for (const m of mats) m.dispose();
    for (const t of [faceTex, metalTex, printTex, hairTex, roomEnv, capEnv]) t.dispose();
    renderer.dispose();
  }
  const r1 = v => Math.round(v * 10) / 10, r2 = v => Math.round(v * 100) / 100;
  const state = () => ({ quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded,
    version, kits, lastP, hero: { x: r1(last.x), y: r1(last.y), H: r1(last.H), yaw: r1(last.yaw) }, mist: mistCount(), glow: r2(last.glow) });
  return { draw, kit, dispose, state, animated: true };
}
