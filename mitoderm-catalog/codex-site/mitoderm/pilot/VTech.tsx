'use client';

import {useEffect,useState} from 'react';
import {SiteHeader,SiteFooter} from '../shared';
import {VTechStory} from './VTechStory';
import {VTechCases,VTechOffer,VTechTraining,VTechRelated} from './VTechDetails';
import './vtech-cinema.css';

const pageSections=[{id:'vtech-intro',label:'הטיפול'},{id:'vtech-results',label:'תוצאות'},{id:'vtech-kit',label:'הערכה'},{id:'vtech-training',label:'הדרכה'}];
function SectionNavigation(){
 const [active,setActive]=useState('vtech-intro');
 useEffect(()=>{
  const observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting)setActive(entry.target.id);},{rootMargin:'-20% 0px -65% 0px',threshold:0});
  pageSections.forEach(({id})=>{const section=document.getElementById(id);if(section)observer.observe(section);});
  return()=>observer.disconnect();
 },[]);
 return <nav className="vc-section-nav" aria-label="ניווט בעמוד V-TECH" data-vtech-hud="true">
  <a className="vc-section-brand" dir="ltr" href="/" aria-label="חזרה לכל המוצרים" title="כל המוצרים"><span className="vc-section-brand-title">V-TECH</span><svg className="vc-section-collection-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg></a>
  <div className="vc-section-links">{pageSections.map(item=><a key={item.id} href={'#'+item.id} aria-current={active===item.id?'location':undefined} onClick={item.id==='vtech-intro'?event=>{event.preventDefault();window.dispatchEvent(new CustomEvent('mitoderm:vtech-chapter',{detail:'vtech-consultation'}));}:undefined}>{item.label}</a>)}</div>
  <a className="vc-section-inquiry" href="#contact" data-product="v-tech-system" data-source="vtech-section-nav"><span className="vc-section-inquiry-long">לקבלת מחיר</span><span className="vc-section-inquiry-short">הצעה</span><span className="vc-section-inquiry-arrow" aria-hidden="true">←</span></a>
 </nav>;
}

function FloatingInquiry(){
 const [visible,setVisible]=useState(false);
 useEffect(()=>{
  const hero=document.getElementById('vtech-intro'),kit=document.getElementById('vtech-kit');
  if(!hero||!kit)return;
  let heroVisible=true,kitVisible=false;
  const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.target===hero)heroVisible=entry.isIntersecting;if(entry.target===kit)kitVisible=entry.isIntersecting;}setVisible(!heroVisible&&!kitVisible);},{threshold:0});
  observer.observe(hero);observer.observe(kit);return()=>observer.disconnect();
 },[]);
 return <a className="vc-floating-inquiry" data-visible={visible} href="#contact" data-product="v-tech-system" data-source="vtech-mobile-sticky" tabIndex={visible?0:-1} aria-hidden={!visible}><bdi dir="ltr">V-TECH</bdi><span>לקבלת מחיר ←</span></a>;
}
export default function VTech(){return <div className="vtech-cinema"><SiteHeader/><SectionNavigation/><main id="main-content">
 <VTechStory/>
 <VTechCases/><VTechOffer/><VTechTraining/><VTechRelated/>
 </main><SiteFooter/><FloatingInquiry/></div>;}
