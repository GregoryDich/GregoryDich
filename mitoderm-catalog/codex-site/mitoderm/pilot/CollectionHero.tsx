'use client';

import {useEffect,useRef,useState,type CSSProperties} from 'react';
import {entryMedia,getEntryMedia} from './vtech-entry';

export type CollectionHeroProduct={slug:string;name:string;href:string;number:string};
type Rect={x:number;y:number;width:number;height:number};
type Hotspot=Rect&{slug:string;box?:Rect};
type Variant='desktop'|'mobile';
// Wide screens (22/11): two even rows on an empty stage, built by state/tasks/build-hero-rows.py from the real
// cut-outs. V-TECH is one of the row, not the centre; its box is not in the picture - it is drawn below from the
// first frame of its film, so it has no old footprint to clean. The picture's edges fall into the page colour.
const desktopSize = {width:3840, height:2160};
const mobileSize = {width:1049, height:1500};
const desktopWidths=[1920,2560,3840];
const desktopSrc=(width:number)=>'/assets/hero/collection-rows-desktop-'+width+'.webp';
// The phone photograph: replace only the old V-TECH footprint. Every other pack keeps its approved
// original pixels; the generated clean plate supplies the empty podium only.
const mobileCleanMask='linear-gradient(90deg,transparent 37.18%,#000 39.47%,#000 62.73%,transparent 64.73%),linear-gradient(transparent 14.2%,#000 15.4%,#000 42.2%,transparent 43.4%)';

