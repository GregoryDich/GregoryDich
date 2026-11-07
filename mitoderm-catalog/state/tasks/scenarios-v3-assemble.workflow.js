export const meta = {
  name: 'scenarios-v3-assemble',
  description: 'Scenarios v3: harmonize the 13 Hebrew chapters with the concept and costs, build the HE PDF+DOCX with the two-pass builder, verify by numbers, independent page read, fix and rebuild',
  phases: [
    { title: 'Prepare', detail: 'builder adapted from v2.1 and dry-run on the chapters already written (parallel with the last chapters)', model: 'opus' },
    { title: 'Consolidate', detail: 'one editor harmonizes all chapters, fills costs, syncs the roadmap, checks Cyrillic/structure', model: 'opus' },
    { title: 'Build', detail: 'final two-pass build, verify.py, page renders', model: 'sonnet' },
    { title: 'Read', detail: 'independent read of rendered pages against the owner request' },
    { title: 'Fix', detail: 'fix sources/builder on findings, rebuild, re-verify' },
  ],
}

const S = '/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad'
const REPO = '/home/user/GregoryDich'
const CAT = REPO + '/mitoderm-catalog'
const V3 = CAT + '/state/scenarios-v3'
const OLDB = S + '/scenarios-0511'
const OUT = CAT + '/site/xlsx-he/scenarios'
const BUILD = V3 + '/build'
const WORK = S + '/scenarios-v3-build'

const WAIT = (files, what) => `DEPENDENCY: ${what} are still being written by parallel jobs: ${files.join(', ')}. Read and do everything else first. Before the step that needs them, check that each file exists AND is committed (cd ${REPO} && git log --oneline -1 -- <path> prints a commit); if not, wait with "sleep 120" and check again, up to 60 minutes in total; if some never appear, continue without them and say so in your return.`

const ORDER = ['00-concept', '01-home', '02-production', 'exo-nad', 'v-tech-system', 'exotech-gel', 'exocell-mask', 'exosignal-hair', 'exosignal-spray', 'micro-boost-10', 'cellular-age-defense-2-5', 'cell-renew-1-5', 'derma-recovery-cream', 'mitopen', 'mitoscan', 'mitotech-cell-booster', '95-materials', '97-rules', '98-costs', '99-roadmap']

const CTX = `CONTEXT. MITODERM (Israel), professional cosmetics; version 3 of the video-scenarios file for the site (Hebrew, RTL), requested by the owner on 06/11. Brief with the owner's request verbatim, decisions D1-D8 and the roadmap: ${V3}/BRIEF.md. Sources of the client file: ${V3}/src/*.md (Hebrew) - parts 00-concept, 01-home, 02-production, 13 product chapters by slug, 95-materials, 97-rules, 98-costs, 99-roadmap; the chapter template ${V3}/src/format-v3.md (internal, not printed); research in ${V3}/research (facts.json = approved facts per product, costs.json = models and unit costs, r1-r4 notes); editor notes in ${V3}/review; English prompts in ${V3}/prompts (not printed). Print order of the client file: ${JSON.stringify(ORDER)}.
RULES: client file entirely in Hebrew (Latin only for product names, paths, hex, model ids); Cyrillic 0 - check with python3 -c "import re,sys;print(len(re.findall('[\\u0400-\\u04FF]',open(sys.argv[1]).read())))" <file>; approved texts quoted verbatim with sources; new on-screen lines marked (הצעה — לאישור); nothing invented (results, prices of MITODERM, offers, dates); before/after only real photos with consent; AI cast = dramatization. Texts the owner approved earlier are never changed.
PROGRESS: append a line to ${V3}/progress/<your label>.jsonl after each step; on start, if it exists, continue from it (the container restarts sometimes).
GIT: commit only your own files (git add <files>; git commit -m "<imperative subject <= 72 chars>" -m "<why>" -- <files>); the message ends with exactly these two lines:
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014kxi7WWH4xGLi2AcFRd4q2
then git push -u origin claude/mitoderm-figma-catalog-74tbuw (retry on network errors or index.lock). Never force-push. Do not commit people photos or price lists.`

