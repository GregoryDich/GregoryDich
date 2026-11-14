'use client';

import {useEffect,useMemo,useRef,useState,type CSSProperties} from 'react';
import type {Product} from '../types';
import {products,assets} from '../data';
import {SiteHeader,SiteFooter,ContactBlock} from '../shared';
import registry from '../../production/page-bible/REGISTRY.json';
import nadStoryboard from '../../production/page-bible/pages/exo-nad/STORYBOARD.json';
import './product-cinema.css';

type Chapter={title:string;seconds:number;vh:number;type:string;index:number};
const clamp=(n:number)=>Math.max(0,Math.min(1,n));
const related:Record<string,string[]>={
 'exo-nad':['exocell-mask','derma-recovery-cream','exotech-gel'],
 'exosignal-hair':['mitoscan','mitopen','exosignal-spray'],
 'exocell-mask':['v-tech-system','exo-nad','derma-recovery-cream'],
 'micro-boost-10':['derma-recovery-cream','cell-renew-1-5','mitopen'],
 'mitotech-cell-booster':['mitopen','exocell-mask','derma-recovery-cream'],
 'mitopen':['v-tech-system','mitotech-cell-booster','exosignal-hair'],
 'mitoscan':['exosignal-hair','exosignal-spray','mitopen'],
 'exotech-gel':['v-tech-system','exocell-mask','derma-recovery-cream'],
 'derma-recovery-cream':['micro-boost-10','cell-renew-1-5','cellular-age-defense-2-5'],
 'exosignal-spray':['exosignal-hair','mitoscan','exotech-gel'],
 'cell-renew-1-5':['derma-recovery-cream','cellular-age-defense-2-5','micro-boost-10'],
 'cellular-age-defense-2-5':['cell-renew-1-5','derma-recovery-cream','micro-boost-10']
};
// Separate Hebrew film copy, based on each real product's screenplay, never
// published age-based casting tags or substituted models.
const scriptTitles:Record<string,string[]>={
 'exosignal-hair':['EXOSIGNAL HAIR','מה מביא אותך לטיפול?','מתבוננים בקרקפת','האמפולה המקצועית','אותו אזור, אותו מטופל','תיעוד ומעקב','המערכת לקליניקה'],
 'exocell-mask':['EXOCELL MASK','בחירה מקצועית','מסכה אחת, שכבות שונות','מסירים שכבה ראשונה','מסירים שכבה שנייה','מניחים את המסכה הלבנה','מסיימים בעדינות','המסכה המקצועית'],
 'micro-boost-10':['MICRO BOOST 10%','התאמה מתחילה באבחון','המוליך הלבן','עבודה מקצועית מבוקרת','אותו אזור של העור','סיום והתאמה','המערכת לקליניקה'],
 'mitotech-cell-booster':['MITOTECH CELL BOOSTER','מתחילים באבחון','שני מרכיבים במערכת אחת','הכנת החומר','עבודה עם MITOPEN','סיום התהליך','תיעוד ומעקב','הערכה המקצועית'],
 'mitopen':['MITOPEN','אזור עבודה שנבחר','הכלי בידיים מקצועיות','מיקרונידלינג','דיוק ושליטה','מסיימים את הטיפול','לתיאום הדגמה'],
 'mitoscan':['MITOSCAN','מתחילים בבירור','מבט קרוב על הקרקפת','תצוגה מקורית','בוחנים ביחד','תיעוד מקצועי','מכירים את המכשיר'],
 'exotech-gel':['EXOTECH GEL','המלצה מהקליניקה','אותה שגרה, בבית','מרקם הג׳ל','טיפוח ביתי','ממשיכים לאורך זמן','המוצר הביתי'],
 'derma-recovery-cream':['DERMA RECOVERY CREAM','התאמת הטיפוח','אותה מטופלת בבית','מרקם הקרם','טיפוח משלים','סיום השגרה','הקרם'],
 'exosignal-spray':['EXOSIGNAL SPRAY','מתחילים בקרקפת','ממשיכים בבית','המוליך המדויק','השימוש הביתי','שגרה לאורך זמן','התרסיס'],
 'cell-renew-1-5':['CELL RENEW 1.5%','בחירת טיפוח מתאים','אותה מטופלת בבית','הפורמולה','טיפוח ביתי','ממשיכים בשגרה','המוצר'],
 'cellular-age-defense-2-5':['CELLULAR AGE DEFENSE 2.5%','התאמה מקצועית','אותה מטופלת בבית','הפורמולה','טיפוח ביתי','שגרה מותאמת','המוצר']
};
function sceneryCopy(slug:string,chapter:Chapter,i:number){
 if(slug==='exo-nad'){
  const shot=nadStoryboard.shots[i];
  if(shot)return {title:shot.headlineHE,body:shot.copyHE,tag:shot.titleHE};
 }
 const title=scriptTitles[slug]?.[i]??chapter.title;
 const body=chapter.type==='patient'?'ההתאמה מתחילה בהקשבה ובבחינת הצורך של אותה מטופלת.':
  chapter.type==='procedure'?'שלב העבודה נקבע לפי פרוטוקול מקצועי ובהתאם לאזור שנבחר.':
  chapter.type==='device'?'כלי מקצועי עם תפקיד ברור במסגרת תוכנית העבודה.':
  chapter.type==='home'?'אותה מטופלת ממשיכה בשגרת הטיפוח בבית.':
  chapter.type==='evidence'||chapter.type==='record'?'תיעוד אמיתי והערכה מקצועית, ללא הבטחות לתוצאה.':
  'מכירים את המוצר המקורי ואת מקומו בתוכנית העבודה.';
 return {title,body,tag:chapter.type==='home'?'טיפוח בבית':'MITODERM · לשימוש מקצועי'};
}

