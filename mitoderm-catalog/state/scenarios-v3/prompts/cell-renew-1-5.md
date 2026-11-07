# CELL RENEW 1.5% — production prompts (v3 clinic film)

Companion of `src/cell-renew-1-5.md` (the Hebrew chapter is the contract). Shared bible = `prompts/exo-nad.md` §0 (cast `cast-C01`,
room `set-R01`, table `set-T01`, look, shared negative, aspect plan, MODEL classes): paste it on top of every prompt. Line accent
BIOSPICULE GREEN `#1E4634` (glow core `#2F6A50`). MODEL = `per costs.json → <class>` (costs.json not on disk at writing time; fill
id + params before the first paid run; price + balance, run only after "approved"). Aspect: master 16:9 1920×1080 → upscale ×2;
shots with people re-generated 9:16 from their own vertical still; product-only shots rendered or cropped. Each generated shot ≤ 5 s.

**Product fidelity:** the box = OUR three.js scene `site/proto/scenes/cell-renew-1-5.js` via `render-keys.cjs` (3840×2400, alpha;
page copies `site/public/cell-renew-1-5/img/still.webp`, `kit.webp`, `m3.webp`); every face from the dieline
(`site/design/biospicule/panels/cell-renew-1-5/`, 35 × 35 × 110 mm) → full turn in flight allowed. Methods (a) composite,
(b) i2v + `replace-object`, (c) three.js motion composited. PACKAGING: tall ivory box; gold M monogram; 'MITODERM' / 'BIOSPICULE
SYSTEM'; MEDIUM green band with gold 'CELL RENEW' / '1.5%'; 'BIOSPICULE' / 'SERUM'; round medallion in a green ring with dark green
spicules; gold-framed 'ADVANCED' / 'BIOSPICULE TECHNOLOGY'.
**BOTTLE IS BLOCKING:** the 30 ml bottle was never photographed (probably a white airless pump bottle like CELLULAR AGE DEFENSE 2.5%
— unconfirmed; label print `panels/cell-renew-1-5/label.png`). F04, F06, F07 run the FALLBACK (box only, serum already on the
fingertips) until MITODERM's photos arrive. Serum colour unknown: `#4fb285` is a design colour, not a photo — do not use it on skin.
**Extra negative (all shots):** `no bottle unless composited from MITODERM's photo, no dropper, no spatula or brush, no other
products, no sparkles on skin, no rubbing or pressing hard, no drawn redness, no glow or smoothing added to the skin`.

**Stills first:** `cell-renew-1-5-K01` client casting, 4:5 ×2 — `Portrait photograph in set-R01: a young woman about 27, Fitzpatrick
IV, no make-up, hair loose, a small bag on her shoulder at the end of a clinic visit; real skin with visible enlarged pores, slightly
uneven tone and faint post-inflammatory marks, dull tired look — subtle and dignified; 50mm f/2, window light from the right, fine
grain.` `clinic-table-cell-renew-1-5` = `set-T01` with soft shapeless GREEN haze.

