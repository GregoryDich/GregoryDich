# MICRO BOOST 10% — production prompts (v3 clinic film)

Companion of `src/micro-boost-10.md` (the Hebrew chapter is the contract). Shared bible = `prompts/exo-nad.md` §0 (cast `cast-C01`,
room `set-R01`, table `set-T01`, look, shared negative, aspect plan, MODEL classes): paste it on top of every prompt. Line accent
BIOSPICULE GREEN `#1E4634` (glow core `#2F6A50`): the uniform's small detail and the shapeless haze around the product only.
MODEL = `per costs.json → <class>` (costs.json not on disk at writing time; fill id + params before the first paid run; price +
balance, run only after "approved"). Aspect: master 16:9 1920×1080 → upscale ×2; shots with people re-generated 9:16 from their
own vertical still; product-only shots rendered or cropped. Each generated shot ≤ 5 s, trimmed to the listed length.

**Product fidelity:** the box = OUR three.js scene `site/proto/scenes/micro-boost-10.js` via `render-keys.cjs` (3840×2400, alpha;
`v1-meet.png` … `v6-kit.png`; page copies `site/public/micro-boost-10/img/still.webp`, `kit.webp`, `m3.webp`). The S1 key
(`v1-meet.png` / `still.webp`) carries a spicule swarm beside the box: for every clinic composite take the box ALONE (`v6-kit.png`
alpha) — no floating spicules in a real room. Since 31/10 every
face carries the printer's dieline (`site/design/biospicule/panels/micro-boost-10/`, 33 × 22.5 × 150 mm, `geometry.json`), so a
full turn in flight is allowed. Methods: (a) composite stills, (b) i2v + `replace-object` with our render, (c) three.js motion
composited. PACKAGING: tall slim ivory box; gold M monogram; 'MITODERM' / 'BIOSPICULE PROFESSIONAL'; very dark green, near-black band (`#102018` on the dieline) with gold
'MICRO BOOST 10%'; 'SPICULE SERUM'; round medallion in a gold ring with dark green spicules; gold-framed 'Concentrated' /
'Spicule System'; top tuck flap hinged to the front.
**SYRINGE IS BLOCKING:** the 3 ml syringe was never photographed (label print known: `panels/micro-boost-10/label.png`, 63×34 mm).
F04 and F08 have a FALLBACK without it; the full version only from MITODERM's photos, composited / replace-object. Never
generate a syringe from text; never a needle.
**Extra negative (all shots):** `no syringe unless composited from MITODERM's photo, no needle, no microneedling device or roller,
no brush or spatula, no other products, no sparkles or glitter on the skin, no drawn redness or peeling, no glow or smoothing added
to the skin, no spicules visible on skin`.

**Stills first:** `micro-boost-10-K01` client casting, 4:5 ×2 — `Portrait photograph in set-R01: a woman about 40, Fitzpatrick III,
no make-up, white towelling headband, light robe; real skin with visible enlarged pores, slightly rough uneven texture and faint
post-acne marks on the cheeks, dull tired tone — subtle and dignified, never a caricature; 50mm f/2, window light from the right,
fine grain.` `clinic-table-micro-boost-10` = `set-T01` with soft shapeless GREEN haze behind the product spot.

