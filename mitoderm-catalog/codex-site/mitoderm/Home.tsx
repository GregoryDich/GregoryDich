'use client';

import {useState, type CSSProperties} from 'react';
import {assets, products, lineGroups, ui, productHref} from './data';
import {Chapter, ProductImage, ContactBlock, SiteHeader, SiteFooter} from './shared';
import {SupportSection} from './pilot/HomeSections';
import {CollectionHero} from './pilot/CollectionHero';
import './pilot/home-cinema.css';

// One verified inventory powers the photograph links and the readable product index.
const collection = [
  {slug:'v-tech-system', shortName:'V-TECH', role:'סרום ומסכת ג׳ל'},
  {slug:'exo-nad', shortName:'EXO-NAD', role:'מערכת פילינג מקצועית'},
  {slug:'exocell-mask', shortName:'EXOCELL', role:'מסכת ביו-צלולוז'},
  {slug:'exotech-gel', shortName:'EXOTECH', role:'ג׳ל לטיפוח משלים'},
  {slug:'exosignal-hair', shortName:'EXOSIGNAL HAIR', role:'אמפולות לשימוש מקצועי'},
  {slug:'exosignal-spray', shortName:'EXOSIGNAL SPRAY', role:'טיפוח ביתי לקרקפת'},
  {slug:'mitopen', shortName:'MITOPEN', role:'מכשור מיקרונידלינג'},
  {slug:'micro-boost-10', shortName:'MICRO BOOST 10%', role:'BIOSPICULE · מקצועי'},
  {slug:'cell-renew-1-5', shortName:'CELL RENEW 1.5%', role:'BIOSPICULE · טיפוח ביתי'},
  {slug:'cellular-age-defense-2-5', shortName:'AGE DEFENSE 2.5%', role:'BIOSPICULE · טיפוח ביתי'},
  {slug:'derma-recovery-cream', shortName:'DERMA RECOVERY', role:'טיפוח משלים לעור'},
  {slug:'mitoscan', shortName:'MITOSCAN', role:'סקירת הקרקפת והשיער'},
  {slug:'mitotech-cell-booster', shortName:'MITOTECH CELL BOOSTER', role:'מערכת דו-רכיבית'},
].map((item, index) => ({
  ...item,
  number: String(index + 1).padStart(2, '0'),
  product: products.find(product => product.slug === item.slug)!,
  asset: assets[item.slug],
}));
type CollectionItem = (typeof collection)[number];

function Cutout({item, eager=false}: {item:CollectionItem; eager?:boolean}) {
  return <img
    data-flight-image="true"
    className="mc-cutout"
    src={item.asset.src}
    alt=""
    width={item.asset.width}
    height={item.asset.height}
    loading={eager ? 'eager' : 'lazy'}
    decoding="async"
    fetchPriority={eager && item.slug === 'v-tech-system' ? 'high' : 'auto'}
    style={{'--mc-asset-max': `${Math.min(item.asset.maxWidth, item.asset.width / 2)}px`} as CSSProperties}
  />;
}

function FullCollection() {
  return <section className="mc-collection" id="products" aria-labelledby="mc-collection-heading">
    <div className="mc-collection-heading">
      <div><p className="mc-eyebrow" dir="ltr">THE COLLECTION / 13</p><h2 id="mc-collection-heading">לכל מוצר, המקום שלו</h2></div>
      <p>הכירו את המוצרים ואת מקומם בעבודה המקצועית ובטיפוח המשלים.</p>
    </div>
    <div className="mc-collection-grid">
      {collection.map(item => <a
        key={item.slug}
        className={'mc-collection-card' + (item.slug === 'mitotech-cell-booster' ? ' mc-collection-booster' : '')}
        href={productHref(item.slug)}
        data-flight="true"
        data-product={item.slug}
        aria-label={'לפרטי ' + item.product.name}
      >
        <span className="mc-collection-picture"><Cutout item={item}/></span>
        <span className="mc-collection-copy"><bdi dir="ltr">{item.product.name}</bdi><span>{item.role}</span></span>
        <span className="mc-collection-arrow" aria-hidden="true">↗</span>
      </a>)}
    </div>
  </section>;
}

export default function Home() {
  return <div className="mc-home"><SiteHeader/><main id="main-content"><CollectionHero products={collection.map(item => ({slug:item.slug, name:item.product.name, href:productHref(item.slug), number:item.number}))}/><FullCollection/><SupportSection/><ContactBlock/></main><SiteFooter/></div>;
}

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
