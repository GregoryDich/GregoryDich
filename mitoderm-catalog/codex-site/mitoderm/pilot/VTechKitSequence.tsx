'use client';

import {useEffect,useId,useState,type CSSProperties,type RefObject} from 'react';

// Geometry is referenced to the approved fully opened V-TECH composition.
// The exterior gold sleeve is drawn by VTechPackFlight from the same closed
// pack photo throughout; only the physical internal case is depicted here.
// The exact manufactured motion was checked against IMG_9258.MOV.
export const kitSequence={width:1277,height:1266,count:40,box:{left:420,top:260,height:900}};
const openedParts='/assets/vtech/unboxing/open-039.webp';
const tray='408,270 800,268 844,1108 501,1158 480,1118';
const lid='827,270 1194,263 1209,1116 871,1155';

/** Sequence: (1) exterior sleeve slides along the long axis, (2) the
 * closed inner black case is exposed, (3) its hinged door folds open,
 * (4) the approved open-kit packshot settles. All phases reverse on scroll. */
export function VTechKitSequence({stage,style,onReady}:{stage:RefObject<HTMLDivElement|null>;style:CSSProperties;onReady:(mode:'layers'|'fallback')=>void}){
 const [state,setState]=useState<'loading'|'layers'|'fallback'>('loading');
 const id=useId().replace(/:/g,'');
 useEffect(()=>{
  const screen=stage.current;if(!screen)return;
  let disposed=false,started=false;
  const image=new Image();image.decoding='async';
  const sync=()=>{
   if(started||screen.dataset.kitLoad!=='true')return;started=true;
   image.onload=()=>{void image.decode().then(()=>{if(!disposed){setState('layers');onReady('layers');}}).catch(()=>{if(!disposed)setState('fallback');});};
   image.onerror=()=>{if(!disposed)setState('fallback');};
   image.src=openedParts;
  };
  const observer=new MutationObserver(sync);
  observer.observe(screen,{attributes:true,attributeFilter:['data-kit-load']});sync();
  return()=>{disposed=true;observer.disconnect();image.onload=null;image.onerror=null;};
 },[stage,onReady]);

 return <div className="vts-kit-sequence" style={style} data-renderer="physical-sleeve-and-hinge" data-state={state} aria-hidden="true">
  {state==='layers'&&<>
   <svg className="vts-kit-tray vts-kit-layer" viewBox="0 0 1277 1266" preserveAspectRatio="none">
    <defs><clipPath id={id+'-tray'}><polygon points={tray}/></clipPath></defs>
    <polygon points={tray} fill="#101114"/>
    <image href={openedParts} width="1277" height="1266" clipPath={'url(#'+id+'-tray)'}/>
   </svg>
   <div className="vts-kit-black-door" role="presentation">
    <div className="vts-kit-door-face vts-kit-door-front">
     <span className="vts-kit-door-vm">VM</span>
     <span className="vts-kit-door-vmark">V</span>
     <span className="vts-kit-door-wordmark">V - T E C H<small>S Y S T E M</small></span>
    </div>
    <div className="vts-kit-door-face vts-kit-door-reverse">
     <span className="vts-kit-door-vm">VM</span>
     <span className="vts-kit-door-vmark">V</span>
     <span className="vts-kit-door-wordmark">V - T E C H<small>S Y S T E M</small></span>
    </div>
   </div>
   <svg className="vts-kit-lid vts-kit-layer" viewBox="0 0 1277 1266" preserveAspectRatio="none">
    <defs><clipPath id={id+'-lid'}><polygon points={lid}/></clipPath></defs>
    <image href={openedParts} width="1277" height="1266" clipPath={'url(#'+id+'-lid)'}/>
   </svg>
  </>}
  {state==='fallback'&&<img className="vts-kit-sequence-fallback" src="/assets/vtech/kit-open.webp" alt="" width="1188" height="882" onLoad={()=>onReady('fallback')}/>}
 </div>;
}
