export const meta = {
  name: 'vtech-finish',
  description: 'Finish the V-TECH page: apply the approved fix list, verify independently, repair, re-check',
  phases: [
    { title: 'Implement', detail: 'one engineer applies the eight approved fixes', model: 'opus' },
    { title: 'Verify', detail: 'browser QA and code review, independent of the engineer', model: 'opus' },
    { title: 'Repair', detail: 'fix confirmed findings', model: 'opus' },
    { title: 'Recheck', detail: 'independent re-test of repaired items', model: 'opus' },
  ],
}

const S = '/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad'
const ROOT = '/home/user/GregoryDich/mitoderm-catalog/codex-site'

const LIMITS = `Hard limits:
- Do NOT touch: mitoderm/pilot/ProductCinema.tsx, mitoderm/pilot/product-cinema.css, mitoderm/media-urls.json, mitoderm/pilot/vtech-timeline.ts, mitoderm/pilot/vtech-entry.ts, anything under production/. Another engineer edits ProductCinema in a separate checkout.
- Do NOT commit, push, stash or create branches. Leave the changes in the working tree.
- Never submit the lead form on any real site. Local checks only.
- Must keep working: (a) the cross-route "flight" of the V-TECH pack from the home page into this page (ProductTransition.tsx and VTechPackFlight.tsx measure the stage and [data-flight-target]; they assume the stage is pinned at the top of the viewport and 100svh tall, so do not change the stage size or its sticky top); (b) reduced-motion "linear" mode (data-mode=linear); (c) RTL.`

