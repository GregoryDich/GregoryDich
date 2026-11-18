// Dumps visible text, headings, links, forms and media of every route (desktop 1440x900) to JSON + TXT. Read-only: never submits.
const fs = require('fs'); const { open } = require('./px.cjs');
const routes = ['/', '/catalog', '/privacy', ...['v-tech-system','exo-nad','exotech-gel','exocell-mask','exosignal-hair','exosignal-spray','micro-boost-10','cellular-age-defense-2-5','cell-renew-1-5','derma-recovery-cream','mitopen','mitoscan','mitotech-cell-booster'].map(s => '/products/' + s)];
(async () => {
  const out = process.argv[2]; const base = process.env.BASE || 'https://mitoderm-cinematic.evenradish1.chatgpt.site';
  for (const route of routes) {
    const { browser, page, log } = await open({ width: 1440, height: 900 });
    try {
      const t0 = Date.now();
      const resp = await page.goto(base + route, { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.waitForTimeout(4000);
      const H = await page.evaluate(() => document.documentElement.scrollHeight);
      for (let y = 0; y < H; y += 700) { await page.evaluate(v => scrollTo(0, v), y); await page.waitForTimeout(250); }
      const d = await page.evaluate(() => {
        const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
        const tx = e => (e.innerText || e.textContent || '').replace(/\s+/g, ' ').trim();
        return {
          title: document.title, lang: document.documentElement.lang, dir: document.documentElement.dir,
          metaDescription: (document.querySelector('meta[name=description]') || {}).content || '',
          headings: [...document.querySelectorAll('h1,h2,h3,h4')].map(h => h.tagName + ': ' + tx(h)).filter(s => s.length > 4),
          buttons: [...document.querySelectorAll('button,a')].map(b => ({ t: tx(b).slice(0, 80), href: b.getAttribute('href') || '', aria: b.getAttribute('aria-label') || '' })).filter(b => b.t || b.aria),
          forms: [...document.querySelectorAll('form')].map(f => [...f.querySelectorAll('input,select,textarea,button')].map(i => ({ tag: i.tagName, type: i.type, name: i.name, ph: i.placeholder || '', req: i.required || false, label: (i.labels && i.labels[0] ? tx(i.labels[0]) : '') || i.getAttribute('aria-label') || '' }))),
          images: [...document.querySelectorAll('img')].map(i => ({ src: (i.currentSrc || i.src).split('?')[0].split('/').slice(-2).join('/').slice(-70), alt: i.alt, nw: i.naturalWidth, nh: i.naturalHeight, cw: Math.round(i.getBoundingClientRect().width), ch: Math.round(i.getBoundingClientRect().height) })),
          videos: [...document.querySelectorAll('video')].map(v => ({ src: (v.currentSrc || v.src).split('/').slice(-1)[0], w: v.videoWidth, h: v.videoHeight, dur: +(v.duration || 0).toFixed(1) })),
          jsonld: document.querySelectorAll('script[type="application/ld+json"]').length,
          text: (document.body.innerText || '').replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim(),
        };
      });
      const slug = route === '/' ? 'home' : route.replace(/^\/(products\/)?/, '');
      const meta = { route, status: resp ? resp.status() : 0, pageHeight: H, loadMs: Date.now() - t0, transferMB: +(log.bytes / 1e6).toFixed(1), requests: log.requests, consoleErrors: log.console, failed: log.failed.filter(f => !/ERR_ABORTED/.test(f)) };
      fs.writeFileSync(`${out}/${slug}.json`, JSON.stringify({ meta, ...d, text: undefined }, null, 1));
      fs.writeFileSync(`${out}/${slug}.txt`, d.text);
      console.log(slug.padEnd(26), 'H', String(H).padStart(6), 'MB', String(meta.transferMB).padStart(5), 'chars', String(d.text.length).padStart(5), 'imgs', d.images.length, 'vid', d.videos.length, 'forms', d.forms.length, 'err', meta.consoleErrors.length, 'fail', meta.failed.length);
    } catch (e) { console.log('FAILED', route, String(e).slice(0, 160)); }
    await browser.close();
  }
})();
