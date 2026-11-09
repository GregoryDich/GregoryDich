'use client';

import {useEffect,useRef,useState,type CSSProperties,type ReactNode} from 'react';
import {assets,contact,lineKeys,products,ui,productHref} from './data';
import {LeadForm} from './pilot/LeadForm';

export function Chapter({id,line,className='',children}:{id:string;line?:string;className?:string;children:ReactNode}) {
  const ref=useRef<HTMLElement>(null);
  useEffect(()=>{
    const el=ref.current;if(!el)return;
    const preference=window.matchMedia('(prefers-reduced-motion: reduce)');
    const measure=()=>{const heading=el.querySelector('.section-copy h2');if(heading&&window.innerWidth<=760){const r=el.getBoundingClientRect();el.style.setProperty('--stage-top',`${heading.getBoundingClientRect().bottom-r.top+20}px`);}};
    const resizeObserver=new ResizeObserver(measure);resizeObserver.observe(el);measure();
    let frame=0,near=true,targetX=0,targetY=0,x=0,y=0;
    const apply=()=>{
      frame=0;
      if(preference.matches){el.style.setProperty('--scroll-progress','.5');el.style.setProperty('--tilt-x','0');el.style.setProperty('--tilt-y','0');return;}
      if(!near)return;
      const r=el.getBoundingClientRect();
      const p=Math.max(0,Math.min(1,(window.innerHeight-r.top)/(window.innerHeight+r.height)));
      x+=(targetX-x)*.12;y+=(targetY-y)*.12;
      el.style.setProperty('--scroll-progress',p.toFixed(4));
      el.style.setProperty('--tilt-x',x.toFixed(3));el.style.setProperty('--tilt-y',y.toFixed(3));
      if(Math.abs(targetX-x)+Math.abs(targetY-y)>.006)frame=requestAnimationFrame(apply);
    };
    const schedule=()=>{if(!frame)frame=requestAnimationFrame(apply);};
    const onPointer=(e:PointerEvent)=>{if(e.pointerType!=='mouse'||preference.matches)return;const r=el.getBoundingClientRect();targetX=(e.clientX-r.left)/r.width-.5;targetY=(e.clientY-r.top)/r.height-.5;schedule();};
    const reset=()=>{targetX=0;targetY=0;schedule();};
    const observer=new IntersectionObserver(entries=>{near=entries[0].isIntersecting;if(near)schedule();},{rootMargin:'120px'});
    observer.observe(el);window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',schedule);el.addEventListener('pointermove',onPointer,{passive:true});el.addEventListener('pointerleave',reset);preference.addEventListener('change',schedule);schedule();
    return()=>{cancelAnimationFrame(frame);observer.disconnect();resizeObserver.disconnect();window.removeEventListener('scroll',schedule);window.removeEventListener('resize',schedule);el.removeEventListener('pointermove',onPointer);el.removeEventListener('pointerleave',reset);preference.removeEventListener('change',schedule);};
  },[]);
  return <section ref={ref} id={id} className={`chapter ${className}`} data-line={lineKeys[line??'']??line??'neutral'}>{children}</section>;
}

export function ProductImage({slug,className=''}:{slug:string;className?:string}) {
  const asset=assets[slug];const product=products.find(p=>p.slug===slug);
  if(!asset||!product)return null;
  return <img className={`product-image ${className}`} src={asset.src} alt={product.name} width={asset.width} height={asset.height} loading="lazy" decoding="async" style={{'--asset-max':`${Math.min(asset.maxWidth,asset.width/2)}px`,'--asset-height':`${asset.height/2}px`} as CSSProperties}/>;
}

export function Smoke(){return <div className="soft-smoke" aria-hidden="true"><i/><i/><i/></div>;}

export function SiteHeader(){
 const [open,setOpen]=useState(false);
 return <header className="site-header"><div className="nav-inner">
   <a className="brand-home" href="/" aria-label="MITODERM"><img src="/assets/brand/logo-white.webp" alt="MITODERM" width="480" height="144"/></a>
   <nav className={`header-links ${open?'is-open':''}`} aria-label={ui.catalog}>
     <a href="/#products">מוצרים</a><a href="/products/v-tech-system"><bdi>V-TECH</bdi></a><a href="/#support">הדרכה וליווי</a><a href="/catalog">{ui.catalog}</a>
   </nav>
   <a href="#contact" className="nav-contact">{ui.contact}<span aria-hidden="true">↗</span></a>
   <button className="mobile-menu" onClick={()=>setOpen(!open)} aria-expanded={open} aria-label={ui.catalog}>{open?'×':'☰'}</button>
 </div></header>;
}

export function ContactBlock({productName='MITODERM'}:{productName?:string}){
 const product=products.find(item=>item.name===productName);
 return <Chapter id="contact" className="contact-section" line="neutral"><div className="layer-background" aria-hidden="true"/><div className="layer-content contact-layout"><div className="contact-copy"><span className="contact-brand" dir="ltr">{product?.name??'MITODERM'}</span><h2>בואו נדבר על הקליניקה שלכם</h2><p>השאירו פרטים לקבלת מידע, הצעה מקצועית ואפשרויות הדרכה.</p><div className="contact-destinations"><a href={contact.whatsapp_url} target="_blank" rel="noopener noreferrer">WhatsApp<span aria-hidden="true">↗</span></a><a href={contact.tel}>{ui.phone}<bdi dir="ltr">{contact.phone}</bdi></a><a href={contact.mailto}>{ui.email}<bdi dir="ltr">{contact.email}</bdi></a></div></div><LeadForm key={product?.slug??'unsure'} productSlug={product?.slug??'unsure'} sourceBlock="contact-section"/></div></Chapter>;
}

export function SiteFooter(){return <footer className="site-footer"><a href="/" className="footer-logo"><img src="/assets/brand/logo-white.webp" alt="MITODERM" width="480" height="144"/></a><a href="/catalog">{ui.catalog}</a><a href="#contact">{ui.contact}</a><a className="footer-privacy" href="/privacy">פרטיות</a><bdi dir="ltr">MITODERM</bdi></footer>;}

export function ProductLink({slug}:{slug:string}){const p=products.find(p=>p.slug===slug);return p?<a href={productHref(slug)} className="product-text-link"><bdi dir="ltr">{p.name}</bdi><span aria-hidden="true">↗</span></a>:null;}