const FACTS = `KNOWN FACTS (verified; use them instead of re-deriving)
Layout
- mitoderm/pilot/VTech.tsx renders SiteHeader (mitoderm/shared.tsx:44-54: header.site-header > div.nav-inner > a.brand-home, nav.header-links, a.nav-contact, button.mobile-menu) + SectionNavigation (nav.vc-section-nav: brand link, 4 anchor links, price link) + VTechStory + VTechTraining + VTechRelated + SiteFooter + FloatingInquiry.
- Header CSS: mitoderm/mitoderm.css:11 — position:fixed; z-index:100; height:90px; background: linear-gradient(180deg, rgba(10,10,11,.96), rgba(10,10,11,.72), transparent). Phone rules at max-width 760px (line 43): height 78px. No scroll state exists today.
- Section nav CSS: mitoderm/pilot/vtech-cinema.css:46 — position:fixed; z-index:90; top:90px; min-height:53px; background rgba(8,8,10,.92) with blur. Line 48: transition:top .28s. Line 49: html[data-vtech-immersed=true] .vtech-cinema .site-header is translated up and hidden. Line 50: html[data-vtech-immersed=true] .vc-section-nav{top:0}. At max-width 860px (line 99): top:78px. So today header and section nav are stacked whenever the page is not "immersed": on the first screen, after the story, and always in reduced motion.
- mitoderm/pilot/VTechStory.tsx:148 sets html[data-vtech-immersed] = inside && units > .12. Line 131: inside = position >= -1 && position <= (total + arrival + 1.8) * height. Line 286: --vts-length = total + 2 + arrivalLength. total = 10.35 viewport units (scene weights 1.67, 1.33, 1.25, 1.25, 1.25, 1.45, 2.15; scene starts 0, 1.67, 3.0, 4.25, 5.5, 6.75, 8.2).
- mitoderm/pilot/vtech-story.css:3-4: the story is height: calc(var(--vts-length) * var(--vts-viewport,100svh)); the stage is position:sticky; top:0; height:100svh. So the stage stays pinned for (total + 1 + arrival) viewport heights: 1.0 H after the story reaches its end.
Kit scene (last scene, kind offer, weight 2.15)
- mitoderm/pilot/vtech-kit-timing.ts maps the scene's local progress 0..1: the video plays during 0-.33 (returnEnd), the closed pack flies .33-.415 (flightEnd), reveal .405-.44, the kit opens .415-.565 (openStart/openEnd). After .565 nothing changes. Static hold today = (1-.565)*2.15 = 0.935 H inside the scene + 1.0 H after it = 1.94 H of scrolling with a frozen picture. This is the "dead tail" the owner wants removed.
- VTechStory.tsx:313 passes onReveal={()=>jumpTo(index,false,scene.id,.94)} to the offer panel: the button jumps to local .94, which must remain a fully open state.
- The offer panel (mitoderm/pilot/VTechDetails.tsx:48-61; CSS vtech-cinema.css:136-153 desktop, 190-199 phone) is visible from the first moment of the kit scene on desktop: the scene article fades in on activation (vtech-story.css:7-8). On phone its copy is gated by the opening: opacity: clamp(0, calc((var(--vts-kit-open,0) - .73) * 4.6), 1) (vtech-story.css:179-188). The offer scrim is forced to opacity:1 in cinema mode by vtech-story.css:25 (a rule at vtech-cinema.css:120 that should fade it never applies because of lower specificity).
- VTechPackFlight (mitoderm/pilot/VTechPackFlight.tsx, vtech-pack-flight.css): a backdrop image (the mask-scene poster, darkened with brightness(.39), .42 on phone, lines 70-80) becomes opaque by local ~.35 (line 18: opacity clamp(0, calc(var(--vts-pack-progress)*7), 1)) and covers the film; the pack object appears with opacity clamp(0, calc(var(--vts-pack-progress)*100), 1) (line 32). A face is still recognisable in that backdrop behind the kit.
Captions
- vtech-story.css:37-41: desktop caption box (inline-start, bottom:100px, width min(440px,38vw)). Phone (max-width 860px) lines 76-80: inset-inline:24px; bottom: calc(64px + env(safe-area-inset-bottom)); h1 clamp(34px,9.2vw,46px).
- Phone hero frame: the phone poster/video is a 9:16 frame, cover-scaled to the stage. In it the gold V-TECH box occupies x 25.6%-73.2% and y 27.4%-87.8% of the frame. Today the phone hero caption (H1 "V-TECH SYSTEM", body, two buttons) sits at the bottom and covers the lower part of the box, including lettering.
Linear (reduced-motion) mode
- vtech-story.css:146-171. The toolbar has padding-top 158px (line 148) and 137px at max-width 860px (line 158), sized for header + section nav. scroll-margin-top for the Training anchor is 160px / 146px (vtech-cinema.css:60, 102).
Tap targets on phone (CSS boxes under 44px)
- .nav-contact: no padding or min-height (mitoderm.css:15, 43). .brand-home img height 40px (line 43). .mobile-menu: font-size 24px, padding 10px (line 15). .header-links a: padding 12px 0 with 12px text (line 14). Section nav links: min-height 44px but padding-inline 3px, so short labels are narrower than 44px (vtech-cinema.css:100, 114). .inquiry-close 38x38 (mitoderm/pilot/pilot.css:19). Footer links: no padding, 11px text (mitoderm.css:39). Desktop .vc-section-inquiry min-height 42px (vtech-cinema.css:58).
Hebrew
- Headings broken with <br/> have no space at the break, so their text content glues two words (screen readers, copy, search): VTechDetails.tsx:26 (רוצים לראות<br/>את התמונה המלאה?), :55, :79, :88 and mitoderm/pilot/HomeSections.tsx:38.
- The catalog "all" filter and other strings in mitoderm/content.json use the spelling הכל; the site copy elsewhere uses the standard spelling with vav (קודם כול). content.json is a single-line JSON file.
- Catalog filter buttons show English group names from mitoderm/data.ts:12-19 (V-TECH FACE, PEELING, BIOSPICULE, DEVICES, HAIR, MITOTECH); they are rendered in mitoderm/Home.tsx:75-84.`

