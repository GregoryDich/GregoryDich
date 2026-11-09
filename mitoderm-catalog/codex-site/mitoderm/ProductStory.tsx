import type {Product,StorySection} from './types';
import {Chapter,ProductImage,Smoke,ContactBlock,SiteHeader,SiteFooter} from './shared';
import {ui,contact} from './data';
import './product-story.css';
function SectionBody({section,nextId}:{section:StorySection;nextId?:string}){
 const tags=section.tags.split(' · ').map(s=>s.trim()).filter(Boolean);
 const ingredients=/פורמולה|מרכיב|רכיב/i.test(`${section.eyebrow??''} ${section.title} ${section.cta}`);
 const shown=ingredients?tags.slice(0,4):tags.slice(0,4),extra=tags.slice(4);
 const actions=section.cta.split(' · ').filter(Boolean);
 return <div className="story-copy-body"><p>{section.body}</p>
  {shown.length>0&&<ul className="story-terms">{shown.map((tag,i)=><li key={i}>{tag}</li>)}</ul>}
  {(extra.length>0||ingredients)&&<details className="story-details"><summary>{ingredients?(actions.find(x=>/פורמולה|מרכיב|רכיב/.test(x))??ui['buttons.learnMore']):ui['buttons.learnMore']}</summary><ul>{(extra.length?extra:tags).map((tag,i)=><li key={i}>{tag}</li>)}</ul></details>}
  <div className="story-actions">{actions.filter(x=>!(/פורמולה|מרכיב|רכיב/.test(x)&&ingredients)).map((action,i)=>{
    const href=/WhatsApp/.test(action)?contact.whatsapp_url:/טלפון/.test(action)?contact.tel:/דוא/.test(action)?contact.mailto:/גלו/.test(action)&&nextId?`#${nextId}`:'#contact';
    return <a key={i} className="story-contact-link" href={href}>{action}</a>;
  })}</div>
 </div>;
}
export default function ProductStory({product}:{product:Product}){
 const chapters=[product.intro,...product.sections].filter(s=>s.index<=7);
 return <div className="product-story"><SiteHeader/><main id="main-content">
  {chapters.map((section,index)=>{const id=`${product.slug}-chapter-${index+1}`;return <Chapter key={id} id={id} line={product.line} className={`product-story-chapter story-composition-${index%3}`}>
   <div className="layer-background" aria-hidden="true"/>
   <div className="layer-motion story-motion"><Smoke/><div className="product-stage story-product-stage"><div className="story-product-pose"><ProductImage slug={product.slug} className="story-product-image"/></div></div></div>
   <div className="layer-content story-content"><header className="story-copy-heading">{index===0&&<p className="story-product-name"><bdi dir="ltr">{product.name}</bdi></p>}{index===0?<h1><bdi dir="auto">{section.title}</bdi></h1>:<h2>{section.title}</h2>}</header><SectionBody section={section} nextId={index+1<chapters.length?`${product.slug}-chapter-${index+2}`:undefined}/></div>
  </Chapter>;})}
  <ContactBlock productName={product.name}/></main><SiteFooter/></div>;
}
