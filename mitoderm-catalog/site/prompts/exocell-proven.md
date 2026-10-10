# EXOCELL MASK — промпты, которые дали утверждаемые кадры (10/10/2026)

Модель: **GPT Image 2 (edit)** через Cloudinary, 16:9, 1K (1088×608), 4 единицы квоты за кадр.
Референс [1]: основное фото коробки `protocols/assets/img/exocell-mask.webp`.
Текст упаковки — из `site/packaging-text.json`. Кадры: `site/proto/scenes/`.

Уроки этого прогона:
- без точного списка надписей в промпте генератор рисует пустую или кривую коробку;
- Gemini (Nano Banana 2) хуже держит мелкий текст и стоит дороже (9–14 единиц за кадр);
- если на маске нужна форма как на фото коробки — просить «exactly the mask in [1]… soft 3D face shape», иначе выходит плоская мокрая плёнка;
- маска не должна закрывать фасад: «with a clear gap… it does not cover the carton»;
- финальные кадры не делаем в 2K (решение заказчика).

## Кадр 0 — герой (`scenes/01-meet.jpg`)

```
REFERENCE IMAGES: reference [1] is the EXOCELL MASK product photo; the carton AND the face mask in the frame are exactly those in [1]. PACKAGING TEXT — reproduce exactly as listed, every word spelled exactly as written here, crisp and legible, nothing added or translated: CARTON — matte muted-teal portrait carton (#5ca0a5), dark navy print: top centre: VM monogram, below it small 'VM corporation'; centre: 'EXOCELL' in wide-spaced capitals ('EXO' bold, 'CELL' thin), below it letter-spaced 'M A S K'; below the middle, light italic pale aqua, two lines: 'Your Second Skin' / 'For Exo Bio-Regeneration'; small block, first line bold: 'Professional facial moisturizing mask' / 'Maschera viso idratante ad uso professionale' / 'Mascarilla hidratante facial profesional' / 'Masque hydratant visage professionnel'; bottom two lines: '5 face masks – maschere viso - máscaras facial - masques facial' / 'Net 5 x 25 ml ℮ 5 x 0.84 fl.oz'; left side panel: 'EXOCELL' and 'MASK' running vertically, grey. FACE MASK — exactly the mask in [1]: a smooth, glossy, pale aqua-white translucent bio-cellulose mask holding a soft 3D face shape (forehead, nose bridge, cheeks, chin), eye, nose and mouth cut-outs, a small slit at the right jaw. Photoreal cinematic product hero, 16:9. SET: a polished black glass counter in a near-black studio (#0b0f10), no haze. The carton stands upright in the right third, about 45% of the frame height, turned about 20 degrees so its left side panel shows, its whole front fully visible. The face mask stands upright on the glass just to the left of the carton, turned slightly toward the camera, with a clear gap between them — it does not cover the carton. LIGHT: one soft teal (#6fb7ba) key from the upper left, faint neutral fill from the front, a thin teal rim along the mask edge, carton and mask softly reflected in the black glass. CAMERA: 85 mm, eye level, f/8, carton and mask sharp; the left half of the frame empty near-black for text. No people, no hands. No captions or overlay text, no text other than the packaging's own print, no extra objects.
```

## Кадр «Inside» — мокрый лист на стекле (`scenes/02-inside.jpg`)

Тот же блок PACKAGING TEXT; лист: «one unfolded bio-cellulose face mask: a thin, wet, translucent milky-white film with a faint aqua tint… fine water droplets… lying almost flat on the glass… to the left of the carton with a clear gap, not touching it and not covering it».

## Кадр 3 — применение в кабинете (`scenes/03-mirror.jpg`)

Тот же блок PACKAGING TEXT + «Photoreal cinematic treatment scene, 16:9, dark clinic room, the same soft teal light as the hero. A woman in her thirties reclines on a treatment bed, eyes closed, calm, hair under a black disposable cap; a bio-cellulose sheet mask lies smoothly on her face — on skin it turns almost clear and milky…; a practitioner's hands in black nitrile gloves peel a pale-blue protective backing film away from the mask at the forehead. In the right third, on a black glass side table at shoulder height, the EXOCELL MASK carton, about 35% of the frame height… its print readable. CAMERA: 50 mm, slightly above, f/4… Realistic skin texture, no redness… no purple, no extra people.»

## Кадр 5 — набор (`scenes/04-protocol.jpg`)

Тот же блок PACKAGING TEXT + «SINGLE-MASK SACHET — flat pale-aqua foil sachet, slightly glossy, with the VM monogram at the top centre and 'EXOCELL' with letter-spaced 'MASK' below it in dark navy, two tiny grey lines near the bottom (not words)… five sealed sachets fan out across the glass, the front one slightly lifted, all fronts readable…»
