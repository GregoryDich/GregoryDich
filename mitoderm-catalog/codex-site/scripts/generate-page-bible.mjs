#!/usr/bin/env node
// Generate or validate per-product PAGE.md files from the only source: REGISTRY.json.
import fs from 'node:fs';
import {readBoard,renderApprovalPage} from './render-approval-package.mjs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../production/page-bible');
const registry=JSON.parse(fs.readFileSync(path.join(root,'REGISTRY.json'),'utf8'));
const renderPage=(function renderPage(p){
 if(p.approvalPackage)return renderApprovalPage(p,readBoard(p),registry);
 const f=(x,n=2)=>Number(x).toFixed(n);
 let sec=0,vh=0;
 const rows=p.shots.map(s=>{const a=sec,b=vh;sec+=s.seconds;vh+=s.vh;const shotType=s.type==="pack"?"rigged 3D / real packshot":s.type==="evidence"?"verified real case / neutral placeholder":s.type==="patient"?"one locked patient + professional":s.type==="home"?"same patient at home":s.type==="device"?"real device/reference":s.type==="record"?"verified real interface":"real clinic technique / approved reference";return `| ${String(s.index).padStart(2,"0")} | ${f(a)}–${f(sec)} | ${f(b)}–${f(vh)} | **${s.title}** | ${shotType} |`;});
 const pal=registry.paletteByFamily[p.palette];const stripped=p.isFrozen?"**FROZEN: Do not edit the already published V-TECH page or its film. This is only a reference entry.**":"**STORYBOARD ONLY:** No implementation, new model, paid generation or site edit authorized by this specification.";
 let output=[
 `# ${p.name} — PAGE.md`, "",stripped,"",
 `> Category: **${p.line}** · slug \`${p.slug}\` · ${p.shots.length} filmed sections · ${f(p.timeline.seconds,3)} s · ${f(p.timeline.scrollVh)} viewport heights · font **Rubik** · Hebrew RTL + EN/RU · Last planned review: 2026-11-13`,
 "",
 "## Production reference and color", "",
 `- Approved product image path: \`${p.packImage}\` (from existing repo, not a newly generated SKU).`,
 `- Palette: **${p.palette}** — background \`${pal.bg}\`, surface \`${pal.surface}\`, accent \`${pal.accent}\`, typography \`${pal.text}\`. ${pal.source}.`,
 `- Protocol: **${p.source}**, pages **${p.pages||"not yet verified"}**. Prose for a web audience; technical doses and exact settings stay in clinician materials and require separate approval.`,
 `- Clinician visual cohort suggestion: **${p.cast.suggestedFemaleCosmetologistBand}**. Identity: **${p.cast.referenceStatus}**. Patient: **${p.cast.patientReference}**. No actor may change across any page blocks.`,
 `- Instagram: **NOT YET APPROVED**; official direct procedure clip link and usage permissions are missing. Never substitute random social video.`,
 "",
 "## Video / scroll map", "",
 "| Scene | Film seconds | Scroll vh | Action | Source/production treatment |","|---|---:|---:|---|---|",...rows,"",
 `- Film duration **${f(p.timeline.seconds,3)} s**; scroll **${f(p.timeline.scrollVh)} vh**. Proposed figures except for the frozen V-TECH reference. 1 vh = viewport height, not 1 real-time second.`,
 "- Camera transitions: begin shot with preceding end framing; move only via motivated object/hand/camera; prohibit sudden blur, color temperature jump, morphing or changes to patient face.",
 "- Package moves: model exact real geometry/label once; use photo or controlled 3D keyframes, not independently imagined Higgsfield packs.",
 "",
 "## Complete page below film (separate semantic HTML, not video seconds)", "",
 "1. **Evidence panel:** comparable authorized real before/after with dates, intervention list and written permission. If missing, hide comparison and show a factual information panel with a way to request supporting material.",
 "2. **Exact kit and product contents:** real original packshot and source-checked volumes/parts; professional CTA. Any other kit shown elsewhere is a distinct SKU.",
 `3. **Professional offer:** headline \`${p.heroHE}\`; primary claim / UTP (DRAFT) \`${p.uspHE}\`; action \`${p.ctaHE}\`. Qualify clinicians, show training availability only if confirmed.`,
 "4. **Education and FAQ:** protocol introduction (no patient-directed invasive instructions), correct usage category, prerequisites, follow-up and request for training.",
 "5. **Related products:** contextual separate SKUs, never imply the related product is inside this kit.",
 "6. **Contact:** lead source and selected product retained in form; available from first screen as on V-TECH.",
 "",
 "## Quality gates / owners", "",
 "- [ ] User approves final characters and patient/professional roles, including all age-cohort portraits.",
 "- [ ] Real procedure Instagram clip link or uploaded permitted reference reviewed; model is NOT a clinical source.",
 "- [ ] Real package geometry, ingredients and protocol edition signed off.",
 "- [ ] Scene order and duration signed off; desktop 16:9 and mobile 9:16 compositions.",
 "- [ ] Real consented before/after obtained or evidence block remains informational.",
 "- [ ] Draft Hebrew texts clinically and commercially reviewed.",
 "- [ ] Credits/cost approved BEFORE any paid Higgsfield work.",
 "- [ ] Release QA: no identity drift, correct packaging, stable lighting, readable RTL, reduced motion, first-screen CTA.",
 "",
 ];
 if(p.slug==="exo-nad")output.push("## Mandatory EXO-NAD details", "", "- **Physical look:** user-supplied \`NAD.png\` is canonical: gold/ivory box, orange/amber **pH NORMALIZER** bottle, turquoise **LONGEVITY SERUM**, transparent **EXO-NAD** main bottle with gold cap. Do NOT depict the invented green 1/2/3 packaging.","- **Protocol order** in MITODERM-Protocols-HE.pdf pp.9–10: EXO BIPHASIC PEEL → pH NORMALIZER → LONGEVITY SERUM. The first phase has professionally assessed variants, not a single universal approach.","- **Commercial kit content** in MITODERM catalog: EXO BIPHASIC PEEL 15 ml + pH NORMALIZER 5×5 ml + LONGEVITY SERUM 5×5 ml. The hero photo showing three types is not necessarily a photograph of all units supplied; cross-check the latest kit specification.","- **Palette:** EXO-NAD is VM, **not BIOSPICULE**, no dark green brand background. Champagne and warm ivory must be calibrated against real foil; turquoise/amber are the colors of individual bottles only.","- **Evidence:** no AI before/after; keep patient face unchanged through all three phases.","");
 if(p.slug==="exotech-gel")output.push("## Critical SKU distinction", "", "**EXOTECH GEL** is a separate spherical gold home-care product in a black/gold box. It is NOT the 5 rectangular V-TECH GEL MASK sachets with white dispensing nozzles from the clinical V-TECH kit. Show the professional recommendation as a transition to independent home care, not as the same product.", "");
 if(p.slug==="exocell-mask")output.push("## Mask physical construction", "", "The user-supplied instruction is: remove two auxiliary paper/impregnated supporting layers, place ONLY the main white face mask on the face. The full printed instructions must be verified before production of the exact hand movement.", "");
 if(p.slug==="micro-boost-10")output.push("## Applicator lock", "", "Use the real white syringe-shaped topical applicator; appearance does NOT authorize portraying a subcutaneous injection. Current protocol pp.4–5 describe controlled topical application / massage, not injection.", "");
 return output.join("\n")+"\n";
});
let failed=[];
for(const p of registry.pages){const expected=renderPage(p);const file=path.join(root,'pages',p.slug,'PAGE.md');if(process.argv.includes('--check')){if(!fs.existsSync(file)||fs.readFileSync(file,'utf8')!==expected)failed.push(p.slug);}else{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,expected,'utf8');}}
if(registry.pages.length!==13)failed.push('expected 13 pages');
for(const p of registry.pages){const sec=Number(p.shots.reduce((a,s)=>a+s.seconds,0).toFixed(3)),vh=Number(p.shots.reduce((a,s)=>a+s.vh,0).toFixed(3));if(sec!==p.timeline.seconds||vh!==p.timeline.scrollVh)failed.push(p.slug+' timeline mismatch');if(!registry.paletteByFamily[p.palette])failed.push(p.slug+' palette undefined');if(p.slug==='exo-nad'&&p.palette!=='vm_nad')failed.push('EXO-NAD must use champagne palette');if(p.slug==='v-tech-system'&&!p.isFrozen)failed.push('V-TECH must stay frozen');}
if(failed.length){console.error('PAGE BIBLE QA FAILED:',failed.join(', '));process.exit(1);}console.log('PAGE BIBLE QA passed for',registry.pages.length,'products.');
