# Home page — production prompts (v3)

Working file, English. Companion of `src/01-home.md`. The home page needs almost no generation: the hanging pack, the line
cycle and the 13 transition clips come from our three.js scenes; the only paid items are the table plates of the clinic,
which also serve the 13 product films. Shared bible (cast, set, look, product fidelity, negative prompt, MODEL convention):
`prompts/exo-nad.md` §0 — it applies here unchanged.

## 1. Block 1 — the hanging pack (0 credits)

- **Source per product:** the S1 key of its scene: `site/public/<slug>/img/still.webp` (3840×2400, alpha cut from
  `render-keys.cjs` → `v1-meet.png`); V-TECH SYSTEM `site/design/vtech-3d/hd/v1-meet.webp`; EXOCELL MASK
  `site/design/exocell-3d/d1-meet.jpg`; MITOTECH CELL BOOSTER — render `v1-meet.png` from `site/proto/scenes/mitotech-cell-booster.js`
  (the packshot `site/design/mitotech/packshot-kit-r15.png` until then).
- **Line cycle (recommended option):** order V-TECH SYSTEM → EXO-NAD → MICRO BOOST 10% → MITOPEN → EXOSIGNAL HAIR (→ MITOTECH
  CELL BOOSTER if the owner wants six); each pack holds ≈32vh of the 200vh block; cross-dissolve 12 frames between packs; the
  glow behind changes with the pack: black+gold `#c9a24b` → champagne `#d8c48a` → green `#1E4634` → silver `#d9d4cc` →
  black+gold (→ MITOTECH `#144434` / `#78E0BC`, to confirm). Idle motion as on the product pages: breath ±1.5 %, yaw ≤ 10°
  toward the copy, sway ±1.5°; never more (several boxes have no photographed sides).
- **Engine:** the existing `SCENE` path of `engine/story.js` with one scene alive at a time, or pre-rendered 3840 stills with a
  CSS cross-dissolve when the device is `capped`. Reduced motion / no JS: one still (V-TECH SYSTEM).
- **QA:** the pack's print colours unchanged across packs (ΔE ≤ 8 to each packshot); nothing drawn but the pack, the glow and
  the haze; the right third of the frame free for the copy.

## 2. Table plates (paid stills; shared with the 13 films)

One room (`set-R01`, see `prompts/exo-nad.md` §1) and six table plates — one per line colour environment. Each plate is the
LAST frame of that line's transition clips and FRAME 0 of its product pages, with our render composited later. Generate at
16:9 (1920×1080 → upscale ×2) and 9:16 (1080×1920) each.

| id | lines / products | prompt (after the shared bible; then the shared negative) |
|---|---|---|
| `set-T01` | PEELING — EXO-NAD (champagne `#d8c48a`) | `Same room as set-R01 (reference attached): the low wooden side table with the stone top, empty, seen from table height, 35mm, the treatment chair and the round brass mirror soft in the background, warm window light from the right, a very soft shapeless champagne-gold haze in the air behind the table, the right third a dark stone wall in shadow; cinema camera, natural light, fine grain; no people, no products, nothing on the table.` |
| `set-T02` | V-TECH FACE (V-TECH SYSTEM, EXOTECH GEL) and HAIR (EXOSIGNAL HAIR, EXOSIGNAL SPRAY) — black + gold `#c9a24b` | same as T01 with `a very soft shapeless warm gold haze, the shadows deeper and more black` |
| `set-T03` | BIOSPICULE (MICRO BOOST 10%, CELLULAR AGE DEFENSE 2.5%, CELL RENEW 1.5%, DERMA RECOVERY CREAM) — green `#1E4634` | same with `a very soft shapeless deep-green haze low behind the table, the wood slightly cooler` |
| `set-T04` | DEVICES (MITOPEN, MITOSCAN) — silver `#d9d4cc` | same with `a very soft shapeless silver-grey haze, the stone top catching a cool highlight` |
| `set-T05` | MITOTECH CELL BOOSTER — box green `#144434`, mint `#78E0BC` (colours to confirm) | same with `a very soft shapeless dark-green haze with a faint mint edge` |
| `set-T06` | EXOCELL MASK — its own turquoise environment (`#6fb7ba`) | same with `a very soft shapeless turquoise haze behind the table` |

