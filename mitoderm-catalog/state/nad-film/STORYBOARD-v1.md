# EXO-NAD: раскадровка фильма v1 + концовка V-TECH (рабочая записка для архитектора)

19/11/2026. Машиночитаемая копия — `storyboard.json` в этой же папке. Ничего не сгенерировано, ни одного
кредита не потрачено. Перед каждой платной генерацией — цена и баланс заказчику, запуск только после «утверждаю»;
сначала один образец (K1, потом черновик клипа A), серия — после «ок».

`<scratch>` ниже = `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad`.
Эта папка временная: если её стёрли, кадры пересоздаются по `REFS-SUMMARY.md` (ffmpeg по фильму V-TECH,
`tools/render-nad.cjs` для 3D, `123.mp4` с живого сайта). Файлы из репозитория указаны полным путём.

## 0. Что изменилось по сравнению с исходным планом (коротко)

1. **Стыки по сценарию.** PAGE.md сам просит монтажные склейки: 02→03 «склейка на движении руки к лотку»,
   03→04 «явная склейка по времени», 04→05 «склейка на новые инструменты», 05→06 «склейка чуть шире».
   Смену перчаток нельзя прятать в непрерывном движении. Поэтому клипы C, D, E не «перетекают» из
   кадра в кадр, а **играют действие своего шага** от своего ключевого кадра, а между шагами стоит склейка.
   Такому клипу второй (конечный) кадр не нужен, и он делается дешёвой моделью Kling 4.0 (16.25 кр.).
2. **Конечный кадр (Seedance) нужен только там, где без него нельзя:** клип A (из кадра с набором в разговор:
   лица обеих женщин должны прийти точно в K1, и этот же клип задом наперёд закрывает фильм в сцене 08)
   и клип раскрытия набора V-TECH (раскрытая упаковка обязана совпасть с референсом, её нельзя «придумать»).
3. **Шестой клип F вместо перехода E K4→K5.** Сцена 06 (разговор в конце) — отдельный клип Kling от K5,
   который проигрывается **задом наперёд**: так он гарантированно кончается точно на K5, а K5 почти
   совпадает с K1, откуда начинается перевёрнутый клип A. Если обратное движение будет заметно —
   запасной вариант: Seedance от последнего кадра E до K5 (+95…110 кр.).
4. **Порядок стиллов:** первым делается K1 — в нём впервые появляется новая пациентка; после «ок»
   заказчика K1 становится референсом лица пациентки для всех остальных кадров.

Итог по деньгам (подробно в разделе 6): рекомендованный план — **456.5 кр.** с запасом попыток
(минимум, если всё выйдет с первого раза, — 290.5 кр.). Исходный план «всё на Seedance» — 717.75 кр.
Потолок 1000 кр.

## 1. Общие правила для всех кадров

- **Мастер один: 16:9, 1912×1080, 24 кадра/с.** Телефонная версия — вырез из центра (см. раздел 5).
  Всё действие, оба лица, руки и продукт — в средней вертикальной трети кадра (полоса ≈607 px шириной).
  Левая и правая трети спокойные: на десктопе там стоит текст страницы.
- **Кабинет и косметолог — из фильма V-TECH:** светлый кабинет, большое окно слева, зелень за окном,
  высокое растение, тёплые белые стены, белое кожаное кресло, бежевый мраморный стол. Косметолог: длинные
  тёмные волнистые волосы, белая туника с розовым кантом, кулон-аметист на чёрном шнурке
  (`<scratch>/nad/refs/vtech/f121.png` — лицо, `f080.png` — комната).
- **Новая пациентка (предложение, нужен «ок» заказчика на K1):** взрослая женщина около сорока, медово-
  русые волосы убраны назад под белую махровую повязку, простой трикотажный топ цвета слоновой кости,
  натуральная кожа с порами и мелкими морщинками, чуть неровный тон, без макияжа. Явно не та женщина, что
  в V-TECH (у той каре и бежевая повязка). Возраст — только выбор кастинга, не показание.
- **Перчатки в процедуре — чёрные нитриловые**, как в настоящем видео с набором (`123-t10.png`).
  В фильме V-TECH были белые латексные — это открытый вопрос (раздел 7).
