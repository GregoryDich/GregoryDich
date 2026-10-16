# Aquarium engine — architecture review & spec (source of truth for all stages)

Produced by the architecture review of the plan. Coordinates/line numbers refer to aquarium/index.html at commit 041f9c0.

I've finished the review. I didn't modify anything. The main conclusion is that the draft is built and tested in headless Chromium, but the real target is WKWebView (WebKit) loading `file://`. That mismatch hides several critical problems. The rest of the plan is ordered by severity.

---

# 1. Facts from the code that change the plan

| # | Finding | Location | Consequence |
|---|---|---|---|
| F1 | **`ctx.filter` is not enabled by default in Safari/WebKit**, up to and including 26.x (caniuse: 18.0–26.5 "disabled by default"). The `HAS_FILTER` check correctly returns false there. | `index.html:54`, `:109-114`, `:116-126` | On the Mac, `graded()` returns the raw photo and `makeLod()` never blurs. **The user has never seen the grade or blur the headless tests show.** Any texture the draft builds with `filter` (shaft blur, softened sprites) won't exist on the target. |
| F2 | **file:// taints canvases.** Chromium treats file:// as an opaque origin, and WKWebView `loadFileURL` likely does the same (`WallpaperWindow.swift:loadAquarium`). Any `getImageData` on a canvas that has had a loaded image drawn into it throws `SecurityError`. | — | Never read pixels back from asset-derived canvases. Ship scene geometry as JS data, never as images to read. Test under file:// (`http-server` hides this). |
| F3 | The draft is wrong that `streamX` is never set. `resize()` always calls `buildScenery()` (`:985`), which sets `streamX = W*0.72` (`:573`). | `:573`, `:980`, `:1007-1015`, `:476` | The real bug: `floorY=0.78H` and `streamX` belong to the procedural layout and have nothing to do with the photo. Random bubbles appear out of nowhere in front of the rocks at `y=0.78H`. Bubble rise speed is 28–100 px/s, about 10–40 s to cross the screen; real bubbles take ~2–3 s, so they look floaty and toy-like. |
| F4 | Sand is never visited. At 1920×1200 the photo's sand starts at ~0.81H, but fish are clamped to `floorY - 0.28·len` with `floorY = 0.78H`. | `:302`, `:316`, `:980` | The bottom ~20% of the screen is dead space for fish. |
| F5 | Fish speed is not scaled by `sizeScale()`, but fish length is. | `:249`, `:260` | At large CSS widths fish are up to 2.8× bigger but move at the same px/s, so they look sluggish. Speeds should be in body lengths per second. |
| F6 | The tail wave is **vertical**: up to 8% of h at the tail. | `:342-350` | A fish seen from the side beats its tail toward and away from the camera, which shows up as the tail getting **narrower and wider**, not moving up and down. The current dolphin-like up/down flap is a strong fake cue. |
| F7 | Every fish has a floating radial-gradient "contact shadow" in open water, created fresh every frame. | `:336-338` | It reads as a drop-shadowed sticker. Remove it and replace it with a floor shadow only near the sand. |
| F8 | Crop maths. `drawCover` with `BG_ZOOM=1.12`, anchored to the bottom (`:163-169`): on the MacBook (1512×982 CSS, aspect 1.54) only photo x∈[0.136, 0.864] is visible. On a 1920×1080 "looks like" mode it's [0.08, 0.92]. | — | The photo's pink long-tentacle anemone (x≈0.87–1.0) is **off-screen on the MacBook**. Anything anchored in screen fractions slides relative to the reef between aspect ratios. Every reef-attached item must be anchored in **backdrop space**. |
| F9 | Backdrop defects (I viewed `assets/reef_bg.jpg`): (a) hard-edged, saturated blue blotches on the grey rock, left sand and left rocks (likely from the hue-selective "toward blue-teal" correction); (b) an orange room wall visible through the glass at top-right (x≈0.85–0.95, y<0.12); (c) **no water surface** in frame, and coral tops are cut off. It is also dark. | asset | A "shimmer band" painted over the coral tops would read as fog. The blotches look painted. The grade has to be fixed offline (also because of F1). |
| F10 | Sprite problems. `clownfish.png` has a green anemone remnant on its belly. Sprites are studio-lit (clownfish on white, anthias on black) and the near LOD is the untouched original. `blue_tang.png` has dark/green fringe on its edges. | `fish/*.png`, `:125` | Near fish look pasted in. They need an offline scene white-balance, a top-down light gradient and edge cleanup. |
| F11 | Headless timing is not real time. At 3.5 fps, `raw` is clamped to 0.1 and `dt` to 0.05, so positions run at ~17% speed. But `t = now/1000` (real time) drives tail, bob and rays. | `:992-1002` | Frame sequences from headless runs are not valid for motion review. A deterministic step API is required. |
| F12 | Missing files: `reef_fg.png` (`:104`, `:134-140`) and the five `count:0` species images (`:221-226`) cause error noise. README says `background.jpg` takes priority, but the code tries `reef_bg.jpg` first (`:100-103`). | — | Fold into the foundation stage. |
| F13 | `build.sh` copies the **whole** `aquarium/` folder into the .app (`cp -R ../aquarium`). | `macos-app/build.sh` | Raw stock downloads, previews and the test harness must live **outside** `aquarium/`. |
| F14 | Wallpaper mode turns input off (`:1066-1080`). | — | The draft's "feed (click food keeps priority)" never happens on the wallpaper, so the story needs an autonomous feeding event. |
| F15 | Backing store. Canvas size is `W*DPR`, with DPR capped at 2. | `:51`, `:982` | External 4K at "looks like 2560×1440" gives 5120×2880 (14.7 MP). A 6K XDR at "looks like 3840×2160" gives 7680×4320 (33 MP, ~133 MB per buffer), and that is per screen, since each monitor is a separate WebContent process (`AppDelegate.rebuildWindows`). The photo source is only 2560 px wide, so anything above ~1.5× of 2560 is wasted. |

