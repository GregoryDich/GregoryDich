# CELLULAR AGE DEFENSE 2.5% — production prompts (v3 clinic film)

Companion of `src/cellular-age-defense-2-5.md` (the Hebrew chapter is the contract). Shared bible = `prompts/exo-nad.md` §0 (cast
`cast-C01`, room `set-R01`, table `set-T01`, look, shared negative, aspect plan, MODEL classes): paste it on top of every prompt.
Line accent BIOSPICULE GREEN `#1E4634` (glow core `#2F6A50`). MODEL = `per costs.json → <class>` (costs.json not on disk at writing
time; fill id + params before the first paid run; price + balance, run only after "approved"). Aspect: master 16:9 1920×1080 →
upscale ×2; shots with people re-generated 9:16 from their own vertical still; product-only shots rendered or cropped. ≤ 5 s each.

**Product fidelity:** TWO boxes, both OUR three.js scenes via `render-keys.cjs` (3840×2400, alpha): this one
`site/proto/scenes/cellular-age-defense-2-5.js` (page copies `site/public/cellular-age-defense-2-5/img/still.webp`, `kit.webp`,
`m3.webp`) and the previous step `site/proto/scenes/cell-renew-1-5.js` (page copy `site/public/cellular-age-defense-2-5/img/cell-renew-15.webp`).
Both 35 × 35 × 110 mm, every face from the dieline (`site/design/biospicule/panels/<slug>/`) → full turn allowed. Methods (a)
composite, (b) i2v + `replace-object`, (c) three.js motion composited. PACKAGING (2.5%): tall ivory box; gold M monogram; 'MITODERM'
/ 'BIOSPICULE SYSTEM'; DARK green band (≈ `#183020` on the dieline) with gold 'CELLULAR AGE' / 'DEFENSE 2.5%'; 'BIOSPICULE' / 'SERUM'; medallion in a dark green
ring; gold-framed 'ADVANCED' / 'BIOSPICULE TECHNOLOGY'. The 1.5% box has a MEDIUM green band (≈ `#4a7b5b`) — the two must read as different.
**BOTTLE IS BLOCKING:** white airless pump bottle per Figma photo 9 (not in the repo, small); its print says 'CELL CELLULAR / AGE
DEFENSE / 2.5%' vs the dieline label 'CELLULAR AGE DEFENSE 2.5%' — unresolved. F04, F06 run the FALLBACK (boxes only, serum already
on the fingertips) until photos + the answer arrive.
**Extra negative (all shots):** `no bottle unless composited from MITODERM's photo, no dropper, no spatula or brush, no other
products, no gold threads or glowing particles, no sparkles on skin, no rubbing or pressing hard, no drawn redness, no wrinkle
smoothing or skin change between shots`.

**Stills first:** `cellular-age-defense-2-5-K01` client casting, 4:5 ×2 — `Portrait photograph in set-R01: a man about 50, Fitzpatrick
III, short greying hair, a plain dark shirt; real mature skin with forehead lines and crow's feet, slightly less firm, tired dull tone
— dignified, warm, never a caricature; 50mm f/2, window light from the right, fine grain.` `clinic-table-cellular-age-defense-2-5` =
`set-T01` with soft shapeless GREEN haze and the 1.5% box (our render) standing at the left of the product spot.

