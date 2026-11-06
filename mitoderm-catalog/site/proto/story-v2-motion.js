// Site v2 (story_content.V2 pages only; build-vtech.py inlines it into the page's module script, before three.js loads):
// the motion layer z10, the line's soft shapeless haze (a mint glow, two green smokes) placed by the story position p
// (window.__mtP, which the scene writes as it draws; window.__seq().pos without WebGL) screen by screen; a slow drift in time,
// none under reduced motion (p is then rounded). And the page's geometry for the scene and the engine:
// – the opening's free band (desktop: window.__mtBand, viewport css px at scroll 0: the subtitle's foot + 16 to the dock's
//   top − 16, and the header's foot): the scene frames the kit in it (scenes/mitotech-cell-booster.js openCam());
// – the step cards (desktop): the live 3D steps aside while they are on screen, by scroll (window.__mtCards 1 → 0 → 1:
//   the scene sends the pair back into the dark and brings it back; html.mt-cards0 while it is fully out: the canvas is
//   hidden and the scene does not draw): out as card 01's drawn picture comes up to the screen's foot, back only once card
//   05's has left the screen's top (each picture's transparent margins measured): never two pairs on screen at once,
//   never a stage with neither;
// – the kit card (desktop): while the kit flies onto it (the engine: the card's top from 85 % to 25 % of the screen) the
//   card's body and all on it but the picture wait (--mt-card 0), then show (l 1 → 1.12); at the landing the 3D hands
//   over to the card's own picture in one frame (html.mt-land, --mt-land 1 → 0: the same pose, no cross-fade);
// – phone and tablet (flow): room after each stage block (--mt-gap on the next screen), so the next block's product
//   enters the screen only once the one before has gone under the header (each block holds its run's end pose, the next
//   one shows its still of that same pose, at the same place in its block: never two at once; measured on the products,
//   not the blocks, so no screen between them is emptier than it must be); so too the step cards' pictures after the
//   protocol's block, and the kit card's picture after the step cards;
// – a tablet turned or a window resized across 899 px (desktop screens ↔ phone blocks: another page): the place being
//   read is kept and put back under the screen's reading line once the other layout is in.
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
  var els = haze ? Array.prototype.slice.call(haze.children) : [], size = [], W = 0, H = 0, raf = 0, tm = 0, lastP = -1, hdr = 0;
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
    hdr = head ? head.getBoundingClientRect().bottom : 0;
    if (sub && wide.matches) {   // the opening's free band (scroll 0); the dock is fixed, the header sticky
      var dk = dock && getComputedStyle(dock).display !== 'none' ? dock.getBoundingClientRect() : null;
      window.__mtBand = { top: Math.round(sub.getBoundingClientRect().bottom + scrollY + 16), bottom: Math.round(dk ? dk.top - 16 : H - 24),
        head: head ? Math.round(head.getBoundingClientRect().bottom) : 0 };
    } else window.__mtBand = null;
    gaps(); remember();   // remember: also without a scroll yet (a page opened at a link)
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
        var a = seq[k - 1][0].getBoundingClientRect(), b = seq[k][0].getBoundingClientRect(), dist = b.top - old - a.bottom;
        // two stage blocks: the block before ends holding the pose the next one's still shows, at the same place in its
        // block (the engine places both by one cover); its product's foot there against the still's top. The scene's run
        // has ended by then (its canvas's top 8 px under the header), and the canvas moves on only after this block
        var s = k < st.length && seq[k][0].querySelector('.stage-still'), r = s && s.getBoundingClientRect();
        if (r && r.height) dist = (r.top - old) - (a.top + r.bottom - b.top);
        g = Math.max(0, Math.ceil(room - dist + 4));
      }
      if (Math.abs(g - old) > 0.5) set.push([box, g]);
    }
    set.forEach(function (x) { if (x[1]) x[0].style.setProperty('--mt-gap', x[1] + 'px'); else x[0].style.removeProperty('--mt-gap'); });
    if (turned) restore();
  }
  // a tablet turned (or a window resized) across 899 px: desktop screens ↔ phone blocks, another page, where the browser's
  // own anchoring lands the reader elsewhere (S5 → the footer). The place being read is kept on scroll (the stretch between
  // two marks – a screen's top, the step cards', the footer's – that the screen's reading line is in, and how far into it)
  // and put back under that line once the other layout's gaps are written (applyGaps, the frame after the flip)
  var marks = Array.prototype.slice.call(document.querySelectorAll('main > section, .mt-prep, .foot')), at = null, atQ = small.matches, turned = false;
  function stretch() {   // the marks shown and their tops in the page, the page's foot last
    var m = marks.filter(function (e) { return e.getClientRects().length; });
    return { m: m, t: m.map(function (e) { return e.getBoundingClientRect().top + scrollY; }).concat(root.scrollHeight) };
  }
  function remember() {
    if (small.matches !== atQ) return;   // the query has flipped: this scroll is the browser's, not the reader's
    var s = stretch(), y = scrollY + 0.4 * innerHeight, i = 0; if (!s.m.length) return;
    while (i < s.m.length - 1 && s.t[i + 1] <= y) i++;
    at = [s.m[i], Math.max(0, Math.min(1, (y - s.t[i]) / Math.max(1, s.t[i + 1] - s.t[i]))),
      scrollY < 1 ? -1 : scrollY > root.scrollHeight - innerHeight - 2 ? 1 : 0];   // at the page's top or foot: stays there
  }
  function restore() {
    turned = false; atQ = small.matches;
    var s = stretch(), i = at ? s.m.indexOf(at[0]) : -1; if (i < 0) return;
    scrollTo(0, at[2] < 0 ? 0 : at[2] > 0 ? root.scrollHeight : Math.round(s.t[i] + at[1] * (s.t[i + 1] - s.t[i]) - 0.4 * innerHeight));
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
  addEventListener('scroll', function () { remember(); kick(true); }, { passive: true });
  addEventListener('resize', measure);
  addEventListener('load', measure);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) kick(true); });
  calm.addEventListener('change', measure); small.addEventListener('change', function () { turned = true; measure(); });
  if (window.ResizeObserver) new ResizeObserver(measure).observe(document.querySelector('main') || root);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
  measure();

  var figs = Array.prototype.slice.call(document.querySelectorAll('.mt-step img')), cardsV = -1, inked = [];
  function ink(n) {   // a step picture's drawn part: [top, foot] as fractions of its box (its transparent margins), measured once
    if (inked[n]) return inked[n];
    var im = figs[n], r = [0, 1];
    if (!im.complete || !im.naturalWidth) return r;   // not there yet: its box
    try {
      var w = 120, h = Math.max(1, Math.round(w * im.naturalHeight / im.naturalWidth)), c = document.createElement('canvas'), x, d, t = -1, b = -1;
      c.width = w; c.height = h; x = c.getContext('2d'); x.drawImage(im, 0, 0, w, h); d = x.getImageData(0, 0, w, h).data;
      for (var i = 3; i < d.length; i += 4) if (d[i] > 8) { if (t < 0) t = Math.floor(i / 4 / w); b = Math.floor(i / 4 / w); }
      if (t >= 0) r = [t / h, (b + 1) / h];
    } catch (e) {}
    return (inked[n] = r);
  }
  function cards() {   // desktop: 1 (the 3D shown) … 0 (stepped aside): out as card 01's drawn picture comes from 145 % to 100 %
    var v = 1;          // of the screen (before it enters), back as card 05's drawn picture goes on from the header's foot by 45 %
    if (figs.length && desk()) {   // (and at least 400 px: the pair's steps into the dark stay small on a short screen)
      var A = figs[0].getBoundingClientRect(), B = figs[figs.length - 1].getBoundingClientRect(), ia = ink(0), ib = ink(figs.length - 1);
      var a = (A.top + ia[0] * A.height) / H, b = (B.top + ib[1] * B.height - hdr) / H, w = Math.max(0.45, 400 / H);
      v = Math.max(Math.min(1, Math.max(0, (a - 1) / w)), Math.min(1, Math.max(0, -b / w)));
    }
    window.__mtCards = v;   // the scene (run 5's branch) sends the pair back into the dark by it
    if (Math.abs(v - cardsV) < 0.002 && !(v !== cardsV && (v === 0 || v === 1))) return;
    cardsV = v; root.classList.toggle('mt-cards', v < 1); root.classList.toggle('mt-cards0', v === 0);
    root.style.setProperty('--mt-cards', v.toFixed(3));
  }
})();