- **Продукт — только по настоящей фотографии.** Главный референс в каждом кадре с продуктом:
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/product-cinema/exo-nad/kit-photo.png`
  и кадры настоящего видео `<scratch>/nad/refs/live/123-t02.png`, `123-t10.png`. Что видно по фото:
  золотая коробка с откинутой на петлях крышкой (на внутренней стороне VM / EXO-NAD / SKIN LONGEVITY
  PEELING), чёрный лоток с золотой печатью, слева квадратный прозрачный флакон с золотой крышкой и чёрной
  надписью EXO-NAD PEELING прямо по стеклу (бледно-золотая жидкость с золотыми хлопьями), верхний ряд —
  5 прозрачных флаконов с бледной янтарно-золотой жидкостью, нижний — 5 с бледно-голубой, серебристые
  алюминиевые обжимные колпачки с отщёлкивающейся крышечкой, монограмма VM по стеклу, жидкость до плеч.
  3D-рендеры — только для закрытой коробки и раскладки лотка (`x-tray-open.png`, `x-box-34.png`):
  белые колпачки, тонированная жидкость и бумажная этикетка в рендерах неверны.
- **Никакого текста в кадре**, кроме печати на самой упаковке. Все надписи — HTML поверх видео.
- **Ограничения PAGE.md:** без доз и времени экспозиции, без инъекций и игл, без MITOPEN и любых
  приборов, без масок, без мгновенного изменения кожи, без «после», без сглаживания и сияния кожи.
  Сыворотку не смывают. Шаг 05 не начинается до смыва и сушки.

**Общий хвост для стиллов (дописывать к каждому промпту):**
`16:9 film still, photorealistic, warm natural daylight, real skin texture with pores and fine lines, true colours, fine grain. Keep all action and faces inside the central vertical third of the frame; the outer left and right thirds stay calm and uncluttered. No added text, captions or logos beyond the packaging's own print, no invented packaging, no needles, syringes or devices, no face masks, no skin smoothing or glow, no before/after look, no extra fingers, no duplicate people.`

**Общий хвост для Kling (дописывать к каждому промпту):**
`Photorealistic, one continuous take, no cuts. Faces, hair, clothes, gloves and room stay exactly as in the start image. Product shapes, caps and printed words stay exactly as in the start image while visible. Skin texture and tone unchanged throughout. No text, no new objects, no needles or devices, no skin smoothing, no extra fingers, no morphing. No audio.`

Модель для стиллов — та же, что делала ключевые кадры V-TECH (`gpt_image_2_6` с референсами),
≈2–2.75 кр. за кадр.

## 2. Таблица сцен (24 кадра/с, всего 876 кадров = 36.5 с, как на странице)

| Сцена | Кадры | Чем закрыта (кадры исходника) | Стык на входе |
|---|---|---|---|
| 01 Набор | 0–108 | 0–24: стоп-кадр K0 (= кадр 0 клипа A); 24–108: клип A, кадры 1–84 (медленный наезд на набор) | — |
| 02 Консультация | 108–204 | 108–144: клип A, кадры 85–120 (отъезд и перевод фокуса на двоих); 144–204: клип B, кадры 0–59 | A→B без стыка: B стартует с последнего кадра A |
| 03 Шаг 1, EXO BIPHASIC PEEL | 204–312 | клип C, кадры 0–107 | склейка на движении руки к набору |
| 04 pH NORMALIZER, смыв, сушка | 312–420 | клип D, кадры 0–107 | склейка по времени (подпись HTML «קיצור זמן») |
| 05 LONGEVITY SERUM | 420–552 | клип E, 120 кадров, замедление ×1.1 → 132 | склейка на новые перчатки и флакон |
| 06 Завершение встречи | 552–648 | клип F (задом наперёд), кадры 0–95 | склейка чуть шире |
| 07 Место для доказательств | 648–744 | 648–672: клип F, кадры 96–119 (доходит ровно до K5); 672–738: стоп-кадр K5; 738–744: 6 кадров оптического стыка K5→K1 | — |
| 08 Полная система | 744–876 | 744–864: клип A задом наперёд, кадры 120→1; 864–876: стоп-кадр K0 (кадр 0 клипа A) | стык 6 кадров (в сцене 07) |

Последний кадр фильма = первый кадр (K0), как в V-TECH. Стоп-кадры и стык делает скрипт сборки, кредитов
не стоят. В сцене 07 поверх стоп-кадра — пустые окна «до/после» в HTML, никаких новых кадров.

## 3. Ключевые кадры (стиллы)

Порядок генерации: **K1 → (ок заказчика на пациентку) → K0 → K2 → K3 → K4 → K5 → VK.**

