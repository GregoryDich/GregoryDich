'use client';

import {useEffect,useRef,type CSSProperties,type RefObject} from 'react';

// Original owner-approved pack opening from the previous V-TECH page. These
// transparent frames retain the actual sleeve, lid and 5 + 5 insert layout.
export const kitSequence={width:1277,height:1266,count:40,box:{left:520,top:158,width:255,height:567}};
const frameUrl=(index:number)=>'/assets/vtech/unboxing/open-'+String(index).padStart(3,'0')+'.webp';

export function VTechKitSequence({stage,style,onReady}:{stage:RefObject<HTMLDivElement|null>;style:CSSProperties;onReady:()=>void}){
 const canvas=useRef<HTMLCanvasElement>(null),group=useRef<HTMLDivElement>(null);
 const fallbackImage=useRef<HTMLImageElement>(null),fallbackLoaded=useRef<()=>void>(()=>{});
 useEffect(()=>{
  const screen=stage.current,element=canvas.current,container=group.current;
  const context=element?.getContext('2d',{alpha:true});
  if(!screen||!element||!context||!container)return;
  const controller=new AbortController();
  const blobs=new Map<number,Promise<Blob>>(),decoded=new Map<number,ImageBitmap>();
  let disposed=false,started=false,wanted=0,drawn=-1,busy=false,ready=false,wantsFallback=false;
  const cacheSize=window.innerWidth<=860?4:6;
  const blob=(index:number)=>{
   let request=blobs.get(index);
   if(!request){request=fetch(frameUrl(index),{signal:controller.signal}).then(response=>{if(!response.ok)throw new Error('Kit frame unavailable');return response.blob();});blobs.set(index,request);}
   return request;
  };
  const showReady=()=>{if(!ready){ready=true;onReady();}};
  const revealFallback=()=>{
   if(disposed||!wantsFallback)return;
   container.dataset.fallback='true';showReady();
  };
  fallbackLoaded.current=revealFallback;
  const fallback=()=>{
   if(disposed)return;wantsFallback=true;
   const image=fallbackImage.current;if(!image)return;
   image.loading='eager';
   if(image.complete&&image.naturalWidth>0)revealFallback();
  };
  const paint=async()=>{
   if(disposed||drawn===wanted||busy)return;
   busy=true;
   try{
    while(!disposed&&drawn!==wanted){
    const index=wanted;
    let bitmap=decoded.get(index);
    if(!bitmap){
     const bytes=await blob(index);
     if(disposed)return;
     // Decode only a few adjacent frames. Keeping all40 RGBA frames decoded
     // would use about259MB on a phone for a2MB compressed sequence.
     bitmap=await createImageBitmap(bytes);
     if(disposed){bitmap.close();return;}
     decoded.set(index,bitmap);
    }
    if(index===wanted){
     context.clearRect(0,0,kitSequence.width,kitSequence.height);
     context.drawImage(bitmap,0,0);drawn=index;
     wantsFallback=false;container.dataset.frame=String(index);container.dataset.fallback='false';showReady();
    }
    // LRU is bounded even after forward/backward scrubbing.
    decoded.delete(index);decoded.set(index,bitmap);
    while(decoded.size>cacheSize){const oldest=decoded.keys().next().value;if(oldest===undefined)break;decoded.get(oldest)?.close();decoded.delete(oldest);}
    }
   }catch{fallback();}
   finally{busy=false;}
  };
  const start=()=>{
   if(started)return;started=true;
   // Compressed prefetch starts one chapter before the offer, not at entry.
   // Three workers keep requests modest; the currently wanted frame has priority.
   const queue=[0,39,...Array.from({length:38},(_,i)=>i+1)];
   const worker=async()=>{while(!disposed&&queue.length){const index=queue.shift();if(index===undefined)return;try{await blob(index);}catch{if(disposed)return;}}};
   void worker();void worker();void worker();
  };
  const sync=()=>{
   if(screen.dataset.kitLoad!=='true')return;
   wanted=Math.max(0,Math.min(kitSequence.count-1,Number(screen.dataset.kitFrame)||0));
   if(typeof createImageBitmap!=='function'){fallback();return;}
   start();
   void paint();
  };
  const observer=new MutationObserver(sync);observer.observe(screen,{attributes:true,attributeFilter:['data-kit-frame','data-kit-load']});sync();
  return()=>{disposed=true;fallbackLoaded.current=()=>{};observer.disconnect();controller.abort();decoded.forEach(bitmap=>bitmap.close());decoded.clear();blobs.clear();};
 },[stage,onReady]);
 return <div className="vts-kit-sequence" ref={group} style={style} data-fallback="false" aria-hidden="true">
  <canvas ref={canvas} width={kitSequence.width} height={kitSequence.height}/>
  <img ref={fallbackImage} className="vts-kit-sequence-fallback" src="/assets/vtech/kit-open.webp" alt="" width="1188" height="882" loading="lazy" onLoad={()=>fallbackLoaded.current()}/>
 </div>;
}
