# Обучение RF-DETR-Seg на класс FOOT

RF-DETR-Seg из коробки знает только COCO (класса «foot» там нет), поэтому модель
дообучается на датасете сегментации стоп с Roboflow Universe. Это единственная
нейросеть в проекте.

Скрипт `train_foot_rfdetr.py` лежит **в ветке `claude/foot-measurement-mvp-i7rynx`**
(в `main` его нет, пока ветка не смержена):
https://github.com/GregoryDich/GregoryDich/blob/claude/foot-measurement-mvp-i7rynx/foot-measurement/python/training/train_foot_rfdetr.py

## Что нужно

* GPU с CUDA — достаточно бесплатного Google Colab (T4), ~1 час на 50 эпох
  для `small`. На CPU/Apple MPS обучение непрактично.
* Бесплатный аккаунт Roboflow → API key (`https://app.roboflow.com` → Settings → API).
* Датасет (instance segmentation, класс `foot`), например:
  * `https://universe.roboflow.com/allard/foot-segmentation-ehn9q` (~2k изображений)
  * `https://universe.roboflow.com/ubeyd-cukur/feet-h43sa` (~150 изображений)

  На странице датасета посмотрите номер последней версии и подставьте её в URL
  (`.../foot-segmentation-ehn9q/<version>`). Экспорт-формат — `coco`
  (COCO JSON с polygon-сегментацией; RF-DETR определяет формат автоматически).

## Colab — по шагам

1. https://colab.research.google.com → New notebook → Runtime → Change runtime type → **T4 GPU**.
2. Получить скрипт в Colab любым из способов:

   ```python
   # (a) raw-URL из ветки
   !wget -q https://raw.githubusercontent.com/GregoryDich/GregoryDich/claude/foot-measurement-mvp-i7rynx/foot-measurement/python/training/train_foot_rfdetr.py
   # (b) или клонировать ветку
   !git clone -b claude/foot-measurement-mvp-i7rynx --depth 1 https://github.com/GregoryDich/GregoryDich.git
   %cd GregoryDich/foot-measurement/python/training
   ```

   (c) или загрузить файл вручную: панель **Files** слева → Upload → `train_foot_rfdetr.py`.
3. Установить зависимости, задать ключ, запустить:

   ```python
   !pip install -q rfdetr roboflow
   import os; os.environ["ROBOFLOW_API_KEY"] = "..."
   !python train_foot_rfdetr.py --dataset-url https://universe.roboflow.com/allard/foot-segmentation-ehn9q/1 \
       --size small --epochs 50 --batch-size 4 --grad-accum-steps 4 --output /content/output
   ```

   Первые строки вывода: `classes: {0: 'feet', 1: 'foot'}` (имена из датасета) и
   параметры обучения; дальше — прогресс по эпохам (~1 мин/эпоха на T4).
4. Проверить результат: в `/content/output/` есть `checkpoint_best_total.pth` и
   `classes.json`. Скачать оба (панель Files → правый клик → Download) и положить в
   `foot-measurement/python/weights/`.
5. Проверить на реальной записи с iPhone:

   ```bash
   footmeasure detect sessions/<session> --weights weights/checkpoint_best_total.pth --step 15 --rotate
   ```

   Ожидаемо: `frame N: foot conf=0.8x area=...px two_pass=True` и `out/<session>/detect_*.png`
   с зелёной маской по стопе.

## Замечания

* `batch_size × grad_accum_steps ≈ 16`. На T4: `4 × 4`; на A100: `16 × 1`.
* `--size medium` точнее по границе, но медленнее на CPU Mac при инференсе
  (RF-DETR делает два прохода на кадр: полный кадр + кроп).
* Датасеты Universe — босые стопы, вид сверху/сбоку; снимайте в тех же условиях.
* Если в датасете класс называется иначе (см. `classes.json`), передайте
  `--class-name <имя>` в `footmeasure`.
* Если Colab отключился до конца обучения — запустить с `--epochs` поменьше или
  использовать промежуточный `checkpoint.pth` из `output/`.
