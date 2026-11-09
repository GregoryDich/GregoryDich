'use client';

import {useCallback,useEffect,useRef,useState,type ReactNode} from 'react';
import {usePathname,useRouter} from 'next/navigation';
import {products,assets} from '../data';
import {LeadForm} from './LeadForm';
import {ProductTransition,type ProductFlight} from './ProductTransition';
import './product-flight.css';

type Inquiry={productSlug:string;sourceBlock:string;comment:string;topic:string};

export function SiteExperience({children}:{children:ReactNode}){
 const pathname=usePathname();
 const router=useRouter();
 const [inquiry,setInquiry]=useState<Inquiry|null>(null),[flight,setFlight]=useState<ProductFlight|null>(null);
 const dialog=useRef<HTMLDialogElement>(null),returnFocus=useRef<HTMLElement|null>(null);
 const navigationTimer=useRef<number|null>(null);
 const pendingHref=useRef<string|null>(null),previousPathname=useRef(pathname);

 const finishFlight=useCallback(()=>{
  const destination=pendingHref.current;
  if(navigationTimer.current!==null)window.clearTimeout(navigationTimer.current);
  navigationTimer.current=null;pendingHref.current=null;setFlight(null);
  // Finishing a visual effect must never cancel the user's chosen navigation.
  if(destination&&window.location.pathname!==destination)window.location.assign(destination);
 },[]);
 const openProduct=useCallback((href:string)=>{
  pendingHref.current=href;
  navigationTimer.current=window.setTimeout(()=>{
   if(pendingHref.current!==href)return;
   navigationTimer.current=null;pendingHref.current=null;setFlight(null);
   if(window.location.pathname!==href)window.location.assign(href);
  },8000);
  try{router.push(href,{scroll:true});}
  catch{finishFlight();window.location.assign(href);}
 },[router,finishFlight]);

 // A measured landing, rather than pathname, finishes the product handoff.
 useEffect(()=>{
  if(previousPathname.current===pathname)return;
  previousPathname.current=pathname;
  if(navigationTimer.current!==null)window.clearTimeout(navigationTimer.current);
  navigationTimer.current=null;setInquiry(null);
  if(pendingHref.current!==pathname||!flight){pendingHref.current=null;setFlight(null);}
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
    const productSlug=anchor.dataset.product??pageProduct?.slug??'unsure';
    const productName=products.find(product=>product.slug===productSlug)?.name??'MITODERM';
    const topic=anchor.dataset.topic??'offer';
    const comments:Record<string,string>={training:'אשמח לקבל מידע על הדרכה ושילוב '+productName+' בעבודה המקצועית.',protocol:'אשמח לקבל מידע על הפרוטוקול המקצועי של '+productName+'.',cases:'אשמח לקבל מקרי טיפול מתועדים ומידע מקצועי על '+productName+'.',demo:'אשמח לתאם היכרות מקצועית והדגמה של '+productName+'.'};
    setInquiry({productSlug,sourceBlock:anchor.dataset.source??(pageProduct?'product-cta':'home-cta'),comment:comments[topic]??'',topic});return;
   }
   if(!href.startsWith('/products/'))return;
   const slug=href.slice('/products/'.length);
   if(!products.some(product=>product.slug===slug))return;
   event.preventDefault();
   if(flight||pendingHref.current!==null)return;
   // A same-page link cannot clear a flight through a pathname change.
   if(pathname===href){setFlight(null);window.scrollTo({top:0,left:0,behavior:'instant'});return;}

   if(slug==='v-tech-system'&&anchor.dataset.flightPhoto==='true'&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches){
    const frame=anchor.closest('[data-collection-frame]');
    const poster=Array.from(frame?.querySelectorAll<HTMLImageElement>('img[data-collection-poster]')??[]).find(item=>item.getBoundingClientRect().width>0);
    const sourceBox=anchor.querySelector<HTMLElement>('[data-flight-box]')??anchor;
    if(poster?.complete&&poster.naturalWidth>0){
     const measured=sourceBox.getBoundingClientRect(),photoRect=poster.getBoundingClientRect();
     if(measured.width>0&&measured.height>0){
      const rect={left:measured.left,top:measured.top,width:measured.width,height:measured.height};
      pendingHref.current=href;
      setFlight({id:performance.now(),slug,href,src:poster.currentSrc||poster.src,rect,box:rect,photo:{rect:{left:photoRect.left,top:photoRect.top,width:photoRect.width,height:photoRect.height},silhouette:sourceBox.dataset.photoSilhouette??'polygon(0% 2%,12% 0%,100% 1%,100% 99%,12% 100%,0% 97%)'}});
      return;
     }
    }
   }
   const image=anchor.querySelector<HTMLImageElement>('[data-flight-image],img');
   if(slug!=='v-tech-system'||anchor.dataset.flightSkip==='true'||!image||window.matchMedia('(prefers-reduced-motion: reduce)').matches){openProduct(href);return;}
   const rect=image.getBoundingClientRect();
   if(rect.width<1||rect.height<1){openProduct(href);return;}
   const scale=Math.min(rect.width/(image.naturalWidth||513),rect.height/(image.naturalHeight||875));
   const width=(image.naturalWidth||513)*scale,height=(image.naturalHeight||875)*scale;
   const rendered={left:rect.left+(rect.width-width)/2,top:rect.top+(rect.height-height)/2,width,height};
   // Match the box, excluding the vials/sachet photographed beside the catalog kit.
   const box={left:rendered.left,top:rendered.top,width:width*362/513,height:height*800/875};
   pendingHref.current=href;
   setFlight({id:performance.now(),slug,href,src:image.currentSrc||assets[slug].src,rect:rendered,box});
  };
  document.addEventListener('click',onClick);
  return()=>document.removeEventListener('click',onClick);
 },[pathname,router,flight,openProduct]);

 useEffect(()=>()=>{
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
 const inquiryTitles:Record<string,string>={offer:'הצעה מקצועית לקליניקה',training:'הדרכה וליווי מקצועי',protocol:'מידע על הפרוטוקול',cases:'מקרי טיפול ומידע מקצועי',demo:'היכרות והדגמה מקצועית'};
 return <><a className="mitoderm-skip" href="#main-content">דלגו לתוכן</a>{children}
  <dialog ref={dialog} className="inquiry-dialog" onCancel={event=>{event.preventDefault();close();}} onClose={()=>setInquiry(null)} onClick={event=>{if(event.target===event.currentTarget)close();}} aria-labelledby="inquiry-heading">
   {inquiry&&<div className="inquiry-panel"><button className="inquiry-close" type="button" onClick={close} aria-label="סגירה">×</button><p className="inquiry-brand" dir="ltr">{selected?.name??'MITODERM'}</p><h2 id="inquiry-heading">{inquiryTitles[inquiry.topic]??inquiryTitles.offer}</h2><p className="inquiry-intro">השאירו פרטים לשיחה על התאמה, מידע ותנאים מקצועיים.</p><LeadForm key={inquiry.productSlug+inquiry.sourceBlock+inquiry.topic} productSlug={inquiry.productSlug} sourceBlock={inquiry.sourceBlock} initialComment={inquiry.comment}/></div>}
  </dialog>
  {flight&&<ProductTransition flight={flight} onNavigate={openProduct} onFinish={finishFlight}/>}
 </>;
}
