#!/usr/bin/env python3
"""
make_artifact_page.py - build the claude.ai page edition of the WS1.0 coding
instrument (one fragment at a time, practice block, CSV export).

Reads coding_sample.csv (git-ignored) or recovers the fragments from
ws1_survey.html, and writes a single HTML file WITHOUT doctype/html/head/body
(the artifact publisher wraps it). Output goes to --out (default: scratch).
"""
import argparse, csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CODEBOOK = "v1"

PRACTICE = [
    {"text": "The bank says its new AI assistant will let it cut about 300 back-office roles by next year.",
     "rel": "1", "val": "minus"},
    {"text": "Since the hospital started using AI to schedule operating rooms, it has hired two more data analysts to run the system.",
     "rel": "1", "val": "plus"},
    {"text": "Everyone panicked that AI would replace paralegals. Two years on, the firm employs more paralegals than before.",
     "rel": "1", "val": "plus"},
    {"text": "The company laid off 800 people in March, most of them in sales and marketing.",
     "rel": "0", "val": "none"},
    {"text": "The newest model now scores higher than 90% of humans on the bar exam.",
     "rel": "0", "val": "none"},
    {"text": "Was it really the AI, or did management just need an excuse for the layoffs? Honestly, nobody knows yet.",
     "rel": "1", "val": "none"},
    {"text": "AI will wipe out a lot of clerical work, but it will also create a wave of new roles in oversight and maintenance.",
     "rel": "1", "val": "mixed"},
    {"text": "AI is going to change the economy in ways we can't imagine. The real question is where you will stand in the new one.",
     "rel": "0", "val": "none"},
]

