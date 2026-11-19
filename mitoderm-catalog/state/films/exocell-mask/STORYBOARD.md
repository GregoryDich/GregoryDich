# EXOCELL MASK: раскадровка фильма страницы /products/exocell-mask

19/11/2026. Машиночитаемая копия — `storyboard.json` в этой же папке. По раскадровке ничего не сгенерировано. Отдельно от неё
кадр упаковки K0 уже снимается (`PROGRESS.md`, таблица медиа: первый вариант K0/K0v отклонён из-за мелкого текста,
повторы запущены 19/11 23:02); правки ревью 19/11 K0 не касаются. Бриф серии — `state/films/SERIES-BRIEF.md`; образец строения — `state/nad-film/STORYBOARD-v1.md` и
раскадровка `state/films/micro-boost-10/storyboard.json`. Факты о средстве — из аудита
`state/films/audit/audits-19-11.json` (запись `exocell-mask`), `codex-site/mitoderm/content.json` (products[2]),
`protocols/src/content.he.mjs` (id `exocell-mask`), `site/packaging-text.md`, `state/scenarios-v3/research/r4-facts.md`.

`<scratch>` = `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad` (временная папка:
листы персонажей и кадры V-TECH; если её очистили — достать заново, см. `PROGRESS.md`).

## 0. Главное коротко

1. **4 ролика, 152 кредита** (4 кадра × 2 формата × 2.75 + 4 ролика × 2 формата × 16.25 = 22 + 130). Фильм 666 кадров
   = 27.75 с при 24 к/с, 8 глав — столько же, сколько сцен у страницы в `REGISTRY.json`.
2. **Порядок сцен — по протоколу.** Протокол (`protocols/src/content.he.mjs`): наложить маску равномерно на зону
   процедуры → оставить (до 30 минут) → снять и мягко «הספיג» остатки сыворотки; затем DERMA RECOVERY CREAM и SPF
   (content.json, раздел 6: «1 · הנחת המסכה · 2 · ספיגה · 3 · סיום»). Фильм: упаковка → консультация → наложение и
   разглаживание → покой (впитывание) → маска снята, остатки сыворотки похлопываются → упаковка (первый ролик задом
   наперёд). Процедуру до маски, дозы и время на экран не выводим.
3. **Коробка всё время закрыта, саше в фильме нет.** Фото или точной модели открытой коробки, разорванного саше и
   маски, вынутой из саше, нет (аудит, `packAssets.missingFaces`; 3D-шаблон — с выдуманными сторонами). Маска
   появляется сразу на лице через склейку. Видны только лицевая и левая боковая стороны коробки — по пакшоту
   `protocols/print/img/exocell-mask.webp`.
4. **Устройство маски не согласовано** (аудит: «пока заказчик не скажет, как правильно, раскадровку снимать нельзя»):
   вариант (а) PAGE.md/REGISTRY — снять два вспомогательных слоя и положить только белую; вариант (б) content.json,
   packaging-text.md — белый и синий слои кладутся один за другим. **По умолчанию** показан вариант (а): на лице
   один молочно-белый полупрозрачный слой, как на пакшоте, без синего слоя и без отделения подложек. При (б) K2, C и
   стоп-кадр главы 05 переписываются: по content.json (разделы index 5 и 7, «שמניחים בזו אחר זו») синий слой ложится
   вторым, поверх белого, и в главе 05 на лице был бы виден он. Кадры K2, K3 и ролики C, D **ждут ответа** заказчика; K0, K1, A, B от ответа не зависят и
   снимаются сразу.
   **Решение 19/11 (после перепроверки): ответа не ждём.** Заказчик запретил останавливать работу вопросами, а вид
   маски на лице подтверждён его же фотографиями применения от 10/10 (`PLAN.md`, раздел про EXOCELL: «руки в перчатках
   снимают голубую защитную плёнку; маска на лице молочно-прозрачная»). В фильме на лице — одна молочно-прозрачная
   маска; голубой слой, подложки и момент наложения из саше не показываем. K2, K3, C и D снимаются по этому варианту;
   вопрос записан в `QUESTIONS.md` с этим вариантом по умолчанию.
5. Тексты глав — только из content.json (и одна связка «מסירים את המסכה;» из `site/product-pages.he.json`); они
   заменяют нынешний шаблон `sceneryCopy()` и заголовки про «снятие слоёв».

## 1. Общие правила для всех кадров

- **Люди (бриф, утверждённые листы):** косметолог **M** — женщина около 30, длинные тёмные волнистые волосы, белая
  форма с розовым кантом, кулон с синим камнем на чёрном шнурке (`<scratch>/cast/main-photo.jpg`,
  `<scratch>/cast/main-turnaround.jpg`; медиа Higgsfield 90121c86-…, 182a0e01-…). Пациентка **P7** — 25–30, длинные
  каштановые волосы, чёрная повязка (`<scratch>/cast/p7-turnaround.jpg`; медиа Higgsfield 387b9773-…, `PROGRESS.md`). Других людей в кадрах нет.
- **Место:** светлый кабинет, как в фильмах V-TECH и EXO-NAD (`<scratch>/nad/refs/vtech/f080.png`, `f121.png`):
  большое окно, мягкий дневной свет, тёплые белые стены, белое кресло, светлый мраморный столик. Перчатки белые.
- **Кожа P7** спокойная, без покраснения, одинаковая во всех кадрах; никакого «после», сияния и сглаживания.
- **Композиция 16:9** (страница справа налево): правые 35 % кадра — без лиц, рук и упаковки (там подпись), нижние
  15 % — без важного (там шаги). **Композиция 9:16:** лица и упаковка — между 13 % и 62 % высоты сверху; верхние 13 %
  без лиц (шапка сайта); нижние 38 % — стол, одежда, полотенце (там тёмная полоса с подписью). Кадры 9:16 —
  отдельные генерации, не обрезка. Каждое правило вписано в промпт явно.
- **Никакого текста в кадре**, кроме печати на самой коробке. Все надписи — HTML поверх ролика.
- Модель кадров `gpt_image_2_6`, 2K, high (2.75); ролики `kling4_0`, image-to-video, 1080p, 5 с (16.25), по одному
  дублю на формат. **Опор не больше 5 на кадр** (в EXO-NAD 2–5); порядок приложения — список «Опоры» у кадра.
  В промпте опоры называются по тому, что на них («the attached K1», «the attached packshot»), как в EXO-NAD.
- **Уже загружено в Higgsfield** (`PROGRESS.md`): M фото 90121c86-…, M лист 182a0e01-…, P7 лист 387b9773-…, пакшот
  `exocell-mask.webp` 61ca8e69-…, коробка спереди `exocell-box-front.jpg` a5346a0d-…. Не загружена только
  `exocell-box-side.jpg` (нужна лишь K0).

## 2. Упаковка: что прикладывать и что показывать

**Прикладывать к кадрам с коробкой** (K0 — все три; K1 16:9 — пакшот и лицевую сторону, K1 9:16 — пакшот; к K2 — только
пакшот как образец формы маски, с припиской «ignore the box in it»; к K3 — ничего):
- `/home/user/GregoryDich/mitoderm-catalog/protocols/print/img/exocell-mask.webp`
- `/home/user/GregoryDich/mitoderm-catalog/site/img/exocell-box-front.jpg`
- `/home/user/GregoryDich/mitoderm-catalog/site/img/exocell-box-side.jpg`

protocols/print/img/exocell-mask.webp (1196x956) — настоящий пакшот: лицевая сторона и левая боковая сторона коробки под углом и маска рядом (форма маски: вырезы глаз, носа с клапаном, рта, прорезь у нижнего края). exocell-box-front.jpg (740x1000) и exocell-box-side.jpg (150x1000) — те же стороны, вырезанные из пакшота и выпрямленные, для сверки мелкого текста. Текст на коробке сверен с site/packaging-text.md.

