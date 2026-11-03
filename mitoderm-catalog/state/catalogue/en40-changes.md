# EN catalogue → HE final (40 pp.): complete change list

Figma `x7NyyASEmlMwazkZmZwOXk`. Reference: HE page `793:2` "EXPORT — HE — Design 40" (FINAL, not to be modified). Target: EN page `667:2` "EXPORT — EN — Design 36". Read-only survey of 01/11/2026; nothing in Figma was changed.

Dumps (all text nodes: id, characters, font runs, position; image nodes with hash): `dump/he-40.json`, `dump/en-36.json`, extra (frame fills, ToC colours) `dump/extra.json`. Machine-readable copy of this list: `changes.json`.

Page mapping: EN 1–19 ↔ HE 1–19; EN old 20–36 ↔ HE 24–40 (they become EN 24–40); EN 20–23 are new (HE 20–23, MITOTECH).

## Legend and conventions

- **A**: HE content that the EN lacks or states differently (owner edits since the EN was made, missing blocks). Must do.
- **B**: EN translation drifts from the HE meaning (missing claim, different item, softened wording). Recommended.
- **C**: consistency, units, typos, empty nodes. Recommended.
- **IMG**: image edit. **L**: layout-only note, no text change. **Q**: owner decision (also listed under Open questions).
- "New EN" blocks are exact text, ready to paste: line breaks are real `\n` in the node; nothing else is hidden. Do not paste the ```text fences.
- **Weight mapping used by the EN edition** (keep it): HE SemiBold / Bold inline emphasis → EN **Medium**; HE ExtraBold titles → EN **Bold**; HE Regular → Regular. Exception, as on HE: MITOTECH titles = "MITOTECH " Rubik **ExtraBold** + "CELL BOOSTER" Rubik **Light**. In this file "emphasised" = the EN emphasis weight (Medium).
- Text editing: load fonts with `getRangeAllFontNames(0, len)` first; for small edits use `insertCharacters`/`deleteCharacters` (mind style bleed at line breaks); for full replacements set `characters` and then re-apply the emphasis runs listed (offsets given are for the new text).
- Language checks after editing: no Hebrew (U+0590–05FF), no Cyrillic, no RLM/LRM (U+200E/200F) on EN pages. Today the EN page has none of these.

Summary: A: 15, B: 19, B/Q: 2, C: 22, IMG: 3, L: 3, L/Q: 1, Q: 1 page/global items, plus the new ToC (27 lines) and 4 new MITOTECH pages (46 text nodes).

## 1. Structure of the EN page (do first)

- **G1** Rename page `667:2` → `EXPORT — EN — Design 40`.
- **G2** Insert four new frames for EN pp.20–23 by cloning HE `941:2`, `941:21`, `956:2`, `956:23` into `667:2`, then mirror (section 4 below). Names:
  - `941:2` → `EN — 20 — MITOTECH CELL BOOSTER`
  - `941:21` → `EN — 21 — MITOTECH CELL BOOSTER — Active ingredients`
  - `956:2` → `EN — 22 — MITOTECH CELL BOOSTER — Preparation`
  - `956:23` → `EN — 23 — MITOTECH CELL BOOSTER — Combinations and kit`
- **G3** Renumber the old EN frames 20–36 to 24–40 (name change only):

| old EN | node | new name |
|---|---|---|
| 20 | `667:242` | EN — 24 — Complementary Home Care |
| 21 | `667:229` | EN — 25 — Synthetic Exosome Series |
| 22 | `667:213` | EN — 26 — EXOTECH GEL |
| 23 | `667:199` | EN — 27 — EXOSIGNAL SPRAY |
| 24 | `667:182` | EN — 28 — BIOSPICULE Series |
| 25 | `667:163` | EN — 29 — CELL RENEW 1.5% |
| 26 | `667:138` | EN — 30 — CELL RENEW 1.5% — Active ingredients |
| 27 | `668:10` | EN — 31 — CELL RENEW 1.5% — Ingredients and use |
| 28 | `667:120` | EN — 32 — CELLULAR AGE DEFENSE 2.5% |
| 29 | `667:93` | EN — 33 — CELLULAR AGE DEFENSE 2.5% — Active ingredients |
| 30 | `668:12` | EN — 34 — CELLULAR AGE DEFENSE 2.5% — Ingredients and use |
| 31 | `667:74` | EN — 35 — DERMA RECOVERY |
| 32 | `667:56` | EN — 36 — DERMA RECOVERY — Ingredients and use |
| 33 | `667:44` | EN — 37 — Professional Equipment |
| 34 | `667:27` | EN — 38 — MITOPEN |
| 35 | `667:10` | EN — 39 — MITOSCAN |
| 36 | `667:3` | EN — 40 — Back Cover |

- **G4** Canvas and layer order (skill "figma-print-layout", step 8). Canvas grid as today: page n (2–39) at x = 0 if n even else 820, y = 641 × floor(n/2); p.1 at (820, 0); p.40 at (0, 0). So new p.20 (0, 6410), p.21 (820, 6410), p.22 (0, 7051), p.23 (820, 7051); old p.20 → (0, 7692) … old p.35 → p.39 (820, 12179). Layers: `children` must read 40, 39, …, 1 (first page last). Only the 40 frames on the page; `exportSettings` only on the frames, none on the clones' descendants.
- **G5** Units "ml" → "mL", "mg/ml" → "mg/mL" in body text (language rule). Nodes: p.6 `667:442` 5 ml ×2 -> 5 mL (E6.5); p.6 `667:436` "20 mg/ml" disappears with E6.2; p.7 `667:417` 1–1.5 ml (E7.1); p.9 `667:386` 15 ml, 5 × 5 ml (E9.3); p.12 `667:341` 20 mg/ml (E12.1); p.12 `667:343` 5 × 5 ml (E12.3); p.18 `667:269` 3 ml (E18.1); p.26 (old 22) `667:222` 30 ml (E26.1). Keep label copies exactly as HE: 667:206 "HOME USE · 15 ml", 667:177 / 667:133 "30 ml ℮ 1.0 fl.oz.", 667:90 "50 ml ℮ 1.69 fl.oz.". "mm" (MITOPEN) unchanged.
- **G6** One word for HE "סדרה": **series** (ToC, pp.24, 25, 26, 28; optional also "range" in `667:85` p.35). Done inside E24.2, E24.3, E25.1, E26.2, E28.1 and the ToC.
- **G7** Empty / stray nodes to delete: `667:492`, `667:499` (p.2), `667:466` (p.4), `667:356`, `667:357` (p.11), `667:342` (p.12), loose "™" `667:260` (p.24) and `667:188` (p.28) after E24.3/E28.1.

## 2. Table of contents (EN p.2, frame `667:480`) — mirrors HE p.2 `793:12`

HE p.2 shows **no page numbers** (none on the page), so the EN ToC has none either. For reference only, the sections run: 1 → p.3; 2 → pp.4–10; 3 → pp.11–13; 4 → pp.14–19; 5 → pp.20–23; 6 → pp.24–27; 7 → pp.28–36; 8 → pp.37–39; back cover p.40.

Layout: HE right column (sections 1–5, x 420) becomes the EN **left** column (x 54); HE left column (sections 6–8, x 54) becomes the EN **right** column (x 420); both 320 px wide, same y rhythm as HE (section heads 14 pt, sub-heading 12 pt, bullets 10 pt — use the HE sizes, the current EN 12 pt bullets will not fit eight sections). Colours as HE: section heads and sub-heading ink `#1a1817` (EN now `#57524a`), product bullets gold `#9e661f`, descriptive lines grey `#57524a`.

Complete new EN ToC (in reading order):

```text
Table of Contents
PROFESSIONAL AESTHETIC CATALOG
1. About MITODERM
2. Synthetic exosomes for professional facial treatments
• V-TECH
• EXO-NAD
• EXOCELL MASK
3. Synthetic exosomes for scalp and hair treatments
• EXOSIGNAL HAIR
4. BIOSPICULE™ technology
• What are spongillas and how do they work in the skin?
• The science and technology behind BIOSPICULE™
• MICRO BOOST 10% professional in-clinic treatment
5. MITOTECH CELL BOOSTER
Advanced skin to cell delivery system
6. Complementary products for home use
Synthetic exosome series
• EXOTECH GEL
• EXOSIGNAL SPRAY
7. BIOSPICULE™ series
• CELL RENEW 1.5% home-care serum for renewal and brightening
• CELLULAR AGE DEFENSE 2.5% advanced serum for firming and anti-ageing
• DERMA RECOVERY restorative cream for soothing and skin barrier support
• MITOTECH CELL BOOSTER two-step booster system with transdermal delivery
8. Professional equipment for the clinic
• MITOPEN professional microneedling device
• MITOSCAN advanced system for scalp and hair diagnostics
```

