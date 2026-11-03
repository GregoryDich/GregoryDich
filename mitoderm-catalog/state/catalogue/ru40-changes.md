# RU catalogue → HE final (40 pp.): complete change list

Figma `x7NyyASEmlMwazkZmZwOXk`. Reference: HE page `793:2` "EXPORT — HE — Design 40" (FINAL, not to be modified). Target: RU page `667:519` "EXPORT — RU — Дизайн 36". Read-only survey of 02/11/2026; nothing in Figma was changed.

Dumps (all text nodes: id, characters, font runs family/style/size, x/y/w/h relative to the frame via the parent chain, visibility; image nodes with hash): `dump/he.json` (40 frames, 399 text nodes) and `dump/ru.json` (36 frames, 320 text nodes). They were written 01/11 22:31 and re-verified today against the live file (live hashes saved in `work/live-he.json`, `work/live-ru.json`): per-frame hashes of text ids + characters + font runs + geometry + image fills match on 76/76 frames (`work/verify.py`; the only image hash difference is HE p.15 `793:245`, which carries two image fills where the dump lists the first). This list is generated from the dumps by `work/build_changes.py` (data: `work/edits_ru.py`), so every "current RU" and "HE text" below is an exact copy; every replacement was checked to occur exactly once in the current text, and no new RU text contains Hebrew or RLM/LRM.

Page mapping: RU 1–19 ↔ HE 1–19; RU old 20–36 ↔ HE 24–40 (they become RU 24–40); RU 20–23 are new (HE 20–23, MITOTECH).

## Legend and conventions

- **A**: HE content the RU lacks or states differently because of owner edits or missing blocks. Must do.
- **B**: the RU translation drifts from the HE meaning (missing or softened claim, different item). Recommended — substance.
- **C**: consistency (one term per HE term), units, typos, label copy, empty nodes. Recommended.
- **IMG**: image edit. **L**: layout / page furniture, no change of meaning. **Q**: owner decision (also under Open questions).
- "New RU" blocks are exact text, ready to paste: line breaks are real `\n` in the node. Do not paste the ```text fences.
- **Weights** (the RU edition uses only Rubik Regular / Medium / Bold): HE ExtraBold titles → RU **Bold**; HE SemiBold and inline Bold emphasis → RU **Medium** (RU keeps Bold where it already marks brand words, e.g. MITO / DERM, "MITODERM –"). Exception, as on HE: MITOTECH titles = "MITOTECH " Rubik **ExtraBold** + "CELL BOOSTER" Rubik **Light**. Offsets of emphasis runs are given for the new text.
- **Numbers and units** as HE: мл, мг, мг/мл, мм; decimal comma in Russian running text (0,5 мл; the RU edition already writes 1–1,5 мл and 0,25–2,5 мм); product names keep the dot (CELL RENEW 1.5%, MICRO BOOST 10%). Label copy that HE keeps in English stays Latin exactly as HE ("30 ml ℮ 1.0 fl.oz.").
- Product names, INCI names and Latin line names exactly as HE (MITOTECH CELL BOOSTER, MICRO BOOST 10%, V-TECH, EXO-NAD, BIOSPICULE™, DST-516, Hydrolyzed Sponge …).
- Text editing (Plugin API): load fonts with `getRangeAllFontNames(0, len)` first; for small edits use `deleteCharacters` / `insertCharacters` (insertCharacters(i, s, 'AFTER') takes the style of the char at i — watch style bleed across line breaks, e.g. after a Medium heading run ending in "\n"); for whole-node replacements set `characters`, then re-apply the runs listed. `setPluginData` / `createImageAsync` are unsupported (use `setSharedPluginData`; clone image nodes from HE instead of creating images). A script that throws may leave partial changes — re-read the nodes after any error.

Summary: A: 16, B: 35, C: 22, IMG: 3, L: 2, L/Q: 2; plus the ToC (27 lines, 10 of them new or changed) and 4 new MITOTECH pages (46 text nodes).

## 1. Structure of the RU page (do first)

- **G1** Rename page `667:519` → `EXPORT — RU — Дизайн 40`.
- **G2** Insert four new frames for RU pp.20–23 by cloning HE `941:2`, `941:21`, `956:2`, `956:23` into `667:519`, then translate and mirror them (section 4). Names:
  - `941:2` → `RU — 20 — MITOTECH CELL BOOSTER`
  - `941:21` → `RU — 21 — MITOTECH CELL BOOSTER — активные компоненты`
  - `956:2` → `RU — 22 — MITOTECH CELL BOOSTER — приготовление`
  - `956:23` → `RU — 23 — MITOTECH CELL BOOSTER — сочетания и комплект`
- **G3** Renumber the old RU frames 20–36 to 24–40 (name change only; the p.24 descriptor follows its new title E24.1):

| old RU | node | current name | new name |
|---|---|---|---|
| 20 | `667:750` | RU — 20 — Дополняющий домашний уход | RU — 24 — Дополняющие средства для домашнего ухода |
| 21 | `667:737` | RU — 21 — Серия синтетических экзосом | RU — 25 — Серия синтетических экзосом |
| 22 | `667:721` | RU — 22 — EXOTECH GEL | RU — 26 — EXOTECH GEL |
| 23 | `667:707` | RU — 23 — EXOSIGNAL SPRAY | RU — 27 — EXOSIGNAL SPRAY |
| 24 | `667:691` | RU — 24 — Серия BIOSPICULE | RU — 28 — Серия BIOSPICULE |
| 25 | `667:673` | RU — 25 — CELL RENEW 1.5% | RU — 29 — CELL RENEW 1.5% |
| 26 | `667:649` | RU — 26 — CELL RENEW — компоненты | RU — 30 — CELL RENEW — компоненты |
| 27 | `669:30` | RU — 27 — CELL RENEW — применение | RU — 31 — CELL RENEW — применение |
| 28 | `667:631` | RU — 28 — CELLULAR AGE DEFENSE 2.5% | RU — 32 — CELLULAR AGE DEFENSE 2.5% |
| 29 | `667:605` | RU — 29 — AGE DEFENSE — компоненты | RU — 33 — AGE DEFENSE — компоненты |
| 30 | `669:32` | RU — 30 — AGE DEFENSE — применение | RU — 34 — AGE DEFENSE — применение |
| 31 | `667:587` | RU — 31 — DERMA RECOVERY CREAM | RU — 35 — DERMA RECOVERY CREAM |
| 32 | `667:569` | RU — 32 — DERMA RECOVERY — компоненты | RU — 36 — DERMA RECOVERY — компоненты |
| 33 | `667:558` | RU — 33 — Профессиональное оборудование | RU — 37 — Профессиональное оборудование |
| 34 | `667:543` | RU — 34 — MITOPEN | RU — 38 — MITOPEN |
| 35 | `667:527` | RU — 35 — MITOSCAN | RU — 39 — MITOSCAN |
| 36 | `667:520` | RU — 36 — Задняя обложка | RU — 40 — Задняя обложка |

- **G4** Canvas and layer order (skill "figma-print-layout", step 8). Canvas grid as today: page n (2–39) at x = 0 if n is even, else 820; y = 641 × floor(n/2); p.1 at (820, 0); p.40 at (0, 0). New p.20 (0, 6410), p.21 (820, 6410), p.22 (0, 7051), p.23 (820, 7051); old p.20 → p.24 (0, 7692) … old p.35 → p.39 (820, 12179); the back cover stays at (0, 0). Layers: `children` must read 40, 39, …, 1 (the first page last). Only the 40 frames on the page; exactly one export setting per frame (all 36 have one today; check the clones), none on any descendant.
- **G5** One Russian term per HE term (applied inside the edits below): HE "סדרה" → **серия** (E18.1, E26.1, E35.1, ToC; never "линия/линейка"); "תכולת האריזה" → **Содержимое упаковки** (E6.5; pp.9, 10, 12, 23 already); "הרכיבים הפעילים המרכזיים" → **Ключевые активные компоненты** (E36.3; pp.30, 33 already); "רכיבים פעילים" → **Активные компоненты** (E12.3, new p.21); ספיקולות → **спикулы** in Russian text (E35.2/3); CELLULAR AGE DEFENSE descriptor → **усовершенствованная сыворотка для укрепления кожи и антивозрастного ухода** (E28.2, E32.2, ToC; p.33 already); pack-shot label copy Latin as HE (E27.1, E35.4).
- **G6** Delete: the hidden empty text nodes `667:1000`, `667:993` (p.2) and the loose "™" `667:697` (p.24 → 28) after E28.1.
- **G7** Continuation pages built without furniture: RU 17, 19, 27, 30 (frames `669:26`, `669:28`, `669:30`, `669:32`) have no running head, no repeated header and no footer, while HE 17, 19, 31, 34 repeat them — E17.1/E17.2, E19.2, E31.1, E34.1.
- **G8** Language check after editing: no Hebrew (U+0590–05FF) and no RLM/LRM (U+200E/200F) anywhere on `667:519` — none today; the four HE clones bring Hebrew and RLM in until every node is replaced. Latin is expected only in product / INCI / line names and in the lines HE itself keeps in English (PROFESSIONAL AESTHETIC CATALOG, SYNTHETIC EXOSOMES, PROFESSIONAL … TREATMENT, ADVANCED SKIN TO CELL DELIVERY SYSTEM, "Advanced skin to cell delivery system", label copy, footer).

## 2. Table of contents (RU p.2, frame `667:978`) — mirrors HE p.2 `793:12`

HE p.2 shows **no page numbers** (there are none on the HE page), so the RU ToC gets none either. For reference only, the HE sections run: 1 → p.3; 2 → pp.4–10; 3 → pp.11–13; 4 → pp.14–19; 5 → pp.20–23; 6 → pp.24–27; 7 → pp.28–36; 8 → pp.37–39; back cover p.40.

Layout: the HE right column (sections 1–5, x 420) becomes the RU **left** column (x 54); the HE left column (sections 6–8, x 54) becomes the RU **right** column (x 420); both 320 px wide (RU now x 42 / 418, 340 / 330 px). Sizes as HE: section heads 14, sub-heading 12, bullets and descriptive lines 10 (the current RU 14/12 will not fit eight sections; Russian lines are longer, so re-flow y top-down, x and reading order from HE). Weights: HE SemiBold → RU Medium (the RU edition uses only Regular / Medium / Bold). Colours as HE (RU today has every line in #57524a): section heads and the sub-heading "Серия синтетических экзосом" ink `#1a1817`; product bullets gold `#9e661f`; descriptive lines (`667:991`, `667:992`, new 5-sub-line) grey `#57524a`; running head `667:979` gold (as now); `667:980` and footer `667:982` grey `#57524a`; title ink `#1a1817`.

Delete the two hidden empty text nodes `667:1000` and `667:993`.

Complete new RU ToC, in reading order (left column, then right column):

```text
Содержание
PROFESSIONAL AESTHETIC CATALOG
1. О компании MITODERM
2. Синтетические экзосомы для профессиональных процедур для лица
• V-TECH
• EXO-NAD
• EXOCELL MASK
3. Синтетические экзосомы для процедур для кожи головы и волос
• EXOSIGNAL HAIR
4. Технология BIOSPICULE™
• Что такое Spongilla и как она действует в коже?
• Наука и технология, лежащие в основе BIOSPICULE™
• MICRO BOOST 10% профессиональная процедура для клиники
5. MITOTECH CELL BOOSTER
Advanced skin to cell delivery system
6. Дополняющие средства для домашнего ухода
Серия синтетических экзосом
• EXOTECH GEL
• EXOSIGNAL SPRAY
7. Серия BIOSPICULE™
• CELL RENEW 1.5% домашняя сыворотка для обновления и осветления
• CELLULAR AGE DEFENSE 2.5% усовершенствованная сыворотка для укрепления кожи и антивозрастного ухода
• DERMA RECOVERY восстанавливающий крем для успокоения и поддержки кожного барьера
• MITOTECH CELL BOOSTER двухэтапная бустерная система с трансдермальной доставкой
8. Профессиональное оборудование для клиники
• MITOPEN профессиональный аппарат для микронидлинга
• MITOSCAN передовая система диагностики кожи головы и волос
```