const FIXES = `FIX LIST
1. Dead tail. Re-time the kit scene and shorten the story so that, once the kit is fully open, the pinned stage stays for at most 0.5 viewport heights before it starts to scroll away, and so that between the start of the kit scene and the fully open kit there is no stretch longer than 0.3 H in which nothing moves. Suggested values (adjust if your own check shows a better feel): in vtech-kit-timing.ts keep returnEnd .33, set flightEnd .47, revealStart .455, revealEnd .50, openStart .47, openEnd .88; in VTechStory.tsx:286 use total + 1.2 + arrivalLength; in line 131 end the inside window at (total + arrival + .25) so immersion ends as the stage unpins. Update the comment at the top of vtech-kit-timing.ts so it describes the new timing truthfully. Check every other place that assumes the old constants (jumpTo with .94, resize preservation, phone opacity gates that depend on --vts-kit-open, data-kit-opened).
2. One navigation bar. At any scroll position exactly one of the two bars is visible. Not immersed (first screen, after the story, reduced motion): only the site header. Immersed: only the section nav, at top 0. Implement by hiding the section nav (transform/visibility/pointer-events with the same .28s transition) unless html[data-vtech-immersed=true]. Then remove the space that was reserved for the second bar where it is now wrong: the linear-mode toolbar paddings and the scroll-margin-top values. Do not change the insets of the evidence and offer panels (they are only seen while immersed).
3. Opaque header when scrolled, on every page. Add a small scroll state to SiteHeader (for example data-scrolled on the header when window.scrollY > 8; passive listener, requestAnimationFrame-throttled, cleaned up on unmount) and CSS: at the very top of a page the header keeps today's gradient; once scrolled its background is fully opaque rgb(10 10 11) with a 1px bottom border rgba(223,186,116,.16) and a .2s transition. The phone menu dropdown must keep working.
4. No stray offer text. In cinema mode on desktop the offer panel (kit slot button, kicker, heading, list, buttons, note) and the offer scrim must be invisible while the film's last chapter still plays (kit local 0-.33) and fade in together with the pack flight, so the film's ending is clean and the panel text never floats over unrelated footage. Keep the phone gate working. Reduced-motion mode must show the panel as today.
5. Phone hero (max-width 860px, cinema mode, first scene only). Put the H1 and the body text between the header and the top edge of the box, and the two buttons in the band under the box; nothing may cover the V logo or the lettering on the box. Check at 390x844, 360x740, 430x932 and 412x915. Do not move or scale the footage or the entry target.
6. Kit backdrop. Make the darkened backdrop behind the flying pack and the open kit unrecognisable as a person (stronger darkening plus blur, scaled slightly to hide blurred edges) on desktop and phone.
7. Tap targets. At max-width 860px every interactive element in the header, section nav, inquiry dialog and footer has a hit area of at least 44x44 CSS px (use min-height/min-width/padding; keep the visual design). Also raise the desktop .vc-section-inquiry to 44px.
8. Hebrew. (a) Add a real space before each <br/> listed in the facts (in JSX: {' '}<br/>). (b) In mitoderm/content.json replace the standalone word הכל with הכול everywhere it is a whole word (not inside longer words); edit the file surgically and keep it valid single-line JSON. (c) Give the catalog filter groups Hebrew display labels while leaving the internal names untouched: V-TECH FACE -> V-TECH לפנים, PEELING -> פילינג, BIOSPICULE -> ביו-ספיקולות, DEVICES -> מכשור, HAIR -> שיער, MITOTECH -> MITOTECH. Verify the buttons render correctly right-to-left.`

const BROWSER = `Browser tooling: Playwright is installed globally (NODE_PATH=$(npm root -g); never run "playwright install"). Launch with chromium.launch({ proxy: require('/home/user/GregoryDich/mitoderm-catalog/state/live-review/tools/px.cjs').proxyOpts() }) so the film on the CDN loads through the proxy while localhost bypasses it. Phone viewports use isMobile:true and hasTouch:true. Reduced motion: context option reducedMotion:'reduce'.
Scroll math: story root = [data-vtech-story], stage = [data-vtech-stage], H = stage.clientHeight, rootTop = root.getBoundingClientRect().top + scrollY. The scroll position for u story units is rootTop + u*H. The stage exposes data-active-chapter, data-chapter-progress (0..1 inside the scene) and data-kit-opened; html exposes data-vtech-immersed. The film is one <video> scrubbed by scroll: after each scroll wait until video.seeking is false, plus about 400 ms, before a screenshot. Take JPEG screenshots at quality 80 and deviceScaleFactor 1, and look at them with the Read tool before judging.`