function Evidence({product}:{product:Product}){
 return <section id="pc-evidence" className="pc-evidence" aria-labelledby="pc-evidence-title">
  <div className="pc-width pc-evidence-grid"><div>
   <p className="pc-eyebrow"><bdi dir="ltr">{product.name}</bdi> · תיעוד</p>
   <h2 id="pc-evidence-title">רוצים לראות את התמונה המלאה?</h2>
   <p>בוחנים את נקודת המוצא, תוכנית העבודה ומועד ההערכה. רק תיעוד מקרים אמיתי ומאושר יוצג כתוצאה של טיפול.</p>
   <a className="pc-link" href="#contact" data-product={product.slug} data-source="pc-evidence" data-topic="cases">למידע על מקרים ותיעוד <span aria-hidden="true">←</span></a>
  </div><div className="pc-evidence-steps" aria-label="פרטי תיעוד מקצועי">
   <div><span>01</span><strong>נקודת המוצא</strong><small>מה נבדק בתחילת הדרך</small></div>
   <div><span>02</span><strong>תוכנית העבודה</strong><small>פרוטוקול מותאם</small></div>
   <div><span>03</span><strong>מועד הערכה</strong><small>מידע מתועד בלבד</small></div>
  </div></div>
 </section>;
}

function Offer({product,pack,openKit,usp}:{product:Product;pack:string;openKit:string;usp:string}){
 const nad=product.slug==='exo-nad';
 const home=['exotech-gel','derma-recovery-cream','exosignal-spray','cell-renew-1-5','cellular-age-defense-2-5'].includes(product.slug);
 return <section className="pc-offer" id="pc-offer" aria-labelledby="pc-offer-title">
  <div className="pc-width pc-offer-grid">
   <div className="pc-offer-product"><img src={nad?openKit:pack} alt={'הערכה המקורית של '+product.name} loading="lazy" decoding="async"/><span>המוצר המקורי</span></div>
   <div className="pc-offer-copy">
    <p className="pc-eyebrow">MITODERM · הצעה מקצועית</p>
    <h2 id="pc-offer-title">הכירו את <bdi dir="ltr">{product.name}</bdi><br/>{home?'כהמשך לטיפוח בבית.':'בקליניקה שלכם.'}</h2>
    <p>{usp}</p>
    {nad?<dl className="pc-components">
     <div><dt>EXO BIPHASIC PEEL</dt><dd><bdi dir="ltr">1 × 15 ml</bdi></dd></div>
     <div><dt>pH NORMALIZER</dt><dd><bdi dir="ltr">5 × 5 ml</bdi></dd></div>
     <div><dt>LONGEVITY SERUM</dt><dd><bdi dir="ltr">5 × 5 ml</bdi></dd></div>
    </dl>:<p className="pc-offer-note">תכולה, הזמנת המוצר ואפשרויות הדרכה לפי ההוראות והמידע העדכני מאת MITODERM.</p>}
    <a href="#contact" data-product={product.slug} data-source="pc-offer" className="pc-primary">לקבלת פרטים והצעה <span aria-hidden="true">←</span></a>
    <a href="#contact" data-product={product.slug} data-topic="training" data-source="pc-offer-training" className="pc-link">למידע על פרוטוקול והדרכה</a>
   </div>
  </div>
 </section>;
}
function Professional({product}:{product:Product}){
 const questions=product.slug==='exo-nad'?
 nadStoryboard.lower.find(section=>section.id==='10')?.faq:
 [{q:'למי מיועד המוצר?',a:'התאמה מקצועית או המלצה להמשך טיפוח לפי הייעוד וההנחיות של המוצר.'},
  {q:'כיצד מקבלים מידע על הפרוטוקול?',a:'מוזמנים להשאיר פרטים ולבקש מידע מקצועי, הדרכה ותנאי רכישה.'},
  {q:'האם התמונות מציגות תוצאה טיפולית?',a:'המחשת מוצר אינה תיעוד קליני. מקרים יוצגו רק לאחר אישור המקור וההסכמה לפרסום.'}];
 const home=['exotech-gel','derma-recovery-cream','exosignal-spray','cell-renew-1-5','cellular-age-defense-2-5'].includes(product.slug);
 return <section id="pc-training" className="pc-training" aria-labelledby="pc-training-title"><div className="pc-width">
  <div className="pc-training-title"><p className="pc-eyebrow">לשימוש מקצועי · MITODERM</p>
   <h2 id="pc-training-title">מכירים את {home?'המוצר.':'המערכת.'}<br/><em>{home?'מחברים בין קליניקה לבית.':'בונים את דרך העבודה.'}</em></h2>
   <p>לומדים את התפקיד של <bdi dir="ltr">{product.name}</bdi> במסגרת תוכנית עבודה ומבררים על הדרכה מקצועית.</p>
   <a className="pc-primary" href="#contact" data-product={product.slug} data-source="pc-training" data-topic="training">מידע על הדרכה <span aria-hidden="true">←</span></a>
  </div>
  <div className="pc-questions"><div><p className="pc-eyebrow">שאלות נפוצות</p><h3>מה כדאי לדעת לפני שמתחילים?</h3></div>
   <div>{(questions??[]).map((item,i)=><details key={i}><summary>{item.q}<span aria-hidden="true">+</span></summary><p>{item.a}</p></details>)}</div>
  </div>
 </div></section>;
}
function Related({slug}:{slug:string}){
 const cards=(related[slug]??[]).map(s=>products.find(p=>p.slug===s)).filter((p):p is Product=>Boolean(p));
 return <section className="pc-related" id="pc-related" aria-labelledby="pc-related-title"><div className="pc-width">
  <p className="pc-eyebrow">MITODERM · מוצרים משלימים</p><h2 id="pc-related-title">הטיפוח ממשיך בדרך המתאימה.</h2><p>מוצרים נפרדים שניתן לבחון עם אשת מקצוע. אינם כלולים במערכת זו אלא אם צוין במפורש.</p>
  <div className="pc-related-list">{cards.map(p=><a key={p.slug} href={'/products/'+p.slug}><img src={assets[p.slug]?.src} alt={p.name} loading="lazy" decoding="async"/><span><bdi dir="ltr">{p.name}</bdi></span><span aria-hidden="true">←</span></a>)}</div>
 </div></section>;
}

