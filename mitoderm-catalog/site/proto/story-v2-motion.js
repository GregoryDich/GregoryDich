// Site v2 (story_content.V2 pages only; build-vtech.py inlines it into the page's module script, before three.js loads):
// the motion layer z10, the line's soft shapeless haze (a mint glow, two green smokes) placed by the story position p
// (window.__mtP, which the scene writes as it draws; window.__seq().pos without WebGL) screen by screen; a slow drift in time,
// none under reduced motion (p is then rounded). And the page's geometry for the scene and the engine:
// – the opening's free band (desktop: window.__mtBand, viewport css px at scroll 0: the subtitle's foot + 16 to the dock's
//   top − 16, and the header's foot): the scene frames the kit in it (scenes/mitotech-cell-booster.js openCam());
// – the step cards (desktop): the live 3D steps aside while they are on screen, by scroll (html.mt-cards, --mt-cards: out
//   before card 01's picture enters the screen, back only once card 05's has left it; html.mt-cards0 while it is fully
//   out: the scene does not draw), never two pairs on screen at once;
// – the kit card (desktop): while the kit flies onto it (the engine: the card's top from 85 % to 25 % of the screen) the
//   card's body and all on it but the picture wait (--mt-card 0), then show (l 1 → 1.12); at the landing the 3D hands
//   over to the card's own picture in one frame (html.mt-land, --mt-land 1 → 0: the same pose, no cross-fade);
// – phone and tablet (flow): room after each stage block (--mt-gap on the next screen), so the next block's stage enters
//   the screen only once the one before has gone under the header (each block holds its run's end pose, the next one
//   shows its still of that same pose: never two at once); so too the step cards' pictures after the protocol's block,
//   and the kit card's picture after the step cards.
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
  var card = document.querySelector('.kitcard'), landOn = false, landV = -1, cardV = -1, probe = null;
  var desk = function () { return wide.matches && root.classList.contains('story') && !root.classList.contains('flow'); };
  function measure() {
    W = innerWidth; H = innerHeight; size = els.map(function (e) { return [e.offsetWidth, e.offsetHeight]; });
    var card = document.querySelector('.kitcard'), fig = card && card.querySelector('.kc-fig');
    if (fig) {   // the card's background starts under its picture (story-v2.css), half the card's gap below it
      var c = card.getBoundingClientRect(), f = fig.getBoundingClientRect(), gap = parseFloat(getComputedStyle(card).rowGap) || 0;
      card.style.setProperty('--body-top', (f.bottom - c.top - card.clientTop + gap / 2).toFixed(1) + 'px');
    }
    var sub = document.querySelector('#open .open-sub'), dock = document.querySelector('.dock'), head = document.querySelector('.top');
    if (sub && wide.matches) {   // the opening's free band (scroll 0); the dock is fixed, the header sticky
      var dk = dock && getComputedStyle(dock).display !== 'none' ? dock.getBoundingClientRect() : null;
      window.__mtBand = { top: Math.round(sub.getBoundingClientRect().bottom + scrollY + 16), bottom: Math.round(dk ? dk.top - 16 : H - 24),
        head: head ? Math.round(head.getBoundingClientRect().bottom) : 0 };
    } else window.__mtBand = null;
    gaps();
    kick(true);
  }
  function lvh() {   // the large viewport (browser toolbars retracted): the room a block needs does not change as they move
    if (!probe) { probe = document.createElement('div'); probe.setAttribute('aria-hidden', 'true');
      probe.style.cssText = 'position:fixed;left:0;top:0;width:0;height:100vh;height:100lvh;visibility:hidden;pointer-events:none'; document.body.appendChild(probe); }
    return Math.max(innerHeight, probe.offsetHeight);
  }
  var gapRaf = 0;
  function gaps() { if (!gapRaf) gapRaf = requestAnimationFrame(applyGaps); }   // out of the ResizeObserver's callback
  function applyGaps() {   // flow: --mt-gap before what holds the next picture of the product, measured without it (all read, then
    gapRaf = 0;             // written): each stage block, then the step cards' row (after the protocol's block), then the kit card
    var st = Array.prototype.slice.call(document.querySelectorAll('main .stage')), flow = root.classList.contains('flow'), set = [];
    var hb = flow ? document.querySelector('.top').getBoundingClientRect().bottom : 0, room = flow ? lvh() - hb : 0;
    var seq = st.map(function (e) { return [e, e.closest('.sec')]; }), step = document.querySelector('.mt-step figure'), kit = document.querySelector('.kitcard .kc-fig');
    if (step) seq.push([step, step.closest('.mt-prep')]);
    if (kit) seq.push([kit, kit.closest('.sec')]);
    for (var k = 1; k < seq.length; k++) {
      var box = seq[k][1]; if (!box) continue;
      var old = parseFloat(box.style.getPropertyValue('--mt-gap')) || 0, g = 0;
      if (flow && seq[k - 1][0].offsetHeight && seq[k][0].offsetHeight) {
        var dist = seq[k][0].getBoundingClientRect().top - old - seq[k - 1][0].getBoundingClientRect().bottom;
        g = Math.max(0, Math.ceil(room - dist + 4));
      }
      if (Math.abs(g - old) > 0.5) set.push([box, g]);
    }
    set.forEach(function (x) { if (x[1]) x[0].style.setProperty('--mt-gap', x[1] + 'px'); else x[0].style.removeProperty('--mt-gap'); });
  }
  function pos() {
    if (typeof window.__mtP === 'number') return window.__mtP;
    try { return window.__seq ? window.__seq().pos || 0 : 0; } catch (e) { return 0; }
  }
  function land() {   // desktop, the kit's flight onto the card (l 0 → 1 as the card's top goes from 85 % to 25 % of the screen)
    var on = false, l = 0, v = 1, cv = 1;
    if (card && desk()) {
      var t = card.getBoundingClientRect().top / H; l = (0.85 - t) / 0.6;
      on = t < 1; v = l < 1 ? 1 : 0; cv = Math.max(0, Math.min(1, (l - 1) / 0.12));
    }
    if (on !== landOn) { root.classList.toggle('mt-land', on); landOn = on; }
    if (v !== landV) { root.style.setProperty('--mt-land', String(v)); landV = v; }
    if (Math.abs(cv - cardV) > 0.002 || (cv !== cardV && (cv === 0 || cv === 1))) { root.style.setProperty('--mt-card', cv.toFixed(3)); cardV = cv; }
  }
  function frame(now) {
    raf = 0; land(); cards(); if (!els.length || document.hidden) return;
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
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
  measure();

  var figs = Array.prototype.slice.call(document.querySelectorAll('.mt-step figure')), cardsV = -1;
  function cards() {   // desktop: 1 (the 3D shown) … 0 (out): out as card 01's picture top comes from 130 % to 100 % of the screen
    var v = 1;          // (before it enters), back as card 05's picture foot goes from 0 to −30 % (after it has left)
    if (figs.length && desk()) {
      var a = figs[0].getBoundingClientRect().top / H, b = figs[figs.length - 1].getBoundingClientRect().bottom / H;
      v = Math.max(Math.min(1, Math.max(0, (a - 1) / 0.3)), Math.min(1, Math.max(0, -b / 0.3)));
    }
    if (Math.abs(v - cardsV) < 0.002 && !(v !== cardsV && (v === 0 || v === 1))) return;
    cardsV = v; root.classList.toggle('mt-cards', v < 1); root.classList.toggle('mt-cards0', v === 0);
    root.style.setProperty('--mt-cards', v.toFixed(3));
  }
})();
