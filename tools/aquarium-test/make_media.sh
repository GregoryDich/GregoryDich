#!/usr/bin/env bash
# make_media.sh — живой задник аквариума из стокового видео рифа (Adobe Stock 188049047,
# бесплатная коллекция, лицензировано под аккаунтом владельца).
#
# Делает бесшовную петлю (кроссфейд хвоста в начало), два грейда — ДЕНЬ «Мальдивы» и
# НОЧЬ «королевский синий LED» — и раскладывает результат:
#   aquarium/assets/reef_day.mp4, reef_night.mp4   H.264 High, yuv420p, 2560x1440, 29.97 fps,
#                                                  +faststart, без звука, BT.709 (тег), <= 25 МБ
#   aquarium/assets/reef_day.jpg, reef_night.jpg   постеры = точный первый кадр петли (q88)
#   tools/aquarium-test/media/reef_day.webm, ...    VP9 1920x1080, те же кадры — для headless-тестов (Chromium без
#                                                  H.264); media/ в .gitignore, НЕ в бандле .app
#   tools/aquarium-test/media/reef_day.cube, ...    сгенерированные 3D LUT (reef_grade.py)
#
# Всё детерминировано: окно петли — константы ниже, грейд — reef_grade.py (python3.13 + numpy).
#
# Запуск:
#   tools/aquarium-test/make_media.sh SRC.mov [--theme day|night|both] [--no-mp4] [--no-webm]
#                                     [--stills DIR]   # только контрольные кадры PNG, без кодирования
#                                     [--keep-master] [--reuse-master]   # FFV1-мастер петли в media/
#   (или REEF_SRC=SRC.mov tools/aquarium-test/make_media.sh)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
ASSETS="$ROOT/aquarium/assets"
MEDIA="$HERE/media"
PY="${PYTHON:-python3.13}"

SRC="${REEF_SRC:-}"
THEMES="day night"
DO_MP4=1
DO_WEBM=1
STILLS=""
KEEP_MASTER=0      # --keep-master: оставить media/.master_*.mkv (FFV1) для перекодирования
REUSE_MASTER=0     # --reuse-master: не пересобирать мастер, если он есть
while [ $# -gt 0 ]; do
  case "$1" in
    --theme) shift; [ "$1" = both ] && THEMES="day night" || THEMES="$1" ;;
    --no-mp4) DO_MP4=0 ;;
    --no-webm) DO_WEBM=0 ;;
    --stills) shift; STILLS="$1" ;;
    --keep-master) KEEP_MASTER=1 ;;
    --reuse-master) REUSE_MASTER=1; KEEP_MASTER=1 ;;
    -h|--help) sed -n 2,22p "$0"; exit 0 ;;
    *) SRC="$1" ;;
  esac
  shift
done
if [ -z "$SRC" ] || [ ! -f "$SRC" ]; then
  echo "make_media.sh: нужен исходник 188049047.mov (аргумент или REEF_SRC)" >&2
  exit 1
fi

# ---------- окно петли (кадры исходника, 30000/1001 fps, нумерация от 0) ----------
# Выбрано по минимуму расхождения «голова/хвост» на всём кроссфейде (нет крупных рыб в каньоне,
# лучи и каустика в близкой фазе): S=138 (4.60 с), длина L=600 (20.02 с), кроссфейд F=40 (1.33 с).
# Выход: out[k] = смесь(src[S+L+k], src[S+k]) при k<F (smoothstep), иначе src[S+k].
# Поэтому out[L-1]=src[S+L-1] -> out[0]=src[S+L]: шов петли — обычная пара соседних кадров.
S=138
L=600
F=40
W=2560
H=1440
WEBM_W=1920
WEBM_H=1080
MP4_RATE=9400k   # 9.4 Мбит/с * 20.02 с = 23.5 МБ (+ контейнер) — с запасом до 25 МБ
MAXRATE=14M      # VBV: пики (I-кадры) без «ступенек» качества
BUFSIZE=28M

t_of() { "$PY" -I -c "print('%.6f' % (($1 - 0.5) * 1001 / 30000))"; }   # точный seek на кадр
T_TAIL="$(t_of $((S + L)))"
T_HEAD="$(t_of $S)"
XDUR="$("$PY" -I -c "print('%.6f' % (($F - 0.25) * 1001 / 30000))")"