Что видно на пакшоте (сверено глазами): вертикальная плоская коробка матового приглушённо-бирюзового цвета, печать
тёмно-синяя: вверху монограмма VM и «VM corporation», в центре «EXOCELL» («EXO» жирно, «CELL» тонко) и «M A S K»
вразрядку, ниже светлым курсивом «Your Second Skin / For Exo Bio-Regeneration», мелкий блок на четырёх языках и
«5 face masks … / Net 5 x 25 ml ℮ 5 x 0.84 fl.oz». Левая боковая сторона — серые вертикальные «EXOCELL / MASK».
Маска рядом: молочно-белая с лёгким бирюзовым оттенком, полупрозрачная, вырезы глаз, носа с клапаном, рта,
прорезь у нижнего края справа.

**Видимые стороны:** только лицевая и узкая левая (коробка повёрнута примерно на 20°, как на пакшоте).

**Не показывать никогда:**
- правую боковую сторону коробки (фото нет; в 3D-шаблоне это зеркальная копия левой);
- заднюю сторону, верхний клапан и дно коробки;
- открытую коробку, внутренний лоток и то, как уложены 5 саше (ни фото, ни модели);
- саше вообще (есть только плоская печать лицевой стороны `site/img/exocell-sachet-front.jpg`; оборота и разорванного саше нет);
- маску, вынимаемую из саше или расправляемую в руках (фото нет);
- синий слой, второй слой и подложки маски (устройство не согласовано, см. раздел 9).

**Не прикладывать:**
- `/home/user/GregoryDich/mitoderm-catalog/codex-site/public/assets/products/exocell-mask.webp` — 428×331, мыльная, в кадре край золотой банки другого средства
- `/home/user/GregoryDich/mitoderm-catalog/site/design/exocell-3d/kit-hd.png` — рендер: правая сторона — зеркальная копия левой; саше подталкивают к показу содержимого
- `/home/user/GregoryDich/mitoderm-catalog/site/design/exocell-3d/mask-layers.png` — рендер с синим слоем, устройство маски не согласовано
- `/home/user/GregoryDich/mitoderm-catalog/site/design/exocell-3d/d2-open.jpg, d3-maskout.jpg, d5-burst.jpg` — рендеры открытой коробки и саше: геометрия придумана
- `/home/user/GregoryDich/mitoderm-catalog/sources/exocell-box-v2-front.png` — светлая версия коробки; какая в продаже — открытый вопрос
- `/home/user/GregoryDich/mitoderm-catalog/sources/exocell-wow-effect-he.webp` — листовка, на ней третья версия коробки «The Ultimate Beauty Ritual»

## 3. Сцены и тексты глав (24 к/с, 666 кадров = 27.75 с)

| Глава | Кадры | Что на экране | Чем закрыта | Стык на входе |
|---|---|---|---|---|
| 01 | 0–108 | закрытая коробка крупно на мраморном столике, M и P7 размыты позади; камера медленно отъезжает | 0–24: hold_k0 (A frame 0); 24–108: A frames 1-84 | — |
| 02 | 108–204 | консультация: M внимательно смотрит на щёку P7, P7 слушает; коробка на столике | 108–144: A frames 85-120; 144–204: B frames 0-59 (cut in) | A→B склейка |
| 03 | 204–264 | консультация продолжается (M выпрямляется, кивает), коробка в кадре | 204–264: B frames 60-119 | без стыка (тот же ролик B) |
| 04 | 264–348 | маска уже лежит на лице P7; M разглаживает её ладонями от центра к краям | 264–348: C frames 0-83 (cut in) | склейка B→C |
| 05 | 348–420 | руки уходят, P7 спокойно лежит с маской — впитывание; стоп-кадр | 348–385: C frames 84-120; 385–420: hold_c_end (C frame 120) | без стыка |
| 06 | 420–528 | маска снята (за склейкой); M лёгкими похлопываниями вбивает остатки сыворотки, P7 открывает глаза | 420–528: D frames 0-107 (cut in) | склейка C→D (маска снята за склейкой) |
| 07 | 528–594 | наплыв в общий план, камера медленно возвращается к коробке (A задом наперёд) | 528–534: join: D frames 108-113 dissolve into A frame 120 (6-frame DIS); 534–594: A reversed frames 120->61 | наплыв 6 кадров D→A |
| 08 | 594–666 | коробка крупно, последний кадр = первый кадр фильма | 594–654: A reversed frames 60->1; 654–666: hold_k0_end (A frame 0) | без стыка |

Последний кадр фильма = первый (K0). Стоп-кадры, разворот и наплыв делает сборка, кредитов не стоят.

**Запись для `codex-site/mitoderm/pilot/product-films.ts` (когда фильм будет собран; сейчас код не трогали):**

```ts
 'exocell-mask':{desktop:'/assets/world/exocell-mask-film.mp4',mobile:'/assets/world/exocell-mask-film-mobile.mp4',fps:24,frames:666,chapters:[
  {start:0,end:108},   // 01 pack
  {start:108,end:204},   // 02 consultation
  {start:204,end:264},   // 03 what the sheet holds
  {start:264,end:348},   // 04 placing the mask
  {start:348,end:420},   // 05 absorption
  {start:420,end:528},   // 06 finish
  {start:528,end:594},   // 07 kit
  {start:594,end:666}   // 08 offer
 ]}
```

### Тексты глав (вместо шаблона `sceneryCopy()` и нынешних `scriptTitles['exocell-mask']`)

Заголовок + одна строка. Латиница в иврите — в `<bdi dir="ltr">` (EXOCELL MASK, DERMA RECOVERY CREAM, Q10, «5 × 25»).
Заголовок главы 01 остаётся латинским (H1 с `dir="ltr"`).

| Глава | Заголовок (he) | Строка (he) | Источник |
|---|---|---|---|
| 01 | EXOCELL MASK | השלב המסכם והמרגיע לאחר טיפולים מקצועיים. | content.json products[2].intro.body (дословный отрезок после тире) |
| 02 | רוגע לאחר הפרוצדורה | העור זקוק ללחות ולתמיכה במחסום האפידרמלי. | content.json products[2].sections index 2: title + дословный отрезок body |
| 03 | מה מכילה היריעה | מבנים אקסוזומליים סינתטיים, פולינוקלאוטידים, חומצה היאלורונית ו-Q10. | content.json products[2].sections index 3: title + body до тире (сокращено, без новых слов) |
| 04 | 1 · הנחת המסכה | על עור נקי לאחר הפרוצדורה – כמעט ללא כיסי אוויר. | content.json sections index 6: tag «1 · הנחת המסכה», начало body «על עור נקי לאחר הפרוצדורה», tag «כמעט ללא כיסי אוויר» |
| 05 | 2 · ספיגה | מגע לח ורציף עם הסרום. | content.json sections index 6: tag «2 · ספיגה» + фрагмент body «מגע לח ורציף עם הסרום» |
| 06 | 3 · סיום | מסירים את המסכה; בסיום: DERMA RECOVERY CREAM והגנה מהשמש. | content.json sections index 6: tag «3 · סיום» + конец body «בסיום: DERMA RECOVERY CREAM והגנה מהשמש.»; «מסירים את המסכה;» — site/product-pages.he.json (шаг «סיום»), то же в протоколе protocols/src/content.he.mjs «יש להסיר את המסכה» |
| 07 | 5 מסכות, אריזה אחת | מסכות ביו־צלולוז חד־פעמיות עם סרום פעיל · תכולה נטו 5 × 25 מ״ל. | content.json sections index 5 title; sections index 7 tags «מסכות ביו־צלולוז חד־פעמיות עם סרום פעיל.» и «תכולה נטו 5 × 25 מ״ל» |
| 08 | הכניסו את EXOCELL MASK לקליניקה שלכם | לשימוש מקצועי בלבד. | content.json sections index 7: title + body (дословно) |

Подпись для кнопок шагов (aria-label, вместо «MITODERM · לשימוש מקצועי»): 01 EXOCELL MASK · 02 ייעוץ · 03 היריעה · 04 הנחת המסכה · 05 ספיגה · 06 סיום · 07 ערכה · 08 הצעה. Слова взяты из надзаголовков и заголовков content.json («ערכה ועובדות», «הצעה», «מה מכילה היריעה», шаги протокола) и из меню сайта («ייעוץ והצעה»).

