export const meta = {
  name: 'mitotech-fix4',
  description: 'MITOTECH sample: one fix pass on everything the page map, the layout rules and the eye found (page files only, texts unchanged), then final values by the numeric checks and the QA chain',
  phases: [
    { title: 'Fix', detail: 'one writer, page files only, rebuild, numeric checks' },
    { title: 'Values', detail: 'independent final evaluation: page map + layout + QA chain', model: 'sonnet' },
  ],
}

const S = '/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad'
const W = S + '/pages/mitotech-cell-booster'
const REPO = '/home/user/GregoryDich'
const CAT = REPO + '/mitoderm-catalog'
const PROTO = CAT + '/site/proto'
const KEYS = S + '/pages/mitotech-cell-booster-keys'
const THREE = S + '/rdemo/node_modules/three/build/three.module.min.js'

const CTX = `CONTEXT. The MITOTECH CELL BOOSTER sample page (Hebrew RTL, three.js) is published as v3; the owner wants it checked by numbers and made pleasant to the eye: pictures fitting their space, text blocks symmetric and by the rules, even rhythm. Two numeric tools now exist and are calibrated: the page map ${PROTO}/qa/pagemap.cjs (3D motion: CUT, UNDER_CHROME, UNDER_TEXT, TWO_PRODUCTS, GHOST, POP, EMPTY, RUN_SPAN, LAYOUT, HD; map and README in ${CAT}/site/pagemap/) and the layout check ${PROTO}/qa/layout-check.cjs with rules L1-L8 in ${CAT}/design-rules.md (section «Сайт v2 — вёрстка по замерам») and the report ${CAT}/site/pagemap/mitotech-cell-booster.layout.md / .json (failures by severity, the eye review mapped to values in «Взгляд со стороны»). The eye review itself: ${W}/layout-eye/list.json (+ frames). Pixel verification of the map and its notes: ${W}/map-verify/progress.jsonl and files there; map review: ${W}/map-review/.
PAGE AND BUILD: sources are only ${PROTO}/scenes/mitotech-cell-booster.js, ${PROTO}/story-v2-motion.js, ${PROTO}/story-v2.css. Build: cd ${PROTO} && python3 build-vtech.py --product mitotech-cell-booster --scene --files ${W}/site --keys ${KEYS} --links artifact; rm -rf __pycache__. QA chain: ${W}/qa/me/chain.sh (exports FONTDIR=${S}/fonts THREE=${THREE} NODE_PATH; verify-live 51/51 + 6 SKIP, verify-hd all HD, verify-edges 9/9, verify-scene mitotech 8/8 and exotech-gel 11/11, regress.sh <tag> vs ${W}/regress/before.md5 = 12/12 identical, Cyrillic 0 via Python, clash 0). Numeric checks: node ${PROTO}/qa/pagemap.cjs and node ${PROTO}/qa/layout-check.cjs (see their --help / README; ${W}/layout/run.sh re-runs the layout collection).
HARD LIMITS: texts never change (same Hebrew strings, same markup order); do not touch the engine ${PROTO}/engine/, the template, build-vtech.py, story_content.py or any other page - the 12 published pages must stay byte-identical (regress 12/12); do not publish (the orchestrator does); one browser job at a time (another job may be running sweeps - check with ps and wait); keep progress in ${W}/fix4/progress.jsonl and resume from it after a restart; snapshot-commit working states (git add the three page files; commit message imperative <= 72 chars, body explains why, ending with exactly:
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014kxi7WWH4xGLi2AcFRd4q2
then git push -u origin claude/mitoderm-figma-catalog-74tbuw; never force-push).`

