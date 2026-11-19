'use client';

import {useCallback,useEffect,useRef,useState,type CSSProperties,type RefObject} from 'react';
import {getEntryBoxRect,getEntryMedia} from './vtech-entry';
import {mediaUrl} from '../media';
import {VTechKitSequence,kitSequence} from './VTechKitSequence';
import './vtech-pack-flight.css';

type Geometry={style:CSSProperties;sequence:CSSProperties;poster:string;backdrop:string;image:CSSProperties;silhouette:string;window:string;triangle:string;clip:CSSProperties;clipSrc:string};

// Generated opening footage (16:9, both files), in 1920x1080 frame units: the
// closed box on its first frame (= the film's last frame) and the opened kit
// on its last frame. The frame starts over the film's box and pulls back onto
// the offer slot; the layer sequence stays for loading, errors and old data.
const clipFrame={width:1920,height:1080},clipBox={left:716,top:40,height:974},clipKit={left:428,top:182,width:1054,height:730};
type ClipState='off'|'loading'|'ready'|'error';

/** The last camera frame returns to the original pack. Its exact photographic
 * silhouette then takes over, so the offer never introduces a second product. */
export function VTechPackFlight({stage,reduced}:{stage:RefObject<HTMLDivElement|null>;reduced:boolean}){
 const [geometry,setGeometry]=useState<Geometry|null>(null);
 const [sequenceMode,setSequenceMode]=useState<'loading'|'layers'|'fallback'>('loading');
 const ready=useCallback((mode:'layers'|'fallback')=>setSequenceMode(mode),[]);
 const clipVideo=useRef<HTMLVideoElement>(null);
 const [clipState,setClipState]=useState<ClipState>('off');
 const [clipBlob,setClipBlob]=useState<string|null>(null);
 useEffect(()=>{
  const screen=stage.current;if(reduced){setSequenceMode('loading');return;}if(!screen)return;
  const target=screen.querySelector<HTMLElement>('[data-kit-product-target]');
  if(!target)return;
  let pending=0,disposed=false;
  const measure=()=>{
   if(disposed)return;
   const frame=screen.getBoundingClientRect(),slot=target.getBoundingClientRect();
   if(!frame.width||!frame.height||!slot.width||!slot.height)return;
   const media=getEntryMedia(window.innerWidth),box=getEntryBoxRect(frame.width,frame.height);
   // One fixed camera and one physical scale for the closed and open pack.
   // The photograph itself becomes the moving sleeve; it is never dissolved
   // into the old, differently lit 3D carton or its zooming frame sequence.
   const sequenceScale=Math.min(slot.width/kitSequence.width,slot.height/1050)*.98;
   const sequenceLeft=slot.left-frame.left+(slot.width-kitSequence.width*sequenceScale)/2;
   const sequenceTop=slot.top-frame.top+(slot.height-1050*sequenceScale)/2-150*sequenceScale;
   const endHeight=kitSequence.box.height*sequenceScale;
   const endWidth=endHeight*media.box.width/media.box.height;
   const endLeft=sequenceLeft+kitSequence.box.left*sequenceScale;
   const endTop=sequenceTop+kitSequence.box.top*sequenceScale;
   const sourceScale=box.width/media.box.width;
   const mobile=window.innerWidth<=860;
   const clipStart=box.height/clipBox.height,clipEnd=Math.min(slot.width/clipKit.width,slot.height/clipKit.height)*.98;
   const clipLeft=box.left-clipBox.left*clipStart,clipTop=box.top-clipBox.top*clipStart;
   const clipEndLeft=slot.left-frame.left+(slot.width-clipKit.width*clipEnd)/2-clipKit.left*clipEnd;
   const clipEndTop=slot.top-frame.top+(slot.height-clipKit.height*clipEnd)/2-clipKit.top*clipEnd;
   const polygon=(points:number[][])=>'polygon('+points.map(([x,y])=>`${(x-media.box.left)/media.box.width*100}% ${(y-media.box.top)/media.box.height*100}%`).join(',')+')';
   const next:Geometry={
    poster:media.poster,backdrop:mediaUrl(mobile?'/assets/world/vtech-mask-mobile-poster.webp':'/assets/world/vtech-mask-poster.webp'),silhouette:media.silhouette,
    triangle:polygon(mobile?[[178,294],[207,294],[193,326]]:[[899,260],[975,259],[938,340]]),
    window:polygon(mobile?[[145,313],[159,313],[195,390],[228,312],[242,312],[195,416]]:[[816,309],[849,308],[940,494],[1023,307],[1056,307],[941,565]]),
    style:{
     '--pack-left':box.left+'px','--pack-top':box.top+'px',
     '--pack-width':box.width+'px','--pack-height':box.height+'px',
     '--pack-dx':(endLeft-box.left)+'px','--pack-dy':(endTop-box.top)+'px',
     '--pack-scale-delta':endHeight/box.height-1,
     '--pack-open-dx':(-400*sequenceScale)+'px',
     '--pack-lift-dy':(-endHeight*1.13)+'px',
     '--pack-return-dy':(endHeight*1.13-10*sequenceScale)+'px',
     '--pack-shadow-left':(endLeft-endWidth*.18)+'px',
     '--pack-shadow-top':(endTop+endHeight-8)+'px',
     '--pack-shadow-width':(endWidth*1.36)+'px',
    } as CSSProperties,
    sequence:{left:sequenceLeft,top:sequenceTop,width:kitSequence.width*sequenceScale,height:kitSequence.height*sequenceScale},
    image:{width:media.width*sourceScale,height:media.height*sourceScale,left:-media.box.left*sourceScale,top:-media.box.top*sourceScale},
    clip:{left:clipLeft,top:clipTop,width:clipFrame.width*clipStart,height:clipFrame.height*clipStart,
     '--clip-dx':(clipEndLeft-clipLeft)+'px','--clip-dy':(clipEndTop-clipTop)+'px','--clip-scale-delta':clipEnd/clipStart-1} as CSSProperties,
    clipSrc:mediaUrl(mobile?'/assets/world/vtech-kit-open-mobile.mp4':'/assets/world/vtech-kit-open.mp4'),
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
 const hasGeometry=geometry!==null,clipSrc=geometry?.clipSrc;
 useEffect(()=>{
  // Load the footage only near the kit, as the layer sequence does.
  const screen=stage.current;if(reduced||!screen)return;
  const sync=()=>{if(screen.dataset.kitLoad==='true')setClipState(current=>current==='off'?'loading':current);};
  const observer=new MutationObserver(sync);
  observer.observe(screen,{attributes:true,attributeFilter:['data-kit-load']});sync();
  return()=>observer.disconnect();
 },[stage,reduced]);
 useEffect(()=>{
  const screen=stage.current,video=clipVideo.current;if(!screen||!video)return;
  // Scroll owns the footage: data-kit-clip is its progress, set by VTechStory.
  const target=()=>(+(screen.dataset.kitClip??0))*Math.max(0,video.duration-.04);
  const seekable=()=>video.seekable.length>0&&video.seekable.end(0)>=video.duration-.1;
  const sync=()=>{
   if(video.readyState<2||!Number.isFinite(video.duration)||!seekable())return;
   const time=target();
   if(Math.abs(video.currentTime-time)<.03){setClipState(current=>current==='loading'?'ready':current);return;}
   if(!video.seeking)video.currentTime=time;
  };
  const failed=()=>setClipState('error');
  // A server without byte ranges (the local worker) leaves the video
  // unseekable; the short clip is then read whole and played from memory.
  const loaded=()=>{
   if(seekable()||video.currentSrc.startsWith('blob:')){sync();return;}
   void fetch(video.currentSrc).then(response=>response.ok?response.blob():Promise.reject(new Error(String(response.status)))).then(blob=>setClipBlob(URL.createObjectURL(blob))).catch(failed);
  };
  const observer=new MutationObserver(sync);
  observer.observe(screen,{attributes:true,attributeFilter:['data-kit-clip']});
  video.addEventListener('loadeddata',loaded);video.addEventListener('seeked',sync);video.addEventListener('error',failed);if(video.readyState>=2)loaded();
  return()=>{observer.disconnect();video.removeEventListener('loadeddata',loaded);video.removeEventListener('seeked',sync);video.removeEventListener('error',failed);};
 },[stage,hasGeometry,clipSrc,clipState]);
 useEffect(()=>()=>{if(clipBlob)URL.revokeObjectURL(clipBlob);},[clipBlob]);
 if(reduced||!geometry)return null;
 return <div className="vts-pack-flight" style={geometry.style} data-sequence-ready={sequenceMode!=='loading'} data-kit-renderer={sequenceMode} data-clip={clipState} aria-hidden="true">
  <div className="vts-pack-backdrop"><img src={geometry.backdrop} alt=""/></div>
  {clipState!=='off'&&clipState!=='error'&&<video ref={clipVideo} className="vts-kit-clip" style={geometry.clip} src={clipBlob??geometry.clipSrc} muted playsInline preload="auto" tabIndex={-1} onLoadStart={()=>setClipState(current=>current==="ready"?"loading":current)}/>}
  <div className="vts-pack-ground"/>
  <div className="vts-pack-object"><div className="vts-pack-sleeve"><div className="vts-pack-cutout" style={{clipPath:geometry.silhouette}}>
   <img src={geometry.poster} style={geometry.image} alt="" draggable={false}/>
   <span className="vts-pack-window" style={{clipPath:geometry.window}}/>
   <span className="vts-pack-window" style={{clipPath:geometry.triangle}}/>
   <span className="vts-pack-softlight"/>
  </div></div></div>
  <VTechKitSequence stage={stage} style={geometry.sequence} onReady={ready}/>
 </div>;
}
