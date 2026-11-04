// Site v2 (story_content.V2 pages only; build-vtech.py inlines it into the page's module script, before three.js loads):
// the motion layer z10, the line's soft shapeless haze (a mint glow, two green smokes) placed by the story position p
// (window.__mtP, which the scene writes as it draws; window.__seq().pos without WebGL) screen by screen; a slow drift in time,
// none under reduced motion (p is then rounded). Desktop: the live 3D steps aside while the step cards fill the middle of the
// screen (html.mt-cards), and it hands over to the kit card's own picture before the rising card reaches it (html.mt-land,
// --mt-land: the product is never cut by the card). Phone: while the canvas plays the opening in its block, S1's block below
// does not show its still of the same kit (html.mt-open). The kit card's picture window (--fig-top, --fig-h) for its opaque
// background (story-v2.css).
(function () {
  var root = document.documentElement, haze = document.querySelector('.mt-haze');
  var calm = matchMedia('(prefers-reduced-motion: reduce)'), small = matchMedia('(max-width: 899px)'), wide = matchMedia('(min-width: 900px)');
  // per screen p = 0 … 6: [x %, y % of the viewport (the ellipse's centre), scale, opacity] for the glow, smoke a, smoke b
  var P = [
    [[50, 64, 1.2, .85], [30, 76, 1, .50], [70, 70, 1, .40]],   // the opening: the glow behind the kit (its middle at 63 %)
    [[27, 52, 1, .70], [18, 70, 1, .35], [40, 30, 1, .25]],     // S1
    [[30, 48, 1, .30], [22, 60, 1.3, .75], [36, 42, 1.2, .65]], // S2: the green smoke thickens
    [[28, 55, 1, .75], [20, 68, 1, .45], [38, 40, 1, .35]],     // S3: light behind the pair
    [[28, 68, 1.4, .90], [22, 74, 1, .60], [36, 56, 1, .55]],   // S4: an even glow, mint and green in turn
    [[27, 62, 1, .35], [20, 82, 1, .20], [38, 80, 1, .20]],     // S5: the haze settles
    [[27, 54, 1.2, .95], [18, 70, 1, .40], [40, 36, 1, .30]]];  // the kit and the offer: the strongest glow, behind the card
  var els = haze ? Array.prototype.slice.call(haze.children) : [], size = [], W = 0, H = 0, raf = 0, tm = 0, lastP = -1;
  var card = document.querySelector('.kitcard'), openStage = document.querySelector('#open .stage'), landOn = false, landV = -1, openOn = false;
  function measure() {
    W = innerWidth; H = innerHeight; size = els.map(function (e) { return [e.offsetWidth, e.offsetHeight]; });
    var card = document.querySelector('.kitcard'), fig = card && card.querySelector('.kc-fig');
    if (fig) {
      var c = card.getBoundingClientRect(), f = fig.getBoundingClientRect();
      card.style.setProperty('--fig-top', (f.top - c.top - card.clientTop).toFixed(1) + 'px');
      card.style.setProperty('--fig-h', f.height.toFixed(1) + 'px');
    }
    kick(true);
  }
  function pos() {
    if (typeof window.__mtP === 'number') return window.__mtP;
    try { return window.__seq ? window.__seq().pos || 0 : 0; } catch (e) { return 0; }
  }
  function land() {   // desktop: the card's top from 90 % to 80 % of the screen fades the 3D out and the card's picture in
    var on = false, v = 1;
    if (card && wide.matches && root.classList.contains('story') && !root.classList.contains('flow')) {
      var t = card.getBoundingClientRect().top / H; v = Math.max(0, Math.min(1, (t - 0.8) / 0.1)); on = t < 0.9;
    }
    if (on !== landOn) { root.classList.toggle('mt-land', on); landOn = on; }
    if (on && Math.abs(v - landV) > 0.002) { root.style.setProperty('--mt-land', v.toFixed(3)); landV = v; }
  }
  function opening() {   // phone: the canvas is in the opening's block until that block has gone under the header (the engine's place())
    var on = false;
    if (openStage && root.classList.contains('flow')) on = openStage.getBoundingClientRect().bottom > (parseFloat(root.style.getPropertyValue('--stage-top')) || 0);
    if (on !== openOn) { root.classList.toggle('mt-open', on); openOn = on; }
  }
  function frame(now) {
    raf = 0; land(); opening(); if (!els.length || document.hidden) return;
    var still = calm.matches, p = Math.max(0, Math.min(6, pos())); if (still) p = Math.round(p);
    var i = Math.min(5, Math.floor(p)), f = p - i, t = still ? 0 : now / 1000, ph = small.matches;
    var w4 = Math.max(0, 1 - Math.abs(p - 4)), tint = 0.5 + 0.5 * Math.sin(t * Math.PI / 8);   // S4: mint ↔ green, 16 s
    els.forEach(function (el, n) {
      var a = P[i][n], b = P[i + 1][n], v = a.map(function (x, k) { return x + (b[k] - x) * f; });
      if (ph) { v[0] = 50; v[1] = 45; v[3] *= 0.7; }
      if (n === 0) v[3] *= 1 - 0.35 * w4 * tint; else if (n === 2) v[3] += 0.2 * w4 * tint;
      var dx = 2 * Math.sin(t * Math.PI / 20 + n * 2.1), dy = 1.2 * Math.cos(t * Math.PI / 20 + n * 1.3);   // ±2 vw over 40 s
      var x = (v[0] + dx) * W / 100 - size[n][0] / 2, y = (v[1] + dy) * H / 100 - size[n][1] / 2;
      el.style.transform = 'translate3d(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px,0) scale(' + v[2].toFixed(3) + ')';
      el.style.opacity = Math.min(1, v[3]).toFixed(3);
    });
    lastP = p;
    if (!still) { clearTimeout(tm); tm = setTimeout(kick, 50); }   // the drift: about 20 updates a second (one timer), scrolling redraws at once
  }
  function kick(force) { if (!raf && (force === true || !calm.matches || pos() !== lastP)) raf = requestAnimationFrame(frame); }
  addEventListener('scroll', function () { kick(true); }, { passive: true });
  addEventListener('resize', measure);
  addEventListener('load', measure);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) kick(true); });
  calm.addEventListener('change', measure); small.addEventListener('change', measure);
  if (window.ResizeObserver) new ResizeObserver(measure).observe(document.querySelector('main') || root);
  measure();

  var steps = document.querySelector('.mt-steps'), off = 0;
  function cards(on) {
    if (root.classList.contains('mt-cards') === on) return;
    root.classList.add('mt-fade'); root.classList.toggle('mt-cards', on);
    clearTimeout(off); off = setTimeout(function () { root.classList.remove('mt-fade'); }, 350);
  }
  if (steps && 'IntersectionObserver' in window) {
    var inBand = false;
    new IntersectionObserver(function (es) { inBand = es[es.length - 1].isIntersecting; cards(inBand && wide.matches); },
      { rootMargin: '-15% 0px -15% 0px' }).observe(steps);
    wide.addEventListener('change', function () { cards(inBand && wide.matches); });
  }
})();