| shot | purpose · s · scroll | start → end frame | still prompt (key) | video prompt | model · fidelity | QA |
|---|---|---|---|---|---|---|
| F01 | rung 1, box on table · 3 · 0–100 | `clinic-table-…` + our 2.5% `still.webp` box (1.5% box out of frame) → 12 % tighter | none (composite) | none (eased crop) | none · (a) | ΔE ≤ 8; dark-green band; contact shadow |
| F02 | rung 2, "when the lines start to bother" · 4 · 100–240 | S02a → S02b | S02a: `Over-the-shoulder into the brass-rimmed mirror: client K01 seated, eyebrows raised, looking at his forehead lines, fingertips at the corner of his eye; the CELL RENEW 1.5% box (our render) blurred on the side table; right third dark wall; 50mm f/2.` S02b: same + `cast-C01 behind him, hand on his shoulder, eyes meet in the mirror, calm half-smile.` | `Start exactly on the first frame and end exactly on the last. He raises his brows and looks; the cosmetologist rests a hand on his shoulder; eyes meet in the reflection. Slow lateral dolly, 50mm, 4 s.` | i2v-first-last, char refs C01+K01 + replace-object (1.5% box) | fingers; mirror; real lines, not exaggerated; same face as F07/F10 |
| F03 | transition, the next step arrives · 4 · 240–340 | plate with the 1.5% box → 2.5% box landed beside it + gloved hand | none | three.js: 2.5% box from room depth, slow full turn, slows, lands beside the 1.5% box, half a step in front of it (the next step forward), small settle, contact shadow; 40 frames 3840 alpha. Paid fallback: i2v + replace-object | none / i2v + replace-object | same size boxes; two band shades; no float |
| F04 | rung 3, discovery · 3 · 340–440 | F03 last → S04 | S04: `Three-quarter high angle over cast-C01's shoulder, pale nitrile gloves: she holds the 2.5% box and the 1.5% box side by side (our renders) up to the window light, comparing; eyebrow lifted, small smile.` FULL (after the bottle photos, the open-box photo and the print answer): `the 2.5% top flap open, the airless bottle (MITODERM photo) in her hand.` | `Start on the first, end on the last. She lifts both boxes to the light and compares them, small smile [FULL: opens the flap, slides out the bottle]. One take, 3 s.` | i2v-first-last + replace-object (both boxes; bottle from photo) | both prints exact; right box in the right hand; flap only on its hinge |
| F05 | rung 3, texture (illustration) · 2 loop · 440–500 | our scene pose S3 (`m3.webp`, denser cloud) | none | three.js loop: a denser cloud of loose fine silica spicules (the catalogue's mineral needles) swaying in green haze; HTML tag "illustration" | none (0 credits) | denser than 1.5%; no tip-on views; no figures |
| F06 | rung 4, demonstration · 3 · 500–620 | S06a → S06b | S06a: `Macro profile, 100mm: client K01 seated, eyes closed; gloved fingertips with a thin film of serum on his clean dry forehead.` S06b: same, `the thin layer massaged in gently.` [FULL: open on one pump press.] | `Start on the first, end on the last. Fingertips spread a thin layer across the forehead with gentle circles, never rubbing. Short dolly, 3 s.` | i2v-first-last | lines unchanged; thin film; fingers |
| F07 | rung 4, "you will feel it" · 3 · 620–700 | S07a → S07b | S07a: `50mm over-the-shoulder into the mirror: client K01 opening his eyes with a brief surprised look; cast-C01 smiling, an open-hand "gently" gesture.` S07b: same, `he nods and lightly smooths his own forehead with his fingertips, calm.` | `Start on the first, end on the last. He feels the tingling, looks surprised, she reassures with a gesture, he nods and touches his forehead gently. Locked, 3 s.` | i2v-first-last · THIS FILM'S SAMPLE SHOT | honest, restrained reaction; no redness; same man |
| F08 | rung 4, the routine steps up · 2 · 700–760 | S08a → S08b | S08a: `Close, 85mm: cast-C01's hands placing the 2.5% box (our render) into the man's open palms; the 1.5% box blurred behind on the table.` S08b: `the 2.5% box in his hands, band and medallion toward camera.` | `Start on the first, end on the last. The box is placed into his palms; his hands close around it. Locked, 2 s.` | i2v-first-last + replace-object | the right box (dark green); print sharp; fingers |
| F09 | proof · 5 · 760–900 | MITODERM `media/cellular-age-defense-2-5/testimonial-01.jpg` + quote, or `ba-01-before/after.jpg` (not in git) | none | quote card or CSS wipe 800–900vh | none | consent; verbatim quote; dropped if none |
| F10 | joy · 3 · 900–1020 | S10a → S10b | S10a: `50mm: client K01 by the door, the 2.5% box in his hand, turning back toward cast-C01; skin exactly as in S02a.` S10b: same, `he smiles; she smiles quietly, proud.` | `Start on the first, end on the last. He turns back and smiles; she smiles back. Slow dolly-in, 3 s.` | i2v-first-last, char refs + replace-object (the box in his hand) | no skin change; same faces; print sharp |
| F11 | rung 5, offer · 3 · 1020–1120 | S11a → S11b | S11a: `35mm: cast-C01 alone leaning on the table, the 1.5% and 2.5% boxes beside her (our renders), eyes lowered; right third dark wall.` S11b: same, `eyes to camera, small warm smile.` | `Start on the first, end on the last. She lifts her eyes to the camera. Locked, 3 s.` | i2v-first-last, very low motion | eyes alive; both prints; right third free |
| F12 | family · 2 · 1120–1200 | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` (phone `phone-b/a.webp`) | none | engine dissolve + zoom-out; CELLULAR AGE DEFENSE hotspot glows green | none | no AI crowds/events |

**Order:** after the EXO-NAD sample is approved and the client (man ~50 vs woman) is confirmed: K01 + table → owner OK → F07 as
this film's sample → 480p → OK → rest; FULL F04/F06 only after the bottle photos and the print answer. 2–4 attempts per paid item;
nothing that fails QA goes to the site. People stills are not committed to git.
