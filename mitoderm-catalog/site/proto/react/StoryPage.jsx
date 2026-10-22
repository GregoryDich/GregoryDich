// Example: the page structure the frame story needs, in React, with the prototype's class names (vtech-live.html), so
// its CSS applies unchanged. Layers in this order: smoke (.bg), deep plate (.plate), DNA helix, cells behind, the frame
// canvas (#seq), cells in front; then the sticky header and the story screens, runs.length + 1 of them, the last being
// the offer with the kit card. Each screen's copy sits in a .wrap: a run starts once its screen's copy has been read.
// Content after the offer (related products, footer) gives the kit room to land in the card. JSX: the automatic runtime
// (Vite, Next.js). Real copy and the rest of each block: vtech-live.html and Figma.
import { useFrameStory } from './useFrameStory.js';

const IDS = ['meet', 'why', 'inside', 'feel', 'protocol'];

export function StoryPage({ config, base, screens, offer, onReady }) {
  const story = useFrameStory(config, { base, onReady });
  return (
    <>
      <div className="bg" ref={story.ref('bg')} aria-hidden="true" />
      <div className="plate" ref={story.ref('plate')} aria-hidden="true" />
      <img className="helix" ref={story.ref('helix')} alt="" aria-hidden="true" decoding="async" />
      <div className="cells back" ref={story.ref('cellBack')} aria-hidden="true" />
      <canvas id="seq" ref={story.ref('canvas')} aria-hidden="true" />
      <div className="cells front" ref={story.ref('cellFront')} aria-hidden="true" />
      <header className="top" ref={story.ref('header')}>
        <div className="wrap"><a className="logo" href="#meet" aria-label="MITODERM"><img src={base + 'img/logo-mark.png'} alt="MITODERM" /></a></div>
      </header>
      <main>
        {screens.map((s, i) => (
          <section key={IDS[i]} id={IDS[i]} className="sec" ref={story.section(i)}>
            <div className="wrap"><div className="copy">
              {i === 0 ? <h1><bdi>{s.title}</bdi></h1> : <h2>{s.title}</h2>}
              <p className="lead">{s.text}</p>
            </div></div>
          </section>
        ))}
        <section id="offer" className="sec offer" ref={story.section(IDS.length)}>
          <div className="wrap">
            <div className="offer-copy"><h2>{offer.title}</h2><p className="lead">{offer.text}</p></div>
            <aside className="kitcard" ref={story.ref('card')}>
              <figure className="kc-fig">
                <canvas className="kc-live" ref={story.ref('cardCanvas')} role="img" aria-label={offer.kitAlt} />
                <img className="kc-pic" src={base + 'img/kit.webp'} alt={offer.kitAlt} loading="lazy" />
              </figure>
            </aside>
          </div>
        </section>
        {/* at least a screen of content after the card (on the page: related products, the footer), or the kit cannot land */}
        <section className="related" style={{ minHeight: '100vh' }}><div className="wrap"><h2>{offer.relatedTitle}</h2></div></section>
      </main>
    </>
  );
}
