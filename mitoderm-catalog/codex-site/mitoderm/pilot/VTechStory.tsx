'use client';

import {useCallback,useEffect,useRef,useState,type CSSProperties} from 'react';
import {mediaUrl} from '../media';
import {entryMedia,mobileMedia,getEntryBoxRect,type EntryRect} from './vtech-entry';
import {vtechTimeline} from './vtech-timeline';
import {mapVTechKitProgress} from './vtech-kit-timing';
import {VTechEvidencePanel,VTechOfferPanel} from './VTechDetails';
import {VTechPackFlight} from './VTechPackFlight';
import './vtech-story.css';

type Scene={id:string;label:string;name:string;title:string;body:string;alt:string;kind:'intro'|'bridge'|'clinical'|'evidence'|'offer';weight:number;poster:string;mobilePoster:string};
const scenes:Scene[]=[
 {id:'vtech-hero',label:'המערכת',name:'V-TECH SYSTEM',title:'V-TECH SYSTEM',body:'סרום ומסכת ג׳ל. מערכת אחת לעבודה מקצועית על עור הפנים.',alt:'אריזת V-TECH על שולחן בקליניקה',kind:'intro',weight:1.67,poster:entryMedia.poster,mobilePoster:mobileMedia.poster},
 {id:'vtech-consultation',label:'הבקשה',name:'בקשה אחת · אזור הלחי',title:'מראה הקמטוטים ומרקם העור',body:'מתחילים בבקשת המטופלת ובבחינת עור הלחי. משם מתקרבים לאזור העבודה.',alt:'המחשה: הקוסמטיקאית בוחנת את עור הלחי בעקבות בקשה הנוגעת למראה קמטוטים ולמרקם העור',kind:'bridge',weight:1.33,poster:mediaUrl('/assets/world/vtech-consultation.webp'),mobilePoster:mediaUrl('/assets/world/vtech-consultation-mobile.webp')},
 {id:'vtech-pen',label:'MITOPEN',name:'MITOPEN',title:'מתמקדים באזור שנבחר',body:'הקוסמטיקאית עובדת באזור הלחי. מיקרונידלינג דורש הכשרה ופרוטוקול מקצועי.',alt:'המחשת עבודה מקצועית עם MITOPEN באזור הלחי של אותה מטופלת',kind:'clinical',weight:1.25,poster:mediaUrl('/assets/world/vtech-pen-poster.webp'),mobilePoster:mediaUrl('/assets/world/vtech-pen-mobile-poster.webp')},
 {id:'vtech-serum',label:'סרום',name:'V-TECH SERUM',title:'אותו אזור. הסרום של המערכת.',body:'מבט קרוב על הסרום באזור הלחי, כחלק מתוכנית העבודה שנבחרה.',alt:'המחשת יישום סרום V-TECH באזור הלחי שנבחר בתחילת הסיפור',kind:'clinical',weight:1.25,poster:mediaUrl('/assets/world/vtech-serum-poster.webp'),mobilePoster:mediaUrl('/assets/world/vtech-serum-mobile-poster.webp')},
 {id:'vtech-mask',label:'מסכת ג׳ל',name:'V-TECH GEL MASK',title:'משלימים עם מסכת הג׳ל',body:'מסכת הג׳ל של V-TECH נמרחת על אותו אזור לאחר העבודה עם הסרום.',alt:'המחשת מריחת V-TECH GEL MASK על אותו אזור בלחי לאחר הסרום',kind:'clinical',weight:1.25,poster:mediaUrl('/assets/world/vtech-mask-poster.webp'),mobilePoster:mediaUrl('/assets/world/vtech-mask-mobile-poster.webp')},
 {id:'vtech-results',label:'המבט המקצועי',name:'V-TECH',title:'המבט המקצועי',body:'',alt:'המחשת הטיפול ב-V-TECH לצד מידע על תיעוד ותוכנית עבודה; התמונה אינה תיעוד של תוצאה',kind:'evidence',weight:1.45,poster:mediaUrl('/assets/world/vtech-mask-poster.webp'),mobilePoster:mediaUrl('/assets/world/vtech-mask-mobile-poster.webp')},
 {id:'vtech-kit',label:'הערכה',name:'V-TECH SYSTEM',title:'הערכה המקצועית',body:'',alt:'אריזת V-TECH SYSTEM נפתחת ומציגה את הסרום ומסכת הג׳ל',kind:'offer',weight:2.15,poster:entryMedia.poster,mobilePoster:mobileMedia.poster},
];
const procedureCount=5;
const starts=scenes.map((_,index)=>scenes.slice(0,index).reduce((sum,scene)=>sum+scene.weight,0));
const total=scenes.reduce((sum,scene)=>sum+scene.weight,0);
const clamp=(value:number,min=0,max=1)=>Math.min(max,Math.max(min,value));
const chapterIndex=(id:string)=>id==='vtech-intro'?0:scenes.findIndex(scene=>scene.id===id);
const sectionId=(index:number)=>index<procedureCount?'vtech-intro':scenes[index].id;
type MediaState={phase:'loading'|'ready'|'error';painted:boolean};