const CONSOLIDATE = `${CTX}
YOU ARE THE CHIEF EDITOR (label consolidate). ${WAIT([V3 + '/src/00-concept.md', V3 + '/src/02-production.md', V3 + '/src/format-v3.md', V3 + '/src/95-materials.md', V3 + '/src/97-rules.md', V3 + '/src/98-costs.md', V3 + '/src/99-roadmap.md', V3 + '/src/mitotech-cell-booster.md', V3 + '/src/mitoscan.md', V3 + '/review/g4.md', V3 + '/review/g5.md'], 'the concept parts and the last chapters (with their editor notes)')} Start with the 11 chapters already committed (exo-nad, hair, spray, v-tech, gel, mask, micro-boost, cellular, cell-renew, derma, mitopen) and costs.json; take the rest as they land. Read BRIEF.md (its roadmap section is the owner-approved staged plan with time, token and credit budgets and the speed-ups: 99-roadmap.md must carry the same stages, gates, budgets and speed-ups in Hebrew - sync it), 00-concept.md, 02-production.md, format-v3.md, costs.json, then ALL 13 chapters and 01-home.md, 95/97/98/99. Make the file one book:
1. Terminology and names identical everywhere: the five rung names of the ladder (as 00-concept defines them), the love-arc moments, the cast and set description (one wording, defined once in 02-production; chapters refer to it in one line), the proof caption («אחרי [N] טיפולים · תוצאות אישיות משתנות»), the dramatization line, the form fields, the family block, the phone order (heading -> stage -> text).
2. Structure of every chapter = format-v3.md exactly (headings, tables, columns); shot ids <slug>-F01..; durations sum 30-40 s; scroll ranges continuous from 0; a totals line; sections 7 and 8 present.
3. Costs: fill every chapter's section 8 with real numbers from costs.json (credits and USD, low/likely/high) using the same method; 98-costs.md totals = the sum of the chapters + home transitions + the sample; the balance line (credits, plan, time checked) identical everywhere.
4. Facts: spot-check every chapter against facts.json (main effect quote, zone, tool, kit, indications); remove or mark anything not traceable; medical-sounding claims (hair growth, scars, pigmentation) only as approved and never as a shown result.
5. Hebrew: natural professional Hebrew, gender agreement (הקוסמטיקאית; visitors in plural), RTL punctuation; Latin only where allowed; Cyrillic 0 in every src file.
6. Cross-references between parts resolve (section numbers, chapter names).
Fix in place (you are the only writer now). Write ${V3}/review/consolidate.md (English: changes per file, open questions for the owner). Commit and push. RETURN (English, <= 300 words): what changed, open questions, and the final totals (shots, seconds, credits low/likely/high for the sample and the series).`

const BUILDPREP = `${CTX}
YOU ARE THE BUILDER (label build:prepare). Prepare and dry-run the build of ${OUT}/MITODERM-video-scenarios-HE-v3.docx and .pdf from ${V3}/src in the order above (format-v3.md is NOT printed). Some sources are still being written in parallel (00/02/95/97/98/99, mitotech-cell-booster, mitoscan): the builder must skip a missing file with a console note and build the rest, so you can dry-run NOW on the 11 committed chapters + 01-home; the final build is a separate later step by another agent, so leave ${BUILD}/build.sh runnable with one command and document it in ${BUILD}/README.md (how to build, verify, render pages).
Start from the v2.1 tooling, which worked: ${OLDB}/build.sh (two passes: --mark adds QQMARKnn to every Heading 1, the PDF is scanned for start pages, the second pass prints TOC numbers), ${OLDB}/src/build-docx.cjs (docx-js; ORDER at line ~20; cover subtitle at line ~389 says גרסה 2.1), ${OLDB}/src/post-docx.py (post-processing of the docx XML), ${OLDB}/verify.py (Cyrillic in docx XML and PDF text, page count, TOC numbers vs starts, source tokens present on the chapter pages, words outside the printable area). Copy them into ${BUILD}/ (committed to git) and adapt: SRC = ${V3}/src, ORDER as above, part headings for the book (part 1 «הקונספט וההפקה» = 00, 01, 02; part 2 «13 פרקי מוצר» = the chapters, EXO-NAD first as the model; part 3 «נספחים» = 95, 97, 98, 99), cover title «תסריטי וידאו לדפי MITODERM — מהיכרות לאהבה», subtitle «גרסה 3.0 · 07/11/2026 · סרט בקליניקה · סולם המודעות · טופס מהבלוק הראשון», TOC on page 2 with page numbers, headers/footers as before, RTL tables with the wide shot tables in landscape or with reduced font so no column is clipped. Work dir ${WORK} (LibreOffice profile ${OLDB}/lo-profile or a new one there); export NODE_PATH=$(npm root -g). Generalize verify.py: the token check runs for EVERY source file against its page range (missing tokens 0), not only MITOTECH; outside-printable-area words 0; TOC == starts; Cyrillic 0 in docx XML and PDF text. Render pages: pdftoppm -r 70 -jpeg to ${WORK}/pages/ (look at 6-8 of them yourself with the Read tool: RTL correct, tables not clipped, Hebrew not reversed; fix the builder until they are). Do NOT copy the dry-run output to ${OUT}/. Commit the build tooling (${BUILD}/) and push. RETURN (English): the one-command build line, dry-run page count, verify.py output verbatim, remaining clipping issues if any.`