| shot | purpose · s · scroll | start → end frame | still prompt (key) | video prompt | model · fidelity | QA |
|---|---|---|---|---|---|---|
| F01 | rung 1, box on table · 3 · 0–100 | `clinic-table-cell-renew-1-5` + our `still.webp` box → 12 % tighter | none (composite) | none (eased crop) | none · (a) | ΔE ≤ 8; medium-green band (not the 2.5% dark green); contact shadow |
| F02 | rung 2, "seen first in the mirror" · 4 · 100–240 | S02a → S02b | S02a: `Over-the-shoulder into the brass-rimmed mirror: client cell-renew-1-5-K01 standing, leaning closer to the mirror, studying her pores and uneven tone, a quiet "and at home?" look; right third dark wall; 50mm f/2, window light right.` S02b: same + `cast-C01 behind her, hand on her shoulder, eyes meet in the mirror, reassuring half-smile.` | `Start exactly on the first frame and end exactly on the last. She leans in and looks; the cosmetologist rests a hand on her shoulder; eyes meet in the reflection. Slow lateral dolly, 50mm, one take, 4 s.` | i2v-first-last, char refs C01+K01 | fingers; mirror; no caricature; same face as F07/F10 |
| F03 | transition, the box arrives · 4 · 240–340 | F01 plate without box → box landed + gloved hand | none | three.js: box from room depth, slow full turn (all printed faces), slows, lands with a small settle, contact shadow; 40 frames 3840 alpha. Paid fallback: i2v + replace-object | none / i2v + replace-object | no blank face; no float |
| F04 | rung 3, discovery · 3 · 340–440 | F03 last → S04 | FALLBACK S04: `Three-quarter high angle over cast-C01's shoulder, pale nitrile gloves: she holds the closed CELL RENEW box (our render) tilted to the window light, looking at its medallion; eyebrow lifted, small smile.` FULL (after photos): `top flap open, she slides out the bottle (MITODERM photo composited), label toward camera.` | `Start on the first, end on the last. She lifts the box to the light [FULL: opens the flap and slides out the bottle]; small smile. One take, 3 s.` | i2v-first-last + replace-object | flap only on its hinge; bottle/label per photo |
| F05 | rung 3, texture (illustration) · 2 loop · 440–500 | our scene pose S3 (`m3.webp`, sparse cloud) | none | three.js loop: a few loose glass spicules in green haze; HTML tag "illustration" | none (0 credits) | sparser than 2.5%; no figures; no drop |
| F06 | rung 4, demonstration · 3 · 500–620 | S06a → S06b | S06a: `Macro profile, 100mm: client K01 seated, eyes closed, calm; gloved fingertips with a thin film of serum touching her clean dry cheek.` S06b: same, `the thin layer massaged in gently and absorbed.` [FULL: open on one pump press onto the fingertips.] | `Start on the first, end on the last. Fingertips spread a thin layer over the cheek with gentle, light circles until it is absorbed, no pressure. Short dolly, 3 s.` | i2v-first-last | light touch; thin transparent film; skin identical in both frames |
| F07 | rung 4, "every day" · 3 · 620–700 | S07a → S07b | S07a: `Over-the-shoulder into the mirror: client K01, no gloves, applying a thin layer to her own cheek with her fingertips, a small surprised look at the gentle tingling; cast-C01 beside her, a soft open-hand "gently" gesture.` S07b: same, `she smiles.` | `Start on the first, end on the last. She smooths the serum in lightly, feels the gentle tingle, then smiles; the cosmetologist nods. Locked, 50mm, 3 s.` | i2v-first-last · THIS FILM'S SAMPLE SHOT | reaction gentle, not pain; no bottle in frame (fallback); clean hands |
| F08 | rung 4, the routine goes home · 2 · 700–760 | S08a → S08b | S08a: `Close, 85mm: cast-C01's hands placing the CELL RENEW box (our render) into the client's open palms.` S08b: `the box resting in her cupped hands, green band and medallion toward camera.` | `Start on the first, end on the last. The box is placed into her palms and her hands close around it. Locked, 2 s.` | i2v-first-last + replace-object (box) | print sharp; 35×110 proportion; fingers |
| F09 | proof · 5 · 760–900 | MITODERM `media/cell-renew-1-5/testimonial-01.jpg` + quote, or `ba-01-before/after.jpg` (not in git) | none | quote card or CSS wipe 800–900vh | none | consent; verbatim quote with name; dropped if none |
| F10 | joy · 3 · 900–1020 | S10a → S10b | S10a: `50mm: client K01 by the door, the box in her hand, turning back toward cast-C01; skin exactly as in S02a.` S10b: same, `she smiles a wordless thank-you; the cosmetologist smiles, proud.` | `Start on the first, end on the last. She turns back and smiles; the cosmetologist smiles back. Slow dolly-in, 3 s.` | i2v-first-last, char refs + replace-object (box) | no skin change; same faces |
| F11 | rung 5, offer · 3 · 1020–1120 | S11a → S11b | S11a: `35mm: cast-C01 alone leaning on the table, the CELL RENEW box beside her (our render, kit pose), eyes lowered; right third dark wall.` S11b: same, `eyes to camera, small warm smile.` | `Start on the first, end on the last. She lifts her eyes to the camera. Locked, 3 s.` | i2v-first-last, very low motion | eyes alive; right third free |
| F12 | family · 2 · 1120–1200 | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` (phone `phone-b/a.webp`) | none | engine dissolve + zoom-out; CELL RENEW hotspot glows green | none | no AI crowds/events |

**Order:** after the EXO-NAD sample is approved: K01 + table → owner OK → F07 as this film's sample → 480p → OK → rest; FULL
versions of F04/F06 only after the bottle photos. 2–4 attempts per paid item; nothing that fails QA goes to the site. People stills
are not committed to git.
