/* ============================================================
   СПИСОК РЫБ аквариума — имена, описания, размеры, количество.
   Подключается из index.html как <script src="fish/manifest.js">.

   • Положите рядом картинку  fish/<id>.png  — прозрачный PNG, рыба
     повёрнута ВПРАВО (+x), вид сбоку. Тогда вместо векторной рыбки
     будет ваша реалистичная.
   • Пока картинки нет — рисуется векторный двойник (поле `fallback`),
     так что аквариум выглядит правильно сразу.
   • `count` — относительное количество (масштабируется под размер экрана).
   • `fallback` — один из: clown, regal, yellowtang, puffer, damsel,
     coralfish, chromis.
   • Повадки (этап E3, SPEC §3; старые поля speedMin/Max остаются запасными):
       habit     — cruise | graze | pick | hover | shoal | home | lurk | hide
                   (крейсер, «пасётся» на камне, выклёвывает из щелей, зависает,
                   стая, живёт в доме, сторож у норы, прячется за холмом);
       traits    — { shy, territorial, darty } 0..1: пугливость, территориальность, «рывковость»;
       zone      — [верх, низ] — доли толщи воды (0 — у поверхности, 1 — у песка);
       zRange    — [zMin, zMax] — глубина (1.0 — стекло … 2.6 — задняя стенка);
       cruiseBL  — [min, max] — крейсерская скорость в длинах тела в секунду;
       turnTime  — длительность разворота, с (0.35 мелкие … 0.8 групер);
       school    — { size, spacingBL } — стая (ведущий и ведомые);
       home      — id реквизита-дома из scene.js (актиния рыб-клоунов);
       veil      — (этап V2) вуалевые плавники: { tail, lag, beat } — tail — доля длины тела сзади, которая
                   «вуаль» (мягкий плавник, гнётся сильнее тела), lag — во сколько раз медленнее бежит волна
                   по вуали (плавник «струится» с запаздыванием), beat — множитель частоты биения хвоста
                   (< 1 — неторопливо). Без поля — обычный хвост.
     V2 (видео-задник): каньон теперь настоящей глубины до 2.6 — у крейсеров и стай zRange до 2.5
     (уплывают вглубь каньона и за дальний риф), у прячущихся (регал, огненный ангел) — до 2.05
     (укрытия за кромками колонн на z ≈ 1.95–2.0), рыба-бабочка выклёвывает и на дне каньона (до 2.1).
   ============================================================ */
