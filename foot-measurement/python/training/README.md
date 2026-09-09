# Обучение RF-DETR-Seg на класс FOOT

RF-DETR-Seg из коробки знает только COCO (класса «foot» там нет), поэтому модель
дообучается на датасете сегментации стоп с Roboflow Universe. Это единственная
нейросеть в проекте.

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

## Colab

```python
!pip install -q rfdetr roboflow
import os; os.environ["ROBOFLOW_API_KEY"] = "..."
!wget -q https://raw.githubusercontent.com/GregoryDich/GregoryDich/claude/foot-measurement-mvp-i7rynx/foot-measurement/python/training/train_foot_rfdetr.py
!python train_foot_rfdetr.py --dataset-url https://universe.roboflow.com/allard/foot-segmentation-ehn9q/1 \
    --size small --epochs 50 --batch-size 4 --grad-accum-steps 4 --output /content/output
```

Результат: `/content/output/checkpoint_best_total.pth` и `/content/output/classes.json`.
Скопируйте оба файла в `foot-measurement/python/weights/`.

Проверка на реальной записи:

```bash
footmeasure detect sessions/<session> --weights weights/checkpoint_best_total.pth --step 15 --rotate
```

## Замечания

* `batch_size × grad_accum_steps ≈ 16`. На T4: `4 × 4`; на A100: `16 × 1`.
* `--size medium` точнее по границе, но медленнее на CPU Mac при инференсе
  (RF-DETR делает два прохода на кадр: полный кадр + кроп).
* Датасеты Universe — босые стопы, вид сверху/сбоку; снимайте в тех же условиях.
* Если в датасете класс называется иначе (см. `classes.json`), передайте
  `--class-name <имя>` в `footmeasure`.
