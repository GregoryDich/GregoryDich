# Foot Measurement MVP — iPhone 16 Pro Max (RGB + LiDAR) → RF-DETR → длина и ширина стопы в мм

> Код живёт в ветке **`claude/foot-measurement-mvp-i7rynx`** (в `main` его пока нет):
> ```bash
> git clone -b claude/foot-measurement-mvp-i7rynx https://github.com/GregoryDich/GregoryDich.git
> cd GregoryDich/foot-measurement
> ```
> Просмотр на GitHub: https://github.com/GregoryDich/GregoryDich/tree/claude/foot-measurement-mvp-i7rynx/foot-measurement

Минимальный прототип: телефон записывает RGB-видео + LiDAR-depth + калибровку камеры,
Python-сервис находит стопу с помощью **RF-DETR-Seg** (единственная нейросеть),
объединяет маску с LiDAR-геометрией и **вычисляет** из этих данных:

```
Length: 268.7 mm
Width:  101.4 mm
```

```
iPhone                        Python
──────                        ──────────────────────────────────────────────
video.mov + depth.bin  ──►    session.py   кадр i ↔ depth i ↔ K_i, T_i
+ metadata.json               detector.py  RF-DETR-Seg  → маска FOOT (где стопа?)
                              floor.py     RANSAC по LiDAR → плоскость пола
                              measure.py   контур RGB × плоскость(пол + h_LiDAR) → 3D-контур
                                           → проекция на пол → PCA → длина, макс. ширина
                              multiframe.py N кадров → gating → медиана
                              debug.png    маска + контур + линии L / W + вид сверху
```

Принцип: RF-DETR отвечает *где стопа*, RGB даёт *направление луча* через границу,
LiDAR даёт *масштаб и плоскость пола*, несколько кадров дают *стабильность*.
На вход пайплайна подаются только видео, depth и калибровка — никаких эталонных размеров.

## Состав

```
foot-measurement/
  ios/                          приложение FootCapture: [START] [STOP] [SEND] (SwiftUI + ARKit)
  python/footmeasure/           пакет: CLI по стадиям + FastAPI-сервер
  python/tests/                 синтетические тесты (без iPhone)
  python/make_synthetic_session.py  генератор демо-сессии (без iPhone)
  python/training/              дообучение RF-DETR-Seg на класс foot (Colab)
  python/evaluate.py            сверка с ручным измерением (раздел «Эталонная проверка»)
```

## A. Проверка за 10 минут без iPhone

Показывает, что пайплайн действительно *вычисляет* размеры из video + depth.

```bash
cd foot-measurement/python
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'          # numpy, opencv, rfdetr (+torch ~2 ГБ), fastapi, uvicorn, pytest
pytest                            # 29 тестов: геометрия, RANSAC, рендер стопы, детектор, CLI, сервер
```

Дальше — синтетическая сессия. Скрипт рисует объёмную «стопу» с размерами, которые
вы зададите, и сохраняет её в **точно таком же формате, как iOS-приложение**
(`video.mov`, `depth.bin`, `confidence.bin`, `metadata.json`). Эти размеры — параметры
*генератора*; пайплайн их не получает и должен восстановить сам:

```bash
python make_synthetic_session.py out/demo --length-mm 251 --width-mm 93
footmeasure process out/demo --mock-detector --step 1 --rotate
```

Ожидаемый вывод — числа, вычисленные из данных (отличие от заданных 251/93 — в пределах
±3 мм, это погрешность геометрии на синтетике):

```
Length: 250.x mm
Width:   92.x mm
```

Результат: `out/demo/result.json` (медиана, IQR, по-кадровые значения и причины отбраковки)
и `out/demo/debug.png` (маска, контур, линия длины, линия максимальной ширины, вид сверху).
Попробуйте другие `--length-mm/--width-mm` — результат меняется вслед за данными.