window.FISH_MANIFEST = {
  facing: "right",
  fish: [
    {
      id: "clownfish",
      name: "Рыба-клоун (Amphiprion ocellaris)",
      description: "Оранжевая с тремя белыми полосами в чёрной окантовке. Живёт в актинии, плавает короткими рывками. Та самая «Немо».",
      image: "fish/clownfish.png",
      sizeMin: 85, sizeMax: 125, speedMin: 30, speedMax: 55, count: 2, fallback: "clown",
      habit: "home", traits: { shy: 0.5, territorial: 0.8, darty: 0.8 }, zone: [0.55, 0.95], zRange: [1.0, 1.25], cruiseBL: [0.5, 1.0], turnTime: 0.35, home: "anemone",
    },
    {
      id: "blue_tang",
      name: "Голубой хирург (Paracanthurus hepatus)",
      description: "Ярко-синее тело с чёрным «палитра»-узором и жёлтым хвостом. «Дори». Плавно скользит в толще воды.",
      image: "fish/blue_tang.png",
      sizeMin: 110, sizeMax: 150, speedMin: 34, speedMax: 60, count: 2, fallback: "regal",
      habit: "cruise", traits: { shy: 0.2, territorial: 0.1, darty: 0.3 }, zone: [0.08, 0.7], zRange: [1.0, 2.5], cruiseBL: [0.6, 1.0], turnTime: 0.5,
    },
    {
      id: "yellow_tang",
      name: "Жёлтый хирург (Zebrasoma flavescens)",
      description: "Насыщенно-жёлтый, дисковидный, с острым рыльцем. Днём ярко-жёлтый, ночью бледнеет.",
      image: "fish/yellow_tang.png",
      sizeMin: 90, sizeMax: 125, speedMin: 30, speedMax: 52, count: 2, fallback: "yellowtang",
      habit: "graze", traits: { shy: 0.2, territorial: 0.3, darty: 0.2 }, zone: [0.15, 0.85], zRange: [1.0, 1.8], cruiseBL: [0.5, 0.9], turnTime: 0.45,
    },
    {
      id: "powder_blue_tang",
      name: "Белогрудый хирург (Acanthurus leucosternon)",
      description: "Голубое тело, чёрная «маска» на голове, жёлтый спинной плавник и белая грудь. Очень контрастный.",
      image: "fish/powder_blue_tang.png",
      sizeMin: 100, sizeMax: 140, speedMin: 32, speedMax: 56, count: 1, fallback: "regal",
      habit: "cruise", traits: { shy: 0.2, territorial: 0.9, darty: 0.4 }, zone: [0.15, 0.75], zRange: [1.0, 1.7], cruiseBL: [0.5, 0.9], turnTime: 0.5,
    },
    {
      id: "pufferfish",
      name: "Спинорог-клоун (Balistoides conspicillum)",
      description: "Тёмный, с крупными белыми пятнами на брюхе и жёлтым «седлом» в леопардовую крапинку на спине, жёлтые губы. Звезда аквариума — величаво плывёт в центре кадра.",
      image: "fish/pufferfish.png",
      sizeMin: 150, sizeMax: 200, speedMin: 22, speedMax: 38, count: 1, fallback: "puffer",
      habit: "cruise", traits: { shy: 0.1, territorial: 0.4, darty: 0.1 }, zone: [0.15, 0.8], zRange: [1.05, 2.5], cruiseBL: [0.4, 0.75], turnTime: 0.65,
    },
    {
      id: "royal_gramma",
      name: "Королевская грамма (Gramma loreto)",
      description: "Маленькая: передняя половина фиолетовая, задняя — ярко-жёлтая, резкий переход посередине.",
      image: "fish/royal_gramma.png",
      sizeMin: 55, sizeMax: 80, speedMin: 30, speedMax: 50, count: 0, fallback: "damsel",
      habit: "hide", traits: { shy: 0.8, territorial: 0.5, darty: 0.6 }, zone: [0.45, 0.95], zRange: [1.0, 1.6], cruiseBL: [0.5, 1.0], turnTime: 0.35,
    },
    {
      id: "emperor_angelfish",
      name: "Императорский ангел (Pomacanthus imperator)",
      description: "Сине-жёлтые горизонтальные полосы, чёрная «маска» с синей окантовкой. Крупный и величавый.",
      image: "fish/emperor_angelfish.png",
      sizeMin: 120, sizeMax: 165, speedMin: 28, speedMax: 48, count: 1, fallback: "coralfish",
      habit: "graze", traits: { shy: 0.3, territorial: 0.4, darty: 0.1 }, zone: [0.2, 0.85], zRange: [1.05, 1.8], cruiseBL: [0.4, 0.75], turnTime: 0.6,
    },
    {
      id: "regal_angelfish",
      name: "Жемчужный ангел (Pygoplites diacanthus)",
      description: "Вертикальные оранжево-белые полосы в синей окантовке, синяя «грудь». Очень нарядный.",
      image: "fish/regal_angelfish.png",
      sizeMin: 105, sizeMax: 145, speedMin: 30, speedMax: 50, count: 1, fallback: "yellowtang",
      habit: "hide", traits: { shy: 0.8, territorial: 0.2, darty: 0.2 }, zone: [0.3, 0.9], zRange: [1.05, 2.05], cruiseBL: [0.4, 0.8], turnTime: 0.55,
    },
    {
      id: "mandarinfish",
      name: "Мандаринка (Synchiropus splendidus)",
      description: "Психоделические зелёно-оранжево-синие волнистые узоры. Маленькая, перемещается короткими зависаниями.",
      image: "fish/mandarinfish.png",
      sizeMin: 55, sizeMax: 80, speedMin: 22, speedMax: 40, count: 0, fallback: "damsel",
      habit: "pick", traits: { shy: 0.7, territorial: 0.1, darty: 0.3 }, zone: [0.7, 0.98], zRange: [1.0, 1.4], cruiseBL: [0.3, 0.6], turnTime: 0.4,
    },
    {
      id: "blue_chromis",
      name: "Голубой хромис (Chromis viridis)",
      description: "Мелкая мерцающая сине-зелёная рыбка. Держится стайкой — фон и «жизнь» сцены.",
      image: "fish/blue_chromis.png",
      sizeMin: 36, sizeMax: 56, speedMin: 34, speedMax: 58, count: 0, fallback: "chromis",
      habit: "shoal", traits: { shy: 0.3, territorial: 0.1, darty: 0.5 }, zone: [0.1, 0.6], zRange: [1.0, 2.2], cruiseBL: [0.7, 1.2], turnTime: 0.35, school: { size: 6, spacingBL: 1.3 },
    },
    {
      id: "flame_angel",
      name: "Огненный ангел (Centropyge loricula)",
      description: "Ярко-красно-оранжевый с тёмными вертикальными штрихами и сине-чёрной каймой плавников.",
      image: "fish/flame_angel.png",
      sizeMin: 60, sizeMax: 90, speedMin: 30, speedMax: 52, count: 1, fallback: "coralfish",
      habit: "hide", traits: { shy: 0.9, territorial: 0.3, darty: 0.6 }, zone: [0.4, 0.95], zRange: [1.05, 2.05], cruiseBL: [0.5, 1.0], turnTime: 0.4,
    },
    {
      id: "moorish_idol",
      name: "Мавританский идол (Zanclus cornutus)",
      description: "Чёрно-бело-жёлтые широкие полосы и длинный нитевидный спинной плавник. «Жабр» из «Немо».",
      image: "fish/moorish_idol.png",
      sizeMin: 110, sizeMax: 150, speedMin: 30, speedMax: 50, count: 1, fallback: "damsel",
      habit: "cruise", traits: { shy: 0.2, territorial: 0.1, darty: 0.1 }, zone: [0.08, 0.65], zRange: [1.0, 2.5], cruiseBL: [0.5, 0.85], turnTime: 0.6,
    },
    {
      id: "bicolor_angel",
      name: "Двухцветный ангел (Centropyge bicolor)",
      description: "Передняя половина жёлтая, задняя синяя, хвост жёлтый, синяя полоска над глазом. Частый обитатель рифовых аквариумов.",
      image: "fish/bicolor_angel.png",
      sizeMin: 80, sizeMax: 115, speedMin: 28, speedMax: 48, count: 0, fallback: "damsel",
      habit: "hide", traits: { shy: 0.7, territorial: 0.4, darty: 0.4 }, zone: [0.4, 0.95], zRange: [1.05, 1.8], cruiseBL: [0.5, 0.9], turnTime: 0.4,
    },
    {
      id: "spanish_hogfish",
      name: "Испанская рыба-кабан (Bodianus rufus)",
      description: "Пурпурно-красная спина, жёлтые брюхо и хвост. Яркий акцент сцены — держится у самого рифа.",
      image: "fish/spanish_hogfish.png",
      sizeMin: 95, sizeMax: 135, speedMin: 30, speedMax: 52, count: 0, fallback: "coralfish",
      habit: "cruise", traits: { shy: 0.2, territorial: 0.3, darty: 0.3 }, zone: [0.3, 0.9], zRange: [1.0, 1.8], cruiseBL: [0.6, 1.0], turnTime: 0.5,
    },
    {
      id: "anthias",
      name: "Антиас (Pseudanthias squamipinnis)",
      description: "Розово-оранжевая стайная рыбка с лировидным хвостом. Держится группой в толще воды над рифом.",
      image: "fish/anthias.png",
      sizeMin: 66, sizeMax: 90, speedMin: 34, speedMax: 58, count: 6, fallback: "coralfish",
      habit: "shoal", traits: { shy: 0.3, territorial: 0.1, darty: 0.5 }, zone: [0.08, 0.6], zRange: [1.0, 2.5], cruiseBL: [0.6, 1.1], turnTime: 0.35, school: { size: 6, spacingBL: 1.25 },
    },
    {
      id: "copperband",
      name: "Медная рыба-бабочка (Chelmon rostratus)",
      description: "Белая с медно-жёлтыми полосами и «ложным глазом» на спинном плавнике, длинное рыльце — выедает полипы из щелей.",
      image: "fish/copperband.png",
      sizeMin: 90, sizeMax: 120, speedMin: 26, speedMax: 44, count: 1, fallback: "coralfish",
      habit: "pick", traits: { shy: 0.4, territorial: 0.2, darty: 0.2 }, zone: [0.35, 0.95], zRange: [1.0, 1.6], cruiseBL: [0.4, 0.75], turnTime: 0.5,
    },
    {
      id: "sergeant_major",
      name: "Сержант-майор (Abudefduf saxatilis)",
      description: "Серебристая с чёрными «сержантскими» полосами. Бойкая, плавает парами.",
      image: "fish/sergeant_major.png",
      sizeMin: 70, sizeMax: 100, speedMin: 34, speedMax: 60, count: 1, fallback: "damsel",
      habit: "hover", traits: { shy: 0.2, territorial: 0.5, darty: 0.6 }, zone: [0.12, 0.7], zRange: [1.0, 2.0], cruiseBL: [0.6, 1.1], turnTime: 0.4,
    },
    {
      id: "striped_surgeon",
      name: "Полосатый хирург (Acanthurus lineatus)",
      description: "Сине-жёлтые продольные полосы, острые «скальпели» у хвоста. Быстрый и территориальный.",
      image: "fish/striped_surgeon.png",
      sizeMin: 110, sizeMax: 150, speedMin: 36, speedMax: 62, count: 1, fallback: "regal",
      habit: "cruise", traits: { shy: 0.1, territorial: 0.9, darty: 0.4 }, zone: [0.2, 0.8], zRange: [1.0, 1.8], cruiseBL: [0.5, 0.9], turnTime: 0.5,
    },
    {
      id: "orange_spot_surgeon",
      name: "Оранжевопятнистый хирург (Acanthurus olivaceus)",
      description: "Светло-серый с оранжевым «эполетом» за головой. Плавно скользит у дна.",
      image: "fish/orange_spot_surgeon.png",
      sizeMin: 110, sizeMax: 150, speedMin: 28, speedMax: 48, count: 1, fallback: "regal",
      habit: "graze", traits: { shy: 0.2, territorial: 0.3, darty: 0.2 }, zone: [0.3, 0.9], zRange: [1.0, 1.7], cruiseBL: [0.5, 0.95], turnTime: 0.5,
    },
    {
      id: "coral_grouper",
      name: "Коралловый групер (Cephalopholis miniata)",
      description: "Оранжево-красный в голубых точках. Неторопливо патрулирует риф у самого дна.",
      image: "fish/coral_grouper.png",
      sizeMin: 120, sizeMax: 165, speedMin: 18, speedMax: 34, count: 1, fallback: "coralfish",
      habit: "lurk", traits: { shy: 0.4, territorial: 0.6, darty: 0.1 }, zone: [0.6, 0.95], zRange: [1.05, 1.5], cruiseBL: [0.3, 0.55], turnTime: 0.8,
    },
    {
      id: "goldfish",
      name: "Золотая рыбка-оранда (Carassius auratus)",
      description: "Оранжево-белая оранда с «шапочкой» на голове и длинными вуалевыми плавниками. Плывёт спокойно и величаво в средней воде, вуаль хвоста и плавников мягко струится за ней.",
      image: "fish/goldfish.png",
      sizeMin: 115, sizeMax: 150, speedMin: 18, speedMax: 32, count: 1, fallback: "coralfish",
      habit: "cruise", traits: { shy: 0.15, territorial: 0.0, darty: 0.0 }, zone: [0.25, 0.65], zRange: [1.05, 2.2], cruiseBL: [0.3, 0.55], turnTime: 0.8,
      veil: { tail: 0.45, lag: 1.8, beat: 0.6 },
    },
    {
      id: "butterflyfish",
      name: "Рыба-бабочка (Chaetodon)",
      description: "Золотистая с тонкими косыми линиями и чёрной полосой через глаз. Порхает над кораллами.",
      image: "fish/butterflyfish.png",
      sizeMin: 90, sizeMax: 120, speedMin: 28, speedMax: 48, count: 1, fallback: "coralfish",
      habit: "pick", traits: { shy: 0.3, territorial: 0.2, darty: 0.2 }, zone: [0.3, 0.9], zRange: [1.0, 2.1], cruiseBL: [0.4, 0.75], turnTime: 0.45,
    },
  ],
};