export function VTechStory(){
 const root=useRef<HTMLElement>(null),stage=useRef<HTMLDivElement>(null);
 const cameraVideo=useRef<HTMLVideoElement|null>(null),targetTime=useRef(0);
 const activeRef=useRef(0),inside=useRef(false),snapSeek=useRef(true);
 const seekFrame=useRef<number|null>(null),paintFrame=useRef<number|null>(null);
 const arrivalUnits=useRef<number|null>(null);
 const [arrivalLength,setArrivalLength]=useState(0);
 const environment=useRef({mobile:false,reduced:false,ready:false});
 const [settings,setSettings]=useState({mobile:false,reduced:false,ready:false});
 const [active,setActive]=useState(0),[outgoing,setOutgoing]=useState<number|null>(null);
 const [mediaState,setMediaState]=useState<MediaState>({phase:'loading',painted:false});
 const [entryRect,setEntryRect]=useState<EntryRect>({left:0,top:0,width:0,height:0});
 const fadingTimer=useRef<number|null>(null),focusAfterJump=useRef<number|null>(null),restoreChapter=useRef<number|null>(null);
 const updatePosition=useRef<()=>void>(()=>{});

 const announceSection=useCallback((index:number)=>{
  window.dispatchEvent(new CustomEvent('mitoderm:vtech-section',{detail:sectionId(index)}));
 },[]);

 const paintedCamera=useCallback(()=>{
  const video=cameraVideo.current;if(!video)return;
  if(paintFrame.current!==null)return;
  // seeked means a decoded frame is available. Give it two paints before
  // revealing the sole video above its poster, including on a deep-link load.
  paintFrame.current=window.requestAnimationFrame(()=>{
   paintFrame.current=window.requestAnimationFrame(()=>{
    paintFrame.current=null;
    const chapter=vtechTimeline[environment.current.mobile?'mobile':'desktop'].chapters.find(item=>item.id===scenes[activeRef.current].id);
    const currentChapter=chapter&&video.currentTime>=chapter.start-.08&&video.currentTime<=chapter.end+.08;
    if(cameraVideo.current===video&&video.readyState>=2&&!video.seeking&&(Math.abs(video.currentTime-targetTime.current)<.12||currentChapter)){
     setMediaState(current=>current.painted?current:{phase:'ready',painted:true});
    }
   });
  });
 },[]);

 const seekScrollVideo=useCallback((immediate=false)=>{
  snapSeek.current=snapSeek.current||immediate;
  if(seekFrame.current!==null||environment.current.reduced||document.hidden)return;
  const began=performance.now();
  const tick=()=>{
   seekFrame.current=null;
   const video=cameraVideo.current;
   if(!video||environment.current.reduced||document.hidden||!inside.current||video.readyState<2||!Number.isFinite(video.duration)||video.duration<=0)return;
   // One source and one decoder span every chapter. Native scroll moves only
   // this timeline; caption changes never replace or play another video.
   const target=clamp(targetTime.current,0,Math.max(0,video.duration-.04));
   const distance=target-video.currentTime;
   if(Math.abs(distance)<.025){snapSeek.current=false;paintedCamera();return;}
   if(!video.seeking){
    const next=snapSeek.current||Math.abs(distance)>.9?target:video.currentTime+distance*.55;
    try{video.currentTime=Math.abs(distance)<.06?target:next;snapSeek.current=false;}catch{return;}
   }
   // Large jumps settle immediately; a slow decoder cannot leave an endless
   // animation loop running. seeked/loadeddata or new scroll resumes a target.
   if(performance.now()-began<900)seekFrame.current=window.requestAnimationFrame(tick);
  };
  seekFrame.current=window.requestAnimationFrame(tick);
 },[paintedCamera]);

 useEffect(()=>{
  const element=root.current,screen=stage.current;if(!element||!screen)return;
  const preference=window.matchMedia('(prefers-reduced-motion: reduce)');
  let frame=0,height=window.innerHeight,rootTop=0,disposed=false;
  const measure=()=>{
   // The arrival offset survives removal of the transition marker, so the
   // selected product can finish its flight before the film starts to move.
   if(arrivalUnits.current===null){
    arrivalUnits.current=document.documentElement.dataset.productTransit==='v-tech-system'?.9:0;
    setArrivalLength(arrivalUnits.current);
   }
   const next={mobile:window.innerWidth<=860,reduced:preference.matches,ready:true};
   environment.current=next;
   setSettings(current=>current.mobile===next.mobile&&current.reduced===next.reduced&&current.ready?current:next);
   if(!next.reduced){
    height=Math.max(element.dataset.mode==='linear'?window.innerHeight:screen.clientHeight,1);
    element.style.setProperty('--vts-viewport',height+'px');
    const rect=getEntryBoxRect(screen.clientWidth,height);
    setEntryRect(current=>Object.keys(rect).every(key=>current[key as keyof EntryRect]===rect[key as keyof EntryRect])?current:rect);
   }
   rootTop=element.getBoundingClientRect().top+window.scrollY;
   element.dataset.entryUnits=String(arrivalUnits.current);
   element.dataset.entryStart=String(rootTop);
  };
  const read=()=>{
   frame=0;if(disposed||environment.current.reduced)return;
   const position=window.scrollY-rootTop;
   const units=clamp(position/height-(arrivalUnits.current??0),0,total);
   let next=scenes.length-1;
   for(let index=0;index<scenes.length;index++)if(units<starts[index]+scenes[index].weight){next=index;break;}
   const local=clamp((units-starts[next])/scenes[next].weight);
   const timeline=vtechTimeline[environment.current.mobile?'mobile':'desktop'];
   const chapter=timeline.chapters.find(item=>item.id===scenes[next].id);
   const kit=scenes[next].kind==='offer';
   // The same closed pack moves, begins opening on arrival, and settles into
   // the offer. Overlapping phases remove the previous static middle pose.
   const kitMotion=mapVTechKitProgress(kit?local:0);
   const videoLocal=kit?kitMotion.video:local;
   const mapped=chapter?chapter.start+(chapter.end-chapter.start)*videoLocal:0;
   targetTime.current=clamp(mapped,0,Math.max(0,timeline.duration-.04));
   const wasInside=inside.current;
   inside.current=position>=-1&&position<=(total+(arrivalUnits.current??0)+1.8)*height;
   element.dataset.storyProgress=(units/total).toFixed(4);
   element.dataset.chapterProgress=local.toFixed(4);
   screen.dataset.storyProgress=(units/total).toFixed(4);
   screen.dataset.chapterProgress=local.toFixed(4);
   screen.style.setProperty('--vts-progress',String(units/total));
   screen.style.setProperty('--vts-kit-progress',String(kit?local:0));
   screen.style.setProperty('--vts-pack-progress',String(kitMotion.pack));
   screen.style.setProperty('--vts-kit-reveal',String(kitMotion.reveal));
   screen.style.setProperty('--vts-kit-open',String(kitMotion.opening));
   screen.dataset.kitLoad=String(units>=starts[5]-.25);
   screen.dataset.kitFrame=String(Math.round(kitMotion.opening*39));
   // Browser scroll positions round to a pixel; the fully eased pose can be
   // visually complete a fraction of a pixel before the mathematical endpoint.
   screen.dataset.kitOpened=String(kit&&kitMotion.opening>=.99999);
   screen.dataset.kitOpening=String(kit&&kitMotion.openingRaw>.005);
   screen.dataset.introMoved=String(units>.001);
   document.documentElement.dataset.vtechImmersed=String(inside.current&&units>.12);
   if(next!==activeRef.current){
    const previous=activeRef.current;activeRef.current=next;
    setOutgoing(previous);setActive(next);
    if(fadingTimer.current!==null)window.clearTimeout(fadingTimer.current);
    fadingTimer.current=window.setTimeout(()=>{setOutgoing(null);fadingTimer.current=null;},380);
    if(inside.current)announceSection(next);
   }else if(inside.current&&!wasInside){
    // Returning from Training to the same last chapter must reselect the kit
    // in the global navigation even though its numeric index did not change.
    announceSection(next);
   }
   seekScrollVideo();
  };
  const schedule=()=>{if(!frame)frame=window.requestAnimationFrame(read);};
  const resized=()=>{
   const previousHeight=height,previousPosition=(window.scrollY-rootTop)/Math.max(height,1);
   const preserveChapter=inside.current&&!environment.current.reduced&&restoreChapter.current===null;
   measure();
   if(preserveChapter&&!environment.current.reduced&&Math.abs(height-previousHeight)>.5){
    // A taller viewport changes distances, not the chosen moment in the story.
    // Preserve the fractional interval, including arrival and the final hold.
    window.scrollTo({top:Math.max(0,rootTop+previousPosition*height),behavior:'instant'});
    snapSeek.current=true;
   }
   schedule();
  };
  const motionChanged=()=>{
   restoreChapter.current=activeRef.current;
   measure();cameraVideo.current?.pause();
   if(environment.current.reduced){
    delete document.documentElement.dataset.vtechImmersed;
    if(seekFrame.current!==null)window.cancelAnimationFrame(seekFrame.current);
    seekFrame.current=null;screen.style.setProperty('--vts-pack-progress','0');
   }else snapSeek.current=true;
   schedule();
  };
  const visibility=()=>{
   cameraVideo.current?.pause();
   if(document.hidden){if(seekFrame.current!==null)window.cancelAnimationFrame(seekFrame.current);seekFrame.current=null;}
   else{read();seekScrollVideo(true);}
  };
  updatePosition.current=()=>{measure();read();};
  const observer=new ResizeObserver(resized);observer.observe(screen);
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',resized,{passive:true});
  window.addEventListener('orientationchange',resized);
  document.addEventListener('visibilitychange',visibility);
  preference.addEventListener('change',motionChanged);
  measure();read();
  return()=>{
   disposed=true;observer.disconnect();window.cancelAnimationFrame(frame);
   if(seekFrame.current!==null)window.cancelAnimationFrame(seekFrame.current);
   if(paintFrame.current!==null)window.cancelAnimationFrame(paintFrame.current);
   seekFrame.current=null;paintFrame.current=null;delete document.documentElement.dataset.vtechImmersed;
   if(fadingTimer.current!==null)window.clearTimeout(fadingTimer.current);
   window.removeEventListener('scroll',schedule);window.removeEventListener('resize',resized);window.removeEventListener('orientationchange',resized);
   document.removeEventListener('visibilitychange',visibility);preference.removeEventListener('change',motionChanged);
   cameraVideo.current?.pause();updatePosition.current=()=>{};
  };
 },[announceSection,seekScrollVideo]);

 useEffect(()=>{
  cameraVideo.current?.pause();
  if(!settings.reduced&&restoreChapter.current===null){updatePosition.current();seekScrollVideo(true);}
  if(focusAfterJump.current===active){
   document.getElementById(scenes[active].id+'-title')?.focus({preventScroll:true});
   focusAfterJump.current=null;
  }
 },[active,settings,seekScrollVideo]);

 const jumpTo=useCallback((index:number,moveFocus=false,hashId=scenes[index].id,local=0)=>{
  const element=root.current,screen=stage.current;if(!element||!screen)return;
  window.history.replaceState(window.history.state,'','#'+hashId);
  if(environment.current.reduced){
   activeRef.current=index;setActive(index);announceSection(index);
   document.getElementById(scenes[index].id)?.scrollIntoView({behavior:'instant',block:'start'});
   if(moveFocus)document.getElementById(scenes[index].id+'-title')?.focus({preventScroll:true});
   return;
  }
  if(moveFocus){if(activeRef.current===index)document.getElementById(scenes[index].id+'-title')?.focus({preventScroll:true});else focusAfterJump.current=index;}
  snapSeek.current=true;
  const top=element.getBoundingClientRect().top+window.scrollY+(starts[index]+clamp(local)*scenes[index].weight+(arrivalUnits.current??0))*screen.clientHeight+(index===0?0:1);
  // Chapter links jump to the corresponding pinned interval. Wheel and touch
  // keep native scrolling, and never wait for a long animation to catch up.
  window.scrollTo({top:Math.max(0,top),behavior:'instant'});
  updatePosition.current();announceSection(index);seekScrollVideo(true);
 },[announceSection,seekScrollVideo]);

 useEffect(()=>{
  if(restoreChapter.current===null)return;
  const index=restoreChapter.current;restoreChapter.current=null;
  jumpTo(index);
 },[settings.reduced,jumpTo]);

 useEffect(()=>{
  if(!settings.ready)return;
  const navigate=(id:string,focus=false)=>{const index=chapterIndex(id);if(index<0)return false;jumpTo(index,focus,id);return true;};
  const fromHash=()=>navigate(window.location.hash.slice(1));
  const fromNavigation=(event:Event)=>navigate((event as CustomEvent<string>).detail.replace(/^#/,''),true);
  const fromLink=(event:MouseEvent)=>{
   if(event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||!(event.target instanceof Element))return;
   const link=event.target.closest<HTMLAnchorElement>('a[href]');
   if(!link||link.hasAttribute('download')||(link.target&&link.target!=='_self'))return;
   const url=new URL(link.href,window.location.href);
   if(url.origin!==window.location.origin||url.pathname!==window.location.pathname||url.search!==window.location.search)return;
   const id=url.hash.slice(1);if(chapterIndex(id)<0)return;
   event.preventDefault();navigate(id,true);
  };
  fromHash();
  window.addEventListener('hashchange',fromHash);
  window.addEventListener('mitoderm:vtech-chapter',fromNavigation);
  document.addEventListener('click',fromLink,true);
  return()=>{window.removeEventListener('hashchange',fromHash);window.removeEventListener('mitoderm:vtech-chapter',fromNavigation);document.removeEventListener('click',fromLink,true);};
 },[settings.ready,jumpTo]);

 useEffect(()=>{
  if(!settings.ready||!settings.reduced)return;
  let wasInside=false;
  const update=()=>{
   const element=root.current;if(!element)return;
   const anchor=Math.min(window.innerHeight*.35,220),bounds=element.getBoundingClientRect();
   const isInside=bounds.top<=anchor&&bounds.bottom>anchor;
   let selected=0;
   scenes.forEach((scene,index)=>{const section=document.getElementById(scene.id);if(section&&section.getBoundingClientRect().top<=anchor)selected=index;});
   if(activeRef.current!==selected){activeRef.current=selected;setActive(selected);if(isInside)announceSection(selected);}
   else if(isInside&&!wasInside)announceSection(selected);
   wasInside=isInside;
  };
  let frame=0;
  const schedule=()=>{if(!frame)frame=window.requestAnimationFrame(()=>{frame=0;update();});};
  window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',schedule,{passive:true});update();
  return()=>{window.removeEventListener('scroll',schedule);window.removeEventListener('resize',schedule);window.cancelAnimationFrame(frame);};
 },[settings.ready,settings.reduced,announceSection]);

 const cameraClip=mediaUrl(settings.mobile?'/assets/world/vtech-full-story-mobile.mp4':'/assets/world/vtech-full-story.mp4');
 const posterScene=scenes[active];

 return <section id="vtech-intro" className="vts-story" ref={root} data-vtech-story="true" data-mode={settings.reduced?'linear':'cinema'} data-active-chapter={scenes[active].id} data-active-index={active} style={{'--vts-length':total+2+arrivalLength} as CSSProperties} aria-label="הכירו את מערכת V-TECH">
  <div className="vts-stage" ref={stage} data-vtech-stage="true" data-active-chapter={scenes[active].id} data-active-index={active} data-intro-moved="false">
   <div className="vts-toolbar" data-vtech-hud="true" data-hidden={!settings.reduced&&active>=procedureCount} aria-hidden={!settings.reduced&&active>=procedureCount} inert={!settings.reduced&&active>=procedureCount}>
    <nav className="vts-chapter-nav" aria-label="שלבי ההמחשה של V-TECH">{scenes.slice(0,procedureCount).map((scene,index)=><button type="button" key={scene.id} onClick={()=>jumpTo(index,true)} aria-current={active===index?'step':undefined} aria-label={(index+1)+'. '+scene.label}><span className="vts-nav-number" aria-hidden="true">{String(index+1).padStart(2,'0')}</span><span className="vts-nav-label">{scene.label}</span></button>)}</nav>
   </div>
   {!settings.reduced&&<div className="vts-camera-media vts-media" data-active="true">
    <div className="vts-footage">
     <picture><source media="(max-width: 860px)" srcSet={posterScene.mobilePoster}/><img className="vts-poster" data-vtech-entry-poster={active===0?'true':undefined} src={posterScene.poster} alt={posterScene.alt} width={entryMedia.width} height={entryMedia.height} loading="eager" fetchPriority="high" decoding="async"/></picture>
     {settings.ready&&<video ref={cameraVideo} className={'vts-video'+(mediaState.painted?' is-painted':'')} src={cameraClip} muted playsInline preload="auto" aria-hidden="true" tabIndex={-1}
      onLoadStart={()=>{snapSeek.current=true;setMediaState({painted:false,phase:'loading'});}}
      onLoadedMetadata={()=>seekScrollVideo(true)}
      onLoadedData={()=>{setMediaState(current=>({...current,phase:'ready'}));paintedCamera();seekScrollVideo(true);}}
      onCanPlay={()=>seekScrollVideo()}
      onSeeked={()=>{paintedCamera();seekScrollVideo();}}
      onError={()=>setMediaState({painted:false,phase:'error'})}/>
     }
    </div>
   </div>}
   <VTechPackFlight stage={stage} reduced={settings.reduced}/>
   <div className="vts-scenes">
    {scenes.map((scene,index)=>{
     const isActive=index===active,Heading=index===0?'h1':'h2';
     return <article key={scene.id} id={scene.id} className="vts-scene" data-kind={scene.kind} data-scene-start={starts[index]} data-scene-weight={scene.weight} data-active={isActive} data-outgoing={index===outgoing} aria-hidden={settings.reduced?undefined:!isActive} inert={!settings.reduced&&!isActive} aria-labelledby={scene.id+'-title'}>
      {settings.reduced&&<div className="vts-media"><div className="vts-footage">
       {scene.kind!=='offer'&&<picture><source media="(max-width: 860px)" srcSet={scene.mobilePoster}/><img data-vtech-entry-poster={index===0?'true':undefined} className="vts-poster" src={scene.poster} alt={scene.alt} width={index===0?entryMedia.width:1920} height="1080" loading={index===0?'eager':'lazy'} decoding="async"/></picture>}
      </div></div>}
      {index===0&&<span className="vts-entry-target" data-flight-target="v-tech-system" aria-hidden="true" style={entryRect}/>}
      {scene.kind==='evidence'?<VTechEvidencePanel/>:scene.kind==='offer'?<VTechOfferPanel staticProduct={settings.reduced} onReveal={()=>jumpTo(index,false,scene.id,.94)}/>:<div className="vts-caption" data-vtech-hud="true">
       {index>0&&<p className="vts-kicker" dir={index===1?'rtl':'ltr'}>{scene.name}</p>}
       <Heading id={scene.id+'-title'} tabIndex={-1} dir={index===0?'ltr':undefined}>{scene.title}</Heading>
       <p className="vts-body">{scene.body}</p>
       {index===0?<div className="vts-hero-actions"><a className="vts-main-inquiry" href="#contact" data-product="v-tech-system" data-source="vtech-hero">לקבלת מחיר <span aria-hidden="true">←</span></a><button type="button" onClick={()=>jumpTo(1,true)}>אל הקליניקה <span aria-hidden="true">↓</span></button></div>:index===1?<div className="vts-clinical-actions"><a href="#contact" data-product="v-tech-system" data-source="vtech-consultation" data-topic="protocol">לשיחה על התאמה <span aria-hidden="true">←</span></a></div>:index===4?<div className="vts-clinical-actions"><a href="#vtech-results">לתיעוד וציפיות מהטיפול <span aria-hidden="true">↓</span></a></div>:null}
      </div>}
     </article>;
    })}
   </div>
   <div className="vts-bottom" data-vtech-hud="true"><span className="vts-counter" aria-live="polite" aria-atomic="true"><bdi dir="ltr">{String(active+1).padStart(2,'0')} / {String(scenes.length).padStart(2,'0')}</bdi><span>{scenes[active].label}</span></span><span className="vts-disclosure" role={mediaState.phase==='error'?'status':undefined}>{mediaState.phase==='error'?'סרטון לא נטען · המחשת AI בתמונה':'המחשה שנוצרה באמצעות AI'}</span><span className="vts-scroll-cue">גללו כדי להתקדם <span aria-hidden="true">↓</span></span></div>
   <div className="vts-progress" aria-hidden="true"><span/></div>
  </div>
 </section>;
}
