# aquarium-test — детерминированный харнесс для `aquarium/index.html`

Живёт **вне** `aquarium/` (macOS-сборка `macos-app/build.sh` копирует всю папку `aquarium/` в .app —
тестам и результатам там не место). Источник правды по архитектуре и гейтам — `SPEC.md` рядом.

Headless Chromium (puppeteer-core + @sparticuz/chromium) рисует программно: абсолютные fps и мс
**бессмысленны**, кадры «в реальном времени» **непригодны** для оценки движения. Всё, что идёт в
отчёты и гейты, снимается шагами `window.__aq.step(dt)` в режиме `?test=1`.

## Установка

```sh
cd tools/aquarium-test && npm install        # node_modules/ и out/ в .gitignore
```

Chromium распаковывается @sparticuz/chromium во временную папку при первом запуске.
Флаг `--allow-file-access-from-files` **не** передаётся: иначе Chromium перестаёт «пачкать» холст
картинками с `file://`, и запрещённый `getImageData` по холсту с фото не упадёт (SPEC F2).
Нужен он только в исключительных случаях: `--file-access`.

## Флаги движка (query string)

| Флаг | Что делает |
|---|---|
| `?test=1` | симуляция **не** идёт от rAF; кадр — только по `__aq.step()`; включает счётчики |
| `?seed=N` | один сидированный ГПСЧ (mulberry32) вместо `Math.random` во всём движке |
| `?debug=1` | оверлей: RS, буфер, уровень качества, p90/fps, счётчики canvas, JS мс; `?debug=2` — плюс геометрия сцены (линия воды, горизонт, safeX, пол, точки, источники пузырьков и света) |
| `?nofilter=1` | `HAS_FILTER = false` (как в WebKit). В отгружаемом коде `ctx.filter` не используется вовсе — кадры с флагом и без совпадают |
| `?nobg=1` | задник не грузится → процедурный векторный риф (проверка фолбэка) |
| `?gov=0` | регулятор качества выключен (нужно `bench.js`: синтетическое время 1/30 с иначе «роняет» качество) |
| `?wallpaper=1` | режим обоев, как в macOS-приложении (без подсказки, курсора и ввода) |

Скрипты харнесса по умолчанию добавляют `test=1&wallpaper=1&nofilter=1&seed=1`
(отключаются `--no-test`, `--no-wallpaper`, `--no-nofilter`; `--seed N`; прочее — `--q "debug=2&nobg=1"`).

## `window.__aq` (есть всегда; счётчики — только при `?test=1` или `?debug=1`)

| Вызов | Результат |
|---|---|
| `ready()` | `true`, когда задник загружен/отвергнут и все спрайты рыб с `count > 0` загружены |
| `step(dt = 1/30, n = 1, { render })` | `n` шагов по `dt` с; `render: true` (каждый шаг, по умолчанию) \| `false` \| `"last"`; возвращает `simT` |
| `setTime(t)` | часы симуляции `simT` (фазы хвостов, лучей, планктона) |
| `render()` | перерисовать текущее состояние без шага |
| `stats()` | `{ last, avg, max }` по ключам `drawImage, setTransform, gradients, patterns, save, restore, getImageData, filter, jsMs` (среднее/максимум — с последнего `resetStats()`), `frames, backing {w,h,mp}, css, dpr, RS, quality {level, particles, fishSlices, causticScale, rsMul}, governor {p90, fps, …}, hasFilter, photo, sceneFromFile, fish, bubbles, simT, seed` |
| `resetStats()` | обнулить накопленные среднее/максимум |
| `fish()` | снимок рыб: `{ i, id, x, y, z, depth, len, facing, vx, vy, alpha, sprite }` |
| `scene()` | `{ fromFile, backdrop, photo, bandH, map (BGX), horizon [x,y], visibleBX, visibleBY, scene }` |
| `bgMap(bx, by)` / `bgUnmap(x, y)` | доли задника ↔ CSS-пиксели экрана |
| `setQuality(level)` | принудительно уровень качества 0…4 |

