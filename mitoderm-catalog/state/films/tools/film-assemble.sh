#!/bin/bash
# film-assemble.sh <spec file> <clips dir> <output.mp4> <width> <height>
# Builds a scroll film from pieces of clips. Each spec line is one piece, in film order:
#   clip <file> <from> <to> [step] [rev]   frames from..to (inclusive) of <file>; step N keeps every Nth frame
#                                          (2 = twice as fast); rev plays the piece backwards
#   hold <file> <frame> <count>            one frame of <file> held for <count> frames
# Lines starting with # and empty lines are ignored. Output: 24 fps, a keyframe every 12 frames.
set -euo pipefail
SPEC=${1:?spec}; C=${2:?clips dir}; O=${3:?output}; W=${4:?width}; H=${5:?height}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
N="scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1,format=yuv420p"
ENC="-an -c:v libx264 -preset medium -crf 8 -pix_fmt yuv420p -r 24"
i=0; total=0; : > "$T/list.txt"
while read -r kind f a b c d; do
  case "$kind" in ''|'#'*) continue;; esac
  i=$((i+1)); P=$(printf '%s/p%03d.mp4' "$T" "$i")
  if [ "$kind" = hold ]; then
    ffmpeg -nostdin -v error -y -i "$C/$f" -vf "select='eq(n,$a)',${N},loop=loop=$((b-1)):size=1:start=0,setpts=N/24/TB" -frames:v "$b" $ENC "$P"
    n=$b
  else
    step=${c:-1}; rev=${d:-}; [ "$step" = rev ] && { step=1; rev=rev; }
    R=""; [ "$rev" = rev ] && R="reverse,"
    ffmpeg -nostdin -v error -y -i "$C/$f" -vf "select='between(n,$a,$b)*not(mod(n-$a,$step))',setpts=N/24/TB,${R}${N},setpts=N/24/TB" $ENC "$P"
    n=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$P" < /dev/null)
  fi
  printf '%4d..%-4d  %-5s %-12s %s %s %s %s  (%d frames)\n' "$total" "$((total+n-1))" "$kind" "$f" "$a" "$b" "${c:-}" "${d:-}" "$n"
  total=$((total+n)); echo "file '$P'" >> "$T/list.txt"
done < "$SPEC"
ffmpeg -nostdin -v error -y -f concat -safe 0 -i "$T/list.txt" -vf "setpts=N/24/TB" -an -c:v libx264 -preset slower -tune film -profile:v high -pix_fmt yuv420p -crf 22 -r 24 \
  -g 12 -keyint_min 12 -sc_threshold 0 -movflags +faststart "$O"
echo "frames=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$O") (planned $total) size=$(stat -c %s "$O")"
