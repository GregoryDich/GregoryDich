export const meta = {
  name: 'vtech-v3-skeleton',
  description: 'V-TECH SYSTEM v3 sample page skeleton (free, no credits): scroll film with our HD frames + labelled storyboard frames for clinic shots, three layers, lead form from block 1, before/after wipe, phone; then an independent check',
  phases: [
    { title: 'Build', detail: 'one builder: page, layers, scroll film, form, wipe, phone, 4 key screens' },
    { title: 'Check', detail: 'independent check by numbers and 4 screens', model: 'sonnet' },
  ],
}

const S = '/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad'
const REPO = '/home/user/GregoryDich'
const CAT = REPO + '/mitoderm-catalog'
const PROTO = CAT + '/site/proto'
const V3 = CAT + '/state/scenarios-v3'
const OUT = PROTO + '/v3/v-tech-system'

const CTX = `CONTEXT. MITODERM (Israel), professional cosmetics, Hebrew RTL site. The owner wants ONE sample page that shows the new v3 story - a cosmetologist's clinic film scrubbed by scroll that walks a cosmetologist up Ben Hunt's awareness ladder to a lead - on the flagship V-TECH SYSTEM. Paid generation is not approved yet, so this is the FREE SKELETON: real product frames from our existing V-TECH page and labelled storyboard frames where the clinic shots will go. The task spec is the last section of ${V3}/BRIEF.md («Каркас образца V-TECH — задание»): read that section and nothing else of BRIEF. The scenario: ${V3}/src/v-tech-system.md (Hebrew; §2 the blocks by rung with the on-screen texts and their sources, §3 the 12 shots F01-F12 with seconds and scroll ranges, §5 offer and form, §6 phone). Design tokens and type: the existing V-TECH page ${CAT}/site/public/v-tech-system/index.html (colours, Rubik, spacing, header) - reuse its look; its assets ${CAT}/site/public/v-tech-system/img/ (kit.webp, m1-m5.webp stills, bg.webp, logo) and frame sequences ${CAT}/site/public/v-tech-system/seq/ (the HD box/ampoule motion). Rules: ${CAT}/design-rules.md - grep the sections «Сайт v2» and «вёрстка по замерам» only when you need a number.
OUTPUT: ${OUT}/index.html (+ v3.css, v3.js, and an img/ folder with only the files you use - copies, not links), self-contained for publishing as a claude.ai artifact: no external requests except Google Fonts (Rubik); no build step; total <= 40 MB and <= 200 files; every image at least 2x its CSS size on the screens you test (HD).
TOKEN BUDGET: about 1 million tokens for the build. Read only the files named here; do not explore the repo. One browser job at a time (other jobs run browser checks - check ps and wait if two chromium processes are already running).
LIMITS: do not touch the 12 published pages, the template, the engine, build-vtech.py or anything under site/public; texts are taken verbatim from the chapter (approved texts) and proposals keep a small visible tag «הצעה»; nothing invented. Git: commit only ${OUT}/ and your progress file ${OUT}/progress.jsonl (append a line per step; resume from it after a restart); message imperative <= 72 chars, body explains why, ending with exactly:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014kxi7WWH4xGLi2AcFRd4q2
then git push -u origin claude/mitoderm-figma-catalog-74tbuw (retry on errors); never force-push.`

