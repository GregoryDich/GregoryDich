(function () {
  var root = document.documentElement;
  var M = window.Motion;
  if (!M) { root.classList.remove('js'); return; }
  window.__mdMotion = true;
  try {
    var animate = M.animate, inView = M.inView, scroll = M.scroll, stagger = M.stagger;
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var ease = [0.16, 1, 0.3, 1];
    var $ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

    // Focal moment: the title settles, the gold rule draws, the product families rise onto their light.
    var hero = document.querySelector('[data-hero]');
    if (hero && !reduce) {
      animate(hero.querySelector('.hero__title'),
        { opacity: [0, 1], clipPath: ['inset(0 0 100% 0)', 'inset(0 0 0% 0)'], transform: ['translateY(18px)', 'translateY(0px)'] },
        { duration: 0.75, ease: ease });
      animate(hero.querySelector('.hero__rule'), { transform: ['scaleX(0)', 'scaleX(1)'] }, { duration: 0.7, delay: 0.18, ease: ease });
      animate($('.hero__sub, .hero__latin', hero), { opacity: [0, 1], transform: ['translateY(8px)', 'translateY(0px)'] },
        { duration: 0.5, delay: stagger(0.06, { startDelay: 0.22 }), ease: ease });
      animate($('.shelf .glow', hero), { opacity: [0, 1], transform: ['scaleX(0.4)', 'scaleX(1)'] },
        { duration: 0.9, delay: stagger(0.1, { startDelay: 0.3 }), ease: ease });
      animate($('.shelf .pic', hero), { opacity: [0, 1], transform: ['translateY(40px)', 'translateY(0px)'] },
        { duration: 0.8, delay: stagger(0.07, { startDelay: 0.38 }), ease: ease });
      animate($('.shelf__title, .shelf__links', hero), { opacity: [0, 1], transform: ['translateY(8px)', 'translateY(0px)'] },
        { duration: 0.5, delay: stagger(0.05, { startDelay: 0.6 }), ease: ease });
    }

    // Product plates rise once, the first time they come into view.
    $('.protocol .plate, .maintain .plate').forEach(function (plate) {
      if (reduce) return;
      inView(plate, function () {
        animate($('.pic', plate), { opacity: [0, 1], transform: ['translateY(26px)', 'translateY(0px)'] },
          { duration: 0.7, delay: stagger(0.1), ease: ease });
      }, { amount: 0.3 });
    });

    // Step sequences: the gold line follows reading progress, each marker fills once its step is reached.
    $('.steps-wrap').forEach(function (wrap) {
      var bar = wrap.querySelector('.steps__bar');
      if (bar && !reduce) {
        scroll(animate(bar, { transform: ['scaleY(0)', 'scaleY(1)'] }, { ease: 'linear' }),
          { target: wrap, offset: ['start 70%', 'end 70%'] });
      }
      $('.step', wrap).forEach(function (step) {
        inView(step, function () { step.classList.add('is-reached'); }, { margin: '0px 0px -30% 0px' });
      });
    });

    // Peel stages: the connector draws across the three stages in order.
    $('.stages-wrap').forEach(function (wrap) {
      if (reduce) return;
      inView(wrap, function () {
        animate(wrap.querySelector('.stages__line'), { transform: ['scaleX(0)', 'scaleX(1)'] }, { duration: 0.9, ease: ease });
        animate($('.stage__num', wrap), { opacity: [0, 1], transform: ['scale(0.6)', 'scale(1)'] },
          { duration: 0.5, delay: stagger(0.16, { startDelay: 0.1 }), ease: ease });
      }, { amount: 0.25 });
    });

    // Sticky header: hairline once the page scrolls; the indicator follows the protocol family in view.
    var header = document.querySelector('.site-header');
    var sentinel = document.querySelector('.top-sentinel');
    if (header && sentinel) {
      inView(sentinel, function () {
        header.classList.remove('is-stuck');
        return function () { header.classList.add('is-stuck'); };
      });
    }
    var nav = document.querySelector('.nav');
    var ind = nav && nav.querySelector('.nav__ind');
    var links = nav ? $('a[data-target]', nav) : [];
    var current = null;
    function place(instant) {
      if (!ind) return;
      var a = null;
      links.forEach(function (l) {
        var on = l.getAttribute('data-target') === current;
        l.classList.toggle('is-active', on);
        if (on) { a = l; l.setAttribute('aria-current', 'true'); } else { l.removeAttribute('aria-current'); }
      });
      if (!a) { animate(ind, { opacity: 0 }, { duration: 0.2 }); return; }
      var transform = 'translateX(' + (a.offsetLeft + 12) + 'px) scaleX(' + ((a.offsetWidth - 24) / 100) + ')';
      animate(ind, { opacity: 1, transform: transform }, { duration: instant || reduce ? 0 : 0.45, ease: ease });
      if (nav.scrollWidth > nav.clientWidth) {
        a.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: reduce ? 'auto' : 'smooth' });
      }
    }
    $('[data-section]').forEach(function (section) {
      inView(section, function () {
        current = section.id; place(false);
        return function () { if (current === section.id) { current = null; place(false); } };
      }, { margin: '-40% 0px -55% 0px' });
    });
    window.addEventListener('resize', function () { place(true); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { place(true); });
  } catch (e) {
    root.classList.remove('js');
  }
})();