const FINALBUILD = (p) => `${CTX}
YOU ARE THE FINAL BUILDER (label build:final). The build tooling is ready in ${BUILD}/ (README.md there; the preparer reported: ${JSON.stringify(p || '').slice(0, 1500)}). All sources in ${V3}/src are now final (the chief editor finished). Run the full two-pass build with ${BUILD}/build.sh into ${WORK}; it must include ALL files of the print order (none skipped - if one is missing, stop and report); run ${BUILD}/verify.py (Cyrillic 0 in docx XML and PDF text, TOC == starts, missing source tokens 0 for every file, words outside the printable area 0); render all pages with pdftoppm -r 70 -jpeg to ${WORK}/pages/; copy the final pair to ${OUT}/MITODERM-video-scenarios-HE-v3.docx and .pdf; commit them and push. RETURN (English): page count, verify.py output verbatim, the paths.`

const READ_SCHEMA = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['high', 'medium', 'low'] }, page: { type: 'integer' }, file: { type: 'string' }, issue: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'page', 'issue'] } }, coverage: { type: 'string' }, verdict: { type: 'string', enum: ['ready', 'fix-first'] } }, required: ['issues', 'coverage', 'verdict'] }

const READER = (b) => `${CTX}
YOU ARE THE INDEPENDENT READER (label read). The builder reported: ${JSON.stringify(b || '').slice(0, 1200)}. Rendered pages are in ${WORK}/pages/ (jpeg per page) and the PDF at ${OUT}/MITODERM-video-scenarios-HE-v3.pdf (pdftotext for text). Look at EVERY page of parts 1 and 3 and at least 3 pages of each product chapter with the Read tool (full size): Hebrew renders right-to-left and reads naturally (no reversed words, no broken niqqud/geresh), tables not clipped, no text outside the page, headings and TOC correct, numbers consistent (shots, seconds, credits) between chapters and 98-costs, no Cyrillic, no Latin sentences. Then check coverage of the owner's request (verbatim in BRIEF.md): Higgsfield motion; love + Hunt's ladder from not knowing to trust and the request; the request possible from the very first block; what makes a cosmetologist love the product; home block 1 with the hanging 3D pack along the scroll; choosing a product -> a clip moves the visitor to it -> below only that product; frames by scroll; how it is done beautifully (references); the cartoon look answer; the clinic; the pack rotating and reaching the cosmetologist; her wow; a real case; before/after per product as short striking situations; the pack flying onto the table and applied to face or head by the main effect; no protocols in the film; strong offers; you can be the same cosmetologist; the MITODERM family; events; the limits; the roadmap; costs and balance. Do NOT edit files. RETURN JSON per the schema: issues with page numbers and the exact fix; coverage = a short paragraph; verdict ready or fix-first (fix-first only for high issues).`

const FIXER = (r) => `${CTX}
YOU ARE THE FIXER (label fix). The reader found these issues in the built file: ${JSON.stringify(r).slice(0, 6000)}. Fix the sources in ${V3}/src or the builder in ${BUILD} (only what the issues need; approved texts unchanged), rebuild with ${BUILD}/build.sh into ${WORK} and copy the pair to ${OUT}/, rerun ${BUILD}/verify.py (all zeros, TOC == starts), re-render ${WORK}/pages/, look at the fixed pages yourself with the Read tool, commit and push. RETURN (English): what you fixed, verify.py output verbatim, page count.`

phase('Prepare')
const [prep, consolidated] = await parallel([
  () => agent(BUILDPREP, { label: 'build:prepare', phase: 'Prepare', model: 'opus' }),
  () => agent(CONSOLIDATE, { label: 'consolidate', phase: 'Consolidate', model: 'opus' }),
])
phase('Build')
const built = await agent(FINALBUILD(prep), { label: 'build:final', phase: 'Build', model: 'sonnet' })
phase('Read')
const read = await agent(READER(built), { label: 'read', phase: 'Read', schema: READ_SCHEMA, model: 'opus' })
let fixed = null
if (read && read.verdict === 'fix-first') {
  phase('Fix')
  fixed = await agent(FIXER(read), { label: 'fix', model: 'opus' })
}
return { consolidated, built, read, fixed }