**Проверка языка.** Обращение — как везде на странице, во множественном числе без рода («מסירים», «הכניסו … שלכם»).
Согласование: «העור זקוק» (м. р.), «השלב המסכם והמרגיע» (м. р.), «מגע לח ורציף» (м. р.),
«מסכות … חד־פעמיות» (ж. р. мн. ч.), «הנחת המסכה» (смихут). Новых утверждений о действии нет: строки вырезаны из
content.json без добавленных слов, кроме связки «מסירים את המסכה;» из утверждённого шага «סיום» в
`site/product-pages.he.json` (тот же шаг в протоколе: «יש להסיר את המסכה»). Слова «מערכת» нет. Из обещаний
content.json («חלק, גמיש וזוהר») в подписи ничего не взято. Время «עד 30 דקות» на экран не идёт.
Строки 01 и 02 сокращены до дословных отрезков (были около 95 и 80 знаков); «ביו־צלולוז» остался только в главе 07, с
макафом, как в content.json (раздел index 7). Направление и перенос строк проверить на странице на 1440×900 и 390×664
после вставки (здесь не проверялось).

## 4. Кадры (каждый в 16:9 и в 9:16)

Порядок съёмки — раздел 8. Общие хвосты (композиция формата + запреты) уже вписаны в каждый промпт.

### K0 — Кадр упаковки (первым, ссылка заказчику). Сцена 01 и последний кадр фильма; старт ролика A.
- **Композиция:** Камера низко, на высоте столика. Закрытая коробка резко на переднем плане: в 16:9 — на 25–55 % ширины, верх ~15 %, низ выше нижних 15 %; в 9:16 — по центру, от ~18 % до ~60 % высоты. M (слева) и P7 (в кресле) позади размыты, ни одного резкого лица. Правые 35 % в 16:9 — окно и стена. Лица впервые появляются в K1; здесь они только размытые силуэты, поэтому кадр упаковки идёт первым, не дожидаясь утверждения P7.
- **Упаковка в кадре:** закрытая коробка, лицевая и узкая левая сторона, резко. Прикладывать: `/home/user/GregoryDich/mitoderm-catalog/protocols/print/img/exocell-mask.webp` (главный), `/home/user/GregoryDich/mitoderm-catalog/site/img/exocell-box-front.jpg`, `/home/user/GregoryDich/mitoderm-catalog/site/img/exocell-box-side.jpg`.
- **Опоры:**
  - M: `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/main-photo.jpg (Higgsfield media 90121c86-7093-44bb-a03d-ebc0648e392c)`; `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/main-turnaround.jpg (Higgsfield media 182a0e01-b7ac-48e9-b01f-2815d8862009)`
  - P7: `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/p7-turnaround.jpg (Higgsfield media 387b9773-c5a5-4fe3-bb19-7399c9998925)`
  - кабинет: `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/nad/refs/vtech/f080.png`; `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/nad/refs/vtech/f121.png`
  - упаковка: `/home/user/GregoryDich/mitoderm-catalog/protocols/print/img/exocell-mask.webp`; `/home/user/GregoryDich/mitoderm-catalog/site/img/exocell-box-front.jpg`; `/home/user/GregoryDich/mitoderm-catalog/site/img/exocell-box-side.jpg`
- **Промпт 16:9:**

  `Low camera at the height of the light marble side table, 50mm, f/2, in a bright, clean treatment room as in the attached V-TECH frames: soft natural daylight from a large window, warm white walls, white treatment chair, light marble side table. In the sharp foreground stands the closed EXOCELL MASK box exactly as in the attached pack reference (exocell-mask.webp packshot, with the flat front scan exocell-box-front.jpg and the left-side scan exocell-box-side.jpg for checking small print): a flat portrait-format matte muted-teal carton (#5ca0a5) with dark navy print, shallow in depth; FRONT face visible with the VM monogram and small 'VM corporation' at the top, 'EXOCELL' in wide-spaced capitals ('EXO' bold, 'CELL' thin) with letter-spaced 'M A S K' below, the light italic pale-aqua lines 'Your Second Skin' / 'For Exo Bio-Regeneration', the small four-language block and '5 face masks' / 'Net 5 x 25 ml' at the bottom (lines too small to read render as fine grey lines, never as invented words); the narrow LEFT side panel visible at an angle on the left, with 'EXOCELL' / 'MASK' running vertically in grey. The box stands upright and closed, turned about 20 degrees exactly as in the packshot so that only the front and the left side show; never show its right side, back, top or bottom; never open it. The sheet mask that stands next to the box in the packshot is NOT on the table, and there is no sachet. The box stands at about 25-55% of the frame width, its top at about 15% and its base above the bottom 15% of the frame height. Behind it, softly out of focus and unrecognisable in detail, the cosmetologist M (the brand's main face: a woman about 30 with long dark wavy hair, a white uniform with pink piping and a pendant with a blue stone on a black cord, identical to the attached M reference photos), in clean white examination gloves, stands on the left (about 10-25% of the width) and the patient P7 (a woman 25-30 with long chestnut hair held back by a black headband, identical to the attached P7 character sheet; natural calm young skin with real texture) sits in the white treatment chair at about 40-60% of the width; their faces are blurred soft shapes, no face is sharp. Right 35% of the frame: only the softly lit window and wall. 16:9 horizontal film still, framed for 1920x1080. COMPOSITION RULE FOR 16:9 (desktop, right-to-left page): the right 35% of the frame contains no faces, no hands and no packaging, only calm softly lit wall and window background, because the Hebrew caption sits there; the bottom 15% contains nothing important, because the step markers sit there. Photorealistic, true colours, real skin texture with pores, fine grain. No added text, captions, logos or watermarks beyond the box's own print; no invented packaging; no opened box, no sachet; no needle, syringe or device; no skin smoothing or glow; no redness appearing or disappearing; no before/after look; no extra fingers; no duplicate people.`

- **Промпт 9:16:**

  `Low camera at the height of the light marble side table, 50mm, f/2, in a bright, clean treatment room as in the attached V-TECH frames: soft natural daylight from a large window, warm white walls, white treatment chair, light marble side table. In the sharp foreground, centred, stands the closed EXOCELL MASK box exactly as in the attached pack reference (exocell-mask.webp packshot, with the flat front scan exocell-box-front.jpg and the left-side scan exocell-box-side.jpg for checking small print): a flat portrait-format matte muted-teal carton (#5ca0a5) with dark navy print, shallow in depth; FRONT face visible with the VM monogram and small 'VM corporation' at the top, 'EXOCELL' in wide-spaced capitals ('EXO' bold, 'CELL' thin) with letter-spaced 'M A S K' below, the light italic pale-aqua lines 'Your Second Skin' / 'For Exo Bio-Regeneration', the small four-language block and '5 face masks' / 'Net 5 x 25 ml' at the bottom (lines too small to read render as fine grey lines, never as invented words); the narrow LEFT side panel visible at an angle on the left, with 'EXOCELL' / 'MASK' running vertically in grey. The box stands upright and closed, turned about 20 degrees exactly as in the packshot so that only the front and the left side show; never show its right side, back, top or bottom; never open it. The sheet mask that stands next to the box in the packshot is NOT on the table, and there is no sachet. Its top sits at about 18% and its base at about 60% of the frame height. Behind it, softly out of focus, the cosmetologist M (the brand's main face: a woman about 30 with long dark wavy hair, a white uniform with pink piping and a pendant with a blue stone on a black cord, identical to the attached M reference photos) on the left in clean white examination gloves and the patient P7 (a woman 25-30 with long chestnut hair held back by a black headband, identical to the attached P7 character sheet; natural calm young skin with real texture) on the right, their blurred faces at about 18-32% of the frame height beside the box, no face sharp. Below 62%: only the marble table top. 9:16 vertical film still, framed natively for 1080x1920 (composed for a phone, not a crop of a horizontal frame). COMPOSITION RULE FOR 9:16 (phone): every face and the packaging sit between 13% and 62% of the frame height measured from the top; the top 13% (under the site header) shows no face; the bottom 38% shows only table surface, clothing or neutral background with nothing important, because a dark caption band sits there. Photorealistic, true colours, real skin texture with pores, fine grain. No added text, captions, logos or watermarks beyond the box's own print; no invented packaging; no opened box, no sachet; no needle, syringe or device; no skin smoothing or glow; no redness appearing or disappearing; no before/after look; no extra fingers; no duplicate people.`

