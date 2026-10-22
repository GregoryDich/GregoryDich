# Лицензионное соглашение (EULA) / End User Licence Agreement — ЧЕРНОВИК / DRAFT

> **ЧЕРНОВИК. Не публиковать до проверки израильским юристом (ROADMAP, задача R13).**
> Соглашение для прямого канала: DMG с сайта, подпись Developer ID и нотаризация. Это не юридическая
> консультация. Всё, что должен вписать или решить владелец, помечено `[ВЛАДЕЛЕЦ: …]`; найти все места:
> поиск по «ВЛАДЕЛЕЦ».
>
> **DRAFT. Do not publish before review by an Israeli lawyer (ROADMAP task R13).** For direct distribution
> (DMG from the website, Developer ID signature, notarization). Not legal advice. Every placeholder is marked
> `[ВЛАДЕЛЕЦ: …]` (owner).

## Для владельца — удалить этот блок перед публикацией

**Что вписать (плейсхолдеры):**
1. Название приложения после R10 (сейчас «Морской аквариум»).
2. Ваше полное имя или название бизнеса, статус и номер, почтовый адрес в Израиле.
3. Адрес поддержки на домене продукта (сейчас `support@tonamorph.com`).
4. Суд: по умолчанию в тексте — Тель-Авив-Яффо.
5. Предел ответственности для бесплатной версии (в тексте предложено 50 долларов США).
6. Раздел 5 (платный контент): продавец, число Mac на ключ (в ROADMAP R18 — 3), длительность предпросмотра
   (в R18 — 15 минут). До начала продаж раздел можно оставить: он прямо говорит «сейчас бесплатно».

**Вопросы юристу:**
1. Разрешать ли показ приложения на экранах в общественных местах (кафе, магазин, приёмная) — сверить
   с условиями лицензий стокового контента (реестр: `docs/licences/ASSETS.md`).
2. Разрешение на скриншоты и короткие записи экрана для обзоров и соцсетей (раздел 3) — совместимо ли
   с лицензиями контента.
3. Закон о стандартных договорах (חוק החוזים האחידים, התשמ"ג-1982): не признает ли суд ограничение ответственности,
   отказ от гарантий или выбор суда «ущемляющим условием». Нужна ли версия на иврите. Отдельно — условия из
   презумпций ст. 4 (право поставщика в одностороннем порядке прекратить, приостановить или изменить свои основные
   обязательства), уже смягчённые в тексте:
   а) лицензия больше не «отзывная» — прекращается только по разделу 13;
   б) замена или удаление Контента (раздел 4) — для купленного Платного контента без равноценной замены возврат денег
      (п. 5.7);
   в) новая редакция при продолжении использования (п. 16.5) — без согласия не ухудшает условия уже купленного;
   г) суд по месту жительства потребителя — и для потребителей в Израиле (раздел 14).
4. Возвраты: в тексте — добровольные 14 дней (ROADMAP R13); как это сочетается со ст. 14ג закона о защите прав
   потребителя (исключение для цифрового контента) и с правом отказа в ЕС; кто даёт добровольный возврат за 14 дней —
   продавец (merchant of record: Paddle, Gumroad) или вы. Покупки в Mac App Store возвращает только Apple (п. 5.6).
5. Нужен ли пункт об экспортном контроле (раздел 12).

**Где показывать — обязательно до первого публичного DMG.** Без этого фраза «Устанавливая или используя Приложение,
вы принимаете…» — browse-wrap, на который запреты раздела 3 (извлечение Контента, обучение ИИ) надёжно не опираются:
1. страница продукта (R14), рядом с кнопкой «Скачать»: «Скачивая, вы принимаете Лицензионное соглашение и Политику
   конфиденциальности» — со ссылками;
2. файл `License.txt` (русская и английская версии) в DMG рядом с приложением: окончательный текст положить в
   `macos-app/Resources/License.txt` — `macos-app/scripts/release.sh` кладёт его в DMG и без `--internal`
   останавливается, если файла нет или в нём остались «[ВЛАДЕЛЕЦ: …]» / «ЧЕРНОВИК»;