I18N = {
 "en": {
  "eyebrow": "WS1.0 · Narrative validation gate",
  "h1": "AI × Jobs Narrative Coding",
  "welcome.h2": "Before you start",
  "welcome.p": "Short fragments (about 50 words) from YouTube videos about AI and work, two quick questions each. All fragments are in English. First 8 practice items with answers, then 300 fragments. About 40–50 minutes; you can close the page and continue later on this device.",
  "rules.title": "Rules",
  "rules.1": "Code alone — no discussing fragments until you finish.",
  "rules.2": "Judge <b>only the words in the fragment</b>, not the video's topic.",
  "rules.3": "One fragment at a time, no going back — your first reading under the rules is what we need.",
  "rules.4": "The order is random and different for every coder.",
  "field.name": "Your name or coder ID",
  "field.ph": "e.g. Anna, Coder_B",
  "consent": "I agree that my coding may be used and published as pseudonymised research data.",
  "english.q": "How comfortably do you read English?",
  "english.pick": "— choose —",
  "english.native": "Native or near-native",
  "english.fluent": "Fluent",
  "english.good": "Good (I read articles without a dictionary)",
  "english.basic": "Basic",
  "err.english": "Please tell us how comfortably you read English.",
  "err.basic": "This task needs comfortable English reading — thank you for your interest!",
  "source.q": "How did you get this link?",
  "source.public": "From a public post",
  "source.researcher": "From the researcher personally",
  "source.other": "Other",
  "err.source": "Please tell us how you got the link.",
  "btn.start": "Start with the practice items",
  "err.name": "Please enter your name or coder ID.",
  "err.consent": "Please confirm the research-data consent.",
  "resume.finished": "This name has already finished all {n} fragments on this device. Resume shows the results again; Start over begins a fresh run.",
  "resume.found": "Saved progress for {name}: {done} of {n} fragments coded{practice}.",
  "resume.practice": " (still in practice)",
  "btn.resume": "Resume",
  "btn.restart": "Start over",
  "ref.summary": "Coding rules — quick reference",
  "ref.rel": "<b>Relevant = Yes</b> only if THIS fragment has an AI/automation word <b>and</b> a job/occupation word <b>and</b> links them. Anything missing → No.",
  "ref.minus": "Alarming (minus)",
  "ref.minus.d": "AI destroys / replaces / shrinks jobs; hiring freezes; wages fall.",
  "ref.plus": "Reassuring (plus)",
  "ref.plus.d": "AI creates / augments jobs — <b>or</b> the destruction fear is overblown or false (debunking, “had to rehire”, “AI costs more than the worker”).",
  "ref.mixed": "Mixed",
  "ref.mixed.d": "Both directions, about equal weight.",
  "ref.none": "Neutral (none)",
  "ref.none.d": "Relevant, but no direction: a question, background, or doubt that AI is the cause.",
  "ref.rules": "<b>Rule 1:</b> debunking destruction = plus, not minus. <b>Rule 2:</b> doubt about the cause = none, not minus.",
  "item.practice": "Practice {i} of {n}",
  "item.fragment": "Fragment {i} of {n}",
  "item.training": "training example",
  "q1.legend": "1. Relevant to “AI affecting jobs”?",
  "q1.help": "Only if the fragment itself has an AI/automation word AND a job/occupation word AND links them.",
  "q1.yes": "Yes (1)",
  "q1.yes.d": "AI word + job word + a link, all in this fragment",
  "q1.no": "No (0)",
  "q1.no.d": "One of the three is missing",
  "q2.legend": "2. Valence (direction)?",
  "q2.help": "Which story does the fragment tell, on balance?",
  "q2.minus": "Alarming (minus)",
  "q2.minus.d": "AI destroys, replaces or shrinks jobs; hiring freezes; wages fall",
  "q2.plus": "Reassuring (plus)",
  "q2.plus.d": "AI creates or augments jobs — or the destruction fear is debunked",
  "q2.mixed": "Mixed",
  "q2.mixed.d": "Both directions, about equal",
  "q2.none": "Neutral / no direction (none)",
  "q2.none.d": "A question, background, or doubt that AI is the cause",
  "btn.next": "Next →",
  "btn.check": "Check answer",
  "btn.nextPractice": "Next practice item →",
  "btn.startMain": "Start the 300 fragments →",
  "hint": "Keys: <kbd>1</kbd>/<kbd>0</kbd> relevance · <kbd>A</kbd><kbd>S</kbd><kbd>D</kbd><kbd>F</kbd> valence · <kbd>Enter</kbd> next",
  "ptext.practice": "Practice · the answer is shown after each item",
  "ptext.coding": "{done} coded · {left} left",
  "ptext.session": "session {m} min",
  "fb.correct": "Correct.",
  "fb.miss": "Not quite.",
  "fb.answer": "Codebook answer: relevant = {rel}{val}. {why}",
  "fb.val": ", valence = {label}",
  "yes": "Yes",
  "no": "No",
  "finish.h2": "All fragments coded — thank you",
  "st.n": "fragments coded",
  "st.rel": "marked relevant",
  "st.min": "minutes",
  "st.med": "median sec / fragment",
  "practice.score": "Practice: {ok} of {n} matched the codebook on the first try.",
  "btn.save": "Save results (CSV)",
  "btn.copy": "Copy results as text",
  "save.unavailable": "Saving a file is not available here — copy the text below and send it to the researcher.",
  "finish.note": "Send the saved file (or the copied text) to the researcher. Please do not edit it.",
  "msg.copied": "Copied — paste it into a message to the researcher.",
  "msg.selectall": "Select all the text below (Ctrl/Cmd+A) and copy it.",
  "msg.saved": "Saved. Send the file to the researcher.",
  "msg.declined": "Not saved — try again, or copy the text below.",
  "msg.wait": "Please wait a moment and try again.",
  "practice.why": [
   "An AI word, a job word, and a claim that AI shrinks the work: relevant, alarming.",
   "AI plus hiring: the fragment says AI created work, so it is reassuring.",
   "It quotes “replace” but argues the fear was wrong. Debunking destruction is plus, not minus (rule 1).",
   "Layoffs, but no AI or automation word anywhere in the fragment. Do not borrow the video's topic.",
   "AI capability only: no job, occupation, hiring or wage outcome is mentioned.",
   "AI and layoffs are both there, but the speaker doubts AI is the cause. Doubt about the cause is none (rule 2).",
   "Destruction and creation stated with roughly equal weight.",
   "AI is present, but there is no occupation and no labour outcome: too vague to count."
  ]
 },
 "ru": {
  "eyebrow": "WS1.0 · Валидационный гейт нарратива",
  "h1": "Кодирование нарратива «ИИ × работа»",
  "welcome.h2": "Перед началом",
  "welcome.p": "Короткие фрагменты (около 50 слов) из YouTube-видео об ИИ и работе, по два быстрых вопроса к каждому. Все фрагменты — на английском. Сначала 8 тренировочных примеров с ответами, затем 300 фрагментов. Около 40–50 минут; страницу можно закрыть и продолжить позже на этом устройстве.",
  "rules.title": "Правила",
  "rules.1": "Работайте в одиночку — не обсуждайте фрагменты, пока не закончите.",
  "rules.2": "Судите <b>только по словам самого фрагмента</b>, а не по теме видео.",
  "rules.3": "По одному фрагменту, без возврата — нам нужно ваше первое прочтение по правилам.",
  "rules.4": "Порядок случайный, у каждого кодировщика свой.",
  "field.name": "Ваше имя или код кодировщика",
  "field.ph": "например, Anna, Coder_B",
  "consent": "Я согласен/согласна, что моя разметка может быть использована и опубликована как обезличенные исследовательские данные.",
  "english.q": "Насколько свободно вы читаете по-английски?",
  "english.pick": "— выберите —",
  "english.native": "Родной или почти родной",
  "english.fluent": "Свободно",
  "english.good": "Хорошо (читаю статьи без словаря)",
  "english.basic": "Базовый",
  "err.english": "Укажите, насколько свободно вы читаете по-английски.",
  "err.basic": "Для этого задания нужно уверенное чтение по-английски — спасибо за интерес!",
  "source.q": "Откуда у вас эта ссылка?",
  "source.public": "Из публичного объявления",
  "source.researcher": "Лично от исследователя",
  "source.other": "Другое",
  "err.source": "Укажите, откуда у вас ссылка.",
  "btn.start": "Начать с тренировочных примеров",
  "err.name": "Введите имя или код кодировщика.",
  "err.consent": "Подтвердите согласие на использование данных.",
  "resume.finished": "Под этим именем на этом устройстве уже размечены все {n} фрагментов. «Продолжить» покажет результаты снова, «Начать заново» запустит новый проход.",
  "resume.found": "Сохранённый прогресс для {name}: размечено {done} из {n}{practice}.",
  "resume.practice": " (ещё в тренировке)",
  "btn.resume": "Продолжить",
  "btn.restart": "Начать заново",
  "ref.summary": "Правила кодирования — краткая справка",
  "ref.rel": "<b>Релевантно = Да</b>, только если в ЭТОМ фрагменте есть слово об ИИ/автоматизации <b>и</b> слово о работе/профессии <b>и</b> они связаны. Чего-то нет → Нет.",
  "ref.minus": "Тревожный (minus)",
  "ref.minus.d": "ИИ уничтожает / заменяет / сокращает рабочие места; найм замораживается; зарплаты падают.",
  "ref.plus": "Успокаивающий (plus)",
  "ref.plus.d": "ИИ создаёт / дополняет рабочие места — <b>или</b> страх разрушения преувеличен или ложен (разоблачение, «пришлось нанимать обратно», «ИИ дороже работника»).",
  "ref.mixed": "Смешанный",
  "ref.mixed.d": "Оба направления, примерно поровну.",
  "ref.none": "Нейтральный (none)",
  "ref.none.d": "Релевантно, но без направления: вопрос, фон или сомнение, что причина — ИИ.",
  "ref.rules": "<b>Правило 1:</b> разоблачение угрозы = plus, а не minus. <b>Правило 2:</b> сомнение в причине = none, а не minus.",
  "item.practice": "Тренировка {i} из {n}",
  "item.fragment": "Фрагмент {i} из {n}",
  "item.training": "учебный пример",
  "q1.legend": "1. Релевантно теме «ИИ влияет на рабочие места»?",
  "q1.help": "Только если в самом фрагменте есть слово об ИИ/автоматизации И слово о работе/профессии И они связаны.",
  "q1.yes": "Да (1)",
  "q1.yes.d": "Слово об ИИ + слово о работе + связь, всё в этом фрагменте",
  "q1.no": "Нет (0)",
  "q1.no.d": "Чего-то из трёх не хватает",
  "q2.legend": "2. Валентность (направление)?",
  "q2.help": "Какую историю в целом рассказывает фрагмент?",
  "q2.minus": "Тревожный (minus)",
  "q2.minus.d": "ИИ уничтожает, заменяет или сокращает рабочие места; найм замораживается; зарплаты падают",
  "q2.plus": "Успокаивающий (plus)",
  "q2.plus.d": "ИИ создаёт или дополняет рабочие места — или страх разрушения разоблачён",
  "q2.mixed": "Смешанный",
  "q2.mixed.d": "Оба направления, примерно поровну",
  "q2.none": "Нейтральный / без направления (none)",
  "q2.none.d": "Вопрос, фон или сомнение, что причина — ИИ",
  "btn.next": "Дальше →",
  "btn.check": "Проверить ответ",
  "btn.nextPractice": "Следующий пример →",
  "btn.startMain": "Начать 300 фрагментов →",
  "hint": "Клавиши: <kbd>1</kbd>/<kbd>0</kbd> релевантность · <kbd>A</kbd><kbd>S</kbd><kbd>D</kbd><kbd>F</kbd> валентность · <kbd>Enter</kbd> дальше",
  "ptext.practice": "Тренировка · ответ показывается после каждого примера",
  "ptext.coding": "размечено {done} · осталось {left}",
  "ptext.session": "сессия {m} мин",
  "fb.correct": "Верно.",
  "fb.miss": "Не совсем.",
  "fb.answer": "Ответ по рубрике: релевантно = {rel}{val}. {why}",
  "fb.val": ", валентность = {label}",
  "yes": "Да",
  "no": "Нет",
  "finish.h2": "Все фрагменты размечены — спасибо",
  "st.n": "фрагментов размечено",
  "st.rel": "отмечено релевантными",
  "st.min": "минут",
  "st.med": "медиана сек / фрагмент",
  "practice.score": "Тренировка: {ok} из {n} совпали с рубрикой с первой попытки.",
  "btn.save": "Сохранить результаты (CSV)",
  "btn.copy": "Скопировать результаты как текст",
  "save.unavailable": "Сохранение файла здесь недоступно — скопируйте текст ниже и отправьте исследователю.",
  "finish.note": "Отправьте сохранённый файл (или скопированный текст) исследователю. Пожалуйста, не редактируйте его.",
  "msg.copied": "Скопировано — вставьте в сообщение исследователю.",
  "msg.selectall": "Выделите весь текст ниже (Ctrl/Cmd+A) и скопируйте.",
  "msg.saved": "Сохранено. Отправьте файл исследователю.",
  "msg.declined": "Не сохранено — попробуйте ещё раз или скопируйте текст ниже.",
  "msg.wait": "Подождите немного и попробуйте снова.",
  "practice.why": [
   "Есть слово об ИИ, слово о работе и утверждение, что ИИ сокращает работу: релевантно, тревожно.",
   "ИИ плюс найм: фрагмент говорит, что ИИ создал работу, — значит, успокаивающий.",
   "Цитирует «replace», но утверждает, что страх был напрасным. Разоблачение угрозы — plus, а не minus (правило 1).",
   "Увольнения, но во фрагменте нет ни одного слова об ИИ или автоматизации. Тему видео не подставляем.",
   "Только возможности ИИ: ни профессии, ни найма, ни зарплаты, ни другого исхода для работы.",
   "ИИ и увольнения есть, но говорящий сомневается, что причина — ИИ. Сомнение в причине = none (правило 2).",
   "Разрушение и созидание примерно с равным весом.",
   "ИИ есть, но нет ни профессии, ни исхода для работы: слишком размыто."
  ]
 },
 "he": {
  "eyebrow": "WS1.0 · שער אימות הנרטיב",
  "h1": "קידוד נרטיב «בינה מלאכותית × עבודה»",
  "welcome.h2": "לפני שמתחילים",
  "welcome.p": "קטעים קצרים (כ־50 מילים) מסרטוני יוטיוב על בינה מלאכותית ועבודה, שתי שאלות מהירות לכל קטע. כל הקטעים באנגלית. תחילה 8 פריטי תרגול עם תשובות, אחר כך 300 קטעים. כ־40–50 דקות; אפשר לסגור את הדף ולהמשיך מאוחר יותר במכשיר הזה.",
  "rules.title": "כללים",
  "rules.1": "עבדו לבד — בלי לדון בקטעים עד שתסיימו.",
  "rules.2": "שפטו <b>רק לפי המילים שבקטע עצמו</b>, לא לפי נושא הסרטון.",
  "rules.3": "קטע אחד בכל פעם, בלי לחזור אחורה — הקריאה הראשונה שלכם לפי הכללים היא מה שאנחנו צריכים.",
  "rules.4": "הסדר אקראי ושונה אצל כל מקודד.",
  "field.name": "השם שלכם או מזהה מקודד",
  "field.ph": "לדוגמה: Anna, Coder_B",
  "consent": "אני מסכים/ה שהקידוד שלי ישמש ויפורסם כנתוני מחקר בשם בדוי.",
  "english.q": "עד כמה בנוחות אתם קוראים אנגלית?",
  "english.pick": "— בחרו —",
  "english.native": "שפת אם או קרוב לזה",
  "english.fluent": "שוטף",
  "english.good": "טוב (קורא/ת מאמרים בלי מילון)",
  "english.basic": "בסיסי",
  "err.english": "נא לציין עד כמה בנוחות אתם קוראים אנגלית.",
  "err.basic": "המשימה דורשת קריאה נוחה באנגלית — תודה על העניין!",
  "source.q": "איך הגיע אליכם הקישור?",
  "source.public": "מפרסום פומבי",
  "source.researcher": "ישירות מהחוקר",
  "source.other": "אחר",
  "err.source": "נא לציין איך הגיע אליכם הקישור.",
  "btn.start": "להתחיל בפריטי התרגול",
  "err.name": "נא להזין שם או מזהה מקודד.",
  "err.consent": "נא לאשר את ההסכמה לשימוש בנתונים.",
  "resume.finished": "שם זה כבר סיים את כל {n} הקטעים במכשיר הזה. «להמשיך» יציג שוב את התוצאות, «להתחיל מחדש» יפתח מעבר חדש.",
  "resume.found": "התקדמות שמורה עבור {name}: קודדו {done} מתוך {n}{practice}.",
  "resume.practice": " (עדיין בתרגול)",
  "btn.resume": "להמשיך",
  "btn.restart": "להתחיל מחדש",
  "ref.summary": "כללי הקידוד — תזכורת קצרה",
  "ref.rel": "<b>רלוונטי = כן</b> רק אם בקטע הזה עצמו יש מילה של AI/אוטומציה <b>וגם</b> מילה של עבודה/מקצוע <b>וגם</b> חיבור ביניהן. אם משהו חסר → לא.",
  "ref.minus": "מדאיג (minus)",
  "ref.minus.d": "AI מחסל / מחליף / מצמצם משרות; הגיוס מוקפא; השכר יורד.",
  "ref.plus": "מרגיע (plus)",
  "ref.plus.d": "AI יוצר / מעצים משרות — <b>או</b> שהפחד מהחיסול מוגזם או שגוי (הפרכה, «נאלצו להעסיק מחדש», «AI עולה יותר מהעובד»).",
  "ref.mixed": "מעורב",
  "ref.mixed.d": "שני הכיוונים, בערך שווה.",
  "ref.none": "ניטרלי (none)",
  "ref.none.d": "רלוונטי, אבל בלי כיוון: שאלה, רקע, או ספק ש-AI הוא הסיבה.",
  "ref.rules": "<b>כלל 1:</b> הפרכת החיסול = plus, לא minus. <b>כלל 2:</b> ספק לגבי הסיבה = none, לא minus.",
  "item.practice": "תרגול {i} מתוך {n}",
  "item.fragment": "קטע {i} מתוך {n}",
  "item.training": "דוגמת אימון",
  "q1.legend": "1. רלוונטי לנושא «AI משפיע על משרות»?",
  "q1.help": "רק אם בקטע עצמו יש מילה של AI/אוטומציה וגם מילה של עבודה/מקצוע וגם חיבור ביניהן.",
  "q1.yes": "כן (1)",
  "q1.yes.d": "מילת AI + מילת עבודה + חיבור, הכול בקטע הזה",
  "q1.no": "לא (0)",
  "q1.no.d": "אחד משלושת אלה חסר",
  "q2.legend": "2. כיוון (ערכיות)?",
  "q2.help": "בסך הכול, איזה סיפור הקטע מספר?",
  "q2.minus": "מדאיג (minus)",
  "q2.minus.d": "AI מחסל, מחליף או מצמצם משרות; הגיוס מוקפא; השכר יורד",
  "q2.plus": "מרגיע (plus)",
  "q2.plus.d": "AI יוצר או מעצים משרות — או שהפחד מהחיסול הופרך",
  "q2.mixed": "מעורב",
  "q2.mixed.d": "שני הכיוונים, בערך שווה",
  "q2.none": "ניטרלי / בלי כיוון (none)",
  "q2.none.d": "שאלה, רקע, או ספק ש-AI הוא הסיבה",
  "btn.next": "הבא ←",
  "btn.check": "בדיקת תשובה",
  "btn.nextPractice": "פריט התרגול הבא ←",
  "btn.startMain": "להתחיל את 300 הקטעים ←",
  "hint": "מקשים: <kbd>1</kbd>/<kbd>0</kbd> רלוונטיות · <kbd>A</kbd><kbd>S</kbd><kbd>D</kbd><kbd>F</kbd> כיוון · <kbd>Enter</kbd> הבא",
  "ptext.practice": "תרגול · התשובה מוצגת אחרי כל פריט",
  "ptext.coding": "{done} קודדו · {left} נותרו",
  "ptext.session": "מפגש {m} דק׳",
  "fb.correct": "נכון.",
  "fb.miss": "לא בדיוק.",
  "fb.answer": "התשובה לפי ספר הקודים: רלוונטי = {rel}{val}. {why}",
  "fb.val": ", כיוון = {label}",
  "yes": "כן",
  "no": "לא",
  "finish.h2": "כל הקטעים קודדו — תודה",
  "st.n": "קטעים קודדו",
  "st.rel": "סומנו כרלוונטיים",
  "st.min": "דקות",
  "st.med": "חציון שניות לקטע",
  "practice.score": "תרגול: {ok} מתוך {n} תאמו את ספר הקודים בניסיון הראשון.",
  "btn.save": "שמירת התוצאות (CSV)",
  "btn.copy": "העתקת התוצאות כטקסט",
  "save.unavailable": "שמירת קובץ אינה זמינה כאן — העתיקו את הטקסט שלמטה ושלחו לחוקר.",
  "finish.note": "שלחו את הקובץ השמור (או את הטקסט שהועתק) לחוקר. נא לא לערוך אותו.",
  "msg.copied": "הועתק — הדביקו בהודעה לחוקר.",
  "msg.selectall": "סמנו את כל הטקסט שלמטה (Ctrl/Cmd+A) והעתיקו.",
  "msg.saved": "נשמר. שלחו את הקובץ לחוקר.",
  "msg.declined": "לא נשמר — נסו שוב, או העתיקו את הטקסט שלמטה.",
  "msg.wait": "נא להמתין רגע ולנסות שוב.",
  "practice.why": [
   "יש מילת AI, מילת עבודה, וטענה ש-AI מצמצם את העבודה: רלוונטי, מדאיג.",
   "AI ועוד גיוס: הקטע אומר ש-AI יצר עבודה, ולכן הוא מרגיע.",
   "הקטע מצטט «replace» אבל טוען שהפחד היה שגוי. הפרכת החיסול היא plus, לא minus (כלל 1).",
   "פיטורים, אבל אין בקטע אף מילה של AI או אוטומציה. לא שואלים את נושא הסרטון.",
   "יכולת של AI בלבד: לא מוזכרת שום משרה, מקצוע, גיוס או שכר.",
   "גם AI וגם פיטורים נמצאים, אבל הדובר מפקפק ש-AI הוא הסיבה. ספק לגבי הסיבה = none (כלל 2).",
   "חיסול ויצירה במשקל שווה בערך.",
   "AI נמצא, אבל אין מקצוע ואין תוצאה תעסוקתית: מעורפל מדי כדי להיחשב."
  ]
 }
}