const IMPL = `You are finishing the V-TECH product page of a Hebrew (RTL) marketing site for professional cosmetologists. Work in ${ROOT} (Next app router on vinext/Vite, React 19, TypeScript, pnpm through corepack). Dependencies are installed and dist/ holds a build of the current code. The page is /products/v-tech-system: a sticky full-viewport stage with one scroll-scrubbed video ("the film"), seven scenes, then the Training and Related sections.

The owner approved the fix list below. Make the smallest correct change for each item. Keep the existing dense code style of these files (one compact rule per line, no reformatting of untouched code). Add no dependencies. UI text stays in Hebrew.

${LIMITS}

${FACTS}

${FIXES}

RESTART SAFETY
This job can be interrupted and started again from the beginning with this same message. Before doing anything else, read ${S}/vtech-impl/PROGRESS.md if it exists and run git -C /home/user/GregoryDich diff --stat to see what is already done; then continue with the first unfinished item instead of redoing finished ones. After finishing each numbered item append one line to that file (item number, files touched, how it was checked).

HOW TO CHECK
- corepack pnpm exec tsc --noEmit, then corepack pnpm build (both must pass).
- Serve the build: corepack pnpm start (wrangler dev on http://127.0.0.1:8787). Run it in the background with nohup and a log file under ${S}/vtech-impl/, and wait until curl gets HTTP 200. If something already listens on 8787, stop it first.
- ${BROWSER}
- Save screenshots under ${S}/vtech-impl/shots/ at 1440x900 and 390x844. Cover at least: scroll 0; the middle of each scene; the kit scene at local .1, .3, .4, .6, .85, .95; just after the story; the catalog page; reduced motion at the top and in the kit section; the flight (open /, click the V-TECH product in the hero collection and capture the arrival). Fix what looks wrong and re-check.
- Leave the server running on port 8787 when you finish.

FINAL MESSAGE (plain text; it is your return value): for each of the 8 items: what you changed with file:line, how you checked it (numbers, screenshot paths) and anything still open. Then: tsc and build status, the server log path, and the list of every file you modified.`

const FINDINGS = {
  type: 'object',
  properties: {
    passed: { type: 'array', items: { type: 'string' } },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          check: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'note'] },
          viewport: { type: 'string' },
          summary: { type: 'string' },
          evidence: { type: 'string' },
          repro: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['id', 'check', 'severity', 'summary', 'evidence'],
      },
    },
    measurements: { type: 'string' },
  },
  required: ['passed', 'findings'],
}