`--mock-detector` здесь обязателен: синтетическая «стопа» — это просто цветное пятно, и
RF-DETR на ней не нужен. На реальных записях вместо него используется `--weights`.

Сервер тоже можно проверить без телефона:

```bash
FOOTMEASURE_MOCK=1 uvicorn footmeasure.server:app --port 8000 &
(cd out && zip -qr demo.zip demo) && curl -s --data-binary @out/demo.zip -H 'Content-Type: application/zip' \
    http://127.0.0.1:8000/sessions
```

## B. Проверка на реальном iPhone 16 Pro Max — по шагам

### Шаг 1. Python-сервис на Mac (Apple Silicon)

Как в разделе A (`pip install -e '.[dev]'`). Сервер, к которому обращается кнопка SEND:

```bash
export FOOTMEASURE_WEIGHTS=weights/checkpoint_best_total.pth   # после шага 4; без весов — только --class-name person
uvicorn footmeasure.server:app --host 0.0.0.0 --port 8000
```

IP Mac'а в Wi-Fi: `ipconfig getifaddr en0`. В телефоне указать `http://<ip>:8000`.
Телефон и Mac — в одной Wi-Fi-сети.

### Шаг 2. Собрать и запустить приложение

```bash
brew install xcodegen
cd foot-measurement/ios && xcodegen generate
open FootCapture.xcodeproj
```

В Xcode: Signing & Capabilities → выбрать Team (бесплатный Apple ID подходит) → выбрать
iPhone → Run. При первом запуске разрешить камеру и локальную сеть.
Без XcodeGen: создать пустой проект *iOS App (SwiftUI)*, заменить его swift-файлы на
`ios/FootCapture/Sources/*.swift` и добавить в Info.plist ключи из `ios/FootCapture/Info.plist`
(камера, локальная сеть, `NSAllowsLocalNetworking`, `UIFileSharingEnabled`).

Ожидаемо: статус `ready: 1920x1440 @ 30 fps + sceneDepth`. Если `sceneDepth not supported` —
устройство без LiDAR.

### Шаг 3. Записать сессию и проверить данные (MVP-1)

Одна босая стопа на ровном полу, хорошее освещение, телефон **над стопой** (камера смотрит
вниз, ~40–60 см), стопа целиком в кадре. START → 5–10 с (авто-STOP через 10 с) → STOP.
Статус: `saved N frames → 20260909-101500`.

Перенести сессию на Mac (Finder → iPhone → Files → FootCapture → `sessions/<дата>/`,
или кнопка SEND — тогда она окажется в `python/sessions/<id>/` на сервере) и посмотреть:

```bash
footmeasure visualize sessions/<s> --step 15 --rotate
```

Ожидаемо в `out/<s>/frame_*.png`: RGB | depth | confidence, снизу RGB с depth-оверлеем —
контуры стопы в depth совпадают с RGB, depth в центре ≈ 0.4–0.6 м, `valid ≈ 100 %`.

### Шаг 4. Геометрия без нейросети — лист A4

Положить лист A4 на пол, записать сессию, найти на `frame_*.png` (без `--rotate`) пиксельные
координаты 4 углов листа, записать их в `corners.json`: `[[u1,v1],[u2,v2],[u3,v3],[u4,v4]]`.

```bash
footmeasure measure sessions/<a4> --frame 60 --mask-polygon corners.json --fixed-height-mm 0.2 --rotate
```

Ожидаемо: `Length ≈ 297`, `Width ≈ 210` (±2 мм). Если нет — проблема в калибровке/depth,
а не в нейросети; сюда же смотреть `plane_rms_mm` (< 3 мм для ровного пола).

### Шаг 5. Обучить RF-DETR-Seg на класс FOOT (Colab, ~1 час)

