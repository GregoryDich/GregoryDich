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
