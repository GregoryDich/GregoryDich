# Foot Measurement MVP — iPhone 16 Pro Max (RGB + LiDAR) → RF-DETR → длина и ширина стопы в мм

Минимальный прототип: телефон записывает RGB-видео + LiDAR-depth + калибровку камеры,
Python-сервис находит стопу с помощью **RF-DETR-Seg** (единственная нейросеть),
объединяет маску с LiDAR-геометрией и выдаёт:

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

## Состав

```
foot-measurement/
  ios/                 приложение FootCapture: [START] [STOP] [SEND] (SwiftUI + ARKit)
  python/              пакет footmeasure: CLI по стадиям + FastAPI-сервер + тесты
  python/training/     дообучение RF-DETR-Seg на класс foot (Colab)
  python/evaluate.py   сверка с ручным измерением (раздел «Эталонная проверка»)
```

## 1. Python (Mac, Apple Silicon)

```bash
cd foot-measurement/python
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'          # numpy, opencv, rfdetr (+torch), fastapi, uvicorn, pytest
pytest                            # синтетические тесты геометрии/пайплайна (без iPhone)
```

Сервер, к которому обращается кнопка SEND:

```bash
export FOOTMEASURE_WEIGHTS=weights/checkpoint_best_total.pth   # после обучения (см. ниже)
uvicorn footmeasure.server:app --host 0.0.0.0 --port 8000
```

IP Mac'а в Wi-Fi: `ipconfig getifaddr en0`. В телефоне укажите `http://<ip>:8000`.

## 2. iOS-приложение

```bash
brew install xcodegen
cd foot-measurement/ios && xcodegen generate
open FootCapture.xcodeproj
```

В Xcode: Signing & Capabilities → выбрать Team (бесплатный Apple ID подходит), запустить на
iPhone 16 Pro Max. Без XcodeGen: создать пустой проект *iOS App (SwiftUI)*, заменить его
swift-файлы на `ios/FootCapture/Sources/*.swift` и добавить в Info.plist ключи из
`ios/FootCapture/Info.plist` (камера, локальная сеть, `NSAllowsLocalNetworking`,
`UIFileSharingEnabled`).

Съёмка: одна босая стопа на ровном полу, хорошее освещение, телефон **над стопой**
(камера смотрит вниз, ~40–60 см), стопа целиком в кадре. START → 5–10 с (авто-STOP через
10 с) → STOP → SEND. Сессия также остаётся в Files / Finder (`Documents/sessions/<дата>/`):
`video.mov`, `depth.bin`, `confidence.bin`, `metadata.json` — её можно перенести на Mac
вручную и обработать CLI.

## 3. Стадии MVP — проверка на реальной записи

| Стадия | Команда | Что проверить |
|---|---|---|
| MVP-1 данные | `footmeasure visualize sessions/<s> --step 15 --rotate` | depth-оверлей совпадает с RGB (`out/<s>/frame_*.png`) |
| геометрия без нейросети | лист A4 на полу, `footmeasure measure sessions/<a4> --frame N --mask-polygon corners.json --fixed-height-mm 0.2` | ≈ 297 × 210 мм |
| MVP-2 RF-DETR | `footmeasure detect sessions/<s> --weights weights/checkpoint_best_total.pth --step 15 --rotate` | маска покрывает стопу, confidence |
| MVP-3 3D-точки | `footmeasure points sessions/<s> --weights … --frame N` | `points_N.ply` (красный — стопа, зелёный — пол), plane rms < 3 мм |
| MVP-4 один кадр | `footmeasure measure sessions/<s> --weights … --frame N --rotate` | `measure_N.png` + Length/Width |
| MVP-5 медиана | `footmeasure process sessions/<s> --weights … --step 5 --rotate` | `result.json`, `debug.png`, IQR по кадрам |

`corners.json` для A4 — 4 угла листа в пикселях **исходного (landscape) кадра**:
`[[u1,v1],[u2,v2],[u3,v3],[u4,v4]]` (координаты видны на `frame_*.png` без `--rotate`).

Пока foot-модель не обучена, обёртку можно прогнать на COCO-весах:
`footmeasure detect sessions/<s> --class-name person` (маска включает голень — только
smoke-test).

## 4. Обучение RF-DETR-Seg на класс FOOT

См. `python/training/README.md` (Colab T4, ~1 час). Результат — `checkpoint_best_total.pth`
и `classes.json` в `python/weights/`.

## 5. Эталонная проверка (раздел 24 ТЗ)

1. Измерить стопу линейкой: `reference_length`, `reference_width` (мм).
2. Снять 5 сессий (START/STOP/SEND или вручную).
3. `reference.csv` (пример: `reference.example.csv`), затем
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
