# Asset licence registry — `aquarium/` media (R7)

**Purpose.** One row per media file shipped in `aquarium/` (the whole folder is copied into the `.app`
by `macos-app/build.sh`, minus the exclusions noted below): file → source (Adobe Stock ID, or
"derived from <id>", or procedural/own) → licence type → licence date → account → derivation.
This is the durable record required by ROADMAP §2 step 2 / R7 (KR2: registry covers 100 % of media in
the build). It lives outside `aquarium/` on purpose so it is never bundled into the app.

**R7 note.** Every photo and video currently in the build comes from the **Adobe Stock Free
collection**, licensed at $0 under the owner's personal Adobe account on 16–17 Oct 2026. Free-collection
assets carry the **Standard licence (photos)** and the **Enhanced licence (video)** — both allow
embedding in software but forbid stand-alone redistribution and products whose primary value is the
asset itself, and the free collection cannot be upgraded to Extended (video has no Extended at all).
Consequences (owner's decisions, ROADMAP §2): **paid packs (species packs, "own fish") must use own
assets only**; the stock backdrop video is the high-risk item (R8) and must be replaceable by an update;
no attribution is required, but stock must not be used in the icon or logo; the licences are
non-transferable, so sales must run under the account that holds them (re-license if a company sells).

**Sources of truth** (this file summarises them; if they disagree, the License History on
stock.adobe.com wins): `aquarium/scene/README.txt` (sources & licences tables), `aquarium/fish/manifest.js`,
`aquarium/fish/PROMPTS.md`, `aquarium/scene/corals/catalog.js` (`sourceId`), `aquarium/assets/README.txt`,
`aquarium/blender/README.md`, `tools/aquarium-test/art/README.md`, `tools/aquarium-test/make_media.sh`,
and the agent's scratch download index (`scratchpad/stock/dl/INDEX.md`, `scratchpad/stock/video/dl2.sh`
— ephemeral; this file replaces it).

**How to update.** When a media file is added, replaced or re-derived in `aquarium/`, edit this file in
the **same commit**: add/modify the row (ID from the stock.adobe.com URL, licence date from
*License History*, derivation in one line), update the counts, and move the ID out of the
"licensed but unused" list if it becomes used. Keep the per-stage notes in `scene/README.txt` as before;
this file is the index. Before release (ROADMAP §2 step 2) export License History and tick, per ID:
licensed on stock.adobe.com (not Adobe Express "Limited"), not Unmetered, not Editorial, not
"Generated with AI".

Account for every stock row below: **owner's Adobe account** (personal), Free collection, $0.
"Std" = Adobe Stock Free collection, Standard licence (photo). "Enh" = Adobe Stock Free collection,
Enhanced licence (video; confirm the type in License History — ROADMAP §2).
"In .app" = Yes unless `macos-app/build.sh` strips it.

## Counts (2026-10-22)

| | files |
|---|---|
| Media files in `aquarium/` | **79** |
| Std — photo cut-outs and derivatives (25 stock photos) | 56 |
| Enh — video 188049047 loop, posters and derived masks | 8 |
| Procedural / own (Blender renders, **not bundled**) | 14 |
| UNKNOWN — verify (**not bundled**) | 1 |
| Bundled into the `.app` | 64 (56 Std + 8 Enh) |
| Distinct stock IDs used | 26 (25 photos + 1 video) |
| Licensed but not used | 56 IDs (40 photos + 16 videos) — see last section |

