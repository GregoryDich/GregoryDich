#!/bin/bash
# still-zoom.sh <still.png> <out.mp4> <count> <z0> <z1> <cx> <cy> [width height]
# A free camera move on one still: the picture is enlarged from z0 to z1 times over <count> frames, eased at both
# ends, around the point (cx, cy) - fractions of the frame, 0..1 - that keeps its place (0.5 0.5 = the centre).
# z0 > z1 is a pull-back. The result is a short clip (24 fps) for film-assemble.sh: use it with "clip" and "blur".
# It gives a frame camera life where a paid clip is not shot yet; the people in it do not move.
# Default size 1912x1080. A still of 2688x1520 stays sharp up to about 1.4x.
set -euo pipefail
IN=${1:?still}; OUT=${2:?out}; N=${3:?count}; Z0=${4:?z0}; Z1=${5:?z1}; CX=${6:?cx}; CY=${7:?cy}; W=${8:-1912}; H=${9:-1080}
T="clip(n/($N-1),0,1)"
Z="($Z0*pow($Z1/$Z0,$T*$T*(3-2*$T)))"
ffmpeg -nostdin -v error -y -loop 1 -framerate 24 -i "$IN" -f lavfi -i "color=c=black:s=${W}x${H}:r=24" -filter_complex \
  "[0:v]scale=w='2*ceil($W*$Z/2)':h='2*ceil($W*$Z*ih/iw/2)':eval=frame:flags=lanczos[s];[1:v][s]overlay=x='-(w-$W)*$CX':y='-(h-$H)*$CY':eval=frame,format=yuv420p[v]" \
  -map "[v]" -frames:v "$N" -an -c:v libx264 -preset medium -crf 8 -pix_fmt yuv420p -r 24 "$OUT"
echo "$(basename "$OUT"): $(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$OUT") frames, zoom $Z0 -> $Z1 around $CX,$CY"
