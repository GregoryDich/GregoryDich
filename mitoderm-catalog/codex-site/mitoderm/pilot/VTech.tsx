'use client';

import {useEffect,useState} from 'react';
import {SiteHeader,SiteFooter} from '../shared';
import {VTechStory} from './VTechStory';
import {VTechCases,VTechOffer,VTechRelated} from './VTechDetails';
import './vtech-cinema.css';

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
 <VTechStory/>
 <VTechCases/><VTechOffer/><VTechRelated/>
 </main><SiteFooter/><FloatingInquiry/></div>;}