### K1 — консультация (первый, образец для заказчика)
- **Зачем:** конец клипа A и начало клипа B; первое появление новой пациентки; основа для K5.
- **Композиция:** средний план на двоих у мраморного стола, как кадр 121 фильма V-TECH, но женщины
  ближе друг к другу: оба лица в средней трети кадра. Косметолог левее центра смотрит на пациентку,
  пациентка правее центра в белом кресле, слушает, руки спокойно лежат на столе. На столе между ними
  внизу по центру — открытый набор EXO-NAD анфас, печать читается. Слева мягкий свет окна, справа
  спокойная стена и спинка кресла.
- **Референсы:** `<scratch>/nad/refs/vtech/f121.png`, `<scratch>/nad/refs/vtech/f080.png`,
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/product-cinema/exo-nad/kit-photo.png`,
  `<scratch>/nad/refs/live/123-t02.png`, `<scratch>/nad/refs/3d/x-tray-open.png`.
- **Промпт:**
  `Same clinic, camera height and daylight as the attached V-TECH frame: medium two-shot at the beige marble table, 50mm, eye level. Left of centre, the same cosmetologist as in the reference (long dark wavy hair, white tunic with pink piping, amethyst pendant), looking warmly at the patient. Right of centre, a NEW patient seated in the white treatment chair: a woman in her early forties, honey-brown hair pulled back under a white towelling headband, simple ivory knit top, natural skin with pores and fine lines, no make-up; she listens calmly, hands resting on the table. She is a different person from the woman in the reference frame. On the table between them, lower centre, stands the open EXO-NAD kit exactly as in the attached real photo: gold box with the hinged lid standing open behind, black tray with gold print, square clear EXO-NAD PEELING bottle with gold cap on the left, five pale golden-amber vials on top, five pale blue vials below, silver crimp caps; print sharp. Both faces sit close together inside the central third of the frame.` + общий хвост.

### K0 — набор на столе (первый кадр фильма и его последний кадр)
- **Зачем:** сцена 01 и финальный кадр сцены 08; начало клипа A.
- **Композиция:** камера низко, у края стола: открытый набор стоит по центру резко, занимает около трёх
  четвертей высоты кадра, крышка поднята, видны все три вида флаконов и передний борт коробки. За ним в
  мягком размытии косметолог (слева) и пациентка (справа), как в кадре 40 фильма V-TECH. Набор целиком
  в средней трети.
- **Референсы:** `<scratch>/nad/refs/vtech/f040.png`, K1 (утверждённый),
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/product-cinema/exo-nad/kit-photo.png`,
  `<scratch>/nad/refs/live/123-t02.png`, `<scratch>/nad/refs/3d/x-tray-open.png`.
- **Промпт:**
  `Same scene, light and camera axis as the attached K1, but the camera is low and close to the marble table, as in the attached V-TECH frame 40: the open EXO-NAD kit stands sharp in the centre foreground, about three quarters of the frame height, lid upright, the whole tray and the front band with small EXO-NAD print visible, exactly as in the attached real photo (clear glass, pale golden-amber and pale blue liquids, silver crimp caps, EXO-NAD PEELING printed on the square bottle). Behind it the same cosmetologist (left) and the same patient (right) are softly out of focus at the table. 50mm, f/2, lens at tray height. The kit stays entirely inside the central third.` + общий хвост.

### K2 — шаг 1, пилинг
- **Зачем:** старт клипа C (встряхивание и нанесение).
- **Композиция:** средне-крупный план. Пациентка откинулась в белом кресле (чуть наклонено), голова слегка
  к окну, глаза открыты, спокойна; щека в центре кадра. Косметолог у левого края, лицо в мягком ¾ вниз;
  в чёрных перчатках держит внизу по центру квадратный флакон EXO-NAD PEELING надписью к камере. Набор
  за кадром.