mkdir -p "$MEDIA"
PREMIX="$("$PY" -I "$HERE/reef_grade.py" premix)"

# Общая подготовка каждого входа: хрома исходника блочная (H.264 4:2:0 на плоской воде) —
# мягкий билатеральный фильтр только по U/V; затем 4K -> 2560x1440 в 16 бит.
PREP="bilateral=sigmaS=8:sigmaR=0.06:planes=6,zscale=w=$W:h=$H:f=spline36,format=yuv444p16le"
# V5: радужная кайма (пурпур/циан/жёлтый) по вертикальным кромкам кораллов у краёв кадра — тонкий «звон» хромы
# самого исходника (не сдвиг каналов: R/B к G совпадают ≤ 1 px), ночной LUT её усиливает. Только хрома (U/V),
# только по краям кадра: справа (bx > 0.6, жёлтые ветвистые и розовые трубчатые) gblur σ 5, слева (bx < 0.3) σ 3.
# Ночная кайма справа 0.54% → 0.005% пикселей; яркость и резкость не трогаются (глаз к хроме в 4–5 раз менее зорок).
CFX_R=$((W * 6 / 10)); CFX_L=$((W * 3 / 10))
prep() {   # $1 — суффикс меток (граф использует подготовку дважды: хвост и голова петли)
  echo "$PREP,split=3[po$1][pr$1][pl$1];[pr$1]crop=w=$((W - CFX_R)):h=$H:x=$CFX_R:y=0,gblur=sigma=5:planes=6[cr$1];[pl$1]crop=w=$CFX_L:h=$H:x=0:y=0,gblur=sigma=3:planes=6[cl$1];[po$1][cr$1]overlay=x=$CFX_R:y=0:format=yuv444[pq$1];[pq$1][cl$1]overlay=x=0:y=0:format=yuv444,format=yuv444p16le"
}
# smoothstep-кроссфейд: P идёт 1 -> 0 (A = хвост, B = голова)
XF="xfade=transition=custom:duration=$XDUR:offset=0:expr='A*(P*P*(3-2*P))+B*(1-P*P*(3-2*P))'"
# BT.709 limited -> float RGB -> сжатие гаммы -> LUT -> BT.709 limited 4:2:0 с диффузией ошибки
grade_chain() {
  echo "zscale=min=709:rin=limited:m=709:r=full,format=gbrpf32le,colorchannelmixer=$PREMIX,lut3d=file='$MEDIA/reef_$1.cube':interp=tetrahedral,zscale=m=709:r=limited:dither=error_diffusion,format=yuv420p"
}