`jsMs` — `performance.now()` вокруг тела кадра (симуляция + отрисовка). Счётчики — обёртки на
`CanvasRenderingContext2D.prototype`, т.е. учитываются и offscreen-холсты; `filter` считает любые
присваивания `ctx.filter` ≠ `"none"` (должно быть 0).

## Команды

Все скрипты печатают JSON в stdout, ошибки страницы (pageerror, console.error, requestfailed,
http ≥ 400) — в stderr, и выходят с кодом 2, если ошибки были (`--allow-errors` — не падать).
`--http` — вместо `file://` поднять встроенный http-сервер на 127.0.0.1. `--root DIR` — другой
каталог движка (например, старая версия для сравнения). Пути `--out` — относительно текущей папки;
по умолчанию результаты пишутся в `tools/aquarium-test/out/`.

```sh
# кадр: 90 шагов по 1/30 с, последний отрисован → PNG (+ кадрирование 100% --clip x,y,w,h)
node still.js --out /tmp/x/still.png --w 1920 --h 1200 --seed 1 --steps 90
node still.js --out /tmp/x/dbg.png --q debug=2 --http
node still.js --out /tmp/x/fallback.png --q nobg=1

# клип: 150 кадров ровно по 1/30 с → H.264 MP4 (yuv420p, crf 18) [+ GIF 960 px через palettegen]
node clip.js --out /tmp/x/clip.mp4 --frames 150 --warm 30 --gif /tmp/x/clip.gif
node clip.js --out /tmp/x/crop.mp4 --clip 600,300,640,400 --frames 90 --keep /tmp/x/frames
node clip.js --out /tmp/x/long.mp4 --frames 600 --format jpeg     # кадры JPEG q95 — быстрее (≈1–2 с/кадр в PNG при 1920×1200)

# статистика: прогрев 60, затем 300 шагов (каждый рисуется и показывается) → avg/max/last
node stats.js --out /tmp/x/stats.json            # file://
node stats.js --http --out /tmp/x/stats_http.json

# матрица мониторов: RS и буфер холста (гейт ≤ 8.4 Мп), --shots — уменьшенные кадры 1280 px
node matrix.js --shots /tmp/x/matrix --out /tmp/x/matrix.json
node matrix.js --http

# «равный метод» JS-времени для ЛЮБОЙ версии движка (подмена rAF, без test-режима и счётчиков)
node bench.js --runs 3 --out /tmp/x/bench_new.json                       # текущий движок (?seed=1&nofilter=1&gov=0)
git show 041f9c0:aquarium/index.html > /tmp/base/index.html  # + скопировать fish/ и assets/ рядом
node bench.js --root /tmp/base --strip-filter --seed-math 1 --runs 3     # исходный движок

# регулятор качества и режимы питания (синтетические интервалы кадров, без test-режима)
node governor.js
```

## Гейты (SPEC §5): как мерить

- **Ошибки:** `still.js` и `stats.js` под `file://` и `--http` — `errors: none`.
- **Буфер:** `matrix.js` (и с `--http`) — `pass: true`.
- **Градиенты в фото-режиме:** `stats.js` → `max.gradients == 0`, `max.patterns`, `max.filter == 0`, `max.getImageData == 0`.
- **JS-время:** сравнивать только одним методом и на одной машине, прогоны по очереди (не параллельно).
  Для «baseline + X мс» — `bench.js` на обеих версиях; для «G0 + X мс» между этапами — `stats.js`
  (`avg.jsMs`, режим `?test=1` со счётчиками).
- **Движение:** только `clip.js` (шаговый режим), никогда — запись реального времени из headless.

## Опорные числа S0 (1920×1200@1, headless, этот контейнер)

Ориентиры для следующих этапов (относительные — машина и программный растр те же):