export default function ProductCinema({product}:{product:Product}){
 const config=registry.pages.find(p=>p.slug===product.slug);
 const palettes:Record<string,{bg:string;surface:string;accent:string;text:string;source:string}>=registry.paletteByFamily;
 const theme=palettes[config?.palette??'vm_gold']??palettes.vm_gold;
 const chapters:Chapter[]=useMemo(()=>config?.shots.map((s,i)=>({...s,index:i+1}))??[],[config]);
 const starts=useMemo(()=>chapters.map((_,i)=>chapters.slice(0,i).reduce((n,x)=>n+x.vh,0)),[chapters]);
 const total=chapters.reduce((n,c)=>n+c.vh,0);
 const [active,setActive]=useState(0),[linear,setLinear]=useState(false);
 const root=useRef<HTMLElement>(null),stage=useRef<HTMLDivElement>(null);
 const nad=product.slug==='exo-nad';
 const pack=nad?'/assets/product-cinema/exo-nad/NAD.png':(assets[product.slug]?.src??'/assets/brand/cover.webp');
 // Approved real-pack photo must not morph into older invented vial colors.
 // Match original product types during scene closeups; true kit photo used only in final kit shot.
 const vials=pack;
 const openKit=nad?'/assets/product-cinema/exo-nad/kit.webp':pack;
 const jump=(i:number)=>{
  if(linear){document.getElementById('pc-shot-'+(i+1))?.scrollIntoView({behavior:'smooth',block:'start'});return;}
  if(!root.current)return;
  const y=root.current.getBoundingClientRect().top+window.scrollY+starts[i]*window.innerHeight;
  window.scrollTo({top:y,behavior:'instant'});
 };
 useEffect(()=>{
  const r=root.current,s=stage.current;if(!r||!s||!chapters.length)return;
  const mm=window.matchMedia('(prefers-reduced-motion: reduce)');
  let raf=0,last=-1;
  const read=()=>{
   raf=0;if(mm.matches)return;
   const v=Math.max(1,window.innerHeight);
   const traveled=-r.getBoundingClientRect().top/v;
   const u=Math.min(total,Math.max(0,traveled));
   let i=chapters.length-1;
   for(let n=0;n<chapters.length;n++)if(u<starts[n]+chapters[n].vh){i=n;break;}
   const local=clamp((u-starts[i])/chapters[i].vh);
   r.dataset.activeShot=String(i);r.dataset.chapterProgress=local.toFixed(4);
   s.style.setProperty('--pc-progress',(u/total).toFixed(5));
   s.style.setProperty('--pc-local',local.toFixed(4));
   if(i!==last){last=i;setActive(i);}
  };
  const schedule=()=>{if(!raf)raf=requestAnimationFrame(read);};
  const motion=()=>{setLinear(mm.matches);if(!mm.matches)read();};
  mm.addEventListener('change',motion);
  window.addEventListener('scroll',schedule,{passive:true});
  window.addEventListener('resize',schedule);
  motion();read();
  return()=>{cancelAnimationFrame(raf);mm.removeEventListener('change',motion);window.removeEventListener('scroll',schedule);window.removeEventListener('resize',schedule);};
 },[chapters,starts,total]);
 if(!config||!chapters.length)return null;
 const current=chapters[active];
 const style={'--pc-bg':theme.bg,'--pc-surface':theme.surface,'--pc-accent':theme.accent,'--pc-ink':theme.text,'--pc-scroll':total+1} as CSSProperties;
 // One canonical product photograph supplies all three actual EXO-NAD bottles.
 // Never hallucinate numbered flacons or morph bottle colors during a scroll.
 const mediaPhase=nad?(['hero','hero','peel','normalizer','serum','hero','hero','kit'][active]??'hero'):'hero';
 const chapterName=(i:number)=>sceneryCopy(product.slug,chapters[i],i);
 return <div className="pc-page" style={style} data-linear={linear}>
  <SiteHeader/>
  <main id="main-content">
   <section className="pc-story" id="pc-story" ref={root} aria-label={'סיפור המוצר '+product.name} data-active-shot={active}>
    <div className="pc-stage" ref={stage}>
     <div className="pc-atmosphere" aria-hidden="true"><span className="pc-aura pc-aura-a"/><span className="pc-aura pc-aura-b"/><span className="pc-arc"/></div>
     <div className="pc-object" aria-hidden="true" data-phase={mediaPhase}>
      <figure data-visible={mediaPhase==='hero'}><img src={pack} alt="" width={nad?795:800} height={nad?489:800}/></figure>
      {nad&&<>
       {(['peel','normalizer','serum'] as const).map((bottle)=>
        <figure className="pc-nad-focus" key={bottle} data-visible={mediaPhase===bottle} data-bottle={bottle}>
         <div className="pc-nad-focus-photo" style={{backgroundImage:'url('+pack+')'}}/>
         <span className="pc-nad-focus-legend" dir="ltr">{bottle==='peel'?'EXO BIPHASIC PEEL':bottle==='normalizer'?'pH NORMALIZER':'LONGEVITY SERUM'}</span>
        </figure>)}
       <figure className="pc-nad-kit" data-visible={mediaPhase==='kit'}><img src="/assets/product-cinema/exo-nad/kit.webp" alt="" width="500" height="720"/></figure>
      </>}
     </div>
     <div className="pc-scenes">
      {chapters.map((chapter,i)=>{const copy=chapterName(i),Heading=i===0?'h1':'h2';return <article key={i} id={'pc-shot-'+(i+1)} className="pc-scene" data-visible={active===i} data-kind={chapter.type} aria-hidden={!linear&&active!==i} inert={!linear&&active!==i}>
       {linear&&<div className="pc-linear-product"><img src={nad&&i===7?'/assets/product-cinema/exo-nad/kit.webp':pack} alt={'מוצר '+product.name} loading={i===0?'eager':'lazy'}/></div>}
       <div className="pc-caption" dir="rtl">
        <p className="pc-kicker"><span>{String(i+1).padStart(2,'0')} / {String(chapters.length).padStart(2,'0')}</span><bdi dir="ltr">{product.name}</bdi></p>
        <Heading dir={i===0?'ltr':undefined}>{copy.title}</Heading>
        <p>{copy.body}</p>
        {i===0?<div className="pc-actions"><a className="pc-primary" href="#contact" data-product={product.slug} data-source="pc-hero">לקבלת פרטים <span aria-hidden="true">←</span></a><button type="button" onClick={()=>jump(1)}>אל התהליך ↓</button></div>:i===chapters.length-1?<a className="pc-link" href="#pc-offer">לערכה המקצועית ↓</a>:null}
       </div>
      </article>;})}
     </div>
     <div className="pc-hud" aria-label="ניווט בין שלבי ההמחשה">
      <div className="pc-steps">{chapters.map((chapter,i)=><button key={i} className="pc-step" aria-label={'שלב '+(i+1)+': '+chapterName(i).tag} aria-current={active===i?'step':undefined} onClick={()=>jump(i)}><span>{String(i+1).padStart(2,'0')}</span></button>)}</div>
      <span className="pc-hud-note">{current.index} / {chapters.length} · גללו להמשך</span>
     </div>
     <div className="pc-line" aria-hidden="true"><i/></div>
    </div>
   </section>
   <Evidence product={product}/>
   <Offer product={product} pack={pack} openKit={openKit} usp={config.uspHE}/>
   <Professional product={product}/>
   <Related slug={product.slug}/>
   <ContactBlock productName={product.name}/>
  </main>
  <SiteFooter/>
 </div>;
}
