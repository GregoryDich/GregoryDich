# Чек-лист запуска — твои шаги

Дата документа: 2026-09-09. Источники: план запуска (шаги 0–8), аудит готовности,
юридический отчёт, отчёт по названию, рыночный отчёт, `docs/API_CONTRACT.md`,
`backend/.env.example`, `infra/aws/README.md`, `infra/supabase/config.md`, `db/README.md`.

---

## 0. Как пользоваться этим документом

**Разделение труда.** «Я» — ассистент: всё, что делается кодом, текстом, SQL и через MCP
(Vercel, GitHub, Klaviyo). «Ты» — только то, что требует твоей личности (паспорт, teudat
osek murshe, селфи-проверка), твоей карты или твоего физического устройства (Mac M4,
Keychain, Windows-машина). Каждый твой шаг ниже рассчитан на 5–15 минут и написан так,
чтобы его можно было выполнить буквально: где нажать, что вставить, куда положить результат.

**Порядок.** Раздел 1 — решения, без которых остальное не имеет смысла. Раздел 2 — аккаунты
и сервисы, каждый как чек-бокс с подпунктами; их можно делать в любом порядке, кроме
явных зависимостей (например, Paddle проверяет сайт, поэтому сайт раньше Paddle). Раздел 3
собирает всё в календарь. Разделы 4–5 — юрист/бухгалтер и открытые вопросы.

**Легенда.**

| знак | значение |
|------|----------|
| ⏱ | сколько это займёт у тебя |
| 💳 | сколько стоит (и когда списывается) |
| 🔑 | что получаешь на выходе и **куда именно** это положить: точное имя секрета или переменной |
| ✅ | как понять, что сработало |

**Про имена переменных.** В этом файле используются имена переменных и секретов *в том
виде, в каком они существуют в коде сегодня* (`SNAPPLAY_PIPELINE`, `snapplay-worker`,
`ai.snapplay.plugin`, префикс `snapplay-prod` в Terraform). После решения №1 я переименовываю
репозиторий целиком, и эти идентификаторы поменяются; тогда я обновлю и этот документ.
Пока — копируй как есть, чтобы всё совпадало с кодом.

**Плейсхолдеры.** `<domain>` — домен из решения №1 (например `stemkeys.com`);
`<Имя>` — название продукта; `<ref>` — идентификатор проекта Supabase
(`https://<ref>.supabase.co`); `<repo>` — `owner/name` нового репозитория.

---

## 1. Решения, без которых дальше нельзя

| # | Решение | Варианты | Моя рекомендация | 💳 Цена | Что блокирует |
|---|---------|----------|------------------|---------|---------------|
| 1 | **Название и домен** | StemKeys · NoteBreak · TrackBreak (см. ниже) | **StemKeys** + `stemkeys.com` | `stemkeys.com` $11.25/год; `stemkeys.app` $9.99/год; `stemkeys.io` $30/год; `stemkeys.ai` $160/2 года; `notebreak.ai` $160/2 года (цены Vercel) | **Всё.** Идентификаторы плагина (`BUNDLE_ID`, коды `Snpl`/`Snap`) после первого релиза менять нельзя — DAW-проекты ссылаются на них навсегда. Переименование идёт первым. |
| 2 | **Лицензия весов Demucs** | (a) письменный грант от Meta · (b) замена модели · (c) коммерческий API разделения | **(b)**, если найдётся 4-стемный чекпойнт с подтверждённой MIT; иначе **(c)** на запуск | (a) $0, но недели–месяцы и без гарантии; (b) $0 лицензия + моё время на интеграцию и бенчмарк; (c) поштучная цена вендора — переделывает всю экономику (`docs/ECONOMICS.md`) | **Продажу.** Веса `htdemucs` — «only for scientific purposes» (см. ниже). Код Demucs — MIT, проблема только в весах и датасете. |
| 3 | **Платёжный провайдер** | Paddle · Lemon Squeezy | **Paddle** | оба 5 % + 50 ¢ с продажи; Paddle — без отдельной платы за чарджбэк; LS — $15 за спор и 1 % за международную выплату | Чекаут, вебхуки, `plans.provider_variant_ids` → без них пейволл без кнопок. Lemon Squeezy в 2026 — только по инвайту (waitlist); Paddle принимает физлиц/sole traders, Израиль в списке поддерживаемых. |
| 4 | **Rubber Band** | купить коммерческую лицензию · собирать с `SNAPPLAY_USE_RUBBERBAND=OFF` | **OFF на запуск**, купить, когда появится выручка | лицензия — разовая, бессрочная, без роялти; цена не публикуется, нужен запрос на breakfastquay.com | Release-сборку. GPL-вариант в закрытом плагине распространять нельзя. С `OFF` работает резервный ресемплинг (Lagrange): длительность стема меняется на `2^(-semitones/12)` — хуже, но легально. |
| 5 | **JUCE tier** | Starter (бесплатно) · Indie · Pro | **Starter** сейчас; Indie в месяц, когда выручка за 12 мес. превысит $20k | Starter $0 (лимит $20k/год валовой выручки, без сплэш-скрина в JUCE 8); Indie $40–50/мес или $800–1000 бессрочно (лимит $500k) — источники расходятся; Pro $130/мес | Ничего прямо сейчас. Упоминание в `THIRD_PARTY_LICENSES.md`. |
| 6 | **Где жить репозиторию** | оставить `GregoryDich/GregoryDich` · новый приватный `GregoryDich/<name>` · организация `<name>/<name>` | **Организация `<name>/<name>`, приватный** | $0 | GitHub Secrets/Variables, OIDC-доверие деплой-роли (`github_repository` в Terraform), импорт проекта в Vercel, Vercel GitHub App. |
| 7 | **Где крутится control plane (API)** | существующий AWS-сервер через `infra/docker-compose.yml` · Terraform ECS Fargate | **Существующий сервер**, если тянет (см. 2.8); ECS — потом | сервер уже оплачен; ECS-baseline ≈ $75/мес без GPU | Куда класть `.env`, где живёт `api.<domain>`, какие GitHub Variables нужны. |

### 1.1 Название — почему StemKeys и что не так с остальными

Кодовое имя **SnapPlay** отвергнуто и нигде дальше в этом документе не используется как
название продукта; 1154 вхождения в 166 файлах переименовываются мною после твоего «да».

* **StemKeys** — единственный кандидат с пустым пространством имён: ни торговой марки, ни
  GitHub-пользователя/репозитория, ни npm/PyPI, ни продукта в KVR/Plugin Boutique, ни
  соцхэндлов в индексе, и одновременно свободные `.com` и `.ai`. Опасение насчёт марки
  STEMS у Native Instruments не подтвердилось: регистрации STEMS как словесной марки не
  найдено, формат был объявлен открытым, слово «stems» — отраслевой термин, NI в
  процедуре несостоятельности с января 2026. Реальный (не фатальный) риск — живая марка
  **STEM** у Stem Disintermedia (Reg. 5023828, класс 42, софт для музыкальной индустрии).
  Минусы коммерческие: «stems» — самое конкурентное слово в категории, а «STEM» для
  непосвящённых читается как наука/образование.
* **NoteBreak** — юридически самый сильный (придуманное слово), но имя занято в твоей же
  индустрии: продюсер NoteBreak держит `@notebreak` на X, SoundCloud, Pinterest, YouTube,
  Last.fm, и его трек — аутро Mark Rober (~70M подписчиков). Первая страница поиска —
  чужая музыка навсегда. `notebreak.com` занят.
* **TrackBreak** — «trackbreak» уже термин в аудио-софте (маркер разрезания записи в
  VinylStudio) → описательное, слабое для регистрации в классе 9; рядом Trackbreakers
  (музмаркетинг). `trackbreak.com` — паркинг HugeDomains.

Ни одна база торговых марок (USPTO/EUIPO/WIPO) напрямую не проверялась — только выдача
поисковиков. Это скрининг, не клиренс; см. раздел 4 (юрист).

**Ты:** одно слово в ответ — какое имя. Домен куплю через Vercel MCP с твоей карты только
после явного «да» на конкретную сумму (2.1).

### 1.2 Demucs — детали для решения №2

* Файл LICENSE в репозитории — MIT, но MIT покрывает «software and associated documentation
  files». Веса не лежат в репо (скачиваются с `dl.fbaipublicfiles.com`) и ничем не покрыты.
  Мейнтейнер (Défossez) в issue #327 (2022-05-23): *«The model weights are not covered by
  the MIT license, and are provided only for scientific purposes»* — цитата из двух
  вторичных источников, сам тред был заблокирован прокси. **Открой
  `https://github.com/facebookresearch/demucs/issues/327` и сделай скриншот** прежде чем
  решать.
* Датасет MUSDB18-HQ — «educational purposes only», часть треков CC BY-NC-SA. Конвертация в
  ONNX/CoreML лицензию не «отмывает». Репозиторий заархивирован 2025-01-01, Défossez ушёл
  из Meta — просить грант придётся у Meta Legal.
