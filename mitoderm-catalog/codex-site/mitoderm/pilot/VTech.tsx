'use client';

import {useEffect,useState} from 'react';
import {SiteHeader,SiteFooter} from '../shared';
import {VTechStory} from './VTechStory';
import {VTechTraining,VTechRelated} from './VTechDetails';
import './vtech-cinema.css';

const pageSections=[{id:'vtech-intro',label:'הטיפול'},{id:'vtech-results',label:'תוצאות'},{id:'vtech-kit',label:'הערכה'},{id:'vtech-training',label:'הדרכה'}];
function SectionNavigation(){
 const [active,setActive]=useState('vtech-intro');
 useEffect(()=>{
  const storyIds=new Set(['vtech-intro','vtech-hero','vtech-consultation','vtech-pen','vtech-serum','vtech-mask']);
  const selectStorySection=(id?:string)=>{
   if(id==='vtech-results'||id==='vtech-kit')setActive(id);
   else if(id&&storyIds.has(id))setActive('vtech-intro');
  };
  const onStorySection=(event:Event)=>selectStorySection((event as CustomEvent<string>).detail);
  window.addEventListener('mitoderm:vtech-section',onStorySection);
  const observer=new IntersectionObserver(entries=>{
   for(const entry of entries){
    if(entry.isIntersecting){setActive(entry.target.id);continue;}
    // Scrolling back up can leave the training heading before the story's
    // last active chapter changes. Restore it only when training moves below
    // this band; leaving the band upward must keep the training selection.
    if(entry.boundingClientRect.top<(entry.rootBounds?.bottom??window.innerHeight*.35))continue;
    const story=document.querySelector<HTMLElement>('[data-vtech-story]');
    if(!story)continue;
    const bounds=story.getBoundingClientRect();
    if(bounds.bottom>0&&bounds.top<window.innerHeight)selectStorySection(story.dataset.activeChapter);
   }
  },{rootMargin:'-20% 0px -65% 0px',threshold:0});
  const training=document.getElementById('vtech-training');if(training)observer.observe(training);
  return()=>{observer.disconnect();window.removeEventListener('mitoderm:vtech-section',onStorySection);};
 },[]);
 return <nav className="vc-section-nav" aria-label="ניווט בעמוד V-TECH" data-vtech-hud="true">
  <a className="vc-section-brand" dir="ltr" href="/" aria-label="חזרה לכל המוצרים" title="כל המוצרים"><span className="vc-section-brand-title">V-TECH</span><svg className="vc-section-collection-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg></a>
  <div className="vc-section-links">{pageSections.map(item=><a key={item.id} href={'#'+item.id} aria-current={active===item.id?'location':undefined}>{item.label}</a>)}</div>
  <a className="vc-section-inquiry" href="#contact" data-product="v-tech-system" data-source="vtech-section-nav"><span className="vc-section-inquiry-long">לקבלת מחיר</span><span className="vc-section-inquiry-short">הצעה</span><span className="vc-section-inquiry-arrow" aria-hidden="true">←</span></a>
 </nav>;
}

function FloatingInquiry(){
 const [visible,setVisible]=useState(false);
 useEffect(()=>{
  const story=document.querySelector('[data-vtech-story]');
  if(!story)return;
  const observer=new IntersectionObserver(entries=>{for(const entry of entries)setVisible(!entry.isIntersecting&&entry.boundingClientRect.bottom<=0);},{threshold:0});
  observer.observe(story);return()=>observer.disconnect();
 },[]);
 return <a className="vc-floating-inquiry" data-visible={visible} href="#contact" data-product="v-tech-system" data-source="vtech-mobile-sticky" tabIndex={visible?0:-1} aria-hidden={!visible}><bdi dir="ltr">V-TECH</bdi><span>לקבלת מחיר ←</span></a>;
}
export default function VTech(){return <div className="vtech-cinema"><SiteHeader/><SectionNavigation/><main id="main-content">
 <VTechStory/>
 <VTechTraining/><VTechRelated/>
 </main><SiteFooter/><FloatingInquiry/></div>;}
