export const meta = {
  name: 'nad-prep',
  description: 'Lighter V-TECH film, EXO-NAD film engine, reference frames and storyboard (no paid generation)',
  phases: [
    { title: 'Film', detail: 're-encode the V-TECH film and prove it looks the same', model: 'opus' },
    { title: 'References', detail: 'exact 3D renders, cast frames, leftover media', model: 'opus' },
    { title: 'Engine', detail: 'scroll-film engine for product pages', model: 'opus' },
    { title: 'Storyboard', detail: 'stills, clips, prompts and cost for the owner', model: 'opus' },
  ],
}

const S = '/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad'
const REPO = '/home/user/GregoryDich'
const CAT = REPO + '/mitoderm-catalog'
const WT = S + '/wt-nad/mitoderm-catalog/codex-site'

const FILM = `You are a video encoding engineer. Goal: make the scroll-scrubbed film of a product page much lighter without visible loss. Work only under ${S}/film/ (create it). Do not modify the repository. ffmpeg 6.1 with libx264 and ffprobe are installed. Use at most 3 threads per encode (-threads 3): other jobs share this 4-core machine.

Sources: download with curl (the proxy is already configured in the environment) the two URLs stored in ${CAT}/codex-site/mitoderm/media-urls.json under the keys /assets/world/vtech-full-story.mp4 and /assets/world/vtech-full-story-mobile.mp4. Desktop master: about 34.6 MB, 1912x1080, 873 frames at 24 fps, 36.4 s. Phone master: about 16 MB, 812x1440, same length. No audio is needed.

How the page uses the film: one <video> is scrubbed by scroll (the page sets video.currentTime continuously, forward and backward), so seeking must be cheap: short closed GOPs. Frame count and timing must stay exactly the same (873 frames, 24 fps, same duration), same resolution, yuv420p, H.264 High profile, +faststart, no audio track.

Do:
1. Probe both masters: codec, profile, bitrate, frame count, key frame positions, B-frames, whether the moov atom comes first. Record it in report.json.
2. Encode candidates with libx264, preset slower, -g 12 -keyint_min 12 -sc_threshold 0, closed GOP (open-gop=0), -bf 2, -pix_fmt yuv420p, -movflags +faststart, -an, two-pass at these targets: desktop 2400k and 1900k; phone 1000k and 800k. Also one CRF 23 encode of each, to see the size of a "transparent" encode. Name the files desktop-2400k.mp4 and so on.
3. For each candidate compute SSIM and PSNR against its master over all frames (ffmpeg ssim and psnr filters; report the mean and the worst 1 percent of frames) and confirm 873 frames and the same duration.
4. Visual proof: for frames 60, 175, 300, 460, 600, 700 and 800 make side-by-side crops at 100 percent scale (master on the left, candidate on the right) of the most demanding area: faces and skin, and the lettering on the gold pack. Save PNG files under ${S}/film/compare/. Look at them with the Read tool and say honestly whether you can see a difference at 100 percent.
5. Seek test in a browser. Playwright is installed globally (NODE_PATH=$(npm root -g); never run "playwright install"; launch chromium with args ['--no-proxy-server']). Serve ${S}/film/ with a tiny local static server that supports HTTP range requests. For the desktop master and the chosen desktop candidate do 40 seeks to random frame times and measure the median and the 95th percentile of the time from setting currentTime to the seeked event. Do the same for the phone pair.
6. Recommend one desktop file (target 12 MB or less) and one phone file (target 5 MB or less): the smallest that you cannot tell from the master at 100 percent. If a target cannot be met without visible loss, recommend the smallest clean file and say so plainly.

This job can be interrupted and started again with this same message: keep a log in ${S}/film/PROGRESS.md, read it first, and do not redo encodes that already exist and are complete.

Final message (plain text; it is your return value): a table of all candidates (size in MB, bitrate, SSIM mean and worst 1 percent, PSNR), the seek timings, your recommendation with the two file paths, and the paths of the comparison images.`

