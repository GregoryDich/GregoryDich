# MITODERM — אתר v2: מסירה למתכנת

עודכן 23/10/2026.

## מאיפה מתחילים

1. **Figma:** עמוד «00 · התחלה כאן למתכנת» בקובץ Catalog · Product Pages:
   https://www.figma.com/design/KcOGIzO76mDODxjwIrkGyo/?node-id=223-2
   שם נמצאים:
   - מפת כל העמודים ומצבם;
   - תבנית עמוד מוצר;
   - טוקנים, טיפוגרפיה, פריסה ורכיבים;
   - מנוע ה-3D;
   - מפת הדרכים, נכון ל-23/10 — אותן שורות כמו בגיליון «מפת דרכים» בקובץ `MITODERM-3D-story.xlsx`.
2. **עמודי הדוגמה ב-Figma:**
   - «V-TECH SYSTEM — 3D story (design)», ‏node-id=142-3;
   - «EXOCELL MASK — 3D story (design)», ‏node-id=98-2.

   מעל המסכים יש צילומים של אב-הטיפוס החי — הם מקור האמת לבנייה. המסכים עצמם הם שכבות לעריכה.
3. **אב-טיפוס שרץ:**
   ```
   cd mitoderm-catalog/site/proto
   python3 serve-local.py
   ```
   קבצי אב-הטיפוס הם קטעי body בלי doctype, ‏charset ו-viewport, כי המארח עוטף אותם. גם בדיקת ה-QA עוטפת אותם. ‏serve-local.py עוטף אותם באותה דרך תוך כדי הגשה.

   אחר כך פותחים בדפדפן:
   - http://localhost:8000/vtech-live.html
   - http://localhost:8000/exocell-mask-3d.html
4. **העמודים החיים, ב-HD, בלי התקנה.** כל 12 עמודי המוצרים. הקישורים נפתחים אחרי שהמזמין/ה משתף/ת אותם (Share ← גישה לפי קישור):
   - V-TECH SYSTEM — https://claude.ai/artifact/NdQezU5bikrsuaWVVW5TBK
   - EXOCELL MASK — https://claude.ai/artifact/FA5ySxGihnDAmjQPvDftzn
   - EXOTECH GEL — https://claude.ai/artifact/LsJVky9GDssBuW1eQkLaTe
   - EXOSIGNAL HAIR — https://claude.ai/artifact/2ws7qr1xL7Y7wp5xdbE1jh
   - EXOSIGNAL SPRAY — https://claude.ai/artifact/GAUwhjxzqdk7jEg7JgSBJz
   - EXO-NAD — https://claude.ai/artifact/NcP4v3p7KAdvqZGTnoGK8S
   - MICRO BOOST 10% — https://claude.ai/artifact/3hwRLR8RxjcQV2oGTynari
   - CELLULAR AGE DEFENSE 2.5% — https://claude.ai/artifact/RhFJsLyLDinq2HcizL1hvq
   - MITOPEN — https://claude.ai/artifact/KAn13gS9E2on2ZikQSz4eW
   - CELL RENEW 1.5% — https://claude.ai/artifact/2rVvsAFJ9NRUjymZDmANup
   - MITOSCAN — https://claude.ai/artifact/KD3L1gfgVA8twY7HBvYofp
   - DERMA RECOVERY CREAM — https://claude.ai/artifact/7a3EpTpcTbYMWjTypNk2pV

   הקוד כולו: https://github.com/GregoryDich/GregoryDich/tree/claude/mitoderm-figma-catalog-74tbuw/mitoderm-catalog/site

   כל העמודים שפורסמו, ב-HD ומוכנים לאחסון סטטי, נמצאים בתיקייה `site/public`. בה גם דף פתיחה עם קישורים לעמודים, למסמך הזה ולקובץ ה-Excel של הטקסטים. כל עמוד הוא `<slug>/index.html`, ולידו `img/` עם התמונות שלו (ב-EXOCELL MASK התמונות נמצאות בתוך הדף), ו-`seq/` רק ב-V-TECH, שבנוי מפריימים. את התיקייה בונה `proto/stage-public.py`.

## סדר הבנייה

1. מערכת עיצוב: טוקנים, Rubik, רכיבים.
2. שלד משותף: כותרת עליונה, תפריט צף, כפתורים, טופס פנייה, תחתית.
3. עמוד V-TECH SYSTEM: סיפור 3D בפריימים.
4. עמוד EXOCELL MASK: ‏3D חי ב-three.js.
5. שאר עמודי המוצרים לפי התבנית. הטקסטים — מ-`MITODERM-3D-story.xlsx`. לכל מוצר יש סצנת three.js משלו (`proto/scenes/<slug>.js`), והעמודים שפורסמו הם הדוגמה.
6. דף הבית, הקטלוג, אודות ומדע.
7. עמודי שירות.

