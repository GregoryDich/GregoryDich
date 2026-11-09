'use client';

import {useCallback,useEffect,useRef,useState,type CSSProperties} from 'react';
import {mediaUrl} from '../media';
import {entryMedia,mobileMedia,getEntryBoxRect,type EntryRect} from './vtech-entry';
import './vtech-story.css';

type Scene={id:string;label:string;name:string;title:string;body:string;alt:string;kind:'intro'|'bridge'|'clinical';weight:number;poster:string;mobilePoster:string;clip?:string;mobileClip?:string};
const scenes:Scene[]=[
 {id:'vtech-hero',label:'המערכת',name:'V-TECH SYSTEM',title:'V-TECH SYSTEM',body:'סרום ומסכת ג׳ל. מערכת אחת לעבודה מקצועית על עור הפנים.',alt:'אריזת V-TECH על שולחן בקליניקה',kind:'intro',weight:1.67,poster:entryMedia.poster,mobilePoster:mobileMedia.poster},
 {id:'vtech-consultation',label:'הבקשה',name:'בקשה אחת · אזור הלחי',title:'מראה הקמטוטים ומרקם העור',body:'מתחילים בבקשת המטופלת ובבחינת עור הלחי. משם מתקרבים לאזור העבודה.',alt:'המחשה: הקוסמטיקאית בוחנת את עור הלחי בעקבות בקשה הנוגעת למראה קמטוטים ולמרקם העור',kind:'bridge',weight:1.33,poster:mediaUrl('/assets/world/vtech-consultation.webp'),mobilePoster:mediaUrl('/assets/world/vtech-consultation-mobile.webp')},
 {id:'vtech-pen',label:'MITOPEN',name:'MITOPEN',title:'מתמקדים באזור שנבחר',body:'הקוסמטיקאית עובדת באזור הלחי. מיקרונידלינג דורש הכשרה ופרוטוקול מקצועי.',alt:'המחשת עבודה מקצועית עם MITOPEN באזור הלחי של אותה מטופלת',kind:'clinical',weight:1.25,poster:mediaUrl('/assets/world/vtech-pen-poster.webp'),mobilePoster:mediaUrl('/assets/world/vtech-pen-mobile-poster.webp'),clip:mediaUrl('/assets/world/vtech-pen.mp4'),mobileClip:mediaUrl('/assets/world/vtech-pen-mobile.mp4')},
 {id:'vtech-serum',label:'סרום',name:'V-TECH SERUM',title:'אותו אזור. הסרום של המערכת.',body:'מבט קרוב על הסרום באזור הלחי, כחלק מתוכנית העבודה שנבחרה.',alt:'המחשת יישום סרום V-TECH באזור הלחי שנבחר בתחילת הסיפור',kind:'clinical',weight:1.25,poster:mediaUrl('/assets/world/vtech-serum-poster.webp'),mobilePoster:mediaUrl('/assets/world/vtech-serum-mobile-poster.webp'),clip:mediaUrl('/assets/world/vtech-serum.mp4'),mobileClip:mediaUrl('/assets/world/vtech-serum-mobile.mp4')},
 {id:'vtech-mask',label:'מסכת ג׳ל',name:'V-TECH GEL MASK',title:'משלימים עם מסכת הג׳ל',body:'מסכת הג׳ל של V-TECH נמרחת על אותו אזור לאחר העבודה עם הסרום.',alt:'המחשת מריחת V-TECH GEL MASK על אותו אזור בלחי לאחר הסרום',kind:'clinical',weight:1.25,poster:mediaUrl('/assets/world/vtech-mask-poster.webp'),mobilePoster:mediaUrl('/assets/world/vtech-mask-mobile-poster.webp'),clip:mediaUrl('/assets/world/vtech-mask.mp4'),mobileClip:mediaUrl('/assets/world/vtech-mask-mobile.mp4')},
];
const starts=scenes.map((_,index)=>scenes.slice(0,index).reduce((sum,scene)=>sum+scene.weight,0));
const total=scenes.reduce((sum,scene)=>sum+scene.weight,0);
const clamp=(value:number,min=0,max=1)=>Math.min(max,Math.max(min,value));
type Phase='loading'|'ready'|'playing'|'paused'|'ended'|'blocked'|'error';
type ClipState={phase:Phase;painted:boolean};
type Playback={time:number;ended:boolean;userPaused:boolean;trying:boolean};
const initialClips=():ClipState[]=>scenes.map(()=>({phase:'loading',painted:false}));

