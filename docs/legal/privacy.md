# Политика конфиденциальности / Privacy Policy — ЧЕРНОВИК / DRAFT

> **ЧЕРНОВИК. Не публиковать до проверки израильским юристом (ROADMAP, задача R13).**
> Текст подготовлен по тому, что приложение делает на самом деле (код на 22.10.2026), а не по шаблону.
> Это не юридическая консультация. Всё, что должен вписать или решить владелец, помечено
> `[ВЛАДЕЛЕЦ: …]`; найти все места: поиск по «ВЛАДЕЛЕЦ».
>
> **DRAFT. Do not publish before review by an Israeli lawyer (ROADMAP task R13).** Based on what the app
> actually does (code as of 22 Oct 2026). Not legal advice. Every placeholder is marked `[ВЛАДЕЛЕЦ: …]` (owner).

## Для владельца — удалить этот блок перед публикацией

**Что вписать (плейсхолдеры):**
1. Название приложения после R10 (сейчас «Морской аквариум», англ. — пока нет).
2. Ваше полное имя или название бизнеса, статус (осек патур / осек мурше), номер (ת.ז. или ע.מ.), почтовый адрес в Израиле.
3. Адрес поддержки на домене продукта (сейчас `support@tonamorph.com`, письма пересылаются вам).
4. Почтовый провайдер и сервис пересылки домена (например, Cloudflare Email Routing → Google Gmail): письма на
   адрес поддержки проходят через оба.
5. Номер редакции и дата публикации.
6. Разделы «Обновления» и «Покупки» — оставить с пометкой «вступает в силу…» или убрать до появления функции.
7. ИИ-сервис для разбора отзывов (разделы 5–7) — выбрать одно:
   - Claude по коммерческим условиям (тариф Team или API/Console — в них есть DPA): тогда он «обработчик»;
   - личная подписка (Free/Pro/Max): Anthropic работает по своим потребительским условиям, без DPA, — это **не**
     наш обработчик; в тексте — вариант «по своей политике», и в настройках выключить использование чатов для обучения.

**Вопросы юристу:**
1. Нужно ли регистрировать базу данных и назначать ответственного за защиту данных по поправке 13 (для малого разработчика, судя по исследованию, — нет, но подтвердить).
2. Нужен ли представитель в ЕС по ст. 27 GDPR (обработка эпизодическая и мелкая — возможно, нет).
3. Нужна ли версия на иврите для пользователей в Израиле и какая языковая версия имеет силу при расхождении.
4. Достаточно ли текста согласия в окне отзыва (`fb-consent-ru-2`) и галочки рассылки (`fb-marketing-ru-2`)
   для уведомления по ст. 11 закона и для ст. 30А Закона о связи: покрывает ли согласие + ссылка на политику все
   пункты ст. 11 в редакции поправки 13 (кто отвечает за данные, цель, добровольность и последствия отказа,
   получатели, право на доступ и исправление); нужна ли пометка «פרסומת» для получателей за пределами Израиля.
5. Срок хранения бухгалтерских записей о продажах (обычно 7 лет — уточнить у бухгалтера).

**До выпуска v1.0 — обязательно:**
- Опубликовать политику и вписать её URL в `macos-app/Resources/Info.plist`, ключ `AQPrivacyPolicyURL` (только
  https). Тогда под галочкой согласия в окне отзыва появится ссылка «Политика конфиденциальности» — на неё опирается
  уведомление по ст. 11: текст согласия в окне говорит, что «кто отвечает за данные, кому они передаются и ваши
  права» — в политике. `macos-app/scripts/release.sh` без `--internal` останавливается, если ключ пуст или не https.
- Та же ссылка — на странице продукта (R14) и, позже, в App Store Connect (R16).
- Любая правка текста согласия в приложении → новая версия согласия в коде и правка этой политики (и наоборот).

**Правила для владельца (выполнять всегда):**
- **ИИ-разбор отзывов:** перед вставкой письма в ИИ удалять из него имя и адрес отправителя, подпись, вложения и
  цитаты заголовков (From/To/Reply-To) — в ИИ уходит только текст отзыва.
- **Рассылка «группе первых пользователей» (ст. 30А Закона о связи):** вносить адрес в список, только если он
  совпадает с адресом отправителя письма-отзыва; если не совпадает — одно письмо без рекламы с просьбой подтвердить,
  без ответа не вносить. В каждом письме: слово «פרסומת» в начале темы, ваше имя и почтовый адрес, строка «Чтобы
  отписаться, ответьте „отписаться“ на это письмо». Письма-отзывы с отметкой «Группа первых пользователей: да
  (fb-marketing-…, время)» хранить как доказательство согласия, пока адрес в списке. Нарушение — до ₪1 000 за
  письмо без доказательства ущерба.

