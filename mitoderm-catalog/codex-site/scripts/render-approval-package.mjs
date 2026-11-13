import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../production/page-bible');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=n=>Number(n.toFixed(3)).toString();
export function readBoard(p){return JSON.parse(fs.readFileSync(path.join(root,p.approvalPackage.data),'utf8'));}
export function timedShots(p,b){
 let sec=0,vh=0;
 return b.shots.map((s,i)=>{
  const t=p.shots[i];if(s.id!==t.index)throw Error('Shot order mismatch: '+p.slug);
  const row={...s,seconds:t.seconds,scrollHeights:t.vh,start:sec,end:sec+t.seconds,scrollStart:vh,scrollEnd:vh+t.vh};
  sec=row.end;vh=row.scrollEnd;return row;
 });
}
export function renderApprovalPage(p,b,registry){
 const shots=timedShots(p,b),lines=[
 '# '+p.name+' — תסריט וערכת אישור','',
 '**מוכן לבדיקת כיוון, עם מקומות שמורים לרפרנסים חסרים. לא אושר להפקה ולא פורסם באתר.**','',
 '[פתיחת התצוגה החזותית](STORYBOARD.html) · [לוח חזותי](STORYBOARD.png) · [בדיקות](QA.md) · [נתוני התסריט](STORYBOARD.json)','',
 'נוצר מתוך REGISTRY.json ו־STORYBOARD.json. אין לערוך קובץ זה ידנית.','',
 '## היקף וסגנון','',
 b.timingNote,'',
 '8 סצנות ומקטעים 09–11. Rubik; טקסט חי בעברית מימין לשמאל. כל ניסוח חדש: **הצעה — לאישור**. אין יצירה בתשלום ואין שינוי ב־V-TECH.','',
 'צבעים: רקע '+b.palette.background+'; משטח '+b.palette.surface+'; זהב '+b.palette.accent+'; טקסט '+b.palette.text+'. '+b.palette.note,'',
 '## מקורות שנבדקו','',
 ...b.sources.map(s=>'- **'+s.id+'** — '+s.path+(s.page?' · עמוד '+s.page:'')+'. '+s.verified+(s.sha256?' SHA-256: '+s.sha256:'')),'',
 '## הדמויות וההמשכיות','',
 b.cast.note,'',...b.cast.locks.map(s=>'- '+s),'',
 'C01: קוסמטיקאית; P01: מטופלת. כרגע אין פנים מוצגות. החלפת כפפות וכלים בין שלבים היא שינוי מתוכנן, לא טעות המשכיות.','',
 '## מפת הזמן והגלילה','',
 '| סצנה | שניות עריכה | גבהי חלון | פעולה |','|---|---:|---:|---|',
 ...shots.map(s=>'| '+String(s.id).padStart(2,'0')+' | '+num(s.start)+'–'+num(s.end)+' | '+num(s.scrollStart)+'–'+num(s.scrollEnd)+' | '+s.titleHE+' |'),'',
 'יחידת גובה חלון ברישום = 100vh ב־CSS. הסכום 10.35 = 1035vh; המקטעים שמתחת לסרט אינם נכללים בו.','',
 '## שוטליסט מלא',''
 ];
 for(const s of shots)lines.push(
  '### '+String(s.id).padStart(2,'0')+' · '+s.titleHE+' · '+num(s.start)+'–'+num(s.end)+' שניות','',
  '**טקסט מסך — הצעה לאישור:** '+s.headlineHE+' / '+s.copyHE,'',
  '- **תוכן:** '+s.actionHE,'- **מצלמה:** '+s.cameraHE,'- **חלוקת הזמן:** '+s.beatsHE,
  '- **חיבור לשוט הבא:** '+s.joinHE,'- **טלפון:** '+s.mobileHE,
  '- **בדיקת קבלה:** '+s.checkHE,'- **מקור:** '+(s.refs.join(', ')||'חסר — חלון ריק בלבד')+' · '+s.statusHE,''
 );
 lines.push('## מקטעי העמוד שמתחת לסרט','');
 for(const l of b.lower){
  lines.push('### '+l.id+' · '+l.title,'');
  if(l.headline)lines.push('**'+l.headline+'**','',l.copy,'');
  if(l.items)lines.push(...l.items.map(x=>'- '+x),'',l.cta,'',l.notes,'');
  if(l.faq)for(const f of l.faq)lines.push('**'+f.q+'**','',f.a,'');
  if(l.related)lines.push(...l.related.map(x=>'- **'+x.name+'** — '+x.reason),'',l.provider,'',l.community,'',
   '**טופס:** '+l.form.title+'. '+l.form.fields.join(' · ')+'. מוצר קבוע: '+l.form.product+'. כפתור: '+l.form.button+'.',l.form.note,'');
 }
 lines.push('## תכולה לפי תמליל הקטלוג','',...b.kit.map(x=>'- '+x.name+' — '+x.quantity),'',
 'התצלום מציג שלושה סוגי בקבוקים בלבד. אין יצירת תמונת אחת־עשרה יחידות או פתיחת קופסה בלי חומר מקור.','',
 '## הצעות ערך','',...b.claims.map(x=>'- **'+x.copy+'** — '+x.state+'; מקור '+x.basis+'. '+x.note),'',
 '## בדיקת רפרנסים','',
 '| מזהה | חומר | מצב | הנדרש |','|---|---|---|---|',
 ...b.references.map(x=>'| '+x.id+' | '+x.label+' | '+({verified:'נבדק',verified_for_layout:'נבדק לפריסה',missing:'חסר',pending:'ממתין לאישור'}[x.state])+' | '+x.need+' |'),'',
 '## פערי מקורות','',...b.conflicts.map(x=>'- '+x),'',
 '## שערי אישור','',...b.approvalChecklist.map(x=>'- [ ] '+x),'',
 '## מימוש עתידי ונגישות','',
 '- טקסטים וממשק נשארים HTML; שמות מוצרים וזמנים מבודדים בכיוון משמאל לימין.',
 '- בדוגמה: כפתור מהמסך הראשון מוביל לטופס הדגמה; אין איסוף מידע, שליחה או שמירה.',
 '- ללא JavaScript כל שמונה הסצנות וכל המקטעים נשארים קריאים. בהעדפת תנועה מופחתת אין ניגון אוטומטי.',
 '- דגימת המצלמה בתצוגה היא המחשת קצב בלבד. היא אינה וידאו טיפולי ואינה מחליפה צילום מאושר.',
 '- לפני הפקה: צילום 16:9 וצילום 9:16 מתוכננים בנפרד; אין חיתוך אוטומטי של פני דמויות או אריזה.',
 '- אין פרטי מטופלות, תמונות אנשים או הרשאות שימוש במאגר הציבורי; רק מזהי סטטוס.',
 ''
 );
 return lines.join('\n')+'\n';
}
function product(visual){
 if(visual==='pack'||visual==='kit')return '<div class="pack-stage"><img class="pack" src="assets/NAD.png" width="795" height="489" alt="צילום המקור של ערכת EXO-NAD: קופסה זהובה ושלושה סוגי בקבוקים"><span class="photo-note">תצלום מקור · NAD.png</span></div>';
 if(['peel','normalizer','serum'].includes(visual))return '<div class="bottle-stage"><div class="bottle '+visual+'"><img src="assets/NAD.png" width="795" height="489" alt="'+esc({peel:'EXO BIPHASIC PEEL — בקבוק שקוף עם מכסה זהוב',normalizer:'pH NORMALIZER — בקבוקון ענברי',serum:'LONGEVITY SERUM — בקבוקון טורקיז'}[visual])+'"></div><span class="photo-note">פרט מהתצלום המקורי</span></div>';
 return '';
}
function placeholder(s){
 if(s.visual==='evidence')return '<div class="evidence-slots"><div>לפני<span>תיעוד מאומת חסר</span></div><div>אחרי<span>תיעוד מאומת חסר</span></div></div><p class="hold-note">אין כאן תוצאת טיפול. החלונות שמורים למקרה אמיתי בלבד.</p>';
 return '<div class="cast-slots"><div><bdi>C01</bdi><span>קוסמטיקאית</span></div><i aria-hidden="true">↔</i><div><bdi>P01</bdi><span>מטופלת</span></div></div><p class="hold-note">מקום לצילום מאושר · אותה זוגת דמויות לאורך הסיפור</p>';
}
function visual(s){
 const real=product(s.visual);
 if(real)return real+(['pack','kit'].includes(s.visual)?'':'<div class="action-hold"><span>מקום לצילום הפעולה</span><bdi>C01 + P01</bdi><small>'+esc(s.visual==='normalizer'?'נטרול ← שטיפה ← ייבוש':s.visual==='peel'?'ניעור ← יישום מקצועי':'יישום ← ספיגה · ללא שטיפה')+'</small></div>');
 return placeholder(s);
}
export function renderApprovalHtml(p,b,registry){
 const shots=timedShots(p,b);
 const cards=shots.map(s=>'<article class="shot" id="s'+s.id+'"><header class="shot-meta"><span>סצנה '+String(s.id).padStart(2,'0')+' / 08</span><bdi>'+num(s.start)+'–'+num(s.end)+' s · '+num(s.scrollHeights)+' H</bdi></header><div class="shot-picture '+s.visual+'">'+visual(s)+'</div><div class="shot-copy"><span class="eyebrow">'+esc(s.titleHE)+'</span><h3 dir="auto">'+esc(s.headlineHE)+'</h3><p>'+esc(s.copyHE)+'</p><p class="status">'+esc(s.statusHE)+'</p><details><summary>בימוי, חיבור ומקור</summary><p>'+esc(s.actionHE)+'</p><p><strong>מצלמה:</strong> '+esc(s.cameraHE)+'</p><p><strong>חיבור:</strong> '+esc(s.joinHE)+'</p><p><strong>בדיקה:</strong> '+esc(s.checkHE)+'</p><p><strong>טלפון:</strong> '+esc(s.mobileHE)+'</p><p class="source">מקור: <bdi>'+esc(s.refs.join(' · ')||'CASE01 — חסר')+'</bdi></p></details></div></article>').join('\n');
 const professional=b.lower[0],faq=b.lower[1],last=b.lower[2];
 const lower='<section class="professional lower-section" id="professional"><div class="section-top"><span>09 / לקליניקה שלך</span><span>הצעה — לאישור</span></div><div class="offer-grid"><div><h2>'+esc(professional.headline)+'</h2><p>'+esc(professional.copy)+'</p><a class="button" href="#contact">'+esc(professional.cta)+'</a></div><ol>'+professional.items.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ol></div><p class="micro">'+esc(professional.notes)+'</p></section>'+
 '<section class="lower-section faq" id="faq"><div class="section-top"><span>10 / שאלות לפני שמתחילים</span><span>טקסט חי · עברית</span></div><h2>'+esc(faq.title)+'</h2>'+faq.faq.map(f=>'<details><summary>'+esc(f.q)+'</summary><p>'+esc(f.a)+'</p></details>').join('')+'</section>'+
 '<section class="lower-section related" id="continuation"><div class="section-top"><span>11 / ממשיכות מכאן</span><span>מוצרים נפרדים</span></div><h2>'+esc(last.headline)+'</h2><p>'+esc(last.copy)+'</p><div class="related-grid">'+last.related.map(r=>'<article><img src="../../../../public/assets/products/'+r.slug+'.webp" alt="'+esc(r.name)+'" width="400" height="300"><h3><bdi>'+esc(r.name)+'</bdi></h3><p>'+esc(r.reason)+'</p></article>').join('')+'</div><div class="support-grid"><p>'+esc(last.provider)+'</p><p>'+esc(last.community)+'</p></div></section>'+
 '<section class="lower-section contact" id="contact"><span class="eyebrow">הצעה — לאישור</span><h2>'+esc(last.form.title)+'</h2><p>'+esc(last.form.note)+'</p><fieldset disabled aria-label="טופס הדגמה בלבד"><legend>הדגמת טופס · EXO-NAD</legend><div class="form-grid">'+last.form.fields.map((x,i)=>'<label>'+esc(x)+'<input id="field-'+i+'" type="'+(i===1?'tel':'text')+'" placeholder="'+esc(x)+'" autocomplete="off"></label>').join('')+'</div><button type="button">בקשת פרטים · הדגמה</button></fieldset></section>';
 const references=b.references.map(r=>'<li><bdi>'+r.id+'</bdi><div><strong>'+esc(r.label)+'</strong><p>'+esc(r.need)+'</p></div><span class="ref-state">'+esc({verified:'נבדק',verified_for_layout:'נבדק לפריסה',missing:'חסר',pending:'לאישור'}[r.state])+'</span></li>').join('');
 const timeline=shots.map(s=>'<a href="#s'+s.id+'" style="flex:'+s.seconds+'" title="'+esc(s.titleHE)+'">'+String(s.id).padStart(2,'0')+'</a>').join('');
 const payload=shots.map(s=>({id:s.id,title:s.titleHE,headline:s.headlineHE,copy:s.copyHE,start:s.start,end:s.end,html:visual(s),visual:s.visual}));
 return fs.readFileSync(path.join(root,'templates/approval.html'),'utf8')
 .replace('@@TITLE@@',esc(b.title)).replace('@@SUBTITLE@@',esc(b.subtitle))
 .replace('@@CARDS@@',cards).replace('@@LOWER@@',lower).replace('@@REFERENCES@@',references)
 .replace('@@TIMELINE@@',timeline).replace('@@FIRST_VISUAL@@',visual(shots[0]))
 .replace('@@KIT@@',b.kit.map(k=>'<div><bdi>'+k.name+'</bdi><span>'+k.quantity+'</span></div>').join(''))
 .replace('@@DATA@@',JSON.stringify(payload).replace(/</g,'\\u003c'))
 .replace('@@CSS@@',fs.readFileSync(path.join(root,'templates/approval.css'),'utf8'));
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const registry=JSON.parse(fs.readFileSync(path.join(root,'REGISTRY.json'),'utf8'));
 for(const p of registry.pages.filter(p=>p.approvalPackage)){
  const b=readBoard(p),out=path.join(root,'pages',p.slug,'STORYBOARD.html'),expected=renderApprovalHtml(p,b,registry);
  if(process.argv.includes('--check')){
   if(!fs.existsSync(out)||fs.readFileSync(out,'utf8')!==expected)throw Error('Stale storyboard: '+p.slug);
  }else fs.writeFileSync(out,expected);
 }
 console.log('Approval package HTML: OK');
}
