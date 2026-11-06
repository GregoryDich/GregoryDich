# Карты страниц сайта — дорожная карта

Карта страницы — машиночитаемое описание того, что где на странице на каждом экране (`<slug>.json`) и рабочая заметка по ней (`<slug>.md`):
экраны и диапазоны прокрутки, прогоны и их длина, позиции истории p, рамка продукта через каждые 10 px, картинки, тексты, флаги проверок.
Строит её `site/proto/qa/pagemap.cjs` (three.js без рисования: секунды на экран вместо часов рендера) после каждой сборки страницы;
проверки правил заказчика идут по числам, картинки — только там, где числа нашли подозрение (`--spot`), и финальный взгляд на 4 экрана.
Ссылки страниц — `site/HANDOFF-dev.he.md` и `HANDOFF-session.md`.

| страница | slug | ссылка | последняя сборка | последняя проверка | флаги | открытые вопросы |
|---|---|---|---|---|---|---|
| V-TECH SYSTEM | `v-tech-system` | https://claude.ai/artifact/NdQezU5bikrsuaWVVW5TBK | — | карта ещё не построена | — | размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| EXOCELL MASK | `exocell-mask` | https://claude.ai/artifact/FA5ySxGihnDAmjQPvDftzn | — | карта ещё не построена | — | кадр зеркала MASK ≥ 1196 px; размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| EXOTECH GEL | `exotech-gel` | https://claude.ai/artifact/LsJVky9GDssBuW1eQkLaTe | — | карта ещё не построена | — | цвет геля; размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| EXOSIGNAL HAIR | `exosignal-hair` | https://claude.ai/artifact/2ws7qr1xL7Y7wp5xdbE1jh | — | карта ещё не построена | — | размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| EXOSIGNAL SPRAY | `exosignal-spray` | https://claude.ai/artifact/GAUwhjxzqdk7jEg7JgSBJz | — | карта ещё не построена | — | пакшот SPRAY; размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| EXO-NAD | `exo-nad` | https://claude.ai/artifact/NcP4v3p7KAdvqZGTnoGK8S | — | карта ещё не построена | — | фото EXO-NAD в полном размере; размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| MICRO BOOST 10% | `micro-boost-10` | https://claude.ai/artifact/3hwRLR8RxjcQV2oGTynari | — | карта ещё не построена | — | размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| CELLULAR AGE DEFENSE 2.5% | `cellular-age-defense-2-5` | https://claude.ai/artifact/RhFJsLyLDinq2HcizL1hvq | — | карта ещё не построена | — | размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| MITOPEN | `mitopen` | https://claude.ai/artifact/KAn13gS9E2on2ZikQSz4eW | — | карта ещё не построена | — | данные MITOPEN; размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| CELL RENEW 1.5% | `cell-renew-1-5` | https://claude.ai/artifact/2rVvsAFJ9NRUjymZDmANup | — | карта ещё не построена | — | «ок» телефонного образца (T1); размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| MITOSCAN | `mitoscan` | https://claude.ai/artifact/KD3L1gfgVA8twY7HBvYofp | — | карта ещё не построена | — | данные MITOSCAN; размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| DERMA RECOVERY CREAM | `derma-recovery-cream` | https://claude.ai/artifact/7a3EpTpcTbYMWjTypNk2pV | — | карта ещё не построена | — | банка DERMA в HD; размеры коробки в мм; см. `HANDOFF-session.md` «Ждёт заказчика» |
| MITOTECH CELL BOOSTER | `mitotech-cell-booster` | https://claude.ai/artifact/G3tdcwusRsVdw4E5HeGM5s | md5 `4bd6d1d4` | 06.11.2026, 20:44, 15 режимов за 118.8 с | RUN_SPAN 4, HD 10, TWO_PRODUCTS 12 (`mitotech-cell-booster.md`) | `state/mitotech/texts-for-approval.md` §6: цвет раствора, аппликаторы в наборе, заголовок оффера, янтарь — стекло или жидкость; бейдж линейки |
