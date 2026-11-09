'use client';

import {useEffect,useRef,useState,type CSSProperties} from 'react';
import {assets,home,products,lineGroups,ui,productHref} from './data';
import {Chapter,ProductImage,ContactBlock,SiteHeader,SiteFooter} from './shared';
import {SupportSection} from './pilot/HomeSections';
import './pilot/home-cinema.css';

// One inventory powers the complete stage, mobile rail and accessible collection.
const collection=[
 {slug:'v-tech-system',role:'סרום ומסכת ג׳ל',x:28,y:23,w:13,h:74,z:3},
 {slug:'exo-nad',role:'מערכת פילינג מקצועית',x:81,y:29,w:10,h:49,z:2},
 {slug:'exocell-mask',role:'מסכת ביו-צלולוז',x:68,y:28,w:14,h:48,z:2},
 {slug:'exotech-gel',role:'ג׳ל לטיפוח משלים',x:94,y:25,w:8,h:51,z:3},
 {slug:'exosignal-hair',role:'אמפולות לשימוש מקצועי',x:44,y:35,w:19,h:44,z:2},
 {slug:'exosignal-spray',role:'טיפוח ביתי לקרקפת',x:57,y:32,w:7,h:43,z:3},
 {slug:'mitopen',role:'מכשור מיקרונידלינג',x:5,y:23,w:7,h:75,z:3},
 {slug:'mitoscan',role:'סקירת הקרקפת והשיער',x:14,y:22,w:15,h:38,z:3},
 {slug:'micro-boost-10',role:'BIOSPICULE · מקצועי',x:37,y:3,w:7,h:45,z:5},
 {slug:'cell-renew-1-5',role:'BIOSPICULE · טיפוח ביתי',x:44.5,y:3,w:6.5,h:43,z:5},
 {slug:'cellular-age-defense-2-5',role:'BIOSPICULE · טיפוח ביתי',x:52,y:3,w:6.5,h:43,z:5},
 {slug:'derma-recovery-cream',role:'טיפוח משלים לעור',x:61.5,y:3,w:10,h:41,z:5},
 {slug:'mitotech-cell-booster',role:'מערכת דו-רכיבית',x:81,y:1,w:20,h:36,z:5},
].map(item=>({...item,product:products.find(product=>product.slug===item.slug)!,asset:assets[item.slug]}));
type CollectionItem=(typeof collection)[number];

function Cutout({item,eager=false}:{item:CollectionItem;eager?:boolean}){
 return <img data-flight-image="true" className="mc-cutout" src={item.asset.src} alt="" width={item.asset.width} height={item.asset.height} loading={eager?'eager':'lazy'} decoding="async" fetchPriority={eager&&item.slug==='v-tech-system'?'high':'auto'}/>;
}

function MobileCollection(){
 const rail=useRef<HTMLDivElement>(null);
 const [current,setCurrent]=useState(0);
 useEffect(()=>{
  const element=rail.current;if(!element)return;
  const observer=new IntersectionObserver(entries=>{
   for(const entry of entries){if(entry.isIntersecting&&entry.intersectionRatio>=.65)setCurrent(Number((entry.target as HTMLElement).dataset.index));}
  },{root:element,threshold:[.65]});
  element.querySelectorAll('[data-index]').forEach(child=>observer.observe(child));
  return()=>observer.disconnect();
 },[]);
 function move(offset:number){
  const next=Math.min(collection.length-1,Math.max(0,current+offset));
  const child=rail.current?.querySelector<HTMLElement>(`[data-index="${next}"]`);
  child?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest',inline:'center'});
 }
 return <div className="mc-mobile">
  <div className="mc-mobile-family" aria-hidden="true">
   <span className="mc-family-floor"/>
   {collection.map(item=><span key={item.slug} className="mc-family-object" style={{'--family-x':item.x+'%','--family-y':item.y+'%','--family-width':item.w+'%','--family-height':item.h+'%','--family-z':item.z} as CSSProperties}><Cutout item={item} eager/></span>)}
  </div>
  <p className="mc-mobile-family-caption"><span><bdi dir="ltr">{collection.length}</bdi> מוצרים בקולקציה</span><span>בחרו מוצר והכירו אותו</span></p>
  <div className="mc-mobile-rail" ref={rail} aria-label="כל 13 מוצרי MITODERM">
   {collection.map((item,index)=><a key={item.slug} href={productHref(item.slug)} className="mc-mobile-card" data-index={index} data-flight="true" data-product={item.slug} aria-label={'לפרטי '+item.product.name} style={{'--mobile-max':Math.min(item.asset.width,310)+'px'} as CSSProperties}>
    <span className="mc-mobile-picture"><Cutout item={item} eager={index===0}/></span>
    <span className="mc-mobile-name"><bdi dir="ltr">{item.product.name}</bdi><span aria-hidden="true">↗</span></span>
    <span className="mc-mobile-role" dir="rtl">{item.role}</span>
   </a>)}
  </div>
  <div className="mc-mobile-controls">
   <button type="button" onClick={()=>move(-1)} disabled={current===0} aria-label="המוצר הקודם">→</button>
   <span className="mc-mobile-count" aria-live="polite"><bdi dir="ltr">{String(current+1).padStart(2,'0')} / {collection.length}</bdi></span>
   <button type="button" onClick={()=>move(1)} disabled={current===collection.length-1} aria-label="המוצר הבא">←</button>
   <a href="#products">כל המוצרים <span aria-hidden="true">↓</span></a>
  </div>
 </div>;
}