# 2. Platform constraints (fixed rules for every stage)

1. **No `ctx.filter` anywhere in shipped paths.** Bake grading offline. Make blur by drawing a canvas down to 1/4–1/8 and back up. Build every texture with `ImageData` math on procedurally generated data only.
2. **No `getImageData`** on anything that has had a loaded image drawn into it. CPU-side samplers (caustic intensity, light) use Float32Arrays generated in JS. Scene geometry (depth grid, polygons, spots) is JS data.
3. **Target API level is Safari 16.1** (`LSMinimumSystemVersion 13.0`).
   - Don't use: `OffscreenCanvas`, `ctx.reset()`, `ctx.filter`.
   - Safe to use: `createPattern` + `CanvasPattern.setTransform`; composite modes `lighter`, `screen`, `multiply`, `darken`, `source-atop`, `destination-in`; `setTransform`; `imageSmoothingQuality`.
4. **Render-scale cap.** `RS = min(DPR, sqrt(8.3e6 / (W·H)))`, applied in `resize()` instead of DPR. Optionally cap at 5 MP when `POWER === 'low'`. Results:
   - MacBook 14": 3024×1964, unchanged.
   - 4K at "looks like 2560": 3840×2160.
   - XDR at "looks like 3840": 3840×2160.
5. **On-device quality governor.** We can't test on the M4, so the engine measures itself. If the 90th-percentile rAF interval is over 1.25× the target for 5 s, step down in this order: particles −50% → fish slices −30% → caustic buffer 0.5→0.35 → RS −15%. Recover after 30 s of good frames. Log the current level in `?debug=1`.

# 3. Architecture and data contracts (replaces the draft's `props/manifest.js` and `occluders.js`)

**One scene file**, `aquarium/scene/scene.js`, holding `window.AQUARIUM_SCENE`. It applies only when `scene.backdrop.src` matches the backdrop that actually loaded. If the user drops in another background, there is no scene and nothing is misplaced. Coordinates are **backdrop fractions** (bx, by) unless noted. z is world depth, where 1.0 = glass and about 2.6 = back wall.

```js
window.AQUARIUM_SCENE = { version: 1,
  backdrop: { src:"assets/reef_bg.jpg", w:2560, h:1355, zoom:1.08, anchor:"bottom", safeX:[0.14,0.86] },
  camera:   { horizonBy:0.42, zNear:1.0, depthPx:0.31 /* 1 z-unit = 0.31·W glass-plane px */, fogSigma:0.42 },
  surface:  { bandH:0.075 /* of screen H */, mirrorRows:0.14 },
  depthGrid:{ cols:32, rows:17, z:[ /* backdrop-surface depth per cell; rock faces ≈1.3–2.0, open-water gaps 2.6 */ ] },
  floor:    [[bx,by], ...],                 // sand contact polyline (fish lower bound, shadows, crab path)
  light:    { color:"#d6ecff", sources:[{bx:0.34,byAbove:-0.35,streaks:5,spread:9},{bx:0.70,byAbove:-0.35,streaks:4,spread:8}],
              caustics:{ mask:"scene/light_mask.png" /* alpha PNG, 1/4 res */, strength:0.32 } },
  occluders:[{ id:"mound", src:"scene/occ_mound.png", bx,by,bw,bh, z:1.30 }, ...],   // ≤3
  patches:  [{ id:"white_anemone", src:"scene/patch_white_anemone.png", bx,by,bw,bh, z:1.18,
               sway:{ amp:0.022 /* of patch h at tips */, period:4.5, baseBy:0.95 } }, ...], // ≤3, base inpainted
  props:    [{ id:"crab", src:"scene/props/crab.png", bx, byBottom, bw, z:1.03,
               anim:{ type:"crab"|"star"|"sway"|"rock"|"none", ... }, shadow:{ w:0.9, h:0.18, a:0.35 },
               layers:{ front:"scene/props/anemone_front.png" } /* optional split for nestling */ }],
  spots:    [{ id, type:"graze"|"pick"|"shelter"|"peek"|"home"|"perch", bx,by,z, r, behind:"mound"|null, species:[...] }],
  bubbles:  [{ id:"airstone", bx:0.70, by:0.80, z:1.45, rate:[12,25], sizes:[1.5,7] },
             { id:"burp", bx,by,z, every:[20,45], count:[3,8] }],
};
```

