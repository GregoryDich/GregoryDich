import {mediaUrl} from '../media';
import {useRef,useState,type PointerEvent} from 'react';
import {ProductImage} from '../shared';
import {contact,productHref} from '../data';
import {vtechCases} from './case-data';

const approvedCases=vtechCases.filter(item=>item.publicationApproved&&item.sourceVerified&&item.product==='v-tech-system');
const related=[
 {slug:'exocell-mask',name:'EXOCELL MASK',role:'מסכת ביוצלולוזה משלימה',group:'face'},
 {slug:'exotech-gel',name:'EXOTECH GEL',role:'טיפוח ביתי משלים',group:'face'},
 {slug:'mitopen',name:'MITOPEN',role:'מכשור לעבודה מקצועית',group:'professional'},
 {slug:'micro-boost-10',name:'MICRO BOOST 10%',role:'לפרוטוקול מקצועי נוסף',group:'professional'},
 {slug:'derma-recovery-cream',name:'DERMA RECOVERY CREAM',role:'קרם טיפוח משלים',group:'professional'}
];
export function VTechCases(){
 const [index,setIndex]=useState(0);
 const touch=useRef<{x:number;y:number}|null>(null);
 function go(step:number){setIndex(current=>(current+step+approvedCases.length)%approvedCases.length);}
 function pointerUp(event:PointerEvent<HTMLElement>){
  if(!touch.current)return;const dx=event.clientX-touch.current.x,dy=event.clientY-touch.current.y;
  touch.current=null;if(Math.abs(dx)>48&&Math.abs(dx)>Math.abs(dy)*1.5)go(dx>0?1:-1);
 }
 if(!approvedCases.length)return <section id="vtech-results" className="vc-results vc-results-request" aria-labelledby="vc-results-title">
  <div className="vc-results-intro"><h2 id="vc-results-title">מבט מקצועי על התוצאות</h2><p>מקרה טיפול נבחן לפי מצב העור, התוכנית שנבחרה וזמן ההערכה.</p></div>
  <div className="vc-case-request"><div><h3>מקרי טיפול ומידע מקצועי</h3><p>פנו לצוות MITODERM לשיחה על יישום המערכת, תיעוד מקרים והציפיות מהטיפול.</p></div><a href="#contact" data-product="v-tech-system" data-source="vtech-case-request" data-topic="cases">לבקשת מקרי טיפול <span aria-hidden="true">←</span></a></div>
 </section>;
 const item=approvedCases[index];
 return <section id="vtech-results" className="vc-results" aria-labelledby="vc-results-title">
  <div className="vc-results-intro"><h2 id="vc-results-title">מקרים מהקליניקה</h2><p>אותו אזור, תיעוד לפני ואחרי, ופרטי התוכנית.</p></div>
  <div className="vc-case-carousel" role="region" aria-roledescription="קרוסלה" aria-label="מקרי טיפול ב-V-TECH" tabIndex={0}
   onKeyDown={event=>{if(event.key==='ArrowLeft'){event.preventDefault();go(1);}if(event.key==='ArrowRight'){event.preventDefault();go(-1);}}}
   onPointerDown={event=>{if(event.target instanceof Element&&event.target.closest('button,a'))return;touch.current={x:event.clientX,y:event.clientY};}}
   onPointerUp={pointerUp} onPointerCancel={()=>{touch.current=null;}}>
   <article className="vc-case" aria-label={item.title} aria-roledescription="שקופית">
    <div className="vc-case-pair" dir="ltr"><figure><img src={item.before.src} alt={item.before.alt} loading="lazy"/><figcaption>לפני</figcaption></figure><figure><img src={item.after.src} alt={item.after.alt} loading="lazy"/><figcaption>אחרי</figcaption></figure></div>
    <div className="vc-case-caption" aria-live="polite"><h3>{item.title}</h3><p>{item.program} · {item.sessions} · {item.assessment}</p>{item.details&&<details><summary>פרטי המקרה</summary><p>{item.details}</p></details>}</div>
   </article>
   {approvedCases.length>1&&<><button className="vc-case-arrow vc-case-prev" type="button" onClick={()=>go(-1)} aria-label="המקרה הקודם">›</button><button className="vc-case-arrow vc-case-next" type="button" onClick={()=>go(1)} aria-label="המקרה הבא">‹</button><div className="vc-case-dots" aria-label="בחירת מקרה">{approvedCases.map((entry,i)=><button type="button" key={entry.id} aria-label={'מקרה '+(i+1)} aria-current={i===index?'true':undefined} onClick={()=>setIndex(i)}/>)}</div></>}
  </div>
 </section>;
}
export function VTechOffer(){return <section id="vtech-kit" className="vc-offer" aria-labelledby="vc-offer-title">
 <div className="vc-kit-card"><div className="vc-kit-top"><h3>מה בערכה</h3><bdi dir="ltr">V-TECH SYSTEM</bdi></div>
  <img className="vc-kit-image" src={mediaUrl('/assets/world/vtech-kit.webp')} alt="ערכת V-TECH: חמש אמפולות סרום וחמישה שקיקי מסכת ג׳ל" width="1800" height="1200" loading="lazy" decoding="async"/>
  <dl className="vc-kit-counts"><div><dt><bdi dir="ltr">5 × 5 ml</bdi></dt><dd><bdi dir="ltr">V-TECH SERUM</bdi><span>אמפולות סרום</span></dd></div><div><dt><bdi dir="ltr">5 × 5 ml</bdi></dt><dd><bdi dir="ltr">V-TECH GEL MASK</bdi><span>שקיקי מסכת ג׳ל</span></dd></div></dl>
 </div>
 <div className="vc-offer-copy"><h2 id="vc-offer-title">הכניסו את <bdi dir="ltr">V-TECH</bdi><br/>לקליניקה שלכם</h2><p>קבלו פרטים על הערכה, תנאים מקצועיים ואפשרויות הדרכה.</p>
  <div className="vc-offer-actions"><a className="vc-offer-price" href="#contact" data-product="v-tech-system" data-source="vtech-kit">לקבלת מחיר <span aria-hidden="true">←</span></a><a className="vc-offer-training" href="#contact" data-product="v-tech-system" data-source="vtech-kit-training" data-topic="training">לתיאום הדרכה <span aria-hidden="true">↗</span></a></div>
  <p className="vc-professional-note">לשימוש מקצועי. התאמה ורכישה בהתאם להכשרה ולאימות מקצועי.</p>
  <details className="vc-formula"><summary>מרכיבי המערכת <span aria-hidden="true">+</span></summary><div><h3>הסרום</h3><p>אקסוזומים סינתטיים, PDRN, פפטידים ביומימטיים ותמצית תאי גזע של תפוח, לפי תיאור המוצר בקטלוג.</p><h3>מסכת הג׳ל</h3><p>PDRN, פפטידים, חומצה היאלורונית, אלוורה ורכיבים משלימים המתוארים בקטלוג.</p><a href="#contact" data-product="v-tech-system" data-source="vtech-formula" data-topic="protocol">לפרטים על הפרוטוקול ←</a></div></details>
  <a className="vc-direct-contact" href={contact.whatsapp_url+'?text='+encodeURIComponent('שלום, אשמח לקבל מחיר ומידע מקצועי על V-TECH SYSTEM.')} target="_blank" rel="noopener noreferrer">WhatsApp <bdi dir="ltr">{contact.phone}</bdi></a>
 </div>
 </section>;}
export function VTechRelated(){return <section id="vtech-related" className="vc-related" aria-labelledby="vc-related-title"><h2 id="vc-related-title">עוד מהעולם של <bdi dir="ltr">MITODERM</bdi></h2>
 <p className="vc-related-intro">מכשור, מוצרים משלימים ואפשרויות לפרוטוקולים נוספים. לבחירה בנפרד מהערכה.</p>
 {(['face','professional'] as const).map(group=><div className={'vc-related-group vc-related-'+group} key={group}><h3>{group==='face'?'עוד מקו הפנים':'לתוכניות מקצועיות נוספות'}</h3><div className="vc-related-grid">{related.filter(item=>item.group===group).map(item=><a className={'vc-related-card vc-related-card-'+item.slug} key={item.slug} href={productHref(item.slug)} data-flight="true"><div className="vc-related-image"><ProductImage slug={item.slug}/></div><div><h4><bdi dir="ltr">{item.name}</bdi></h4><p>{item.role}</p><span className="vc-related-link">לפרטים <span aria-hidden="true">←</span></span></div></a>)}</div></div>)}
 </section>;}
