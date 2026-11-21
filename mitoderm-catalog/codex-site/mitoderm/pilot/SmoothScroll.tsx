'use client';

import {useEffect} from 'react';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';

// Smooth wheel scrolling (Lenis) for a mouse or a trackpad, so the scroll films
// advance evenly instead of in wheel steps. Touch screens keep the browser's own
// scrolling. Lenis turns its smoothing off by itself when the visitor asks for
// reduced motion. Page code keeps reading window.scrollY as before.
let lenis:Lenis|null=null;

// An instant jump (chapter buttons): while Lenis is easing it would undo a plain
// window.scrollTo, so the jump goes through it when it is running.
export function jumpTo(top:number){
 if(lenis)lenis.scrollTo(top,{immediate:true,force:true});
 else window.scrollTo({top,behavior:'instant'});
}

export function SmoothScroll(){
 useEffect(()=>{
  if(!window.matchMedia('(hover: hover) and (pointer: fine)').matches)return;
  // Boxes with their own scrolling (the inquiry dialog, the V-TECH evidence
  // panel) keep the wheel for themselves.
  const ownScroll=(node:HTMLElement)=>node.tagName==='DIALOG'||node.classList.contains('vc-story-evidence-approved');
  const instance=new Lenis({autoRaf:true,stopInertiaOnNavigate:true,prevent:ownScroll});
  lenis=instance;
  // In-page links keep the site's own handling (the browser's anchor scroll,
  // the V-TECH chapter jumps); the easing only has to let go before they run.
  const release=(event:MouseEvent)=>{
   const link=event.target instanceof Element?event.target.closest<HTMLAnchorElement>('a[href]'):null;
   if(link&&link.hash&&link.host===window.location.host&&link.pathname===window.location.pathname)
    instance.scrollTo(instance.actualScroll,{immediate:true,force:true});
  };
  window.addEventListener('click',release,true);
  return()=>{window.removeEventListener('click',release,true);lenis=null;instance.destroy();};
 },[]);
 return null;
}
