# MITOTECH CELL BOOSTER — production prompts (v3 clinic film)

Companion of `src/mitotech-cell-booster.md` (the Hebrew chapter is the contract). Shared bible = `prompts/exo-nad.md` §0 (cast
`cast-C01`, room `set-R01`, look, shared negative, aspect plan, MODEL classes): paste it on top of every prompt. Table plate
`set-T05` (`prompts/home.md`). Line accent BOX GREEN `#144434` with a MINT `#78E0BC` edge (measured on `BOX_FRONT_PRINT_R15.pdf`,
to confirm): the uniform's small detail and the shapeless haze around the product only; amber light only inside the booster glass.
MODEL = `per costs.json → <class>`. `research/costs.json` (08/11) gives credit ranges per second, not a per-model table:
Seedance 1080p 9/12/16 cr/s (480p drafts 3 cr/s), Genjutsu swap 2.1–9.6 cr/s, upscale 0–8 cr/s, stills 2/3/6 cr — the
chapter's unit keys (`still`, `video_5s`, `replace_object`, `upscale_video`) are priced from these in `src/98-costs.md`.
Candidate ids from `research/higgsfield-models.json`: `i2v-first-last` → `seedance_2_5` (480p draft → 1080p) or `minimax_hailuo` (faces, emotion); `replace-object` →
`hf_mult_replace_object`; stills → `gpt_image_2_6`. Fill id + params before the first paid run; price + balance, run only after
"approved". Aspect: master 16:9 1920×1080 → upscale ×2; people shots re-generated 9:16 from their own vertical still; product-only
shots rendered from the scene (it has phone poses). Each generated shot ≤ 5 s.