**Где в коде проверены факты** (при изменении кода обновить политику):
`macos-app/Sources/Feedback.swift` (тексты согласий, сроки 90 дней / 100 файлов, маршруты доставки, что входит в
письмо: время создания, язык, версия и время согласия), `FeedbackWindow.swift` (галочки по умолчанию сняты;
диагностику приложение само не включает — для «Ошибки» только подсказка), `Diagnostics.swift` (состав диагностики и
что не собирается), `Lifecycle.swift` (настройки и счётчики в UserDefaults, системный журнал без личных данных),
`WallpaperWindow.swift` (хранилище WebKit по умолчанию: `~/Library/WebKit/…`, `~/Library/Caches/…`),
`AppDelegate.swift` (автозапуск через `SMAppService` — объекты входа macOS),
`Coverage.swift` (размеры окон для паузы, без заголовков и названий), `Resources/Info.plist`
(`AQFeedbackEndpoint` пуст, `AQFeedbackEmail`), `aquarium/index.html` (localStorage — уровень качества,
sessionStorage — служебные метки), `docs/plans/feedback-window-spec.md` (24 месяца, сервер в ЕС),
`docs/plans/feedback-ai-pipeline.md` (разбор отзывов в ИИ-чате без коннекторов).

---

# Русская версия

## Политика конфиденциальности приложения [ВЛАДЕЛЕЦ: название приложения после R10; сейчас «Морской аквариум»]

Редакция [ВЛАДЕЛЕЦ: номер, например 1.0] от [ВЛАДЕЛЕЦ: дата публикации].

### Коротко

- Приложение — живые обои с аквариумом. Оно работает на вашем Mac и **само ничего не отправляет**.
  В нём нет рекламы, аналитики, счётчиков посещений, SDK слежения и автоматических отчётов о сбоях.
- Данные попадают к нам, только когда **вы сами** отправляете отзыв (после галочки согласия) или пишете нам письмо.
- E-mail в отзыве **необязателен**. Новости и опросы приходят, только если вы **отдельно** поставили галочку;
  по умолчанию она снята.
- Диагностику и снимок аквариума вы прикладываете по желанию. Перед отправкой видно, что именно уйдёт.
- Мы не продаём данные и не используем их для рекламы.

### 1. Кто отвечает за данные и как с нами связаться

Ответственный за обработку данных (controller по GDPR; בעל שליטה במאגר מידע — контролёр базы данных по Закону о
защите частной жизни, 5741-1981, в редакции поправки 13): [ВЛАДЕЛЕЦ: полное имя или название бизнеса], [ВЛАДЕЛЕЦ: статус и номер — עוסק פטור / עוסק מורשה,
ת.ז. или ע.מ.], [ВЛАДЕЛЕЦ: почтовый адрес в Израиле]. Далее — «мы».

Вопросы о приватности, поддержка и запросы о ваших данных: [ВЛАДЕЛЕЦ: адрес поддержки на домене продукта;
сейчас support@tonamorph.com].

Ответственного за защиту данных (DPO) мы не назначали: [ВЛАДЕЛЕЦ: подтвердить у юриста, что для нашего объёма
он не обязателен]. Представитель в ЕС: [ВЛАДЕЛЕЦ: нужен ли по ст. 27 GDPR; если нужен — имя и адрес].

### 2. На что распространяется политика

На приложение для macOS, скачанное с нашего сайта, и на переписку с нами. Если приложение будет
распространяться через Mac App Store, дополнительно действует политика конфиденциальности Apple. Сайт продукта и
лист ожидания описаны в [ВЛАДЕЛЕЦ: отдельной политике сайта или разделе ниже — решить к запуску сайта (R14)].

### 3. Что остаётся только на вашем Mac

Эти данные не покидают ваш компьютер. У нас к ним доступа нет.