| # | col | RU node | current RU | HE node | HE text | new RU | role / style |
|---|---|---|---|---|---|---|---|
| 1 | L | `667:981` | Содержание | `793:15` | תוכן העניינים | **Содержание** | Title (Bold 30; HE ExtraBold 30, ink #1a1817) |
| 2 | L | `667:980` | PROFESSIONAL AESTHETIC CATALOG | `793:14` | PROFESSIONAL AESTHETIC CATALOG | **PROFESSIONAL AESTHETIC CATALOG** | As HE: Regular 8, grey #57524a, under the running head (HE y 42), not under the title; now Medium 14 green #294d3b |
| 3 | L | `667:983` | 1. О бренде MITODERM | `793:18` | 1. אודות MITODERM | **1. О компании MITODERM** **(changes)** | Section head; "О бренде" → "О компании" = RU p.3 title (HE uses one phrase for both) |
| 4 | L | `667:984` | 2. Синтетические экзосомы для профессиональных процедур для лица | `793:19` | 2. אקסוזומים סינתטיים לטיפולי פנים מקצועיים | **2. Синтетические экзосомы для профессиональных процедур для лица** | Section head (unchanged text) |
| 5 | L | `667:985` | • V-TECH | `793:20` | • V-TECH | **• V-TECH** | Product bullet |
| 6 | L | `667:986` | • EXO-NAD | `793:21` | • EXO-NAD | **• EXO-NAD** | Product bullet |
| 7 | L | `667:987` | • EXOCELL MASK | `793:22` | • EXOCELL MASK | **• EXOCELL MASK** | Product bullet |
| 8 | L | `667:988` | 3. Синтетические экзосомы для процедур для кожи головы и волос | `793:23` | 3. אקסוזומים סינתטיים לטיפולי קרקפת ושיער | **3. Синтетические экзосомы для процедур для кожи головы и волос** | Section head (unchanged text) |
| 9 | L | `667:989` | • EXOSIGNAL HAIR | `793:24` | • EXOSIGNAL HAIR | **• EXOSIGNAL HAIR** | Product bullet |
| 10 | L | `667:990` | 4. Технология BIOSPICULE™ | `793:25` | 4. טכנולוגיית BIOSPICULE™ | **4. Технология BIOSPICULE™** | Section head (unchanged text) |
| 11 | L | `667:991` | • Что такое Spongilla и как она действует в коже? | `793:26` | • מהן ספונגילות וכיצד הן פועלות בעור? | **• Что такое Spongilla и как она действует в коже?** | Descriptive line, Regular, grey (unchanged text) |
| 12 | L | `667:992` | • Наука и технология, лежащие в основе BIOSPICULE™ | `793:27` | • המדע והטכנולוגיה שמאחורי BIOSPICULE™ | **• Наука и технология, лежащие в основе BIOSPICULE™** | Descriptive line, Regular, grey (unchanged text) |
| 13 | L | `667:994` | • MICRO BOOST 10% профессиональная процедура для клиники | `793:29` | • MICRO BOOST 10% טיפול מקצועי לקליניקה | **• MICRO BOOST 10% профессиональная процедура для клиники** | Product bullet (unchanged text) |
| 14 | L | `NEW (clone 667:990)` | — | `936:2` | 5. MITOTECH CELL BOOSTER | **5. MITOTECH CELL BOOSTER** **(changes)** | NEW section head; "5. MITOTECH " section-head weight (Medium; HE SemiBold), "CELL BOOSTER" Rubik Light, same size; runs Medium [0,12) “5. MITOTECH ”, Light [12,24) “CELL BOOSTER” |
| 15 | L | `NEW (clone 667:991)` | — | `936:4` | Advanced skin to cell delivery system | **Advanced skin to cell delivery system** **(changes)** | NEW descriptive line under section 5, Regular, grey, no bullet; Latin as on HE |
| 16 | R | `667:995` | 5. Дополнительные средства для домашнего ухода | `793:30` | 6. תכשירים משלימים לשימוש ביתי | **6. Дополняющие средства для домашнего ухода** **(changes)** | Section head: number 5 → 6; wording = new p.24 title (E24.1) |
| 17 | R | `667:996` | Серия синтетических экзосом | `793:31` | סדרת האקסוזומים הסינתטיים | **Серия синтетических экзосом** | Sub-heading (HE SemiBold 12, ink): size 14 → 12 |
| 18 | R | `667:997` | • EXOTECH GEL | `793:32` | • EXOTECH GEL | **• EXOTECH GEL** | Product bullet |
| 19 | R | `667:998` | • EXOSIGNAL SPRAY | `793:33` | • EXOSIGNAL SPRAY | **• EXOSIGNAL SPRAY** | Product bullet |
| 20 | R | `667:999` | Серия BIOSPICULE™ | `793:34` | 7. סדרת BIOSPICULE™ | **7. Серия BIOSPICULE™** **(changes)** | Now a numbered SECTION HEAD (HE 793:34 SemiBold 14), not a sub-heading |
| 21 | R | `667:1001` | • CELL RENEW 1.5%  | `793:36` | • CELL RENEW 1.5% סרום ביתי לחידוש והבהרה | **• CELL RENEW 1.5% домашняя сыворотка для обновления и осветления** **(changes)** | Product bullet + descriptor (as RU p.28 667:698); trailing space removed |
| 22 | R | `667:1002` | • CELLULAR AGE DEFENSE 2.5% | `793:37` | • CELLULAR AGE DEFENSE 2.5% סרום מתקדם למיצוק ואנטי-אייג׳ינג | **• CELLULAR AGE DEFENSE 2.5% усовершенствованная сыворотка для укрепления кожи и антивозрастного ухода** **(changes)** | Product bullet + descriptor (E28.2 wording) |
| 23 | R | `667:1003` | • DERMA RECOVERY CREAM | `793:38` | • DERMA RECOVERY קרם משקם להרגעה ולתמיכה במחסום העור | **• DERMA RECOVERY восстанавливающий крем для успокоения и поддержки кожного барьера** **(changes)** | Product bullet + descriptor; HE writes "DERMA RECOVERY" here (CREAM moves into the descriptor) |
| 24 | R | `NEW (clone 667:1003)` | — | `884:2` | • MITOTECH CELL BOOSTER מערכת בוסטר דו־שלבית בהולכה טרנסדרמלית | **• MITOTECH CELL BOOSTER двухэтапная бустерная система с трансдермальной доставкой** **(changes)** | NEW product bullet in section 7, as HE (see open questions) |
| 25 | R | `667:1004` | 6. Профессиональные аппараты для клиник | `793:39` | 8. מכשור מקצועי לקליניקה | **8. Профессиональное оборудование для клиники** **(changes)** | Section head: number 6 → 8; wording = RU p.33 title |
| 26 | R | `667:1005` | • MITOPEN профессиональный аппарат для микронидлинга | `793:40` | • MITOPEN מכשיר מיקרונידלינג מקצועי | **• MITOPEN профессиональный аппарат для микронидлинга** | Product bullet (unchanged text) |
| 27 | R | `667:1006` | • MITOSCAN передовая система диагностики кожи головы и волос | `793:41` | • MITOSCAN מערכת מתקדמת לאבחון הקרקפת והשיער | **• MITOSCAN передовая система диагностики кожи головы и волос** | Product bullet (unchanged text) |

## 3. Page-by-page edits (existing RU pages)

Codes: E<new page>.<n>. "RU p.20 (→ p.24)" = the old RU page number, then its number in the 40-page edition. "Current RU" and "HE text" are copied from the dumps (HE without RLM marks). "New RU" is the whole node text after the edit, ready to paste; where a "Replacements" list is given, the same result can be reached surgically with deleteCharacters/insertCharacters, which keeps the existing style runs.

### RU p.1 — frame `667:1008` “RU — 01 — Обложка” ↔ HE p.1 `824:43` “HE — 01 — Cover”

#### E1.1 [B] Cover title: HE "קטלוג מוצרים" = "Product catalogue"

- RU node: `667:1015` — Rubik Regular 55, at (140, 103) w 514
- HE node(s): `824:50`
- Current RU:
```text
Каталог
```
- HE text:
```text
קטלוג מוצרים
```
- **New RU** (ready to paste):
```text
Каталог продукции
```
- Style: Rubik Regular 55 as now, centred. At 55 pt the line is ~520 px: set textAutoResize WIDTH_AND_HEIGHT and re-centre on the frame (x = (794 − w)/2), or keep 514 px and let it wrap to two lines.
- Note: Cover photos: same visible art as HE (HE hides the five background layers 824:44–48, RU keeps 667:1009–1013 visible under the top image — no visible difference, no change).

### RU p.3 — frame `667:968` “RU — 03 — О компании MITODERM” ↔ HE p.3 `824:52` “HE — 03 — אודות MITODERM”

#### E3.1 [L] Running head "MITODERM" missing on RU p.3 (HE 824:53)

- RU node: `NEW near 667:969`
- HE node(s): `824:53`
- HE text:
```text
MITODERM
```
- **New RU** (ready to paste):
```text
MITODERM
```
- Style: Clone RU p.5 running head 667:945 (Rubik Bold 10.5, gold) into 667:968 at (46, 25).

#### E3.2 [B] Paragraph 2: HE "laboratories, manufacturers and corporations … to bring to clinics in Israel … advanced treatment protocols"

- RU node: `667:970` — Rubik Regular 12, at (46, 106) w 340
- HE node(s): `824:56`
- Current RU (runs: Medium 12 [0,8) 'MITODERM'; Regular 12 [8,597) ' — израильская компания, специализирующа'):
```text
MITODERM — израильская компания, специализирующаяся на разработке, импорте и дистрибуции передовых технологий в области профессиональной косметологии и эстетики кожи и кожи головы.

Компания сотрудничает с ведущими лабораториями и производителями Италии и Южной Кореи, предлагая клиникам профессиональные решения, объединяющие науку, инновации и современные протоколы.

В основе нашей деятельности — технологии на базе синтетических экзосом, пептидов, PDRN, NAD+ и биомиметических компонентов, а также BIOSPICULE™ на основе спикул Spongilla, прошедших строгие процессы очистки и контроля качества.
```
- HE text:
```text
מיטודרם היא חברה ישראלית המתמחה בפיתוח, בייבוא ובהנגשה של טכנולוגיות מתקדמות, לעולמות הקוסמטיקה והאסתטיקה המקצועית בתחום העור והקרקפת.

החברה פועלת בשיתוף פעולה עם מעבדות, יצרנים ותאגידים מובילים באיטליה ובדרום קוריאה, במטרה להביא לקליניקות בישראל פתרונות מקצועיים המשלבים בין מדע, חדשנות ופרוטוקולי טיפול מתקדמים.

בליבת הפעילות שלנו עומדות טכנולוגיות מתקדמות המבוססות על אקסוזומים סינתטיים, פפטידים, PDRN, +NAD ורכיבים ביומימטיים, לצד טכנולוגיית BIOSPICULE™ המבוססת על ספונגילות – מיקרו מחטים שעברו תהליכי טיהור ובקרה קפדניים.
```
- Replacements (old → new):
  - “с ведущими лабораториями и производителями Италии и Южной Кореи, предлагая клиникам профессиональные решения, объединяющие науку, инновации и современные протоколы.” → “с ведущими лабораториями, производителями и корпорациями Италии и Южной Кореи, предлагая клиникам в Израиле профессиональные решения, объединяющие науку, инновации и передовые протоколы процедур.”
- **New RU** (ready to paste):
```text
MITODERM — израильская компания, специализирующаяся на разработке, импорте и дистрибуции передовых технологий в области профессиональной косметологии и эстетики кожи и кожи головы.

Компания сотрудничает с ведущими лабораториями, производителями и корпорациями Италии и Южной Кореи, предлагая клиникам в Израиле профессиональные решения, объединяющие науку, инновации и передовые протоколы процедур.

В основе нашей деятельности — технологии на базе синтетических экзосом, пептидов, PDRN, NAD+ и биомиметических компонентов, а также BIOSPICULE™ на основе спикул Spongilla, прошедших строгие процессы очистки и контроля качества.
```
- Style: Keep the existing Medium run on "MITODERM" at the start.
- Note: Paragraphs 1 and 3 match HE in meaning.

#### E3.3 [B] "Science and clinic" + "Our standard": HE "founded out of deep familiarity with the skin", "not only the treatment", "development and marketing", "complete, personalised protocol", "work directly with our partners abroad", "full professional support for the clinic"

- RU node: `667:971` — Rubik Regular 12, at (416, 106) w 332
- HE node(s): `824:57`
- Current RU (runs: Medium 12 [0,35) 'Связь науки и клинической практики\n'; Regular 12 [35,402) 'MITODERM объединяет глубокое понимание б'; Medium 12 [402,417) 'Наши стандарты\n'; Regular 12 [417,696) 'Каждый продукт и каждая технология MITOD'):
```text
Связь науки и клинической практики
MITODERM объединяет глубокое понимание биологии кожи с реальными потребностями профессиональной практики. Мы убеждены, что эффективная процедура — это не только сам продукт, но и знание механизмов его действия и точный протокол. Поэтому наряду с разработкой продукции мы предоставляем профессиональное обучение, научные знания и индивидуально подобранные протоколы.

Наши стандарты
Каждый продукт и каждая технология MITODERM оцениваются по принципам инновационности, качества, безопасности и удобства применения.
Мы тесно сотрудничаем с международными партнёрами на всех этапах — от выбора сырья и разработки формул до создания комплексных решений для клиники.
```
- HE text:
```text
החיבור בין מדע לקליניקה
מיטודרם נוסדה מתוך היכרות עמוקה עם העור מבפנים ומתוך הבנה אמיתית של הצרכים בשטח. אנו מאמינים שכדי להעניק טיפול מקצועי ברמה גבוהה, זה לא רק הטיפול אלא הידע, הבנת מנגנון הפעולה, ופרוטוקול מדויק 
לכן, לצד פיתוח ושיווק המוצרים, אנו מעניקים הדרכות מקצועיות, ידע מדעי ופרוטוקול טיפול שלם ומותאם אישית.

הסטנדרט שלנו
כל מוצר וכל טכנולוגיה הנכנסים למערך המקצועי של מיטודרם נבחנים על פי עקרונות של חדשנות, איכות, בטיחות ונוחות יישום.
אנו מקפידים על עבודה ישירה עם השותפים המקצועיים שלנו בחו״ל – החל מבחירת חומרי הגלם ופיתוח הפורמולות ועד לבניית מעטפת מקצועית מלאה עבור הקליניקה.
```
- Replacements (old → new):
  - “MITODERM объединяет глубокое понимание биологии кожи с реальными потребностями профессиональной практики. Мы убеждены, что эффективная процедура — это не только сам продукт, но и знание механизмов его действия и точный протокол. Поэтому наряду с разработкой продукции мы предоставляем профессиональное обучение, научные знания и индивидуально подобранные протоколы.” → “MITODERM основана на глубоком знании кожи изнутри и на реальном понимании потребностей специалистов. Мы убеждены, что профессиональная процедура высокого уровня — это не только сама процедура, но и знания, понимание механизма действия и точный протокол. Поэтому наряду с разработкой и продвижением продукции мы проводим профессиональное обучение, делимся научными знаниями и предоставляем полный, индивидуально подобранный протокол процедуры.”
  - “Каждый продукт и каждая технология MITODERM оцениваются” → “Каждый продукт и каждая технология, входящие в профессиональный портфель MITODERM, оцениваются”
  - “Мы тесно сотрудничаем с международными партнёрами на всех этапах — от выбора сырья и разработки формул до создания комплексных решений для клиники.” → “Мы работаем напрямую с нашими профессиональными партнёрами за рубежом — от выбора сырья и разработки формул до создания полного профессионального сопровождения для клиники.”
- **New RU** (ready to paste):
```text
Связь науки и клинической практики
MITODERM основана на глубоком знании кожи изнутри и на реальном понимании потребностей специалистов. Мы убеждены, что профессиональная процедура высокого уровня — это не только сама процедура, но и знания, понимание механизма действия и точный протокол. Поэтому наряду с разработкой и продвижением продукции мы проводим профессиональное обучение, делимся научными знаниями и предоставляем полный, индивидуально подобранный протокол процедуры.

Наши стандарты
Каждый продукт и каждая технология, входящие в профессиональный портфель MITODERM, оцениваются по принципам инновационности, качества, безопасности и удобства применения.
Мы работаем напрямую с нашими профессиональными партнёрами за рубежом — от выбора сырья и разработки формул до создания полного профессионального сопровождения для клиники.
```
- Style: Keep the two Medium heading runs ("Связь науки и клинической практики", "Наши стандарты").

#### E3.4 [C] MITO line: HE "an organelle in all the cells of the body responsible for producing energy"

- RU node: `667:974` — Rubik Regular 12, at (60, 430) w 674
- HE node(s): `824:64`, `824:61`
- Current RU (runs: Bold 12 [0,4) 'MITO'; Regular 12 [4,71) ' — митохондрия, органелла клетки, отвеча'; Bold 12 [71,75) 'DERM'; Regular 12 [75,95) ' — дерма, слой кожи.'):
```text
MITO — митохондрия, органелла клетки, отвечающая за выработку энергии.
DERM — дерма, слой кожи.
```
- HE text:
```text
MITO
—
 – מיטוכונדריה - אברון בכל תאי הגוף האחראי על הפקת אנרגיה
  – דרמיס

```
- Replacements (old → new):
  - “органелла клетки, отвечающая” → “органелла во всех клетках организма, отвечающая”
- **New RU** (ready to paste):
```text
MITO — митохондрия, органелла во всех клетках организма, отвечающая за выработку энергии.
DERM — дерма, слой кожи.
```
- Style: Keep Bold runs "MITO" and "DERM".

#### E3.5 [A] Closing line: HE adds the signature "MITODERM - WHERE SCIENCE MEETS BEAUTY" and says "full potential"

- RU node: `667:975` — Rubik Regular 12, at (60, 468) w 674
- HE node(s): `824:62`
- Current RU:
```text
Как каждой клетке нужна энергия для реализации своего потенциала, так и эстетике нужны инновации, наука и профессиональные знания для развития.
```
- HE text:
```text
כשם שכל תא זקוק לאנרגיה כדי לפעול ולממש את מלוא הפוטנציאל שלו – כך גם עולם האסתטיקה זקוק לחדשנות,
למדע ולידע מקצועי כדי להתקדם.
MITODERM - WHERE SCIENCE MEETS BEAUTY
```
- **New RU** (ready to paste):
```text
Как каждой клетке нужна энергия, чтобы функционировать и полностью реализовать свой потенциал, так и миру эстетики нужны инновации, наука и профессиональные знания для развития.
MITODERM – WHERE SCIENCE MEETS BEAUTY
```
- Emphasis runs (offsets in the new text): Bold [178,189) “MITODERM – ”; Medium [189,215) “WHERE SCIENCE MEETS BEAUTY”
- Style: Body Regular 12 as now; signature line as HE: "MITODERM – " Bold, "WHERE SCIENCE MEETS BEAUTY" Medium. The box grows by one line (~15 px); there is room above the footer (y 529).

### RU p.4 — frame `667:958` “RU — 04 — Синтетические экзосомы” ↔ HE p.4 `824:67` “HE — 04 — אקסוזומים סינתטיים”

#### E4.1 [IMG] Section opener visual: HE = V-TECH kit photo on solid #241c12; RU = exosome-sphere image fill, kit photo hidden

- RU node: `667:958 / 667:966`
- HE node(s): `824:67`, `824:77`
- Style: Frame 667:958: replace the IMAGE fill (hash 6a48aa79d9) with SOLID #241c12 (as HE 824:67). Set 667:966 visible = true — it is the same image as HE 824:77 (hash d217c5045b) and already sits on the mirrored side (x 400, y 139, 320×306; HE 300×287 at x 80).
- Note: Text stays white on the dark fill; check contrast of the grey line 667:965 after the change.

#### E4.2 [C] Latin line "SYNTHETIC EXOSOMES" missing (HE 824:75 above "PROFESSIONAL FACIAL TREATMENT")

- RU node: `NEW near 667:965`
- HE node(s): `824:75`
- HE text:
```text
SYNTHETIC EXOSOMES
```
- **New RU** (ready to paste):
```text
SYNTHETIC EXOSOMES
```
- Style: Clone 667:965, Rubik Medium 14 (HE SemiBold 14), fill as HE 824:75 (gold), letter-spacing as HE; place ~22 px above 667:965 (HE y 331 vs 353).

### RU p.5 — frame `667:944` “RU — 05 — Что такое синтетические экзосомы” ↔ HE p.5 `824:79` “HE — 05 — מהם אקסוזומים סינתטיים”

#### E5.1 [B] "Exosomes … secreted by stem cells" (HE paragraph 1)

- RU node: `667:953` — Rubik Regular 12, at (46, 191) w 346
- HE node(s): `824:89`
- Current RU:
```text
Экзосомы — наноразмерные везикулы, участвующие в межклеточной коммуникации. Они переносят различные биологические молекулы между клетками в рамках естественных механизмов взаимодействия в организме.
```
- HE text:
```text
אקסוזומים הם בועיות ננומטריות המופרשות מתאי אב ומשתתפות בתהליכי תקשורת בין־תאית. הן נושאות מולקולות ביולוגיות שונות ומעבירות אותן בין תאים, כחלק ממנגנוני התקשורת הטבעיים בגוף.
האקסוזומים הסינתטיים פותחו בהשראת מנגנון ביולוגי דומה. הם מתוכננים כמערכות נשא מתקדמות, בעלות מעטפת המדמה מאפיינים מבניים של ממברנת התא ומאפשרות לשלב בתוכן רכיבים פעילים ולהוביל אותם באופן ממוקד ויעיל פנימה אל התאים שלנו. 
האקסוזומים הסינתטיים המיוצרים באיטליה פועלים כשליחי וולט שמעבירים מידע מתא לתא. בתוך הבועיות יש רכיבים פעילים כגון PDRN, פפטידים ורכיבים נוספים שנבחרו בקפידה בהתאם למטרת הפורמולה.
למעשה המבנה הנונמטרי של האקסוזום נועד להגן על הרכיבים שהוא נושא, לתמוך בהעברתם ולשפר את חדירותם. 
```
- Replacements (old → new):
  - “Экзосомы — наноразмерные везикулы, участвующие в межклеточной коммуникации.” → “Экзосомы — наноразмерные везикулы, которые секретируются стволовыми клетками и участвуют в межклеточной коммуникации.”
- **New RU** (ready to paste):
```text
Экзосомы — наноразмерные везикулы, которые секретируются стволовыми клетками и участвуют в межклеточной коммуникации. Они переносят различные биологические молекулы между клетками в рамках естественных механизмов взаимодействия в организме.
```

#### E5.2 [B] Synthetic exosomes: "into our cells"; "act like couriers carrying information from cell to cell"; "the exosome structure is designed to protect the components it carries"

- RU node: `667:954` — Rubik Regular 12, at (46, 264) w 346
- HE node(s): `824:89`
- Current RU (runs: Medium 12 [0,22) 'Синтетические экзосомы'; Regular 12 [22,601) ' созданы по принципу сходного биологичес'):
```text
Синтетические экзосомы созданы по принципу сходного биологического механизма и работают как современные системы доставки. Их оболочка имитирует определённые структурные особенности клеточной мембраны, позволяя заключать внутрь активные компоненты и способствовать их направленной и эффективной доставке.

Синтетические экзосомы итальянского производства содержат тщательно подобранные активные компоненты, включая PDRN, пептиды и другие ингредиенты в соответствии с назначением формулы.

Наноразмерная структура помогает защищать активные компоненты, поддерживать их доставку и улучшать проникновение.
```
- HE text:
```text
אקסוזומים הם בועיות ננומטריות המופרשות מתאי אב ומשתתפות בתהליכי תקשורת בין־תאית. הן נושאות מולקולות ביולוגיות שונות ומעבירות אותן בין תאים, כחלק ממנגנוני התקשורת הטבעיים בגוף.
האקסוזומים הסינתטיים פותחו בהשראת מנגנון ביולוגי דומה. הם מתוכננים כמערכות נשא מתקדמות, בעלות מעטפת המדמה מאפיינים מבניים של ממברנת התא ומאפשרות לשלב בתוכן רכיבים פעילים ולהוביל אותם באופן ממוקד ויעיל פנימה אל התאים שלנו. 
האקסוזומים הסינתטיים המיוצרים באיטליה פועלים כשליחי וולט שמעבירים מידע מתא לתא. בתוך הבועיות יש רכיבים פעילים כגון PDRN, פפטידים ורכיבים נוספים שנבחרו בקפידה בהתאם למטרת הפורמולה.
למעשה המבנה הנונמטרי של האקסוזום נועד להגן על הרכיבים שהוא נושא, לתמוך בהעברתם ולשפר את חדירותם. 
```
- Replacements (old → new):
  - “позволяя заключать внутрь активные компоненты и способствовать их направленной и эффективной доставке.” → “позволяя заключать внутрь активные компоненты и направленно и эффективно доставлять их внутрь наших клеток.”
  - “Синтетические экзосомы итальянского производства содержат тщательно подобранные активные компоненты, включая PDRN, пептиды и другие ингредиенты в соответствии с назначением формулы.” → “Синтетические экзосомы итальянского производства действуют как курьеры, передающие информацию от клетки к клетке. Внутри везикул находятся тщательно подобранные активные компоненты — PDRN, пептиды и другие ингредиенты в соответствии с назначением формулы.”
  - “Наноразмерная структура помогает защищать активные компоненты,” → “Наноразмерная структура экзосомы призвана защищать переносимые компоненты,”
- **New RU** (ready to paste):
```text
Синтетические экзосомы созданы по принципу сходного биологического механизма и работают как современные системы доставки. Их оболочка имитирует определённые структурные особенности клеточной мембраны, позволяя заключать внутрь активные компоненты и направленно и эффективно доставлять их внутрь наших клеток.

Синтетические экзосомы итальянского производства действуют как курьеры, передающие информацию от клетки к клетке. Внутри везикул находятся тщательно подобранные активные компоненты — PDRN, пептиды и другие ингредиенты в соответствии с назначением формулы.

Наноразмерная структура экзосомы призвана защищать переносимые компоненты, поддерживать их доставку и улучшать проникновение.
```
- Style: Keep the Medium run "Синтетические экзосомы" at the start.
- Note: The box grows by ~1–2 lines; it ends at ~y 480 today, footer at 529.

#### E5.3 [B] Advantages: HE "large molecules that could not penetrate the target cells without this structure"

- RU node: `667:955` — Rubik Regular 12, at (414, 191) w 334
- HE node(s): `824:90`
- Current RU:
```text
В отличие от экзосом, получаемых из клеток человека, животных или растений, синтетические экзосомы не имеют живого биологического источника.

Их структура позволяет инкапсулировать активные ингредиенты, включая крупные молекулы, доставка которых без такой системы может быть ограничена.

После доставки активных компонентов запускаются биологические процессы, направленные на обновление, восстановление и улучшение внешнего вида кожи.
```
- HE text:
```text
בניגוד לאקסוזומים המופקים מתאים אנושיים, מבעלי חיים או מצמחים, האקסוזומים הסינתטיים אינם מופקים ממקור חי. 
המבנה הייחודי שלהם מאפשר לשלב בתוכם רכיבים פעילים ומולקולות גדולות שלא היו יכולות לחדור לתאי המטרה לולא המבנה.
עם הגעתם של המולקולות פנימה, מופעלת שרשרת של פעילויות ותהליכים ביולוגיים הגורמים להתחלה של תהליכי התחדשות, שיקום ושיפור מראה העור.
```
- Replacements (old → new):
  - “Их структура позволяет инкапсулировать активные ингредиенты, включая крупные молекулы, доставка которых без такой системы может быть ограничена.” → “Их уникальная структура позволяет заключать внутрь активные компоненты и крупные молекулы, которые без такой структуры не смогли бы проникнуть в клетки-мишени.”
- **New RU** (ready to paste):
```text
В отличие от экзосом, получаемых из клеток человека, животных или растений, синтетические экзосомы не имеют живого биологического источника.

Их уникальная структура позволяет заключать внутрь активные компоненты и крупные молекулы, которые без такой структуры не смогли бы проникнуть в клетки-мишени.

После доставки активных компонентов запускаются биологические процессы, направленные на обновление, восстановление и улучшение внешнего вида кожи.
```

### RU p.6 — frame `667:923` “RU — 06 — V-TECH SYSTEM” ↔ HE p.6 `824:94` “HE — 06 — V-TECH SYSTEM”

#### E6.1 [A] Two-step line: HE "two-step system: bio-lifting serum and gel mask for intensive hydration and renewal" (HE: subtitle under the title)

- RU node: `667:943` — Rubik Regular 12, at (262, 217) w 230
- HE node(s): `824:106`
- Current RU (runs: Medium 12 [0,19) 'Двухэтапная система'; Regular 12 [19,21) ': '; Medium 12 [21,30) 'сыворотка'; Regular 12 [30,65) ' для интенсивного ухода за кожей и '; Medium 12 [65,78) 'гелевая маска'; Regular 12 [78,121) ' для глубокого увлажнения и восстановлен'):
```text
Двухэтапная система: сыворотка для интенсивного ухода за кожей и гелевая маска для глубокого увлажнения и восстановления.
```
- HE text:
```text
מערכת דו-שלבית: סרום ביו-ליפטינג ומסכת ג׳ל לחות וחידוש אינטנסיבי
```
- **New RU** (ready to paste):
```text
Двухэтапная система: сыворотка-биолифтинг и гелевая маска для интенсивного увлажнения и обновления.
```
- Emphasis runs (offsets in the new text): Medium [0,19) “Двухэтапная система”; Medium [21,30) “сыворотка”; Medium [42,57) “и гелевая маска”
- Style: Emphasis as HE (HE Bold on "מערכת דו-שלבית", "סרום", "ומסכת ג׳ל" → RU Medium). Layout (recommended): HE sets this line as the page subtitle directly under "V-TECH SYSTEM" (14 pt Regular, y 162); move it there, full text-column width.

#### E6.2 [A] Formula lead-in: HE "Inside the synthetic exosomes the formula combines:"

- RU node: `667:933` — Rubik Medium 13, at (262, 286) w 230
- HE node(s): `824:103`
- Current RU:
```text
Формула сочетает:
```
- HE text:
```text
ערכה מקצועית המבוססת על אקסוזומים סינתטיים  בטכנולוגיה איטלקית מתקדמת.
Synthetic Exosomes
בתוך אקסוזומים סינתטיים הפורמולה משלבת:
PDRN 2%
קומפלקס פפטידים ביומימטיים
תאי גזע של תפוח
```
- **New RU** (ready to paste):
```text
Внутри синтетических экзосом формула сочетает:
```
- Style: Medium 13 as now (HE Bold inside 824:103).

#### E6.3 [A] Formula list: HE "PDRN 2% / biomimetic peptide complex / apple stem cells" — the salmon detail belongs to the ingredient list (E7.3)

- RU node: `667:932` — Rubik Regular 12, at (262, 307) w 230
- HE node(s): `824:103`
- Current RU:
```text
PDRN 2% (20 мг/мл), полученный из лосося
Комплекс биомиметических пептидов
Экстракт стволовых клеток яблока
```
- HE text:
```text
ערכה מקצועית המבוססת על אקסוזומים סינתטיים  בטכנולוגיה איטלקית מתקדמת.
Synthetic Exosomes
בתוך אקסוזומים סינתטיים הפורמולה משלבת:
PDRN 2%
קומפלקס פפטידים ביומימטיים
תאי גזע של תפוח
```
- **New RU** (ready to paste):
```text
PDRN 2%
Комплекс биомиметических пептидов
Стволовые клетки яблока
```
- Style: Regular 12 as now.
- Note: "20 мг/мл, из лосося" moves to p.7 (E7.3), as on HE (824:111 sits next to the serum list).

#### E6.4 [A] Indications: HE now has 13 items (first item "treatment in the depth of the skin"; "post-acne scars"; last item "reducing signs of ageing and restoring the skin barrier")

- RU node: `667:942` — Rubik Regular 12, at (518, 137) w 230
- HE node(s): `824:105`
- Current RU:
```text
Интенсивное обновление кожи | Антивозрастной уход | Морщины и мелкие линии | Тусклая, уставшая кожа | Постакне и рубцы постакне | Послеоперационные рубцы | Улучшение текстуры и тона кожи | Поствоспалительная гиперпигментация (PIH) | Ангиогенез — образование новых кровеносных сосудов | Улучшение качества кожи | Снижение эластичности | Повышение упругости | Уменьшение видимых признаков старения | Поддержка кожного барьера

```
- HE text:
```text
טיפול בעומק של העור | אנטי-אייג׳ינג | קמטים וקמטוטים | עור חסר ברק וחיוניות | צלקות פוסט אקנה | צלקות לאחר ניתוח | שיפור מרקם וגוון העור | כתמים פוסט דלקתיים PIH | אנגיוגנזה – היווצרות כלי דם חדשים | שיפור איכות העור | לעור חסר גמישות | מיצוק | הפחתת סימני הגיל ושיקום מחסום העור
```
- **New RU** (ready to paste):
```text
Глубокое воздействие на кожу | Антивозрастной уход | Морщины и мелкие линии | Тусклая кожа, лишённая сияния и жизненной силы | Рубцы постакне | Послеоперационные рубцы | Улучшение текстуры и тона кожи | Поствоспалительная гиперпигментация (PIH) | Ангиогенез — образование новых кровеносных сосудов | Улучшение качества кожи | Кожа со сниженной эластичностью | Повышение упругости | Уменьшение признаков старения и восстановление кожного барьера
```
- Style: Regular 12 as now; the trailing line break of the current node is dropped.

#### E6.5 [C] Heading "Комплектация" → the edition term "Содержимое упаковки" (HE "תכולת האריזה", same as pp.9, 10, 12, 23)

- RU node: `667:937` — Rubik Medium 14, at (262, 376) w 230
- HE node(s): `824:108`
- Current RU:
```text
Комплектация
```
- HE text:
```text
תכולת האריזה
```
- **New RU** (ready to paste):
```text
Содержимое упаковки
```
- Style: Medium 14 as now.

#### E6.6 [C] Trailing empty lines in the kit description

- RU node: `667:931` — Rubik Regular 12, at (262, 126) w 230
- HE node(s): `824:103`
- Current RU:
```text
Профессиональный набор на основе синтетических экзосом, разработанный с применением передовой итальянской технологии.


```
- HE text:
```text
ערכה מקצועית המבוססת על אקסוזומים סינתטיים  בטכנולוגיה איטלקית מתקדמת.
Synthetic Exosomes
בתוך אקסוזומים סינתטיים הפורמולה משלבת:
PDRN 2%
קומפלקס פפטידים ביומימטיים
תאי גזע של תפוח
```
- **New RU** (ready to paste):
```text
Профессиональный набор на основе синтетических экзосом, разработанный с применением передовой итальянской технологии.
```
- Style: Regular 12 as now (delete the two trailing "\n").

#### E6.7 [B] Results statement: HE "immediate improvement … structural results and improvement in texture and density accumulate along the series" (HE p.7)

- RU node: `667:917` — Rubik Medium 12, at (262, 436) w 486
- HE node(s): `824:123`
- Current RU:
```text
Заметное улучшение увлажнённости и сияния уже после первой процедуры; структура, текстура и плотность кожи улучшаются в течение курса.
```
- HE text:
```text
שיפור מיידי בלחות ובזוהר כבר מהטיפול הראשון; תוצאות מבניות ושיפור במרקם ובצפיפות מצטברות לאורך הסדרה.
```
- **New RU** (ready to paste):
```text
Мгновенное улучшение увлажнённости и сияния уже после первой процедуры; структурные результаты, улучшение текстуры и плотности кожи накапливаются в течение курса.
```
- Style: Medium 12 as now (HE SemiBold 12).
- Note: The benefits line 667:918 matches HE 824:124 — no change.

#### E6.8 [L/Q] Block distribution pp.6–7: HE p.6 holds "Active ingredients" (both lists), HE p.7 holds the results statement + benefits; RU has them the other way round, and the RU heading "Активные компоненты" (667:935) sits over the kit description, while the ingredient lists on p.7 have no heading

- RU node: `667:935, 667:938, 667:939, 667:917, 667:918`
- HE node(s): `824:107`, `824:109`, `824:123`, `824:124`
- HE text:
```text
רכיבים פעילים
—
סרום Synthetic Exosomes
PDRN 2%
:Biomimetic Peptides
Acetyl Decapeptide-3 & Oligopeptide-20
תאי גזע של תפוח Malus domestica

מסכת ג׳ל לאחר האמפולה ללא שטיפה
PDRN
Acetyl Heptapeptide-9 על נשא זהב קולואידי
Copper Tripeptide-1  נחושת טריפפטיד
פוליסכריד מריר חלזון
חומצה היאלורונית
אלוורה
—
שיפור מיידי בלחות ובזוהר כבר מהטיפול הראשון; תוצאות מבניות ושיפור במרקם ובצפיפות מצטברות לאורך הסדרה.
—
עור חיוני בריא ורענן | מחזיק תוצאות מבניות לאורך זמן | מיצוק |
איכות ומרקם | אלסטיות | שיפור בגוון העור.
```
- Style: Recommended (mirror HE): move 667:935 + 667:938 + 667:939 to p.6 (ingredient column) and 667:917 + 667:918 to p.7 (left column under the title, as HE 824:123/124). Minimum fix if the blocks stay: move heading 667:935 to p.7 above 667:938 so it heads the ingredient lists, and leave the p.6 kit description without a heading (as HE).
- Note: Text content is identical either way after E6.x/E7.x. Owner decision (see open questions).

### RU p.7 — frame `667:908` “RU — 07 — V-TECH — составы и протокол” ↔ HE p.7 `824:114` “HE — 07 — V-TECH SYSTEM (המשך)”

#### E7.1 [A] Areas block: "At the end of the treatment" now reads "DERMA RECOVERY CREAM" (owner edit); "Laser CO2" is one item in HE

- RU node: `667:914` — Rubik Regular 12, at (418, 261) w 330
- HE node(s): `824:120`
- Current RU (runs: Regular 12 [0,69) 'Лицо | Шея | Декольте | Кисти рук\nКоличе'; Medium 12 [69,95) 'Дополнительные сочетания:\n'; Regular 12 [95,161) 'Microneedling | RF Microneedling | BIOSP'; Medium 12 [161,186) 'По завершении процедуры:\n'; Regular 12 [186,335) 'EXOCELL MASK | DERMA RECOVERY\nСолнцезащи'):
```text
Лицо | Шея | Декольте | Кисти рук
Количество: 1–1,5 мл на процедуру

Дополнительные сочетания:
Microneedling | RF Microneedling | BIOSPICULE™ 10% | Laser | CO₂

По завершении процедуры:
EXOCELL MASK | DERMA RECOVERY
Солнцезащитное средство

В начале процедуры, перед микронидлингом, возможно применение стандартного RF (необязательно).
```
- HE text:
```text
פנים - צוואר - דקולטה - כפות ידיים
כמות: בין 1 ל1.5 מ״ל לטיפול
שילובים נוספים:
Microneedling | RF microneedling | BIOSPICULE 10% | Laser CO2
בסיום טיפול:
EXOCELL MASK | DERMA RECOVERY CREAM
מקדם הגנה

בתחילת הטיפול-לפני מיקרונידלינג ניתן לשלב עם RF רגיל (לא חובה)
```
- Replacements (old → new):
  - “BIOSPICULE™ 10% | Laser | CO₂” → “BIOSPICULE™ 10% | Laser CO₂”
  - “EXOCELL MASK | DERMA RECOVERY⏎Солнцезащитное” → “EXOCELL MASK | DERMA RECOVERY CREAM⏎Солнцезащитное”
- **New RU** (ready to paste):
```text
Лицо | Шея | Декольте | Кисти рук
Количество: 1–1,5 мл на процедуру

Дополнительные сочетания:
Microneedling | RF Microneedling | BIOSPICULE™ 10% | Laser CO₂

По завершении процедуры:
EXOCELL MASK | DERMA RECOVERY CREAM
Солнцезащитное средство

В начале процедуры, перед микронидлингом, возможно применение стандартного RF (необязательно).
```
- Style: Keep the Medium runs "Дополнительные сочетания:" and "По завершении процедуры:". Insert " CREAM" with insertCharacters after "RECOVERY" (inherits Regular).

#### E7.2 [A] Gel mask: HE "Acetyl Heptapeptide-9 on a colloidal gold carrier" (owner edit)

- RU node: `667:939` — Rubik Regular 12, at (46, 225) w 342
- HE node(s): `824:109`
- Current RU (runs: Medium 12 [0,63) 'Гелевая маска — после нанесения сыворотк'; Regular 12 [63,242) 'PDRN с низкой молекулярной массой (1%)\nA'):
```text
Гелевая маска — после нанесения сыворотки, не требует смывания
PDRN с низкой молекулярной массой (1%)
Acetyl Heptapeptide-9 с коллоидным золотом
Copper Tripeptide-1 (медный трипептид)
Полисахариды секрета улитки
Гиалуроновая кислота
Алоэ вера
```
- HE text:
```text
סרום Synthetic Exosomes
PDRN 2%
:Biomimetic Peptides
Acetyl Decapeptide-3 & Oligopeptide-20
תאי גזע של תפוח Malus domestica

מסכת ג׳ל לאחר האמפולה ללא שטיפה
PDRN
Acetyl Heptapeptide-9 על נשא זהב קולואידי
Copper Tripeptide-1  נחושת טריפפטיד
פוליסכריד מריר חלזון
חומצה היאלורונית
אלוורה
```
- Replacements (old → new):
  - “Acetyl Heptapeptide-9 с коллоидным золотом” → “Acetyl Heptapeptide-9 на носителе из коллоидного золота”
- **New RU** (ready to paste):
```text
Гелевая маска — после нанесения сыворотки, не требует смывания
PDRN с низкой молекулярной массой (1%)
Acetyl Heptapeptide-9 на носителе из коллоидного золота
Copper Tripeptide-1 (медный трипептид)
Полисахариды секрета улитки
Гиалуроновая кислота
Алоэ вера
```
- Style: Keep the Medium heading run.
- Note: Rest of the gel-mask list matches HE (PDRN low molecular weight (1%) = HE annotation 824:110).

#### E7.3 [A] Serum: PDRN 2% carries the HE annotation "20 mg/mL from salmon stem cells" (HE 824:111)

- RU node: `667:938` — Rubik Regular 12, at (46, 130) w 342
- HE node(s): `824:109`, `824:111`
- Current RU (runs: Medium 12 [0,38) 'Сыворотка с синтетическими экзосомами\n'; Regular 12 [38,160) 'PDRN 2%\nБиомиметические пептиды:\nAcetyl '):
```text
Сыворотка с синтетическими экзосомами
PDRN 2%
Биомиметические пептиды:
Acetyl Decapeptide-3 & Oligopeptide-20
Экстракт стволовых клеток яблока (Malus domestica)
```
- HE text:
```text
סרום Synthetic Exosomes
PDRN 2%
:Biomimetic Peptides
Acetyl Decapeptide-3 & Oligopeptide-20
תאי גזע של תפוח Malus domestica

מסכת ג׳ל לאחר האמפולה ללא שטיפה
PDRN
Acetyl Heptapeptide-9 על נשא זהב קולואידי
Copper Tripeptide-1  נחושת טריפפטיד
פוליסכריד מריר חלזון
חומצה היאלורונית
אלוורה
—
20 מ״ג/מ״ל מתא גזע של סלמון
```
- Replacements (old → new):
  - “PDRN 2%⏎Биомиметические” → “PDRN 2% — 20 мг/мл, из стволовых клеток лосося⏎Биомиметические”
- **New RU** (ready to paste):
```text
Сыворотка с синтетическими экзосомами
PDRN 2% — 20 мг/мл, из стволовых клеток лосося
Биомиметические пептиды:
Acetyl Decapeptide-3 & Oligopeptide-20
Экстракт стволовых клеток яблока (Malus domestica)
```
- Style: Regular 12; keep the Medium heading run. Alternative as HE: leave "PDRN 2%" and add a separate Regular 12 annotation node "20 мг/мл, из стволовых клеток лосося" level with that line.
- Note: Pairs with E6.3.

### RU p.8 — frame `667:893` “RU — 08 — EXO-NAD — этапы 1 и 2” ↔ HE p.8 `824:130` “HE — 08 — EXO-NAD”

#### E8.1 [B] Step 1: HE "a total of 30% acids" (RU adds "около")

- RU node: `667:900` — Rubik Regular 12, at (416, 144) w 332
- HE node(s): `824:140`
- Current RU:
```text
Двухфазная формула, сочетающая липидную и кислотную фазы.
Липидная фаза помогает подготовить кожу и сохранить ощущение комфорта во время процедуры. Кислотная фаза способствует удалению ороговевших клеток, улучшению текстуры кожи и стимулирует контролируемый процесс обновления.
Формула содержит комплекс активных кислот, включая AHA и BHA, общей концентрацией около 30%, а также транексамовую кислоту и антиоксидантные компоненты.
```
- HE text:
```text
פורמולה דו-פאזית המשלבת פאזה ליפידית ופאזה חומצית.
הפאזה הליפידית מסייעת בהכנת העור ובשמירה על תחושת נוחות במהלך הטיפול. הפאזה החומצית מסייעת בהסרת תאים מתים, בשיפור מרקם העור ובעידוד תהליך התחדשות מבוקר.
הפורמולה מכילה שילוב חומצות פעילות, ובהן AHA ו-BHA,  בסה”כ-30% חומצות, לצד חומצה טרנקסמית ורכיבים נוגדי חמצון.
```
- Replacements (old → new):
  - “общей концентрацией около 30%” → “общей концентрацией 30%”
- **New RU** (ready to paste):
```text
Двухфазная формула, сочетающая липидную и кислотную фазы.
Липидная фаза помогает подготовить кожу и сохранить ощущение комфорта во время процедуры. Кислотная фаза способствует удалению ороговевших клеток, улучшению текстуры кожи и стимулирует контролируемый процесс обновления.
Формула содержит комплекс активных кислот, включая AHA и BHA, общей концентрацией 30%, а также транексамовую кислоту и антиоксидантные компоненты.
```

#### E8.2 [B] Intro: HE "the whole aim — to RESTORE the epidermal barrier during the treatment"

- RU node: `667:897` — Rubik Regular 12, at (42, 143) w 340
- HE node(s): `824:136`
- Current RU (runs: Regular 12 [0,441) 'Профессиональная многоэтапная система пи'; Medium 12 [441,460) 'Три этапа процедуры'; Regular 12 [460,786) ' действуют последовательно: удаление оро'):
```text
Профессиональная многоэтапная система пилинга, разработанная в лабораториях VM в Италии на основе современных исследований в области клеточного долголетия и биохакинга кожи.
Система объединяет двухфазный пилинг, нейтрализатор-восстановитель и усовершенствованную сыворотку Longevity, содержащую синтетические экзосомальные структуры, NAD⁺, биомиметические пептиды и активные компоненты, поддерживающие естественные процессы обновления кожи.
Три этапа процедуры действуют последовательно: удаление ороговевших клеток и обновление поверхности кожи, восстановление баланса после воздействия кислот и, наконец, нанесение активной сыворотки для улучшения упругости, увлажнённости, сияния и общего состояния кожи. Основная цель — поддержка эпидермального барьера на протяжении всей процедуры.
```
- HE text:
```text
היא מערכת פילינג מקצועית ורב־שלבית, שפותחה במעבדות VM באיטליה בהשראת מחקר מתקדם בתחום אריכות החיים התאית והביוהאקינג של העור.
המערכת משלבת בין פילינג דו-פאזי, מנטרל – משקם וסרום Longevity מתקדם המכיל מבנים אקסוזומליים סינתטיים, NAD⁺, פפטידים ביומימטיים ורכיבים התומכים בתהליכי ההתחדשות הטבעיים של העור.

שלושת שלבי הטיפול פועלים ברצף: הסרת תאים מתים וחידוש פני העור, איזון ושיקום לאחר פעולת החומצות, ולבסוף החדרת סרום פעיל לשיפור מראה החיוניות, המוצקות, הלחות והזוהר. כל המטרה – לשקם את המחסום האפידרמלי
תוך כדי הטיפול
```
- Replacements (old → new):
  - “Основная цель — поддержка эпидермального барьера на протяжении всей процедуры.” → “Главная цель — восстановление эпидермального барьера во время процедуры.”
- **New RU** (ready to paste):
```text
Профессиональная многоэтапная система пилинга, разработанная в лабораториях VM в Италии на основе современных исследований в области клеточного долголетия и биохакинга кожи.
Система объединяет двухфазный пилинг, нейтрализатор-восстановитель и усовершенствованную сыворотку Longevity, содержащую синтетические экзосомальные структуры, NAD⁺, биомиметические пептиды и активные компоненты, поддерживающие естественные процессы обновления кожи.
Три этапа процедуры действуют последовательно: удаление ороговевших клеток и обновление поверхности кожи, восстановление баланса после воздействия кислот и, наконец, нанесение активной сыворотки для улучшения упругости, увлажнённости, сияния и общего состояния кожи. Главная цель — восстановление эпидермального барьера во время процедуры.
```
- Style: Keep the Medium run "Три этапа процедуры".

#### E8.3 [B] Step 2 text: HE "components that RESTORE the epidermal barrier"

- RU node: `667:901` — Rubik Regular 12, at (416, 382) w 332
- HE node(s): `824:142`
- Current RU:
```text
Формула предназначена для нейтрализации действия кислот и восстановления баланса кожи после этапа пилинга.
Содержит компоненты, поддерживающие эпидермальный барьер: коллаген, биомиметические пептиды и витамин B12.
```
- HE text:
```text
פורמולה המיועדת לעצירת פעילות החומצות ולאיזון העור לאחר שלב הפילינג.
המנטרל משלב רכיבים  המשקמים מחסום אפידרמלי: קולגן, פפטידים ביומימטיים, ויטמין B12
```
- Replacements (old → new):
  - “Содержит компоненты, поддерживающие эпидермальный барьер:” → “Содержит компоненты, восстанавливающие эпидермальный барьер:”
- **New RU** (ready to paste):
```text
Формула предназначена для нейтрализации действия кислот и восстановления баланса кожи после этапа пилинга.
Содержит компоненты, восстанавливающие эпидермальный барьер: коллаген, биомиметические пептиды и витамин B12.
```

#### E8.4 [C] Step 2 title: HE "pH NORMALIZER – neutralises and restores"

- RU node: `667:907` — Rubik Medium 14, at (416, 335) w 332
- HE node(s): `824:141`
- Current RU:
```text
2. pH NORMALIZER — нейтрализатор и восстановление
```
- HE text:
```text
 pH NORMALIZER – מנטרל ומשקם
```
- Replacements (old → new):
  - “нейтрализатор и восстановление” → “нейтрализует и восстанавливает”
- **New RU** (ready to paste):
```text
2. pH NORMALIZER — нейтрализует и восстанавливает
```
- Style: Medium 14 as now.

#### E8.5 [L/Q] Step 3 LONGEVITY SERUM is on HE p.8 (824:146–148); RU has it on p.9 (667:905/906)

- RU node: `667:905, 667:906`
- HE node(s): `824:146`, `824:147`, `824:148`
- HE text:
```text
.3
—
 LONGEVITY SERUM – סרום אריכות וחיוניות העור
—
סרום מקצועי מתקדם המשלב מבנים אקסוזומליים סינתטיים עם NAD⁺, אפיטלון, GHK-Cu, פפטידים ביומימטיים.
הסרום פותח במטרה לתמוך בתקשורת בין־תאית, באנרגיית התא ובתהליכי ההתחדשות הטבעיים שלו. הוא מסייע בשיפור מראה העור, האלסטיות ובהגברת הלחות, ובכך תומך במראה עור מחודש זוהר ובריא יותר.
```
- Style: Optional, mirror HE: move 667:905/906 to p.8 under step 2, and the p.9 benefits/package blocks up. Text matches HE.
- Note: Owner decision (open questions).

### RU p.9 — frame `667:879` “RU — 09 — EXO-NAD — этап 3 и протокол” ↔ HE p.9 `824:149` “HE — 09 — EXO-NAD (המשך)”

#### E9.1 [B] Key benefits as HE (16 items): "suitable for ALL pigmentation types", "permitted in melasma", "senile lentigo", "acne spots PIH", "glow treatment before an event", separate "radiance"

- RU node: `667:889` — Rubik Regular 12, at (46, 296) w 341
- HE node(s): `824:160`
- Current RU:
```text
Удаление ороговевших клеток | Ускорение обновления кожи | Улучшение текстуры | Повышение упругости и эластичности | Уменьшение видимости мелких морщин | Подходит для разных типов пигментации | Подходит для всех фототипов по Фитцпатрику | Выравнивание тона кожи | Подходит при мелазме | Возрастные пигментные пятна | Постакне и PIH | Сияние кожи | Идеально перед важным событием | Для зрелой, уставшей и тусклой кожи | Обновление | Антивозрастной эффект
```
- HE text:
```text
הסרת תאים מתים | האצת התחדשות | שיפור מרקם העור | שיפור מוצקות ואלסטיות | הפחתת מראה קמטוטים | מתאים לכל סוגי הפיגמנטציה | כל סוגי הפצפטריק | שיפור בגוון העור | מותר במלזמה | סניל לנטיגו | כתמי אקנה PIH טיפול זוהר לפני ארוע | לעור בוגר עייף וחסר ברק | זוהר | חידוש | אנטי-אייג׳ינג
```
- **New RU** (ready to paste):
```text
Удаление ороговевших клеток | Ускорение обновления кожи | Улучшение текстуры | Повышение упругости и эластичности | Уменьшение видимости мелких морщин | Подходит для всех типов пигментации | Подходит для всех фототипов по Фитцпатрику | Выравнивание тона кожи | Допустимо при мелазме | Сенильное лентиго | Пятна постакне (PIH) | Процедура для сияния кожи перед важным событием | Для зрелой, уставшей и тусклой кожи | Сияние | Обновление | Антивозрастной эффект
```
- Style: Regular 12 as now.

#### E9.2 [C] First line of "How to use" lacks its bullet

- RU node: `667:885` — Rubik Regular 12, at (417, 130) w 331
- HE node(s): `824:156`
- Current RU:
```text
Одна процедура каждые 3–4 недели
• Трёхэтапный протокол в соответствии с показаниями
• Подходит для всех типов кожи и применения круглый год
• Не требует обязательного курса процедур
```
- HE text:
```text
· טיפול אחד כל 3-4 שבועות
· פרוטוקול תלת-שלבי לפי התוויה 
· כל סוגי העור. כל ימות השנה 
· לא מחייב סדרה
```
- Replacements (old → new):
  - “Одна процедура каждые 3–4 недели” → “• Одна процедура каждые 3–4 недели”
- **New RU** (ready to paste):
```text
• Одна процедура каждые 3–4 недели
• Трёхэтапный протокол в соответствии с показаниями
• Подходит для всех типов кожи и применения круглый год
• Не требует обязательного курса процедур
```
- Style: insertCharacters(0, "• ", "BEFORE").

#### E9.3 [B] Devices: HE "not necessary; can be combined in a device protocol for infusions / hydration"

- RU node: `667:886` — Rubik Regular 12, at (417, 220) w 331
- HE node(s): `824:157`
- Current RU (runs: Medium 12 [0,35) 'Сочетание с аппаратными методиками\n'; Regular 12 [35,117) 'Необязательно; возможно сочетание с проц'; Medium 12 [117,141) 'По завершении процедуры\n'; Regular 12 [141,200) 'Солнцезащитное средство\nEXOCELL MASK | D'):
```text
Сочетание с аппаратными методиками
Необязательно; возможно сочетание с процедурами и аппаратами для увлажнения кожи.
По завершении процедуры
Солнцезащитное средство
EXOCELL MASK | DERMA RECOVERY CREAM
```
- HE text:
```text
שילוב במכשור
לא הכרחי אפשר לשלב בפרוטוקל מכשור החדרות לחויות

בסיום טיפול
מקדם הגנה
EXOCELL MASK | DERMA RECOVERY CREAM





```
- Replacements (old → new):
  - “Необязательно; возможно сочетание с процедурами и аппаратами для увлажнения кожи.” → “Необязательно; возможно сочетание с аппаратными протоколами введения активных компонентов и увлажнения.”
- **New RU** (ready to paste):
```text
Сочетание с аппаратными методиками
Необязательно; возможно сочетание с аппаратными протоколами введения активных компонентов и увлажнения.
По завершении процедуры
Солнцезащитное средство
EXOCELL MASK | DERMA RECOVERY CREAM
```
- Style: Keep the two Medium heading runs.

### RU p.10 — frame `667:860` “RU — 10 — EXOCELL MASK” ↔ HE p.10 `824:164` “HE — 10 — EXOCELL MASK”

#### E10.1 [B] Description: HE "restoration of the epidermal barrier"; emphasised sentence "can be used in ANY treatment protocol after procedures, especially for dry, tired, sensitive or lifeless skin"; "precise adhesion keeps a moist environment"; result "calm, freshness, skin saturated with moisture, smooth, supple, more radiant"

- RU node: `667:867` — Rubik Regular 12, at (286, 116) w 462
- HE node(s): `824:172`, `824:173`
- Current RU:
```text
Создана на основе технологии плотного прилегания, синтетических экзосомальных структур и комплекса активных компонентов для интенсивного увлажнения и успокоения кожи.
Маска предназначена для завершения профессиональных косметологических процедур, особенно когда кожа нуждается в интенсивном увлажнении и поддержке эпидермального барьера.
Подходит для различных постпроцедурных протоколов, особенно для сухой, уставшей, чувствительной и обезвоженной кожи.

Тонкая и эластичная биоцеллюлозная основа плотно и равномерно прилегает к поверхности кожи, практически без воздушных карманов. Это обеспечивает постоянный контакт активной сыворотки с кожей на протяжении всей процедуры.
Результат — ощущение комфорта и свежести, интенсивное увлажнение, гладкость и сияние кожи.
```
- HE text:
```text
מבוססת על שילוב בין טכנולוגיית הצמדה מתקדמת, מבנים אקסוזומליים סינתטיים ומכלול רכיבים פעילים התומכים בלחות והרגעה.
המסכה פותחה לשימוש בסיום טיפולים קוסמטיים מקצועיים, ובמיוחד כאשר העור זקוק ללחות אינטנסיבית ולשיקום מחסום אפידרמלי.
ניתן להשתמש בה בכל פרוטוקול טיפול לאחר פרוצדורות ובמיוחד לעור יבש, עייף, רגיש או חסר חיוניות.
—
מבנה הביו-צלולוז הדק והגמיש נצמד לפני השטח של העור בצורה אחידה, כמעט ללא כיסי אוויר. ההצמדה המדויקת שומרת על סביבה לחה ומאפשרת מגע רציף בין הסרום הפעיל לבין העור במשך כל זמן הטיפול.
התוצאה היא תחושת רוגע ורעננות, לצד עור רווי בלחות, חלק, גמיש וזוהר יותר.
```
- Replacements (old → new):
  - “и поддержке эпидермального барьера.” → “и восстановлении эпидермального барьера.”
  - “Подходит для различных постпроцедурных протоколов, особенно для сухой, уставшей, чувствительной и обезвоженной кожи.” → “Может применяться в любом протоколе после процедур, особенно для сухой, уставшей, чувствительной кожи или кожи, лишённой жизненной силы.”
  - “практически без воздушных карманов. Это обеспечивает постоянный контакт” → “практически без воздушных карманов. Точное прилегание сохраняет влажную среду и обеспечивает постоянный контакт”
  - “Результат — ощущение комфорта и свежести, интенсивное увлажнение, гладкость и сияние кожи.” → “Результат — ощущение спокойствия и свежести, а также насыщенная влагой, гладкая, эластичная и более сияющая кожа.”
- **New RU** (ready to paste):
```text
Создана на основе технологии плотного прилегания, синтетических экзосомальных структур и комплекса активных компонентов для интенсивного увлажнения и успокоения кожи.
Маска предназначена для завершения профессиональных косметологических процедур, особенно когда кожа нуждается в интенсивном увлажнении и восстановлении эпидермального барьера.
Может применяться в любом протоколе после процедур, особенно для сухой, уставшей, чувствительной кожи или кожи, лишённой жизненной силы.

Тонкая и эластичная биоцеллюлозная основа плотно и равномерно прилегает к поверхности кожи, практически без воздушных карманов. Точное прилегание сохраняет влажную среду и обеспечивает постоянный контакт активной сыворотки с кожей на протяжении всей процедуры.
Результат — ощущение спокойствия и свежести, а также насыщенная влагой, гладкая, эластичная и более сияющая кожа.
```
- Emphasis runs (offsets in the new text): Medium [343,479) “Может применяться в любом протоколе после процедур, особенно для сухой, уставшей, чувствительной кожи или кожи, лишённой жизненной силы.”
- Style: The third sentence is emphasised in HE (SemiBold) → RU Medium; rest Regular 12.
- Note: Box grows ~1 line; next block (667:868) starts at y 356 — check.

#### E10.2 [B] Key benefits: HE "treatment of damage to the epidermal barrier", "smoothing and tightening effect"

- RU node: `667:869` — Rubik Regular 12, at (286, 379) w 462
- HE node(s): `824:175`
- Current RU:
```text
Интенсивное и мгновенное увлажнение | Успокаивающий уход после профессиональных процедур | Поддержка эпидермального барьера | Ощущение прохлады и свежести | Уменьшение сухости | Более гладкая и упругая кожа | Свежий, спокойный и увлажнённый вид
```
- HE text:
```text
לחות אינטנסיבית ומיידית | הרגעה לאחר טיפוליים מקצועיים | טיפול בפגיעה במחסום האפידרמלי | קרירות ורעננות | הפחתה ביובש | אפקט החלקה ומתיחה | מראה עור רענן, רגוע ורווי בלחות
```
- Replacements (old → new):
  - “Поддержка эпидермального барьера” → “Восстановление повреждённого эпидермального барьера”
  - “Более гладкая и упругая кожа” → “Эффект разглаживания и подтяжки”
- **New RU** (ready to paste):
```text
Интенсивное и мгновенное увлажнение | Успокаивающий уход после профессиональных процедур | Восстановление повреждённого эпидермального барьера | Ощущение прохлады и свежести | Уменьшение сухости | Эффект разглаживания и подтяжки | Свежий, спокойный и увлажнённый вид
```

#### E10.3 [B] Heading: HE "combining with ANY treatment protocol and professional equipment in the clinic"

- RU node: `667:870` — Rubik Medium 12, at (286, 449) w 462
- HE node(s): `824:176`
- Current RU:
```text
Сочетание с профессиональными протоколами и аппаратными процедурами
```
- HE text:
```text
שילוב בכל פרוטוקול טיפול ומכשור מקצועי בקליניקה
```
- **New RU** (ready to paste):
```text
Сочетание с любым протоколом процедур и профессиональным оборудованием в клинике
```
- Style: Medium 12 as now.

### RU p.11 — frame `667:848` “RU — 11 — Экзосомы для кожи головы” ↔ HE p.11 `793:178` “HE — 11 — אקסוזומים סינתטיים לקרקפת”

#### E11.1 [C] Latin line "SYNTHETIC EXOSOMES" missing (HE 793:187 above "PROFESSIONAL SCALP TREATMENT")

- RU node: `NEW near 667:854`
- HE node(s): `793:187`
- HE text:
```text
SYNTHETIC EXOSOMES
```
- **New RU** (ready to paste):
```text
SYNTHETIC EXOSOMES
```
- Style: Clone 667:854; Rubik Medium 14 (HE SemiBold 14), colour as HE 793:187; ~26 px above 667:854 (HE y 314 vs 340). Same treatment as E4.2.

### RU p.12 — frame `667:833` “RU — 12 — EXOSIGNAL HAIR” ↔ HE p.12 `824:185` “HE — 12 — EXOSIGNAL HAIR”

#### E12.1 [C] Subtitle: HE "professional synthetic-exosome system for SCALP treatments" (RU adds "and hair")

- RU node: `667:837` — Rubik Regular 14, at (42, 91) w 706
- HE node(s): `824:189`
- Current RU:
```text
Профессиональная система на основе синтетических экзосом для ухода за кожей головы и волосами
```
- HE text:
```text
מערכת אקסוזומים סינתטיים מקצועית לטיפולי הקרקפת
```
- **New RU** (ready to paste):
```text
Профессиональная система синтетических экзосом для процедур на коже головы
```
- Style: Regular 14 as now.

#### E12.2 [B] Description, last sentence: HE "to support scalp health and ENCOURAGE HAIR GROWTH. A synergistic combination … helps reduce shedding and slow further hair loss"

- RU node: `667:838` — Rubik Regular 12, at (42, 131) w 340
- HE node(s): `824:191`
- Current RU:
```text
Профессиональная формула, разработанная в лабораториях VM Corporation в Италии для интенсивного ухода за кожей головы и поддержки волосяных фолликулов.
Формула сочетает систему доставки на основе синтетических экзосомальных структур, PDRN в высокой концентрации, гиалуроновую кислоту, восемь биомиметических пептидов, растительные стволовые клетки, витамины и антиоксиданты. Разработана для поддержания здоровья кожи головы, укрепления волос и уменьшения их выпадения.
```
- HE text:
```text
פורמולה מקצועית שפותחה במעבדות VM Corporation באיטליה לטיפוח אינטנסיבי של הקרקפת ולתמיכה בזקיקי השיער.
הפורמולה משלבת מערכת הולכה המבוססת על מבנים אקסוזומליים סינתטיים, PDRN בריכוז גבוה, חומצה היאלורונית, שמונה פפטידים ביומימטיים, תאי גזע צמחיים, ויטמינים ונוגדי חמצון. פותח במטרה לתת תמיכה בבריאות הקרקפת ובעידוד צמיחת שיער. שילוב סינרגטי של רכיבים פעילים המסייע להפחית נשירה ולהאט אובדן שיער נוסף.
```
- Replacements (old → new):
  - “Разработана для поддержания здоровья кожи головы, укрепления волос и уменьшения их выпадения.” → “Разработана для поддержания здоровья кожи головы и стимуляции роста волос. Синергетическое сочетание активных компонентов помогает уменьшить выпадение и замедлить дальнейшую потерю волос.”
- **New RU** (ready to paste):
```text
Профессиональная формула, разработанная в лабораториях VM Corporation в Италии для интенсивного ухода за кожей головы и поддержки волосяных фолликулов.
Формула сочетает систему доставки на основе синтетических экзосомальных структур, PDRN в высокой концентрации, гиалуроновую кислоту, восемь биомиметических пептидов, растительные стволовые клетки, витамины и антиоксиданты. Разработана для поддержания здоровья кожи головы и стимуляции роста волос. Синергетическое сочетание активных компонентов помогает уменьшить выпадение и замедлить дальнейшую потерю волос.
```

#### E12.3 [C] Heading: HE "Active ingredients" (not "main")

- RU node: `667:841` — Rubik Medium 14, at (416, 140) w 332
- HE node(s): `824:194`
- Current RU:
```text
Основные активные компоненты
```
- HE text:
```text
רכיבים פעילים
```
- **New RU** (ready to paste):
```text
Активные компоненты
```
- Style: Medium 14 as now.

#### E12.4 [B] Ingredient list: HE puts "2% PDRN" (emphasised) second, annotated "from salmon stem cells, concentration 20 mg/mL"

- RU node: `667:842` — Rubik Regular 12, at (416, 167) w 332
- HE node(s): `824:195`, `824:197`, `824:196`
- Current RU:
```text
Синтетические экзосомальные структуры
Высокомолекулярная гиалуроновая кислота
Биомиметические пептиды:
SH-Oligopeptide-1/2, SH-Polypeptide-1/9/11, Acetyl Decapeptide-3, Copper (GHK-Cu) Tripeptide-1, Oligopeptide-20
Растительные стволовые клетки швейцарского яблока Malus domestica
Витамины: Panthenol — провитамин B5, Biotin — витамин B7, Pyridoxine — витамин B6, Thiamine — витамин B1
PDRN 2% — 20 мг/мл
```
- HE text:
```text
מבנים אקסוזומליים סינתטיים.

חומצה היאלורונית במשקל מולקולרי גבוה
פפטידים ביומימטיים
SH-Oligopeptide-1/2, SH-Polypeptide-1/9/11, Acetyl Decapeptide-3
Copper (GHK-Cu) Tripeptide-1 ו-Oligopeptide-20
תאי גזע צמחיים מתפוח שווייצרי Malus Domestica 
ויטמינים: פנתנול – פרו־ויטמין B5, ביוטין – ויטמין B7, פירידוקסין – ויטמין B6, תיאמין – ויטמין B1
—
2% PDRN
—
מתא גזע של סלמון ריכוז של 20 מ״ג למ״ל
```
- Replacements (old → new):
  - “Синтетические экзосомальные структуры⏎” → “Синтетические экзосомальные структуры⏎2% PDRN — из стволовых клеток лосося, 20 мг/мл⏎”
  - delete “⏎PDRN 2% — 20 мг/мл”
- **New RU** (ready to paste):
```text
Синтетические экзосомальные структуры
2% PDRN — из стволовых клеток лосося, 20 мг/мл
Высокомолекулярная гиалуроновая кислота
Биомиметические пептиды:
SH-Oligopeptide-1/2, SH-Polypeptide-1/9/11, Acetyl Decapeptide-3, Copper (GHK-Cu) Tripeptide-1, Oligopeptide-20
Растительные стволовые клетки швейцарского яблока Malus domestica
Витамины: Panthenol — провитамин B5, Biotin — витамин B7, Pyridoxine — витамин B6, Thiamine — витамин B1
```
- Emphasis runs (offsets in the new text): Medium [38,45) “2% PDRN”
- Style: Regular 12; "2% PDRN" Medium (HE 824:197 Medium 12). The old last line is deleted.

#### E12.5 [B] Multi-system action: HE claims increased blood-vessel formation + oxygen to follicles, renewal/revival of dormant follicles, LONGER anagen and SHORTER telogen (RU softened all four)

- RU node: `667:840` — Rubik Regular 12, at (42, 346) w 340
- HE node(s): `824:193`
- Current RU:
```text
Поддерживает баланс и оптимальный уровень увлажнённости кожи головы.
Способствует улучшению микроциркуляции и питания волосяных фолликулов.
Поддерживает существующие фолликулы и процессы их обновления.
Активные компоненты способствуют поддержанию фазы анагена и нормального цикла роста волос.
```
- HE text:
```text
טיפוח סביבת הקרקפת – הפורמולה מסייעת לשמור על קרקפת מאוזנת,
רוויה בלחות.
יצור מוגבר של כלי דם והזנה מקסימלית של הקרקפת תוך אספקת חמצן לזקיקי שיער. 
תמיכה בזקיקי השיער הקיימים, חידוש זקיקים רדומים והחייאתם.
הרכיבים הפעילים גורמים להארכת שלב האנאגן וקיצור  שלב הטלוגן.

```
- **New RU** (ready to paste):
```text
Уход за кожей головы — формула помогает поддерживать баланс кожи головы и её насыщенность влагой.
Усиленное образование кровеносных сосудов и максимальное питание кожи головы со снабжением волосяных фолликулов кислородом.
Поддержка существующих волосяных фолликулов, обновление и пробуждение спящих фолликулов.
Активные компоненты удлиняют фазу анагена и сокращают фазу телогена.
```
- Style: Regular 12 as now.
- Note: About 2 lines longer; the box ends ~y 450, package block 667:843 at y 485 — check.

### RU p.15 — frame `667:798` “RU — 15 — Что такое Spongilla” ↔ HE p.15 `793:237` “HE — 15 — מהי ספונגילה”

#### E15.1 [IMG] Different photo: RU shows a sponge photo (hash fc3303f661); HE shows the loose-spicules cut-out (hash ebe521959d, same layer name)

- RU node: `667:805`
- HE node(s): `793:245`
- Style: Copy the fills array of HE 793:245 (two IMAGE fills: ebe521959d + 24e53969dd) onto 667:805, or replace 667:805 with a clone of 793:245 (HE 324×259). Keep it on the RU side of the layout; check the "Показания" block 671:16 does not overlap.

#### E15.2 [B] Sub-heading: HE "Millions of micro-needles penetrate quickly and reach the depth of the skin"

- RU node: `667:803` — Rubik Medium 14, at (46, 310) w 340
- HE node(s): `793:243`
- Current RU:
```text
Миллионы микроспикул создают интенсивную механическую стимуляцию кожи
```
- HE text:
```text
מיליוני מיקרו מחטים חודרות במהירות ומגיעות לעומק של העור
```
- **New RU** (ready to paste):
```text
Миллионы микроигл быстро проникают в кожу и достигают её глубоких слоёв
```
- Style: Medium 14 as now.

#### E15.3 [B] Body: HE "80–300 micron depth", "reach the epidermal level", microcirculation → metabolism → shorter renewal cycle, "activate the basal and dermal layers", "up to 72 h", "more collagen and epidermal restoration" (RU says "surface layers" and drops most claims)

- RU node: `667:802` — Rubik Regular 12, at (46, 356) w 340
- HE node(s): `793:242`
- Current RU:
```text
Миллионы спикул контактируют с кожей и создают контролируемую микростимуляцию. Благодаря своему микроскопическому размеру они воздействуют на поверхностные слои кожи, активируя процессы обновления и микроциркуляцию.
После процедуры мельчайшие спикулы могут сохраняться в коже до 72 часов, продолжая механическую стимуляцию и поддерживая процессы обновления эпидермиса.

```
- HE text:
```text
מיליוני מחטים בעומק של 80-300 מיקרון חודרות במהירות אל העור ומגיעות לעומק האפידרמלי  חדירה זו מפעילה מיקרוסירקולציה של העור בכך מאיצה חילוף חומרים ומקצרת את מחזור חידוש העור מ 7 ל 28 ימים. מתחת למיקרוסקופ ניתן לראות מחטים זעירות וכשהן חודרות הם מפעילות את השכבה הבזאלית והדרמלית, יכולות להשאר עד 72 שעות וגורמות להגברת יצור קולגן ושיקום האפידרמיס מתוך המרצה של המטבוליזם התאי וחידוש העור.

אינדיקציות: אנטי-אייג׳ינג | קמטים וקמטוטים | נקבוביות פעורות | מיצוק | הבהרה | שיפור גוון העור פיגמנטציה פוסט דלקתית PIH | סניל לנטיגו | צלקות | צלקות פוסט אקנה | אקנה קל- בינוני | עור דק וחסר חיוניות | עור אפרורי וחסר ברק | חידוש והזנה | AGING | פנים, צוואר, דקולטה, ידיים, גב
טיפול במיקרו מחטים יכול להוות כתחליף לטיפול המסורתי במיקרונידלינג!
```
- **New RU** (ready to paste):
```text
Миллионы игл быстро проникают в кожу на глубину 80–300 микрон и достигают эпидермального уровня. Такое проникновение активирует микроциркуляцию кожи, ускоряя обмен веществ и сокращая цикл обновления кожи с 28 до 7 дней. Под микроскопом видны крошечные иглы: проникая в кожу, они активируют базальный и дермальный слои, могут сохраняться до 72 часов и усиливают выработку коллагена и восстановление эпидермиса за счёт стимуляции клеточного метаболизма и обновления кожи.
```
- Emphasis runs (offsets in the new text): Medium [128,143) “микроциркуляцию”; Medium [158,171) “обмен веществ”; Medium [188,198) “обновления”; Medium [417,427) “стимуляции”
- Style: Regular 12; Medium on the four words HE emphasises (מיקרוסירקולציה, חילוף, חידוש, המרצה). Trailing line break dropped.
- Note: HE literally reads "shortens the renewal cycle from 7 to 28 days" (logically reversed) — written here as "с 28 до 7 дней"; see open questions.

#### E15.4 [B] Indications as HE: "improving skin tone", "senile lentigo", "post-acne scars", "thin, lifeless skin" + "greyish, dull skin" as two items, "AGING", areas as one item; closing line ends with "!"

- RU node: `671:16` — Rubik Regular 12, at (416, 310) w 332
- HE node(s): `793:242`
- Current RU (runs: Medium 12 [0,11) 'Показания:\n'; Regular 12 [11,356) 'Антивозрастной уход | Морщины и мелкие л'; Medium 12 [356,449) 'Процедура с микроспикулами может использ'):
```text
Показания:
Антивозрастной уход | Морщины и мелкие линии | Расширенные поры | Повышение упругости | Осветление | Неровный тон кожи | Поствоспалительная гиперпигментация (PIH) | Возрастная пигментация | Рубцы | Постакне | Акне лёгкой и средней степени | Тонкая, тусклая и уставшая кожа | Обновление и питание кожи | Лицо | Шея | Декольте | Кисти рук | Спина
Процедура с микроспикулами может использоваться как альтернатива традиционному микронидлингу.
```
- HE text:
```text
מיליוני מחטים בעומק של 80-300 מיקרון חודרות במהירות אל העור ומגיעות לעומק האפידרמלי  חדירה זו מפעילה מיקרוסירקולציה של העור בכך מאיצה חילוף חומרים ומקצרת את מחזור חידוש העור מ 7 ל 28 ימים. מתחת למיקרוסקופ ניתן לראות מחטים זעירות וכשהן חודרות הם מפעילות את השכבה הבזאלית והדרמלית, יכולות להשאר עד 72 שעות וגורמות להגברת יצור קולגן ושיקום האפידרמיס מתוך המרצה של המטבוליזם התאי וחידוש העור.

אינדיקציות: אנטי-אייג׳ינג | קמטים וקמטוטים | נקבוביות פעורות | מיצוק | הבהרה | שיפור גוון העור פיגמנטציה פוסט דלקתית PIH | סניל לנטיגו | צלקות | צלקות פוסט אקנה | אקנה קל- בינוני | עור דק וחסר חיוניות | עור אפרורי וחסר ברק | חידוש והזנה | AGING | פנים, צוואר, דקולטה, ידיים, גב
טיפול במיקרו מחטים יכול להוות כתחליף לטיפול המסורתי במיקרונידלינג!
```
- **New RU** (ready to paste):
```text
Показания:
Антивозрастной уход | Морщины и мелкие линии | Расширенные поры | Повышение упругости | Осветление | Улучшение тона кожи | Поствоспалительная гиперпигментация (PIH) | Сенильное лентиго | Рубцы | Рубцы постакне | Акне лёгкой и средней степени | Тонкая кожа, лишённая жизненной силы | Сероватая, тусклая кожа | Обновление и питание кожи | Возрастные изменения кожи | Лицо, шея, декольте, кисти рук, спина
Процедура с микроиглами может служить альтернативой традиционному микронидлингу!
```
- Emphasis runs (offsets in the new text): Medium [0,10) “Показания:”; Medium [414,494) “Процедура с микроиглами может служить альтернативой традиционному микронидлингу!”
- Style: Regular 12; Medium on the heading and on the closing sentence (HE Bold).
- Note: HE lists both "אנטי-אייג׳ינג" and Latin "AGING"; rendered as "Возрастные изменения кожи" (open questions).

### RU p.16 — frame `667:784` “RU — 16 — BIOSPICULE — четвёртое поколение” ↔ HE p.16 `795:2` “HE — 16 — BIOSPICULE הדור הרביעי”

#### E16.1 [B] "How are we different?": HE lists the three dependencies (purity, size/length ratio, EXACT CONCENTRATION), "traditional powder is one non-uniform mixture of the whole spongilla", "With us:", "Korean processing", "every bio-needle separately!"

- RU node: `667:787` — Rubik Regular 12.5, at (42, 152) w 340
- HE node(s): `795:6`
- Current RU (runs: Regular 12.5 [0,476) 'Эффективность Spongilla зависит от степе'; Medium 12.5 [476,507) 'Каждая био-игла имеет значение.'):
```text
Эффективность Spongilla зависит от степени очистки спикул, их размера и соотношения различной длины. В традиционном сырье эти параметры могут значительно различаться от продукта к продукту.

В технологии BIOSPICULE™ используются 4 типа Spongilla. В процессе многоэтапной обработки удаляются нежелательные остатки, а микроскопические структуры очищаются и сортируются по размеру и характеристикам.

Это позволяет контролировать структуру, длину и соотношение спикул в формуле.
Каждая био-игла имеет значение.
```
- HE text:
```text
כל הספונגילות הקיימות בעולם תלויות ב:
רמת הטיהור של הספיקולות.
גודל הספיקולות והיחס בין אורכים שונים.
הריכוז המדויק שלהן בכל מוצר.
האבקה המסורתית הינה תערובת אחת לא אחידה שכוללת את כל הספונג׳ילה
אצלנו:
בטכנולוגיית הדור הרביעי של BIOSPICULE, יש לנו 4 סוגים של ספונגילות. בתהליך עיבוד קוריאני הוסרו שאריות בלתי רצויות, טיהרו את המבנים המיקרוסקופיים ומיינו אותם בהתאם למאפייניהם ולגודלם.
כך שיש לנו מבנה של כל ספיקולה בנפרד.  כל ביו-מחט בנפרד!
```
- **New RU** (ready to paste):
```text
Все продукты на основе Spongilla зависят от:
степени очистки спикул;
размера спикул и соотношения разных длин;
их точной концентрации в каждом продукте.
Традиционный порошок — это одна неоднородная смесь, включающая всю губку Spongilla.
У нас:
в технологии BIOSPICULE™ четвёртого поколения используются 4 типа Spongilla. В ходе корейского процесса обработки удалены нежелательные остатки, а микроскопические структуры очищены и рассортированы по характеристикам и размеру.
Таким образом, мы получаем структуру каждой спикулы в отдельности. Каждая био-игла — отдельно!
```
- Emphasis runs (offsets in the new text): Medium [153,203) “Традиционный порошок — это одна неоднородная смесь”; Medium [237,243) “У нас:”; Medium [303,309) “4 типа”; Medium [540,567) “Каждая био-игла — отдельно!”
- Style: Regular 12.5 as now; Medium on the four HE emphasis runs.
- Note: About 3 lines longer than now; the column runs to ~y 400, footer 529.

#### E16.2 [B] "Why purification changes everything": HE adds stimulation spread across epidermal layers, "raw material becomes precise cosmetic technology", "miniature cannelloni", "unlike competitors we control every needle, every length", "not unfiltered powder but a delivery system into the dermis"

- RU node: `667:795` — Rubik Regular 12.5, at (416, 152) w 332
- HE node(s): `795:15`
- Current RU (runs: Regular 12.5 [0,416) 'BIOSPICULE™ учитывает не только концентр'; Medium 12.5 [416,458) 'Это основа Hybrid Spicule Delivery Syste'):
```text
BIOSPICULE™ учитывает не только концентрацию Spongilla, но и архитектуру спикул — сочетание коротких и длинных структур, определяющее характер механического воздействия на кожу.

Под микроскопом спикула имеет пористую структуру с внутренним микроскопическим каналом. Благодаря этому она представляет собой не просто механический элемент, а часть системы, сочетающей обновление кожи и доставку активных компонентов.

Это основа Hybrid Spicule Delivery System.
```
- HE text:
```text
במקום לעבוד רק עם כמות גדולה של ספונגילות, הטכנולוגיה שלנו מתייחסת גם לארכיטקטורה שלהן: ולאורך הספיקולות:  קצרות וארוכות, וכיצד השילוב ביניהן משפיע על פיזור הגירוי בשכבות השונות של האפידרמיס.
זוהי הנקודה שבה חומר גלם טבעי הופך לטכנולוגיה קוסמטית מדויקת.
תחת המיקרוסקופ, הספיקולה היא בעלת מבנה נקבובי, המזכיר צינור זעיר: חלל מיקרוסקופי מאורך - כמעט כמו קנלוני מיניאטורי. לעומת המתחרים אנחנו שולטים בכל מחט כזאת! בכל אורך שלה בנפרד. זה לא רק אבקה של החומר ללא סינון אלא מערכת הובלה שנכנסת פנימה לתוך הדרמיס תוך שליטה בכל סוגי האורכים בפורמולה. המבנה הזה הוא הבסיס ל-Hybrid Spicule Delivery System 

```
- **New RU** (ready to paste):
```text
Вместо того чтобы работать лишь с большим количеством Spongilla, наша технология учитывает и их архитектуру — длину спикул, короткие и длинные, и то, как их сочетание влияет на распределение стимуляции в разных слоях эпидермиса.
Именно здесь природное сырьё превращается в точную косметическую технологию.
Под микроскопом спикула имеет пористую структуру, напоминающую крошечную трубочку: вытянутую микроскопическую полость — почти как миниатюрные каннеллони. В отличие от конкурентов, мы контролируем каждую такую иглу — каждую её длину в отдельности. Это не просто нефильтрованный порошок сырья, а система доставки, которая проникает вглубь, в дерму, с контролем всех типов длины в формуле. Эта структура — основа Hybrid Spicule Delivery System.
```
- Style: Regular 12.5, no emphasis (HE 795:15 has none; drop the current Medium on the last sentence).
- Note: About 4 lines longer; check against the footer.

### RU p.17 — frame `669:26` “RU — 17 — BIOSPICULE — механизмы” ↔ HE p.17 `795:18` “HE — 17 — BIOSPICULE הדור הרביעי (המשך)”

#### E17.1 [A] Running head "MITODERM" and footer missing on RU p.17 (HE 795:34, 795:35)

- RU node: `NEW in 669:26`
- HE node(s): `795:34`, `795:35`
- HE text:
```text
MITODERM
—
MITODERM  |  WHERE SCIENCE MEETS BEAUTY
```
- Style: Clone RU p.16 667:785 (MITODERM, Bold 10.5) to (46, 25) and 667:797 (footer, Regular 9) to (46, 529).

#### E17.2 [A] HE repeats the p.16 title and uses "This is how they work along two parallel pathways:" as a sub-heading; RU uses a different page title

- RU node: `667:792 + NEW title`
- HE node(s): `795:20`, `795:28`
- HE text:
```text
BIOSPICULE — הדור הרביעי של טכנולוגיית הספיקולות
—
כך הן פועלות בשני מסלולים מקבילים:
```
- **New RU** (ready to paste):
```text
Так они действуют по двум параллельным путям:
```
- Style: 667:792 becomes the sub-heading: Medium 14 (HE 795:28 SemiBold 14), at the column-head line (~y 122). New title node: clone RU p.16 title 667:786 "BIOSPICULE™ — четвёртое поколение технологии спикул" (Bold 27) to (42, 48).
- Note: Fit: header adds ~70 px; the body 667:788 + 667:789 must fit above the footer (layout pass; HE sets the body in a 330 px column next to the photo).

#### E17.3 [B] Body as HE: spicules "penetrate the stratum corneum immediately", "gradual removal of epidermal cells", Resurfacing = "brings the spicules in; roughness, pores, dullness, uneven texture", Delivery = channels in the OUTER layer, "biological micro-needles remain up to 72 hours"

- RU node: `667:788` — Rubik Regular 12.5, at (46, 159) w 424
- HE node(s): `795:23`, `795:24`, `795:25`
- Current RU (runs: Regular 12.5 [0,190) 'Во время массажа спикулы создают контрол'; Medium 12.5 [190,220) 'Resurfacing — обновление кожи\n'; Regular 12.5 [220,325) 'Механическое воздействие спикул способст'; Medium 12.5 [325,367) 'Delivery — косметическая система доставк'; Regular 12.5 [367,626) 'Спикулы создают временные микроскопическ'):
```text
Во время массажа спикулы создают контролируемую механическую микростимуляцию, способствуя постепенному обновлению кожи, улучшению её текстуры и подготовке к нанесению активных компонентов.

Resurfacing — обновление кожи
Механическое воздействие спикул способствует улучшению гладкости, текстуры и общего внешнего вида кожи.

Delivery — косметическая система доставки
Спикулы создают временные микроскопические каналы в поверхностных слоях кожи, способствуя более эффективному проникновению активных компонентов, наносимых в ходе процедуры.

Микроспикулы могут сохраняться в коже до 72 часов, продолжая механическую стимуляцию.
```
- HE text:
```text
בזמן העיסוי, הספיקולות משתלבות וחודרות במיידי בשכבה הקרנית ויוצרות גירוי מכני קוסמטי מבוקר. פעולה זו תומכת בהסרה הדרגתית של תאים אפידרמלים, משפרת את מראה העור, מרקם העור ומכינה את העור לקבלת הרכיבים הפעילים המשולבים בהמשך הטיפול.


פעולה מכנית המכניסה פנימה את הספיקולות ומסייעת לשיפור מראה החספוס, הנקבוביות, העמימות והמרקם הבלתי אחיד.

Delivery - מערכת הולכה קוסמטית
יצירת מסלולים מיקרוסקופיים זמניים בשכבה החיצונית של העור, התומכים במעבר יעיל יותר של הפורמולה והרכיבים הפעילים הנמרחים במהלך הטיפול.

המטרה אינה רק ליצור אפקט של פילינג. המטרה היא להפוך את שלב החידוש לשער קוסמטי מדויק – BIOMICRONEEDLING

מיקרו-מחטים ביולוגיות נשארות בעור עד 72 שעות
—
חידוש פני העור -
—
Resurfacing
```
- **New RU** (ready to paste):
```text
Во время массажа спикулы сразу внедряются в роговой слой и создают контролируемую механическую косметическую стимуляцию. Это способствует постепенному удалению клеток эпидермиса, улучшает внешний вид и текстуру кожи и подготавливает её к восприятию активных компонентов, которые наносятся на следующих этапах процедуры.

Resurfacing — обновление поверхности кожи
Механическое действие вводит спикулы в кожу и помогает улучшить внешний вид шероховатости, пор, тусклости и неровной текстуры.

Delivery — косметическая система доставки
Спикулы создают временные микроскопические каналы в наружном слое кожи, способствуя более эффективному прохождению формулы и активных компонентов, наносимых во время процедуры.

Биологические микроиглы остаются в коже до 72 часов.
```
- Emphasis runs (offsets in the new text): Medium [321,362) “Resurfacing — обновление поверхности кожи”; Medium [491,532) “Delivery — косметическая система доставки”
- Style: Regular 12.5 as now; the two sub-heads Medium (HE Bold).

#### E17.4 [B] Goal sentence: HE "The goal is not only a peeling effect. The goal is to turn the renewal stage into a precise cosmetic gateway – BIOMICRONEEDLING"

- RU node: `667:789` — Rubik Medium 16, at (46, 454) w 702
- HE node(s): `795:23`
- Current RU:
```text
Цель технологии — не просто эффект пилинга, а сочетание контролируемого обновления и косметической доставки активных компонентов — BIOMICRONEEDLING.
```
- HE text:
```text
בזמן העיסוי, הספיקולות משתלבות וחודרות במיידי בשכבה הקרנית ויוצרות גירוי מכני קוסמטי מבוקר. פעולה זו תומכת בהסרה הדרגתית של תאים אפידרמלים, משפרת את מראה העור, מרקם העור ומכינה את העור לקבלת הרכיבים הפעילים המשולבים בהמשך הטיפול.


פעולה מכנית המכניסה פנימה את הספיקולות ומסייעת לשיפור מראה החספוס, הנקבוביות, העמימות והמרקם הבלתי אחיד.

Delivery - מערכת הולכה קוסמטית
יצירת מסלולים מיקרוסקופיים זמניים בשכבה החיצונית של העור, התומכים במעבר יעיל יותר של הפורמולה והרכיבים הפעילים הנמרחים במהלך הטיפול.

המטרה אינה רק ליצור אפקט של פילינג. המטרה היא להפוך את שלב החידוש לשער קוסמטי מדויק – BIOMICRONEEDLING

מיקרו-מחטים ביולוגיות נשארות בעור עד 72 שעות
```
- **New RU** (ready to paste):
```text
Цель — не только эффект пилинга. Цель — превратить этап обновления в точный косметический «вход» — BIOMICRONEEDLING.
```
- Style: Medium 16 as now (HE has it inside the body in Regular; keeping it as the RU closing line is fine).

### RU p.18 — frame `667:768` “RU — 18 — MICRO BOOST 10%” ↔ HE p.18 `795:38` “HE — 18 — BIOSPICULE Micro BOOST 10%”

#### E18.1 [B] Description: HE "the most PROFESSIONAL and CONCENTRATED serum in the BIOSPICULE series", "according to skin diagnosis", "multi-layer distribution of the cosmetic stimulation", long spicules "more noticeable and intense stimulation, reach deeper", "professional RENEWAL system and scientific DELIVERY of substances inward"

- RU node: `667:774` — Rubik Regular 12, at (302, 169) w 446
- HE node(s): `795:45`
- Current RU (runs: Regular 12 [0,382) 'Самая концентрированная профессиональная'; Medium 12 [382,399) '40% Mini Spicules'; Regular 12 [399,430) ' — длиной около 80–100 микрон.\n'; Medium 12 [430,447) '60% Long Spicules'; Regular 12 [447,805) ' — длиной около 300–360 микрон.\nСочетани'; Medium 12 [805,821) 'BIOMICRONEEDLING'; Regular 12 [821,910) ' — профессиональным подходом, сочетающим'):
```text
Самая концентрированная профессиональная сыворотка в линейке BIOSPICULE™. Предназначена исключительно для применения в клинике и выпускается в шприце объёмом 3 мл, что позволяет косметологу контролировать количество продукта, продолжительность массажа и интенсивность процедуры в соответствии с состоянием кожи.

Формула содержит 10% Hydrolyzed Sponge и сочетает две группы спикул:
40% Mini Spicules — длиной около 80–100 микрон.
60% Long Spicules — длиной около 300–360 микрон.
Сочетание коротких и длинных спикул обеспечивает разные уровни механической стимуляции. Короткие спикулы воздействуют преимущественно на наружные слои эпидермиса, тогда как длинные обеспечивают более интенсивное воздействие на более глубоких уровнях кожи.
Таким образом, косметолог работает не просто с пилингом, а с системой BIOMICRONEEDLING — профессиональным подходом, сочетающим обновление кожи и доставку активных компонентов.
```
- HE text:
```text
סרום מקצועי והמרוכז ביותר בסדרת BIOSPICULE. הוא מיועד לשימוש בקליניקה בלבד ומגיע במזרק של 3 מ״ל, המאפשר לקוסמטיקאית לשלוט בכמות החומר, במשך העיסוי ובעוצמת הטיפול בהתאם לאבחון העור.
הפורמולה מכילה 10% Hydrolyzed Sponge ומשלבת שתי קבוצות של ספיקולות:
                                  , באורך של כ־80–100 מיקרון.
                                    , באורך של כ־300–360 מיקרון.
השילוב בין הספיקולות הקצרות והארוכות יוצר פיזור רב־שכבתי של הגירוי הקוסמטי. הספיקולות הקצרות פועלות בעיקר באזור החיצוני יותר של האפידרמיס, ואילו הארוכות יוצרות גירוי מורגש ואינטנסיבי יותר ומגיעות עמוק יותר בשכבות העור.
כך הקוסמטיקאית אינה עובדת רק עם פילינג אלא עם מערכת הובלה של BIOMICRONEEDLING  
 מערכת חידוש מקצועית והובלה מדעית של חומרים פנימה.
```
- Replacements (old → new):
  - “Самая концентрированная профессиональная сыворотка в линейке BIOSPICULE™.” → “Самая профессиональная и концентрированная сыворотка в серии BIOSPICULE™.”
  - “в соответствии с состоянием кожи.” → “в соответствии с диагностикой кожи.”
  - “Сочетание коротких и длинных спикул обеспечивает разные уровни механической стимуляции.” → “Сочетание коротких и длинных спикул обеспечивает многоуровневое распределение косметической стимуляции.”
  - “Короткие спикулы воздействуют преимущественно на наружные слои эпидермиса, тогда как длинные обеспечивают более интенсивное воздействие на более глубоких уровнях кожи.” → “Короткие спикулы действуют преимущественно в наружной зоне эпидермиса, а длинные создают более ощутимую и интенсивную стимуляцию и достигают более глубоких слоёв кожи.”
  - “— профессиональным подходом, сочетающим обновление кожи и доставку активных компонентов.” → “— профессиональной системой обновления кожи и научно обоснованной доставки активных компонентов внутрь.”
- **New RU** (ready to paste):
```text
Самая профессиональная и концентрированная сыворотка в серии BIOSPICULE™. Предназначена исключительно для применения в клинике и выпускается в шприце объёмом 3 мл, что позволяет косметологу контролировать количество продукта, продолжительность массажа и интенсивность процедуры в соответствии с диагностикой кожи.

Формула содержит 10% Hydrolyzed Sponge и сочетает две группы спикул:
40% Mini Spicules — длиной около 80–100 микрон.
60% Long Spicules — длиной около 300–360 микрон.
Сочетание коротких и длинных спикул обеспечивает многоуровневое распределение косметической стимуляции. Короткие спикулы действуют преимущественно в наружной зоне эпидермиса, а длинные создают более ощутимую и интенсивную стимуляцию и достигают более глубоких слоёв кожи.
Таким образом, косметолог работает не просто с пилингом, а с системой BIOMICRONEEDLING — профессиональной системой обновления кожи и научно обоснованной доставки активных компонентов внутрь.
```
- Emphasis runs (offsets in the new text): Medium [6,22) “профессиональная”; Medium [25,42) “концентрированная”; Medium [384,401) “40% Mini Spicules”; Medium [432,449) “60% Long Spicules”; Medium [823,839) “BIOMICRONEEDLING”; Medium [868,878) “обновления”; Medium [906,914) “доставки”
- Style: Regular 12; Medium as HE on "профессиональная", "концентрированная", "обновления", "доставки" (HE Bold); keep the existing Medium on the two spicule lines and on BIOMICRONEEDLING.

### RU p.19 — frame `669:28` “RU — 19 — MICRO BOOST — протокол” ↔ HE p.19 `795:59` “HE — 19 — BIOSPICULE Micro BOOST 10% (המשך)”

#### E19.1 [A] Combinations (owner edit): "V-TECH | Longevity Serum | MITOTECH CELL BOOSTER"; "Treatment finish:" EXOCELL Mask / Derma Recovery Cream "– also for continued home care" / SPF

- RU node: `667:777` — Rubik Regular 12, at (46, 353) w 434
- HE node(s): `795:71`, `936:8`
- Current RU (runs: Regular 12 [0,114) 'Структура спикул и техника массажа созда'; Medium 12 [114,163) 'V-TECH или Longevity Serum\nЗавершение пр'; Regular 12 [163,176) 'EXOCELL MASK\n'; Medium 12 [176,196) 'DERMA RECOVERY CREAM'; Regular 12 [196,341) ' — также обязательное домашнее применени'):
```text
Структура спикул и техника массажа создают временные микроскопические каналы, что позволяет сочетать процедуру с:
V-TECH или Longevity Serum
Завершение процедуры:
EXOCELL MASK
DERMA RECOVERY CREAM — также обязательное домашнее применение для поддержки эпидермального барьера и уменьшения ощущения сухости и стянутости
Солнцезащитное средство
```
- HE text:
```text
מבנה הספיקולות ותהליך העיסוי יוצרים תעלות מיקרוסקופיות זמניות ולכן ניתן לשלב עם:
V-TECH | Longevity Serum | MITOTECH CELL BOOSTER
סיום טיפול:
EXOCELL Mask
Derma Recovery Cream
מקדם הגנה
—
– גם להמשך טיפול ביתי
```
- **New RU** (ready to paste):
```text
Структура спикул и техника массажа создают временные микроскопические каналы, что позволяет сочетать процедуру с:
V-TECH | Longevity Serum | MITOTECH CELL BOOSTER
Завершение процедуры:
EXOCELL Mask
Derma Recovery Cream — также для продолжения домашнего ухода
Солнцезащитное средство
```
- Emphasis runs (offsets in the new text): Medium [163,184) “Завершение процедуры:”
- Style: Regular 12; only "Завершение процедуры:" Medium (HE SemiBold; the product line is Regular in HE). Product spellings exactly as HE p.19 ("EXOCELL Mask", "Derma Recovery Cream"). HE sets the "– also for continued home care" note as a separate node (936:8) beside the cream line; one RU line is fine.
- Note: Drops the RU-only claim "обязательное домашнее применение для поддержки эпидермального барьера…" (not in HE).

#### E19.2 [A] Running head, page header and footer missing on RU p.19 (HE repeats "BIOSPICULE", "Professional treatment for the clinic", "MICRO BOOST 10%")

- RU node: `NEW in 669:28`
- HE node(s): `795:81`, `795:62`, `795:63`, `795:64`, `795:82`
- HE text:
```text
MITODERM
—
BIOSPICULE
—
טיפול מקצועי לקליניקה
—
MICRO BOOST 10%
—
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style: Clone from RU p.18: 667:769 (MITODERM), 667:771 (BIOSPICULE™), 667:772 (Профессиональная процедура для клиники), 667:773 (MICRO BOOST 10%), 667:770 (footer), same positions as on p.18 (mirror x if the p.19 photo side requires).
- Note: Fit: +~90 px of header; body 667:775/776/777 must reflow (two columns as HE, or the next scale step down). Layout pass.

#### E19.3 [B] "Who is it for": HE adds "AGING", "improvement of skin tone and uneven tone", "post-acne SCARS", "skin that has lost elasticity and firmness", one item "firming and improving skin quality"

- RU node: `667:775` — Rubik Regular 12, at (46, 70) w 434
- HE node(s): `795:69`
- Current RU (runs: Medium 12 [0,25) 'Кому подходит процедура?\n'; Regular 12 [25,725) 'При условии профессиональной диагностики'):
```text
Кому подходит процедура?
При условии профессиональной диагностики:
Антивозрастной уход | Тусклая, уставшая кожа | Неровная или шероховатая текстура | Расширенные поры | Неровный тон кожи | Постакне | Послеоперационные рубцы | Пигментация и солнечные пятна | Поствоспалительная пигментация (PIH) | Морщины, мелкие линии и признаки старения | Снижение упругости и эластичности | Кожа курильщика | Акне лёгкой и средней степени | Повышение упругости | Улучшение качества кожи

Из-за высокой концентрации спикул во время процедуры и в последующие дни может возникать характерное покалывание, особенно при прикосновении к коже. Также возможны временное покраснение, сухость, чувство стянутости и шелушение различной интенсивности.
```
- HE text:
```text
למי מתאים הטיפול?
בכפוף לאבחון מקצועי:
אנטי-אייג׳ינג | AGING | עור עמום, עייף וחסר חיוניות | מרקם מחוספס או בלתי אחיד | נקבוביות פעורות | שיפור גוון העור וגוון בלתי אחיד | צלקות פוסט אקנה | צלקות ניתוחיות | פיגמנטציה וכתמי שמש פיגמנטציה פוסט דלקתית | קמטים, קמטוטים וסימני גיל | עור שאיבד ממראה הגמישות והמוצקות | מעשנות | אקנה קל עד בינוני | מיצוק ושיפור איכות העור.

בשל ריכוז הספיקולות הגבוה, במהלך הטיפול ובימים שלאחריו עשויה להופיע תחושת עקצוץ אופיינית, בעיקר בזמן מגע בעור. ייתכנו גם אדמומיות זמנית, יובש, מתיחה או קילוף ברמה משתנה.

```
- Replacements (old → new):
  - “Антивозрастной уход | Тусклая, уставшая кожа | Неровная или шероховатая текстура | Расширенные поры | Неровный тон кожи | Постакне | Послеоперационные рубцы | Пигментация и солнечные пятна | Поствоспалительная пигментация (PIH) | Морщины, мелкие линии и признаки старения | Снижение упругости и эластичности | Кожа курильщика | Акне лёгкой и средней степени | Повышение упругости | Улучшение качества кожи” → “Антивозрастной уход | Возрастные изменения кожи | Тусклая, уставшая кожа, лишённая жизненной силы | Шероховатая или неровная текстура | Расширенные поры | Улучшение тона кожи и неровный тон | Рубцы постакне | Послеоперационные рубцы | Пигментация и солнечные пятна | Поствоспалительная пигментация (PIH) | Морщины, мелкие линии и признаки старения | Кожа, утратившая эластичность и упругость | Кожа курильщиков | Акне лёгкой и средней степени | Повышение упругости и улучшение качества кожи”
- **New RU** (ready to paste):
```text
Кому подходит процедура?
При условии профессиональной диагностики:
Антивозрастной уход | Возрастные изменения кожи | Тусклая, уставшая кожа, лишённая жизненной силы | Шероховатая или неровная текстура | Расширенные поры | Улучшение тона кожи и неровный тон | Рубцы постакне | Послеоперационные рубцы | Пигментация и солнечные пятна | Поствоспалительная пигментация (PIH) | Морщины, мелкие линии и признаки старения | Кожа, утратившая эластичность и упругость | Кожа курильщиков | Акне лёгкой и средней степени | Повышение упругости и улучшение качества кожи

Из-за высокой концентрации спикул во время процедуры и в последующие дни может возникать характерное покалывание, особенно при прикосновении к коже. Также возможны временное покраснение, сухость, чувство стянутости и шелушение различной интенсивности.
```
- Style: Keep the Medium run "Кому подходит процедура?". The reaction paragraph matches HE.
- Note: "AGING" → "Возрастные изменения кожи", as E15.4.

### RU p.20 (→ p.24) — frame `667:750` “RU — 20 — Дополняющий домашний уход” ↔ HE p.24 `793:247` “HE — 24 — תכשירים משלימים לשימוש ביתי”

#### E24.1 [B] Title: HE "complementary PRODUCTS for home use" (= ToC section 6)

- RU node: `667:755` — Rubik Bold 41, at (57, 105) w 686
- HE node(s): `793:252`
- Current RU:
```text
Дополняющий домашний уход
```
- HE text:
```text
תכשירים משלימים לשימוש ביתי
```
- **New RU** (ready to paste):
```text
Дополняющие средства для домашнего ухода
```
- Style: Bold 41 as now; at 41 pt the line is ~1000 px → two lines, or 30 pt on one line (HE 40 pt, one line). Same wording as ToC section 6.

#### E24.2 [C] Series label: "BIOSPICULE ™" with a space; HE "BIOSPICULE™" with a small ™ run

- RU node: `667:757` — Rubik Medium 16, at (400, 202) w 340
- HE node(s): `793:255`
- Current RU:
```text
Серия BIOSPICULE ™
```
- HE text:
```text
סדרת BIOSPICULE™
```
- **New RU** (ready to paste):
```text
Серия BIOSPICULE™
```
- Emphasis runs (offsets in the new text): Medium [0,16) “Серия BIOSPICULE”; Medium [16,17) “™”
- Style: Medium 16 as now; "™" at ~9 pt (HE 8 pt inside 14 pt).
- Note: Pack-shot of the spray: RU uses another file of the same box + bottle (667:759, hash dca06568a4; HE 793:257 hash 7a8ed5b1fc) — same product, no change needed.

### RU p.21 (→ p.25) — frame `667:737` “RU — 21 — Серия синтетических экзосом” ↔ HE p.25 `793:267` “HE — 25 — סדרת האקסוזומים הסינתטיים”

#### E25.1 [B] Lead: HE "complementary products designed to fit into the professional system and home care ACCORDING TO THE PROTOCOL"

- RU node: `667:747` — Rubik Regular 16, at (150, 169) w 493
- HE node(s): `793:277`
- Current RU:
```text
Дополняющие средства для интеграции в профессиональные протоколы и домашний уход.
```
- HE text:
```text
מוצרים משלימים שנועדו להשתלב במערך המקצועי ובטיפוח הביתי בהתאם לפרוטוקול
```
- **New RU** (ready to paste):
```text
Дополняющие средства, которые встраиваются в профессиональную программу и домашний уход в соответствии с протоколом.
```
- Style: Regular 16 as now.
- Note: Spray pack-shot 667:749: same product, other file (as E24.2) — no change.

### RU p.22 (→ p.26) — frame `667:721` “RU — 22 — EXOTECH GEL” ↔ HE p.26 `824:203` “HE — 26 — EXOTECH GEL”

#### E26.1 [C] "линией BIOSPICULE™" → "серией" (HE "סדרת BIOSPICULE", one word for "series" throughout)

- RU node: `667:734` — Rubik Regular 12, at (416, 455) w 332
- HE node(s): `824:218`
- Current RU:
```text
Для продолжения домашнего ухода, особенно после профессиональных процедур в клинике. EXOTECH GEL может быть интегрирован в программы ухода с V-TECH, EXO-NAD и линией BIOSPICULE™.
```
- HE text:
```text
להמשך כל שגרת הטיפוח ובמיוחד לאחר טיפול מקצועי בקליניקה – ניתן לשלב אותו כחלק מתוכנית טיפול הכוללת V-TECH, EXO-NAD, סדרת BIOSPICULE
```
- Replacements (old → new):
  - “и линией BIOSPICULE™” → “и серией BIOSPICULE™”
- **New RU** (ready to paste):
```text
Для продолжения домашнего ухода, особенно после профессиональных процедур в клинике. EXOTECH GEL может быть интегрирован в программы ухода с V-TECH, EXO-NAD и серией BIOSPICULE™.
```

### RU p.23 (→ p.27) — frame `667:707` “RU — 23 — EXOSIGNAL SPRAY” ↔ HE p.27 `793:298` “HE — 27 — EXOSIGNAL SPRAY”

#### E27.1 [C] Pack-shot caption is the label copy, Latin on HE (as RU keeps it on pp.25/28); the RU translation also has a gender error ("питающая спрей")

- RU node: `667:714` — Rubik Regular 12, at (46, 272) w 550
- HE node(s): `793:306`
- Current RU:
```text
Глубоко питающая спрей для кожи головы
ДОМАШНИЙ УХОД · 15 мл
```
- HE text:
```text
Deep nourishing scalp spray
HOME USE · 15 ml
```
- **New RU** (ready to paste):
```text
Deep nourishing scalp spray
HOME USE · 15 ml
```
- Style: Regular 12 as now; keep it next to the pack-shot as HE (HE x 52, y 426).

#### E27.2 [C] Bullet 5: HE "the spray mechanism … directly on the scalp, WITHOUT RINSING"

- RU node: `675:2` — Rubik Regular 12, at (287, 310) w 222
- HE node(s): `793:309`
- Current RU:
```text
• Подходит для точечного нанесения на участки с видимым поредением, ослаблением или снижением качества волос.
• Обеспечивает удобное и равномерное нанесение непосредственно на кожу головы.
```
- HE text:
```text
• תומך בסביבת הקרקפת ובתנאים האופטימליים לפעילות זקיקי השיער.
• מסייע בטיפוח קרקפת המתמודדת עם יובש, תחושת אי־נוחות או חוסר איזון.
• מסייע בשמירה על מראה שיער מלא, חזק וחיוני יותר במסגרת שימוש עקבי.
• מתאים למריחה ממוקדת באזורים שבהם נראים דלילות, היחלשות או ירידה באיכות השיער.
• מנגנון ההתזה מאפשר פיזור נוח ואחיד ישירות על הקרקפת, ללא צורך בשטיפה.
```
- Replacements (old → new):
  - “Обеспечивает удобное и равномерное нанесение непосредственно на кожу головы.” → “Распылитель обеспечивает удобное и равномерное нанесение непосредственно на кожу головы без необходимости смывания.”
- **New RU** (ready to paste):
```text
• Подходит для точечного нанесения на участки с видимым поредением, ослаблением или снижением качества волос.
• Распылитель обеспечивает удобное и равномерное нанесение непосредственно на кожу головы без необходимости смывания.
```

#### E27.3 [L] Reading order of the "Рекомендуется:" list: its first two items sit at the bottom of column 2 (667:718), the other five at the top of column 3 (675:3)

- RU node: `667:718, 675:3`
- HE node(s): `793:311`
- HE text:
```text
• מתאים לנשים ולגברים המתמודדים עם מראה שיער דליל או מוחלש
• לשיער דק, שביר וחסר חיוניות
• לקרקפת הזקוקה לטיפוח ולאיזון
• כחלק מתוכנית לטיפול בנשירה ובדלילות שיער
• להמשך טיפול ביתי בין טיפולי EXOSIGNAL HAIR
• לתחזוקת הקרקפת לאחר השלמת סדרת טיפולים מקצועית
• כחלק ממעטפת טיפוח לאחר השתלת שיער
```
- Style: Optional: put 667:718 at the top of column 3 and 675:3 under it, so the list reads in one run (HE: one block 793:311).
- Note: Text matches HE.

### RU p.24 (→ p.28) — frame `667:691` “RU — 24 — Серия BIOSPICULE” ↔ HE p.28 `793:314` “HE — 28 — סדרת BIOSPICULE”

#### E28.1 [C] Title: "™" is a separate node (667:697); HE has it in the title node as a 21 pt run

- RU node: `667:696 (+ delete 667:697)`
- HE node(s): `793:319`
- HE text:
```text
סדרת BIOSPICULE™
```
- **New RU** (ready to paste):
```text
Серия BIOSPICULE™
```
- Emphasis runs (offsets in the new text): Bold [0,16) “Серия BIOSPICULE”; Bold [16,17) “™”
- Style: Bold 41; "™" Bold 21 (HE ExtraBold 21). Delete 667:697.

#### E28.2 [C] CELLULAR AGE DEFENSE descriptor: one RU wording for HE "סרום מתקדם למיצוק ואנטי-אייג׳ינג" (pp.28, 32, 33, 34, ToC); sizes as HE (all three lines 14 pt)

- RU node: `667:699` — Rubik Medium 12, at (54, 197) w 686
- HE node(s): `793:323`
- Current RU:
```text
CELLULAR AGE DEFENSE 2.5% — усовершенствованная антивозрастная сыворотка для упругости
```
- HE text:
```text
CELLULAR AGE DEFENSE 2.5% סרום מתקדם למיצוק ואנטי-אייג׳ינג
```
- **New RU** (ready to paste):
```text
CELLULAR AGE DEFENSE 2.5% — усовершенствованная сыворотка для укрепления кожи и антивозрастного ухода
```
- Style: Medium 14 (now 12); also 667:700 12 → 14, as HE 793:322–324.

### RU p.25 (→ p.29) — frame `667:673` “RU — 25 — CELL RENEW 1.5%” ↔ HE p.29 `793:331` “HE — 29 — CELL RENEW 1.5%”

#### E29.1 [B] Last paragraph: HE "a complementary envelope of renewal, building, radiance and evenness"

- RU node: `667:681` — Rubik Regular 12, at (46, 153) w 434
- HE node(s): `793:342`
- Current RU:
```text
Сыворотка со спикулами предназначена для постепенного введения кожи в продвинутую программу обновления, с акцентом на более сияющий, гладкий и ровный внешний вид.
Формула сочетает умеренную концентрацию спикул с активными компонентами, способствующими увлажнению, свежести, улучшению текстуры и тона кожи. Во время массажа может возникать лёгкое характерное покалывание, связанное с механическим контактом спикул с наружным слоем кожи.
Это не обычный домашний пилинг. Спикулы обеспечивают умеренную механическую косметическую стимуляцию и поддерживают процессы обновления поверхности кожи, а активные компоненты формулы дополняют действие, способствуя восстановлению, сиянию и более ровному тону.
```
- HE text:
```text
זהו אינו פילינג ביתי רגיל. הספיקולות מעניקות גירוי מכני קוסמטי מתון ותומכות בתהליך החידוש של פני העור, בעוד הרכיבים הפעילים שבפורמולה מעניקים מעטפת משלימה של חידוש, בניה, זוהר ואחידות.
```
- Replacements (old → new):
  - “а активные компоненты формулы дополняют действие, способствуя восстановлению, сиянию и более ровному тону.” → “а активные компоненты формулы дополняют действие, обеспечивая обновление, восстановление структуры, сияние и ровный тон кожи.”
- **New RU** (ready to paste):
```text
Сыворотка со спикулами предназначена для постепенного введения кожи в продвинутую программу обновления, с акцентом на более сияющий, гладкий и ровный внешний вид.
Формула сочетает умеренную концентрацию спикул с активными компонентами, способствующими увлажнению, свежести, улучшению текстуры и тона кожи. Во время массажа может возникать лёгкое характерное покалывание, связанное с механическим контактом спикул с наружным слоем кожи.
Это не обычный домашний пилинг. Спикулы обеспечивают умеренную механическую косметическую стимуляцию и поддерживают процессы обновления поверхности кожи, а активные компоненты формулы дополняют действие, обеспечивая обновление, восстановление структуры, сияние и ровный тон кожи.
```

### RU p.27 (→ p.31) — frame `669:30` “RU — 27 — CELL RENEW — применение” ↔ HE p.31 `796:27` “HE — 31 — CELL RENEW 1.5% (המשך 2)”

#### E31.1 [A] Header, pack-shot label and footer missing on RU p.27 (HE p.31 repeats MITODERM, "CELL RENEW 1.5%", "BIOSPICULE SERUM", subtitle, label "Advanced Biospicule Technology / 30 ml", footer)

- RU node: `NEW in 669:30`
- HE node(s): `796:57`, `796:30`, `796:31`, `796:32`, `796:59`, `796:58`
- HE text:
```text
MITODERM
—
CELL RENEW 1.5%
—
BIOSPICULE SERUM
—
סרום ביתי לחידוש והבהרה
—
Advanced Biospicule Technology
30 ml ℮ 1.0 fl.oz.
—
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style: Clone from RU p.26: 667:650, 667:652, 667:653, 667:654, 667:651; label from RU p.25 667:686 ("Advanced Biospicule Technology\n30 ml ℮ 1.0 fl.oz.") next to the pack-shot. Then 667:668 → ingredient heading Medium 14 (HE 796:47 SemiBold 14), 667:670 → Medium 14 (HE 796:49), body 667:669/667:671 → Regular 12.
- Note: Block order (layout only): Salicylic + Citric is on RU p.26 (667:666/667) but on HE p.31 (796:45/46); optional move to match HE.

### RU p.28 (→ p.32) — frame `667:631` “RU — 28 — CELLULAR AGE DEFENSE 2.5%” ↔ HE p.32 `793:441` “HE — 32 — CELLULAR AGE DEFENSE 2.5%”

#### E32.1 [B] "Suitable for": HE "IMPROVEMENT of elasticity and skin quality", "tired and LIFELESS skin"

- RU node: `667:641` — Rubik Regular 12.5, at (314, 354) w 434
- HE node(s): `793:452`
- Current RU:
```text
Все типы кожи | Морщины и мелкие линии | Антивозрастной уход | Снижение эластичности и упругости кожи | Уставшая и обезвоженная кожа | Неровная или шероховатая текстура | Расширенные поры | Укрепление и осветление | Улучшение внешнего вида рубцов постакне | Акне лёгкой и средней степени
```
- HE text:
```text
לכל סוגי העור | שיפור במראה קמטים וקמטוטים | אנטי-אייג׳ינג | שיפור באלסטיות ואיכות העור | עור עייף וחסר חיוניות | מרקם בלתי אחיד או מחוספס | צמצום נקבוביות 
מיצוק והבהרה | שיפור במראה צלקות פוסט אקנה | אקנה רגיל עד בינוני
```
- Replacements (old → new):
  - “Снижение эластичности и упругости кожи” → “Улучшение эластичности и качества кожи”
  - “Уставшая и обезвоженная кожа” → “Уставшая кожа, лишённая жизненной силы”
- **New RU** (ready to paste):
```text
Все типы кожи | Морщины и мелкие линии | Антивозрастной уход | Улучшение эластичности и качества кожи | Уставшая кожа, лишённая жизненной силы | Неровная или шероховатая текстура | Расширенные поры | Укрепление и осветление | Улучшение внешнего вида рубцов постакне | Акне лёгкой и средней степени
```

#### E32.2 [C] Subtitle wording as on p.29 / E28.2

- RU node: `667:634` — Rubik Regular 14, at (314, 116) w 434
- HE node(s): `793:444`
- Current RU:
```text
Продвинутая сыворотка для укрепления кожи и антивозрастного ухода
```
- HE text:
```text
סרום מתקדם למיצוק ואנטי-אייג׳ינג
```
- **New RU** (ready to paste):
```text
Усовершенствованная сыворотка для укрепления кожи и антивозрастного ухода
```
- Style: Regular 14 as now.
- Note: RU p.29 667:610 already reads so.

### RU p.30 (→ p.34) — frame `669:32` “RU — 30 — AGE DEFENSE — применение” ↔ HE p.34 `796:90` “HE — 34 — CELLULAR AGE DEFENSE 2.5% (המשך 2)”

#### E34.1 [A] Header, pack-shot label and footer missing on RU p.30 (HE p.34 repeats MITODERM, title, "BIOSPICULE SERUM", subtitle, label "Advanced Biospicule Technology / 30 ml", footer)

- RU node: `NEW in 669:32`
- HE node(s): `796:126`, `796:117`, `796:118`, `796:119`, `796:128`, `796:127`
- HE text:
```text
MITODERM
—
CELLULAR AGE DEFENSE 2.5%
—
BIOSPICULE SERUM
—
סרום מתקדם למיצוק ואנטי-אייג׳ינג
—
Advanced Biospicule Technology
30 ml ℮ 1.0 fl.oz.
—
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style: Clone from RU p.29: 667:606, 667:608, 667:609, 667:610, 667:607; label from RU p.28 667:644. Then 667:629 "Способ применения" → section heading Medium 14 (HE 796:115 SemiBold 14), body 667:630 Regular 12.
- Note: Block order (layout only): Yeast Beta-Glucan and Akebia/Camellia are on RU p.29 (667:625–628) but on HE p.34 (796:111–114); optional move to match HE.

#### E34.2 [B] How to use: HE "to support the skin's moisture and VITALITY"

- RU node: `667:630` — Rubik Regular 13, at (318, 143) w 430
- HE node(s): `796:116`
- Current RU:
```text
Для ежедневного применения. Нанести на чистую сухую кожу и мягко массировать до впитывания. Возможно заметное характерное покалывание, особенно при контакте с кожей. Не следует интенсивно растирать кожу.

После сыворотки рекомендуется нанести Derma Recovery Cream для поддержания увлажнённости и комфорта кожи. В дневное время обязательно использовать солнцезащитное средство.

Для кожи, ещё не привыкшей к продукту, рекомендуется постепенный переход с Cell Renew 1.5% на Cellular Age Defense 2.5%, с учётом индивидуальной переносимости.
```
- HE text:
```text
לשימוש יומיומי. על עור נקי ויבש יש למרוח ולעסות בעדינות. עשוי לגרום לתחושת עקצוץ מורגשת, במיוחד בזמן מגע בעור. אין לשפשף בחוזקה
לאחר הסרום מומלץ למרוח Derma Recovery Cream לתמיכה בלחות וחיוניות העור. בשעות היום חובה להשתמש במסנן קרינה.
בעור שאינו מורגל מומלץ לבצע מעבר הדרגתי מ־1.5% ל־2.5%, בהתאם לסבילות העור.
```
- Replacements (old → new):
  - “для поддержания увлажнённости и комфорта кожи” → “для поддержания увлажнённости и жизненной силы кожи”
- **New RU** (ready to paste):
```text
Для ежедневного применения. Нанести на чистую сухую кожу и мягко массировать до впитывания. Возможно заметное характерное покалывание, особенно при контакте с кожей. Не следует интенсивно растирать кожу.

После сыворотки рекомендуется нанести Derma Recovery Cream для поддержания увлажнённости и жизненной силы кожи. В дневное время обязательно использовать солнцезащитное средство.

Для кожи, ещё не привыкшей к продукту, рекомендуется постепенный переход с Cell Renew 1.5% на Cellular Age Defense 2.5%, с учётом индивидуальной переносимости.
```

### RU p.31 (→ p.35) — frame `667:587` “RU — 31 — DERMA RECOVERY CREAM” ↔ HE p.35 `793:352` “HE — 35 — DERMA RECOVERY”

#### E35.1 [C] Indications: product name as HE "MICRO BOOST 10%"; "series"

- RU node: `667:597` — Rubik Regular 12, at (46, 316) w 434
- HE node(s): `793:363`
- Current RU:
```text
Завершение профессионального протокола V-TECH SYSTEM | После инвазивных процедур в клинике | Завершение профессионального протокола с Micro BOOST 10% | Домашний уход после применения средств линии BIOSPICULE™: Cell Renew 1.5% и Cellular Age Defense 2.5%
```
- HE text:
```text
סיום פרוטוקול מקצועי V-TECH SYSTEM | לאחר פרוצדורה פולשנית בקליניקה  
סיום פרוטוקול טיפול מקצועי בקליניקה עם MICRO BOOST 10% 
לאחר שגרת טיפוח ביתית: מסדרת ה-BIOSPICULE 
Cell Renew 1.5% -ו Cellular Age Defense 2.5%  
```
- Replacements (old → new):
  - “Micro BOOST 10%” → “MICRO BOOST 10%”
  - “средств линии BIOSPICULE™” → “средств серии BIOSPICULE™”
- **New RU** (ready to paste):
```text
Завершение профессионального протокола V-TECH SYSTEM | После инвазивных процедур в клинике | Завершение профессионального протокола с MICRO BOOST 10% | Домашний уход после применения средств серии BIOSPICULE™: Cell Renew 1.5% и Cellular Age Defense 2.5%
```

#### E35.2 [C] "Spicules" in Latin inside Russian text → "спикулы" (edition term)

- RU node: `667:595` — Rubik Regular 12, at (46, 167) w 434
- HE node(s): `793:361`
- Current RU (runs: Regular 12 [0,189) 'Восстанавливающий крем для ежедневного у'; Medium 12 [189,218) 'Сам крем не содержит Spicules'; Regular 12 [218,348) ' — его роль дополняющая: обеспечивать ув'):
```text
Восстанавливающий крем для ежедневного увлажнения и питания. Предназначен как дополнение к профессиональным протоколам и домашнему уходу, в том числе после применения средств со Spicules.

Сам крем не содержит Spicules — его роль дополняющая: обеспечивать увлажнение, мягкость и комфорт, поддерживая эпидермальный барьер в процессе обновления кожи.
```
- HE text:
```text
קרם שיקום – לחות והזנה לשימוש יומיומי
מיועד כקרם משלים לכל פרוטוקול טיפול ושגרת טיפוח, ובנוסף לאחר שימוש 
במוצרים המכילים ספיקולות.
הקרם עצמו אינו מכיל ספיקולות, ולכן תפקידו משלים:
להעניק לעור לחות, רכות ונוחות ולתמוך במחסום האפידרמלי במהלך תהליך החידוש.
```
- Replacements (old → new):
  - “средств со Spicules” → “средств со спикулами”
  - “Сам крем не содержит Spicules” → “Сам крем не содержит спикул”
- **New RU** (ready to paste):
```text
Восстанавливающий крем для ежедневного увлажнения и питания. Предназначен как дополнение к профессиональным протоколам и домашнему уходу, в том числе после применения средств со спикулами.

Сам крем не содержит спикул — его роль дополняющая: обеспечивать увлажнение, мягкость и комфорт, поддерживая эпидермальный барьер в процессе обновления кожи.
```
- Emphasis runs (offsets in the new text): Medium [190,217) “Сам крем не содержит спикул”
- Style: Keep the Medium run on the second paragraph lead (now "Сам крем не содержит Spicules").

#### E35.3 [C] "Who is it for": HE "after a PROFESSIONAL spicule treatment"

- RU node: `667:599` — Rubik Regular 12, at (46, 415) w 434
- HE node(s): `793:365`
- Current RU:
```text
Для всех типов кожи | Для увлажнения после профессиональных процедур | Для сухой и обезвоженной кожи | Для кожи, нуждающейся в поддержке после процедур со Spicules | Для раздражённой, шероховатой или склонной к шелушению кожи | Для ежедневного ухода, сочетающего увлажнение, питание и успокаивающее действие.
```
- HE text:
```text
הקרם מעניק לחות לכל סוגי העור | לחות כללית לאחר טיפול בקליניקה | לחות לעור יבש או מיובש | לחות לעור הזקוק לתמיכה לאחר טיפול ספיקולות מקצועי | עור בעל מראה מגורה, מחוספס או מתקלף  שגרת טיפוח המבקשת לשלב לחות, הזנה והרגעה.
```
- Replacements (old → new):
  - “после процедур со Spicules” → “после профессиональных процедур со спикулами”
- **New RU** (ready to paste):
```text
Для всех типов кожи | Для увлажнения после профессиональных процедур | Для сухой и обезвоженной кожи | Для кожи, нуждающейся в поддержке после профессиональных процедур со спикулами | Для раздражённой, шероховатой или склонной к шелушению кожи | Для ежедневного ухода, сочетающего увлажнение, питание и успокаивающее действие.
```

#### E35.4 [C] Pack-shot caption is label copy, Latin on HE; RU mixes Russian and "fl.oz."

- RU node: `667:602` — Rubik Regular 11.5, at (536, 462) w 222
- HE node(s): `793:368`
- Current RU:
```text
Ежедневный питательный крем с коллагеном для здорового сияния кожи
50 мл ℮ 1.69 fl.oz.
```
- HE text:
```text
Daily nourishing collagen cream for healthy-looking glow
50 ml ℮ 1.69 fl.oz.
```
- **New RU** (ready to paste):
```text
Daily nourishing collagen cream for healthy-looking glow
50 ml ℮ 1.69 fl.oz.
```
- Style: Regular 12 (now 11.5).

### RU p.32 (→ p.36) — frame `667:569` “RU — 32 — DERMA RECOVERY — компоненты” ↔ HE p.36 `793:371` “HE — 36 — DERMA RECOVERY (המשך)”

#### E36.1 [B] Niacinamide: HE adds "anti-inflammatory" and "improves the skin's ability to retain moisture"

- RU node: `667:583` — Rubik Regular 12, at (416, 242) w 332
- HE node(s): `793:385`
- Current RU (runs: Medium 12 [0,25) 'Niacinamide — Ниацинамид\n'; Regular 12 [25,171) 'Помогает поддерживать кожный барьер, спо'):
```text
Niacinamide — Ниацинамид
Помогает поддерживать кожный барьер, способствует удержанию влаги и улучшает внешний вид кожи, придавая ей более ровный, спокойный и здоровый вид.
```
- HE text:
```text
Niacinamide – ניאצינאמיד
מסייע לתמוך במחסום העורי, אנטידלקתי ומשפר את יכולת העור 
לשמור על לחות. מעניק לעור מראה אחיד, רגוע ובריא יותר.
```
- Replacements (old → new):
  - “Помогает поддерживать кожный барьер, способствует удержанию влаги и улучшает внешний вид кожи,” → “Помогает поддерживать кожный барьер, оказывает противовоспалительное действие и улучшает способность кожи удерживать влагу,”
- **New RU** (ready to paste):
```text
Niacinamide — Ниацинамид
Помогает поддерживать кожный барьер, оказывает противовоспалительное действие и улучшает способность кожи удерживать влагу, придавая ей более ровный, спокойный и здоровый вид.
```
- Style: Keep the Medium heading run.

#### E36.2 [B] Madecassoside: HE adds "anti-inflammatory", "moisture barrier"

- RU node: `667:579` — Rubik Regular 12, at (42, 283) w 340
- HE node(s): `793:381`
- Current RU (runs: Medium 12 [0,14) 'Madecassoside\n'; Regular 12 [14,180) 'Активный компонент, получаемый из растен'):
```text
Madecassoside
Активный компонент, получаемый из растения Centella asiatica. Помогает успокоить кожу, поддерживает нормальную функцию барьера и обладает антиоксидантными свойствами.
```
- HE text:
```text
Madecassoside
רכיב פעיל המופק מצמח הסנטלה האסיאתית. הוא מסייע להרגיע את מראה העור ולתמוך בתפקודו התקין של מחסום הלחות, אנטידלקתי ונוגד תהליך חמצון.
```
- Replacements (old → new):
  - “поддерживает нормальную функцию барьера и обладает антиоксидантными свойствами.” → “поддерживает нормальную функцию влагоудерживающего барьера, обладает противовоспалительными и антиоксидантными свойствами.”
- **New RU** (ready to paste):
```text
Madecassoside
Активный компонент, получаемый из растения Centella asiatica. Помогает успокоить кожу, поддерживает нормальную функцию влагоудерживающего барьера, обладает противовоспалительными и антиоксидантными свойствами.
```
- Style: Keep the Medium heading run.

#### E36.3 [C] Heading: same HE phrase as pp.30 and 33 ("Ключевые активные компоненты" there)

- RU node: `667:576` — Rubik Medium 16, at (42, 166) w 340
- HE node(s): `793:379`
- Current RU:
```text
Основные активные компоненты
```
- HE text:
```text
הרכיבים הפעילים המרכזיים
```
- **New RU** (ready to paste):
```text
Ключевые активные компоненты
```
- Style: Medium 16 as now.

### RU p.34 (→ p.38) — frame `667:543` “RU — 34 — MITOPEN” ↔ HE p.38 `793:401` “HE — 38 — MITOPEN”

#### E38.1 [IMG] Third product under "for infusing products": MITOTECH CELL BOOSTER kit photo (owner edit)

- RU node: `NEW in 667:543`
- HE node(s): `886:2`
- Style: Clone HE 886:2 (111×148, hash e2436bfbd7) into 667:543. Order as HE, left to right: V-TECH SYSTEM | MITOTECH CELL BOOSTER | EXOSIGNAL HAIR (the RU MITOPEN page is not mirrored, same as HE). Re-space the three pack-shots across the text column (x 312–750), bottoms level with the two existing shots (groups 702:4, 702:6).

#### E38.2 [A] Caption for the new product

- RU node: `NEW near 667:557`
- HE node(s): `886:3`
- HE text:
```text
MITOTECH
CELL BOOSTER
```
- **New RU** (ready to paste):
```text
MITOTECH
CELL BOOSTER
```
- Style: Clone 667:557 (Medium 12, as the other two captions; HE SemiBold 12, one weight for the whole caption), centred under the new photo, same baseline as 667:557/667:552.

#### E38.3 [A] Last bullet introduces the product row: HE "• for infusing products:"

- RU node: `667:554` — Rubik Regular 12, at (312, 139) w 438
- HE node(s): `793:416`
- Current RU:
```text
MITOPEN — профессиональный беспроводной аппарат для микронидлинга, создающий временные микроканалы в коже и открывающий путь для активных компонентов MITODERM.
В сочетании с профессиональными формулами аппарат способствует более эффективной доставке активных компонентов и позволяет проводить процедуру точно, равномерно и контролируемо.

• Регулируемая глубина игл 0,25–2,5 мм — позволяет точно адаптировать процедуру к зоне, толщине кожи и показаниям.
• Несколько регулируемых скоростей — для контроля плотности микроканалов и интенсивности стимуляции.
• До 5 скоростей работы.
• Эргономичный беспроводной дизайн — для точной, тихой и комфортной работы в течение дня.
• Предназначен для доставки активных компонентов.
```
- HE text:
```text
•  עומק מחט מתכוונן בין 0.25-2.5 מ״מ – התאמה מדויקת לכל אזור, לעובי העור ולאינדיקציה.
•  מספר מהירויות מתכווננות לשליטה בצפיפות המיקרו־תעלות ועוצמת הגירוי.
עד 5 מהירויות.
•  עיצוב ארגונומי ואלחוטי לעבודה מדויקת ושקטה לאורך יום קליני.
•  להחדרת חומרים:
```
- Replacements (old → new):
  - “• Предназначен для доставки активных компонентов.” → “• Для введения средств:”
- **New RU** (ready to paste):
```text
MITOPEN — профессиональный беспроводной аппарат для микронидлинга, создающий временные микроканалы в коже и открывающий путь для активных компонентов MITODERM.
В сочетании с профессиональными формулами аппарат способствует более эффективной доставке активных компонентов и позволяет проводить процедуру точно, равномерно и контролируемо.

• Регулируемая глубина игл 0,25–2,5 мм — позволяет точно адаптировать процедуру к зоне, толщине кожи и показаниям.
• Несколько регулируемых скоростей — для контроля плотности микроканалов и интенсивности стимуляции.
• До 5 скоростей работы.
• Эргономичный беспроводной дизайн — для точной, тихой и комфортной работы в течение дня.
• Для введения средств:
```

#### E38.4 [C] "Up to 5 speeds." is a continuation line without a bullet in HE

- RU node: `667:554` — Rubik Regular 12, at (312, 139) w 438
- HE node(s): `793:416`
- Current RU:
```text
MITOPEN — профессиональный беспроводной аппарат для микронидлинга, создающий временные микроканалы в коже и открывающий путь для активных компонентов MITODERM.
В сочетании с профессиональными формулами аппарат способствует более эффективной доставке активных компонентов и позволяет проводить процедуру точно, равномерно и контролируемо.

• Регулируемая глубина игл 0,25–2,5 мм — позволяет точно адаптировать процедуру к зоне, толщине кожи и показаниям.
• Несколько регулируемых скоростей — для контроля плотности микроканалов и интенсивности стимуляции.
• До 5 скоростей работы.
• Эргономичный беспроводной дизайн — для точной, тихой и комфортной работы в течение дня.
• Предназначен для доставки активных компонентов.
```
- HE text:
```text
•  עומק מחט מתכוונן בין 0.25-2.5 מ״מ – התאמה מדויקת לכל אזור, לעובי העור ולאינדיקציה.
•  מספר מהירויות מתכווננות לשליטה בצפיפות המיקרו־תעלות ועוצמת הגירוי.
עד 5 מהירויות.
•  עיצוב ארגונומי ואלחוטי לעבודה מדויקת ושקטה לאורך יום קליני.
•  להחדרת חומרים:
```
- Replacements (old → new):
  - “интенсивности стимуляции.⏎• До 5 скоростей работы.” → “интенсивности стимуляции.⏎До 5 скоростей.”
- **New RU** (ready to paste):
```text
MITOPEN — профессиональный беспроводной аппарат для микронидлинга, создающий временные микроканалы в коже и открывающий путь для активных компонентов MITODERM.
В сочетании с профессиональными формулами аппарат способствует более эффективной доставке активных компонентов и позволяет проводить процедуру точно, равномерно и контролируемо.

• Регулируемая глубина игл 0,25–2,5 мм — позволяет точно адаптировать процедуру к зоне, толщине кожи и показаниям.
• Несколько регулируемых скоростей — для контроля плотности микроканалов и интенсивности стимуляции.
До 5 скоростей.
• Эргономичный беспроводной дизайн — для точной, тихой и комфортной работы в течение дня.
• Предназначен для доставки активных компонентов.
```
- Style: Apply after E38.3 (same node).

### RU p.35 (→ p.39) — frame `667:527` “RU — 35 — MITOSCAN” ↔ HE p.39 `793:418` “HE — 39 — MITOSCAN”

#### E39.1 [B] HE "demonstrates hair density, NUMBER OF FOLLICLES, hair diameter and scalp condition"

- RU node: `667:534` — Rubik Regular 12.5, at (46, 133) w 434
- HE node(s): `793:426`
- Current RU:
```text
Передовой аппарат ZOOM IN для диагностики кожи головы и волос с камерой высокого увеличения X50 и X200.
Система позволяет объективно оценить плотность и количество волос, их диаметр и состояние кожи головы.
HD-увеличение и последовательная фотофиксация позволяют выявлять детали, невидимые невооружённым глазом, и отслеживать изменения в динамике.
```
- HE text:
```text
מכשיר ZOOM IN מתקדם לקרקפת ולשיער, המשלב מצלמה בהגדלה
גבוהה X50 ו X200
המערכת מדגימה באופן אובייקטיבי צפיפות שיער, מספר זקיקים, קוטר שערה
ומצב הקרקפת.
הגדלה HD ומעקב עקבי — מאפשרים לצלם את האזור, לזהות פרטים שאינם 
נראים בעין ולהשוות לאורך זמן.
```
- Replacements (old → new):
  - “Система позволяет объективно оценить плотность и количество волос, их диаметр и состояние кожи головы.” → “Система объективно показывает плотность волос, количество фолликулов, диаметр волоса и состояние кожи головы.”
- **New RU** (ready to paste):
```text
Передовой аппарат ZOOM IN для диагностики кожи головы и волос с камерой высокого увеличения X50 и X200.
Система объективно показывает плотность волос, количество фолликулов, диаметр волоса и состояние кожи головы.
HD-увеличение и последовательная фотофиксация позволяют выявлять детали, невидимые невооружённым глазом, и отслеживать изменения в динамике.
```

### Pages and blocks checked with no change needed

- RU p.13 (`667:817`, HE 13) — same meaning, item by item (7 audience items, MITOPEN line).
- RU p.14 (`667:807`, HE 14) — same; "4-Е ПОКОЛЕНИЕ" renders HE's Latin "4TH GENERATION" (meaning identical; keeping the Latin as HE would be an optional styling choice, not counted).
- RU p.20 → 24 / p.21 → 25 pack-shots of EXOSIGNAL SPRAY: another file of the same box and bottle (RU `667:759`, `667:749`, hash dca06568a4; HE `793:257` 7a8ed5b1fc, `793:279` 7b089e65a8) — same product, no change.
- RU p.26 → 30 (`667:649`) — all five ingredient texts match HE 796:10–19 / 796:45–46 (see Q on "basal cells"); Salicylic + Citric sits on RU p.26 instead of HE p.31 (layout only, E31.1 note).
- RU p.29 → 33 (`667:605`) — all ingredient texts match HE 796:69–79 and 796:111–114; subtitle already in the E28.2 wording.
- RU p.33 → 37 (`667:558`) — same title and captions.
- RU p.36 → 40 back cover (`667:520`) — the RU top image "RU 1" (`667:526`, hash 07e9a4f927) carries the Russian back-cover copy: same content as the HE art (company blurb, "contact us on WhatsApp", QR, site, Instagram). HE hides four background layers that RU keeps visible under the top image — no visible difference. Keep.
- Cover (`667:1008`): same visible photos (only the title changes, E1.1).
- Blocks that match HE inside edited pages: p.3 paragraphs 1 and 3, name heading and DERM line; p.5 VM paragraph `667:950`, advantages paragraph 3; p.6 kit description, package lines, benefits `667:918`; p.7 protocol `667:912`, gel-mask list (except E7.2); p.8 subtitle, step 3 text; p.9 package; p.10 active ingredients, package, last line; p.12 package, arrows; p.15 Spongilla paragraph `667:801`; p.18 headers; p.19 reaction paragraph; p.22 → 26 all except E26.1; p.23 → 27 all except E27.x; p.24 → 28 CELL RENEW and DERMA RECOVERY lines; p.25 → 29 indications ("Молодая кожа" = HE "young ages"); p.31 → 35 description and "who is it for" except E35.x; p.32 → 36 Panthenol, Hydrolyzed Collagen, Snail, Allantoin, Shea; p.34 → 38 subtitle and first paragraph; p.35 → 39 the other three blocks.

## 4. New RU pp.20–23 — MITOTECH CELL BOOSTER (clone the HE frames, translate node by node)

Translated from the Hebrew now on HE pp.20–23 (owner text 01/11 v2, `canon-v2.md`), with the RU protocol terms (`protocols-ru.md`, section "MITOTECH CELL BOOSTER"): концентрированный порошок, ампула-бустер / активные ампулы-бустеры, флакон, «Рекомендуемая дозировка: 0,5 мл два раза в день или 1 мл один раз в день», «Каждая пара флаконов рассчитана на использование в течение двух недель», «Всего до 60 процедур!», «домашняя программа ухода на 8 недель — весь набор», «отдать клиентке домой». Decimal comma in running text (0,5 мл), as in the RU protocols and RU catalogue (p.7 "1–1,5 мл", p.34 "0,25–2,5 мм"); product names keep the dot (MICRO BOOST 10%).

How to build each page: clone the HE frame into page `667:519`, rename it, set the RU texts below, then mirror. Mirroring (LTR): x_RU = 794 − x_HE − w for text boxes and content blocks; text alignment RIGHT → LEFT (CENTER stays); the two content columns swap (HE right column x 410 → RU x 54; HE left column x 54 → RU x 410); full-width nodes (x 54, w 686) stay. p.20: the product panel with the kit photo `941:19` moves to the right edge (as its glows and hairline), text column to the left. p.22: the five step columns run 1 → 5 left to right (step 1 at x 54, step 5 at x 614); icons move with their step, the pictograms are not flipped. p.23: kit icons stay with their lines. Remove every RLM (U+200F) left at line starts. Weights: HE SemiBold → RU Medium (RU edition uses Regular / Medium / Bold only); exception, as on HE: titles "MITOTECH " Rubik ExtraBold + "CELL BOOSTER" Rubik Light. Fit: Russian runs 30–50 % longer than the Hebrew; the 126 px step texts on p.22 (`957:4` … `957:271`) are the tightest — step 5 needs ~7 lines at 12 pt and reaches the note line `957:398` (y 495): set the step texts at 10 pt or move the note down (layout pass, one sample page first).

### New frame “RU — 20 — MITOTECH CELL BOOSTER” ← HE p.20 `941:2` “HE — 20 — MITOTECH CELL BOOSTER”

| HE node | HE geometry (x, y, w) → RU x | HE style | HE text | RU text | RU runs |
|---|---|---|---|---|---|
| `941:16` (running head, unchanged) | (60, 24, 180) → 554 | Rubik Bold 11 | MITODERM | MITODERM | — |
| `941:3` (title, unchanged (ExtraBold + Light, as HE)) | (340, 56, 400) → 54 | Rubik Light 30 / runs: ExtraBold 30 [0,9) 'MITOTECH '; Light 30 [9,21) 'CELL BOOSTER' | MITOTECH CELL BOOSTER | MITOTECH CELL BOOSTER | ExtraBold [0,9) “MITOTECH ”, Light [9,21) “CELL BOOSTER” |
| `941:4` (Latin subtitle, unchanged) | (340, 101, 400) → 54 | Rubik SemiBold 12 | ADVANCED SKIN TO CELL DELIVERY SYSTEM | ADVANCED SKIN TO CELL DELIVERY SYSTEM | — |
| `941:5` (lead) | (340, 122, 400) → 54 | Rubik Regular 12 | מערכת בוסטר דו־שלבית המבוססת על טכנולוגיית הולכה טרנסדרמלית מתקדמת, למראה עור מוצק, חלק ורווי בלחות. | Двухэтапная бустерная система на основе передовой технологии трансдермальной доставки — для более упругого, гладкого и увлажнённого вида кожи. | — |
| `941:11` (body, 4 paragraphs) | (340, 179, 400) → 54 | Rubik Regular 12 | מערכת טיפוח מתקדמת המשלבת חומצה היאלורונית במשקלים מולקולריים שונים, קולגן שעבר הידרוליזה ופפטידים ייעודיים, בטכנולוגיית הולכה המבוססת על הפפטיד DST-516.⏎הטכנולוגיה פותחה כדי להתמודד עם מגבלות החדירה של רכיבים פעילים דרך מחסום העור. במחקרי מעבדה על מודל עור אנושי הודגמה יכולת הולכה של חומצה היאלורונית אל שכבת הדרמיס.⏎המערכת מבוססת על שני שלבים המופעלים בעת הערבוב, ומיועדת לתמיכה בלחות העור, במוצקותו, בגמישותו ובשיפור מראה סימני הגיל.⏎מבנה הנוצר לאחר ערבוב קטן פיזית פי 1,000 (!) מנקבוביות העור, חודר דרך שכבות האפידרמיס, מגיע לדרמיס ויוצר אפקט דמוי פילר. | Передовая система ухода, сочетающая гиалуроновую кислоту разной молекулярной массы, гидролизованный коллаген и специальные пептиды, с технологией доставки на основе пептида DST-516.⏎Технология разработана, чтобы преодолеть ограничения проникновения активных компонентов через кожный барьер. В лабораторных исследованиях на модели человеческой кожи была продемонстрирована доставка гиалуроновой кислоты в слой дермы.⏎Система состоит из двух этапов, которые активируются при смешивании, и предназначена для поддержки увлажнённости, упругости и эластичности кожи и уменьшения видимых признаков старения.⏎Структура, образующаяся после смешивания, физически в 1000 (!) раз меньше пор кожи: она проходит через слои эпидермиса, достигает дермы и создаёт филлер-подобный эффект. | — |
| `941:17` (footer, unchanged) | (40, 535, 300) → 454 | Rubik Regular 8 | MITODERM \| WHERE SCIENCE MEETS BEAUTY | MITODERM \| WHERE SCIENCE MEETS BEAUTY | — |

RU texts as paste-ready blocks:

`941:5` (lead):
```text
Двухэтапная бустерная система на основе передовой технологии трансдермальной доставки — для более упругого, гладкого и увлажнённого вида кожи.
```
`941:11` (body, 4 paragraphs):
```text
Передовая система ухода, сочетающая гиалуроновую кислоту разной молекулярной массы, гидролизованный коллаген и специальные пептиды, с технологией доставки на основе пептида DST-516.
Технология разработана, чтобы преодолеть ограничения проникновения активных компонентов через кожный барьер. В лабораторных исследованиях на модели человеческой кожи была продемонстрирована доставка гиалуроновой кислоты в слой дермы.
Система состоит из двух этапов, которые активируются при смешивании, и предназначена для поддержки увлажнённости, упругости и эластичности кожи и уменьшения видимых признаков старения.
Структура, образующаяся после смешивания, физически в 1000 (!) раз меньше пор кожи: она проходит через слои эпидермиса, достигает дермы и создаёт филлер-подобный эффект.
```

### New frame “RU — 21 — MITOTECH CELL BOOSTER — активные компоненты” ← HE p.21 `941:21` “HE — 21 — MITOTECH CELL BOOSTER (המשך)”

| HE node | HE geometry (x, y, w) → RU x | HE style | HE text | RU text | RU runs |
|---|---|---|---|---|---|
| `941:22` (running head) | (560, 24, 180) → 54 | Rubik Bold 11 | MITODERM | MITODERM | — |
| `941:24` (title) | (54, 56, 686) → 54 (full width) | Rubik Light 30 / runs: ExtraBold 30 [0,9) 'MITOTECH '; Light 30 [9,21) 'CELL BOOSTER' | MITOTECH CELL BOOSTER | MITOTECH CELL BOOSTER | ExtraBold [0,9) “MITOTECH ”, Light [9,21) “CELL BOOSTER” |
| `941:25` (Latin subtitle) | (54, 96, 686) → 54 (full width) | Rubik SemiBold 12 | ADVANCED SKIN TO CELL DELIVERY SYSTEM | ADVANCED SKIN TO CELL DELIVERY SYSTEM | — |
| `941:29` (column heading) | (410, 150, 330) → 54 | Rubik SemiBold 14 | רכיבים פעילים | Активные компоненты | — |
| `941:30` (item 1 (first column in reading order)) | (410, 169, 330) → 54 | Rubik Regular 12 / runs: SemiBold 12 [0,26) '\u200f1. CONCENTRATED POWDER –\n'; Regular 12 [26,389) 'אבקה מרוכזת בטכנולוגיית ייבוש בהקפאה: אב' | 1. CONCENTRATED POWDER –⏎אבקה מרוכזת בטכנולוגיית ייבוש בהקפאה: אבקה ליופילית המכילה חומצה היאלורונית במשקל מולקולרי גבוה ונמוך ביחס 3:1, קולגן שעבר הידרוליזה ופפטידים מתקדמים.⏎הרכיבים עוברים תהליך ייבוש בהקפאה בטמפרטורה של 70°C−, המסייע בשמירה על יציבותם עד להפעלת הפורמולה. המערכת משלבת את טכנולוגיית DST-516, המבוססת על פפטיד חודר טרנסדרמלי, לתמיכה בהולכת רכיבים פעילים דרך מחסום העור. | 1. CONCENTRATED POWDER –⏎Концентрированный порошок, полученный методом сублимационной сушки: лиофилизированный порошок с гиалуроновой кислотой высокой и низкой молекулярной массы в соотношении 3:1, гидролизованным коллагеном и современными пептидами.⏎Компоненты проходят сублимационную сушку при температуре −70 °C, что помогает сохранять их стабильность до активации формулы. Система включает технологию DST-516 на основе трансдермального проникающего пептида — для поддержки доставки активных компонентов через кожный барьер. | Medium [0,24) “1. CONCENTRATED POWDER –” |
| `941:31` (item 2) | (54, 169, 330) → 410 | Rubik Regular 12 / runs: SemiBold 12 [0,23) '\u200f2. BOOSTING AMPOULE –\n'; Regular 12 [23,227) 'אמפולת בוסטר להפעלת הפורמולה: תמיסת בוסט' | 2. BOOSTING AMPOULE –⏎אמפולת בוסטר להפעלת הפורמולה: תמיסת בוסטר המכילה ניאצינאמיד, אדנוזין, לציטין וצרמידים. האמפולה מיועדת לערבוב עם האבקה המרוכזת ליצירת סרום פעיל במרקם קליל, הנספג במהירות ומעניק תחושת עור חלקה ולחות מוגברת. | 2. BOOSTING AMPOULE –⏎Ампула-бустер для активации формулы: бустерный раствор с ниацинамидом, аденозином, лецитином и церамидами. Ампула предназначена для смешивания с концентрированным порошком: получается активная сыворотка с лёгкой текстурой, которая быстро впитывается и дарит ощущение гладкой, более увлажнённой кожи. | Medium [0,21) “2. BOOSTING AMPOULE –” |
| `941:12` (heading) | (54, 260, 330) → 410 | Rubik SemiBold 14 | יתרונות מרכזיים | Основные преимущества | — |
| `941:13` (benefits) | (54, 279, 330) → 410 | Rubik Regular 12 | לחות אינטנסיבית \| מראה עור מוצק ומתוח יותר \| שיפור מראה קמטוטים \| תמיכה בגמישות העור \| שיפור מראה מרקם העור \| מראה עור חלק ואחיד \| תמיכה במחסום העור \| תחושת רכות \| מראה עור רענן וזוהר \| מערכת בוסטר ללא מחטים | Интенсивное увлажнение \| Более упругий и подтянутый вид кожи \| Уменьшение видимости мелких морщин \| Поддержка эластичности кожи \| Улучшение текстуры кожи \| Гладкий и ровный вид кожи \| Поддержка кожного барьера \| Ощущение мягкости \| Свежий и сияющий вид кожи \| Бустерная система без игл | — |
| `941:23` (footer) | (440, 535, 300) → 54 | Rubik Regular 8 | MITODERM \| WHERE SCIENCE MEETS BEAUTY | MITODERM \| WHERE SCIENCE MEETS BEAUTY | — |

RU texts as paste-ready blocks:

`941:29` (column heading):
```text
Активные компоненты
```
`941:30` (item 1 (first column in reading order)):
```text
1. CONCENTRATED POWDER –
Концентрированный порошок, полученный методом сублимационной сушки: лиофилизированный порошок с гиалуроновой кислотой высокой и низкой молекулярной массы в соотношении 3:1, гидролизованным коллагеном и современными пептидами.
Компоненты проходят сублимационную сушку при температуре −70 °C, что помогает сохранять их стабильность до активации формулы. Система включает технологию DST-516 на основе трансдермального проникающего пептида — для поддержки доставки активных компонентов через кожный барьер.
```
`941:31` (item 2):
```text
2. BOOSTING AMPOULE –
Ампула-бустер для активации формулы: бустерный раствор с ниацинамидом, аденозином, лецитином и церамидами. Ампула предназначена для смешивания с концентрированным порошком: получается активная сыворотка с лёгкой текстурой, которая быстро впитывается и дарит ощущение гладкой, более увлажнённой кожи.
```
`941:12` (heading):
```text
Основные преимущества
```
`941:13` (benefits):
```text
Интенсивное увлажнение | Более упругий и подтянутый вид кожи | Уменьшение видимости мелких морщин | Поддержка эластичности кожи | Улучшение текстуры кожи | Гладкий и ровный вид кожи | Поддержка кожного барьера | Ощущение мягкости | Свежий и сияющий вид кожи | Бустерная система без игл
```

### New frame “RU — 22 — MITOTECH CELL BOOSTER — приготовление” ← HE p.22 `956:2` “HE — 22 — MITOTECH CELL BOOSTER — הכנה”

| HE node | HE geometry (x, y, w) → RU x | HE style | HE text | RU text | RU runs |
|---|---|---|---|---|---|
| `956:3` (running head) | (560, 24, 180) → 54 | Rubik Bold 11 | MITODERM | MITODERM | — |
| `956:5` (title) | (54, 56, 686) → 54 (full width) | Rubik Light 30 / runs: ExtraBold 30 [0,9) 'MITOTECH '; Light 30 [9,21) 'CELL BOOSTER' | MITOTECH CELL BOOSTER | MITOTECH CELL BOOSTER | ExtraBold [0,9) “MITOTECH ”, Light [9,21) “CELL BOOSTER” |
| `956:6` (Latin subtitle) | (54, 96, 686) → 54 (full width) | Rubik SemiBold 12 | ADVANCED SKIN TO CELL DELIVERY SYSTEM | ADVANCED SKIN TO CELL DELIVERY SYSTEM | — |
| `950:2` (heading) | (410, 150, 330) → 54 | Rubik SemiBold 14 | אופן השימוש | Способ применения | — |
| `941:32` (how to use) | (360, 169, 380) → 54 | Rubik Regular 12 | מערבבים אמפולת בוסטר אחת עם בקבוקון האבקה המרוכזת עד לקבלת תמיסה אחידה ושקופה. מורחים על עור נקי ויבש ומעסים עד לספיגה.⏎– כל זוג בקבוקונים מיועד לשימוש עד שבועיים. | Смешать одну ампулу-бустер с флаконом концентрированного порошка до получения однородного прозрачного раствора. Нанести на чистую сухую кожу и массировать до впитывания.⏎– Каждая пара флаконов рассчитана на использование до двух недель. | — |
| `957:2` (heading of the 5-step strip) | (54, 230, 686) → 54 (full width) | Rubik SemiBold 14 | הכנה ב-5 שלבים | Приготовление в 5 шагов | — |
| `957:3` (step 1 title) | (614, 259, 126) → 54 | Rubik SemiBold 12 | 1. פתיחת הבקבוקונים | 1. Открыть флаконы | — |
| `957:4` (step 1 text) | (614, 404, 126) → 54 | Rubik Regular 12 | מסירים את הפקקים מבקבוקון האבקה המרוכזת ומאמפולת הבוסטר. | Снять крышки с флакона концентрированного порошка и с ампулы-бустера. | — |
| `957:46` (step 2 title) | (474, 259, 126) → 194 | Rubik SemiBold 12 | 2. ללא ניעור | 2. Не встряхивать | — |
| `957:47` (step 2 text) | (474, 404, 126) → 194 | Rubik Regular 12 | מוסיפים לאט 15 מ״ל מאמפולת הבוסטר לבקבוקון האבקה. יש להקפיד שלא יגלוש. לא לנער. | Медленно добавить 15 мл из ампулы-бустера во флакон с порошком, следя, чтобы раствор не перелился. Не встряхивать. | — |
| `957:161` (step 3 title) | (334, 259, 126) → 334 | Rubik SemiBold 12 | 3. להמתין שעה | 3. Подождать час | — |
| `957:162` (step 3 text) | (334, 404, 126) → 334 | Rubik Regular 12 | מניחים לאבקה להתמוסס בהדרגה. ממתינים לפחות שעה אחת להפעלה, ללא ניעור. | Дать порошку постепенно раствориться. Для активации подождать не менее одного часа, не встряхивая. | — |
| `957:193` (step 4 title) | (194, 259, 126) → 474 | Rubik SemiBold 12 | 4. לנער היטב | 4. Хорошо встряхнуть | — |
| `957:194` (step 4 text) | (194, 404, 126) → 474 | Rubik Regular 12 | לאחר ההמסה מחליפים את הפקק באפליקטור ומנערים היטב לערבוב מלא. | После растворения заменить крышку на аппликатор и хорошо встряхнуть для полного смешивания. | — |
| `957:270` (step 5 title) | (54, 259, 126) → 614 | Rubik SemiBold 12 | 5. יישום | 5. Нанесение | — |
| `957:271` (step 5 text) | (54, 404, 126) → 614 | Rubik Regular 12 | לוחצים קלות על האפליקטור כדי להוציא את המוצר. מינון מומלץ: 0.5 מ״ל פעמיים ביום או 1 מ״ל פעם ביום. | Слегка нажать на аппликатор, чтобы выдавить средство. Рекомендуемая дозировка: 0,5 мл два раза в день или 1 мл один раз в день. | — |
| `957:398` (note) | (54, 495, 686) → 54 (full width) | Rubik Regular 12 | הערה: בעת ניעור חזק עשויות להיווצר בועות. זה תקין — אפשר להשתמש בביטחון. | Примечание: при интенсивном встряхивании могут образоваться пузырьки. Это нормально — средство можно спокойно использовать. | — |
| `956:4` (footer) | (440, 535, 300) → 54 | Rubik Regular 8 | MITODERM \| WHERE SCIENCE MEETS BEAUTY | MITODERM \| WHERE SCIENCE MEETS BEAUTY | — |

RU texts as paste-ready blocks:

`950:2` (heading):
```text
Способ применения
```
`941:32` (how to use):
```text
Смешать одну ампулу-бустер с флаконом концентрированного порошка до получения однородного прозрачного раствора. Нанести на чистую сухую кожу и массировать до впитывания.
– Каждая пара флаконов рассчитана на использование до двух недель.
```
`957:2` (heading of the 5-step strip):
```text
Приготовление в 5 шагов
```
`957:3` (step 1 title):
```text
1. Открыть флаконы
```
`957:4` (step 1 text):
```text
Снять крышки с флакона концентрированного порошка и с ампулы-бустера.
```
`957:46` (step 2 title):
```text
2. Не встряхивать
```
`957:47` (step 2 text):
```text
Медленно добавить 15 мл из ампулы-бустера во флакон с порошком, следя, чтобы раствор не перелился. Не встряхивать.
```
`957:161` (step 3 title):
```text
3. Подождать час
```
`957:162` (step 3 text):
```text
Дать порошку постепенно раствориться. Для активации подождать не менее одного часа, не встряхивая.
```
`957:193` (step 4 title):
```text
4. Хорошо встряхнуть
```
`957:194` (step 4 text):
```text
После растворения заменить крышку на аппликатор и хорошо встряхнуть для полного смешивания.
```
`957:270` (step 5 title):
```text
5. Нанесение
```
`957:271` (step 5 text):
```text
Слегка нажать на аппликатор, чтобы выдавить средство. Рекомендуемая дозировка: 0,5 мл два раза в день или 1 мл один раз в день.
```
`957:398` (note):
```text
Примечание: при интенсивном встряхивании могут образоваться пузырьки. Это нормально — средство можно спокойно использовать.
```

### New frame “RU — 23 — MITOTECH CELL BOOSTER — сочетания и комплект” ← HE p.23 `956:23` “HE — 23 — MITOTECH CELL BOOSTER — שאלות נפוצות”

| HE node | HE geometry (x, y, w) → RU x | HE style | HE text | RU text | RU runs |
|---|---|---|---|---|---|
| `956:24` (running head) | (560, 24, 180) → 54 | Rubik Bold 11 | MITODERM | MITODERM | — |
| `956:26` (title) | (54, 56, 686) → 54 (full width) | Rubik Light 30 / runs: ExtraBold 30 [0,9) 'MITOTECH '; Light 30 [9,21) 'CELL BOOSTER' | MITOTECH CELL BOOSTER | MITOTECH CELL BOOSTER | ExtraBold [0,9) “MITOTECH ”, Light [9,21) “CELL BOOSTER” |
| `956:27` (Latin subtitle) | (54, 96, 686) → 54 (full width) | Rubik SemiBold 12 | ADVANCED SKIN TO CELL DELIVERY SYSTEM | ADVANCED SKIN TO CELL DELIVERY SYSTEM | — |
| `950:3` (heading, column 1) | (410, 150, 330) → 54 | Rubik SemiBold 14 | שילוב במכשור ובטיפולים מקצועיים | Сочетание с аппаратами и профессиональными процедурами | — |
| `941:35` (combination 1) | (410, 169, 330) → 54 | Rubik Regular 12 / runs: SemiBold 12 [0,50) '1. לאחר שימוש במזרק הביוספיקול: MICRO BO'; Regular 12 [50,85) 'מחדירים \u200e1–2 מ״ל של החומר המעורבב.\n'; SemiBold 12 [85,110) 'אופציה להמשך טיפול ביתי:\n'; Regular 12 [110,204) 'ניתן לתת ללקוחה הביתה את האמפולה המעורבב' | 1. לאחר שימוש במזרק הביוספיקול: MICRO BOOST 10% –⏎מחדירים 1–2 מ״ל של החומר המעורבב.⏎אופציה להמשך טיפול ביתי:⏎ניתן לתת ללקוחה הביתה את האמפולה המעורבבת – מינון מומלץ 0.5 מ״ל פעמיים ביום או 1 מ״ל פעם ביום. | 1. После применения шприца BIOSPICULE: MICRO BOOST 10% –⏎Ввести 1–2 мл смешанного средства.⏎Вариант продолжения ухода дома:⏎Смешанную ампулу можно отдать клиентке домой — рекомендуемая дозировка 0,5 мл два раза в день или 1 мл один раз в день. | Medium [0,56) “1. После применения шприца BIOSPICULE: MICRO BOOST 10% –”, Medium [92,123) “Вариант продолжения ухода дома:” |
| `941:36` (combination 2) | (410, 253, 330) → 54 | Rubik Regular 12 / runs: SemiBold 12 [0,12) '\u200f2. MITOPEN\n'; Regular 12 [12,109) 'בשילוב עם מכשיר המיטופן. ניתן להשתמש בחו'; SemiBold 12 [109,134) 'אופציה להמשך טיפול ביתי:\n'; Regular 12 [134,238) 'לאחר מכן ניתן לתת ללקוחה הביתה את האמפול' | 2. MITOPEN⏎בשילוב עם מכשיר המיטופן. ניתן להשתמש בחומר המעורבב בשילוב עם טכנולוגיית מיקרונידלינג – 1–2 מ״ל.⏎אופציה להמשך טיפול ביתי:⏎לאחר מכן ניתן לתת ללקוחה הביתה את האמפולה המעורבבת – מינון מומלץ: 0.5 מ״ל פעמיים ביום או 1 מ״ל פעם ביום. | 2. MITOPEN⏎В сочетании с аппаратом MITOPEN. Смешанное средство можно использовать вместе с технологией микронидлинга — 1–2 мл.⏎Вариант продолжения ухода дома:⏎Затем смешанную ампулу можно отдать клиентке домой — рекомендуемая дозировка: 0,5 мл два раза в день или 1 мл один раз в день. | Medium [0,10) “2. MITOPEN”, Medium [127,158) “Вариант продолжения ухода дома:” |
| `941:37` (combination 3) | (410, 352, 330) → 54 | Rubik Regular 12 / runs: SemiBold 12 [0,36) '3. תוכנית טיפוח ביתית למשך 8 שבועות\n'; Regular 12 [36,150) '\u200f– כל הערכה למכירה\nמינון מומלץ: 0.5 מ״ל ' | 3. תוכנית טיפוח ביתית למשך 8 שבועות⏎– כל הערכה למכירה⏎מינון מומלץ: 0.5 מ״ל פעמיים ביום או 1 מ״ל פעם ביום.⏎כל זוג בקבוקונים מיועד לשימוש במשך שבועיים. | 3. Домашняя программа ухода на 8 недель⏎– весь набор для продажи⏎Рекомендуемая дозировка: 0,5 мл два раза в день или 1 мл один раз в день.⏎Каждая пара флаконов рассчитана на использование в течение двух недель. | Medium [0,39) “3. Домашняя программа ухода на 8 недель” |
| `959:2` (heading, column 2 (kit icons stay with their lines)) | (54, 150, 330) → 410 | Rubik SemiBold 14 | תכולת האריזה | Содержимое упаковки | — |
| `959:76` (kit line 1) | (54, 184, 259) → 481 | Rubik Regular 12 | אבקה מרוכזת – 4 × 154 מ״ג | Концентрированный порошок – 4 × 154 мг | — |
| `959:104` (kit line 2) | (54, 222, 259) → 481 | Rubik Regular 12 | אמפולות בוסטר פעילות – 4 × 15 מ״ל | Активные ампулы-бустеры – 4 × 15 мл | — |
| `959:90` (kit line 3 (not in the owner text; HE keeps it)) | (54, 260, 260) → 480 | Rubik Regular 12 | אפליקטורים – 4 יח׳ | Аппликаторы – 4 шт. | — |
| `941:33` (kit total) | (54, 291, 330) → 410 | Rubik Regular 12 | סה״כ עד 60 טיפולים! | Всего до 60 процедур! | — |
| `956:25` (footer) | (440, 535, 300) → 54 | Rubik Regular 8 | MITODERM \| WHERE SCIENCE MEETS BEAUTY | MITODERM \| WHERE SCIENCE MEETS BEAUTY | — |

RU texts as paste-ready blocks:

`950:3` (heading, column 1):
```text
Сочетание с аппаратами и профессиональными процедурами
```
`941:35` (combination 1):
```text
1. После применения шприца BIOSPICULE: MICRO BOOST 10% –
Ввести 1–2 мл смешанного средства.
Вариант продолжения ухода дома:
Смешанную ампулу можно отдать клиентке домой — рекомендуемая дозировка 0,5 мл два раза в день или 1 мл один раз в день.
```
`941:36` (combination 2):
```text
2. MITOPEN
В сочетании с аппаратом MITOPEN. Смешанное средство можно использовать вместе с технологией микронидлинга — 1–2 мл.
Вариант продолжения ухода дома:
Затем смешанную ампулу можно отдать клиентке домой — рекомендуемая дозировка: 0,5 мл два раза в день или 1 мл один раз в день.
```
`941:37` (combination 3):
```text
3. Домашняя программа ухода на 8 недель
– весь набор для продажи
Рекомендуемая дозировка: 0,5 мл два раза в день или 1 мл один раз в день.
Каждая пара флаконов рассчитана на использование в течение двух недель.
```
`959:2` (heading, column 2 (kit icons stay with their lines)):
```text
Содержимое упаковки
```
`959:76` (kit line 1):
```text
Концентрированный порошок – 4 × 154 мг
```
`959:104` (kit line 2):
```text
Активные ампулы-бустеры – 4 × 15 мл
```
`959:90` (kit line 3 (not in the owner text; HE keeps it)):
```text
Аппликаторы – 4 шт.
```
`941:33` (kit total):
```text
Всего до 60 процедур!
```

## 5. Second pass (all 40 HE pages, looking only for misses)

Re-read every HE text node (399) against its RU counterpart, frame by frame, on all 36 mapped pages; on pp.20–23 the builder checks that every HE text node is mapped to an RU text (it fails otherwise). Images compared by hash on all 36 pairs (differences only on pp.1, 4, 15, 20, 21, 34, 36 → covered by E4.1, E15.1, E38.1 and the no-change notes), frame fills compared on all pages (only p.4 differs → E4.1), and renders compared for pp.1, 4, 15, 24/20, 25/21, 40/36.

Added or confirmed in the second pass (mostly small items first noted and then decided there): the missing running head on p.3 (E3.1) and "organelle in all cells of the body" (E3.4); "the whole aim is to RESTORE the barrier" and the step-2 title wording on p.8 (E8.2, E8.4); the subtitle "and hair" on p.12 (E12.1); "without rinsing" on p.23 → 27 (E27.2); "renewal, building, radiance and evenness" on p.25 → 29 (E29.1); "moisture and vitality" on p.30 → 34 (E34.2); "number of follicles" on p.35 → 39 (E39.1); the reading order of the spray audience list (E27.3). Nothing else was found: every other HE node is either covered by an edit above or listed under "checked with no change".

Not counted as edits (pure typography or same meaning): HE RLM/LRM marks and spacing; HE double spaces; heading colons (HE p.25 title ends with ":"); RU-only headings that only label a HE block ("Показания:" p.15, "Рекомендуется:" p.27, "Синтетические экзосомы" p.6); bullets vs " | " lists; "·" vs "•" bullets; singular "Spongilla" vs HE plural "spongillas" in the ToC; sizes 9/10.5/12.5/13/15 pt of the RU edition (off the HE scale 8·10·11·12·14·16·21·30·41) — a separate layout pass, not part of this list.

## 6. Open questions

1. ToC: HE section 7 (BIOSPICULE™ series) also lists "• MITOTECH CELL BOOSTER two-step booster system with transdermal delivery" (HE `884:2`), although MITOTECH is section 5 with its own pages 20–23. Mirrored as instructed — keep it in RU, or remove it from HE and RU together?
2. p.15 (`793:242`): HE literally says the renewal cycle is shortened "from 7 to 28 days" (reversed); E15.3 writes "с 28 до 7 дней". Confirm.
3. "AGING" (HE pp.15 and 19) is a Latin item next to "אנטי-אייג׳ינג"; rendered "Возрастные изменения кожи" (E15.4, E19.3). Keep, or drop the duplicate?
4. PDRN source: HE "from salmon stem cells" (`824:111` p.6, `824:196` p.12); RU said "полученный из лосося". E7.3 / E12.4 follow HE — confirm.
5. p.30 (`796:12`): HE "gradual removal of basal cells"; RU keeps "постепенному обновлению поверхности кожи" (a literal "базальных клеток" would be a wrong claim). Keep the RU?
6. p.23: "Аппликаторы – 4 шт." (HE `959:90`) is not in the owner text of 01/11 (it comes from the user guide R7); kept because HE keeps it.
7. p.22: "until a uniform, clear solution forms" (owner text) vs user guide R7 "the mixture turns cloudy" — already open on HE; RU follows HE.
8. p.4 (E4.1): switch RU to the HE visual (kit photo on dark brown) instead of the exosome-sphere background?
9. Block distribution (text identical either way): pp.6–7 V-TECH ingredients vs results (E6.8), pp.8–9 EXO-NAD step 3 (E8.5), Salicylic + Citric p.30 vs p.31, Beta-Glucan + Akebia p.33 vs p.34. Mirror HE block for block, or keep the RU distribution?
10. Fit: the repeated headers on pp.17, 19, 31, 34 (E17.2, E19.2, E31.1, E34.1) and the longer texts (E5.2, E12.5, E15.3, E16.1, E16.2) need a layout pass; on p.19 the header adds ~90 px. Two columns as HE, or one scale step down (12 → 10)?
11. p.24 title "Дополняющие средства для домашнего ухода" (E24.1): two lines at 41 pt or one line at 30 pt?
12. Cover (E1.1): "Каталог продукции" (HE "Product catalogue") instead of "Каталог" — confirm.
13. MITOTECH pages: mirror the layout (default here), or keep the HE side as RU p.10 (EXOCELL MASK) and p.34 (MITOPEN) do?
14. p.22 step texts at 126 px width overflow at 12 pt in Russian; 10 pt for the five step texts, or a lower note line?
