# Tonamorph: план выхода на рынок США и качества услуги

Единый план от первого касания до любви к продукту. Собран из трёх спринтов (лестница
осведомлённости Бена Ханта и контент; качество услуги и механики удержания; операционная
система на MCP) и сверен с кодом. Русский текст — для основателя, вся клиентская копия —
в американском английском и используется дословно. Статус выполнения ведётся в
[`ROADMAP.md`](ROADMAP.md), пошаговые инструкции — в [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md).

_Обновлено: 2026-09-11._

## 0. Платформа бренда (зафиксировано)

| Элемент | Значение |
|---|---|
| Имя / компания | **Tonamorph** (TOH-na-morf) / Tonamorph Audio |
| Бренд-идея | Every sound is an instrument. |
| Главный слоган | **Any track. Now an instrument.** |
| Описание для магазинов | Tonamorph turns any audio into a playable instrument inside FL Studio and Ableton: stems, MIDI and key in two seconds.* |
| Глагол бренда | morph it |
| Единица покупки в маркетинге | morphs (в API и леджере остаётся `credits`) |
| Оффер | 3 free morphs, no card. 50 for $9, never expire. 60 a month for $7.99, cancel anytime. |
| Гарантия | If a morph is unusable, that morph is refunded. |
| Позиционирование | Играбельный инструмент внутри DAW, никогда «разделение стемов» (FL Studio и Logic дают его бесплатно) |
| Рынок | США, продюсеры 18–34 (hip-hop, trap, drill, R&B, EDM, lo-fi), FL Studio и Ableton, TikTok/Shorts/Reddit |

\* «two seconds» до измерения на GPU пишется как «about two seconds of processing on our
GPU tier» либо «seconds, not minutes»; после бенчмарка подставляется измеренный p95.

## 1. Лестница Бена Ханта

Одно сообщение на ступень, каждое поднимает ровно на одну ступень; кнопка покупки появляется
только на пятой. Полная версия с хуками, форматами, CTA и метриками — приложение A.

| Ступень | Состояние продюсера | Сообщение | Ловит | Метрика |
|---|---|---|---|---|
| L0 нет осознания проблемы | скроллит биты, режет сэмплы, доволен сплиттером FL | «That sound you like is already playable.» | TikTok-хуки «This bassline is now a keyboard», «Stop chopping. Play it.» | удержание 3 с ≥ 30 % |
| L1 знает проблему | «нарезка медленная, питч-чопы звучат не так, но это сэмплинг» | «The slow part is not sampling. It's leaving the DAW.» | ролик «Four steps for one melody», секция Problem на лендинге | клики в профиль ≥ 8 на 1000 просмотров |
| L2 знает решения | сплиттеры FL/Logic, Ableton audio-to-MIDI, Samplab, Moises: отдельные шаги, заканчивающиеся файлами | «Stems, MIDI and key inside one plugin, mapped on your keys.» | ролик «FL already splits stems. Here's what it doesn't do», How it works, страница /samplab | `demo_play` ≥ 40 % сессий |
| L3 знает продукт | «а на моей DAW, моём жанре, моей машине?» | «Proof on your DAW, your genre, our measured numbers.» | YouTube 5 мин в FL Studio, Reddit-посты, KVR, BPB, секции Speed/Proof/FAQ | `pricing_view` → `signup_start` ≥ 25 % |
| L4 знает, не убеждён | зарегистрировался или установил; должно сработать на своём клипе | «Your first three morphs are free. Morph your loop now.» | оверлей первого запуска, письма welcome и first-morph, ответные ролики «Your loop, morphed» | активация за 24 ч ≥ 60 % |
| L5 убеждён | три морфа использованы, MIDI оставил, баланс ноль | «50 morphs for $9, or 60 a month for $7.99. Same plugin, no re-install.» | пейволл с двумя кнопками и «Not now», письмо credits-at-zero, /pricing | CTR пейволла ≥ 10 %; free→paid ≥ 3 % |

Северная звезда: **weekly morphers** (аккаунты с ≥ 1 успешным морфом за 7 дней): 500 в первый
месяц, 2500 в третий. Лендинг из девяти секций написан финальным текстом (приложение A §2),
30-дневный календарь (1 ролик основателя + 2 автоматических в день с AI-дисклеймером),
шесть Reddit-постов без ссылок, питчи в KVR и Bedroom Producers Blog, семь писем Klaviyo
(приложение A §3–4). Страница /samplab выходит только после личной проверки samplab.com.

## 2. Качество услуги: чем оправдано обещание

### 2.1 Сценарий «ага» (первые пять минут)
Плагин открывается с уже морфнутым демо-клипом, играбельным до входа в аккаунт (0 кредитов).
Затем свой клип из текущего проекта (≤ 60 с, слышимая басовая линия) → Bass → **C3** звучит
как оригинал («это мой клип») → **G3** на квинту выше и в тональности (Scale-Snap по
найденному ключу) → перетаскивание `.mid` в piano roll ложится на сетку в найденном BPM.
Три клавиши и одно перетаскивание: узнавание, контроль, владение. Всё в §2.2–2.5 защищает
именно эту последовательность.

### 2.2 Десять критериев качества (гейты релиза)

| # | Критерий | Цель | Чем измеряется |
|---|---|---|---|
| 1 | Задержка drop → playable | серверный p95 ≤ 2.5 с warm (бюджет контракта 2.0); ощущаемый p95 ≤ 10 с при 10 Мбит; cold p95 ≤ 45 с | `scripts/benchmark_modal.py`, клиентский таймер `drop_to_ready_ms` |
| 2 | Артефакты разделения | SDR bass/drums ≥ базовой модели на золотом наборе из 20 клипов; «bleed» ≤ 10 % оценок | museval, таблица обратной связи |
| 3 | Точность MIDI | note F1 (±50 мс) ≥ 0.80 bass, ≥ 0.65 melody | mir_eval на золотом наборе |
| 4 | Тональность | root+mode ≥ 85 % (с относительной ≥ 92 %); confidence < 0.6 показывается как «shaky» | золотой набор |
| 5 | Без щелчков | 0 скачков > 6 дБ на границах нот в рендере из 1000 нот | тест в `tonamorph_core_tests` |
| 6 | Время загрузки | окно ≤ 2 с; повторная загрузка кэша ≤ 3 с; ни одного «unstable» при сканировании | DAW-матрица из `BETA_TEST_PLAN.md` |
| 7 | Crash-free | ≥ 99.5 % сессий; pluginval L5 `--repeat 2 --randomise` | opt-in crash-репорты плагина (добавить) |
| 8 | Ошибки загрузки/задач | 413/415/422 + транспорт ≤ 2 % дропов; `release+refund ÷ reserve` ≤ 1 % | метрики по `POST /v1/jobs`, SQL по леджеру |
| 9 | Ясность пейволла | 100 % пейволлов с кнопками (`app.checks`); ≥ 90 % бета-тестеров объясняют, что будет при 0 | гейт деплоя, форма беты |
| 10 | Трение возврата | возврат морфа ≤ 60 с самообслуживанием; решение по деньгам ≤ 1 рабочий день | леджер `refund`, тикеты |

### 2.3 SLO и обещание клиенту

| SLO | Цель |
|---|---|
| Доступность `/v1/health` и `POST /v1/jobs` | 99.5 % в месяц (≈ 3.6 ч); плановые работы ≤ 2 ч/мес, анонс за 24 ч |
| Успешность морфов | ≥ 99 % зарезервированных задач захвачены |
| Время до результата (с очередью) | p50 ≤ 4 с, p95 ≤ 10 с warm; cold p95 ≤ 45 с |
| Первый ответ поддержки | ≤ 24 ч в будни; S1 («списали, результата нет», «оплатил, кредитов нет») ≤ 12 ч |
| Возвраты | морфы мгновенно; деньги: решение ≤ 1 рабочий день, Paddle платит 5–7 дней |

ToS обещает только то, что уже верно в коде: кредит списывается лишь при успехе и
возвращается при сбое; аудио удаляется в течение 24 ч; правило возврата; экспорт и удаление
самообслуживанием. Аптайм, «2 секунды» и точность живут на статус-странице как пересматриваемые
обязательства, не в договоре.

Бюджет ошибок: 0.5 % ≈ 3.6 ч/мес; израсходовано > 50 % → заморозка фич до восстановления
30-дневного окна. Успешность < 99 % за час → SMS основателю. Успешность < 90 % за 15 мин или
очередь вебхуков → `MAINTENANCE_MODE=true` (503 с `Retry-After: 300`, ничего не резервируется,
баннер в плагине, остальное работает). GPU: serverless с keep-warm 14:00–02:00 ET, переход на
постоянный g5.xlarge после 3.4 пакетов/день; потолок бюджета AWS $300/мес с действием при 100 %
(сейчас в tfvars $150 — поднять при деплое).

Тексты инцидентов: статус-страница «Investigating: morphs failing or slow since 14:05 ET.
Failed morphs are not charged. Next update in 30 min.»; баннер «Morphing is paused for
maintenance. Your morphs are safe.» / «Morphs are slower than usual. Nothing extra is
charged.»; письмо только при > 2 ч или деньгах: что сломалось, что это стоило пользователю
(N неудачных морфов, все возвращены автоматически), что изменилось, одно извинение, без купонов.

### 2.4 Механики «влюбления»
Строки интерфейса (US English, ≤ 12 слов), три празднования (первый морф своего клипа:
клавиши в гамме светятся 2 с, «Your first morph. F minor · 124 BPM.»; первое перетаскивание
`.mid`: «MIDI's in your DAW.»; первая покупка: «50 morphs loaded. Thanks for backing a
one-person shop.»), реферальная петля «send a morph to a friend» (друг получает 3 + 2,
отправитель +3 после первого успешного морфа друга, ключ идемпотентности
`referral:<friend_user_id>`), подарок на 7-й день (+2 при ≥ 1 морфе), пейволл без тёмных
паттернов («That was your last free morph. Nothing happens unless you buy.», кнопка «Not now»
того же размера, строка про истечение месячных морфов). Полные таблицы строк — приложение B §3.