3. в приложении — решить: пункт меню рыбки «Лицензия и приватность…», открывающий опубликованные адреса (новый ключ
   `Info.plist`, например `AQEulaURL`, рядом с `AQPrivacyPolicyURL`), или окно при первом запуске с кнопкой «Принимаю».

Первую фразу соглашения («Устанавливая или используя…») оставлять, только когда есть пункты 1 и 2.
Для Mac App Store (R16) — стандартное соглашение Apple или этот текст, дополненный минимальными условиями Apple.

**Связь с кодом и ROADMAP:** запрет извлекать медиа опирается на R9 (упаковка медиа в контейнер);
право заменять контент обновлением — на R7/R8 (любой ассет заменяется обновлением); обработка фото «своей рыбки»
на Mac без загрузки — на R17; ключ без сети и предпросмотр — на R18.

---

# Русская версия

## Лицензионное соглашение с конечным пользователем приложения [ВЛАДЕЛЕЦ: название приложения после R10; сейчас «Морской аквариум»]

Редакция [ВЛАДЕЛЕЦ: номер, например 1.0] от [ВЛАДЕЛЕЦ: дата публикации].

**Прочитайте до установки.** Устанавливая или используя Приложение, вы принимаете это Соглашение. Если вы
не согласны, не устанавливайте Приложение, а если уже установили — удалите его.

### 1. Стороны и термины

- **«Мы»** — [ВЛАДЕЛЕЦ: полное имя или название бизнеса], [ВЛАДЕЛЕЦ: статус и номер — עוסק פטור / עוסק מורשה,
  ת.ז. или ע.מ.], [ВЛАДЕЛЕЦ: почтовый адрес в Израиле], правообладатель Приложения.
- **«Вы»** — человек или организация, которые устанавливают или используют Приложение.
- **«Приложение»** — программа [ВЛАДЕЛЕЦ: название] для macOS, включая обновления, сопроводительные тексты и Контент.
- **«Контент»** — изображения, видео, 3D-модели, анимации, звуки, рыбы, кораллы и другие медиа в Приложении,
  в том числе полученные нами по лицензии от третьих лиц.
- **«Платный контент»** — дополнительные наборы и функции, которые могут продаваться отдельно.

### 2. Лицензия

Мы даём вам ограниченную, неисключительную и непередаваемую лицензию без права сублицензирования, которая
прекращается только по разделу 13: установить Приложение на компьютеры Mac, которыми вы владеете или управляете, и пользоваться им для личных целей
или для внутренних нужд вашей организации. [ВЛАДЕЛЕЦ: разрешать ли показ на экранах в общественных местах —
решить с юристом после сверки с лицензиями Контента.]

Приложение предоставляется по лицензии, а не продаётся. Все права, которые прямо не названы в этом Соглашении,
остаются за нами и нашими лицензиарами.

### 3. Что запрещено

Нельзя:
1. копировать Приложение, кроме установки и обычного резервного копирования вашего Mac (например, Time Machine);
2. распространять Приложение: продавать, сдавать в аренду, давать во временное пользование, выкладывать
   для скачивания, передавать другим или включать в свои продукты;
3. **извлекать Контент** и использовать его отдельно от Приложения — из пакета приложения, его кэша или памяти,
   с помощью записи экрана или любым другим способом. Например, нельзя использовать Контент как обои, фон или
   видеофутаж, в своих роликах, на сайтах, в приложениях или наборах медиа;
4. использовать Контент для обучения или настройки моделей искусственного интеллекта;
5. декомпилировать, дизассемблировать или изменять Приложение, обходить защиту Контента, лицензионные ключи
   или ограничения Платного контента — кроме случаев, когда закон прямо разрешает это, несмотря на запрет;
6. удалять или менять уведомления об авторских правах и товарных знаках;
7. использовать Приложение с нарушением закона.

