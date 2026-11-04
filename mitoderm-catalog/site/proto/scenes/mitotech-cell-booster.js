// MITOTECH CELL BOOSTER live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a
// real 3D scene, as the approved sample EXOTECH GEL (scenes/exotech-gel.js) and the pages that followed it (the HAIR
// line's glass and print materials, EXO-NAD's vials, liquids and crimp caps; their pace, state, restore and dispose).
// The engine keeps the story geometry (the cover-fitted 16:10 frame, the run's box, the phone stage, the kit card); this
// module draws the pose for the story position into the box. This page has six runs (an opening screen before S1):
// p 0 open · 1 meet · 2 why · 3 inside · 4 feel · 5 protocol · 6 kit (scratchpad spec pages/mitotech-cell-booster/spec.md §2).
//
// The kit as the owner's render R15 shows it (design/mitotech/packshot-kit-r15.png, mapped into the frame as
// X = 708 + 0.9 (x − 549.5), Y = 750 + 0.9 (y − 720.5)): the closed green box and before it a row of eight 20R vials, four
// boosting ampoules (amber glass, see BOOSTER) and four concentrated powders (the white freeze-dried cake hidden by the label),
// the fifth with its applicator. The box and the row were fitted in this camera (EL 15°: the render's own perspective is
// not one pinhole's — its verticals converge as a wide lens does, its top shows as a 15° view would not — so the corners
// stay within ≈ 12 px, the vials within 1 px). No dieline, no size in mm: the box is W : H : D = 1.332 : 1 : 0.33 (its
// print's proportions on the render; the depth an assumption), a vial Ø 0.466 of its height with the cap (≈ 31 × 67 mm
// at the box's 237 mm print height: a 20R vial). The print is the owner's vector files, rasterised
// (design/mitotech-cell-booster/make_textures.py): no text of ours.
//
// The story: p0 the kit full screen under the name, the camera far; run 0 the camera moves in (dolly) to S1's framing;
// run 1 the eight vials go round the box's sides and behind it (never through it: the box stays closed); run 2 a pair
// comes out from behind its left edge, the powder first, then the booster, and stands large before the camera; run 3 the
// camera goes into the booster's amber (a soft amber light inside, nothing drawn in it) and back; run 4 the R7 preparation
// as the user guide's drawings show it: the white caps (with their aluminium rings) lift off, then the dark stoppers; the
// booster lifts, turns over the open powder vial and pours slowly (no stream drawn: what leaves the booster rises in the
// powder vial as a clear solution, the owner's «תמיסה שקופה», and stays there to the kit); a stopper on the powder vial, a
// wait; the stopper off, the applicator down onto the neck; run 5 the empty booster goes into the dark, the ready vial
// to the fifth place of the row, the box and the other seven come back: the kit, which flies into the offer card.
// Five more poses (p 11…15) are the preparation's five steps as stills for the page's step cards (render-keys).
// Only what exists is drawn (the owner, 22/10): the box, the vials, their caps, stoppers and applicator, the liquid; no
// lines, rings, discs, particles, bubbles or drops; no hands. The line's green and mint live in the page's haze (z10),
// not here. The product keeps its print's colours (emissive ≈ 85 % + neutral shading, toneMapped off).
//
// The booster's amber (the owner's render R15, 04/11): the GLASS is amber, from its foot to under the crimp (the shoulder
// and the neck too, the thick base catching a yellow light), and what it holds is colourless: no level shows through the
// amber. Run 4 pours that colourless content into the powder vial (the clear solution) and the booster stays amber glass,
// empty. BOOSTER below switches it in one line: 'glass' (R15) or 'liquid' (the earlier reading: clear glass, an amber
// liquid to the shoulder, poured out amber) — the owner's open question (texts-for-approval §6).
//
// createScene(THREE, { canvas, base, onLoad }) → { draw(p, view), kit(view) → canvas, steps, animated, state(), dispose() }
//   p: the story position 0…6 (run index + progress), 11…15 the step stills; view: { cover, box, dpr, t, still }
const BOOSTER = 'glass';   // 'glass' | 'liquid' (see above)
export function createScene(THREE, { canvas, base, onLoad }) {
  const V3 = THREE.Vector3, rad = THREE.MathUtils.degToRad;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  const lerp = (a, b, s) => a + (b - a) * s;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  renderer.localClippingEnabled = true;   // the booster's liquid, cut by its level as it pours
  const scene = new THREE.Scene();

  // the camera looks down 15° (fitted to R15: the box's top shows as a sliver, the caps as ellipses); `lay` is the story's
  // camera without the box's view offset, for placing objects by their frame pixels
  const FOV = 20, EL = rad(15), DIST = 14;
  const camera = new THREE.PerspectiveCamera(FOV, 1.6, 1, 80);
  camera.position.set(0, Math.sin(EL) * DIST, Math.cos(EL) * DIST); camera.lookAt(0, 0, 0);
  const lay = camera.clone(); lay.updateMatrixWorld(); lay.updateProjectionMatrix();
  const fwd = new V3(), RIGHT = new V3(1, 0, 0).applyQuaternion(lay.quaternion), UP = new V3(0, 1, 0).applyQuaternion(lay.quaternion);
  lay.getWorldDirection(fwd);
  const ray = new V3(), TAN = Math.tan(rad(FOV / 2));
  function at(cx, cy, depth, out) {   // the point seen at frame pixel (cx, cy), `depth` in front of the camera
    ray.set(cx / 1200 - 1, 1 - cy / 750, 0.5).unproject(lay).sub(lay.position).normalize();
    return out.copy(lay.position).addScaledVector(ray, depth / ray.dot(fwd));
  }
  const depthOf = p => ray.copy(p).sub(lay.position).dot(fwd);
  const facing = p => Math.atan2(lay.position.x - p.x, lay.position.z - p.z);   // the yaw that turns +z to the story camera

  // ---- light: a neutral studio for reflections (PMREM), as the HAIR scenes': dark above and below, an even horizon, two
  // tall narrow softboxes either side of the camera, rims behind; the glass has its own room without the front softboxes
  // (a clear body, bright at its edges)
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
    if (!glass) { panel(5, -5.7, 3, 8.2, 2.4, 9); panel(2.5, 6.4, 3, 7.7, 1.6, 9); }   // ±35–40° from the camera, the left one the key
    else { panel(0.8, 0, 1, 12, 24, 12); panel(2.2, -5.7, 3, 8.2, 1.4, 9); panel(1.3, 6.4, 3, 7.7, 1.0, 9); }   // the glass: a light wall
    // behind the camera and two soft boxes (R15's clear glass reads light grey with tall soft reflections, not the page's black)
    panel(2.5, -9, 1.5, -7, 2.5, 9); panel(2, 9, 2, -7, 2.5, 9);     // rims from behind
    const rt = pm.fromScene(room, 0.02); pm.dispose();
    room.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    return rt;   // its target: disposing that frees the framebuffer too, not only the texture
  }
  let roomEnv = makeEnv(false), glassEnv = makeEnv(true);
  scene.environment = roomEnv.texture;
  const glassMats = [];   // the materials that see the glass room (rebuilt after a lost context)
  const restored = () => {   // after a lost context three.js restores image textures, not the rendered environments
    const old = [roomEnv, glassEnv]; roomEnv = makeEnv(false); glassEnv = makeEnv(true); scene.environment = roomEnv.texture;
    for (const m of glassMats) m.envMap = glassEnv.texture;
    old.forEach(t => t.dispose()); sizeW = -1; NOID();
    version++; if (onLoad) onLoad();   // the engine redraws (the kit picture too), also under reduced motion
  };
  canvas.addEventListener('webglcontextrestored', restored);
  const key = new THREE.DirectionalLight(0xffffff, 1.2); key.position.set(-4, 7, 6); scene.add(key);
  const noGlint = sh => {   // the key leaves no glint on glass (a white dot in the same place on every vial)
    sh.fragmentShader = sh.fragmentShader.replace('#include <lights_fragment_end>', `#include <lights_fragment_end>
      reflectedLight.directSpecular = vec3(0.0);
      #ifdef USE_CLEARCOAT
      clearcoatSpecularDirect = vec3(0.0);
      #endif`);
  };

  // ---- textures: the owner's print (make_textures.py)
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy(), NTEX = 4;
  const tex = (name, srgb) => {
    const t = new THREE.TextureLoader().load(new URL(`img/mitotech-cell-booster-3d/${name}`, base).href, () => {
      t.needsUpdate = true; NOID(); if (++loaded === NTEX) { version++; if (onLoad) onLoad(); }
    });
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = ANISO; return t;
  };
  const frontTex = tex('box-front.webp', true), metalTex = tex('box-metal.png'), powderTex = tex('label-powder.webp', true), boosterTex = tex('label-booster.webp', true);
  const TEXS = [frontTex, metalTex, powderTex, boosterTex];

  // ---- materials. The product in its print's colours: emissive 0.85 of the colour plus a neutral shading (a diffuse 0.2
  // of it under the key and the room), not tone mapped; the foil a satin metal (roughness 0.24 on the bare green, the
  // inks matte). Nothing is dimmed or tinted: things come and go by opacity only
  const SHADE = 0.2;
  const P = (hex, opts = {}, key = 'p') => {
    const m = new THREE.MeshPhysicalMaterial(Object.assign({ color: new THREE.Color(hex).multiplyScalar(SHADE), emissive: hex,
      emissiveIntensity: 0.85, roughness: 0.7, specularIntensity: 0.3, toneMapped: false, transparent: true }, opts));
    m.customProgramCacheKey = () => 'mtcb-' + key; return m;
  };
  const GREEN = 0x154734;   // the print's green (box, labels), measured on the PDF
  const front = P(0xffffff, { color: new THREE.Color(SHADE, SHADE, SHADE), map: frontTex, emissiveMap: frontTex, metalnessMap: metalTex,
    roughnessMap: metalTex, metalness: 1, roughness: 1, specularIntensity: 1, envMapIntensity: 0.55 }, 'front');
  // the inks (where the metal mask is 0) lit 1.16 ×, the saturated ones (the mint plates) a little less red and more green-blue:
  // R15's mint reads brighter and cooler than the PDF's (#6cf8d7 vs #7ae1bf), the ΔE probe aims between them (#73ecca); white
  // and grey inks keep their colour. The bare green foil keeps its colour (between the PDF's and R15's) under a broad, low
  // satin sheen: the reflection of a soft box up left, placed by the view (it slides as the box turns; R15's satin foil)
  front.onBeforeCompile = sh => {
    sh.fragmentShader = sh.fragmentShader.replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
      { float bare = texture2D(metalnessMap, vMetalnessMapUv).b; vec3 ec = emissiveColor.rgb;
        float sat = max(max(ec.r, ec.g), ec.b) - min(min(ec.r, ec.g), ec.b);
        vec3 ink = 1.16 * mix(vec3(1.0), vec3(0.8, 1.02, 1.035), smoothstep(0.15, 0.4, sat));
        vec3 rv = reflect(-normalize(vViewPosition), normal);
        float sheen = exp(-(pow(rv.x + 0.31, 2.0) + 1.6 * pow(rv.y + 0.43, 2.0)) / 0.012);   // S1's view: the face's upper left
        totalEmissiveRadiance *= mix(ink, vec3(1.0 + 0.5 * sheen), bare); }`);
  };
  const foil = (hex, k) => P(hex, { metalness: 1, roughness: 0.26, specularIntensity: 1, envMapIntensity: 0.55 }, 'foil' + k);
  const sideMat = foil(GREEN, 's'), topMat = foil(0x1e5c42, 't');   // the top: the render's lit foil (#1e5c42)
  const boxMats = [front, sideMat, topMat];
  // glass (HAIR's): no transmission (on a transparent canvas it cannot see the page's haze, and a phone pays a pass for
  // it); its opacity follows Fresnel and its own highlights, so its edges and highlights read and the body stays clear
  const VIAL_H = { body: 0.735 };
  // the amber glass (R15 pipetted: the body #9b6630 away from the highlights and the label, the edges a deep amber, the
  // base's light #f9e929): its back wall's light of its own and opacity, the limbs' colours, the rim and the foot (linear)
  const AG = { back: 0x92520a, backA: 0.94, dark: 0.62, light: 0xae6610, gold: 0.7, shade: 0x4a2604, env: [0.35, 0.7],
    rim: '0.62, 0.3, 0.04', foot: '0.55, 0.45, 0.06', neck: '0.2, 0.08, 0.008' };
  function glassMat(side, a0, aF, aS, lit = null, key = '', color = 0x0b0b0c, emissive = 0) {   // emissive: a faint
    // milky light of its own (the far wall's grey, the applicator's clear plastic), so it reads on the dark page
    const m = new THREE.MeshPhysicalMaterial({ color, emissive, roughness: 0.04, ior: 1.5, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.6,
      envMap: glassEnv.texture, transparent: true, depthWrite: false, side, toneMapped: false });
    const k = [a0, aF, aS].map(v => v.toFixed(3));
    m.onBeforeCompile = sh => {
      noGlint(sh);
      sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float F = pow(1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0), 5.0);
        vec3 sp = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
        #ifdef USE_CLEARCOAT
        sp += (clearcoatSpecularDirect + clearcoatSpecularIndirect) * material.clearcoat;
        #endif
        gl_FragColor.a = clamp(${k[0]} + ${k[1]} * F + dot(sp, vec3(0.2126, 0.7152, 0.0722)) * ${k[2]}, 0.0, 1.0) * opacity; }`);
      if (lit) lit(sh);
    };
    m.customProgramCacheKey = () => 'mtcb-glass' + k.join() + key + color + emissive; glassMats.push(m);
    return m;
  }
  // the vial's outline: glass seen edge-on (the walls, the shoulder) catches the room's light, so clear glass on the dark
  // page reads; two soft tall reflections of the softboxes on the body, off the axis (the ΔE probes sit on it)
  // amber glass (BOOSTER 'glass'): the rim takes the glass's colour (R15's edges a deep saturated amber) and the thick
  // base a soft yellow light toward its middle, below the label (R15)
  const vialLitC = amber => sh => {
    sh.vertexShader = 'varying float vVy;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vVy = position.y;');
    sh.fragmentShader = 'varying float vVy;\n' + sh.fragmentShader.replace(/(gl_FragColor\.a = clamp\([^\n]*\n)/, `$1
      { float nx = normal.x, body = smoothstep(0.04, 0.1, vVy) * (1.0 - smoothstep(${(VIAL_H.body - 0.03).toFixed(3)}, ${(VIAL_H.body + 0.03).toFixed(3)}, vVy));
        float s = body * (0.85 * exp(-pow((nx + 0.45) / 0.08, 2.0)) + 0.4 * exp(-pow((nx - 0.55) / 0.05, 2.0)) + 0.05);
        float rim = 0.5 * pow(1.0 - clamp(abs(dot(nonPerturbedNormal, normalize(vViewPosition))), 0.0, 1.0), 3.0);
        ${amber ? `float foot = (1.0 - smoothstep(0.004, 0.03, vVy)) * exp(-pow(nx / 0.42, 2.0));
        vec3 add = vec3(s - rim - 0.05 * body) + rim * vec3(${AG.rim}) + foot * vec3(${AG.foot});
        gl_FragColor.rgb += add; gl_FragColor.a = max(gl_FragColor.a, max(max(add.r, add.g), add.b) * opacity);
        float neck = smoothstep(0.745, 0.775, vVy);   // the shoulder and the neck: the stopper inside seen through amber
        gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(${AG.neck}), neck * 0.85); gl_FragColor.a = max(gl_FragColor.a, neck * 0.85 * opacity); }`
        : 's += rim; gl_FragColor.rgb += vec3(s); gl_FragColor.a = max(gl_FragColor.a, s * opacity); }'}
`);
  };
  const vialLit = vialLitC(false), amberLit = vialLitC(true);
  // the amber wall seen through the vial (its back faces): the body's colour (the ΔE probe); as R15, a deep brown just
  // over the label (the label's back seen through), golden toward the shoulder, deeper again under the crimp, and
  // deeper toward the limbs
  const amberBack = sh => {
    const v = h => { const c = new THREE.Color(h); return `vec3(${c.r.toFixed(4)}, ${c.g.toFixed(4)}, ${c.b.toFixed(4)})`; };
    sh.vertexShader = 'varying float vVy;\n' + sh.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n  vVy = position.y;');
    sh.fragmentShader = 'varying float vVy;\n' + sh.fragmentShader.replace(/(gl_FragColor\.a = clamp\([^\n]*\n)/, `$1
      { float y = vVy, ax = abs(normal.x);
        float gold = smoothstep(0.3, 0.55, y) * (1.0 - smoothstep(0.74, 0.8, y));
        gl_FragColor.rgb = mix(gl_FragColor.rgb * ${AG.dark.toFixed(2)}, ${v(AG.light)}, gold * ${AG.gold.toFixed(2)});
        gl_FragColor.rgb = mix(gl_FragColor.rgb, ${v(AG.shade)}, 0.6 * smoothstep(0.55, 0.95, ax)); }
`);
  };
  // the booster's amber, clear and dark as rendered: the front colour where the body faces the camera (the ΔE probe),
  // the light behind coming through toward the right limb, the left limb in shade; thinner toward the limbs. Its cut
  // (the level, while it pours) shows the liquid's own back faces, flat in the surface's colour: no disc is drawn
  // The prepared solution in the powder vial (from the pour on): clear, the owner's «תמיסה שקופה» (its colour is still his
  // open question): a darker refracting body, light toward its limbs, a light surface (the meniscus) so its level reads
  const AMBER = { c: [0x965512, 0xc4833b, 0x3a1e05], surf: 0xb47a36, a: [0.98, 0.66], sa: 0.9, key: 'liq' };   // dense: the light far wall does not show through
  // the colourless content seen through the amber glass (BOOSTER 'glass'): a faint deepening of the amber below its level
  const THRU = { c: [0x6a3a08, 0x8a5418, 0x3a1c04], surf: 0x9a6024, a: [0.08, 0.05], sa: 0.12, key: 'thr' };
  const CLEAR = { c: [0x252b2a, 0xc8d0cf, 0x8f9796], surf: 0xe4eae9, a: [0.66, 0.8], sa: 0.92, key: 'clr' };
  function liquidMat(clip, pal = AMBER) {
    const m = P(pal.c[0], { roughness: 0.5, specularIntensity: 0.2, depthWrite: false, side: clip ? THREE.DoubleSide : THREE.FrontSide }, pal.key + (clip ? 'c' : ''));
    const L = new THREE.Color(pal.c[1]), S = new THREE.Color(pal.c[2]), U = new THREE.Color(pal.surf);
    m.onBeforeCompile = sh => {
      sh.uniforms.uLimb = { value: new V3(L.r, L.g, L.b) }; sh.uniforms.uShade = { value: new V3(S.r, S.g, S.b) }; sh.uniforms.uSurf = { value: new V3(U.r, U.g, U.b) };
      sh.fragmentShader = 'uniform vec3 uLimb, uShade, uSurf;\n' + sh.fragmentShader.replace('#include <opaque_fragment>', `#include <opaque_fragment>
      { float nx = normal.x, ax = abs(nx), up = normal.y;
        gl_FragColor.rgb = mix(gl_FragColor.rgb, uLimb, 0.8 * smoothstep(0.55, 0.85, nx) * (1.0 - smoothstep(0.93, 1.0, nx)));
        gl_FragColor.rgb = mix(gl_FragColor.rgb, uShade, 0.75 * smoothstep(-0.55, -0.9, nx));
        gl_FragColor.a *= mix(${pal.a[0].toFixed(2)}, ${pal.a[1].toFixed(2)}, smoothstep(0.5, 0.97, ax));
        if (up > 0.7) { gl_FragColor.rgb = uSurf; gl_FragColor.a = ${pal.sa.toFixed(2)} * opacity; }   // the closed fill's top: the surface
        ${clip ? `if (!gl_FrontFacing) { gl_FragColor.rgb = uSurf; gl_FragColor.a = ${pal.sa.toFixed(2)} * opacity; }` : ''} }`);
    };
    return m;
  }
  const capMat = () => P(0xffffff, { color: new THREE.Color(0.36, 0.36, 0.36), emissiveIntensity: 0.64, roughness: 0.45, specularIntensity: 0.5 }, 'cap');   // white
  // flip-off: less light of its own than the other parts, so the key and the room model its dome and its dent (R15's grey shading)
  const ringMat = () => P(0xd6d6d4, { metalness: 0.9, roughness: 0.3, specularIntensity: 1, emissiveIntensity: 0.55, envMapIntensity: 0.7 }, 'ring');   // aluminium
  const stopMat = () => P(0x2a2b2b, { roughness: 0.6 }, 'stop');   // grey rubber (R7 icon 1)
  const cakeMat = () => P(0xf2f0ea, { roughness: 0.95, specularIntensity: 0.05 }, 'cake');   // the freeze-dried cake
  const tipMat = () => P(0xf3f3f3, { roughness: 0.5 }, 'tip');
  const labelMat = map => P(0xffffff, { color: new THREE.Color(SHADE, SHADE, SHADE), map, emissiveMap: map, roughness: 0.55, specularIntensity: 0.25,
    polygonOffset: true, polygonOffsetFactor: -2 }, 'label');

  // ---- the box, height 1 (origin its front's centre, y up, the front at z 0, depth BD behind)
  const WR = 1.332, BD = 0.33, BH = 1;
  const box = new THREE.Group(); scene.add(box);
  const bface = (geo, mat, x, y, z, rx, ry) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, 0); box.add(m); return m; };
  bface(new THREE.PlaneGeometry(WR, BH), front, 0, 0, 0, 0, 0);
  bface(new THREE.PlaneGeometry(WR, BD), topMat, 0, BH / 2, -BD / 2, -Math.PI / 2, 0);
  bface(new THREE.PlaneGeometry(WR, BD), sideMat, 0, -BH / 2, -BD / 2, Math.PI / 2, 0);
  bface(new THREE.PlaneGeometry(BD, BH), sideMat, -WR / 2, 0, -BD / 2, 0, -Math.PI / 2);
  bface(new THREE.PlaneGeometry(BD, BH), sideMat, WR / 2, 0, -BD / 2, 0, Math.PI / 2);
  bface(new THREE.PlaneGeometry(WR, BH), sideMat, 0, 0, -BD, 0, Math.PI);

  // ---- the vial, height 1 = foot → top of the cap (L; 0.2834 world units, scaled per vial): a lathe of R15's profile
  // (fractions of L): the body Ø 0.466 to 0.735 (its foot rounded), the shoulder to Ø 0.336 at 0.79, the neck Ø 0.256, the
  // lip Ø 0.30 to 0.868; over the lip the aluminium crimp ring (Ø 0.31, 0.815…0.872) and the white flip-off cap (Ø 0.392,
  // 0.872…1, its top a soft dome with a centre dent); under them the grey stopper (its flange on the lip). The label: a
  // band 0.03…0.488 round 74 % of the glass (the print's 71 × 30 mm), its left column toward the camera. The booster's
  // content to 0.755 (the render's shoulder; BOOSTER 'liquid': its amber). The applicator (R15's fifth vial): a clear collar over the neck and a cone with a white
  // tip, 1.32 L at its top
  const R = 0.2331, LW = 0.2834, V2 = (r, y) => new THREE.Vector2(r, y), SEG = 72;
  const arc = (cx, cy, r, a0, a1, n) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return V2(cx + r * Math.cos(a), cy + r * Math.sin(a)); });
  const shoulder = new THREE.SplineCurve([V2(R, 0.735), V2(R - 0.006, 0.76), V2(0.2, 0.778), V2(0.168, 0.79), V2(0.135, 0.798), V2(0.128, 0.806)]).getPoints(20);
  const glassGeo = new THREE.LatheGeometry([V2(0, 0), V2(R - 0.035, 0)].concat(arc(R - 0.035, 0.035, 0.035, -Math.PI / 2, 0, 8), shoulder,
    [V2(0.128, 0.83), V2(0.15, 0.836), V2(0.15, 0.864), V2(0.142, 0.868), V2(0.1, 0.868), V2(0.1, 0.84)]), SEG);
  const RI = R - 0.013;   // inside the wall
  const inner = [V2(0, 0.028), V2(RI - 0.03, 0.028)].concat(arc(RI - 0.03, 0.058, 0.03, -Math.PI / 2, 0, 6));
  const FILL = 0.755;
  const fillGeo = new THREE.LatheGeometry(inner.concat([V2(RI, FILL), V2(0, FILL)]), SEG);   // the kit's boosters
  const NECK = 0.83;   // the hero vials' fill ends inside the neck, short of the lip (no flat face across the open mouth)
  const fullGeo = new THREE.LatheGeometry(inner.concat([V2(RI, 0.735), V2(RI - 0.008, 0.758), V2(0.19, 0.775), V2(0.155, 0.787), V2(0.118, 0.796),
    V2(0.112, 0.806), V2(0.112, NECK), V2(0.07, NECK - 0.004), V2(0, NECK - 0.006)]), SEG);   // a hero vial's whole inside, cut at its level
  const cakeGeo = new THREE.CylinderGeometry(0.2, 0.2, 0.22, 48).translate(0, 0.028 + 0.11, 0);
  const ringGeo = new THREE.LatheGeometry([V2(0.1, 0.872), V2(0.152, 0.872), V2(0.156, 0.866), V2(0.156, 0.82), V2(0.15, 0.815), V2(0.135, 0.815), V2(0.135, 0.86), V2(0.1, 0.866)], SEG);
  const capGeo = new THREE.LatheGeometry([V2(0, 0.872), V2(0.19, 0.872), V2(0.196, 0.878)].concat(arc(0.172, 0.976, 0.024, 0, Math.PI / 2, 8),
    [V2(0.11, 0.999), V2(0.07, 0.997), V2(0.06, 0.992), V2(0, 0.991)]), SEG);
  const stopGeo = new THREE.LatheGeometry([V2(0, 0.80), V2(0.1, 0.80), V2(0.105, 0.806), V2(0.105, 0.866), V2(0.146, 0.866), V2(0.15, 0.872),
    V2(0.15, 0.882), V2(0.14, 0.888), V2(0, 0.888)], SEG);
  const LB = [0.03, 0.488], LTH = 0.74 * Math.PI * 2;
  const labelGeo = new THREE.CylinderGeometry(R * 1.004, R * 1.004, LB[1] - LB[0], 128, 1, true, -0.24 * LTH, LTH).translate(0, (LB[0] + LB[1]) / 2, 0);
  const appGeo = new THREE.LatheGeometry([V2(0.13, 0.80), V2(0.192, 0.80), V2(0.198, 0.81), V2(0.198, 0.98), V2(0.19, 1.0), V2(0.15, 1.035),
    V2(0.09, 1.06), V2(0.063, 1.075), V2(0.05, 1.15), V2(0.036, 1.27), V2(0.0, 1.27)], SEG);
  const tipGeo = new THREE.LatheGeometry([V2(0, 1.262), V2(0.037, 1.262)].concat(arc(0.017, 1.3, 0.02, -0.2, Math.PI / 2, 6), [V2(0, 1.32)]), 32);
  const APP_TOP = 1.32;

  // a vial: { g (foot centre, upright), parts, mats } — its moving parts in their own groups (cap with ring, stopper,
  // applicator); each vial has its own materials (opacity per vial and part). The glass as R15 renders it: clear (the
  // booster's amber glass: AG), but light grey on the dark page (its far wall catches the studio's light), the applicator a
  // brighter clear plastic. `wet`: a powder vial already prepared (the kit's fifth, the one with the applicator): the clear
  // solution, no cake
  const GL = { backA: 0.76, backE: 0x8a8f8e, appA: 0.56, appE: 0xdce4e3, appBA: 0.66, appBE: 0xb4bcbb };
  function makeVial(kind, hero, wet = false) {
    const g = new THREE.Group(); g.rotation.order = 'YXZ'; g.scale.setScalar(LW); scene.add(g);
    const capG = new THREE.Group(), stopG = new THREE.Group(), appG = new THREE.Group(); g.add(capG, stopG, appG);
    const amber = kind === 'B' && BOOSTER === 'glass';
    const m = { back: amber ? glassMat(THREE.BackSide, AG.backA, 0.3, 0.7, amberBack, 'amb', 0x0b0b0c, AG.back) : glassMat(THREE.BackSide, GL.backA, 0.3, 0.7, null, '', 0x0b0b0c, GL.backE),
      front: amber ? glassMat(THREE.FrontSide, 0.03, 0.55, 1.0, amberLit, 'va') : glassMat(THREE.FrontSide, 0.03, 0.55, 1.0, vialLit, 'v'),
      label: labelMat(kind === 'B' ? boosterTex : powderTex), cap: capMat(), ring: ringMat(), stop: stopMat(),
      app: glassMat(THREE.FrontSide, GL.appA, 0.6, 1.0, vialLit, 'a', 0x0b0b0c, GL.appE), appB: glassMat(THREE.BackSide, GL.appBA, 0.3, 0.7, null, 'ab', 0x0b0b0c, GL.appBE), tip: tipMat() };   // clear plastic
    if (amber) { m.back.envMapIntensity = AG.env[0]; m.front.envMapIntensity = AG.env[1]; }   // glass reflections over amber: fainter
    if (kind === 'B') { if (!amber || hero) m.liquid = liquidMat(hero, amber ? THRU : AMBER); } else { if (!wet) m.cake = cakeMat(); if (hero || wet) m.liquid = liquidMat(hero, CLEAR); }
    const parts = [];
    const add = (geo, mat, parent, j) => { const x = new THREE.Mesh(geo, mat); x.userData.j = j; parent.add(x); parts.push(x); return x; };
    add(glassGeo, m.back, g, 0);
    const cake = m.cake ? add(cakeGeo, m.cake, g, 1) : null, liq = m.liquid ? add(hero ? fullGeo : fillGeo, m.liquid, g, 2) : null;
    add(stopGeo, m.stop, stopG, 3); add(ringGeo, m.ring, capG, 4); add(capGeo, m.cap, capG, 5);
    add(glassGeo, m.front, g, 6); add(labelGeo, m.label, g, 7);
    add(appGeo, m.appB, appG, 8); add(appGeo, m.app, appG, 9); add(tipGeo, m.tip, appG, 10);
    const clip = hero ? new THREE.Plane(new V3(0, -1, 0), 0) : null;
    if (clip) m.liquid.clippingPlanes = [clip];
    return { g, capG, stopG, appG, m, parts, kind, clip, cake, liq };
  }
  // the kit's eight (R15 left to right: four boosters, four powders; the fifth prepared) and the travelling pair
  const kitV = [0, 1, 2, 3, 4, 5, 6, 7].map(i => makeVial(i < 4 ? 'B' : 'P', false, i === 4));
  const heroB = makeVial('B', true), heroP = makeVial('P', true);
  const ALL = kitV.concat([heroB, heroP]);

  // ---- a hero vial's level: points spread evenly through its inside (vial units), so the level that holds a volume (the
  // booster's amber left, the solution poured into the powder vial) is a quantile of their heights, whatever the vial's tilt
  const NS = 1500, SMP = new Float32Array(NS * 3), SY = new Float32Array(NS);
  {
    let s = 20261104 | 0; const rnd = () => { s = s + 0x6d2b79f5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    const rAt = y => (y < 0.735 ? RI : y < 0.79 ? lerp(RI, 0.13, (y - 0.735) / 0.055) : 0.112);
    let n = 0;
    while (n < NS) {
      const y = 0.03 + rnd() * (NECK - 0.03), x = (rnd() * 2 - 1) * RI, z = (rnd() * 2 - 1) * RI, r = rAt(y);
      if (x * x + z * z > r * r) continue;
      SMP[n * 3] = x; SMP[n * 3 + 1] = y; SMP[n * 3 + 2] = z; n++;
    }
  }
  let FULL_FRAC = 0; for (let i = 0; i < NS; i++) if (SMP[i * 3 + 1] < FILL) FULL_FRAC++; FULL_FRAC /= NS;
  function levelOf(v, frac) {   // the world height of the level holding `frac` of the full fill, for vial v as placed
    const e = v.g.matrixWorld.elements;
    for (let i = 0; i < NS; i++) SY[i] = e[1] * SMP[i * 3] + e[5] * SMP[i * 3 + 1] + e[9] * SMP[i * 3 + 2] + e[13];
    SY.sort(); const k = Math.floor(clamp(frac * FULL_FRAC) * (NS - 1)); return SY[k];
  }

  // ---- inside the amber (run 3): a soft amber light over the scene's box, brighter toward its middle, its alpha a round
  // gaussian falling to nothing well inside the box's edges (no panel, no rounded rectangle, no circle's edge); drawn after the scene
  const qScene = new THREE.Scene(), qCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const hexv = h => new V3(((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255);   // sRGB as drawn
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
    uniforms: { uA: { value: 0 }, uRes: { value: new THREE.Vector2(1, 1) }, uC0: { value: hexv(0x8d5210) }, uC1: { value: hexv(0xc4833b) } },
    vertexShader: 'void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `uniform float uA; uniform vec2 uRes; uniform vec3 uC0, uC1;
      void main() { vec2 q = gl_FragCoord.xy / uRes, d = min(q, 1.0 - q) * uRes; float m = min(uRes.x, uRes.y);
        vec2 c = (gl_FragCoord.xy - 0.5 * uRes) / (0.5 * m); float r = clamp(dot(c, c), 0.0, 1.0), a = exp(-2.4 * dot(c, c));
        float n = fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) - 0.5;
        gl_FragColor = vec4(mix(uC1, uC0, smoothstep(0.0, 1.0, r)) + n / 255.0, 1.0) * (uA * a); }`,
    transparent: true, depthTest: false, depthWrite: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
    blendSrc: THREE.OneFactor, blendDst: THREE.OneMinusSrcAlphaFactor, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneMinusSrcAlphaFactor }));
  quad.frustumCulled = false; qScene.add(quad);
  // the dive's edges: while the camera is inside, the whole picture (the amber filling the view, the soft light over it)
  // fades softly toward the canvas's edges, so the amber is a shapeless glow and never a panel cut by the canvas (also the
  // phone's opening push-in, where the kit grows past its block: no straight cut through the box at the block's edge)
  const vScene = new THREE.Scene(), vig = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
    uniforms: { uW: { value: 0 }, uF: { value: 0.5 }, uRes: quad.material.uniforms.uRes },
    vertexShader: 'void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `uniform float uW, uF; uniform vec2 uRes;
      void main() { vec2 q = gl_FragCoord.xy / uRes, d = min(q, 1.0 - q) * uRes; float m = min(uRes.x, uRes.y);
        float v = smoothstep(0.0, uF * m, d.x) * smoothstep(0.0, uF * m, d.y);
        gl_FragColor = vec4(0.0, 0.0, 0.0, mix(1.0, v * v, uW)); }`,
    transparent: true, depthTest: false, depthWrite: false, blending: THREE.CustomBlending, blendEquation: THREE.AddEquation,
    blendSrc: THREE.ZeroFactor, blendDst: THREE.SrcAlphaFactor, blendSrcAlpha: THREE.ZeroFactor, blendDstAlpha: THREE.SrcAlphaFactor }));
  vig.frustumCulled = false; vScene.add(vig);

  // ---- the poses. The kit K (R15, fitted): the box's front centre and yaw, the vials' foot centres, in the world
  const K_BOX = new V3(-0.84148, 1.77789, 5.93207), K_YAW = -0.063372;
  const VX = [-1.41075, -1.23785, -1.06455, -0.89168, -0.71799, -0.54485, -0.37195, -0.20007];
  const VZ = [6.99128, 7.02929, 7.06706, 7.10440, 7.13244, 7.15284, 7.17267, 7.19360];
  const K_V = VX.map((x, i) => new V3(x, K_BOX.y - BH / 2, VZ[i]));
  const REL = K_YAW - facing(K_BOX);   // the box's turn from facing the camera (kept in every pose)
  const boxM = new THREE.Matrix4(), boxQ = new THREE.Quaternion(), YAX = new V3(0, 1, 0), ONE = new V3(1, 1, 1);
  const boxMatrix = (pos, out) => out.compose(pos, boxQ.setFromAxisAngle(YAX, facing(pos) + REL), ONE);
  const K_LOCAL = (() => { const inv = boxMatrix(K_BOX, new THREE.Matrix4()).invert(); return K_V.map(v => v.clone().applyMatrix4(inv)); })();
  const boxPx = (cx, cy, h) => at(cx, cy, 750 / (TAN * h), new V3());   // the front's centre at a frame pixel, h px tall
  const vialPx = (x, foot, h) => at(x, foot, LW * 750 / (TAN * h), new V3());   // a vial's foot at a frame pixel, h px tall
  const BOX2 = boxPx(720, 700, 478);                        // S2: alone, stepped back
  const B3 = vialPx(560, 1150, 600), P3 = vialPx(860, 1150, 600);   // S3: the pair, large
  const B4 = vialPx(640, 1190, 300), P4 = vialPx(780, 1190, 300);   // S4: small and low
  const B5 = vialPx(560, 1150, 470), P5 = vialPx(820, 1150, 470);   // S5: the preparation
  const deeper = (pos, k, out) => out.copy(pos).sub(lay.position).multiplyScalar(k).add(lay.position);   // on its line of sight, k × as far
  // the step stills (p 11…15): one camera distance for all five (a vial 640 frame px tall, so step 2's pour fits), each
  // centred in the frame by its outline (its middle on (1200, 750): OFF), never scaled: the vials keep one size card to card
  const SH = 640, sx = (x, h) => 1200 + (x - 1200) * SH / h;
  const S1B = vialPx(sx(930, 820), 1290, SH), S1P = vialPx(sx(1470, 820), 1290, SH);
  const S2P = vialPx(1360, 1310, SH), S3P = vialPx(sx(1440, 940), 1300, SH), S3B = vialPx(sx(900, 940), 1300, SH);
  const S4P = vialPx(1180, 1290, SH), S5P = vialPx(1270, 220, SH);
  const OFF = [];   // per step: its shift in frame px, measured once on its first pose
  const shiftPx = (pos, dx, dy) => { const w = 2 * depthOf(pos) * TAN / 1500; return pos.addScaledVector(RIGHT, dx * w).addScaledVector(UP, -dy * w); };

  // the state, written in place every frame (nothing allocated per frame)
  // fill: the booster's amber left (1 full); liq: the solution in the powder vial (0 … 1 of the same volume)
  const vs = () => ({ pos: new V3(), yaw: 0, tilt: 0, a: 0, cap: 0, stop: 0, app: 0, fill: 1, liq: 0, cake: 1, stopBack: 0, keep: 0 });
  const ST = { box: { pos: new V3(), a: 0 }, kit: kitV.map(vs), B: vs(), P: vs(), cam: 0, push: 0, dive: 0, quad: 0 };
  const resetV = (o, pos, a = 1) => { o.pos.copy(pos); o.yaw = 0; o.tilt = 0; o.a = a; o.cap = 0; o.stop = 0; o.app = 0; o.fill = 1; o.liq = 0; o.cake = 1; o.stopBack = 0; o.keep = 0; return o; };
  const tmpM = new THREE.Matrix4(), tA = new V3(), tB = new V3(), tC = new V3();
  // a path through points (box-local or world), m 0…1 by length; returns the fraction where segment `seg` begins
  function along(pts, m, out) {
    let L = 0; for (let i = 1; i < pts.length; i++) L += pts[i].distanceTo(pts[i - 1]);
    let d = m * L;
    for (let i = 1; i < pts.length; i++) {
      const s = pts[i].distanceTo(pts[i - 1]);
      if (d <= s || i === pts.length - 1) return out.lerpVectors(pts[i - 1], pts[i], s > 0 ? clamp(d / s) : 1);
      d -= s;
    }
    return out.copy(pts[pts.length - 1]);
  }
  const fracAt = (pts, seg) => { let L = 0, A = 0; for (let i = 1; i < pts.length; i++) { const s = pts[i].distanceTo(pts[i - 1]); L += s; if (i <= seg) A += s; } return A / L; };
  // run 1 (and back in run 5): a kit vial's way round the box (box-local): on a slant back to the box's front corner,
  // clear of its side and just in front of its face (FRONT), then back along the side, in behind its back (×0.9 of its
  // place), a little up; the left four by the left side, the right four by the right. Not sideways at the row's depth
  // first: that near the camera the outer vials went wider than the box on screen and the canvas's edge cut them
  const SIDE = WR / 2 + 0.13, BACK = -BD - 0.12, FRONT = 0.12;
  const ROUND = K_LOCAL.map((l, i) => { const sx = i < 4 ? -SIDE : SIDE;
    return [l.clone(), new V3(sx, l.y, FRONT), new V3(sx, l.y, BACK), new V3(l.x * 0.9, l.y + 0.03, BACK)]; });
  const ROUND_HIDE = ROUND.map(p => fracAt(p, 2));   // from here on behind the box
  const OUT_ORDER = [0, 7, 1, 6, 2, 5, 3, 4];           // run 1: from the ends of the row to its middle
  const BACK_ORDER = [3, 5, 2, 6, 1, 7, 0];             // run 5: from the middle out (the fifth place is the hero's)
  // run 2: the pair from behind the box's left edge (box-local): behind, to the left side, forward along it
  const PAIR = [-0.25, -0.05].map(x => [new V3(x, -BH / 2, BACK - 0.03), new V3(-SIDE - 0.03, -BH / 2, BACK - 0.03), new V3(-SIDE - 0.03, -BH / 2, 0.15)]);
  const PAIR_HIDE = fracAt(PAIR[0], 1);
  const GO = [[ST.P, 0.1, P3, 0], [ST.B, 0.25, B3, 1]];   // run 2: the powder first, then the booster

  function story(p) {   // the state at story position p (phone: the same poses; only p0's camera differs)
    const st = ST, b = st.box;
    // a phone: each run plays in the first 45 % of its scroll window and holds its end pose, so it is whole while its
    // block is still mostly on screen (the engine's flow moves the block up under the header as the run plays)
    if (p < 6 && phone.matches) { const k0 = Math.floor(p); p = k0 + Math.min(1, (p - k0) / 0.45); }
    st.cam = st.push = st.dive = st.quad = 0;
    b.pos.copy(K_BOX); b.a = 0;
    for (let i = 0; i < 8; i++) resetV(st.kit[i], K_V[i], 0);
    resetV(st.B, B3, 0); resetV(st.P, P3, 0);
    if (p >= 10) return steps(p);
    const k = Math.min(5, Math.floor(p)), f = p - k;
    if (k === 0) {   // open → meet: the kit as R15, large under the name; the camera moves in toward it, then on to S1's
      // framing (one camera move, the kit solid throughout: no fade, no empty frame)
      b.a = 1; for (let i = 0; i < 8; i++) st.kit[i].a = 1;
      st.push = smooth(0.04, 0.55, f); st.cam = 1 - smooth(0.35, 0.95, f);
    } else if (k === 1) {   // meet → why: the eight go round the box's sides and in behind it; it steps back (0.92)
      b.a = 1; b.pos.lerpVectors(K_BOX, BOX2, smooth(0.1, 0.9, f));
      boxMatrix(b.pos, tmpM);
      for (let r = 0; r < 8; r++) {
        const i = OUT_ORDER[r], o = st.kit[i], m = smooth(0.05 * r, 0.05 * r + 0.45, f);
        along(ROUND[i], m, o.pos).applyMatrix4(tmpM); o.a = 1 - smooth(ROUND_HIDE[i], 1, m);
      }
    } else if (k === 2) {   // why → inside: the pair from behind its left edge (the powder first), forward to S3; the box
      // goes deeper and into the dark
      b.pos.copy(deeper(BOX2, lerp(1, 1.4, smooth(0, 0.6, f)), tA)); b.a = 1 - smooth(0.55, 0.9, f);
      boxMatrix(b.pos, tmpM);
      for (let n = 0; n < 2; n++) {
        const o = GO[n][0], t0 = GO[n][1], end = GO[n][2], j = GO[n][3], m = smooth(t0, t0 + 0.3, f), w = smooth(t0 + 0.3, t0 + 0.65, f);
        along(PAIR[j], m, tB).applyMatrix4(tmpM);
        o.pos.lerpVectors(tB, end, w); o.a = smooth(0, PAIR_HIDE, m); o.yaw = rad(-30) * (1 - w);
      }
    } else if (k === 3) {   // inside → feel: through the booster's amber and back (it passes, it does not hold); the glass
      // fades before the camera is in (no straight glass edge in the glow); the pair goes small and low
      st.B.a = st.P.a = 1 - smooth(0.16, 0.3, f) * (1 - smooth(0.55, 0.68, f));
      st.dive = smooth(0, 0.4, f) * (1 - smooth(0.48, 0.74, f));
      st.quad = smooth(0.22, 0.36, f) * (1 - smooth(0.48, 0.62, f));   // over the glass's fade: never an empty frame
      const g = smooth(0.6, 1, f); st.B.pos.lerpVectors(B3, B4, g); st.P.pos.lerpVectors(P3, P4, g);
    } else if (k === 4) {   // feel → protocol: the R7 preparation (prep())
      prep(f);
    } else {   // protocol → kit: the empty booster into the dark; the ready vial to the row's fifth place; the box and the
      // other seven come back
      prep(1);
      const B = st.B, P = st.P, gB = smooth(0.3, 0.55, f);
      deeper(B5, lerp(1, 3, gB), B.pos); B.a = 1 - smooth(0.35, 1, gB);
      const m = smooth(0.4, 0.75, f);
      P.pos.lerpVectors(P5, K_V[4], m); P.pos.y += 0.12 * Math.sin(Math.PI * m);
      const gb = smooth(0.45, 0.8, f);
      deeper(K_BOX, lerp(1 / 0.6, 1, gb), b.pos); b.a = gb;
      boxMatrix(b.pos, tmpM);
      for (let r = 0; r < 7; r++) {
        const i = BACK_ORDER[r], o = st.kit[i], mm = 1 - smooth(0.5 + 0.03 * r, 0.8 + 0.03 * r, f);
        along(ROUND[i], mm, o.pos).applyMatrix4(tmpM); o.a = 1 - smooth(ROUND_HIDE[i], 1, mm);
      }
      if (p >= 6) { b.pos.copy(K_BOX); b.a = 1; for (let i = 0; i < 8; i++) if (i !== 4) resetV(st.kit[i], K_V[i]); P.pos.copy(K_V[4]); B.a = 0; }
    }
    if (p < 2) { st.kit[4].app = 1; st.kit[4].cap = 1; st.kit[4].stop = 1; }   // R15's fifth: the applicator on
    return st;
  }
  // run 4: f 0–0.22 the pair rises and grows to S5; 0.22–0.36 the caps (with their rings) lift and go, then the stoppers;
  // 0.36–0.66 the booster lifts, comes over the powder vial, turns 115° over it (its neck over the other's, a little
  // behind) and pours slowly (its level falls 0.44–0.60), then goes back to its place, empty and open; 0.66–0.74 a
  // stopper onto the powder vial; 0.74–0.80 the wait; 0.80–0.94 the stopper off, the applicator down onto the neck
  const tQ = new THREE.Quaternion(), tE = new THREE.Euler(0, 0, 0, 'YXZ');
  function pourFoot(P, out) {   // where the booster's foot is when its neck is over the powder vial's (tilt 115°)
    const yaw = facing(P), c = Math.cos(yaw), s = Math.sin(yaw), t = rad(115), n = 0.868 * LW;
    const dx = -Math.sin(t) * n, dy = -Math.cos(t) * n + 0.06 * LW + 0.868 * LW;
    return out.set(P.x + c * dx - s * 0.12 * LW, P.y + dy, P.z - s * dx - c * 0.12 * LW);
  }
  const POUR_B = pourFoot(P5, new V3());
  function prep(f) {
    const B = ST.B, P = ST.P;
    B.a = P.a = 1;
    const g = smooth(0, 0.22, f);
    B.pos.lerpVectors(B4, B5, g); P.pos.lerpVectors(P4, P5, g);
    const cap = smooth(0.22, 0.3, f), stop = smooth(0.28, 0.36, f);
    B.cap = P.cap = cap; B.stop = P.stop = stop;
    // the pour
    const up = smooth(0.36, 0.42, f), over = smooth(0.4, 0.48, f), back = smooth(0.6, 0.66, f);
    const tilt = rad(115) * smooth(0.4, 0.48, f) * (1 - back);
    tA.copy(B5); tA.y += 0.35 * LW * up;
    tB.copy(POUR_B);
    B.pos.lerpVectors(tA, tB, over); if (back > 0) B.pos.lerpVectors(B.pos, B5, back);
    B.yaw = (facing(P5) - facing(B.pos)) * over * (1 - back); B.tilt = tilt;   // turned in P's plane
    B.fill = 1 - smooth(0.44, 0.6, f); P.liq = 1 - B.fill; P.cake = 1 - smooth(0.46, 0.66, f);   // what leaves the booster rises in the powder vial
    // the stopper back onto the powder vial, then off; the applicator down
    const sIn = smooth(0.66, 0.74, f), sOut = smooth(0.8, 0.86, f), aIn = smooth(0.84, 0.94, f);
    P.stop = f < 0.66 ? stop : 1 - sIn * (1 - sOut); P.stopBack = f >= 0.66 ? 1 : 0;
    P.app = aIn;
    if (f < 0.22) B.pos.lerpVectors(B4, B5, g);
  }
  function steps(p) {   // the five step stills: as the R7 drawings, no hands, no arrows, no stream, no drop
    const n = Math.round(p) - 10, B = ST.B, P = ST.P;
    if (n === 1) { resetV(B, S1B); resetV(P, S1P); B.cap = P.cap = 0.78; B.stop = P.stop = 0.64; B.keep = P.keep = 1; }     // lifted, as the arrows
    else if (n === 2) { resetV(P, S2P); P.cap = P.stop = 1; resetV(B, pourFoot(S2P, tA)); B.cap = B.stop = 1; B.tilt = rad(115); B.yaw = facing(S2P) - facing(B.pos); B.fill = 0.25; P.liq = 0.75; P.cake = 0.4; }   // the level risen above the label
    else if (n === 3) { resetV(P, S3P); P.cap = 1; P.stop = 0; P.stopBack = 1; P.cake = 0; P.liq = 1; resetV(B, S3B); B.cap = B.stop = 1; B.fill = 0; }
    else if (n === 4) { resetV(P, S4P); P.cap = P.stop = 1; P.app = 1; P.cake = 0; P.liq = 1; P.tilt = rad(12); }
    else { resetV(P, S5P); P.cap = P.stop = 1; P.app = 1; P.cake = 0; P.liq = 1; P.tilt = rad(140); }
    const o = OFF[n]; if (o) for (const v of [B, P]) if (v.a > 0) shiftPx(v.pos, o[0], o[1]);
    return ST;
  }

  // ---- applying a state
  const last = { level: 0 };
  const DEPTH = new Float32Array(11), RANK = Array.from({ length: 11 }, (_, i) => i), farFirst = (i, j) => DEPTH[j] - DEPTH[i];
  const OBJ = ALL.concat([{ box: true }]);
  const FADE = ['back', 'front', 'label', 'liquid', 'cake'];   // the parts that come and go with the vial
  function applyVial(v, s, t, live, sway) {
    const g = v.g; g.visible = s.a > 0.004; if (!g.visible) return;
    g.position.copy(s.pos); g.rotation.set(0, facing(s.pos) + s.yaw + rad(sway) * Math.sin(t * 0.45 + v.kind.length) * live, -s.tilt);
    g.updateMatrixWorld();
    const m = v.m, a = s.a;
    for (let i = 0; i < FADE.length; i++) if (m[FADE[i]]) m[FADE[i]].opacity = a;
    // the cap with its ring: up 0.45 L and gone; the stopper up 0.25 L and gone (or coming back down onto the neck)
    v.capG.position.y = 0.45 * smooth(0, 1, s.cap); v.capG.visible = s.cap < 0.999 && s.app < 0.001;
    m.cap.opacity = m.ring.opacity = a * (s.keep ? 1 : 1 - smooth(0.45, 1, s.cap));
    v.stopG.position.y = 0.25 * s.stop; v.stopG.visible = s.stop < 0.999 && s.app < 0.6;
    m.stop.opacity = a * (1 - smooth(0.5, 1, s.stop)) * (s.app > 0 ? 1 - smooth(0, 0.4, s.app) : 1);
    if (s.cap < 0.999 && s.app < 0.001) m.stop.opacity = a;   // under the cap: not seen
    if (s.keep) m.stop.opacity = a;
    v.appG.visible = s.app > 0.001; v.appG.position.y = 0.5 * (1 - smooth(0, 1, s.app));
    m.app.opacity = m.appB.opacity = m.tip.opacity = a * smooth(0, 0.35, s.app);
    if (v.cake) { v.cake.visible = s.cake > 0.01; v.cake.scale.set(1, Math.max(0.01, s.cake), 1); }
    if (v.clip) {   // a hero vial: its level as the world sees it (the booster's amber left, the solution in the powder vial)
      const fr = v.kind === 'B' ? s.fill : s.liq;
      v.liq.visible = fr > 0.004;
      if (v.liq.visible) { const L = levelOf(v, fr); v.clip.constant = L; if (v.kind === 'B') last.level = L; }
    }
  }
  const camPos = new V3(), openPos = new V3(), Q = new V3();
  function pose(p, t, still) {
    if (p >= 10 && !OFF[Math.round(p) - 10]) {   // a step still's first pose: measure its outline, centre it
      pose1(p, 0, true); const bb = outline(), n = Math.round(p) - 10;
      OFF[n] = bb ? [1200 - (bb[0] + bb[2]) / 2, 750 - (bb[1] + bb[3]) / 2] : [0, 0];
    }
    pose1(p, t, still);
  }
  function pose1(p, t, still) {
    const st = story(p), live = still ? 0 : 1 - smooth(5.85, 6, p);
    // the camera: the story's, or moved back for the opening (the kit ×0.68 round (1200, 1010) on a desktop's full screen,
    // ×0.8 round the scene box's middle on a phone), or into the booster's amber
    camera.position.copy(lay.position); camera.quaternion.copy(lay.quaternion); camera.near = 1;
    if (st.cam > 0) camera.position.lerpVectors(lay.position, openCam(openPos, st.push), st.cam);
    if (st.dive > 0) {
      Q.copy(B3).addScaledVector(YAX, 0.66 * LW);
      tC.copy(lay.position).sub(Q).normalize().multiplyScalar(R * LW * 1.6).add(Q);
      camera.position.lerpVectors(lay.position, tC, st.dive); camera.near = 0.02;
    }
    camPos.copy(camera.position);
    // the box
    const b = st.box; box.visible = b.a > 0.004;
    if (box.visible) {
      box.position.copy(b.pos); box.rotation.set(0, facing(b.pos) + REL, 0); box.updateMatrixWorld();
      for (const m of boxMats) { m.opacity = b.a; m.depthWrite = b.a > 0.99; }
    }
    for (let i = 0; i < 8; i++) applyVial(kitV[i], st.kit[i], t, 0, 0);
    applyVial(heroB, st.B, t, live, 1.5); applyVial(heroP, st.P, t, live, 1.5);
    // drawn back to front: each object's parts in their own order
    for (let i = 0; i < 10; i++) DEPTH[i] = ALL[i].g.visible ? tA.copy(ALL[i].g.position).sub(camPos).length() : 0;
    DEPTH[10] = box.visible ? tA.copy(box.position).sub(camPos).length() + 0.05 : 0;
    RANK.sort(farFirst);
    for (let r = 0; r < 11; r++) {
      const o = OBJ[RANK[r]];
      if (o.box) { for (const c of box.children) c.renderOrder = 100 + r * 12; continue; }
      for (const x of o.parts) x.renderOrder = 100 + r * 12 + x.userData.j;
    }
  }
  // the opening's camera: along the view so the kit is s × as large as in S1, shifted so its middle (frame (708, 750)) lands
  // on the target pixel; `push` 0 … 1 moves it on toward that point (× 1.2: the kit stays whole on a desktop's screen, above the dock). A desktop: the kit ≈ 55 % of the screen's
  // height (frame y 525 … 1355), centred under the name (its copy ends above 31 % of a 16:10 screen, 30 % of a 16:9 one) and
  // above the dock; a phone: S1's own framing in the opening's block
  const OPEN = { desk: [0.98, 1200, 940], phone: [1, 708, 750] }, PUSH = 1.2;
  function openCam(out, push) {
    const o = phone.matches ? OPEN.phone : OPEN.desk, tx = o[1], ty = o[2], s = o[0] * lerp(1, PUSH, push);
    const D = depthOf(K_BOX), D2 = D / s, wpp = 2 * D2 * TAN / 1500;
    const dx = tx - (1200 + s * (708 - 1200)), dy = ty - 750;
    return out.copy(lay.position).addScaledVector(fwd, -(D2 - D)).addScaledVector(RIGHT, -dx * wpp).addScaledVector(UP, dy * wpp);
  }
  function clashes() {   // QA: vials whose body meets the box's volume (box-local, with the vial's radius)
    let n = 0; tmpM.copy(box.matrixWorld).invert();
    for (const v of ALL) {
      if (!v.g.visible) continue;
      tA.copy(v.g.position).applyMatrix4(tmpM); const r = R * LW;
      tB.set(0, 1, 0).applyQuaternion(v.g.quaternion).multiplyScalar((v.appG.visible ? APP_TOP : 1) * LW).add(v.g.position).applyMatrix4(tmpM);
      for (let n = 0; n < 3; n++) { const u = n / 2;
        const x = lerp(tA.x, tB.x, u), y = lerp(tA.y, tB.y, u), z = lerp(tA.z, tB.z, u);
        if (Math.abs(x) < WR / 2 + r && z > -BD - r && z < r && y > -BH / 2 - 0.001 && y < BH / 2) { n++; break; }
      }
    }
    return n;
  }

  // ---- drawing into the engine's box: the full frame is the cover; the canvas shows the box's part of it
  // the density drawn: a phone's stage is small, so it draws at the screen's full density (≤ 3), a desktop at the
  // engine's (≤ 2); long frames lower it under a cap (pace), never below 2 (a 2× picture, ARCHITECTURE-v2 / audit T13)
  const phone = matchMedia('(max-width: 899px)'), full = view => (phone.matches ? Math.min(3, devicePixelRatio || 1) : view.dpr);
  let cap = Infinity, pr = 0, sizeW = -1, sizeH = -1, sizePr = -1, renders = 0, lastT = 0, lastP = 0, lastView = null, trial = null, capped = false;
  const LADDER = [2, 1.5, 1.25], FLOOR = 2, win = [];
  function pace(now, still) {   // fewer pixels when frames run long: a 90-frame median over 24 ms tries the next cap that
    if (still || capped) { lastT = now; return; }   // cuts ≥ 20 % of the pixels (and is ≥ 2); the next window keeps it only if
    const dt = lastT ? now - lastT : 0; lastT = now;   // frames got ≥ 20 % shorter; if not, the rate is a cap (low-power
    if (!dt || dt > 400) return;   // 30 Hz), not the GPU: back, no more tries. A gap over 400 ms is a pause, not a frame
    win.push(dt); if (win.length < 90) return;
    const m = win.slice().sort((a, b) => a - b)[45], mean = win.reduce((a, v) => a + Math.min(v, 100), 0) / win.length; win.length = 0;
    if (trial) { if (mean > trial.mean * 0.8) { cap = trial.cap; capped = true; } trial = null; return; }
    const next = LADDER.find(q => q >= FLOOR && (q / pr) ** 2 <= 0.8);
    if (m > 24 && next) { trial = { cap, mean }; cap = next; }
  }
  const VO = [0, 0, 2400, 1500];   // the canvas's box in frame px
  function fit(view, pr) {
    if (view.box.w !== sizeW || view.box.h !== sizeH || pr !== sizePr) {
      renderer.setPixelRatio(pr); renderer.setSize(view.box.w, view.box.h, false); sizeW = view.box.w; sizeH = view.box.h; sizePr = pr;
    }
    camera.aspect = view.cover.w / view.cover.h;
    camera.setViewOffset(view.cover.w, view.cover.h, view.box.x - view.cover.x, view.box.y - view.cover.y, view.box.w, view.box.h);
    camera.updateProjectionMatrix();
    const k = 2400 / view.cover.w; VO[0] = (view.box.x - view.cover.x) * k; VO[1] = (view.box.y - view.cover.y) * k; VO[2] = view.box.w * k; VO[3] = view.box.h * k;
    quad.material.uniforms.uRes.value.set(canvas.width, canvas.height);
  }
  // the kit (from p 5.85 and every still) draws at the screen's full density whatever the cap; a pose that does not move
  // (p ≥ 6, a still) is drawn once
  // the fixed pose last drawn (its key field by field, nothing allocated per frame; NaN: none, the next draw renders)
  const ID = new Float64Array(11); ID[0] = NaN;
  function NOID() { ID[0] = NaN; }
  function render(p, view) {
    const fixed = view.still || p >= 6, kitAt = fixed || p >= 5.85;
    pr = kitAt ? full(view) : Math.min(full(view), cap);
    if (fixed) {
      const b = view.box, c = view.cover;
      if (ID[0] === p && ID[1] === b.x && ID[2] === b.y && ID[3] === b.w && ID[4] === b.h && ID[5] === c.x && ID[6] === c.y && ID[7] === c.w
        && ID[8] === pr && ID[9] === version && ID[10] === +phone.matches) return;
      ID[0] = p; ID[1] = b.x; ID[2] = b.y; ID[3] = b.w; ID[4] = b.h; ID[5] = c.x; ID[6] = c.y; ID[7] = c.w; ID[8] = pr; ID[9] = version; ID[10] = +phone.matches;
    } else NOID();
    pose(p, view.still ? 0 : view.t, view.still); fit(view, pr);
    renderer.render(scene, camera);
    // the edges fade while the camera is in the amber, and on a phone while the opening's push-in outgrows its block
    // (from the dive's first step: the pair is never cut flat by the canvas's edge as the camera moves in)
    const qa = ST.quad, vw = Math.max(smooth(0, 0.25, ST.dive), phone.matches ? smooth(0.02, 0.3, ST.push) : 0);
    quad.material.uniforms.uA.value = qa; vig.material.uniforms.uW.value = vw; vig.material.uniforms.uF.value = ST.dive > 0 ? lerp(0.16, 0.7, smooth(0.2, 0.7, ST.dive)) : 0.16;   // the push: its edges only; the dive: the edges first, then all soft
    if (qa > 0.002 || vw > 0.002) {
      renderer.autoClear = false;
      if (qa > 0.002) renderer.render(qScene, qCam);
      if (vw > 0.002) renderer.render(vScene, qCam);
      renderer.autoClear = true;
    }
    renders++;
  }
  const html = document.documentElement;
  function draw(p, view) {
    window.__mtP = p;   // the story position for the page's motion layer (story-v2-motion.js), without the QA state()
    if (html.classList.contains('mt-cards0')) return;   // desktop: the step cards stand in for the 3D (story-v2.css hides it): the last frame stays
    pace(performance.now(), view.still || p >= 5.85); lastP = p; lastView = view; render(p, view);
  }
  let kits = 0;   // kit pictures rendered (QA: none on a phone, none for a toolbar)
  function kit(view) {   // the kit pose rendered once into a picture (the offer card, the flight into it), then the current pose again
    kits++;
    pose(6, 0, true); fit(view, view.dpr); renderer.render(scene, camera); NOID();
    const c = document.createElement('canvas'); c.width = canvas.width; c.height = canvas.height; c.getContext('2d').drawImage(canvas, 0, 0);
    if (lastView) render(lastP, lastView);
    return c;
  }
  function dispose() {
    canvas.removeEventListener('webglcontextrestored', restored);
    const mats = new Set(), geos = new Set();
    for (const s of [scene, qScene]) s.traverse(o => { if (o.geometry) geos.add(o.geometry); if (o.material) mats.add(o.material); });
    for (const g of geos) g.dispose();
    for (const m of mats) m.dispose();
    for (const t of TEXS.concat([roomEnv, glassEnv])) t.dispose();
    renderer.dispose();
  }

  // ---- QA (state() only: nothing per frame): the ΔE probes and the objects' outline in frame px for the pose drawn
  const fc = new THREE.PerspectiveCamera(FOV, 1.6, 0.01, 80), pv = new V3();
  const toFrame = (v) => { pv.copy(v).project(fc); return [r1((pv.x + 1) * 1200), r1((1 - pv.y) * 750)]; };
  function frameCam() { fc.position.copy(camera.position); fc.quaternion.copy(camera.quaternion); fc.near = camera.near; fc.updateProjectionMatrix(); fc.updateMatrixWorld(); }
  const onBox = (u, v) => toFrame(tA.set((u - 0.5) * WR, (0.5 - v) * BH, 0.002).applyMatrix4(box.matrixWorld));
  const onVial = (v, x, y, z) => toFrame(tA.set(x, y, z).applyMatrix4(v.g.matrixWorld));
  function probes() {
    frameCam();
    const solid = box.visible && ST.box.a > 0.99, th = (0.42 - 0.24) * LTH;
    const k0 = kitV[0].g.visible && ST.kit[0].a > 0.99 ? kitV[0] : heroB.g.visible && ST.B.a > 0.99 && ST.B.fill > 0.99 ? heroB : null;
    return { front: solid ? onBox(0.35, 0.436) : null, mint: solid ? onBox(0.93, 0.32) : null,
      label: k0 ? onVial(k0, R * Math.sin(th), LB[1] - 0.3 * (LB[1] - LB[0]), R * Math.cos(th)) : null,
      amber: k0 ? onVial(k0, 0, 0.66, R) : null, cap: kitV[0].g.visible && ST.kit[0].a > 0.99 ? onVial(kitV[0], 0, 0.935, 0.197) : null };
  }
  function outline() {   // the visible objects' box in frame px (the opening's QA: the kit never under the copy)
    frameCam(); let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    const pt = v => { pv.copy(v).project(fc); const x = (pv.x + 1) * 1200, y = (1 - pv.y) * 750; x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); };
    if (box.visible) for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const z of [0, -BD]) pt(tB.set(sx * WR / 2, sy * BH / 2, z).applyMatrix4(box.matrixWorld));
    for (const v of ALL) {
      if (!v.g.visible) continue;
      const top = Math.max(1, v.capG.visible ? 1 + v.capG.position.y : 0, v.stopG.visible ? 0.888 + v.stopG.position.y : 0, v.appG.visible ? APP_TOP + v.appG.position.y : 0);
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) for (const y of [0, top]) pt(tB.set(sx * 0.2, y, sz * 0.2).applyMatrix4(v.g.matrixWorld));
    }
    return x0 > x1 ? null : [r1(x0), r1(y0), r1(x1), r1(y1)];
  }
  const r1 = v => Math.round(v * 10) / 10, r2 = v => Math.round(v * 100) / 100;
  const state = () => {
    const st = ST;
    return { quality: pr, cap, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded, version, kits, lastP,
      box: { o: r2(box.visible ? st.box.a : 0) }, shown: ALL.filter(v => v.g.visible).length, clash: box.visible ? clashes() : 0,
      kitP: 6, floor: FLOOR,   // this page's kit pose (six runs: the opening first) and the pace's floor (verify-scene)
      B: { o: r2(st.B.a), cap: r2(st.B.cap), stop: r2(st.B.stop), tilt: r1(THREE.MathUtils.radToDeg(st.B.tilt)), fill: r2(st.B.fill) },
      P: { o: r2(st.P.a), cap: r2(st.P.cap), stop: r2(st.P.stop), app: r2(st.P.app), liq: r2(st.P.liq) }, dive: r2(st.dive), inside: r2(st.quad),
      probes: probes(), aabb: outline() };
  };
  // the step stills for the page's cards (render-keys: these positions, named step1…step5)
  const STEPS = [11, 12, 13, 14, 15];
  return { draw, kit, dispose, state, steps: STEPS, animated: true };
}