// Coordinates refer to the complete pictures, never a cropped cover. The wide-screen ones are the exact
// places of the packs (hero-rows-map.json of the builder), left to right, upper row then lower row.
const desktopHotspots: Hotspot[] = [
  {slug:'exosignal-spray', x:269,y:581,width:304,height:499},
  {slug:'exosignal-hair', x:725,y:716,width:553,height:364},
  {slug:'exotech-gel', x:1430,y:633,width:334,height:447},
  {slug:'exocell-mask', x:1915,y:664,width:520,height:416},
  {slug:'exo-nad', x:2587,y:716,width:593,height:364},
  {slug:'v-tech-system', x:3332,y:560,width:239,height:520, box:{x:3332,y:560,width:239,height:520}},
  {slug:'mitoscan', x:269,y:1328,width:589,height:400},
  {slug:'mitopen', x:1009,y:1231,width:462,height:497},
  {slug:'mitotech-cell-booster', x:1622,y:1339,width:513,height:389},
  {slug:'derma-recovery-cream', x:2286,y:1264,width:337,height:464},
  {slug:'cellular-age-defense-2-5', x:2774,y:1188,width:163,height:540},
  {slug:'cell-renew-1-5', x:3088,y:1188,width:166,height:540},
  {slug:'micro-boost-10', x:3405,y:1188,width:166,height:540},
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

function PhotoFrame({variant,products,viewport,onChoose}:{variant:Variant;products:CollectionHeroProduct[];viewport:number;onChoose:()=>void}){
 const size=variant==='desktop'?desktopSize:mobileSize;
 const hotspots=variant==='desktop'?desktopHotspots:mobileHotspots;
 const media=viewport?getEntryMedia(viewport):entryMedia;
 const wide=variant==='desktop';
 const cleanSrc=wide?undefined:'/assets/hero/collection-clean-mobile-v7.webp';
 return <div className={'mc-collection-frame mc-collection-frame-'+variant} data-collection-frame={variant} style={{'--collection-ratio':`${size.width} / ${size.height}`} as CSSProperties}>
  {wide
   ?<img data-collection-poster="true" className="mc-collection-photo" src={desktopSrc(1920)} srcSet={desktopWidths.map(width=>desktopSrc(width)+' '+width+'w').join(', ')} sizes="(max-width: 900px) 1px, 100vw" width={size.width} height={size.height} alt="קולקציית MITODERM: שלושה עשר מוצרים מקצועיים" fetchPriority="high" loading="eager" decoding="async"/>
   :<img data-collection-poster="true" data-clean-src={cleanSrc} data-clean-mask={mobileCleanMask} className="mc-collection-photo" src="/assets/hero/collection-atelier-mobile.webp" width={size.width} height={size.height} alt="קולקציית MITODERM: שלושה עשר מוצרים מקצועיים" fetchPriority="high" loading="eager" decoding="async"/>}
  {cleanSrc&&<img className="mc-collection-photo mc-collection-clean" src={cleanSrc} width={size.width} height={size.height} alt="" aria-hidden="true" loading="eager" decoding="async" style={{maskImage:mobileCleanMask,maskComposite:'intersect',WebkitMaskComposite:'source-in'}}/>}
  <div className="mc-collection-ambient" aria-hidden="true"/>
  <nav className="mc-photo-hotspots" aria-label="בחרו מוצר מתוך הקולקציה">
   {hotspots.map(spot=>{
    const product=products.find(item=>item.slug===spot.slug)!;
    const isVTech=spot.slug==='v-tech-system',box=spot.box;
    const width=box?box.height*media.box.width/media.box.height:0;
    const x=box?box.x+(box.width-width)/2:0;
    // Where the pack stands, as parts of the picture; on wide screens also its separate cut-out. Both feed
    // the entry into the product (ProductEntry.tsx): the chosen pack lifts off the collection.
    const packRect=[spot.x/size.width,spot.y/size.height,spot.width/size.width,spot.height/size.height].map(value=>value.toFixed(5)).join(',');
    const packSrc=isVTech?undefined:'/assets/hero/pack-'+spot.slug+'.webp';
    // The cut-out is fetched when the pointer reaches the product, so it is there when the product is chosen.
    const warm=()=>{if(packSrc){const image=new Image();image.decoding='async';image.src=packSrc;}};
    return <a key={spot.slug} className={'mc-photo-hotspot'+(isVTech?' mc-photo-hotspot-vtech':'')} href={product.href} data-product={spot.slug} data-flight={isVTech?'true':undefined} data-flight-photo={isVTech?'true':undefined} data-pack-rect={isVTech?undefined:packRect} data-pack-src={packSrc} aria-label={'לפרטי '+product.name} onClick={onChoose} onPointerEnter={warm} onPointerDown={warm} onFocus={warm}
     style={{left:`${(spot.x+spot.width/2)/size.width*100}%`,top:`${(spot.y+spot.height/2)/size.height*100}%`,width:`${spot.width/size.width*100}%`,height:`${spot.height/size.height*100}%`}}>
     {box&&<span className="mc-canonical-pack" data-flight-box="true" data-canonical-pack="true" data-canonical-src={media.poster} data-canonical-width={media.width} data-canonical-height={media.height} data-canonical-left={media.box.left} data-canonical-top={media.box.top} data-canonical-box-width={media.box.width} data-canonical-box-height={media.box.height} data-photo-silhouette={media.silhouette} aria-hidden="true"
      style={{left:`${(x-spot.x)/spot.width*100}%`,top:`${(box.y-spot.y)/spot.height*100}%`,width:`${width/spot.width*100}%`,height:`${box.height/spot.height*100}%`,clipPath:media.silhouette}}>
      <img src={media.poster} alt="" draggable={false} decoding="async" style={{width:`${media.width/media.box.width*100}%`,height:`${media.height/media.box.height*100}%`,left:`${-media.box.left/media.box.width*100}%`,top:`${-media.box.top/media.box.height*100}%`}}/>
     </span>}
     <span className="mc-photo-tooltip" aria-hidden="true"><bdi dir="ltr">{product.name}</bdi><span>לפרטי המוצר ←</span></span>
    </a>;
   })}
  </nav>
 </div>;
}

/** A seamless live-light loop keeps the collection alive without changing any
 * package artwork. Selection pauses the current pose before it is measured. */
export function CollectionHero({products}:{products:CollectionHeroProduct[]}){
 const hero=useRef<HTMLElement>(null);
 const [viewport,setViewport]=useState(0),[paused,setPaused]=useState(false);
 const [inView,setInView]=useState(true),[visible,setVisible]=useState(true),[reduced,setReduced]=useState(false);
 useEffect(()=>{
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const resize=()=>setViewport(window.innerWidth),preference=()=>setReduced(motion.matches),visibility=()=>setVisible(!document.hidden);
  resize();preference();visibility();
  const observer=new IntersectionObserver(entries=>setInView(entries[0].isIntersecting),{threshold:.02});if(hero.current)observer.observe(hero.current);
  window.addEventListener('resize',resize,{passive:true});motion.addEventListener('change',preference);document.addEventListener('visibilitychange',visibility);
  return()=>{observer.disconnect();window.removeEventListener('resize',resize);motion.removeEventListener('change',preference);document.removeEventListener('visibilitychange',visibility);};
 },[]);
 const choose=()=>{if(hero.current)hero.current.dataset.motion='paused';setPaused(true);};
 return <section id="home" className="mc-photo-hero" ref={hero} data-motion={paused||!inView||!visible||reduced?'paused':'running'} aria-labelledby="mc-photo-title">
  <div className="mc-photo-heading"><div className="mc-photo-copy"><p className="mc-eyebrow" dir="ltr">THE MITODERM COLLECTION</p><h1 id="mc-photo-title">הקולקציה של <bdi dir="ltr">MITODERM</bdi></h1><p className="mc-intro">13 מוצרים. בחרו את המוצר שלכם.</p></div><div className="mc-photo-actions"><a className="mc-primary" href="#contact" data-source="home-hero">ייעוץ והצעה <span aria-hidden="true">←</span></a><a className="mc-photo-skip" href="/products/v-tech-system" data-product="v-tech-system" data-flight-skip="true">לעמוד <bdi dir="ltr">V-TECH</bdi><span aria-hidden="true">↗</span></a></div></div>
  <PhotoFrame variant="desktop" products={products} viewport={viewport} onChoose={choose}/>
  <PhotoFrame variant="mobile" products={products} viewport={viewport} onChoose={choose}/>
  <div className="mc-photo-caption"><p>בחרו מוצר בתמונה, או גלו את הקולקציה למטה.</p>{!reduced&&<div className="mc-photo-video-controls" aria-label="שליטה בתנועת התמונה"><button type="button" onClick={()=>setPaused(value=>!value)} aria-pressed={paused} aria-label={paused?'המשך תנועת הקולקציה':'השהיית תנועת הקולקציה'}><span aria-hidden="true">{paused?'▷':'Ⅱ'}</span>{paused?'המשך':'השהיה'}</button></div>}<a href="#products">כל 13 המוצרים <span aria-hidden="true">↓</span></a></div>
 </section>;
}