### K1 — Первый кадр с людьми (образец: M и P7 впервые вместе, ждать «ок»). Сцены 02-03, старт ролика B.
- **Композиция:** Средний план на двоих. Камера на уровне глаз сидящего, объектив на высоте верхнего края коробки: верхняя грань коробки не видна (фото верха нет). 16:9: M на 15–35 % ширины, P7 в кресле на 38–60 %, коробка на столике слева внизу (18–32 %), лицом слегка к правому краю кадра, чтобы к камере была обращена левая сторона, а правая скрыта; правые 35 % пустые. 9:16: лица на 18–38 % высоты, коробка между ними на 42–60 %, ниже — стол и одежда.
- **Упаковка в кадре:** закрытая коробка на столике, лицевая и левая сторона, меньше, резко. Прикладывать: 16:9 — пакшот и `exocell-box-front.jpg`; 9:16 — пакшот (мелкий текст держит приложенный K0v).
- **Опоры (по порядку, не больше 5):**
  - 16:9: 1) K0 (утверждён: комната, столик, свет, место коробки); 2) M `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/main-photo.jpg` (медиа 90121c86-…); 3) P7 `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/p7-turnaround.jpg` (медиа 387b9773-…); 4) пакшот `/home/user/GregoryDich/mitoderm-catalog/protocols/print/img/exocell-mask.webp` (медиа 61ca8e69-…); 5) `/home/user/GregoryDich/mitoderm-catalog/site/img/exocell-box-front.jpg` (медиа a5346a0d-…).
  - 9:16: 1) K0 vertical; 2) K1 16:9 (утверждён: лица); 3) M; 4) P7; 5) пакшот.
- **Промпт 16:9:**

  `Medium two-shot, 50mm, camera at seated eye level, the lens height level with the top edge of the box on the side table so its top face is not visible, in the same bright, clean treatment room as the attached K0: soft natural daylight from a large window, warm white walls, white treatment chair, light marble side table; same room, table, box placement and light as K0. Left of centre, at about 15-35% of the frame width, stands the cosmetologist M (the brand's main face: a woman about 30 with long dark wavy hair, a white uniform with pink piping and a pendant with a blue stone on a black cord, identical to the attached M reference photo); she wears clean white examination gloves; she leans in slightly and looks attentively at the patient's cheek. At about 38-60% of the width sits the patient P7 (a woman 25-30 with long chestnut hair held back by a black headband, identical to the attached P7 character sheet; natural calm young skin with real texture), upright in the white treatment chair, calm, eyes open, face in soft three-quarter view toward M, listening. On the marble side table in the lower left, at about 18-32% of the width and above the bottom 15%, stands the closed EXOCELL MASK box exactly as in the attached packshot (exocell-mask.webp) and the attached flat front scan (exocell-box-front.jpg, for checking small print): a flat portrait-format matte muted-teal carton (#5ca0a5) with dark navy print, shallow in depth; FRONT face visible with the VM monogram and small 'VM corporation' at the top, 'EXOCELL' in wide-spaced capitals ('EXO' bold, 'CELL' thin) with letter-spaced 'M A S K' below, the light italic pale-aqua lines 'Your Second Skin' / 'For Exo Bio-Regeneration', the small four-language block and '5 face masks' / 'Net 5 x 25 ml' at the bottom (lines too small to read render as fine grey lines, never as invented words); the narrow LEFT side panel visible at an angle on the left, with 'EXOCELL' / 'MASK' running vertically in grey. The box stands upright and closed, turned about 30 degrees so that its front faces slightly toward the right edge of the frame and its LEFT side faces the camera, as in the packshot; only the front and the left side show; its right side is hidden; never show its right side, back, top or bottom; never open it. The top of the box is exactly at the camera's eye line; its top face is never visible. The sheet mask that stands next to the box in the packshot is NOT on the table, and there is no sachet. Right 35% of the frame: only the softly lit window and wall. 16:9 horizontal film still, framed for 1920x1080. COMPOSITION RULE FOR 16:9 (desktop, right-to-left page): the right 35% of the frame contains no faces, no hands and no packaging, only calm softly lit wall and window background, because the Hebrew caption sits there; the bottom 15% contains nothing important, because the step markers sit there. Photorealistic, true colours, real skin texture with pores, fine grain. No added text, captions, logos or watermarks beyond the box's own print; no invented packaging; no opened box, no sachet; no needle, syringe or device; no skin smoothing or glow; no redness appearing or disappearing; no before/after look; no extra fingers; no duplicate people.`

- **Промпт 9:16:**

  `Vertical medium two-shot, 50mm, camera at seated eye level, the lens height level with the top edge of the box on the side table so its top face is not visible, in the same bright, clean treatment room as the attached vertical K0: soft natural daylight from a large window, warm white walls, white treatment chair, light marble side table; same room and light as the vertical K0, same people as the attached approved 16:9 K1. The cosmetologist M (the brand's main face: a woman about 30 with long dark wavy hair, a white uniform with pink piping and a pendant with a blue stone on a black cord, identical to the attached M reference photo) stands on the left in clean white examination gloves, leaning in slightly and looking attentively at the patient's cheek. The patient P7 (a woman 25-30 with long chestnut hair held back by a black headband, identical to the attached P7 character sheet; natural calm young skin with real texture) sits upright in the white treatment chair on the right, calm, eyes open, listening. Both faces sit at about 18-38% of the frame height. On the marble side table between them, its top at about 42% and its base at about 60% of the frame height, stands the closed EXOCELL MASK box exactly as in the attached packshot (exocell-mask.webp) and as in the attached vertical K0: a flat portrait-format matte muted-teal carton (#5ca0a5) with dark navy print, shallow in depth; FRONT face visible with the VM monogram and small 'VM corporation' at the top, 'EXOCELL' in wide-spaced capitals ('EXO' bold, 'CELL' thin) with letter-spaced 'M A S K' below, the light italic pale-aqua lines 'Your Second Skin' / 'For Exo Bio-Regeneration', the small four-language block and '5 face masks' / 'Net 5 x 25 ml' at the bottom (lines too small to read render as fine grey lines, never as invented words); the narrow LEFT side panel visible at an angle on the left, with 'EXOCELL' / 'MASK' running vertically in grey. The box stands upright and closed, turned about 30 degrees so that its front faces slightly toward the right edge of the frame and its LEFT side faces the camera, as in the packshot; only the front and the left side show; its right side is hidden; never show its right side, back, top or bottom; never open it. The top of the box is exactly at the camera's eye line; its top face is never visible. The sheet mask that stands next to the box in the packshot is NOT on the table, and there is no sachet. Below 62%: the table top, M's uniform and P7's lap only. 9:16 vertical film still, framed natively for 1080x1920 (composed for a phone, not a crop of a horizontal frame). COMPOSITION RULE FOR 9:16 (phone): every face and the packaging sit between 13% and 62% of the frame height measured from the top; the top 13% (under the site header) shows no face; the bottom 38% shows only table surface, clothing or neutral background with nothing important, because a dark caption band sits there. Photorealistic, true colours, real skin texture with pores, fine grain. No added text, captions, logos or watermarks beyond the box's own print; no invented packaging; no opened box, no sachet; no needle, syringe or device; no skin smoothing or glow; no redness appearing or disappearing; no before/after look; no extra fingers; no duplicate people.`

