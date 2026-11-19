# Task for one agent: browser check (and repair) of the V-TECH page

You are the independent browser verifier and fixer for the V-TECH product page of the MITODERM "cinematic" site.
Work autonomously to the end; nobody will answer questions.

## Where things are
- Repo root: the checkout of `GregoryDich/GregoryDich`, branch `claude/mitoderm-figma-catalog-74tbuw`.
- App: `mitoderm-catalog/codex-site` (Next app router on vinext/Vite, React 19, pnpm via corepack, Cloudflare worker).
- V-TECH page code: `mitoderm/pilot/` (VTech.tsx, VTechStory.tsx, VTechDetails.tsx, vtech-kit-timing.ts,
  vtech-story.css, vtech-cinema.css, vtech-pack-flight.css, pilot.css) plus `mitoderm/shared.tsx`,
  `mitoderm/mitoderm.css`, `mitoderm/data.ts`, `mitoderm/content.json`.
- Build and run: `corepack pnpm install --frozen-lockfile` (once), `corepack pnpm exec tsc --noEmit`,
  `corepack pnpm build`, then detached `setsid nohup corepack pnpm start > <log> 2>&1 < /dev/null &`
  (wrangler dev on http://127.0.0.1:8787). Page: `/products/v-tech-system`, home: `/`.
- Commits to verify: `c324b8f` (eight fixes, never verified in a browser) and `2dd9327` (kit links land on the
  opened kit, title focus). Read both diffs first.
- Older, longer checklist C1-C12: `mitoderm-catalog/state/tasks/vtech-finish.workflow.js` (browser verifier prompt).
  If it conflicts with this file, this file wins.
- Keep scripts and screenshots in a scratch directory outside the repo.

## What must be true (measure, do not assume)
1. Dead tail: after the kit has fully opened, the picture stands still for no more than 0.5 viewport heights of
   scrolling before the sticky stage unpins. Measure in px at 1440x900 and 390x844.
2. One navigation bar: the site header and the section navigation `.vc-section-nav` are never both visible.
   Section nav shows only while `html[data-vtech-immersed]` is set. Check first screen, mid-film, after the film.
3. Header: transparent only at the very top; once scrolled it is solid `rgb(10 10 11)` with a 1px border
   (`data-scrolled` on the header). Check computed styles.
4. Offer text: the offer panel and its scrim are not visible ("ghost headline") before the kit starts opening;
   they appear with the opening. Desktop and phone.
5. Phone hero (390x844): headline above the box, buttons below it; no text over the box.
6. Kit backdrop: blurred and darkened enough that a face behind the kit cannot be read.
7. Tap targets on the phone: every button, link chip and nav item is at least 44x44 px (header, section nav,
   hero, offer, footer). List anything smaller.
8. Captions during film chapters do not cover faces or the pack (one screenshot per chapter, desktop and phone).
9. Transition from the home page: clicking the V-TECH product on the home page still plays the pack flight and
   lands on the V-TECH page correctly.
10. `prefers-reduced-motion: reduce`: page fully usable, all content reachable, nothing overlaps.
11. Hebrew: no glued words at headline line breaks (a space where a `<br>` splits a headline), spelling «הכול»,
    catalog filter labels in Hebrew (V-TECH לפנים, פילינג, ביו-ספיקולות, מכשור, שיער; MITOTECH stays Latin), RTL correct.
12. Links that jump to the kit (offer, navigation, deep-link restore) land on the OPENED kit and the chapter title
    receives focus.
Also: no console errors or failed requests on load and during a full scroll (list third-party noise you ignore).

## How to work
- Chromium and Playwright are pre-installed in cloud sessions: `NODE_PATH=$(npm root -g) node script.cjs`,
  `chromium.launch()` with no options. Do not run `playwright install`, install nothing else.
- Viewports: desktop 1440x900, phone 390x844. Scroll in small steps and wait for the scrubbed video to seek
  before measuring or shooting. `mitoderm-catalog/state/live-review/tools/record.cjs` is an existing recorder.
- First run ALL checks and write down pass/fail with numbers. Then fix what fails with the smallest correct
  change in the existing style (no new abstractions, dependencies or config). Rebuild, re-run the affected
  checks and a quick pass over the others. Commit every verified fix at once (the session may restart).
  If the same defect survives two fix attempts, stop patching, write hypotheses and evidence, report it open.
- Leave the server running on 8787 with the final code.

## Hard rules
- NEVER submit the lead form (it writes to a real database).
- No Higgsfield / image / video generation tools, no credits.
- Do not touch `production/`, media files or `mitoderm/media-urls.json`.
- Git: add only files you changed, by explicit path. Small commits, imperative subject <= 72 chars, body says why.
  Trailer exactly `Claude-Session: <this session's link>`, no model names, no Co-Authored-By. Push with
  `git push -u origin claude/mitoderm-figma-catalog-74tbuw`; if rejected, fetch + `git merge --no-edit FETCH_HEAD`
  and push again. Never force-push. Leave the tree clean.

## Final report (compact)
- Table: check number, desktop result, phone result, measured numbers; for each fix: what was wrong, file:line.
- Commits pushed; confirmation that tsc and build pass and the server answers 200 on 8787.
- Anything still open, with evidence. Paths of up to 10 key screenshots.