const REFS = `You are preparing reference images for an AI video production. Do not modify tracked files of the repository ${REPO}; write everything under ${S}/nad/. Do not call any Higgsfield or other generation tools. The npm registry works; these hosts are reachable through the proxy already configured in the environment: d2ol7oe51mr4n9.cloudfront.net and mitoderm-cinematic.evenradish1.chatgpt.site.

This job can be interrupted and started again with this same message: keep a log in ${S}/nad/PROGRESS.md, read it first, and do not redo parts whose files already exist.

A. Exact 3D renders of the EXO-NAD kit.
The exact model is a three.js scene module: ${CAT}/site/proto/scenes/exo-nad.js (exports createScene(THREE,{canvas,base,onLoad}) returning {draw(p,view), kit(view), dispose, state}; p runs 0 to 5). Its print textures are in ${CAT}/site/proto/img/exo-nad-3d/. The earlier headless renderer is ${CAT}/site/proto/scenes/render-keys.cjs (Playwright + Chromium software GL + three@0.160.0 three.module.min.js; it wrote 3840x2400 key PNGs v1-meet to v6-kit). three.js is not in the repo: install three@0.160.0 with npm into ${S}/nad/. Playwright is installed globally (NODE_PATH=$(npm root -g); never run "playwright install").
Render the six standard keys at 3840x2400 into ${S}/nad/refs/3d/. If the scene API allows it without editing the module, also render: the closed box alone in a front three-quarter view; the open tray with all bottles; and close views in which the labels of the peel bottle, the pH NORMALIZER vial and the LONGEVITY SERUM vial are readable. Look at every render with the Read tool (downscale copies to about 1600 px wide for viewing). Then compare with the only verified real photo, ${CAT}/codex-site/public/assets/product-cinema/exo-nad/NAD.png (795x489), and with ${CAT}/site/packaging-text.json (what is printed). Report differences in box colour, print, vial glass and liquid colours and cap type. Known disagreement: the 3D model has clear glass with amber-brown and blue liquid and white flip-off caps; an older prompt file describes amber and teal glass with silver crimp caps. Say what the real photo shows.

B. Cast and location frames from the existing V-TECH film (the same clinic and the same cosmetologist will be reused).
Download the film: read the URL for the key /assets/world/vtech-full-story.mp4 from ${CAT}/codex-site/mitoderm/media-urls.json and fetch it with curl into ${S}/nad/src/ (if ${S}/film/ already holds the same file, copy it instead). It has 873 frames at 24 fps, 1912x1080; chapters by frame: hero 0-121, consultation 121-230, pen 230-388, serum 388-546, mask 546-649, results 649-752, kit 752-873 (the last chapter is the intro played backwards). Extract PNG frames at 0, 40, 80, 121, 140, 160, 180, 200, 229, 260, 320, 388, 430, 500, 546, 600, 649, 700, 751, 800 and 872 into ${S}/nad/refs/vtech/ and build one contact sheet. Look at them and describe each in one line (who is visible, framing, where the product is). Name the best frames for: the cosmetologist's identity (face clear, front or three-quarter view), the room in a wide view, the marble table with the pack, gloved hands at work.

C. Media that exist only on the live site.
In ${CAT}/state/live-review/dump-1811/exo-nad.json find the image and video URLs whose names contain IMG_9803, kit-photo or 123.mp4. Download them into ${S}/nad/refs/live/ and report pixel sizes and what they show (look at the images; extract three frames from the video).

D. Leftover generated material that may be reusable.
Download these keys from media-urls.json into ${S}/nad/refs/leftover/ and describe them (resolution, duration, content; extract 3 frames from each video): /assets/world/vtech-kit.webp, /assets/world/vtech-bridge.mp4, /assets/world/vtech-camera.mp4, /assets/world/vtech-intro.mp4, /assets/world/vtech-consultation.webp. Also copy ${CAT}/codex-site/public/assets/vtech/unboxing/open-000.webp and open-039.webp there (Blender renders of the closed pack and the fully open kit) and say whether vtech-kit.webp shows the same kit contents and lettering as open-039.webp.

Write ${S}/nad/refs/refs.json: a list of {file, kind, description, use} for every reference file. Final message (plain text; it is your return value): a compact summary of what was rendered, the comparison result of part A, the best frames of part B with their file paths, what parts C and D contain, and any problems.`

