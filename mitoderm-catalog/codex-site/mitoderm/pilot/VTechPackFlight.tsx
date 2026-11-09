'use client';

import {useEffect,useState,type CSSProperties,type RefObject} from 'react';
import {getEntryBoxRect,getEntryMedia} from './vtech-entry';
import './vtech-pack-flight.css';

type Geometry={style:CSSProperties;poster:string;image:CSSProperties;silhouette:string};

/** The last camera frame returns to the original pack. Its exact photographic
 * silhouette then takes over, so the offer never introduces a second product. */
export function VTechPackFlight({stage,reduced}:{stage:RefObject<HTMLDivElement|null>;reduced:boolean}){
 const [geometry,setGeometry]=useState<Geometry|null>(null);
 useEffect(()=>{
  const screen=stage.current;if(!screen||reduced)return;
  const target=screen.querySelector<HTMLElement>('[data-kit-product-target]');
  if(!target)return;
  let pending=0,disposed=false;
  const measure=()=>{
   if(disposed)return;
   const frame=screen.getBoundingClientRect(),slot=target.getBoundingClientRect();
   if(!frame.width||!frame.height||!slot.width||!slot.height)return;
   const media=getEntryMedia(frame.width),box=getEntryBoxRect(frame.width,frame.height);
   const fit=Math.min(slot.width/box.width,slot.height/box.height)*.94;
   const endWidth=box.width*fit,endHeight=box.height*fit;
   const endLeft=slot.left-frame.left+(slot.width-endWidth)/2;
   const endTop=slot.top-frame.top+(slot.height-endHeight)/2;
   const sourceScale=box.width/media.box.width;
   const next:Geometry={
    poster:media.poster,silhouette:media.silhouette,
    style:{
     '--pack-left':box.left+'px','--pack-top':box.top+'px',
     '--pack-width':box.width+'px','--pack-height':box.height+'px',
     '--pack-dx':(endLeft-box.left)+'px','--pack-dy':(endTop-box.top)+'px',
     '--pack-scale-delta':fit-1,
     '--pack-shadow-left':(endLeft-endWidth*.18)+'px',
     '--pack-shadow-top':(endTop+endHeight-8)+'px',
     '--pack-shadow-width':(endWidth*1.36)+'px',
    } as CSSProperties,
    image:{width:media.width*sourceScale,height:media.height*sourceScale,left:-media.box.left*sourceScale,top:-media.box.top*sourceScale},
   };
   setGeometry(previous=>JSON.stringify(previous)===JSON.stringify(next)?previous:next);
  };
  // A navigation change can move a fixed-size slot without resizing it.
  // Measure after React and the immersed-layout rule have both painted.
  const afterLayout=()=>{
   if(pending)window.cancelAnimationFrame(pending);
   pending=window.requestAnimationFrame(()=>{pending=window.requestAnimationFrame(()=>{pending=0;measure();});});
  };
  const observer=new ResizeObserver(measure);observer.observe(screen);observer.observe(target);
  window.addEventListener('resize',afterLayout,{passive:true});
  window.addEventListener('mitoderm:vtech-section',afterLayout);
  void document.fonts.ready.then(()=>{if(!disposed)afterLayout();});measure();
  return()=>{disposed=true;observer.disconnect();if(pending)window.cancelAnimationFrame(pending);window.removeEventListener('resize',afterLayout);window.removeEventListener('mitoderm:vtech-section',afterLayout);};
 },[stage,reduced]);
 if(reduced||!geometry)return null;
 return <div className="vts-pack-flight" style={geometry.style} aria-hidden="true">
  <div className="vts-pack-backdrop"><img src={geometry.poster} alt=""/></div>
  <div className="vts-pack-ground"/>
  <div className="vts-pack-object"><div className="vts-pack-cutout" style={{clipPath:geometry.silhouette}}><img src={geometry.poster} style={geometry.image} alt="" draggable={false}/></div></div>
 </div>;
}