- **Референсы:** K1 (утверждённый), `<scratch>/nad/refs/vtech/f121.png`, `<scratch>/nad/refs/vtech/f546.png`
  (наклон кресла и посадка в фильме V-TECH),
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/product-cinema/exo-nad/kit-photo.png`,
  `<scratch>/nad/refs/live/123-t10.png`.
- **Промпт:**
  `Same clinic and daylight. Medium close-up, 50mm: the patient from the attached K1 (same face, hair, white towelling headband, ivory top) leans back in the slightly reclined white treatment chair, head turned a little toward the window, eyes open and calm; her cheek is in the centre of the frame. The same cosmetologist stands at the left edge, face in soft three-quarter view looking down, wearing black nitrile gloves as in the attached video frame. In the lower centre she holds the square clear EXO-NAD PEELING bottle with its gold cap at chest height, print facing the camera, exactly as in the attached real photo: black print directly on the glass, pale gold liquid with gold flakes.` + общий хвост.

### K3 — шаг 2, pH NORMALIZER
- **Зачем:** старт клипа D (нормализатор, смыв, сушка).
- **Композиция:** та же постановка, что K2. Новые чёрные перчатки. Левая рука внизу по центру держит
  открытый флакон PH NORMALIZER (колпачок отщёлкнут), кончики пальцев правой руки на той же щеке, тонкий
  прозрачный слой едва блестит.
- **Референсы:** K2 (утверждённый),
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/product-cinema/exo-nad/kit-photo.png`,
  `<scratch>/nad/refs/live/123-t10.png`, `<scratch>/nad/refs/live/123-t02.png`.
- **Промпт:**
  `Exactly the same framing, people and light as the attached K2. The cosmetologist now wears a fresh pair of black nitrile gloves. Her left hand holds, in the lower centre, an opened PH NORMALIZER vial exactly as in the attached real photo and video frame: small clear glass vial, pale golden-amber liquid near the shoulder, VM monogram print on the glass, silver aluminium crimp ring with the flip-off top removed. The fingertips of her right hand rest on the same cheek, where a thin clear layer of liquid barely glistens. The patient's skin, tone and expression are identical to K2.` + общий хвост.

### K4 — шаг 3, LONGEVITY SERUM
- **Зачем:** старт клипа E.
- **Композиция:** то же, что K3; кожа после смыва и сушки сухая, матовая, как в K2. Опять новые перчатки.
  Внизу по центру открытый флакон с бледно-голубой жидкостью; кончики пальцев мягко прижаты к щеке.
- **Референсы:** K3 (утверждённый),
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/product-cinema/exo-nad/kit-photo.png`,
  `<scratch>/nad/refs/live/123-t10.png`.
- **Промпт:**
  `Exactly the same framing, people and light as the attached K3. Fresh black nitrile gloves again. The cheek is clean and dry, matte, with the same natural texture and tone as in K2. In the lower centre her left hand holds an opened LONGEVITY SERUM vial exactly as in the attached real photo and video frame: small clear glass vial, pale blue liquid near the shoulder, VM monogram print, silver crimp ring with the flip-off top removed. The fingertips of her right hand press gently on the same cheek. Nothing in the skin looks changed or improved.` + общий хвост.

### K5 — спокойный общий план в конце (сцены 06–07)
- **Зачем:** конец клипа F, стоп-кадр сцены 07 и вход в перевёрнутый клип A. Должен почти совпадать с K1,
  чтобы шестикадровый стык K5→K1 был незаметен.
- **Композиция:** камера, свет, мебель и набор — ровно как в K1. Меняются только выражения: обе женщины
  мягко, естественно улыбаются, косметолог что-то спокойно говорит; руки у обеих лежат на столе.
- **Референсы:** K1 (утверждённый, главный), `<scratch>/nad/refs/vtech/f121.png`.
- **Промпт:**
  `Exactly the same camera, framing, light, furniture and kit position as the attached K1 — this is the same shot a few minutes later. Only small changes: the cosmetologist speaks calmly with a soft natural smile, the patient listens with a relaxed, quiet smile; both keep their hands resting on the table. The patient's skin, hair, headband and top are identical to K1: no glow, no smoothing, nothing that reads as a treatment result.` + общий хвост.

### VK — раскрытый набор V-TECH на том же столе (концовка фильма V-TECH)
- **Зачем:** конечный кадр клипа VK; заменяет нынешнее раскрытие из вырезанных слоёв Blender.
- **Композиция:** та же камера, что в последнем кадре фильма V-TECH (стол на уровне объектива, женщины
  размыты за набором), чуть отъехавшая, чтобы поместился раскрытый набор. Как в рендере `open-039`:
  слева стоит пустая золотая гильза с V-образным вырезом, по центру стоит открытая чёрная коробка —
  в лотке один золотой пакет V-TECH GEL MASK с белым носиком и под ним пять флаконов, колпачками к камере;
  справа стоит откинутая чёрная крышка с надписями VM / V-TECH SYSTEM. Лоток ровно в центре кадра.
  Похоже, V на гильзе — сквозное окно (на закрытой коробке через него видна чёрная коробка, на снятой
  гильзе — то, что за ней); модель должна взять вид гильзы из рендера, а не придумывать.