QA for every plate: same table, same camera height and lens, same window direction as `set-R01`; the table top empty and
evenly lit where the pack will stand (a 600×400 px clean zone at the frame's left-centre); the right third dark; no objects.
Composite step: `site/tools/composite.py` places the product's 3840 key on the table, scales it to the real size relation
(the EXO-NAD box front ≈ 1/3 of the table width), matches the light direction, adds a contact shadow and a faint reflection
on the stone — the result is `clinic-table-<slug>` (16:9 and 9:16).

## 3. The 13 transition clips (three.js, 0 credits; AI alternative below)

**Spec for `flight(p)` (added to each scene module, the same signature as `story(p)`):**
- p 0 → 0.15: the pack appears deep in the room above the table at ≈0.35 of its landing scale, already turning slowly
  about its vertical axis (one full turn over the flight; for boxes without photographed sides the sides are shown only in
  motion with a strong rim light, never held); the dark base of the home dissolves to the plate `set-T0x` between p 0 and 0.4.
- p 0.15 → 0.8: it approaches along a gentle arc, decelerating (ease-out), the turn slowing with it; the glow of the line
  follows it and thins out.
- p 0.8 → 1: it squares to the camera (yaw toward the copy as in its S1 pose), lands with a 0.3 s settle (2 % scale bounce,
  no overshoot in position), a contact shadow grows from the window's direction. For MITOPEN the pen lies down along the
  table edge; MITOSCAN glides and stands, no spin; EXOTECH GEL's cube rolls once and stands on a face; DERMA RECOVERY CREAM
  and EXOSIGNAL SPRAY: the jar/bottle leads and the box follows and stands beside it.
- Output: 1080p 16:9 (3 s = 72 frames at 24 fps; EXO-NAD 4 s; MITOPEN 2 s) and 9:16 from the same scene (the pack lands in the
  lower third); H.264 MP4 for playback (not scrubbed), muted; `clip.mp4` never in git. The last frame is written as a PNG and
  must be pixel-identical to `clinic-table-<slug>`.
- QA per clip, frame by frame: the print; ΔE ≤ 8 on the flat print area; no float at landing; the shadow direction; the 9:16
  composition; file ≤ 3 MB desktop / ≤ 1.5 MB phone.

**AI alternative (only if the owner finds the render "digital"):** `MODEL: per costs.json → i2v-first-last` + `replace-object`
with our render as the reference; first frame = the product's S1 key on the dark base, last frame = `clinic-table-<slug>`;
prompt template: `The [product description from site/packaging-text.md], exactly the one in the last frame, glides in from
the depth of the treatment room above the wooden table, turning slowly about its vertical axis, catches the warm window light
on its front, slows, squares itself to the camera and lands softly on the table with a tiny settle. Camera locked at table
height, 35mm. The dark studio background dissolves into the room during the first second. Natural window light, fine grain,
one continuous take, [N] seconds.` + shared negative + `the packaging never deforms or changes proportion, no hovering at the
end, no sparkle trail`. Then the replace-object pass and the frame-by-frame print check; a clip that fails is replaced by the
three.js render.

## 4. Block 4 — the clinic glimpse loop (0 credits)

A 5 s muted loop cut from EXO-NAD's F06 frames (hands on the cheek, no face in the crop): desktop 16:9 crop of the lower-left
two-thirds, phone 9:16 centre crop on the hands; `loop` with a 12-frame cross-fade; `playsinline`, `muted`, a visible pause
control (WCAG 2.2.2); click → the EXO-NAD page (plays its transition clip first). No separate generation.

## 5. Phone

- Block 1 stage: the same S1 keys cropped to the stage (≈46 % of the screen height), the pack centred; the line cycle as on
  desktop.
- Transition clips: the 9:16 renders of §3; start on tap (user gesture), ≤ 1.5 MB, 720×1280 is enough at DPR 3 under the
  grain overlay.
- Plates: generate 9:16 versions of `set-T01…T06` from their own prompt (not a crop).

## 6. Order and attempts

1. `set-R01` → owner's OK on the room → `set-T01` (EXO-NAD first, it is the sample) → composite `clinic-table-exo-nad` → the
   EXO-NAD flight in three.js → the owner sees ONE transition end to end.
2. Then `set-T02…T06` and the other 12 flights, one line at a time.
3. Attempts: 1 / 2 / 4 per paid still (low / likely / high); three.js items cost time, not credits.