**Product fidelity — the scene is the source of every pack pose:** `site/proto/scenes/mitotech-cell-booster.js` (fitted to the
owner's render R15 `site/design/mitotech/packshot-kit-r15.png`: box corners ≈ 12 px, vials 1 px), rendered with `render-keys.cjs`
at 3840×2400 alpha: p 1 kit in its column (box yaw ≈ 4°) · p 3 the pair large (booster LEFT, powder RIGHT, caps on) · run 4 the R7
preparation (caps then stoppers off; booster turns 115° over the open powder vial and pours, NO stream drawn, the level rises in the
powder vial; stopper for the wait; applicator onto the neck) · p 5 ready vial with applicator + empty booster · p 6 the kit (R15) ·
p 11–15 the five step stills. Print = MITODERM's vector files (`site/design/mitotech/print/`): no text of ours. Methods (a) composite,
(b) i2v + `replace-object` with our render, (c) three.js motion composited.
PACKAGING: closed green box (front 'MITOTECH®' / 'CELL BOOSTER', faceted mint diamond, mint strips 'Advanced skin to cell delivery
technology', '−70°C', vertical 'MITODERM'); sides and top plain green as the thin slivers on R15 show; the back print exists
(`BOX_BACK_PRINT_R15.pdf`) but the depth is unknown, so the back is never shown; the box NEVER opens. Row of 8 20R vials: 4 Boosting
Ampoules in AMBER GLASS with colourless content (R15), 4 Concentrated Powder vials (white cake hidden by the label), green labels,
white flip caps with aluminium rings; the 5th vial carries the clear applicator.
**THREE OPEN ANSWERS GATE THE CONTENTS:** amber = glass or liquid; ready solution clear («שקופה», b4.line) or cloudy (R7 step 4);
what is under the white cap. Until answered: contents hidden by the label, pour = scene render (no stream), never a close-up of the
liquid's colour, never invent a stopper.
**Extra negative (all shots):** `no needle, no microneedling pen, no syringe in frame, no dropper pipette other than the kit's
applicator, no spilled or overflowing liquid, no foam, no coloured liquid unless MITODERM confirms it, no opened box, no extra vials,
no new or changed label text, no glow or smoothing added to the skin`.

**Stills first:** `mitotech-cell-booster-K01` client casting, 4:5 ×2 — `Portrait photograph in set-R01: a woman about 50, Fitzpatrick
II–III, no make-up, white towelling headband, light robe open at the neck; real skin with a dry, tired look, fine lines around the
eyes and mouth, the neck and jawline slightly less firm — subtle and dignified, never a caricature; 50mm f/2, window light from the
right, fine grain.` `clinic-table-mitotech-cell-booster` = `set-T05` with soft shapeless dark-green haze and a faint mint edge.

| shot | purpose · s · scroll | start → end frame | still prompt (key) | video prompt | model · fidelity | QA |
|---|---|---|---|---|---|---|
| F01 | rung 1, the kit on the table · 3 · 0–100 | `clinic-table-mitotech-cell-booster` + scene p 1 (R15 kit) → 12 % tighter | none (composite) | none (eased crop) | none · (a) | ΔE ≤ 8 vs R15; 4 + 4 vials, one applicator; amber only on boosters; frame 0 = end of the home transition |
| F02 | rung 2, "I see myself" · 4 · 100–240 | S02a → S02b | S02a: `Over-the-shoulder into the brass-rimmed mirror: client mitotech-cell-booster-K01 in the treatment chair, fingertips tracing her jawline down to her neck, a thoughtful look; right third dark wall; 50mm f/2, window light right, real skin.` S02b: same + `cast-C01 behind her, hand on her shoulder, eyes meet in the mirror, calm confident half-smile.` | `Start exactly on the first frame and end exactly on the last. Her fingertips run along the jaw to the neck; the cosmetologist rests a hand on her shoulder; eyes meet in the reflection. Slow lateral dolly, 50mm, one take, 4 s.` | i2v-first-last, char refs C01+K01 · no product | fingers; mirror; no caricature; same face as F07/F09 |
| F03 | transition, the box arrives · 4 · 240–340 | plate with the row of 8 (scene p 6 without the box) → p 6 (= F04 frame 0) | none | three.js: the closed box glides in from room depth, turning ≤ 30° (front and plain green side catch the window light), squares to camera and lands behind the row exactly as R15, small settle, contact shadow; 40 frames 3840 alpha. Paid fallback: i2v + replace-object | none / i2v + replace-object | no back face shown (depth unknown, no dieline); turn ≤ 30° as in the live scene's opening run; box closed; no float |
| F04 | rung 3, discovery + "open the vials" · 3 · 340–460 | F03 last → S04 → S04b | S04: `Three-quarter high angle over cast-C01's shoulder, pale nitrile gloves: she holds a Boosting Ampoule (left hand) and a Concentrated Powder vial (right hand) up to the window light, labels toward camera (our render, pose p 3), the amber glass glowing; eyebrow lifted, small smile; 50mm f/2.2.` S04b: `both vials standing on the table, caps and stoppers lifted off and set beside them, seen from the side at a distance (scene step still p 11).` | `Start on the first, end on the last. She lifts the pair to the light, sets them down and takes off the white caps and the stoppers. One take, 3 s.` | i2v-first-last + replace-object (both vials) | booster left / powder right; labels sharp; under-cap detail only from MITODERM's photo; gloves' fingers |
| F05 | rung 3, "slowly, no shaking" · 2 · 460–520 | DEFAULT scene run 4 (36–66 %) on a macro table plate; FULL M05 | FULL M05 (after the answers): `Macro 100mm: the amber booster tilted over the open powder vial, neck over neck, pouring slowly along the inner wall; [clear / cloudy per MITODERM] liquid.` | DEFAULT three.js: booster turns 115°, its level falls while the level rises in the powder vial, no stream; FULL: `Start on the first, end on the last. A slow careful pour, no overflow, no shaking. Locked macro, 2 s.` | DEFAULT none (0 credits) · FULL i2v-first-last | no foam, no overflow; content colour only per the answers |
| F06 | rung 4, "wait one hour", "shake well" · 3 · 520–640 | (a) scene step still p 13 (stoppered vial + empty booster) on the plate, light sweep in our pipeline → (b) S06a → S06b | S06a: `Close, 85mm: cast-C01's gloved fingers seating the clear applicator on the powder vial's neck (scene pose p 14), label toward camera.` S06b: same, `she shakes the vial firmly, a few small bubbles, the label hides the content.` | (a) none; (b) `Start on the first, end on the last. She presses the applicator on and shakes the vial hard. Locked, 2 s.` | (a) none · (b) i2v-first-last + replace-object (vial + applicator) · THIS FILM'S SAMPLE SHOT | the hour is shown only by the window light moving; bubbles allowed (prep_note); applicator per R15 |
| F07 | rung 4, "apply" · 3 · 640–720 | S07a → S07b | S07a: `Macro 100mm: the ready vial upside down, applicator down (scene step still p 15), a gloved fingertip under it, a light press releasing a small amount of serum onto the fingertips; client K01 lying back, eyes closed.` S07b: `85mm: gloved fingertips massaging a thin light layer along her jawline and down her neck until absorbed, profile, window light; the décolleté stays out of frame.` | `Start on the first, end on the last. A light press on the applicator, then the fingertips spread the serum along the jawline and down the neck and massage until absorbed. Short dolly, 3 s.` | i2v-first-last + replace-object (vial) | thin transparent film (colour per answer); no tool on the skin; skin identical in both frames |
| F08 | proof · 5 · 720–860 | MITODERM `media/mitotech-cell-booster/ba-01-before/after.jpg` (face + neck; not in git) | none | CSS wipe 760–860vh | none | signed consent; no retouch; dropped if none |
| F09 | joy + home programme · 4 · 860–980 | S09a → S09b | S09a: `50mm: client K01 holding a hand mirror, touching her neck and cheek; cast-C01 behind her; skin exactly as in S02a.` S09b: same, `she smiles with relief; the cosmetologist, proud, places the ready vial with its applicator (our render, pose p 5) into her free hand.` | `Start on the first, end on the last. She looks, touches her neck and smiles; the cosmetologist places the vial in her hand. Slow dolly-in, 4 s.` | i2v-first-last, char refs + replace-object (vial) | no skin change; same faces; vial = R15 5th vial |
| F10 | rung 5, offer · 3 · 980–1100 | S10a → S10b | S10a: `35mm: cast-C01 alone leaning on the table, her hand on the closed green box, the row of vials before it (scene p 6), eyes lowered; right third dark wall.` S10b: same, `eyes to camera, warm and confident.` | `Start on the first, end on the last. She lifts her eyes to the camera. Locked, 3 s.` | i2v-first-last + replace-object (kit), very low motion | print under her hand; eyes alive; right third free |
| F11 | family · 2 · 1100–1180 | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` + R15 card (phone `phone-b/a.webp`) | none | engine dissolve + zoom-out; MITOTECH card glows mint | none | no AI crowds or events |

**Order:** after the EXO-NAD sample is approved and the three open answers are in: K01 + table → owner OK → F06 as this film's
sample → 480p → OK → rest; FULL F05 only after the answers. 2–4 attempts per paid item; nothing that fails QA goes to the site.
People stills are not committed to git.