### K2 — Нанесение: маска уже лежит на лице, M разглаживает её (новый приём в серии: образец, ждать «ок»). Сцены 04-05, старт ролика C. Снимается только после ответа заказчика об устройстве маски.
- **Композиция:** Немного сверху, три четверти. P7 полулёжа в откинутом кресле, глаза закрыты; маска уже лежит на лице (один молочно-белый слой по пакшоту). M стоит за головой P7, ладони в центре маски. 16:9: голова P7 на 30–50 % ширины, M на 8–28 %, вправо уходит тело под белым полотенцем — в правых 35 % только тело под полотенцем, кресло и стена, ни лиц, ни рук. 9:16: лицо M на 18–32 %, лицо P7 на 36–58 % высоты, ниже — плечи, полотенце, кресло. Коробки в кадре нет.
- **Упаковка в кадре:** коробки в кадре нет. Прикладывать `/home/user/GregoryDich/mitoderm-catalog/protocols/print/img/exocell-mask.webp` только как образец формы маски (вырезы, клапан носа, прорезь у края); в промпте прямо: «use the attached packshot only for the mask's shape and ignore the box in it».
- **Опоры (по порядку, не больше 5):** 1) K1 (утверждён: лица, одежда, комната; для 9:16 — K1 vertical); 2) P7 `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/p7-turnaround.jpg` (медиа 387b9773-…); 3) M `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/main-photo.jpg` (медиа 90121c86-…); 4) пакшот `/home/user/GregoryDich/mitoderm-catalog/protocols/print/img/exocell-mask.webp` (медиа 61ca8e69-…) — только форма маски.
- **Промпт 16:9:**

  `Slightly high three-quarter view, 50mm, in the same bright, clean treatment room as the attached K1: soft natural daylight from a large window, warm white walls, white treatment chair, light marble side table; same people and light as the attached K1. The patient P7 (a woman 25-30 with long chestnut hair held back by a black headband, identical to the attached P7 character sheet; natural calm young skin with real texture) lies back in the reclined white treatment chair, eyes closed, relaxed; her head is at about 30-50% of the frame width and her body runs to the right under a white towel. On her face lies the EXOCELL sheet mask exactly as in the attached packshot (exocell-mask.webp; use the attached packshot only for the mask's shape and ignore the box in it): one translucent milky-white bio-cellulose sheet with a faint aqua tint, moist and glistening with serum, with eye cut-outs, a nose cut-out with its flap, a mouth cut-out and the small slit at the lower jaw edge; it lies smooth and close on her face from the hairline to the chin, following its contours, the cut-outs aligned with her eyes, nose and mouth; the black headband stays visible at the hairline above the mask. The cosmetologist M (the brand's main face: a woman about 30 with long dark wavy hair, a white uniform with pink piping and a pendant with a blue stone on a black cord, identical to the attached M reference photo) stands behind her head on the left, at about 8-28% of the width, face in soft three-quarter view looking down; in clean white examination gloves she rests both palms flat on the centre of the mask, on the forehead and beside the nose, about to smooth it outwards. Right 35% of the frame: only the chair, the white towel and the softly lit wall; no face, no hands there. 16:9 horizontal film still, framed for 1920x1080. COMPOSITION RULE FOR 16:9 (desktop, right-to-left page): the right 35% of the frame contains no faces, no hands and no packaging (only the towel-covered body, chair and wall), because the Hebrew caption sits there; the bottom 15% contains nothing important, because the step markers sit there. Photorealistic, true colours, real skin texture with pores, fine grain. No added text, captions, logos or watermarks; no box, no sachet in frame; the mask is one single milky-white layer: no blue layer, no second layer, no paper or backing sheet; no needle, syringe or device; no skin smoothing or glow; no redness; no before/after look; no extra fingers; no duplicate people.`

- **Промпт 9:16:**

  `Vertical, slightly high view, 50mm, in the same bright, clean treatment room as the attached K1: soft natural daylight from a large window, warm white walls, white treatment chair, light marble side table; same people and light as the attached K1. The patient P7 (a woman 25-30 with long chestnut hair held back by a black headband, identical to the attached P7 character sheet; natural calm young skin with real texture) lies back in the reclined white treatment chair, eyes closed, relaxed; her face, turned up toward the camera, sits at about 36-58% of the frame height. On her face lies the EXOCELL sheet mask exactly as in the attached packshot (exocell-mask.webp; use the attached packshot only for the mask's shape and ignore the box in it): one translucent milky-white bio-cellulose sheet with a faint aqua tint, moist and glistening with serum, with eye cut-outs, a nose cut-out with its flap, a mouth cut-out and the small slit at the lower jaw edge; it lies smooth and close on her face from the hairline to the chin, following its contours, the cut-outs aligned with her eyes, nose and mouth; the black headband stays visible at the hairline above the mask. The cosmetologist M (the brand's main face: a woman about 30 with long dark wavy hair, a white uniform with pink piping and a pendant with a blue stone on a black cord, identical to the attached M reference photo) stands behind her head, her face in soft three-quarter view looking down at about 18-32% of the frame height; in clean white examination gloves she rests both palms flat on the centre of the mask. Below 62%: only P7's shoulders, the white towel and the chair. 9:16 vertical film still, framed natively for 1080x1920 (composed for a phone, not a crop of a horizontal frame). COMPOSITION RULE FOR 9:16 (phone): every face and the packaging sit between 13% and 62% of the frame height measured from the top; the top 13% (under the site header) shows no face; the bottom 38% shows only table surface, clothing or neutral background with nothing important, because a dark caption band sits there. Photorealistic, true colours, real skin texture with pores, fine grain. No added text, captions, logos or watermarks; no box, no sachet in frame; the mask is one single milky-white layer: no blue layer, no second layer, no paper or backing sheet; no needle, syringe or device; no skin smoothing or glow; no redness; no before/after look; no extra fingers; no duplicate people.`

### K3 — Завершение: маска уже снята, M мягко похлопывает остатки сыворотки. Сцена 06, старт ролика D. Снимается после K2.
- **Композиция:** Точно та же постановка, что K2, через несколько минут: маски нет (снята за склейкой и в кадр не попадает), кожа та же, только лёгкий влажный блеск сыворотки; кончики пальцев M у щеки и лба. Коробки в кадре нет.
- **Упаковка в кадре:** коробки и маски в кадре нет. Пакшот `exocell-mask.webp` **не прикладывать**: на нём маска, а маски в кадре быть не должно. Из хвоста промпта убрано описание маски, вместо него «no sheet mask anywhere in frame, no mask in hands». 9:16: лицо M на 18–32 %, P7 на 36–58 %.
- **Опоры (по порядку, не больше 5):** 1) K2 (утверждён: точная постановка; для 9:16 — K2 vertical); 2) K1 (утверждён: лицо P7); 3) P7 `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/p7-turnaround.jpg` (медиа 387b9773-…); 4) M `/tmp/claude-0/-home-user-GregoryDich/0aa82102-fd8e-5074-bffe-35af07ddfed7/scratchpad/cast/main-photo.jpg` (медиа 90121c86-…).
- **Промпт 16:9:**

  `Exactly the same framing, people and light as the attached K2, a few minutes later, in the same bright, clean treatment room as the attached K2: soft natural daylight from a large window, warm white walls, white treatment chair, light marble side table. The sheet mask has been removed and is nowhere in frame. The patient P7 (a woman 25-30 with long chestnut hair held back by a black headband, identical to the attached P7 character sheet; natural calm young skin with real texture) lies back in the reclined white treatment chair, eyes closed, relaxed; her face, identical to the attached K1, shows the same natural skin texture and tone with only a faint moist sheen of serum residue. In clean white examination gloves, the cosmetologist M (the brand's main face: a woman about 30 with long dark wavy hair, a white uniform with pink piping and a pendant with a blue stone on a black cord, identical to the attached M reference photo) lightly touches P7's cheek and forehead with her fingertips, about to pat the remaining serum in. Right 35% of the frame: only the chair, the white towel and the softly lit wall; no face, no hands there. 16:9 horizontal film still, framed for 1920x1080. COMPOSITION RULE FOR 16:9 (desktop, right-to-left page): the right 35% of the frame contains no faces, no hands and no packaging (only the towel-covered body, chair and wall), because the Hebrew caption sits there; the bottom 15% contains nothing important, because the step markers sit there. Photorealistic, true colours, real skin texture with pores, fine grain. No added text, captions, logos or watermarks; no sheet mask anywhere in frame, no mask in hands, no box, no sachet; no needle, syringe or device; no skin smoothing or glow; no redness; no before/after look; no extra fingers; no duplicate people.`

