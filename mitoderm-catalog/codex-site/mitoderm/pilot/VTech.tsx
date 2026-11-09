'use client';

import {useEffect,useState} from 'react';
import {SiteHeader,SiteFooter} from '../shared';
import {ScrollScrub} from '@/components/scroll-scrub/scroll-scrub';
import {scrollScrubScenes,scrollScrubTheme} from '@/scroll-scrub-scenes';
import {CinematicStage} from './CinematicStage';
import {VTechCases,VTechOffer,VTechRelated} from './VTechDetails';
import './vtech-cinema.css';

const clinicalScenes=[
 {id:'vtech-pen',kind:'pen',title:'עבודה מדויקת באזור שנבחר',name:'MITOPEN',body:'מיקרונידלינג כחלק מתוכנית עבודה מקצועית.',alt:'הקוסמטיקאית עובדת עם MITOPEN באזור הלחי של אותה מטופלת'},
 {id:'vtech-serum',kind:'serum',title:'הסרום במרכז המערכת',name:'V-TECH SERUM',body:'מבט מקרוב על יישום הסרום באזור הטיפול.',alt:'יישום סרום V-TECH על אזור הלחי'},
 {id:'vtech-mask',kind:'mask',title:'השלב הבא באותה מערכת',name:'V-TECH GEL MASK',body:'מסכת הג׳ל משלימה את המערכת על אותו אזור.',alt:'יישום ג׳ל V-TECH GEL MASK על הלחי'}
] as const;
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
export default function VTech(){return <div className="vtech-cinema"><SiteHeader/><main id="main-content">
 <div id="vtech-intro" className="vc-intro"><ScrollScrub scenes={scrollScrubScenes} theme={scrollScrubTheme} className="vc-scrub"/></div>
 <nav className="vc-page-nav" aria-label="ניווט בעמוד V-TECH"><a href="/" className="vc-back-collection">כל המוצרים <span aria-hidden="true">↗</span></a><div><a href="#vtech-consultation">הטיפול</a><a href="#vtech-results">מקרי טיפול</a><a href="#vtech-kit">הערכה</a></div><a className="vc-nav-inquiry" href="#contact" data-product="v-tech-system" data-source="vtech-section-nav">לקבלת מחיר</a></nav>
 <section id="vtech-consultation" className="vc-consultation" aria-labelledby="vc-consultation-title"><div className="vc-consultation-heading"><h2 id="vc-consultation-title">מתחילים באדם שמולנו</h2><p>מכירים את העור, מקשיבים למטרה ובוחרים את אזור העבודה.</p></div><CinematicStage media={{poster:'/assets/world/vtech-consultation.webp',mobilePoster:'/assets/world/vtech-consultation-mobile.webp'}} alt="המחשת טיפול: קוסמטיקאית מקשיבה למטופלת ובוחנת את אזור הלחי"/><div className="vc-consultation-caption"><div><p>מראה הקמטוטים ומרקם העור. בקשה אחת, אזור אחד ותוכנית מקצועית מותאמת.</p><p className="vc-media-note">סרטון המחשה שנוצר ב־AI</p></div><a href="#contact" data-product="v-tech-system" data-source="vtech-consultation" data-topic="protocol">לשיחה על התאמה <span aria-hidden="true">←</span></a></div></section>
 <div className="vc-procedure" aria-label="עיקרי הטיפול">{clinicalScenes.map(scene=><section key={scene.id} id={scene.id} className={'vc-treatment vc-treatment-'+scene.kind} aria-labelledby={scene.id+'-title'}><div className="vc-treatment-copy"><span className="vc-stage-name" dir="ltr">{scene.name}</span><h2 id={scene.id+'-title'}>{scene.title}</h2><p>{scene.body}</p></div><CinematicStage media={{poster:'/assets/world/vtech-'+scene.kind+'-poster.webp',mobilePoster:'/assets/world/vtech-'+scene.kind+'-mobile-poster.webp',clip:'/assets/world/vtech-'+scene.kind+'.mp4',mobileClip:'/assets/world/vtech-'+scene.kind+'-mobile.mp4'}} alt={scene.alt} className={'vc-shot-'+scene.kind}/></section>)}</div>
 <VTechCases/><VTechOffer/><VTechRelated/>
 </main><SiteFooter/><FloatingInquiry/></div>;}