| Что | Где | Зачем | Сколько хранится |
|---|---|---|---|
| Настройки: тема аквариума, «Показать FPS», «Только на главном экране» | Настройки приложения в `~/Library/Preferences/` | Чтобы помнить ваш выбор | Пока вы их не удалите |
| Автозапуск | Объекты входа macOS (Системные настройки ▸ Основные ▸ Объекты входа) | Запуск при входе | Пока вы его не выключите |
| Технические счётчики: перезагрузки страницы аквариума, сбои и «зависания» движка (время, номер экрана, причина) | Там же | Чтобы при вашей жалобе на сбой было видно, что произошло | Последние 20 записей каждого вида |
| Уровень качества графики для каждого экрана и режима питания; служебные метки движка (номер запуска, последние замеры кадров) | Хранилище встроенного браузера приложения: `~/Library/WebKit/com.gregorydich.aquariumwallpaper` (и его кэш в `~/Library/Caches/com.gregorydich.aquariumwallpaper`) | Плавная анимация без перегрева; разбор сбоев | Уровень качества — пока не удалите; служебные метки — до закрытия приложения |
| Черновик отзыва (тема, текст, e-mail, рыбка) | Настройки приложения | Чтобы текст не пропал, если вы закрыли окно | До отправки или пока вы не очистите поля |
| Последний e-mail из отзыва | Настройки приложения | Подставить его в следующий раз | Забывается, если вы отправите отзыв без e-mail |
| Время последних отправок отзывов | Настройки приложения | Ограничение: не больше 5 отзывов за 10 минут | 10 минут |
| Копии отправленных отзывов (`<id>.json`) и снимков (`<id>.jpg`) | `~/Library/Application Support/AquariumWallpaper/Feedback/`, доступ только у вашей учётной записи macOS | Чтобы отзыв не потерялся и его можно было отправить повторно | Копии отправленных удаляются через 90 дней (проверка при запуске); всего хранится не больше 100 последних |
| Служебные сообщения о работе (без личных данных) | Системный журнал macOS | Диагностика | По правилам macOS |

Кроме того, приложение **только в памяти, без записи и без отправки** использует:
- **положение и размер окон на экране** (без заголовков, названий программ и содержимого; разрешение «Запись
  экрана» не нужно и не запрашивается) — чтобы ставить аквариум на паузу, когда рабочий стол закрыт окнами;
- **состояние питания** (батарея, режим энергосбережения, нагрев) — чтобы снижать частоту кадров.

**Как удалить всё локальное:** выключите в меню рыбки «Запускать при входе», выйдите из приложения, удалите его из
«Программ», удалите папки `~/Library/Application Support/AquariumWallpaper`,
`~/Library/WebKit/com.gregorydich.aquariumwallpaper` и `~/Library/Caches/com.gregorydich.aquariumwallpaper`
(и `~/Library/Saved Application State/com.gregorydich.aquariumwallpaper.savedState`, если она есть) и выполните в
Терминале `defaults delete com.gregorydich.aquariumwallpaper`.

### 4. Что попадает к нам — только по вашему действию

#### 4.1. Окно «Написать отзыв…»

Кнопка «Отправить» работает, только если вы отметили согласие. Галочка согласия по умолчанию **снята**.

**Всегда входит в отзыв:**
- текст сообщения и тема («Ошибка», «Идея», «Хочу рыбку», «Другое»);
- номер отзыва — случайный, создаётся заново для каждого отзыва и не связан ни с вами, ни с вашим Mac;
- версия приложения, версия macOS, время создания, язык интерфейса;
- отметка о согласии: время и версия текста согласия (и то же для согласия на «группу первых пользователей», если
  вы его дали).

**Только если вы сами указали или включили:**
- **e-mail для ответа** — чтобы ответить на этот отзыв;
- **название рыбки**, которую вы хотите видеть;
- **согласие на «группу первых пользователей»** — отдельная галочка, по умолчанию снята, доступна только при
  указанном e-mail. Она разрешает присылать короткие опросы и новости о новых рыбках;
- **снимок аквариума** — флажок по умолчанию выключен. Снимается только изображение аквариума, без иконок,
  окон и вашего рабочего стола; JPEG не больше 1600 пикселей и 400 КБ;
- **диагностика** — флажок по умолчанию выключен; для темы «Ошибка» окно предложит его включить. Точное содержимое
  видно по кнопке «Показать, что отправится». Состав: версия и сборка macOS, модель Mac (например, Mac15,6),
  тип процессора и работа через Rosetta, объём памяти, размеры и масштаб экранов, светлое или тёмное оформление,
  питание от батареи, режим энергосбережения, нагрев, включён ли автозапуск, время работы приложения,
  предпочитаемый язык, показатели движка (кадры в секунду, время кадра, уровень качества, число рыб, тема).

**Не собираем никогда:** серийный номер, аппаратный идентификатор (UUID), имя пользователя или компьютера,
IP-адрес и сведения о Wi-Fi, списки программ и окон, пути к файлам, постоянный идентификатор установки.

#### 4.2. Как отзыв доходит до нас

Строка внизу окна отзыва показывает, какой способ сейчас действует.

1. **Письмо (так работает текущая версия).** Открывается готовое письмо в вашей почтовой программе на адрес
   [ВЛАДЕЛЕЦ: адрес поддержки]. Вы проверяете его и отправляете сами. Письмо проходит через вашего почтового
   провайдера, сервис пересылки нашего домена и наш почтовый ящик. Мы видим также ваш адрес отправителя, имя отправителя и служебные заголовки письма —
   **даже если поле e-mail в окне вы не заполнили**. Снимок вы прикладываете к письму сами.
