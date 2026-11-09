'use client';

import {useEffect, useRef, useState, type CSSProperties, type ReactNode} from 'react';

// Root may replace this verified media URL with the same clip hosted locally.
export const COLLECTION_DESKTOP_VIDEO_SRC: string | undefined = 'https://d2ol7oe51mr4n9.cloudfront.net/user_2wup4xNeevN3QH5Pxv4g6PWRmPW/863547b6-0d08-4675-bbac-1b8b31264b1d.mp4';
export const COLLECTION_MOBILE_VIDEO_SRC: string | undefined = undefined;

export type CollectionHeroProduct = {slug:string; name:string; href:string; number:string};
type Rect = {x:number; y:number; width:number; height:number};
type Hotspot = Rect & {slug:string; box?:Rect};
type Variant = 'desktop' | 'mobile';

const desktopSize = {width:1672, height:941};
const mobileSize = {width:1049, height:1500};
const boxSilhouette = 'polygon(0% 2%, 11% 0%, 100% 1%, 100% 96%, 12% 100%, 0% 98%)';

// Coordinates refer to the complete approved photographs, never a cropped cover.
const desktopHotspots: Hotspot[] = [
  {slug:'v-tech-system', x:722,y:204,width:274,height:573, box:{x:730,y:213,width:251,height:552}},
  {slug:'exo-nad', x:76,y:300,width:203,height:219},
  {slug:'exocell-mask', x:297,y:337,width:215,height:182},
  {slug:'exotech-gel', x:519,y:307,width:178,height:212},
  {slug:'exosignal-hair', x:51,y:568,width:245,height:194},
  {slug:'exosignal-spray', x:301,y:555,width:109,height:211},
  {slug:'mitotech-cell-booster', x:415,y:582,width:289,height:186},
  {slug:'cell-renew-1-5', x:1095,y:276,width:95,height:266},
  {slug:'cellular-age-defense-2-5', x:1210,y:272,width:95,height:270},
  {slug:'micro-boost-10', x:1328,y:265,width:96,height:277},
  {slug:'derma-recovery-cream', x:1434,y:318,width:166,height:224},
  {slug:'mitoscan', x:1087,y:581,width:303,height:219},
  {slug:'mitopen', x:1430,y:548,width:147,height:252},
];
const mobileHotspots: Hotspot[] = [
  {slug:'v-tech-system', x:408,y:230,width:213,height:395, box:{x:420,y:242,width:186,height:369}},
  {slug:'exo-nad', x:89,y:373,width:248,height:245},
  {slug:'exocell-mask', x:704,y:387,width:303,height:229},
  {slug:'exotech-gel', x:107,y:636,width:198,height:225},
  {slug:'mitotech-cell-booster', x:366,y:655,width:343,height:211},
  {slug:'mitopen', x:770,y:623,width:178,height:236},
  {slug:'exosignal-hair', x:82,y:880,width:355,height:210},
  {slug:'exosignal-spray', x:482,y:867,width:150,height:222},
  {slug:'mitoscan', x:665,y:880,width:318,height:216},
  {slug:'cell-renew-1-5', x:120,y:1100,width:152,height:281},
  {slug:'cellular-age-defense-2-5', x:334,y:1100,width:150,height:282},
  {slug:'micro-boost-10', x:552,y:1102,width:150,height:281},
  {slug:'derma-recovery-cream', x:739,y:1126,width:197,height:258},
];

