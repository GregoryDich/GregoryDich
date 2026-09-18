Фон аквариума.

reef_bg.jpg — задник (вода, дальний риф, песок), reef_fg.png — прозрачный
передний план (ближние кораллы). Оба рендерятся Blender'ом скриптом
../blender/reef.py:  python3 reef.py --out ../assets

Хотите свой фон — положите сюда background.jpg (или .png): он имеет приоритет
над reef_bg.jpg. Передний план reef_fg.png при этом можно удалить.
Порядок поиска задника: reef_bg.jpg, background.jpg/png, reef.jpg/png, marine.jpg.
