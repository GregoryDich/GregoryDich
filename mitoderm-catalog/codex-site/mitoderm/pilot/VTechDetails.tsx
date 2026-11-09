import {mediaUrl} from '../media';
import {useRef,useState,type PointerEvent} from 'react';
import {ProductImage} from '../shared';
import {contact,productHref} from '../data';
import {vtechCases} from './case-data';

const approvedCases=vtechCases.filter(item=>item.publicationApproved&&item.sourceVerified&&item.product==='v-tech-system');
const related=[
 {slug:'mitopen',name:'MITOPEN',role:'מכשור המיקרונידלינג שמופיע בהמחשה. לעבודה לפי הכשרה ופרוטוקול.',group:'care'},
 {slug:'exocell-mask',name:'EXOCELL MASK',role:'מסכת ביוצלולוזה כאפשרות לסיום הטיפול, בהתאם לפרוטוקול. נבחרת בנפרד ממסכת הג׳ל.',group:'care'},
 {slug:'derma-recovery-cream',name:'DERMA RECOVERY CREAM',role:'קרם כאפשרות לטיפוח משלים לאחר הטיפול, לפי התאמה מקצועית.',group:'care'},
 {slug:'exotech-gel',name:'EXOTECH GEL',role:'טיפוח ביתי משלים. ההתאמה נעשית בנפרד מתוכנית העבודה עם V-TECH.',group:'care'},
 {slug:'micro-boost-10',name:'MICRO BOOST 10%',role:'מערכת BIOSPICULE מקצועית לפרוטוקול נוסף. אינה חלק מהערכה או מרצף ההמחשה שמעל.',group:'alternative'}
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
  <div className="vc-results-intro"><p className="vc-section-eyebrow">מההמחשה להחלטה מקצועית</p><h2 id="vc-results-title">תיעוד ותיאום ציפיות</h2><p>מראה הקמטוטים ומרקם העור הם הבקשה בסיפור. כדי להעריך תוצאה, בוחנים מקרה אמיתי עם נקודת התחלה, תוכנית עבודה וזמן הערכה מוגדר.</p></div>
  <div className="vc-evidence-grid"><article><span aria-hidden="true">01</span><h3>נקודת ההתחלה</h3><p>בקשת המטופלת, מצב העור ואזור העבודה לפני תחילת התוכנית.</p></article><article><span aria-hidden="true">02</span><h3>תוכנית העבודה</h3><p>המוצרים והפעולות שנבחרו, מספר המפגשים וההקשר המקצועי.</p></article><article><span aria-hidden="true">03</span><h3>תנאי ההשוואה</h3><p>מועד התיעוד, זווית וצילום בתנאים דומים, כדי להבין מה באמת מוצג.</p></article></div>
  <div className="vc-case-request"><div><h3>נבדוק מה רלוונטי לקליניקה שלכם</h3><p>בקשו מהצוות תיעוד זמין ופרטים על יישום V-TECH. השיחה מאפשרת לבחון את ההתאמה והציפיות לפני בחירת תוכנית.</p><p className="vc-case-availability">בעמוד מוצגת המחשת טיפול. תמונות לפני ואחרי מאושרות לפרסום אינן מוצגות כאן בשלב זה.</p></div><a href="#contact" data-product="v-tech-system" data-source="vtech-case-request" data-topic="cases">לבקשת תיעוד ופרטים <span aria-hidden="true">←</span></a></div>
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
  <p className="vc-kit-separate">המכשור והמוצרים המשלימים נבחרים בנפרד מהערכה.</p>
 </div>
 <div className="vc-offer-copy"><h2 id="vc-offer-title">הכניסו את <bdi dir="ltr">V-TECH</bdi><br/>לקליניקה שלכם</h2><p>הכירו את המערכת, בדקו התאמה לעבודה שלכם וקבלו תנאים מקצועיים מהצוות.</p>
  <dl className="vc-decision-facts"><div><dt>אזורי עבודה</dt><dd>פנים, צוואר ומחשוף, לפי התאמה מקצועית.</dd></div><div><dt>המערכת</dt><dd>סרום ומסכת ג׳ל במסגרת פרוטוקול מקצועי. בהמחשה מתמקדים בלחי.</dd></div><div><dt>לפני שמתחילים</dt><dd>מבררים הכשרה, פרוטוקול עדכני ואפשרויות הדרכה עם צוות MITODERM.</dd></div></dl>
  <div className="vc-offer-actions"><a className="vc-offer-price" href="#contact" data-product="v-tech-system" data-source="vtech-kit">לקבלת מחיר <span aria-hidden="true">←</span></a><a className="vc-offer-training" href="#contact" data-product="v-tech-system" data-source="vtech-kit-training" data-topic="training">לתיאום הדרכה <span aria-hidden="true">↗</span></a></div>
  <p className="vc-professional-note">לשימוש מקצועי. לפרטים על התאמה, תנאי רכישה והדרכה פנו לצוות MITODERM.</p>
  <details className="vc-formula"><summary>מרכיבי המערכת <span aria-hidden="true">+</span></summary><div><h3>הסרום</h3><p>אקסוזומים סינתטיים, PDRN, פפטידים ביומימטיים ותמצית תאי גזע של תפוח, לפי תיאור המוצר בקטלוג.</p><h3>מסכת הג׳ל</h3><p>PDRN, פפטידים, חומצה היאלורונית, אלוורה ורכיבים משלימים המתוארים בקטלוג.</p><a href="#contact" data-product="v-tech-system" data-source="vtech-formula" data-topic="protocol">לפרטים על הפרוטוקול ←</a></div></details>
  <a className="vc-direct-contact" href={contact.whatsapp_url+'?text='+encodeURIComponent('שלום, אשמח לקבל מחיר ומידע מקצועי על V-TECH SYSTEM.')} target="_blank" rel="noopener noreferrer">WhatsApp <bdi dir="ltr">{contact.phone}</bdi></a>
 </div>
 </section>;}