function PhotoFrame({variant, products, video, showVideo, onInspect}: {
  variant:Variant; products:CollectionHeroProduct[]; video?:ReactNode;
  showVideo:boolean; onInspect:()=>void;
}) {
  const desktop = variant === 'desktop';
  const size = desktop ? desktopSize : mobileSize;
  const hotspots = desktop ? desktopHotspots : mobileHotspots;
  return <div
    className={'mc-collection-frame mc-collection-frame-' + variant}
    data-collection-frame={variant}
    data-show-video={showVideo}
    style={{'--collection-ratio': `${size.width} / ${size.height}`} as CSSProperties}
  >
    <img
      data-collection-poster="true"
      className="mc-collection-photo"
      src={'/assets/hero/collection-atelier-' + variant + '.webp'}
      width={size.width}
      height={size.height}
      alt="קולקציית MITODERM: שלושה עשר מוצרים מקצועיים, עם V-TECH במרכז"
      fetchPriority="high"
      loading="eager"
      decoding="async"
    />
    {video}
    <nav className="mc-photo-hotspots" aria-label="בחרו מוצר מתוך הקולקציה">
      {hotspots.map(spot => {
        const product = products.find(item => item.slug === spot.slug)!;
        const isVTech = spot.slug === 'v-tech-system';
        const box = spot.box;
        return <a
          key={spot.slug}
          className={'mc-photo-hotspot' + (isVTech ? ' mc-photo-hotspot-vtech' : '')}
          href={product.href}
          data-product={spot.slug}
          data-flight={isVTech ? 'true' : undefined}
          data-flight-photo={isVTech ? 'true' : undefined}
          data-photo-silhouette={isVTech ? boxSilhouette : undefined}
          aria-label={'לפרטי ' + product.name}
          onPointerEnter={event => {if (event.pointerType !== 'touch') onInspect();}}
          onPointerDown={onInspect}
          onFocus={onInspect}
          onClick={onInspect}
          style={{
            left: `${(spot.x + spot.width / 2) / size.width * 100}%`,
            top: `${(spot.y + spot.height / 2) / size.height * 100}%`,
            width: `${spot.width / size.width * 100}%`,
            height: `${spot.height / size.height * 100}%`,
          }}
        >
          {box && <span
            data-flight-box="true"
            data-photo-silhouette={boxSilhouette}
            aria-hidden="true"
            style={{
              position:'absolute', pointerEvents:'none',
              left:`${(box.x - spot.x) / spot.width * 100}%`,
              top:`${(box.y - spot.y) / spot.height * 100}%`,
              width:`${box.width / spot.width * 100}%`,
              height:`${box.height / spot.height * 100}%`,
            }}
          />}
          <span className="mc-photo-marker" aria-hidden="true">{product.number}</span>
          <span className="mc-photo-tooltip" aria-hidden="true"><bdi dir="ltr">{product.name}</bdi><span>לפרטי המוצר ←</span></span>
        </a>;
      })}
    </nav>
  </div>;
}