| Метрика | Значение S0 |
|---|---|
| `stats.js` avg drawImage / setTransform / gradients / patterns / save=restore | 443 / 0 / 0 / 0 / 22 (20 рыб × 22 среза + задник + полоса + виньетка) |
| `stats.js` avg jsMs, `?test=1` со счётчиками (file:// / http) | 2.11 / 2.27 мс |
| `bench.js`, медиана средних по 3 прогонам, два раунда | исходный 041f9c0: 2.72 и 2.68 мс; S0: 2.19 и 1.83 мс |
| Буфер 1512×982@2 / 1728×1117@2 / 1920×1080@2 / 2560×1440@2 / 3008×1692@2 / 3840×2160@1 | 5.94 / 7.72 / 8.29 / 8.30 / 8.30 / 8.29 Мп (RS 2 / 2 / 2 / 1.50 / 1.28 / 1) |

Разброс `jsMs` между прогонами ±15–20%: сравнивать средние нескольких прогонов, запущенных по очереди.

## Этап E1 «свет и вода»: гейт G1 и API

```sh
# кадровые проверки G1 (каустика вне маски, контраст нитей на песке, лучи ≤ 8%, drawImage света ≤ 60,
# filter/getImageData = 0) + счётчики за 300 шагов; кадры mask/on/no_caustics/no_rays и карта вклада
node gates_e1.js --out /tmp/x/g1                 # --count 1 — без 300-шагового прогона счётчиков
node gates_e1.js --http --w 1512 --h 982 --dpr 2
```

Один момент симуляции рисуется несколько раз (`__aq.render()` без шага) с разными слоями; скриншоты
декодируются в отдельной чистой вкладке — движок пиксели не читает. Внимание: `page.screenshot({clip})`
в puppeteer может вызвать `resize` движка (перерисовка с пересевом частиц) — для кадров «до/после»
снимать весь экран и резать потом.

Добавлено в `window.__aq` (E1):

| Вызов | Результат |
|---|---|
| `layers({caustics, rays, band, bubbles, particles, glow, shadows})` | вкл/выкл слоёв (тесты; то же — `?layers=-rays,-caustics`); возвращает текущие |
| `lightAt(x, y)` | яркость лучей в точке (CSS px), ≈0…1 |
| `causticAt(x, y)` | сырой рисунок каустики 0…1 в момент `simT` |
| `current(x)` | общее течение C(t, x) (безразмерно) |
| `floorYAt(x)` | линия пола (контакт песка) на экране |
| `maskAt(x, y)` | процедурная маска каустики (NaN, если маска — PNG) |
| `showMask()` | нарисовать маску каустики на холст (белое = 1) |
| `burp(id)` | «отрыжка» пузырьков из камня |
| `bubbles()` | `{ n, sources: [{id, kind, x, y, z}], list: [{src, x, y, r, vy, age}] }` |
| `streaks()` | состояние полос света кадра `[x0, y0, ux, uy, wpx, len, I, Ifil]` |
| `drawWithCaustic(img, x, y, w, h, opts)` / `occluderRoundTrip(img, x, y, w, h)` | проверка `applyMaskedCaustic` / `captureLitBackdrop` (E4) |

`stats()` — дополнительно счётчики `e1Light` (drawImage света/воды без пузырьков и частиц; гейт ≤ 60),
`e1Bubbles`, `e1Particles`, а также `particles`, `layers`, `light {streaks, kBuffer, kScale, mask}`.

JS-время G1 под нагрузкой соседних агентов: средние по блокам «плывут» из-за выбросов. Надёжнее —
пер-кадровые значения, два движка вперемешку блоками по 20 кадров, сравнивать медиану/p25:
`node abtime.js --a /path/to/prev_engine_root [--b ../../aquarium] --rounds 16` (корень A — index.html прошлого
этапа + симлинки assets/ fish/ scene/).

## Этап E3 «рыбы»: гейт G3 и API

```sh
# 10-минутная детерминированная симуляция (18000 шагов по 1/30 с, считается в странице), отрисовка
# каждого --renderEvery шага (счётчики drawImage рыб): все метрики G3 + gates + allPass, exit 2 при ошибках
node sim.js --minutes 10 --renderEvery 10 --out /tmp/x/sim.json [--seed 1 --w 1920 --h 1200 --http]
```

Метрики `sim.js` (по ВИДИМЫМ рыбам — на экране, не за кадром, не за окклюдером):
`jump` (смещение центра рамки тела и опорной точки за шаг; гейт ≤ 3% W), `width` (x-протяжённость тела /
экранная длина; гейт ≥ 0.15), `turns` (длительности 0.35–0.9 с; развороты, оборванные уходом за кадр, —
отдельно `cutByOffstage`; `perMinutePerFish`, `byState`, `byFish`), `yaw` (|рыскание| вне разворота ≤ 32°),
`cruise` (доля шагов CRUISE в 0.3–1.5 BL/s ≥ 95%), `scale` (диапазон 1/z, гейт покрывает 0.45–1.0),
`visibility` (среднее ≥ 70%, у каждой рыбы скрыто < 25%), `story` (наибольший промежуток между битами
≤ 60 с, журнал битов, кормушка), `drawImage` (рыбы ≤ 420; из них `fog`/`lit`), `stateShare`,
`violSecondsTotal` (секунды прямых поправок z рифом — рыба при этом НЕ рисуется перед камнем: у предела
запас 0.05). JS-время G3 («G1 + 2 мс») — `stats.js` или `abtime.js` против снимка движка E1.

Добавлено в `window.__aq` (E3):

| Вызов | Результат |
|---|---|
| `fish()` | на рыбу: `id, state, sub, x, y` (экран, опорная точка), `z, X, Y` (мир), `L0, len, h, dir, facing, yawDeg, pitchDeg, turning, turnP, turnT, speedBL, visible, visFrac, onScreen, widthFrac, bbox, near, leaving, school, target [x, y, z], slices, litMax, hiddenT, aliveT, viol` |
| `fishGeom()` | Float64Array по 14 чисел на рыбу (для `sim.js`): visible, x, y, центр рамки x/y, widthFrac, turning, yawDeg, speedBL, индекс состояния (`states`), z, offstage, onScreen, viol |
| `states` | список состояний: CRUISE GRAZE PICK HOVER HIDE PEEK HOME SHOAL LURK CHASE FLEE FEED OFFSTAGE |
| `director()` | `{ log: [{t, id, fish}], next, major, beats, feeder {on, nextAuto, left}, feed {dropped, eaten, feeds} }` |
| `beat(id)` | запустить бит сейчас: `nearGlass, farPass, shoalSweep, peek, graze, chase, crab, burp` (true — сработал) |
| `feed()` / `dropFood(x, y)` | автокормушка сейчас / горсть хлопьев в точке экрана (как клик) |
| `camera()` | `{cx, hy, D, fogK, floorW}` — точка схода, 1 z = D px, дымка, плоскость песка |
| `flakesDbg()` / `flakeSprites()` | хлопья корма (экран, z, возраст) / спрайты хлопьев (dataURL) |

`stats()` — дополнительно счётчики `e3Fish` (все drawImage рыб: срезы, дымка, свет, вспышки, тени на песке,
отражения у поверхности), `e3Fog`, `e3Lit`, `e3Food`; поле `flakes`. Слои: `fishlight`, `reflections`
(`?layers=-fishlight` или `__aq.layers({fishlight: false})`).

JS-время G3: базу E1 сравнивать с ТЕМ ЖЕ составом рыб, на котором она мерилась (манифест из git HEAD:
2 антиаса, 20 рыб) — корень движка E1 + `fish/` с PNG-симлинками и старым `manifest.js`; запуски по очереди
`nice -n -15 node stats.js --root <база>` и `nice -n -15 node stats.js`, по 3, медиана `avg.jsMs`.
Опорные числа (1920×1200, этот контейнер): база E1 2.76 мс, E3 4.34 мс (+1.58); без подсветки рыб E3 ≈ 3.05 мс.
Подсветка рыб в программном растре дорога из-за промежуточных холстов: один слой света на кадр (½…⅜ RS),
маска и сложение — после всех рыб; никаких черновиков на каждую рыбу (каждый такой холст ≈ 0.3–0.4 мс).

Для E4 (внутри движка): окклюдеры/пропсы — в общий список отрисовки со своим `z` (`rlPush(z, kind, obj)`);
рыба с большим `z` рисуется раньше и оказывается за ними. Если окклюдер рисуется поверх подсвеченной рыбы —
`llEraseImage(img, x, y, w, h)` (стирает свет рыбы под альфой картинки). Бит краба — `STORY_HOOKS.crab = (t) => bool`.
Клоуны держат z = z актинии ± 0.025 (`homeOf` читает `props[].nest`, размер картинки — `props[].imgW/imgH`, по
умолчанию 770×717).

## Этап V2 «сцена видео-задника»: гейт и сборка

```sh
# маски-окклюдеры колонн поверх живого кадра (постеры + кадры MP4 дня и ночи, t = 1.0 и 12.3 с) без рыб:
# путь captureLitBackdrop ≤ 2/255 на 1.54 / 1.6 / 1.78 / 2.33 (+ 3440×1440) × RS 1/2; реквизит внутри safeX и
# видим ≥ 60% на каждом соотношении. Раскладка — контракт scene.js v2 (bandH 0, cover × zoom, anchorY).
node gates_v2.js --out /tmp/x/gates_v2.json [--cases "1512x982@2,…"] [--times "1.0,12.3"]
```

Скрипты сборки масок, глубины, маски каустики, превью переднего рифа и генерации `scene.js` — `scene_v2/`
(порядок — `scene_v2/README.md`). `requestfailed … .mp4 net::ERR_ABORTED` — нормальная отмена первого запроса
`<video>` (перезапрос диапазонами), гейт её не считает ошибкой.

## Этап V4a «видео-задник, темы, свет, маски»: флаги и API

Флаги движка (вдобавок к таблице выше):

| Флаг | Что делает |
|---|---|
| `?theme=day\|night` | тема принудительно (иначе — `prefers-color-scheme` системы; в headless — день) |
| `?bgvideo=webm` | только с `?test=1`: задник — тестовые копии VP9 `tools/aquarium-test/media/reef_{day,night}.webm` (1920×1080, вне бандла; пересборка — `make_media.sh … --no-mp4`) |
| `?bgvideo=intra` | только с `?test=1`: `media/reef_{day,night}_i.mp4` — H.264 1920×1080, ВСЕ кадры ключевые (перемотка на соседний кадр — один декод: клипы и `stats.js` быстрые). Сборка: `ffmpeg -i ../../aquarium/assets/reef_day.mp4 -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset veryfast -crf 18 -g 1 -keyint_min 1 -sc_threshold 0 -pix_fmt yuv420p -an media/reef_day_i.mp4` (≈110 МБ, не в git) |
| `?bgvideo=mp4` | только с `?test=1`: отгружаемые MP4 (один ключевой кадр — перемотка дорогая: годится для кадров, не для клипов) |
| `?bgvideo=0` | без видео и вне теста (постер) |

Тест-режим без `bgvideo` рисует ПОСТЕРЫ (кадр 0 петли) — синхронно, все прежние скрипты работают как раньше.
С `bgvideo` видео стоит на паузе и перед каждым рисуемым шагом перематывается на кадр `floor(simT·29.97) mod 600`;
тогда `__aq.step()` возвращает Promise — `still.js`, `clip.js`, `stats.js` (через `L.stepFrames`) его ждут (`await`).
Время перемотки в `jsMs` не входит. `requestfailed … .webm net::ERR_ABORTED` харнесс пишет в warnings (перезапрос медиа).

```sh
node still.js --out /tmp/x/day.png --steps 300 --q "bgvideo=webm"                 # день, кадр видео t = 10 с
node still.js --out /tmp/x/night.png --steps 300 --q "bgvideo=mp4&theme=night"    # ночь, отгружаемый MP4
node clip.js --out /tmp/x/fade.mp4 --frames 150 --format jpeg --q "bgvideo=webm" --at "15:__aq.setTheme('night')"
node stats.js --q "bgvideo=webm" --out /tmp/x/stats.json                          # 360 перемоток — ≈5–8 мин
```

`window.__aq` (V4a): `theme()` → `{mode, target, p, k (вес ночи), dark, bgMode, bgSrc, sources [{theme, poster, video, aligned,
frame, t, playing, size}], tv}`; `setTheme('day'|'night'|'auto', instant)` (как `window.aquariumSetTheme`; `instant` — без
перехода). `stats()` — плюс `bgMode` (`video`|`photo`|null), `theme`, `themeK`, `video` (состояния видео тем).