- **Промпт 9:16:**

  `Exactly the same framing, people and light as the attached vertical K2, a few minutes later, in the same bright, clean treatment room as the attached K2: soft natural daylight from a large window, warm white walls, white treatment chair, light marble side table. The sheet mask has been removed and is nowhere in frame. The patient P7 (a woman 25-30 with long chestnut hair held back by a black headband, identical to the attached P7 character sheet; natural calm young skin with real texture), eyes closed, relaxed, her face (identical to the attached K1) at about 36-58% of the frame height, the same natural skin texture and tone with only a faint moist sheen of serum residue. In clean white examination gloves, the cosmetologist M (the brand's main face: a woman about 30 with long dark wavy hair, a white uniform with pink piping and a pendant with a blue stone on a black cord, identical to the attached M reference photo), face at about 18-32% of the frame height looking down, lightly touches P7's cheek and forehead with her fingertips. Below 62%: only P7's shoulders, the white towel and the chair. 9:16 vertical film still, framed natively for 1080x1920 (composed for a phone, not a crop of a horizontal frame). COMPOSITION RULE FOR 9:16 (phone): every face and the packaging sit between 13% and 62% of the frame height measured from the top; the top 13% (under the site header) shows no face; the bottom 38% shows only table surface, clothing or neutral background with nothing important, because a dark caption band sits there. Photorealistic, true colours, real skin texture with pores, fine grain. No added text, captions, logos or watermarks; no sheet mask anywhere in frame, no mask in hands, no box, no sachet; no needle, syringe or device; no skin smoothing or glow; no redness; no before/after look; no extra fingers; no duplicate people.`

## 5. Ролики (Kling 4.0, 5 с, 121 кадр, без конечного кадра)

### A — от K0 (16:9) и K0 vertical (9:16)
- Старт K0. Камера отъезжает прямо назад, не поднимаясь (верх коробки не виден: фото верха нет), коробка неподвижна и резкая, люди всё время размыты (без перевода фокуса — иначе Kling дорисует лица). Конечный кадр не нужен: дальше склейка в B.
- **Решение (отход от EXO-NAD):** в EXO-NAD ролик A идёт от упаковки к людям и кончается на K1. Здесь A — только отъезд от коробки, к K1 жёсткая склейка (A→B). Причина: если дать A конечный кадр K1, Kling будет переводить фокус на людей и дорисовывать лица между K0 и K1, а наплыв не нужен — B начинается точно с K1. Записано в открытые вопросы (п. 14) с этим вариантом по умолчанию. Тот же ролик задом наперёд закрывает фильм и кончается точно на K0.
- **Использование:** frame 0 -> hold at the start (0-24) and the end (654-666); frames 1-120 forward (24-144, chapters 01-02); frames 120->1 reversed (534-654, chapters 07-08).
- **Промпт 16:9:**

  `The camera slowly pulls straight back about 15%, staying exactly at the height of the box's top edge; it never rises, so the top of the box is never visible; keeping the closed EXOCELL MASK box sharp and still at the same place in frame; M and P7 behind stay softly out of focus the whole time (no focus pull), they only breathe and shift very slightly. Keep the right 35% of the frame free of faces, hands and packaging, as in the start image. Photorealistic, one continuous take, no cuts. Faces, hair, black headband, uniform, pendant, white gloves and room stay exactly as in the start image. While visible, the EXOCELL MASK box never moves, opens, turns or changes; its shape, colour and printed words stay exactly as in the start image. P7's skin texture and tone stay unchanged throughout. No text, captions or graphics in frame, no new objects, no sachet, no needle or device, no skin smoothing or glow, no extra fingers, no morphing. No audio.`

- **Промпт 9:16:**

  `The camera slowly pulls straight back about 15%, staying exactly at the height of the box's top edge; it never rises, so the top of the box is never visible; keeping the closed EXOCELL MASK box sharp and still in the centre, its top never above 13% and its base never below 62% of the frame height; M and P7 behind stay softly out of focus the whole time (no focus pull), they only breathe and shift very slightly; the bottom 38% of the frame stays plain (table, clothing), no hands or objects of interest enter it. Photorealistic, one continuous take, no cuts. Faces, hair, black headband, uniform, pendant, white gloves and room stay exactly as in the start image. While visible, the EXOCELL MASK box never moves, opens, turns or changes; its shape, colour and printed words stay exactly as in the start image. P7's skin texture and tone stay unchanged throughout. No text, captions or graphics in frame, no new objects, no sachet, no needle or device, no skin smoothing or glow, no extra fingers, no morphing. No audio.`

- **Проверить:** frame 0 = K0; box print (EXOCELL / M A S K / Your Second Skin) crisp and unchanged in every frame; only front and left side of the box ever visible; faces stay soft: no invented sharp faces; reversed playback reads as a slow push-in onto the box; 16:9: right 35% clean; 9:16: box inside 13-62%, bottom 38% plain; top face of the box never visible.

### B — от K1 (16:9) и K1 vertical (9:16)
- Старт K1. Консультация: лёгкое касание у скулы без нажима, кивки, коробку никто не трогает. Первая половина — глава 02, вторая — глава 03.
- **Использование:** frames 0-59 (144-204, chapter 02, cut in after A); frames 60-119 (204-264, chapter 03).
- **Промпт 16:9:**

  `Camera almost still. M and P7 talk quietly. M leans in a little and looks attentively at P7's cheek, one gloved fingertip resting lightly beside the cheekbone for a moment without pressing; then she straightens up and nods calmly. P7 listens and nods once. Lips mostly closed, no talking-head mouth motion. The closed box on the side table stays exactly as in the start image; nobody touches it. Keep the right 35% of the frame free of faces, hands and packaging, as in the start image. Photorealistic, one continuous take, no cuts. Faces, hair, black headband, uniform, pendant, white gloves and room stay exactly as in the start image. While visible, the EXOCELL MASK box never moves, opens, turns or changes; its shape, colour and printed words stay exactly as in the start image. P7's skin texture and tone stay unchanged throughout. No text, captions or graphics in frame, no new objects, no sachet, no needle or device, no skin smoothing or glow, no extra fingers, no morphing. No audio.`

- **Промпт 9:16:**

  `Camera almost still. M and P7 talk quietly. M leans in a little and looks attentively at P7's cheek, one gloved fingertip resting lightly beside the cheekbone for a moment without pressing; then she straightens up and nods calmly. P7 listens and nods once. Lips mostly closed, no talking-head mouth motion. The closed box on the side table stays exactly as in the start image; nobody touches it. Keep every face and the box between 13% and 62% of the frame height, as in the start image; the bottom 38% of the frame stays plain (table, clothing), no hands or objects of interest enter it. Photorealistic, one continuous take, no cuts. Faces, hair, black headband, uniform, pendant, white gloves and room stay exactly as in the start image. While visible, the EXOCELL MASK box never moves, opens, turns or changes; its shape, colour and printed words stay exactly as in the start image. P7's skin texture and tone stay unchanged throughout. No text, captions or graphics in frame, no new objects, no sachet, no needle or device, no skin smoothing or glow, no extra fingers, no morphing. No audio.`

- **Проверить:** faces = K1 for all 120 frames; fingertip only touches, no pressing or rubbing; box static, print intact; five fingers; P7 skin unchanged.