2. **Буфер обмена.** Если почтовой программы нет, текст отзыва копируется. Вы сами решаете, куда его вставить.
3. **Наш сервер (если включим в будущей версии).** Отзыв уходит по защищённому соединению (HTTPS) на сервер у
   [ВЛАДЕЛЕЦ: провайдер, например Cloudflare или AWS; хранение в ЕС]. Сервер видит ваш IP-адрес, как любой
   сайт; мы используем его только для защиты от злоупотреблений, в виде хэша, и храним не дольше 24 часов. Если
   сети не было, приложение повторит отправку само: до 5 попыток в течение 7 дней.

#### 4.3. «Скопировать диагностику» и «Тест производительности»

Эти пункты меню **ничего не отправляют**. Они копируют технический отчёт в буфер обмена, а вы решаете,
отправлять ли его нам. В отчёте: то же, что в диагностике выше, а также название процессора (например,
Apple M4 Pro), технические счётчики из раздела 3, номера и размеры экранов с аквариумом и замеры кадров.

#### 4.4. Письма в поддержку

Всё, что вы пишете нам сами, включая ваш адрес и вложения.

#### 4.5. Проверка обновлений — [ВЛАДЕЛЕЦ: включить раздел, когда появятся автообновления (R11); до тех пор удалить]

Приложение раз в [ВЛАДЕЛЕЦ: период] запрашивает с нашего сайта список обновлений. При этом передаются только
версия приложения и версия macOS, без профиля системы. Сервер видит IP-адрес, как при любом запросе; мы его
не храним [ВЛАДЕЛЕЦ: проверить настройки журналов хостинга]. Число проверок мы считаем только в сумме, без
привязки к устройству. Проверку можно выключить в [ВЛАДЕЛЕЦ: где].

#### 4.6. Покупки — [ВЛАДЕЛЕЦ: вступает в силу с началом продаж (R15, R17, R18); до тех пор удалить]

Платный контент продаёт [ВЛАДЕЛЕЦ: продавец — Paddle, Gumroad или другой merchant of record]. Он принимает
оплату и обрабатывает платёжные данные по своей политике. Данные карты к нам не попадают. От продавца мы получаем
e-mail, страну, купленный товар, номер заказа и лицензионный ключ: чтобы выдать и восстановить покупку, помочь
и оформить возврат, вести учёт. Проверка ключа в приложении работает без сети. При покупке через Mac App Store
оплату обрабатывает Apple.

### 5. Зачем мы используем данные и на каком основании

| Цель | Данные | Основание |
|---|---|---|
| Ответить на отзыв, исправить ошибки, улучшить приложение | Отзыв, e-mail, снимок, диагностика | Ваше согласие (галочка в окне отзыва; ст. 6(1)(a) GDPR) |
| Опросы и новости для «группы первых пользователей» | E-mail | Отдельное согласие (вторая галочка; ст. 6(1)(a) GDPR; ст. 30А Закона о связи (бизек и вещание), 5742-1982) |
| Ответ на ваше письмо | Письмо и адрес | Ваш запрос; наш законный интерес отвечать пользователям (ст. 6(1)(f) GDPR) |
| Защита сервера от злоупотреблений (если сервер включён) | Хэш IP-адреса, до 24 часов | Законный интерес (ст. 6(1)(f) GDPR) |
| Продажа, выдача и восстановление покупок, возвраты | Данные заказа | Договор (ст. 6(1)(b) GDPR) |
| Бухгалтерия и налоги | Данные заказа | Обязанность по закону (ст. 6(1)(c) GDPR) |

Давать данные не обязательно. Без e-mail мы просто не сможем ответить. Автоматических решений, влияющих на вас,
и профилирования нет.

Чтобы разобрать много отзывов, мы можем передавать текст отзыва — без e-mail, имени, подписи и вложений — ИИ-сервису
[ВЛАДЕЛЕЦ: Claude, Anthropic PBC, США], в отдельном чате без доступа к другим системам. [ВЛАДЕЛЕЦ: по договору с DPA
(Claude Team или API) — «как обработчику, по нашему поручению»; по личной подписке — «он обрабатывает текст по своей
политике; использование чатов для обучения моделей выключено».]

### 6. Кому мы передаём данные