const ENGINE = `You are adding a scroll-film engine to the product pages of a Hebrew (RTL) marketing site. Work ONLY in this separate checkout: ${WT} (a git worktree on branch nad-film-engine; dependencies are installed). Do not touch ${REPO} itself: another engineer is editing the V-TECH page there.

This job can be interrupted and started again with this same message: keep a log in ${S}/nad-engine/PROGRESS.md, read it and the git log of the worktree first, commit after each working step, and continue instead of starting over.

Context: /products/v-tech-system is rendered by mitoderm/pilot/VTech.tsx and VTechStory.tsx: a sticky stage with one <video> scrubbed by scroll. All other product pages (/products/exo-nad and so on) are rendered by mitoderm/pilot/ProductCinema.tsx, which is image-only today: its scroll handler (about lines 144-156) computes the active shot and sets --pc-progress and --pc-local, and the stage images fade with CSS (product-cinema.css:16-17). Page data come from production/page-bible/REGISTRY.json (shots[] with vh weights) and production/page-bible/pages/<slug>/STORYBOARD.json. Media paths are resolved by mediaUrl() in mitoderm/media.ts: a key present in mitoderm/media-urls.json resolves to a CDN URL, anything else stays a local path under public/. public/assets/world/ is git-ignored.

Goal: a product page shows a scroll-scrubbed film behind its stages when a film is configured for its slug. With no film configured the page must behave exactly as today.

Design (follow it):
1. New file mitoderm/pilot/product-films.ts: export type ProductFilm = { desktop: string; mobile: string; fps: number; frames: number; chapters: Array<{ start: number; end: number }> } where start and end are frame numbers, chapters[i] belongs to shot i of the page, and start === end means "hold this frame". Export const productFilms: Record<string, ProductFilm> = {} and commit it EMPTY, so nothing changes in production yet.
2. New file mitoderm/pilot/useScrollFilm.ts: a hook with the generic video logic copied and adapted from VTechStory.tsx (do not import from VTechStory.tsx and do not modify it): the requestAnimationFrame seek loop with easing, snapping and the 900 ms cap (VTechStory.tsx:66-88), the "painted" state that reveals the video only after a decoded frame is shown (lines 49-64 and the media handlers at 294-300), pausing on visibilitychange (185-189). Nothing V-TECH specific.
3. ProductCinema.tsx: when productFilms[product.slug] exists and reduced motion is off, render one <video muted playsInline preload="auto"> in the stage's media layer above the stage images. The images stay underneath as posters and remain the only media in reduced motion and after a video error. Source: film.mobile at max-width 860px, otherwise film.desktop, both through mediaUrl(). Target time = (chapter.start + (chapter.end - chapter.start) * local) / fps for the active shot, clamped to the film length. In product-cinema.css the video covers the stage (object-fit: cover) and fades in with a class once painted.
4. While you are in ProductCinema.tsx fix two small defects: add a real space before the <br/> inside the headings at about lines 80 and 102 (in JSX: {' '}<br/>), and correct the width and height attributes of the kit image at about line 186 (public/assets/product-cinema/exo-nad/kit.webp is 800x1361; the attributes say 500x720).
Keep the dense code style of these files; add no dependencies.

Proof with a test film (never committed):
- Build a placeholder film for exo-nad with ffmpeg from the page's existing images (public/assets/product-cinema/exo-nad/NAD.png and kit.webp): 8 chapters at 24 fps with the frame boundaries 0, 108, 204, 312, 420, 552, 648, 744, 876 (from the planned scene seconds 0, 4.5, 8.5, 13, 17.5, 23, 27, 31, 36.5); each chapter a slow zoom or pan with a large burned-in label TEST 01 to TEST 08; one 1920x1080 file and one vertical 812x1440 file; H.264, yuv420p, a key frame every 12 frames, +faststart, no audio, -threads 2. Put them at public/assets/world/exo-nad-film.mp4 and exo-nad-film-mobile.mp4 (git-ignored). Keep the generator script in ${S}/nad-engine/.
- Temporarily add the exo-nad entry to productFilms in your working tree for testing. Remove it again before the final commit and quote the exact entry in your final message.
- corepack pnpm exec tsc --noEmit and corepack pnpm build must pass. Serve with corepack pnpm start --port 8791 in the background (nohup, log in ${S}/nad-engine/). Port 8787 belongs to the other engineer: never use or stop it.
- Playwright (NODE_PATH=$(npm root -g); never run "playwright install"; launch chromium with args ['--no-proxy-server']): on /products/exo-nad at 1440x900 and at 390x844 (isMobile and hasTouch true) step through the film in steps of 0.1 viewport heights, wait until the video stops seeking, take screenshots and look at them with the Read tool. Pass when the burned-in label always matches the active stage, the picture changes continuously with scroll, the last frame is reached at the end of the last stage, there are no console errors, and with the context option reducedMotion:'reduce' no video is rendered. Also confirm that /products/exotech-gel (no film) looks as before.
- Stop your server on port 8791 when you are done.

Commits in the worktree (do not push): small, imperative subject of at most 72 characters, a body that says why. End each commit message with exactly this trailer line and no other attribution line: Claude-Session: https://claude.ai/code/session_014kxi7WWH4xGLi2AcFRd4q2

Final message (plain text; it is your return value): commit hashes; files changed; the productFilms entry for exo-nad you tested with; evidence paths; anything unfinished.`