### C — от K2 (16:9) и K2 vertical (9:16)
- Старт K2. Лёгкое разглаживание маски ладонями, чтобы она легла ровно (жест в источниках не описан — открытый вопрос 13; «כמעט ללא כיסי אוויר» в content.json — свойство самой маски, а не действие косметолога), затем руки уходят и P7 лежит спокойно — это часть «ספיגה»; кадр 120 держится стоп-кадром до конца главы 05. Снимается только после ответа об устройстве маски.
- **Использование:** frames 0-83 (264-348, chapter 04, cut in after B); frames 84-120 (348-385, chapter 05) and a hold of frame 120 (385-420).
- **Промпт 16:9:**

  `Camera nearly still, a very slight push-in of no more than 3%. With slow, gentle movements M smooths the sheet mask on P7's face with her gloved palms and fingertips from the centre outwards: across the forehead, along the cheeks toward the temples and down to the jaw, gently smoothing so the sheet lies evenly. The mask keeps its shape and its cut-outs stay aligned with the eyes, nose and mouth; nothing peels, folds, tears, slides or changes colour, and nothing is laid on top of it. After about three seconds M lifts her hands away and steps back slightly; P7 rests with her eyes closed, breathing slowly. Keep the right 35% of the frame free of faces, hands and packaging, as in the start image. Photorealistic, one continuous take, no cuts. Faces, hair, black headband, uniform, pendant, white gloves and room stay exactly as in the start image. The sheet mask stays one single milky-white translucent layer with the same shape and cut-outs; no blue or second layer, no backing sheet. P7's skin texture and tone stay unchanged throughout. No text, captions or graphics in frame, no new objects, no box, no sachet, no needle or device, no skin smoothing or glow, no extra fingers, no morphing. No audio.`

- **Промпт 9:16:**

  `Camera nearly still, a very slight push-in of no more than 3%. With slow, gentle movements M smooths the sheet mask on P7's face with her gloved palms and fingertips from the centre outwards: across the forehead, along the cheeks toward the temples and down to the jaw, gently smoothing so the sheet lies evenly. The mask keeps its shape and its cut-outs stay aligned with the eyes, nose and mouth; nothing peels, folds, tears, slides or changes colour, and nothing is laid on top of it. After about three seconds M lifts her hands away and steps back slightly; P7 rests with her eyes closed, breathing slowly. Keep every face between 13% and 62% of the frame height; the bottom 38% of the frame stays plain (only shoulders, towel and chair), no hands or objects of interest enter it. Photorealistic, one continuous take, no cuts. Faces, hair, black headband, uniform, pendant, white gloves and room stay exactly as in the start image. The sheet mask stays one single milky-white translucent layer with the same shape and cut-outs; no blue or second layer, no backing sheet. P7's skin texture and tone stay unchanged throughout. No text, captions or graphics in frame, no new objects, no box, no sachet, no needle or device, no skin smoothing or glow, no extra fingers, no morphing. No audio.`

- **Проверить:** mask shape and cut-outs = packshot in every frame; one milky-white layer only, no blue appears; hands leave the face by frame ~84 (absorption part is calm); no sliding or melting of the sheet into the skin; fingers; faces = K1/K2.

### D — от K3 (16:9) и K3 vertical (9:16)
- Старт K3. Маска уже снята; лёгкие похлопывания остатков сыворотки, без растирания и салфетки; P7 открывает глаза. Белое полотенце на теле P7 остаётся как в K3 (в промпте запрещены салфетка и ватный диск в руках, а не полотенце). Снимается после C.
- **Использование:** frames 0-107 (420-528, chapter 06, cut in); frames 108-113 blend over 6 frames (DIS dissolve) into frame 120 of A, which then plays reversed (528-534).
- **Промпт 16:9:**

  `Camera nearly still. With light, gentle taps of her gloved fingertips M pats the remaining serum into P7's cheeks and forehead: no rubbing, no wiping. Then her hands lift away. P7 slowly opens her eyes and stays calm and relaxed. The skin keeps the same faint moist sheen and the same natural texture and tone; nothing changes or improves. The white towel over P7's body stays exactly as in the start image. Keep the right 35% of the frame free of faces, hands and packaging, as in the start image. Photorealistic, one continuous take, no cuts. Faces, hair, black headband, uniform, pendant, white gloves and room stay exactly as in the start image. P7's skin texture and tone stay unchanged throughout. No text, captions or graphics in frame, no new objects, no mask, no box, no sachet, no tissue, no wipe, no cotton pad in her hands, no needle or device, no skin smoothing or glow, no extra fingers, no morphing. No audio.`

- **Промпт 9:16:**

  `Camera nearly still. With light, gentle taps of her gloved fingertips M pats the remaining serum into P7's cheeks and forehead: no rubbing, no wiping. Then her hands lift away. P7 slowly opens her eyes and stays calm and relaxed. The skin keeps the same faint moist sheen and the same natural texture and tone; nothing changes or improves. The white towel over P7's body stays exactly as in the start image. Keep every face between 13% and 62% of the frame height; the bottom 38% of the frame stays plain (only shoulders, towel and chair), no hands or objects of interest enter it. Photorealistic, one continuous take, no cuts. Faces, hair, black headband, uniform, pendant, white gloves and room stay exactly as in the start image. P7's skin texture and tone stay unchanged throughout. No text, captions or graphics in frame, no new objects, no mask, no box, no sachet, no tissue, no wipe, no cotton pad in her hands, no needle or device, no skin smoothing or glow, no extra fingers, no morphing. No audio.`

- **Проверить:** taps, not rubbing; skin identical first/last frame (no glow, no redness change); no mask reappears; P7 face = K1 when eyes open; fingers.

## 6. Сборка

Образец — `state/nad-film/tools/assemble-nad.sh` (клипы по 121 кадру, стоп-кадры через `tpad` clone, наплыв `xfade`
0.25 с, `reverse`) и `codex-site/production/assemble-vtech-continuity-v5.py`. Делается копия под эту страницу, один
список сегментов для обоих форматов (16:9 — из 16:9 исходников, 9:16 — из 9:16):

`hold A0 ×24 → A 1–120 → склейка B 0–119 → склейка C 0–120 + стоп-кадр C120 ×35 → склейка D 0–107 → наплыв 6 кадров
(D 108–113 в A120) → A задом наперёд 120→1 → стоп-кадр A0 ×12` = 666 кадров; 24 к/с, ключевой кадр каждые 12, без звука,
faststart; проверка: число кадров 666, последний кадр = кадр 0 ролика A.

## 7. Стоимость (кредиты, цены брифа)

| Статья | Расчёт | Кредиты |
|---|---|---:|
| Кадры | 4 stills x 2 formats x 2.75 = 22 | 22 |
| Ролики | 4 clips x 2 formats x 16.25 = 130 | 130 |
| **Итого** | потолок 152 | **152** |

Переснятия в 152 не входят: кадр 2.75, ролик 16.25 за дубль. Запасной план на 3 ролика: убрать B, K1 остаётся стоп-кадром (медленный наезд при сборке): 8 кадров × 2.75 + 6 роликов × 16.25 = 22 + 97.5 = 119.5. Это на 5.5 дороже 114 из брифа (там 3 кадра), но в пределах 150 на страницу: кадров остаётся 4, потому что каждый нужен — K0, K2, K3 стартуют ролики A, C, D, а K1 — единственная картинка консультации (без него главы 02–03 без людей). Раскладка без B: 108–144 — A frames 85–120 (как сейчас); 144–264 — стоп-кадр K1, 120 кадров, медленный наезд при сборке не больше 4 % (глава 02 — 144–204, глава 03 — 204–264); дальше как в основном плане.

## 8. Порядок съёмки и пробники

Правило заказчика 19/11: сначала кадр упаковки, затем первый кадр с людьми, затем остальное; каждая вещь — ссылкой.
Ролики с коробкой — только после того, как кадр упаковки выложен заказчику. После каждой партии — запись в
`PROGRESS.md` (что, сколько, остаток).