המתכנת בונה את האתר ב-React (18/10). העיצוב, המנוע והבדיקות לא תלויים בבחירה הזו.

## קבצים

| נתיב (בתוך `mitoderm-catalog/site`) | מה יש שם |
|---|---|
| `proto/vtech-live.html`, `proto/img/`, `proto/seq/`, `proto/serve-local.py` | אב-טיפוס V-TECH לעבודה ושרת מקומי, עם פריימי הטיוטה ב-`seq/480`. העמוד ב-HD נמצא ב-`public/v-tech-system`. |
| `public/`, `proto/stage-public.py` | האתר הסטטי ב-HD: כל העמודים שפורסמו ודף פתיחה. |
| `proto/exocell-mask-3d.html` | אב-טיפוס MASK. ‏three.js 0.160 נטען מ-jsDelivr. |
| `proto/vtech-live-template.html`, `proto/build-vtech.py` | התבנית והבונה של V-TECH |
| `proto/engine/story.js` | מנוע הפריימים: מודול ES אחד, `createFrameStory`. ‏`build-vtech.py` מכניס אותו לתוך העמוד, כך שאב-הטיפוס של V-TECH ועמוד EXOTECH GEL רצים עליו. |
| `proto/react/useFrameStory.js`, `proto/react/StoryPage.jsx`, `proto/react/demo/` | אותו מנוע ב-React: hook, דוגמת עמוד ודמו שרץ (ראו «React» למטה) |
| `proto/scenes/<slug>.js`, `proto/scenes/render-keys.cjs` | סצנת three.js חיה לכל מוצר מלבד V-TECH ו-MASK: המנוע מצייר אותה במקום פריימים (`build-vtech.py --product <slug> --scene`). ‏`render-keys.cjs` מרנדר ממנה את תמונות המפתח: הסטילס לטלפון ותמונת הערכה. |
| `design/exotech-gel/make_textures.py` | ההדפסה על הצנצנת ועל הקופסה, מסודרת מחדש בגופן Jost לפי מדידות מתמונת המוצר, ולכן חדה בכל גודל |
| `proto/story_content.py` | הטקסטים של מוצר אחר על אותה תבנית, מתוך המקורות המאושרים: `build-vtech.py --product <slug> --files <dir>`. לכל מוצר הקו שלו (V-TECH FACE, ‏HAIR, ‏PEELING, ‏BIOSPICULE, ‏DEVICES): תג הקו, הכותרת «עוד מקו …» וכרטיסי «משלימים את הטיפול». האגדה של האקסוזומים, התאים, מולקולות ה-PDRN וסליל ה-DNA מופיעים רק במוצר שהרכב שלו כולל אותם. |
| `proto/exocell-3d-template.html`, `proto/build-exocell.py` | התבנית והבונה של MASK |
| `proto/vtech-he-figma.json`, `proto/exocell-he-design.json`, `proto/exocell-he-ui.json` | הטקסטים המאושרים בעברית |
| `MITODERM-3D-story.xlsx`, `product-pages.he.json` | הטקסטים לכל המוצרים; מפת הדרכים |
| `design/vtech-3d/` | פריימי מפתח, תאים, מולקולות, סליל DNA, סצנות Blender |
| `design/handoff/` | צילומי האב-טיפוס ופריימי המפתח העדכניים |
| `proto/qa/verify-live.cjs`, `proto/qa/verify-3d.cjs` | בדיקות קבלה ב-Playwright: ‏V-TECH — ‏55 בדיקות, MASK — ‏240 בדיקות |
| `proto/qa/verify-hd.cjs` | בדיקת HD: כל תמונה, רקע וקנבס שנראים בגלילה, בטלפון 390 (DPR 3) ובמחשב 1440 ו-1920 (DPR 2). כמות הפיקסלים שיש מול הכמות שצריך. |
| `../design-rules.md` | כללי העיצוב המלאים |

## React

המתכנת בונה ב-React, ולכן מנוע הפריימים מוכן כמודול שאפשר להרכיב בכל עמוד React:

- **המודול:** ‏`proto/engine/story.js`, הפונקציה `createFrameStory`. זה בדיוק הקוד שאב-הטיפוס של V-TECH רץ עליו: בדיקות ה-QA ‏(55/55) ובדיקת השוואה מול הגרסה הקודמת ‏(45 מיקומי גלילה × מחשב, טלפון והפחתת תנועה, בלי אף הבדל) בודקות אותו.
- **ב-React:** ה-hook ‏`proto/react/useFrameStory.js` ודוגמת העמוד `proto/react/StoryPage.jsx`. בדוגמה יש אותם שמות מחלקות כמו באב-הטיפוס, כך שה-CSS שלו עובד בלי שינוי.
- **מחזור חיים:** המנוע מתחיל ב-`useEffect`, וב-unmount משחרר הכול: המאזינים, ה-worker, הפריימים המפוענחים והתאים שהוסיף. זה עובד גם עם StrictMode (הרכבה, פירוק והרכבה מחדש) וגם במעבר בין עמודים.
- **SSR:** הייבוא בטוח, כי שום דבר לא נוגע ב-`window` לפני ה-effect. ב-Next.js משתמשים בו בקומפוננטת לקוח (`'use client'`).
- **נתונים:** ‏`config` הוא האובייקט ש-`build-vtech.py` כותב לעמוד ‏(runs, tiers, cells, mols, helix). ‏`base` היא התיקייה עם `seq/` ו-`img/`, ואפשר לתת נתיב יחסי כמו `'/v-tech/'`.
- **מבנה:** מסכי הסיפור לפי הסדר, אחד יותר ממספר המעברים, כשהאחרון הוא ההצעה עם כרטיס הערכה. הטקסט של כל מסך נמצא בתוך `.wrap`. לקנבס, לשתי שכבות התאים ולתמונת הסליל אסור שיהיו ילדים של React, כי המנוע מוסיף ומעצב את התוכן שלהם.
- **אחרי ההצעה** צריך לפחות מסך אחד של תוכן (מוצרים קשורים, תחתית), אחרת הערכה לא מספיקה לנחות בכרטיס.
- **דמו:** בתיקייה `proto/react/demo` מריצים `npm install && npm run build`, אחר כך `python3 serve-local.py` בתיקייה `proto`, ופותחים http://localhost:8000/react/demo/dist/index.html. נבדק ב-Playwright, ‏11/11: הרכבה כפולה ב-StrictMode עם worker אחד, גלילה עד הסוף, נחיתת הערכה, פירוק בלי שאריות והרכבה מחדש, טלפון.

## מנוע הפריימים (V-TECH)

- **שמות הקבצים:**
  ```
  seq/<tier>/<a>_<b>_NNN.webp
  seq/runs.json → { "runs": [ { "a": "v1-meet", "b": "v2-why", "n": 40, "box": [x0, y0, x1, y1] }, … ], "frame": [480, 300] }
  frame = round(progress × (n − 1))
  ```
  - כל run הוא מעבר בין שני מסכים.
  - ‏box הוא מלבן החיתוך בתוך הפריים המלא של הרינדור (16:10), בשברים שלו. כל קובץ WebP מכיל רק את החיתוך הזה.
  - במחשב הפריים המלא נמתח לכיסוי המסך (cover). בטלפון האיחוד של כל ה-box נכנס לבמה.
  - הרמות (tiers) אינן רשומות ב-runs.json. אלה התיקיות `seq/<tier>/` השלמות: ‏build-vtech.py מוצא אותן וכותב אותן לתוך הדף (CFG.tiers: ב-`proto` ‏[480], ב-`public` ובדף שפורסם [1600, 2400]).
- **סצנה חיה (three.js):** במקום פריימים אפשר להעביר למנוע `scene`, אובייקט עם `draw(p, view)` ו-`kit(view)`. המנוע שומר על כל השאר: המסכים, הבמה בטלפון וכרטיס הערכה. הסצנה מציירת את התנוחה לפי מיקום הגלילה. כך בנוי EXOTECH GEL.
- **בזמן הקריאה:** כל מסך מחזיק את פריים המפתח שלו כל זמן שקוראים את הטקסט שלו.
- **הציור:**
  - ‏canvas אחד קבוע;
  - פענוח ב-Web Worker בעזרת createImageBitmap;
  - בזיכרון נשאר רק חלון של פריימים סביב המיקום, ועוד פריימי הקצה;
  - רמת האיכות: הקטנה ביותר מבין 2400, ‏1920 ו-1600 שרוחבה גדול או שווה לרוחב הפריים המלא כפי שהוא מצויר × DPR. ה-DPR מוגבל ל-2 במחשב ול-3 בטלפון, שבו הבמה קטנה.
  - ב-iPad ובמכשירים עם 4GB זיכרון ומטה — עד 1600.
  - אין רמה נפרדת לטלפון: הפריים שם קטן יותר, ולכן נבחרת רמה נמוכה יותר.
- **בטלפון (עד 899px; רק ב-V-TECH):**
  - במה קבועה מתחת לכותרת העליונה, בגובה של כ-46svh, וה-3D מתנגן בה;
  - הטקסט נגלל מתחת לבמה;
  - בבלוק ההצעה הבמה נדחפת למעלה.
