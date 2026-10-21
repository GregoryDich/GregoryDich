# art/ — офлайн-доводка ассетов (этап V5)

Скрипты меняют PNG в `aquarium/` детерминированно (python3.13 + numpy/scipy/PIL; запуск с `-I`). Исходники
до доводки — в истории git (коммит `7716297`), поэтому повторный прогон делается от них:

```sh
git show 7716297:aquarium/scene/props/tube_sponges.png > /tmp/ts.png
python3.13 -I tools/aquarium-test/art/sponge_retouch.py /tmp/ts.png aquarium/scene/props/tube_sponges.png
git show 7716297:aquarium/fish/goldfish.png > /tmp/gf.png
python3.13 -I tools/aquarium-test/art/goldfish_alpha.py /tmp/gf.png aquarium/fish/goldfish.png
python3.13 -I tools/aquarium-test/art/crown_cut.py aquarium/scene/props/anemone.png aquarium/scene/props/anemone_front_crown.png
# R2c: производные от НЕизменных исходников в aquarium/ (повторный прогон даёт те же PNG)
python3.13 -I tools/aquarium-test/art/r2c_assets.py aquarium
```

| Скрипт | Что делает |
|---|---|
| `sponge_retouch.py` | жёлтые трубчатые губки: из «пластикового» лайма с зелёной каймой → охристо-жёлтые (тон ≈ 47°, насыщенность ≤ 0.5), свет сверху, тёмное основание, деспилл каймы, эрозия альфы 1 px |
| `goldfish_alpha.py` | вуаль оранды: полупрозрачный хвост/плавники (α ≈ 158) → почти непрозрачные (247), растушёвка только внешних ~4 px — без «швов» на перекрытиях срезов |
| `r2c_assets.py` | R2c: `scene/props/starfish_floor.png` — звезда «лёжа» из `starfish.png` (сжатие по вертикали до 0.56, дальний край уже на 8%, перспектива по премультиплицированной альфе); `scene/corals/tube_sponges_yellow.png` — жёлтые трубчатые губки: перекраска `tube_sponges_lilac.png` по яркости рампой охра → жёлтый → сливочный, альфа та же. Исходники не меняются (их берут фото-сцена и каталог) |
| `crown_cut.py` | передний венец актинии `anemone_front_crown.png` (щупальца ниже линии диска в эллипсе 0.42 × 0.17 вокруг гнезда, без яркого центра, α × 0.85; R2c-2: БЕЗ ножки под диском — венец рисуется на z − 0.03 перед низкой акропорой, и ножка в нём висела бурой трапецией); печатает `crownBox` и `crownGrid` для scene.js |

Сетки занятости колоний (`box`, `grid` в `scene.corals`) — `scene_v2/coral_grids.py aquarium --write` (после смены PNG,
`flip` или добавления колонии).
