import {useId,useRef,useState,type FormEvent} from 'react';
import {products,contact} from '../data';

const professionLabels=[['cosmetologist','קוסמטיקאי/ת'],['doctor','רופא/ה'],['nurse','אח/ות'],['clinic_owner','בעל/ת קליניקה'],['other','תחום מקצועי אחר']];
export type LeadDraft={name:string;phone:string;profession:string;productSlug:string;comment:string;privacyConsent:boolean};
type Props={productSlug?:string;sourceBlock?:string;initialComment?:string;initialDraft?:LeadDraft;onDraftChange?:(draft:LeadDraft)=>void;onSuccess?:()=>void};
type Result={ok:boolean;code:string;id?:string;fields?:Record<string,string>};
export function LeadForm({productSlug='unsure',sourceBlock='contact',initialComment='',initialDraft,onDraftChange,onSuccess}:Props){
 const prefix=useId();
 const [values,setValues]=useState(()=>({name:initialDraft?.name??'',phone:initialDraft?.phone??'',profession:initialDraft?.profession??'',productSlug:initialDraft?.productSlug??productSlug,comment:initialDraft?.comment??initialComment,privacyConsent:initialDraft?.privacyConsent??false,website:''}));
 const [status,setStatus]=useState<'idle'|'sending'|'error'|'success'>('idle');
 const [message,setMessage]=useState('');
 const [fields,setFields]=useState<Record<string,string>>({});
 const [receipt,setReceipt]=useState('');
 const requestId=useRef<string|null>(null);
 const formRef=useRef<HTMLFormElement>(null);
 function update<K extends keyof typeof values>(key:K,value:(typeof values)[K]){
  const next={...values,[key]:value};
  if(key==='productSlug'&&value!==values.productSlug)next.privacyConsent=false;
  setValues(next);
  // The dialog owns this draft only for its current mount. Never store the
  // honeypot or copy consent to a different selected product.
  const {website:discarded,...draft}=next;
  void discarded;onDraftChange?.(draft);
  requestId.current=null;setFields(current=>({...current,[key]:''}));
  if(status==='error')setStatus('idle');
 }
 const selected=products.find(product=>product.slug===values.productSlug);
 const question=values.comment.trim();
 const whatsapp=contact.whatsapp_url+'?text='+encodeURIComponent('שלום, אשמח לקבל מידע מקצועי והצעה לקליניקה בנושא '+(selected?.name??'מוצרי MITODERM')+'.'+(question?'\n\n'+question:''));
 async function submit(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(status==='sending')return;
  setStatus('sending');setMessage('');setFields({});
  requestId.current??=crypto.randomUUID();
  const controller=new AbortController();const timeout=window.setTimeout(()=>controller.abort(),18000);
  try{
   const response=await fetch('/api/leads',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',signal:controller.signal,body:JSON.stringify({...values,requestId:requestId.current,locale:'he',sourceBlock})});
   const result=await response.json() as Result;
   if(!response.ok||!result.ok){
    setFields(result.fields??{});
    setMessage(result.code==='rate_limited'?'התקבלו מספר פניות בזמן קצר. נסו שוב מאוחר יותר או פנו ב-WhatsApp.':result.code==='validation_error'?'בדקו את הפרטים המסומנים ונסו שוב.':'הפנייה לא נשלחה. הפרטים נשמרו בטופס. אפשר לנסות שוב או לפנות ב-WhatsApp.');
    setStatus('error');
    const invalid=Object.keys(result.fields??{})[0];
    if(invalid)window.setTimeout(()=>{const input=formRef.current?.elements.namedItem(invalid);if(input instanceof HTMLElement)input.focus();},0);
    return;
   }
   setReceipt((result.id??requestId.current).slice(0,8).toUpperCase());setStatus('success');onSuccess?.();
  }catch{
   setStatus('error');setMessage('לא התקבל אישור לשליחה. הפרטים נשמרו בטופס ואפשר לנסות שוב.');
  }finally{window.clearTimeout(timeout);}
 }
 function fieldError(name:string){return fields[name]?<span className="lead-field-error" id={prefix+'-'+name+'-error'}>{name==='phone'?'בדקו את מספר הטלפון.':name==='privacyConsent'?'יש לאשר יצירת קשר בנוגע לפנייה.':'יש לבדוק את השדה.'}</span>:null;}
 if(status==='success')return <div className="lead-success" role="status" tabIndex={-1}>
  <span className="lead-success-mark" aria-hidden="true">✓</span><h3>הפנייה התקבלה</h3><p>תודה שפניתם ל-MITODERM.</p>{selected&&<p>הבקשה נשמרה בנושא <bdi dir="ltr">{selected.name}</bdi>.</p>}<p>לשיחה ישירה עם הצוות אפשר להמשיך ב-WhatsApp.</p><p className="lead-receipt">מספר פנייה: <bdi dir="ltr">{receipt}</bdi></p><a className="lead-whatsapp" href={whatsapp} target="_blank" rel="noopener noreferrer">להמשך שיחה ב-WhatsApp <span aria-hidden="true">↗</span></a>
 </div>;
 return <form className="lead-form" ref={formRef} onSubmit={submit}>
  <div className="lead-fields">
   <label htmlFor={prefix+'-name'}><span>שם מלא</span><input id={prefix+'-name'} name="name" autoComplete="name" value={values.name} onChange={event=>update('name',event.target.value)} minLength={2} maxLength={100} required aria-invalid={!!fields.name} aria-describedby={fields.name?prefix+'-name-error':undefined}/>{fieldError('name')}</label>
   <label htmlFor={prefix+'-phone'}><span>טלפון לחזרה</span><input id={prefix+'-phone'} name="phone" type="tel" autoComplete="tel" dir="ltr" value={values.phone} onChange={event=>update('phone',event.target.value)} maxLength={32} required aria-invalid={!!fields.phone} aria-describedby={fields.phone?prefix+'-phone-error':undefined}/>{fieldError('phone')}</label>
   <label htmlFor={prefix+'-profession'}><span>תחום העיסוק</span><select id={prefix+'-profession'} name="profession" value={values.profession} onChange={event=>update('profession',event.target.value)} required aria-invalid={!!fields.profession}><option value="">בחרו תחום</option>{professionLabels.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>{fieldError('profession')}</label>
   {productSlug!=='unsure'&&selected?<div className="lead-product-context"><span>המוצר שנבחר</span><bdi dir="ltr">{selected.name}</bdi><input type="hidden" name="productSlug" value={values.productSlug}/></div>:<label htmlFor={prefix+'-product'}><span>המוצר שמעניין אותי</span><select id={prefix+'-product'} name="productSlug" value={values.productSlug} onChange={event=>update('productSlug',event.target.value)}><option value="unsure">עדיין לא בחרתי</option>{products.map(product=><option key={product.slug} value={product.slug}>{product.name}</option>)}</select>{fieldError('productSlug')}</label>}
   <label className="lead-wide" htmlFor={prefix+'-comment'}><span>מה תרצו לדעת? <small>(לא חובה)</small></span><textarea id={prefix+'-comment'} name="comment" rows={2} maxLength={1000} value={values.comment} onChange={event=>update('comment',event.target.value)}/>{fieldError('comment')}</label>
  </div>
  <div className="lead-honeypot" aria-hidden="true"><label>Website<input name="website" tabIndex={-1} autoComplete="off" value={values.website} onChange={event=>update('website',event.target.value)}/></label></div>
  <label className="lead-consent"><input type="checkbox" name="privacyConsent" checked={values.privacyConsent} onChange={event=>update('privacyConsent',event.target.checked)} required/><span>אני מאשר/ת ליצור איתי קשר בנוגע לפנייה זו, בהתאם ל<a href="/privacy" target="_blank" rel="noopener noreferrer">מדיניות הפרטיות</a>.</span></label>
  {fieldError('privacyConsent')}
  <p className="lead-professional-note">מיועד לאנשי מקצוע. לפרטים על תנאי רכישה והדרכה פנו לצוות MITODERM.</p>
  {status==='error'&&<p className="lead-error" role="alert">{message}</p>}
  <button type="submit" className="lead-submit" disabled={status==='sending'} aria-busy={status==='sending'}>{status==='sending'?'שולחים את הפנייה…':'שליחת פנייה'}<span aria-hidden="true">{status==='sending'?'…':'←'}</span></button>
  <a className="lead-whatsapp" href={whatsapp} target="_blank" rel="noopener noreferrer">לפנייה ב-WhatsApp <span aria-hidden="true">↗</span></a>
 </form>;
}