**Additions to `fish/manifest.js`.** The old fields stay as fallbacks.
- `habit`: one of `cruise | graze | pick | hover | shoal | home | lurk | hide`
- `traits {shy, territorial, darty}`, each 0..1
- `zone [yTop, yBottom]`, as fractions of the water column
- `zRange [zMin, zMax]`
- `cruiseBL [min, max]`, in body lengths per second
- `turnTime`, in seconds
- `school {size, spacingBL}`, optional
- `home: "<prop id>"`, optional

**Projection.** One centralised `bgMap(bx, by)` turns backdrop coordinates into screen coordinates (cover transform plus surface-band offset). Fish live in glass-plane coordinates (X, Y) plus z, and map to the screen as `x = cx + (X−cx)/z`, `y = hy + (Y−hy)/z`, scale `1/z`, where (cx, hy) is the vanishing point at `bgMap(0.5, horizonBy)`. Speeds are in world units, so perspective-correct speed and parallax come for free. No ad-hoc "pull toward the horizon".

**Depth grid constraint.** A fish's z must stay below `depthGrid(projected x, y) − 0.05`. The only exception is behind an occluder, where the fish is hidden anyway. This stops small, hazy far fish from being drawn *in front of* sharp mid-ground rocks, which would be the main depth contradiction. On this photo it means:
- most of the frame allows z∈[1.0, ~1.6];
- the far range (z up to 2.6) exists only in the dark top-centre gap and the area above the mound.

**Render order:**
1. Backdrop with patch bases inpainted
2. Background caustic pass
3. Surface band
4. Far particles
5. Depth-sorted list of fish, props, occluders, sway patches and bubble columns. Each occluder or prop is followed by its masked caustic contribution (see 4.3).
6. Near particles
7. Light streaks (`screen`)
8. Cached vignette

Sort one preallocated array in place. No per-frame `filter()`; replace `:1016-1017` with in-place compaction.

# 4. Techniques per feature (photographic, at moderate cost)

### 4.1 Water surface ("light flickers on the water at the top")
Use a **reflected-surface band**, not a glow over the coral tops:
- Draw the photo into `[bandH, H]` with `bandH ≈ 0.075H`. This also widens the visible photo on the MacBook to x∈[0.10, 0.90].
- Cache M is built from the top 14% of the backdrop: flipped vertically, softened by an 1/8 down-up pass, multiplied by 0.55, and tinted 30% toward `#0d2a4a`. This is the total-internal-reflection look aquarium photos show (compare `assets/alt/reef_bg_sea_aquarium.jpg`).
- Per frame:
  - Draw M as 12–16 horizontal strips with `dx = 3·sin(0.9t + 0.25y) + 1.5·sin(1.7t − 0.6y)` CSS px. Strip distortion belongs **only here**.
  - Add caustic layer A with pattern transform `scaleY 0.25`, so it reads as horizontal glints, drawn `lighter` at α≈0.3 and stronger near the waterline.
  - Draw the **meniscus**: a bright 1.5–2 px line at bandH (α 0.35–0.55, flickering) with a faint dark line just under it. This double line is the strongest single realism cue.
  - Bubbles pop there as a 0.15 s ring sprite.
- Stretch goal: fish within 0.18H of the band get a flipped, dimmed (α 0.25), unsliced reflection, clipped to the band.
- Fallback if review rejects the band: no band, and caustic glints on the top coral tips only.