const trainingQuestions=[
 {question:'למי מיועדת המערכת?',answer:'V-TECH מיועדת לעבודה מקצועית בקליניקה. לשאלות על התאמה לתחום העיסוק שלכם, תנאי רכישה ואפשרויות הדרכה, פנו לצוות MITODERM.'},
 {question:'מה כדאי לברר לקראת הדרכה?',answer:'אפשר לשוחח על תפקיד הסרום ומסכת הג׳ל, בחירת אזור העבודה, שילוב המכשור והנחיות להמשך הטיפוח. תוכן ההדרכה, המתכונת, הזמינות והתנאים מאושרים מול הצוות.'},
 {question:'האם EXOCELL היא מסכת הג׳ל שבערכה?',answer:'לא. V-TECH GEL MASK היא מסכת הג׳ל הכלולה בערכת V-TECH. EXOCELL היא מסכת ביוצלולוזה נפרדת, שאפשר לשקול לסיום הטיפול בהתאם לפרוטוקול. היא אינה כלולה בערכה.'},
 {question:'כמה מפגשים נדרשים ומתי בוחנים תוצאה?',answer:'מספר המפגשים, המרווחים ומועד ההערכה נקבעים במסגרת תוכנית מקצועית ובהתאם למצב העור. בקשו את הפרוטוקול העדכני ואת התיעוד הרלוונטי; ההמחשה בעמוד אינה הבטחה לתוצאה או ללוח זמנים.'},
 {question:'מה קורה אחרי השארת פרטים?',answer:'הפנייה כוללת את המוצר שנבחר, תחום העיסוק והשאלה שלכם. בהמשך השיחה עם הצוות ניתן לברר התאמה, מחיר, תנאי רכישה ואפשרויות הדרכה. הפרטים והתנאים מסוכמים באופן אישי.'},
];
export function VTechTraining(){return <section id="vtech-training" className="vc-training" aria-labelledby="vc-training-title">
 <div className="vc-training-heading"><div><p className="vc-section-eyebrow">ידע מקצועי, לפני שמתחילים</p><h2 id="vc-training-title">מכירים את המערכת.<br/>בונים את דרך העבודה.</h2></div><p>הצעד הבא הוא שיחה על הקליניקה, הניסיון והמטרה שלכם. כך אפשר לברר את הפרוטוקול ואת ההדרכה המתאימה לפני תחילת העבודה.</p></div>
 <ol className="vc-training-steps"><li><span aria-hidden="true">01</span><h3>משאירים פנייה ממוקדת</h3><p>מציינים את תחום העיסוק ומה תרצו לדעת על V-TECH, המכשור או ההדרכה.</p></li><li><span aria-hidden="true">02</span><h3>מבררים התאמה מקצועית</h3><p>בשיחה עם הצוות מבררים ניסיון, הכשרה ותוכנית עבודה רלוונטית לקליניקה.</p></li><li><span aria-hidden="true">03</span><h3>מסכמים את הפרטים</h3><p>תכולת הערכה, תנאי הרכישה ואפשרויות ההדרכה מוצגים ומאושרים מול הצוות.</p></li></ol>
 <div className="vc-training-contact"><div><h3>מה חשוב לכם לדעת לפני שמתחילים?</h3><p>אפשר להתחיל משאלה אחת על התאמה, פרוטוקול או הדרכה.</p></div><a href="#contact" data-product="v-tech-system" data-source="vtech-training" data-topic="training">לשיחה על הדרכה <span aria-hidden="true">←</span></a></div>
 <div className="vc-faq" aria-labelledby="vc-faq-title"><h3 id="vc-faq-title">שאלות לפני בחירה</h3><div>{trainingQuestions.map(item=><details key={item.question}><summary>{item.question}<span aria-hidden="true">+</span></summary><p>{item.answer}</p></details>)}</div></div>
 </section>;}
export function VTechRelated(){return <section id="vtech-related" className="vc-related" aria-labelledby="vc-related-title"><h2 id="vc-related-title">עוד מהעולם של <bdi dir="ltr">MITODERM</bdi></h2>
 <p className="vc-related-intro">לצד הסרום ומסכת הג׳ל אפשר לברר התאמה של מכשור וטיפוח משלים. כל המוצרים כאן נבחרים בנפרד; הצוות מסייע להבחין בין תוספת לתוכנית לבין פרוטוקול אחר.</p>
 {(['care','alternative'] as const).map(group=><div className={'vc-related-group vc-related-'+group} key={group}><h3>{group==='care'?'מכשור וטיפוח לצד תוכנית העבודה':'להיכרות עם פרוטוקול מקצועי נוסף'}</h3><div className="vc-related-grid">{related.filter(item=>item.group===group).map(item=><a className={'vc-related-card vc-related-card-'+item.slug} key={item.slug} href={productHref(item.slug)} data-flight="true"><div className="vc-related-image"><ProductImage slug={item.slug}/></div><div><h4><bdi dir="ltr">{item.name}</bdi></h4><p>{item.role}</p><span className="vc-related-link">לפרטי המוצר <span aria-hidden="true">←</span></span></div></a>)}</div></div>)}
 </section>;}
