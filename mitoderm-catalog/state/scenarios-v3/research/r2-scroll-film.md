# r2 - How beautiful scroll-driven film pages are made (references, technique, budgets, our engine)

Working note, English. Written 2026-11-06 for scenarios v3.

## 0. Method and honesty about sources

This session's network allowed only WebSearch result summaries, github.com pages through WebFetch, raw.githubusercontent.com and the npm registry. web.dev, MDN, gsap.com, css-tricks.com, awwwards.com, dev.to and the agency case pages all failed to resolve, so NO primary page was read in full. Every external fact below carries a tag:
- [S] = stated in a search-result summary of the cited URL (secondary, not opened).
- [G] = read on github.com (primary for that repo).
- [M] = measured by me today in this container (numbers reproducible, see section 5).
- [K] = my own prior knowledge or estimate, NOT verified today - check before quoting to the owner.
The owner's reference SELVA could not be identified (searches for a perfume site "SELVA" with forest + bird returned only fragrance listings and an unrelated studio, selvatoi.com). Ask the owner for the URL; section 1 describes the mechanism generically so the scenario does not depend on it.

## 1. References (13)

| # | Reference | What happens on scroll | Technique | Borrow for MITODERM |
|---|---|---|---|---|
| 1 | Apple AirPods Pro (2019 page, widely cloned) | A pinned canvas shows a product spin / explode as you scroll; copy fades in on top | Canvas image sequence: ~140-147 numbered JPEG frames, canvas 1158x770, frame = floor(scrollFraction x count), frames preloaded then drawImage. Clones: https://github.com/Rachit-Pal/Apple-Scroll-Animation/blob/master/app.js [S], https://www.cssscript.com/image-sequence-animation-canvas-clip/ [S]. Whether the live page still uses images or video: not confirmed [S] | The grammar: one pinned stage, scroll = playhead, copy in short fades. Our engine already is this; the news is photoreal full-bleed frames |
| 2 | GSAP ImageSequence helper (official recipe) | Same pattern, generic | `imageSequence` helper + ScrollTrigger scrub/pin: https://gsap.com/docs/v3/HelperFunctions/helpers/imageSequenceScrub [S]; demo https://codepen.io/GreenSock/embed/VwgevYW [S] (canvas 1158x770, the AirPods frames) | Reference implementation for a pin + scrub of N frames; we keep our own engine (windowed decode) but use the same ScrollTrigger-style start/end maths |
| 3 | Moooi "Beauty Blooms" (Build in Amsterdam), Awwwards Site of the Day 29 Jun 2021 | Chapters of interior "moods"; you scroll through rooms with shader transitions between them, music reacts | Responsive WebGL (PixiJS) driven by GSAP, shader transitions, image sequences, interactive music: https://dutchdigital.design/cases/moooi-beauty-blooms [S], https://www.awwwards.com/sites/moooi-beauty-blooms [S] | Closest to our "cabinet" idea: a sequence of rooms/moods linked by transitions, and one hero object (their armchair, our pack). Borrow shader dissolve between blocks instead of hard cuts; sound optional, default off |
| 4 | Moooi "Defy Gravity" / "Paper Play" (same series) | Same chapter structure, objects float / unfold | same stack [S] https://www.dutchdigital.design/cases/moooi-defy-gravity | Our pack-flies-to-the-desk transition = their "defy gravity" beat |
| 5 | Gucci Beauty "Wishes" (MONOGRID), Site of the Day + Developer Award 11 Dec 2023 | Illustrated, scroll-triggered navigation between campaign scenes; transitions between sections | Listed on Awwwards with scroll-navigation and transition elements https://www.awwwards.com/inspiration/scroll-navigation-gucci-beauty-wishes [S], https://www.awwwards.com/inspiration/transition-design-gucci-beauty-wishes [S]; technology not stated in what I read | Luxury-beauty proof that a campaign can be navigated by scroll; take the idea that the scroll IS the menu (our home -> product choice) |
| 6 | Skinfinity cosmetics "Storytelling scroll" (BROWNCATZ) | Skincare story told in scroll chapters | Awwwards element https://www.awwwards.com/inspiration/storytelling-scroll [S]; tech not stated | Skincare tone and pacing reference; check live for chapter length |
| 7 | Renee Crown Wellness Institute "science + love storytelling page" | Science told as emotion | https://www.awwwards.com/inspiration/science-love-storytelling-page-the-renee-crown-wellness-institute [S] | Exactly our problem: B2B science told with warmth (Hunt step 3-4 to love) |
| 8 | Bright Biotech scrolling story | Mission / tech / team as one scrolling story | https://www.awwwards.com/inspiration/mission-scrolling-story-bright-biotech [S] | Biotech credibility without sterile look |
| 9 | Video-on-scroll examples: Goldschmiede Schubart, Archi Malin studio | A real video scrubbed by scroll in a craft setting (hands, workshop) | https://www.awwwards.com/inspiration/video-on-scroll-goldschmiede-schubart [S], https://www.awwwards.com/inspiration/scroll-video-archi-malin-studio [S] | Hands doing a craft in a real room is our cabinet film; learn how they hold on hands/tools rather than faces |
| 10 | Lando Norris site (Off+Brand) | Personal storytelling, reactive overlays, fast transitions | three.js, depth maps, custom shaders, CSS masking (third-party summary) https://designrush.com/best-designs/websites/lando-norris-website-design [S] | Depth-map parallax on a still = cheap "camera move" on a single photoreal still (useful where we have no clip) |
| 11 | Dr. LEVY Switzerland (premium skincare) | Homepage video banner of products + philosophy | https://www.designrush.com/best-designs/websites/dr-levy-switzerland-website-design [S] | Floor of the category: autoplay hero video. We aim above it with scroll control |
| 12 | Framer "Expand Media Story" / scroll video components | Hero video either autoplays or is synced to scroll | https://www.framer.com/marketplace/components/expand-media-story/ [S] | Confirms both modes are mainstream: play (transition) and scrub (story) |
| 13 | SELVA (owner's reference: perfume, full-screen forest, entering the frame by scroll, a bird crossing between screens) | per the owner: you walk into the forest scene; a bird flies between screens as the connective tissue | NOT located; likely scrubbed video or image sequence plus a foreground element animated across the block boundary [K] | Pattern to steal regardless: ONE moving element crosses the boundary between two blocks (our pack, or a hand, or a light beam), so blocks feel like one shot. Ask the owner for the link |

Also worth a live look (from memory, unverified [K]): Apple product pages for AirPods Max / Mac / iPhone (mix of video and sequences), Awwwards "Site of the Year" pieces built on three.js + scroll. Treat as to-do for the owner meeting, not as cited evidence.

Cross-cutting patterns across 1-13: (a) a pinned full-bleed stage with copy on top; (b) one hero object that never leaves; (c) transitions between rooms are shader dissolves or object-led wipes, never plain cuts; (d) sound is optional; (e) the cinematic part is short (the Moooi chapters, Apple spins are seconds, not minutes) and text blocks between them carry the argument.

## 2. Technique numbers

### 2.1 Scrub: images vs video
- Image sequence on canvas: deterministic, instant random access, no seek latency; cost is bytes. Library comparison tables say frame sequences give "1:1 instant scrubbing" while video depends on keyframes [S] https://socket.dev/npm/package/react-scroll-media/diff/1.0.1 (vendor claim, not a benchmark).
- Scrubbed `<video>`: `currentTime` can only cheaply land on keyframes, so a normal encode yields few distinct frames across a scroll; fix = all-intra `-g 1` [S] https://www.hontran.dev/blog/scroll-scrubbed-video-stutters-fix ; `ffmpeg -i source.mp4 -g 1 -an performance-scrub.mp4` [G] https://github.com/steveharrison/scroll-video (that repo also fetches the file as a blob and plays from an object URL because browsers may ignore `preload="auto"` for large files; needs HTTP, not file://). The hontran post suggests `-crf 32 -b:v 0 -g 1 -pix_fmt yuv420p -an -row-mt 1 out.webm`, warns Safari does not reliably play VP9 so keep an H.264 MP4 fallback, and not to encode larger than the displayed size [S]. A keyframe every 10 frames (`-g 10`) is the compromise [S]. Codec behaviour on Safari vs Firefox is reported inconsistently [S]: test on real devices.
- Size penalty of all-intra [M]: synthetic 1920x1080, 96 frames, x264 veryfast, grain added. Normal GOP 48: 132 KB (crf 28); all-intra `-g 1`: 1069 KB (crf 28) = 8x. 9977 KB at crf 23. 1280x720 all-intra crf 28: 473 KB. Absolute numbers are meaningless (synthetic source), the ~8x ratio between GOP and all-intra is the reusable fact. Blog numbers for a ~1280 px clip: about 8 MB MP4 / 13 MB WebM all-intra vs 1-2 MB normal [S].
- iOS: large images/canvases can crash Safari (old Stack Overflow report) [S]; our engine already caps tiers and decodes in a worker window.
- Recommendation [K+M]: keep WebP canvas sequence as the main scrub (matches our engine, safe on iOS). Run ONE A/B on the sample page: the same 5 s with an all-intra H.264 720p video; adopt only if its weight is clearly below the WebP set and Safari iOS scrubs without stalls.

### 2.2 Frame rate and counts
- Mapping is scroll-driven, not time-driven: smoothness = frames per scroll-pixel and a 60 Hz draw loop. A DEV write-up of a canvas WebP scrub rig [S] https://dev.to/pratham7711/how-i-made-a-scroll-scrubbed-video-portfolio-fast-nextjs-15-gsap-canvas-1mj6 reports: seeking is async, keyframe intervals stutter, mobile Safari fights autoplay/inline; best WebP setting `-q 68 -m 6` (~20% smaller than JPEG frames, no visible loss), total media 12.8 MB -> 9.8 MB. Single author, not a benchmark.
- Framer component guidance: 60-120 evenly spaced images for a 3D rotation [S]. Apple clones: 140-147 frames [S].
- Our own sequences today [M]: 5 runs x 40 frames = 200 frames per page.
- Recommended for the 30-40 s film [K]: do NOT extract 24-30 fps (720-1200 frames). Use 5-6 frames per film second of key motion = 150-220 frames per page, plus cross-blend of the two nearest frames on the canvas (globalAlpha lerp, cheap) so slow scrolling does not look stepped. Static beats (holds) need only 1 frame, so the real count is lower. Fast motion beats (pack flight, hand gesture) get higher density (10-12 fps locally).

### 2.3 Formats and quality
- Savings vs JPEG: WebP ~30%, AVIF ~50% median; AVIF ~20-30% smaller than WebP at equal quality [S] https://www.ctrl.blog/entry/webp-avif-comparison/ (DSSIM method). Decode: WebP fast, AVIF moderate; evidence thin [S] -> AVIF only as a later optimisation for the largest tier after a device test. Keep WebP (our worker pipeline, createImageBitmap, already proven).
- My encodes today [M] on a smooth 1087 px source upscaled (so a LOWER bound; real skin/hair/film grain is heavier): 1920x1080 WebP q60/70/80 = 28/31/39 KB clean, 31/38/78 KB with film grain sigma 3; AVIF q45 21-24 KB; JPEG q75 90-157 KB. 1280x720 WebP q70: 20-24 KB. 768x1366 phone WebP q70: 11-14 KB. 540x960: 7-9 KB.
- Reality check [K]: photoreal cabinet frames with skin, hair, glass and grain are 3-6x heavier than the lower bound: plan 1920x1080 WebP q72 at 90-180 KB; 1280x720 at 40-80 KB; 720x1280 phone at 35-70 KB. Grain is the budget killer (q80 doubled the size in my test): apply grain as a CSS/canvas overlay texture, not baked into frames, and encode frames at q68-74 `-m 4..6` (cwebp `-m 6`, `-sharp_yuv` for edges).

### 2.4 Weight budgets (per product page; proposal [K], to confirm on the sample)
| Item | Desktop (16:9) | Phone (9:16) |
|---|---|---|
| Critical, before first scroll | <= 250 KB poster (AVIF/WebP, first frame of block 1) + CSS/JS as today | <= 120 KB poster |
| First 12-16 frames (first 10% of scroll) | <= 1.2 MB, fetched right after poster | <= 0.6 MB |
| Whole sequence | 150-200 frames at 1600-1920 wide: target 10-14 MB, hard cap 18 MB | 120-150 frames at 720x1280: target 4-6 MB, cap 8 MB |
| Key frames only (Save-Data, reduced motion, slow 4g) | 8-12 stills x ~150 KB = 1.5-2 MB | 8-12 x ~60 KB = 0.6-0.8 MB |
| Transition clip home -> product | 2-4 s H.264/VP9 muted, 1080p ~1.5-3 MB, 720p ~0.8-1.5 MB, shared per product | same file or 720p |
Total site: 13 pages x 12 MB = ~160 MB of frames on the CDN, but a visitor loads only the pages visited. Vercel/Cloudflare static hosting handles this; git must NOT hold clip.mp4 (project rule) and should hold only the final WebP sets, not drafts (13 x 12 MB = 160 MB in git is too much for the repo and for the owner's 2 GB disk): put frame sets on a CDN/asset store and keep only keys + manifests in git (decision for the owner/me).
Core Web Vitals thresholds for context: LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1 at p75 [S] https://web.dev/articles/defining-core-web-vitals-thresholds ; a video poster / large image can be the LCP element [S].

### 2.5 Progressive loading
- Order: poster (LCP, `fetchpriority=high`, preloaded, explicit width/height / aspect-ratio box so CLS = 0) -> frames 0..15 -> the rest in scroll direction first, then behind. Our engine already keeps only frames -4..+8 around the wanted one decoded and fetches ahead by scroll direction (story.js BACK=4, AHEAD=8, FLIGHT=4 concurrent fetches, WARM=2) [engine source].
- Start loading the NEXT block's frames when the current block passes ~50%. On the home page, prefetch the three most likely product transition clips on idle (`requestIdleCallback`), not all 13.
- Without preloading each frame causes its own request and visible lag [S] css-tricks.com/?p=308477; hence the windowed preload, not "all or nothing".

### 2.6 Pinning and the scroll maths
- GSAP: ScrollTrigger `pin: true`, `scrub: true`, `end: "+=500%"` style config; playhead tweened `ease: "none"` with `snap: "value"` and `onUpdate` redraw [S] https://gsap.com/docs/v3/HelperFunctions/helpers/imageSequenceScrub, https://skills.sh/freshtechbro/claudedesignskills/gsap-scrolltrigger. Pitfall: pinning + absolute positioning in React created multiple scroller instances [S] greensock forums topic 34794.
- Native alternative: `position: sticky` stage inside a tall section; progress = (scrollY - top)/(height - vh), no library. Our engine already uses a fixed canvas and geometry per block (no GSAP). CSS scroll-driven animations (`animation-timeline: scroll()/view()`): Chrome/Edge since 115, Safari reported from 2025 (version reports conflict), Firefox reported Baseline in Oct 2026 (Firefox 159) [S] https://web.dev/blog/web-platform-10-2026 -> OK for text reveals via CSS with JS fallback; keep canvas drawing in JS (CSS cannot pick frames, only sprite tricks).
- Smoothing: scroll position -> target frame, then ease the displayed frame toward the target (lerp ~0.15-0.25 per rAF) so inertial wheels do not jump; blend two frames.

### 2.7 Text legibility over film
- WCAG AA: 4.5:1 normal text, 3:1 large (>= 18 pt or 14 pt bold); test the brightest spot under the text, not the average; 4.49 fails [S] https://a11ybot.pages.dev/learn/1-4-3-contrast/ , https://docs.acquia.com/md/web-governance/do-links-top-images-have-minimum-contrast .
- Scrim recipes: a gradient that darkens the text side or the bottom (safe area) [S] developer.amazon.com APL docs; or a fixed dark overlay whose opacity is tuned until 4.5:1 [S] UCLA video banner; e.g. rgba(0,0,0,.55) [S].
- For us [K]: text is HTML (Rubik, Hebrew RTL) in a column on the side that the shot leaves empty (compose every plan with a quiet third: tell the generator "leave the left third dark and uncluttered" for RTL: text on the RIGHT, product/hands on the LEFT). Add a CSS gradient scrim `linear-gradient(to left, rgba(10,10,11,.78), rgba(10,10,11,0) 55%)` plus text-shadow only as a backup; one measured check per block on the worst frame (automated: sample the canvas pixels under the text box, compute contrast).

### 2.8 Hand-over: played clip -> scrubbed sequence
- The transition clip (2-4 s, pack flying into the cabinet) is PLAYED once, muted, `playsinline`, `preload=auto`, started by a click/tap on the product (a user gesture, so autoplay policy is satisfied on iOS). It ends on the same frame as frame 0 of the page's sequence (build rule: last clip frame == first sequence frame, same grade, same crop). Swap: keep the `<video>` last frame visible, draw sequence frame 0 on the canvas beneath, then remove the video next rAF (no flash). Our existing rule is the same idea ("first/last frame is the key exactly, EASE frames blend", video_frames.py).
- If the clip cannot start (low power, Save-Data, reduced motion): skip to the poster = frame 0, navigate instantly.
- Never scrub the transition clip; never play the story clips by time. One mode per segment.

### 2.9 Reduced motion and no-JS
- `prefers-reduced-motion: reduce` -> no scrub, no clip: show one HD still per block (the engine's 'keys' mode does this; also Save-Data) [engine source]. The v2 rule is the same: reduced motion and no JS show the final frame [design-rules.md L507].
- No-JS: server-rendered blocks, each with `<img>` of its key still (`<noscript>` not needed if the img is in the markup and the canvas is added by JS), and the lead form as a plain HTML form posting to a mail/WhatsApp link. Pause control for any autoplaying loop video (WCAG 2.2.2).
- Hebrew RTL: mirror layout, text side flips; frames are NOT mirrored (printed pack text would break) - compose shots with the empty side on the right from the start.

### 2.10 LCP / CLS / INP impact
- LCP element = block-1 poster (or the video poster): preload it, <= 250 KB, serve AVIF/WebP with `srcset` per DPR; target LCP < 2.5 s on mid 4G. The frame stream starts AFTER LCP.
- CLS: stage with fixed aspect-ratio box and `100svh` height (avoid the mobile address-bar jump; use `svh/dvh`), no layout from late-loading frames; the form drawer overlays, never reflows.
- INP: decode off the main thread (our worker + `createImageBitmap`), never decode on the scroll handler; draw in rAF only when the wanted frame changed; free bitmaps outside the window (memory: a 1920x1080 bitmap is ~8 MB decoded, so a window of 13 frames = ~100 MB; on phone 720x1280 = 3.7 MB each) [K, arithmetic].

## 3. Our engine today (read: site/proto/engine/story.js 533 lines, site/proto/story-v2-motion.js 182 lines, site/design/vtech-3d/src/hd/video_frames.py)

Facts read from the code:
- `createFrameStory()` plays RUNS of N frames between screens; frame = share of scroll between two screens; on a screen the key frame holds (HOLD0 0.04, HOLD 0.15, READ 0.85). Config from build-vtech.py: `{runs:[{a,b,n,box}], tiers:[...], cells, ...}`.
- Frame URL: `seq/<tier>/<A>_<B>_<NNN>.webp`; tier picked by `need = cover.w * dpr` -> first tier >= need, else the largest; `capped` devices limited to tiers <= 1600; dpr capped at 2 desktop, 3 phone.
- Decode: fetch + `createImageBitmap(blob, {premultiplyAlpha:'premultiply', colorSpaceConversion:'none'})` in a worker (two at a time), a window of BACK 4 / AHEAD 8 frames around the wanted one, stride grows with scroll velocity, run end frames stay decoded, everything else `bitmap.close()`d. `reset()` on mode/tier change.
- Modes: 'full' | 'keys' (reduced motion or Save-Data: only key frames) | 'off'. Phone: `flow` layout, one block per run, the canvas sits in its block; per-block stills at the canvas scale.
- Canvas drawn at the frame's own size 1:1 inside a per-run crop box (`runs[].box` as fractions of the frame, `clearRect` each draw, then CSS-scaled by the compositor).
- A `SCENE` path draws a live three.js scene instead of frames (the 12 product pages today) - the film pages replace that with frames, or keep the 3D scene only for the home hero (block 1) and the pack in the transition.
- video_frames.py: Kling clip -> n=40 evenly spaced frames, cover-cropped to 2400x1500 (16:10), product on pure black keyed to alpha by brightness (LO .05, HI .16), RGBA WebP q92 alpha_quality 100 method 4, first/last 4 frames blend to the exact key frames.
- Measured weights of the current V-TECH set [M]: 200 frames; tier 2400 = 6.9 MB (avg 32.6 KB/frame), tier 1600 = 4.5 MB (avg 20.6 KB). Tiny because they are cropped alpha cut-outs of a product, mostly transparent.

What changes for full-bleed photoreal film frames (no alpha):
1. Remove keying: `keyed()`, `to_image()`, CLOSE/NEAR/silhouette code and scipy are not needed. New script `film_frames.py`: clip -> N frames, cover-crop to the target aspect (16:9 1920x1080 desktop; 9:16 1080x1920 phone made from its OWN generation or a safe crop, not from the 16:9), `Image.save(..., 'WEBP', quality=72, method=6)` (or `cwebp -q 72 -m 6 -sharp_yuv`), no alpha channel (a 24-bit WebP, no `alpha_quality`). Keep EASE blending to the key stills so neighbour runs meet.
2. Engine: canvas context `getContext('2d', {alpha:false})`; skip `clearRect`; `premultiplyAlpha:'none'` (or default) in `createImageBitmap`; draw full-bleed `cover` (object-fit cover maths) instead of the per-run `box` crop (set box = [0,0,1,1]); tiers become widths 720 / 1280 / 1920 (+2560 optional) with phone-specific 9:16 sets (tier key includes orientation). `pickTier` logic stays (need = cover.w*dpr; phone dpr 3 capped by bytes: choose 720 wide even at dpr 3 and let it upscale slightly; film grain overlay hides softness).
3. Memory: full-bleed bitmaps are 8 MB (1920x1080) vs a few MB for cropped cut-outs: shrink the window on phone (BACK 2 / AHEAD 5) and keep the "capped" rule.
4. Add the blend: draw frame i at alpha 1 and frame i+1 at alpha = fraction (needs both decoded; window already holds neighbours).
5. Add the hand-over: a `<video>` layer for the 2-4 s transition, then `createFrameStory` starts at frame 0 (new small module; no change to the scrub core).
6. Text: the existing HTML blocks stay; add the scrim layer between canvas and text.
7. The 3D pack: stays three.js in the home hero; inside the film the pack comes from our render/packshot composited per Genjutsu replace-object (BRIEF D6), so the frames contain the correct print.

What weight per product page is realistic at HD:
- Desktop 1920x1080 WebP q72, 170 frames x ~120 KB = ~20 MB; trimmed to the budget with 1600-wide tier (x ~75 KB) = ~13 MB, or with holds de-duplicated (about 40% of a film is held shots needing one frame): ~120 frames x 120 KB = ~14 MB.
- Phone 720x1280, 120 frames x ~50 KB = ~6 MB.
- Key-frame-only mode: 10 stills = 1.5 MB / 0.5 MB.
- Compare today: V-TECH 6.9 MB. So film pages are ~2-3x heavier; acceptable only with the progressive loading above, the Save-Data/slow-network drop to keys, and the CDN. All figures [K] estimates built on [M] lower bounds - the first sample page (EXO-NAD) must report the true KB/frame, then we freeze budgets.

## 4. Recommended technique (summary)
1. Two modes only: PLAY (transition clip, 2-4 s, user-gesture started) and SCRUB (the page film as WebP canvas sequence in our engine). No scrubbed `<video>` in production unless the A/B in 2.1 wins.
2. Pinned full-bleed stage, copy as HTML on a scrimmed quiet side; one object that crosses block boundaries (pack -> hands -> product on desk).
3. 150-220 frames desktop (1600-1920 wide), 120-150 phone (720x1280, own composition), WebP q68-74, blend between frames, ease the playhead; hold shots cost one frame.
4. Budgets: LCP poster <= 250 KB; first 12-16 frames <= 1.2 MB; page <= 14 MB desktop / <= 6 MB phone; keys-only fallback 1.5 / 0.6 MB; Save-Data, reduced motion and no-JS get HD stills per block.
5. Anti-cartoon: photoreal stills first (cinema look prompts, one grade for the whole line, grain as overlay), pack from packshot, per BRIEF D6.
6. Measure first: ONE sample (EXO-NAD) -> real KB/frame, decode time on a mid Android and an iPhone, then fix budgets for the other 12.

## 5. Reproduce my measurements
- Image sizes: PIL (WebP/AVIF/JPEG) on protocols/print/img/exosignal-hair.webp cover-cropped to 1920x1080, 1280x720, 768x1366, 540x960, with and without Gaussian noise sigma 3 (lower bound: smooth source).
- Video: ffmpeg libx264 veryfast, 96 frames 1920x1080 from the same image with a pan and noise; compare `-g 48` vs `-g 1`.
- Frame sizes of existing sets: `site/public/v-tech-system/seq/{1600,2400}` (200 files each).