| shot | purpose · s · scroll | start → end frame | still prompt (key) | video prompt | model · fidelity | QA |
|---|---|---|---|---|---|---|
| F01 | rung 1, box on table · 3 · 0–100 | `clinic-table-micro-boost-10` + our box alone (`v6-kit.png` alpha, not the S1 still with the swarm) → 12 % tighter | none (composite) | none (eased crop) | none · (a) | print ΔE ≤ 8; tall slim proportion; contact shadow; frame 0 = home transition end |
| F02 | rung 2, "more than a peel" · 4 · 100–240 | S02a → S02b | S02a: `Over-the-shoulder into the brass-rimmed mirror: client micro-boost-10-K01 in the treatment chair, fingertips tracing her cheek, feeling its texture, a thoughtful look; right third dark wall; 50mm f/2, window light right, real skin, fine grain.` S02b: same + `cast-C01 behind her, hand on her shoulder, eyes meet in the mirror, calm confident half-smile.` | `Start exactly on the first frame and end exactly on the last. She runs her fingertips over her cheek and looks; the cosmetologist steps in and rests a hand on her shoulder; eyes meet in the reflection. Slow lateral dolly, 50mm, one take, 4 s.` | i2v-first-last, char refs C01+K01 · no product | fingers; mirror geometry; skin not exaggerated; same face as F10 |
| F03 | transition, the box arrives · 4 · 240–340 | F01 plate without box → box landed + gloved hand (= F04 frame 0) | none | three.js: box from room depth, slow full turn about its vertical axis (all printed faces), slows, front squares to camera, lands with a small settle, contact shadow; 40 frames 3840 alpha over the plate. Paid fallback: i2v-first-last + replace-object | none / i2v + replace-object | no blank face; print sharp at the end; no float; tall box does not wobble |
| F04 | rung 3, discovery · 3 · 340–440 | F03 last → S04 | FALLBACK S04: `Three-quarter high angle over cast-C01's shoulder, pale nitrile gloves: she holds the closed tall ivory box (our render composited) tilted to the window light, looking at its round medallion; eyebrow lifted, small smile; 50mm f/2.2.` FULL S04 (after the syringe photos and the open-box photo): same, `the top flap open, she holds the 3 ml syringe (MITODERM photo composited) up to the light, label toward camera.` | `Start on the first, end on the last. Her gloved hands lift the box and tilt it to the light [FULL: open the top flap and draw out the syringe, raise it to the light]; eyebrow lifts, small smile. One take, 3 s.` | i2v-first-last + replace-object (box; syringe from photo) | flap moves only on its hinge; no needle; label = `label.png`; gloves' fingers |
| F05 | rung 3, texture (illustration) · 2 loop · 440–500 | our scene pose S3 (`v3-inside.png` / `m3.webp`) | none | three.js loop: loose fine silica spicules (the catalogue's mineral needles) of two lengths in green haze, one turning slowly; HTML corner tag "illustration" | none (0 credits) | no rows/rings/figures; no drop; no skin section |
| F06 | rung 4, gradual spreading · 3 · 500–620 | S06a → S06b | S06a: `Macro profile, 100mm: client K01 lying back, eyes closed, calm; gloved fingertips with a thin film of serum on her clean dry forehead.` S06b: same, `the fingertips now on her cheekbone, a thin even film spread.` | `Start on the first, end on the last. Gloved fingertips spread the serum gradually from the forehead to the cheek in a thin layer. Short dolly, shallow depth of field, one take, 3 s.` | i2v-first-last | serum colour per MITODERM answer; thin film, not cream; no tool in frame |
| F07 | rung 4, controlled massage · 3 · 620–700 | S07a → S07b | S07a: `85mm, three-quarter above the head: both gloved hands on the client's cheeks, small even circles; cast-C01 watching the client's face attentively, a quiet "how does it feel?" look.` S07b: same, `the client opens her eyes briefly and nods, a small half-smile; the hands keep the same even pressure.` | `Start on the first, end on the last. Even, controlled small circular massage; the client feels the expected tingling, opens her eyes, nods, relaxes. Locked, 3 s.` | i2v-first-last · THIS FILM'S SAMPLE SHOT | reaction subtle, not pain, not spa; no drawn redness (only if MITODERM approves a mild even flush); fingers |
| F08 | rung 4, "one syringe, one treatment" · 2 · 700–760 | S08a → S08b | S08a: `Close, 85mm: gloved hands lifting off the client's cheek, the serum absorbed.` S08b FALLBACK: `cast-C01's gloved hand resting on the closed box on the side table.` FULL: `she lays the empty syringe (MITODERM photo) on a tray beside the box.` | `Start on the first, end on the last. The hands lift off the skin and move to the table [FULL: and lay the syringe down]. Locked, 2 s.` | i2v-first-last + replace-object | no serum residue after absorption; box print; syringe per photo |
| F09 | proof · 5 · 760–900 | MITODERM `media/micro-boost-10/ba-01-before/after.jpg` (not in git) | none | CSS wipe 800–900vh | none | consent; no retouch; same crop; dropped if none |
| F10 | joy · 3 · 900–1020 | S10a → S10b | S10a: `50mm: client K01 seated, holding a hand mirror, skin exactly as in S02a; cast-C01 behind her, hands on the chair back; the closed box blurred in the foreground (our render).` S10b: same, `she smiles at herself; the cosmetologist smiles quietly, proud.` | `Start on the first, end on the last. She looks at herself and smiles; the cosmetologist smiles. Slow dolly-in, 3 s.` | i2v-first-last, char refs; the blurred box = our render composited into both stills (no replacement pass, as in the model chapter) | no skin change; same faces; natural smile; print legible even blurred |
| F11 | rung 5, offer · 3 · 1020–1120 | S11a → S11b | S11a: `35mm: cast-C01 alone leaning on the table, hand on the box (our render, kit pose), eyes lowered; right third dark wall.` S11b: same, `eyes to camera, small warm smile.` | `Start on the first, end on the last. She lifts her eyes to the camera and holds the look. Locked, 3 s.` | i2v-first-last, very low motion | eyes alive; print under the hand; right third free |
| F12 | family · 2 · 1120–1200 | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` (phone `phone-b/a.webp`) | none | engine dissolve + zoom-out; MICRO BOOST 10% hotspot glows green | none | no AI crowds/events |

**Order:** after the EXO-NAD sample is approved: K01 + table → owner OK → F07 as this film's sample (the controlled massage is the
story) → 480p → OK → rest; F04/F08 FULL only after the syringe photos. 2–4 attempts per paid item; nothing that fails QA goes to the
site. People stills are not committed to git.
