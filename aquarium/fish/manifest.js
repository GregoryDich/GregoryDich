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
   ============================================================ */
window.FISH_MANIFEST = {
  facing: "right",
  fish: [
    {
      id: "clownfish",
      name: "Рыба-клоун (Amphiprion ocellaris)",
      description: "Оранжевая с тремя белыми полосами в чёрной окантовке. Живёт в актинии, плавает короткими рывками. Та самая «Немо».",
      image: "fish/clownfish.png",
      sizeMin: 80, sizeMax: 120, speedMin: 30, speedMax: 55, count: 3, fallback: "clown",
    },
    {
      id: "blue_tang",
      name: "Голубой хирург (Paracanthurus hepatus)",
      description: "Ярко-синее тело с чёрным «палитра»-узором и жёлтым хвостом. «Дори». Плавно скользит в толще воды.",
      image: "fish/blue_tang.png",
      sizeMin: 90, sizeMax: 130, speedMin: 34, speedMax: 60, count: 2, fallback: "regal",
    },
    {
      id: "yellow_tang",
      name: "Жёлтый хирург (Zebrasoma flavescens)",
      description: "Насыщенно-жёлтый, дисковидный, с острым рыльцем. Днём ярко-жёлтый, ночью бледнеет.",
      image: "fish/yellow_tang.png",
      sizeMin: 70, sizeMax: 100, speedMin: 30, speedMax: 52, count: 2, fallback: "yellowtang",
    },
    {
      id: "powder_blue_tang",
      name: "Белогрудый хирург (Acanthurus leucosternon)",
      description: "Голубое тело, чёрная «маска» на голове, жёлтый спинной плавник и белая грудь. Очень контрастный.",
      image: "fish/powder_blue_tang.png",
      sizeMin: 85, sizeMax: 120, speedMin: 32, speedMax: 56, count: 1, fallback: "regal",
    },
    {
      id: "pufferfish",
      name: "Рыба-ёж / иглобрюх (Arothron)",
      description: "Кремово-белая, округлая, покрыта тёмными пятнышками. Плывёт медленно, забавно работая плавниками.",
      image: "fish/pufferfish.png",
      sizeMin: 95, sizeMax: 140, speedMin: 18, speedMax: 34, count: 1, fallback: "puffer",
    },
    {
      id: "royal_gramma",
      name: "Королевская грамма (Gramma loreto)",
      description: "Маленькая: передняя половина фиолетовая, задняя — ярко-жёлтая, резкий переход посередине.",
      image: "fish/royal_gramma.png",
      sizeMin: 55, sizeMax: 80, speedMin: 30, speedMax: 50, count: 2, fallback: "damsel",
    },
    {
      id: "emperor_angelfish",
      name: "Императорский ангел (Pomacanthus imperator)",
      description: "Сине-жёлтые горизонтальные полосы, чёрная «маска» с синей окантовкой. Крупный и величавый.",
      image: "fish/emperor_angelfish.png",
      sizeMin: 100, sizeMax: 150, speedMin: 28, speedMax: 48, count: 1, fallback: "coralfish",
    },
    {
      id: "regal_angelfish",
      name: "Жемчужный ангел (Pygoplites diacanthus)",
      description: "Вертикальные оранжево-белые полосы в синей окантовке, синяя «грудь». Очень нарядный.",
      image: "fish/regal_angelfish.png",
      sizeMin: 80, sizeMax: 115, speedMin: 30, speedMax: 50, count: 1, fallback: "yellowtang",
    },
    {
      id: "mandarinfish",
      name: "Мандаринка (Synchiropus splendidus)",
      description: "Психоделические зелёно-оранжево-синие волнистые узоры. Маленькая, перемещается короткими зависаниями.",
      image: "fish/mandarinfish.png",
      sizeMin: 55, sizeMax: 80, speedMin: 22, speedMax: 40, count: 1, fallback: "damsel",
    },
    {
      id: "blue_chromis",
      name: "Голубой хромис (Chromis viridis)",
      description: "Мелкая мерцающая сине-зелёная рыбка. Держится стайкой — фон и «жизнь» сцены.",
      image: "fish/blue_chromis.png",
      sizeMin: 36, sizeMax: 56, speedMin: 34, speedMax: 58, count: 6, fallback: "chromis",
    },
    {
      id: "flame_angel",
      name: "Огненный ангел (Centropyge loricula)",
      description: "Ярко-красно-оранжевый с тёмными вертикальными штрихами и сине-чёрной каймой плавников.",
      image: "fish/flame_angel.png",
      sizeMin: 60, sizeMax: 90, speedMin: 30, speedMax: 52, count: 1, fallback: "coralfish",
    },
    {
      id: "moorish_idol",
      name: "Мавританский идол (Zanclus cornutus)",
      description: "Чёрно-бело-жёлтые широкие полосы и длинный нитевидный спинной плавник. «Жабр» из «Немо».",
      image: "fish/moorish_idol.png",
      sizeMin: 85, sizeMax: 120, speedMin: 30, speedMax: 50, count: 1, fallback: "damsel",
    },
  ],
};