Мы **не продаём** персональные данные, не передаём их рекламодателям и не «делимся» ими (share) в смысле законов
штатов США. Доступ к данным есть только у нас и у сервисов ниже — обработчиков, которые работают по нашему поручению,
и тех, кто, как сказано ниже, действует самостоятельно:
- почта: [ВЛАДЕЛЕЦ: сервис пересылки домена] и [ВЛАДЕЛЕЦ: почтовый ящик, например Google (Gmail)];
- хостинг сервера отзывов, если он включён: [ВЛАДЕЛЕЦ: провайдер];
- сервис рассылок для «группы первых пользователей», если будет: [ВЛАДЕЛЕЦ: сервис или «рассылаем вручную»];
- ИИ-сервис для разбора отзывов (раздел 5): [ВЛАДЕЛЕЦ: сервис; обработчик — только по договору с DPA, иначе —
  самостоятельно, по своей политике];
- продавец платного контента — самостоятельно, как продавец (раздел 4.6);
- бухгалтер и налоговые органы — в объёме, который требует закон;
- государственные органы — только если этого требует закон или суд;
- покупатель или правопреемник бизнеса — при его продаже или передаче, на условиях этой политики.

### 7. Где обрабатываются данные

Мы находимся в Израиле. Европейская комиссия признала, что Израиль обеспечивает достаточный уровень защиты
данных. Наши провайдеры могут хранить данные в ЕС и США; передача идёт на условиях, которые требует закон
(стандартные договорные условия ЕС или EU–US Data Privacy Framework) [ВЛАДЕЛЕЦ: уточнить по каждому провайдеру].
ИИ-сервис для разбора отзывов (раздел 5) находится в США [ВЛАДЕЛЕЦ: основание передачи — по его договору (DPF или
стандартные условия); для личной подписки — решить с юристом].

### 8. Сколько мы храним данные

| Данные | Срок |
|---|---|
| Отзывы и вложения у нас (почта или сервер) | До 24 месяцев с получения, затем удаляются; раньше — по вашей просьбе |
| Переписка с поддержкой | [ВЛАДЕЛЕЦ: например, 24 месяца после последнего письма] |
| Адрес в «группе первых пользователей» | Пока вы не отпишетесь. После этого храним только адрес и дату отписки в списке «не писать» |
| Хэш IP-адреса на сервере | До 24 часов |
| Данные о покупках | [ВЛАДЕЛЕЦ: срок по требованию бухгалтера, обычно 7 лет] |
| Локальные копии на вашем Mac | См. раздел 3: 90 дней, не больше 100 отзывов |

### 9. Безопасность