### 2.5 Поддержка для одного человека
`support@tonamorph.com` (SLO 24 ч), Discord для сообщества и совета тестеров (не канал
поддержки), кнопка Help в плагине открывает письмо с версией, хостом, ОС и id последней
задачи (никогда аудио и токены). Двенадцать макросов, правило эскалации (любой S1 или
расхождение леджера → сразу баг; одна причина ≥ 3 тикетов за 7 дней → в следующий релиз),
еженедельный обзор качества (Sentry по ролям, неудачные задачи по кодам, доля возвратов,
причины «палец вниз», NPS, теги тикетов, p50/p95, расходы) и гейт релиза (ctest, roundtrip,
pluginval на VST3 и AU, DAW-матрица, бенчмарк без ухудшения > 5 %, `app.checks`, terraform,
`spctl`/`signtool`, предыдущий инсталлятор доступен). Тексты макросов — приложение B §4.

### 2.6 Правило возврата (реализуемо на `refund_job`)
Право: `status = succeeded`, «палец вниз» в течение 24 ч после `finished_at`, причина не
`slow`. Автоматически: строка леджера `refund`, источник `job:<id>`, причина
`user:unusable:<reason>`, баланс в плагине обновляется сразу. Лимиты против злоупотреблений:
авто-возвраты ≤ max(3, 20 % захваченных задач) на пользователя за 30 дней; бесплатные аккаунты
≤ 2 за всё время; сверх — ручная проверка. Деньги: полный возврат через Paddle в 14 дней,
если из пакета использовано ≤ 5 морфов, иначе только морфы.

## 3. Операционная система на MCP

### 3.1 Кто что делает

| Задача | Инструмент | Статус доступа |
|---|---|---|
| Производство UGC (клип с правами → реальный морф → вертикальный ролик → публикация с UTM и дисклеймером) | собственный движок `tonamorph-growth` | код готов, аудиты TikTok/YouTube впереди |
| Варианты и хуки (несколько версий победителя, генерация ведущего над скриншотами, превью, предсказание виральности) | Higgsfield | 1 кредит, нужна покупка и `tiktok_connect` |
| Запуск-видео и объяснялки 9:16 | Motion.so | 0 кредитов ($5 за пакет) |
| Нарезка DAW-записей, субтитры | Descript | доступен |
| Айдентика, шаблоны 9:16/16:9, обложки, шапка писем | Figma | доступен (Pro team) |
| Доска лестницы и таблица экспериментов | Miro | доступен |
| Email: списки, шаблоны, кампании, профили | Klaviyo | доступен на запись, но аккаунт **Fitscan** (отправитель indo@fitscan.io) → нужен аккаунт Tonamorph |
| Klaviyo flows и сегменты | Windsor.ai `create_flow` после подключения Klaviyo, либо руками в UI | MCP Klaviyo их только читает |
| Аналитика сайта | Vercel Web Analytics (кастомные события требуют Pro) | проектов пока нет |
| Недельный скоркард (TikTok, YouTube, Instagram, Klaviyo, Paddle, Supabase, Sentry → SQL) | Coupler.io → Notion | 0 подключённых источников (OAuth-клики) |
| Ошибки и SLO | Sentry, GitHub Actions пробa `/v1/health` каждые 5 мин | Sentry встроен |
| Недоступно | Ahrefs («Insufficient plan»), Zapier без Paddle | Paddle → Klaviyo идёт через наш бэкенд |

### 3.2 Таксономия событий (реализует инженерия)
Продуктовые имена snake_case, метрики Klaviyo в Title Case; в Klaviyo события уходят с бэкенда
приватным ключом. Ключевые: `signup_completed` (source, referral_code, utm_*, marketing_opt_in),
`plugin_installed` (os, daw, plugin_version), `morph_started`, `morph_completed` (latency_ms,
credits_charged, balance_after, morphs_total, bpm, key), `morph_failed` (error_code, stage),
`credits_exhausted` (checkout URLs как свойства), `paywall_viewed`, `checkout_started`,
`purchase_completed` (plan_id, price_usd, is_renewal, referral_code), `subscription_cancelled`,
`refund_issued`, `nps_submitted`, `content_published`, `content_metrics`, `api_error`,
`health_probe`. Полная таблица со свойствами и потребителями — приложение C §3.

### 3.3 Klaviyo: списки, свойства, семь потоков
Списки `Tonamorph users` (все), `Tonamorph newsletter` (только `marketing_opt_in`),
`Tonamorph waitlist`. Свойства профиля: signup_source, referral_code, utm_*, plan,
credits_available, morphs_total, first/last_morph_at, daw, os, plugin_version, cohort_week,
nps_score. Потоки: Welcome (список; 0 ч / +2 д / +5 д), First morph (+30 мин), Failed morph
(транзакционный, +20 мин, выход при успехе в течение часа), Zero credits (0 ч / +48 ч / +7 д с
персональными checkout URL), Day-7 (ветвление по morphs_total), Win-back (сегмент Dormant 30d,
исключить возвраты), Purchase (транзакционный; +3 д; +14 д NPS). Тексты писем — из спринта A
(приложение A §4). Метрика в Klaviyo появляется только после первого события, поэтому бэкенд
шлёт по одному тестовому событию на метрику до создания потоков.

### 3.4 Регламент
Ежедневно автоматически (15:00 UTC, утро США): `run_daily_batch(3)` → `report_metrics(48h)`,
потоки Klaviyo, дайджест Sentry и Vercel, проба health каждые 5 мин. Ежедневно 15 минут
основателя: утвердить подписи и хуки на завтра, прочитать блок `credits`, ответить на письма о
неудачных морфах. Еженедельно автоматически: Coupler → SQL-скоркард → страница Notion «Week N» +
событие в календаре; еженедельно основатель: выбрать углы, записать одну DAW-сессию для Descript,
манифесты лицензий на новые клипы, подтвердить рассылку. Ежемесячно: письмо об обновлениях, чтение
NPS, ротация кода win-back, обновление превью.

Ограничители: лицензионный гейт движка (без платформенных музыкальных библиотек), AI-дисклеймер
везде (`is_aigc=true` в Higgsfield, строка в подписи для Motion/Descript), кредитный пол 5 и
бюджет 3 морфа/день, лимиты публикаций (IG 3/день, YT 2, FB 2, TikTok ≤ 3), прогрев новых
аккаунтов 14 дней вручную, один ролик → один аккаунт на платформу, кросс-аккаунт только
через переозвученные варианты, TikTok в приватном режиме до аудита.

### 3.5 Измерение SLO и маршрутизация тревог
Источники: пробa health (GitHub Actions → issue), `growth_daily` SQL-вью в Supabase (успешность,
p50/p95), Sentry, Paddle (возвраты), отчёты потоков Klaviyo (доставка ≥ 98 %, отписки < 0.5 %),
хранилище движка (доля `ai_flag_set` = 100 %). P1 (health лежит 10 мин, успешность < 90 % за час,
5xx на вебхуке Paddle) → push на телефон; P2 (новая ошибка Sentry, возврат, всплеск
недоставки) → дайджест дважды в день; P3 (контент и рост) → недельная страница Notion.

### 3.6 Четырнадцать дней: порядок действий

| День | Действие | Кто |
|---|---|---|
| 1 | Аккаунт Klaviyo для Tonamorph (или ребренд Fitscan), DKIM/DMARC для домена отправителя; Vercel Pro, если нужны кастомные события | ты |
| 1 | Notion: хаб «Tonamorph Growth» и база «Weekly reviews»; календарь: «Daily growth check» 09:00, «Weekly review» пн 10:00 | я через MCP |
| 2 | Figma: файл «Tonamorph identity» (логотип, палитра, шрифт, шаблоны 9:16/16:9, шапка писем) | я через MCP, ты утверждаешь |
| 3 | Vercel: проект из репозитория (root `tonamorph/web`), затем DNS tonamorph.com, `NEXT_PUBLIC_KLAVIYO_COMPANY_ID`, Paddle client token | я / ты |
| 4 | Бэкенд: сервис Klaviyo (события + upsert профиля), хуки в signup, complete_job, сбой, `_apply` Paddle, `/v1/nps`; вью `growth_daily`; workflow пробы health; веб-события `track()` | я |
| 4 | `KLAVIYO_PRIVATE_API_KEY` в секреты, деплой, по одному тестовому событию на метрику | ты |
| 5 | Klaviyo: три списка, картинки, 12 шаблонов, рендер-проверка, тестовые отправки | я через MCP (отправка с твоего подтверждения) |
| 5 | Сегменты ×4 в UI Klaviyo; подключить Klaviyo в Windsor.ai | ты |
| 6 | Windsor: шесть потоков черновиками; проверка `get_flow` | я через MCP |
| 6 | Поток win-back (сегментный триггер), транзакционные флаги, включение | ты |
| 7 | Движок: имя `tonamorph-growth`, CTA «3 free morphs», `GROWTH_LANDING_URL`, реферальный код, лимиты | я |
| 7 | Лицензированные клипы и манифесты; аккаунты IG Pro/FB/YouTube/TikTok; старт ручного прогрева | ты |
| 8 | Кредиты Higgsfield и `tiktok_connect`; Motion $5 | ты |
| 8 | Higgsfield: два хука ugc-website-video + предсказание виральности; Motion: запуск-объяснялка 9:16; Descript: субтитры на DAW-записи | я через MCP |
| 9 | Miro: доска «Tonamorph growth ladder» с воронкой и таблицей экспериментов | я через MCP |
| 10 | Coupler: подключить TikTok Organic, YouTube, Instagram Insights, Klaviyo, Paddle, Supabase, Sentry | ты |
| 10 | Coupler: семь dataflow, запуск, схемы | я через MCP |
| 11 | Движок: `run_daily_batch(2, dry_run=true)`, затем YouTube private + IG; TikTok в черновики | я, ты просматриваешь |
| 12 | Klaviyo: кампания «Launch week» в newsletter, оценка аудитории | я; отправка с твоего подтверждения |
| 13 | Базовая линия ошибок Vercel, шаблон issue `slo-breach`, SQL скоркарда в Notion, правила алертов Sentry | я / ты (правила Sentry) |
| 14 | Первый недельный обзор от начала до конца → Notion «Week 1», событие в календаре, список блокеров | я через MCP |