const VISUAL = `You are an independent QA reviewer with a browser. Verify the V-TECH product page of a Hebrew (RTL) site after a round of fixes. Do not edit any source file. A production build is served at http://127.0.0.1:8787 (if nothing answers there: cd ${ROOT}, run "corepack pnpm start" in the background with nohup and wait for HTTP 200; do not rebuild unless dist/ is missing). Never submit the lead form.

${BROWSER}
Save your scripts and evidence under ${S}/vtech-verify/. ffmpeg is available for image comparison. Judge only what you see or measure.
This job can be interrupted and started again with this same message: after each check append its result to ${S}/vtech-verify/RESULTS.md, and on start read that file, skip the checks already recorded there and carry their results into your final answer.

Page facts: /products/v-tech-system. Scenes start at units 0 (hero), 1.67 (consultation), 3.0 (pen), 4.25 (serum), 5.5 (mask), 6.75 (results), 8.2 (kit); the story ends at 10.35. Top bars: header.site-header and nav.vc-section-nav.

CHECKS (report each as passed or as findings; use the check id as the prefix of each finding id)
C1 Dead tail (1440x900 and 390x844). Step through the kit scene and beyond in steps of 0.05 H, screenshot the stage, and compare consecutive frames (mean absolute pixel difference). Pass when: (a) between kit local 0 and the first frame where data-kit-opened is true there is no run of identical frames longer than 0.3 H; (b) after data-kit-opened first becomes true the stage stays pinned (its top at 0) for at most 0.5 H more before it starts moving up. Report the measured numbers.
C2 One bar. Sample every 0.25 H from the top of the page to the footer (wait 600 ms after each scroll). A bar counts as visible when its computed visibility is visible, its opacity is above .05 and its rectangle intersects the top 150 px of the viewport. Pass when exactly one of the two bars is visible at every sample, at 1440x900, at 390x844 and in reduced motion. List violating positions.
C3 Opaque header. On /, /catalog and /products/exo-nad scroll 300 px: the header background must be fully opaque (computed style and screenshot: nothing readable through the band). At scroll 0 it may be transparent.
C4 No stray offer text (1440x900 and 1920x1080). For kit local 0, .1, .2, .3: no offer-panel text or buttons visible and the film not dimmed more than in the previous scene; from about .35 on the panel appears with the pack. Also: at no position may the Training heading (מכירים את המערכת.) be visible on top of the pinned stage.
C5 Phone hero at scroll 0 (390x844, 360x740, 430x932, 412x915): the H1, the body text and both buttons must not cover the V logo or the lettering on the gold box; the H1 is not under the header; the buttons are fully visible and not overlapped by the bottom status line.
C6 Kit backdrop: in the kit scene at local .5 and .95 (1440x900 and 390x844) no person may be recognisable behind the kit or the text.
C7 Tap targets at 390x844: at scroll 0, mid film (units 3.5), kit opened, the Training section, the contact form, the footer, and with the header menu opened: every visible a, button, input, select, textarea, summary and [role=button] must measure at least 44x44 px, except links that sit inline inside a sentence. List violators with selector, text and size.
C8 Captions and faces (1440x900, 1280x720, 1920x1080, 390x844): for the consultation, pen, serum and mask scenes at local .1, .5, .9 the caption (small label, heading, body, button) must not cover a face, the hands at work or a product label. Take two screenshots per state: clean, and with a red outline drawn around the caption elements. Report each overlap with the frame path.
C9 Flight from the home page (1440x900 and 390x844): open /, click the link to /products/v-tech-system inside the hero collection, capture a frame every 100 ms for 4 s, then scroll down slowly through the first viewport. Pass when the flying pack ends exactly on the box of the film's first frame (no double image, no jump larger than a few pixels at the hand-off) and the page ends in a normal state. If the hero has no such link, say what you found.
C10 Reduced motion (1440x900 and 390x844): the page shows its scenes as normal stacked sections with images and a chapter toolbar; nothing is hidden under the header; chapter buttons work; no console errors.
C11 Hebrew: on /catalog list the filter button texts (they should be Hebrew, the first one הכול); the text content of these headings must contain a space where the visual line break is: the h2 of the results panel (רוצים לראות את התמונה המלאה?), the offer panel h2, the Training h2. Check in a screenshot that labels mixing Latin and Hebrew read correctly right-to-left.
C12 Regressions: console errors and failed requests on the page (ignore aborted video range requests); the links #vtech-results, #vtech-kit and #vtech-training land on the right content with their headings visible and not hidden under a bar; the price buttons open the inquiry panel (do not submit).

Severity: blocker = broken or unusable; major = clearly visible defect or a failed check; minor = small visual flaw; note = observation. Report only what you verified. When unsure, mark it as a note and say what would settle it. Put the key numbers of C1 and C7 into "measurements".`

const REVIEW = `You are reviewing an uncommitted change set. Do not edit files. Run: git -C /home/user/GregoryDich diff -- mitoderm-catalog/codex-site and read the touched files in full where needed. Also run corepack pnpm exec tsc --noEmit in ${ROOT}.

The change is meant to do exactly this on the V-TECH page of a Hebrew RTL site (and nothing else):
${FIXES}

Files that must NOT have been changed: mitoderm/pilot/ProductCinema.tsx, mitoderm/pilot/product-cinema.css, mitoderm/media-urls.json, mitoderm/pilot/vtech-timeline.ts, mitoderm/pilot/vtech-entry.ts, anything under production/.

${FACTS}

Review for real defects only:
- wrong timing math (recompute it: the static hold after the kit is fully open must be at most 0.5 viewport heights; the button jump to local .94 must still land on a fully open kit; immersion must not end while the stage is still pinned; hash jumps and resize preservation still consistent);
- CSS rules that do not actually win (specificity and source order; this code base already has a rule at vtech-cinema.css:120 defeated by vtech-story.css:25);
- rules that hide or move something in a mode they should not (reduced-motion linear mode; breakpoints: the header switches at 760px, V-TECH phone rules at 860px);
- broken RTL; listeners that leak; hydration mismatches from reading window during render; invalid JSON in mitoderm/content.json (parse it); filter logic broken by the new labels; unintended edits outside the list; leftover debug code.

Do not report style preferences. For each finding give file:line in "evidence", what goes wrong for the visitor in "summary", and a concrete fix in "fix". Use check = "code" and ids like R1, R2. List what you checked and found correct in "passed".`