Локальные копии отзывов доступны только вашей учётной записи macOS. Отправка на сервер — только по HTTPS. Почта
и сервисы, где лежат данные, защищены двухфакторным входом [ВЛАДЕЛЕЦ: включить 2FA везде]; доступ есть только
у нас. Мы следуем израильским правилам защиты информации (תקנות הגנת הפרטיות (אבטחת מידע), התשע"ז-2017).
Если произойдёт утечка, мы уведомим Управление по защите приватности и пострадавших, как требует закон.

### 10. Ваши права

Вы можете:
- узнать, какие данные о вас у нас есть, и получить их копию (ст. 13 Закона о защите частной жизни;
  ст. 15 GDPR);
- исправить или удалить неточные данные (ст. 14 закона; ст. 16 GDPR);
- потребовать удалить данные (ст. 17 GDPR) и ограничить их обработку (ст. 18 GDPR);
- получить данные в машиночитаемом виде (ст. 20 GDPR);
- возразить против обработки на основании законного интереса (ст. 21 GDPR);
- в любой момент отозвать согласие. Это не делает незаконной обработку до отзыва. Отозвать согласие на отзыв —
  написать нам. Отписаться от рассылки — ответить «отписаться» на любое письмо (ст. 17F Закона о защите частной
  жизни; ст. 30А Закона о связи);
- подать жалобу: в Израиле — в Управление по защите приватности (הרשות להגנת הפרטיות, gov.il); в ЕС — в надзорный
  орган своей страны.

Напишите на [ВЛАДЕЛЕЦ: адрес поддержки]. Ответим в течение 30 дней. Чтобы не выдать чужие данные, можем
попросить написать с того же адреса, который указан в отзыве.

### 11. Дети

Приложение не предназначено для сбора данных детей. Мы не собираем сознательно данные детей младше 13 лет.
Если вам меньше 16 лет, отправляйте отзыв с e-mail только вместе с родителем. Если мы узнаем, что получили данные
ребёнка без согласия родителей, мы их удалим.

### 12. Изменения политики

Новую редакцию мы публикуем по этому адресу с новой датой. О существенных изменениях сообщим на сайте или в
приложении. Если изменение касается того, на что вы давали согласие, мы попросим согласие заново.

### 13. Язык

Политика составлена на русском и английском языках. [ВЛАДЕЛЕЦ: какая версия имеет силу при расхождении —
предлагаем английскую; нужна ли версия на иврите — решить с юристом.]

---

# English version

## Privacy Policy for [ВЛАДЕЛЕЦ: app name after R10; currently «Морской аквариум»]

Version [ВЛАДЕЛЕЦ: number, e.g. 1.0], effective [ВЛАДЕЛЕЦ: publication date].

### Summary

- The app is a living aquarium wallpaper. It runs on your Mac and **sends nothing on its own**. It contains no
  ads, no analytics, no visit counters, no tracking SDKs and no automatic crash reporting.
- We receive data only when **you** send feedback (after ticking the consent box) or e-mail us.
- An e-mail address in feedback is **optional**. You get news and surveys only if you tick a **separate** box,
  which is unticked by default.
- Diagnostics and an aquarium snapshot are attached only if you choose to, and you can see what will be sent
  before sending.
- We do not sell your data or use it for advertising.

### 1. Who is responsible and how to contact us

Controller (under the GDPR; database controller (בעל שליטה במאגר מידע) under the Protection of Privacy Law,
5741-1981, as amended by Amendment 13): [ВЛАДЕЛЕЦ: full name or
business name], [ВЛАДЕЛЕЦ: status and number — Osek Patur / Osek Murshe, ID or VAT number], [ВЛАДЕЛЕЦ: postal
address in Israel] ("we", "us").

Privacy questions, support and data requests: [ВЛАДЕЛЕЦ: support address on the product domain; currently
support@tonamorph.com].

We have not appointed a data protection officer: [ВЛАДЕЛЕЦ: confirm with the lawyer that none is required at our
scale]. EU representative: [ВЛАДЕЛЕЦ: whether one is required under Art. 27 GDPR; if so, name and address].

### 2. Scope

This policy covers the macOS app downloaded from our website and your correspondence with us. If the app is
distributed through the Mac App Store, Apple's privacy policy also applies. The product website and the waiting
list are covered by [ВЛАДЕЛЕЦ: a separate website policy or a section below — decide when the site launches (R14)].

### 3. Data that stays on your Mac

This data never leaves your computer. We have no access to it.

| What | Where | Why | How long |
|---|---|---|---|
| Settings: aquarium theme, "Show FPS", "Main display only" | App preferences in `~/Library/Preferences/` | To remember your choices | Until you delete them |
| Launch at login | macOS Login Items (System Settings ▸ General ▸ Login Items) | To start at login | Until you turn it off |
| Technical counters: aquarium page reloads, engine crashes and freezes (time, display number, reason) | Same place | So that, if you report a problem, it is clear what happened | Last 20 entries of each kind |
| Graphics quality level per display and power mode; engine housekeeping marks (launch number, latest frame timings) | The app's built-in browser storage: `~/Library/WebKit/com.gregorydich.aquariumwallpaper` (and its cache in `~/Library/Caches/com.gregorydich.aquariumwallpaper`) | Smooth animation without overheating; crash analysis | Quality level until you delete it; housekeeping marks until the app quits |
| Feedback draft (topic, text, e-mail, fish) | App preferences | So your text is not lost if you close the window | Until sent or until you clear the fields |
| The last e-mail address used in feedback | App preferences | To pre-fill it next time | Forgotten when you send feedback without an e-mail |
| Times of your latest feedback sends | App preferences | Limit of 5 sends per 10 minutes | 10 minutes |
| Copies of sent feedback (`<id>.json`) and snapshots (`<id>.jpg`) | `~/Library/Application Support/AquariumWallpaper/Feedback/`, readable only by your macOS user account | So feedback is not lost and can be resent | Copies of delivered feedback are deleted after 90 days (checked at launch); at most the 100 most recent are kept |
| Operational messages without personal data | macOS system log | Troubleshooting | As macOS keeps its log |

The app also uses the following **in memory only, without storing or sending it**:
- **the position and size of windows on screen** (no titles, app names or content; the Screen Recording
  permission is neither needed nor requested), to pause the aquarium while the desktop is covered;
- **power state** (battery, Low Power Mode, thermal state), to lower the frame rate.

**To delete everything stored locally:** turn off «Запускать при входе» (Launch at login) in the fish menu, quit the
app, delete it from Applications, delete the folders `~/Library/Application Support/AquariumWallpaper`,
`~/Library/WebKit/com.gregorydich.aquariumwallpaper` and `~/Library/Caches/com.gregorydich.aquariumwallpaper` (and
`~/Library/Saved Application State/com.gregorydich.aquariumwallpaper.savedState`, if present), and run
`defaults delete com.gregorydich.aquariumwallpaper` in Terminal.

### 4. Data we receive — only when you act

#### 4.1. The "Send feedback…" window

The Send button works only after you tick the consent box. The consent box is **unticked** by default.

**Always included:**
- your message and its topic ("Bug", "Idea", "I want a fish", "Other");
- a feedback number — random, created anew for each message and linked neither to you nor to your Mac;
- app version, macOS version, time of creation, interface language;
- a consent record: the time and the version of the consent wording (and the same for the "early users group"
  consent, if you gave it).

**Only if you enter or switch it on:**
- **a reply e-mail address**, to answer this message;
- **the name of a fish** you would like to see;
- **consent to join the "early users group"** — a separate box, unticked by default and available only with an
  e-mail address. It lets us send you short surveys and news about new fish;
- **an aquarium snapshot** — off by default. Only the aquarium image is captured, without icons, windows or your
  desktop; a JPEG of at most 1600 pixels and 400 KB;
- **diagnostics** — off by default; for the «Ошибка» (Bug) topic the window suggests switching it on. The exact
  content is shown by "Show what will be sent". It contains: macOS version and build, Mac model identifier
  (e.g. Mac15,6), processor type and whether Rosetta is used, memory size, display sizes and scale, light or dark
  appearance, battery power, Low Power Mode, thermal state, whether launch at login is on, app uptime, preferred
  language, engine figures (frames per second, frame time, quality level, number of fish, theme).

**Never collected:** serial number, hardware identifier (UUID), user or computer name, IP address or Wi-Fi details,
lists of apps or windows, file paths, any persistent installation identifier.

#### 4.2. How your feedback reaches us

A line at the bottom of the feedback window shows which route is active.

1. **E-mail (how the current version works).** A pre-filled message opens in your mail app, addressed to
   [ВЛАДЕЛЕЦ: support address]. You review it and send it yourself. It passes through your mail provider, our
   domain's forwarding service and our mailbox.
   We also see your sender address, sender name and the message headers — **even if you left the e-mail field in
   the window empty**. You attach the snapshot to the message yourself.
2. **Clipboard.** If there is no mail app, the feedback text is copied. You decide where to paste it.
3. **Our server (if enabled in a future version).** Feedback is sent over an encrypted connection (HTTPS) to a
   server hosted by [ВЛАДЕЛЕЦ: provider, e.g. Cloudflare or AWS; storage in the EU]. Like any website, the server
   sees your IP address; we use it only to prevent abuse, as a hash, and keep it for no longer than 24 hours. If
   you were offline, the app retries on its own: up to 5 attempts within 7 days.

#### 4.3. "Copy diagnostics" and "Performance test"

These menu items **send nothing**. They copy a technical report to the clipboard, and you decide whether to send
it to us. The report contains the diagnostics listed above plus the processor name (e.g. Apple M4 Pro), the
technical counters from section 3, the numbers and sizes of the displays showing the aquarium, and frame timings.

#### 4.4. E-mails to support

Whatever you write to us yourself, including your address and attachments.

#### 4.5. Update checks — [ВЛАДЕЛЕЦ: include once automatic updates exist (R11); remove until then]

Every [ВЛАДЕЛЕЦ: interval] the app asks our website for the list of updates. Only the app version and the macOS
version are sent, with no system profile. Like any request, the server sees your IP address; we do not store it
[ВЛАДЕЛЕЦ: check the hosting log settings]. We count update checks only in total, never per device. You can turn
update checks off in [ВЛАДЕЛЕЦ: where].

#### 4.6. Purchases — [ВЛАДЕЛЕЦ: effective when sales start (R15, R17, R18); remove until then]

Paid content is sold by [ВЛАДЕЛЕЦ: reseller — Paddle, Gumroad or another merchant of record], which takes payment
and processes payment data under its own privacy policy. Card details never reach us. From the reseller we receive
your e-mail address, country, the product bought, the order number and the licence key, to deliver and restore
purchases, provide support and refunds, and keep accounts. The licence check inside the app works offline. For
purchases in the Mac App Store, Apple processes the payment.

### 5. Why we use data and on what legal basis

| Purpose | Data | Legal basis |
|---|---|---|
| Answer your feedback, fix bugs, improve the app | Feedback, e-mail, snapshot, diagnostics | Your consent (box in the feedback window; Art. 6(1)(a) GDPR) |
| Surveys and news for the "early users group" | E-mail | Separate consent (second box; Art. 6(1)(a) GDPR; s. 30A of the Communications (Telecommunications and Broadcasting) Law, 5742-1982) |
| Reply to your e-mail | Your message and address | Your request; our legitimate interest in answering users (Art. 6(1)(f) GDPR) |
| Protect the server from abuse (if the server is enabled) | IP address hash, up to 24 hours | Legitimate interest (Art. 6(1)(f) GDPR) |
| Sell, deliver and restore purchases; refunds | Order data | Contract (Art. 6(1)(b) GDPR) |
| Accounting and tax | Order data | Legal obligation (Art. 6(1)(c) GDPR) |

Providing data is voluntary. Without an e-mail address we simply cannot reply. We make no automated decisions
that affect you and do no profiling.

To sort large volumes of feedback we may pass the message text — without e-mail addresses, names, signatures or
attachments — to an AI service [ВЛАДЕЛЕЦ: Claude, Anthropic PBC, USA], in a separate session with no access to other
systems. [ВЛАДЕЛЕЦ: under a contract with a DPA (Claude Team or API) — "as our processor, on our instructions"; under
a personal subscription — "it processes the text under its own policy; use of chats for model training is turned
off".]

### 6. Who we share data with

We **do not sell** personal data, do not pass it to advertisers and do not "share" it as defined by US state privacy
laws. Only we and the services below have access — processors acting on our behalf, and those that act
independently, as stated:
- e-mail: [ВЛАДЕЛЕЦ: domain forwarding service] and [ВЛАДЕЛЕЦ: mailbox provider, e.g. Google (Gmail)];
- feedback server hosting, if enabled: [ВЛАДЕЛЕЦ: provider];
- mailing service for the "early users group", if any: [ВЛАДЕЛЕЦ: service, or "sent manually"];
- AI service for sorting feedback (section 5): [ВЛАДЕЛЕЦ: service; a processor only under a contract with a DPA,
  otherwise independently, under its own policy];
- the reseller of paid content, independently, as the seller (section 4.6);
- our accountant and the tax authorities, to the extent the law requires;
- public authorities, only where required by law or a court;
- a buyer or successor of the business, if it is sold or transferred, under the terms of this policy.

### 7. Where data is processed

We are based in Israel, which the European Commission recognises as providing an adequate level of data
protection. Our providers may store data in the EU and the US; such transfers rely on the safeguards the law
requires (EU Standard Contractual Clauses or the EU–US Data Privacy Framework) [ВЛАДЕЛЕЦ: confirm for each
provider]. The AI service for sorting feedback (section 5) is in the US [ВЛАДЕЛЕЦ: transfer basis — under its
contract (DPF or Standard Contractual Clauses); for a personal subscription — decide with the lawyer].

### 8. How long we keep data

| Data | Period |
|---|---|
| Feedback and attachments on our side (mailbox or server) | Up to 24 months from receipt, then deleted; earlier on request |
| Support correspondence | [ВЛАДЕЛЕЦ: e.g. 24 months after the last message] |
| Address in the "early users group" | Until you unsubscribe. After that we keep only the address and the date in a do-not-contact list |
| IP address hash on the server | Up to 24 hours |
| Purchase records | [ВЛАДЕЛЕЦ: period required by the accountant, usually 7 years] |
| Local copies on your Mac | See section 3: 90 days, at most 100 messages |

### 9. Security

Local feedback copies are readable only by your macOS user account. Data is sent to the server only over HTTPS.
The mailbox and services holding data are protected by two-factor sign-in [ВЛАДЕЛЕЦ: enable 2FA everywhere], and
only we have access. We follow the Israeli Privacy Protection (Data Security) Regulations, 5777-2017. In the event
of a data breach we will notify the Privacy Protection Authority and the people affected, as the law requires.

### 10. Your rights

You may:
- find out what data we hold about you and get a copy (s. 13 of the Protection of Privacy Law; Art. 15 GDPR);
- correct or delete inaccurate data (s. 14 of the Law; Art. 16 GDPR);
- ask us to erase your data (Art. 17 GDPR) or restrict its use (Art. 18 GDPR);
- receive your data in a machine-readable format (Art. 20 GDPR);
- object to processing based on legitimate interest (Art. 21 GDPR);
- withdraw consent at any time; this does not affect processing before the withdrawal. To withdraw consent for
  feedback, write to us. To leave the mailing list, reply "unsubscribe" to any message (s. 17F of the Protection of
  Privacy Law; s. 30A of the Communications Law);
- complain to a regulator: in Israel, the Privacy Protection Authority (gov.il); in the EU, the supervisory
  authority of your country.

Write to [ВЛАДЕЛЕЦ: support address]. We reply within 30 days. To avoid disclosing someone else's data, we may ask
you to write from the address given in your feedback.

### 11. Children

The app is not designed to collect children's data. We do not knowingly collect data from children under 13. If you
are under 16, send feedback with an e-mail address only together with a parent. If we learn that we have received
a child's data without parental consent, we will delete it.

### 12. Changes to this policy

We publish each new version at this address with a new date. We announce material changes on the website or in
the app. If a change affects something you consented to, we will ask for your consent again.

### 13. Language

This policy is written in Russian and English. [ВЛАДЕЛЕЦ: which version prevails in case of discrepancy — we
suggest English; whether a Hebrew version is needed — decide with the lawyer.]
