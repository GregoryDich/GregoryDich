'use client';

import {useEffect,useRef,useState,type CSSProperties} from 'react';
import {entryMedia,getEntryMedia} from './vtech-entry';

export type CollectionHeroProduct={slug:string;name:string;href:string;number:string};
type Rect={x:number;y:number;width:number;height:number};
type Hotspot=Rect&{slug:string;box?:Rect};
type Variant='desktop'|'mobile';
const desktopSize = {width:1672, height:941};
const mobileSize = {width:1049, height:1500};
// Replace only the old V-TECH footprint. Every other pack keeps its approved
// original pixels; the generated clean plate supplies the empty podium only.
const cleanMasks={
 desktop:'linear-gradient(90deg,transparent 42.34%,#000 43.48%,#000 63.52%,transparent 64.6%),linear-gradient(transparent 20.19%,#000 22%,#000 86.4%,transparent 88.31%)',
 mobile:'linear-gradient(90deg,transparent 37.18%,#000 39.47%,#000 62.73%,transparent 64.73%),linear-gradient(transparent 14.2%,#000 15.4%,#000 42.2%,transparent 43.4%)',
};

// Coordinates refer to the complete approved photographs, never a cropped cover.
const desktopHotspots: Hotspot[] = [
  {slug:'v-tech-system', x:777,y:470,width:156,height:300, box:{x:790,y:478,width:129,height:280}},
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

function PhotoFrame({variant,products,viewport,onChoose}:{variant:Variant;products:CollectionHeroProduct[];viewport:number;onChoose:()=>void}){
 const size=variant==='desktop'?desktopSize:mobileSize;
 const hotspots=variant==='desktop'?desktopHotspots:mobileHotspots;
 const media=viewport?getEntryMedia(viewport):entryMedia;
 const cleanSrc='/assets/hero/collection-clean-'+variant+'-v7.webp';
 return <div className={'mc-collection-frame mc-collection-frame-'+variant} data-collection-frame={variant} style={{'--collection-ratio':`${size.width} / ${size.height}`} as CSSProperties}>
  <img data-collection-poster="true" data-clean-src={cleanSrc} data-clean-mask={cleanMasks[variant]} className="mc-collection-photo" src={'/assets/hero/collection-atelier-'+variant+'.webp'} width={size.width} height={size.height} alt="קולקציית MITODERM: שלושה עשר מוצרים מקצועיים" fetchPriority="high" loading="eager" decoding="async"/>
  <img className="mc-collection-photo mc-collection-clean" src={cleanSrc} width={size.width} height={size.height} alt="" aria-hidden="true" loading="eager" decoding="async" style={{maskImage:cleanMasks[variant],maskComposite:'intersect',WebkitMaskComposite:'source-in'}}/>
  <div className="mc-collection-ambient" aria-hidden="true"/>
  <nav className="mc-photo-hotspots" aria-label="בחרו מוצר מתוך הקולקציה">
   {hotspots.map(spot=>{
    const product=products.find(item=>item.slug===spot.slug)!;
    const isVTech=spot.slug==='v-tech-system',box=spot.box;
    const width=box?box.height*media.box.width/media.box.height:0;
    const x=box?box.x+(box.width-width)/2:0;
    return <a key={spot.slug} className={'mc-photo-hotspot'+(isVTech?' mc-photo-hotspot-vtech':'')} href={product.href} data-product={spot.slug} data-flight={isVTech?'true':undefined} data-flight-photo={isVTech?'true':undefined} aria-label={'לפרטי '+product.name} onClick={onChoose}
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
