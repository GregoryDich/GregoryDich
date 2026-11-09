import {mediaUrl} from '../media';
import {useEffect,useRef,useState} from 'react';

type Media={poster:string;mobilePoster:string;clip?:string;mobileClip?:string};
type Props={media:Media;alt:string;className?:string;id?:string};
export function CinematicStage({media:inputMedia,alt,className='',id}:Props){
 const media:Media={poster:mediaUrl(inputMedia.poster),mobilePoster:mediaUrl(inputMedia.mobilePoster),clip:inputMedia.clip?mediaUrl(inputMedia.clip):undefined,mobileClip:inputMedia.mobileClip?mediaUrl(inputMedia.mobileClip):undefined};
 const stage=useRef<HTMLElement>(null),video=useRef<HTMLVideoElement>(null);
 const near=useRef(false),userPaused=useRef(false);
 const [source,setSource]=useState<string>(),[painted,setPainted]=useState(false);
 const [playing,setPlaying]=useState(false),[reduced,setReduced]=useState(true);
 const [failed,setFailed]=useState(false);
 useEffect(()=>{
  const element=stage.current;if(!element||!media.clip)return;
  const preference=window.matchMedia('(prefers-reduced-motion: reduce)');
  const portrait=window.matchMedia('(max-width: 860px)');
  const motion=()=>{
   setReduced(preference.matches);setPainted(false);setFailed(false);
   if(preference.matches){video.current?.pause();setSource(undefined);setPlaying(false);}
   else if(near.current)setSource(portrait.matches?(media.mobileClip??media.clip):media.clip);
  };
  const observer=new IntersectionObserver(entries=>{
   const entry=entries[0];near.current=entry.isIntersecting&&entry.intersectionRatio>=.35;
   if(!near.current){video.current?.pause();return;}
   if(preference.matches)return;
   setSource(portrait.matches?(media.mobileClip??media.clip):media.clip);
   if(!userPaused.current&&video.current&&!video.current.ended){
    void video.current.play().catch(()=>setPlaying(false));
   }
  },{threshold:.35});
  observer.observe(element);preference.addEventListener('change',motion);portrait.addEventListener('change',motion);motion();
  const visibility=()=>{if(document.hidden)video.current?.pause();};
  document.addEventListener('visibilitychange',visibility);
  return()=>{observer.disconnect();preference.removeEventListener('change',motion);portrait.removeEventListener('change',motion);document.removeEventListener('visibilitychange',visibility);video.current?.pause();};
 },[media.clip,media.mobileClip]);
 function onReady(){if(near.current&&!userPaused.current&&!reduced)void video.current?.play().catch(()=>setPlaying(false));}
 function toggle(){
  const element=video.current;if(!element)return;
  if(element.paused){userPaused.current=false;if(element.ended)element.currentTime=0;void element.play().catch(()=>setPlaying(false));}
  else {userPaused.current=true;element.pause();}
 }
 return <figure className={'vc-media '+className} ref={stage} id={id}>
  <picture><source media="(max-width: 860px)" srcSet={media.mobilePoster}/><img className="vc-media-poster" src={media.poster} width="1920" height="1080" alt={alt} loading="lazy" decoding="async"/></picture>
  {source&&!failed&&<video ref={video} className={'vc-media-video'+(painted?' is-painted':'')} src={source} muted playsInline preload="metadata" aria-label={alt}
   onCanPlay={onReady} onPlaying={()=>{setPainted(true);setPlaying(true);}}
   onPause={()=>setPlaying(false)} onEnded={()=>{setPlaying(false);userPaused.current=true;}}
   onError={()=>{setFailed(true);setPlaying(false);setPainted(false);}}/>}
  {source&&!reduced&&!failed&&<button className="vc-media-control" type="button" onClick={toggle} aria-label={playing?'עצירת הסרטון':'ניגון הסרטון'} aria-pressed={playing}><span aria-hidden="true">{playing?'Ⅱ':'▷'}</span><span>{playing?'עצירה':'ניגון'}</span></button>}
 </figure>;
}
