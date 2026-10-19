// React hook for the V-TECH frame story (engine/story.js, the module the prototype pages run). The engine starts in an
// effect, after the elements exist, and destroy() on unmount removes its listeners, its worker, the decoded frames and
// the cell sprites it added, so it survives React 18 StrictMode (mount, unmount, mount again) and route changes.
// Server rendering: importing is safe, nothing touches window until the effect runs (Next.js: use it in a client
// component, 'use client').
//
//   const story = useFrameStory(config, { base: '/v-tech/' });
//   <canvas id="seq" ref={story.ref('canvas')} />   <section ref={story.section(0)}>…</section>   (see StoryPage.jsx)
//
// config: the object build-vtech.py writes into the page ({ runs, tiers, cells, mols, helix }); keep it the same
// object between renders (import it, or useMemo), a new object restarts the story. options: base (the folder with
// seq/ and img/), phoneQuery, tier, noWorker, onReady(story) (story.state() for debugging); read once per start.
// The elements the engine draws into (the canvas, the cell layers, the helix <img>) must have no React children: it
// adds and styles their content itself.
import { useEffect, useRef } from 'react';
import { createFrameStory } from '../engine/story.js';

const NAMES = ['canvas', 'header', 'card', 'cardCanvas', 'bg', 'plate', 'helix', 'cellBack', 'cellFront'];

export function useFrameStory(config, options = {}) {
  const els = useRef({ sections: [] }), refs = useRef(null), opts = useRef(options);
  opts.current = options;
  if (!refs.current) {   // stable callback refs: React calls each once per mount, not on every render
    const ref = Object.fromEntries(NAMES.map(n => [n, el => { els.current[n] = el; }]));
    const sec = [];
    refs.current = {
      ref: name => { if (!ref[name]) throw new Error(`useFrameStory: no element "${name}"`); return ref[name]; },
      section: i => sec[i] || (sec[i] = el => { els.current.sections[i] = el; }),
    };
  }
  useEffect(() => {
    const e = els.current, { onReady, ...rest } = opts.current;
    if (!config || !e.canvas || !e.sections.length) return undefined;
    const story = createFrameStory({
      ...rest, config, canvas: e.canvas, sections: e.sections.filter(Boolean), header: e.header, card: e.card,
      cardCanvas: e.cardCanvas, bg: e.bg, plate: e.plate, helix: e.helix, cellLayers: [e.cellBack, e.cellFront],
    });
    if (onReady) onReady(story);
    return () => story.destroy();
  }, [config]);
  return refs.current;
}
