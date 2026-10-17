# scene_v2 — сборка сцены видео-задника (этап V2)

Строит из петли `aquarium/assets/reef_day.mp4` всё, что лежит в `aquarium/scene/` для видео-сцены:
маски-окклюдеры колонн `mask_left.png`, `mask_right.png`, `mask_far.png`, маску каустики
`light_mask_video.png` и `scene.js` (видео-сцена + прежняя фото-сцена как `AQUARIUM_SCENE_PHOTO`).
В репозиторий кладутся только итоговые файлы; кадры, промежуточные массивы и превью — в рабочей папке.

Всё — `python3.13 -I` (PIL, numpy, scipy, scikit-image, onnxruntime), запуск из РАБОЧЕЙ папки с подпапками
`frames/ out/ final/ tpl/ prev/ evidence/` (скрипты пишут туда относительные пути):

```sh
S=/home/user/GregoryDich/tools/aquarium-test/scene_v2
mkdir -p frames out final tpl prev evidence && cp $S/tpl/* tpl/
git -C /home/user/GregoryDich show 978d7af:aquarium/scene/scene.js > tpl/scene_photo_orig.js   # фото-сцена до V2
V=/home/user/GregoryDich/aquarium/assets/reef_day.mp4
ffmpeg -i $V -vf "select='not(mod(n\,10))',scale=1280:720:flags=area" -vsync 0 -pix_fmt rgb24 frames/d720_%03d.png
ffmpeg -i $V -vf "select='not(mod(n\,40))'" -vsync 0 -pix_fmt rgb24 frames/dfull_%02d.png      # 15 кадров — сборка масок
ffmpeg -i $V -vf "select='eq(mod(n\,40)\,20)'" -vsync 0 -pix_fmt rgb24 frames/dhold_%02d.png   # 15 других — проверка
python3.13 -I $S/tstats.py            # медиана 720p, разброс по петле
python3.13 -I $S/median_full.py       # медиана 2560×1440 (рыбы и «снег» уходят)
python3.13 -I $S/depth.py models/da_vits14.onnx   # относительная глубина (Depth Anything ViT-S, ONNX)
python3.13 -I $S/water.py             # гладкая модель цвета воды (полином 4-й степени) + вода/не вода
python3.13 -I $S/regions.py           # глубина в 720p (+ контуры для просмотра)
python3.13 -I $S/labels720.py         # метки: вода / левая колонна / правая / дальний риф / дно каньона
python3.13 -I $S/alpha_full.py        # матирование «вода ↔ риф» (проекция на F − B) по 16 кадрам, минимум по времени
python3.13 -I $S/assemble.py          # маски окклюдеров (кромка 1–2 px, просветы кружева, без швов между масками)
python3.13 -I $S/validate_temporal.py # проверка на 15 ДРУГИХ кадрах: маска поверх воды (ghost) ≤ 4 px
python3.13 -I $S/write_masks.py && python3.13 -I $S/mask_meta.py   # PNG серый+альфа, рамки, профили, сетки 32×32
python3.13 -I $S/geom.py              # depthGrid 48×27, линия дна, маска каустики 640×360
python3.13 -I $S/gen_scene.py tpl/scene.js   # шаблон + tpl/placements.py (передний риф, реквизит, точки, дорожки, пузырьки)
node $S/dump_scene.js tpl/scene.js /home/user/GregoryDich/aquarium/scene/corals/catalog.js > tpl/scene.json
python3.13 -I $S/check_z.py tpl/scene.json      # точки/дорожки/пузырьки перед поверхностью рифа; спрятанные — в маске
python3.13 -I $S/footprint.py tpl/scene.json    # глубина рифа под каждой колонией (z колонии < поверхности)
python3.13 -I $S/preview.py tpl/scene.json prev/p 1.54,1.6,1.78,2.33 day,night [--debug]   # превью = bgMap движка
python3.13 -I $S/demo_hide.py tpl/scene.json evidence/hide day   # рыбы за кромками колонн / дальним рифом / в кроне
```

Скопировать в `aquarium/scene/`: `final/mask_*.png`, `out/light_mask_video.png` (как `light_mask_video.png`),
`tpl/scene.js` (как `scene.js`). Гейт: `node ../gates_v2.js` (из `tools/aquarium-test`).

Ручная часть — `tpl/placements.py` (передний риф, реквизит, точки поведения, дорожки, пузырьки, линия дна) и
константы камеры/тем в `tpl/scene_video_tpl.js`. Глубина колонн: z = 1/(0.0334·d + 0.385) от относительной
диспаратности d модели; дно — плоскость камеры (horizonBy 0.58, floorBy 1.243).