Инструкция: [`python/training/README.md`](python/training/README.md); скрипт:
[`python/training/train_foot_rfdetr.py`](https://github.com/GregoryDich/GregoryDich/blob/claude/foot-measurement-mvp-i7rynx/foot-measurement/python/training/train_foot_rfdetr.py).
Результат — `checkpoint_best_total.pth` и `classes.json` → положить в `python/weights/`.

### Шаг 6. Стадии MVP-2 … MVP-5 на реальной записи

| Стадия | Команда | Ожидаемо |
|---|---|---|
| MVP-2 RF-DETR | `footmeasure detect sessions/<s> --weights weights/checkpoint_best_total.pth --step 15 --rotate` | `detect_*.png`: зелёная маска покрывает стопу, `conf ≥ 0.5` |
| MVP-3 3D-точки | `footmeasure points sessions/<s> --weights … --frame N` | `points_N.ply` (открыть в MeshLab/CloudCompare): красная стопа над зелёным полом, `plane rms < 3 mm` |
| MVP-4 один кадр | `footmeasure measure sessions/<s> --weights … --frame N --rotate` | `measure_N.png` + `Length/Width` |
| MVP-5 медиана | `footmeasure process sessions/<s> --weights … --step 5 --rotate` | `result.json` (`length_mm`, `width_mm`, `valid_frames`, IQR), `debug.png` |

Пока модель не обучена, обёртку можно прогнать на COCO-весах:
`footmeasure detect sessions/<s> --class-name person` (маска включит голень — только smoke-test).

### Шаг 7. Полный цикл с телефона

Сервер запущен (шаг 1, с `FOOTMEASURE_WEIGHTS`) → START → STOP → SEND. На экране:

```
Length: 268.7 mm
Width:  101.4 mm
valid frames: 17
```

Debug-картинка: `http://<ip>:8000/sessions/<id>/debug.png`.

### Шаг 8. Эталонная проверка (раздел 24 ТЗ)

1. Измерить стопу линейкой: `reference_length`, `reference_width` (мм).
2. Снять 5 сессий (шаг 7 или вручную).
3. Заполнить `reference.csv` (пример: `reference.example.csv`), затем
   `python evaluate.py reference.csv --weights weights/checkpoint_best_total.pth` →
   таблица `system − reference` и `out/evaluation.json`.

Параметры, которые калибруются по этой таблице: `--height-fraction` (на какую долю
локальной высоты стопы поднимать контур; 0.5 по умолчанию), `--h-min-mm`, `--step`,
`--top-k`. Метод `--method depth` (чистые LiDAR-точки, разделы 12–17 ТЗ) оставлен как
кросс-проверка — он систематически занижает на несколько мм (эрозия маски + порог высоты
+ размытие depth на границе).

## Формат сессии

```
metadata.json
  video: {width, height, fps, codec}       кадры видео = frames[i] по индексу
  depth: {width: 256, height: 192}         depth.bin: float32 LE, метры, кадры подряд
  interface_orientation: "portrait"        сам кадр всегда в landscape-ориентации сенсора
  frames[i]: {index, t, timestamp, fx, fy, cx, cy, transform_row_major[16], exposure_duration}
```

Unprojection (ARKit): `x = (u−cx)·d/fx, y = −(v−cy)·d/fy, z = −d`; `transform` — camera→world.
Depth 256×192 выровнен с RGB 1920×1440 масштабом 7.5 (intrinsics пересчитываются по центрам пикселей).

## Ограничения MVP

Одна стопа, целиком в кадре, на ровном полу, стабильная камера, достаточный свет,
iPhone 16 Pro Max. Сырой LiDAR ~24×24 точки (ML-апсемплинг до 256×192) — поэтому граница
берётся из RGB, а не из depth. Снимать желательно сверху: при наклонном ракурсе силуэт
округлой стопы уже её отпечатка на несколько мм. Multi-frame point-cloud fusion —
заготовка `multiframe.fuse_clouds` (`--fuse`), числа пока объединяются медианой.
Swift-код написан без компиляции (нет Xcode в среде разработки) — ошибки сборки присылайте.