- **Референсы:** `<scratch>/nad/refs/vtech/f872.png` (лучше — настоящий последний кадр десктоп-фильма:
  terminal poster из `vtech-continuity-v5.json`, media `d3242869-63a4-4c3d-927a-2da885ec2005`),
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/vtech/kit-open.webp`,
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/vtech/unboxing/open-039.webp`,
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/vtech/unboxing/open-000.webp`,
  `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/vtech/unboxing/open-020.webp`.
  **Не прикладывать:** `vtech-kit.webp` (не совпадает с набором) и `public/assets/vtech/system-kit.webp`
  (по мелкому тексту видно, что это тоже генерация: буквы искажены).
- **Промпт:**
  `Photorealistic film still matching the attached last frame of the V-TECH film: the same beige marble table, the same bright clinic and daylight, the same two women softly out of focus behind the table, camera at table height, pulled back slightly. On the table, centred, the opened V-TECH kit exactly as in the attached renders: on the left the empty gold sleeve standing upright, its front and V-shaped cut-out exactly as in the render; in the centre the black inner box standing open, its tray holding one gold V-TECH GEL MASK pouch with a white spout above five vials whose silver-white caps face the camera; on the right the opened black lid standing, with VM and V-TECH SYSTEM print in light grey. Exact shapes, proportions, colours and print of the references; no extra items, no extra pouches or vials. The tray sits exactly in the centre of the frame.` + общий хвост (без фразы про лица в центре).

## 4. Клипы

Формат промпта Seedance — как в `vtech-continuity-v5.json` (start_image + end_image, omni_reference,
16:9, без звука). Kling 4.0 — анимация от одного стартового кадра, как клипы действия V-TECH.

### A — набор → консультация. Seedance 2.5, 5 с, нужен конечный кадр
- **Старт / конец:** K0 → K1.
- **Что движется:** 3.5 с камера очень медленно наезжает на набор (≈4 %), женщины размыты; последние 1.5 с
  камера мягко отъезжает и чуть поднимается, фокус переходит на женщин, кадр садится точно в K1. Набор
  неподвижен. Женщины только дышат и моргают.
- **Почему Seedance:** лица обеих женщин должны прийти точно в утверждённый K1, а сам клип задом наперёд
  закрывает фильм и обязан кончиться ровно на K0. Kling от одного кадра «дорисует» лица при отъезде.
- **Промпт:**
  `Create a single continuous photorealistic camera shot in the same warm daylight aesthetic clinic. Frame zero must match the supplied START IMAGE exactly: framing, positions, scale, skin texture, clothing, jewelry, light, objects. Finish on the exact supplied END IMAGE, with no cut or new composition. Preserve the same dark wavy-haired female professional in the white tunic with pink piping and amethyst pendant, and the same patient with honey-brown hair under a white towelling headband and an ivory knit top. For the first three and a half seconds the camera stays on the open EXO-NAD kit on the marble table and pushes in very slowly, the print sharp, the two women soft behind it. In the last second and a half the camera eases back and rises slightly while focus shifts from the kit to the two women, settling exactly on the end two-shot with the kit on the table between them. The women only breathe and blink with small natural head movement. The kit never moves, opens or changes; every vial, cap and printed word stays attached and unchanged. Keep all action inside the central vertical third. Preserve natural fine lines and skin texture throughout; no beautification, skin smoothing, before/after effect, morphing faces, double exposure, dissolve, wipe, hard cuts, extra fingers, duplicate people, text overlays or added graphics. No audio.`
- **Проверить:** кадр 0 = K0 и последний = K1 без сдвига; печать EXO-NAD, колпачки и цвет жидкостей
  не плывут; лицо косметолога = f121, лицо пациентки = K1; нет двойного изображения в момент перевода
  фокуса; в вырезе 9:16 оба лица целиком.

### B — консультация продолжается. Kling 4.0, 5 с (в фильм идут первые 2.5 с)
- **Старт:** настоящий последний кадр одобренного клипа A (≈K1) — тогда стык A→B бесшовный.
- **Что движется:** разговор: косметолог внимательно смотрит на щёку пациентки, затем поворачивается и
  тянет правую руку к открытому набору; пациентка слушает. Камера — короткое смещение справа налево.
  Склейка в C — на движении руки.
- **Конечный кадр не нужен:** продукт уже в стартовом кадре и не двигается, лица заданы стартом, дальше
  склейка (так требует PAGE: «склейка на движении руки к лотку»).
- **Промпт:**
  `The cosmetologist and the patient talk quietly at the marble table. The cosmetologist looks attentively at the patient's cheek, then turns and reaches her right hand toward the open EXO-NAD kit on the table; the patient listens and nods slightly. The camera drifts a few centimetres from right to left. The kit stays exactly as in the start image; nothing is taken out. Lips mostly closed, no talking-head mouth motion.` + общий хвост Kling.