## 4. Инженерный бэклог из плана (по приоритетам)

| P | Что | Объём | Где |
|---|---|---|---|
| 0 | Золотой набор из 20 клипов + бенчмарк (latency, SDR, MIDI F1, key); измеренный p95 вместо «2 s» | M | backend/ops |
| 0 | Внешняя проба аптайма + статус-страница с живыми числами | S | ops/web |
| 0 | Metric filters CloudWatch, алерт по доле неудач, `alarm_email`, SMS | S | ops |
| 0 | Opt-in краш-репортер в плагине (Sentry native, `role=plugin`) | M | plugin |
| 0 | Применять анализ на событии `result` до окончания загрузок стемов | S | plugin |
| 0 | Встроенный демо-морф, играбельный до входа | M | plugin |
| 0 | Строки §2.4, пейволл с раскрытием истечения и равной кнопкой «Not now» | S | plugin |
| 0 | Оценка результата: `POST /v1/jobs/{id}/feedback` + таблица `job_feedback` | M | plugin/backend |
| 0 | Авто-возврат на `refund_job` с лимитами §2.6 | S | backend/plugin |
| 0 | Supabase: подтверждение email до гранта, троттлинг регистраций | S | ops |
| 0 | Сервис Klaviyo + события §3.2 + `growth_daily` + проба health + веб-события | M | backend/web/ops |
| 1 | `GET /v1/version` + баннер обновления | M | backend/plugin |
| 1 | Событие возврата Paddle → `adjust_credits` + `void` комиссии | M | backend |
| 1 | Клиентский таймер `drop_to_ready_ms` | S | plugin/backend |
| 1 | Пользовательские реферальные коды, грант после первого морфа друга, страница `/m/<code>` | M | backend/web |
| 1 | Крон подарка на 7-й день; карточка NPS на 14-й | S | backend/plugin |
| 1 | Read-only вид поддержки: задачи + леджер по пользователю | M | ops |
| 1 | Расписание keep-warm под пик США | S | ops |
| 2 | `/roadmap` и `/changelog` | S | web |
| 2 | Платная полоса в очереди; общие (Redis) лимиты | M | backend |
| 2 | Токены в Keychain/DPAPI | M | plugin |

## 5. Согласования и открытые вопросы
- «2 секунды» = бюджет GPU-вычисления в контракте §7; клиентское обещание — секунды, не минуты,
  до измерения. После бенчмарка обе цифры (серверная и сквозная) публикуются на статус-странице.
- Klaviyo сейчас привязан к другому бизнесу основателя (Fitscan); для Tonamorph нужен свой
  аккаунт или ребренд, иначе письма уйдут с чужого отправителя.
- Две программы вознаграждений: аффилиаты (контракт §12, 30 % комиссии) и пользовательские
  рефералы морфами (§2.4). Это разные таблицы и разные ключи идемпотентности.
- Дата закрытия Samplab не подтверждена; копия «closing» только после проверки основателем.
- Кастомные события Vercel требуют Pro; без них веб-часть измеряется Klaviyo и бэкендом.

---

## Приложение A. Лестница осведомлённости и контент (отчёт спринта, English)


### Tonamorph — US launch: Awareness Ladder plan

Web check 2026-09-11: Samplab's 17 Sep 2026 wind-down is corroborated by several search summaries of samplab.com (uploads stop, pro-rata refunds, offline build for existing projects). Egress-blocked, not read directly: samplab.com, reddit, kvraudio.com, bedroomproducersblog.com, selektaudio.com. No Reddit, YouTube or Gearspace closure thread was findable.

#### 1. Awareness Ladder

One message per rung; the buy button appears only at L5.

**L0 — no problem awareness.** State: scrolls for beats, chops samples, happy with FL's splitter. Message: "That sound you like is already playable." TikTok, automated `bass`: "This bassline is now a keyboard." — licensed loop, bass on keys C2–C4; caption CTA "morph it — link in bio". TikTok, founder: "Stop chopping. Play it." — slice-and-pitch vs keys; CTA "follow for the FL version". Short, automated `sample_flip`: "One loop, three beats, no chopping." Surface: profile bio. Metric: 3-s hold ≥ 30 %.

**L1 — problem aware.** State: "chopping is slow and pitched chops sound wrong, but that's sampling." Message: "The slow part is not sampling. It's leaving the DAW." Founder TikTok: "Upload, wait, download, re-import. Four steps for one melody." — web-tool loop vs stopwatch; CTA "plugin version next video". Reddit post 1. Automated `tutorial`: "Why pitched chops lose their punch." Surface: hero + Problem section. Metric: profile clicks per 1,000 views ≥ 8; landing sessions by `utm_content`.

**L2 — solution aware.** State: knows FL/Logic splitters, Ableton audio-to-MIDI, Samplab, Moises — separate steps ending in files. Message: "Stems, MIDI and key inside one plugin, mapped on your keys." Founder Short: "FL already splits stems. Here's what it doesn't do." — FL split, then the same loop morphed and played; CTA "3 free morphs, no card". Automated `speed`: "Drop. Play. Drag the MIDI." — real elapsed time on screen; CTA "60-second demo on the site". The /samplab page. Surface: How-it-works, compatibility strip. Metric: `demo_play` on ≥ 40 % of sessions.

**L3 — product aware.** State: "Tonamorph does that — on my DAW, my genre, my machine?" Message: "Proof on your DAW, your genre, our measured numbers." Founder YouTube, 5 min: "Tonamorph in FL Studio 21: trap loop to playable bass and .fsc drag", elapsed time visible; CTA "install free". Reddit posts 3–5. KVR listing, BPB pitch. Surface: Speed, Not-a-splitter, Proof, FAQ. Metric: `pricing_view` → `signup_start` ≥ 25 %.

