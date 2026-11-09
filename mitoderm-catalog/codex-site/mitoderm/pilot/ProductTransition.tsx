'use client';

import {useEffect,useRef,type CSSProperties} from 'react';
import {getEntryMedia,type EntryRect} from './vtech-entry';

export type ProductFlight={id:number;slug:string;src:string;rect:EntryRect;box:EntryRect;href:string;photo?:{rect:EntryRect;silhouette:string}};

/** A selected photograph survives navigation and grows with native scroll. */
export function ProductTransition({flight,onNavigate,onFinish}:{flight:ProductFlight;onNavigate:(href:string)=>void;onFinish:()=>void}){
 const root=useRef<HTMLDivElement>(null),cutout=useRef<HTMLDivElement>(null);
 const matched=useRef<HTMLDivElement>(null),glint=useRef<HTMLDivElement>(null),room=useRef<HTMLImageElement>(null),backdrop=useRef<HTMLImageElement>(null);
 const veil=useRef<HTMLDivElement>(null),label=useRef<HTMLDivElement>(null),enterButton=useRef<HTMLButtonElement>(null);
 const skip=useRef<()=>void>(()=>{});
 const media=getEntryMedia(typeof window==='undefined'?1200:window.innerWidth);
 useEffect(()=>{
  const source=cutout.current,exact=matched.current,scene=room.current,ground=veil.current;
  if(!source||!exact||!scene||!ground)return;
  let cancelled=false,finishing=false,skipRequested=false,scrollFrame=0;
  let readScroll:()=>void=()=>{},resize:()=>void=()=>{};
  const animations:Animation[]=[],timers=new Set<number>();
  const delay=(ms:number)=>new Promise<void>(resolve=>{const id=window.setTimeout(()=>{timers.delete(id);resolve();},ms);timers.add(id);});
  const animate=(element:HTMLElement,keyframes:Keyframe[],options:KeyframeAnimationOptions)=>{
   const animation=element.animate(keyframes,{fill:'forwards',...options});animations.push(animation);return animation;
  };
  const onScroll=()=>{if(!scrollFrame)scrollFrame=window.requestAnimationFrame(()=>{scrollFrame=0;readScroll();});};
  const onResize=()=>resize();
  const onKey=(event:KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();skip.current();}};
  skip.current=()=>{skipRequested=true;};
  window.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('resize',onResize,{passive:true});
  window.addEventListener('keydown',onKey);
  document.documentElement.dataset.productTransit=flight.slug;
  const run=async()=>{
   animate(ground,[{opacity:0},{opacity:.96}],{duration:400,easing:'ease-out'});
   animate(source,[{transform:'translate3d(0,0,0) scale(1)'},{transform:'translate3d(0,-14px,0) scale(1.08)'}],{duration:230,easing:'ease-out'});
   animate(label.current!,[{opacity:0,transform:'translateY(10px)'},{opacity:1,transform:'translateY(0)'}],{duration:280,delay:200});
   if(backdrop.current)animate(backdrop.current,[{opacity:1},{opacity:.24}],{duration:420,easing:'ease-out'});
   await delay(230);if(cancelled)return;
   onNavigate(flight.href);
   const started=performance.now();let destination:HTMLElement|null=null;
   while(!cancelled&&performance.now()-started<6000){
    destination=document.querySelector<HTMLElement>('[data-flight-target="v-tech-system"]');
    const poster=document.querySelector<HTMLImageElement>('[data-vtech-entry-poster]');
    if(destination&&destination.getBoundingClientRect().height>40&&poster?.complete&&poster.naturalWidth>0)break;
    destination=null;await delay(40);
   }
   if(cancelled)return;if(!destination){onFinish();return;}
   await Promise.race([scene.decode().catch(()=>undefined),delay(1200)]);if(cancelled)return;
   const story=destination.closest<HTMLElement>('[data-vtech-story]');
   const stageElement=document.querySelector<HTMLElement>('[data-vtech-stage]');
   const target=destination.getBoundingClientRect();
   const stage=stageElement?.getBoundingClientRect()??{left:0,top:0,width:window.innerWidth,height:window.innerHeight};
   const entry=getEntryMedia(stage.width),cover=Math.max(stage.width/entry.width,stage.height/entry.height);
   const renderedWidth=entry.width*cover,renderedHeight=entry.height*cover;
   const offsetX=(stage.width-renderedWidth)/2,offsetY=(stage.height-renderedHeight)/2;
   Object.assign(exact.style,{left:target.left+'px',top:target.top+'px',width:target.width+'px',height:target.height+'px',backgroundImage:`url("${entry.poster}")`,backgroundSize:`${renderedWidth}px ${renderedHeight}px`,backgroundPosition:`${stage.left+offsetX-target.left}px ${stage.top+offsetY-target.top}px`,clipPath:entry.silhouette});
   if(glint.current)Object.assign(glint.current.style,{left:target.left+'px',top:target.top+'px',width:target.width+'px',height:target.height+'px',clipPath:entry.silhouette});
   Object.assign(scene.style,{left:stage.left+'px',top:stage.top+'px',width:stage.width+'px',height:stage.height+'px'});
   const scaleX=target.width/flight.box.width,scaleY=target.height/flight.box.height;
   const dx=target.left-flight.box.left,dy=target.top-flight.box.top;
   const endLeft=target.left-(flight.box.left-flight.rect.left)*scaleX,endTop=target.top-(flight.box.top-flight.rect.top)*scaleY;
   const sourceEnd=`translate3d(${endLeft-flight.rect.left}px,${endTop-flight.rect.top}px,0) scale(${scaleX},${scaleY})`;
   const exactStart=`translate3d(${-dx}px,${-dy-14}px,0) scale(${1.08/scaleX},${1.08/scaleY})`;
   const scrub:Animation[]=[];
   const tracked=(element:HTMLElement,keyframes:Keyframe[])=>{const animation=animate(element,keyframes,{duration:1000,easing:'linear',fill:'both'});animation.pause();animation.currentTime=0;scrub.push(animation);};
   tracked(source,[{transform:'translate3d(0,-14px,0) scale(1.08)'},{transform:sourceEnd}]);
   // A brief foil highlight covers the change of photographic lighting. The two
   // printed faces never overlap, even when the viewer stops halfway through.
   tracked(source,[{opacity:1,offset:0},{opacity:1,offset:.57},{opacity:0,offset:.625},{opacity:0,offset:1}]);
   tracked(exact,[{transform:exactStart},{transform:'translate3d(0,0,0) scale(1)'}]);
   tracked(exact,[{opacity:0,offset:0},{opacity:0,offset:.625},{opacity:1,offset:.68},{opacity:1,offset:1}]);
   if(glint.current){tracked(glint.current,[{transform:exactStart},{transform:'translate3d(0,0,0) scale(1)'}]);tracked(glint.current,[{opacity:0,offset:0},{opacity:0,offset:.56},{opacity:.98,offset:.625},{opacity:0,offset:.69},{opacity:0,offset:1}]);}
   tracked(scene,[{opacity:0,offset:0},{opacity:0,offset:.6},{opacity:1,offset:.96},{opacity:1,offset:1}]);
   tracked(label.current!,[{opacity:1,offset:0},{opacity:1,offset:.65},{opacity:0,offset:.94},{opacity:0,offset:1}]);
   if(backdrop.current)tracked(backdrop.current,[{opacity:.24,offset:0},{opacity:0,offset:.35},{opacity:0,offset:1}]);
   const entryUnits=Number(story?.dataset.entryUnits)||.9;
   const entryStart=()=>Number(story?.dataset.entryStart)||0;
   const entryDistance=()=>Math.max(1,(stageElement?.clientHeight??stage.height)*entryUnits);
   root.current?.setAttribute('data-phase','awaiting-scroll');enterButton.current?.focus({preventScroll:true});
   const finish=async()=>{if(finishing||cancelled)return;finishing=true;root.current?.setAttribute('data-phase','settled');animate(root.current!,[{opacity:1},{opacity:0}],{duration:160});await delay(170);if(!cancelled)onFinish();};
   readScroll=()=>{
    if(finishing||cancelled)return;
    const progress=Math.max(0,Math.min(1,(window.scrollY-entryStart())/entryDistance()));
    scrub.forEach(animation=>{animation.currentTime=progress*1000;});root.current?.style.setProperty('--flight-progress',String(progress));
    if(progress>=.999)void finish();
   };
   skip.current=()=>{window.scrollTo({top:entryStart()+entryDistance()+1,behavior:'instant'});readScroll();};
   resize=()=>skip.current();if(skipRequested)skip.current();else readScroll();
  };
  void run().catch(()=>{if(!cancelled)onFinish();});
  return()=>{
   cancelled=true;timers.forEach(id=>window.clearTimeout(id));animations.forEach(animation=>animation.cancel());window.cancelAnimationFrame(scrollFrame);
   window.removeEventListener('scroll',onScroll);window.removeEventListener('resize',onResize);window.removeEventListener('keydown',onKey);delete document.documentElement.dataset.productTransit;
  };
 // One effect owns one selected-product transition across the route boundary.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[flight.id]);
 const sourceStyle:CSSProperties={...flight.rect,backgroundImage:`url("${flight.src}")`,backgroundSize:flight.photo?`${flight.photo.rect.width}px ${flight.photo.rect.height}px`:'100% 100%',backgroundPosition:flight.photo?`${flight.photo.rect.left-flight.rect.left}px ${flight.photo.rect.top-flight.rect.top}px`:'0 0',clipPath:flight.photo?.silhouette};
 return <div ref={root} className="vc-product-flight" data-phase="selecting" role="region" aria-label="כניסה לחוויית V-TECH">
  <div ref={veil} className="vc-product-flight-ground"/>
  {flight.photo&&<img ref={backdrop} className="vc-flight-backdrop" src={flight.src} alt="" style={flight.photo.rect}/>}
  <img ref={room} className="vc-flight-room" src={media.poster} alt="" decoding="async"/>
  <div ref={cutout} className="vc-flight-cutout" style={sourceStyle}/><div ref={matched} className="vc-flight-matched"/><div ref={glint} className="vc-flight-glint" aria-hidden="true"/>
  <div ref={label} className="vc-flight-caption"><span>MITODERM · THE CLINIC EXPERIENCE</span><bdi dir="ltr">V-TECH SYSTEM</bdi><p>גללו כדי להיכנס לקליניקה <span aria-hidden="true">↓</span></p><button ref={enterButton} type="button" onClick={()=>skip.current()}>למעבר ישיר <span aria-hidden="true">←</span></button></div>
  <div className="vc-flight-progress" aria-hidden="true"><span/></div>
 </div>;
}
