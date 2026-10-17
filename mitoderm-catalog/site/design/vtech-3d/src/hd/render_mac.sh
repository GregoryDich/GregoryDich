#!/bin/bash
# V-TECH HD frames on the owner's Apple Silicon Mac: Cycles on the Metal GPU (an M4 is ~7-9x the 4-core cloud container).
# Installs nothing: Blender 4.2.0 (the cloud's version) runs from its mounted disk image, which is deleted at the end.
# Needs ~1 GB free while it runs; leaves only ~/Desktop/vtech-render.zip (~20 MB: 200 frames) to attach to the chat.
# Resumable: run it again after an interruption, finished frames are kept.
# Run in Terminal:
#   curl -fsSL https://raw.githubusercontent.com/GregoryDich/GregoryDich/claude/mitoderm-figma-catalog-74tbuw/mitoderm-catalog/site/design/vtech-3d/src/hd/render_mac.sh -o ~/render_mac.sh && bash ~/render_mac.sh
set -euo pipefail
BR=claude/mitoderm-figma-catalog-74tbuw
RAW=https://raw.githubusercontent.com/GregoryDich/GregoryDich/$BR/mitoderm-catalog/site/design/vtech-3d/src/hd
REL=https://download.blender.org/release/Blender4.2; DMG=blender-4.2.0-macos-arm64.dmg
W="$HOME/vtech-render"; mkdir -p "$W/tex" "$W/seq"; cd "$W"

[ "$(uname -m)" = arm64 ] || { echo "Нужен Mac на Apple Silicon (M1–M4)."; exit 1; }
free=$(df -g "$HOME" | awk 'NR == 2 { print $4 }')
[ "$free" -ge 1 ] || { echo "Нужен хотя бы 1 ГБ свободного места, сейчас ${free} ГБ."; exit 1; }

echo "1/3 Скачиваю Blender 4.2 (~350 МБ, без установки)…"
if [ ! -f "$DMG" ]; then
  curl -fL --progress-bar -o "$DMG.part" "$REL/$DMG" || { echo "Не удалось скачать Blender — проверьте интернет и запустите ещё раз."; exit 1; }
  mv -f "$DMG.part" "$DMG"
fi
sum=$(curl -fsSL "$REL/blender-4.2.0.sha256" 2>/dev/null | grep " $DMG\$" || true)   # the official checksum list
if [ -n "$sum" ]; then ok() { echo "$sum" | shasum -a 256 -c - >/dev/null; }; else ok() { hdiutil verify -quiet "$DMG"; }; fi
ok || { echo "Файл Blender повреждён — удаляю, запустите скрипт ещё раз."; rm -f "$DMG"; exit 1; }
mkdir -p mnt; hdiutil attach -quiet -nobrowse -readonly -mountpoint "$W/mnt" "$DMG"
trap 'hdiutil detach -quiet "$W/mnt" 2>/dev/null || true' EXIT
B="$W/mnt/Blender.app/Contents/MacOS/Blender"

echo "2/3 Скачиваю сцену и текстуры печати…"
curl -fsSL -o vtech_scene.py "$RAW/vtech_scene.py"
for t in box-front-albedo box-front-metal box-front-rough box-side-albedo box-side-metal box-side-rough label sachet-albedo sachet-metal sachet-rough sleeve-window lid-albedo lid-rough lid-metal; do
  curl -fsSL -o "tex/$t.png" "$RAW/tex/$t.png"
done

export VT_DEVICE=METAL
render() {   # <out.webp> <shot> <width> <samples> [part]; a finished file is kept
  [ -s "$1" ] && return 0
  caffeinate -i "$B" -b --factory-startup --python vtech_scene.py -- "$W/tex" "$@" > log.txt 2>&1 \
    || { echo "Ошибка рендера $1:"; tail -15 log.txt; exit 1; }
}

# the story of 17/10, S1→S6; each run renders only the region its 3D crosses (boxes from the 480 px draft, ingest_seq.py
# --boxes: x0,y0,x1,y1 of the frame, y from the top), about a third of the frame, so the M4 spends its time on the 3D only
RUNS="v1-meet:v2-why:0.185,0.207,0.476,0.823 v2-why:v3-inside:0.037,0.073,0.424,0.867 v3-inside:v4-feel:0.012,0.070,0.513,0.847
v4-feel:v5-protocol:0.000,0.073,0.513,0.770 v5-protocol:v6-kit:0.000,0.000,0.532,0.843"
echo "3/3 Переходы для живой страницы: 5 × 40 кадров (первый кадр дольше: видеокарта готовит шейдеры)…"
export VT_WEBP_Q=90
n=0
for run in $RUNS; do
  a=${run%%:*}; rest=${run#*:}; b=${rest%%:*}; box=${rest#*:}; n=$((n + 1))
  for i in $(seq 0 39); do
    t=$(awk -v i="$i" 'BEGIN { printf "%.4f", i / 39 }')
    VT_BORDER="$box" render "$W/seq/${a}_${b}_$(printf %03d "$i").webp" "$a>$b@$t" 2400 128
    printf "\r   переход %d/5, кадр %d/40" "$n" "$((i + 1))"
  done
  echo
done
echo "$RUNS" > "$W/seq/boxes.txt"   # the cloud's ingest_seq.py takes the crops as given (VT_CROPPED)

hdiutil detach -quiet "$W/mnt"; trap - EXIT; rm -f "$DMG"
cd "$HOME"; rm -f "$HOME/Desktop/vtech-render.zip"
zip -qr "$HOME/Desktop/vtech-render.zip" vtech-render/seq && rm -rf "$W"
echo "Готово: на рабочем столе vtech-render.zip — прикрепите его в чат."
