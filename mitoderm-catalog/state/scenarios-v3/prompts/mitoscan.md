# MITOSCAN — production prompts (v3 clinic film)

Companion of `src/mitoscan.md` (the contract: shots, scroll ranges, approved texts). Shared bible = `prompts/exo-nad.md` §0
(cast-C01, set-R01, the table plates set-T01…T06, look, shared negative, MODEL classes, aspect plan); paste it on top of every prompt.
Line overrides: the table plate of this film is `set-T04` (silver haze #d9d4cc, `src/02-production.md` §3), not the champagne T01;
accent detail on the tunic = thin SILVER piping (#d9d4cc); haze around the device #d9d4cc; NO blue glow (removed in v2.1; the blue
drop #5aa9e6 of `design-rules.md` is an open decision, chapter F03).
MODEL ids (`research/costs.json`, `r3-ai-video.md` §2, `src/02-production.md` §5; published prices conflict — confirm on the cost
button before every run): i2v-first-last = `seedance_2_5` (start_image + end_image, 4–5 s, 1080p, 16:9 / 9:16, omni_reference for
cast-C01 / K01; 480p draft → finalize 1080p within 7 days; needs the Plus plan or above); facial emotion (F02, F10) = `minimax_hailuo`
(start + end image, 6 s, 1080); replace-object = `hf_mult_replace_object` (ref = our render; drafts `hf_mult_replace_object_flash`);
stills = `gpt_image_2_6` (alternatives `nano_banana_pro`, `soul_2`); upscale = `upscale_video` ×2 (price unpublished); the screen
region is always our planar-track composite, 0 credits. Balance 1 credit, free plan (08/11): nothing runs before the owner pays;
price + balance to the owner, run after "approved".
Every 16:9 shot with people is generated AGAIN in 9:16 from its own vertical still (suffix `-v`); device-only shots are rendered.

**SYSTEM (what the camera may see — `packaging-text.json` mitoscan, `mitoscan.js`; never retyped by the generator):** white
tablet on a white stand, black screen with a teal-to-purple target logo, 'Mitoscan' and 'By Mitoderm Ltd'; a white handheld
scanner in its cradle at the tablet's right with a black oval panel 'Mitoscan' / 'By Mitoderm Ltd'; a white coiled cable; a
brushed silver cylinder with chrome ends and a small 'Mitoscan' badge in front. Photographed range only: front three-quarter
from the right, azimuth ≤ 26°, elevation ≤ 9°.

**SCREEN RULE (hard):** the generator never paints the screen. Every frame with the screen in view gets the screen region
replaced in our pipeline (planar track + composite) by either the packshot logo screen (SAFE) or a real MITODERM screen capture
with signed consent (FULL, `media/mitoscan/scan-01-x50.jpg`, `-x200.jpg`). In prompts the screen is "showing only its logo".

**Line negative (append after the shared negative):** `no microscope or trichoscopy image, no hair or scalp close-up on the
screen, no charts, numbers, graphs, measurements or UI on the screen, no blue glow, no back of the tablet, no scanner seen from
its unphotographed side, no scanner lens or tip visible, no empty cradle (SAFE version), no finger touching the screen, no
stretched or floating cable, no bald caricature, no hair thickening or thinning between shots, no labels on the silver cylinder
other than its badge`.

**Product fidelity:** system = `site/proto/scenes/mitoscan.js` via `render-keys.cjs` (v1-meet … v6-kit, 3840×2400, alpha) /
packshot `protocols/print/img/mitoscan.webp` (1145×777; HD pending). Method (a) composite into stills, (b) first/last frame +
`hf_mult_replace_object` (scanner / tablet), (c) screen region always composited by us. QA every frame: print legible on the
panel and the screen logo, whites ΔE ≤ 8 vs packshot, angles inside the photographed range, scanner tip hidden.

**Casting still `mitoscan-K01`** (4:5, front + profile + crown from above, still-photoreal): `Portrait photograph in set-R01
(reference attached): a man about 38, short-to-medium dark hair with subtle, realistic thinning at the crown, dark crew-neck
shirt, seated in the treatment chair, calm and a little shy, real skin and hair texture, 50mm, f/2, window light from the
right, fine grain.` QA: thinning subtle and dignified; the crown IDENTICAL in every later shot.

| shot | purpose · s · scroll · aspect | start → end frame | still prompt (key frame) | video prompt | extra negative | model + params · fidelity | QA |
|---|---|---|---|---|---|---|---|
| F01 | system on the table, rung 1, home continuity · 3 s · 0–100 · 16:9, 9:16 crop | `set-T04` + `still.webp`/`v1-meet.png` → tighter crop | — (composite) | — (dolly-in in our pipeline) | — | none, 0 credits | cable loops on the table; logo sharp; right third calm |
| F02 | concern: he cannot see his own crown · 4 s · 100–240 · 16:9 + `-v` | `S02a` → `S02b` | `Over-the-shoulder into the round brass mirror in set-R01: mitoscan-K01 in the chair holds a hand mirror above and behind his head, tilting it, squinting, trying to see his crown.` / b: `same, cast-C01 behind him, a hand on his shoulder; he lowers the hand mirror with a shy smile; eyes meet in the big mirror.` | `Slow lateral dolly; he tilts the hand mirror, cannot quite see; the cosmetologist steps in and rests a hand on his shoulder; he lowers the mirror and smiles shyly; eyes meet. Ends exactly on the last frame.` | `no visible device` | i2v-first-last 5 s, 1080p | reflections consistent in both mirrors; 5 fingers; crown = K01 |
| F03 | glide: system lands by the chair · 3 s · 240–315 · rendered 16:9 and 9:16 | `set-T04` → system on table + gloved hand on the stand (= F04 start) | — | — (three.js glide added to `mitoscan.js`: azimuth 26° → 18°, el ≤ 9°, all parts as one, per-frame shadow) | — | three.js, 0 credits; fallback i2v + replace-object | angles in range; scanner stays in cradle; cable rigid in loops; no hover |
| F04 | discovery: hand on the scanner, quiet wow · 3 s · 315–430 · 16:9 + `-v` | F03 end → `S04` | `cast-C01's gloved hand rests on the white handheld scanner in its cradle (reference render attached), black 'Mitoscan' panel toward camera; the tablet screen showing only its logo; her face in soft focus, eyebrow raised, small smile; 50mm.` | `Her hand closes around the scanner in its cradle; she looks from the scanner to the screen with a raised eyebrow and a quiet smile. The scanner stays in its cradle. Ends exactly on the last frame.` | — | i2v-first-last 5 s (use 3 s); scanner replace-object; screen composited | FULL version (lift from cradle) only after photos of all sides + empty cradle |
| F05 | what the eye cannot see: ×50 → ×200 · 3 s · 430–505 | real captures `scan-01-x50.jpg` → `scan-01-x200.jpg` in our screen frame; fallback: render macro panel → logo | — | — (push-in + dissolve in our pipeline) | — | none, 0 credits | NEVER generated, upscaled with AI or retouched; consent signed |
| F06 | ritual: scan at the parting · 2 s · 505–595 · 16:9 + `-v` · SAMPLE SHOT | `S06a` → `S06b` | `Three-quarter top view 85mm: cast-C01's gloved fingers open a parting at the crown of mitoscan-K01.` / b: `her other hand holds the white scanner (reference render) against the parting, black panel toward camera, the tip lost in the hair, the coiled cable falling naturally.` | `Gloved fingers open a parting at the crown; the other hand brings the scanner to it and holds it still; he sits calmly. Short dolly to the parting. Ends exactly on the last frame.` | `no lens visible` | i2v-first-last 3 s; scanner replace-object | tip hidden; cable relaxed; real hair |
| F07 | ritual: explaining on the screen · 3 s · 595–670 · 16:9 + `-v` | `S07a` → `S07b` | `Camera just beside the tablet, over its right edge, 50mm: mitoscan-K01 and cast-C01 look at the screen (screen showing only its logo, seen at the photographed angle); she points toward the image without touching.` / b: `he leans in and nods.` | `She explains quietly, pointing toward the screen without touching it; he leans in, listens and nods. Locked camera. Ends exactly on the last frame.` | `no touch on the glass` | i2v-first-last 5 s (use 3 s); tablet replace-object; screen composited (logo or real ×200) | screen region replaced in every frame; no tablet back |
| F08 | ritual: tracking — the same spot, another visit · 2 s · 670–720 · 16:9 + `-v` | `S08a` → `S08b` | `Same framing as S06 but morning light and a different shirt colour on mitoscan-K01: the scanner again at the same point of the same parting.` | `The scanner comes to the same point of the same parting and holds still. Same framing as F06. Ends exactly on the last frame.` | `no change in hair density vs F06` | i2v-first-last 3 s; scanner replace-object | hair = F06 frame-by-frame; no marking shown |
| F09 | proof: real MITOSCAN before/after, same area · 5 s · 720–860 | MITODERM files `media/mitoscan/scan-01-before/after.jpg` (+ optional `ba-01-*`) | — | — (CSS clip-path wipe) | — | none | same area + magnification; treatment named; absent → dropped |
| F10 | joy: "the patient sees it too" · 4 s · 860–1000 · 16:9 + `-v` | `S10a` → `S10b` | `mitoscan-K01 looks at the screen (logo only, composited later), exhales and smiles with relief; cast-C01 beside him, quiet proud smile; 50mm, window light. Face and crown IDENTICAL to K01.` | `Slow dolly-in to both; he exhales, smiles, turns to her and nods; she smiles quietly. Ends exactly on the last frame.` | `no improved hair` | i2v-first-last 5 s; character refs cast-C01, K01; tablet replace-object; screen composited | natural smile; screen never generated |
| F11 | rung 5: "you can be her" · 3 s · 1000–1115 · 16:9 + `-v` | `S11a` → `S11b` | `cast-C01 alone leaning on the side table beside the MITOSCAN system (our render composited, photographed angle), one hand on the scanner in its cradle; a: looking at the screen (logo); b: looking into the lens, warm and confident; 35mm, right third dark wall.` | `She raises her gaze from the screen to the camera with calm, confident warmth. Locked camera.` | — | i2v-first-last 5 s (use 3 s); system replace-object | live eyes; print; right third dark |
| F12 | family: line image · 2 s · 1115–1205 | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` (devices area) | — | — (dissolve + zoom-out) | — | none | no AI crowd/event |

**9:16 notes:** F02, F04, F06, F07, F08, F10, F11 regenerated vertical (`-v` stills, same prompts + "vertical 9:16 framing, subject
in the middle 46% band"); F03 rendered 9:16 from `mitoscan.js`; F01 centre crop; F05/F09 real images cropped square in the stage.
**Order of runs:** after the EXO-NAD sample is approved and MITODERM sends the scanner photos / a scan video (chapter §7) → K01
stills → owner's OK → F06 sample (most sensitive) → rest. Screen compositing is our pipeline work, 0 credits.