Скриншоты и короткие записи экрана с работающим Приложением можно делать и публиковать для личных
некоммерческих целей и для обзоров, если по ним нельзя восстановить Контент как самостоятельный материал
(например, сделать из них обои или футаж). [ВЛАДЕЛЕЦ: подтвердить у юриста.]

### 4. Контент третьих лиц

Часть Контента мы получили по лицензии от третьих лиц. Эти лицензии разрешают использовать такой Контент только
внутри Приложения. Отдельно от Приложения вы не получаете на него никаких прав. Его правообладатели могут защищать
свои права напрямую.

Мы можем в любой момент заменить или убрать любой Контент обновлением, например если изменятся условия лицензии.

### 5. Бесплатная версия и Платный контент

1. **Сейчас Приложение бесплатно.**
2. Позже мы можем предложить Платный контент: [ВЛАДЕЛЕЦ: например, наборы особых рыб и «своя рыбка по фото»].
   Цена, состав и условия видны до покупки. [ВЛАДЕЛЕЦ: решить, обещать ли, что уже бесплатные функции не станут
   платными.]
3. Платный контент продаёт [ВЛАДЕЛЕЦ: продавец — Paddle, Gumroad или другой merchant of record; в Mac App Store —
   Apple]. Его условия продажи действуют вместе с этим Соглашением.
4. Лицензионный ключ — только для вас, на [ВЛАДЕЛЕЦ: 3] Mac. Передавать, продавать или публиковать ключ нельзя.
   Ключ проверяется на Mac, без сети.
5. Платный контент можно бесплатно посмотреть в режиме «Предпросмотр» в течение [ВЛАДЕЛЕЦ: 15 минут].
6. **Возврат денег:** в течение 14 дней с покупки, без объяснения причин. Напишите на [ВЛАДЕЛЕЦ: адрес поддержки].
   Права, которые даёт вам закон вашей страны (например, израильский закон о защите прав потребителя или правила
   ЕС), сохраняются. Покупки в Mac App Store возвращает Apple по своим правилам (reportaproblem.apple.com); сами мы
   вернуть их не можем.
7. Если нам придётся заменить купленный Контент из-за условий лицензии, мы постараемся дать равноценную замену. Если
   равноценной замены нет, по вашему запросу вернём деньги за этот Платный контент.
8. «Своя рыбка по фото»: фото обрабатывается на вашем Mac и никуда не загружается. Используйте только фото,
   на которые у вас есть права. Получившаяся рыбка — для использования в Приложении.
9. Если вам меньше 18 лет, покупайте только с согласия родителей.

### 6. Обновления

Мы можем выпускать обновления: исправления, новые функции, замену Контента. Они устанавливаются
[ВЛАДЕЛЕЦ: автоматически или после вашего подтверждения — решить к запуску автообновлений (R11)]. Обновления
подпадают под это Соглашение, если к ним не приложено новое. Мы не обязаны выпускать обновления или поддерживать
будущие версии macOS. На старых версиях macOS часть функций может перестать работать.

### 7. Права на Приложение и ваши предложения

Приложение, его код, дизайн, название и Контент принадлежат нам или нашим лицензиарам и защищены законами
об авторском праве и товарных знаках. Если вы присылаете идеи и предложения, мы можем использовать их бесплатно
и без обязательств перед вами. Персональные данные из отзывов мы обрабатываем по Политике конфиденциальности.

### 8. Приватность

Как Приложение обращается с данными, описано в Политике конфиденциальности: [ВЛАДЕЛЕЦ: URL политики]. Коротко:
Приложение само ничего не отправляет; данные попадают к нам, только когда вы отправляете отзыв или пишете нам.

### 9. Сторонние компоненты

Сейчас в Приложении нет стороннего программного кода. [ВЛАДЕЛЕЦ: если появятся компоненты с открытым кодом
(например, Sparkle для обновлений), перечислить их и их лицензии здесь и в Приложении.]

### 10. Отказ от гарантий

