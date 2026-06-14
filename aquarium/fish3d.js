/* ============================================================
   3D-рыбы (Three.js) — слой поверх 2D-рифа.
   Настоящие 3D-модели: тело изгибается, хвост виляет, рыбы
   кренятся на поворотах и плавают в объёме (как в оригинале).
   Если WebGL недоступен — тихо выключаемся, остаются 2D-рыбки.
   ============================================================ */
(function () {
  "use strict";
  window.__FISH3D = false;
  const THREE = window.THREE;
  const canvas = document.getElementById("fish3d");
  if (!THREE || !canvas) return;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    if (!renderer.getContext()) return;
  } catch (e) { return; }

  const DPR = Math.min(window.devicePixelRatio || 1, 2);
  renderer.setPixelRatio(DPR);
  renderer.setClearColor(0x000000, 0); // прозрачный фон — снизу виден риф

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x1f74aa, 24, 52); // подводная дымка вдаль

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
  camera.position.set(0, 0, 20);

  // свет: солнце сверху-сбоку + холодный подсвет снизу
  const key = new THREE.DirectionalLight(0xffffff, 1.15); key.position.set(-5, 11, 8); scene.add(key);
  scene.add(new THREE.HemisphereLight(0xcdeeff, 0x18415a, 0.95));
  scene.add(new THREE.AmbientLight(0x6fa6c8, 0.32));

  /* ---------- виды рыб ---------- */
  const SPECIES = [
    { name: "clown",  color: 0xff7a1f, fin: 0xff8a33, bands: true,  size: [1.5, 2.2], w: 3 },
    { name: "blue",   color: 0x1f6fd0, fin: 0xffce1f, tail: 0xffce1f, size: [1.7, 2.4], w: 2 },
    { name: "yellow", color: 0xffce1f, fin: 0xffb400, size: [1.3, 1.9], w: 2 },
    { name: "purple", color: 0x9b50d0, fin: 0xc98ef0, size: [1.2, 1.7], w: 2 },
    { name: "red",    color: 0xe23b3b, fin: 0xff6a5a, size: [1.3, 1.9], w: 2 },
    { name: "teal",   color: 0x27b3bd, fin: 0x86e3e8, size: [1.1, 1.6], w: 3 },
  ];
  function pickSpecies() {
    let tot = 0; for (const s of SPECIES) tot += s.w;
    let r = Math.random() * tot;
    for (const s of SPECIES) { r -= s.w; if (r <= 0) return s; }
    return SPECIES[0];
  }

  /* ---------- геометрия ---------- */
  const taper = (z) => (z < 0 ? 0.28 + 0.72 * (z + 1) : 1 - 0.35 * z * z); // -1..1 вдоль тела

  function bodyGeo() {
    const g = new THREE.SphereGeometry(1, 30, 18);
    const p = g.attributes.position, v = new THREE.Vector3();
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i);
      const tp = taper(v.z);
      p.setXYZ(i, v.x * 0.34 * tp, v.y * 0.42 * tp, v.z * 1.0);
    }
    g.computeVertexNormals();
    return g;
  }
  function triGeo(verts) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(verts.flat(), 3));
    g.computeVertexNormals();
    return g;
  }
  const TAIL = [
    [0, 0, 0], [0, 0.55, -0.85], [0, 0, -0.55],
    [0, 0, 0], [0, 0, -0.55], [0, -0.55, -0.85],
  ];
  const DORSAL = [[0, 0.30, 0.32], [0, 0.74, -0.10], [0, 0.24, -0.55]];
  const PECT_R = [[0.26, 0.02, 0.28], [0.62, -0.20, 0.04], [0.30, -0.06, -0.04]];
  const PECT_L = PECT_R.map((p) => [-p[0], p[1], p[2]]);

  function makeFish(sp) {
    const group = new THREE.Group();
    const col = new THREE.Color(sp.color);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: col, roughness: 0.5, metalness: 0.0, emissive: col.clone().multiplyScalar(0.05),
    });
    const finMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(sp.tail || sp.fin), roughness: 0.6, metalness: 0.0, side: THREE.DoubleSide,
    });

    const body = new THREE.Mesh(bodyGeo(), bodyMat);
    group.add(body);
    body.add(new THREE.Mesh(triGeo(DORSAL), finMat));
    body.add(new THREE.Mesh(triGeo(PECT_R), finMat));
    body.add(new THREE.Mesh(triGeo(PECT_L), finMat));

    // хвост на вилочном шарнире (виляет)
    const tailPivot = new THREE.Group(); tailPivot.position.set(0, 0, -0.92);
    tailPivot.add(new THREE.Mesh(triGeo(TAIL), finMat));
    group.add(tailPivot);

    // глаза
    const eyeW = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.4 });
    const eyeB = new THREE.MeshStandardMaterial({ color: 0x10141a });
    for (const s of [1, -1]) {
      const w = new THREE.Mesh(new THREE.SphereGeometry(0.1, 12, 12), eyeW);
      w.position.set(s * 0.17, 0.13, 0.6); group.add(w);
      const b = new THREE.Mesh(new THREE.SphereGeometry(0.055, 10, 10), eyeB);
      b.position.set(s * 0.2, 0.13, 0.67); group.add(b);
    }

    // белые полосы рыбы-клоуна (кольца вокруг тела)
    if (sp.bands) {
      const bandMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.5 });
      for (const z of [0.42, 0.0, -0.45]) {
        const R = 0.4 * taper(z);
        const ring = new THREE.Mesh(new THREE.TorusGeometry(R * 1.03, R * 0.2, 8, 22), bandMat);
        ring.position.z = z; group.add(ring);
      }
    }

    const sc = sp.size[0] + Math.random() * (sp.size[1] - sp.size[0]);
    group.scale.setScalar(sc * 0.9);
    return { group, tailPivot };
  }

  /* ---------- объём плавания ---------- */
  function bounds() {
    const vH = Math.tan((camera.fov * Math.PI / 180) / 2) * camera.position.z;
    return { x: vH * camera.aspect * 0.9, y: vH * 0.8, zMin: -10, zMax: 6 };
  }
  function newTarget(f) {
    const b = bounds();
    f.target.set(
      (Math.random() * 2 - 1) * b.x,
      (Math.random() * 1.55 - 0.7) * b.y,
      b.zMin + Math.random() * (b.zMax - b.zMin)
    );
  }

  /* ---------- рыбы ---------- */
  const fishes = [];
  const _fwd = new THREE.Vector3(), _up = new THREE.Vector3(0, 1, 0),
        _right = new THREE.Vector3(), _up2 = new THREE.Vector3(),
        _m = new THREE.Matrix4(), _qH = new THREE.Quaternion(), _qB = new THREE.Quaternion();

  function spawnFish() {
    const sp = pickSpecies();
    const mesh = makeFish(sp);
    const b = bounds();
    mesh.group.position.set((Math.random() * 2 - 1) * b.x, (Math.random() * 2 - 1) * b.y * 0.7,
                            b.zMin + Math.random() * (b.zMax - b.zMin));
    scene.add(mesh.group);
    const f = {
      group: mesh.group, tailPivot: mesh.tailPivot,
      dir: new THREE.Vector3(Math.random() * 2 - 1, (Math.random() - 0.5) * 0.2, Math.random() * 2 - 1).normalize(),
      target: new THREE.Vector3(), speed: 1.8 + Math.random() * 2.0,
      bank: 0, wagFreq: 6 + Math.random() * 4, wagAmp: 0.28 + Math.random() * 0.22,
      phase: Math.random() * Math.PI * 2,
    };
    newTarget(f);
    fishes.push(f);
  }

  function updateFish(f, dt, t) {
    const toT = f.target.clone().sub(f.group.position);
    if (toT.length() < 2.2) newTarget(f);
    const desired = toT.normalize();
    const prevX = f.dir.x;
    f.dir.lerp(desired, 1 - Math.exp(-dt * 1.1)).normalize();
    f.group.position.addScaledVector(f.dir, f.speed * dt);

    // крен в повороте
    const turn = f.dir.x - prevX;
    const targetBank = THREE.MathUtils.clamp(-turn * 60, -0.6, 0.6);
    f.bank += (targetBank - f.bank) * (1 - Math.exp(-dt * 3));

    // ориентация: нос (+z) вдоль направления, верх — вверх; затем крен вокруг направления
    _fwd.copy(f.dir);
    _right.crossVectors(_up, _fwd);
    if (_right.lengthSq() < 1e-6) _right.set(1, 0, 0);
    _right.normalize();
    _up2.crossVectors(_fwd, _right).normalize();
    _m.makeBasis(_right, _up2, _fwd);
    _qH.setFromRotationMatrix(_m);
    _qB.setFromAxisAngle(_fwd, f.bank);
    f.group.quaternion.copy(_qB).multiply(_qH);

    // вилять хвостом
    f.tailPivot.rotation.y = Math.sin(t * f.wagFreq + f.phase) * f.wagAmp;
  }

  /* ---------- размеры / цикл ---------- */
  function resize() {
    const W = window.innerWidth, H = window.innerHeight;
    renderer.setSize(W, H, false);
    camera.aspect = W / H; camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener("resize", resize);

  const N = Math.min(18, Math.max(8, Math.round((window.innerWidth * window.innerHeight) / 110000)));
  for (let i = 0; i < N; i++) spawnFish();

  let last = performance.now(), acc = 0;
  function loop(now) {
    requestAnimationFrame(loop);
    let dt = (now - last) / 1000; last = now;
    if (dt > 0.1) dt = 0.1;
    const power = window.__AQ_POWER || "high";
    if (power === "paused" || document.hidden) return;
    acc += dt;
    const step = power === "low" ? 1 / 30 : 0;
    if (acc < step) return;
    const fdt = Math.min(acc, 0.05); acc = 0;
    const t = now / 1000;
    for (const f of fishes) updateFish(f, fdt, t);
    renderer.render(scene, camera);
  }

  window.AquariumFish3D = { setPower: (m) => { window.__AQ_POWER = m; } };
  window.__FISH3D = true;
  requestAnimationFrame(loop);
})();