* Кандидаты на замену (из отчёта):
  * **Mel-Band RoFormer (модели Kim)** — по карточке на Hugging Face перелицензированы с
    GPL-3.0 на **MIT** 2026-04-22, веса включены; по вокалу лучше htdemucs. Но это
    вокал/инструментал, а не 4 стема — для bass/drums/other нужны другие чекпойнты, и
    лицензию каждого надо проверить на репозитории автора и заархивировать текст в день
    релиза.
  * **Open-Unmix** — код MIT, веса `umxl` явно CC BY-NC-SA 4.0; `umxhq`/`umx` обучены на
    MUSDB18. Не подходит.
  * **Spleeter** — код MIT, про веса README молчит, Deezer продаёт Spleeter Pro. Не подходит.
  * **Коммерческий API** — AudioShake, Music.ai/Moises, LALAL.AI продают B2B/API. Убирает
    GPU-хостинг и юридический риск, добавляет поштучную себестоимость и зависимость.
* Серверные GPL/LGPL-зависимости (`aubio` GPL-3.0, `libsndfile` LGPL) — **не блокер**: они
  работают только на сервере и не распространяются. В плагине их нет.
* Бета на `htdemucs` с реальными людьми — серая зона («scientific purposes»). Мой совет:
  сменить движок до публичной беты, и в любом случае до первого платежа. Вопрос юристу №1.

---

## 2. Аккаунты и сервисы

### 2.1 Домен (Vercel)

- [ ] **Купить домен** ⏱ 5 мин 💳 см. таблицу в разделе 1
  1. Скажи мне «покупай `<domain>` за $X» — я вызываю Vercel MCP `buy_domain` (списание с
     карты, привязанной к твоему Vercel-аккаунту). Либо сам: vercel.com → **Domains** →
     **Buy** → введи домен → **Buy** → карта.
  2. Если название StemKeys, минимальный набор: `stemkeys.com`. `.app` и `.ai` — по желанию,
     для защиты (редиректы на `.com`).
  3. Vercel сам становится DNS-провайдером домена — все записи ниже (A для `api.`, TXT для
     Resend, TikTok, Meta; MX для почты) добавляются в vercel.com → Domains → `<domain>` →
     **DNS Records**.
  4. ✅ `dig +short NS <domain>` показывает `ns1.vercel-dns.com`, `ns2.vercel-dns.com`.
  5. 🔑 `<domain>` → `NEXT_PUBLIC_SITE_URL=https://<domain>`,
     `AUTH_SITE_URL=https://<domain>`, `GROWTH_LANDING_URL=https://<domain>`,
     `NEXT_PUBLIC_API_URL=https://api.<domain>`.

- [ ] **Почта на домене** ⏱ 10 мин 💳 $0
  Нужны адреса `support@`, `privacy@`, `legal@`, `noreply@` — они пойдут в юридические
  тексты, в Vercel env и в заявки Meta/TikTok (Meta быстрее верифицирует бизнес с почтой
  на домене, а не с Gmail). Самый дешёвый путь — пересылка на твой Gmail:
  1. improvmx.com → **Add domain** → `<domain>` → он покажет две MX-записи и одну TXT (SPF).
  2. Vercel → Domains → `<domain>` → DNS Records → добавь их (тип MX, имя `@`, значения
     `mx1.improvmx.com` приоритет 10 и `mx2.improvmx.com` приоритет 20; TXT `@` со
     значением SPF, которое покажет ImprovMX).
  3. В ImprovMX создай алиасы `support`, `privacy`, `legal` → твой Gmail; `*` (catch-all) —
     по желанию.
  4. ✅ Отправь письмо на `support@<domain>` с другого ящика — оно пришло в Gmail.
  5. 🔑 `NEXT_PUBLIC_SUPPORT_EMAIL=support@<domain>`, `NEXT_PUBLIC_PRIVACY_EMAIL=privacy@<domain>`,
     `NEXT_PUBLIC_LEGAL_EMAIL=legal@<domain>`. Исходящую почту (подтверждения регистрации)
     отправляет не ImprovMX, а Resend — см. 2.3, шаг «SMTP».

### 2.2 GitHub — репозиторий и окружение

- [ ] **Создать репозиторий** ⏱ 5 мин 💳 $0
  1. github.com → **Your organizations** → **New organization** → Free → имя `<name>` (или
     пропусти организацию и создай репозиторий под своим логином — решение №6).
  2. **New repository** → имя `<name>` → **Private** → без README (я перенесу subtree сам).
  3. Скажи мне `owner/name` — перенос истории и первый пуш делаю я через GitHub MCP.
  4. **Settings → Environments → New environment** → имя ровно `production` → **Required
     reviewers** → добавь себя → Save. Это тот approve, которого ждёт `deploy.yml` перед
     `terraform apply` (нужно только для пути ECS; для docker-compose не мешает).
  5. ✅ Репозиторий приватный, окружение `production` с тобой как ревьюером.
  6. 🔑 `<repo>` → переменная Terraform `github_repository` (в `production.tfvars` сейчас
     `GregoryDich/GregoryDich`; меняю я) и Vercel-импорт (2.9).

- [ ] **Где вводить секреты и переменные** (пригодится во всех шагах ниже)
  * Секреты: репозиторий → **Settings → Secrets and variables → Actions → Secrets → New
    repository secret**. Многострочные значения (например `.p8`) вставляются как есть.
  * Переменные (не секретные): та же страница → вкладка **Variables → New repository
    variable**.
  * Сводная таблица всех имён — в 2.10.

### 2.3 Supabase

- [ ] **Проект** ⏱ 5 мин 💳 Pro $25/мес (Free нельзя: бесплатные проекты **ставятся на паузу
  после 7 дней без активности**, а плагин в проде на такое не рассчитан)
  1. supabase.com → **New project** → организация → имя `<name>-prod`.
  2. **Database password** — сгенерируй и сохрани в менеджере паролей: это пароль для `psql`
     и миграций.
  3. **Region — реши EU vs US** (см. врезку ниже). Рекомендация: **`eu-central-1` (Frankfurt)**.
  4. Plan → **Pro**. → **Create new project**, подожди 2–3 минуты.
  5. ✅ Дашборд проекта открывается; **Project Settings → General → Reference ID** — это `<ref>`.

  > **EU или US?** GDPR не запрещает хранить данные европейцев в США, но требует DPA со
  > стандартными договорными условиями и честного ответа в Privacy Policy «где данные».
  > Регион в ЕС убирает этот абзац из политики и из головы. Израиль имеет решение ЕС об
  > адекватности, так что EU→Израиль (ты как контролёр) — не проблема. Латентность: на один
  > запрос плагина API делает несколько вызовов в PostgREST, каждый трансатлантический хоп
  > +80–100 мс — поэтому **Supabase и API-сервер должны быть в одном регионе**. Если твой
  > AWS-сервер в `us-east-1`, выбор такой: (а) Supabase в `us-east-1` и абзац про США в
  > политике, или (б) Supabase во Франкфурте и API-сервер тоже в ЕС (новый инстанс или
  > ECS в `eu-central-1`). Аудитория — «продюсер в Берлине», так что я за (б); скажи регион
  > своего сервера (2.8), и я зафиксирую.

- [ ] **Ключи и секреты** ⏱ 5 мин
  1. **Project Settings → API**:
     * **Project URL** → 🔑 `SUPABASE_URL` (backend `.env`, Modal-секрет, GitHub Variable
       `SUPABASE_URL` для ECS) и `NEXT_PUBLIC_SUPABASE_URL` (Vercel).
     * **anon public** → 🔑 `SUPABASE_ANON_KEY` (backend) и `NEXT_PUBLIC_SUPABASE_ANON_KEY`
       (Vercel). Если дашборд показывает новые ключи `sb_publishable_…`/`sb_secret_…`,
       legacy-ключи лежат под **Legacy API keys** — бери их, бэкенд тестировался с ними.
     * **service_role** → 🔑 `SUPABASE_SERVICE_ROLE_KEY` — **только** backend `.env`,
       Modal-секрет и AWS Secrets Manager. Никогда в Vercel, плагин или `growth/`.
  2. **Project Settings → API → JWT Settings**:
     * если есть **JWT Secret** (HS256) → 🔑 `SUPABASE_JWT_SECRET`, а `SUPABASE_JWKS_URL`
       оставь пустым;
     * если проект на асимметричных ключах (ES256/RS256, раздел **JWT Signing Keys**) →
       🔑 `SUPABASE_JWKS_URL=https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`, а
       `SUPABASE_JWT_SECRET` пустой. Нужен ровно один из двух.
  3. **Project Settings → Database → Connection string → URI** (порт 5432, «Direct» или
     «Session pooler») → подставь пароль → это `DATABASE_URL` для миграций (только для
     твоего терминала, в конфиг не идёт).

- [ ] **Применить миграции** ⏱ 10 мин
  Вариант A — `psql` (проще, ничего ставить кроме `brew install libpq`):
  ```sh
  cd snapplay-ai
  export DATABASE_URL='postgresql://postgres.<ref>:<пароль>@<host>:5432/postgres'
  for f in db/migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
  ```
  Вариант B — Supabase CLI (`brew install supabase/tap/supabase`):
  ```sh
  cd snapplay-ai
  supabase login
  supabase link --project-ref <ref>
  for f in db/migrations/*.sql; do
    supabase migration new "$(basename "$f" .sql)"
    cp "$f" "$(ls -t supabase/migrations/*.sql | head -n 1)"
  done
  supabase db push
  ```
  **Не применяй** `db/tests/00_local_auth_shim.sql` — он только для локального кластера.
  ✅ В **SQL Editor**: `select id, credits, price_cents from public.plans order by sort_order;`
  → три строки `free/3/0`, `pack_50/50/900`, `sub_monthly/60/799`.
  ✅ `select tgname from pg_trigger where tgname = 'on_auth_user_created';` → одна строка.