const BUILD = `${CTX}
YOUR TASK (builder): build the skeleton page.
1. LAYERS: z0 - background in the line colours (black and gold #c9a24b, as the V-TECH page); z10 - the film stage, pinned, full-bleed on desktop, a stage block of about 46% of the screen height under the heading on phones (< 900 px); z20 - HTML text in Rubik with a soft scrim under it, copy on the right (RTL), never covering the product.
2. FILM BY SCROLL: one pinned stage; every shot of §3 gets its scroll range from the chapter (40vh read-hold per text block, then motion at 25vh per second). Product shots (F01 the box, F03 the flight, F05 macro, F12 back to the lineup) use our real frames: the box/ampoule sequences in seq/ played by scroll on a canvas with progressive loading (first frames first), the stills m1-m5 / kit.webp. Clinic shots (F02, F04, F06, F07, F08, F10, F11) are STORYBOARD FRAMES drawn in HTML/CSS (not generated images): a full-bleed dark warm frame with a thin gold rule, the shot id, one Hebrew line of what will be filmed (from the chapter's «מה רואים», shortened, verbatim words), the rung name, and a small tag «סטוריבורד — ייווצר אחרי אישור». Dissolve between shots; the product frame hands over to the next shot without a jump.
3. LEAD FROM BLOCK 1: a CTA button in the header on desktop and a sticky bottom bar on phones (the chapter's CTA text) open a side drawer (bottom sheet on phones): שם, טלפון, «אני…» (קוסמטיקאית / בעל/ת קליניקה / רופא/ה / אחר), the product prefilled (V-TECH SYSTEM), a WhatsApp link shown as text; submit is handled in script with preventDefault and shows «תודה, נחזור אליכם» (tag הצעה); keyboard and screen-reader accessible; Escape closes.
4. PROOF: the before/after block (F09) as a wipe driven by scroll (clip-path), with two neutral placeholders «צילום לפני — MITODERM» / «צילום אחרי — MITODERM» (no faces, no drawn results) and the chapter's caption with [N].
5. OFFER, FAMILY, INFO: the offer block with the offer types as placeholders, the family/events block, then the static info blocks of the chapter below the film (kit image, facts), the protocol link.
6. PHONE (< 900) per §6: heading -> stage -> text in every block; storyboard frames in 9:16 composition; the bar never covers the stage at a reading position.
7. FALLBACKS: prefers-reduced-motion and no JS: one still per block, no pinning, everything readable; dir="rtl" lang="he" in the markup.
8. VERIFY YOURSELF before returning: render 1280x720, 1440x900, 1920x1080 and 390x844@3 (touch) at the reading position of every block with Playwright (chromium.launch() works; serve ${OUT} with python3 -m http.server on a free port), look at the screenshots with the Read tool, and fix what is wrong: text over the product, cut frames, overlaps, empty bands, jumps between shots, the drawer. Python check: Cyrillic 0 in your files. Measure the page weight (files and MB).
Commit and push. RETURN (English, <= 300 words): what the page does block by block, the file count and size, what you could not do, the screenshot paths for the 4 key screens.`

const CHECK = (b) => `${CTX}
YOU ARE THE INDEPENDENT CHECKER (read-only except ${OUT}/check/). The builder reported: ${JSON.stringify(b || '').slice(0, 2000)}. Serve ${OUT} locally and check with Playwright at 1280x720, 1440x900, 1920x1080, 390x844@3 touch and 820x1180@2 touch, scrolling the whole page in 40 px steps (canvas frames are cheap here): (1) at every step: no text box over the product/storyboard frame's main subject, nothing outside the screen, no two blocks' texts at once, the CTA/bar visible; (2) at each block's reading position: the copy and the stage level, even air; (3) the drawer opens from block 1 on every screen, focus moves into it, Escape closes, submit shows the thank-you; (4) the wipe moves with scroll; (5) reduced motion and JavaScript disabled: everything readable; (6) network: no requests except the page's own files and Google Fonts; (7) Cyrillic 0; (8) weight and file count. Look at the 4 key screens yourself with the Read tool. Write ${OUT}/check/report.md (values and verdicts). RETURN JSON per the schema.`

const SCHEMA = { type: 'object', properties: { verdict: { type: 'string', enum: ['ready', 'fix-first'] }, issues: { type: 'array', items: { type: 'object', properties: { severity: { type: 'string', enum: ['high', 'medium', 'low'] }, screen: { type: 'string' }, where: { type: 'string' }, issue: { type: 'string' }, fix: { type: 'string' } }, required: ['severity', 'issue'] } }, weight: { type: 'string' }, notes: { type: 'string' } }, required: ['verdict', 'issues', 'weight', 'notes'] }

const FIX = (c) => `${CTX}
YOU ARE THE BUILDER AGAIN (label fix). The independent checker found: ${JSON.stringify(c).slice(0, 5000)}. Fix every high and medium issue in ${OUT}/ only, re-render the affected screens, look at them, commit and push. RETURN (English, <= 200 words): what you fixed, what remains.`

phase('Build')
const built = await agent(BUILD, { label: 'build:vtech-v3', phase: 'Build', model: 'opus' })
phase('Check')
const checked = await agent(CHECK(built), { label: 'check:vtech-v3', phase: 'Check', model: 'sonnet', schema: SCHEMA })
let fixed = null
if (checked && checked.verdict === 'fix-first') fixed = await agent(FIX(checked), { label: 'fix:vtech-v3', phase: 'Check', model: 'opus' })
return { built, checked, fixed }
