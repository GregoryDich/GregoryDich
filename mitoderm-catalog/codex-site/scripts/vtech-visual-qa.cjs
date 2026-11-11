/* MITODERM v9 — browser acceptance for the V-TECH product film.
   Invoked on the production-capable app locally in GitHub Actions.
   Screenshots are uploaded as CI artifacts for HUMAN visual review.
   Do not equate a passing automated run with an approved film. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('/tmp/mitoderm-qa/node_modules/playwright-core');

const base = process.env.MITODERM_URL || 'http://127.0.0.1:5173';
const outDir = path.resolve(process.cwd(), 'production/proof/ci-v9');
fs.mkdirSync(outDir, { recursive: true });
const configs = [
 {name:'desktop-1440',width:1440,height:900,mobile:false},
 {name:'desktop-1920',width:1920,height:1080,mobile:false},
 {name:'phone-390',width:390,height:844,mobile:true},
 {name:'phone-320',width:320,height:568,mobile:true},
 {name:'phone-430',width:430,height:932,mobile:true}
];
const samples=[
 ['patient',null],['closed',.335],['sleeve',.466],['hinge',.516],['opened',.85]
];
let issues=[],checks=[];
function check(ok,msg){
 checks.push({ok:!!ok,msg});
 if(!ok){issues.push(msg);process.stderr.write('FAIL '+msg+'\n');}
 else process.stdout.write('PASS '+msg+'\n');
}
async function goToLocal(page,local){
 const target=await page.evaluate(v=>{
  const el=document.querySelector('[data-vtech-story]');
  const scene=document.getElementById('vtech-kit');
  const root=el.getBoundingClientRect().top+window.scrollY;
  const start=Number(scene.dataset.sceneStart);
  const weight=Number(scene.dataset.sceneWeight);
  const entry=Number(el.dataset.entryUnits||0);
  return Math.round(root+(entry+start+v*weight)*window.innerHeight+1);
 },local);
 await page.evaluate(y=>window.scrollTo({top:y,left:0,behavior:'instant'}),target);
 await page.waitForFunction(v=>{
  const s=document.querySelector('[data-vtech-stage]');
  return s && s.dataset.activeChapter==='vtech-kit' &&
   Math.abs(Number(s.dataset.chapterProgress)-v)<.013;
 },local,{timeout:12000});
}
async function snapshot(page,config,name,local){
 if(local!==null) {
  await goToLocal(page,local);
  await page.waitForFunction(()=>{
   const img=document.querySelector('.vts-pack-backdrop img');
   return img?.complete && img.naturalWidth>0;
  },null,{timeout:15000});
 }
 else {
  const y=await page.evaluate(()=>{
   const el=document.querySelector('[data-vtech-story]');
   const patient=document.getElementById('vtech-mask');
   const root=el.getBoundingClientRect().top+window.scrollY;
   return Math.round(root+(Number(el.dataset.entryUnits||0)+Number(patient.dataset.sceneStart)+.6*Number(patient.dataset.sceneWeight))*window.innerHeight);
  });
  await page.evaluate(y=>window.scrollTo({top:y,left:0,behavior:'instant'}),y);
  await page.waitForFunction(()=>document.querySelector('[data-vtech-stage]')?.dataset.activeChapter==='vtech-mask',{timeout:12000});
 }
 await page.screenshot({path:path.join(outDir,config.name+'-'+name+'.png'),animations:'disabled',timeout:30000});
 const s=await page.evaluate(()=>{
  const stage=document.querySelector('[data-vtech-stage]');
  const sleeve=document.querySelector('.vts-pack-object');
  const layer=document.querySelector('.vts-kit-lid');
  const box=document.querySelector('.vts-pack-flight');
  const render=document.querySelector('.vts-kit-sequence');
  const room=document.querySelector('.vts-pack-backdrop img');
  const overlay=document.querySelector('.vts-training-film-copy');
  return {
   chapter:stage.dataset.activeChapter,local:Number(stage.dataset.chapterProgress),
   opened:stage.dataset.kitOpened,kitLoad:stage.dataset.kitLoad,
   openAmount:Number(stage.style.getPropertyValue('--vts-kit-open')),
   sleeve: sleeve?getComputedStyle(sleeve).transform:null,
   hinge: layer?getComputedStyle(layer).transform:null,
   packVisible:box?getComputedStyle(box).visibility:null,
   render:render?.dataset.state,
   roomLoaded:!!room?.complete&&room.naturalWidth>0,
   width:document.documentElement.scrollWidth,
   viewport:window.innerWidth
  };
 });
 fs.writeFileSync(path.join(outDir,config.name+'-'+name+'.json'),JSON.stringify(s,null,2));
 check(s.width<=s.viewport+2,config.name+' '+name+': no horizontal overflow ('+s.width+'/'+s.viewport+')');
 if(local!==null){
  check(s.chapter==='vtech-kit',config.name+' '+name+': product kit chapter');
  check(s.packVisible==='visible',config.name+' '+name+': pack flight visible');
  check(s.render==='layers'||s.render==='fallback'||s.render==='loading',config.name+' '+name+': kit renderer available');
  if(name==='closed')check(s.openAmount<.01,config.name+' closed: sealed pose');
  if(name==='opened')check(s.opened==='true'&&s.openAmount>.999,config.name+' opened: full pack reveal');
  check(s.roomLoaded,config.name+' '+name+': clinic background loaded');
 }
 return s;
}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  for(const cfg of configs){
   const page=await browser.newPage({viewport:{width:cfg.width,height:cfg.height},deviceScaleFactor:1,isMobile:cfg.mobile,hasTouch:cfg.mobile,reducedMotion:'no-preference'});
   page.on('pageerror',e=>{issues.push(cfg.name+' JS error: '+e.message);});
   await page.goto(base+'/products/v-tech-system',{waitUntil:'domcontentloaded',timeout:30000});
   await page.waitForSelector('[data-vtech-story][data-entry-units]',{timeout:20000});
   await page.waitForSelector('.vts-stage',{timeout:20000});
   await page.evaluate(()=>document.fonts.ready);
   let previous=-1;
   for(const [name,progress] of samples){
    const state=await snapshot(page,cfg,name,progress);
    if(progress!==null){
     check(state.openAmount>=previous-.0001,cfg.name+' '+name+': monotonic opening');
     previous=state.openAmount;
    }
   }
   const reversed=await snapshot(page,cfg,'reversed',.335);
   check(reversed.openAmount<.01,cfg.name+': reversed scroll closes kit');
   const train=await page.locator('#vtech-training').count();
   check(train===1,cfg.name+': training section renders');
   const three=await page.locator('.vc-training-steps').count();
   check(three===0,cfg.name+': no obsolete 3-step cards');
   const editorial=await page.locator('.vc-training-film-copy').count();
   check(editorial===1,cfg.name+': editorial education section');
   await page.evaluate(()=>{const node=document.querySelector('#vtech-training');window.scrollTo({top:window.scrollY+node.getBoundingClientRect().top,left:0,behavior:'instant'});});
   await page.waitForTimeout(120);
   await page.screenshot({path:path.join(outDir,cfg.name+'-training.png'),animations:'disabled',timeout:30000});
   await page.locator('#vtech-related').scrollIntoViewIfNeeded();
   await page.waitForFunction(()=>{
    const images=[...document.querySelectorAll('#vtech-related img')];
    return images.length>=5 && images.every(img=>img.complete && img.naturalWidth>0);
   },null,{timeout:15000});
   await page.evaluate(async()=>{
    const images=[...document.querySelectorAll('#vtech-related img')];
    await Promise.all(images.map(img=>img.decode()));
   });
   await page.waitForTimeout(250); /* allow a post-decode compositor paint */
   check((await page.locator('#vtech-related img').count())>=5,cfg.name+': all related product images loaded');
   const relatedDiagnostics=await page.evaluate(()=>[...document.querySelectorAll('#vtech-related img')].map(img=>{
    const r=img.getBoundingClientRect(),st=getComputedStyle(img);
    return {src:img.getAttribute('src'),naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight,
     box:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],
     opacity:st.opacity,display:st.display,visibility:st.visibility,filter:st.filter,
     objectFit:st.objectFit,mixBlendMode:st.mixBlendMode,transform:st.transform};
   }));
   fs.writeFileSync(path.join(outDir,cfg.name+'-related-diagnostics.json'),JSON.stringify(relatedDiagnostics,null,2));
   process.stdout.write('IMAGE DIAGNOSTICS '+cfg.name+' '+JSON.stringify(relatedDiagnostics)+'\\n');
   await page.screenshot({path:path.join(outDir,cfg.name+'-related.png'),animations:'disabled',timeout:30000});
   await page.close();
  }
  const reduced=await browser.newPage({viewport:{width:390,height:844},reducedMotion:'reduce'});
  await reduced.goto(base+'/products/v-tech-system',{waitUntil:'domcontentloaded',timeout:30000});
  await reduced.waitForSelector('[data-vtech-story]');
  await reduced.waitForFunction(()=>document.querySelector('[data-vtech-story]')?.getAttribute('data-mode')==='linear',null,{timeout:12000});
  check((await reduced.locator('[data-vtech-story]').getAttribute('data-mode'))==='linear','reduced motion uses semantic linear mode');
  await reduced.screenshot({path:path.join(outDir,'reduced-motion.png'),animations:'disabled'});
  await reduced.close();
  fs.writeFileSync(path.join(outDir,'qa-result.json'),JSON.stringify({time:new Date().toISOString(),checks,issues},null,2));
  process.stdout.write('QA '+checks.filter(x=>x.ok).length+'/'+checks.length+' checks passed, '+issues.length+' issues.\n');
  if(issues.length)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
