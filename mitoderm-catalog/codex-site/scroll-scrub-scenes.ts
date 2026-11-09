import {mediaUrl} from './mitoderm/media';
import {createElement} from 'react';
import type {ScrollScrubScene,ScrollScrubTheme} from '@/components/scroll-scrub/scroll-scrub';
export const scrollScrubTheme:ScrollScrubTheme={accent:'#dfba74',background:'#08080a',ink:'#f7f6f2',muted:'#ddd9d0'};
export const scrollScrubScenes:ScrollScrubScene[]=[{
 id:'vtech-hero',label:'V-TECH',title:'V-TECH SYSTEM',
 body:'סרום ומסכת ג׳ל לטיפולי פנים מקצועיים.',
 poster:mediaUrl('/assets/world/vtech-intro-poster.webp'),
 mobilePoster:mediaUrl('/assets/world/vtech-intro-mobile-poster.webp'),
 clip:mediaUrl('/assets/world/vtech-intro.mp4'),
 mobileClip:mediaUrl('/assets/world/vtech-intro-mobile.mp4'),
 scroll:1.7,linger:.12,align:'right',
 objectPosition:'50% 50%',mobileObjectPosition:'50% 50%',
 actions:createElement('div',{className:'vc-hero-actions'},
  createElement('a',{href:'#contact',className:'vc-hero-price','data-product':'v-tech-system','data-source':'vtech-hero'},'לקבלת מחיר',createElement('span',{'aria-hidden':true},'←')),
  createElement('a',{href:'#vtech-consultation',className:'vc-hero-explore'},'אל הקליניקה',createElement('span',{'aria-hidden':true},'↓')))
}];
