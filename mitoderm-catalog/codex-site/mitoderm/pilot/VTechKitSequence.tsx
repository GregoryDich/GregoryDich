'use client';

import {useEffect,useId,useState,type CSSProperties,type RefObject} from 'react';

// Stable camera coordinates from the approved open kit. The sleeve uses the
// actual clinic photograph in VTechPackFlight, so its gold/print never changes.
// The original opening assets remain in the repository as source material.
export const kitSequence={width:1277,height:1266,count:40,box:{left:420,top:260,height:900}};
const closedParts='/assets/vtech/unboxing/open-000.webp';
const openedParts='/assets/vtech/unboxing/open-039.webp';
const tray='408,270 800,268 844,1108 501,1158 480,1118';
const lid='827,270 1194,263 1209,1116 871,1155';

/** Native layers move continuously with scroll. Two source images replace the
 * old 40-frame zoom/shrink sequence; five caps and the actual insert stay intact.
 * The brief serum/sachet composition is retained while both parts dock. */
export function VTechKitSequence({stage,style,onReady}:{stage:RefObject<HTMLDivElement|null>;style:CSSProperties;onReady:(mode:'layers'|'fallback')=>void}){
 const [state,setState]=useState<'loading'|'layers'|'fallback'>('loading');
 const id=useId().replace(/:/g,'');
 useEffect(()=>{
  const screen=stage.current;if(!screen)return;
  let disposed=false,started=false;
  const images:HTMLImageElement[]=[];
  const load=(src:string)=>new Promise<void>((resolve,reject)=>{
   const image=new Image();images.push(image);image.decoding='async';
   image.onload=()=>{void image.decode().then(resolve,reject);};image.onerror=reject;image.src=src;
  });
  const sync=()=>{
   if(started||screen.dataset.kitLoad!=='true')return;started=true;
   void Promise.all([load(openedParts),load(closedParts)]).then(()=>{
    if(disposed)return;setState('layers');onReady('layers');
   }).catch(()=>{if(!disposed)setState('fallback');});
  };
  const observer=new MutationObserver(sync);observer.observe(screen,{attributes:true,attributeFilter:['data-kit-load']});sync();
  return()=>{disposed=true;observer.disconnect();images.forEach(image=>{image.onload=null;image.onerror=null;});};
 },[stage,onReady]);
 return <div className="vts-kit-sequence" style={style} data-renderer="continuous-layers" data-state={state} aria-hidden="true">
  {state==='layers'&&<>
   <svg className="vts-kit-tray vts-kit-layer" viewBox="0 0 1277 1266">
    <defs>
     <clipPath id={id+'-tray'}><polygon points={tray}/></clipPath>
     <mask id={id+'-dock'} maskUnits="userSpaceOnUse" x="0" y="0" width="1277" height="1266">
      <rect width="1277" height="1266" fill="white"/>
      <g className="vts-kit-docking-mask" fill="black"><rect x="479" y="309" width="314" height="516" rx="12"/><ellipse cx="745" cy="877" rx="53" ry="54"/></g>
     </mask>
    </defs>
    <polygon points={tray} fill="#0b0c0e"/>
    <image href={openedParts} width="1277" height="1266" clipPath={'url(#'+id+'-tray)'} mask={'url(#'+id+'-dock)'}/>
   </svg>
   <svg className="vts-kit-lid vts-kit-layer" viewBox="0 0 1277 1266">
    <defs><clipPath id={id+'-lid'}><polygon points={lid}/></clipPath></defs>
    <image href={openedParts} width="1277" height="1266" clipPath={'url(#'+id+'-lid)'}/>
   </svg>
   <div className="vts-kit-pouch vts-kit-layer vts-kit-floating"><img src={closedParts} alt="" draggable={false}/></div>
   <div className="vts-kit-vial vts-kit-layer vts-kit-floating"><img src={closedParts} alt="" draggable={false}/></div>
  </>}
  {state==='fallback'&&<img className="vts-kit-sequence-fallback" src="/assets/vtech/kit-open.webp" alt="" width="1188" height="882" onLoad={()=>onReady('fallback')}/>}
 </div>;
}
