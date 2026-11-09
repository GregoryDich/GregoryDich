import {useState,type KeyboardEvent} from 'react';
import {products,productHref} from '../data';
import {Chapter,ProductImage} from '../shared';
const groups=[
 {id:'face',label:'טיפולי פנים',slugs:['v-tech-system','exo-nad','exocell-mask','micro-boost-10','mitotech-cell-booster']},
 {id:'scalp',label:'קרקפת ושיער',slugs:['exosignal-hair','exosignal-spray','mitoscan']},
 {id:'homecare',label:'טיפוח ביתי',slugs:['exotech-gel','cell-renew-1-5','cellular-age-defense-2-5','derma-recovery-cream','exosignal-spray']},
 {id:'devices',label:'מכשור מקצועי',slugs:['mitopen','mitoscan']}
];
const roles:Record<string,string>={
 'v-tech-system':'סרום ומסכת ג׳ל לעבודה מקצועית על עור הפנים',
 'exo-nad':'מערכת פילינג מקצועית בשלושה שלבים',
 'exocell-mask':'מסכת ביו-צלולוז לטיפוח משלים',
 'micro-boost-10':'BIOSPICULE לטיפול מקצועי בקליניקה',
 'mitotech-cell-booster':'אבקה ואמפולת בוסטר במערכת דו-רכיבית',
 'exosignal-hair':'אמפולות לתוכנית מקצועית לקרקפת',
 'exosignal-spray':'טיפוח ביתי לקרקפת ולשיער',
 'exotech-gel':'לחות וטיפוח משלים בין הביקורים',
 'cell-renew-1-5':'סרום BIOSPICULE לטיפוח ביתי',
 'cellular-age-defense-2-5':'סרום BIOSPICULE לטיפוח ביתי ממוקד',
 'derma-recovery-cream':'לחות ותמיכה במחסום העור',
 'mitopen':'עט מיקרונידלינג לעבודה מקצועית',
 'mitoscan':'מצלמה לסקירת הקרקפת והשיער'
};
export function ProductSelector(){
 const [active,setActive]=useState(0);const group=groups[active];
 function keyboard(event:KeyboardEvent<HTMLButtonElement>,index:number){
  let next=index;if(event.key==='ArrowLeft')next=(index+1)%groups.length;else if(event.key==='ArrowRight')next=(index+groups.length-1)%groups.length;else if(event.key==='Home')next=0;else if(event.key==='End')next=groups.length-1;else return;
  event.preventDefault();setActive(next);event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
 }
 return <section id="products" className="product-discovery"><div className="discovery-heading"><h2>מוצאים את המוצר המתאים</h2><p>בחרו תחום והכירו את המוצרים בהקשר של העבודה שלכם.</p></div>
  <div className="discovery-tabs" role="tablist" aria-label="תחום עניין">{groups.map((item,index)=><button id={'domain-'+item.id} key={item.id} type="button" role="tab" aria-selected={active===index} aria-controls={'domain-panel-'+item.id} tabIndex={active===index?0:-1} onClick={()=>setActive(index)} onKeyDown={event=>keyboard(event,index)}>{item.label}</button>)}</div>
  <div className="discovery-results" id={'domain-panel-'+group.id} role="tabpanel" aria-labelledby={'domain-'+group.id} tabIndex={0}>
   {group.slugs.map(slug=>{const product=products.find(item=>item.slug===slug)!;return <a className="discovery-product" key={slug} href={productHref(slug)}><span className="discovery-thumb"><ProductImage slug={slug}/></span><span className="discovery-product-copy"><bdi dir="ltr">{product.name}</bdi><span>{roles[slug]}</span></span><span className="discovery-arrow" aria-hidden="true">←</span></a>;})}
  </div><a href="/catalog" className="discovery-all">לכל המוצרים <span aria-hidden="true">←</span></a>
 </section>;
}
export function VTechInvitation(){return <Chapter id="vtech" line="V-TECH FACE" className="vtech-invitation"><div className="invitation-visual"><img src="/assets/vtech/system-kit.webp" width={1600} height={1468} alt="ערכת V-TECH, סרום ומסכת ג׳ל" loading="lazy" decoding="async"/></div><div className="invitation-copy"><bdi dir="ltr">V-TECH SYSTEM</bdi><h2>שני מרכיבים.<br/>מחשבה אחת על העור.</h2><p>הכירו את הסרום ואת מסכת הג׳ל במערכת מקצועית לטיפולי פנים, צוואר ומחשוף.</p><a href="/products/v-tech-system" className="invitation-link">להכיר את V-TECH <span aria-hidden="true">←</span></a></div></Chapter>;}
export function SupportSection(){return <section id="support" className="support-section"><div className="support-intro"><h2>מוצר טוב צריך גם ליווי</h2><p>הקשר עם MITODERM ממשיך גם אחרי בחירת המוצר.</p><a href="#contact" data-topic="training" data-source="home-support" className="support-link">מידע על הדרכה <span aria-hidden="true">↗</span></a></div><div className="support-rows"><article><h3>בחירה שמתאימה לקליניקה</h3><p>שיחה על תחום העבודה, המוצרים והצרכים של הצוות שלכם.</p></article><article><h3>ידע ופרוטוקולים</h3><p>מידע מקצועי ואפשרויות הדרכה לשילוב המוצרים בעבודה.</p></article><article><h3>קשר עם הצוות</h3><p>כתובת לשאלות מקצועיות ולמידע על המפגשים של MITODERM.</p></article></div></section>;}