- **מצבים מיוחדים:**
  - כשמבוקשת הפחתת תנועה — רק פריימי מפתח;
  - ב-Save-Data — כמו בהפחתת תנועה: רק פריימי המפתח, בלי שדה התאים ובלי סליל ה-DNA;
  - בלי JS — במחשב פריים המפתח הראשון כתמונה, ובטלפון תמונת סטילס קטנה ליד כל כותרת.
- **ב-MASK:**
  - הטלפון מתחיל ב-760px, ואין במה: ה-3D עומד בחלון קטן ליד כל כותרת.
  - בטלפון המוצר מצויר בקנבס שנמצא בתוך החלון הזה, ולכן הוא נגלל יחד עם הטקסט, ברזולוציה של המסך (עד פי 3). העשן ברקע נשאר בקנבס הקבוע.
  - בלי WebGL מוצגת תמונת סטילס אחת של הערכה.
- **הרינדור הסופי (21/10):** ‏200 פריימים ב-2400px ‏(Blender, ‏128 דגימות + OIDN), באותם חמישה מעברים ובאותם box כמו `src/hd/render_mac.sh`.
  - ‏`ingest_seq.py` הכין מהם שתי רמות, `seq/2400` ו-`seq/1600`: ‏400 קבצים, כ-11MB, עם runs.json משלהם.
  - הם נמצאים ב-`public/v-tech-system/seq` ובדף V-TECH שפורסם (https://claude.ai/artifact/NdQezU5bikrsuaWVVW5TBK). אפשר לייצר אותם מחדש בעזרת `render_mac.sh`.
  - רמה שלישית, ‏3840px, ברינדור: במחשב עם מסך Retina ‏(DPR 2) הפריים המלא צריך 2880–3840px. כשתהיה מוכנה, רמות העמוד יהיו [2400, 3840].
  - אחרי שמוסיפים את התיקיות (ואת runs.json של הרינדור) מריצים מחדש את build-vtech.py, כי רשימת הרמות נכתבת לתוך הדף בזמן הבנייה.

## כללים

- עברית מימין לשמאל: `dir="rtl"`, ‏`lang="he"`. שמות מוצרים ורכיבים בלטינית לא מתורגמים.
- גופן Rubik בכל מקום, בלי נטוי. לשני עמודי הדוגמה יש אותו סולם טיפוגרפי (עמוד 00 ב-Figma, סעיף 05).
- המוצר מוצג תמיד בצבעי ההדפסה האמיתיים. צבע הקו מופיע רק בסביבה.
- מומחים בעמוד הציבורי: מונוגרמה ועיר בלבד.
- צילומי לפני/אחרי ותמונות של אנשים: רק צילומים אמיתיים, באישור, ולא במאגר הקוד הציבורי.
- מפתחות API נשמרים רק במשתני סביבה.

## מה עוד חסר

- רמת 3840px של V-TECH: רינדור על ה-Mac בעזרת `render_mac.sh`, לבחירת המזמין/ה. הרינדור הסופי ב-2400px כבר בעמוד.
- חיבור טופס הפנייה: הפרטים נשלחים ל-CRM ול-WhatsApp, שכבר מוגדרים אצל המזמין/ה. את החיבור עושים בשלב מאוחר יותר. הטופס כולל שם, מקצוע, דוא״ל, טלפון ותיבת הסכמה לתנאים, שהיא חובה.
- צילומי לפני/אחרי.
- נתוני המומחים.
- ההדפסה על צידי הקופסאות של BIOSPICULE ‏(CELLULAR AGE DEFENSE 2.5%, CELL RENEW 1.5%, MICRO BOOST 10%, DERMA RECOVERY CREAM): ממתינה לקבצים ולמידות במ״מ מהמזמין/ה.
- כתובת משותפת לאתר (Vercel או GitHub Pages): ממתינה לגישה מהמזמין/ה.
- שאלות פתוחות למזמין/ה: האם ב-EXOSIGNAL HAIR יש PDRN בריכוז 2%; האם להשאיר את סליל ה-DNA ומולקולות ה-PDRN ב-V-TECH, ב-EXOTECH GEL וב-EXOSIGNAL HAIR; האם הזהב נמצא ב-pH Normalizer או בפילינג של EXO-NAD.
- «אוקיי» של המזמין/ה על עמוד EXOCELL MASK.
- הצילומים של EXO-NAD כקבצים בגודל מלא, מהמזמין/ה.
- תמונת מוצר אמיתית ל-EXOSIGNAL SPRAY.
