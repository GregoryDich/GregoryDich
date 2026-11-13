const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'../production/page-bible'),registry=JSON.parse(fs.readFileSync(path.join(root,'REGISTRY.json'))),p=registry.pages.find(p=>p.slug==='exo-nad'),dir=path.join(root,'pages/exo-nad'),b=JSON.parse(fs.readFileSync(path.join(dir,'STORYBOARD.json')));
assert.equal(p.shots.length,8);assert.equal(p.palette,'vm_nad');
assert.equal(p.shots.reduce((a,s)=>a+s.seconds,0),36.5);
assert.equal(Number(p.shots.reduce((a,s)=>a+s.vh,0).toFixed(2)),10.35);
assert.deepEqual(b.shots.filter(s=>s.phase).map(s=>s.phase),['EXO BIPHASIC PEEL','pH NORMALIZER','LONGEVITY SERUM']);
assert.equal(b.cast.clinicianId,'C01');assert.equal(b.cast.patientId,'P01');assert.equal(b.cast.status,'awaiting_user_images');
assert.equal(b.shots[6].visual,'evidence');assert.equal(b.references.find(x=>x.id==='CASE01').state,'missing');
assert.equal(p.approvalPackage.deployed,false);assert.equal(p.approvalPackage.paidGenerationUsed,false);
assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,'assets/NAD.png'))).digest('hex'),b.sources.find(x=>x.id==='PACK').sha256);
for(const f of ['PAGE.md','STORYBOARD.html'])assert(!/[Ѐ-ӿ]/.test(fs.readFileSync(path.join(dir,f),'utf8')),f+' contains Cyrillic');
const report={date:'2026-11-13',structural:'pass',viewports:[],interactions:{},limits:['No approved people, procedure footage, or before/after evidence.','Source photograph is 795×489; no HD detail invented.','Language and clinical/commercial approval pending.']};
async function run(){
 const {chromium}=require(process.env.MITODERM_PLAYWRIGHT_MODULE||'playwright');
 const browser=await chromium.launch({executablePath:process.env.MITODERM_CHROME||undefined,headless:true});
 const page=await browser.newPage();const errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>errors.push(r.url()+': '+r.failure()?.errorText));
 for(const [width,height] of [[1280,720],[1440,900],[1920,1080],[390,844]]){
  await page.setViewportSize({width,height});await page.goto(pathToFileURL(path.join(dir,'STORYBOARD.html')).href);await page.evaluate(()=>document.fonts.ready);
  const result=await page.evaluate(()=>{
   const out=[...document.querySelectorAll('body *')].filter(e=>!e.closest('script,style,details:not([open])')&&!e.matches('.bottle img,.skip')).filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&(r.left< -1||r.right>innerWidth+1)}).map(e=>e.tagName+'.'+e.className);
   return {scrollWidth:document.documentElement.scrollWidth,viewport:innerWidth,overflow:out,shots:document.querySelectorAll('.shot').length,lower:['professional','faq','continuation','contact'].every(id=>document.getElementById(id)),rubik:document.fonts.check('16px Rubik','שלום'),direction:getComputedStyle(document.body).direction,images:[...document.images].every(i=>i.complete&&i.naturalWidth>0)};
  });
  assert.equal(result.scrollWidth,width);assert.deepEqual(result.overflow,[]);assert.equal(result.shots,8);assert(result.lower&&result.rubik&&result.images);assert.equal(result.direction,'rtl');
  report.viewports.push({width,height,...result});
  await page.screenshot({path:path.join(dir,'QA-'+width+'.png'),fullPage:false});
 }
 await page.locator('#seek').fill('14');await page.locator('#seek').dispatchEvent('input');assert.equal(await page.locator('#preview-headline').textContent(),'pH NORMALIZER');
 await page.locator('#seek').fill('20');await page.locator('#seek').dispatchEvent('input');assert.equal(await page.locator('#preview-headline').textContent(),'LONGEVITY SERUM');
 await page.locator('#seek').fill('28');await page.locator('#seek').dispatchEvent('input');assert.equal(await page.locator('#preview-visual img').count(),0);
 await page.locator('#seek').fill('36.5');await page.locator('#seek').dispatchEvent('input');assert.equal(await page.locator('#preview-number').textContent(),'08 / 08');
 await page.locator('#seek').fill('0');await page.locator('#seek').dispatchEvent('input');await page.locator('#play').click();await page.waitForTimeout(1100);await page.locator('#play').click();assert(Number(await page.locator('#seek').inputValue())>0.7);report.interactions.playback='pass';
 await page.emulateMedia({reducedMotion:'reduce'});await page.locator('#play').click();assert.equal(await page.locator('#play').getAttribute('aria-pressed'),'false');
 await page.locator('#faq summary').first().click();assert(await page.locator('#faq details').first().getAttribute('open')!==null);
 await page.locator('.topbar a').click();assert.equal(new URL(page.url()).hash,'#contact');assert(await page.locator('#field-0').isDisabled());
 report.interactions={playback:'pass',seekStages:'pass',evidenceEmpty:'pass',finalShot:'pass',reducedMotion:'pass',faq:'pass',firstScreenCta:'pass',formNonSubmitting:'pass'};
 const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}}),fallback=await nojs.newPage();
 await fallback.goto(pathToFileURL(path.join(dir,'STORYBOARD.html')).href);assert.equal(await fallback.locator('.shot').count(),8);assert(await fallback.locator('#contact').isVisible());report.interactions.noJavaScript='pass';await nojs.close();
 await page.setViewportSize({width:1440,height:900});await page.goto(pathToFileURL(path.join(dir,'STORYBOARD.html')).href);await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:path.join(dir,'STORYBOARD-full.png'),fullPage:true});
 await page.addStyleTag({content:'.preview-section,.references,.controls,.shot details{display:none!important}.intro{padding:30px 0;gap:50px}.hero-product{max-width:480px;justify-self:center}.intro h1{font-size:64px}.intro h2{font-size:26px}.facts{padding:15px 0}.notice{margin:20px 0 35px}.shots{gap:20px}.shot-picture{min-height:232px;height:232px}.pack-stage,.bottle-stage{height:210px}.shot-copy{padding:20px}.shot-copy h3{font-size:24px}.shot-copy .status{margin:10px 0 0}.kit-section{margin:35px 0}.lower-section{padding:28px 0}.professional{padding:28px}.related-grid img{height:120px}.related-grid{margin:20px 0}.contact{padding:28px;margin:20px 0 30px}.faq details{display:block}.faq details p{display:block;font-size:13px;margin:0 0 12px}.faq summary{font-size:15px;padding:12px 0}.section-top{margin-bottom:20px}h2{font-size:32px}.section-lead{margin-bottom:24px}footer{padding:20px 40px}'});
 await page.evaluate(()=>document.querySelectorAll('#faq details').forEach(x=>x.open=true));
 await page.screenshot({path:path.join(dir,'STORYBOARD.png'),fullPage:true});
 assert.deepEqual(errors,[]);report.browserErrors=errors;fs.writeFileSync(path.join(dir,'QA.json'),JSON.stringify(report,null,2)+'\n');
 await browser.close();console.log(JSON.stringify({structural:'pass',viewports:report.viewports.map(x=>x.width+'×'+x.height),interactions:report.interactions,errors}));
}
run().catch(e=>{console.error(e);process.exit(1)});
