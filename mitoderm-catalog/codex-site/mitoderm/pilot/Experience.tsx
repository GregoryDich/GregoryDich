'use client';

import {useEffect,useRef,useState,type ReactNode,type CSSProperties} from 'react';
import {usePathname,useRouter} from 'next/navigation';
import {products,assets} from '../data';
import {mediaUrl} from '../media';
import {LeadForm} from './LeadForm';
import './product-flight.css';

type Inquiry={productSlug:string;sourceBlock:string;comment:string};
type Flight={slug:string;src:string;x:number;y:number;width:number;height:number;moveX:number;moveY:number;scale:number};

export function SiteExperience({children}:{children:ReactNode}){
 const pathname=usePathname();
 const router=useRouter();
 const [inquiry,setInquiry]=useState<Inquiry|null>(null),[flight,setFlight]=useState<Flight|null>(null);
 const dialog=useRef<HTMLDialogElement>(null),returnFocus=useRef<HTMLElement|null>(null);
 const flightTimer=useRef<number|null>(null),navigationTimer=useRef<number|null>(null);
 const pendingHref=useRef<string|null>(null),previousPathname=useRef(pathname);

 // App Router navigation is not a promise: finish when the destination commits.
 // This also cancels a pending product flight after back/forward navigation.
 useEffect(()=>{
  if(previousPathname.current===pathname)return;
  previousPathname.current=pathname;
  if(flightTimer.current!==null)window.clearTimeout(flightTimer.current);
  if(navigationTimer.current!==null)window.clearTimeout(navigationTimer.current);
  flightTimer.current=null;navigationTimer.current=null;pendingHref.current=null;
  setFlight(null);setInquiry(null);
 },[pathname]);

 useEffect(()=>{
  const pageProduct=products.find(product=>pathname==='/products/'+product.slug);
  const onClick=(event:MouseEvent)=>{
   if(event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.altKey||event.shiftKey)return;
   const anchor=event.target instanceof Element?event.target.closest<HTMLAnchorElement>('a'):null;
   if(!anchor||anchor.target==='_blank'||anchor.hasAttribute('download'))return;
   const href=anchor.getAttribute('href')??'';
   if(href==='#contact'){
    event.preventDefault();returnFocus.current=anchor;
    const comments:Record<string,string>={training:'אשמח לקבל מידע על הדרכה.',protocol:'אשמח לקבל מידע על הפרוטוקול המקצועי.',cases:'אשמח לקבל מקרי טיפול מתועדים ומידע מקצועי על V-TECH.'};
    setInquiry({productSlug:anchor.dataset.product??pageProduct?.slug??'unsure',sourceBlock:anchor.dataset.source??(pageProduct?'product-cta':'home-cta'),comment:comments[anchor.dataset.topic??'']??''});return;
   }
   if(!href.startsWith('/products/'))return;
   const slug=href.slice('/products/'.length);
   if(!products.some(product=>product.slug===slug))return;
   event.preventDefault();
   if(flightTimer.current!==null||pendingHref.current!==null)return;
   // A same-page link cannot clear a flight through a pathname change.
   if(pathname===href){setFlight(null);window.scrollTo({top:0,left:0,behavior:'instant'});return;}

   const openProduct=()=>{
    pendingHref.current=href;
    navigationTimer.current=window.setTimeout(()=>{
     if(pendingHref.current!==href)return;
     navigationTimer.current=null;pendingHref.current=null;setFlight(null);
     if(window.location.pathname!==href)window.location.assign(href);
    },8000);
    try{router.push(href,{scroll:true});}
    catch{
     if(navigationTimer.current!==null)window.clearTimeout(navigationTimer.current);
     navigationTimer.current=null;pendingHref.current=null;setFlight(null);
     window.location.assign(href);
    }
   };
   const image=anchor.querySelector<HTMLImageElement>('[data-flight-image],img');
   if(!image||window.matchMedia('(prefers-reduced-motion: reduce)').matches){openProduct();return;}
   const rect=image.getBoundingClientRect();
   if(rect.width<1||rect.height<1){openProduct();return;}
   const targetHeight=Math.min(window.innerHeight*.58,500),scale=Math.min(targetHeight/rect.height,window.innerWidth*.66/rect.width);
   const targetX=window.innerWidth*(window.innerWidth>860?.49:.5),targetY=window.innerHeight*.43;
   setFlight({slug,src:image.currentSrc||assets[slug].src,x:rect.left,y:rect.top,width:rect.width,height:rect.height,moveX:targetX-(rect.left+rect.width/2),moveY:targetY-(rect.top+rect.height/2),scale});
   if(slug==='v-tech-system'){const poster=new Image();poster.src=mediaUrl(window.matchMedia('(hover: none) and (pointer: coarse), (max-width: 860px)').matches?'/assets/world/vtech-intro-mobile-poster.webp':'/assets/world/vtech-intro-poster.webp');}
   flightTimer.current=window.setTimeout(()=>{flightTimer.current=null;openProduct();},650);
  };
  document.addEventListener('click',onClick);
  return()=>document.removeEventListener('click',onClick);
 },[pathname,router]);

 useEffect(()=>()=>{
  if(flightTimer.current!==null)window.clearTimeout(flightTimer.current);
  if(navigationTimer.current!==null)window.clearTimeout(navigationTimer.current);
 },[]);
 useEffect(()=>{
  const element=dialog.current;if(!element)return;
  if(inquiry){if(!element.open)element.showModal();const previous=document.body.style.overflow;document.body.style.overflow='hidden';return()=>{document.body.style.overflow=previous;};}
  if(element.open)element.close();
 },[inquiry]);
 const close=()=>{
  if(dialog.current?.open)dialog.current.close();
  setInquiry(null);
  if(returnFocus.current?.isConnected)returnFocus.current.focus({preventScroll:true});
 };
 const selected=inquiry?products.find(product=>product.slug===inquiry.productSlug):null;
 return <><a className="mitoderm-skip" href="#main-content">דלגו לתוכן</a>{children}
  <dialog ref={dialog} className="inquiry-dialog" onCancel={event=>{event.preventDefault();close();}} onClose={()=>setInquiry(null)} onClick={event=>{if(event.target===event.currentTarget)close();}} aria-labelledby="inquiry-heading">
   {inquiry&&<div className="inquiry-panel"><button className="inquiry-close" type="button" onClick={close} aria-label="סגירה">×</button><p className="inquiry-brand" dir="ltr">{selected?.name??'MITODERM'}</p><h2 id="inquiry-heading">מחיר, תנאים והדרכה</h2><p className="inquiry-intro">פרטים מקצועיים עבור הקליניקה שלכם.</p><LeadForm key={inquiry.productSlug+inquiry.sourceBlock} productSlug={inquiry.productSlug} sourceBlock={inquiry.sourceBlock} initialComment={inquiry.comment}/></div>}
  </dialog>
  {flight&&<div className="vc-product-flight" aria-hidden="true"><div className="vc-product-flight-ground"/><img src={flight.src} alt="" style={{left:flight.x,top:flight.y,width:flight.width,height:flight.height,'--transfer-x':flight.moveX+'px','--transfer-y':flight.moveY+'px','--transfer-scale':flight.scale} as CSSProperties}/></div>}
 </>;
}