- [ ] **pg_cron и очистка** ⏱ 3 мин
  1. **Database → Extensions** → найди `pg_cron` → **Enable**.
  2. **SQL Editor** → вставь содержимое `infra/supabase/cleanup.sql` → **Run** (файл
     идемпотентный, можно повторять).
  3. ✅ `select jobname, schedule from cron.job;` → `snapplay_expire_credits`,
     `snapplay_reap_stale_jobs`, `snapplay_purge_expired_jobs`. Второй — страховка от
     «воркер умер, кредит списался» для не-AWS деплоя.

- [ ] **Storage bucket `jobs`** ⏱ 3 мин (по `infra/supabase/config.md` §1)
  1. **Storage → New bucket** → name `jobs` → **Public bucket: OFF** → Additional
     configuration: file size limit `64 MB`, allowed MIME types
     `audio/wav, audio/x-wav, audio/midi, audio/x-midi, application/json` → Save.
  2. **Не добавляй** политики на `storage.objects` для `anon`/`authenticated`: к бакету
     ходит только service-role-ключ, пользователи получают подписанные URL на 24 ч.
  3. ✅ Бакет `jobs` в списке с пометкой Private.
  4. 🔑 `STORAGE_BACKEND=supabase`, `STORAGE_BUCKET=jobs` в backend `.env` и в Modal-секрете.

- [ ] **Auth: провайдер и URL-ы** ⏱ 5 мин
  1. **Authentication → Providers → Email**: Enable ON; **Confirm email ON**; Secure email
     change ON; Minimum password length `8`.
  2. **Authentication → URL Configuration**:
     * **Site URL**: `https://<domain>`
     * **Redirect URLs** → Add: `https://<domain>/auth/confirm`,
       `https://<domain>/auth/reset-password`, `https://*-<vercel-project>.vercel.app/auth/confirm`
       (для preview-деплоев), `http://localhost:3000/auth/confirm`,
       `http://localhost:3000/auth/reset-password` (для разработки).
     Без первых двух GoTrue молча подставит свой Site URL, и письма поведут не туда
     (комментарий в `backend/.env.example` к `AUTH_SITE_URL`).
  3. **Authentication → Sessions** (в старом дашборде — Settings): Access token (JWT)
     expiry `3600`; **Refresh token rotation ON**, reuse interval `10` с.
  4. **Authentication → Rate Limits**: sign-ups/sign-ins per IP — оставь по умолчанию
     (30 / 5 мин); «emails per hour» поднимешь после подключения SMTP (следующий шаг).
  5. **Не включай CAPTCHA** (Authentication → Attack Protection → Bot and Abuse
     Protection): плагин логинится через `POST /v1/auth/token` и капчу решить не сможет.
  6. ✅ На странице URL Configuration — Site URL и 5 redirect-URL.
  7. 🔑 Тот же `https://<domain>` → `AUTH_SITE_URL` (backend) и `NEXT_PUBLIC_SITE_URL` (Vercel).

  > Про 3 кредита: триггер `on_auth_user_created` срабатывает при вставке в `auth.users`,
  > то есть **до** подтверждения почты. Но с «Confirm email ON» неподтверждённый пользователь
  > не получит JWT (`/v1/auth/token` ответит ошибкой), так что кредиты у него есть, а
  > дотянуться до них нельзя. Это проверяем вместе в разделе 3, день 1.

- [ ] **SMTP через Resend** ⏱ 10 мин 💳 $0 (3 000 писем/мес, 100/день)
  Встроенный почтовик Supabase — **3 письма в час** на весь проект и письма от
  `noreply@mail.app.supabase.io`; на бету этого не хватит.
  1. resend.com → Sign up → **Domains → Add Domain** → `<domain>` (регион — ближайший к
     Supabase) → он покажет DNS-записи: TXT для DKIM (`resend._domainkey`), MX + TXT для
     return-path (`send.<domain>`).
  2. Vercel → Domains → `<domain>` → DNS Records → добавь ровно эти записи → в Resend
     нажми **Verify** (до 15 минут).
  3. Resend → **API Keys → Create API Key** → имя `supabase-smtp`, permission **Sending
     access**, домен `<domain>` → скопируй `re_…` (показывается один раз).
  4. Supabase → **Project Settings → Authentication → SMTP Settings** → **Enable Custom
     SMTP**: Sender email `noreply@<domain>`, Sender name `<Имя>`, Host `smtp.resend.com`,
     Port `465`, Username `resend`, Password — ключ `re_…` → Save.
  5. **Authentication → Rate Limits → Rate limit for sending emails** → `30` в час
     (появится после включения custom SMTP). Minimum interval between emails — `60` с.
  6. ✅ Authentication → Users → **Invite user** на свой второй адрес → письмо пришло от
     `noreply@<domain>`, в Resend → Emails статус Delivered.

- [ ] **Шаблоны писем** ⏱ 10 мин — **Authentication → Emails** (Email Templates), для
  каждого шаблона замени Subject и Body целиком. Ссылки ведут на `/auth/confirm` сайта;
  `type` в каждом шаблоне свой — это значения, которые GoTrue принимает в `verifyOtp`.
  Страницу `/auth/confirm` делаю я; для `recovery` она перебрасывает на `/auth/reset-password`.

  **Confirm signup** — Subject: `Confirm your <Имя> account`
  ```html
  <h2>Confirm your email</h2>
  <p>Thanks for signing up for <Имя>. Confirm your address to activate your account and
  your 3 free credits.</p>
  <p><a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email">Confirm my email</a></p>
  <p>If you did not create this account, ignore this email — nothing will happen.</p>
  <p style="color:#888;font-size:12px">The link expires in 24 hours. Sent by <Имя>, {{ .SiteURL }}</p>
  ```

  **Reset password** — Subject: `Reset your <Имя> password`
  ```html
  <h2>Reset your password</h2>
  <p>Someone asked to reset the password for {{ .Email }}. If it was you, use the link
  below; if not, ignore this email and your password stays unchanged.</p>
  <p><a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=recovery">Choose a new password</a></p>
  <p style="color:#888;font-size:12px">The link expires in 1 hour. Sent by <Имя>, {{ .SiteURL }}</p>
  ```

  **Magic link** (только сайт; плагин им не пользуется) — Subject: `Your <Имя> sign-in link`
  ```html
  <h2>Sign in to <Имя></h2>
  <p><a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=magiclink">Sign in</a></p>
  <p>If you did not request this link, ignore this email.</p>
  ```

  **Change email address** — Subject: `Confirm your new <Имя> email`
  ```html
  <h2>Confirm your new email</h2>
  <p>Confirm that you want to change your <Имя> sign-in address to {{ .NewEmail }}.</p>
  <p><a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email_change">Confirm the change</a></p>
  ```
  ✅ Регистрация на preview-сайте → письмо приходит с этими текстами, ссылка ведёт на `<domain>`.

### 2.4 Paddle

Paddle проверяет **сайт** (Terms, Privacy, Refund policy, видимые цены, описание продукта)
и **личность** — подавайся, когда сайт с юридическими страницами уже на `<domain>`
(2.9), и подавайся **раньше запуска**: проверка 2–4 рабочих дня, а новых продавцов без
истории иногда отклоняют.

- [ ] **Регистрация как sole trader** ⏱ 15 мин 💳 $0 (комиссия 5 % + 50 ¢ с продажи)
  1. paddle.com → **Get started** → email/пароль. Ты получишь два аккаунта: **sandbox**
     (`sandbox-vendors.paddle.com`, для тестов, доступен сразу) и **live**
     (`vendors.paddle.com`, после проверки).
  2. Live → **Business details**: тип — *Individual / Sole trader* (компания не нужна);
     имя как в teudat osek murshe; адрес; **сайт** `https://<domain>`; описание: *«Audio
     plugin (VST3/AU) that turns a music clip into a playable instrument with MIDI; sold as
     credit packs and a monthly subscription»*.
  3. **Verification**: фото удостоверения личности, подтверждение адреса (счёт за
     коммуналку/выписка), налоговые данные (для не-США физлица — форма **W-8BEN**, Paddle
     её генерирует).
  4. **Payouts → Bank account**: израильский счёт — IBAN + SWIFT/BIC, валюта USD.
  5. **Checkout → Website approval** → `https://<domain>` — Paddle зайдёт и посмотрит
     юридические страницы и цены.
  6. ✅ Письмо «Your account is approved» / статус Approved в дашборде.

- [ ] **Продукты и цены** ⏱ 10 мин — сначала в **sandbox**, потом то же в **live**
  1. **Catalog → Products → New product**: name `50 Credits`, tax category **Standard
     digital goods**, description `50 conversion credits for <Имя>. Credits never expire.`
     → **Add price**: `9.00 USD`, **One-time** → Save. Скопируй **price ID** (`pri_…`).
  2. **New product**: name `Pro Monthly`, tax category **Software as a service (SaaS)**,
     description `60 credits every month. Unused credits expire at the end of the billing
     period.` → **Add price**: `7.99 USD`, **Recurring — every 1 month** → Save. Скопируй
     `pri_…`.
  3. **Checkout → Checkout settings → Default payment link**: `https://<domain>/checkout`
     (страницу `/checkout` с Paddle.js делаю я; она получает price id, `user_id` и `ref`
     из query и открывает overlay с `customData`).
  4. 🔑 Два `pri_…` → в базу (следующий шаг). Sandbox-ids и live-ids **разные**: сначала
     прогоняем sandbox, потом заменяем на live.

