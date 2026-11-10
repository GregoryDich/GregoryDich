import {useRef,useState,type PointerEvent} from 'react';
import {ProductImage} from '../shared';
import {productHref} from '../data';
import {vtechCases} from './case-data';
import './vtech-training.css';

const approvedCases=vtechCases.filter(item=>item.publicationApproved&&item.sourceVerified&&item.product==='v-tech-system');
const related=[
 {slug:'mitopen',name:'MITOPEN',role:'מכשור המיקרונידלינג שמופיע בהמחשה. לעבודה לפי הכשרה ופרוטוקול.',group:'care'},
 {slug:'exocell-mask',name:'EXOCELL MASK',role:'מסכת ביוצלולוזה כאפשרות לסיום הטיפול, בהתאם לפרוטוקול. נבחרת בנפרד ממסכת הג׳ל.',group:'care'},
 {slug:'derma-recovery-cream',name:'DERMA RECOVERY CREAM',role:'קרם כאפשרות לטיפוח משלים לאחר הטיפול, לפי התאמה מקצועית.',group:'care'},
 {slug:'exotech-gel',name:'EXOTECH GEL',role:'טיפוח ביתי משלים. ההתאמה נעשית בנפרד מתוכנית העבודה עם V-TECH.',group:'care'},
 {slug:'micro-boost-10',name:'MICRO BOOST 10%',role:'מערכת BIOSPICULE מקצועית לפרוטוקול נוסף. אינה חלק מהערכה או מרצף ההמחשה שמעל.',group:'alternative'}
];
export function VTechEvidencePanel(){
 const [index,setIndex]=useState(0);
 const touch=useRef<{x:number;y:number}|null>(null);
 function go(step:number){if(approvedCases.length>1)setIndex(current=>(current+step+approvedCases.length)%approvedCases.length);}
 function pointerUp(event:PointerEvent<HTMLElement>){
  if(!touch.current)return;const dx=event.clientX-touch.current.x,dy=event.clientY-touch.current.y;
  touch.current=null;if(Math.abs(dx)>48&&Math.abs(dx)>Math.abs(dy)*1.5)go(dx>0?1:-1);
 }
 if(!approvedCases.length)return <div className="vc-story-evidence-panel" data-vtech-hud="true">
  <p className="vc-story-panel-kicker"><bdi dir="ltr">V-TECH</bdi> · המבט המקצועי</p>
  <h2 id="vtech-results-title" tabIndex={-1}>רוצים לראות<br/>את התמונה המלאה?</h2>
  <p className="vc-story-panel-body">שאלו על תיעוד מקרים ועל תוכנית העבודה עם <bdi dir="ltr">V-TECH</bdi>, כדי לבחון התאמה לקליניקה שלכם.</p>
  <ul className="vc-story-evidence-facts" aria-label="מה בוחנים בתיעוד"><li>נקודת ההתחלה</li><li>תוכנית העבודה</li><li>מועד ההערכה</li></ul>
  <a className="vc-story-panel-cta" href="#contact" data-product="v-tech-system" data-source="vtech-case-request" data-topic="cases">לבירור תיעוד והתאמה <span aria-hidden="true">←</span></a>
  <p className="vc-story-panel-note">הסרטון הוא המחשה שנוצרה באמצעות AI, ולא תיעוד של תוצאה.</p>
 </div>;
 const item=approvedCases[index];
 return <div className="vc-story-evidence-panel vc-story-evidence-approved" data-vtech-hud="true">
  <div className="vc-story-case-heading"><p className="vc-story-panel-kicker"><bdi dir="ltr">V-TECH</bdi> · תיעוד מאושר</p><h2 id="vtech-results-title" tabIndex={-1}>מקרים מהקליניקה</h2></div>
  <div className="vc-case-carousel" role="region" aria-roledescription="קרוסלה" aria-label="מקרי טיפול ב-V-TECH" tabIndex={0}
   onKeyDown={event=>{if(event.target!==event.currentTarget)return;if(event.key==='ArrowLeft'){event.preventDefault();go(1);}if(event.key==='ArrowRight'){event.preventDefault();go(-1);}}}
   onPointerDown={event=>{if(event.target instanceof Element&&event.target.closest('button,a'))return;touch.current={x:event.clientX,y:event.clientY};}}
   onPointerUp={pointerUp} onPointerCancel={()=>{touch.current=null;}}>
   <article className="vc-case" aria-label={item.title} aria-roledescription="שקופית">
    <div className="vc-case-pair" dir="ltr"><figure><img src={item.before.src} alt={item.before.alt} loading="lazy"/><figcaption>לפני</figcaption></figure><figure><img src={item.after.src} alt={item.after.alt} loading="lazy"/><figcaption>אחרי</figcaption></figure></div>
    <div className="vc-case-caption" aria-live="polite"><h3>{item.title}</h3><p>{item.program} · {item.sessions} · {item.assessment}</p>{item.details&&<details><summary>פרטי המקרה</summary><p>{item.details}</p></details>}</div>
   </article>
   {approvedCases.length>1&&<><button className="vc-case-arrow vc-case-prev" type="button" onClick={()=>go(-1)} aria-label="המקרה הקודם">›</button><button className="vc-case-arrow vc-case-next" type="button" onClick={()=>go(1)} aria-label="המקרה הבא">‹</button><div className="vc-case-dots" aria-label="בחירת מקרה">{approvedCases.map((entry,i)=><button type="button" key={entry.id} aria-label={'מקרה '+(i+1)} aria-current={i===index?'true':undefined} onClick={()=>setIndex(i)}/>)}</div></>}
  </div>
  <div className="vc-story-case-footer"><a className="vc-story-panel-cta" href="#contact" data-product="v-tech-system" data-source="vtech-case-request" data-topic="cases">לבירור תיעוד והתאמה <span aria-hidden="true">←</span></a><p className="vc-story-panel-note">סרטון הרקע הוא המחשת AI. תמונות המקרים מוצגות בנפרד עם פרטי התוכנית.</p></div>
 </div>;
}
export function VTechOfferPanel({staticProduct=false,onReveal}:{staticProduct?:boolean;onReveal?:()=>void}){return <div className="vc-story-offer-panel" data-vtech-hud="true">
 <div className="vc-story-kit-display">
  <div className="vc-story-kit-target" data-kit-product-target="true" aria-hidden="true">{staticProduct&&<img src="/assets/vtech/kit-open.webp" width="1188" height="882" className="vc-story-kit-fallback" alt="" loading="lazy"/>}</div>
  {!staticProduct&&<button className="vc-story-kit-reveal" type="button" onClick={onReveal}>גללו לפתיחת הערכה <span aria-hidden="true">↓</span><span className="vc-story-kit-reveal-direct">או לחצו להצצה פנימה</span></button>}
 </div>
 <div className="vc-story-offer-copy">
  <p className="vc-story-panel-kicker"><bdi dir="ltr">V-TECH SYSTEM</bdi> · הערכה המקצועית</p>
  <h2 id="vtech-kit-title" tabIndex={-1}>הכניסו את <bdi dir="ltr">V-TECH</bdi><br/>לקליניקה שלכם</h2>
  <dl className="vc-story-kit-contents"><div><dt><bdi dir="ltr">5 × 5 ml</bdi></dt><dd><bdi dir="ltr">V-TECH SERUM</bdi><span>אמפולות סרום</span></dd></div><div><dt><bdi dir="ltr">5 × 5 ml</bdi></dt><dd><bdi dir="ltr">V-TECH GEL MASK</bdi><span>שקיקי מסכת ג׳ל</span></dd></div></dl>
  <p className="vc-story-kit-separate">המכשור והמוצרים המשלימים אינם כלולים בערכה.</p>
  <div className="vc-story-offer-actions"><a className="vc-story-panel-cta" href="#contact" data-product="v-tech-system" data-source="vtech-kit">לקבלת מחיר <span aria-hidden="true">←</span></a><a className="vc-story-panel-secondary" href="#contact" data-product="v-tech-system" data-source="vtech-kit-training" data-topic="training">לתיאום הדרכה <span aria-hidden="true">↗</span></a></div>
  <p className="vc-story-panel-note">לשימוש מקצועי. התאמה, תנאי רכישה והדרכה מול צוות <bdi dir="ltr">MITODERM</bdi>.</p>
 </div>
 </div>;}