TEMPLATE = r'''<title>WS1.0 Narrative Coding</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
:root{--ground:#F4F5F8;--surface:#FFFFFF;--ink:#171A21;--muted:#5B6270;--line:#E1E4EA;--accent:#0E6F6A;--accent-soft:#E6F2F1;--accent-ink:#FFFFFF;--warn:#7A4E00;--warn-soft:#FFF3DA;--ok:#1F6B3A;--ok-soft:#E4F3E9;--focus:#0E6F6A}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ground:#121417;--surface:#1A1D23;--ink:#E7E9EE;--muted:#9AA3B2;--line:#2A2F38;--accent:#4FB3AC;--accent-soft:#173331;--accent-ink:#0B1413;--warn:#E7BC66;--warn-soft:#2E2510;--ok:#7CC894;--ok-soft:#14291C;--focus:#4FB3AC}}
:root[data-theme="dark"]{--ground:#121417;--surface:#1A1D23;--ink:#E7E9EE;--muted:#9AA3B2;--line:#2A2F38;--accent:#4FB3AC;--accent-soft:#173331;--accent-ink:#0B1413;--warn:#E7BC66;--warn-soft:#2E2510;--ok:#7CC894;--ok-soft:#14291C;--focus:#4FB3AC}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;padding-inline:16px;padding-block:0 40px;margin:0}
.wrap{max-width:680px;margin:0 auto}
.top{padding-block:22px 6px}
.eyebrow{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}
h1{font-size:20px;line-height:1.2;margin:4px 0 0;font-weight:650;text-wrap:balance}
h2{font-size:18px;line-height:1.25;margin:0 0 10px;font-weight:650;text-wrap:balance}
.progress{position:sticky;top:env(safe-area-inset-top,0px);background:var(--ground);padding-block:10px 8px;z-index:2}
.bar{height:6px;background:var(--line);border-radius:6px;overflow:hidden}
.fill{height:100%;width:0;background:var(--accent);border-radius:6px;transition:width .25s ease}
.ptext{display:flex;justify-content:space-between;gap:12px;font-size:12px;color:var(--muted);margin-top:6px;font-variant-numeric:tabular-nums}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:22px 20px;margin-block:12px}
.rules{background:var(--ground);border-radius:10px;padding:12px 14px;font-size:13.5px;line-height:1.6;margin-block:12px}
.rules b{font-weight:650}
.note{font-size:13px;color:var(--muted);line-height:1.5}
label.field{display:block;font-size:13px;font-weight:600;margin-top:14px}
input[type=text]{width:100%;padding:11px 12px;border:1.5px solid var(--line);border-radius:10px;font:inherit;background:var(--surface);color:var(--ink);margin-top:6px}
input[type=text]:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
select{width:100%;padding:11px 12px;border:1.5px solid var(--line);border-radius:10px;font:inherit;background:var(--surface);color:var(--ink);margin-top:6px}
select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.check{display:flex;gap:10px;align-items:flex-start;font-size:14px;margin-top:14px;cursor:pointer}
.check input{margin-top:3px;accent-color:var(--accent)}
.frag{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin-block:12px 14px}
.frag .eyebrow{display:flex;justify-content:space-between;gap:10px}
.frag .fid{font:11px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:0;text-transform:none;font-weight:400}
.frag p{font-family:"Source Serif 4",Georgia,"Times New Roman",serif;font-size:17px;line-height:1.6;border-left:3px solid var(--accent);padding-left:14px;margin:10px 0 0}
fieldset.q{border:0;padding:0;margin:14px 0 0;min-width:0}
fieldset.q legend{font-weight:650;font-size:15px;padding:0}
.help{font-size:13px;color:var(--muted);margin:4px 0 10px;line-height:1.5}
.opts{display:grid;gap:8px}
.opt{position:relative;display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border:1.5px solid var(--line);border-radius:10px;background:var(--surface);cursor:pointer;transition:border-color .12s,background .12s}
.opt input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
.opt:hover{border-color:var(--accent)}
.opt.on,.opt:has(input:checked){border-color:var(--accent);background:var(--accent-soft)}
.opt:has(input:focus-visible){outline:2px solid var(--focus);outline-offset:2px}
.opt b{display:block;font-size:15px;font-weight:600}
.opt small{display:block;color:var(--muted);font-size:12.5px;margin-top:2px;line-height:1.4}
.key{font:11px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:3px 5px;margin-inline-start:auto;align-self:center;flex-shrink:0}
.toprow{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.langs{display:flex;gap:2px;background:var(--line);border-radius:10px;padding:3px;flex-shrink:0}
.lang{appearance:none;border:0;background:transparent;padding:6px 10px;border-radius:8px;font:inherit;font-size:13px;cursor:pointer;color:var(--muted)}
.lang.on{background:var(--surface);color:var(--ink);font-weight:650}
.lang:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.actions{display:flex;gap:10px;align-items:center;margin-top:16px;flex-wrap:wrap}
.btn{appearance:none;border:0;border-radius:10px;padding:12px 18px;font:inherit;font-weight:650;cursor:pointer;background:var(--accent);color:var(--accent-ink)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn.ghost{background:transparent;border:1.5px solid var(--line);color:var(--ink)}
.btn:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.feedback{border-radius:10px;padding:12px 14px;margin-top:14px;font-size:14px;line-height:1.55}
.feedback.ok{background:var(--ok-soft);color:var(--ok)}
.feedback.miss{background:var(--warn-soft);color:var(--warn)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-block:12px}
.stat{background:var(--ground);border-radius:10px;padding:10px 12px}
.stat b{display:block;font-size:20px;font-variant-numeric:tabular-nums;font-weight:650}
.stat span{font-size:12px;color:var(--muted)}
textarea{width:100%;min-height:150px;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;border:1.5px solid var(--line);border-radius:10px;padding:10px;background:var(--ground);color:var(--ink);margin-top:8px}
details.ref{margin-block:6px 4px;font-size:13px}
details.ref summary{cursor:pointer;color:var(--accent);font-weight:600;list-style:none}
details.ref summary::-webkit-details-marker{display:none}
details.ref .rules{margin-top:8px}
.ref table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}
.ref td{padding:4px 6px;border-top:1px solid var(--line);vertical-align:top}
.ref td:first-child{white-space:nowrap;font-weight:650}
.msg{font-size:13px;margin-top:10px;min-height:1.2em}
.msg.err{color:var(--warn)}
.log{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--muted);margin-top:12px;word-break:break-word}
kbd{font:11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;border:1px solid var(--line);border-radius:4px;padding:1px 4px}
@media (max-width:420px){.frag p{font-size:16px}h1{font-size:18px}.card{padding:18px 16px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<div class="wrap">
<header class="top"><div class="toprow">
  <div><div class="eyebrow" data-i18n="eyebrow"></div><h1 data-i18n="h1"></h1></div>
  <div class="langs" role="group" aria-label="Language / Язык / שפה">
    <button type="button" class="lang" id="lang-en" data-lang="en" lang="en">English</button>
    <button type="button" class="lang" id="lang-ru" data-lang="ru" lang="ru">Русский</button>
    <button type="button" class="lang" id="lang-he" data-lang="he" lang="he">עברית</button>
  </div>
</div></header>

<div class="progress" id="progressWrap" hidden>
  <div class="bar"><div class="fill" id="pfill"></div></div>
  <div class="ptext"><span id="ptext-left"></span><span id="ptext-right"></span></div>
</div>

<!-- WELCOME -->
<section id="s-welcome" class="card">
  <h2 data-i18n="welcome.h2"></h2>
  <p data-i18n="welcome.p"></p>
  <div class="rules">
    <b data-i18n="rules.title"></b><br>
    • <span data-i18n="rules.1"></span><br>
    • <span data-i18n-html="rules.2"></span><br>
    • <span data-i18n="rules.3"></span><br>
    • <span data-i18n="rules.4"></span>
  </div>
  <label class="field" for="coder-name" data-i18n="field.name"></label>
  <input type="text" id="coder-name" data-i18n-ph="field.ph" autocomplete="off" maxlength="60">
  <label class="field" for="english-level" data-i18n="english.q"></label>
  <select id="english-level">
    <option value="" data-i18n="english.pick"></option>
    <option value="native" data-i18n="english.native"></option>
    <option value="fluent" data-i18n="english.fluent"></option>
    <option value="good" data-i18n="english.good"></option>
    <option value="basic" data-i18n="english.basic"></option>
  </select>
  <label class="field" for="source" data-i18n="source.q"></label>
  <select id="source">
    <option value="" data-i18n="english.pick"></option>
    <option value="public" data-i18n="source.public"></option>
    <option value="researcher" data-i18n="source.researcher"></option>
    <option value="other" data-i18n="source.other"></option>
  </select>
  <label class="check" for="consent-ok"><input type="checkbox" id="consent-ok"><span data-i18n="consent"></span></label>
  <div class="actions">
    <button class="btn" id="btn-start" type="button" data-i18n="btn.start"></button>
  </div>
  <div class="msg" id="welcome-msg"></div>
  <div id="resume" hidden>
    <p class="note" id="resume-text"></p>
    <div class="actions">
      <button class="btn" id="btn-resume" type="button" data-i18n="btn.resume"></button>
      <button class="btn ghost" id="btn-restart" type="button" data-i18n="btn.restart"></button>
    </div>
  </div>
</section>

<!-- ITEM (practice + coding) -->
<section id="s-item" hidden>
  <details class="ref">
    <summary data-i18n="ref.summary"></summary>
    <div class="rules">
      <span data-i18n-html="ref.rel"></span>
      <table>
        <tr><td data-i18n="ref.minus"></td><td data-i18n-html="ref.minus.d"></td></tr>
        <tr><td data-i18n="ref.plus"></td><td data-i18n-html="ref.plus.d"></td></tr>
        <tr><td data-i18n="ref.mixed"></td><td data-i18n-html="ref.mixed.d"></td></tr>
        <tr><td data-i18n="ref.none"></td><td data-i18n-html="ref.none.d"></td></tr>
      </table>
      <span data-i18n-html="ref.rules"></span>
    </div>
  </details>

  <div class="frag">
    <div class="eyebrow"><span id="item-label"></span><span class="fid" id="item-id"></span></div>
    <p id="item-text" dir="ltr" lang="en"></p>
  </div>

  <fieldset class="q" id="q1">
    <legend data-i18n="q1.legend"></legend>
    <div class="help" data-i18n="q1.help"></div>
    <div class="opts">
      <label class="opt" for="q1-yes"><input type="radio" name="q1" id="q1-yes" value="1"><span><b data-i18n="q1.yes"></b><small data-i18n="q1.yes.d"></small></span><span class="key">1</span></label>
      <label class="opt" for="q1-no"><input type="radio" name="q1" id="q1-no" value="0"><span><b data-i18n="q1.no"></b><small data-i18n="q1.no.d"></small></span><span class="key">0</span></label>
    </div>
  </fieldset>

  <fieldset class="q" id="q2" hidden>
    <legend data-i18n="q2.legend"></legend>
    <div class="help" data-i18n="q2.help"></div>
    <div class="opts">
      <label class="opt" for="q2-minus"><input type="radio" name="q2" id="q2-minus" value="minus"><span><b data-i18n="q2.minus"></b><small data-i18n="q2.minus.d"></small></span><span class="key">A</span></label>
      <label class="opt" for="q2-plus"><input type="radio" name="q2" id="q2-plus" value="plus"><span><b data-i18n="q2.plus"></b><small data-i18n="q2.plus.d"></small></span><span class="key">S</span></label>
      <label class="opt" for="q2-mixed"><input type="radio" name="q2" id="q2-mixed" value="mixed"><span><b data-i18n="q2.mixed"></b><small data-i18n="q2.mixed.d"></small></span><span class="key">D</span></label>
      <label class="opt" for="q2-none"><input type="radio" name="q2" id="q2-none" value="none"><span><b data-i18n="q2.none"></b><small data-i18n="q2.none.d"></small></span><span class="key">F</span></label>
    </div>
  </fieldset>

  <div class="feedback" id="feedback" hidden></div>
  <div class="actions">
    <button class="btn" id="btn-next" type="button" disabled></button>
    <span class="note" id="item-hint" data-i18n-html="hint"></span>
  </div>
</section>

<!-- FINISH -->
<section id="s-finish" class="card" hidden>
  <h2 data-i18n="finish.h2"></h2>
  <div class="stats">
    <div class="stat"><b id="st-n">0</b><span data-i18n="st.n"></span></div>
    <div class="stat"><b id="st-rel">0</b><span data-i18n="st.rel"></span></div>
    <div class="stat"><b id="st-min">0</b><span data-i18n="st.min"></span></div>
    <div class="stat"><b id="st-med">0</b><span data-i18n="st.med"></span></div>
  </div>
  <p class="note" id="practice-score"></p>
  <div class="actions">
    <button class="btn" id="btn-save" type="button" hidden data-i18n="btn.save"></button>
    <button class="btn ghost" id="btn-copy" type="button" data-i18n="btn.copy"></button>
  </div>
  <div class="msg" id="finish-msg"></div>
  <p class="note" id="save-unavailable" hidden data-i18n="save.unavailable"></p>
  <p class="note" data-i18n="finish.note"></p>
  <textarea id="csv-box" dir="ltr" readonly spellcheck="false" aria-label="Results as CSV text"></textarea>
  <div class="log" id="session-log" dir="ltr"></div>
</section>
</div>

<script>
const FRAGMENTS = __FRAGMENTS_JSON__;
const PRACTICE = __PRACTICE_JSON__;
const I18N = __I18N_JSON__;
let LANG = "en";
const CODEBOOK = "__CODEBOOK__";
const N = FRAGMENTS.length;
const $ = id => document.getElementById(id);
const use = name => (window.claude && typeof window.claude.use === "function")
  ? window.claude.use(name).catch(() => null) : Promise.resolve(null);

let S = blank();
let q1 = null, q2 = null, itemStart = 0, checked = false, sessionTimer = null;

function blank() { return { coder: "", mode: "welcome", pIdx: 0, cIdx: 0, order: [], answers: [], practice: [], startedAt: null, finishedAt: null, seed: 0, lang: LANG, english: "", source: "" }; }
function t(k, vars) { let v = (I18N[LANG] && I18N[LANG][k] !== undefined) ? I18N[LANG][k] : I18N.en[k]; if (v === undefined) return k; if (vars) for (const x in vars) v = v.split("{" + x + "}").join(vars[x]); return v; }
function why(i) { const a = (I18N[LANG] && I18N[LANG]["practice.why"]) || I18N.en["practice.why"]; return a[i] || ""; }
let lastFb = null;
function nextLabel() { if (S.mode !== "practice") return t("btn.next"); if (!checked) return t("btn.check"); return (S.pIdx + 1 < PRACTICE.length) ? t("btn.nextPractice") : t("btn.startMain"); }
function refreshDynamic() {
  if (!$("s-item").hidden) {
    const practice = S.mode === "practice";
    $("item-label").textContent = practice ? t("item.practice", { i: S.pIdx + 1, n: PRACTICE.length }) : t("item.fragment", { i: S.cIdx + 1, n: N });
    if (practice) $("item-id").textContent = t("item.training");
    $("ptext-left").textContent = practice ? t("ptext.practice") : t("ptext.coding", { done: S.cIdx, left: N - S.cIdx });
    $("btn-next").textContent = nextLabel();
    if (lastFb && !$("feedback").hidden) renderFeedback();
  }
  if (!$("s-finish").hidden) $("practice-score").textContent = t("practice.score", { ok: S.practice.filter(p => p.ok).length, n: PRACTICE.length });
  $("welcome-msg").textContent = ""; $("finish-msg").textContent = ""; $("resume").hidden = true;
}
function setLang(l, fromUser) {
  LANG = I18N[l] ? l : "en"; S.lang = LANG;
  try { localStorage.setItem("ws1v2_lang", LANG); } catch (e) {}
  document.documentElement.lang = LANG; document.documentElement.dir = (LANG === "he") ? "rtl" : "ltr";
  document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-html]").forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
  document.querySelectorAll("[data-i18n-ph]").forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  document.querySelectorAll(".lang").forEach(b => b.classList.toggle("on", b.dataset.lang === LANG));
  refreshDynamic(); if (fromUser && S.coder) persist();
}
document.querySelectorAll(".lang").forEach(b => b.addEventListener("click", () => setLang(b.dataset.lang, true)));
function guessLang() { try { const saved = localStorage.getItem("ws1v2_lang"); if (saved && I18N[saved]) return saved; } catch (e) {} const nl = ((navigator.languages && navigator.languages[0]) || navigator.language || "en").toLowerCase(); if (nl.startsWith("ru")) return "ru"; if (nl.startsWith("he") || nl.startsWith("iw")) return "he"; return "en"; }
// same hash + LCG as ws1_survey.html / build_form.gs -> identical order for the same coder name
function hashStr(s) { let h = 0; for (let i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; } return Math.abs(h); }
function seededShuffle(arr, seed) {
  let s = seed; const rand = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
  const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a;
}
const key = name => "ws1v2_" + name;
function persist() { try { localStorage.setItem(key(S.coder), JSON.stringify(S)); localStorage.setItem("ws1v2_last", S.coder); } catch (e) {} }
function loadSaved(name) { try { const r = localStorage.getItem(key(name)); return r ? JSON.parse(r) : null; } catch (e) { return null; } }
function safeName(s) { return (s.replace(/[^A-Za-z0-9_\-]+/g, "_").replace(/^_+|_+$/g, "")) || "coder"; }

function show(id) {
  ["s-welcome", "s-item", "s-finish"].forEach(s => { $(s).hidden = (s !== id); });
  $("progressWrap").hidden = (id !== "s-item");
}
function setMsg(id, text, err) { const el = $(id); el.textContent = text || ""; el.className = "msg" + (err ? " err" : ""); }

// ---------- welcome ----------
$("btn-start").addEventListener("click", () => {
  const name = $("coder-name").value.trim();
  if (!name) { setMsg("welcome-msg", t("err.name"), true); return; }
  const lvl = $("english-level").value, src = $("source").value;
  if (!lvl) { setMsg("welcome-msg", t("err.english"), true); return; }
  if (lvl === "basic") { setMsg("welcome-msg", t("err.basic"), true); return; }
  if (!src) { setMsg("welcome-msg", t("err.source"), true); return; }
  if (!$("consent-ok").checked) { setMsg("welcome-msg", t("err.consent"), true); return; }
  setMsg("welcome-msg", "");
  const saved = loadSaved(name);
  if (saved && saved.mode !== "welcome") {
    const done = saved.mode === "finish" ? N : (saved.mode === "coding" ? saved.cIdx : 0);
    $("resume-text").textContent = saved.mode === "finish"
      ? t("resume.finished", { n: N })
      : t("resume.found", { name: name, done: done, n: N, practice: (saved.mode === "practice" ? t("resume.practice") : "") });
    $("resume").hidden = false;
    $("btn-resume").onclick = () => { S = saved; $("resume").hidden = true; if (S.lang) setLang(S.lang, false); resume(); };
    $("btn-restart").onclick = () => { $("resume").hidden = true; begin(name, lvl, src); };
    return;
  }
  begin(name, lvl, src);
});
function begin(name, lvl, src) {
  S = blank(); S.coder = name; S.seed = hashStr(name); S.lang = LANG; S.english = lvl || ""; S.source = src || "";
  S.order = seededShuffle(Array.from({ length: N }, (_, i) => i), S.seed);
  S.mode = "practice"; persist(); resume();
}
function resume() {
  if (S.mode === "finish") { finish(); return; }
  show("s-item"); startSessionClock(); render();
}

// ---------- item screen ----------
function resetChoices() {
  q1 = null; q2 = null; checked = false;
  document.querySelectorAll('input[name="q1"], input[name="q2"]').forEach(i => { i.checked = false; });
  document.querySelectorAll(".opt").forEach(o => o.classList.remove("on"));
  $("q2").hidden = true; $("feedback").hidden = true; $("feedback").textContent = "";
  $("btn-next").disabled = true;
  lastFb = null; $("btn-next").textContent = nextLabel();
}
function render() {
  const practice = S.mode === "practice";
  let item, label, id;
  if (practice) { item = PRACTICE[S.pIdx]; label = t("item.practice", { i: S.pIdx + 1, n: PRACTICE.length }); id = t("item.training"); }
  else { item = FRAGMENTS[S.order[S.cIdx]]; label = t("item.fragment", { i: S.cIdx + 1, n: N }); id = item.id; }
  $("item-label").textContent = label; $("item-id").textContent = id; $("item-text").textContent = item.text;
  resetChoices();
  const frac = practice ? S.pIdx / PRACTICE.length : S.cIdx / N;
  $("pfill").style.width = (frac * 100).toFixed(1) + "%";
  $("ptext-left").textContent = practice ? t("ptext.practice") : t("ptext.coding", { done: S.cIdx, left: N - S.cIdx });
  itemStart = Date.now();
  window.scrollTo({ top: 0, behavior: "auto" });
}
function pickQ1(v) {
  q1 = v; $("q1-" + (v === "1" ? "yes" : "no")).checked = true;
  document.querySelectorAll("#q1 .opt").forEach(o => o.classList.toggle("on", o.htmlFor === "q1-" + (v === "1" ? "yes" : "no")));
  if (v === "1") {
    q2 = null; $("q2").hidden = false;
    document.querySelectorAll('input[name="q2"]').forEach(i => { i.checked = false; });
    document.querySelectorAll("#q2 .opt").forEach(o => o.classList.remove("on"));
  } else { q2 = "none"; $("q2").hidden = true; }
  if (checked) { checked = false; lastFb = null; $("feedback").hidden = true; $("btn-next").textContent = nextLabel(); }
  updateNext();
}
function pickQ2(v) {
  q2 = v; $("q2-" + v).checked = true;
  document.querySelectorAll("#q2 .opt").forEach(o => o.classList.toggle("on", o.htmlFor === "q2-" + v));
  if (checked) { checked = false; lastFb = null; $("feedback").hidden = true; $("btn-next").textContent = nextLabel(); }
  updateNext();
}
function updateNext() { $("btn-next").disabled = !(q1 !== null && q2 !== null); }
document.querySelectorAll('input[name="q1"]').forEach(i => i.addEventListener("change", () => pickQ1(i.value)));
document.querySelectorAll('input[name="q2"]').forEach(i => i.addEventListener("change", () => pickQ2(i.value)));

function renderFeedback() {
  const it = PRACTICE[lastFb.i]; const fb = $("feedback");
  fb.className = "feedback " + (lastFb.ok ? "ok" : "miss");
  fb.textContent = (lastFb.ok ? t("fb.correct") : t("fb.miss")) + " " + t("fb.answer", { rel: (it.rel === "1" ? t("yes") : t("no")), val: (it.rel === "1" ? t("fb.val", { label: t("q2." + it.val) }) : ""), why: why(lastFb.i) });
  fb.hidden = false;
}
function showFeedback() {
  const it = PRACTICE[S.pIdx];
  const ok = (q1 === it.rel) && (it.rel === "0" ? true : q2 === it.val);
  lastFb = { i: S.pIdx, ok: ok }; renderFeedback();
  S.practice.push({ i: S.pIdx, rel: q1, val: q2, ok: ok });
}
$("btn-next").addEventListener("click", () => {
  if (q1 === null || q2 === null) return;
  if (S.mode === "practice") {
    if (!checked) { showFeedback(); checked = true; $("btn-next").textContent = nextLabel(); persist(); return; }
    S.pIdx++;
    if (S.pIdx >= PRACTICE.length) { S.mode = "coding"; S.cIdx = 0; S.answers = []; S.startedAt = new Date().toISOString(); }
    persist(); render(); return;
  }
  const f = FRAGMENTS[S.order[S.cIdx]];
  S.answers.push({ frag_id: f.id, rel: q1, val: q2, position: S.cIdx + 1, secs: Math.max(1, Math.round((Date.now() - itemStart) / 1000)) });
  S.cIdx++;
  if (S.cIdx >= N) { S.mode = "finish"; S.finishedAt = new Date().toISOString(); persist(); finish(); return; }
  persist(); render();
});
function startSessionClock() {
  if (sessionTimer) return;
  const tick = () => {
    if ($("s-item").hidden) return;
    const from = S.startedAt ? Date.parse(S.startedAt) : null;
    $("ptext-right").textContent = from ? t("ptext.session", { m: Math.max(0, Math.round((Date.now() - from) / 60000)) }) : "";
  };
  tick(); sessionTimer = setInterval(tick, 30000);
}
document.addEventListener("keydown", e => {
  if ($("s-item").hidden || e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === "1" || k === "y") pickQ1("1");
  else if (k === "0" || k === "2" || k === "n") pickQ1("0");
  else if (q1 === "1" && k === "a") pickQ2("minus");
  else if (q1 === "1" && k === "s") pickQ2("plus");
  else if (q1 === "1" && k === "d") pickQ2("mixed");
  else if (q1 === "1" && k === "f") pickQ2("none");
  else if (k === "enter" && !$("btn-next").disabled) { e.preventDefault(); $("btn-next").click(); }
});

// ---------- finish ----------
function csvCell(s) { s = String(s == null ? "" : s); return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
function buildCSV() {
  const text = {}; FRAGMENTS.forEach(f => { text[f.id] = f.text; });
  const rows = S.answers.slice().sort((a, b) => a.frag_id.localeCompare(b.frag_id));
  const head = ["frag_id", "text", "human_relevant_0_1", "human_valence_minus_plus_none", "position", "time_seconds", "coder", "codebook_version", "order_seed", "session_start", "session_end", "ui_language", "english_level", "source"];
  const lines = [head.join(",")];
  for (const r of rows) {
    lines.push([r.frag_id, text[r.frag_id] || "", r.rel, r.val, r.position, r.secs, S.coder, CODEBOOK, S.seed, S.startedAt || "", S.finishedAt || "", S.lang || LANG, S.english || "", S.source || ""].map(csvCell).join(","));
  }
  return lines.join("\n") + "\n";
}
function median(a) { if (!a.length) return 0; const s = a.slice().sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2); }
async function finish() {
  show("s-finish");
  const n = S.answers.length, rel = S.answers.filter(a => a.rel === "1").length;
  const mins = (S.startedAt && S.finishedAt) ? Math.round((Date.parse(S.finishedAt) - Date.parse(S.startedAt)) / 60000) : 0;
  $("st-n").textContent = n; $("st-rel").textContent = rel; $("st-min").textContent = mins; $("st-med").textContent = median(S.answers.map(a => a.secs));
  const pOk = S.practice.filter(p => p.ok).length;
  $("practice-score").textContent = t("practice.score", { ok: pOk, n: PRACTICE.length });
  const csv = buildCSV(); $("csv-box").value = csv;
  $("session-log").textContent = "coder=" + S.coder + " · codebook " + CODEBOOK + " · order seed " + S.seed + " · started " + (S.startedAt || "—") + " · finished " + (S.finishedAt || "—") + " · " + n + " rows";
  $("btn-copy").onclick = async () => {
    try { await navigator.clipboard.writeText(csv); setMsg("finish-msg", t("msg.copied")); }
    catch (e) { $("csv-box").focus(); $("csv-box").select(); setMsg("finish-msg", t("msg.selectall"), true); }
  };
  const dl = await use("downloads");
  if (!dl) { $("save-unavailable").hidden = false; return; }
  const btn = $("btn-save"); btn.hidden = false;
  btn.onclick = async () => {
    btn.disabled = true;
    try { await dl.save({ filename: "ws1_coded_" + safeName(S.coder) + ".csv", data: csv }); setMsg("finish-msg", t("msg.saved")); }
    catch (e) {
      const code = e && e.code;
      if (code === "declined") setMsg("finish-msg", t("msg.declined"), true);
      else if (code === "rate_limited") setMsg("finish-msg", t("msg.wait"), true);
      else { btn.hidden = true; $("save-unavailable").hidden = false; }
    }
    btn.disabled = false;
  };
}

// ---------- boot (hot reload across republish, then localStorage) ----------
function boot(data) {
  setLang(guessLang(), false);
  try { if (data && data.S && data.S.coder) { S = data.S; if (S.lang) setLang(S.lang, false); if (S.mode !== "welcome") { resume(); return; } } } catch (e) {}
  try { const last = localStorage.getItem("ws1v2_last"); if (last) $("coder-name").value = last; } catch (e) {}
}
try { window.claude && window.claude.hot && typeof window.claude.hot.snapshot === "function" && window.claude.hot.snapshot(() => ({ S })); } catch (e) {}
try {
  if (window.claude && window.claude.hot && typeof window.claude.hot.ready === "function") window.claude.hot.ready(boot);
  else boot(window.claude && window.claude.hot ? window.claude.hot.data : null);
} catch (e) { boot(null); }
</script>
'''


