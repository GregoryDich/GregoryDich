# DERMA RECOVERY CREAM — production prompts (v3 clinic film)

Companion of `src/derma-recovery-cream.md` (the Hebrew chapter is the contract). Shared bible = `prompts/exo-nad.md` §0 (cast
`cast-C01`, room `set-R01`, look, shared negative, aspect plan, MODEL classes): paste it on top of every prompt. Table plate
`set-T03` (BIOSPICULE green, `prompts/home.md`). Line accent BIOSPICULE GREEN `#1E4634` with DERMA SAGE `#9AA889` at the glow's
heart: the uniform's small detail and the shapeless haze around the product only.
MODEL = `per costs.json → <class>`. `research/costs.json` (08/11) gives credit ranges per second, not a per-model table:
Seedance 1080p 9/12/16 cr/s (480p drafts 3 cr/s), Genjutsu swap 2.1–9.6 cr/s, upscale 0–8 cr/s, stills 2/3/6 cr — the
chapter's unit keys (`still`, `video_5s`, `replace_object`, `upscale_video`) are priced from these in `src/98-costs.md`.
Candidate ids from `research/higgsfield-models.json`: `i2v-first-last` → `seedance_2_5` (480p draft → 1080p) or `minimax_hailuo` (faces, emotion); `i2v-loop` → `kling3_0_turbo`
(start frame only); `replace-object` → `hf_mult_replace_object`; stills → `gpt_image_2_6`. Fill id + params from costs.json before the
first paid run; price + balance to the owner, run only after "approved". Aspect: master 16:9 1920×1080 → upscale ×2; shots with
people re-generated 9:16 from their own vertical still; product-only shots rendered or cropped. Each generated shot ≤ 5 s.