export function VTechStory(){
 const root=useRef<HTMLElement>(null),stage=useRef<HTMLDivElement>(null);
 const cameraVideo=useRef<HTMLVideoElement|null>(null),cameraProgress=useRef(0);
 const videos=useRef<Array<HTMLVideoElement|null>>(scenes.map(()=>null));
 const playback=useRef<Playback[]>(scenes.map(()=>({time:0,ended:false,userPaused:false,trying:false})));
 const activeRef=useRef(0),introProgress=useRef(0),inside=useRef(true);
 const seekFrame=useRef<number|null>(null);
 const arrivalUnits=useRef<number|null>(null);
 const [arrivalLength,setArrivalLength]=useState(0);
 const environment=useRef({mobile:false,reduced:false,ready:false});
 const [settings,setSettings]=useState({mobile:false,reduced:false,ready:false});
 const [active,setActive]=useState(0),[outgoing,setOutgoing]=useState<number|null>(null);
 const [clips,setClips]=useState<ClipState[]>(initialClips);
 const [entryRect,setEntryRect]=useState<EntryRect>({left:0,top:0,width:0,height:0});
 const fadingTimer=useRef<number|null>(null),focusAfterJump=useRef<number|null>(null);
 const updatePosition=useRef<()=>void>(()=>{});

 const updateClip=useCallback((index:number,patch:Partial<ClipState>)=>{
  setClips(previous=>{
   const current=previous[index];
   if(Object.entries(patch).every(([key,value])=>current[key as keyof ClipState]===value))return previous;
   return previous.map((item,i)=>i===index?{...item,...patch}:item);
  });
 },[]);

 const updateCamera=useCallback((patch:Partial<ClipState>)=>{
  updateClip(0,patch);updateClip(1,patch);
 },[updateClip]);

 const seekScrollVideo=useCallback(()=>{
  if(seekFrame.current!==null||environment.current.reduced||document.hidden)return;
  const began=performance.now();
  const tick=()=>{
   seekFrame.current=null;
   const index=activeRef.current,video=cameraVideo.current;
   if(!video||scenes[index].kind==='clinical'||environment.current.reduced||document.hidden||!inside.current||video.readyState<2||!Number.isFinite(video.duration)||video.duration<=0)return;
   // Only the camera moves follow scroll in both directions. Medical actions
   // stay forward-only and retain their own pause/replay control.
   // One encoded camera move and one persistent decoder span both chapters.
   // Changing the HTML caption never swaps, scales or restarts the picture.
   const target=clamp(cameraProgress.current)*Math.max(0,video.duration-.04);
   const distance=target-video.currentTime;
   if(Math.abs(distance)<.025)return;
   // Settle small wheel/touch increments gently. Direct chapter navigation or
   // a large scroll seeks immediately, without forcing a long catch-up movie.
   if(!video.seeking){
    const next=Math.abs(distance)>1.1?target:video.currentTime+distance*.55;
    try{video.currentTime=Math.abs(distance)<.06?target:next;}catch{return;}
   }
   // A stalled decoder must not keep a permanent animation loop running.
   // loadeddata/seeked, or the next scroll, will resume a pending target.
   if(performance.now()-began<900)seekFrame.current=window.requestAnimationFrame(tick);
  };
  seekFrame.current=window.requestAnimationFrame(tick);
 },[]);

 const playForward=useCallback((index:number)=>{
  const video=videos.current[index],memory=playback.current[index];
  if(!video||scenes[index].kind!=='clinical'||activeRef.current!==index||!inside.current||environment.current.reduced||document.hidden||memory.ended||memory.userPaused||memory.trying||!video.paused)return;
  memory.trying=true;
  void video.play().catch(()=>{
   if(videos.current[index]===video&&activeRef.current===index)updateClip(index,{phase:'blocked'});
  }).finally(()=>{memory.trying=false;});
 },[updateClip]);

 const reconcileVideos=useCallback(()=>{
  cameraVideo.current?.pause();
  videos.current.forEach((video,index)=>{
   if(!video)return;
   if(scenes[index].kind!=='clinical'||index!==activeRef.current||!inside.current||environment.current.reduced||document.hidden)video.pause();
   else playForward(index);
  });
  seekScrollVideo();
 },[playForward,seekScrollVideo]);

 useEffect(()=>{
  const element=root.current,screen=stage.current;if(!element||!screen)return;
  const videoElements=videos.current;
  const preference=window.matchMedia('(prefers-reduced-motion: reduce)');
  let frame=0,height=window.innerHeight,rootTop=0,disposed=false;
  const measure=()=>{
   // Keep this entry offset for the whole mount, including after the shared
   // product overlay removes its transit marker and after viewport changes.
   if(arrivalUnits.current===null){
    arrivalUnits.current=document.documentElement.dataset.productTransit==='v-tech-system'?.9:0;
    setArrivalLength(arrivalUnits.current);
   }
   const next={mobile:window.innerWidth<=860,reduced:preference.matches,ready:true};
   environment.current=next;
   setSettings(current=>current.mobile===next.mobile&&current.reduced===next.reduced&&current.ready?current:next);
   if(!next.reduced){
    height=Math.max(screen.clientHeight,1);
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
   introProgress.current=clamp(units/scenes[0].weight);
   cameraProgress.current=clamp(units/starts[2]);
   const wasInside=inside.current;
   inside.current=position>=-1&&position<=(total+(arrivalUnits.current??0)+.8)*height;
   element.dataset.storyProgress=(units/total).toFixed(4);
   element.dataset.chapterProgress=local.toFixed(4);
   screen.dataset.storyProgress=(units/total).toFixed(4);
   screen.style.setProperty('--vts-progress',String(units/total));
   screen.dataset.introMoved=String(introProgress.current>.001);
   document.documentElement.dataset.vtechImmersed=String(inside.current&&units>.12);
   if(next!==activeRef.current){
    const previous=activeRef.current;activeRef.current=next;
    if(previous<2&&next>=2){
     const camera=cameraVideo.current;
     if(camera&&Number.isFinite(camera.duration))try{camera.currentTime=Math.max(0,camera.duration-.04);}catch{/* Keep the last decoded camera frame during the blend. */}
    }
    setOutgoing(previous);setActive(next);
    if(fadingTimer.current!==null)window.clearTimeout(fadingTimer.current);
    fadingTimer.current=window.setTimeout(()=>{setOutgoing(null);fadingTimer.current=null;},380);
    reconcileVideos();
   }else if(wasInside!==inside.current)reconcileVideos();
   seekScrollVideo();
  };
  const schedule=()=>{if(!frame)frame=window.requestAnimationFrame(read);};
  const resized=()=>{measure();schedule();};
  const motionChanged=()=>{measure();if(environment.current.reduced)delete document.documentElement.dataset.vtechImmersed;reconcileVideos();schedule();};
  const visibility=()=>reconcileVideos();
  updatePosition.current=()=>{measure();read();};
  const observer=new ResizeObserver(resized);
  observer.observe(screen);
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',resized,{passive:true});
  window.addEventListener('orientationchange',resized);
  document.addEventListener('visibilitychange',visibility);
  preference.addEventListener('change',motionChanged);
  measure();read();
  return()=>{
   disposed=true;observer.disconnect();window.cancelAnimationFrame(frame);
   if(seekFrame.current!==null)window.cancelAnimationFrame(seekFrame.current);
   seekFrame.current=null;delete document.documentElement.dataset.vtechImmersed;
   if(fadingTimer.current!==null)window.clearTimeout(fadingTimer.current);
   window.removeEventListener('scroll',schedule);window.removeEventListener('resize',resized);window.removeEventListener('orientationchange',resized);
   document.removeEventListener('visibilitychange',visibility);preference.removeEventListener('change',motionChanged);
   videoElements.forEach(video=>video?.pause());cameraVideo.current?.pause();updatePosition.current=()=>{};
  };
 },[reconcileVideos,seekScrollVideo]);

 useEffect(()=>{
  reconcileVideos();
  if(focusAfterJump.current===active){
   document.getElementById(scenes[active].id+'-title')?.focus({preventScroll:true});
   focusAfterJump.current=null;
  }
 },[active,settings,reconcileVideos]);

 const jumpTo=useCallback((index:number,moveFocus=false)=>{
  const element=root.current,screen=stage.current;if(!element||!screen)return;
  window.history.replaceState(window.history.state,'','#'+scenes[index].id);
  if(environment.current.reduced){activeRef.current=index;setActive(index);document.getElementById(scenes[index].id)?.scrollIntoView({behavior:'instant',block:'start'});if(moveFocus)document.getElementById(scenes[index].id+'-title')?.focus({preventScroll:true});return;}
  if(moveFocus){if(activeRef.current===index)document.getElementById(scenes[index].id+'-title')?.focus({preventScroll:true});else focusAfterJump.current=index;}
  const top=element.getBoundingClientRect().top+window.scrollY+(starts[index]+(arrivalUnits.current??0))*screen.clientHeight+(index===0?0:1);
  // An explicit chapter choice jumps directly; wheel/touch scrolling stays native.
  window.scrollTo({top:Math.max(0,top),behavior:'instant'});
  updatePosition.current();
 },[]);

 useEffect(()=>{
  if(!settings.ready)return;
  const fromHash=()=>{const index=scenes.findIndex(scene=>'#'+scene.id===window.location.hash);if(index>=0)jumpTo(index);};
  const fromNavigation=(event:Event)=>{const id=(event as CustomEvent<string>).detail;const index=scenes.findIndex(scene=>scene.id===id);if(index>=0)jumpTo(index,true);};
  fromHash();window.addEventListener('hashchange',fromHash);window.addEventListener('mitoderm:vtech-chapter',fromNavigation);
  return()=>{window.removeEventListener('hashchange',fromHash);window.removeEventListener('mitoderm:vtech-chapter',fromNavigation);};
 },[settings.ready,jumpTo]);

 useEffect(()=>{
  if(!settings.ready||!settings.reduced)return;
  const update=()=>{
   const anchor=Math.min(window.innerHeight*.35,220);
   let selected=0;
   scenes.forEach((scene,index)=>{const section=document.getElementById(scene.id);if(section&&section.getBoundingClientRect().top<=anchor)selected=index;});
   if(activeRef.current!==selected){activeRef.current=selected;setActive(selected);}
  };
  let frame=0;
  const schedule=()=>{if(!frame)frame=window.requestAnimationFrame(()=>{frame=0;update();});};
  window.addEventListener('scroll',schedule,{passive:true});update();
  return()=>{window.removeEventListener('scroll',schedule);window.cancelAnimationFrame(frame);};
 },[settings.ready,settings.reduced]);

 function loaded(index:number){
  const video=videos.current[index];if(!video)return;
  const memory=playback.current[index];
  if(scenes[index].kind!=='clinical'){updateClip(index,{phase:'ready'});seekScrollVideo();return;}
  if(Number.isFinite(video.duration)&&memory.time>0){
   const resume=Math.min(memory.time,Math.max(0,video.duration-.035));
   if(Math.abs(video.currentTime-resume)>.025){try{video.currentTime=resume;}catch{/* Keep the poster until the browser is ready. */}}
  }
  updateClip(index,{phase:memory.ended?'ended':memory.userPaused?'paused':'ready'});
  playForward(index);
 }
 function painted(index:number){
  const video=videos.current[index];if(!video)return;
  const show=()=>{if(videos.current[index]===video)updateClip(index,{painted:true});};
  if('requestVideoFrameCallback' in video)video.requestVideoFrameCallback(show);
  // Paused seeks do not consistently schedule a subsequent video frame callback.
  window.requestAnimationFrame(()=>window.requestAnimationFrame(()=>{if(video.readyState>=2&&!video.seeking)show();}));
 }
 function paintedCamera(){
  const video=cameraVideo.current;if(!video)return;
  const show=()=>{
   const target=cameraProgress.current*Math.max(0,video.duration-.04);
   if(cameraVideo.current===video&&Number.isFinite(target)&&Math.abs(video.currentTime-target)<.09)updateCamera({painted:true});
  };
  if('requestVideoFrameCallback' in video)video.requestVideoFrameCallback(show);
  window.requestAnimationFrame(()=>window.requestAnimationFrame(()=>{if(video.readyState>=2&&!video.seeking)show();}));
 }
 function toggle(index:number){
  const video=videos.current[index];if(!video)return;
  const memory=playback.current[index];
  if(!video.paused&&!video.ended){memory.userPaused=true;video.pause();updateClip(index,{phase:'paused'});return;}
  memory.userPaused=false;
  if(memory.ended||video.ended){memory.time=0;memory.ended=false;video.currentTime=0;}
  if(clips[index].phase==='error'){updateClip(index,{painted:false,phase:'loading'});video.load();}
  playForward(index);
 }

 const cameraClip=mediaUrl(settings.mobile?'/assets/world/vtech-camera-mobile.mp4':'/assets/world/vtech-camera.mp4');
 const cameraScene=scenes[active<2?active:1];
 const cameraEligible=active<3||(outgoing!==null&&outgoing<2);

 return <section id="vtech-intro" className="vts-story" ref={root} data-vtech-story="true" data-mode={settings.reduced?'linear':'cinema'} data-active-chapter={scenes[active].id} data-active-index={active} style={{'--vts-length':total+1+arrivalLength} as CSSProperties} aria-label="הכירו את מערכת V-TECH">
  <div className="vts-stage" ref={stage} data-vtech-stage="true" data-active-chapter={scenes[active].id} data-active-index={active} data-intro-moved="false">
   <div className="vts-toolbar" data-vtech-hud="true">
    <nav className="vts-chapter-nav" aria-label="פרקי הסיפור של V-TECH">{scenes.map((scene,index)=><button type="button" key={scene.id} onClick={()=>jumpTo(index)} aria-current={active===index?'step':undefined} aria-label={(index+1)+'. '+scene.label}><span className="vts-nav-number" aria-hidden="true">{String(index+1).padStart(2,'0')}</span><span className="vts-nav-label">{scene.label}</span></button>)}</nav>
   </div>
   {!settings.reduced&&cameraEligible&&<div className="vts-camera-media vts-media" data-active={active<2} data-outgoing={outgoing!==null&&outgoing<2} aria-hidden={active>=2}>
    <div className="vts-footage">
     <picture><source media="(max-width: 860px)" srcSet={cameraScene.mobilePoster}/><img className="vts-poster" data-vtech-entry-poster={active===0?'true':undefined} src={cameraScene.poster} alt={cameraScene.alt} width={entryMedia.width} height={entryMedia.height} loading="eager" fetchPriority="high" decoding="async"/></picture>
     {settings.ready&&<video key={cameraClip} ref={cameraVideo} className={'vts-video'+(clips[0].painted?' is-painted':'')} src={cameraClip} muted playsInline preload="auto" aria-hidden="true" tabIndex={-1}
      onLoadStart={()=>updateCamera({painted:false,phase:'loading'})}
      onLoadedData={()=>{updateCamera({phase:'ready'});if(cameraProgress.current<.001)paintedCamera();seekScrollVideo();}}
      onCanPlay={seekScrollVideo}
      onSeeked={()=>{paintedCamera();seekScrollVideo();}}
      onError={()=>updateCamera({phase:'error',painted:false})}/>
     }
    </div>
   </div>}
   <div className="vts-scenes">
    {scenes.map((scene,index)=>{
     const isActive=index===active;
     const eligible=settings.reduced||isActive||index===active+1||index===outgoing;
     const clip=settings.mobile?(scene.mobileClip??scene.clip):scene.clip;
     const state=clips[index];
     const Heading=index===0?'h1':'h2';
     const replay=state.phase==='ended';
     return <article key={scene.id} id={scene.id} className="vts-scene" data-kind={scene.kind} data-active={isActive} data-outgoing={index===outgoing} data-media-state={state.phase} aria-hidden={settings.reduced?undefined:!isActive} inert={!settings.reduced&&!isActive} aria-labelledby={scene.id+'-title'}>
      {(settings.reduced||index>=2)&&<div className="vts-media">
       <div className="vts-footage">
       <picture>{eligible&&<source media="(max-width: 860px)" srcSet={scene.mobilePoster}/>}<img data-vtech-entry-poster={index===0?'true':undefined} className="vts-poster" src={eligible?scene.poster:undefined} alt={scene.alt} width={index===0?entryMedia.width:1920} height="1080" loading={index===0||(!settings.reduced&&eligible)?'eager':'lazy'} fetchPriority={index===0?'high':'auto'} decoding="async"/></picture>
       {settings.ready&&!settings.reduced&&eligible&&clip&&<video key={clip} ref={node=>{videos.current[index]=node;}} className={'vts-video'+(state.painted?' is-painted':'')} src={clip} muted playsInline preload={isActive?'auto':'metadata'} aria-hidden="true" tabIndex={-1}
        onLoadStart={()=>updateClip(index,{painted:false,phase:playback.current[index].ended?'ended':'loading'})}
        onLoadedMetadata={()=>loaded(index)} onLoadedData={()=>{if(scene.kind!=='clinical'){updateClip(index,{phase:'ready'});seekScrollVideo();}}}
        onCanPlay={()=>{if(scene.kind!=='clinical')seekScrollVideo();else playForward(index);}}
        onSeeked={()=>{painted(index);if(scene.kind!=='clinical')seekScrollVideo();}}
        onPlaying={()=>{painted(index);updateClip(index,{phase:'playing'});}}
        onPause={()=>{if(!playback.current[index].ended&&scene.kind==='clinical')updateClip(index,{phase:'paused'});}}
        onTimeUpdate={event=>{if(scene.kind==='clinical')playback.current[index].time=event.currentTarget.currentTime;}}
        onEnded={()=>{const memory=playback.current[index];memory.ended=true;memory.time=videos.current[index]?.duration??memory.time;updateClip(index,{phase:'ended',painted:true});}}
        onError={()=>updateClip(index,{phase:'error',painted:false})}/>
       }
       </div>
      </div>}
      {index===0&&<span className="vts-entry-target" data-flight-target="v-tech-system" aria-hidden="true" style={entryRect}/>}
      <div className="vts-caption" data-vtech-hud="true">
       {index>0&&<p className="vts-kicker" dir={index===1?'rtl':'ltr'}>{scene.name}</p>}
       <Heading id={scene.id+'-title'} tabIndex={-1} dir={index===0?'ltr':undefined}>{scene.title}</Heading>
       <p className="vts-body">{scene.body}</p>
       {index===0?<div className="vts-hero-actions"><a className="vts-main-inquiry" href="#contact" data-product="v-tech-system" data-source="vtech-hero">לקבלת מחיר <span aria-hidden="true">←</span></a><button type="button" onClick={()=>jumpTo(1,true)}>אל הקליניקה <span aria-hidden="true">↓</span></button></div>:<div className="vts-clinical-actions">
        {scene.kind==='clinical'&&!settings.reduced&&<button className="vts-play" type="button" onClick={()=>toggle(index)} disabled={!settings.ready||!eligible} aria-label={state.phase==='playing'?'עצירת הסרטון':replay?'ניגון הסרטון מחדש':'ניגון הסרטון'}><span aria-hidden="true">{state.phase==='playing'?'Ⅱ':replay?'↻':'▷'}</span>{state.phase==='playing'?'עצירה':replay?'לניגון חוזר':state.phase==='error'?'ניסיון נוסף':'ניגון'}</button>}
        {index===1&&<a href="#contact" data-product="v-tech-system" data-source="vtech-consultation" data-topic="protocol">לשיחה על התאמה <span aria-hidden="true">←</span></a>}
        {index===scenes.length-1&&<a href="#vtech-results">לתיעוד וציפיות מהטיפול <span aria-hidden="true">↓</span></a>}
        {state.phase==='error'&&<span className="vts-fallback" role="status">המחשה בתמונה</span>}
       </div>}
      </div>
     </article>;
    })}
   </div>
   <div className="vts-bottom" data-vtech-hud="true"><span className="vts-counter" aria-live="polite" aria-atomic="true"><bdi dir="ltr">{String(active+1).padStart(2,'0')} / 05</bdi><span>{scenes[active].label}</span></span><span className="vts-disclosure">המחשה שנוצרה באמצעות AI</span><span className="vts-scroll-cue" aria-hidden="true">גללו להמשך ↓</span></div>
   <div className="vts-progress" aria-hidden="true"><span/></div>
  </div>
 </section>;
}
