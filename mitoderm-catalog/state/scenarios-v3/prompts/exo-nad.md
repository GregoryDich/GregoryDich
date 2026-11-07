# EXO-NAD — production prompts (v3 clinic film)

Working file, English. Companion of `src/exo-nad.md` (the Hebrew chapter, which is the contract: shot list, scroll ranges,
approved texts). Nothing here invents product properties; every product in frame is OUR render or packshot, never a
text-generated pack (BRIEF D6). Model ids and prices come from `research/costs.json` / `r3-ai-video.md`; where that file was
not yet on disk at writing time the field says `MODEL: per costs.json` and names the class of model needed.

## 0. Shared bible (paste on top of every prompt of the series)

**Cast (proposal, needs the owner's approval before any video):**
- `cast-C01` — the MITODERM cosmetologist, the same woman in all 13 films: 35–40, Israeli / Mediterranean, warm and expert
  face, hair tied back in a low bun, no visible make-up beyond natural, small stud earrings at most, dark graphite professional
  tunic with a short stand collar and one small champagne-coloured detail (a piping line or a pin) for the PEELING line;
  pale (white) nitrile gloves in treatment shots — glove colour to confirm with MITODERM.
- `exo-nad-K01` — the client of this film: woman about 45, Fitzpatrick III–IV, no make-up, white towelling headband, light
  robe; real skin texture, slightly dull and uneven tone, faint sun spots — subtle and dignified, NEVER a caricature of a
  flaw; never retouched between shots (the "after" is not ours to show).

**Set (one room for the whole series):** a quiet premium treatment room: dark walnut and warm grey stone, clean surfaces, a
treatment chair/bed with cream linen, a large round mirror with a thin brass rim, a low wooden side table (the product's
table) with a stone top, warm late-afternoon window light from camera RIGHT with the window itself out of frame; the RIGHT
third of the 16:9 frame is a dark stone/wood wall in soft shadow (the Hebrew copy sits there as HTML; RTL layout: text right,
action left). Soft, shapeless champagne haze and glow (`#d8c48a`) live only around the product, never as beams, rays or
particles.

**Look:** "shot on a cinema camera, [lens], shallow depth of field, natural window light, real skin texture, fine natural film
grain, true colours, calm luxury editorial". Words never used: render, 3D, CGI, HDR, glossy, glowing skin, flawless.
One grade for the whole line: warm neutral, gently lifted blacks, no teal-and-orange. Grain is added later as a CSS/canvas
overlay — ask the generator for CLEAN frames with only a trace of grain.

**Product fidelity (every frame that shows the kit):** the box, the peel bottle and the vials come from our three.js scene
`site/proto/scenes/exo-nad.js` rendered with `render-keys.cjs` (3840×2400, alpha; `v1-meet.png` closed box, `v6-kit.png` open
kit) or from the packshot `protocols/print/img/exo-nad.webp`. Method per shot: (a) STILLS — composite our render into the
generated plate (`site/tools/composite.py`), match light direction and add a contact shadow; (b) VIDEO — generate with the
composited still as first/last frame, then replace the product region with our render per frame or run an object-replacement
pass (Higgsfield Genjutsu `hf_mult_replace_object`, reference = our render) so the print is exact; (c) if the print still
drifts, the product's own motion is rendered in three.js and composited over the generated clip. QA on every frame: the
print legible and unchanged; ΔE ≤ 8 on the flat gold of the lid against the packshot; 1 + 5 + 5 vessels in the tray; the
lid moves only straight up; caps stay on.

**PACKAGING TEXT (from `site/packaging-text.md`, exo-nad — what the camera may see; never retyped by the generator):**
- square box — brushed gold gradient, thin lid line near the bottom, black print: top centre VM monogram + 'VM corporation';
  centre 'EXO-NAD' ('EXO-' thin, 'NAD' bold); below, letter-spaced 'SKIN LONGEVITY PEELING'.
- peel bottle — clear square glass, gold cap, gold flakes in a two-phase pale-yellow liquid: 'EXO-NAD' / 'SKIN LONGEVITY PEELING'.
- amber vial — amber glass, silver crimp cap: VM monogram, 'PH NORMALIZER'.
- teal vial — blue-teal glass, silver crimp cap: VM monogram, 'LONGEVITY SERUM'.
- tray — black insert with gold print (circled 1 2 3, 'EXO-NAD'); peel bottle at the left, 5 pH vials top row, 5 serum vials bottom row.

**Shared negative prompt (append to every video and still):**
`no text or lettering except the packaging's own print, no invented logos, no extra products, no brushes, spatulas, needles
or syringes with needles, no jewelry on hands, no watermark, no 3D-render or CGI look, no plastic or waxy skin, no extra or
missing fingers, no duplicated or mirrored faces, no glitter, sparkles, dust motes or light rays, no lens-flare streaks, no UI,
no subtitles, no colour change of the packaging, no retouched or "improved" skin`

**Aspect plan:** master 16:9 at 1920×1080 → upscale ×2 (3840×2160) for the desktop tier (rule: assets ≥ 2× CSS size); every
shot with people is generated AGAIN in 9:16 (1080×1920) from its own vertical still — a crop of the 16:9 loses the
composition; product-only shots (F01, F03, F05, F11) are cropped from the master. Frame extraction and WebP encoding:
`film_frames.py` per `r2-scroll-film.md` §3 (q68–74, no alpha, 5–6 fps for motion, 10 fps for F03, one frame per hold).

**MODEL field convention:** `MODEL: per costs.json → <class>` where class ∈ {`still-photoreal` (text/ref-to-image, character
reference supported), `i2v-first-last` (image-to-video with first AND last frame, 5 s, 1080p), `i2v-loop` (first frame only,
seamless loop), `replace-object`, `upscale-video-x2`}. Fill the exact id and params from `research/costs.json` before the first
paid run; price + balance to the owner, run only after "approved".

## 1. Casting and set stills (first paid step; owner's OK before any video)

| id | purpose | aspect | prompt (then the shared negative) | QA |
|---|---|---|---|---|
| `set-R01` | the room, wide; the reference every other still must match | 16:9 | `Editorial interior photograph of a quiet premium aesthetic treatment room in Tel Aviv: dark walnut cabinetry, warm grey stone counter, a treatment chair with cream linen, a large round mirror with a thin brass rim, a low wooden side table with a stone top in the foreground left, clean empty surfaces, warm late-afternoon window light from the right with the window out of frame, the right third of the frame a dark stone wall in soft shadow, shot on a cinema camera, 35mm, f/2.8, natural light, fine natural grain, true colours, no people, no products.` | right third dark and calm; one light direction; no logos or art on the walls |
| `set-T01` | the product table plate (champagne) — F01 start, F03 plate, the home transition end frame | 16:9 | `Same room as set-R01 (reference image attached): close view of the low wooden side table with the stone top, empty, seen from table height, 35mm, the treatment chair and mirror soft in the background, warm window light from the right, a very soft shapeless champagne-gold haze (#d8c48a) in the air behind the table, the right third dark stone wall in shadow, cinema camera, natural light, fine grain, no people, no products, no objects on the table.` | the table surface receives a clear light direction for the composite shadow; nothing on the table |
| `cast-C01` | the cosmetologist, casting portrait (front + ¾) | 4:5 ×2 | `Portrait photograph in set-R01 (reference attached): an Israeli cosmetologist, woman about 38, warm expert face, calm direct gaze, hair tied back in a low bun, natural skin, minimal make-up, small stud earrings, dark graphite professional tunic with a short stand collar and one thin champagne piping line, standing by the mirror, 50mm, f/2, window light from the right, fine grain, true skin texture.` | the same face in both; no name badge, no logo on the tunic |
| `exo-nad-K01` | the client, casting portrait (front + profile) | 4:5 ×2 | `Portrait photograph in set-R01: a woman about 45, Fitzpatrick III–IV skin, no make-up, white towelling headband, light cream robe, seated in the treatment chair, real skin texture with a slightly dull uneven tone and faint sun spots, dignified and calm, 50mm, f/2, window light from the right, fine grain.` | realistic, respectful; no exaggerated flaws; no retouch |

## 2. Shots

### exo-nad-F01 — the pack on the table (rung 1, continuity from home)
- **Purpose:** frame 0 of the page = the last frame of the home transition clip; the name on top; curiosity.
- **Duration / scroll:** 3 s · 0–100vh (0–40 hold). **Aspect:** 16:9 master; 9:16 = crop (box centred).
- **Start frame:** `clinic-table-exo-nad` = `set-T01` + our render `site/public/exo-nad/img/still.webp` (the closed box; the
  render's own alpha is cut from the 3840 key `v1-meet.png`) composited on the table, light matched to the plate, contact
  shadow. **End frame:** the same composite framed ~12 % tighter.
- **Still prompt:** none (composite). **Video prompt:** none — the push-in is done in our pipeline (progressive crop of the
  3840×2160 composite, eased), or in three.js with the box drawn over the plate.
- **MODEL:** none (0 credits). **Product fidelity:** method (a). **QA:** print legible; ΔE ≤ 8; shadow direction = window; the
  right third stays dark for the copy; frame 0 is byte-identical to the transition clip's last frame.

### exo-nad-F02 — the client in the mirror (rung 2)
- **Purpose:** the concern, named by a human and in dignity; the cosmetologist's reassurance.
- **Duration / scroll:** 4 s · 100–240vh (100–140 hold). **Aspect:** 16:9 + own 9:16.
- **Start frame:** `exo-nad-S02a`; **End frame:** `exo-nad-S02b`.
- **Still prompt S02a:** `Over-the-shoulder view into the round brass-rimmed mirror in set-R01: the client exo-nad-K01
  (reference attached) seated in the treatment chair in a white headband and cream robe, looking at her own skin, fingertips
  resting on her cheekbone, expression thoughtful, not sad; her reflection fills the left two-thirds, the right third is the
  dark stone wall; 50mm, f/2, warm window light from the right, real skin texture, slightly dull uneven tone, no make-up,
  cinema camera, fine grain.`
- **Still prompt S02b:** `Same frame and light as S02a: the cosmetologist cast-C01 (reference attached) has stepped in behind
  the chair, her gloved-free hand resting gently on the client's shoulder, both faces visible in the mirror, eyes meeting in
  the reflection, a quiet reassuring half-smile from the cosmetologist; same lens, same framing.`
- **Video prompt:** `Start exactly on the first frame and end exactly on the last frame. The client studies her skin in the
  mirror and lowers her hand slowly; the cosmetologist enters from the right edge behind the chair and rests her hand on the
  client's shoulder; their eyes meet in the reflection; the client's expression softens. Camera: slow lateral dolly of a few
  centimetres toward the mirror, 50mm, shallow depth of field, locked height. Natural window light, real skin texture, fine
  grain, calm editorial pace, one continuous take, 4 seconds.`
- **Negative:** shared + `no second reflection, no distorted mirror geometry, no change of the client's skin between frames`.
- **MODEL:** per costs.json → `i2v-first-last`, 5 s, 1080p, low motion strength; character refs = `cast-C01`, `exo-nad-K01`.
- **Product fidelity:** no product in frame. **QA:** 5 fingers per hand; the reflection matches the room; no "plastic" skin; the
  client is recognisably the same woman as in F09; nothing implies a result.

### exo-nad-F03 — the pack flies in and lands (transition, mystery)
- **Purpose:** the gift arrives; the owner's "the pack flies rotating onto the cosmetologist's table".
- **Duration / scroll:** 4 s · 240–340vh (no text). **Aspect:** 16:9; 9:16 rendered directly.
- **Start frame:** plate `set-T01` (empty table). **End frame:** `clinic-table-exo-nad` + the gloved hand = F04 frame 0.
- **Primary (0 credits):** three.js — add `flight(p)` to `exo-nad.js`: the box starts deep in the room above the table at
  ~0.35 scale, turns about its vertical axis (one slow turn, the unphotographed sides seen only in motion and rim light),
  decelerates, squares to the camera (yaw 4° toward the copy as in S1), settles on the table with a 0.3 s "sit" (2 % scale
  bounce), contact shadow from the window direction; render 40 frames at 3840×2160 with alpha, composite over the plate
  (`composite.py` per frame, shadow baked from the box's silhouette). The hand entering at the end is a 1 s generated insert
  (`i2v-first-last` from the composite to `exo-nad-S03b`, hand only) or a real hand plate.
- **Alternative (paid, only if the render reads digital):** `i2v-first-last` from the plate to the composite end frame with the
  prompt `A brushed-gold square box, exactly the one in the last frame, glides in from the depth of the room above the table,
  turning slowly about its vertical axis, catches the window light on its front, slows, squares itself to the camera and
  lands softly on the wooden table with a tiny settle; a hand in a pale nitrile glove enters from the left and steadies it.
  Camera locked at table height, 35mm. Natural window light, fine grain, one continuous take, 4 seconds.` + replace-object pass
  with our render as reference.
- **Negative:** shared + `the box never deforms, bends or changes proportion; no hovering above the table at the end; no
  sparkle trail; no motion streaks`.
- **MODEL:** none (three.js) / per costs.json → `i2v-first-last` + `replace-object`.
- **QA:** print sharp in every frame (the three.js route guarantees it); physics (deceleration, shadow, no float); the last
  frame is pixel-identical to F04's first; the 9:16 lands in the lower third.

### exo-nad-F04 — discovery: lid up, the tray, the bottle to the light (rung 3)
- **Purpose:** the professional "wow": real mechanics only — the sleeve lifts straight up, the shake before use.
- **Duration / scroll:** 3 s · 340–460vh (340–380 hold). **Aspect:** 16:9 + own 9:16.
- **Start frame:** F03 last (box on table + hand). **Mid frame (composite):** `set-T01` + our open-kit render `v6-kit.png`
  (page copy: `site/public/exo-nad/img/kit.webp`) with both gloved hands holding the lifted sleeve. **End frame:** `exo-nad-S04`.
- **Still prompt S04:** `Three-quarter high angle over the cosmetologist's shoulder (cast-C01, pale nitrile gloves): on the
  wooden table the open EXO-NAD kit — a black tray in a brushed-gold base (the kit rendered by us is composited; leave a clean
  area) — and in her raised right hand a small clear square glass bottle with a gold cap held up toward the window light,
  pale yellow two-phase liquid with fine gold flakes inside; her face in soft profile, eyebrow lifted, a small genuine smile;
  50mm, f/2.2, warm window light from the right, real skin, fine grain.`
- **Video prompt:** `Start exactly on the first frame and end exactly on the last frame. Her gloved hands lift the gold sleeve
  of the box straight up — only vertically — revealing the black tray with its bottles; she sets the sleeve aside out of
  frame, takes the square glass bottle from the left of the tray, gives it two gentle shakes and raises it toward the window
  light, turning it slightly; her eyebrow lifts and she smiles a little. Camera: three-quarter high angle, 50mm, a slight rise
  following the lid. Natural window light, fine grain, one continuous take, 3 seconds.`
- **Negative:** shared + `the lid never tilts, hinges or folds; no vial leaves the tray; the cap stays on; no liquid drips`.
- **MODEL:** per costs.json → `i2v-first-last` + `replace-object` (box, tray, bottle ← our render).
- **Product fidelity:** method (b); vessel counts and tray print from `v6-kit.png`. **QA:** lid motion straight up; 1 + 5 + 5 in
  every frame; print on lid and tray; cap on; glove fingers.

### exo-nad-F05 — macro: two phases and gold flakes (rung 3, texture)
- **Purpose:** sensuality; the material itself. Only what the kit really holds (two phases, gold flakes).
- **Duration / scroll:** 2 s loop · 460–520vh. **Aspect:** 16:9; 9:16 = centre crop.
- **Start = end frame:** `exo-nad-M05`.
- **Still prompt M05:** `Macro photograph through clear glass, 100mm macro, f/4: a pale yellow liquid in two phases, one above
  the other, meeting at a soft boundary; fine gold leaf flakes suspended and sinking slowly; warm window backlight; the glass
  edges soft and dark at the frame sides; the colours of the two phases as in the attached reference
  (site/proto/img/exo-nad-3d/peel-liquid.png); no label, no text, no cap in frame.`
- **Video prompt:** `Start on the first frame; seamless 2-second loop. The gold flakes drift and turn slowly inside the liquid,
  catching the light; the soft boundary between the two phases sways very slightly. Camera locked, 100mm macro, shallow depth
  of field, natural backlight, fine grain, no cuts.`
- **Negative:** shared + `no bubbles or foam, no spheres, cells or exosomes, no other colours, flakes never leave the liquid`.
- **MODEL:** per costs.json → `i2v-loop`. **QA:** loop seam invisible; flake size realistic; phase colours ΔE ≤ 10 to the texture.

### exo-nad-F06 — the ritual, step 1: the peel on the cheek (rung 4)
- **Purpose:** the owner's own example — the cosmetologist applies it to the face; hands and texture, no result.
- **Duration / scroll:** 3 s · 520–640vh (520–560 hold). **Aspect:** 16:9 + own 9:16.
- **Start frame:** `exo-nad-S06a`; **End frame:** `exo-nad-S06b`.
- **Still prompt S06a:** `Macro-close photograph, 100mm, f/2.8: the client exo-nad-K01 reclined, eyes closed, calm, white
  headband; the cosmetologist's fingertips in pale nitrile gloves resting on the client's cheekbone, a thin even transparent
  glistening layer of liquid on the cheek; profile toward the window light from the right; real skin texture, pores visible,
  no redness beyond a natural warmth, fine grain.`
- **Still prompt S06b:** `Same frame and light: the gloved fingertips now at the angle of the jaw, having moved along the cheek
  in small circles; the liquid layer even and glistening; the client unchanged, eyes closed.`
- **Video prompt:** `Start exactly on the first frame and end exactly on the last frame. The gloved fingertips spread the thin
  liquid over the cheek in small gentle circles, moving from the cheekbone to the jaw; the layer stays even and glistening;
  the client breathes slowly, eyes closed. Camera: a very short dolly along the cheek, 100mm macro, shallow depth of field.
  Natural window light, real skin texture, fine grain, one continuous take, 3 seconds.`
- **Negative:** shared + `no brush, fan brush, cotton or spatula; no white cream texture; no visible peeling, flaking or
  irritation; no change of skin tone during the shot`.
- **MODEL:** per costs.json → `i2v-first-last`, low motion strength. **QA:** fingers; the liquid reads as a transparent layer;
  the skin is identical in first and last frame; no "effect".

### exo-nad-F07 — the ritual, steps 2–3: normaliser, water, serum (rung 4)
- **Purpose:** the sequence is honest to the protocol: new gloves, the amber normaliser, water, the blue serum pressed in.
- **Duration / scroll:** 3 s · 640–720vh. **Aspect:** 16:9 + own 9:16.
- **Frames:** `exo-nad-S07a` (new gloves, amber vial in hand, liquid on the cheek) → `exo-nad-S07b` (a damp white pad wiping
  the area, skin dried) → `exo-nad-S07c` (the blue-teal vial, fingertips pressing the serum into the skin). Three ≈1 s
  segments with short dissolves, or one 3 s clip S07a → S07c.
- **Still prompt S07a:** `Close photograph, 85mm, f/2.8: the cosmetologist's hands in FRESH pale nitrile gloves, one hand
  holding a small amber glass vial with a silver crimp cap (our vial composited), the other applying a thin amber liquid on
  the client's cheek; the client calm, eyes closed; window light from the right; real skin, fine grain.`
- **Still prompt S07b:** `Same frame: a damp white cotton pad wipes the cheek, the skin clean and dry afterwards; no vial in frame.`
- **Still prompt S07c:** `Same frame: a small blue-teal glass vial with a silver crimp cap (our vial composited) in one hand,
  the other hand's fingertips pressing a thin translucent serum into the cheek until it disappears; the client calm.`
- **Video prompt (single clip):** `Start exactly on the first frame and end exactly on the last frame. The gloved hands set the
  amber liquid on the cheek, a damp white pad wipes the area clean, then fingertips press a thin translucent serum into the
  skin in slow presses until it is absorbed. Camera locked, 85mm, shallow depth of field, natural window light, fine grain, one
  continuous take with two soft dissolves, 3 seconds.`
- **Negative:** shared + `no syringe with a needle, no dropper, no foam, no colour staining on the skin, the correct vial for
  each step (amber then blue-teal), no change of skin tone`.
- **MODEL:** per costs.json → `i2v-first-last` (×3 or ×1) + `replace-object` for the vials (`vial-ph.png`, `vial-ls.png` print).
- **QA:** glove change visible between F06 and F07; vial colours right; no needle near the face; the rinse mechanic as MITODERM
  confirms it (water + pad is our placeholder).

### exo-nad-F08 — real before/after (proof)
- **Purpose:** the only place a result appears; MITODERM's own photos with consent. NO generation.
- **Duration / scroll:** 5 s wipe · 720–860vh (720–760 hold). **Aspect:** the photos themselves; portrait-friendly crop for phone.
- **Sources:** `media/exo-nad/ba-01-before.jpg`, `ba-01-after.jpg` (not in git), ≥ 2000 px, same angle/light/distance, no
  make-up, no retouch; consent form on file.
- **Build:** two stills in one crop, CSS `clip-path` wipe right → left driven by scroll 760–860vh; labels «לפני» / «אחרי»;
  caption «אחרי [N] טיפולים · תוצאות אישיות משתנות» (owner fills N). Without photos the shot is dropped (F07 → F09).
- **MODEL:** none. **QA:** consent signed; identical crop; caption contrast ≥ 4.5:1 on the brightest pixel under it.

### exo-nad-F09 — joy: the hand mirror, the smile, the pride (rung 4 → 5)
- **Purpose:** the emotional peak; identification — the viewer wants to be the cosmetologist.
- **Duration / scroll:** 4 s · 860–980vh (860–900 hold). **Aspect:** 16:9 + own 9:16.
- **Start frame:** `exo-nad-S09a`; **End frame:** `exo-nad-S09b`.
- **Still prompt S09a:** `Photograph, 50mm, f/2: the client exo-nad-K01 seated upright in the treatment chair holding a round
  hand mirror, looking at herself, neutral and attentive; the cosmetologist cast-C01 standing behind the chair, hands on the
  backrest; in the soft foreground left the closed brushed-gold EXO-NAD box on the wooden table (our render composited, out of
  focus); warm window light from the right, the right third dark wall; real skin, the client's skin exactly as in S02a, fine grain.`
- **Still prompt S09b:** `Same frame: the client smiles — a relieved, genuine smile with the eyes; the cosmetologist behind her
  smiles quietly, proud, looking at the client in the mirror; nothing else changed.`
- **Video prompt:** `Start exactly on the first frame and end exactly on the last frame. The client tilts the hand mirror a
  little, studies her face, and a genuine smile arrives slowly, eyes first; the cosmetologist behind her lets a quiet proud smile
  appear and lifts her chin slightly. Camera: slow dolly-in toward both, 50mm, shallow depth of field. Natural window light,
  real skin texture, fine grain, one continuous take, 4 seconds.`
- **Negative:** shared + `no brightening, smoothing or glow added to the skin; no change of skin tone from the first frame;
  no teeth-whitening grin; no second mirror reflection of the camera`.
- **MODEL:** per costs.json → `i2v-first-last`; character refs `cast-C01`, `exo-nad-K01`. **QA:** same two faces as F02/F04; the
  skin is unchanged (the joy is emotion, not a result); the box print readable even out of focus.

### exo-nad-F10 — "you can be this cosmetologist" (rung 5)
- **Purpose:** the direct address; the offer card and the form open over this frame.
- **Duration / scroll:** 3 s · 980–1100vh (980–1020 hold). **Aspect:** 16:9 + own 9:16 (portrait).
- **Start frame:** `exo-nad-S10a` (eyes down to the box); **End frame:** `exo-nad-S10b` (eyes to camera).
- **Still prompt S10a:** `Portrait photograph, 35mm, f/2.8: the cosmetologist cast-C01 alone, leaning lightly on the wooden
  table, her ungloved hand resting on the closed brushed-gold EXO-NAD box (our render composited), eyes lowered to the box, a
  calm confident expression; the treatment room behind her; warm window light from the right; the right third of the frame
  dark wall; real skin, fine grain.`
- **Still prompt S10b:** `Same frame: she has lifted her eyes to the camera, a warm direct look and a small smile; hand still on
  the box.`
- **Video prompt:** `Start exactly on the first frame and end exactly on the last frame. She lifts her eyes from the box to the
  camera and holds the look with a small warm smile; her hand stays on the box. Camera locked, 35mm, shallow depth of field,
  natural window light, fine grain, one continuous take, 3 seconds.`
- **Negative:** shared + `no walking, no hand gestures, no talking mouth, no dead stare`.
- **MODEL:** per costs.json → `i2v-first-last`, very low motion. **QA:** eyes alive; box print under the hand; the right third
  free for the card and the form.

### exo-nad-F11 — the family (belonging)
- **Purpose:** the box returns to the MITODERM lineup; events and training (real photos only when MITODERM supplies them).
- **Duration / scroll:** 2 s · 1100–1180vh (1100–1140 hold). **Aspect:** desktop `desktop-b.webp` → `desktop-a.webp` (EXO-NAD
  region); phone `phone-b.webp` → `phone-a.webp`.
- **Build:** dissolve from F10's last frame to the lineup image; the EXO-NAD hotspot glows; a gentle zoom-out in the engine.
- **MODEL:** none. **QA:** no AI crowd or event imagery; only the owner's images.

## 3. Attempt plan and order (price + balance before each; sample first)

1. Stills `set-R01`, `set-T01`, `cast-C01`, `exo-nad-K01` → owner's OK on the casting and the room.
2. ONE sample shot end to end: F06 (the owner's own example: the application on the face) — stills S06a/b → 480p draft →
   OK → 1080p → upscale ×2 → frames → the scroll page sample.
3. Then F02, F04, F07, F09, F10 (stills → drafts → finals), F05 loop, F03 in three.js, F01/F11 in the pipeline.
4. Expect 2–4 attempts per paid item (BRIEF D8); never publish a frame that fails the QA of its shot.