В максимальной степени, разрешённой законом, Приложение предоставляется **«как есть» и «как доступно»**, без
гарантий, явных или подразумеваемых, в том числе гарантий пригодности для определённой цели, ненарушения прав,
отсутствия ошибок и бесперебойной работы. Мы не гарантируем работу на любом Mac, мониторе или версии macOS,
определённую частоту кадров или расход энергии.

Ваши права потребителя, которые по закону нельзя ограничить договором, сохраняются.

### 11. Ограничение ответственности

В максимальной степени, разрешённой законом:
1. мы не отвечаем за косвенные, случайные и особые убытки, упущенную выгоду, потерю данных и перерывы в работе;
2. наша общая ответственность ограничена суммой, которую вы заплатили нам за Приложение и Платный контент
   за 12 месяцев до претензии, а если вы ничего не платили — [ВЛАДЕЛЕЦ: суммой, например 50 долларов США].

Эти ограничения не действуют при умысле, грубой неосторожности, обмане, причинении вреда жизни или здоровью,
а также там, где закон их не допускает.

### 12. Экспортный контроль

Вы подтверждаете, что не находитесь в стране под эмбарго, не включены в санкционные списки и используете
Приложение по законам об экспорте Израиля и США. [ВЛАДЕЛЕЦ: подтвердить у юриста, нужен ли этот раздел.]

### 13. Прекращение

Соглашение действует, пока вы пользуетесь Приложением. Вы можете прекратить его в любой момент, удалив
Приложение. При нарушении Соглашения оно прекращается автоматически. После прекращения вы должны перестать
пользоваться Приложением и удалить его. Разделы 3, 4, 7, 10, 11, 14 и 16 действуют и после прекращения.

### 14. Применимое право и споры

Соглашение регулируется законами Государства Израиль без учёта норм о выборе права. Конвенция ООН о договорах
международной купли-продажи товаров не применяется. Споры рассматривают компетентные суды
[ВЛАДЕЛЕЦ: Тель-Авива-Яффо — подтвердить].

Если вы потребитель (в Израиле, ЕС или другой стране), вы сохраняете защиту обязательных норм страны вашего проживания
и право обратиться в суд по месту жительства, если его даёт закон.

### 15. Apple

Apple не является стороной этого Соглашения и не отвечает за Приложение. [ВЛАДЕЛЕЦ: для Mac App Store (R16) —
стандартное соглашение Apple или этот текст с минимальными условиями Apple.]

### 16. Прочее

1. Это Соглашение вместе с Политикой конфиденциальности и условиями продавца — полное соглашение между нами
   о Приложении.
2. Если какое-то положение недействительно, остальные продолжают действовать.
3. Если мы не воспользовались правом сразу, это не отказ от него.
4. Мы можем передать свои права и обязанности при продаже или передаче бизнеса. Вы — только с нашего письменного
   согласия.
5. Новую редакцию мы публикуем на сайте с новой датой. О существенных изменениях сообщим на сайте или
   в Приложении. Если вы продолжаете пользоваться Приложением после вступления новой редакции в силу, она
   действует для вас. Изменения, ухудшающие условия уже купленного Платного контента, к нему без вашего согласия
   не применяются.
6. Соглашение составлено на русском и английском языках. [ВЛАДЕЛЕЦ: какая версия имеет силу при расхождении —
   предлагаем английскую; нужна ли версия на иврите — решить с юристом.]

### 17. Контакты

[ВЛАДЕЛЕЦ: адрес поддержки на домене продукта; сейчас support@tonamorph.com], [ВЛАДЕЛЕЦ: почтовый адрес].

---

# English version

## End User Licence Agreement for [ВЛАДЕЛЕЦ: app name after R10; currently «Морской аквариум»]

Version [ВЛАДЕЛЕЦ: number, e.g. 1.0], effective [ВЛАДЕЛЕЦ: publication date].

**Please read before installing.** By installing or using the App you accept this Agreement. If you do not agree,
do not install the App, and if you have already installed it, delete it.

### 1. Parties and definitions