- **Проверить:** лица не меняются к 2.5 с; пальцы; набор не «оживает»; рука к 2.5 с явно движется к набору.

### C — шаг 1, EXO BIPHASIC PEEL. Kling 4.0, 5 с (в фильм 4.5 с)
- **Старт:** K2.
- **Что движется:** два мягких встряхивания флакона, флакон уходит вниз из кадра, кончики пальцев в
  перчатках распределяют тонкий прозрачный слой по щеке медленными мягкими кругами. Камера почти стоит.
- **Конечный кадр не нужен:** флакон в стартовом кадре, дальше склейка по времени.
- **Промпт:**
  `Camera nearly still, 50mm. The cosmetologist in black nitrile gloves gives the EXO-NAD PEELING bottle two gentle shakes, then lowers it out of frame. Her gloved fingertips spread a thin, clear layer evenly over the patient's cheek with slow, gentle circular movements. The patient rests calmly, breathing slowly. While visible, the bottle keeps its square shape, gold cap and black print on the glass. No redness, no flaking, no foam, no brush or cotton pad.` + общий хвост Kling.
- **Проверить:** встряхивание раньше нанесения; надпись на флаконе не превращается в кашу; пять пальцев;
  кожа в первом и последнем кадре одинаковая; лица = K1/f121.

### D — шаг 2, pH NORMALIZER, смыв, сушка. Kling 4.0, 5 с (в фильм 4.5 с)
- **Старт:** K3.
- **Что движется:** флакон уходит вниз из кадра, пальцы разглаживают прозрачный слой по той же щеке;
  затем влажный белый ватный компресс протирает участок, мягкое белое полотенце промакивает насухо,
  руки уходят из кадра. Самый трудный клип — заложены 3 попытки.
- **Конечный кадр не нужен:** флакон в стартовом кадре; компресс и полотенце — не упаковка, их можно
  не задавать референсом. Дальше склейка на новые перчатки.
- **Промпт:**
  `Same framing. In fresh black gloves the cosmetologist lowers the opened PH NORMALIZER vial out of frame and smooths the thin clear liquid over the same cheek with her fingertips. Then she gently wipes the area with a damp white cotton compress and pats the skin dry with a soft white towel, and her hands leave the frame. The patient stays calm. The area simply looks clean and dry; no glow, no colour change.` + общий хвост Kling.
- **Проверить:** видны смыв и сушка (жёсткое условие PAGE перед сывороткой); нет второго флакона; кожа
  не «улучшилась». **Запасной путь**, если одна сцена не вмещает три действия: ещё один стилл K3b
  (полотенце у щеки) + второй Kling от него, ≈19 кр.

### E — шаг 3, LONGEVITY SERUM. Kling 4.0, 5 с (замедление ×1.1 → 5.5 с)
- **Старт:** K4.
- **Что движется:** флакон уходит вниз из кадра, кончики пальцев мягкими нажатиями вводят прозрачную
  сыворотку в ту же щеку до впитывания, без смывания; руки расслабляются и уходят влево. Наезд ≤3 %.
- **Конечный кадр не нужен:** флакон в стартовом кадре, дальше склейка «чуть шире».
- **Промпт:**
  `Same framing, camera pushes in no more than three percent. In fresh black gloves the cosmetologist lowers the opened pale blue LONGEVITY SERUM vial out of frame and presses the clear serum gently into the same cheek with her fingertips in slow presses until it is absorbed. No rinsing, no towel. Then her hands relax and leave the frame to the left. The patient rests calmly.` + общий хвост Kling.
- **Проверить:** голубой флакон до ухода из кадра узнаваем; нет «частиц в клетки» и сияния; кожа
  в начале и в конце одинаковая.

### F — завершение встречи. Kling 4.0, 5 с, проигрывается задом наперёд
- **Старт генерации:** K5. В фильме клип идёт в обратную сторону и поэтому кончается точно на K5.
- **Что движется (в генерации):** очень мало: косметолог поднимает руку в небольшом поясняющем жесте,
  пациентка один раз кивает; обе дышат, моргают. В обратном проигрывании жест опускается и всё
  успокаивается в K5. Камера неподвижна.
