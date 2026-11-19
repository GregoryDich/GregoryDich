# EXO-NAD: опорные материалы — отчёт агента 19/11

Файлы лежали во временной папке сессии (`<scratch>/nad/refs/`); изображения с людьми в git не кладём. Пересоздать: `tools/render-nad.cjs` (3D-рендеры), ffmpeg по фильму V-TECH (кадры кабинета и косметолога), живой сайт (`/assets/product-cinema/exo-nad/kit-photo.png`, `123.mp4`).

All four parts (A to D) are finished, but the main finding from part A is that the vials in the 3D model don't match the real kit. The live site has a real photograph of the open kit, and it disagrees with the model on the vial caps, the vial print, the liquid level and how the box opens. Everything is in `<scratch>/nad/refs/`, and `refs.json` lists all 58 files with kind, description and use. I looked at every image with Read. Nothing in the repository was changed and no generation tools were called.

**A. 3D renders** (`refs/3d/`, all 3840x2400 transparent PNG)
- **Six standard keys:** v1-meet to v6-kit.
- **Extra views:**
  - `x-box-34.png`: closed box turned about 32° and tilted about 14°, showing the front, right side and top.
  - `x-tray-open.png`: the full tray with the sleeve removed, showing all 11 bottles and the gold print.
  - `x-kit-crop.png`: the tray in the standard kit pose, closer.
  - `x-label-peel.png`, `x-label-ph.png`, `x-label-ls.png`: close views where each label is readable.
  - `x-row-3.png`: the three products large, side by side.
- **How the extra views were made:** the close views use only the scene's own view settings (a crop). The three-quarter box and the open tray needed a small hook in my renderer that turns the box or hides the sleeve just before drawing; the module itself is untouched. The renderer is `<scratch>/nad/tools/render-nad.cjs`.
- **Depth:** the box's depth in the model is an assumption, so the side visible in the three-quarter view is the model's guess.

**A. Comparison**
- **Real photo (`refs/real-NAD.png`):** it is a composite packshot, not a photograph.
  - **Box:** gold foil going from lemon at the centre-left to bronze at the right. The print is VM corporation / EXO-NAD / SKIN LONGEVITY PEELING, with the thin lid line near the bottom.
  - **Vials:** they look opaque, orange-amber and teal, filled up to the shoulder. They have **silver aluminium crimp caps** and large black VM plus PH NORMALIZER / LONGEVITY SERUM print.
  - **Peel bottle:** square clear glass, gold cap, gold flakes, with "EXO-NAD / SKIN LONGEVITY PEELING" printed straight on the glass.
- **Box against the model:** colour and front print match. The model also carries the small multilingual and contents block listed in `packaging-text.json`, which is not visible in the packshot. The packshot's gradient is stronger than the model's.
- **The 3D model:**
  - **Vials:** clear glass, amber-brown and blue liquid at about 70%, **white flip-off caps**, small quiet labels.
  - **Peel bottle:** a cream paper label reading EXO-NAD PEELING with four language lines.
  - **Box:** the sleeve lifts straight up.
- **The real kit photo (`refs/live/kit-photo.png`):**
  - **Vials:** clear glass, pale golden-amber and pale blue liquid at about 85–90%. The print is a repeating VM monogram wrapped around the glass, with no product-name label. The caps are **silver-grey aluminium crimp seals with flip-off tops**, and the real video shows a cap being flipped off.
  - **Peel bottle:** clear glass, gold cap, black EXO-NAD PEELING printed directly on the glass.
  - **Box:** a **hinged lid** standing open behind the tray, with VM / EXO-NAD printed on its inner face. The front band also carries a small EXO-NAD print.
- **Verdict:** the older prompt file is right about silver crimp caps; the model's white plastic caps are wrong. The prompt file is wrong about tinted glass: the real glass is clear and the colour comes from the liquid. The packshot's opaque saturated colours come from compositing. The tray layout and gold print in the model match the real photo.

**B. V-TECH film** (`refs/vtech/f000.png` to `f872.png`, contact sheet `refs/vtech-contact.jpg`)
- **Cosmetologist's identity:** `refs/vtech/f121.png` (also f080 and f751). Her face is sharp, three-quarter view; dark long wavy hair, white tunic with pink trim, amethyst pendant.
- **Room in a wide view:** the film has no truly wide shot. The widest is the first frame of the leftover clip, `refs/leftover/vtech-bridge-f0.png` (window, plant, marble table, white chair). The next best are `refs/vtech/f080.png` and f121.
- **Marble table with the pack:** `refs/vtech/f040.png` (the box is sharp on the table), then f000 and f872, where the box is in the foreground and the women are blurred.
- **Gloved hands:** `refs/vtech/f229.png` (pen at the cheek), `refs/vtech/f430.png` (dropper and amber vial), `refs/vtech/f600.png` (spatula, with the gold pouch in view). The gloves are white latex; the real EXO-NAD video uses black nitrile gloves.

**C. Live-site media** (`refs/live/`, all three downloaded)
- `kit-photo.png`, 960x1637: the real open-kit photo described above.
- `IMG_9803.JPG`, 3808x5712, Sony A7III: a woman lying back with eyes closed and glowing wet skin, no product visible. It is a photo of a person, so it stays out of the repo.
- `123.mp4`, 476x844 vertical, 21 s, 25 fps, with sound: real handling of the kit. The three frames I extracted (`123-t02/t10/t18.png`) show the open kit with the lid upright, a blue vial's flip-off cap being removed, and a gold sparkle MITODERM end card.

**D. Leftover material** (`refs/leftover/`, with three frames from each video)
- **The three clips** (vtech-bridge 1920x1080 6.0 s, vtech-camera 1912x1080 9.3 s, vtech-intro 1912x1080 5.0 s, all 24 fps): same clinic and cast, the box-to-two-shot camera moves and the pen close-up.
- **`vtech-consultation.webp`**, 1912x1080: the same two-shot as frame ~121.
- **`vtech-kit.webp`**, 2048x1360: a generated still on black showing a tall V-TECH box, five gold gel-mask pouches and five amber V-TECH SERUM vials with champagne-silver caps.
- **Does `vtech-kit.webp` match `open-039.webp`?** No. In vtech-kit the box has black top and bottom bands, a black V, and five pouches laid out. The Blender render `open-039.webp` (1277x1266) has a gold sleeve with a white V, a black tray with one pouch and five vial caps seen from above, and a black card. Only the product names (V-TECH SERUM / GEL MASK) agree.
- **`open-000.webp`:** shows the standing box with one pouch and one vial, not a closed pack.
- None of the leftover material is EXO-NAD; it is only useful for the clinic, the cast and the lighting style.

**Problems**
- In the media-urls file the live paths were relative; the real location turned out to be `/assets/product-cinema/exo-nad/...` on the live site.
- The task calls `NAD.png` the only verified real photo, but it is a composite, and `kit-photo.png` contradicts it on the vials and the peel bottle.