const storyPrompt = refsSummary => `You are the storyboard writer for two short AI-generated film pieces for a Hebrew professional-cosmetics site. Write files only under ${CAT}/state/nad-film/ (create the folder). Do not call any generation tools and do not edit anything else.

This job can be interrupted and started again with this same message: if the two output files already exist, read them and finish or improve them instead of starting over.

Read first:
- the production rules and the planned page: ${CAT}/codex-site/production/page-bible/pages/exo-nad/PAGE.md and STORYBOARD.json, PROTOCOL-TRACE.md if it is in that folder, and under ${CAT}/codex-site/production/page-bible/ the files CASTING-REFERENCES.md and PALETTE-CONTROLS.md (search for them);
- how the existing V-TECH film was generated, including full prompts: ${CAT}/codex-site/production/vtech-continuity-v5.json, vtech-bridge-v3.json and vtech-pilot-motion.json;
- earlier prompt drafts: ${CAT}/state/scenarios-v3/prompts/exo-nad.md (use what fits; its cast and room are superseded by the decisions below);
- the reference inventory produced just now: ${S}/nad/refs/refs.json, and this summary from the engineer who made it:
<<<
${refsSummary}
>>>

Decisions already made (do not reopen):
- Same clinic and same cosmetologist as the V-TECH film; identity and room come from frames of that film. A new, different adult patient for EXO-NAD.
- The film tells the procedure step by step in the page's 8 scenes (PAGE.md): 01 the kit; 02 consultation; 03 step one, EXO BIPHASIC PEEL; 04 pH NORMALIZER, rinse, dry; 05 LONGEVITY SERUM; 06 close of the session; 07 evidence placeholder (no new footage: hold a calm frame); 08 the complete system (the intro clip played backwards, as in the V-TECH film).
- Generation plan: 6 key stills K0 to K5 and 5 clips of 5 seconds. Each clip is generated from a start still and an end still, so the clips chain without separate bridges: A K0 to K1 (kit on the table to consultation), B K1 to K2 (to the peel application), C K2 to K3 (to neutralising), D K3 to K4 (to the serum), E K4 to K5 (to a calm wide close, composed so that clip A reversed can follow it). Clip model: Seedance 2.5, mode omni_reference, no audio; tests at 720p, finals at 1080p. Stills: an image model with reference images (the exact 3D renders and the real photo for the product, film frames for the person and the room).
- Packaging is never invented by the model: every still that shows the product names the exact reference files for it. All on-screen text is HTML over the video, never inside the footage.
- One master for both layouts: compose every frame so the action stays inside the central 9:16 column (the phone version is a crop) and the side areas stay calm (page text sits there on desktop).
- The claim limits in PAGE.md apply (no doses or times, no injection, no instant skin change, no "after" look, no needle device in this film).
- Second piece: the ending of the V-TECH film. Today the kit opens as code-animated layers cut from Blender renders (${CAT}/codex-site/public/assets/vtech/unboxing/open-000.webp is the closed pack, open-039.webp the fully open kit). Plan one 5-second clip from the film's last frame (the pack on the marble table) to a photoreal still of the exact open kit on the same table, plus the one still needed for its end frame. If the inventory says a leftover generated kit image is usable, say so.

Write:
1. ${CAT}/state/nad-film/STORYBOARD-v1.md, in Russian (a working note for the project architect): a table of the 8 scenes with the clip that covers each and its frame range at 24 fps; for each still K0 to K5 and for the V-TECH kit still: purpose, composition in plain words, the reference files to attach (exact paths) and the English prompt; for each clip A to E and for the V-TECH kit clip: start and end stills, what moves, the camera, the English prompt (model its style on the Seedance prompts in vtech-continuity-v5.json), the duration, and what to check on review (hands, label text, face identity). Then the assembly plan (which existing script to reuse; look at ${CAT}/codex-site/production/assemble-vtech-continuity-v5.py; how the vertical crop is made) and a cost table using these rates: clips 16 credits per second at 1080p (measured on this account), about 7 per second at 720p (estimate), stills about 2 to 6 credits each (estimate).
2. ${CAT}/state/nad-film/storyboard.json, the same in machine-readable form: {stills:[{id, aspect, refs:[paths], prompt}], clips:[{id, start, end, seconds, prompt}], vtechKit:{still:{...}, clip:{...}}, timeline:[{scene, clip, startFrame, endFrame}]}.

Keep the prompts concrete and short enough to use directly. Final message (plain text; it is your return value): the two file paths and a summary of at most 10 lines with the open questions for the architect.`

const filmP = agent(FILM, { label: 'film: re-encode V-TECH', phase: 'Film', model: 'opus', effort: 'high' })
const refsP = agent(REFS, { label: 'references', phase: 'References', model: 'opus', effort: 'high' })
const engineP = agent(ENGINE, { label: 'film engine', phase: 'Engine', model: 'opus', effort: 'high' })
const refs = await refsP
const story = await agent(storyPrompt(refs || 'The reference step returned nothing; read refs.json and the folder ' + S + '/nad/refs/ yourself.'), { label: 'storyboard', phase: 'Storyboard', model: 'opus', effort: 'high' })
const film = await filmP
const engine = await engineP
return { film, refs, engine, story }