| # | col | EN node | HE node | HE text | new EN text | style |
|---|---|---|---|---|---|---|
| 1 | L | `667:508` (now: "Table of Contents") | `793:15` | תוכן העניינים | **Table of Contents** | Title as now (EN Bold 30; HE ExtraBold 30, ink #1a1817) |
| 2 | L | `667:507` (now: "PROFESSIONAL AESTHETIC CATALOG") | `793:14` | PROFESSIONAL AESTHETIC CATALOG | **PROFESSIONAL AESTHETIC CATALOG** | As now |
| 3 | L | `667:482` (now: "1. About MITODERM") | `793:18` | ‏1. אודות MITODERM | **1. About MITODERM** | Section head |
| 4 | L | `667:483` (now: "2. Synthetic exosomes for professional facial treatments") | `793:19` | ‏2. אקסוזומים סינתטיים לטיפולי פנים מקצועיים | **2. Synthetic exosomes for professional facial treatments** | Section head |
| 5 | L | `667:484` (now: "• V-TECH") | `793:20` | ‏• V-TECH | **• V-TECH** | Product bullet (gold) |
| 6 | L | `667:485` (now: "• EXO-NAD") | `793:21` | ‏• EXO-NAD | **• EXO-NAD** | Product bullet (gold) |
| 7 | L | `667:486` (now: "• EXOCELL MASK") | `793:22` | ‏• EXOCELL MASK | **• EXOCELL MASK** | Product bullet (gold) |
| 8 | L | `667:487` (now: "3. Synthetic exosomes for scalp and hair treatments") | `793:23` | ‏3. אקסוזומים סינתטיים לטיפולי קרקפת ושיער | **3. Synthetic exosomes for scalp and hair treatments** | Section head |
| 9 | L | `667:488` (now: "• EXOSIGNAL HAIR") | `793:24` | ‏• EXOSIGNAL HAIR | **• EXOSIGNAL HAIR** | Product bullet (gold) |
| 10 | L | `667:489` (now: "4. BIOSPICULE™ technology") | `793:25` | ‏4. טכנולוגיית BIOSPICULE™‎ | **4. BIOSPICULE™ technology** | Section head |
| 11 | L | `667:490` (now: "• What is Spongilla and how does it work in the skin") | `793:26` | ‏• מהן ספונגילות וכיצד הן פועלות בעור? | **• What are spongillas and how do they work in the skin?** | Descriptive line (Regular, grey #57524a) — text changes |
| 12 | L | `667:491` (now: "• The science and technology behind BIOSPICULE™") | `793:27` | ‏• המדע והטכנולוגיה שמאחורי BIOSPICULE™‎ | **• The science and technology behind BIOSPICULE™** | Descriptive line (Regular, grey) |
| 13 | L | `667:493` (now: "• MICRO BOOST 10% professional in-clinic treatment") | `793:29` | ‏• MICRO BOOST 10% טיפול מקצועי לקליניקה | **• MICRO BOOST 10% professional in-clinic treatment** | Product bullet (gold) |
| 14 | L | `NEW (clone 667:489)` | `936:2` | ‏5. MITOTECH CELL BOOSTER | **5. MITOTECH CELL BOOSTER** | Section head; runs: "5. MITOTECH " = section-head weight (HE SemiBold), "CELL BOOSTER" = Rubik Light, same size; emphasised run [[0, 12]] |
| 15 | L | `NEW (clone 667:490)` | `936:4` | Advanced skin to cell delivery system | **Advanced skin to cell delivery system** | Descriptive line (Regular, grey) — HE already has it in English |
| 16 | R | `667:494` (now: "5. Complementary products for home use") | `793:30` | ‏6. תכשירים משלימים לשימוש ביתי | **6. Complementary products for home use** | Section head — number 5 -> 6 |
| 17 | R | `667:495` (now: "Synthetic exosome range") | `793:31` | ‏סדרת האקסוזומים הסינתטיים | **Synthetic exosome series** | Sub-heading (HE SemiBold 12, ink) — "range" -> "series"; size 14 -> 12 |
| 18 | R | `667:496` (now: "• EXOTECH GEL") | `793:32` | ‏• EXOTECH GEL | **• EXOTECH GEL** | Product bullet (gold) |
| 19 | R | `667:497` (now: "• EXOSIGNAL SPRAY") | `793:33` | ‏• EXOSIGNAL SPRAY | **• EXOSIGNAL SPRAY** | Product bullet (gold) |
| 20 | R | `667:498` (now: "BIOSPICULE™ range") | `793:34` | ‏7. סדרת BIOSPICULE™‎ | **7. BIOSPICULE™ series** | Now a numbered SECTION HEAD (HE 793:34 SemiBold 14), not a sub-heading |
| 21 | R | `667:500` (now: "• CELL RENEW 1.5% ") | `793:36` | ‏• CELL RENEW 1.5% סרום ביתי לחידוש והבהרה | **• CELL RENEW 1.5% home-care serum for renewal and brightening** | Product bullet (gold), descriptor added; trailing space removed |
| 22 | R | `667:501` (now: "• CELLULAR AGE DEFENSE 2.5% ") | `793:37` | ‏• CELLULAR AGE DEFENSE 2.5% סרום מתקדם למיצוק ואנטי-אייג׳ינג | **• CELLULAR AGE DEFENSE 2.5% advanced serum for firming and anti-ageing** | Product bullet (gold), descriptor added |
| 23 | R | `667:502` (now: "• DERMA RECOVERY CREAM") | `793:38` | ‏• DERMA RECOVERY קרם משקם להרגעה ולתמיכה במחסום העור | **• DERMA RECOVERY restorative cream for soothing and skin barrier support** | Product bullet (gold); HE writes "DERMA RECOVERY" + "restorative cream ..." (CREAM moves into the descriptor) |
| 24 | R | `NEW (clone 667:502)` | `884:2` | ‏• MITOTECH CELL BOOSTER מערכת בוסטר דו־שלבית בהולכה טרנסדרמלית | **• MITOTECH CELL BOOSTER two-step booster system with transdermal delivery** | Product bullet (gold), 2 lines as HE; mirror HE even though MITOTECH is also section 5 (Q) |
| 25 | R | `667:503` (now: "6. Professional equipment for the clinic") | `793:39` | 8. מכשור מקצועי לקליניקה | **8. Professional equipment for the clinic** | Section head — number 6 -> 8 |
| 26 | R | `667:504` (now: "• MITOPEN professional microneedling device") | `793:40` | ‏• MITOPEN מכשיר מיקרונידלינג מקצועי | **• MITOPEN professional microneedling device** | Product bullet (gold) |
| 27 | R | `667:505` (now: "• MITOSCAN advanced system for scalp and hair diagnostics") | `793:41` | ‏• MITOSCAN מערכת מתקדמת לאבחון הקרקפת והשיער | **• MITOSCAN advanced system for scalp and hair diagnostics** | Product bullet (gold) |

Delete the empty nodes `667:492`, `667:499`. The current EN section numbers 5 and 6 become 6 and 8; "BIOSPICULE™ range" becomes section 7. HE line `884:2` (MITOTECH bullet inside section 7) is mirrored as instructed although MITOTECH is also section 5 — see Open questions.

## 3. Page-by-page edits (existing EN pages)

### EN p.1 — frame `667:510` "EN — 01 — Cover" ↔ HE p.1 `824:43`

#### E1.1 [B/Q] Cover word

- Target: `667:517`
- Current EN (`667:517`, Rubik/Regular/55):
```text
CATALOG
```
- HE (`824:50`, p.1, Rubik/Regular/55):
```text
קטלוג מוצרים
```
- New EN (paste):
```text
PRODUCT CATALOG
```
- Style / notes: Rubik Regular 55 as now; at 55 pt the line is ~480 px wide (box 341 px) — widen the box to ~500 px centred, or break into two lines "PRODUCT\nCATALOG". Owner may prefer to keep "CATALOG" (Q).

### EN p.3 — frame `667:469` "EN — 03 — About MITODERM" ↔ HE p.3 `824:52`

#### E3.1 [A] Name story: MITO / DERM

- Target: `667:477`
- Current EN (`667:477`, [0,4) Rubik/Bold/12 + [4,85) Rubik/Regular/12 + [85,89) Rubik/Bold/12 + [89,158) Rubik/Regular/12):
```text
MITO — representing the cellular energy that drives function, renewal, and vitality.
DERM — representing the skin, where science and aesthetics come together.
```
- HE (`824:64`, p.3, Rubik/Bold/12; HE emphasis: whole node (Bold)):
```text
MITO
```
- HE (`824:61`, p.3, Rubik/Regular/12):
```text
 – מיטוכונדריה - אברון בכל תאי הגוף האחראי על הפקת אנרגיה
  – דרמיס

```
- HE (`824:63`, p.3, Rubik/Bold/12; HE emphasis: whole node (Bold)):
```text
 DERM
```
- New EN (paste):
```text
MITO — mitochondria, the organelle in every cell of the body responsible for producing energy
DERM — dermis
```
- Emphasised runs in the new text: "MITO" [0, 4], "DERM" [94, 98]
- Style / notes: "MITO" and "DERM" emphasised (EN Medium/Bold as now = HE Bold 12), rest Regular 12.

#### E3.2 [B] About, paragraph 1: HE says "cosmetics and professional aesthetics in skin and scalp"

- Target: `667:472`
- Current EN (`667:472`, Rubik/Regular/12):
```text
MITODERM is an Israeli company specializing in the development, import, and distribution of advanced technologies for professional aesthetics, skin, and scalp care.

The company collaborates with leading laboratories, manufacturers, and technology partners in Italy and South Korea to provide clinics in Israel with professional solutions that combine science, innovation, and advanced treatment protocols.

At the core of our portfolio are advanced technologies based on synthetic exosomes, peptides, PDRN, NAD+, and biomimetic ingredients, alongside BIOSPICULE™ technology, based on purified Spongilla-derived spicules that undergo rigorous purification and quality-control processes.
```
- HE (`824:56`, p.3, Rubik/Regular/12):
```text
מיטודרם היא חברה ישראלית המתמחה בפיתוח, בייבוא ובהנגשה של טכנולוגיות מתקדמות, לעולמות הקוסמטיקה והאסתטיקה המקצועית בתחום העור והקרקפת.

החברה פועלת בשיתוף פעולה עם מעבדות, יצרנים ותאגידים מובילים באיטליה ובדרום קוריאה, במטרה להביא לקליניקות בישראל פתרונות מקצועיים המשלבים בין מדע, חדשנות ופרוטוקולי טיפול מתקדמים.

בליבת הפעילות שלנו עומדות טכנולוגיות מתקדמות המבוססות על אקסוזומים סינתטיים, פפטידים, PDRN, +NAD ורכיבים ביומימטיים, לצד טכנולוגיית BIOSPICULE™ המבוססת על ספונגילות – מיקרו מחטים שעברו תהליכי טיהור ובקרה קפדניים.
```
- New EN (paste):
```text
MITODERM is an Israeli company specializing in the development, import, and distribution of advanced technologies for professional cosmetics and aesthetics in skin and scalp care.

The company collaborates with leading laboratories, manufacturers, and technology partners in Italy and South Korea to provide clinics in Israel with professional solutions that combine science, innovation, and advanced treatment protocols.

At the core of our portfolio are advanced technologies based on synthetic exosomes, peptides, PDRN, NAD+, and biomimetic ingredients, alongside BIOSPICULE™ technology, based on purified Spongilla-derived spicules that undergo rigorous purification and quality-control processes.
```
- Style / notes: Only the end of sentence 1 changes ("for professional aesthetics, skin, and scalp care." -> "for professional cosmetics and aesthetics in skin and scalp care."). Regular 12.

#### E3.3 [L] EN-only heading "The Story Behind the Name" (HE has only the sentence)

- Target: `667:475`
- Current EN (`667:475`, Rubik/Medium/12):
```text
The Story Behind the Name
The name MITODERM was born from the connection between two worlds:
```
- HE (`824:60`, p.3, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
השם מיטודרם נולד מתוך חיבור בין שני עולמות:
```
- Style / notes: Optional: keep (harmless) or delete the first line to mirror HE exactly. No translation change.

### EN p.4 — frame `667:459` "EN — 04 — Synthetic Exosomes" ↔ HE p.4 `824:67`

#### E4.1 [IMG] Section opener visual: HE shows the V-TECH kit photo on solid #241c12; EN shows an exosome-sphere background image (frame fill IMG 6a48aa79d9) and keeps the same kit photo 667:467 HIDDEN

- Target: `667:459 (frame fill) + 667:467`
- HE node `824:67` (image / frame, see dump)
- HE node `824:77` (image / frame, see dump)
- Style / notes: Set frame 667:459 fill to solid #241c12 (as HE 824:67), unhide 667:467 (same image d217c5045b as HE 824:77) and size/place it as HE mirrored: 300×287 at x=414, y=137 (now 286×273 at 414,185). If the exosome background was a deliberate EN choice, ask the owner (Q).

#### E4.2 [C] Empty text node

- Target: `667:466`
- Current EN (`667:466`, ):
```text

```
- Style / notes: Delete (characters = "").

### EN p.5 — frame `667:445` "EN — 05 — Synthetic Exosomes — Science" ↔ HE p.5 `824:79`

#### E5.1 [B] "Exosomes are ... secreted by stem cells" (HE paragraph 1)

- Target: `667:454`
- Current EN (`667:454`, Rubik/Regular/12):
```text
Exosomes are nanoscale extracellular vesicles involved in intercellular communication. They can carry a variety of biological molecules and facilitate their transfer between cells as part of natural cellular communication processes.

```
- HE (`824:89`, p.5, [0,177) Rubik/Regular/12 + [177,198) Rubik/Bold/12 + [198,680) Rubik/Regular/12; HE emphasis: "‏האקסוזומים הסינתטיים" (Bold 12)):
```text
‏אקסוזומים הם בועיות ננומטריות המופרשות מתאי אב ומשתתפות בתהליכי תקשורת בין־תאית. הן נושאות מולקולות ביולוגיות שונות ומעבירות אותן בין תאים, כחלק ממנגנוני התקשורת הטבעיים בגוף.
‏האקסוזומים הסינתטיים פותחו בהשראת מנגנון ביולוגי דומה. הם מתוכננים כמערכות נשא מתקדמות, בעלות מעטפת המדמה מאפיינים מבניים של ממברנת התא ומאפשרות לשלב בתוכן רכיבים פעילים ולהוביל אותם באופן ממוקד ויעיל פנימה אל התאים שלנו. 
‏האקסוזומים הסינתטיים המיוצרים באיטליה פועלים כשליחי וולט שמעבירים מידע מתא לתא. בתוך הבועיות יש רכיבים פעילים כגון PDRN, פפטידים ורכיבים נוספים שנבחרו בקפידה בהתאם למטרת הפורמולה.
‏למעשה המבנה הנונמטרי של האקסוזום נועד להגן על הרכיבים שהוא נושא, לתמוך בהעברתם ולשפר את חדירותם. 
```
- New EN (paste):
```text
Exosomes are nanoscale vesicles secreted by stem cells that take part in intercellular communication. They carry various biological molecules and transfer them between cells as part of the body's natural communication mechanisms.

```
- Style / notes: Regular 12. Keeps the trailing line break the node has now.

#### E5.2 [B] Synthetic exosomes: envelope mimics the cell membrane; "act like couriers carrying information from cell to cell" (HE paragraphs 2–4)

- Target: `667:455`
- Current EN (`667:455`, [0,18) Rubik/Medium/12 + [18,665) Rubik/Regular/12):
```text
Synthetic exosomes are engineered delivery systems inspired by these biological mechanisms. Their structure is designed to mimic certain characteristics of natural vesicles, enabling selected active ingredients to be encapsulated and supporting their targeted and efficient delivery.
The synthetic exosome technology developed in Italy functions as an advanced delivery system for carefully selected active ingredients, including PDRN, peptides, and other components chosen according to the purpose of each formulation.
The nanoscale structure is designed to protect the encapsulated ingredients, support their delivery, and enhance their penetration into the skin.
```
- HE (`824:89`, p.5, [0,177) Rubik/Regular/12 + [177,198) Rubik/Bold/12 + [198,680) Rubik/Regular/12; HE emphasis: "‏האקסוזומים הסינתטיים" (Bold 12)):
```text
‏אקסוזומים הם בועיות ננומטריות המופרשות מתאי אב ומשתתפות בתהליכי תקשורת בין־תאית. הן נושאות מולקולות ביולוגיות שונות ומעבירות אותן בין תאים, כחלק ממנגנוני התקשורת הטבעיים בגוף.
‏האקסוזומים הסינתטיים פותחו בהשראת מנגנון ביולוגי דומה. הם מתוכננים כמערכות נשא מתקדמות, בעלות מעטפת המדמה מאפיינים מבניים של ממברנת התא ומאפשרות לשלב בתוכן רכיבים פעילים ולהוביל אותם באופן ממוקד ויעיל פנימה אל התאים שלנו. 
‏האקסוזומים הסינתטיים המיוצרים באיטליה פועלים כשליחי וולט שמעבירים מידע מתא לתא. בתוך הבועיות יש רכיבים פעילים כגון PDRN, פפטידים ורכיבים נוספים שנבחרו בקפידה בהתאם למטרת הפורמולה.
‏למעשה המבנה הנונמטרי של האקסוזום נועד להגן על הרכיבים שהוא נושא, לתמוך בהעברתם ולשפר את חדירותם. 
```
- New EN (paste):
```text
Synthetic exosomes were developed with a similar biological mechanism in mind. They are designed as advanced carrier systems with an envelope that mimics structural features of the cell membrane, allowing active ingredients to be incorporated and delivered in a targeted, efficient way into our cells.
The synthetic exosomes made in Italy act like couriers, carrying information from cell to cell. Inside the vesicles are active ingredients such as PDRN, peptides, and other components carefully selected according to the purpose of each formulation.
The nanoscale structure is designed to protect the encapsulated ingredients, support their delivery, and enhance their penetration into the skin.
```
- Emphasised runs in the new text: "Synthetic exosomes" [0, 18]
- Style / notes: First two words emphasised (HE Bold "האקסוזומים הסינתטיים" = EN Medium as now). HE says "שליחי וולט" (Wolt couriers, an Israeli delivery brand) — brand dropped in EN.

#### E5.3 [A] Advantages: HE paragraph 3 ("once the molecules arrive inside, a chain of biological processes ... renewal, repair") is missing in EN

- Target: `667:456`
- Current EN (`667:456`, Rubik/Regular/12):
```text
Unlike exosomes derived from human, animal, or plant sources, synthetic exosomes are not obtained from living biological material.
Their engineered structure enables the encapsulation of selected active ingredients, including larger molecules whose delivery may otherwise be limited. This approach is designed to protect the active ingredients and support their effective delivery to the skin.
```
- HE (`824:90`, p.5, Rubik/Regular/12):
```text
בניגוד לאקסוזומים המופקים מתאים אנושיים, מבעלי חיים או מצמחים, האקסוזומים הסינתטיים אינם מופקים ממקור חי. 
המבנה הייחודי שלהם מאפשר לשלב בתוכם רכיבים פעילים ומולקולות גדולות שלא היו יכולות לחדור לתאי המטרה לולא המבנה.
עם הגעתם של המולקולות פנימה, מופעלת שרשרת של פעילויות ותהליכים ביולוגיים הגורמים להתחלה של תהליכי התחדשות, שיקום ושיפור מראה העור.
```
- New EN (paste):
```text
Unlike exosomes derived from human, animal, or plant sources, synthetic exosomes are not obtained from living biological material.
Their unique structure allows active ingredients and large molecules to be incorporated that could not reach their target cells without it.
Once these molecules arrive inside, a chain of biological activities and processes is triggered, initiating renewal, repair, and an improvement in the appearance of the skin.
```
- Style / notes: Regular 12. The EN sentence "This approach is designed to protect the active ingredients..." is not in HE and is dropped.

### EN p.6 — frame `667:427` "EN — 06 — V-TECH SYSTEM" ↔ HE p.6 `824:94`

#### E6.1 [A] Subtitle: HE "two-step system: bio-lifting serum and gel mask for intensive hydration and renewal"

- Target: `667:438`
- Current EN (`667:438`, [0,16) Rubik/Medium/14 + [16,22) Rubik/Regular/14 + [22,40) Rubik/Medium/14):
```text
Professional Kit with Synthetic Exosomes
```
- HE (`824:106`, p.6, [0,14) Rubik/Bold/14 + [14,16) Rubik/Regular/14 + [16,20) Rubik/Bold/14 + [20,33) Rubik/Regular/14 + [33,42) Rubik/Bold/14 + [42,64) Rubik/Regular/14; HE emphasis: "מערכת דו-שלבית" (Bold 14), "סרום" (Bold 14), "ומסכת ג׳ל" (Bold 14)):
```text
מערכת דו-שלבית: סרום ביו-ליפטינג ומסכת ג׳ל לחות וחידוש אינטנסיבי
```
- New EN (paste):
```text
Two-step system: bio-lifting serum and gel mask for intensive hydration and renewal
```
- Emphasised runs in the new text: "Two-step system" [0, 15], "serum" [29, 34], "gel mask" [39, 47]
- Style / notes: 14 pt; emphasised runs as HE (HE Bold "מערכת דו-שלבית", "סרום", "ומסכת ג׳ל") = EN Medium, rest Regular. One line in 496 px at 14 pt — check width.

#### E6.2 [B] Description block: HE "Inside the synthetic exosomes the formula combines:"; salmon detail belongs to the ingredient list (see E7.2)

- Target: `667:436`
- Current EN (`667:436`, [0,129) Rubik/Regular/12 + [129,151) Rubik/Medium/12 + [151,241) Rubik/Regular/12):
```text
A professional treatment kit based on synthetic exosomes, developed using advanced Italian technology.
Synthetic Exosome Formula
The formula combines:
PDRN 2% (20 mg/ml), derived from salmon
Biomimetic peptide complex
Apple stem cell extract
```
- HE (`824:103`, p.6, [0,90) Rubik/Regular/12 + [90,130) Rubik/Bold/12 + [130,180) Rubik/Regular/12; HE emphasis: "בתוך אקסוזומים סינתטיים הפורמולה משלבת:" (Bold 12)):
```text
ערכה מקצועית המבוססת על אקסוזומים סינתטיים  בטכנולוגיה איטלקית מתקדמת.
Synthetic Exosomes
בתוך אקסוזומים סינתטיים הפורמולה משלבת:
PDRN 2%
קומפלקס פפטידים ביומימטיים
תאי גזע של תפוח
```
- New EN (paste):
```text
A professional kit based on synthetic exosomes, using advanced Italian technology.
Synthetic Exosomes
Inside the synthetic exosomes, the formula combines:
PDRN 2%
Biomimetic peptide complex
Apple stem cells
```
- Emphasised runs in the new text: "Inside the synthetic exosomes, the formula combines:" [102, 154]
- Style / notes: Emphasis moves from "Synthetic Exosome Formula" to the line "Inside the synthetic exosomes, the formula combines:" (HE Bold run). Regular 12 elsewhere.

#### E6.3 [A] Indications: 13 items in HE; EN lacks "Angiogenesis – formation of new blood vessels" and words several items differently

- Target: `667:444`
- Current EN (`667:444`, Rubik/Regular/12):
```text
Deep skin revitalization | Signs of ageing | Wrinkles and fine lines | Dull, tired-looking skin | Post-acne marks and scars | Post-surgical scars | Uneven skin texture and tone | Post-inflammatory hyperpigmentation (PIH) | Loss of elasticity | Skin firming | Supporting the skin barrier | Improving overall skin appearance
```
- HE (`824:105`, p.6, Rubik/Regular/12):
```text
טיפול בעומק של העור | אנטי-אייג׳ינג | קמטים וקמטוטים | עור חסר ברק וחיוניות | צלקות פוסט אקנה | צלקות לאחר ניתוח | שיפור מרקם וגוון העור | כתמים פוסט דלקתיים PIH | אנגיוגנזה – היווצרות כלי דם חדשים | שיפור איכות העור | לעור חסר גמישות | מיצוק | הפחתת סימני הגיל ושיקום מחסום העור
```
- New EN (paste):
```text
Deep skin treatment | Anti-ageing | Wrinkles and fine lines | Skin lacking radiance and vitality | Post-acne scars | Post-surgical scars | Improved skin texture and tone | Post-inflammatory hyperpigmentation (PIH) | Angiogenesis – formation of new blood vessels | Improved skin quality | Skin lacking elasticity | Firming | Reducing signs of ageing and restoring the skin barrier
```
- Style / notes: Regular 12, items separated by " | " as HE (B3). Box grows ~1–2 lines; check against 667:420 below.

#### E6.4 [C] Heading wording consistency

- Target: `667:440`
- Current EN (`667:440`, Rubik/Medium/14):
```text
Pack Contents
```
- HE (`824:108`, p.6, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
תכולת האריזה
```
- New EN (paste):
```text
Package Contents
```
- Style / notes: Same heading as pp.9, 10, 12, 23 ("Package Contents").

#### E6.5 [C] Units

- Target: `667:442`
- Current EN (`667:442`, Rubik/Regular/12):
```text
Serum: 5 ampoules × 5 ml
Gel Mask: 5 sachets × 5 ml
```
- HE (`824:112`, p.6, Rubik/Regular/12):
```text
סרום 5 אמפולות × 5 מ״ל
מסכת ג’ל 5 שקיות × 5 מ״ל
```
- New EN (paste):
```text
Serum: 5 ampoules × 5 mL
Gel Mask: 5 sachets × 5 mL
```
- Style / notes: Regular 12.

#### E6.6 [L/Q] Block distribution across the spread: HE p.6 holds "Active ingredients", HE p.7 holds the results statement + benefits; EN has them swapped

- Target: `667:439, 667:441 (EN p.7) ↔ 667:420, 667:421 (EN p.6)`
- Current EN (`667:439`, Rubik/Medium/14):
```text
Active Ingredients
```
- HE (`824:107`, p.6, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
רכיבים פעילים
```
- HE (`824:109`, p.6, [0,24) Rubik/SemiBold/12 + [24,125) Rubik/Regular/12 + [125,157) Rubik/SemiBold/12 + [157,286) Rubik/Regular/12; HE emphasis: "סרום Synthetic Exosomes" (SemiBold 12), "מסכת ג׳ל לאחר האמפולה ללא שטיפה" (SemiBold 12)):
```text
סרום Synthetic Exosomes
PDRN 2%
:Biomimetic Peptides
Acetyl Decapeptide-3 & Oligopeptide-20
תאי גזע של תפוח Malus domestica

מסכת ג׳ל לאחר האמפולה ללא שטיפה
PDRN
‏Acetyl Heptapeptide-9 על נשא זהב קולואידי
Copper Tripeptide-1 ‏ נחושת טריפפטיד
פוליסכריד מריר חלזון
חומצה היאלורונית
אלוורה
```
- HE (`824:123`, p.7, Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
שיפור מיידי בלחות ובזוהר כבר מהטיפול הראשון; תוצאות מבניות ושיפור במרקם ובצפיפות מצטברות לאורך הסדרה.
```
- HE (`824:124`, p.7, Rubik/Regular/12):
```text
עור חיוני בריא ורענן | מחזיק תוצאות מבניות לאורך זמן | מיצוק |
איכות ומרקם | אלסטיות | שיפור בגוון העור.
```
- Style / notes: Content is complete across pp.6–7 (no text change). Swap only if the owner wants the EN to mirror HE block-for-block (English is ~50% longer; check fit).

### EN p.7 — frame `667:411` "EN — 07 — V-TECH SYSTEM — Ingredients and protocol" ↔ HE p.7 `824:114`

#### E7.1 [A] "At the end of the treatment": DERMA RECOVERY → DERMA RECOVERY CREAM (owner edit B5); units

- Target: `667:417`
- Current EN (`667:417`, [0,65) Rubik/Regular/12 + [65,89) Rubik/Medium/12 + [89,152) Rubik/Regular/12 + [152,180) Rubik/Medium/12 + [180,322) Rubik/Regular/12):
```text
Face | Neck | Décolleté | Hands
Quantity: 1–1.5 ml per treatment
Additional Combinations
Microneedling | RF Microneedling | BIOSPICULE™ 10% | Laser CO₂
At the End of the Treatment
EXOCELL MASK | DERMA RECOVERY
Sun protection

Standard RF may also be used at the beginning of the treatment, before microneedling (optional).
```
- HE (`824:120`, p.7, [0,63) Rubik/Regular/12 + [63,79) Rubik/Medium/12 + [79,141) Rubik/Regular/12 + [141,154) Rubik/Medium/12 + [154,263) Rubik/Regular/12; HE emphasis: "שילובים נוספים:" (Medium 12), "בסיום טיפול:" (Medium 12)):
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
- New EN (paste):
```text
Face | Neck | Décolleté | Hands
Quantity: 1–1.5 mL per treatment
Additional Combinations
Microneedling | RF Microneedling | BIOSPICULE™ 10% | Laser CO₂
At the End of the Treatment
EXOCELL MASK | DERMA RECOVERY CREAM
Sun protection

Standard RF may also be used at the beginning of the treatment, before microneedling (optional).
```
- Emphasised runs in the new text: "Additional Combinations" [65, 88], "At the End of the Treatment" [152, 179]
- Style / notes: Emphasis unchanged (the two sub-heads). Minimal edit: insert " CREAM" after "DERMA RECOVERY" (Regular run) and "ml" -> "mL".

#### E7.2 [A] Active ingredients: "Acetyl Heptapeptide-9 on a colloidal gold carrier" (owner edit B4); PDRN 2% line carries HE annotation 824:111 "20 mg/mL from salmon stem cells"

- Target: `667:441`
- Current EN (`667:441`, [0,24) Rubik/Medium/12 + [24,135) Rubik/Regular/12 + [135,201) Rubik/Medium/12 + [201,351) Rubik/Regular/12):
```text
Synthetic Exosome Serum
PDRN 2%
Biomimetic Peptides: Acetyl Decapeptide-3 & Oligopeptide-20
Apple Stem Cell Extract (Malus domestica)

Gel Mask
Designed for use after the ampoule. No rinsing required.
PDRN 1% – Low Molecular Weight
Acetyl Heptapeptide-9 with Colloidal Gold
Copper Tripeptide-1
Snail Secretion Polysaccharides
Hyaluronic Acid
Aloe Vera
```
- HE (`824:109`, p.6, [0,24) Rubik/SemiBold/12 + [24,125) Rubik/Regular/12 + [125,157) Rubik/SemiBold/12 + [157,286) Rubik/Regular/12; HE emphasis: "סרום Synthetic Exosomes" (SemiBold 12), "מסכת ג׳ל לאחר האמפולה ללא שטיפה" (SemiBold 12)):
```text
סרום Synthetic Exosomes
PDRN 2%
:Biomimetic Peptides
Acetyl Decapeptide-3 & Oligopeptide-20
תאי גזע של תפוח Malus domestica

מסכת ג׳ל לאחר האמפולה ללא שטיפה
PDRN
‏Acetyl Heptapeptide-9 על נשא זהב קולואידי
Copper Tripeptide-1 ‏ נחושת טריפפטיד
פוליסכריד מריר חלזון
חומצה היאלורונית
אלוורה
```
- HE (`824:111`, p.6, Rubik/Regular/12):
```text
‏20 מ״ג/מ״ל מתא גזע של סלמון
```
- HE (`824:110`, p.6, Rubik/Regular/12):
```text
במשקל מולקולרי נמוך (1%)
```
- New EN (paste):
```text
Synthetic Exosome Serum
PDRN 2% – 20 mg/mL, from salmon stem cells
Biomimetic Peptides: Acetyl Decapeptide-3 & Oligopeptide-20
Apple Stem Cell Extract (Malus domestica)

Gel Mask
Designed for use after the ampoule. No rinsing required.
PDRN 1% – Low Molecular Weight
Acetyl Heptapeptide-9 on a colloidal gold carrier
Copper Tripeptide-1
Snail Secretion Polysaccharides
Hyaluronic Acid
Aloe Vera
```
- Emphasised runs in the new text: "Synthetic Exosome Serum" [0, 23], "Gel Mask
Designed for use after the ampoule. No rinsing required." [170, 235]
- Style / notes: Emphasis as now (HE SemiBold "סרום Synthetic Exosomes" and "מסכת ג׳ל לאחר האמפולה ללא שטיפה"). "from salmon stem cells" is HE wording — see open question on PDRN source.

#### E7.3 [L] EN-only heading "Expected Results" above the results statement

- Target: `667:420`
- Current EN (`667:420`, Rubik/Medium/12):
```text
Expected Results
Visible improvement in hydration and radiance from the first treatment. Skin structure, texture, and density continue to improve throughout the treatment course.
```
- HE (`824:123`, p.7, Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
שיפור מיידי בלחות ובזוהר כבר מהטיפול הראשון; תוצאות מבניות ושיפור במרקם ובצפיפות מצטברות לאורך הסדרה.
```
- Style / notes: Optional: keep (HE has the sentence without a heading).

### EN p.8 — frame `667:396` "EN — 08 — EXO-NAD" ↔ HE p.8 `824:130`

#### E8.1 [B] "a total of 30% acids" (EN adds "approximately")

- Target: `667:403`
- Current EN (`667:403`, Rubik/Regular/12):
```text
A biphasic formula combining a lipid phase and an acid phase.
The lipid phase helps prepare the skin and maintain comfort during the treatment. The acid phase helps remove dead skin cells, improve skin texture, and support a controlled renewal process.
The formula contains a combination of active acids, including AHA and BHA, at a total concentration of approximately 30%, together with tranexamic acid and antioxidant ingredients.
```
- HE (`824:140`, p.8, Rubik/Regular/10):
```text
פורמולה דו-פאזית המשלבת פאזה ליפידית ופאזה חומצית.
הפאזה הליפידית מסייעת בהכנת העור ובשמירה על תחושת נוחות במהלך הטיפול. הפאזה החומצית מסייעת בהסרת תאים מתים, בשיפור מרקם העור ובעידוד תהליך התחדשות מבוקר.
הפורמולה מכילה שילוב חומצות פעילות, ובהן AHA ו-BHA,  בסה”כ-30% חומצות, לצד חומצה טרנקסמית ורכיבים נוגדי חמצון.
```
- New EN (paste):
```text
A biphasic formula combining a lipid phase and an acid phase.
The lipid phase helps prepare the skin and maintain comfort during the treatment. The acid phase helps remove dead skin cells, improve skin texture, and support a controlled renewal process.
The formula contains a combination of active acids, including AHA and BHA, at a total concentration of 30%, together with tranexamic acid and antioxidant ingredients.
```
- Style / notes: Delete the word "approximately " only.

#### E8.2 [L] Step 3 LONGEVITY SERUM is on HE p.8, on EN p.9

- Target: `667:409, 667:410 (EN p.9)`
- Current EN (`667:409`, Rubik/Medium/14):
```text
3. LONGEVITY SERUM – Skin Longevity & Vitality
```
- HE (`824:146`, p.8, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
.3
```
- HE (`824:147`, p.8, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
 ⁠LONGEVITY SERUM – סרום אריכות וחיוניות העור
```
- HE (`824:148`, p.8, Rubik/Regular/10):
```text
סרום מקצועי מתקדם המשלב מבנים אקסוזומליים סינתטיים עם NAD⁺‎, אפיטלון, GHK-Cu, פפטידים ביומימטיים.
הסרום פותח במטרה לתמוך בתקשורת בין־תאית, באנרגיית התא ובתהליכי ההתחדשות הטבעיים שלו. הוא מסייע בשיפור מראה העור, האלסטיות ובהגברת הלחות, ובכך תומך במראה עור מחודש זוהר ובריא יותר.
```
- Style / notes: Content identical; no change unless block-for-block mirroring is wanted.

### EN p.9 — frame `667:381` "EN — 09 — EXO-NAD — Benefits and use" ↔ HE p.9 `824:149`

#### E9.1 [A] Key benefits: HE "suitable for all pigmentation types" (EN says "all skin types"), item-by-item list of 16

- Target: `667:393`
- Current EN (`667:393`, Rubik/Regular/12):
```text
Removal of dead skin cells | Accelerated skin renewal | Improved skin texture | Improved firmness and elasticity | Reduced appearance of fine lines | Suitable for all skin types | Suitable for Fitzpatrick skin types I–VI | Helps improve uneven skin tone | Suitable for melasma-prone skin | Helps improve the appearance of sun spots and age spots | Helps improve the appearance of PIH and post-acne marks | Enhances skin radiance | Ideal before special events | Suitable for mature, tired, and dull-looking skin | Anti-ageing benefits
```
- HE (`824:160`, p.9, Rubik/Regular/12):
```text
הסרת תאים מתים | האצת התחדשות | שיפור מרקם העור | שיפור מוצקות ואלסטיות | הפחתת מראה קמטוטים | מתאים לכל סוגי הפיגמנטציה | כל סוגי הפצפטריק | שיפור בגוון העור | מותר במלזמה | סניל לנטיגו | כתמי אקנה PIH טיפול זוהר לפני ארוע | לעור בוגר עייף וחסר ברק | זוהר | חידוש | אנטי-אייג׳ינג
```
- New EN (paste):
```text
Removal of dead skin cells | Accelerated renewal | Improved skin texture | Improved firmness and elasticity | Reduced appearance of fine lines | Suitable for all pigmentation types | All Fitzpatrick skin types | Improved skin tone | Suitable for melasma | Senile lentigo | Acne marks (PIH) | Glow treatment before an event | Mature, tired, and dull-looking skin | Radiance | Renewal | Anti-ageing
```
- Style / notes: Regular 12.

#### E9.2 [C] First line lacks its bullet "· "

- Target: `667:389`
- Current EN (`667:389`, Rubik/Regular/12):
```text
One treatment every 3–4 weeks
· Three-stage protocol tailored to the individual indication
· Suitable for all skin types and year-round use
· Can be used as a single treatment or as part of a treatment course
```
- HE (`824:156`, p.9, Rubik/Regular/12):
```text
· טיפול אחד כל 3-4 שבועות
· פרוטוקול תלת-שלבי לפי התוויה 
· כל סוגי העור. כל ימות השנה 
· לא מחייב סדרה
```
- New EN (paste):
```text
· One treatment every 3–4 weeks
· Three-stage protocol tailored to the individual indication
· Suitable for all skin types and year-round use
· Can be used as a single treatment or as part of a treatment course
```
- Style / notes: Insert "· " at index 0 (Regular 12).

#### E9.3 [C] Units

- Target: `667:386`
- Current EN (`667:386`, Rubik/Regular/12):
```text
Biphasic Peel – 15 ml
pH Normalizer – 5 × 5 ml
Longevity Serum – 5 × 5 ml
```
- HE (`824:153`, p.9, [0,1) Rubik/SemiBold/12 + [1,70) Rubik/Regular/12):
```text

Biphasic Peeling 15ml
‏PH Normalizer 5×5 מ״ל
‏Longevity Serum 5×5 מ״ל
```
- New EN (paste):
```text
Biphasic Peel – 15 mL
pH Normalizer – 5 × 5 mL
Longevity Serum – 5 × 5 mL
```
- Style / notes: HE writes "Biphasic Peeling 15ml" / "PH Normalizer"; EN keeps the component names used in the p.8 headings (EXO BIPHASIC PEEL, pH NORMALIZER).

### EN p.10 — frame `667:361` "EN — 10 — EXOCELL MASK" ↔ HE p.10 `824:164`

#### E10.1 [B] Paragraph 3: HE "can be used in any treatment protocol after procedures"

- Target: `667:369`
- Current EN (`667:369`, [0,320) Rubik/Regular/12 + [320,425) Rubik/Medium/12 + [425,767) Rubik/Regular/12):
```text
Based on advanced adhesion technology, synthetic exosomal structures, and a complex of active ingredients that support hydration and soothing.
The mask was developed as a finishing step after professional cosmetic treatments, particularly when the skin requires intensive hydration and support of the epidermal barrier.
It is suitable for post-procedure protocols, especially for dry, tired, sensitive, or devitalized skin.

Its thin, flexible bio-cellulose structure adheres evenly to the skin with minimal air pockets. This close contact creates a moist environment and allows continuous contact between the active serum and the skin throughout the treatment.
The result is a feeling of comfort and freshness, leaving the skin hydrated, smooth, supple, and radiant.
```
- HE (`824:172`, p.10, [0,233) Rubik/Regular/12 + [233,327) Rubik/SemiBold/12; HE emphasis: "‏ניתן להשתמש בה בכל פרוטוקול טיפול לאחר פרוצדורות ובמיוחד לעור יבש, עייף, רגיש או חסר חיוניות." (SemiBold 12)):
```text
‏מבוססת על שילוב בין טכנולוגיית הצמדה מתקדמת, מבנים אקסוזומליים סינתטיים ומכלול רכיבים פעילים התומכים בלחות והרגעה.
‏המסכה פותחה לשימוש בסיום טיפולים קוסמטיים מקצועיים, ובמיוחד כאשר העור זקוק ללחות אינטנסיבית ולשיקום מחסום אפידרמלי.
‏ניתן להשתמש בה בכל פרוטוקול טיפול לאחר פרוצדורות ובמיוחד לעור יבש, עייף, רגיש או חסר חיוניות.
```
- New EN (paste):
```text
Based on advanced adhesion technology, synthetic exosomal structures, and a complex of active ingredients that support hydration and soothing.
The mask was developed as a finishing step after professional cosmetic treatments, particularly when the skin requires intensive hydration and support of the epidermal barrier.
It can be used in any post-procedure treatment protocol, especially for dry, tired, sensitive, or devitalized skin.

Its thin, flexible bio-cellulose structure adheres evenly to the skin with minimal air pockets. This close contact creates a moist environment and allows continuous contact between the active serum and the skin throughout the treatment.
The result is a feeling of comfort and freshness, leaving the skin hydrated, smooth, supple, and radiant.
```
- Emphasised runs in the new text: "It can be used in any post-procedure treatment protocol, especially for dry, tired, sensitive, or devitalized skin." [320, 435]
- Style / notes: The emphasised sentence stays emphasised (HE SemiBold run).

#### E10.2 [B] Heading: HE "combining with any treatment protocol and professional equipment in the clinic"

- Target: `667:377`
- Current EN (`667:377`, Rubik/Medium/14):
```text
Integration into Professional Treatment Protocols
```
- HE (`824:176`, p.10, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
‏שילוב בכל פרוטוקול טיפול ומכשור מקצועי בקליניקה
```
- New EN (paste):
```text
Combines with Any Treatment Protocol and Professional Clinic Equipment
```
- Style / notes: Medium 14 as now (may wrap; box 438 px).

#### E10.3 [B] HE "after professional | invasive treatments" (EN says "advanced aesthetic")

- Target: `667:378`
- Current EN (`667:378`, Rubik/Regular/12):
```text
The mask is particularly suitable as a soothing finishing step after professional and advanced aesthetic treatments.
```
- HE (`824:177`, p.10, Rubik/Regular/12):
```text
‏המסכה מתאימה במיוחד כשלב מסכם ומרגיע לאחר טיפולים מקצועיים | פולשניים
```
- New EN (paste):
```text
The mask is particularly suitable as a soothing finishing step after professional and invasive treatments.
```
- Style / notes: Regular 12.

#### E10.4 [B] Key benefits: HE "treatment of damage to the epidermal barrier" (EN "supports")

- Target: `667:371`
- Current EN (`667:371`, Rubik/Regular/12):
```text
Intensive and immediate hydration | Soothing after professional treatments | Supports the epidermal barrier | Cooling and refreshing effect | Helps reduce the feeling of dryness | Smoothing and firming effect | Leaves the skin looking fresh, calm, and deeply hydrated
```
- HE (`824:175`, p.10, Rubik/Regular/12):
```text
‏לחות אינטנסיבית ומיידית | הרגעה לאחר טיפוליים מקצועיים | טיפול בפגיעה במחסום האפידרמלי | קרירות ורעננות | הפחתה ביובש | אפקט החלקה ומתיחה | מראה עור רענן, רגוע ורווי בלחות
```
- New EN (paste):
```text
Intensive and immediate hydration | Soothing after professional treatments | Treats a compromised epidermal barrier | Cooling and refreshing effect | Helps reduce the feeling of dryness | Smoothing and firming effect | Leaves the skin looking fresh, calm, and deeply hydrated
```
- Style / notes: Only item 3 changes. Regular 12.

### EN p.11 — frame `667:348` "EN — 11 — Scalp Care — Synthetic Exosomes" ↔ HE p.11 `793:178`

#### E11.1 [C] Subtitle wording (HE "professional treatments – scalp"; HE Latin line "PROFESSIONAL SCALP TREATMENT"; parallels EN p.4)

- Target: `667:355`
- Current EN (`667:355`, Rubik/Regular/20):
```text
Professional treatments - scalp
```
- HE (`793:185`, p.11, Rubik/Regular/21):
```text
טיפולים מקצועיים - קרקפת
```
- HE (`793:188`, p.11, Rubik/Regular/12):
```text
PROFESSIONAL SCALP TREATMENT
```
- New EN (paste):
```text
Professional Scalp Treatment
```
- Style / notes: As now.

#### E11.2 [C] Two empty text nodes

- Target: `667:356, 667:357`
- Current EN (`667:356`, ):
```text

```
- Style / notes: Delete.

### EN p.12 — frame `667:331` "EN — 12 — EXOSIGNAL HAIR" ↔ HE p.12 `824:185`

#### E12.1 [B] Ingredient list: HE puts "2% PDRN" (emphasised) second, with annotation "from salmon stem cells, 20 mg/mL"

- Target: `667:341`
- Current EN (`667:341`, Rubik/Regular/12):
```text
Synthetic exosomal structures
High-molecular-weight hyaluronic acid
Biomimetic peptides:
SH-Oligopeptide-1/2
SH-Polypeptide-1/9/11
Acetyl Decapeptide-3
Copper Tripeptide-1 (GHK-Cu)
Oligopeptide-20
Plant stem cells from Swiss apple (Malus domestica)
Vitamins:
Panthenol – Provitamin B5
Biotin – Vitamin B7
Pyridoxine – Vitamin B6
Thiamine – Vitamin B1
PDRN 2% (20 mg/ml), derived from salmon
```
- HE (`824:195`, p.12, Rubik/Regular/12):
```text
מבנים אקסוזומליים סינתטיים.

חומצה היאלורונית במשקל מולקולרי גבוה
פפטידים ביומימטיים
SH-Oligopeptide-1/2, SH-Polypeptide-1/9/11, Acetyl Decapeptide-3
Copper (GHK-Cu) Tripeptide-1 ו-Oligopeptide-20
תאי גזע צמחיים מתפוח שווייצרי Malus Domestica 
ויטמינים: פנתנול – פרו־ויטמין B5, ביוטין – ויטמין B7, פירידוקסין – ויטמין B6, תיאמין – ויטמין B1
```
- HE (`824:197`, p.12, Rubik/Medium/12; HE emphasis: whole node (Medium)):
```text
2% PDRN
```
- HE (`824:196`, p.12, Rubik/Regular/12):
```text
מתא גזע של סלמון ריכוז של 20 מ״ג למ״ל
```
- New EN (paste):
```text
Synthetic exosomal structures
PDRN 2% – 20 mg/mL, from salmon stem cells
High-molecular-weight hyaluronic acid
Biomimetic peptides:
SH-Oligopeptide-1/2
SH-Polypeptide-1/9/11
Acetyl Decapeptide-3
Copper Tripeptide-1 (GHK-Cu)
Oligopeptide-20
Plant stem cells from Swiss apple (Malus domestica)
Vitamins:
Panthenol – Provitamin B5
Biotin – Vitamin B7
Pyridoxine – Vitamin B6
Thiamine – Vitamin B1
```
- Emphasised runs in the new text: "PDRN 2%" [30, 37]
- Style / notes: "PDRN 2%" emphasised (HE 824:197 Medium 12); rest Regular 12. Last line "PDRN 2% (20 mg/ml), derived from salmon" removed (moved up).

#### E12.2 [B] HE uses arrows (scalp → follicle → hair)

- Target: `667:346`
- Current EN (`667:346`, Rubik/Medium/12):
```text
Scalp | Follicle | Hair
```
- HE (`824:201`, p.12, Rubik/SemiBold/16; HE emphasis: whole node (SemiBold)):
```text
‏קרקפת ← זקיק ← שיער
```
- New EN (paste):
```text
Scalp → Follicle → Hair
```
- Style / notes: As now (Medium 12); same arrow style as p.17 caption.

#### E12.3 [C] Units

- Target: `667:343`
- Current EN (`667:343`, [0,17) Rubik/Medium/12 + [17,34) Rubik/Regular/12):
```text
Package Contents
5 ampoules × 5 ml
```
- HE (`824:198`, p.12, [0,13) Rubik/SemiBold/14 + [13,32) Rubik/Medium/12; HE emphasis: "תכולת האריזה" (SemiBold 14), " 5 אמפולות × ‎5 מ״ל" (Medium 12)):
```text
תכולת האריזה
 5 אמפולות × ‎5 מ״ל
```
- New EN (paste):
```text
Package Contents
5 ampoules × 5 mL
```
- Emphasised runs in the new text: "Package Contents" [0, 16]
- Style / notes: As now.

#### E12.4 [C] Empty text node

- Target: `667:342`
- Current EN (`667:342`, ):
```text

```
- Style / notes: Delete.

### EN p.13 — frame `667:314` "EN — 13 — EXOSIGNAL HAIR — Protocol" ↔ HE p.13 `793:210`

#### E13.1 [C] Missing " | " before "Before or after a hair transplant"; HE "thinning and loss of volume and density"

- Target: `667:320`
- Current EN (`667:320`, Rubik/Regular/12):
```text
Designed for men and women experiencing:
Increased or seasonal hair loss | Thinning hair and reduced hair density | Fine, weak, or lifeless hair | Dry, oily, or unbalanced scalp | Androgenetic alopecia | Alopecia areata Before or after a hair transplant
```
- HE (`793:216`, p.13, Rubik/Regular/12):
```text
מיועד לגברים ולנשים המתמודדים עם:
נשירה מוגברת או עונתית | דילול וירידה בנפח ובצפיפות | שיער דק, חלש או חסר חיוניות קרקפת יבשה, שומנית או לא מאוזנת | במצבים של התקרחות אנדרוגנטית | אלופציה אראטה | לפני או לאחר השתלת שיער
```
- New EN (paste):
```text
Designed for men and women experiencing:
Increased or seasonal hair loss | Thinning and loss of hair volume and density | Fine, weak, or lifeless hair | Dry, oily, or unbalanced scalp | Androgenetic alopecia | Alopecia areata | Before or after a hair transplant
```
- Style / notes: Regular 12.

### EN p.15 — frame `667:294` "EN — 15 — Spongilla — Science" ↔ HE p.15 `793:237`

#### E15.1 [IMG] Different photo: EN shows a sponge-with-spicules photo (hash fc3303f661); HE shows the loose spicules cut-out (hash ebe521959d, same layer name)

- Target: `667:302`
- HE node `793:245` (image / frame, see dump)
- Style / notes: Replace the image fill of 667:302 with HE 793:245 image (copy its IMAGE paint / clone the node). HE size 324×259; EN slot is 332×170 under the left column — re-fit (FIT, no crop of the needles) or give it the HE proportions if space allows.

#### E15.2 [B/Q] HE claims missing in EN: shortens the renewal cycle (HE "from 7 to 28 days"), activates the basal and dermal layers; "AGING" item; final "!"

- Target: `667:299`
- Current EN (`667:299`, [0,144) Rubik/Regular/12 + [144,160) Rubik/Medium/12 + [160,183) Rubik/Regular/12 + [183,193) Rubik/Medium/12 + [193,217) Rubik/Regular/12 + [217,224) Rubik/Medium/12 + [224,364) Rubik/Regular/12 + [364,375) Rubik/Medium/12 + [375,803) Rubik/Regular/12 + [803,883) Rubik/Medium/12):
```text
Millions of micro-needles penetrate the skin to a depth of 80–300 microns, reaching the epidermal layers. This mechanical stimulation activates microcirculation, accelerates cellular metabolism, and supports the skin renewal cycle.
Under the microscope, tiny spicules can be seen within the skin. They may remain for up to 72 hours, providing continued mechanical stimulation and supporting collagen production, epidermal repair, cellular metabolism, and skin renewal.

Indications
Anti-ageing | Wrinkles and fine lines | Enlarged pores | Firming | Brightening | Uneven skin tone | Post-inflammatory hyperpigmentation (PIH) | Senile lentigo | Scars | Post-acne scars | Mild to moderate acne | Thin, devitalised skin | Dull, sallow skin | Renewal and nourishment | Face | Neck | Décolleté | Hands | Back
Micro-needle treatment can serve as an alternative to traditional microneedling.
```
- HE (`793:242`, p.15, [0,101) Rubik/Regular/12 + [101,115) Rubik/SemiBold/12 + [115,134) Rubik/Regular/12 + [134,139) Rubik/SemiBold/12 + [139,163) Rubik/Regular/12 + [163,168) Rubik/SemiBold/12 + [168,352) Rubik/Regular/12 + [352,357) Rubik/SemiBold/12 + [357,668) Rubik/Regular/12 + [668,734) Rubik/Bold/12; HE emphasis: "מיקרוסירקולציה" (SemiBold 12), "חילוף" (SemiBold 12), "חידוש" (SemiBold 12), "המרצה" (SemiBold 12), "טיפול במיקרו מחטים יכול להוות כתחליף לטיפול המסורתי במיקרונידלינג!" (Bold 12)):
```text
מיליוני מחטים בעומק של 80-300 מיקרון חודרות במהירות אל העור ומגיעות לעומק האפידרמלי  חדירה זו מפעילה מיקרוסירקולציה של העור בכך מאיצה חילוף חומרים ומקצרת את מחזור חידוש העור מ 7 ל 28 ימים. מתחת למיקרוסקופ ניתן לראות מחטים זעירות וכשהן חודרות הם מפעילות את השכבה הבזאלית והדרמלית, יכולות להשאר עד 72 שעות וגורמות להגברת יצור קולגן ושיקום האפידרמיס מתוך המרצה של המטבוליזם התאי וחידוש העור.

אינדיקציות: אנטי-אייג׳ינג | קמטים וקמטוטים | נקבוביות פעורות | מיצוק | הבהרה | שיפור גוון העור פיגמנטציה פוסט דלקתית PIH | סניל לנטיגו | צלקות | צלקות פוסט אקנה | אקנה קל- בינוני | עור דק וחסר חיוניות | עור אפרורי וחסר ברק | חידוש והזנה | AGING | פנים, צוואר, דקולטה, ידיים, גב
טיפול במיקרו מחטים יכול להוות כתחליף לטיפול המסורתי במיקרונידלינג!
```
- New EN (paste):
```text
Millions of micro-needles penetrate the skin to a depth of 80–300 microns, reaching the epidermal layers. This penetration activates the skin's microcirculation, thereby accelerating metabolism and shortening the skin renewal cycle from 28 to 7 days.
Under the microscope, tiny needles can be seen; as they penetrate, they activate the basal and dermal layers. They can remain for up to 72 hours, boosting collagen production and epidermal repair by stimulating cellular metabolism and skin renewal.

Indications
Anti-ageing | Wrinkles and fine lines | Enlarged pores | Firming | Brightening | Improved skin tone | Post-inflammatory hyperpigmentation (PIH) | Senile lentigo | Scars | Post-acne scars | Mild to moderate acne | Thin, devitalized skin | Dull, sallow skin | Renewal and nourishment | AGING | Face | Neck | Décolleté | Hands | Back
Micro-needle treatment can serve as an alternative to traditional microneedling!
```
- Emphasised runs in the new text: "microcirculation" [144, 160], "metabolism" [183, 193], "renewal" [218, 225], "stimulating" [450, 461], "Indications" [501, 512], "Micro-needle treatment can serve as an alternative to traditional microneedling!" [844, 924]
- Style / notes: Emphasis as HE: microcirculation, metabolism, renewal, stimulating (HE SemiBold מיקרוסירקולציה / חילוף / חידוש / המרצה) and the last sentence (HE Bold); "Indications" stays an emphasised sub-head as in the current EN. "from 28 to 7 days": HE literally says "מ 7 ל 28 ימים" (from 7 to 28) — reversed on purpose, confirm with owner (Q).

### EN p.16 — frame `667:280` "EN — 16 — BIOSPICULE — Fourth generation" ↔ HE p.16 `795:2`

#### E16.1 [B] HE: "Unlike competitors, we control every needle, each length separately ... a delivery system that goes into the dermis"

- Target: `667:291`
- Current EN (`667:291`, Rubik/Regular/12):
```text
Rather than focusing only on the quantity of Spongilla, our technology also considers the architecture of the spicules — their length, the balance between short and long structures, and how this combination influences the distribution of mechanical stimulation across different layers of the epidermis.
This is where a natural raw material becomes a precise cosmetic technology.
Under the microscope, each spicule has a porous structure with an elongated microscopic inner cavity, almost like a miniature cannelloni. This unique architecture makes the spicule more than a mechanical element: it becomes part of a controlled delivery system.
By controlling different spicule lengths within the formula, BIOSPICULE™ combines mechanical stimulation with targeted cosmetic delivery. This structure forms the basis of the Hybrid Spicule Delivery System.
```
- HE (`795:15`, p.16, Rubik/Regular/12):
```text
במקום לעבוד רק עם כמות גדולה של ספונגילות, הטכנולוגיה שלנו מתייחסת גם לארכיטקטורה שלהן: ולאורך הספיקולות:  קצרות וארוכות, וכיצד השילוב ביניהן משפיע על פיזור הגירוי בשכבות השונות של האפידרמיס.
זוהי הנקודה שבה חומר גלם טבעי הופך לטכנולוגיה קוסמטית מדויקת.
תחת המיקרוסקופ, הספיקולה היא בעלת מבנה נקבובי, המזכיר צינור זעיר: חלל מיקרוסקופי מאורך - כמעט כמו קנלוני מיניאטורי. לעומת המתחרים אנחנו שולטים בכל מחט כזאת! בכל אורך שלה בנפרד. זה לא רק אבקה של החומר ללא סינון אלא מערכת הובלה שנכנסת פנימה לתוך הדרמיס תוך שליטה בכל סוגי האורכים בפורמולה. המבנה הזה הוא הבסיס ל-Hybrid Spicule Delivery System 

```
- New EN (paste):
```text
Rather than focusing only on the quantity of Spongilla, our technology also considers the architecture of the spicules — their length, the balance between short and long structures, and how this combination influences the distribution of mechanical stimulation across different layers of the epidermis.
This is where a natural raw material becomes a precise cosmetic technology.
Under the microscope, each spicule has a porous structure with an elongated microscopic inner cavity, almost like a miniature cannelloni. Unlike competitors, we control every one of these needles – each length separately. This is not just an unfiltered powder of the raw material, but a delivery system that travels into the dermis while controlling every length in the formula. This structure is the basis of the Hybrid Spicule Delivery System.
```
- Style / notes: Regular 12 (paragraphs 1–2 unchanged).

#### E16.2 [B] Last sentence: HE "so we have the structure of every spicule separately – every bio-needle separately!"

- Target: `667:283`
- Current EN (`667:283`, [0,211) Rubik/Regular/12 + [211,272) Rubik/Medium/12 + [272,309) Rubik/Regular/12 + [309,323) Rubik/Medium/12 + [323,368) Rubik/Regular/12 + [368,379) Rubik/Medium/12 + [379,673) Rubik/Regular/12 + [673,698) Rubik/Medium/12):
```text
Spongilla-based technologies depend on several key factors:
The purification level of the spicules.
The size of the spicules and the ratio between different lengths.
Their precise concentration in each product.
Traditional Spongilla powder is a single, non-uniform mixture containing the entire raw material.
Our approach:
Fourth-generation BIOSPICULE™ technology uses four types of Spongilla. Through an advanced Korean processing method, unwanted residues are removed, while the microscopic structures are purified and sorted according to their characteristics and size.
This allows us to control the structure and characteristics of the spicules with greater precision. Every bio-needle matters.
```
- HE (`795:6`, p.16, [0,131) Rubik/Regular/12 + [131,170) Rubik/SemiBold/12 + [170,195) Rubik/Regular/12 + [195,202) Rubik/Bold/12 + [202,247) Rubik/Regular/12 + [247,255) Rubik/Bold/12 + [255,423) Rubik/Regular/12 + [423,440) Rubik/Bold/12; HE emphasis: "האבקה המסורתית הינה תערובת אחת לא אחידה" (SemiBold 12), "אצלנו:" (Bold 12), " 4 סוגים" (Bold 12), "כל ביו-מחט בנפרד!" (Bold 12)):
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
- New EN (paste):
```text
Spongilla-based technologies depend on several key factors:
The purification level of the spicules.
The size of the spicules and the ratio between different lengths.
Their precise concentration in each product.
Traditional Spongilla powder is a single, non-uniform mixture containing the entire raw material.
Our approach:
Fourth-generation BIOSPICULE™ technology uses four types of Spongilla. Through an advanced Korean processing method, unwanted residues are removed, while the microscopic structures are purified and sorted according to their characteristics and size.
This gives us the structure of every spicule individually. Every bio-needle, individually!
```
- Emphasised runs in the new text: "Traditional Spongilla powder is a single, non-uniform mixture" [211, 272], "Our approach:" [309, 322], "four types" [369, 379], "Every bio-needle, individually!" [632, 663]
- Style / notes: Emphasis runs as now; only the last two sentences change.

### EN p.17 — frame `668:6` "EN — 17 — BIOSPICULE — Mechanisms" ↔ HE p.17 `795:18`

#### E17.1 [A] Running head "MITODERM" and footer are missing on EN p.17

- Target: `new nodes in 668:6 (clone 667:281, 667:293 from p.16)`
- HE (`795:34`, p.17, Rubik/Bold/11; HE emphasis: whole node (Bold)):
```text
MITODERM
```
- HE (`795:35`, p.17, Rubik/Regular/8):
```text
MITODERM  |  WHERE SCIENCE MEETS BEAUTY
```
- New EN (one block per new / changed node, in the order listed in Target):
```text
MITODERM
```
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style / notes: Clone the p.16 running head (Bold 11) and footer (Regular, same size as the rest of EN) to the mirrored HE positions.

#### E17.2 [A] HE repeats the p.16 title on p.17 and has the sub-heading "This is how they work along two parallel pathways:"; EN uses the sub-heading as page title

- Target: `new title (clone 667:282) + 667:288`
- HE (`795:20`, p.17, Rubik/ExtraBold/30; HE emphasis: whole node (ExtraBold)):
```text
BIOSPICULE — הדור הרביעי של טכנולוגיית הספיקולות
```
- HE (`795:28`, p.17, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
כך הן פועלות בשני מסלולים מקבילים:
```
- New EN (one block per new / changed node, in the order listed in Target):
```text
BIOSPICULE™ – The Fourth Generation of Spicule Technology
```
```text
This is how they work, along two parallel pathways:
```
- Style / notes: Line 1 = new title node (Bold 30, 2 lines as on p.16). Line 2 = new text of 667:288, restyled from Bold 28 to the sub-head style (Medium 14). Body moves down ~70 px — fit risk, see open questions.

#### E17.3 [B] Order as HE: intro paragraph first, then the "Resurfacing" and "Delivery" sub-heads; HE says "epidermal cells", "outer layer", "precise cosmetic gateway", "remain ... up to 72 hours"

- Target: `667:284 (+ delete 667:285)`
- Current EN (`667:284`, [0,273) Rubik/Regular/12 + [273,274) Rubik/Medium/12 + [274,402) Rubik/Regular/12 + [402,438) Rubik/Medium/12 + [438,867) Rubik/Regular/12):
```text
During massage, the spicules penetrate the stratum corneum, creating controlled mechanical stimulation. This supports the gradual removal of dead skin cells, improves skin texture and appearance, and prepares the skin for active ingredients applied later in the treatment.

The mechanical action of the spicules helps improve the appearance of roughness, enlarged pores, dullness, and uneven texture.

Delivery – Cosmetic Delivery System
The spicules create temporary microscopic pathways in the outer layers of the skin, supporting more effective delivery of active ingredients applied during the treatment.

The aim is not only to create a peeling effect, but to transform the renewal stage into a precise cosmetic delivery pathway — BIOMICRONEEDLING.

Biological micro-spicules may remain in the skin for up to 72 hours, providing continued mechanical stimulation.
```
- HE (`795:23`, p.17, [0,230) Rubik/Regular/12 + [230,232) Rubik/Bold/12 + [232,338) Rubik/Regular/12 + [338,369) Rubik/Bold/12 + [369,651) Rubik/Regular/12; HE emphasis: "Delivery - מערכת הולכה קוסמטית" (Bold 12)):
```text
בזמן העיסוי, הספיקולות משתלבות וחודרות במיידי בשכבה הקרנית ויוצרות גירוי מכני קוסמטי מבוקר. פעולה זו תומכת בהסרה הדרגתית של תאים אפידרמלים, משפרת את מראה העור, מרקם העור ומכינה את העור לקבלת הרכיבים הפעילים המשולבים בהמשך הטיפול.


פעולה מכנית המכניסה פנימה את הספיקולות ומסייעת לשיפור מראה החספוס, הנקבוביות, העמימות והמרקם הבלתי אחיד.

Delivery - מערכת הולכה קוסמטית
יצירת מסלולים מיקרוסקופיים זמניים בשכבה החיצונית של העור, התומכים במעבר יעיל יותר של הפורמולה והרכיבים הפעילים הנמרחים במהלך הטיפול.

המטרה אינה רק ליצור אפקט של פילינג. המטרה היא להפוך את שלב החידוש לשער קוסמטי מדויק – BIOMICRONEEDLING

מיקרו-מחטים ביולוגיות נשארות בעור עד 72 שעות
```
- HE (`795:24`, p.17, Rubik/Bold/12; HE emphasis: whole node (Bold)):
```text
חידוש פני העור -
```
- HE (`795:25`, p.17, Rubik/Bold/12; HE emphasis: whole node (Bold)):
```text
Resurfacing
```
- New EN (paste):
```text
During massage, the spicules immediately integrate into and penetrate the stratum corneum, creating controlled cosmetic mechanical stimulation. This supports the gradual removal of epidermal cells, improves skin appearance and texture, and prepares the skin for the active ingredients applied later in the treatment.

Resurfacing – Skin Surface Renewal
A mechanical action that drives the spicules in and helps improve the appearance of roughness, enlarged pores, dullness, and uneven texture.

Delivery – Cosmetic Delivery System
The spicules create temporary microscopic pathways in the outer layer of the skin, supporting more effective passage of the formula and the active ingredients applied during the treatment.

The aim is not only to create a peeling effect, but to turn the renewal stage into a precise cosmetic gateway — BIOMICRONEEDLING.

Biological micro-needles remain in the skin for up to 72 hours.
```
- Emphasised runs in the new text: "Resurfacing – Skin Surface Renewal" [318, 352], "Delivery – Cosmetic Delivery System" [495, 530]
- Style / notes: Two sub-heads emphasised (HE Bold 795:24/795:25 and the Bold run "Delivery - מערכת הולכה קוסמטית"); delete 667:285 "Skin Renewal – Resurfacing" (now inside the body). Caption 667:290 unchanged.

### EN p.18 — frame `667:262` "EN — 18 — MICRO BOOST 10%" ↔ HE p.18 `795:38`

#### E18.1 [C] Units: "3 ml syringe" -> "3 mL syringe"

- Target: `667:269`
- Current EN (`667:269`, [0,9) Rubik/Regular/12 + [9,21) Rubik/Medium/12 + [21,22) Rubik/Regular/12 + [22,34) Rubik/Medium/12 + [34,861) Rubik/Regular/12 + [861,868) Rubik/Medium/12 + [868,878) Rubik/Regular/12 + [878,886) Rubik/Medium/12 + [886,909) Rubik/Regular/12):
```text
The most concentrated professional serum in the BIOSPICULE™ range. Designed exclusively for in-clinic use, it comes in a 3 ml syringe, allowing the aesthetician to control the amount of product, massage duration, and treatment intensity according to the skin diagnosis.
The formula contains 10% Hydrolyzed Sponge and combines two groups of spicules:
40% Mini Spicules, approximately 80–100 microns in length.
60% Long Spicules, approximately 300–360 microns in length.
The combination of short and long spicules creates different levels of mechanical stimulation. Short spicules act mainly in the outer layers of the epidermis, while longer spicules provide a more intense stimulus and reach deeper layers of the skin.
The aesthetician therefore works not merely with a peel, but with a BIOMICRONEEDLING delivery system — a professional approach combining skin renewal with the delivery of active ingredients.
```
- HE (`795:45`, p.18, [0,5) Rubik/Regular/12 + [5,11) Rubik/Bold/12 + [11,12) Rubik/Regular/12 + [12,19) Rubik/Bold/12 + [19,684) Rubik/Regular/12 + [684,689) Rubik/Bold/12 + [689,698) Rubik/Regular/12 + [698,704) Rubik/Bold/12 + [704,727) Rubik/Regular/12; HE emphasis: "מקצועי" (Bold 12), "והמרוכז" (Bold 12), "חידוש" (Bold 12), "והובלה" (Bold 12)):
```text
סרום מקצועי והמרוכז ביותר בסדרת BIOSPICULE. הוא מיועד לשימוש בקליניקה בלבד ומגיע במזרק של 3 מ״ל, המאפשר לקוסמטיקאית לשלוט בכמות החומר, במשך העיסוי ובעוצמת הטיפול בהתאם לאבחון העור.
הפורמולה מכילה 10% Hydrolyzed Sponge ומשלבת שתי קבוצות של ספיקולות:
                                  , באורך של כ־‎80–100 מיקרון.
                                    , באורך של כ־‎300–360 מיקרון.
השילוב בין הספיקולות הקצרות והארוכות יוצר פיזור רב־שכבתי של הגירוי הקוסמטי. הספיקולות הקצרות פועלות בעיקר באזור החיצוני יותר של האפידרמיס, ואילו הארוכות יוצרות גירוי מורגש ואינטנסיבי יותר ומגיעות עמוק יותר בשכבות העור.
כך הקוסמטיקאית אינה עובדת רק עם פילינג אלא עם מערכת הובלה של BIOMICRONEEDLING  
 מערכת חידוש מקצועית והובלה מדעית של חומרים פנימה.
```
- Style / notes: Replace the two characters "ml" in "a 3 ml syringe" by "mL" (no other change).

### EN p.19 — frame `668:8` "EN — 19 — MICRO BOOST 10% — Application" ↔ HE p.19 `795:59`

#### E19.1 [A] Combinations: V-TECH | Longevity Serum | MITOTECH CELL BOOSTER; new "Treatment finish" list; "Derma Recovery Cream – also for continued home care" (owner edit B6)

- Target: `667:272`
- Current EN (`667:272`, [0,167) Rubik/Regular/12 + [167,186) Rubik/Medium/12 + [186,327) Rubik/Regular/12):
```text
The structure of the spicules and the massage technique create temporary microscopic channels, allowing the treatment to be combined with: 
 V-TECH or Longevity Serum
Treatment Finish: 
EXOCELL MASK
 DERMA RECOVERY CREAM — also mandatory for home use to support the epidermal barrier and reduce dryness and tightness 
Sunscreen
```
- HE (`795:71`, p.19, [0,130) Rubik/Regular/12 + [130,142) Rubik/SemiBold/12 + [142,185) Rubik/Regular/12; HE emphasis: "סיום טיפול:" (SemiBold 12)):
```text
מבנה הספיקולות ותהליך העיסוי יוצרים תעלות מיקרוסקופיות זמניות ולכן ניתן לשלב עם:
V-TECH | Longevity Serum | MITOTECH CELL BOOSTER
סיום טיפול:
EXOCELL Mask
Derma Recovery Cream
מקדם הגנה
```
- HE (`936:8`, p.19, Rubik/Regular/12):
```text
– גם להמשך טיפול ביתי
```
- New EN (paste):
```text
The structure of the spicules and the massage technique create temporary microscopic channels, allowing the treatment to be combined with:
V-TECH | Longevity Serum | MITOTECH CELL BOOSTER
Treatment finish:
EXOCELL Mask
Derma Recovery Cream – also for continued home care
Sunscreen
```
- Emphasised runs in the new text: "Treatment finish:" [188, 205]
- Style / notes: "Treatment finish:" emphasised (HE SemiBold "סיום טיפול:"); rest Regular 12. Product spellings exactly as HE on this page ("EXOCELL Mask", "Derma Recovery Cream"). HE puts "– also for continued home care" in a separate node (936:8) only because of RTL; in EN keep it on the same line.

#### E19.2 [A] Running head, page title block and footer are missing on EN p.19 (HE repeats them)

- Target: `new nodes in 668:8 (clone from p.18: 667:263, 667:265, 667:266, 667:267, 667:264)`
- HE (`795:81`, p.19, Rubik/Bold/11; HE emphasis: whole node (Bold)):
```text
MITODERM
```
- HE (`795:62`, p.19, Rubik/SemiBold/10; HE emphasis: whole node (SemiBold)):
```text
BIOSPICULE
```
- HE (`795:63`, p.19, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
טיפול מקצועי לקליניקה
```
- HE (`795:64`, p.19, Rubik/ExtraBold/30; HE emphasis: whole node (ExtraBold)):
```text
MICRO BOOST 10%
```
- HE (`795:82`, p.19, Rubik/Regular/8):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- New EN (one block per new / changed node, in the order listed in Target):
```text
MITODERM
```
```text
BIOSPICULE™
```
```text
Professional In-Clinic Treatment
```
```text
MICRO BOOST 10%
```
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style / notes: Same styles as p.18. The body (667:270–272, now y 68–469) must move down ~90 px — it will not fit as is (ends ~560 > footer 513): see open questions.

### EN p.24 (old EN p.20) — frame `667:242` "EN — 20 — Complementary Home Care" ↔ HE p.24 `793:247`

#### E24.1 [B] Title: HE "complementary products for home use" (= ToC section 6)

- Target: `667:247`
- Current EN (`667:247`, Rubik/Bold/41):
```text
Complementary home care
```
- HE (`793:252`, p.24, Rubik/ExtraBold/40; HE emphasis: whole node (ExtraBold)):
```text
תכשירים משלימים לשימוש ביתי
```
- New EN (paste):
```text
Complementary Products for Home Use
```
- Style / notes: Bold 41 as now (may need 2 lines or 30 pt; HE uses 40).

#### E24.2 [C] Series name

- Target: `667:249`
- Current EN (`667:249`, Rubik/Medium/14):
```text
Line: synthetic exosomes
```
- HE (`793:254`, p.24, Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
סדרת אקסוזומים סינתטיים
```
- New EN (paste):
```text
Synthetic Exosome Series
```
- Style / notes: Medium 14 as now.

#### E24.3 [C] Series name with ™ in one node (owner edit B1)

- Target: `667:250 (+ delete 667:260)`
- Current EN (`667:250`, Rubik/Medium/14):
```text
Line: BIOSPICULE
```
- HE (`793:255`, p.24, [0,15) Rubik/SemiBold/14 + [15,16) Rubik/SemiBold/8 + [16,17) Rubik/SemiBold/14; HE emphasis: "סדרת BIOSPICULE" (SemiBold 14), "™" (SemiBold 8), "‎" (SemiBold 14)):
```text
סדרת BIOSPICULE™‎
```
- New EN (paste):
```text
BIOSPICULE™ Series
```
- Style / notes: "™" run at 8 pt inside the node (as HE 793:255: ™ 8 pt in 14 pt); delete the loose "™" node 667:260; widen the box (now 140 px).

### EN p.25 (old EN p.21) — frame `667:229` "EN — 21 — Synthetic Exosome Series" ↔ HE p.25 `793:267`

#### E25.1 [C] Series name

- Target: `667:236`
- Current EN (`667:236`, Rubik/Bold/41):
```text
Synthetic Exosome Line
```
- HE (`793:274`, p.25, Rubik/ExtraBold/41; HE emphasis: whole node (ExtraBold)):
```text
סדרת אקסוזומים סינתטיים:
```
- New EN (paste):
```text
Synthetic Exosome Series
```
- Style / notes: As now.

### EN p.26 (old EN p.22) — frame `667:213` "EN — 22 — EXOTECH GEL" ↔ HE p.26 `824:203`

#### E26.1 [C] Units

- Target: `667:222`
- Current EN (`667:222`, Rubik/Regular/12):
```text
• Synthetic exosomes
• PDRN polynucleotides
• Biomimetic peptides, gold, and copper
• Hyaluronic acid
• Purified polysaccharides of snail origin
Volume: 30 ml
```
- HE (`824:214`, p.26, Rubik/Regular/12):
```text
‏• אקסוזומים סינתטיים
‏• פולינוקלאוטידים PDRN
‏• פפטידים ביומימטיים, זהב ונחושת
‏• חומצה היאלורונית
‏• פוליסכרידים מטוהרים ממקור חלזון
‏כמות: 30 מ״ל
```
- New EN (paste):
```text
• Synthetic exosomes
• PDRN polynucleotides
• Biomimetic peptides, gold, and copper
• Hyaluronic acid
• Purified polysaccharides of snail origin
Volume: 30 mL
```
- Style / notes: As now.

#### E26.2 [C] Series name

- Target: `667:226`
- Current EN (`667:226`, Rubik/Regular/12):
```text
Designed to complement the daily skincare routine, particularly after professional treatments in the clinic. It can be integrated into a treatment programme that includes V-TECH, EXO-NAD, and the BIOSPICULE™ line
```
- HE (`824:218`, p.26, Rubik/Regular/12):
```text
‏להמשך כל שגרת הטיפוח ובמיוחד לאחר טיפול מקצועי בקליניקה – ניתן לשלב אותו כחלק מתוכנית טיפול הכוללת V-TECH, ‏EXO-NAD, סדרת‏ BIOSPICULE
```
- New EN (paste):
```text
Designed to complement the daily skincare routine, particularly after professional treatments in the clinic. It can be integrated into a treatment programme that includes V-TECH, EXO-NAD, and the BIOSPICULE™ series
```
- Style / notes: "line" -> "series" only.

### EN p.27 (old EN p.23) — frame `667:199` "EN — 23 — EXOSIGNAL SPRAY" ↔ HE p.27 `793:298`

#### E27.1 [B] HE intro sentence "EXOSIGNAL SPRAY is an advanced home scalp product developed to complement the protocol" is missing

- Target: `667:207`
- Current EN (`667:207`, Rubik/Regular/12):
```text
EXOSIGNAL SPRAY combines active ingredients designed to maintain a balanced scalp environment, nourish the hair, and support optimal conditions for the natural hair growth cycle.
```
- HE (`793:307`, p.27, Rubik/Regular/12):
```text
‏EXOSIGNAL SPRAY הוא תכשיר ביתי מתקדם לקרקפת, שפותח להשלמת פרוטוקול
```
- HE (`793:308`, p.27, Rubik/Regular/12):
```text
‏הספריי משלב רכיבים פעילים שנועדו לתמוך בסביבה תקינה ומאוזנת של הקרקפת, לטפח את השיער ולסייע בשמירה על התנאים הדרושים למחזור צמיחה תקין. מתאים לשימוש יום־יומי, נספג במהירות.
```
- New EN (paste):
```text
EXOSIGNAL SPRAY is an advanced home-care scalp product developed to complement the professional protocol. It combines active ingredients designed to maintain a balanced scalp environment, nourish the hair, and support optimal conditions for the natural hair growth cycle.
```
- Style / notes: Regular 12; box grows one line — move 667:208–210 down ~15 px.

#### E27.2 [C] Pack-shot caption copied from the label: HE "Deep nourishing scalp spray"

- Target: `667:206`
- Current EN (`667:206`, Rubik/Regular/12):
```text
Deeply nourishing scalp spray
HOME USE · 15 ml
```
- HE (`793:306`, p.27, Rubik/Regular/12):
```text
Deep nourishing scalp spray
HOME USE · 15 ml
```
- New EN (paste):
```text
Deep nourishing scalp spray
HOME USE · 15 ml
```
- Style / notes: Label copy kept exactly as HE (including "15 ml").

### EN p.28 (old EN p.24) — frame `667:182` "EN — 24 — BIOSPICULE Series" ↔ HE p.28 `793:314`

#### E28.1 [C] Title with ™ in one node (owner edit B1)

- Target: `667:187 (+ delete 667:188)`
- Current EN (`667:187`, Rubik/Bold/41):
```text
BIOSPICULE series
```
- HE (`793:319`, p.28, [0,15) Rubik/ExtraBold/41 + [15,16) Rubik/ExtraBold/21 + [16,17) Rubik/ExtraBold/41; HE emphasis: "סדרת BIOSPICULE" (ExtraBold 41), "™" (ExtraBold 21), "‎" (ExtraBold 41)):
```text
סדרת BIOSPICULE™‎
```
- New EN (paste):
```text
BIOSPICULE™ Series
```
- Style / notes: "™" run at 21 pt inside the 41 pt title (as HE 793:319); delete loose "™" node 667:188; widen the box (now 388 px).

### EN p.29 (old EN p.25) — frame `667:163` "EN — 25 — CELL RENEW 1.5%" ↔ HE p.29 `793:331`

#### E29.1 [B] Indications: HE "young ages" (EN "younger-looking skin"); "fresh, radiant look, hydration"

- Target: `667:174`
- Current EN (`667:174`, Rubik/Regular/12):
```text
Suitable for all skin types | Fresh, radiant-looking skin | Dull and tired-looking skin | Improved skin texture | Enlarged pores | Younger-looking skin | Improvement of uneven skin tone | Hyperpigmentation | Post-inflammatory marks | Skin renewal and brightening | Anti-ageing | Improvement in the appearance of wrinkles and fine lines | Firming
```
- HE (`793:344`, p.29, Rubik/Regular/12):
```text
‏מתאים לכל סוגי העור | מקנה מראה רענן, זוהר, לחות | עור עמום ועייף | שיפור מרקם העור | נקבוביות פעורות | גילאים צעירים | שיפור גוון בלתי אחיד | היפרפיגמנטציה | כתמים פוסט דלקתיים | חידוש והבהרה | אנטי-אייג׳ינג | שיפור בקמטים וקמטוטים | מיצוק.
```
- New EN (paste):
```text
Suitable for all skin types | Fresh, radiant, hydrated look | Dull, tired skin | Improved skin texture | Enlarged pores | Younger age groups | Improvement of uneven skin tone | Hyperpigmentation | Post-inflammatory marks | Renewal and brightening | Anti-ageing | Improvement of wrinkles and fine lines | Firming
```
- Style / notes: Regular 12.

#### E29.2 [C] Subtitle consistency (p.30 and ToC say "home-care serum")

- Target: `667:166`
- Current EN (`667:166`, Rubik/Regular/13):
```text
At-Home Serum for Skin Renewal and Brightening
```
- HE (`793:334`, p.29, Rubik/Regular/12):
```text
‏סרום ביתי לחידוש והבהרה
```
- New EN (paste):
```text
Home-Care Serum for Skin Renewal and Brightening
```
- Style / notes: As now.

### EN p.30 (old EN p.26) — frame `667:138` "EN — 26 — CELL RENEW 1.5% — Active ingredients" ↔ HE p.30 `796:2`

#### E30.1 [Q] HE says the spicules support "gradual removal of basal cells" (תאים באזליים); EN says "dead skin cells"

- Target: `667:148`
- Current EN (`667:148`, Rubik/Regular/12):
```text
Microscopic needle-like structures that provide controlled cosmetic mechanical stimulation to the skin. They support the gradual removal of dead skin cells and prepare the outer layers of the skin to receive the formula.
```
- HE (`796:12`, p.30, Rubik/Regular/12):
```text
‏מבנים מיקרוסקופיים דמויי מחט, המעניקים לעור גירוי מכני קוסמטי מבוקר. הם תומכים בהסרה הדרגתית של תאים באזליים ובהכנת שכבת העור החיצונית לקבלת הפורמולה.
```
- Style / notes: Recommendation: keep EN "dead skin cells" (the meaning HE intends elsewhere) unless the owner wants "basal cells" literally.

### EN p.31 (old EN p.27) — frame `668:10` "EN — 27 — CELL RENEW 1.5% — Ingredients and use" ↔ HE p.31 `796:27`

#### E31.1 [A] Page title block, running head, footer and pack-shot caption are missing on EN p.27 (HE p.31 has them)

- Target: `new nodes in 668:10 (clone from p.26 667:141–143 and p.25 667:175–177)`
- HE (`796:30`, p.31, Rubik/ExtraBold/30; HE emphasis: whole node (ExtraBold)):
```text
CELL RENEW 1.5%
```
- HE (`796:31`, p.31, Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
BIOSPICULE SERUM
```
- HE (`796:32`, p.31, Rubik/Regular/12):
```text
‏סרום ביתי לחידוש והבהרה
```
- HE (`796:57`, p.31, Rubik/Bold/11; HE emphasis: whole node (Bold)):
```text
MITODERM
```
- HE (`796:58`, p.31, Rubik/Regular/8):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- HE (`796:59`, p.31, Rubik/Regular/12):
```text
Advanced Biospicule Technology
30 ml ℮ 1.0 fl.oz.
```
- New EN (one block per new / changed node, in the order listed in Target):
```text
CELL RENEW 1.5%
```
```text
BIOSPICULE™ SERUM
```
```text
Home-Care Serum for Skin Renewal and Brightening
```
```text
MITODERM
```
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
```text
Advanced Biospicule Technology
30 ml ℮ 1.0 fl.oz.
```
- Style / notes: Title block in the text column (as p.26), MITODERM + footer inside the green panel (as p.25), caption under the pack shot 674:3 (as 667:177). Body 667:156–161 moves down ~80 px (ends ~440, fits).

### EN p.34 (old EN p.30) — frame `668:12` "EN — 30 — CELLULAR AGE DEFENSE 2.5% — Ingredients and use" ↔ HE p.34 `796:90`

#### E34.1 [A] Page title block, running head, footer and pack-shot caption are missing on EN p.30 (HE p.34 has them)

- Target: `new nodes in 668:12 (clone from p.28 667:121–123, 667:131–133)`
- HE (`796:117`, p.34, Rubik/ExtraBold/30; HE emphasis: whole node (ExtraBold)):
```text
CELLULAR AGE DEFENSE 2.5%
```
- HE (`796:118`, p.34, Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
BIOSPICULE SERUM
```
- HE (`796:119`, p.34, Rubik/Regular/12):
```text
‏סרום מתקדם למיצוק ואנטי-אייג׳ינג
```
- HE (`796:126`, p.34, Rubik/Bold/11; HE emphasis: whole node (Bold)):
```text
MITODERM
```
- HE (`796:127`, p.34, Rubik/Regular/8):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- HE (`796:128`, p.34, Rubik/Regular/8):
```text
Advanced Biospicule Technology
30 ml ℮ 1.0 fl.oz.
```
- New EN (one block per new / changed node, in the order listed in Target):
```text
CELLULAR AGE DEFENSE 2.5%
```
```text
BIOSPICULE™ SERUM
```
```text
Advanced Serum for Firming and Anti-Ageing
```
```text
MITODERM
```
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
```text
Advanced Biospicule Technology
30 ml ℮ 1.0 fl.oz.
```
- Style / notes: As p.28 (title Bold 26, 1 line). Body 667:114–119 moves down ~70 px (ends ~460, fits).

### EN p.35 (old EN p.31) — frame `667:74` "EN — 31 — DERMA RECOVERY" ↔ HE p.35 `793:352`

#### E35.1 [C] Product name spelling as HE ("MICRO BOOST 10%")

- Target: `667:85`
- Current EN (`667:85`, Rubik/Regular/12):
```text
Completion of the professional V-TECH SYSTEM protocol | After an invasive in-clinic procedure | Completion of a professional in-clinic treatment with Micro BOOST 10% | After a home-care routine from the BIOSPICULE™ range, including CELL RENEW 1.5% and CELLULAR AGE DEFENSE 2.5%
```
- HE (`793:363`, p.35, Rubik/Regular/12):
```text
סיום פרוטוקול מקצועי V-TECH SYSTEM | לאחר פרוצדורה פולשנית בקליניקה  
סיום פרוטוקול טיפול מקצועי בקליניקה עם MICRO BOOST 10% 
לאחר שגרת טיפוח ביתית: מסדרת ה-BIOSPICULE 
Cell Renew 1.5% -ו Cellular Age Defense 2.5%  
```
- New EN (paste):
```text
Completion of the professional V-TECH SYSTEM protocol | After an invasive in-clinic procedure | Completion of a professional in-clinic treatment with MICRO BOOST 10% | After a home-care routine from the BIOSPICULE™ range, including CELL RENEW 1.5% and CELLULAR AGE DEFENSE 2.5%
```
- Style / notes: "Micro BOOST" -> "MICRO BOOST" only (optionally "range" -> "series", see G6).

### EN p.36 (old EN p.32) — frame `667:56` "EN — 32 — DERMA RECOVERY — Ingredients and use" ↔ HE p.36 `793:371`

#### E36.1 [B] Madecassoside: HE adds "anti-inflammatory"

- Target: `667:66`
- Current EN (`667:66`, [0,14) Rubik/Medium/12 + [14,126) Rubik/Regular/12):
```text
Madecassoside
Derived from Centella asiatica, it soothes, strengthens the moisture barrier, and provides antioxidant benefits.
```
- HE (`793:381`, p.36, [0,15) Rubik/SemiBold/14 + [15,149) Rubik/Regular/12; HE emphasis: "‏Madecassoside" (SemiBold 14)):
```text
‏Madecassoside
‏רכיב פעיל המופק מצמח הסנטלה האסיאתית. הוא מסייע להרגיע את מראה העור ולתמוך בתפקודו התקין של מחסום הלחות, אנטידלקתי ונוגד תהליך חמצון.
```
- New EN (paste):
```text
Madecassoside
Derived from Centella asiatica, it helps soothe the skin and supports the normal function of the moisture barrier; anti-inflammatory and antioxidant.
```
- Emphasised runs in the new text: "Madecassoside" [0, 13]
- Style / notes: Name line emphasised (as now), rest Regular 12.

#### E36.2 [B] Niacinamide: HE adds "anti-inflammatory"

- Target: `667:70`
- Current EN (`667:70`, [0,12) Rubik/Medium/12 + [12,125) Rubik/Regular/12):
```text
Niacinamide
Strengthens the skin barrier, improves moisture retention, and promotes a calm, even, healthy-looking complexion.
```
- HE (`793:385`, p.36, [0,26) Rubik/SemiBold/14 + [26,137) Rubik/Regular/12; HE emphasis: "‏Niacinamide – ניאצינאמיד" (SemiBold 14)):
```text
‏Niacinamide – ניאצינאמיד
‏מסייע לתמוך במחסום העורי, אנטידלקתי ומשפר את יכולת העור 
לשמור על לחות. מעניק לעור מראה אחיד, רגוע ובריא יותר.
```
- New EN (paste):
```text
Niacinamide
Supports the skin barrier, is anti-inflammatory, and improves the skin's ability to retain moisture, for a calm, even, healthy-looking complexion.
```
- Emphasised runs in the new text: "Niacinamide" [0, 11]
- Style / notes: Name line emphasised (as now).

#### E36.3 [C] Emphasis run too long ("Provitamin B5" is emphasised too)

- Target: `667:65`
- Current EN (`667:65`, [0,23) Rubik/Medium/12 + [23,117) Rubik/Regular/12):
```text
Panthenol
Provitamin B5 that retains moisture, relieves dryness and discomfort, and promotes softness and suppleness.
```
- HE (`793:380`, p.36, [0,20) Rubik/SemiBold/14 + [20,121) Rubik/Regular/12; HE emphasis: "‏Panthenol – פנתנול" (SemiBold 14)):
```text
‏Panthenol – פנתנול
‏פרו־ויטמין B5 המסייע לשמור על הלחות, להרגיע תחושות של יובש ואי־נוחות ולתמוך במראה עור רך וגמיש יותר.
```
- Emphasised: "Panthenol"
- Style / notes: Set characters 10–23 ("Provitamin B5") to Regular 12; only "Panthenol" stays emphasised (HE: name line only).

### EN p.38 (old EN p.34) — frame `667:27` "EN — 34 — MITOPEN" ↔ HE p.38 `793:401`

#### E38.1 [IMG] Third product under "for infusing products": MITOTECH CELL BOOSTER kit photo (owner edit B7)

- Target: `new image in 667:27 (clone HE 886:2)`
- HE node `886:2` (image / frame, see dump)
- Style / notes: Clone HE 886:2 (IMAGE e2436bfbd7, 111×148, FIT) into 667:27 between 667:41 (V-TECH) and 667:42 (EXOSIGNAL HAIR); order left→right as HE: V-TECH SYSTEM · MITOTECH CELL BOOSTER · EXOSIGNAL HAIR. Re-space the row evenly across the text column (x 312–750) on one baseline with the other two photos.

#### E38.2 [A] Caption for the new product

- Target: `new caption (clone 667:43)`
- HE (`886:3`, p.38, Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
‏MITOTECH
CELL BOOSTER
```
- New EN (paste):
```text
MITOTECH
CELL BOOSTER
```
- Style / notes: Same style as 667:43/667:37 (Medium 12, centred under its photo, 2 lines as HE).

#### E38.3 [A] Last bullet introduces the product row: HE "for infusing products:"

- Target: `667:40`
- Current EN (`667:40`, Rubik/Regular/12):
```text
•  Adjustable needle depth: 0.25–2.5 mm – tailored to the treatment area, skin thickness, and indication.
•  Up to 5 adjustable speeds – allowing control over micro-channel density and stimulation intensity.
•  Ergonomic cordless design – for comfortable, quiet, and precise clinical use.
•  Designed to support the delivery of active ingredients.
```
- HE (`793:416`, p.38, Rubik/Regular/12):
```text
‏•  עומק מחט מתכוונן בין 0.25-2.5 מ״מ – התאמה מדויקת לכל אזור, לעובי העור ולאינדיקציה.
‏•  מספר מהירויות מתכווננות לשליטה בצפיפות המיקרו־תעלות ועוצמת הגירוי.
עד 5 מהירויות.
‏•  עיצוב ארגונומי ואלחוטי לעבודה מדויקת ושקטה לאורך יום קליני.
‏•  להחדרת חומרים:
```
- New EN (paste):
```text
•  Adjustable needle depth: 0.25–2.5 mm – tailored to the treatment area, skin thickness, and indication.
•  Up to 5 adjustable speeds – allowing control over micro-channel density and stimulation intensity.
•  Ergonomic cordless design – for comfortable, quiet, and precise clinical use.
•  For the delivery of active ingredients:
```
- Style / notes: Only the last bullet changes ("Designed to support the delivery of active ingredients." -> "For the delivery of active ingredients:").

#### E38.4 [C] Trailing line break

- Target: `667:29`
- Current EN (`667:29`, Rubik/Regular/13):
```text
Professional Microneedling Pen

```
- HE (`793:403`, p.38, Rubik/Regular/14):
```text
‏עט מיקרונידלינג מקצועי
Professional Microneedling Pen
```
- New EN (paste):
```text
Professional Microneedling Pen
```
- Style / notes: Delete the final "\n".

### Pages checked with no change needed

EN p.14 (`667:304`, HE 14) — identical. EN old 28 → p.32 (`667:120`, HE 32), old 29 → p.33 (`667:93`, HE 33), old 33 → p.37 (`667:44`, HE 37), old 35 → p.39 (`667:10`, HE 39), old 36 → p.40 (`667:3`, HE 40): same meaning, same photos (only the renumbering G3); the EN back cover keeps its own top image "EN 1" (`667:9`, hash b670134de1) over the shared art — keep. EN p.18: only the unit E18.1. Cover p.1: same photos; HE hides the five background images under the top image (`824:44`–`824:48`), EN keeps `667:511`–`667:515` visible under `667:516` (no visible effect); HE logo `824:51` is 189×189 at (303, −35), EN `667:518` 169×169 at (312, −27) — layout only.

## 4. New EN pp.20–23 — MITOTECH CELL BOOSTER (clone HE frames, translate node by node)

Translated from the Hebrew now on HE pp.20–23 (owner text 01/11 v2, `canon-v2.md`); terms as in the EN protocols (`protocols-en.md`: concentrated powder, booster ampoule, vial, "Recommended dosage: 0.5 mL twice a day or 1 mL once a day", "Each pair of vials is intended for use over two weeks", "Total of up to 60 treatments!"). Step wording on p.22 follows the English user guide R7 where the HE matches it.

Mirroring (LTR): container/text x_EN = 794 − x_HE − w; text alignment RIGHT → LEFT (CENTER stays); swap the two CONTENT columns (HE "col right" x 410 → EN x 54; "col left" x 54 → EN x 410); section band `941:38`/`956:22`/`956:43` x 776 → 0; p.20 product panel `941:7` (0–300) → 494–794 with its glows, hairline frame and photo `941:19` (x 38 → 531); hairlines `941:6`, `941:27`, `956:8`, `956:29` mirrored the same way. p.22: the five step columns run 1→5 left to right (step 1 at x 54, step 5 at x 614; icons move with their step, do NOT flip the pictograms). p.23: kit icons stay with their lines in the right-hand column. Remove the RLM (U+200F) at the start of HE lines. Note: the EN edition did not mirror every product page (p.10 and MITOPEN keep the HE side); mirroring is the default here — decide per spread.

### New frame `EN — 20 — MITOTECH CELL BOOSTER` ← HE p.20 `941:2` "HE — 20 — MITOTECH CELL BOOSTER"

Images on the HE page (keep in the clone): `941:19` "IMG — MITOTECH CELL BOOSTER" 225×300 at (38, 98) hash e2436bfbd7.

#### HE `941:3` → EN (HE at x 340, w 400, y 56; mirrored x 54)

- HE ([0,9) Rubik/ExtraBold/30 + [9,21) Rubik/Light/30; HE emphasis: "MITOTECH " (ExtraBold 30)):
```text
MITOTECH CELL BOOSTER
```
- EN (paste):
```text
MITOTECH CELL BOOSTER
```
- Emphasised runs: "MITOTECH " [0, 9]  (here: ExtraBold for "MITOTECH ", Light for the rest)
- Style: Keep: "MITOTECH " Rubik ExtraBold 30 + "CELL BOOSTER" Rubik Light 30 (as HE).

#### HE `941:4` → EN (HE at x 340, w 400, y 101; mirrored x 54)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
ADVANCED SKIN TO CELL DELIVERY SYSTEM
```
- EN (paste):
```text
ADVANCED SKIN TO CELL DELIVERY SYSTEM
```
- Style: Keep (Latin, SemiBold 12).

#### HE `941:5` → EN (HE at x 340, w 400, y 122; mirrored x 54)

- HE (Rubik/Regular/12):
```text
מערכת בוסטר דו־שלבית המבוססת על טכנולוגיית הולכה טרנסדרמלית מתקדמת, למראה עור מוצק, חלק ורווי בלחות.
```
- EN (paste):
```text
A two-step booster system based on advanced transdermal delivery technology, for firmer, smoother, deeply hydrated-looking skin.
```
- Style: Regular 12.

#### HE `941:11` → EN (HE at x 340, w 400, y 179; mirrored x 54)

- HE (Rubik/Regular/12):
```text
מערכת טיפוח מתקדמת המשלבת חומצה היאלורונית במשקלים מולקולריים שונים, קולגן שעבר הידרוליזה ופפטידים ייעודיים, בטכנולוגיית הולכה המבוססת על הפפטיד DST-516.
הטכנולוגיה פותחה כדי להתמודד עם מגבלות החדירה של רכיבים פעילים דרך מחסום העור. במחקרי מעבדה על מודל עור אנושי הודגמה יכולת הולכה של חומצה היאלורונית אל שכבת הדרמיס.
המערכת מבוססת על שני שלבים המופעלים בעת הערבוב, ומיועדת לתמיכה בלחות העור, במוצקותו, בגמישותו ובשיפור מראה סימני הגיל.
מבנה הנוצר לאחר ערבוב קטן פיזית פי 1,000 (!) מנקבוביות העור, חודר דרך שכבות האפידרמיס, מגיע לדרמיס ויוצר אפקט דמוי פילר.
```
- EN (paste):
```text
An advanced skincare system that combines hyaluronic acid in different molecular weights, hydrolyzed collagen and targeted peptides with a delivery technology based on the DST-516 peptide.
The technology was developed to address the limited penetration of active ingredients through the skin barrier. Laboratory studies on a human skin model demonstrated delivery of hyaluronic acid into the dermis.
The system is based on two phases that are activated on mixing, and is designed to support skin hydration, firmness and elasticity and to improve the appearance of signs of ageing.
The structure formed after mixing is physically 1,000 times (!) smaller than the skin's pores: it passes through the layers of the epidermis, reaches the dermis and creates a filler-like effect.
```
- Style: Regular 12, 4 paragraphs (inside CONTENT frame 941:10).

#### HE `941:16` → EN (HE at x 60, w 180, y 24; mirrored x 554)

- HE (Rubik/Bold/11; HE emphasis: whole node (Bold)):
```text
MITODERM
```
- EN (paste):
```text
MITODERM
```
- Style: Keep.

#### HE `941:17` → EN (HE at x 40, w 300, y 535; mirrored x 454)

- HE (Rubik/Regular/8):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- EN (paste):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style: Keep.

### New frame `EN — 21 — MITOTECH CELL BOOSTER — Active ingredients` ← HE p.21 `941:21` "HE — 21 — MITOTECH CELL BOOSTER (המשך)"

#### HE `941:22` → EN (HE at x 560, w 180, y 24; mirrored x 54)

- HE (Rubik/Bold/11; HE emphasis: whole node (Bold)):
```text
MITODERM
```
- EN (paste):
```text
MITODERM
```
- Style: Keep.

#### HE `941:23` → EN (HE at x 440, w 300, y 535; mirrored x 54)

- HE (Rubik/Regular/8):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- EN (paste):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style: Keep.

#### HE `941:24` → EN (HE at x 54, w 686, y 56; mirrored x 54)

- HE ([0,9) Rubik/ExtraBold/30 + [9,21) Rubik/Light/30; HE emphasis: "MITOTECH " (ExtraBold 30)):
```text
MITOTECH CELL BOOSTER
```
- EN (paste):
```text
MITOTECH CELL BOOSTER
```
- Emphasised runs: "MITOTECH " [0, 9]  (here: ExtraBold for "MITOTECH ", Light for the rest)
- Style: Keep (ExtraBold + Light).

#### HE `941:25` → EN (HE at x 54, w 686, y 96; mirrored x 54)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
ADVANCED SKIN TO CELL DELIVERY SYSTEM
```
- EN (paste):
```text
ADVANCED SKIN TO CELL DELIVERY SYSTEM
```
- Style: Keep.

#### HE `941:29` → EN (HE at x 410, w 330, y 150; mirrored x 54)

- HE (Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
רכיבים פעילים
```
- EN (paste):
```text
Active Ingredients
```
- Style: Sub-head (HE SemiBold 14).

#### HE `941:30` → EN (HE at x 410, w 330, y 169; mirrored x 54)

- HE ([0,26) Rubik/SemiBold/12 + [26,389) Rubik/Regular/12; HE emphasis: "‏1. CONCENTRATED POWDER –" (SemiBold 12)):
```text
‏1. CONCENTRATED POWDER –
אבקה מרוכזת בטכנולוגיית ייבוש בהקפאה: אבקה ליופילית המכילה חומצה היאלורונית במשקל מולקולרי גבוה ונמוך ביחס 3:1, קולגן שעבר הידרוליזה ופפטידים מתקדמים.
הרכיבים עוברים תהליך ייבוש בהקפאה בטמפרטורה של ‎70°C−, המסייע בשמירה על יציבותם עד להפעלת הפורמולה. המערכת משלבת את טכנולוגיית DST-516, המבוססת על פפטיד חודר טרנסדרמלי, לתמיכה בהולכת רכיבים פעילים דרך מחסום העור.
```
- EN (paste):
```text
1. CONCENTRATED POWDER –
Concentrated powder made with freeze-drying technology: a lyophilized powder containing high- and low-molecular-weight hyaluronic acid in a 3:1 ratio, hydrolyzed collagen and advanced peptides.
The ingredients are freeze-dried at −70°C, which helps keep them stable until the formula is activated. The system incorporates DST-516 technology, based on a transdermal penetrating peptide, to support the delivery of active ingredients through the skin barrier.
```
- Emphasised runs: "1. CONCENTRATED POWDER –" [0, 24]
- Style: Item title line emphasised (HE SemiBold 12), rest Regular 12. Drop the RLM that starts the HE line.

#### HE `941:31` → EN (HE at x 54, w 330, y 169; mirrored x 410)

- HE ([0,23) Rubik/SemiBold/12 + [23,227) Rubik/Regular/12; HE emphasis: "‏2. BOOSTING AMPOULE –" (SemiBold 12)):
```text
‏2. BOOSTING AMPOULE –
אמפולת בוסטר להפעלת הפורמולה: תמיסת בוסטר המכילה ניאצינאמיד, אדנוזין, לציטין וצרמידים. האמפולה מיועדת לערבוב עם האבקה המרוכזת ליצירת סרום פעיל במרקם קליל, הנספג במהירות ומעניק תחושת עור חלקה ולחות מוגברת.
```
- EN (paste):
```text
2. BOOSTING AMPOULE –
Booster ampoule that activates the formula: a booster solution containing niacinamide, adenosine, lecithin and ceramides. The ampoule is designed to be mixed with the concentrated powder to create an active serum with a light texture that absorbs quickly, leaving the skin feeling smooth and more hydrated.
```
- Emphasised runs: "2. BOOSTING AMPOULE –" [0, 21]
- Style: As 941:30.

#### HE `941:12` → EN (HE at x 54, w 330, y 260; mirrored x 410)

- HE (Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
יתרונות מרכזיים
```
- EN (paste):
```text
Key Benefits
```
- Style: Sub-head.

#### HE `941:13` → EN (HE at x 54, w 330, y 279; mirrored x 410)

- HE (Rubik/Regular/12):
```text
לחות אינטנסיבית | מראה עור מוצק ומתוח יותר | שיפור מראה קמטוטים | תמיכה בגמישות העור | שיפור מראה מרקם העור | מראה עור חלק ואחיד | תמיכה במחסום העור | תחושת רכות | מראה עור רענן וזוהר | מערכת בוסטר ללא מחטים
```
- EN (paste):
```text
Intensive hydration | Firmer, tighter-looking skin | Improved appearance of fine lines | Supports skin elasticity | Improved appearance of skin texture | Smooth, even-looking skin | Supports the skin barrier | Soft feel | Fresh, radiant-looking skin | Needle-free booster system
```
- Style: Regular 12.

### New frame `EN — 22 — MITOTECH CELL BOOSTER — Preparation` ← HE p.22 `956:2` "HE — 22 — MITOTECH CELL BOOSTER — הכנה"

#### HE `956:3` → EN (HE at x 560, w 180, y 24; mirrored x 54)

- HE (Rubik/Bold/11; HE emphasis: whole node (Bold)):
```text
MITODERM
```
- EN (paste):
```text
MITODERM
```
- Style: Keep.

#### HE `956:4` → EN (HE at x 440, w 300, y 535; mirrored x 54)

- HE (Rubik/Regular/8):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- EN (paste):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style: Keep.

#### HE `956:5` → EN (HE at x 54, w 686, y 56; mirrored x 54)

- HE ([0,9) Rubik/ExtraBold/30 + [9,21) Rubik/Light/30; HE emphasis: "MITOTECH " (ExtraBold 30)):
```text
MITOTECH CELL BOOSTER
```
- EN (paste):
```text
MITOTECH CELL BOOSTER
```
- Emphasised runs: "MITOTECH " [0, 9]  (here: ExtraBold for "MITOTECH ", Light for the rest)
- Style: Keep (ExtraBold + Light).

#### HE `956:6` → EN (HE at x 54, w 686, y 96; mirrored x 54)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
ADVANCED SKIN TO CELL DELIVERY SYSTEM
```
- EN (paste):
```text
ADVANCED SKIN TO CELL DELIVERY SYSTEM
```
- Style: Keep.

#### HE `950:2` → EN (HE at x 410, w 330, y 150; mirrored x 54)

- HE (Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
אופן השימוש
```
- EN (paste):
```text
How to Use
```
- Style: Sub-head.

#### HE `941:32` → EN (HE at x 360, w 380, y 169; mirrored x 54)

- HE (Rubik/Regular/12):
```text
מערבבים אמפולת בוסטר אחת עם בקבוקון האבקה המרוכזת עד לקבלת תמיסה אחידה ושקופה. מורחים על עור נקי ויבש ומעסים עד לספיגה.
– כל זוג בקבוקונים מיועד לשימוש עד שבועיים.
```
- EN (paste):
```text
Mix one booster ampoule with the concentrated powder vial until a uniform, clear solution forms. Apply to clean, dry skin and massage until absorbed.
– Each pair of vials is intended for use for up to two weeks.
```
- Style: Regular 12.

#### HE `957:2` → EN (HE at x 54, w 686, y 230; mirrored x 54)

- HE (Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
הכנה ב-5 שלבים
```
- EN (paste):
```text
Preparation in 5 Steps
```
- Style: Sub-head.

#### HE `957:3` → EN (HE at x 614, w 126, y 259; mirrored x 54)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
1. פתיחת הבקבוקונים
```
- EN (paste):
```text
1. Open the vials
```
- Style: Step title (SemiBold 12 in HE).

#### HE `957:4` → EN (HE at x 614, w 126, y 404; mirrored x 54)

- HE (Rubik/Regular/12):
```text
מסירים את הפקקים מבקבוקון האבקה המרוכזת ומאמפולת הבוסטר.
```
- EN (paste):
```text
Remove the caps from the concentrated powder vial and the booster ampoule.
```
- Style: Regular 12.

#### HE `957:46` → EN (HE at x 474, w 126, y 259; mirrored x 194)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
2. ללא ניעור
```
- EN (paste):
```text
2. Do not shake
```
- Style: Step title.

#### HE `957:47` → EN (HE at x 474, w 126, y 404; mirrored x 194)

- HE (Rubik/Regular/12):
```text
מוסיפים לאט 15 מ״ל מאמפולת הבוסטר לבקבוקון האבקה. יש להקפיד שלא יגלוש. לא לנער.
```
- EN (paste):
```text
Slowly add 15 mL of the booster ampoule to the powder vial. Be careful not to let it overflow. Do not shake.
```
- Style: Regular 12.

#### HE `957:161` → EN (HE at x 334, w 126, y 259; mirrored x 334)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
3. להמתין שעה
```
- EN (paste):
```text
3. Wait one hour
```
- Style: Step title.

#### HE `957:162` → EN (HE at x 334, w 126, y 404; mirrored x 334)

- HE (Rubik/Regular/12):
```text
מניחים לאבקה להתמוסס בהדרגה. ממתינים לפחות שעה אחת להפעלה, ללא ניעור.
```
- EN (paste):
```text
Let the powder dissolve gradually. Wait at least one hour for activation, without shaking.
```
- Style: Regular 12.

#### HE `957:193` → EN (HE at x 194, w 126, y 259; mirrored x 474)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
4. לנער היטב
```
- EN (paste):
```text
4. Shake well
```
- Style: Step title.

#### HE `957:194` → EN (HE at x 194, w 126, y 404; mirrored x 474)

- HE (Rubik/Regular/12):
```text
לאחר ההמסה מחליפים את הפקק באפליקטור ומנערים היטב לערבוב מלא.
```
- EN (paste):
```text
Once dissolved, replace the cap with the applicator and shake well to mix completely.
```
- Style: Regular 12.

#### HE `957:270` → EN (HE at x 54, w 126, y 259; mirrored x 614)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
5. יישום
```
- EN (paste):
```text
5. Apply
```
- Style: Step title.

#### HE `957:271` → EN (HE at x 54, w 126, y 404; mirrored x 614)

- HE (Rubik/Regular/12):
```text
לוחצים קלות על האפליקטור כדי להוציא את המוצר. מינון מומלץ: 0.5 מ״ל פעמיים ביום או 1 מ״ל פעם ביום.
```
- EN (paste):
```text
Press the applicator lightly to dispense the product. Recommended dosage: 0.5 mL twice a day or 1 mL once a day.
```
- Style: Regular 12.

#### HE `957:398` → EN (HE at x 54, w 686, y 495; mirrored x 54)

- HE (Rubik/Regular/12):
```text
הערה: בעת ניעור חזק עשויות להיווצר בועות. זה תקין — אפשר להשתמש בביטחון.
```
- EN (paste):
```text
Note: bubbles may form when shaken hard. This is normal — use with confidence.
```
- Style: Regular 12, full width.

### New frame `EN — 23 — MITOTECH CELL BOOSTER — Combinations and kit` ← HE p.23 `956:23` "HE — 23 — MITOTECH CELL BOOSTER — שאלות נפוצות"

#### HE `956:24` → EN (HE at x 560, w 180, y 24; mirrored x 54)

- HE (Rubik/Bold/11; HE emphasis: whole node (Bold)):
```text
MITODERM
```
- EN (paste):
```text
MITODERM
```
- Style: Keep.

#### HE `956:25` → EN (HE at x 440, w 300, y 535; mirrored x 54)

- HE (Rubik/Regular/8):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- EN (paste):
```text
MITODERM | WHERE SCIENCE MEETS BEAUTY
```
- Style: Keep.

#### HE `956:26` → EN (HE at x 54, w 686, y 56; mirrored x 54)

- HE ([0,9) Rubik/ExtraBold/30 + [9,21) Rubik/Light/30; HE emphasis: "MITOTECH " (ExtraBold 30)):
```text
MITOTECH CELL BOOSTER
```
- EN (paste):
```text
MITOTECH CELL BOOSTER
```
- Emphasised runs: "MITOTECH " [0, 9]  (here: ExtraBold for "MITOTECH ", Light for the rest)
- Style: Keep (ExtraBold + Light).

#### HE `956:27` → EN (HE at x 54, w 686, y 96; mirrored x 54)

- HE (Rubik/SemiBold/12; HE emphasis: whole node (SemiBold)):
```text
ADVANCED SKIN TO CELL DELIVERY SYSTEM
```
- EN (paste):
```text
ADVANCED SKIN TO CELL DELIVERY SYSTEM
```
- Style: Keep.

#### HE `950:3` → EN (HE at x 410, w 330, y 150; mirrored x 54)

- HE (Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
שילוב במכשור ובטיפולים מקצועיים
```
- EN (paste):
```text
Combination with Devices and Professional Treatments
```
- Style: Sub-head (may need 2 lines in 330 px at 14 pt).

#### HE `941:35` → EN (HE at x 410, w 330, y 169; mirrored x 54)

- HE ([0,50) Rubik/SemiBold/12 + [50,85) Rubik/Regular/12 + [85,110) Rubik/SemiBold/12 + [110,204) Rubik/Regular/12; HE emphasis: "1. לאחר שימוש במזרק הביוספיקול: MICRO BOOST 10% –" (SemiBold 12), "אופציה להמשך טיפול ביתי:" (SemiBold 12)):
```text
1. לאחר שימוש במזרק הביוספיקול: MICRO BOOST 10% –
מחדירים ‎1–2 מ״ל של החומר המעורבב.
אופציה להמשך טיפול ביתי:
ניתן לתת ללקוחה הביתה את האמפולה המעורבבת – מינון מומלץ 0.5 מ״ל פעמיים ביום או 1 מ״ל פעם ביום.
```
- EN (paste):
```text
1. After using the BIOSPICULE syringe: MICRO BOOST 10% –
Infuse 1–2 mL of the mixed product.
Option for continued home care:
The mixed ampoule can be given to the client to take home – recommended dosage 0.5 mL twice a day or 1 mL once a day.
```
- Emphasised runs: "1. After using the BIOSPICULE syringe: MICRO BOOST 10% –" [0, 56], "Option for continued home care:" [93, 124]
- Style: Two emphasised lines (HE SemiBold), rest Regular 12.

#### HE `941:36` → EN (HE at x 410, w 330, y 253; mirrored x 54)

- HE ([0,12) Rubik/SemiBold/12 + [12,109) Rubik/Regular/12 + [109,134) Rubik/SemiBold/12 + [134,238) Rubik/Regular/12; HE emphasis: "‏2. MITOPEN" (SemiBold 12), "אופציה להמשך טיפול ביתי:" (SemiBold 12)):
```text
‏2. MITOPEN
בשילוב עם מכשיר המיטופן. ניתן להשתמש בחומר המעורבב בשילוב עם טכנולוגיית מיקרונידלינג – ‎1–2 מ״ל.
אופציה להמשך טיפול ביתי:
לאחר מכן ניתן לתת ללקוחה הביתה את האמפולה המעורבבת – מינון מומלץ: 0.5 מ״ל פעמיים ביום או 1 מ״ל פעם ביום.
```
- EN (paste):
```text
2. MITOPEN
In combination with the MITOPEN device: the mixed product can be used together with microneedling technology – 1–2 mL.
Option for continued home care:
The mixed ampoule can then be given to the client to take home – recommended dosage: 0.5 mL twice a day or 1 mL once a day.
```
- Emphasised runs: "2. MITOPEN" [0, 10], "Option for continued home care:" [130, 161]
- Style: As 941:35.

#### HE `941:37` → EN (HE at x 410, w 330, y 352; mirrored x 54)

- HE ([0,36) Rubik/SemiBold/12 + [36,150) Rubik/Regular/12; HE emphasis: "3. תוכנית טיפוח ביתית למשך 8 שבועות" (SemiBold 12)):
```text
3. תוכנית טיפוח ביתית למשך 8 שבועות
‏– כל הערכה למכירה
מינון מומלץ: 0.5 מ״ל פעמיים ביום או 1 מ״ל פעם ביום.
כל זוג בקבוקונים מיועד לשימוש במשך שבועיים.
```
- EN (paste):
```text
3. 8-week home care programme
– the complete kit, for retail sale
Recommended dosage: 0.5 mL twice a day or 1 mL once a day.
Each pair of vials is intended for use over two weeks.
```
- Emphasised runs: "3. 8-week home care programme" [0, 29]
- Style: Title line emphasised.

#### HE `959:2` → EN (HE at x 54, w 330, y 150; mirrored x 410)

- HE (Rubik/SemiBold/14; HE emphasis: whole node (SemiBold)):
```text
תכולת האריזה
```
- EN (paste):
```text
Package Contents
```
- Style: Sub-head (kit icons stay).

#### HE `959:76` → EN (HE at x 54, w 259, y 184; mirrored x 481)

- HE (Rubik/Regular/12):
```text
אבקה מרוכזת – ‏4 × 154 מ״ג
```
- EN (paste):
```text
Concentrated powder – 4 × 154 mg
```
- Style: Regular 12, next to its icon.

#### HE `959:104` → EN (HE at x 54, w 259, y 222; mirrored x 481)

- HE (Rubik/Regular/12):
```text
אמפולות בוסטר פעילות – ‏4 × 15 מ״ל
```
- EN (paste):
```text
Active booster ampoules – 4 × 15 mL
```
- Style: Regular 12.

#### HE `959:90` → EN (HE at x 54, w 260, y 260; mirrored x 480)

- HE (Rubik/Regular/12):
```text
אפליקטורים – 4 יח׳
```
- EN (paste):
```text
Applicators – 4 pcs
```
- Style: Regular 12 — line not in the owner text (from user guide R7); kept as on HE (Q).

#### HE `941:33` → EN (HE at x 54, w 330, y 291; mirrored x 410)

- HE (Rubik/Regular/12):
```text
סה״כ עד 60 טיפולים!
```
- EN (paste):
```text
Total of up to 60 treatments!
```
- Style: Regular 12 (wording as the EN protocols).

## 5. Second pass (all 40 HE pages, looking only for misses)

Re-read every HE text node and image against the EN counterpart, then visually compared EN/HE renders of pp.2, 4, 15, 17, 18, 19, 29↔25, 31↔27, 32↔28, 34↔30, 38↔34 (`shots/`). Found on the second pass and added above: the hidden kit photo + exosome background on p.4 (E4.1), the different photo on p.15 (E15.1), the missing running heads / titles / footers / pack-shot captions on the continuation pages 17, 19, 27→31, 30→34 (E17.1–2, E19.2, E31.1, E34.1), "suitable for all pigmentation types" on p.9 (E9.1), "young ages" on p.29 (E29.1), the missing "|" on p.13 (E13.1), the long emphasis run on p.36 (E36.3), "Pack Contents" on p.6 (E6.4), "treats a compromised epidermal barrier" on p.10 (E10.4), the label copy "Deep nourishing" on p.27 (E27.2). Checked and needing nothing: pp.14, 32, 33, 37, 39, 40; EN has no Hebrew, Cyrillic or bidi marks today.

Not counted as edits (pure typography or same meaning): HE RLM/LRM marks and spacing; HE double spaces; heading colons; the EN-only headings "The Story Behind the Name" (p.3), "Expected Results" (p.7), "Key Benefits"/"Recommended For" (p.27); bullets vs " | " lists on p.27; British/US spelling; HE packaging lines that are already English. Typography of the EN edition (sizes 9.5/13/18/20/26/28 pt off the HE scale 8·10·11·12·14·16·21·30·41) is a separate layout pass, not part of this list.

## 6. Open questions

1. ToC: HE section 7 (BIOSPICULE™ series) also lists "• MITOTECH CELL BOOSTER two-step booster system with transdermal delivery" (HE `884:2`) although MITOTECH is section 5 with its own pages 20–23. Mirrored as instructed — keep it in EN, or remove from both (PLAN.md already asks the owner whether to drop it on HE)?
2. PDRN source: HE says "from salmon stem cells" (`824:111` p.6, `824:196` p.12); the current EN says "derived from salmon". E7.2 / E12.1 follow HE — confirm, or keep the neutral EN wording.
3. p.15 (`793:242`): HE "shortens the skin renewal cycle from 7 to 28 days" is logically reversed; E15.2 writes "from 28 to 7 days". Confirm (the HE page is final and is not touched).
4. p.30 (`796:12`): HE "gradual removal of basal cells"; EN keeps "dead skin cells" (E30.1). Keep EN?
5. p.23: "Applicators – 4 pcs" (HE `959:90`) is not in the owner text 01/11 (it comes from the user guide R7); kept because HE keeps it.
6. p.22: "until a uniform, clear solution forms" (owner text) vs user guide R7 "the mixture turns cloudy" — already open on HE; EN follows HE.
7. p.4 (E4.1): the EN uses an exosome-sphere background and hides the V-TECH kit photo; HE (final) shows the kit photo on dark brown. Switch EN to the HE visual?
8. Cover (E1.1): HE "קטלוג מוצרים" = "Product Catalog"; EN shows "CATALOG". Change to "PRODUCT CATALOG"?
9. Fit: adding the HE running heads / titles to EN p.17 (E17.2, +~70 px) and p.19 (E19.2, +~90 px) overflows the footer line with the current EN text sizes (deficit ~15 px on p.17, ~50 px on p.19). Options: two-column body (as HE), or 12→10 pt body on those pages per the layout skill; decide in the layout pass.
10. Block distribution pp.6–7 and 8–9 (E6.6, E8.2): EN keeps the same content but in a different page order than HE. Mirror block-for-block or leave?
11. MITOTECH pages: mirror the layout (default here) or keep the HE side as EN did on p.10 and MITOPEN?

