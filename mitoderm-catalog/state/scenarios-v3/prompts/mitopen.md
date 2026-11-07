# MITOPEN — production prompts (v3 clinic film)

Companion of `src/mitopen.md` (the contract: shots, scroll ranges, approved texts). Shared bible = `prompts/exo-nad.md` §0
(cast-C01, set-R01, set-T01, look, shared negative, MODEL classes, aspect plan); paste it on top of every prompt. Line overrides:
accent detail on the tunic = thin SILVER piping (#d9d4cc); haze around the product #d9d4cc; the pen's own body colour is champagne
metal (#b8af95), never recoloured to the line colour.
MODEL: class per `prompts/exo-nad.md` §0; candidate ids from `research/higgsfield-models.json` — i2v-first-last: `minimax_hailuo`
(start+end image, 6 s, 1080) / `seedance_2_5` / `flux_3_video`; replace-object: `hf_mult_replace_object` (ref = our render);
upscale-video-x2 and still-photoreal ids per `costs.json` (absent at writing time). Price + balance to the owner, run after "approved".
Every 16:9 shot with people is generated AGAIN in 9:16 from its own vertical still (suffix `-v`); product-only shots are rendered.

**PEN (what the camera may see — `packaging-text.json` mitopen, `mitopen.js`; never retyped by the generator):** a slim
cordless pen, champagne-metal body; a rose-gold knurled grip ring and a rose-gold button, a small dark dot above the button;
vertical white 'MITOPEN' print along the body; an engraved V near the cone; a clear cartridge at the tip. NO cable, no case.

**Line negative (append after the shared negative):** `no needles visible, no blood, no red dots or bleeding points, no wounds,
no cable or cord, no charging dock, no box or case for the pen, no pen seen from its back (turn about its long axis <= 15 deg),
no turning grip ring, no light in the button or the dot, no numbers, depth scale, speed dial or UI, no lines or marks drawn on
skin, no writing pen or stylus look, no syringe or needle near the face`.

**Product fidelity:** pen = `site/proto/scenes/mitopen.js` via `render-keys.cjs` (v1-meet … v6-kit, 3840×2400, alpha) / packshot
`protocols/print/img/mitopen.webp` (273×891 — low; HD pending, chapter §7); V-TECH SYSTEM box = `v1-meet-box.png` (V-TECH chapter).
Method (a) composite into stills, (b) first/last frame + `hf_mult_replace_object` pass, (c) three.js overlay if the print drifts.
QA every frame: 'MITOPEN' legible, body ΔE ≤ 8 vs packshot, photographed side (button + print) toward camera, tip hidden on skin.

**Casting still `mitopen-K01`** (4:5, front + profile, still-photoreal): `Portrait photograph in set-R01 (reference attached): a
woman about 42, Fitzpatrick II–III, no make-up, white towelling headband, light cream robe, seated in the treatment chair, real
skin texture, a little tense but calm before her first microneedling session, dignified, 50mm, f/2, window light from the right,
fine grain.` QA: no invented skin condition; same face in F02, F06, F07, F10.

| shot | purpose · s · scroll · aspect | start → end frame | still prompt (key frame) | video prompt | extra negative | model + params · fidelity | QA |
|---|---|---|---|---|---|---|---|
| F01 | pen on the table, rung 1, home continuity · 3 s · 0–100 · 16:9, 9:16 crop | `set-T01` + `still.webp`/`v1-meet.png` → tighter crop | — (composite) | — (dolly-in in our pipeline) | — | none, 0 credits | contact shadow, pen lies flat, right third calm |
| F02 | concern in the mirror: each zone its own depth · 4 s · 100–240 · 16:9 + `-v` | `S02a` → `S02b` | `Over-the-shoulder into the round brass mirror in set-R01: mitopen-K01 in the chair looks at her face, slightly tense.` / b: `same, cast-C01 behind her, one hand on her shoulder, the index finger of the other hand pointing near (not touching) her neck; eyes meet in the mirror.` | `Slow lateral dolly; the cosmetologist steps in, rests a hand on her shoulder and points, without touching, at the forehead, then the cheek, then the neck; the client's shoulders relax; eyes meet in the mirror. Ends exactly on the last frame.` | `no markings, dots or lines on the skin, no touching the face` | i2v-first-last 5 s, 1080p | 5 fingers; no skin "flaw" drawn; same face as F10 |
| F03 | flight: pen lands by the V-TECH box · 3 s · 240–315 · rendered 16:9 and 9:16 | `set-T01` + V-TECH box render → pen on table + gloved hand (= F04 start) | — | — (three.js `flight(p)` added to `mitopen.js`: in-plane spin, long-axis turn ≤ 15°, per-frame contact shadow) | — | three.js, 0 credits; fallback i2v + replace-object | no back of pen, no roll, no bounce |
| F04 | discovery: balance in her fingers, quiet wow · 3 s · 315–430 · 16:9 + `-v` | F03 end → `S04` | `cast-C01's gloved hand holds the MITOPEN pen (reference render attached) like a pencil at a working angle against the warm window light, button and white print toward camera, tip toward the window; the V-TECH box soft below; her face soft, eyebrow raised, small smile; 50mm.` | `She lifts the pen from the table and balances it between two fingers, feeling its weight; window light slides along the champagne body and the knurled ring; a raised eyebrow and a quiet smile. Nothing on the pen moves or lights. Ends exactly on the last frame.` | `no button press, no ring turn` | i2v-first-last 5 s (use 3 s); pen replace-object | print side to camera; pen proportions = render |
| F05 | "texture" of a tool: macro along the body · 3 s · 430–505 · rendered 16:9 and 9:16 | render: macro camera path in `mitopen.js` over a blurred `set-T01` plate | — | — (three.js dolly cone → dot/button → print → ring → cartridge) | — | three.js, 0 credits | no needle detail in the cartridge; knurl = packshot; stop at the ring if no HD packshot |
| F06 | ritual: V-TECH serum first (protocol §1) · 2 s · 505–595 · 16:9 + `-v` | `S06a` → `S06b` | `Profile close-up 85mm: gloved fingers of cast-C01 touch the cheek of mitopen-K01 lying with eyes closed; the open V-TECH SYSTEM box (our render) soft at the frame edge, MITOPEN beside it.` / b: `a thin clear glossy layer of serum on one cheek zone.` | `Gloved fingers spread a thin, clear, glossy layer of serum over one small zone of the cheek; short dolly along the cheek. Ends exactly on the last frame.` | `no syringe, no cream-white texture` | i2v-first-last 3 s; V-TECH box replace-object if print drifts | serum clear; no device on skin yet |
| F07 | ritual: MITOPEN stamping · 3 s · 595–670 · 16:9 + `-v` · SAMPLE SHOT | `S07a` → `S07b` | `Low profile macro 100mm: cast-C01's gloved hand holds MITOPEN (reference render) against the cheekbone of mitopen-K01 at a shallow angle, the tip hidden by the angle, her other fingers gently stretching the skin.` / b: `pen mid-cheek, skin evenly and slightly flushed.` | `Rhythmic gentle stamping, zone by zone across the cheek; only the hand moves; the skin flushes slightly and evenly. Ends exactly on the last frame.` | `no visible tip contact, no pinpoint redness` | i2v-first-last 3 s; pen replace-object | even flush, not a wound; pen print/colour = render |
| F08 | "one pen, face and scalp" · 2 s · 670–720 | reuse `exosignal-hair-F07` (16:9 + 9:16) | — | — | — | none, 0 credits; only after HAIR F07 is approved | same rules as HAIR F07 |
| F09 | proof: real before/after V-TECH SYSTEM with MITOPEN · 5 s · 720–860 | MITODERM photos `media/mitopen/ba-01-*` | — | — (CSS clip-path wipe) | — | none | consent signed, no retouch; absent → dropped |
| F10 | joy: relief in the hand mirror · 4 s · 860–1000 · 16:9 + `-v` | `S10a` → `S10b` | `mitopen-K01 sitting up, holding a hand mirror, skin evenly and slightly flushed as after treatment, relieved smile; cast-C01 behind her setting the pen down on the table, quiet proud smile; 50mm, window light. Face IDENTICAL to K01.` | `Slow dolly-in to both; she looks at herself and smiles with relief; the cosmetologist lays the pen on the table and smiles quietly. Ends exactly on the last frame.` | `no glowing or improved skin` | i2v-first-last 5 s; character refs cast-C01, K01; pen composite (blurred) | flush = end of F07; natural smile |
| F11 | rung 5: "you can be her" · 3 s · 1000–1115 · 16:9 + `-v` | `S11a` → `S11b` | `cast-C01 alone leaning on the side table, MITOPEN in her hand at rest, the V-TECH SYSTEM box beside her (our renders composited); a: looking at the pen; b: looking into the lens, warm and confident; 35mm, right third dark wall.` | `She raises her gaze from the pen to the camera with calm, confident warmth. Locked camera.` | — | i2v-first-last 5 s (use 3 s); pen + box replace-object | live eyes; print; right third dark |
| F12 | family: line image · 2 s · 1115–1205 | `site/design/home/hero/desktop-b.webp` → `desktop-a.webp` (devices area) | — | — (dissolve + zoom-out) | — | none | no AI crowd/event |

**9:16 notes:** F02, F04, F06, F07, F10, F11 regenerated vertical (`-v` stills, same prompts + "vertical 9:16 framing, subject in
the middle 46% band"); F03 and F05 rendered 9:16 directly from `mitopen.js`; F01 centre crop; F08 = HAIR F07 vertical version.
**Order of runs:** after the EXO-NAD sample is approved and the owner answers the pen mechanics (chapter §7) → K01 stills →
owner's OK → F07 sample (most sensitive) → rest. Sounds are not part of the scroll film; "quiet" is shown by her calm face only.
