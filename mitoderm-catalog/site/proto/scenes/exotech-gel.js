// EXOTECH GEL live in three.js: the product page's scroll story (engine/story.js, option `scene`) drawn as a real 3D
// scene instead of pre-rendered frames. The engine keeps the story geometry (cover-fitted 16:10 frame, the run's box,
// the phone stage, the kit card); this module draws the pose for the story position into the box. Layout per screen
// in frame pixels (2400×1500), as the approved draft (design/exotech-gel/draft_frames.py): the box and the jar left of
// the copy; S3 opens the jar the way it opens in the owner's photos (19/10): the lid unscrews a quarter turn, lifts and
// tips back over the white threaded cup with the pale gel; the silver collar and shoulder show.
// Print: typeset from the packaging (design/exotech-gel/make_textures.py), sharp at any size. The mirror gold is a
// physically based metal lit by a studio environment (softboxes, as in the packshot's two highlights).
//
// createScene(THREE, { canvas, base, onLoad }) → { draw(p, view), kit(view) → canvas, animated, state(), dispose() }
//   p: the story position 0…5 (run index + progress); view: { cover, box, dpr, t, still } from the engine
export function createScene(THREE, { canvas, base, onLoad }) {
  const V3 = THREE.Vector3, rad = THREE.MathUtils.degToRad;
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  const scene = new THREE.Scene();

  // the camera looks down a little, as the packshot does; `lay` is the same camera without the box's view offset,
  // for placing objects by their frame pixels
  const FOV = 20, EL = rad(13), DIST = 14;
  const camera = new THREE.PerspectiveCamera(FOV, 1.6, 1, 60);
  camera.position.set(0, Math.sin(EL) * DIST, Math.cos(EL) * DIST); camera.lookAt(0, 0, 0);
  const lay = camera.clone(); lay.updateMatrixWorld(); lay.updateProjectionMatrix();
  const fwd = new V3(); lay.getWorldDirection(fwd);
  const ray = new V3(), TAN = Math.tan(rad(FOV / 2));
  function at(cx, cy, depth, out) {   // the point seen at frame pixel (cx, cy), `depth` in front of the camera
    ray.set(cx / 1200 - 1, 1 - cy / 750, 0.5).unproject(lay).sub(lay.position).normalize();
    return out.copy(lay.position).addScaledVector(ray, depth / ray.dot(fwd));
  }
  const world = (px, depth) => px / 1500 * 2 * depth * TAN;   // frame pixels → world units at that depth

  // ---- light: a studio room for reflections (PMREM), a warm key for the matte parts (print, black card, gel)
  function makeEnv() {   // as the packshot's studio: a bright warm table below, a dim ceiling with two softboxes, a warm horizon
    const pm = new THREE.PMREMGenerator(renderer), room = new THREE.Scene();
    const dome = new THREE.SphereGeometry(30, 48, 32), col = [], c = new THREE.Color();
    for (let i = 0; i < dome.attributes.position.count; i++) {
      const y = dome.attributes.position.getY(i) / 30;   // −1 floor … 1 ceiling
      const v = y >= 0 ? 0.42 - 0.26 * smooth(0, 0.6, y) : y > -0.12 ? 0.42 - 0.22 * smooth(0, -0.12, y) : 0.2 + 0.85 * smooth(-0.12, -0.5, y);   // a dark band under the horizon shapes the sphere
      c.setRGB(1, 0.9, 0.74).multiplyScalar(v); col.push(c.r, c.g, c.b);
    }
    dome.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    room.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })));
    const panel = (hex, i, x, y, z, w, h) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(hex).multiplyScalar(i), side: THREE.DoubleSide }));
      m.position.set(x, y, z); m.lookAt(0, 0, 0); room.add(m);
    };
    panel(0xffffff, 6, -6, 6, 7, 4.5, 4.5);    // two softboxes high left and right of the camera: the sphere's two highlights
    panel(0xffffff, 4, 7, 5, 6, 3.5, 4.5);
    panel(0xffffff, 3, -9, 1, -7, 2.5, 9);     // rims from behind
    panel(0xffffff, 2.2, 9, 2, -7, 2.5, 9);
    const t = pm.fromScene(room, 0.02).texture; pm.dispose(); return t;
  }
  scene.environment = makeEnv();
  const restored = () => {   // after a lost context three.js restores image textures, not the rendered environment: rebuild
    const old = scene.environment; scene.environment = makeEnv(); old.dispose(); size = '';   // it, and have the engine
    version++; if (onLoad) onLoad();   // redraw (the kit picture too), also under reduced motion
  };
  canvas.addEventListener('webglcontextrestored', restored);
  const key = new THREE.DirectionalLight(0xfff1dc, 1.6); key.position.set(-4, 7, 6); scene.add(key);

  // ---- textures: the typeset print (alpha) and the foil's relief
  let loaded = 0, version = 0;   // version: textures loaded, a context restored — the engine re-renders the kit picture
  const ANISO = renderer.capabilities.getMaxAnisotropy();
  const tex = (name, srgb) => new THREE.TextureLoader().load(new URL(`img/exotech-gel-3d/${name}`, base).href, t => {
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = ANISO; t.needsUpdate = true;
    if (++loaded === 3) { version++; if (onLoad) onLoad(); }   // the engine redraws the kit picture with the print on it
  });
  const jarInk = tex('jar-print.png'), boxInk = tex('box-print.png'), foil = tex('foil.jpg');
  foil.wrapS = foil.wrapT = THREE.RepeatWrapping;

  // ---- materials (colours from the packshot and the owner's photos)
  const gold = new THREE.MeshPhysicalMaterial({ color: 0xf3c968, metalness: 1, roughness: 0.07 });
  const goldSoft = new THREE.MeshPhysicalMaterial({ color: 0xd9ad55, metalness: 1, roughness: 0.32, side: THREE.DoubleSide });
  const silver = new THREE.MeshPhysicalMaterial({ color: 0xe3e6ea, metalness: 1, roughness: 0.14, side: THREE.DoubleSide });
  const white = new THREE.MeshPhysicalMaterial({ color: 0xf3f1ec, roughness: 0.38, clearcoat: 0.4, clearcoatRoughness: 0.3, side: THREE.DoubleSide });
  const gel = new THREE.MeshPhysicalMaterial({ color: 0xf1d985, roughness: 0.04, clearcoat: 1, clearcoatRoughness: 0.03, emissive: 0x4a3a10, sheen: 0.5, sheenColor: 0xfff2c0 });
  const dark = new THREE.MeshBasicMaterial({ color: 0x0a0806 });
  const ink = (map) => new THREE.MeshStandardMaterial({ color: 0x161412, roughness: 0.45, metalness: 0, alphaMap: map, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 });
  const foilMat = new THREE.MeshPhysicalMaterial({ color: 0xead27c, metalness: 1, roughness: 0.32, roughnessMap: foil, bumpMap: foil, bumpScale: 0.04, transparent: true });
  const black = new THREE.MeshPhysicalMaterial({ color: 0x0e0e10, roughness: 0.55, metalness: 0, sheen: 0.3, sheenColor: 0x3a3a3a, transparent: true });
  const boxInkMat = ink(boxInk); boxInkMat.transparent = true;

  // ---- the jar, radius 1 (scaled per pose): the lid's dome above the seam (latitude 6.4°, as fitted to the photo),
  // the base below; under the lid a silver threaded collar; on the base a silver shoulder, the white threaded neck and cup, the gel
  const TS = rad(90 - 6.4), G = rad(0.3), SEG = 160;
  const jar = new THREE.Group(), lid = new THREE.Group(), twist = new THREE.Group(); lid.add(twist); jar.add(lid); scene.add(jar);
  const mesh = (g, m, parent, y = 0) => { const x = new THREE.Mesh(g, m); x.position.y = y; parent.add(x); return x; };
  mesh(new THREE.SphereGeometry(1, SEG, 80, 0, Math.PI * 2, TS + G, Math.PI - TS - G), gold, jar);
  mesh(new THREE.SphereGeometry(1, SEG, 80, 0, Math.PI * 2, 0, TS - G), gold, twist);
  const LON = [-42, 42], LAT = [7, 27];   // the print decal (make_textures.py)
  mesh(new THREE.SphereGeometry(1.0012, 192, 40, Math.PI / 2 + rad(LON[0]), rad(LON[1] - LON[0]), rad(90 - LAT[1]), rad(LAT[1] - LAT[0])), ink(jarInk), twist);
  const seam = mesh(new THREE.CylinderGeometry(0.993, 0.993, 0.012, SEG, 1, true), dark, jar, Math.cos(TS));   // the seam's dark line: inside
  // both shells' rims (0.9932 lid, 0.9943 base), in front of the silver shoulder
  const lathe = (pts, m, parent) => mesh(new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), SEG), m, parent);
  const yLid = Math.cos(TS - G), rLid = Math.sin(TS - G), yBase = Math.cos(TS + G), rBase = Math.sin(TS + G);
  const threads = (r, y0, y1, depth, n, out) => {   // a wall of n rounded thread ridges, from y0 to y1
    const pts = []; for (let i = 0; i <= 48; i++) { const y = y0 + (y1 - y0) * i / 48, s = Math.sin(Math.PI * n * i / 48); pts.push([r + (out ? 1 : -1) * depth * s * s, y]); }
    return pts;
  };
  // under the lid: the flat rim, the silver collar with its thread, a white liner at the top
  lathe([[rLid, yLid], [0.83, yLid], [0.81, yLid + 0.01]].concat(threads(0.81, yLid + 0.01, 0.44, 0.014, 3, false)).concat([[0.81, 0.45], [0, 0.45]]), silver, twist);
  mesh(new THREE.RingGeometry(0.83, rLid, SEG).rotateX(Math.PI / 2), goldSoft, twist, yLid - 0.001);
  mesh(new THREE.CircleGeometry(0.8, SEG).rotateX(Math.PI / 2), white, twist, 0.445);
  // the base: silver shoulder, white neck with its thread and the cup's lip, the cup wall down to the gel
  lathe([[rBase, yBase], [0.96, 0.145], [0.86, 0.172], [0.8, 0.178]], silver, jar);
  lathe([[0.8, 0.178], [0.78, 0.182]].concat(threads(0.78, 0.19, 0.33, 0.014, 3, true)).concat([[0.78, 0.345], [0.77, 0.358], [0.745, 0.364], [0.725, 0.356], [0.72, 0.34], [0.72, 0.27]]), white, jar);
  // the gel's surface, outside in (so it faces up): a meniscus at the wall, a soft swirl that catches the light
  lathe([[0.72, 0.312], [0.69, 0.297], [0.6, 0.29], [0.45, 0.293], [0.32, 0.299], [0.2, 0.297], [0.1, 0.303], [0, 0.31]], gel, jar);
  // pearls of gel rising from the open jar (S3)
  const pearls = [0, 1, 2, 3, 4].map(i => { const m = mesh(new THREE.SphereGeometry(1, 48, 24), gel, jar); m.userData = { a: i * 2.4, r: 0.18 + (i % 3) * 0.17, s: 0.055 + (i % 2) * 0.03, ph: i / 5 }; return m; });

  // ---- the box, 1 : 1.13 : 1: a gold foil front with the print, a black top and back, each side cut on the diagonal
  // into black (back, top) and gold (front, bottom), as in the packshot
  const BW = 1, BH = 1.13, BD = 1, box = new THREE.Group(); scene.add(box);
  const face = (geo, m, pos, ry, rx = 0) => { const x = new THREE.Mesh(geo, m); x.position.copy(pos); x.rotation.set(rx, ry, 0); box.add(x); return x; };
  face(new THREE.PlaneGeometry(BW, BH), foilMat, new V3(0, 0, BD / 2), 0);
  face(new THREE.PlaneGeometry(BW, BH * 0.2), boxInkMat, new V3(0, 0, BD / 2 + 0.0015), 0);   // the print band (make_textures.py BAND)
  face(new THREE.PlaneGeometry(BW, BD), black, new V3(0, BH / 2, 0), 0, -Math.PI / 2);
  face(new THREE.PlaneGeometry(BW, BD), black, new V3(0, -BH / 2, 0), 0, Math.PI / 2);
  face(new THREE.PlaneGeometry(BW, BH), black, new V3(0, 0, -BD / 2), Math.PI);
  // a side in (u: back 0 → front 1, v: top 0 → bottom 1); the diagonal from (0.03, 1) to (0.79, 0), measured on the packshot
  const side = (pts, mirror) => { const s = new THREE.Shape(pts.map(([u, v]) => new THREE.Vector2((mirror ? 0.5 - u : u - 0.5) * BD, (0.5 - v) * BH))); return new THREE.ShapeGeometry(s); };
  const GOLD_SIDE = [[0.03, 1], [1, 1], [1, 0], [0.79, 0]], BLACK_SIDE = [[0, 0], [0.79, 0], [0.03, 1], [0, 1]];
  for (const [mirror, x, ry] of [[false, -BW / 2, -Math.PI / 2], [true, BW / 2, Math.PI / 2]]) {
    face(side(GOLD_SIDE, mirror), foilMat, new V3(x, 0, 0), ry);
    face(side(BLACK_SIDE, mirror), black, new V3(x, 0, 0), ry);
  }
  const boxMats = [foilMat, black, boxInkMat];

  // ---- poses per screen: box [cx, cy, height px, opacity, yaw], jar [cx, cy, height px, yaw, tilt toward the camera, open]
  const KEYS = [
    [[470, 760, 470, 1, 0.62], [930, 800, 330, -0.22, 0, 0]],      // meet: as on the packshot
    [[400, 700, 360, 0.3, 0.5], [720, 780, 560, 0.18, 0.04, 0]],   // why: the jar steps forward, the box in the dark
    [[360, 700, 300, 0, 0.5], [640, 840, 560, 0, 0.2, 1]],         // inside: the lid unscrews and lifts over the gel
    [[360, 700, 300, 0, 0.5], [690, 760, 520, 0.5, 0, 0]],         // feel: closed again, turning in the light
    [[360, 700, 300, 0, 0.5], [700, 780, 440, -0.3, 0, 0]],        // protocol
    [[470, 760, 500, 1, 0.62], [950, 800, 350, -0.22, 0, 0]]];     // kit: the packshot again, flies into the offer card
  const D_BOX = DIST + 1.2, D_JAR = DIST;   // depth in front of the camera: the box a little behind the jar
  const mix = (a, b, s) => a.map((x, i) => x + (b[i] - x) * s);
  let lidUp = 0, pearlsOn = 0;   // the last pose, for QA
  const tmp = new V3();
  function pose(p, t) {
    const k = Math.min(KEYS.length - 2, Math.floor(p)), f = p - k, s = f * f * (3 - 2 * f);
    const live = 1 - smooth(4.85, 5, p);   // the idle sway settles on the kit pose, so it matches the card's picture as it lands
    const bx = mix(KEYS[k][0], KEYS[k + 1][0], s), jx = mix(KEYS[k][1], KEYS[k + 1][1], s);
    // the jar: its height in px is its diameter
    const R = world(jx[2] / 2, D_JAR), bob = 0.006 * Math.sin(t * 0.8) * live;
    jar.position.copy(at(jx[0], jx[1], D_JAR, tmp)); jar.position.y += bob * R; jar.scale.setScalar(R);
    jar.rotation.set(jx[4], jx[3] + 0.05 * Math.sin(t * 0.45) * live, 0);
    const open = jx[5], tw = smooth(0, 0.45, open), up = smooth(0.3, 1, open);
    twist.rotation.y = tw * Math.PI / 2;                                  // unscrews: a quarter turn, counter-clockwise from above
    lid.position.set(0, tw * 0.04 + up * 0.62, -up * 0.18); lid.rotation.x = -smooth(0.5, 1, open) * 0.5;   // lifts and tips back
    seam.visible = up < 0.01; lidUp = up; pearlsOn = 0;
    const gap = Math.max(0, yLid + lid.position.y - 0.08 - 0.36);   // from the gel to just under the lifted lid's rim
    for (const m of pearls) {   // only once the lid is well up, and only in the gap under it (never through the lid)
      const u = m.userData, h = (t * 0.07 + u.ph) % 1, o = smooth(0.55, 0.9, up) * smooth(0, 0.15, h) * (1 - smooth(0.75, 1, h));
      m.visible = o > 0.01; m.scale.setScalar(u.s * o); if (m.visible) pearlsOn++;
      m.position.set(Math.cos(u.a + t * 0.2) * u.r, 0.36 + h * gap, Math.sin(u.a + t * 0.2) * u.r * 0.6 + 0.15);
    }
    // the box: its height px is the front's height plus the top's sliver; drawn as the front's
    box.visible = bx[3] > 0.01;
    if (box.visible) {
      const S = world(bx[2] * 0.86, D_BOX) / BH;
      box.position.copy(at(bx[0], bx[1], D_BOX, tmp)); box.scale.setScalar(S); box.rotation.set(0, bx[4] + 0.02 * Math.sin(t * 0.4 + 1) * live, 0);
      for (const m of boxMats) { m.opacity = clamp(bx[3] / 0.3); m.envMapIntensity = bx[3]; }   // «in the dark»: less light, gone below 0.3
    }
  }

  // ---- drawing into the engine's box: the full frame is the cover; the canvas shows the box's part of it
  let quality = 2, size = '', renders = 0, lastT = 0, lastP = 0, lastView = null, trial = null, capped = false;
  const LADDER = [2, 1.5, 1.25], win = [];
  function pace(now, still) {   // fewer pixels when frames run long: a 90-frame median over 24 ms steps down one rung, and
    if (still || capped) { lastT = now; return; }   // the next window keeps it only if frames got ≥ 20 % shorter; if not,
    const dt = lastT ? now - lastT : 0; lastT = now;   // the rate is a cap (low-power 30 Hz), not the GPU: back, no more tries
    if (!dt || dt > 400) return;   // a pause (hidden, idle), not a frame
    win.push(dt); if (win.length < 90) return;
    const m = win.slice().sort((a, b) => a - b)[45], mean = win.reduce((a, v) => a + Math.min(v, 100), 0) / win.length; win.length = 0;
    if (trial) { if (mean > trial.mean * 0.8) { quality = trial.q; capped = true; } trial = null; return; }   // the mean: vsync-
    const i = LADDER.indexOf(quality);   // quantised medians would hide a 30 → 18 ms gain
    if (m > 24 && i < LADDER.length - 1) { trial = { q: quality, mean }; quality = LADDER[i + 1]; }
  }
  function fit(view, pr) {
    const id = `${view.box.w}x${view.box.h}@${pr}`;
    if (id !== size) { renderer.setPixelRatio(pr); renderer.setSize(view.box.w, view.box.h, false); size = id; }
    camera.aspect = view.cover.w / view.cover.h;
    camera.setViewOffset(view.cover.w, view.cover.h, view.box.x - view.cover.x, view.box.y - view.cover.y, view.box.w, view.box.h);
    camera.updateProjectionMatrix();
  }
  function render(p, view) { fit(view, Math.min(view.dpr, quality)); pose(p, view.still ? 0 : view.t); renderer.render(scene, camera); renders++; }
  function draw(p, view) { pace(performance.now(), view.still); lastP = p; lastView = view; render(p, view); }
  let kits = 0;   // kit pictures rendered (QA: none on a phone, none for a toolbar)
  function kit(view) {   // the kit pose rendered once into a picture (the offer card, the flight into it), then the current pose again
    kits++;
    fit(view, view.dpr); pose(KEYS.length - 1, 0); renderer.render(scene, camera);
    const c = document.createElement('canvas'); c.width = canvas.width; c.height = canvas.height; c.getContext('2d').drawImage(canvas, 0, 0);
    if (lastView) render(lastP, lastView);
    return c;
  }
  function dispose() {
    canvas.removeEventListener('webglcontextrestored', restored);
    scene.traverse(o => { if (o.geometry) o.geometry.dispose(); });
    for (const m of [gold, goldSoft, silver, white, gel, dark, foilMat, black, boxInkMat]) m.dispose();
    for (const t of [jarInk, boxInk, foil, scene.environment]) t.dispose();
    renderer.dispose();
  }
  const state = () => ({ quality, capped, pixelRatio: renderer.getPixelRatio(), width: canvas.width, height: canvas.height, renders, loaded, version, kits, lastP, lidUp, pearlsOn });
  return { draw, kit, dispose, state, animated: true };
}