- [ ] **Записать price id в базу** ⏱ 3 мин — Supabase → SQL Editor:
  ```sql
  update public.plans
     set provider_variant_ids  = '{"paddle": "pri_XXXXXXXXXXXXXXXXXXXXXXXXXX"}'::jsonb,
         checkout_url_template = 'https://<domain>/checkout?price={variant_id}&user_id={user_id}&ref={ref}&plan_id=pack_50'
   where id = 'pack_50';

  update public.plans
     set provider_variant_ids  = '{"paddle": "pri_YYYYYYYYYYYYYYYYYYYYYYYYYY"}'::jsonb,
         checkout_url_template = 'https://<domain>/checkout?price={variant_id}&user_id={user_id}&ref={ref}&plan_id=sub_monthly'
   where id = 'sub_monthly';
  ```
  Сид в `0001_schema.sql` оставляет `provider_variant_ids = '{}'` и шаблон под
  Lemon Squeezy — **до этого UPDATE `GET /v1/plans` отдаёт `checkout_url: null`, и
  пейволл в плагине открывается без кнопок**. Это единственный шаг, пропуск которого
  вообще ничем не проявляется, кроме отсутствия денег.
  ✅ `curl -s https://api.<domain>/v1/plans | jq -r '.plans[] | select(.price_usd > 0) | "\(.id) \(.checkout_url // "MISSING")"'`
  — ни одной строки с `MISSING`.
  ✅ На сервере: `cd snapplay-ai/backend && python3 -m app.checks` → `"ok": true`, код
  выхода 0.

- [ ] **Webhook** ⏱ 5 мин — в sandbox и в live отдельно
  1. **Developer tools → Notifications → New destination**: description `<Имя> API`,
     type **Webhook**, URL `https://api.<domain>/v1/webhooks/paddle`, **Events** — отметь
     ровно: `transaction.completed`, `subscription.activated`, `subscription.updated`,
     `subscription.canceled` → Save.
  2. Открой созданный destination → **Secret key** (`pdl_ntfset_…`) → 🔑
     `PADDLE_WEBHOOK_SECRET` в backend `.env` (и в AWS Secrets Manager
     `<project>-prod/PADDLE_WEBHOOK_SECRET`, если путь ECS).
  3. `LEMONSQUEEZY_WEBHOOK_SECRET` бэкенд в `ENV=production` **тоже требует** (иначе не
     стартует). Раз Lemon Squeezy не используем — положи туда случайную строку:
     `openssl rand -hex 32`. Роут `/v1/webhooks/lemonsqueezy` будет отвергать всё подряд,
     что и нужно.
  4. ✅ Paddle → Notifications → destination → **Send test** → в логах API `200`.

- [ ] **Тестовая покупка в sandbox** ⏱ 5 мин — вместе со мной, раздел 3 день 4
  1. В sandbox-чекауте карта `4242 4242 4242 4242`, любая будущая дата, любой CVC.
  2. ✅ `select amount, source, note from public.credit_ledger where user_id = '<твой uuid>'
     order by seq desc limit 3;` → строка `grant`, `+50`, `source` начинается с `paddle:`.
  3. ✅ В плагине пейволл закрылся сам (он опрашивает `/v1/me` каждые 5 с).

### 2.5 Apple — подпись и нотаризация

Apple Developer Program у тебя уже оплачен ($99/год). Сертификаты **Developer ID** может
создать только Account Holder — то есть ты, на своём Mac.

- [ ] **Сертификаты Developer ID Application + Installer** ⏱ 10 мин 💳 $0
  1. Xcode → **Settings → Accounts** → выбери свой Apple ID → **Manage Certificates…** →
     «+» → **Developer ID Application**. Ещё раз «+» → **Developer ID Installer**.
     (Альтернатива без Xcode: Keychain Access → Certificate Assistant → Request a
     Certificate From a Certificate Authority → сохранить CSR → developer.apple.com →
     Certificates → «+» → Developer ID Application → загрузить CSR → скачать `.cer` →
     двойной клик; то же для Installer.)
  2. ✅ `security find-identity -v -p codesigning` показывает `Developer ID Application:
     <Имя> (<TEAMID>)`; `security find-identity -v | grep "Developer ID Installer"` — вторую.

- [ ] **Экспорт в .p12 → GitHub Secrets** ⏱ 5 мин
  1. Keychain Access → **login** → категория **My Certificates** → выдели **оба**
     сертификата Developer ID (у каждого должен раскрываться приватный ключ) → правый
     клик → **Export 2 items…** → формат `.p12` → файл `developer-id.p12` → придумай пароль
     (это будет `MACOS_CERT_PASSWORD`) → пароль от Keychain.
  2. В терминале: `base64 -i developer-id.p12 | pbcopy` — содержимое буфера вставь в
     🔑 GitHub Secret **`MACOS_CERT_P12_BASE64`**. Пароль → 🔑 **`MACOS_CERT_PASSWORD`**.
  3. Удали `developer-id.p12` с диска (`rm developer-id.p12`), из Downloads и из корзины.
  4. ✅ В Secrets два имени; `echo "$MACOS_CERT_P12_BASE64" | base64 -d > /dev/null` в
     workflow пройдёт (проверю я первым прогоном).

- [ ] **Ключ App Store Connect API для notarytool** ⏱ 5 мин (рекомендуемый путь)
  1. appstoreconnect.apple.com → **Users and Access → Integrations → App Store Connect
     API → Team Keys** → «+» → Name `notarytool`, Access **Developer** → Generate.
  2. Скачай `AuthKey_<KEYID>.p8` — **скачивается один раз**. Скопируй **Key ID** и
     **Issuer ID** (сверху страницы).
  3. 🔑 Содержимое `.p8` (весь файл, с `-----BEGIN PRIVATE KEY-----`) → Secret
     **`NOTARY_KEY_P8`**; Key ID → **`NOTARY_KEY_ID`**; Issuer ID → **`NOTARY_ISSUER_ID`**.
  4. ✅ Локально: `xcrun notarytool history --key AuthKey_<KEYID>.p8 --key-id <KEYID>
     --issuer <ISSUER>` отвечает списком (пусть и пустым), а не ошибкой авторизации.
  5. Удали `.p8` с диска после проверки.

  Запасной путь (если ключ API создать нельзя): appleid.apple.com → **Sign-In and
  Security → App-Specific Passwords** → Generate `notarytool` → 🔑 **`NOTARY_PASSWORD`**;
  твой Apple ID → **`NOTARY_APPLE_ID`**; developer.apple.com → Account → **Membership
  details → Team ID** → **`NOTARY_TEAM_ID`**. Workflow принимает любой из двух наборов.

- [ ] **Проверка результата релиза** (раздел 3, день 2)
  ✅ `spctl -a -vv -t install "<Имя>-<версия>.pkg"` → `accepted` и
  `source=Notarized Developer ID`.
  ✅ `auval -v aumu <PLUGIN_CODE> <MANUFACTURER_CODE>` (коды из `plugin/CMakeLists.txt`
  после переименования) → `AU VALIDATION SUCCEEDED`. Если Logic всё равно не видит
  плагин: `killall -9 AudioComponentRegistrar` и перезапуск Logic.

### 2.6 Windows — подпись

EV-сертификат больше не даёт мгновенного обхода SmartScreen (убрано в 2024) и **выдаётся
только юрлицам** — не плати за EV. Репутация SmartScreen копится неделями при любом
сертификате; на первых установках предупреждение будет — это норма, беты предупредим.

- [ ] **Вариант A (рекомендуемый): Azure Artifact Signing** ⏱ 20 мин + ожидание проверки
  личности 💳 $9.99/мес (Basic, до 5 000 подписей) + возможно лицензия Entra ID P2 (см.
  открытые вопросы)
  1. portal.azure.com → аккаунт Azure (карта; Free-подписка подходит) → **Create a
     resource** → «Artifact Signing» (бывш. Trusted Signing) → Resource group новая
     `signing` → Region `West Europe` → Name `<name>-signing` → SKU **Basic** → Create.
  2. Ресурс → **Identity validation → New identity → Individual** → данные как в
     удостоверении → верификация через **Entra Verified ID**: приложение Microsoft
     Authenticator, фото документа + селфи. Статус Completed приходит от минут до
     нескольких дней.
  3. Ресурс → **Certificate profiles → Create** → Profile type **Public Trust** → Name
     `<name>-public` → Identity validation — только что созданная → Create.
  4. Сервис-принципал для CI: **Microsoft Entra ID → App registrations → New
     registration** → `github-signing` → Register. На странице приложения: **Application
     (client) ID** → 🔑 **`AZURE_CLIENT_ID`**; **Directory (tenant) ID** → 🔑
     **`AZURE_TENANT_ID`**. **Certificates & secrets → New client secret** → срок 24 мес →
     значение (показывается один раз) → 🔑 **`AZURE_CLIENT_SECRET`**.
  5. Ресурс Artifact Signing → **Access control (IAM) → Add role assignment** → роль
     **Artifact Signing Certificate Profile Signer** (бывш. Trusted Signing Certificate
     Profile Signer) → Members: `github-signing` → Review + assign.
  6. Ресурс → **Overview**: **Account URI** (например `https://weu.codesigning.azure.net`)
     → 🔑 **`AZURE_ENDPOINT`**; имя ресурса → **`AZURE_CODE_SIGNING_ACCOUNT`**; имя профиля
     → **`AZURE_CERT_PROFILE`**.
  7. ✅ Все шесть секретов в GitHub; первый релиз-workflow подписывает `Setup.exe`;
     на Windows `signtool verify /pa /v Setup.exe` → `Successfully verified`.