const trainingQuestions=[
 {question:'למי מיועדת המערכת?',answer:'V-TECH מיועדת לעבודה מקצועית בקליניקה. לשאלות על התאמה לתחום העיסוק שלכם, תנאי רכישה ואפשרויות הדרכה, פנו לצוות MITODERM.'},
 {question:'מה כדאי לברר לקראת הדרכה?',answer:'אפשר לשוחח על תפקיד הסרום ומסכת הג׳ל, בחירת אזור העבודה, שילוב המכשור והנחיות להמשך הטיפוח. תוכן ההדרכה, המתכונת, הזמינות והתנאים מאושרים מול הצוות.'},
 {question:'האם EXOCELL היא מסכת הג׳ל שבערכה?',answer:'לא. V-TECH GEL MASK היא מסכת הג׳ל הכלולה בערכת V-TECH. EXOCELL היא מסכת ביוצלולוזה נפרדת, שאפשר לשקול לסיום הטיפול בהתאם לפרוטוקול. היא אינה כלולה בערכה.'},
 {question:'כמה מפגשים נדרשים ומתי בוחנים תוצאה?',answer:'מספר המפגשים, המרווחים ומועד ההערכה נקבעים במסגרת תוכנית מקצועית ובהתאם למצב העור. בקשו את הפרוטוקול העדכני ואת התיעוד הרלוונטי; ההמחשה בעמוד אינה הבטחה לתוצאה או ללוח זמנים.'},
 {question:'מה קורה אחרי השארת פרטים?',answer:'הפנייה כוללת את המוצר שנבחר, תחום העיסוק והשאלה שלכם. בהמשך השיחה עם הצוות ניתן לברר התאמה, מחיר, תנאי רכישה ואפשרויות הדרכה. הפרטים והתנאים מסוכמים באופן אישי.'},
];
export function VTechTraining(){return <section id="vtech-training" className="vc-training vc-training-cinematic vc-training-editorial" aria-labelledby="vc-training-title">
 <div className="vc-training-film">
  <div className="vc-training-film-photo" aria-hidden="true">
   <picture>
    <source media="(max-width: 860px)" srcSet="/assets/world/vtech-consultation-mobile.webp"/>
    <img src="/assets/world/vtech-consultation.webp" alt="" loading="lazy" decoding="async"/>
   </picture>
  </div>
  <div className="vc-training-film-copy">
   <p className="vc-section-eyebrow"><bdi dir="ltr">V-TECH SYSTEM</bdi> · הדרכה וליווי מקצועי</p>
   <h2 id="vc-training-title">מכירים את המערכת.<br/><span>בונים את דרך העבודה.</span></h2>
   <p>השלב הבא לא מתחיל בעוד מצגת. הוא מתחיל בשיחה מקצועית על הקליניקה, תחום העיסוק והפרוטוקול המתאים לכם.</p>
   <a href="#contact" data-product="v-tech-system" data-source="vtech-training-intro" data-topic="training">לשיחה עם הצוות <span aria-hidden="true">←</span></a>
  </div>
  <span className="vc-training-film-label" aria-hidden="true">MITODERM <span>·</span> PROFESSIONAL CARE</span>
 </div>
 <div className="vc-training-editorial-body">
  <div className="vc-training-editorial-lead">
   <p className="vc-section-eyebrow">מהקליניקה שלכם · למערכת מתאימה</p>
   <h3>החלטה מקצועית<br/><em>מתחילה בהתאמה.</em></h3>
   <p>לפני הזמנה בודקים עם הצוות מה מתאים לניסיון שלכם, מה כולל המארז ואילו אפשרויות הדרכה קיימות. בלי הבטחות שאין מאחוריהן תיעוד.</p>
  </div>
  <div className="vc-training-editorial-points">
   <div><span aria-hidden="true" className="vc-training-editorial-rule"/><h4>התאמה לקליניקה</h4><p>אזור העבודה, הצרכים המקצועיים, ניסיון קודם והמכשור הזמין אצלכם.</p></div>
   <div><span aria-hidden="true" className="vc-training-editorial-rule"/><h4>ידע ופרוטוקול</h4><p>מבהירים את תפקיד הסרום, מסכת הג׳ל והאפשרויות לעבודה בהתאם להנחיות המקצועיות.</p></div>
   <div><span aria-hidden="true" className="vc-training-editorial-rule"/><h4>תנאים וליווי</h4><p>מקבלים מידע על המארז, מחיר, אפשרויות הדרכה והמשך הקשר עם צוות MITODERM.</p></div>
  </div>
 </div>
 <div className="vc-training-contact"><div><p className="vc-training-contact-kicker">הקליניקה שלכם. השאלות שלכם.</p><h3>מה חשוב לכם לדעת לפני שמתחילים?</h3><p>אפשר להתחיל משאלה אחת על התאמה, פרוטוקול או הדרכה.</p></div><a href="#contact" data-product="v-tech-system" data-source="vtech-training" data-topic="training">לשיחה על הדרכה <span aria-hidden="true">←</span></a></div>
 <div className="vc-faq" aria-labelledby="vc-faq-title"><div className="vc-training-faq-heading"><p className="vc-section-eyebrow">פרטים שכדאי להכיר</p><h3 id="vc-faq-title">שאלות לפני בחירה</h3></div><div>{trainingQuestions.map(item=><details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div></div>
 </section>;}
export function VTechRelated(){return <section id="vtech-related" className="vc-related" aria-labelledby="vc-related-title"><h2 id="vc-related-title">עוד מהעולם של <bdi dir="ltr">MITODERM</bdi></h2>
 <p className="vc-related-intro">לצד הסרום ומסכת הג׳ל אפשר לברר התאמה של מכשור וטיפוח משלים. כל המוצרים כאן נבחרים בנפרד; הצוות מסייע להבחין בין תוספת לתוכנית לבין פרוטוקול אחר.</p>
 {(['care','alternative'] as const).map(group=><div className={'vc-related-group vc-related-'+group} key={group}><h3>{group==='care'?'מכשור וטיפוח לצד תוכנית העבודה':'להיכרות עם פרוטוקול מקצועי נוסף'}</h3><div className="vc-related-grid">{related.filter(item=>item.group===group).map(item=><a className={'vc-related-card vc-related-card-'+item.slug} key={item.slug} href={productHref(item.slug)} data-flight="true"><div className="vc-related-image"><ProductImage slug={item.slug}/></div><div><h4><bdi dir="ltr">{item.name}</bdi></h4><p>{item.role}</p><span className="vc-related-link">לפרטי המוצר <span aria-hidden="true">←</span></span></div></a>)}</div></div>)}
 </section>;}
