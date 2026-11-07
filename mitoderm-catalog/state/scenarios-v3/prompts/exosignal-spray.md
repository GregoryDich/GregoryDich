# EXOSIGNAL SPRAY — production prompts (v3 clinic film)

Companion of `src/exosignal-spray.md` (the contract). Shared bible = `prompts/exo-nad.md` §0 (cast-C01, set-R01, set-T01, look,
shared negative, MODEL classes, aspect plan); paste it on top of every prompt. Line overrides: thin GOLD piping (#c9a24b) on the
tunic, glow #c9a24b; the only particles in the film are the spray's own fine mist with white highlights and gold rims.
MODEL ids/params: `per costs.json → <class>` (costs.json absent at writing time); price + balance to the owner, run after "approved".
BLOCKER: our spray print is retyped from a 400×300 mockup — no paid run before MITODERM's real studio packshot arrives.
TIMING: the demo happens at a short visit BETWEEN two EXOSIGNAL HAIR sessions, on a clean dry scalp — never right after microneedling
(protocol: the spray "every evening on a clean scalp"; when it may start after a MITOPEN session is a question to MITODERM, chapter §7).

**Line negative (append after the shared negative):** `no nozzle or sprayer close-up, no pump visible, no opaque white bottle, no
transparent clear-glass bottle, no liquid visible through the frosted glass, mist never forms a line, cone, arc or ring, no
puddle, dripping, greasy shine or wet towel, no comb or brush, no falling hairs, no hair growing or thickening between shots, no
bald caricature, no gloves in the home routine shots (F06–F08)`.

**Product fidelity:** tall box + 15 ml bottle = `site/proto/scenes/exosignal-spray.js` via `render-keys.cjs` (v1-meet … v6-kit,
3840×2400, alpha); bottle print `site/proto/img/exosignal-spray-3d/bottle-print.png`, box `box-face.png` — DRAFT until the packshot;
HAIR kit in background = `exosignal-hair.js` render. Method (a) composite, (b) first/last + `replace-object`, (c) three.js overlay.
QA every frame: frosted translucent glass, ribbed gold cap, gold vertical 'EXOSIGNAL' + 'S P R A Y · H O M E' on the box legible,
ΔE ≤ 8 vs packshot; box turn ≤ 10°, bottle ≤ ±30°; cap on except F07 (cap removed off-screen, nozzle hidden by fingers).

**Casting still `exosignal-spray-K01`** (4:5, front + profile, still-photoreal): `Portrait photograph in set-R01 (reference
attached): a man about 38, Fitzpatrick III, short-to-medium dark hair visibly thinner at the crown, natural, no grooming product,
dark crew-neck tee under a light cream robe, seated in the treatment chair, real skin and hair texture, calm and dignified,
50mm, f/2, window light from the right, fine grain.` QA: thinning subtle and realistic; identical hair in every later shot.

| shot | purpose · s · scroll | start → end frame | still prompt (key frame) | video prompt | model + params | QA |
|---|---|---|---|---|---|---|
| F01 | pack on the table, rung 1 · 3 s · 0–100 | `set-T01` + `still.webp`/`v1-meet.png` composite → tighter crop | — | — (dolly-in in our pipeline) | none | bottle never hides box lettering; shadow |
| F02 | concern between two HAIR sessions · 4 s · 100–240 | `S02a` → `S02b` | `Over-the-shoulder into the round brass mirror: exosignal-spray-K01 in the chair, hair clean and dry, holds a hand mirror above his crown and looks; the EXOSIGNAL HAIR kit soft on the side table; cast-C01 steps in behind him, no gloves, one hand on the chair back; 50mm f/2.` / b: `he looks up at her in the mirror, a quiet question in his eyes.` | `Slow lateral dolly; he lowers the hand mirror and looks up at the cosmetologist in the big mirror; she rests a hand on the chair back; their eyes meet. Ends exactly on the last frame.` | i2v-first-last 5 s, 1080p | no fallen hairs, no red dots or fresh-treatment marks on the scalp, respectful, same face as F08/F10 |
| F03 | flight: box + bottle land by the HAIR kit · 4 s · 240–340 | `set-T01` + HAIR kit render → pair on table + hand (= F04 start) | — | — (three.js `flight(p)` added to `exosignal-spray.js`) | three.js, 0 credits | turns within limits, cap on, no hover |
| F04 | discovery: bottle to the window, her wow · 3 s · 340–455 | F03 end → `S04` | `cast-C01 holds the 15 ml frosted translucent glass bottle with a ribbed gold metal cap up to the warm window light (reference render attached), turning it slightly, light running over the cap ribs; tall black box soft below; eyebrow raised, small smile; 50mm.` | `She lifts the bottle into the window light and turns it a little in her fingers; light glides across the ribbed gold cap; a quiet smile. The cap stays on. Ends exactly on the last frame.` | i2v-first-last 5 s; bottle replace-object | not white/opaque, print stable, cap on |
| F05 | "the spray": fine mist macro · 2 s · 455–505 | `M05` → mist lower and thinner | `Macro, dark treatment room background: a soft cloud of very fine droplets drifting down in warm backlight, each with a matte white highlight and a thin gold rim, no bottle in frame, 100mm.` | `Slow motion: the fine mist enters from the top edge and sinks gently, thinning out. Shapeless.` | i2v (first frame) 2 s | no shape, no colour, no text |
| F06 | routine 1: part · 2.5 s · 505–605 | `S06a` → `S06b` | `Top-down 85mm: the bare fingers of cast-C01 part the dark hair at the crown of exosignal-spray-K01, exposing a line of clean scalp; shallow depth of field.` | `Bare fingers open a straight parting at the crown; short dolly along it.` | i2v-first-last 3 s | no comb, no redness, fingers |
| F07 | routine 2: spray on the scalp · 2 s · 605–655 | `S07a` → `S07b` | `Low side view 85mm: her hand holds the uncapped frosted bottle just above the open parting, the top of the bottle hidden by her fingers; a fine mist settling onto the scalp.` | `A short spray: a soft fine mist falls directly onto the parting and disappears into the scalp; only the hand and the mist move.` | i2v-first-last 3 s; bottle replace-object | sprayer never visible, mist on scalp not face, no drip |
| F08 | routine 3: massage, the handover · 1.5 s · 655–695 | `S08a` → `S08b` | `Side close-up 50mm: the client's own fingertips gently massage his crown, her hand resting lightly on his, guiding; no towel, hair dry.` / b: `her hand lifts away, he continues.` | `She guides his hand in small gentle circles, then lets go; he continues on his own. Calm.` | i2v-first-last 3 s (use 1.5 s) | two hands: count fingers; hair dry |
| F09 | proof: real program before/after | MITODERM photos `media/exosignal-spray/ba-01-*` | — | — (CSS clip-path wipe) | none | caption names HAIR + SPRAY program; absent → dropped |
| F10 | joy: he knows the routine · 4 s · 860–1000 | `S10a` → `S10b` | `exosignal-spray-K01 standing by the mirror with the frosted bottle in his hand, looking at himself, a small confident nod and smile; cast-C01 beside him, quiet proud smile; 50mm, window light. Hair IDENTICAL to K01.` | `Slow dolly-in; he nods at his reflection and smiles, she smiles quietly. Ends exactly on the last frame.` | i2v-first-last 5 s; refs cast-C01, K01; bottle replace-object | hair density = F02, print on bottle |
| F11 | rung 5: "you can be her" · 3 s · 1000–1115 | `S11a` → `S11b` | `cast-C01 alone at the side table, the EXOSIGNAL HAIR kit behind; a: the frosted bottle in her hand; b: the bottle set on the table in front of the kit, she looks into the lens, warm and confident; 35mm, right third dark wall.` | `She sets the bottle down in front of the kit, as if offering it, and raises her gaze to the camera. Locked camera.` | i2v-first-last 5 s; products replace-object | both prints, live eyes, right third dark |
| F12 | family: line image | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` (HAIR area) | — | — (dissolve + zoom-out) | none | no AI crowd/event |

**9:16 notes:** F02, F04, F06–F08, F10, F11 regenerated vertical (`-v` stills, "vertical 9:16 framing, subject in the middle 46%
band"); F05/F07 mist enters from the top of the vertical frame; encode mist shots at q74 and check banding. F01 crop, F03 rendered 9:16.
**Order of runs:** real packshot → re-render keys → K01 stills → owner's OK → F07 sample (spray on scalp) → rest.