- [ ] **Вариант B: OV-сертификат** — только если A недоступен для физлица из Израиля
  💳 ~$70–250/год. С июня 2023 ключи OV-сертификатов обязаны жить на токене/HSM, поэтому
  **свежий сертификат в `.pfx` обычно не экспортируется** — путь
  🔑 **`WINDOWS_PFX_BASE64`** / **`WINDOWS_PFX_PASSWORD`** годится, только если у тебя уже
  есть экспортируемый `.pfx`. Иначе у CA нужен облачный signing (например SSL.com eSigner),
  и workflow придётся допиливать под него — скажи, если дойдёт до этого.

### 2.7 Modal — GPU

- [ ] **Аккаунт и токен** ⏱ 5 мин 💳 $30/мес бесплатных кредитов; A10G ≈ $1.10/ч
  посекундно, $0 в простое (для 200 треков/день по 30 с ≈ $1.8/день)
  1. modal.com → **Sign up with GitHub** → workspace `<name>`.
  2. **Settings → Billing** → добавь карту (без неё лимиты песочницы).
  3. На Mac: `pip install modal && modal token new` → откроется браузер → **Approve** →
     токен записан в `~/.modal.toml`. ✅ `modal profile current` печатает имя workspace.
  4. Для API-сервера (он вызывает воркер по имени): **Settings → API Tokens → New Token**
     → скопируй ID и Secret → положишь на сервер в `.env` как переменные, которые читает
     сам Modal (`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` — имена Modal, не наши), я допишу
     их в compose.

- [ ] **Секрет для воркера** ⏱ 5 мин
  1. Dashboard → **Secrets → Create new secret → Custom** → Name ровно
     **`snapplay-supabase`** (значение по умолчанию `SNAPPLAY_MODAL_SECRETS` в
     `backend/worker/modal_app.py`).
  2. Ключи: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `STORAGE_BACKEND=supabase`,
     `STORAGE_BUCKET=jobs`, `SNAPPLAY_PIPELINE=local`, `ENV=staging` (валидация
     `ENV=production` требует вебхук-секреты, которые GPU-воркеру не нужны — я проверю,
     что воркер от `ENV` больше ни в чём не зависит).
  3. ✅ Секрет в списке с 6 ключами.

- [ ] **Деплой воркера и бенчмарк** ⏱ 10 мин (после смены движка разделения — решение №2)
  ```sh
  cd snapplay-ai/backend
  SNAPPLAY_MODAL_GPU=A10G modal deploy -m worker.modal_app
  ```
  ✅ Dashboard → **Apps → `snapplay-worker`** → класс `SnapPlayWorker`, статус Deployed.
  Затем `python3 scripts/benchmark_modal.py` (пишу я) печатает p50/p95 по стадиям; цель
  p95 < 2.0 с на A10G без учёта сети. Первая задача после простоя — холодный контейнер
  плюс загрузка модели, ожидай до 1–2 минут; это учитывается в бета-плане.
  🔑 В backend `.env`: `SNAPPLAY_PIPELINE=modal`, `MODAL_APP_NAME=snapplay-worker`.

### 2.8 AWS — существующий сервер и/или Terraform

- [ ] **Скажи мне, что за сервер** ⏱ 5 мин — выполни на нём и пришли вывод:
  ```sh
  curl -s http://169.254.169.254/latest/meta-data/instance-type; echo
  curl -s http://169.254.169.254/latest/meta-data/placement/region; echo
  nproc; free -h; df -h /; uname -m; cat /etc/os-release | head -2
  docker --version; docker compose version
  ```
  Для API хватает 2 vCPU / 2 GB (API + Caddy); GPU на сервере не нужен — считает Modal.
  Если `docker` нет: `curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER`.

- [ ] **Сеть** ⏱ 10 мин
  1. EC2 → инстанс → **Security → Security groups → Edit inbound rules**: `HTTP 80` и
     `HTTPS 443` от `0.0.0.0/0` и `::/0`; `SSH 22` — только с твоего IP.
  2. EC2 → **Elastic IPs → Allocate → Associate** с инстансом (иначе IP поменяется после
     stop/start).
  3. Vercel → Domains → `<domain>` → DNS Records → **A**, name `api`, value — Elastic IP,
     TTL 60.
  4. ✅ `dig +short api.<domain>` → Elastic IP.
  5. 🔑 `https://api.<domain>` → `NEXT_PUBLIC_API_URL`, `SNAPPLAY_API_URL` (growth), и
     базовый URL плагина (в коде, меняю я).