Licence-date caveat: the scratch index records the A0 photos (264961754 backdrop and the five fish
photos 177282746, 138368184, 647601394, 1132472143, 317344814) as licensed on 2026-10-16, but their
cut-outs were already committed on 2026-09-18 (commit 4f49fb8, "licensed under the repo owner's
account"). The 2026-10-16 date is therefore a re-download; the original licence event is earlier —
confirm the real date in License History and correct the rows.

## 1. Backdrops and video loop — `aquarium/assets/`

| File | px | Source | Licence | Licence date | Derivation | In .app |
|---|---|---|---|---|---|---|
| `assets/reef_day.mp4` | 2560×1440, 20.02 s | Adobe Stock **188049047** "Red Sea reef, static camera" (3840×2160 H.264, 28.16 s) | Enh | 2026-10-17 | `tools/aquarium-test/make_media.sh`: seamless loop (frames 138–737, 40-frame cross-fade), downscale, DAY "Maldives" grade via 3D LUT (`reef_grade.py`), H.264 High yuv420p 29.97 fps, no audio; V5 re-encode: edge chroma blur, keyframe every 2 s | Yes |
| `assets/reef_night.mp4` | 2560×1440, 20.02 s | 188049047 | Enh | 2026-10-17 | same loop, NIGHT "royal-blue LED" grade | Yes |
| `assets/reef_day.jpg` | 2560×1440 | derived from 188049047 | Enh | 2026-10-17 | poster = exact first frame of the day loop (JPEG q88) | Yes |
| `assets/reef_night.jpg` | 2560×1440 | derived from 188049047 | Enh | 2026-10-17 | poster = exact first frame of the night loop | Yes |
| `assets/reef_bg.jpg` | 2560×1355 | Adobe Stock **264961754** "Corals in a Marine Aquarium" (5760×3048) | Std | 2026-10-16 (see caveat) | photo-scene backdrop: downscale to 2560, A0 grade (LED violet cast → blue-teal water), A2 inpaint retouch of narrow strips at patch edges, re-encoded once (q88, 4:4:4) | Yes |
| `assets/alt/reef_bg_sea_aquarium.jpg` | 2560×1707 | **UNKNOWN — verify** (added 2026-09-18 in 4f49fb8 as "natural-light alternative backdrop"; no stock ID recorded anywhere; presumably Adobe Stock Free collection) | UNKNOWN | — | downscaled photo, unmodified otherwise; not loaded by the engine | **No** (stripped by build.sh) |
| `assets/render/reef_bg.jpg` | 1920×1200 | procedural/own — Blender Cycles render from `aquarium/blender/reef.py` | own | — | procedural reef (sand, rock wall, corals, sponges, anemones); alternative style, not loaded | No (stripped) |
| `assets/render/reef_fg.png` | 1920×1200 | procedural/own — `aquarium/blender/reef.py` | own | — | transparent foreground layer of the same render | No (stripped) |

## 2. Fish sprites — `aquarium/fish/`

All photo fish: rembg (ISNet) cut-out from the stock photo, crop, oriented facing right, A0 underwater
grade (white balance to the backdrop, top light), edge clean-up in d0979c2 ("cleaned fish",
2026-10-17). Scratch notes call these the "A0 fish sources".

| File | px | Source | Licence | Licence date | Derivation | In .app |
|---|---|---|---|---|---|---|
| `fish/clownfish.png` | 1000×458 | Adobe Stock **177282746** "Set of tropical saltwater fishes on black background" (5184×3456 composite) | Std | 2026-10-16 (see caveat) | cut-out of one fish from the composite | Yes |
| `fish/yellow_tang.png` | 1000×664 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/powder_blue_tang.png` | 923×413 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/emperor_angelfish.png` | 803×601 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/flame_angel.png` | 1000×671 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/anthias.png` | 1000×464 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/copperband.png` | 911×625 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/sergeant_major.png` | 1000×555 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/striped_surgeon.png` | 1000×385 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/orange_spot_surgeon.png` | 1000×375 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/coral_grouper.png` | 968×490 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/butterflyfish.png` | 1000×593 | 177282746 | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/blue_tang.png` | 1000×451 | Adobe Stock **138368184** "The Real Nemo and Dory" | Std | 2026-10-16 (see caveat) | cut-out of the blue tang ("Dory") | Yes |
| `fish/pufferfish.png` | 1000×477 | Adobe Stock **647601394** "Clown Triggerfish swimming in aquarium" | Std | 2026-10-16 (see caveat) | cut-out; the file name is historical — the sprite is a clown triggerfish (manifest name matches the fish) | Yes |
| `fish/regal_angelfish.png` | 1000×701 | Adobe Stock **1132472143** "Regal angelfish (Pygoplites diacanthus) in the coral reef" | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/moorish_idol.png` | 1000×762 | Adobe Stock **317344814** "Zanclus cornutus fish on a white background" | Std | 2026-10-16 (see caveat) | cut-out | Yes |
| `fish/goldfish.png` | 1000×674 | Adobe Stock **892154672** "Oranda goldfish isolated on white background close up" | Std | 2026-10-17 | re-matted against studio white (white belly/fins kept), A0 grade (379ac6a); V5 `art/goldfish_alpha.py`: veil fins α 158 → 247, 4 px feather (328e878) | Yes |
| `fish/render/blue_chromis.png` | 1200×599 | procedural/own — Blender Cycles, `aquarium/blender/fish.py` | own | — | parametric fish, numpy-baked colour; alternative style, not loaded | No (stripped) |
| `fish/render/blue_tang.png` | 1200×876 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/clownfish.png` | 1200×638 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/emperor_angelfish.png` | 1200×968 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/flame_angel.png` | 1200×723 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/mandarinfish.png` | 1200×690 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/moorish_idol.png` | 1200×1462 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/powder_blue_tang.png` | 1200×896 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/pufferfish.png` | 1200×854 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/regal_angelfish.png` | 1200×926 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/royal_gramma.png` | 1200×608 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |
| `fish/render/yellow_tang.png` | 1200×944 | procedural/own — `blender/fish.py` | own | — | as above | No (stripped) |

Manifest species without a PNG (royal_gramma, mandarinfish, blue_chromis, bicolor_angel,
spanish_hogfish) draw as vector fallbacks — no media file, nothing to license. No AI-generated fish
(`fish/PROMPTS.md`) exist in the repo yet; when they do, add rows with prompt + generation date and
mark them "own (AI-generated, not copyrightable — no exclusivity)".

## 3. Props — `aquarium/scene/props/` (stage A1, 2026-10-16)

Common derivation (scene/README.txt, A1): rembg isnet-general-use cut-out + alpha curve, edge keyed
against the studio background, 1 px erosion + colour decontamination, ~1.5× backdrop pixel scale,
white balance to backdrop sand (70 %), local black/white point (60 %), top light, darkened base.

| File | px | Source | Licence | Licence date | Derivation | In .app |
|---|---|---|---|---|---|---|
| `scene/props/anemone.png` | 770×717 | Adobe Stock **555478310** "Tube anemone / cylinder anemone, Cerianthus membranaceus" | Std | 2026-10-16 | back layer: tentacle key "thin light structure on dark water", tube hand-contoured; neighbouring anemone, seahorse, sand removed | Yes |
| `scene/props/anemone_front.png` | 770×717 | derived from 555478310 (same frame as anemone.png) | Std | 2026-10-16 | front layer: tentacles hanging below the disc (back+front == whole anemone) | Yes |
| `scene/props/anemone_front_crown.png` | 770×717 | derived from `anemone.png` (555478310) | Std | 2026-10-16 | V5 `art/crown_cut.py`: front crown in an ellipse 0.42×0.17 around the nest, no bright centre, α×0.85; R2c-2: stalk below the disc removed (bb2a8ba) | Yes |
| `scene/props/crab.png` | 290×130 | Adobe Stock **318496474** "Velvet crab in studio" | Std | 2026-10-16 | cut-out, squashed vertically ×0.72 (sand-level view) | Yes |
| `scene/props/crab_body.png` | 290×130 | derived from 318496474 (same frame) | Std | 2026-10-16 | body without claws (body + claws at angle 0 == crab.png) | Yes |
| `scene/props/crab_claw_l.png` | 290×130 | derived from 318496474 (same frame) | Std | 2026-10-16 | left claw cut separately for the hinge animation | Yes |
| `scene/props/crab_claw_r.png` | 290×130 | derived from 318496474 (same frame) | Std | 2026-10-16 | right claw | Yes |
| `scene/props/starfish.png` | 262×225 | Adobe Stock **275155162** "isolated starfish on a white background" | Std | 2026-10-16 | cut-out, rotated to stand on two arms, ×0.90 vertical (used by the photo scene) | Yes |
| `scene/props/starfish_floor.png` | 262×126 | derived from `starfish.png` (275155162) | Std | 2026-10-16 | R2c `art/r2c_assets.py`: lying star — vertical squash to 0.56, far edge 8 % narrower (perspective on premultiplied alpha) | Yes |
| `scene/props/tube_sponges.png` | 508×489 | Adobe Stock **413607513** "Colorful yellow tube sponge in caribbean sea" | Std | 2026-10-16 | cut-out keyed "yellow vs blue-teal", big tube + mirrored second tube behind (×0.70, darker); V5 `art/sponge_retouch.py`: lime → ochre-yellow, despill, 1 px alpha erosion (photo scene only) | Yes |

## 4. Coral colony library — `aquarium/scene/corals/` (V3 2026-10-17, "corals-2" 2026-10-18, R2c 2026-10-21, batch 3 2026-10-22)

Common derivation (scene/README.txt, V3): rembg (isnet / birefnet) rough mask → edge refinement by
"projection on F−B" key, edge colour unmixed and decontaminated, neighbours/fish/rocks removed by
polygons or clone patches, LANCZOS downscale on premultiplied alpha (long side ≤ 1200 px), 2 px α=0
border, DAYLIGHT grade in linear light (LED/UV hues mapped to pastel natural colours, top light,
darkened base). `sourceId` per colony is also recorded in `corals/catalog.js`.

| File | px | Source | Licence | Licence date | Derivation | In .app |
|---|---|---|---|---|---|---|
| `scene/corals/gorgonian_pink.png` | 1200×988 | Adobe Stock **191997240** "Beautiful Sea Fan" | Std | 2026-10-16 | large gorgonian colony (centre/right of frame); "fan vs water" key; anthias replaced by clone patches | Yes |
| `scene/corals/gorgonian_red.png` | 1102×1038 | 191997240 | Std | 2026-10-16 | single red fan at the left of the same frame | Yes |
| `scene/corals/soft_tree_white.png` | 776×1003 | Adobe Stock **616540286** (white soft coral + sea fan + pink soft corals on dark reef) | Std | 2026-10-17 | white "tree" soft coral (Dendronephthya/Litophyton) | Yes |
| `scene/corals/soft_orange.png` | 703×578 | 616540286 | Std | 2026-10-17 | orange-pink soft coral at the right of the same frame (last touch 94ef17b) | Yes |
| `scene/corals/finger_leather.png` | 718×802 | Adobe Stock **506270057** (coral farm frags on racks) | Std | 2026-10-17 | finger leather coral (Sinularia); violet LED → daylight cream; curled left branch removed | Yes |
| `scene/corals/carpet_mound.png` | 903×545 | Adobe Stock **733928665** (Andaman soft/mushroom corals) | Std | 2026-10-17 | carpet "mound" from the left of the frame; purple → pastel | Yes |
| `scene/corals/tube_sponges_lilac.png` | 668×902 | Adobe Stock **824786923** (lilac tube sponges on reef) | Std | 2026-10-17 | cut-out, natural light | Yes |
| `scene/corals/tube_sponges_yellow.png` | 668×902 | derived from `tube_sponges_lilac.png` (824786923) | Std | 2026-10-17 | R2c `art/r2c_assets.py`: luminance-ramp recolour ochre → yellow → cream, same alpha (a5cf513) | Yes |
| `scene/corals/stylophora.png` | 763×611 | Adobe Stock **180252895** (Stylophora colony on black, aquarium) | Std | 2026-10-17 | frag plug removed; UV-LED → daylight cream/dusty pink | Yes |
| `scene/corals/acropora_staghorn.png` | 533×352 | Adobe Stock **157134933** (public aquarium reef, natural light) | Std | 2026-10-17 | staghorn acropora cut from the frame (in catalogue, not placed in the video scene since R2c) | Yes |
| `scene/corals/acropora_corymbose.png` | 658×353 | 157134933 | Std | 2026-10-17 | corymbose acropora from the same frame; actinic blue → beige-lilac | Yes |
| `scene/corals/acropora_bush.png` | 364×238 | 157134933 | Std | 2026-10-17 | small cream acropora bush, native size | Yes |
| `scene/corals/brain_dome_olive.png` | 598×473 | Adobe Stock **327247064** (brain dome Wellsophyllia on black) | Std | 2026-10-17 | owner-selected; actinic → daylight olive-khaki hue map (2ff86d0, QA 7a2b95a) | Yes |
| `scene/corals/brain_favia_mauve.png` | 614×394 | Adobe Stock **418791796** (massive brain coral Favia/Favites on black) | Std | 2026-10-17 | LED → daylight mauve; crushed black crevices lifted (QA) | Yes |
| `scene/corals/brain_open_green.png` | 468×281 | Adobe Stock **192532117** (open brain Trachyphyllia, right of frame) | Std | 2026-10-17 | purple LED → daylight; disc muted olive-khaki (QA); sibling brain_open_red from the same photo was dropped | Yes |
| `scene/corals/sps_purple.png` | 718×513 | Adobe Stock **823216913** (purple branching SPS foreground) | Std | 2026-10-17 | actinic → daylight purple-crimson; cut along the natural contour (QA) | Yes |
| `scene/corals/seawhip_orange.png` | 836×961 | Adobe Stock **428884773** (orange sea whips Ellisella, natural light) | Std | 2026-10-17 | "orange vs water/reef" colour key | Yes |
| `scene/corals/gorgonian_bush_red.png` | 1191×577 | Adobe Stock **444143131** (white-red gorgonian bush on blue water) | Std | 2026-10-17 | "fan vs water" key; brown fan, crinoid, fish, sponges and cave removed (QA) | Yes |
| `scene/corals/cauliflower_yellow.png` | 923×701 | Adobe Stock **347525870** ("typical red sea coral structure with anthias fish", Red Sea, natural light) | Std | 2026-10-22 | yellow cauliflower coral (Pocillopora verrucosa) cut on blue water; fish replaced by silhouette patches of the same texture; QA rebuild ad9fbfe (lower-right lobe recovered). In the catalogue, not placed in the scene; fallback/benchmark for the own 3D yellow coral (ROADMAP R2b) | Yes |

## 5. Scene masks, occluders and patches — `aquarium/scene/`

| File | px | Source | Licence | Licence date | Derivation | In .app |
|---|---|---|---|---|---|---|
| `scene/mask_left.png` | 1280×1392 | derived from video 188049047 | Enh | 2026-10-17 | V2: grey+alpha occluder mask of the left pillar in 2560×1440 frame coordinates; water↔reef matting, minimum over 16 loop frames (1963406) | Yes |
| `scene/mask_right.png` | 1264×1256 | derived from 188049047 | Enh | 2026-10-17 | right pillar mask, as above | Yes |
| `scene/mask_far.png` | 784×1016 | derived from 188049047 | Enh | 2026-10-17 | far reef in the canyon, as above | Yes |
| `scene/light_mask_video.png` | 640×360 | derived from 188049047 | Enh | 2026-10-17 | alpha-only caustics mask for the video scene (sand ≈ 1, lit coral faces 0.15–0.8, water 0) | Yes |
| `scene/light_mask.png` | 640×339 | derived from photo 264961754 | Std | 2026-10-16 (see caveat) | alpha-only caustics mask for the photo scene (A2; illumination × "faces up", sand = 1) | Yes |
| `scene/occ_mound.png` | 1376×811 | derived from 264961754 | Std | 2026-10-16 (see caveat) | A2 occluder: crop of the FINAL graded backdrop with alpha from a max(R,G,B) > 97 threshold inside a hand polygon; mip-aligned | Yes |
| `scene/occ_front_frags.png` | 640×171 | derived from 264961754 | Std | 2026-10-16 (see caveat) | A2 occluder crop (front frags), as above | Yes |
| `scene/patch_white_anemone.png` | 288×427 | derived from 264961754 | Std | 2026-10-16 (see caveat) | A2 swaying patch: crop of the backdrop BEFORE retouch with an opaque dark-water field; mask = R-channel threshold in a hand polygon | Yes |
| `scene/patch_white_anemone_core.png` | 288×427 | derived from 264961754 | Std | 2026-10-16 (see caveat) | alpha-only "core" (the coral itself, no water field) used to subtract the patch from the backdrop | Yes |
| `scene/patch_pink_anemone.png` | 384×459 | derived from 264961754 | Std | 2026-10-16 (see caveat) | A2 patch, as above | Yes |
| `scene/patch_pink_anemone_core.png` | 384×459 | derived from 264961754 | Std | 2026-10-16 (see caveat) | alpha-only core | Yes |
| `scene/patch_frogspawn.png` | 256×235 | derived from 264961754 | Std | 2026-10-16 (see caveat) | A2 patch (G-channel threshold) | Yes |
| `scene/patch_frogspawn_core.png` | 256×235 | derived from 264961754 | Std | 2026-10-16 (see caveat) | alpha-only core | Yes |

The depth grid, spots, lanes and all placement data live in `scene/scene.js` (code, no stock content).

## 6. Stock IDs used (26)

Photos (25, all Std): 264961754, 177282746, 138368184, 647601394, 1132472143, 317344814, 892154672,
555478310, 275155162, 318496474, 413607513, 191997240, 616540286, 506270057, 733928665, 824786923,
180252895, 157134933, 327247064, 418791796, 192532117, 823216913, 428884773, 444143131, 347525870.
Video (1, Enh): 188049047.

## 7. Licensed (free collection, $0) but NOT used in the build — 56 IDs

Nothing from these is in `aquarium/`; the originals exist only in the agent's scratch folder. They
still appear in the owner's License History, so they are listed here to avoid confusion. If any of
them is used later, move it to the tables above.

**Photos (22), licensed 2026-10-16 / 2026-10-17:**

| ID | What it is | Why unused |
|---|---|---|
| 236307105 | Euphyllia torch coral under UV | A1 anemone alt; neon-green, not daylight |
| 191511540 | Beadlet anemone (Actinia equina) | A1 anemone alt |
| 371275513 | Dry starfish on white | A1 starfish alt |
| 263235037 | Crab isolated on white | A1 crab alt |
| 281527531 | Huge sponges and tropical fish on a reef | barrel sponge in shade/haze |
| 303351378 | Red gorgonian fan on white | studio, flat |
| 483500005 | Green Acropora macro | texture without a colony silhouette |
| 1569072275 | Montipora macro | texture only |
| 272913972, 206037775, 289106529, 311303045, 97008304, 311304727, 582898854, 448175503 | goldfish candidates (8) | 892154672 chosen instead |
| 403030041, 112497609, 445953902 | brain-coral macro textures (corals-2 review) | no dome silhouette |
| 504265139 | zoanthid carpet, actinic macro | no silhouette, daylight colour unrecoverable |
| 483500043 | polyp macro under blue light | no silhouette |
| 1430578512 | decorator crab | algae over shell, flash colours — not separable |

**Photos (18), licensed 2026-10-22 (stock batch 3 — yellow branching coral and barrel sponge search):**

| ID | What it is | Why unused |
|---|---|---|
| 315953314 | Marsa Alam fire-coral thicket with anthias | soft, chromatic fringing at 100 %, fish everywhere |
| 440175833, 440175889 | Acropora millepora on black, actinic LED | neon colours |
| 440175816 | Acropora tenuis frag on black | tiny frag |
| 216917159 | purple Acropora, blue LED | LED colours |
| 348678194 | Montipora digitata "Forest Fire", blue LED | LED colours |
| 314939252 | staghorn frags hanging on lines | separate branches, not a colony |
| 376592491 | staghorn branch macro | single branch |
| 524620950 | elkhorn coral, Curaçao, backlit | brown, merges with the reef behind |
| 164718346 | Red Sea Porites knobs | not branching |
| 286762658 | pillar coral + sponge, Curaçao | brown pillars, no barrel |
| 390097845, 74185524 | coral skeletons on white | dead skeletons |
| 273568208 | Eilat table corals | murky |
| 335220660 | Maldives brown Acropora tables | wrong form/colour |
| 1175331122 | Bonaire reefscape with parrotfish | no separable colony |
| 1175705008 | coral farm frags on a PVC frame | frags, not colonies |
| 302861284 | Egypt reef, portrait | no separable colony |

281527531 (barrel sponge, licensed 2026-10-16, above) was retried in batch 3: the clean half is too small and a mirrored
composite looked synthetic — still unused. The missing yellow branching coral and barrel sponge are being made as
**own procedural 3D assets** (ROADMAP R2b), which will get their own rows here as "Procedural / own".

**Videos (16), full-resolution downloads dated 2026-10-17:**

| ID | What it is | Note |
|---|---|---|
| 398953025 | blue water, sun rays, fish school (ProRes) | optional ray layer; not used |
| 305660194 | blurred light rays / bokeh (MJPEG) | optional light layer; not used |
| 115766638 | turquoise shallows, static, surface visible | rejected |
| 650749671 | Caribbean sea rods swaying | rejected (drift) |
| 673167220, 679269701 | AI-painted reef loops | rejected (painterly, baked fish) |
| 600040262, 628562270, 431682596, 452779608 | second download batch (`dl2.sh`), reviewed on contact sheets | not in the scratch index; **presumed licensed — verify in License History** |
| 206511744, 285801729, 286136260, 422998833, 560477793, 626523422 | first download batch (09:44–09:48), reviewed on contact sheets | no download log survives; **presumed licensed — verify in License History** |

## 8. Out of scope of this registry

- `tools/aquarium-test/media/` (VP9 test copies of the loop, LUTs) — gitignored, never bundled; same
  source 188049047.
- `tools/aquarium-test/refs/target_day.webp` — the owner's reference image for composition only; not
  shipped. Its provenance is the owner's.
- App icon / logo — must not contain stock (ROADMAP §2); nothing stock-derived is used there today.