- **Конечный кадр не нужен** — благодаря обратному проигрыванию. Если обратное движение будет читаться
  (моргание, губы), запасной вариант: Seedance от последнего кадра E к K5 (95…110 кр.).
- **Промпт:**
  `Camera locked, very low motion. The cosmetologist raises one hand in a small, calm explanatory gesture while speaking softly; the patient listens and nods once. Both breathe and blink naturally, lips mostly closed. The kit on the table stays exactly as in the start image. No one stands up or leaves.` + общий хвост Kling.
- **Проверить:** в обратном просмотре ничего не выдаёт обратный ход; последний кадр (после разворота)
  совпадает с K5; набор не меняется.

### VK — раскрытие набора V-TECH в концовке фильма V-TECH. Seedance 2.5, 5 с, нужен конечный кадр
- **Старт / конец:** настоящий последний кадр десктоп-фильма V-TECH (= кадр 0, `f872.png`) → VK.
- **Что движется:** руки косметолога (без перчаток, как на консультации) появляются из-за коробки,
  снимают золотую гильзу вверх и ставят её слева, открывают переднюю чёрную крышку вправо, уходят.
  Камера чуть отъезжает, оставаясь на высоте стола. Женщины в размытии.
- **Почему Seedance:** раскрытый набор обязан совпасть с референсом; Kling от закрытой коробки
  придумает упаковку.
- **Промпт:**
  `Create a single continuous photorealistic camera shot in the same warm daylight aesthetic clinic. Frame zero must match the supplied START IMAGE exactly: framing, positions, scale, light, objects, the two women softly out of focus behind the table. Finish on the exact supplied END IMAGE, with no cut or new composition. The professional's bare hands reach in from behind the box, slide the gold V-TECH sleeve straight up off the black inner box and stand it on the table to the left; then they swing the black front lid open to the right, revealing the tray with one gold GEL MASK pouch and five vial caps, and withdraw out of frame. The camera pulls back slightly at table height. The two women stay soft in the background. Objects move only by the hands, physically; nothing transforms into another object, no extra pouches or vials appear. Existing product markings stay attached to their objects. No double exposure, dissolve, wipe, hard cuts, extra fingers, duplicate people, text overlays or added graphics. No audio.`
- **Проверить:** кадр 0 совпадает с концом фильма; гильза снимается вверх (как в `open-020`), а не
  складывается; надписи VM / V-TECH / GEL MASK не искажены; пять колпачков; пальцы.

## 5. Сборка

**Основа:** `/home/user/GregoryDich/mitoderm-catalog/codex-site/production/assemble-vtech-continuity-v5.py`.
Его не правим — делаем копию `assemble-exo-nad-film.py` рядом с ним и меняем список сегментов. Берём из него
как есть: нормализацию (масштаб + вырез + `setpts` + `fps=24`), разворот (`reverse`, как у `pack_zoom`),
шестикадровый оптический стык `join()` (DIS), склейку `concat` без перекодирования, проверки (число кадров,
нет звука, ключевые кадры ≤6, faststart, последний кадр = кадр 0 клипа A).

Что добавить в копию (небольшие правки):
1. **Стоп-кадры:** сегменты `hold_k0` (24 кадра), `hold_k5` (66), `hold_k0_end` (12) — заранее делаются
   ffmpeg-ом из нужного кадра (`-loop 1 -frames:v N`) и подаются как обычные исходники.
2. **Склейка без стыка:** флаг `cut_before` у сегмента, чтобы `join()` не вызывался перед C, D, E, F
   (сейчас скрипт строит стык между всеми соседями).
3. **Обрезка:** поле `frames` (B — 60, C и D — 108), например `-frames:v`/`trim`; кадр 0 клипа A
   уходит в `hold_k0`, поэтому вперёд идут кадры 1–120, назад — 120→1.
4. **Одна телефонная версия из того же мастера:** в `config.variants.mobile` те же файлы, что в desktop.

Список сегментов (имя, источник, скорость, смещение выреза для телефона, разворот, стык перед):
`hold_k0 (1,.5,no) · A (1,.5,no, без стыка) · B (1,.5,no, без стыка — старт с последнего кадра A) ·
C (1,.5,cut) · D (1,.5,cut) · E (1.1,.5,cut) · F (1,.5,reverse,cut) · hold_k5 · join K5→A_rev (6) ·
A_rev (1,.5,reverse) · hold_k0_end`. Итого 876 кадров.