function Lineup(){
 const [active,setActive]=useState<string|null>(null);
 const lead=home.find(section=>section.index===1)!;
 const selected=collection.find(item=>item.slug===active);
 return <Chapter id="home" className="mc-hero" line="neutral">
  <div className="mc-atmosphere" aria-hidden="true"/>
  <div className="mc-hero-heading">
   <div className="mc-hero-copy"><p className="mc-eyebrow" dir="ltr">MITODERM · PROFESSIONAL CARE</p><h1>{lead.title}</h1><p className="mc-intro">מוצרים מקצועיים, טיפוח משלים ומכשור לקליניקה.</p></div>
   <div className="mc-hero-actions"><a href="#contact" data-source="home-hero" className="mc-primary">{ui.contact}<span aria-hidden="true">←</span></a><a href="#products" className="mc-all-link">כל המוצרים <span aria-hidden="true">↓</span></a></div>
  </div>
  <div className="mc-stage" aria-label="קולקציית MITODERM — כל 13 המוצרים">
   <div className="mc-floor mc-floor-back" aria-hidden="true"/><div className="mc-floor mc-floor-front" aria-hidden="true"/>
   {collection.map(item=><a key={item.slug} className={'mc-stage-product'+(active===item.slug?' is-active':'')+(item.slug==='mitotech-cell-booster'?' mc-emerald':'')} href={productHref(item.slug)} data-flight="true" data-product={item.slug} aria-label={'לפרטי '+item.product.name} onPointerEnter={event=>{if(event.pointerType==='mouse')setActive(item.slug);}} onPointerLeave={()=>setActive(null)} onFocus={()=>setActive(item.slug)} onBlur={()=>setActive(null)} style={{'--object-x':item.x+'%','--object-y':item.y+'%','--object-width':item.w+'%','--object-height':item.h+'%','--object-z':item.z,'--natural-max':Math.min(item.asset.width,item.asset.maxWidth)+'px'} as CSSProperties}>
    <Cutout item={item} eager/>
    <span className="mc-object-label"><bdi dir="ltr">{item.product.name}</bdi><span aria-hidden="true">↗</span></span>
   </a>)}
  </div>
  <MobileCollection/>
  <div className="mc-stage-caption"><span className="mc-collection-count"><bdi dir="ltr">13</bdi> מוצרים. עולם מקצועי אחד.</span><span className="mc-selected">{selected?<><bdi dir="ltr">{selected.product.name}</bdi><span aria-hidden="true">↗</span></>:<>בחרו מוצר כדי להכיר אותו <span aria-hidden="true">↗</span></>}</span><a href="#products" aria-label="לכל המוצרים">↓</a></div>
 </Chapter>;
}

function FullCollection(){
 return <section className="mc-collection" id="products" aria-labelledby="mc-collection-heading">
  <div className="mc-collection-heading"><div><p className="mc-eyebrow" dir="ltr">THE COLLECTION / 13</p><h2 id="mc-collection-heading">הקולקציה המלאה</h2></div><p>הכירו את המוצרים ובחרו את התחום שמעניין אתכם.</p></div>
  <div className="mc-collection-grid">{collection.map(item=><a key={item.slug} className={'mc-collection-card'+(item.slug==='mitotech-cell-booster'?' mc-collection-booster':'')} href={productHref(item.slug)} data-flight="true" data-product={item.slug} aria-label={'לפרטי '+item.product.name}>
   <span className="mc-collection-picture"><Cutout item={item}/></span><span className="mc-collection-copy"><bdi dir="ltr">{item.product.name}</bdi><span>{item.role}</span></span><span className="mc-collection-arrow" aria-hidden="true">↗</span>
  </a>)}</div>
 </section>;
}

export default function Home(){return <div className="mc-home"><SiteHeader/><main id="main-content"><Lineup/><FullCollection/><SupportSection/><ContactBlock/></main><SiteFooter/></div>;}

export function Catalog(){
 const [filter,setFilter]=useState('all');
 const names=ui.filters.split(' · ');
 return <><SiteHeader/><main id="main-content" className="catalog-main"><Chapter id="catalog" className="catalog-section" line="neutral">
  <div className="layer-background" aria-hidden="true"/>
  <div className="layer-motion" aria-hidden="true"/>
  <div className="layer-content catalog-content"><h1>{ui.catalog}</h1><div className="catalog-filters" aria-label={ui.filterTitle}><button onClick={()=>setFilter('all')} aria-pressed={filter==='all'}>{names[0]}</button>{lineGroups.map(g=><button key={g.id} onClick={()=>setFilter(g.name)} aria-pressed={filter===g.name}><bdi dir="ltr">{g.name}</bdi></button>)}</div></div>
  <div className="catalog-grid">{products.filter(p=>filter==='all'||p.line===filter).map(p=><article key={p.slug} className="catalog-product">
    <div className="catalog-card-background" aria-hidden="true"/>
    <div className="catalog-product-stage layer-motion"><a href={productHref(p.slug)} aria-label={p.name}><ProductImage slug={p.slug}/></a></div>
    <div className="catalog-product-copy layer-content"><h2><bdi dir="ltr">{p.name}</bdi></h2><p>{p.intro.body}</p><a href={productHref(p.slug)}>{ui.productLink}</a></div>
   </article>)}</div>
  </Chapter><ContactBlock/></main><SiteFooter/></>;
}
