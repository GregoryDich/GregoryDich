# EXOSIGNAL HAIR — production prompts (v3 clinic film)

Companion of `src/exosignal-hair.md` (the contract: shots, scroll ranges, approved texts). Shared bible = `prompts/exo-nad.md` §0
(cast-C01, set-R01, set-T01, look, shared negative, MODEL classes, aspect plan); paste it on top of every prompt. Line overrides:
accent detail on the tunic = thin GOLD piping (#c9a24b), glow/haze around the product #c9a24b, liquid colourless.
MODEL ids/params: `per costs.json → <class>` (costs.json absent at writing time); price + balance to the owner, run after "approved".
Every 16:9 shot with people is generated AGAIN in 9:16 from its own vertical still (suffix `-v`); product-only shots are cropped.

**Line negative (append after the shared negative):** `no needles visible, no blood, no red dots or bleeding points, no scalp
wounds, no falling hairs on hands or in the sink, no bald caricature, no wig look, no hair growing or thickening between shots,
no exosome spheres, cells, DNA helix or particles inside the liquid, no tinted liquid, no open or broken ampoule, no text on the
MITOSCAN screen facing camera, no comb or brush`. The shared "no needles" rule still holds: MITOPEN appears only as OUR render with
its tip hidden by the angle.

**Product fidelity:** box + 5 ampoules = `site/proto/scenes/exosignal-hair.js` via `render-keys.cjs` (v1-meet … v6-kit, 3840×2400,
alpha) / packshot `protocols/print/img/exosignal-hair.webp`; ampoule print `site/proto/img/exosignal-hair-3d/amp-print.png`;
MITOPEN = `site/proto/scenes/mitopen.js`; MITOSCAN = `site/proto/scenes/mitoscan.js` or `site/public/exosignal-hair/img/mitoscan.webp`.
Method (a) composite into stills, (b) first/last frame + `replace-object` pass, (c) three.js overlay if print drifts. QA every
frame: gold 'EXOSIGNAL' / 'H A I R' legible, ΔE ≤ 8; lower right box corner hidden by ampoules; box turn ≤ 8°; ampoule sealed,
white neck ring, colourless liquid; 1 + 2 + 2 ampoule arrangement when on the table.

**Casting still `exosignal-hair-K01`** (4:5, front + profile, still-photoreal): `Portrait photograph in set-R01 (reference
attached): a woman about 40, medium-dark brown shoulder-length hair, a natural centre parting where the hair is slightly thinner
and the scalp shows a little, no make-up, light cream robe, seated in the treatment chair, real skin and hair texture, dignified
and calm, 50mm, f/2, window light from the right, fine grain.` QA: thinning subtle and realistic; same hair in every later shot.

| shot | purpose · s · scroll | start → end frame | still prompt (key frame) | video prompt | model + params | QA |
|---|---|---|---|---|---|---|
| F01 | pack on the table, rung 1, home continuity · 3 s · 0–100 | `set-T01` + `still.webp`/`v1-meet.png` composite → tighter crop of same | — (composite only) | — (dolly-in in our pipeline) | none, 0 credits | print, contact shadow, right third calm |
| F02 | concern in the mirror + measurement · 4 s · 100–240 | `S02a` → `S02b` | `Over-the-shoulder into the round brass mirror in set-R01: exosignal-hair-K01 in the chair parts her hair at the crown with her fingers and looks at the parting; 50mm f/2, window light right, real hair texture.` / b: `same, cast-C01 behind her, one hand on her shoulder, the other holding the MITOSCAN handheld camera near the parting, screen turned away; eyes meet in the mirror.` | `Slow lateral dolly; she lowers her fingers from the parting and looks up; the cosmetologist steps in, rests a hand on her shoulder and brings the small handheld scanner to the parting; their eyes meet in the mirror. Calm, respectful. Ends exactly on the last frame.` | i2v-first-last, 5 s, 1080p; MITOSCAN by replace-object | screen never visible; 5 fingers; no fallen hairs; same face as F10 |
| F03 | flight: box + ampoules land by MITOPEN · 4 s · 240–340 | `set-T01` + MITOPEN render → group on table + gloved hand (= F04 start) | — | — (three.js `flight(p)` added to `exosignal-hair.js`, rendered per frame with shadow) | three.js, 0 credits; fallback i2v + replace-object | turn ≤ 8°, corner hidden, no hover |
| F04 | discovery: ampoule raised to the window, her quiet wow · 3 s · 340–455 | F03 end → `S04` | `Gloved hand of cast-C01 holds one sealed clear glass ampoule with a white neck ring up against the warm window light, vertical black 'EXOSIGNAL' print toward camera, colourless liquid catching the light; the black box and four ampoules soft below; her face in soft focus, eyebrow raised, small smile; 50mm.` | `She lifts the single ampoule from the table into the window light and tilts it slightly; the colourless liquid moves slowly; a small raised eyebrow and a quiet smile. The ampoule stays sealed. Ends exactly on the last frame.` | i2v-first-last 5 s; ampoule replace-object (ref amp-print.png) | sealed, print undistorted, 4 ampoules stay |
| F05 | texture macro, nothing drawn · 2 s · 455–505 | `M05` → same, meniscus moved (loop) | `Macro through clear glass: colourless liquid, a soft meniscus line, warm window light refracting into a gentle gold highlight, dark background, 100mm, nothing inside the liquid.` | `The liquid sways gently, the meniscus slides a little and settles; light refracts softly. Seamless 2-second loop.` | i2v-loop 2 s | no particles, bubbles, colour, text |
| F06 | ritual: part + drip · 2.5 s · 505–605 | `S06a` → `S06b` | `Top-down 85mm: gloved fingers part dry dark hair into a straight line at the crown of exosignal-hair-K01, scalp clean; b: a small clear drop of serum sits on the parting, the dropper out of frame.` | `Gloved fingers open a straight parting; a small clear drop falls from above out of frame onto the scalp and spreads slightly. Shallow depth of field, short dolly along the parting.` | i2v-first-last 3 s | no syringe/needle in frame, drop clear, no redness |
| F07 | ritual: MITOPEN stamping · 2 s · 605–655 | `S07a` → `S07b` | `Low profile view along the parting, 85mm: cast-C01's gloved hand holds the MITOPEN pen (reference render attached) against the scalp at a shallow angle, tip hidden by the angle; client calm, eyes closed, soft behind.` / b: `pen at the end of the zone.` | `The gloved hand moves the pen slowly along the parting in a gentle rhythmic stamping; only the hand moves. Ends exactly on the last frame.` | i2v-first-last 3 s; MITOPEN replace-object (ref `mitopen.js` render) | no needles, blood or red dots; pen shape/colour = render |
| F08 | ritual: massage to absorption · 1.5 s · 655–695 | `S08a` → `S08b` | `Side close-up 50mm: two gloved hands gently massage the client's scalp with small movements, her head resting back, shoulders relaxed, warm window light.` | `Small slow massaging movements until the serum is absorbed; calm.` | i2v-first-last 3 s (use 1.5 s) | fingers; hair only slightly damp, not greasy |
| F09 | proof: real before/after + MITOSCAN | MITODERM photos `media/exosignal-hair/ba-01-*`, `scan-01-*` | — | — (CSS clip-path wipe) | none | consent signed, no retouch; absent → shot dropped |
| F10 | joy: she smiles, cosmetologist proud · 4 s · 860–1000 | `S10a` → `S10b` | `exosignal-hair-K01 in the chair arranges her hair with her fingers in the mirror and smiles with relief; cast-C01 beside her, hands on the chair back, quiet proud smile; 50mm, window light. Hair IDENTICAL to K01 (same density).` | `Slow dolly-in to both; she finishes arranging her hair and smiles, the cosmetologist smiles quietly. Ends exactly on the last frame.` | i2v-first-last 5 s; character refs cast-C01, K01 | hair density = F02 (frame compare), natural smile |
| F11 | rung 5: "you can be her" · 3 s · 1000–1115 | `S11a` → `S11b` | `cast-C01 alone leaning on the side table, the black box with five ampoules, MITOPEN and the MITOSCAN handheld in front of her (our renders composited); a: looking down at the kit; b: looking into the lens, warm and confident; 35mm, right third dark wall.` | `She raises her gaze from the kit to the camera with a calm, confident warmth. Locked camera.` | i2v-first-last 5 s; products replace-object | print, live eyes, right third dark |
| F12 | family: line image | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` (HAIR area) | — | — (dissolve + zoom-out) | none | no AI crowd/event |

**9:16 notes:** F02, F04, F06–F08, F10, F11 regenerated vertical (`-v` stills, same prompts + "vertical 9:16 framing, subject in the
middle 46% band"); F06–F08 top-down parting runs along the frame height; F01/F05 centre crops; F03 rendered 9:16 directly.
**Order of runs:** after the EXO-NAD sample is approved → K01 stills → owner's OK → F07 sample (most sensitive) → rest.
