'use client';

import {useCallback,useEffect,useMemo,useRef,useState} from 'react';

// Generic scroll-scrubbed <video>: the caller sets a target time from scroll,
// one rAF loop eases the decoder towards it. Adapted from VTechStory.tsx.
export type FilmState={phase:'loading'|'ready'|'error';painted:boolean};
const clamp=(n:number,min=0,max=1)=>Math.min(max,Math.max(min,n));

export function useScrollFilm(){
 const video=useRef<HTMLVideoElement|null>(null),target=useRef(0),inside=useRef(false),snap=useRef(true);
 const seekFrame=useRef<number|null>(null),paintFrame=useRef<number|null>(null);
 const [state,setState]=useState<FilmState>({phase:'loading',painted:false});

 const painted=useCallback(()=>{
  const v=video.current;if(!v||paintFrame.current!==null)return;
  // seeked means a decoded frame exists; give it two paints before the video
  // is revealed above its poster images.
  paintFrame.current=requestAnimationFrame(()=>{
   paintFrame.current=requestAnimationFrame(()=>{
    paintFrame.current=null;
    if(video.current===v&&v.readyState>=2&&!v.seeking&&Math.abs(v.currentTime-target.current)<.12)
     setState(s=>s.painted?s:{phase:'ready',painted:true});
   });
  });
 },[]);

 const seek=useCallback((immediate=false)=>{
  snap.current=snap.current||immediate;
  if(seekFrame.current!==null||document.hidden)return;
  const began=performance.now();
  const tick=()=>{
   seekFrame.current=null;
   const v=video.current;
   if(!v||document.hidden||!inside.current||v.readyState<2||!Number.isFinite(v.duration)||v.duration<=0)return;
   const t=clamp(target.current,0,Math.max(0,v.duration-.04));
   const distance=t-v.currentTime;
   if(Math.abs(distance)<.025){snap.current=false;painted();return;}
   if(!v.seeking){
    const next=snap.current||Math.abs(distance)>.9?t:v.currentTime+distance*.55;
    try{v.currentTime=Math.abs(distance)<.06?t:next;snap.current=false;}catch{return;}
   }
   // A slow decoder cannot keep the loop alive: seeked or the next scroll resumes it.
   if(performance.now()-began<900)seekFrame.current=requestAnimationFrame(tick);
  };
  seekFrame.current=requestAnimationFrame(tick);
 },[painted]);

 // time in seconds; inView false parks the decoder while the stage is off screen.
 const setTarget=useCallback((time:number,inView:boolean,immediate=false)=>{
  target.current=Math.max(0,time);inside.current=inView;seek(immediate);
 },[seek]);

 useEffect(()=>{
  const visibility=()=>{
   video.current?.pause();
   if(document.hidden){if(seekFrame.current!==null)cancelAnimationFrame(seekFrame.current);seekFrame.current=null;}
   else seek(true);
  };
  document.addEventListener('visibilitychange',visibility);
  return()=>{
   document.removeEventListener('visibilitychange',visibility);
   if(seekFrame.current!==null)cancelAnimationFrame(seekFrame.current);
   if(paintFrame.current!==null)cancelAnimationFrame(paintFrame.current);
   seekFrame.current=null;paintFrame.current=null;video.current?.pause();
  };
 },[seek]);

 const handlers=useMemo(()=>({
  onLoadStart:()=>{snap.current=true;setState({phase:'loading',painted:false});},
  onLoadedMetadata:()=>seek(true),
  onLoadedData:()=>{setState(s=>({...s,phase:'ready'}));painted();seek(true);},
  onCanPlay:()=>seek(),
  onSeeked:()=>{painted();seek();},
  onError:()=>setState({phase:'error',painted:false})
 }),[painted,seek]);

 return {video,state,setTarget,handlers};
}