**Вертикальная версия:** как в v5 для mobile: `scale=812:1440:force_original_aspect_ratio=increase,
crop=812:1440:(iw-812)*0.5:0` — то есть из кадра 1912×1080 берётся центральная полоса ≈607×1080 и
увеличивается в 1.33 раза до 812×1440. Поэтому всё действие и стоит в средней трети. Если в каком-то клипе
действие уехало, смещение выреза задаётся на весь сегмент (в v5 это `focal`), для плавного сдвига внутри
клипа есть готовая функция `registered_portrait_bridge`. Увеличение в 1.33 раза даёт лёгкую мягкость на
телефоне — это цена одного мастера; если заказчику мало, апскейл исходников ×2 перед вырезом.

**Концовка V-TECH:** клип VK нормализуется так же (1912×1080, GOP 6, без звука) и ставится после
последнего кадра фильма; телефонный вариант — центральный вырез VK + шестикадровый стык от последнего
кадра телефонного фильма (он был отдельной генерацией 9:16, точного совпадения не будет, см. вопросы).

## 6. Стоимость (кредиты)

Цены, измеренные сегодня: Seedance 2.5 omni_reference 5 с — 480p черновик 15, 720p 35, 1080p 80
(черновик потом доводится до 1080p как тот же дубль). Kling 4.0 5 с 1080p — 16.25. Стилл ≈2–2.75.

**По клипам — оба варианта за один дубль:**

| Клип | Seedance (черновик 15 + финал 80) | Kling 4.0 | Нужен конечный кадр? | Рекомендация |
|---|---:|---:|---|---|
| A K0→K1 | 95 | 16.25 | да: лица в K1 + обратный финал на K0 | **Seedance** |
| B консультация | 95 (если K1→K2 сплошным движением) | 16.25 | нет: дальше склейка по PAGE | **Kling** |
| C пилинг | 95 (K2→K3) | 16.25 | нет: склейка по времени | **Kling** |
| D нормализатор | 95 (K3→K4) | 16.25 | нет: склейка на новые перчатки | **Kling** |
| E сыворотка | 95 (K4→K5) | 16.25 | нет: склейка «чуть шире» | **Kling** |
| F завершение | 95 (E→K5) | 16.25 | нет, если играть задом наперёд | **Kling**, запас — Seedance |
| VK V-TECH | 95 | 16.25 | да: раскрытую упаковку нельзя придумывать | **Seedance** |

**Рекомендованный план с запасом попыток:**

| Статья | Расчёт | Кредиты |
|---|---|---:|
| Стиллы | 7 кадров (K0–K5, VK) × 3 попытки × 2.75 | 57.75 |
| Пробы Seedance | A и VK по 2 черновика 480p × 15 | 60 |
| Пробы Kling (сразу 1080p, дешевле черновика нет) | B, C, E, F по 2 дубля + D 3 дубля = 11 × 16.25 | 178.75 |
| Финалы Seedance 1080p | A и VK × 80 | 160 |
| **Итого** | | **456.5** |

Минимум (всё с первого раза): 7 × 2.75 + 2 × 95 + 5 × 16.25 = **290.5**. Резерв на запасные пути
(K3b + второй D ≈19, F на Seedance ≈110) — до ≈585, всё равно далеко от потолка 1000.
Для сравнения, исходный план «A–E и VK на Seedance, по 2 черновика и финалу» — 6 × 110 + 57.75 = **717.75**.

**Порядок трат (каждый шаг — цена и баланс заказчику, «утверждаю»):** K1 (2.75) → «ок» на пациентку →
K0, черновик A 480p (15) → «ок» образца → K2–K5 и клипы B–F → финал A 1080p → VK отдельно.

## 7. Открытые вопросы

1. Перчатки: чёрные нитриловые (как в настоящем видео EXO-NAD) или белые латексные (как в фильме V-TECH)?
2. Внешность новой пациентки — утвердить на K1 до любых клипов.
3. Как пилинг попадает на кожу (пальцами, кисточкой, со спонжа; есть ли у флакона пипетка) — уточнить у
   MITODERM; в черновике — пальцами в перчатках, без кисти.
4. Смыв: компресс + полотенце — наша заглушка, нужен «ок» специалиста.
5. Обратное проигрывание F — приемлемо, или сразу брать Seedance (+95…110)?
6. V-TECH: в раскрытом наборе один пакет маски и пять флаконов, как в рендере, — так и в настоящей коробке?
7. Телефон V-TECH: допустим ли стык от отдельного 9:16 финала к центральному вырезу VK, или делать VK
   отдельно в 9:16 (+95)?