const FIX = `${CTX}
YOUR TASK (writer): ONE fix pass over everything found, then prove it by values. TOKEN BUDGET: keep reading small - the findings are already compiled below with their values; open the reports only to look up a specific number or element (grep, not full reads). COMPILED FINDINGS (current build 4bd6d1d4; 1280 / 1440 / 1920 unless noted):
H1 S5 «פרוטוקול» copy pinned to the top while the pair stands low: copy centred in band @dock 0.58/0.66/0.73, level with copy dy 209/293/454 px.
H2 S4 «הרגישו» pair small and low: fill 0.30/0.29/0.39, centre y 0.42/0.36/0.39, level dy 118/134/179 px; phone fill 0.27, air above/below 242/97 px.
H3 S1 «הכירו» copy below the kit at the end of the hold: level dy -117/-140/-152 px; copy centred in band 0.40/0.37/0.33.
H4 phone S3 mid-run spill past the block: 54 px (390), 63 px (360).
H5 step cards: picture and text two islands (gap 303-464 px); series size spread 0.45; baseline spread 71-73 px (feet 22-95 px from frame bottom).
M1 kit small on its card (share 0.33/0.41/0.44); card padding top 7 / bottom 29 / side 30 px.
M2 phone bottom bar label on two right edges (96 px at 390).
M3 phone/tablet empty bands: open->S1 634 px at 390 (0.75 of a screen), spacing spread 515 px (the --mt-gap rooms).
M4 chips wrap onto two lines at 390 (3 of 4), a lone word at 1024.
M5 late layout shift at 360x780: 1348 px at 1841 ms on one of three loads (rooms measured after first paint).
M6 S2/S3 level across screens: spread 158/178/237 px.
L1 card-at-landing opacity late by 50-76 px of scroll; L2 haze after the product 0.95 vs <= 0.3; L3 phone opening band 229 px.
Map-verify: step-card pictures pass under the dock pill while scrolling (fix only if covered at the card's reading position); phone/tablet opening run 180-200 px vs the 300 px rule (owner's decision - note only); no-JS/no-WebGL phone: next still enters 22-33 px early, stills at 2.56-2.8x instead of 3x (cheap CSS only).
Template/engine items (do NOT fix, list for the owner): 1920/2560 cover drift of the 3D vs the 1200 px copy wrap; stacked button widths; related grid 2 of 3; chips 3+1 rows; BIOSPICULE(TM) widow in related; MASK composition question.
Write ${W}/fix4/plan.md: every finding with its current value, the fix you will make (file, rule), or the reason it is NOT fixed here. Not fixed here = template/engine issues shared with the 12 approved pages (the 1920/2560 cover drift of the 3D vs the 1200 px copy wrap, stacked button widths, the related grid with 2 of 3 cards, the chips 3+1 rows, the MASK composition question) - list them for the owner, do not touch. Judge before fixing the map-verify findings: step-card pictures passing under the fixed dock pill while scrolling - a scrolling page always passes under a fixed pill, so fix only if at a card's reading position (card centred in the band) the pill covers the picture; the short phone/tablet opening run (180-200 px against the 300 px rule) needs the owner's decision - leave it and note it; the no-JS/no-WebGL phone early entry of the next still (22-33 px) and the stills shown at 2.56-2.8x instead of 3x are minor - fix if cheap in CSS. Fix in the page's own files, high severity first: S5 «פרוטוקול» copy pinned to the top while the pair stands low (centre the copy in its first screen like S2-S4 and level the pair with it); S4 «הרגישו» pair small and low (fill >= 0.40, centred, level with the copy on every desktop and even air on phone); S1 «הכירו» copy 115-152 px below the kit at the end of the hold; the five step pictures (one drawn height and one baseline across the series within tolerance; picture and text one group); the kit small over its card and the card's uneven padding; phone and tablet empty bands between sections (the --mt-gap rooms: keep the no-two-products guarantee of fix2 but shrink the rooms to what the hand-over needs; the opening -> S1 band especially); phone S3 mid-run spill past the block; phone pose 4 small; bottom bar label on two right edges; chips wrapping onto two lines at 390 (allow wrap rules, not text changes); the late layout shift race at 360x780 (measure sizes before first paint or reserve the rooms in CSS); S2/S3 level across screens; the card-at-landing opacity; the haze after the product. Keep every fix3 guarantee (16:9 opening, no cuts, no see-through, no doubles, one product at a time, no-JS/no-WebGL layouts, the 899 turn). After the fixes: rebuild, run the QA chain (all green, regress 12/12), run pagemap.cjs and layout-check.cjs on the new build at all 11 viewports, and compare before/after counts (high/low per rule). Iterate until no high remains except the listed template items; then commit and push. RETURN (English): the before/after table of values per finding, what remains and why, md5 of the built page, QA chain summary.`

const VALUES = (f) => `${CTX}
YOU ARE THE FINAL EVALUATOR (read-only except ${W}/fix4-values/). The writer reported: ${JSON.stringify(f || '').slice(0, 3000)}. Do not trust it: rebuild nothing, but run on the current ${W}/site yourself: the QA chain ${W}/qa/me/chain.sh (or its steps), node ${PROTO}/qa/pagemap.cjs (all flags, all 11 viewports) and node ${PROTO}/qa/layout-check.cjs (all rules, all 11 viewports), one browser job at a time. Then render 4 key screens for the eye (1280x720, 1440x900, 1920x1080, 390x844@3) at the holds of S1, S4, S5 and the step cards with the harness ${W}/fix2/sweep.cjs, look at them with the Read tool, and say whether anything still looks wrong. Write ${W}/fix4-values/report.md and values.json (every check: value, tolerance, verdict; counts high/low per rule; QA chain lines; md5 of the page; regress 12/12). RETURN (English, <= 400 words): the counts, the remaining failures with values, the eye verdict, md5.`

phase('Fix')
const fixed = await agent(FIX, { label: 'fix:page' })
phase('Values')
const values = await agent(VALUES(fixed), { label: 'values:final', model: 'sonnet' })
return { fixed, values }