phase('Implement')
const impl = await agent(IMPL, { label: 'implement fixes', phase: 'Implement', model: 'opus', effort: 'high' })

phase('Verify')
const [visual, review] = await parallel([
  () => agent(VISUAL, { label: 'verify: browser', phase: 'Verify', model: 'opus', effort: 'high', schema: FINDINGS }),
  () => agent(REVIEW, { label: 'verify: code', phase: 'Verify', model: 'opus', effort: 'high', schema: FINDINGS }),
])
const all = [...((visual && visual.findings) || []), ...((review && review.findings) || [])]
const actionable = all.filter(f => f.severity !== 'note')
log('findings: ' + all.length + ', actionable: ' + actionable.length)
if (!actionable.length) return { impl, visual, review, repair: null, recheck: null }

phase('Repair')
const REPAIR = `You are the fixing engineer for the V-TECH page of a Hebrew (RTL) marketing site. Work in ${ROOT}. An earlier engineer applied the fix list below; two independent reviewers then produced the findings at the end (JSON). For each finding: reproduce it first (browser or code reading). If it is real, fix it with the smallest correct change. If it is not reproducible, say so with evidence. Keep every acceptance criterion of the fix list true while you fix.

${LIMITS}

${FACTS}

${FIXES}

This job can be interrupted and started again with this same message: keep notes in ${S}/vtech-impl/REPAIR-PROGRESS.md (one line per finding handled), read them first and do not redo finished ones.

After fixing: corepack pnpm exec tsc --noEmit and corepack pnpm build must pass; restart the server on http://127.0.0.1:8787 (corepack pnpm start in the background with nohup, log under ${S}/vtech-impl/) and leave it running; re-check each fixed item in the browser.
${BROWSER}

FINAL MESSAGE (plain text): for each finding id: fixed / not reproducible / not fixed and why, with file:line and evidence paths; then tsc and build status and the list of files you modified.

FINDINGS:
${JSON.stringify(actionable, null, 1)}`
const repair = await agent(REPAIR, { label: 'repair findings', phase: 'Repair', model: 'opus', effort: 'high' })

phase('Recheck')
const RECHECK_SCHEMA = {
  type: 'object',
  properties: {
    results: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, status: { type: 'string', enum: ['fixed', 'not_fixed', 'not_reproducible'] }, evidence: { type: 'string' } }, required: ['id', 'status', 'evidence'] } },
    regressions: { type: 'array', items: { type: 'object', properties: { summary: { type: 'string' }, evidence: { type: 'string' } }, required: ['summary', 'evidence'] } },
  },
  required: ['results', 'regressions'],
}
const RECHECK = `You are an independent QA reviewer with a browser. Do not edit any source file. A production build of a Hebrew (RTL) site is served at http://127.0.0.1:8787 (start it from ${ROOT} with "corepack pnpm start" in the background if nothing answers). Never submit the lead form.

${BROWSER}
Save evidence under ${S}/vtech-recheck/.

Page facts: /products/v-tech-system. Scenes start at units 0 (hero), 1.67 (consultation), 3.0 (pen), 4.25 (serum), 5.5 (mask), 6.75 (results), 8.2 (kit); the story ends at 10.35. Top bars: header.site-header and nav.vc-section-nav.

Task 1: re-test every finding below and report for each id whether it is now fixed, still present (not_fixed) or was never reproducible, with an evidence path or a measured number.
Task 2: regression pass. Confirm these still hold and report any failure under "regressions": (a) after the kit is fully open (data-kit-opened true) the stage stays pinned at most 0.5 H more; (b) exactly one top bar visible at every 0.25 H sample from top to footer at 1440x900 and 390x844; (c) no offer-panel text visible during kit local 0-.3 on desktop; (d) on phone at scroll 0 the hero text and buttons do not cover the V logo or lettering on the box (390x844 and 360x740); (e) the flight from the home page into this page ends with the pack exactly on the box, at 1440x900; (f) no console errors.

FINDINGS:
${JSON.stringify(actionable, null, 1)}`
const recheck = await agent(RECHECK, { label: 'recheck', phase: 'Recheck', model: 'opus', effort: 'high', schema: RECHECK_SCHEMA })
return { impl, visual, review, repair, recheck }
