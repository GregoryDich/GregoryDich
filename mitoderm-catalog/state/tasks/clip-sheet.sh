#!/bin/bash
# Review sheet for a generated clip: downloads it (or takes a local file) and lays out every Nth frame in one
# picture, so faces, hands and the pack print can be checked across the whole take.
# Usage: clip-sheet.sh <url or file> <out dir> <name> [step=15] [columns=3] [tile width=640]
# Writes <out dir>/<name>.mp4 (when a URL is given) and <out dir>/<name>-sheet.jpg; prints size, fps and frames.
set -euo pipefail
SRC=${1:?url or file}; OUT=${2:?out dir}; NAME=${3:?name}; STEP=${4:-15}; COLS=${5:-3}; TW=${6:-640}
mkdir -p "$OUT"
if [[ "$SRC" == http* ]]; then
  curl -sS --retry 3 --max-time 300 -o "$OUT/$NAME.mp4" "$SRC"
  SRC="$OUT/$NAME.mp4"
fi
read -r W H FPS FRAMES < <(ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=width,height,r_frame_rate,nb_read_frames -of csv=p=0 "$SRC" | tr ',' ' ')
N=$(( (FRAMES + STEP - 1) / STEP )); ROWS=$(( (N + COLS - 1) / COLS ))
ffmpeg -v error -y -i "$SRC" -vf "select='not(mod(n\,$STEP))',scale=$TW:-2,tile=${COLS}x${ROWS}:padding=6:color=gray" \
  -frames:v 1 -q:v 3 "$OUT/$NAME-sheet.jpg"
echo "$NAME: ${W}x${H} fps=$FPS frames=$FRAMES sheet=$OUT/$NAME-sheet.jpg (every ${STEP}th frame, ${COLS}x${ROWS})"