- **"We", "us"** — [ВЛАДЕЛЕЦ: full name or business name], [ВЛАДЕЛЕЦ: status and number — Osek Patur /
  Osek Murshe, ID or VAT number], [ВЛАДЕЛЕЦ: postal address in Israel], the owner of the rights in the App.
- **"You"** — the person or organisation installing or using the App.
- **"App"** — the macOS application [ВЛАДЕЛЕЦ: name], including updates, accompanying texts and the Content.
- **"Content"** — images, video, 3D models, animations, sounds, fish, corals and other media in the App, including
  media we license from third parties.
- **"Paid Content"** — additional packs and features that may be sold separately.

### 2. Licence

We grant you a limited, non-exclusive, non-transferable licence, without the right to sublicense, that ends only as
set out in section 13, to install the App on Mac computers that you own or control and to use it for personal purposes or for the internal
purposes of your organisation. [ВЛАДЕЛЕЦ: whether to allow display on screens in public places — decide with the
lawyer after checking the Content licences.]

The App is licensed, not sold. All rights not expressly granted in this Agreement are reserved by us and our
licensors.

### 3. Restrictions

You may not:
1. copy the App, except to install it and as part of ordinary backups of your Mac (e.g. Time Machine);
2. distribute the App: sell, rent, lend, offer it for download, transfer it to others or include it in your own
   products;
3. **extract the Content** or use it separately from the App — from the application bundle, its cache or memory,
   by screen recording or by any other means. For example, you may not use the Content as wallpaper, a background or
   stock footage, or in your own videos, websites, apps or media collections;
4. use the Content to train or fine-tune artificial intelligence models;
5. decompile, disassemble or modify the App, or circumvent the protection of the Content, licence keys or Paid
   Content restrictions — except where the law expressly permits this despite this restriction;
6. remove or alter copyright or trademark notices;
7. use the App in breach of any law.

You may take and share screenshots and short screen recordings of the App in operation for personal,
non-commercial purposes and for reviews, provided the Content cannot be recovered from them as standalone material
(for example, turned into wallpaper or footage). [ВЛАДЕЛЕЦ: confirm with the lawyer.]

### 4. Third-party content

Some of the Content is licensed to us by third parties. Those licences allow such Content to be used only within the
App. You receive no rights to it outside the App. Its owners may enforce their rights directly.

We may replace or remove any Content at any time through an update, for example if licence terms change.

### 5. Free version and Paid Content

1. **The App is currently free.**
2. Later we may offer Paid Content: [ВЛАДЕЛЕЦ: e.g. packs of special fish and "your own fish from a photo"]. Price,
   contents and terms are shown before purchase. [ВЛАДЕЛЕЦ: decide whether to promise that features already free
   will not become paid.]
3. Paid Content is sold by [ВЛАДЕЛЕЦ: reseller — Paddle, Gumroad or another merchant of record; Apple in the Mac
   App Store]. Its terms of sale apply in addition to this Agreement.
4. A licence key is for you alone, on up to [ВЛАДЕЛЕЦ: 3] Macs. You may not share, sell or publish your key. The
   key is checked on your Mac, without a network connection.
5. You can try Paid Content free of charge in "Preview" mode for [ВЛАДЕЛЕЦ: 15 minutes].
6. **Refunds:** within 14 days of purchase, no reason needed. Write to [ВЛАДЕЛЕЦ: support address]. Any rights you
   have under the law of your country (for example, the Israeli Consumer Protection Law or EU rules) are not
   affected. Purchases made in the Mac App Store are refunded by Apple under its own rules
   (reportaproblem.apple.com); we cannot refund them ourselves.
7. If we have to replace purchased Content because of licence terms, we will make reasonable efforts to provide an
   equivalent replacement. If no equivalent replacement is available, we will refund that Paid Content on request.
8. "Your own fish from a photo": the photo is processed on your Mac and is not uploaded anywhere. Use only photos
   you have the rights to. The resulting fish is for use within the App.
9. If you are under 18, purchase only with a parent's consent.

### 6. Updates