**Product fidelity:** box + jar = OUR three.js scene `site/proto/scenes/derma-recovery-cream.js` via `render-keys.cjs` (3840×2400,
alpha; `v1-meet.png` … `v6-kit.png`; page copies `site/public/derma-recovery-cream/img/still.webp`, `kit.webp`, `m3.webp`). Box
62 × 62 × 85 mm, every face from the dieline (`site/design/biospicule/panels/derma-recovery-cream/`) → full turn allowed. JAR: only
its front was photographed (owner's Figma photos 1 and 73) → yaw ≤ ±20°. Methods (a) composite, (b) i2v + `replace-object` with our
render, (c) three.js motion composited. PACKAGING: wide ivory box; gold M monogram; 'MITODERM' / 'BIOSPICULE SYSTEM'; SAGE band
(dieline; the angled packshot and `protocols/print/img/derma-recovery.webp` show dark green — unconfirmed) with gold 'DERMA RECOVERY' / 'CREAM'; bold dark green 'SNAIL
COLLAGEN'; printed white cream swirl; gold-framed 'Daily nourishing collagen cream' / 'for healthy-looking glow'; '50 ml ℮ 1.69
fl.oz.'. JAR 50 ml: white body, glossy black collar, frosted translucent lid over a white top (lid lined with matte white plastic),
vertical 'MITODERM' / 'BIOSPICULE SYSTEM', 'DERMA / RECOVERY / CREAM', 'SNAIL COLLAGEN', 'MADE IN KOREA' (`jar-label.png`), Ø:H
1:1.31. LID MECHANIC: lifts straight up and rests beside the jar (photo 73); no unscrewing spin until MITODERM answers.
**CREAM IS BLOCKING:** never photographed. Until MITODERM's photo: no cream visible inside the jar, F05 runs the three.js FALLBACK,
F04 ends with the lid beside the jar, and in F06/F09 the cream is already a thin layer on the fingertips (no colour invented beyond
"thin, soft, light film").
**Extra negative (all shots):** `no spatula, spoon or brush, no other products in hand, no pump or tube, no cream ribbon in the air,
no pearls, flakes or particles, no drawn redness, peeling or irritation, no glow or smoothing added to the skin, no beard stubble
change between frames, no logos in the bathroom`.

**Stills first:** `derma-recovery-cream-K01` client casting, 4:5 ×2 — `Portrait photograph in set-R01: a man about 36, Fitzpatrick
V, clean-shaven, white towelling headband, light robe, sitting in the treatment chair at the end of an in-clinic facial treatment;
real skin texture with a slightly dry, tight look across the cheeks — subtle, no redness, dignified; 50mm f/2, window light from the
right, fine grain.` `clinic-table-derma-recovery-cream` = `set-T03` with soft shapeless green haze and a sage `#9AA889` heart.
`set-H01` (NEW, owner's OK): `Editorial photograph of a calm, simple home bathroom in the evening: a mirror over a light stone sink,
warm soft light above the mirror, a folded towel, no products, no brands, the right third dark tiles in shadow; cinema camera, 35mm,
natural light, fine grain, no people.`

| shot | purpose · s · scroll | start → end frame | still prompt (key) | video prompt | model · fidelity | QA |
|---|---|---|---|---|---|---|
| F01 | rung 1, jar + box on table · 3 · 0–100 | `clinic-table-derma-recovery-cream` + our `v6-kit.png` (box and closed jar side by side) → 12 % tighter | none (composite) | none (eased crop) | none · (a) | ΔE ≤ 8; sage band per dieline; contact shadows; frame 0 = end of the home transition (jar leads, box follows) |
| F02 | rung 2, "it feels tight" · 4 · 100–240 | S02a → S02b | S02a: `Over-the-shoulder into the brass-rimmed mirror: client derma-recovery-cream-K01 in the treatment chair after the treatment, fingertips on his cheek, a slight frown — the skin feels tight and dry; right third dark wall; 50mm f/2, window light right, real skin.` S02b: same + `cast-C01 behind him, gloved hand on his shoulder, eyes meet in the mirror, calm reassuring half-smile.` | `Start exactly on the first frame and end exactly on the last. He touches his cheek and frowns slightly; the cosmetologist rests a hand on his shoulder; eyes meet in the reflection. Slow lateral dolly, 50mm, one take, 4 s.` | i2v-first-last, char refs C01+K01 · no product | fingers; mirror geometry; no drawn redness; same face as F06/F07/F09 |
| F03 | transition, the jar and box arrive · 4 · 240–340 | F01 plate without products → both landed + gloved hand on the jar (= F04 frame 0) | none | three.js: the closed jar glides in first, front to camera, yaw ≤ 20°; the box follows with a slow full turn about its vertical axis (all printed faces; the unprinted crash-lock bottom never shows), both slow and land side by side in the kit pose with a small settle, contact shadows; 40 frames 3840 alpha. Paid fallback: i2v + replace-object | none / i2v + replace-object | jar never shows its unphotographed back; no blank box face; no float |
| F04 | rung 3, discovery · 3 · 340–460 | F03 last → S04 | S04: `Three-quarter high angle over cast-C01's shoulder, pale nitrile gloves: the frosted lid lifted straight off and resting beside the open white jar (our render composited, v3-inside pose), its plain white top visible; she looks down at it, eyebrow lifted, small smile; 50mm f/2.2.` FULL (after the cream photo): `she holds a little cream on a gloved fingertip up to the window light.` | `Start on the first, end on the last. Her gloved hands lift the frosted lid straight up and set it beside the jar [FULL: she takes a little cream on a fingertip and raises it to the light]; small smile. One take, 3 s.` | i2v-first-last + replace-object (jar, lid) | lid moves straight up only; print sharp; no spatula; no cream before the photo |
| F05 | rung 3, texture · 2 loop · 460–520 | FALLBACK: our scene pose S3 (`v3-inside.png`, open jar + lid). FULL: M05 | FULL M05: `Macro 100mm: a small amount of the cream on a gloved fingertip, window light sliding over its sheen; colour and texture exactly as MITODERM's photo.` | FALLBACK three.js: a soft white light sweep over the frosted lid, 2 s loop. FULL: `Start on the first frame; the light slides over the cream; seamless 2 s loop.` | FALLBACK none (0 credits) · FULL i2v-loop | cream colour only from the photo; no ribbon, no particles, no text |
| F06 | rung 4, the finishing step · 3 · 520–640 | S06a → S06b | S06a: `Macro profile, 100mm: client K01 lying back, eyes closed; gloved fingertips with a thin soft layer of cream on his cheekbone, after the treatment.` S06b: same, `fingertips at the jawline, the layer smoothed in; his shoulders relaxed, a slow exhale.` | `Start on the first, end on the last. Gloved fingertips smooth a thin layer of cream over the cheek and along the jaw in soft gliding strokes, no rubbing; he exhales and relaxes. Short dolly, shallow depth of field, 3 s.` | i2v-first-last · THIS FILM'S SAMPLE SHOT | thin film, not a white mask; skin identical in both frames; no redness; fingers |
| F07 | rung 4, the routine goes home · 3 · 640–720 | S07a → S07b | S07a: `Close, 85mm: cast-C01's bare hands placing the closed DERMA RECOVERY CREAM jar (our render) into the client's open palms, print toward camera.` S07b: same, `she lifts the frosted lid straight up to show him; he nods.` | `Start on the first, end on the last. The jar is placed into his palms; she lifts the lid straight up to show him and puts it back; he nods. Locked, 3 s.` | i2v-first-last + replace-object (jar) | print sharp; Ø:H 1:1.31; lid straight up only; fingers |
| F08 | proof · 5 · 720–860 | MITODERM `media/derma-recovery-cream/testimonial-01.jpg` + quote, or `ba-01-before/after.jpg` (not in git) | none | quote card or CSS wipe 760–860vh | none | signed consent; verbatim quote with name; dropped if none |
| F09 | joy, at home · 4 · 860–980 | S09a → S09b | S09a: `set-H01, evening, over-the-shoulder into the bathroom mirror: client K01 with a clean face, the open DERMA RECOVERY CREAM jar on the sink with its print toward camera (our render), the lid beside it; he takes a little cream on his fingertips; skin exactly as in S02a.` S09b: same, `he has smoothed it over his cheek, touches the cheek and smiles at himself — comfort, not an advert.` | `Start on the first, end on the last. He smooths the cream over his cheek, touches it and smiles at his reflection. Slow dolly-in, 50mm, 4 s.` | i2v-first-last, char ref K01 + replace-object (jar on the sink) | same face as F02; no skin change; no other brands; jar print sharp |
| F10 | rung 5, offer · 3 · 980–1100 | S10a → S10b | S10a: `35mm, back in set-R01: cast-C01 alone leaning on the table, the box and the jar beside her (our render, v6-kit pose), a quiet proud smile, eyes lowered; right third dark wall.` S10b: same, `eyes to camera, warm and confident.` | `Start on the first, end on the last. She lifts her eyes to the camera. Locked, 3 s.` | i2v-first-last + replace-object (kit), very low motion | eyes alive; print; right third free for the form |
| F11 | family · 2 · 1100–1180 | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` (phone `phone-b/a.webp`) | none | engine dissolve + zoom-out; DERMA hotspot glows green | none | no AI crowds or events |

**Order:** after the EXO-NAD sample is approved: K01 + `set-H01` + table → owner OK → F06 as this film's sample → 480p → OK → rest;
FULL versions of F04/F05 only after the cream photo. 2–4 attempts per paid item; nothing that fails QA goes to the site. People
stills are not committed to git.