- [ ] **Конфиг API на сервере** ⏱ 10 мин
  1. `git clone` репозитория на сервер (deploy key read-only — сделаю и пришлю), файл
     `snapplay-ai/backend/.env` с правами `chmod 600`. Значения:

     | переменная | откуда |
     |------------|--------|
     | `ENV=production` | фиксировано |
     | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY` | 2.3 «Ключи» |
     | `SUPABASE_JWT_SECRET` **или** `SUPABASE_JWKS_URL` | 2.3 «Ключи», п. 2 |
     | `AUTH_SITE_URL=https://<domain>` | 2.1 |
     | `STORAGE_BACKEND=supabase`, `STORAGE_BUCKET=jobs`, `SIGNED_URL_TTL_SECONDS=86400` | 2.3 «Bucket» |
     | `PADDLE_WEBHOOK_SECRET` | 2.4 «Webhook» |
     | `LEMONSQUEEZY_WEBHOOK_SECRET` | `openssl rand -hex 32` (2.4, п. 3) |
     | `WEBHOOK_CLAIM_LEASE_SECONDS=300` | по умолчанию |
     | `SNAPPLAY_PIPELINE=modal`, `MODAL_APP_NAME=snapplay-worker` | 2.7 |
     | `JOB_TIMEOUT_SECONDS=180` | по умолчанию |
     | `MAX_UPLOAD_BYTES=10485760`, `MAX_INPUT_SECONDS=60`, `FREE_SIGNUP_CREDITS=3` | контракт §2–3 |
     | `RATE_LIMIT_JOBS_PER_MIN=10`, `RATE_LIMIT_READS_PER_MIN=60` | контракт §5 |
     | `AFFILIATE_COMMISSION_RATE=0.30` | контракт §12 |
     | `CORS_ALLOW_ORIGINS=https://<domain>` | вместо `*` из примера |

     Переменные AWS-пути (`AWS_REGION`, `S3_BUCKET`, `S3_ENDPOINT_URL`, `CLOUDFRONT_*`,
     `SQS_JOB_QUEUE_URL`, `SQS_DLQ_URL`) и RunPod (`RUNPOD_ENDPOINT_ID`, `RUNPOD_API_KEY`)
     при Modal + Supabase Storage **не заполняются**.
  2. TLS: `infra/docker-compose.yml` публикует только `8080` — я добавлю сервис Caddy
     (автоматический Let's Encrypt для `api.<domain>`) и `restart: unless-stopped`.
  3. `cd snapplay-ai/infra && docker compose up -d api` (после моего PR — вместе с Caddy).
  4. ✅ `curl -i https://api.<domain>/v1/health` → `200 {"status":"ok"}`.
  5. ✅ `docker compose logs api | grep -i "no checkout URL"` — пусто (иначе 2.4 не сделан).

- [ ] **Бюджет-предохранитель** ⏱ 5 мин 💳 $0
  AWS Console → **Billing → Budgets → Create budget → Cost budget** → $50/мес → Alert
  threshold 80 % actual → email → Create. Это письмо, не выключатель; выключатель
  (`MAINTENANCE_MODE`) — в моём списке.

- [ ] **Если/когда переходим на Terraform ECS** (`infra/aws/README.md`) — GitHub
  **Variables** (не Secrets), ровно эти имена:

  | Variable | значение |
  |----------|----------|
  | `AWS_REGION` | регион (`production.tfvars` → `region`) |
  | `AWS_DEPLOY_ROLE_ARN` | `terraform output -raw github_deploy_role_arn` после первого apply |
  | `TF_STATE_BUCKET` | bucket из bootstrap («Bootstrap: remote state» в README) |
  | `TF_LOCK_TABLE` | таблица DynamoDB из bootstrap |
  | `SUPABASE_URL` | Project URL |
  | `ROUTE53_ZONE_ID` **или** `ACM_CERTIFICATE_ARN` | одно из двух, второе пустое |
  | `ALARM_EMAIL` | **обязательно заполни** — по умолчанию пусто, и тогда три CloudWatch-алярма шлют в SNS-топик без подписчиков |

  И **AWS Secrets Manager** (не GitHub), значения вместо `CHANGE_ME`:
  `<project>-prod/SUPABASE_SERVICE_ROLE_KEY`, `<project>-prod/SUPABASE_JWT_SECRET`,
  `<project>-prod/LEMONSQUEEZY_WEBHOOK_SECRET`, `<project>-prod/PADDLE_WEBHOOK_SECRET`
  (`<project>` = `project_name` из `production.tfvars`). Bootstrap-команды — в README,
  раздел «Apply order», шаг 5. Первый apply — с админ-правами из твоего терминала.

### 2.9 Vercel — сайт

- [ ] **Проект из репозитория** ⏱ 10 мин 💳 Hobby $0 (для коммерческого сайта Vercel
  требует **Pro $20/мес** — по условиям Hobby коммерческое использование запрещено;
  включи Pro до запуска)
  1. vercel.com → **Add New → Project → Import Git Repository** → если репозитория нет в
     списке — **Adjust GitHub App Permissions** → дай доступ к `<repo>`.
  2. **Root Directory** → Edit → `snapplay-ai/web` (после переименования путь изменится —
     напомню). Framework Preset — Next.js определится сам.
  3. **Environment Variables** — добавь все (Production + Preview):

     | имя | значение / откуда |
     |-----|-------------------|
     | `NEXT_PUBLIC_SUPABASE_URL` | Project URL (2.3) |
     | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon key (2.3) |
     | `NEXT_PUBLIC_API_URL` | `https://api.<domain>` |
     | `NEXT_PUBLIC_SITE_URL` | `https://<domain>` (для Preview можно оставить то же) |
     | `NEXT_PUBLIC_PRODUCT_NAME` | `<Имя>` |
     | `NEXT_PUBLIC_SUPPORT_EMAIL` | `support@<domain>` |
     | `NEXT_PUBLIC_COMPANY_LEGAL_NAME` | имя, как в teudat osek murshe, например `Gregory Dich (sole proprietor)` |
     | `NEXT_PUBLIC_COMPANY_ADDRESS` | юридический адрес осек мурше |
     | `NEXT_PUBLIC_COMPANY_REG_ID` | номер осек мурше (מספר עוסק). Он совпадает с номером теудат зеут — публиковать ли его на сайте, спроси юриста (раздел 4) |
     | `NEXT_PUBLIC_PRIVACY_EMAIL` | `privacy@<domain>` |
     | `NEXT_PUBLIC_LEGAL_EMAIL` | `legal@<domain>` |
     | `NEXT_PUBLIC_MERCHANT_OF_RECORD` | `Paddle` (точное юрлицо — Paddle.com Market Ltd для покупателей вне США — сверь в Paddle → Help → «Who is the merchant of record»; юрист проверит формулировку в Terms) |
     | `NEXT_PUBLIC_LEGAL_EFFECTIVE_DATE` | дата публикации юртекстов, `YYYY-MM-DD` |
     | `NEXT_PUBLIC_BILLING_PORTAL_URL` | у Paddle Billing нет статической ссылки на портал — сессии портала выдаются по API на клиента; ставь `https://<domain>/account/billing`, роут, который создаёт сессию, делаю я |
     | `NEXT_PUBLIC_KLAVIYO_COMPANY_ID` | опционально, 2.13 |
  4. **Deploy**. ✅ Preview-URL открывается, `/signup` создаёт пользователя в Supabase →
     Authentication → Users.
  5. **Settings → Domains → Add** → `<domain>` и `www.<domain>` (redirect на apex) — домен
     куплен в Vercel, поэтому DNS настроится сам. ✅ `https://<domain>` открывается с
     замком.
  6. ✅ Lighthouse (Chrome DevTools) ≥ 90 по Performance на лендинге.

### 2.10 GitHub Secrets / Variables — сводная таблица

| имя | тип | источник | кто читает |
|-----|-----|----------|------------|
| `MACOS_CERT_P12_BASE64` | Secret | 2.5, экспорт Keychain → base64 | release workflow (macOS) |
| `MACOS_CERT_PASSWORD` | Secret | пароль, заданный при экспорте `.p12` | release workflow (macOS) |
| `NOTARY_KEY_P8` | Secret | содержимое `AuthKey_<KEYID>.p8` | release workflow (notarytool) |
| `NOTARY_KEY_ID` | Secret | App Store Connect → Team Keys → Key ID | release workflow |
| `NOTARY_ISSUER_ID` | Secret | App Store Connect → Team Keys → Issuer ID | release workflow |
| `NOTARY_APPLE_ID` / `NOTARY_PASSWORD` / `NOTARY_TEAM_ID` | Secret | запасной путь: Apple ID + app-specific password + Team ID | release workflow (вместо трёх выше) |
| `AZURE_TENANT_ID` | Secret | Entra ID → App registration → Directory (tenant) ID | release workflow (Windows) |
| `AZURE_CLIENT_ID` | Secret | Entra ID → App registration → Application (client) ID | release workflow (Windows) |
| `AZURE_CLIENT_SECRET` | Secret | Entra ID → Certificates & secrets | release workflow (Windows) |
| `AZURE_ENDPOINT` | Secret | Artifact Signing → Overview → Account URI | release workflow (Windows) |
| `AZURE_CODE_SIGNING_ACCOUNT` | Secret | имя ресурса Artifact Signing | release workflow (Windows) |
| `AZURE_CERT_PROFILE` | Secret | имя certificate profile | release workflow (Windows) |
| `WINDOWS_PFX_BASE64` / `WINDOWS_PFX_PASSWORD` | Secret | только вариант B (2.6) | release workflow (вместо Azure) |
| `AWS_REGION` | Variable | регион деплоя | `deploy.yml` (ECS-путь) |
| `AWS_DEPLOY_ROLE_ARN` | Variable | `terraform output -raw github_deploy_role_arn` | `deploy.yml` |
| `TF_STATE_BUCKET`, `TF_LOCK_TABLE` | Variable | bootstrap remote state | `deploy.yml` |
| `SUPABASE_URL` | Variable | Project URL | `deploy.yml` → `TF_VAR_supabase_url` |
| `ROUTE53_ZONE_ID` **или** `ACM_CERTIFICATE_ARN` | Variable | Route 53 / ACM | `deploy.yml` |
| `ALARM_EMAIL` | Variable | твой email для аларм-подписки SNS | `deploy.yml` → `TF_VAR_alarm_email` |

Секреты приложения (`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`,
`PADDLE_WEBHOOK_SECRET`, `LEMONSQUEEZY_WEBHOOK_SECRET`) в GitHub **не кладутся** — они живут
в `.env` на сервере (2.8) или в AWS Secrets Manager (ECS-путь).

### 2.11 Sentry

- [ ] ⏱ 5 мин 💳 $0 (Developer plan: 5k ошибок/мес)
  1. sentry.io → Sign up → организация `<name>` → **Create Project** → platform **Python
     → FastAPI** → name `api` → Create.
  2. Скопируй **DSN** (`https://…@….ingest.sentry.io/…`).
  3. 🔑 В backend `.env` под именем, которое я добавлю в `config.py` при шаге 6 плана
     (планируемое имя `SENTRY_DSN`; пока в коде его **нет**). Второй проект `worker` —
     тот же DSN или отдельный, положим в Modal-секрет.
  4. ✅ После деплоя: `curl https://api.<domain>/v1/jobs/00000000-0000-0000-0000-000000000000`
     без токена → 401, а событий в Sentry нет (401 — не ошибка); тестовое исключение
     пришлю я через отладочный роут и удалю его.

### 2.12 Uptime-монитор

- [ ] ⏱ 5 мин 💳 $0 — UptimeRobot (50 мониторов, каждые 5 мин) или Better Stack (10
  мониторов, каждые 3 мин, есть звонок на телефон)
  1. uptimerobot.com → **New monitor** → type **HTTP(s)** → URL
     `https://api.<domain>/v1/health` → interval 5 min → Alert contacts: email (и Telegram
     через их интеграцию, если хочешь просыпаться).
  2. Второй монитор: **Keyword** → та же URL → keyword `ok` → alert when keyword *not*
     exists.
  3. Третий: HTTP(s) → `https://<domain>`.
  4. ✅ Три монитора зелёные; тестовое письмо от сервиса пришло.

### 2.13 Klaviyo (опционально)

- [ ] ⏱ 5 мин 💳 $0 (до 250 контактов)
  1. klaviyo.com → аккаунт → **Settings → Account → API keys** → **Public API Key /
     Site ID** (6 символов).
  2. 🔑 → `NEXT_PUBLIC_KLAVIYO_COMPANY_ID` в Vercel. Списки и welcome-flow настраиваю я
     через Klaviyo MCP.
  3. ✅ Подписка на лендинге → профиль появляется в Klaviyo → Audience.

### 2.14 Платформы для growth-движка — честные сроки

Все три требуют **опубликованных Privacy Policy и Terms** на `<domain>` — подаваться
после 2.9 и раздела 4. Пока аудиты не пройдены, движок работает end-to-end, но посты
приватные (`status: "restricted"` у TikTok, private у YouTube) — годится для QA, не для
воронки. Закладывай **3–6 недель** на всё.

- [ ] **TikTok** ⏱ 20 мин на подачу; аудит 5–10 рабочих дней по одним источникам, 2–4
  недели с раундами правок по другим
  1. developers.tiktok.com → Login → **Manage apps → Connect an app** → название `<Имя>`,
     категория, иконка, описание; **Terms of Service URL** и **Privacy Policy URL** с сайта.
  2. **Add products**: **Login Kit** и **Content Posting API**. Scopes: `user.info.basic`,
     `video.upload` (inbox/draft — **без аудита**) и, если идём на Direct Post, `video.publish`.
  3. **URL properties → Add property** → `<domain>` → верификация: TXT-запись в Vercel
     DNS (или файл в корне сайта — файл кладу я). Для Content Posting API верификация
     обязательна всегда.
  4. **Решение:** v1 на **inbox/draft mode** (видео падают в черновики, ты публикуешь
     пальцем; аудит не нужен) или **Direct Post** (полная автоматика, нужен аудит с
     демо-видео, записанным ещё ограниченным приложением, плюс честное отображение
     настроек приватности/дуэтов автора — самая частая причина отказа). Мой совет для
     старта — draft mode; на Direct Post подаёмся параллельно.
  5. Submit for review → ждём. 🔑 После OAuth-логина твоим аккаунтом —
     `TIKTOK_ACCESS_TOKEN` в `growth/.env` (токен живёт 24 ч, обновление по refresh —
     моя часть).
  6. ✅ Статус приложения Approved; `publish_video` возвращает `status: "published"`, а не
     `restricted`.

- [ ] **Meta (Instagram + Facebook)** ⏱ 30 мин на подачу; business verification 1–5
  рабочих дней (документы 3–7, до 15); app review каждого permission 2–4 недели
  1. Instagram-аккаунт → Settings → **Account type → Switch to Professional → Business**
     (Creator через API публиковать не может) → привяжи к **Facebook Page** (создай Page
     `<Имя>`, если нет).
  2. business.facebook.com → **Business Manager** → **Settings → Security Center → Business
     verification**: юридическое имя (как в осек мурше), адрес, телефон, **сайт**,
     документ — teudat osek murshe / справка НДС + счёт за коммуналку с адресом. Почта на
     домене (2.1) ускоряет проверку примерно вдвое.
  3. developers.facebook.com → **My Apps → Create App → Business** → название `<Имя>` →
     привяжи к Business Manager → **Add products → Instagram → API setup with Facebook
     login**.
  4. **App Review → Permissions and features** → запроси `instagram_business_basic`,
     `instagram_business_content_publish` (старые `instagram_basic`/
     `instagram_content_publish` списаны 2025-01-27), `pages_show_list`,
     `pages_read_engagement`; для Page Reels — `pages_manage_posts`. К каждому — screencast
     полного пути (я запишу с preview-среды) и текст обоснования (напишу).
  5. **Graph API Explorer** (или Business Settings → System Users → Generate token) →
     long-lived token (60 дней) → 🔑 `META_IG_ACCESS_TOKEN`, `META_PAGE_ACCESS_TOKEN`;
     `META_IG_USER_ID` = `GET /me/accounts` → page → `instagram_business_account.id`;
     `META_PAGE_ID` = id страницы. Всё в `growth/.env`.
  6. Техническое ограничение: Graph API принимает Reels **≤ 90 с** — рендер режем под это.
  7. ✅ Business verified; permissions — Approved; тестовый Reel опубликован с `?utm_…`.

- [ ] **YouTube Data API** ⏱ 15 мин; compliance audit — недели
  1. console.cloud.google.com → **New project** `<name>-growth` → **APIs & Services →
     Enable APIs → YouTube Data API v3 → Enable**.
  2. **OAuth consent screen** → External → название, support email, **Privacy Policy /
     Terms URL** с сайта → Scopes → добавь `https://www.googleapis.com/auth/youtube.upload`
     → Test users → твой Google-аккаунт канала.
  3. **Credentials → Create credentials → OAuth client ID → Desktop app** → скачай JSON
     (мне, для однократного получения токена).
  4. 🔑 `YOUTUBE_ACCESS_TOKEN` в `growth/.env` (обновление по refresh token — моя часть).
  5. Пока проект не прошёл **YouTube API Services compliance audit**, загрузки через API
     становятся **private** — подать **Audit and Quota Extension Form** сразу после
     первых тестовых загрузок. Квота 10 000 units/день; стоимость `videos.insert` — см.
     открытые вопросы (1 600 units ≈ 6 загрузок/день по старым данным; по новым —
     отдельная корзина 100 вызовов/день).
  6. ✅ Тестовое Short загружено (private), consent screen в статусе In production после
     верификации.

---

## 3. Порядок запуска

«Я» — что делаю после твоего шага; «вместе» — что проверяем в одном звонке. Дни —
рабочие, от «сегодня» = 2026-09-09. Длинные ожидания (Paddle, Azure-личность, Meta,
TikTok) запускаем в первый день, чтобы они тикали параллельно.

### День 0 — решения и всё, что долго ждёт

**Ты:** решения №1–7 (раздел 1) — одним сообщением. Открой `samplab.com` и сделай скриншот
объявления о закрытии (см. «Окно Samplab» ниже). Купи домен (2.1) и заведи почту на домене.
Создай репозиторий и окружение `production` (2.2). Заведи аккаунт Azure и запусти проверку
личности (2.6, шаги 1–2) — она может занять дни. Заведи Business Manager и запусти business
verification в Meta (2.14, шаг 2).
**Я:** переименование репозитория целиком → все пять сьютов зелёные → `grep -ri snapplay`
= 0 вне git-истории → перенос в новый репозиторий → правка `production.tfvars`
(`project_name`, `domain_name`, `github_repository`) → Vercel-проект (2.9) с preview.

### День 1 — Supabase и сайт

**Ты:** Supabase целиком (2.3: проект, ключи, миграции, pg_cron, bucket, Auth, SMTP,
шаблоны). Vercel env (2.9, шаг 3).
**Вместе (15 мин):**
1. На preview-сайте регистрируешься новым адресом → письмо от `noreply@<domain>` → ссылка
   → страница «confirmed».
2. До подтверждения пробуем войти из плагина (`/v1/auth/token`) → отказ; после — вход
   проходит.
3. SQL: `select p.email, a.balance, a.reserved from public.profiles p join
   public.credit_accounts a on a.user_id = p.id where p.email = '<адрес>';` → `3 / 0`.
4. `/account` показывает 3 кредита из `/v1/me`.
5. «Forgot password» → письмо → `/auth/reset-password` → новый пароль работает.

### День 2 — подпись и инсталляторы

**Ты:** Apple (2.5) → секреты в GitHub. Если Azure-личность уже подтверждена — 2.6 до
конца.
**Я:** `release.yml` по тегу `v0.1.0-beta.1` → `.pkg` (VST3 + AU) и `Setup.exe` в GitHub
Release.
**Вместе:** на M4 — `spctl -a -vv -t install <pkg>` → `accepted, source=Notarized Developer
ID`; установка; `auval` зелёный; Logic/Ableton/FL видят плагин. На Windows —
`signtool verify /pa /v Setup.exe`; SmartScreen может предупредить (репутация нулевая) —
фиксируем, что кнопка «Run anyway» есть.

### День 3 — GPU, API, наблюдаемость

**Ты:** Modal (2.7), данные о сервере + сеть + `.env` (2.8), Sentry (2.11), UptimeRobot
(2.12), AWS-бюджет.
**Я:** compose с Caddy → `docker compose up -d` → бенчмарк → таблица p50/p95 по стадиям
и прослушивание 10 клипов (трап/дрилл — «грязный» бас или нет).
**Вместе:** `curl https://api.<domain>/v1/health` → 200; из плагина — первая реальная
задача: прогресс `upload → separate → transcribe → analyze → package`, четыре стема
играют, `.mid` перетаскивается; ledger: `reserve −1` → `capture −1`, `available` = 2.

### День 4 — деньги

**Ты:** Paddle sandbox: продукты (2.4) → `pri_…` → SQL UPDATE → webhook → тестовая покупка.
**Вместе:** `python3 -m app.checks` → `"ok": true`; `/v1/plans` без `MISSING`; в плагине
тратим 3 кредита → пейволл с **двумя кнопками** → покупка `4242…` → в течение 5 с баланс
50 → ledger `grant +50 paddle:…`; подписка `sub_monthly` → `subscriptions` строка
`active`, грант с `expires_at` = конец периода. Потом live-аккаунт Paddle: те же продукты,
live `pri_…` в SQL, live webhook-секрет, **Website approval**.

### Дни 5–6 — юрист и бухгалтер (раздел 4), пока Paddle проверяет

**Я:** финальные тексты `legal/` с твоими правками → на сайт → `NEXT_PUBLIC_LEGAL_EFFECTIVE_DATE`.

### День 7 — внутренний прогон DAW

**Вместе:** `docs/BETA_TEST_PLAN.md`, раздел «DAW acceptance», на M4 (FL Studio, Ableton
Live 12, Logic) и на Windows (FL, Ableton). Всё, что не Pass, — в мой бэклог до беты.

### Дни 8–21 — бета (2 недели)

**Ты:** посты в r/FL_Studio, r/edmproduction, KVR по текстам из `BETA_TEST_PLAN.md`
(после модераторов), раздача кредитов — по списку, который пришлю (SQL `grant_credits`
делаю я).
**Я:** триаж багов, релизы `v0.1.0-beta.N`, сводка метрик из формы.

### День 22+ — запуск

Решение go/no-go по критериям бета-плана. KVR product listing, Product Hunt (черновик
мой, публикация твоя), Klaviyo-рассылка по бете, growth-движок в приватном режиме до
аудитов. Уведомление о версии — `GET /v1/version` баннер в плагине.

### Окно Samplab — отдельный пункт с дедлайном

По рыночному отчёту, Samplab (облачный audio→MIDI / стемы, ближайший аналог по
«играбельности») **сворачивает сервис 2026-09-17**: после этой даты новые загрузки
невозможны, годовым подписчикам возвращают остаток, а офлайн-Resynthesizer остаётся у
существующих покупателей. Источник — сниппет поисковика с главной samplab.com, сам сайт
из этой среды заблокирован — **непроверено**.

1. **Ты, сегодня:** открой `https://samplab.com`, сделай скриншот текста о закрытии с
   датой. Если даты нет или она другая — скажи, и пункт ниже меняется.
2. **Я, до 17.09:** страница `/samplab-alternative` на сайте с честным текстом («Samplab
   closes on 17 September; here is what we do differently: playable instrument + MIDI
   inside the DAW»), кнопка «Notify me» → Klaviyo/лист ожидания, и — если подписанный
   инсталлятор уже есть — ссылка на бету. Никаких «Samplab shut down» в копи, пока ты не
   подтвердил скриншотом.
3. Позиционирование вообще: FL Studio 21.2+ и Logic Pro 11 разделяют стемы **бесплатно и
   нативно**, поэтому лендинг не про «разделение», а про «стем как играбельный инструмент
   + MIDI, не выходя из DAW». Это же — в текстах для беты и KVR.
4. Окно уже занято как минимум одним конкурентом (MIDI Morph 2, $39 разово, страница
   «vs Samplab») — значит, страницу надо сделать до, а не после 17.09.

---

## 4. Юрист и бухгалтер

### 4.1 Юристу (1 час вычитки + ответы на вопросы)

**Что отдать.** Черновики из `legal/` — Terms of Service, Privacy Policy, Refund Policy,
Copyright/DMCA policy, Cookie notice, `LICENSE` (проприетарная) и
`THIRD_PARTY_LICENSES.md`. Места, где нужна именно юридическая оценка, помечены маркером
**`LAWYER-REVIEW`** — список маркеров с пояснениями в `legal/README.md`. Отдавай
целиком, но просить оценить — только помеченное.

**Вопросы, на которые нужен ответ в письменном виде.**
1. **Веса Demucs.** Являются ли веса производным произведением MIT-кода и/или
   некоммерческого датасета; считается ли комментарий мейнтейнера в issue условием
   лицензии; каков риск закрытой беты на `htdemucs` и нужно ли менять движок до неё
   (раздел 1.2). Приложи скриншот issue #327.
2. **Применимое право и потребители ЕС.** Право Израиля в Terms при продаже цифрового
   контента потребителям ЕС/Великобритании: право отказа 14 дней и его waiver при
   немедленном доступе к кредитам; наша Refund policy (14 дней на неиспользованные
   кредиты) — достаточно ли; роль Paddle как merchant of record в Terms.
3. **GDPR-механика.** Нужен ли представитель в ЕС по ст. 27 при нашей обработке (аудио
   24 ч, email, ledger); DPA/SCC с Supabase, AWS, Modal, Paddle, Resend, Vercel, Sentry —
   какие подписать и где сослаться; сроки хранения ledger/email «для бухгалтерии» — какие
   написать; экспорт и удаление аккаунта по запросу (эндпоинты делаю я — юрист говорит,
   что должно быть в ответе).
4. **Израильский закон о защите приватности, Amendment 13** (вступил в силу 14.08.2025):
   нужна ли регистрация базы данных при нашем объёме и типах данных (email + история
   задач, без особо чувствительных данных), нужен ли DPO/ответственный, нужен ли
   документ определений базы (מסמך הגדרות מאגר) и уведомление субъектов при сборе.
5. **Импринт.** Обязательно ли публиковать номер осек мурше (= номер теудат зеут) на
   сайте для потребителей ЕС, или достаточно имени и адреса
   (`NEXT_PUBLIC_COMPANY_REG_ID`).
6. **Торговая марка.** Стоит ли подать на `<Имя>` в классах 9 и 42 (Израиль — ILPO,
   ЕС — EUIPO ≈ €850 за один класс, США — USPTO ≈ $350 за класс; суммы приблизительные) и
   что делать с маркой STEM (Stem Disintermedia, Reg. 5023828) при выборе StemKeys.
7. **Пользовательский контент.** Формулировка гарантии прав на загружаемое аудио и
   DMCA-процедура; нужна ли отдельная фраза про AI-обработку (EU AI Act, прозрачность
   с 2026-08-02 — для маркетинговых видео с синтетическим голосом, не для продукта).

### 4.2 Бухгалтеру (осек мурше)

1. **НДС на выручку через merchant of record.** Paddle (иностранное юрлицо) — продавец
   конечному покупателю, а ты выставляешь счёт Paddle. Считается ли это экспортом услуг
   иностранному резиденту с нулевой ставкой (סעיף 30(א)(5) חוק מע"מ — уточнить у него) и
   какие документы нужны: self-billing-отчёты Paddle, выписки о выплатах, договор.
   **Письменно, до первой выплаты.**
2. Какой первичный документ выписывать на выплату Paddle (חשבונית מס / קבלה), в какой
   валюте и по какому курсу; периодичность отчётов НДС; авансы подоходного и Битуах Леуми.
3. **Расходы:** Apple $99/год, Azure $9.99/мес, Supabase $25/мес, Vercel $20/мес, Modal
   по факту, домен, Resend/Sentry при переходе на платные — как оформлять зарубежные
   инвойсы без НДС (обратное начисление?).
4. Форма **W-8BEN** для Paddle — заполняем как физлицо-резидент Израиля по договору об
   избежании двойного налогообложения; ему проверить.
5. Порог осек патур → мурше (ILS 107 692/год) — уже мурше, не актуально; но спроси про
   переход в компанию (חברה בע"מ) при выручке, при которой это выгодно, и про JUCE Indie
   как расход.
6. Amendment 13 — это к юристу (4.1, п. 4), но если у бухгалтера есть готовая практика по
   регистрации баз данных у осеков — спроси.

---

## 5. Что я ещё не знаю / открытые вопросы

Неподтверждённые факты из отчётов и где их проверить самому (эта среда блокировала
первоисточники):

| # | Факт | Статус | Где проверить |
|---|------|--------|---------------|
| 1 | Цитата Défossez про веса Demucs («only for scientific purposes») | из двух вторичных источников | `https://github.com/facebookresearch/demucs/issues/327` |
| 2 | Mel-Band RoFormer (Kim) перелицензирован в MIT 2026-04-22, веса включены | карточка на Hugging Face, не репозиторий автора | репозиторий автора + карточка `mlx-community/mel-roformer-kim-vocal-2-mlx`; заархивировать текст лицензии в день релиза |
| 3 | Цены JUCE: Indie $40/мес·$800 или $50/мес·$1000; Starter лимит $20k | источники расходятся | `https://juce.com/get-juce/` |
| 4 | Цена коммерческой лицензии Rubber Band | не публикуется | `https://breakfastquay.com/technology/license.html` → запрос квоты |
| 5 | Поддержка Израиля у Lemon Squeezy (если вдруг придёт инвайт) | не подтверждено | `https://docs.lemonsqueezy.com/help/getting-started/supported-countries` |
| 6 | Квота YouTube `videos.insert`: 1 600 units или отдельная корзина 100 вызовов/день (изменения 2025-12-04 и 2026-06-01) | средняя уверенность | `https://developers.google.com/youtube/v3/determine_quota_cost` + revision history |
| 7 | Samplab закрывает облако 2026-09-17 | сниппет поисковика | `https://samplab.com` — скриншот сегодня |
| 8 | Объёмы поисковых запросов («samplab alternative», «audio to midi vst», «stems to midi» и т.д.) | **нет данных**: Ahrefs MCP в этой среде отвечает «Insufficient plan» | Ahrefs с оплаченным планом, или Google Keyword Planner в твоём Ads-аккаунте |
| 9 | Торговые марки StemKeys/NoteBreak/TrackBreak; статус STEM Reg. 5023828; есть ли у NI незарегистрированная STEMS в ЕС | только поисковые сниппеты, базы USPTO/EUIPO/WIPO не открывались | `tmsearch.uspto.gov`, `euipo.europa.eu/eSearch`, `branddb.wipo.int`; лучше — платный клиренс через юриста |
| 10 | Соцхэндлы `@stemkeys` на IG/TikTok/X/YouTube | «нет следов», не «свободно» | открой профили руками, зарегистрируй в день выбора имени |
| 11 | Azure Artifact Signing: доступна ли валидация физлица из Израиля; нужна ли лицензия Entra ID P2 для назначения роли | один пользовательский отчёт о P2 | `https://azure.microsoft.com/pricing/details/artifact-signing/`; попытка регистрации (2.6) покажет |
| 12 | Тип и регион твоего AWS-сервера, есть ли docker, свободна ли мощность | неизвестно | команда в 2.8 |
| 13 | Реальное качество разделения на трапе/дрилле и p95 на A10G | не измерялось — `real.py` ни разу не запускался с torch | бенчмарк (2.7) |
| 14 | Что реально шлёт Paddle в `custom_data` на `transaction.completed` и на продлениях подписки | тесты только на синтетических payload | sandbox-покупка (2.4) + журнал webhook в Paddle |
| 15 | Статическая ссылка на customer portal Paddle Billing | по докам — только сессии по API | Paddle → Checkout → Customer portal |
| 16 | Есть ли у GoTrue переменная шаблона `{{ .Type }}` | в документации Supabase её нет, поэтому в 2.3 `type=` прописан в каждом шаблоне явно | Supabase → Authentication → Emails → список переменных |
| 17 | Vercel Hobby для коммерческого сайта | по условиям Vercel — нельзя, нужен Pro | `https://vercel.com/pricing` |
| 18 | Стоимость регистрации ТМ в ILPO/EUIPO/USPTO | приблизительно | сайты ведомств / юрист |