for TH in $THEMES; do
  echo "== $TH: LUT" >&2
  "$PY" -I "$HERE/reef_grade.py" cube "$TH" "$MEDIA/reef_$TH.cube" 65
  GRAPH="[0:v]trim=end_frame=$F,setpts=PTS-STARTPTS,$(prep A)[a];[1:v]trim=end_frame=$L,setpts=PTS-STARTPTS,$(prep B)[b];[a][b]$XF,$(grade_chain "$TH")"

  if [ -n "$STILLS" ]; then
    mkdir -p "$STILLS"
    # контрольные кадры петли: 0 (первый), F/2 (середина кроссфейда), F, L/2, L-1 (последний)
    ffmpeg -v error -y -ss "$T_TAIL" -i "$SRC" -ss "$T_HEAD" -i "$SRC" \
      -filter_complex "$GRAPH,select='eq(n\,0)+eq(n\,$((F / 2)))+eq(n\,$F)+eq(n\,$((L / 2)))+eq(n\,$((L - 1)))',zscale=min=709:rin=limited:m=709:r=full,format=rgb24" \
      -fps_mode passthrough -frames:v 5 "$STILLS/${TH}_%d.png"
    continue
  fi

  # 1) мастер: готовые кадры петли (8 бит 4:2:0 — ровно то, что получат кодеры), FFV1 без потерь
  MASTER="$MEDIA/.master_$TH.mkv"
  if [ "$REUSE_MASTER" = 1 ] && [ -f "$MASTER" ]; then
    echo "== $TH: мастер уже есть ($MASTER)" >&2
  else
    echo "== $TH: мастер (петля + грейд)" >&2
    ffmpeg -v error -stats -y -ss "$T_TAIL" -i "$SRC" -ss "$T_HEAD" -i "$SRC" \
      -filter_complex "$GRAPH" -an -c:v ffv1 -level 3 -slices 16 -threads 4 -g 1 \
      -r 30000/1001 -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
      "$MASTER"
  fi
  NF=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 "$MASTER")
  [ "$NF" = "$L" ] || { echo "make_media.sh: в мастере $NF кадров, ожидалось $L" >&2; exit 1; }

  if [ $DO_MP4 = 1 ]; then
    # двухпроходный ABR: предсказуемый размер (<= 25 МБ) при лучшем распределении битов;
    # x264 детерминирован при тех же входе и настройках.
    # V5: закрытая GOP 2 с (keyint 60): смена темы перематывает новое видео к времени старого (alignVideo) —
    # при одной GOP на петлю точная перемотка декодировала до 599 кадров 1440p (≈1–2 с), теперь ≤ 59.
    # «Пульс» текстуры на I-кадрах (почему раньше была одна GOP) гасится ipratio 1.15 (I-кадр не резче P);
    # последние 50 кадров (zones b=1.6) по-прежнему подтянуты к I-кадру 0 — шов петли не «дышит».
    echo "== $TH: H.264 ($MP4_RATE, 2 прохода)" >&2
    for PASS in 1 2; do
      if [ $PASS = 1 ]; then DST=(-f mp4 /dev/null); else DST=(-movflags +faststart -tag:v avc1 "$ASSETS/reef_$TH.mp4"); fi
      ffmpeg -v error -stats -y -i "$MASTER" -an -c:v libx264 -preset slow -tune film \
        -b:v "$MP4_RATE" -maxrate "$MAXRATE" -bufsize "$BUFSIZE" -pass $PASS -passlogfile "$MEDIA/.x264_$TH" \
        -profile:v high -level:v 5.1 -x264-params "aq-mode=3:keyint=60:min-keyint=60:scenecut=0:open-gop=0:ipratio=1.15:zones=$((L - 50)),$((L - 1)),b=1.6" \
        -pix_fmt yuv420p -r 30000/1001 -fps_mode cfr \
        -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
        -map_metadata -1 "${DST[@]}"
    done
    rm -f "$MEDIA/.x264_$TH"*
  fi
  if [ $DO_WEBM = 1 ]; then
    # VP9-копия только для headless-тестов: тот же кадр за кадром, 1920x1080, быстрые настройки
    echo "== $TH: VP9 (тесты)" >&2
    ffmpeg -v error -stats -y -i "$MASTER" -an \
      -vf "zscale=w=$WEBM_W:h=$WEBM_H:f=spline36" -c:v libvpx-vp9 -b:v 0 -crf 34 \
      -deadline good -cpu-used 5 -row-mt 1 -threads 4 -tile-columns 2 -g 150 -pix_fmt yuv420p \
      -r 30000/1001 -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
      -map_metadata -1 "$MEDIA/reef_$TH.webm"
  fi
  [ "$KEEP_MASTER" = 1 ] || rm -f "$MASTER"

  if [ $DO_MP4 = 1 ]; then
    # постер = точный первый кадр петли, декодированный так же, как его покажет WebKit (BT.709 tv)
    TMP="$MEDIA/.poster_$TH.png"
    ffmpeg -v error -y -i "$ASSETS/reef_$TH.mp4" -frames:v 1 \
      -vf "zscale=min=709:rin=limited:m=709:r=full,format=rgb24" "$TMP"
    "$PY" -I -c "
import sys
from PIL import Image
Image.open(sys.argv[1]).convert('RGB').save(sys.argv[2], 'JPEG', quality=88, subsampling=0, optimize=True, progressive=True)
" "$TMP" "$ASSETS/reef_$TH.jpg"
    rm -f "$TMP"
    ls -l "$ASSETS/reef_$TH.mp4" "$ASSETS/reef_$TH.jpg" >&2
  fi
done
