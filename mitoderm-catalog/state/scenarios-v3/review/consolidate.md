# consolidate — chief editor's pass over the v3 scenarios file

Date 2026-11-08 (01:20–01:50 local). Scope: all `src/*.md` in print order. All dependency files (00, 02, format-v3, 95, 97, 98, 99,
MITOTECH, MITOSCAN, g4, g5) landed and were committed before the step that needed them; none was missing.

## Checks run (scripts in the scratchpad, not in the repo)

- Structure of all 13 chapters against `format-v3.md`: 8 headings in order, 7-row card, 10-row ladder (6 columns, rung names as in
  `00-concept.md` §2), 9-column shot table, ids `<slug>-F01..`, seconds contiguous from 0 (36–38 s each), scroll contiguous from 0,
  totals line present, §7 and §8 present. All pass (HAIR/SPRAY use half seconds, contiguous).
- Facts: every unmarked «…» in each chapter searched in the approved sources + `facts.json` (+ catalogue HE-40 texts and the MITOTECH
  page map for MITOTECH). Non-matches are scare quotes, composed kit/step pairs and repeated proposals; no invented claim found.
  High-risk claims (`medical_claim_flags`) on screen: HAIR and SPRAY name them only to say they stay off screen (OK); MITOSCAN showed
  b0.line «מערכת אבחון שיער…» and the kicker «כלי אמון והוכחת תוצאה» while its own §4 kept «אבחון» / «הוכחת תוצאה» off screen — fixed.
- Cyrillic: 0 in every `src/*.md` (format-v3's check command now uses `\u` escapes instead of literal Cyrillic range characters).

## Changes per file

- **All 13 chapters**
  - §8 rewritten with numbers by one seconds-based method (`costs.json` per-film method applied to each chapter's own shots):
    video seconds = generator shots in 16:9 + shots regenerated in 9:16; stills 2/3/6 cr × 2/3/4 tries; drafts 3 cr/s × 1/2/3;
    finals 9/12/16 cr/s × 2/3/4; object swap 2.1/9.6/9.6 cr/s × 1/2/3 on the swap shots in both aspects; 4K upscale 0/4/8 cr/s on
    0/30/50 % of the 16:9 seconds; USD 0.043/0.05/0.07 per credit. Shared library counted once: room + 6 table plates in home §8,
    cosmetologist in EXO-NAD; chapters no longer count a table still.
  - One balance line everywhere: «**היתרה ב-Higgsfield:** 1 קרדיט, מסלול חינמי (נבדק 08/11/2026 00:45; …)».
  - Cast/set paragraph replaced by one line pointing to «השפה החזותית וההפקה», סעיף 3 (+ the series colour detail, the film's client,
    and any product-specific caveat kept).
  - Dramatization line unified: «הסצנות בסרט הן המחשה; התוצאות — צילומי לפני/אחרי אמיתיים בלבד.» (was 4 variants; "בסרט" covers the
    DERMA bathroom and home scenes).
  - Phone order sentence unified: «כותרת ← במה (≈46% מגובה המסך, מתחת לכותרת) ← טקסט».
  - Bridge line unified («תוכלו להיות הקוסמטיקאית הזאת.»; SPRAY had a longer variant).
  - Form: «מטופל/ת» (not «מטופלת») where home products offer the option; the 11/10 no-response-time source added in GEL, MASK,
    CELLULAR, CELL RENEW; SPRAY family block gets the standard photo sentence.
  - Proof captions reduced to the base form and three fixed exceptions, now defined once in `97-rules.md` §1.
- **mitoscan.md**: b0.line off screen (word «אבחון»), kicker «הרגישו»; caption → «אותו אזור · ×[50/200] · אחרי [N] טיפולים · …»;
  plate = silver only (`set-T04`), blue drop left to the owner.
- **mitopen.md / 01-home.md**: MITOPEN transition 3 s and long-axis turn ≤ 15°; HAIR transition no longer turns the box 180° (≤ 8°);
  MITOSCAN plate «כסף»; home §8 with numbers (7 stills = 28/63/168 cr) and the I2V-transition fallback priced but excluded.
- **derma-recovery-cream.md**: bathroom-set sentence kept in the new cast line.
- **00-concept.md**: form table names the home-product «מטופל/ת» option; roadmap ref → «מפת הדרכים, סעיף 7».
- **97-rules.md** §1: the caption family and the male consent variant.
- **98-costs.md**: §1 canonical balance line; §4 unit prices per second with tries; §5 sample from the EXO-NAD chapter (+ room and
  champagne plate) with the research model as cross-check; §6 a table of all 13 films; §7 home; §8 series = 13 films + home + 13
  transitions (0, three.js).
- **99-roadmap.md**: §1 replaced by the BRIEF stages 0–7 with deliverable, date, token budget, credits and gate; gates renumbered
  (3–7); §5 timeline per BRIEF; new §8 (the nine speed-ups) and §9 (what we decide alone / only the owner).
- **format-v3.md**: §8 balance-line wording; Cyrillic-free check command.

## Final totals

- Series: 153 shots, 477 s, 94 generator shots. Credits 13,586 / 31,966 / 58,011 (≈584 / 1,598 / 4,061 USD).
- Sample (EXO-NAD film 11 shots, 36 s, + transition in three.js + 2 set stills): 1,031 / 2,299 / 4,244 cr (≈44 / 115 / 297 USD).
- Research-model caps kept in the roadmap: sample 1,388 / 3,781 / 8,438, series 18,476 / 50,463 / 112,424.

## Open questions for the owner

1. Budget basis: the chapter-based estimate is ~35 % below the research model kept in the roadmap. Keep the model as the cap?
2. Home-product form option «מטופל/ת» (GEL, SPRAY, CELL RENEW, CELLULAR, DERMA) — yes/no.
3. Proof captions: base form + exceptions (weeks at home; clinic + home; MASK right after a procedure; MITOSCAN magnification) — OK?
4. Partner-cosmetologist testimonial as proof for home products (GEL, SPRAY, BIOSPICULE serums) — allowed? (97-rules §1 requires
   name, photo, exact quote, signed approval.)
5. MITOSCAN: the live page's b0.line and the catalogue kicker contain «אבחון» / «הוכחת תוצאה»; the film keeps them off screen — OK,
   or legal review first? Plate silver only or with the `#5aa9e6` drop?
6. The roadmap names the agent models (Fable / Opus / Sonnet) as the BRIEF does — keep in the client file or move to internal notes?
7. Camera/engine terms stay Latin (dolly, dissolve, I2V, WebP, clip-path) as `format-v3.md` allows — OK for the client file?
8. Everything listed in §7 of each chapter and in `95-materials.md` (photos with consent, mechanics, offers, event dates, plan).
