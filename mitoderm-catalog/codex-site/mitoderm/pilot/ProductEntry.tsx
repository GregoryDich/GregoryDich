'use client';

import {useEffect,useRef,type CSSProperties} from 'react';
import type {EntryRect} from './vtech-entry';
import {filmPack,filmPackRect} from './film-entry';

/** The chosen product of the home page: where it stands on the screen and the picture that lifts off.
 * `pack` is a separate cut-out of the product; `photo` is the banner photograph, shown through a soft window.
 * With both (the phone banner, whose packs are part of one photograph) the window of the photograph lifts off
 * and turns into the clean cut-out on the way. */
export type ProductEntryFlight={id:number;slug:string;name:string;href:string;rect:EntryRect;feather?:boolean;
 pack?:{src:string};photo?:{src:string;rect:EntryRect}};

/** Home -> product for every product except V-TECH (which has its own measured flight):
 * the chosen pack lifts off the collection and comes forward, the collection goes dark, the product is named,
 * the product page loads underneath, and the pack comes down onto its own place in the first frame of the
 * product's film (film-entry.ts) while the overlay clears. */
export function ProductEntry({flight,onNavigate,onFinish}:{flight:ProductEntryFlight;onNavigate:(href:string)=>void;onFinish:()=>void}){
 const root=useRef<HTMLDivElement>(null),ground=useRef<HTMLDivElement>(null),pack=useRef<HTMLDivElement>(null),caption=useRef<HTMLDivElement>(null);
 const window_=useRef<HTMLDivElement>(null),cutout=useRef<HTMLDivElement>(null);
 const skip=useRef<()=>void>(()=>{});
 useEffect(()=>{
  const veil=ground.current,item=pack.current,label=caption.current;
  if(!veil||!item||!label)return;
  let cancelled=false,skipped=false,finished=false;
  const animations:Animation[]=[],timers=new Set<number>();
  const delay=(ms:number)=>new Promise<void>(resolve=>{const id=window.setTimeout(()=>{timers.delete(id);resolve();},ms);timers.add(id);});
  const animate=(element:HTMLElement,keyframes:Keyframe[],options:KeyframeAnimationOptions)=>{
   const animation=element.animate(keyframes,{fill:'forwards',...options});animations.push(animation);return animation;
  };
  const finish=()=>{if(finished||cancelled)return;finished=true;delete document.documentElement.dataset.productEntry;onFinish();};
  const onKey=(event:KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();skip.current();}};
  window.addEventListener('keydown',onKey);
  document.documentElement.dataset.productEntry=flight.slug;
  const view={width:window.innerWidth,height:window.innerHeight},phone=view.width<=860;
  const {rect}=flight;
  // The cut-out itself, to know its proportions when it is fitted inside a window of the photograph.
  const natural=flight.pack?new Image():null;
  if(natural&&flight.pack)natural.src=flight.pack.src;
  // Every position of the pack has the same shape, so the browser moves, turns and sizes it in one motion.
  const at=(x:number,y:number,size:number,turn=0)=>`translate3d(${x}px,${y}px,0) rotate(${turn}deg) scale(${size})`;
  // The pack comes to the middle of the screen and grows to about half its height.
  // A clean cut-out is a large picture and may grow freely; a window of the photograph may not.
  const scale=Math.max(1,Math.min(view.height*(phone?.42:.5)/rect.height,view.width*(phone?.8:.5)/rect.width,flight.pack?12:3.4));
  const dx=view.width/2-(rect.left+rect.width/2),dy=view.height*(phone?.43:.47)-(rect.top+rect.height/2);
  const forward=at(dx,dy,scale);
  // Without a measured place it leaves toward where a pack usually stands in a first frame: lower left on a wide screen.
  const away=phone?at(dx,dy-view.height*.05,scale*1.05):at(dx-view.width*.17,dy+view.height*.05,scale*.92);
  // The place of this pack in the first frame of its film, as the film is shown now.
  const landing=()=>{
   const film=window.location.pathname===flight.href?document.querySelector<HTMLVideoElement>('video.pc-film'):null;
   const place=film?filmPackRect(flight.slug,film):null;
   if(!place||place.width<4||place.height<4)return null;
   // The picture as it is drawn at size 1: the pack itself, or the cut-out fitted inside a window of the photograph.
   let shown={width:rect.width,height:rect.height};
   if(flight.photo&&natural&&natural.naturalWidth>0){
    const fit=Math.min(rect.width/natural.naturalWidth,rect.height/natural.naturalHeight);
    shown={width:natural.naturalWidth*fit,height:natural.naturalHeight*fit};
   }
   const x=place.left+place.width/2-(rect.left+rect.width/2),y=place.top+place.height/2-(rect.top+rect.height/2);
   const turn=flight.pack?filmPack[flight.slug]?.turn:undefined;
   if(turn&&flight.pack){
    // The pen lies down: its length meets the length of the pen in the film.
    const [degrees,along]=flight.pack.src.includes('/hero/pack-')?turn.banner:turn.card;
    return at(x,y,place.width/(shown.height*along),degrees);
   }
   return at(x,y,Math.min(place.width/shown.width,place.height/shown.height));
  };
  const ready=()=>{
   if(window.location.pathname!==flight.href)return false;
   const film=document.querySelector<HTMLVideoElement>('video.pc-film');
   return film?film.readyState>=2:!!document.querySelector('[data-vtech-story]');
  };
  const run=async()=>{
   const started=performance.now();
   animate(veil,[{opacity:0},{opacity:.82,offset:.4},{opacity:1}],{duration:520,easing:'ease-out'});
   animate(item,[{transform:at(0,0,1)},{transform:forward}],{duration:680,easing:'cubic-bezier(.22,.8,.2,1)'});
   if(window_.current&&cutout.current){
    animate(window_.current,[{opacity:1},{opacity:0}],{duration:300,delay:90,easing:'ease-in'});
    animate(cutout.current,[{opacity:0},{opacity:1}],{duration:280,delay:60,easing:'ease-out'});
   }
   animate(label,[{opacity:0,transform:'translateY(12px)'},{opacity:1,transform:'translateY(0)'}],{duration:360,delay:260,easing:'ease-out'});
   await delay(300);if(cancelled)return;
   onNavigate(flight.href);
   // The product page loads under the overlay; the overlay waits for the first frame of its film.
   while(!cancelled&&!skipped&&performance.now()-started<5200){
    if(performance.now()-started>1050&&ready())break;
    await delay(50);
   }
   if(cancelled)return;
   root.current?.setAttribute('data-phase','landing');
   animate(label,[{opacity:1},{opacity:0}],{duration:260,easing:'ease-in'});
   const landed=skipped?null:landing();
   if(landed){
    // The pack comes down onto its own place in the first frame and, once there, dissolves into the pack that
    // stands in the film. The move and the dissolve are two animations: an offset inside one would count the way
    // covered, not the time, and the pack would fade while still on its way - two packs side by side.
    animate(item,[{transform:forward},{transform:landed}],{duration:700,easing:'cubic-bezier(.45,0,.2,1)'});
    animate(item,[{opacity:1},{opacity:0}],{duration:200,delay:640,easing:'linear'});
    animate(veil,[{opacity:1},{opacity:0}],{duration:600,easing:'ease-in-out'});
    await delay(860);
   }else{
    animate(item,[{transform:forward,opacity:1},{transform:away,opacity:0}],{duration:skipped?220:620,easing:'cubic-bezier(.5,0,.75,.4)'});
    animate(veil,[{opacity:1},{opacity:0}],{duration:skipped?260:760,easing:'ease-in-out'});
    await delay(skipped?270:780);
   }
   finish();
  };
  skip.current=()=>{skipped=true;};
  void run().catch(()=>finish());
  return()=>{
   cancelled=true;timers.forEach(id=>window.clearTimeout(id));animations.forEach(animation=>animation.cancel());
   window.removeEventListener('keydown',onKey);delete document.documentElement.dataset.productEntry;
  };
 // One effect owns one chosen product across the route boundary.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[flight.id]);
 const {rect,photo}=flight;
 const photoStyle:CSSProperties|undefined=photo?{backgroundImage:`url("${photo.src}")`,backgroundSize:`${photo.rect.width}px ${photo.rect.height}px`,backgroundPosition:`${photo.rect.left-rect.left}px ${photo.rect.top-rect.top}px`}:undefined;
 // Alone, the cut-out is exactly the pack it lifts off; over a window of the photograph it is fitted inside it.
 const packStyle:CSSProperties|undefined=flight.pack?{backgroundImage:`url("${flight.pack.src}")`,backgroundSize:photo?'contain':'100% 100%',backgroundPosition:'50% 50%',opacity:photo?0:1}:undefined;
 return <div ref={root} className="pe-entry" data-phase="lifting" role="status" aria-live="polite" aria-label={'נכנסים אל '+flight.name} onClick={()=>skip.current()}>
  <div ref={ground} className="pe-ground"/>
  <div ref={pack} className="pe-pack" style={rect} aria-hidden="true">
   {photoStyle&&<div ref={window_} className="pe-pack-layer" data-kind="photo" style={photoStyle}/>}
   {packStyle&&<div ref={cutout} className="pe-pack-layer" data-kind={flight.feather?'photo':'pack'} style={packStyle}/>}
  </div>
  <div ref={caption} className="pe-caption"><span dir="ltr">MITODERM · THE COLLECTION</span><bdi dir="ltr">{flight.name}</bdi></div>
 </div>;
}