### 4.2 Light rays
- These are LED pucks, not sun, so rays **fan out** from 2 point sources above the frame (from `scene.light`), 4–6 streaks each, angle spread ±8–9°, width 1.5–6% of W.
- One 64×512 streak texture, built with ImageData: Gaussian cross-section × `(1−e^{−s/0.05H})·e^{−s/0.6H}` × faint lengthwise noise.
- Per streak:
  - one `setTransform` + one `drawImage`, composite `screen` (it doesn't clip to white the way `lighter` does);
  - α = 0.06–0.14 × (0.75 + 0.25 × smooth noise at 0.3–0.8 Hz);
  - sway ±1.5° at 0.03–0.08 Hz.
- `lightAt(x, y)` is analytic: the sum over streaks of `I_k(t)·exp(−d⊥²/2σ²)·atten(y)`. It is shared by fish, particles and bubbles, so what's drawn and what lights things always agree.

### 4.3 Caustics (also "reflecting off the bottom")
**Texture generation** (JS at startup, ~10–20 ms, no images involved, so it is also CPU-sampleable):
- Use a **photon splat over a periodic height field**.
- The height field is `h = Σ₈ a_j sin(2π n_j·p/256 + φ_j)`, with integer `n_j` (|n|∈[2,7]) and `a_j ∝ |n|^-1.6`, which makes it tile exactly.
- Precompute ∇h on the 256² grid. Then splat 4 photons per texel at `p + D∇h` (maximum displacement 6–10 texels) with bilinear accumulation and wrapping.
- Normalise by the mean, then `c = clamp((I−0.6)/2.4)^1.3`, then a 1-texel box blur.
- Make two tiles with different seeds (A and B). Keep the Float32 arrays for CPU sampling.
- This gives real bright cusps and dark cells. Worley F2−F1 looks like uniform cartoon cells instead.

**Animation:** in buffer K, fill pattern A, then pattern B with `darken` (a per-pixel min). The two patterns scroll in different directions at speeds that don't share a ratio, so the result looks like flowing caustics without repeating. Inside the sand band, the pattern transform adds `scaleY 0.35–0.45` (floor seen at a grazing angle) and 2–3 sub-bands for perspective.

**Albedo-correct application.** This is the key to not looking like a projected overlay:
- C = K, then `multiply` the backdrop, then `destination-in` the light mask.
- Then draw C onto the main canvas with `lighter` at α = strength × shaft-footprint. The footprint is a tiny 128×1 canvas of soft blobs at the shaft feet, multiplied into C.
- Result: `bg·(1 + k·c·mask)`. White sand flares, dark rock barely changes, just like real light.
- K and C run at 0.5 RS.

**Occluder/caustic conflict (missing from the draft).** Occluders are drawn later from caustic-free pixels, so they would **erase** the caustics on the mound. The fix: after each occluder, draw the matching C sub-rect masked by the occluder's alpha (`destination-in`), with `lighter`. That's 3 draws per occluder. For props, use K sub-rect `multiply` prop `destination-in` prop alpha, so the dapples carry the prop's own colour.

**Bounce off the bottom:** a soft additive glow sprite just above the sand at each shaft foot (1 draw per source). Fish within 0.15H·s of the floor get a soft shadow ellipse on the floor polyline (1 draw, α ≤ 0.22).

### 4.4 Fish catching the light (replaces the draft's whole-sprite "lit variant")
- Per species, a **lit-mask variant**: the sprite `destination-in` a vertical gradient (alpha 1 at the back → 0.35 at the belly), then `source-atop` LED white at 15%. Compositing only, so no readback.
- Draw it as a **per-slice `lighter` pass**, only for slices where `α_i = clamp(lightAt(slice centre)·(0.6 + 0.4·causticSample), 0, 0.55) > 0.03`.
- Because `lighter` adds the sprite's own colours, the result is about `c·(1 + α)`: physically proportional brightening. A narrow shaft produces a **band of light sliding along the body** as the fish swims through it, with caustic dapples moving over it. This is the most convincing cue, and it costs only the lit slices (~3–8 per lit fish).
- Turn flash: during turns, slices whose local yaw puts them at a mirror-like angle to the light get +0.15 brightness. Real fish flash when they turn.

### 4.5 Fish body motion
- **Rendering:** one `setTransform` per slice (this allows signed, mirrored widths). Remember that negative `drawImage` widths do *not* flip the image per the spec.
- **Slices:** adaptive. When not turning: head 60% as 2 slices and tail 40% as 6–10 slices. When turning: uniform 12–18. In all cases `n ≤ clamp(L_device/36, 6, 18)`. Use ≤0.5 device px overlap to avoid "venetian blind" seams on translucent fins.
- **Tail:** for u<0.4, `θ = A·((0.4−u)/0.4)²·sin(ωt − 3u + φ)`, with A 0.35–0.6 rad scaled by speed and tail beat `f = 1.2 + 1.8·speed(BL/s)` Hz. Slice width × cos θ, laid out from the nose backwards, so the tail visibly shortens and lengthens. Vertical offset ≤1% of h.
- **Turn (not a card flip):**
  - Local yaw `θ(u) = π·clamp((p − (1−u)·0.35)/0.65, 0, 1)`: the **head leads** and the tail follows.
  - Slices lay out cumulatively (`x_next = x − w_i·cos θ_i`), so the body folds into a C/S shape and the slices past 90° draw mirrored.
  - The whole fish is never edge-on at once. Clamp |cos| ≥ 0.15 per slice.
  - T = 0.35 s for small fish up to 0.8 s for the grouper. Turns happen along a small arc (r = 0.3 BL), which naturally changes z by ~0.1.
- **Mips by on-screen size, not depth.** Bake mips at 1.0 (capped at 800 px: device length tops out at ~600 px under the RS cap), 0.5 and 0.25. Pick the smallest mip ≥ `L_dev·k`, with k = 1.0 near and 0.8 far, which gives natural softness at distance. Drop the decoded `Image` reference after baking (`rec.img = mip0`).
- **Fog by z, continuous.** A silhouette variant (mip 0.5, `source-in` water colour `#123d6b`) is drawn as a second slice pass with α = 0.85·(1 − e^{−0.42(z−1)}) (≈0.49 at z = 2.6). Skip it when α < 0.08. Mixing toward the water colour is physically right, and fog no longer depends on discrete LOD levels.
- **Remove** the per-fish shadow gradient (`:336-338`) and the instant facing flip (`:312`).

### 4.6 Depth paths ("into depth and toward you, keeping proportions")
- Uniform scale 1/z. Yaw `= atan2(ż·depthPx, Ẋ)` is limited to **|yaw| ≤ 30°** outside turns, so width × cos yaw ≥ 0.87 and proportions hold.
- With `depthPx = 0.31W` and cruise at 1 BL/s, |ż| ≤ ~0.12 z/s. Crossing the full depth takes ≥14 s, which keeps it calm.
- Depth targets come from behaviour, respecting `zRange` and the depth grid.
- Occasional "near-glass pass" (z 0.85–0.95, scale up to 1.18, slightly soft via one mip down): one big fish every 90 s or more.
- **No teleports:**
  - Fish that leave the screen enter OFFSTAGE for 4–20 s, then re-enter from either edge at a new (Y, z).
  - Territorial and home fish U-turn before the edge instead.
  - Replaces `:313-315`.

### 4.7 Behaviour and story (calm for a wallpaper)
**States:** CRUISE, GRAZE/PICK (nose pitched down 15–25°, 2–6 pecks with 0.1 BL thrusts), HOVER, HIDE (behind an occluder, between occluder z and the depth grid), PEEK (head clears the occluder edge for 3–6 s), HOME, SHOAL, DART (2.5 BL/s for 0.3–0.6 s, then a glide with τ = 0.8 s), CHASE/FLEE, FEED, OFFSTAGE.

**Speed caps:**

| State | Speed (BL/s) |
|---|---|
| Cruise | 0.4–1.2 |
| Graze | ≤0.3 |
| Hover | ≤0.15 |
| Chase | 1.8 |
| Flee | 2.2 |

Pitch ≤15°. Separation is O(n²), which is fine at ≤24 fish.

**Shoal (anthias × 6):** leader-follower with slot offsets plus slow noise, not full boids (which jitter). Followers turn 0.1–0.4 s after the leader, which gives the ripple a real school shows.

**Clownfish × 2** stay within the new anemone prop's ellipse (rx 0.6·w, ry 0.4·h) and nestle between the anemone's back and front layers. Each frame, set z ±0.03 around the anemone's z so they slot between its two layers.

**Suggested casting:**
- grazers: yellow tang, emperor angel
- pickers: copperband, butterflyfish
- hiders: regal angel, flame angel
- lurker: grouper
- territorial chasers: striped surgeon, powder blue tang
- cruisers: blue tang, moorish idol, the "pufferfish" (actually a clown triggerfish)

**Story director:** one "beat" every 20–45 s, at most one major beat at a time, each with a cooldown:

| Beat | Cooldown |
|---|---|
| Near-glass pass | 90 s |
| Shoal sweep across z | 40 s |
| Peek-out from the mound | — |
| Graze showcase | — |
| Chase lasting 2–4 s | 180 s |
| Crab shuffle | 60 s |
| Bubble burp from rock | 30 s |
| **Auto-feeder** (wallpaper mode) | every 6–10 min |

The auto-feeder drops 12–20 flakes from the surface band over 30–45 s. Fish converge from all depths, leftovers sink to the sand and fade at 40 s. Use three irregular flake sprites tumbling (alternating scaleY) instead of the brown circles (`:499-504`).

### 4.8 "Corals alive" without jelly
- **Animate only things that sway in reality:**
  - anemones (the photo's white anemone, the pink anemone where visible, the new prop);
  - Euphyllia (the photo's frogspawn/hammer at upper left, ≈bx 0.14–0.23, by 0.21–0.37, and a torch coral prop if licensed);
  - an optional sea fan, rocking rigidly ±1.2° about its base.
- **Static:** stony corals, plates, zoanthids and sponges.
- **Method:** horizontal row slices (8 device px each). Displacement `d(v, t) = A·v^1.5·[sin(ωt − kv + φ) + 0.4·sin(1.7ωt + φ₂)] + C(t − x·lag)·v²`.
  - Base pinned (v = 0).
  - Tip amplitude ≤2.5% of the patch height.
  - Frequencies 0.15–0.4 Hz.
  - C(t) is **one shared current**, with spatial lag across the tank, so everything leans together as a surge rather than jiggling on its own.
  - No scaleY "breathing" except the anemone: ≤2% contraction over a ≥20 s cycle.
- **Patches cut from the photo** need the backdrop **inpainted under them**. Otherwise the original tips show beside the moved ones as ghosts. Use Adobe `image_fill_area`, or a scipy diffusion fill, which is acceptable because the revealed slivers are thin and dark.
- **Drop the draft's whole-backdrop strip distortion.** Water inside a tank is a uniform medium, so rocks seen through the front glass don't wobble. It would read as heat haze or jelly, it adds ~270–540 drawImage calls, and it breaks occluder alignment. "Everything moves" comes from caustics on every lit surface, the shared current, particles, bubbles, rays and the surface band.

### 4.9 Bubbles ("I don't see bubbles going from bottom to top")
**Main column:** an airstone anchored in backdrop space (≈bx 0.70, by 0.80, z 1.45), rising from behind the mound so the mound occluder hides its base.
- Emission is Poisson-clustered at 12–25 /s.
- Sizes are log-normal, 1.5–7 CSS px × `sizeScale^0.5`.
- Rise speed reaches **0.25–0.45 H/s** within 0.2 s.
- Bubbles over 3 px zig-zag or spiral at 4–8 Hz with amplitude ≈1–2 r, and look slightly squashed (scaleY 0.85, wobbling).

**Rare "burps":** 3–8 bubbles from rock crevices. No uniform random spawning across the floor (`:1007`).

**Look:** pre-rendered sprites at 16/32/64 px with a bright Fresnel rim, transparent centre, top-left highlight and a faintly darker lower rim, drawn `source-over`. Alpha rises with `lightAt`, so bubbles sparkle inside the rays.

### 4.10 Props (starfish, crab, anemone, yellow ball sponge, yellow tube sponges)
- **Anchor in backdrop space inside `safeX` [0.14, 0.86]**, previewed at aspect ratios 1.54, 1.6, 1.78 and 2.33. Following the original's layout (yellow group on the left):
  - yellow tube sponges on the left rock base (≈bx 0.17, by 0.78);
  - yellow ball sponge on the left rock shelf (≈0.20–0.24, 0.62);
  - new anemone plus clownfish on the rock base left of the mound (≈0.30, 0.80);
  - starfish on the front-right sand (≈0.66–0.72, 0.93);
  - crab on the front-left sand (≈0.25–0.40, 0.95).
- **Make them match the photo:**
  - store each prop at about 1.5× its footprint in backdrop pixels, so its sharpness and grain match the photo;
  - white-balance from the measured sand neutral, at 70% strength;
  - match the local black and white points (5th/95th percentiles within 200 px), at 60% strength;
  - bake a top-down light gradient;
  - clean the edges (1 px alpha erode plus colour decontamination);
  - add a soft `multiply` contact shadow and darken the base where it meets the sand.
- **Crab:** sliding a rigid sticker looks toy-like.
  - Mostly idle, with claw picking if the claws can be cut as separate pieces, otherwise a 0.5 px body bob.
  - Short shuffles of 0.3–0.8 s, ≤0.5 body widths/s, while the bottom 35% of rows jitter ±1 px at 8 Hz (leg motion).
  - Occasionally retreats behind the mound edge.
- **Starfish:** static, or an almost invisible creep of 0.5–1 px/s.
- **Cut-outs:** prefer Adobe `image_remove_background` / `image_select_subject` for thin structures (crab legs, tube sponge, sea fan), with rembg isnet as the fallback. Confirm free-collection licence status per stock ID before downloading. Record ID, licence and date in `scene/README.txt`.

### 4.11 Particles
- Replace the 70 twinkling arcs (`:143-160`) with ~90 soft-dot sprites in 3 parallax layers (far: tiny and dim; near: larger and soft).
- They drift with the shared current, and brightness = base + `lightAt`. They glint only inside rays, with no random twinkle.

# 5. Revised stages, order and acceptance gates

All gates are measured in headless Chromium 1920×1200 with `?test=1&nofilter=1&seed=N`, averaged over 300 steps of 1/30 s. JS time = `performance.now()` around the frame body. Treat it as relative only, because software raster makes absolute task time meaningless.

### S0 – Foundation (engine; runs first and alone)
**Scope:**
- Test hooks:
  - `window.__aq` with `step(dt, n)`, `setTime`, `stats()` (counts of drawImage, setTransform, gradients created, save/restore, JS ms) and `fish()`;
  - `?debug=1` overlay;
  - `?nofilter=1` forces `HAS_FILTER = false`;
  - `?nobg=1` forces the procedural fallback.
- Render-scale cap; quality governor skeleton.
- `bgMap`; scene loader plus a **stub scene** with rough geometry, so the engine chain can work before the asset chain finishes.
- Remove `graded()`/`makeLod` filter use, the FG path and requests for count-0 images.
- Cache the vignette (1/4 res); no per-frame `filter()` allocations; preallocated render list.
- Harness in `/home/user/GregoryDich/tools/aquarium-test/` (outside the bundle): Playwright stills, step-mode clips via ffmpeg, stats JSON, file:// and http runs.

**Gate G0:**
- 0 console errors and 0 failed requests under **both** file:// and http.
- Backing store ≤ 8.4 MP at viewports 1512×982@2, 1728×1117@2, 1920×1080@2, 2560×1440@2, 3008×1692@2, 3840×2160@1.
- 0 gradients created per frame in photo mode.
- JS ≤ baseline + 0.3 ms.
- Fallback renders.

### Chain A – assets (sequential; runs alongside chain E; concurrency 2)
- **A0 – Finalise the backdrop.**
  - Check the blue blotches at 100%. If they are confirmed artefacts, find the original stock (search for the same reef image) and redo it as a global white-balance via channel gains, not a hue shift.
  - Fill the orange wall.
  - Raise brightness about +0.3 EV in the midtones with protected highlights and slight vibrance.
  - Inpaint under the sway patches.
  - Clean the fish sprites: clownfish remnant, edge fringes, scene white-balance, top-down gradient.
  - Gate: before/after at 100% crops; no channel clipping above 0.5% of the image.
- **A2 – Scene geometry** (needs the final backdrop):
  - ≤3 occluders as pixel-exact RGBA crops with soft 1–2 px edges from hand polygons;
  - sway patches;
  - light mask (alpha PNG at 1/4 res);
  - depth grid, floor polyline, spots, bubble sources;
  - debug overlays at 4 aspect ratios.
  - Gate: with the occluder layer on vs off (no fish), max per-pixel difference ≤ 2/255 at 4 aspects × RS 1/2.
- **A1 – Props.** Cut-outs can start during A0. Grading waits for A0. Gate: no halo on 100% crops on sand and on dark rock; all 5 requested props inside `safeX` at all 4 aspects; total size ≤ 4 MB on disk and ≤ 40 MB decoded.

### Chain E – engine
- **E1 – Light and water:** caustic generator, K/C pipeline, light streaks, `lightAt`, surface band, particles, bubbles.
  - Gate G1: JS ≤ G0 + 1.5 ms; ≤ 60 new drawImage calls per frame (excluding bubbles and particles); no `filter`; caustics visible only inside the mask (mean change outside < 1/255; filament contrast in the sand band ≥ 30 levels); rays raise mean brightness of the top half by ≤ 8%; frames identical with and without `nofilter`.
- **E3 – Fish:** projection, depth grid, turns, tail, mips/fog/lit, behaviours and director (using stub spots).
  - Gate G3 is checked automatically over a **10-minute deterministic simulation**:
    - no visible jump > 3% W in one step;
    - no frame where the whole fish is narrower than 15% of its length;
    - turns last 0.35–0.9 s;
    - |yaw| ≤ 32° outside turns;
    - cruise 0.3–1.5 BL/s for 95% of the time;
    - scale range observed covers at least 0.45–1.0;
    - ≥ 70% of fish visible on average, and each fish hidden < 25% of the time;
    - a beat at least every 60 s;
    - fish drawImage ≤ 420;
    - JS ≤ G1 + 2 ms.

### E4 – Integration (after A2 and E3)
Wire up props, occluders (with masked caustics), patches, spots, home/hide/peek, the crab and the director.

**Gate G4:**
- JS ≤ baseline + 3 ms.
- drawImage ≤ 850 typical, ≤ 1100 worst case (feeding).
- setTransform ≤ 700.
- Estimated memory per view (offscreens + mips + props) ≤ 120 MB at a 3840×2160 backing store, ≤ 250 MB including the main canvas buffers.
- Startup to first complete frame ≤ 1.5 s headless.
- Debug screenshots show a fish behind the mound, clownfish nestled in the anemone, and the bubble column's base occluded.

### Review loop
- Every finding must include a reproducible capture command (seed, step, viewport).
- 1 verifier for minor findings, 2 for critical or subjective-visual ones. Maximum 2 rounds.
- Also try `npx playwright install webkit` for a WebKit pass (same `filter` flag and file:// rules). If the download is blocked, rely on `nofilter` + file://.
- Send the user **MP4** (H.264) clips rendered in step mode. If a GIF is required, use 960 px wide with ffmpeg `palettegen`/`paletteuse` dithering: a 256-colour GIF bands a photo badly.

# 6. Draw-call budget per frame (typical, 22 fish)

| Item | drawImage |
|---|---|
| Backdrop | 1 |
| K/C caustic buffers | 4 |
| Caustic onto main | 1 |
| Occluder caustics | 3×3 = 9 |
| Surface band | 14 strips + 3 |
| Light streaks | 9 |
| Particles | 90 |
| Bubbles | ≤ 80 |
| Fish (adaptive slices + fog + lit) | ≤ 420 |
| Props | ~8 |
| Sway rows | ≤ 150 |
| Occluders | 3 |
| Floor shadows | ≤ 10 |
| Vignette | 1 |
| **Total** | **≈ 800** |

Full-screen-equivalent composited fill is about 3.5×. At 8.3 MP and 60 fps that is well within an M4 GPU; the real risks are JS/GC and per-call overhead, which the governor covers.

# 7. Risks and mitigations
1. **Filter / file:// divergence** (F1, F2): bake everything offline, never read pixels back, and gate every stage on file:// + `nofilter`.
2. **Occluders erasing caustics:** masked caustic pass per occluder.
3. **Card-flip turns:** head-led bend turn, minimum width, short duration, automated width check.
4. **Aspect crop:** backdrop-space anchoring, `safeX`, previews at 4 aspects.
5. **Pasted-in look of props and fish:** offline grade, matched resolution, contact shadows, edge cleanup, 100% crop review.
6. **Frantic behaviour:** caps in BL/s, director cooldowns, numeric checks.
7. **No access to the target hardware:** quality governor plus conservative budgets.
8. **Memory × monitors:** RS cap, mip cap at 800, drop decoded images.
9. **Inpaint artefacts:** keep regions minimal; they stay mostly covered by their patch.
10. **Stock licence availability:** check per ID; keep 2–3 alternates per prop.
11. **Fallback regressions:** the vector path keeps working off `facing = sign(cos yaw)` and z normalised into the old `depth` range; gated by `?nobg=1`.

# 8. Drop or simplify
- Drop whole-backdrop strip distortion.
- Drop the top shimmer band painted over the photo; use the reflected-surface band instead.
- Drop scaleX 1→0→−1 turns.
- Drop the per-fish floating shadow.
- Drop "≥4 LOD steps by z"; use 3 mips by on-screen size plus a continuous fog overlay.
- Drop full boids; use leader-follower.
- Drop scaleY breathing on props, except slow anemone contraction.
- Drop the separate `props/manifest.js` and `occluders.js`; use one `scene.js`.
- Drop screen-fraction placement and single-screenshot (1920×1200) placement.
- Drop click-feeding as a story source in wallpaper mode; use the auto-feeder.
- Drop 4K headless "task ms" as a pass/fail gate.
- The sea fan is optional.

# 9. Completeness map for the final check

| User demand | Delivered by |
|---|---|
| Light shimmers on the water at the top | Surface band (4.1) |
| Light penetrates down | Rays (4.2) |
| Light reflects off the bottom | Albedo caustics plus floor glow and shadows (4.3) |
| Fish under a beam reflect it beautifully | Sliding per-slice light band, dapples, turn flash (4.4) |
| Corals look alive | Shared current, sway patches and props (4.8) |
| Realistic behaviour; fish hide or swim | Behaviour states, occluders, peek (4.7) |
| I don't see bubbles going from bottom to top | Visible fast column plus burps (4.9) |
| Swim into depth and toward the viewer, keeping proportions | Perspective with yaw cap (4.6) |
| An interesting fish story | Director plus auto-feeder (4.7) |
| Starfish, crab, anemone, ball sponge, tube sponges | Props (4.10) |
| Brighter and livelier, nothing cartoonish | Regrade (A0), grading rules, no toy cues |
| No settings panel | None added |

Sources: [caniuse – CanvasRenderingContext2D.filter](https://caniuse.com/mdn-api_canvasrenderingcontext2d_filter), [WebKit Bug 198416](https://bugs.webkit.org/show_bug.cgi?id=198416), [WebKit Bug 275436](https://bugs.webkit.org/show_bug.cgi?id=275436), [MDN – filter](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/filter)

### Critical Files for Implementation
- /home/user/GregoryDich/aquarium/index.html
- /home/user/GregoryDich/aquarium/fish/manifest.js
- /home/user/GregoryDich/aquarium/scene/scene.js (new; replaces the draft's props/manifest.js and occluders.js)
- /home/user/GregoryDich/aquarium/assets/reef_bg.jpg (A0 regrade, orange-wall fill, inpaint; occluders must be cut after this)
- /home/user/GregoryDich/macos-app/Sources/WallpaperWindow.swift (file:// loading and per-screen WebView; confirms the taint, filter and memory-per-screen constraints)