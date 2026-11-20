#!/bin/bash
# check-clip.sh <clip.mp4> <start still.png> <end still.png> [out dir]
# Prints frame count and size; writes a 4x3 contact sheet, the first and last frames, and side-by-side
# comparisons of the first frame with the start still and of the last frame with the end still (plus RMSE).
set -euo pipefail
C=$1; A=$2; B=$3; O=${4:-$(dirname "$C")}; N=$(basename "$C" .mp4)
IFS=x read W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$C")
F=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$C")
echo "$N: ${W}x${H}, frames=$F, size=$(stat -c %s "$C")"
L=$((F-1))
ffmpeg -v error -y -i "$C" -vf "select='eq(n,0)'" -vframes 1 "$O/$N-f000.png"
ffmpeg -v error -y -i "$C" -vf "select='eq(n,$L)'" -vsync 0 -vframes 1 "$O/$N-flast.png"
if [ "$W" -gt "$H" ]; then TW=480; else TW=270; fi
ffmpeg -v error -y -i "$C" -vf "select='not(mod(n,11))',scale=$TW:-1,tile=4x3" -vsync 0 -frames:v 1 -q:v 3 "$O/$N-sheet.jpg"
for pair in "f000:$A:start" "flast:$B:end"; do
  IFS=: read f still tag <<<"$pair"
  convert "$still" -resize "${W}x${H}^" -gravity center -extent "${W}x${H}" "$O/$N-$tag-still.png"
  printf '%s vs %s still: RMSE ' "$f" "$tag"; compare -metric RMSE "$O/$N-$f.png" "$O/$N-$tag-still.png" null: 2>&1 || true; echo
  convert "$O/$N-$f.png" "$O/$N-$tag-still.png" +append -resize 1600x -quality 88 "$O/$N-$tag-pair.jpg"
done
# largest frame-to-frame changes: a hidden cut shows as one frame with a score several times the rest
echo "largest scene scores (frame:score):" $(ffmpeg -v error -i "$C" -vf "select='gte(scene,0)',metadata=print:file=-" -an -f null - 2>/dev/null | awk -F'[:= ]+' '/frame:/{f=$2} /scene_score/{print $NF, f}' | sort -rn | head -5 | awk '{printf "%s:%s  ", $2, $1}')