**L4 — most aware, not convinced.** State: signed up or installed; needs it to work on their own clip first. Message: "Your first three morphs are free. Morph your loop now." Plugin first-run overlay: "Drop any clip up to 60 s. 3 morphs on us." Welcome and first-morph mails. Founder reply videos "Your loop, morphed" (commenter's own clip, with permission). Surface: sign-in overlay → first drop; /account. Metric: activation = first succeeded morph within 24 h ≥ 60 %.

**L5 — convinced.** State: three morphs used, MIDI kept, balance zero. Message: "50 morphs for $9, or 60 a month for $7.99. Same plugin, no re-install." In-plugin paywall, two buttons, Not now. Credits-at-zero mail. Founder Short "What 50 morphs got me this week." Surface: paywall → checkout; /pricing. Metric: paywall click-through ≥ 10 %; free→paid ≥ 3 % by cohort week.

#### 2. Landing page (final copy)

| section (rung) | headline / subhead | proof |
|---|---|---|
| Hero (L1→2) | **Any track. Now an instrument.** / Tonamorph turns any audio into a playable instrument inside FL Studio and Ableton: stems, MIDI and key in seconds. Drop a clip, play it on your keys, drag the MIDI out. | 12 s muted loop with elapsed timer. Buttons "Get 3 free morphs" (no card) · "Watch the 60 s demo" |
| Problem (L1) | **The slow part is not sampling. It's leaving the DAW.** / Upload, wait, download, re-import, slice, re-pitch. Four apps for one melody. | Timeline graphic |
| How it works (L2) | **Drop. Play. Drag.** / 1 Drop any clip up to 60 s. 2 Bass, drums, synth and vocals arrive mapped across your keyboard, locked to the detected key. 3 Drag the .mid or .fsc into your piano roll. | Three plugin GIFs |
| Speed (L3) | **About two seconds of GPU time.** / On our GPU tier, measured (pipeline budget 1.8 s on an A10G). Drop to playable is usually 5–15 s warm; the first morph after a long idle takes longer. Until the beta p95 exists: **"Playable in seconds, not minutes."** | Beta p95 table (G3/G3b); hero timer until then |
| Not a splitter (L3) | **FL Studio and Logic already split stems. Tonamorph is what happens next.** / Keep their splitter. Tonamorph gives you each stem as a chromatic instrument, drum slices from C1, auto ADSR and the MIDI, without leaving the plugin. | Strip: FL Studio 21.2+ · Ableton Live 12 · Logic Pro 11 (AU) · Windows · macOS |
| Proof (L3) | **Made with morphs.** / Opted-in beta testers (form Q16), with DAW and genre. | Real handles; no synthetic testimonials |
| Free (L4) | **3 free morphs. No card.** / Create an account, sign in inside the plugin, drop your own loop. | Balance screenshot showing 3 |
| /pricing (L5) | **50 morphs for $9, once. 60 morphs a month for $7.99.** / One morph = one clip up to 60 s → stems, MIDI, key and BPM. Failed morphs are not charged. Pack morphs never expire; subscription morphs reset monthly. | Both buttons open checkout; the plugin updates the balance itself |
| FAQ (L3–5) | Rights (only audio you hold rights to; files deleted within 24 h), offline behaviour, refunds. | Privacy and Terms links |

#### 3. 30-day calendar

Per day: 1 founder post (F: phone, native upload, no VO, nothing to disclose) + 2 automated (A: Remotion + synthetic VO; caption "Voiceover generated with AI." plus TikTok `is_aigc` / YouTube `containsSyntheticMedia`; private until the TikTok audit and YouTube verification pass, so the founder re-uploads them by hand). Audio only from `LICENSED_CLIPS_DIR`. Caption: `<what happened>. 3 free morphs, no card — link in bio. #flstudio #ableton` + credit + disclosure. A angles: S `speed` (timer), B `bass`, X `sample_flip`, T `tutorial`, different clip each. Entry: day, F hook · beat, A1/A2.

**Week 1.** 1 "This bassline is now a keyboard." · play C2–C4 · B/S. 2 "Stop chopping. Play it." · slices vs keys · X/T. 3 "Four steps for one melody." · web tool vs plugin · S/B. 4 "FL splits stems. Here's what it doesn't do." · FL split → morph → play · T/X. 5 "Drums on keys from C1." · B/S. 6 "Wrong notes can't happen." · scale-snap off/on · T/B. 7 "Send me your loop." · X/S.

**Week 2.** 8 "Your loop, morphed (1/5)." · commenter's clip · B/T. 9 ".fsc straight into the piano roll." · S/X. 10 "Same loop, Ableton." · .mid into Arrangement · T/B. 11 "Vocals as a pad." · long attack · X/S. 12 "What the key detector heard." · readout vs ear · T/B. 13 "Your loop, morphed (2/5)." · S/X. 14 "Week two numbers." · real p95 · B/T.

**Week 3.** 15 "Lo-fi from a piano loop." · ADSR · X/S. 16 "Drill: 808 from a guitar." · bass re-pitched · T/B. 17 "Samplab users: what carries over." (after founder confirms) · S/X. 18 "Your loop, morphed (3/5)." · B/T. 19 "Where the 3 free morphs go." · first session · X/S. 20 "R&B chords from a vocal stack." · T/B. 21 "Failed morph? Not charged." · error on purpose · S/X.

**Week 4.** 22 "Your loop, morphed (4/5)." · B/T. 23 "Three beats, one loop, ten minutes." · timelapse · X/S. 24 "Auto ADSR: bass vs vocals." · T/B. 25 "EDM lead from a synth stem." · S/X. 26 "Your loop, morphed (5/5)." · B/T. 27 "What 50 morphs got me this week." · X/S. 28 "Logic users: AU is here." · T/B. 29 "Mistakes I made shipping this." · S/X. 30 "Month one, honestly." · B/T.

**Reddit** (modmail first; r/edmproduction only in the mods' thread; no store links, no prices): r/FL_Studio "Chromatic re-pitch vs slicing: why pitched chops lose transients" (no link); r/trapproduction "An 808 from a guitar stem without it sounding like a guitar" (plugin named only if asked); r/edmproduction "Beta numbers from 15 producers: first-job success and p95 latency" (one link); r/FL_Studio ".fsc vs .mid drag into FL: what lands in the piano roll"; r/ableton "Convert Harmony vs stem-first transcription on one loop" (say where Ableton wins); r/trapproduction "AMA: solo dev, cloud instrument plugin, real cost per job".

**KVR** (developer account at kvraudio.com/devs, or contactus@kvraudio.com with images). Subject: "Tonamorph 1.0 — any clip becomes a playable instrument inside FL Studio, Ableton and Logic (VST3/AU)". Pitch: Tonamorph Audio releases Tonamorph, a cloud-connected instrument plugin. Drop a clip up to 60 s; bass, drums, synth and vocals come back mapped across the keyboard, root at C3, scale-snapped to the detected key, drum slices from C1, with auto ADSR and a .mid (plus .fsc for FL Studio) of the transcription. About two seconds of GPU compute per clip, measured on our A10G pipeline; drop-to-playable typically under 15 s warm. Free tier: 3 morphs at sign-up, no card. 50 morphs $9 once; 60 a month $7.99. VST3 Windows/macOS, AU macOS. Screenshots, 60 s video and press key attached. Solo developer, Tonamorph Audio, Israel.

**BPB** (contact form; the editor reads every mail). Subject: "Free tier — 3 morphs turn any loop into a playable instrument inside FL/Ableton (solo-dev plugin)". Pitch: Your readers already have FL's free stem splitter; Tonamorph is the step after it. A dropped loop comes back as four chromatic instruments plus MIDI, inside the plugin, locked to the detected key, with .fsc drag for FL Studio. Three morphs are free with no card, enough to try a real loop. I'm a solo developer. I can send a review key with unlimited morphs, the beta's measured p95 numbers, and honest notes on where transcription still misses (dense polyphony, distorted 808s). No affiliate ask, no embargo. Assets: 60 s demo, five screenshots, a one-paragraph changelog.

#### 4. Klaviyo flows

Backend metrics: `Account Created`, `Morph Succeeded` (first=true), `Morph Failed`, `Balance Zero`, `Placed Order` (checkout webhook); profile property `last_morph_at`.

| flow | trigger · delay | subject / preview | body |
|---|---|---|---|
| Welcome | `Account Created` · now | "Your 3 morphs are ready" / "No card. Drop any clip up to 60 s." | 3 free morphs are on your account. Open Tonamorph in FL Studio, Ableton or Logic, sign in with this email, drop a loop you hold the rights to. Stems come back on your keys, MIDI ready to drag. Not installed: [download]. Reply if anything sticks. |
| First-morph success | `Morph Succeeded`, first · 20 min | "It's on your keys" / "Now drag the MIDI out." | Your first morph worked. Two things people miss: "Drag .mid" (.fsc in FL) drops the transcription into your piano roll; Drum mode maps slices from C1. Scale-snap follows the detected key; off plays free. Two morphs left. |
| First-morph failure | `Morph Failed`, first · 10 min | "That one didn't cost a morph" / "What usually fixes it." | The morph failed; the credit was released, you still have 3. Usual causes: a file over 10 MB or the network dropping mid-upload (clips over 60 s are trimmed, not rejected). Try a WAV or MP3 under 60 s. Fails again? Reply with the file details. |
| Credits at zero | `Balance Zero` · 2 h, skip if `Placed Order` | "3 morphs down. Your MIDI stays." / "50 for $9, or 60 a month." | Everything you morphed stays yours: the stems in your project, the MIDI you dragged out. To keep going: 50 morphs for $9, once, never expire; or 60 a month for $7.99. The plugin updates your balance itself. [Get 50 morphs] [Subscribe] |
| Day-7 nudge | `Account Created` + 7 d, no `Morph Succeeded` | "Still have 3 free morphs" / "One loop is enough to know." | Your 3 morphs are unused. If install was the wall: FL Studio 21.2+, Ableton Live 12, Logic Pro 11; rescan plugins after installing. Windows may show a SmartScreen warning (new certificate): More info → Run anyway. Something else? Reply. |
| Win-back day-30 | `Account Created` + 30 d, no `Placed Order`, `last_morph_at` > 14 d | "What changed in Tonamorph" / "Plus 2 extra morphs." | Since you tried it: [changelog]. I added 2 morphs to your account so you can hear the difference on your own loop. If it still isn't for you, one reply tells me why and I stop mailing. |
| Purchase thank-you | `Placed Order` · now | "Morphs added — three ways to use them well" / "Receipt inside." | Balance updated in the plugin. 1 Morph short, clean loops (under 30 s) for tighter MIDI. 2 Duplicate the track so each stem keeps its settings. 3 Save the project: stems reload; after 24 h the plugin asks to reload them. Subscribers: morphs reset monthly. Receipt: [link]. |

#### 5. Samplab window

Page `/samplab`: "Moving from Samplab? What carries over, what doesn't." Terms: samplab alternative, samplab shutting down, samplab replacement, samplab audio to midi, samplab resynthesizer alternative, stem to midi plugin. Already on that SERP: Selekt (free on-device MIDI), MIDI Morph 2 ($39 until 17 Sep, then $79), RipX, Basic Pitch, AI-directory listicles. Copy (first sentence only after the founder has read samplab.com): "Samplab has announced it will stop accepting uploads after September 17, 2026. If you used it to split a sample and get MIDI, Tonamorph does that inside FL Studio, Ableton and Logic, and adds what Samplab never had: each stem mapped on your keyboard. What it does not do: Samplab's timbre-preserving note editing (Resynthesizer). Existing owners keep an offline version. Three morphs free, no card." Outreach (answers, not link-drops): YouTube "Free Plugin You May Like – Samplab 2", "AUDIO to MIDI – SAMPLAB 2", "Samplab Desktop App FREE Melodyne Alternative", "A.I. Audio to Midi plugin Samplab 2 update"; the PG Music forum thread "Samplab"; the freevstplugins Facebook group's Samplab post; AlternativeTo and G2 listings.

#### 6. Metrics tree

North star: **weekly morphers** — accounts with ≥ 1 succeeded morph in the last 7 days (backend `jobs`). M1 500, M3 2,500.

| rung | metric | M1 | M3 | where |
|---|---|---|---|---|
| L0 | views; 3-s hold | 300k; 30 % | 1.5M; 35 % | platform via `report_metrics` |
| L1 | profile clicks / 1k views; landing sessions | 8; 2,500 | 10; 12,000 | platform; Vercel by `utm_content` |
| L2 | `demo_play`; `pricing_view` rates | 40 %; 30 % | 45 %; 35 % | Vercel custom events |
| L3 | `signup_start` / `pricing_view`; sign-ups | 25 %; 400 | 30 %; 2,500 / mo | Vercel; backend `profiles` |
| L4 | activation ≤ 24 h; first-job success; warm p95 | 60 %; ≥ 85 %; ≤ 5 s | 65 %; ≥ 90 %; ≤ 5 s | backend job metrics |
| L5 | paywall CTR; free→paid; buyers | 10 %; 3 %; 12 | 12 %; 4 %; 100 / mo | plugin event, `purchases`, Klaviyo flow revenue |
| retention | repeat morph within 30 d; sub churn | 25 %; — | 35 %; ≤ 8 % | backend; checkout webhook |

M3 ≈ $30/day, a quarter of the $135/day target until paid retargeting starts.

#### 7. Risks

1. **Automated posts stay private** until the TikTok audit, YouTube verification and Meta review pass. File all three on day 1; founder uploads the engine's MP4s natively until then.
2. **"Any track" invites rights violations.** Demos only from the licensed folder; upload screen and FAQ say "audio you hold the rights to"; no known-song requests.
3. **"Two seconds" gets challenged** (perceived 5–15 s, cold starts). Hero timer shows real elapsed time; copy qualified as in §2; one container kept warm through launch.
4. **Samplab claim wrong or stale; "morph" collides with MIDI Morph 2**, already selling as the Samplab alternative. Founder reads samplab.com before any "closing" copy; watch brand searches for confusion; never name it.
5. **Three morphs too few to reach L5.** Failed morphs cost nothing; win-back grants 2; if week-2 activation is under 50 %, test 5 free morphs on half of sign-ups.

#### Кратко по-русски

План построен по лестнице осведомлённости Ханта: шесть ступеней, на каждой одно сообщение, двигающее ровно на одну ступень, покупка только на пятой. Позиционирование — не «разделение стемов» (это уже бесплатно в FL и Logic), а «стем как инструмент на клавишах плюс MIDI, не выходя из плагина». Лендинг из девяти секций написан финальным текстом; «две секунды» оговорены как GPU-время на нашем A10G-тарифе, до замера p95 из беты — «за секунды, не минуты». Календарь: 30 дней × (1 ролик основателя + 2 автоматических с AI-дисклеймером), 6 постов на Reddit, питчи в KVR и BPB, семь писем Klaviyo. Страница /samplab — только после личной проверки samplab.com (17 сентября): сайт отсюда заблокирован, тредов о закрытии не найдено. Риски: автопосты приватны до аудитов, права на аудио в демо, оспоримые «две секунды», путаница с MIDI Morph 2, трёх бесплатных морфов может не хватить.

---

## Приложение B. Качество услуги и удержание (отчёт спринта, English)

### Tonamorph — earning the right to be loved (US launch)

Sources: `API_CONTRACT.md` (§n), `ARCHITECTURE.md` (ARCH), `SECURITY.md`, `ECONOMICS.md` (ECON), `BETA_TEST_PLAN.md` (rows, G-metrics, Q-questions), both READMEs, audit §5–6. "Morph" = one credit = one job. No files were modified.

#### 1. Quality of the offer

**The first five minutes.** Install → open the plugin → *a demo clip is already morphed and playable before sign-in* (a bundled result in the plugin's own cache format, zero credits) → sign in → drop **their own clip**. The aha is not the demo; it is:

> Drop a ≤60 s clip **from the project they are working on** (a full-mix loop with an audible bassline — the trap/drill/EDM material of beta §2). Select **Bass**. Press **C3** — the bassline plays at its original pitch: "that's my clip" (K1). Press **G3** — a fifth up, still in key, because Scale-Snap defaulted to the detected key (K5). Then **drag ".mid" into the piano roll** — the transcribed bassline lands on the grid at the detected BPM (M1/M2).

Three keys and one drag: recognition, control, ownership. If any fails, "Any track. Now an instrument." is not believed. §7 exists to protect this sequence.

**Ten quality criteria** (launch gates; beta G-values are the floor):

| # | criterion | target | measured how | artefact |
|---|---|---|---|---|
| 1 | Latency, drop→playable | server p95 ≤ 2.5 s warm (§7 budget 2.0); perceived p95 ≤ 10 s at 10 Mbit up (ARCH §5: 5–14 s); cold p95 ≤ 45 s | `finished_at−started_at` SQL (beta §1); client timer `drop_to_ready_ms` | beta SQL; **add** GPU benchmark + client timing |
| 2 | Separation artefacts | SDR on bass/drums ≥ model baseline over a 20-clip golden set; thumbs-down "bleed" ≤ 10 % of rated morphs; Q7 "better/same" ≥ 60 % | museval; feedback table (§5) | **add** golden set + benchmark |
| 3 | MIDI accuracy | note F1 (±50 ms) ≥ 0.80 bass, ≥ 0.65 melody; G7 ≥ 70 % | mir_eval on golden set; Q9 | **add** to benchmark |
| 4 | Key detection | root+mode ≥ 85 % (relative-key tolerant ≥ 92 %); `confidence` < 0.6 shown as "shaky" | golden-set labels vs `analysis.key` | **add** to benchmark |
| 5 | No clicks | zero steps > 6 dB at note-off/slice boundaries in a 1,000-note random render | render scan in `tonamorph_core_tests` (ZeroCrossing exists); E3 | **add** render test |
| 6 | Load time | window ≤ 2 s (U1); cached reload ≤ 3 s (R1); never "unstable" on scan (S1–S3) | DAW matrix stopwatch; plugin log | beta rows |
| 7 | Crash-free | ≥ 99.5 % sessions (G5 floor 98 %); no reproducible scan/load crash | opt-in crash reports; pluginval L5 `--repeat 2 --randomise` | Sentry is backend-only (SECURITY §10); **add** plugin reporter |
| 8 | Upload/job failure | 413/415/422 + transport ≤ 2 % of drops; `release+refund ÷ reserve` ≤ 1 % warm (ECON §11) | metric filter on `POST /v1/jobs`; ledger SQL | **add** metric filters (audit §5) |
| 9 | Paywall clarity | 100 % of paywalls have buttons (`app.checks` gate); Q11 ≥ 90 % can say what happens at 0; zero "surprise charge" tickets | deploy gate; form; ticket tag | gate exists; **add** tags |
| 10 | Refund friction | credit refund ≤ 60 s self-serve; money decision ≤ 1 business day | ledger `refund` by source; ticket timestamps | `refund_job` exists; **add** endpoint (§6) |

#### 2. SLOs and the service promise

| SLO | target | truth |
|---|---|---|
| Availability (`/v1/health` + `POST /v1/jobs`) | 99.5 %/month (≈ 3.6 h); announced maintenance ≤ 2 h/month excluded if posted 24 h ahead | **add** external uptime check (audit §5) |
| Job success | ≥ 99 % of reserved jobs captured | ledger `capture ÷ reserve` |
| Time-to-result (`finished_at − created_at`, incl. queue) | p50 ≤ 4 s, p95 ≤ 10 s warm; cold p95 ≤ 45 s | beta SQL, weekly |
| Support first response | ≤ 24 h weekdays; S1 ("charged, no result", "paid, no credits") ≤ 12 h (beta §6.2) | inbox |
| Refund turnaround | credits instant (auto) or ≤ 1 business day; money decision ≤ 1 business day, Paddle pays in 5–7 | ledger, Paddle |

**Status page:** four components (API, Morph engine, Payments/Paddle, Website & account); live 24 h numbers (morphs succeeded %, p50/p95, queue wait); incident log; scheduled maintenance; monthly SLO scorecard; a fixed box: *"A failed morph is never charged — the credit comes back automatically."*

**ToS may promise:** credits captured only on success and released on failure (§2/§6 — already true); audio deleted within 24 h (§10); the refund rule (§6 below); self-serve export and deletion. **ToS must not promise** uptime, "2 seconds" or accuracy — those are status-page commitments, revisable. "2 s" stays off the landing page until the benchmark yields a measured p95 (beta §8).

**Error budget policy.** 0.5 % ≈ 3.6 h/month. >50 % burnt → feature freeze until the 30-day window recovers. Job success < 99 % for 1 h → page by SMS (SNS; email is not a page — audit §5). Job success < 90 % for 15 min, or a webhook backlog → flip `MAINTENANCE_MODE=true`: `POST /v1/jobs` answers 503 `Retry-After: 300`, nothing is reserved (§2), the banner shows, everything else keeps working. A degraded engine burning people's attempts is worse than a paused one.

**GPU capacity.** Launch serverless (`modal`/`runpod`, ECON §7) with a keep-warm container 14:00–02:00 ET (US producer peak); cold starts only off-peak, and the banner says so. Move to an always-on `g5.xlarge` past 3.4 packs/day (ECON §8), then a Savings Plan. Hard cap: budget $300/month (not $150) with the 100 % `budget_action` (deny `sqs:SendMessage` → 503 `worker_unavailable`, credit released — ARCH §6), alert at 80 %. Planned, not built: a paid lane so free morphs queue behind paid (audit §6).

**Incident templates.** *Status page:* "Investigating — morphs failing or slow since 14:05 ET. Failed morphs are not charged. Next update in 30 min." *In-plugin banner:* "Morphing is paused for maintenance. Your morphs are safe." / "Morphs are slower than usual. Nothing extra is charged." *Email (only if > 2 h or money affected):* subject "Tonamorph was down 14:05–16:40 ET — what happened"; what broke, what it cost you (N failed morphs, all auto-refunded), what changed, one apology, no coupon theatre.

#### 3. Delight mechanics

**Onboarding inside the plugin** (US English, ≤ 12 words):

| state | string |
|---|---|
| Empty, signed out, demo loaded | "Play a key. That's a morphed clip. Now drop yours." |
| Drop zone | "Drop any clip here. Up to 60 seconds." |
| First drop while signed out | "Sign in to morph your own clips. 3 free." |
| upload / separate / transcribe / analyze / package | "Uploading…" / "Splitting bass, drums, synth, vocals…" / "Writing the MIDI…" / "Finding the key and tempo…" / "Almost there…" |
| First sound (C3 highlighted) | "Ready. Play C3 — that's your bass, in key." |
| First drag (arrow on ".mid") | "Drag .mid into your piano roll." |
| Truncated (D3) | "Longer than 60 s — we morphed the first minute." |
| Low key confidence | "Key guess is shaky — tap to pick another." |
| Cancel (P4) | "Cancelled. Morph returned." |

**Errors** (§5 codes / beta rows):

| code | string |
|---|---|
| 413 | "That file's over 10 MB. Try a shorter or 16-bit clip." |
| 415 / D6 | "That's not an audio file we can read. WAV, MP3, FLAC work." |
| 429 | "Whoa, fast. Try again in a minute." |
| 503 service_unavailable | "Morphing is paused for maintenance. Your morphs are safe." |
| 503 worker_unavailable | "Engine's busy. Nothing was charged — try again shortly." |
| failed / worker_timeout / D7 | "That morph didn't work. Morph returned. Try again?" |
| offline (O2) | "You're offline. Loaded stems still play; morphing needs internet." |
| lost contact | "Lost contact with the morph. Checking…" |
| 401 / token_expired | "Please sign in again." |
| wrong password (A3) | "Wrong email or password." |
| unconfirmed email | "Check your inbox to confirm, then sign in." |
| auth rate-limited | "Too many tries. Wait a minute, then sign in." |
| cache missing (R1) | "Cached stems are missing. Morph again to play." |

**Three celebrations** (visual only — the DAW owns the audio): (1) first own-clip morph ready — in-scale keys glow 2 s, "Your first morph. F minor · 124 BPM." (2) first `.mid` drag lands — the export target pulses, "MIDI's in your DAW." (3) first purchase, caught by the existing 5 s `/v1/me` poll — "50 morphs loaded. Thanks for backing a one-person shop."

**Referral loop — "send a morph to a friend".** Share button → `tonamorph.com/m/<code>` (a user-level `referral_codes` row, separate from affiliates). Friend gets 3 + 2 morphs at sign-up; sender gets +3 **when the friend's first morph succeeds** (not at sign-up — kills farming), via `grant_credits` keyed `referral:<friend_user_id>`. No audio is shared; the page shows the sender's handle and the demo.

**First-week gift.** Day 7, if ≥ 1 morph: `grant_credits(2, 'gift:week1', 'gift:week1:<user>')`; banner "One week in. Two morphs on us." Zero-job accounts get nothing.

**No dark patterns.** The 0-credit prompt states the exact state and consequence; "Not now" is the same size as the buy buttons; no countdown, no "only N left"; the subscription line says *"Renews monthly. 60 morphs expire at period end. Cancel anytime."* (§13 — undisclosed today); packs say "never expire"; free morphs never expire; a failed morph is never charged; export and deletion stay one click in the portal. Paywall: **"That was your last free morph. Nothing happens unless you buy."** — buttons "50 morphs · $9 once" / "60 a month · $7.99/mo" / "Not now".

#### 4. Support for one person

**Channels.** `support@` (primary, 24 h weekday SLO); Discord for community and the council — *not* a support channel ("answered when awake"); no live chat. In-plugin "Help" opens a pre-filled email with build, host, OS and last job id — never audio, never tokens.

**Twelve macros**

1. *Charged, no result* — "That shouldn't happen. I've refunded that morph and I'm looking at job `<id>`." → `refund_job(<id>, 'support:no_result')`.
2. *Paid, balance unchanged* — "Paddle order `<id>` hadn't reached us; applied by hand, reopen the plugin." → `grant_credits` keyed by the order id (ARCH §10).
3. *DAW doesn't list it* — rescan per host; Windows is x64 only; macOS installs system-wide; Logic: `killall -9 AudioComponentRegistrar`.
4. *SmartScreen / Gatekeeper* — expected with a new certificate; "More info → Run anyway"; how to verify with `signtool`/`spctl`.
5. *Stems bleed* — thanks, job id and genre, 60 s / 10 MB / 16-bit advice, refund if unusable; tag `quality:separation`.
6. *MIDI wrong* — same shape; bass is the strong case, melody is bonus; tag `quality:midi`.
7. *Wrong key* — "Tap the key selector; Scale-Snap follows it." Tag `quality:key`.
8. *Money refund* — the §6 rule; "Paddle pays in 5–7 days; unused morphs come off the balance."
9. *Cancel subscription* — "Manage subscription" in the portal; morphs stay until period end (§13).
10. *Delete / export* — self-serve in the portal (`/v1/me/export`, `DELETE /v1/me`); export first.
11. *Stuck at "Splitting"* — off-peak cold start; status page link; "if it fails, the morph comes back."
12. *Rights* — upload only what you own or license; audio deleted in 24 h; output is yours; copyright policy link.

**Escalation** (same person, different hat): any S1 (beta §6.2) or any ledger inconsistency → stop support, open a bug now; same cause ≥ 3 tickets in 7 days → next release; everything else → weekly review.

**Weekly quality review** (Monday, 45 min, written): Sentry issues by `role`; failed jobs by `error.code`; `release + refund ÷ reserve`; thumbs-down reasons; NPS verbatims; ticket tags; p50/p95 and cold-start count; spend vs budget. Output: three fixes into the next release; one status-page line if an SLO slipped.

**Quality gate per release:** `ctest` 34/34; `roundtrip.py` OK; pluginval L5 `--repeat 2 --randomise` on VST3 and AU; DAW matrix ★ rows on Mac and Windows; golden-set benchmark with no metric worse than −5 %; `python -m app.checks` green; `terraform validate`; `spctl`/`signtool verify`; no DO-NOT-PUBLISH banner; previous installer still downloadable.

#### 5. Feedback loops

| loop | mechanism | into the backlog |
|---|---|---|
| Thumbs on a result | `POST /v1/jobs/{id}/feedback {rating, reason ∈ bleed/wrong_key/midi_off/clicks/slow/other, note ≤ 140}` → `job_feedback` joined to job metadata (duration, bpm, confidences, error). Never the audio. | weekly review ranks reason × frequency; "unusable" triggers the §6 auto-refund |
| NPS at day 14 | in-plugin card 14 days after the first morph (fallback: Klaviyo email, already wired): 0–10 + "why?" → `nps_responses` | verbatims tagged onto the board; trend on the scorecard |
| Tester council | the beta cohort (10–20) in a private Discord channel; early builds; monthly 30-min call | council votes break ties; shipped items credit them in the changelog (beta §4) |
| Public roadmap | `/roadmap` Now / Next / Later with feedback counts; `/changelog` | one board, every item tagged by source; priority = frequency × severity |

#### 6. Pricing and offer quality

Per morph: $0.18 (pack), $0.13 (sub); contribution $7.93 / $6.94 per sale (ECON §5) — no cost-driven change needed. Three free *is* tight: one morph is a test, so the promise rests on two. Fix the feel without touching the headline:

* **Bundled demo morph** (0 credits) absorbs the test — all 3 go to real clips.
* **Unusable morphs are refunded** — 3 means 3 *good* morphs.
* **Earned morphs**: +2 at day 7, +3 per referred friend's first morph → 5–8 effective.
* No $3 starter pack: the fixed $0.50 fee (ECON §4) would eat 22 %.

**Wording.** "3 free morphs. 50 for $9, never expire. Or 60 a month for $7.99, cancel anytime." **Guarantee:** *"If a morph is unusable, that morph is refunded."*

**Refund rule — implementable today with `refund_job(p_job_id, p_reason)` (§6: reverses a captured job, idempotent):**

| condition | rule |
|---|---|
| eligible | `status = succeeded`; thumbs-down within 24 h of `finished_at`; reason ≠ `slow` |
| automatic | ledger `refund`, source `job:<id>`, `p_reason = 'user:unusable:<reason>'`; plugin balance updates at once |
| abuse bound | auto-refunds ≤ max(3, 20 % of captured jobs) per user per 30 days; free accounts ≤ 2 lifetime; beyond → support review (macro 5) |
| money | Paddle (MoR): full refund within 14 days if ≤ 5 morphs of the pack used; else credits only. Needs Paddle's refund event → `adjust_credits` negative + commission `void` (manual today, ARCH §10) |

#### 7. What to build

| P | item | effort | where |
|---|---|---|---|
| 0 | GPU benchmark + 20-clip golden set (latency, SDR, MIDI F1, key); replaces "2 s" with a measured p95 | M | backend/ops |
| 0 | External uptime check + status page with live numbers | S | ops/web |
| 0 | CloudWatch metric filters, job-failure alarm, `alarm_email` set, SMS | S | ops |
| 0 | Opt-in crash reporter in the plugin (Sentry native, `role=plugin`) | M | plugin |
| 0 | Apply analysis at the `result` event, before downloads finish (ARCH §5) | S | plugin |
| 0 | Bundled demo morph in the cache format, playable before sign-in | M | plugin |
| 0 | §3 strings; paywall rewrite with expiry disclosure and equal "Not now" | S | plugin |
| 0 | Thumbs + `POST /v1/jobs/{id}/feedback` + `job_feedback` | M | plugin/backend |
| 0 | Auto-refund endpoint on `refund_job` with the §6 bounds | S | backend/plugin |
| 0 | Supabase: confirm-before-grant, signup throttle (SECURITY §9) | S | ops |
| 1 | Version endpoint + update banner (README: planned, not built) | M | backend/plugin |
| 1 | Paddle refund event → `adjust_credits` + commission `void` | M | backend |
| 1 | Client timing event `drop_to_ready_ms` | S | plugin/backend |
| 1 | User referral codes, grant on friend's first morph, `/m/<code>` page | M | backend/web |
| 1 | Day-7 gift cron; day-14 NPS card | S | backend/plugin |
| 1 | Support read view: jobs + ledger by user (Retool over a replica) | M | ops |
| 1 | Serverless keep-warm schedule for US peak | S | ops |
| 2 | `/roadmap` + `/changelog` | S | web |
| 2 | Paid lane in the queue; shared (Redis) rate limits | M | backend |
| 2 | Tokens to Keychain/DPAPI | M | plugin |

---

**Краткое резюме (RU).** Tonamorph заслужит любовь одним сценарием: свой клип → C3 звучит как оригинал → G3 в тональности → `.mid` в piano roll. Десять критериев качества с целями и способом измерения; главный пробел — нет GPU-бенчмарка и краш-репортов в плагине. SLO: доступность 99.5 %, успешность морфов ≥ 99 %, p95 ≤ 10 s, ответ поддержки ≤ 24 h; при деградации включается `MAINTENANCE_MODE`, кредиты не сгорают. Оффер: 3 бесплатных морфа + демо без кредита + подарки (день 7, рефералы); гарантия «неудачный морф возвращается» реализуема через `refund_job` с лимитами против злоупотреблений. Работы — в §7 по приоритетам.

---

---

## Приложение C. Операционная система на MCP (отчёт спринта, English)

### Tonamorph growth operating system — MCP architecture

Discovery was read-only; nothing was created or sent.

#### 1. Inventory (verified in this session)

| Server | What it does for us | Access confirmed | Gaps |
|---|---|---|---|
| In-house `tonamorph-growth` (`growth/mcp_server/server.py`) | source → process (real credit-metered job) → script → ElevenLabs voiceover → Remotion 1080×1920 render → publish IG/FB/TikTok/YT → measure; licensing gate, AI disclosure, UTM+`ref` links, credit floor/budget, daily caps, idempotent publish | Code read | Rename to `tonamorph-growth`, CTA "3 free morphs"; TikTok/YouTube audits pending → private posts until then |
| Klaviyo | RW: lists, templates (HTML/DND), campaigns (send needs confirmation), profiles (upsert/bulk/subscribe), images, reports, metric aggregates | Account "Fitscan" (UPKgtg), sender indo@fitscan.io, 3 default lists, 0 flows, 0 segments | **Flows, segments, events are read-only** (no `create_flow`, `create_segment`, `create_event`); account is Fitscan-branded |
| Windsor.ai | Read 350+ connectors; **Klaviyo write actions verified: `create_flow` (metric/list trigger, delay, email-by-template, SMS, conditional split) and `update_flow_status`** | Trial plan, 0 connected accounts | Klaviyo must be connected in Windsor UI first |
| Coupler.io | Dataflows → datasets → DuckDB SQL via `get-data`; sources verified: TikTok Organic, YouTube, Instagram Insights, Facebook Page Insights, Klaviyo, Paddle, Sentry, Supabase/Postgres, Google Sheets | 0 credentials; MCP can create dataflows | Each source needs one OAuth click |
| Vercel | `create_git_project`, `get_web_analytics` (visits + custom `events`, `eventData/<prop>` dimensions), runtime errors/logs | Team "Greg's projects" (hobby), 0 projects | Custom events require Pro |
| Figma | `create_new_file`, `use_figma` (Plugin API JS), `download_assets`, `export_video`, FigJam diagrams | Pro team `team::1029523244465791539` | — |
| Miro | `board_create`, `canvas_create_from_svg`, `table_create`, `doc_create` | Authenticated | — |
| Higgsfield | video/image/TTS generation; workflows `ugc-website-video`, `ugc-product-video`, `thumbnail-generation`, `ad-multiplier`, `subtitles`; `virality_predictor`; TikTok direct publish with `is_aigc`, 13 posts/day cap | Free plan, 1 credit, 0 TikTok accounts | Credits + `tiktok_connect` |
| Motion.so | Brief-driven launch/explainer videos, 9:16, brand DESIGN.md | Authenticated, 0 credits | $5 / 200 credits ≈ 1 video |
| Descript | URL import → Agent Underlord edits (cuts, captions, filler removal) → publish | "Gregory's Drive" | — |
| Notion | Pages, databases, SQL over data sources | Team "General" (owner) | — |
| Google Calendar | Recurring events on hello@fitscan.io | RW | — |
| GitHub | Files, PRs, Actions triggers | RW | — |
| HubSpot | Contacts/deals/tickets RW | Portal not onboarded; CAMPAIGN needs upgrade | Not needed: Klaviyo owns CRM + email |
| Zapier | Klaviyo app found (15 write actions) | 0 actions enabled | **Paddle not in catalog** → Paddle→Klaviyo goes through the backend |
| Ahrefs | SEO/keywords/social | **"Insufficient plan" on every call** | Unusable |
| Adobe Express, Lucid, Idiolect, HyperFrames, Shopify, HuggingFace | Image retouch/resize; diagrams; voice-matched copy; hosted video (compose disabled from CLI); n/a; n/a | Available | Optional |
| Cloudflare, Dango | — | Failed to connect | Retry |

#### 2. Operating system for growth

One owner per job: the engine is the production line, external MCPs are the variant/creative layer and the reporting layer.

**Acquisition.** Core UGC = in-house engine (rights-cleared clip → real morph → 15 s short → publish with credit line, disclosure, UTM). Variant layer = Higgsfield: `ugc-website-video` (creator talks over real tonamorph.com screenshots), `ad-multiplier` (4–10 independent versions of one winner — different presenter/background/hook — this is how one idea reaches a second account without a duplicate render), `thumbnail-generation`, `virality_predictor` to rank hooks before posting. Motion.so = launch video and explainers. Descript = cut DAW screen recordings into shorts, burn captions. Figma = `Tonamorph identity` (logo, palette, type), 9:16/16:9 templates, YouTube covers, email header; exported with `download_assets` → Klaviyo `upload_image_from_url`. Miro = `Tonamorph growth ladder` board: five-touch funnel, experiment table, content calendar. Publishing: engine adapters for IG/FB/YT; TikTok via Higgsfield `tiktok_publish` until the engine's TikTok app passes audit.

**Activation (Klaviyo).** Lists: `Tonamorph users` (single opt-in, everyone), `Tonamorph newsletter` (only `marketing_opt_in = true`), `Tonamorph waitlist`. Backend sends metrics and profile properties (§3–4); flows fire on them.

**Monetisation.** `backend/app/routers/webhooks.py` already verifies Paddle and grants credits on `transaction.completed` with idempotency. Extend `_apply` to emit Klaviyo events `Purchase Completed`, `Subscription Cancelled`, `Refund Issued` and update `plan`/`credits_available`. No Zapier hop. Zero-credit and win-back emails carry per-user checkout URLs built by `/v1/plans?ref=` and passed as event properties.

**Retention.** NPS at day 14 (`/nps?score=` landing → `nps_submitted`), monthly product-update campaign to the newsletter list (template + campaign via Klaviyo MCP, send confirmed by founder), win-back flow with a bonus-morphs code.

**Analytics.** Vercel Web Analytics custom events (web, no PII); backend job metrics via a `growth_daily` SQL view in Supabase; Sentry for errors. Weekly scorecard: **Coupler**, not Windsor — Windsor is on Trial with nothing connected, Coupler exposes SQL directly. Six dataflows (TikTok Organic, YouTube, Instagram Insights, Klaviyo, Paddle, Supabase view) → datasets → I run `get-data` SQL → Notion page. Engine `report_metrics` stays the per-post truth, joined on `utm_content` = content item id.

#### 3. Event taxonomy

Product names are snake_case; the Klaviyo metric is the Title Case twin. Klaviyo receives events server-side (private key) since the MCP cannot create events.

| Event / Klaviyo metric | Fires when | Properties | Source | Consumers |
|---|---|---|---|---|
| `cta_clicked` | any CTA click | cta, location | web | Vercel |
| `signup_started` | signup form opened | — | web | Vercel |
| `signup_completed` / Signed Up | profile created | user_id, source (web/plugin), referral_code, utm_source/medium/campaign/content/term, marketing_opt_in | backend | Klaviyo (+list add, subscribe if opted in), Vercel (source only), dashboard |
| `plugin_downloaded` | download click | os | web | Vercel |
| `plugin_installed` / Plugin Installed | first `/v1/me` from a new device | os, daw, plugin_version | plugin→backend | Klaviyo, dashboard |
| `morph_started` | `POST /v1/jobs` accepted | job_id, duration_s, stems, source (plugin/api/engine) | backend | dashboard |
| `morph_completed` / Morph Completed | `complete_job` | job_id, latency_ms, credits_charged, balance_after, morphs_total, bpm, key | backend | Klaviyo, dashboard, Sentry breadcrumb |
| `morph_failed` / Morph Failed | job failed / timeout / 402 | job_id, error_code, stage, latency_ms | backend | Klaviyo, Sentry, dashboard |
| `credits_exhausted` / Credits Exhausted | balance_after = 0 or reserve refused | plan, checkout_url_pack_50, checkout_url_sub_monthly | backend | Klaviyo, dashboard |
| `paywall_viewed` | plugin shows `/v1/plans` prompt | plans_shown | plugin→backend | dashboard |
| `checkout_started` / Checkout Started | `/checkout` opened or plugin checkout click | plan_id, ref | web (+backend when authenticated) | Vercel, Klaviyo |
| `purchase_completed` / Purchase Completed | Paddle `transaction.completed` | plan_id, price_usd, credits, is_renewal, referral_code | backend | Klaviyo, dashboard |
| `subscription_cancelled` / Subscription Cancelled | Paddle `subscription.canceled` | plan_id, period_end | backend | Klaviyo, dashboard |
| `refund_issued` / Refund Issued | Paddle adjustment | amount_usd, reason | backend | Klaviyo (suppress win-back), dashboard |
| `nps_submitted` / NPS Submitted | `/nps` page | score, comment | web + backend | Vercel, Klaviyo, dashboard |
| `content_published` | engine `publish_video` | content_item_id, platform, angle, visibility, ai_flag_set | engine | dashboard |
| `content_metrics` | engine `report_metrics` | content_item_id, platform, views, likes, ctr, ctr_kind | engine | dashboard |
| `api_error` | unhandled 5xx | route, role | backend | Sentry |
| `health_probe` | cron GET `/v1/health` | ok, latency_ms | GitHub Actions | dashboard, alert |

Existing consent-gated snippet metric `Active on Site` stays as is.

#### 4. Klaviyo build spec

**Profile properties** (backend upsert, `external_id` = user_id): signup_source, referral_code, utm_*, marketing_opt_in, plan (free/credits/subscription), credits_available, morphs_total, first_morph_at, last_morph_at, daw, os, plugin_version, cohort_week, nps_score.

**Segments** (UI): `Activated` (Morph Completed ≥ 1), `Free no morph 48h`, `Paying` (plan ≠ free), `Dormant 30d` (Signed Up > 30 d, no Morph Completed or Purchase Completed in 30 d, no Refund Issued).

| Flow | Trigger metric | Filter / split | Steps and timing |
|---|---|---|---|
| 1 Welcome | Added to list `Tonamorph users` | — | 0 h "Your 3 morphs are waiting" (download + 60 s tutorial); +2 d if morphs_total = 0 "Drop any track"; +5 d if still 0, producer use-cases |
| 2 First morph | Morph Completed, trigger filter morphs_total = 1 | — | +30 min "You made an instrument" (3 angle ideas, share link with `ref`) |
| 3 Failed morph | Morph Failed | split: Morph Completed in last 1 h → exit | +20 min error_code-specific fix (≤10 MB, ≤60 s), reply-to founder; **transactional** |
| 4 Zero credits | Credits Exhausted | exit on Purchase Completed | 0 h plan comparison with per-user checkout URLs; +48 h social proof; +7 d last nudge |
| 5 Day-7 | Signed Up | delay 7 d, split morphs_total | 0 → one-question "what's blocking you?"; ≥1 and free → paid features + checkout; paying → exit |
| 6 Win-back | segment `Dormant 30d` | exclude Refund Issued | 0 h "new since you left" + bonus-morph code; +5 d final |
| 7 Purchase | Purchase Completed | split is_renewal | 0 h thanks + credit expiry + tips (**transactional**); +3 d first-purchase pro workflow; +14 d NPS ask |

**What the MCP can create:** lists (`create_list`), templates (`create_email_template` CODE HTML with `{% unsubscribe %}`, images via `upload_image_from_url`, checks via `render_email_template`, test send via `create_template_preview_send_job` with your confirmation), campaigns (`create_campaign` + `assign_template_to_campaign_message`; `send_campaign` requires confirmation), profiles. **Flows:** the Klaviyo MCP only reads (`get_flows`, `get_flow_report`). Path A: Windsor `create_flow` builds flows 1–5 and 7 in draft (metric/list triggers, delays, conditional splits, `template_id`), `update_flow_status` sets them live — requires Klaviyo connected in Windsor. Path B: UI. **UI only:** flow 6 (segment trigger), segments, transactional flag, smart sending. Metrics exist only after their first event, so the backend must send one test event per metric before flows referencing them can be created.

#### 5. Automation runbook

**Daily, automated.** 15:00 UTC (US morning): engine `run_daily_batch(count=3, dry_run=false)` then `report_metrics(since=-48h)`; Klaviyo flows self-run; `get_runtime_errors(24h)` + Sentry digest; health cron every 5 min. **Daily, human (15 min):** approve tomorrow's captions and hook variants (virality score above threshold), read the batch `credits` block, answer failed-morph replies.

**Weekly, automated → me.** Monday: Coupler `run-dataflow` ×6, `get-data` scorecard SQL, Klaviyo `get_flow_report`/`get_campaign_report`, Vercel aggregate by `utm_content`, Notion "Week N" page, Miro experiment rows. **Weekly, human:** choose angles, record one DAW session for Descript, write licence manifests for new clips, approve campaign send.

**Monthly:** product-update campaign, NPS read, win-back code rotation, thumbnail refresh.

**Guardrails.**
- Licensing gate: engine refuses uncleared clips; Higgsfield/Motion/Descript outputs use engine-rendered audio or voiceover only; never platform music libraries (`tiktok_music_*` unused).
- AI disclosure: engine caption line + platform flags; Higgsfield `tiktok_publish` always `is_aigc=true`; Motion/Descript outputs get the same caption line from a template.
- Credit budget: `GROWTH_CREDIT_FLOOR=5`, `GROWTH_CREDIT_BUDGET=3/day`; Higgsfield `get_cost` preflight, monthly cap; Motion 200-credit packs, no auto-topup.
- Rate limits: engine caps IG 3/day (platform 25), YT 2/day (quota ≈ 6), FB 2/day, TikTok ≤ 3/day (Higgsfield cap 13); Klaviyo template render 3/s, flow creation 100/day; API 10 submissions/min.
- Ban risk: warm-up — new accounts post manually once a day and engage 10 min/day for 14 days before any API post; one content item → one account per platform; cross-account only via `ad-multiplier`/Descript re-cuts with different hook, presenter, caption; TikTok private until audit; own-brand disclosure on; no engagement pods.

#### 6. Service-quality measurement

| SLO | Target | Source → tool |
|---|---|---|
| `/v1/health` availability | 99.5 % / month | GitHub Actions 5-min probe → issue on failure (optional external monitor, founder click) |
| Morph success rate | ≥ 98 % | jobs table → `growth_daily` view → Coupler Supabase |
| Morph latency | p50 ≤ 8 s, p95 ≤ 14 s | same view |
| Errors | 0 new unresolved Sentry issues/week; 0 Vercel runtime errors/24 h | Coupler Sentry source; `get_runtime_errors` |
| Refund rate | < 2 % of transactions / 30 d | Paddle → Coupler |
| Email health | delivery ≥ 98 %, bounce < 2 %, spam < 0.1 %, unsub < 0.5 % | `get_flow_report`, `get_campaign_report` |
| Content compliance | `ai_flag_set` 100 %, posts ≤ caps | engine store |
| North-star | sign-ups per 1,000 views by angle; activation ≥ 40 %; free→paid ≥ 3 % | Vercel `utm_content` × Klaviyo × engine |

**Weekly review, automatic:** Monday 06:00 UTC Claude Code Routine → I pull Coupler, Klaviyo, Vercel and engine data, compose the scorecard and SLO table, `notion-create-pages` under "Weekly reviews", create a 30-min Calendar event Monday 10:00 with the link; any red SLO opens a GitHub issue `slo-breach`.

**Alert routing for one person:** P1 (health down 10 min, job success < 90 % over 1 h, Paddle webhook 5xx) → Sentry/uptime push to phone; P2 (new Sentry issue, refund, deliverability spike) → email digest twice daily; P3 (content, growth metrics) → weekly Notion page. One inbox, no Slack.

#### 7. 14-day setup plan

| Day | Action | Who |
|---|---|---|
| 1 | Klaviyo: create Tonamorph account or rebrand Fitscan, sender domain DKIM/DMARC; Vercel Pro if custom events wanted | founder must click |
| 1 | Notion: "Tonamorph Growth" hub page + "Weekly reviews" database; Calendar: recurring "Daily growth check" 09:00, "Weekly review" Mon 10:00 | I can do via MCP |
| 2 | Figma: `create_new_file` "Tonamorph identity" (planKey `team::1029523244465791539`), `use_figma` logo lockups, palette, 9:16/16:9 templates, email header; `download_assets` | I can do via MCP (founder approves) |
| 3 | Vercel: `create_git_project` the repository, rootDirectory `tonamorph/web`, teamId `team_HhW3kqCH1QeY61ghjGRTLf33`; GitHub PR adding `track()` calls for the web events | I can do via MCP |
| 3 | DNS, `NEXT_PUBLIC_KLAVIYO_COMPANY_ID`, Paddle client token | founder must click |
| 4 | GitHub PR: `app/services/klaviyo.py` (Create Event + profile upsert), hooks in signup, `complete_job`, failure path, Paddle `_apply`, `/v1/nps`; `growth_daily` view; health-probe workflow | I can do via MCP |
| 4 | Set `KLAVIYO_PRIVATE_API_KEY`, deploy, send one test event per metric | founder must click |
| 5 | Klaviyo: `create_list` ×3, `upload_image_from_url`, `create_email_template` ×12, `render_email_template`, preview sends | I can do via MCP (send confirmation from founder) |
| 5 | Segments ×4 in Klaviyo UI; connect Klaviyo in Windsor.ai | founder must click |
| 6 | Windsor `execute_action create_flow` ×6 (flows 1–5, 7, draft) with template ids; verify with `get_flow` | I can do via MCP |
| 6 | Flow 6 (segment trigger), transactional flags, set live (or I run `update_flow_status` after OK) | founder must click |
| 7 | GitHub PR: rename `tonamorph-growth`, CTA "3 free morphs", `GROWTH_LANDING_URL`, `GROWTH_REFERRAL_CODE`, caps | I can do via MCP |
| 7 | Licensed clips + manifests; create IG pro/FB page, YouTube, TikTok accounts; start manual warm-up | founder must click |
| 8 | Buy Higgsfield credits, `tiktok_connect`; Motion Flex $5 | founder must click |
| 8 | Higgsfield `ugc-website-video` ×2 hooks + `virality_predictor`; Motion `create_video` launch explainer (9:16); Descript import + captions on DAW recording | I can do via MCP |
| 9 | Miro: `board_create` "Tonamorph growth ladder", funnel via `canvas_create_from_svg`, experiments `table_create` (angle/hook/platform/status/sign-ups per 1k views) | I can do via MCP |
| 10 | Coupler credentials: TikTok Organic, YouTube, Instagram Insights, Klaviyo, Paddle, Supabase, Sentry | founder must click |
| 10 | Coupler `create-dataflow` ×7 + sources/destinations, `run-dataflow`, `get-schema` | I can do via MCP |
| 11 | Engine `run_daily_batch(count=2, dry_run=true)`, then YouTube private + IG publish; Higgsfield `tiktok_publish` mode `UPLOAD_TO_DRAFT` | I can do via MCP (founder reviews posts) |
| 12 | Klaviyo `create_campaign` "Launch week" to newsletter list, `get_campaign_recipient_estimation` | I can do via MCP; `send_campaign` confirmed by founder |
| 13 | Vercel `get_runtime_errors` baseline; GitHub `slo-breach` issue template; scorecard SQL saved in Notion; Sentry alert rules | me / founder clicks Sentry rules |
| 14 | First weekly review end to end → Notion "Week 1", Calendar event, blocker list (audits, warm-up, plan upgrades) | I can do via MCP |

Repo paths referenced: `tonamorph/growth/mcp_server/server.py`, `tonamorph/backend/app/routers/webhooks.py`, `tonamorph/web/src/app/signup/SignupForm.tsx`, `tonamorph/web/src/components/CookieConsent.tsx`.

---

**Краткое резюме (RU).** Проверены все MCP-серверы сессии: Klaviyo доступен на запись для списков, шаблонов, кампаний и профилей, но flows, сегменты и события — только чтение; flows можно создавать через Windsor.ai (`create_flow`), после подключения Klaviyo в Windsor. Ahrefs недоступен (Insufficient plan), Zapier без действий и без Paddle, Coupler/Windsor без подключённых источников, Higgsfield/Motion без кредитов, Vercel без проектов. Ядро — собственный движок `tonamorph-growth` (лицензионный гейт, AI-дисклеймер, UTM+ref, лимит кредитов); Higgsfield/Motion/Descript — варианты и хуки; Figma — айдентика; Miro — доска; Coupler+Notion — недельный скоркард и SLO-обзор. Таксономия событий, спецификация 7 flows и план на 14 дней выше, с пометкой, что делаю я через MCP, а что кликает основатель.