export function CollectionHero({products, desktopVideoSrc=COLLECTION_DESKTOP_VIDEO_SRC, mobileVideoSrc=COLLECTION_MOBILE_VIDEO_SRC}: {
  products:CollectionHeroProduct[]; desktopVideoSrc?:string; mobileVideoSrc?:string;
}) {
  const hero = useRef<HTMLElement>(null);
  const player = useRef<HTMLVideoElement>(null);
  const pinned = useRef(false);
  const [desktop, setDesktop] = useState<boolean | null>(null);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [inView, setInView] = useState(false);
  const [documentVisible, setDocumentVisible] = useState(true);
  const [ready, setReady] = useState(false);
  const [started, setStarted] = useState(false);
  const [userPaused, setUserPaused] = useState(false);
  const [posterPinned, setPosterPinned] = useState(false);
  const [ended, setEnded] = useState(false);
  const [failed, setFailed] = useState(false);
  const source = desktop === null ? undefined : desktop ? desktopVideoSrc : mobileVideoSrc;

  useEffect(() => {
    const width = window.matchMedia('(min-width: 901px)');
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const syncWidth = () => setDesktop(width.matches);
    const syncMotion = () => setReducedMotion(motion.matches);
    const syncVisibility = () => setDocumentVisible(document.visibilityState !== 'hidden');
    syncWidth(); syncMotion(); syncVisibility();
    width.addEventListener('change', syncWidth);
    motion.addEventListener('change', syncMotion);
    document.addEventListener('visibilitychange', syncVisibility);
    const observer = new IntersectionObserver(entries => setInView(entries[0].isIntersecting), {threshold:0.03});
    if (hero.current) observer.observe(hero.current);
    return () => {
      width.removeEventListener('change', syncWidth);
      motion.removeEventListener('change', syncMotion);
      document.removeEventListener('visibilitychange', syncVisibility);
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    setReady(false); setStarted(false); setEnded(false); setFailed(false);
    setPosterPinned(false); pinned.current = false;
  }, [source]);

  const shouldPlay = !!source && ready && inView && documentVisible && !reducedMotion && !userPaused && !posterPinned && !ended && !failed;
  useEffect(() => {
    const video = player.current;
    if (!video) return;
    if (!shouldPlay) {video.pause(); return;}
    let active = true;
    void video.play().then(() => {
      if (active && !pinned.current) setStarted(true);
    }).catch(() => {if (active) setUserPaused(true);});
    return () => {active = false; video.pause();};
  }, [shouldPlay, source]);

  // Latch the exact poster until explicit replay. This runs before link navigation
  // so the photograph, hit zones and root's box-crop transition agree.
  function pinPoster() {
    pinned.current = true;
    player.current?.pause();
    if (player.current) player.current.style.visibility = 'hidden';
    setPosterPinned(true);
  }
  function replay() {
    if (reducedMotion || !player.current) return;
    pinned.current = false;
    player.current.style.visibility = '';
    player.current.currentTime = 0;
    setPosterPinned(false); setEnded(false); setUserPaused(false);
  }
  function pauseOrResume() {
    if (!userPaused) player.current?.pause();
    setUserPaused(value => !value);
  }
  const showVideo = started && ready && !posterPinned && !ended && !reducedMotion && !failed;
  const video = source ? <video
    key={source}
    ref={player}
    className="mc-collection-video"
    src={source}
    muted
    playsInline
    preload="metadata"
    aria-hidden="true"
    tabIndex={-1}
    onCanPlay={() => setReady(true)}
    onEnded={() => setEnded(true)}
    onError={() => setFailed(true)}
  /> : null;

  return <section id="home" className="mc-photo-hero" ref={hero} aria-labelledby="mc-photo-title">
    <div className="mc-photo-heading">
      <div className="mc-photo-copy">
        <p className="mc-eyebrow" dir="ltr">THE MITODERM COLLECTION</p>
        <h1 id="mc-photo-title">הקולקציה של <bdi dir="ltr">MITODERM</bdi></h1>
        <p className="mc-intro">13 מוצרים. בחרו את המוצר שלכם.</p>
      </div>
      <div className="mc-photo-actions">
        <a className="mc-primary" href="#contact" data-source="home-hero">ייעוץ והצעה <span aria-hidden="true">←</span></a>
        <a className="mc-photo-skip" href="/products/v-tech-system" data-product="v-tech-system" data-flight-skip="true">לעמוד <bdi dir="ltr">V-TECH</bdi><span aria-hidden="true">↗</span></a>
      </div>
    </div>
    <PhotoFrame variant="desktop" products={products} video={desktop ? video : undefined} showVideo={desktop === true && showVideo} onInspect={pinPoster}/>
    <PhotoFrame variant="mobile" products={products} video={desktop === false ? video : undefined} showVideo={desktop === false && showVideo} onInspect={pinPoster}/>
    <div className="mc-photo-caption">
      <p>בחרו מוצר בתמונה, או גלו את הקולקציה למטה.</p>
      {source && !reducedMotion && !failed && <div className="mc-photo-video-controls" aria-label="שליטה בתנועת התמונה">
        <button type="button" disabled={!ready || ended || posterPinned} onClick={pauseOrResume} aria-pressed={userPaused} aria-label={userPaused ? 'המשך ניגון הסרטון' : 'השהיית הסרטון'}><span aria-hidden="true">{userPaused ? '▷' : 'Ⅱ'}</span>{userPaused ? 'המשך' : 'השהיה'}</button>
        <button type="button" disabled={!ready} onClick={replay} aria-label="ניגון הסרטון מההתחלה"><span aria-hidden="true">↻</span>ניגון חוזר</button>
      </div>}
      <a href="#products">כל 13 המוצרים <span aria-hidden="true">↓</span></a>
    </div>
  </section>;
}
