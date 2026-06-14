# 🎨 Промпты для генерации рыб (Midjourney / Firefly / DALL·E / img2img)

Цель — для каждой рыбы получить **прозрачный PNG, вид строго сбоку, рыба
повёрнута ВПРАВО (→)**, без фона, без подписей и водяных знаков, высокое
разрешение (≥ 2048 px по длинной стороне).

> Эти PNG используются как **2.5D-карточки**: движок гнёт их волной (тело +
> хвост), наклоняет и масштабирует. Поэтому идеальны: ровный вид сбоку, плоское
> освещение, рыба целиком (хвост/плавники не обрезаны), нос вправо. Файл
> называйте по `id` из `manifest.js` (`fish/clownfish.png`, `fish/blue_tang.png`,
> …) — он заменит рыбку-заглушку того же вида.
>
> ⚠️ Я не могу сгенерировать их в этой среде (генерация изображений здесь
> отключена), поэтому фотореалистичных рыб генерируете вы — так же, как сделали
> риф. Ниже готовые промпты.

## Общие правила (добавляйте к каждому промпту)
```
single fish, exact side profile view, facing right, full body in frame,
centered, swimming pose, fins spread, photorealistic, studio aquarium lighting,
ultra detailed scales, sharp focus, transparent background, isolated, no shadow,
no text, no watermark --ar 3:2
```
> Если генератор не умеет прозрачный фон — ставьте **плоский белый или
> чистый зелёный (chroma) фон**, затем удалите фон (Photoshop «Удалить фон»,
> remove.bg, или попросите меня — у меня есть инструмент `image_remove_background`).
> Сохраняйте как PNG с прозрачностью, имя файла = `id` из `manifest.js`.

---

## Список (id → промпт)

**clownfish.png** — `orange clownfish (Amphiprion ocellaris), three white vertical bands with thin black edges, side profile facing right`

**blue_tang.png** — `blue tang (Paracanthurus hepatus, "Dory"), royal blue body, black palette marking, bright yellow tail, side profile facing right`

**yellow_tang.png** — `yellow tang (Zebrasoma flavescens), vivid uniform yellow, disc-shaped body, pointed snout, side profile facing right`

**powder_blue_tang.png** — `powder blue tang (Acanthurus leucosternon), light blue body, black face mask, yellow dorsal fin, white chest, side profile facing right`

**pufferfish.png** — `spotted pufferfish (Arothron), rounded cream-white body covered in small dark brown spots, side profile facing right`

**royal_gramma.png** — `royal gramma (Gramma loreto), front half magenta-purple, rear half bright yellow, sharp split, side profile facing right`

**emperor_angelfish.png** — `emperor angelfish (Pomacanthus imperator), horizontal blue and yellow stripes, black eye mask with blue rim, side profile facing right`

**regal_angelfish.png** — `regal angelfish (Pygoplites diacanthus), vertical orange and white stripes with blue outlines, blue chest, side profile facing right`

**mandarinfish.png** — `mandarinfish (Synchiropus splendidus), psychedelic green orange and blue wavy maze pattern, side profile facing right`

**blue_chromis.png** — `blue-green chromis (Chromis viridis), small shimmering teal-blue reef fish, side profile facing right`

**flame_angel.png** — `flame angelfish (Centropyge loricula), bright red-orange body with dark vertical bars, blue-black fin edges, side profile facing right`

**moorish_idol.png** — `moorish idol (Zanclus cornutus), bold black white and yellow bands, long trailing dorsal filament, side profile facing right`

---

## После генерации
1. Удалите фон → прозрачный PNG.
2. Обрежьте по рыбе (без лишних полей), хвост/плавники не срезать.
3. Имя файла строго как `id` (например `blue_tang.png`), положите в эту папку `fish/`.
4. Откройте `index.html` — рыбка появится автоматически. Размер/скорость/количество
   правятся в `manifest.js`.
