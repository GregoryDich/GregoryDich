/* Browser smoke test for MITODERM ProductCinema.
   This verifies the NEW 12 routes in the same local CI preview as V-TECH;
   it is not artistic approval and does not imply that live films exist. */
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('/tmp/mitoderm-qa/node_modules/playwright-core');
const assert=require('node:assert/strict');
const registry=require('../production/page-bible/REGISTRY.json');
const root=process.env.MITODERM_URL||'http://127.0.0.1:5173';
const out=path.resolve('production/proof/ci-v9/product-cinema');
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',args:['--no-sandbox','--disable-dev-shm-usage']});
 let count=0;
 try{
  for(const size of [{name:'desktop',width:1365,height:900},{name:'mobile',width:390,height:844}]){
   const page=await browser.newPage({viewport:{width:size.width,height:size.height},deviceScaleFactor:1});
   page.on('pageerror',error=>{process.stderr.write('PAGE ERROR '+error.message+'\n');});
   for(const config of registry.pages.filter(p=>!p.isFrozen)){
    await page.goto(root+'/products/'+config.slug,{waitUntil:'domcontentloaded',timeout:30000});
    await page.locator('.pc-story').waitFor({timeout:20000});
    await page.evaluate(()=>document.fonts.ready);
    await page.waitForFunction(()=>document.querySelector('.pc-story')?.dataset.activeShot!==undefined,{timeout:10000});
    const state=await page.evaluate(()=>{
     const story=document.querySelector('.pc-story');
     const scroll=getComputedStyle(story).height;
     const pictures=[...document.querySelectorAll('.pc-object img')].map(x=>({src:x.getAttribute('src'),loaded:x.complete&&x.naturalWidth>0}));
     return {count:document.querySelectorAll('.pc-scene').length,
      width:document.documentElement.scrollWidth,viewport:innerWidth,
      height:parseFloat(scroll),images:pictures,header:!!document.querySelector('.site-header'),
      evidence:!!document.querySelector('#pc-evidence'),offer:!!document.querySelector('#pc-offer'),
      training:!!document.querySelector('#pc-training'),contact:!!document.querySelector('#contact'),
      ageLabels:document.body.innerText.includes('18–35')||document.body.innerText.includes('50–80')};
    });
    assert.equal(state.count,config.shots.length,config.slug+' chapter count');
    assert.ok(Math.abs(state.height-(config.timeline.scrollVh+1)*size.height)<size.height*.4,config.slug+' authored scroll timeline');
    assert.ok(state.width<=state.viewport+3,config.slug+' overflow '+JSON.stringify(state));
    assert.ok(state.header&&state.evidence&&state.offer&&state.training&&state.contact,config.slug+' full section architecture');
    assert.ok(!state.ageLabels,config.slug+' should not publish casting cohorts');
    await page.waitForFunction(()=>[...document.querySelectorAll('.pc-object img')].every(i=>i.complete&&i.naturalWidth>0),null,{timeout:15000});
    const shot2=await page.evaluate(()=>{
     const story=document.querySelector('.pc-story'),s=story.getBoundingClientRect().top+window.scrollY;
     const first=Number(document.querySelector('.pc-scene')?.dataset.startVh||0);
     window.scrollTo({top:s+1.68*innerHeight,left:0,behavior:'instant'});
     return s;
    });
    await page.waitForFunction(()=>document.querySelector('.pc-story')?.dataset.activeShot==='1',null,{timeout:8000});
    // Reverse scroll must recover the first scene.
    await page.evaluate(s=>window.scrollTo({top:s,left:0,behavior:'instant'}),shot2);
    await page.waitForFunction(()=>document.querySelector('.pc-story')?.dataset.activeShot==='0',null,{timeout:8000});
    if(config.slug==='exo-nad'){
     const original=await page.locator('.pc-object img').evaluateAll(images=>images.map(x=>x.getAttribute('src')));
     assert.ok(original.includes('/assets/product-cinema/exo-nad/NAD.png'),'EXO-NAD original photo preserved');
     await page.screenshot({path:path.join(out,size.name+'-exo-nad.png'),animations:'disabled'});
    }
    console.log('PASS product '+size.name+' '+config.slug+' '+state.count+' chapters');
    count++;
   }
   await page.close();
  }
 } finally{await browser.close();}
 assert.equal(count,24,'12 products on two viewports');
 console.log('PRODUCT CINEMA QA: '+count+'/24 routes passed');
})().catch(e=>{console.error(e);process.exit(1);});