We may release updates: fixes, new features, replacement Content. Updates are installed [ВЛАДЕЛЕЦ: automatically
or after your confirmation — decide when automatic updates arrive (R11)]. Updates are covered by this Agreement
unless they come with a new one. We are not obliged to release updates or to support future versions of macOS.
Some features may stop working on older versions of macOS.

### 7. Ownership and your suggestions

The App, its code, design, name and Content belong to us or our licensors and are protected by copyright and
trademark laws. If you send us ideas or suggestions, we may use them free of charge and without any obligation to
you. Personal data in feedback is handled under the Privacy Policy.

### 8. Privacy

How the App handles data is described in the Privacy Policy: [ВЛАДЕЛЕЦ: policy URL]. In short, the App sends
nothing on its own; we receive data only when you send feedback or write to us.

### 9. Third-party components

The App currently contains no third-party software code. [ВЛАДЕЛЕЦ: if open-source components are added (e.g.
Sparkle for updates), list them and their licences here and in the App.]

### 10. Disclaimer of warranties

To the maximum extent permitted by law, the App is provided **"as is" and "as available"**, without warranties of any
kind, express or implied, including warranties of fitness for a particular purpose, non-infringement, freedom from
errors and uninterrupted operation. We do not guarantee that the App works on every Mac, display or version of
macOS, or any particular frame rate or energy use.

Your consumer rights that cannot be limited by contract under applicable law are not affected.

### 11. Limitation of liability

To the maximum extent permitted by law:
1. we are not liable for indirect, incidental or special damages, lost profits, loss of data or interruption of use;
2. our total liability is limited to the amount you paid us for the App and Paid Content in the 12 months before the
   claim, or, if you paid nothing, to [ВЛАДЕЛЕЦ: an amount, e.g. USD 50].

These limitations do not apply to wilful misconduct, gross negligence, fraud, death or personal injury, or where the
law does not allow them.

### 12. Export control

You confirm that you are not located in an embargoed country, are not on a sanctions list, and will use the App in
compliance with the export laws of Israel and the United States. [ВЛАДЕЛЕЦ: confirm with the lawyer whether this
section is needed.]

### 13. Termination

This Agreement applies for as long as you use the App. You may end it at any time by deleting the App. It ends
automatically if you breach it. After it ends you must stop using the App and delete it. Sections 3, 4, 7, 10, 11,
14 and 16 survive termination.

### 14. Governing law and disputes

This Agreement is governed by the laws of the State of Israel, without regard to its conflict-of-laws rules. The UN
Convention on Contracts for the International Sale of Goods does not apply. Disputes are heard by the competent
courts of [ВЛАДЕЛЕЦ: Tel Aviv-Jaffa — confirm].

If you are a consumer (in Israel, the EU or elsewhere), you keep the protection of the mandatory laws of your country of
residence and any right the law gives you to bring proceedings in the courts where you live.

### 15. Apple

Apple is not a party to this Agreement and is not responsible for the App. [ВЛАДЕЛЕЦ: for the Mac App Store (R16) —
Apple's standard EULA, or this text with Apple's minimum terms added.]

### 16. General

1. This Agreement, together with the Privacy Policy and the reseller's terms, is the entire agreement between us
   about the App.
2. If any provision is invalid, the rest remains in force.
3. A failure or delay in exercising a right is not a waiver of it.
4. We may transfer our rights and obligations if the business is sold or transferred. You may do so only with our
   written consent.
5. We publish each new version on the website with a new date and announce material changes on the website or in
   the App. If you keep using the App after a new version takes effect, it applies to you. Changes that worsen the
   terms of Paid Content you have already bought do not apply to it without your consent.
6. This Agreement is written in Russian and English. [ВЛАДЕЛЕЦ: which version prevails in case of discrepancy —
   we suggest English; whether a Hebrew version is needed — decide with the lawyer.]

### 17. Contact

[ВЛАДЕЛЕЦ: support address on the product domain; currently support@tonamorph.com], [ВЛАДЕЛЕЦ: postal address].