def load_fragments(sample, html):
    if os.path.exists(sample):
        with open(sample, encoding="utf-8-sig") as fh:
            return [{"id": r["frag_id"], "text": r["text"]} for r in csv.DictReader(fh)], sample
    if os.path.exists(html):
        h = open(html, encoding="utf-8").read()
        i = h.index("const FRAGMENTS = ") + len("const FRAGMENTS = ")
        return json.JSONDecoder().raw_decode(h, i)[0], html
    raise SystemExit("no coding_sample.csv and no ws1_survey.html to recover from")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default=os.path.join(HERE, "coding_sample.csv"))
    ap.add_argument("--html", default=os.path.join(HERE, "ws1_survey.html"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    frags, src = load_fragments(a.sample, a.html)
    ids = [f["id"] for f in frags]
    assert len(ids) == len(set(ids)) and all(f["text"].strip() for f in frags)
    js = lambda obj: json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
    page = (TEMPLATE.replace("__FRAGMENTS_JSON__", js(frags))
                    .replace("__PRACTICE_JSON__", js(PRACTICE))
                    .replace("__I18N_JSON__", js(I18N))
                    .replace("__CODEBOOK__", CODEBOOK))
    assert all(m not in page for m in ("__FRAGMENTS" + "_JSON__", "__PRACTICE" + "_JSON__", "__I18N" + "_JSON__"))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"fragments {len(frags)} (from {os.path.basename(src)}), practice {len(PRACTICE)}, "
          f"page {len(page.encode('utf-8'))/1024:.0f} KB -> {a.out}")


if __name__ == "__main__":
    main()