| Шаг | Что снимается | Кредиты | Что уходит заказчику |
|---|---|---:|---|
| 1 | K0 16:9 + K0 9:16 (кадр упаковки) | 5.5 (всего 5.5) | 2 ссылки: K0 16:9 и K0 9:16. Что проверить: коробка закрыта, видны только лицевая и левая сторона, мелкий текст не выдуман. |
| 2 | K1 16:9 (первый кадр с людьми: M и P7 вместе) | 2.75 (всего 8.25) | 1 ссылка, ждать «ок» на P7 рядом с M (образец). После «ок» — K1 9:16 (2.75) и ещё 1 ссылка. |
| 3 | K1 9:16 | 2.75 (всего 11) | 1 ссылка (серия в утверждённом образе, без ожидания). |
| 4 | ролик A 16:9, затем A 9:16 (только после того, как кадр упаковки K0 уже выложен заказчику) | 32.5 (всего 43.5) | 2 ссылки: A 16:9 и A 9:16 (A 16:9 — образец ролика страницы: показать и ждать «ок» до A 9:16). |
| 5 | ролик B 16:9 + 9:16 | 32.5 (всего 76) | 2 ссылки. |
| 6 | K2 16:9 (маска на лице — новый приём в серии) — только после ответа заказчика, как устроена маска | 2.75 (всего 78.75) | 1 ссылка, ждать «ок» (образец маски на лице). Затем K2 9:16 и K3 16:9 + 9:16 (3 × 2.75) — 3 ссылки. |
| 7 | K2 9:16, K3 16:9, K3 9:16 | 8.25 (всего 87) | 3 ссылки. |
| 8 | ролики C и D, по два формата | 65 (всего 152) | 4 ссылки. |
| 9 | сборка двух фильмов (24 к/с, ключевой кадр каждые 12) и запись в PROGRESS.md | 0 (всего 152) | 2 ссылки: фильм 16:9 и фильм 9:16 (или тестовая страница). |

Остановки с ожиданием «ок»: после K1 16:9 (P7 впервые рядом с M), после A 16:9 (образец ролика страницы), перед K2
(ответ об устройстве маски) и после K2 16:9 (маска на лице — новый приём в серии). Остальное идёт серией, ссылки по ходу.

## 9. Открытые вопросы (работа идёт по варианту по умолчанию)

1. Как устроена маска: (а) снять два вспомогательных слоя и положить только белую (PAGE.md, REGISTRY, заголовки глав сейчас) или (б) двойная маска, белый и синий слои кладутся один за другим (content.json разд. 5 и 7, site/packaging-text.md, решение 11/10 и 14/10)? Если (б) — какой слой касается кожи и что видно на лице в конце.
   **По умолчанию:** Показан вариант (а): на лице один молочно-белый полупрозрачный слой, без синего слоя, без отделения подложек и без самого момента наложения из саше. При (б) K2, C и стоп-кадр главы 05 переписываются (второй, синий слой поверх белого: content.json «שמניחים בזו אחר זו»). K2, K3, ролики C и D не снимать до ответа; если ответ другой — переписать K2/K3/C/D до генерации (лишних трат нет).
2. Открытая коробка, разорванное саше, маска, вынутая из саше: настоящих фото и точной модели нет (audits-19-11.json, packAssets.missingFaces).
   **По умолчанию:** Коробка всё время закрыта, саше в фильме нет; маска появляется сразу на лице через склейку (B -> C). Раскрытие — только когда будут фото открытой коробки и саше.
3. Какая коробка сейчас в продаже: тёмно-бирюзовая «Your Second Skin» (пакшот и сайт), светлая «imbued in serum» (sources/exocell-box-v2-front.png) или ярко-бирюзовая «The Ultimate Beauty Ritual» (листовка sources/exocell-wow-effect-he.webp)?
   **По умолчанию:** Тёмно-бирюзовая «Your Second Skin» по пакшоту protocols/print/img/exocell-mask.webp.
4. Размеры коробки не записаны нигде.
   **По умолчанию:** Пропорции по пакшоту и по 3D-шаблону site/proto/exocell-3d-template.html (1.48 × 2.0 × 0.27): плоская вертикальная коробка; в промптах — «flat portrait-format carton, shallow in depth», без цифр.
5. Показывать ли покраснение после процедуры (сценарий v3: «сразу после микронидлинга»)?
   **По умолчанию:** Нет: у P7 спокойная кожа без покраснения, одинаковая во всех кадрах (бриф: «спокойная молодая кожа»; без вида «до/после» и мгновенного эффекта). Процедура до маски не показывается.
6. Положение пациентки при наложении маски источники не указывают.
   **По умолчанию:** Полулёжа в откинутом белом кресле, глаза закрыты (как в EXO-NAD и сценарии v3).
7. «להספיג בעדינות את שאריות הסרום» (протокол): похлопать пальцами или промокнуть салфеткой?
   **По умолчанию:** Лёгкие похлопывания кончиками пальцев в белых перчатках, без салфетки и растирания (r4-facts: «аккуратно промокнуть»; content.json сам способ не описывает).
8. Перчатки в фазе маски (вопрос из сценария v3).
   **По умолчанию:** Белые перчатки во всех кадрах (бриф серии).
9. Время на коже «до 30 минут» есть в протоколе.
   **По умолчанию:** На экран не идёт (бриф: без времени выдержки); ожидание показано только покоем в конце ролика C и стоп-кадром.
10. Число глав: в REGISTRY.json 8 сцен, из них 3–6 написаны под вариант (а) («снятие вспомогательного слоя 1/2», «только белая маска»), а uspHE «מסכה לבנה אחת» противоречит content.json.
   **По умолчанию:** Оставлены 8 глав (не трогаем число сцен в REGISTRY), тексты глав заменены на тексты из content.json; правка REGISTRY.json (названия сцен, uspHE, heroHE) и ProductCinema.tsx — отдельной задачей после ответа о маске.
11. Серьги P7 (в листе — кольца с ракушками) рядом с маской.
   **По умолчанию:** Как в листе персонажа P7; если мешают маске — снять в K2/K3, решить на образце K2.
12. Если бюджета не хватит на 4 ролика.
   **По умолчанию:** Запасной план на 3 ролика: убрать B, K1 остаётся стоп-кадром (медленный наезд при сборке): 8 кадров × 2.75 + 6 роликов × 16.25 = 22 + 97.5 = 119.5 кредита (на 5.5 больше 114 из брифа: все 4 кадра нужны; раскладка глав 02–03 — раздел 7).
13. Разглаживает ли косметолог маску руками после наложения? В источниках только «להניח באופן אחיד» (протокол) и «נצמד לעור בצורה אחידה, כמעט ללא כיסי אוויר» (site/product-pages.he.json) — о самой маске.
   **По умолчанию:** Лёгкое разглаживание ладонями, «gently smooths so the sheet lies evenly», без выдавливания пузырьков.
14. Первый ролик: в EXO-NAD A идёт от упаковки к людям и кончается на K1; здесь A — отъезд от коробки без перевода фокуса, к K1 склейка.
   **По умолчанию:** Как здесь (без конечного кадра K1, чтобы Kling не дорисовывал лица; разница в цене нулевая). Если заказчик хочет переход к людям — дать A конечный кадр K1.

## 10. Риски

- Устройство маски не согласовано: от ответа зависят K2, K3, ролики C и D (половина фильма).
- Kling от одного кадра может нарисовать заднюю/правую сторону коробки при отъезде камеры (ролик A): проверять каждый кадр, при ошибке — повтор 16.25.
- Маска на лице генерируется: форма вырезов и «один слой» сверять с пакшотом; маска может «сползать» или вплавляться в кожу в ролике C.
- Мелкий текст коробки 5 face masks / Net 5 x 25 ml может превратиться в кашу: на 2K он должен идти тонкими серыми строками, не выдуманными словами.
- Наплыв D -> A reversed (крупный план без маски -> общий план) может читаться как скачок; запас — жёсткая склейка на границе глав 06/07.
- Кастинг-листы M и P7 лежат во временной папке сессии; если её очистят — достать из журнала сессии (PROGRESS.md).

## 11. Что поменять на странице после сборки (не делалось, код не трогали)

- `product-films.ts`: запись из раздела 3.
- `ProductCinema.tsx`: `scriptTitles['exocell-mask']` и строки глав — из раздела 3 вместо шаблона `sceneryCopy()`.
- `REGISTRY.json` (exocell-mask): названия сцен 3–6, `heroHE`/`uspHE` «מסכה לבנה אחת» — после ответа об устройстве маски.
- Найденное аудитом и к фильму не относящееся (слово «המערכת», состав набора в блоке предложения, картинка 428 px)
  — в аудите, отдельными задачами.
