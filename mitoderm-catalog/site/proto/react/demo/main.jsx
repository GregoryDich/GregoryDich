// The React demo of the frame story: StoryPage in StrictMode (so the engine is mounted, unmounted and mounted again,
// as React does in development), with a switch the QA script uses to unmount and remount the page.
import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { StoryPage } from '../StoryPage.jsx';

const { config, screens, offer } = window.__DEMO__;   // written into index.html by build.mjs

function App() {
  const [on, setOn] = useState(true);
  window.__toggleStory = () => setOn(v => !v);
  return on
    ? <StoryPage config={config} base="" screens={screens} offer={offer} onReady={s => { window.__story = s; window.__seq = s.state; }} />
    : <main><section className="sec"><div className="wrap"><p className="lead">—</p></div></section></main>;
}

createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>);
