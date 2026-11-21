#!/bin/bash
# film-assemble.sh <spec file> <clips dir> <output.mp4> <width> <height>
# Builds a scroll film from pieces of clips. Each spec line is one piece, in film order:
#   clip <file> <from> <to> [step] [rev]   frames from..to (inclusive) of <file>; step N keeps every Nth frame
#                                          (2 = twice as fast); rev plays the piece backwards
#   hold <file> <frame> <count>            one frame of <file> held for <count> frames
#   slow <file> <from> <to> <times>       frames from..to, each shown <times> times: a clip that ends while the camera
#                                          still moves is eased into the hold that follows it
#   fade <fileA> <frameA> <fileB> <frameB> <count>   a dissolve from one still frame to another over <count> frames
#                                          (free transition between two places when the pack is identical in both)
#   blur <fileA> <fromA> <toA> <fileB> <fromB> <toB> [overlap] [sigma]
#                                          a soft-focus join of two shots that do not meet (a clip with a hidden cut):
#                                          A goes out of focus, its last <overlap> frames dissolve into the first
#                                          <overlap> frames of B while both are fully blurred (no double image), then
#                                          B comes into focus. Length: framesA + framesB - overlap. Defaults: overlap
#                                          8 frames, sigma 26 px of the output frame. A range written backwards
#                                          (19 0) plays that shot backwards; a still picture is held for its range.
# A <file> may also be a still picture (PNG): it counts as a one-frame clip, frame 0.
# Lines starting with # and empty lines are ignored. Output: 24 fps, a keyframe every 12 frames.
set -euo pipefail
SPEC=${1:?spec}; C=${2:?clips dir}; O=${3:?output}; W=${4:?width}; H=${5:?height}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
N="scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1,format=yuv420p"
ENC="-an -c:v libx264 -preset medium -crf 8 -pix_fmt yuv420p -r 24"
soften() {   # <in.png> <sigma> <out.png>: a gaussian blur; a strong one is made on a smaller copy (same look, much faster)
  local f s
  read -r f s <<< "$(awk -v s="$2" 'BEGIN{f=(s>=12)?4:(s>=6)?2:1; printf "%d %.2f", f, s/f}')"
  if [ "$f" = 1 ]; then convert "$1" -blur "0x$s" "$3"
  else convert "$1" -resize "$((100/f))%" -blur "0x$s" -resize "${W}x${H}!" "$3"; fi
}
grab() {     # <file> <from> <to> <dir> <prefix>: the frames from..to as <dir>/<prefix>000.png ...; from > to = backwards;
  local lo hi n have k idx          # a still picture (one frame) is held for the whole range
  lo=$(( $2 < $3 ? $2 : $3 )); hi=$(( $2 < $3 ? $3 : $2 )); n=$((hi-lo+1))
  ffmpeg -nostdin -v error -y -i "$C/$1" -vf "select='between(n,$lo,$hi)',setpts=N/24/TB,scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1" -start_number 0 "$4/t%03d.png"
  have=$(find "$4" -name 't[0-9]*.png' | wc -l)
  for ((k=0; k<n; k++)); do
    idx=$(( $2 > $3 ? n-1-k : k )); idx=$(( idx < have ? idx : have-1 ))
    cp "$(printf '%s/t%03d.png' "$4" "$idx")" "$(printf '%s/%s%03d.png' "$4" "$5" "$k")"
  done
  find "$4" -name 't[0-9]*.png' -delete
}
i=0; total=0; : > "$T/list.txt"
while read -r kind f a b c d; do
  case "$kind" in ''|'#'*) continue;; esac
  i=$((i+1)); P=$(printf '%s/p%03d.mp4' "$T" "$i")
  if [ "$kind" = hold ]; then
    ffmpeg -nostdin -v error -y -i "$C/$f" -vf "select='eq(n,$a)',${N},loop=loop=$((b-1)):size=1:start=0,setpts=N/24/TB" -frames:v "$b" $ENC "$P"
    n=$b
  elif [ "$kind" = slow ]; then
    ffmpeg -nostdin -v error -y -i "$C/$f" -vf "select='between(n,$a,$b)',setpts=N/24/TB,${N},setpts=PTS*$c,fps=24" $ENC "$P"
    n=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$P" < /dev/null)
  elif [ "$kind" = fade ]; then
    # f=fileA a=frameA b=fileB c=frameB d=count; smooth (eased) blend of the two frames
    ffmpeg -nostdin -v error -y -i "$C/$f" -i "$C/$b" -filter_complex \
      "[0:v]select='eq(n,$a)',${N},loop=loop=$((d-1)):size=1:start=0,setpts=N/24/TB[x];[1:v]select='eq(n,$c)',${N},loop=loop=$((d-1)):size=1:start=0,setpts=N/24/TB[y];[x][y]blend=all_expr='A+(B-A)*(3*pow(N/$((d-1)),2)-2*pow(N/$((d-1)),3))',format=yuv420p" \
      -frames:v "$d" $ENC "$P"
    n=$d
  elif [ "$kind" = blur ]; then
    # f=fileA a=fromA b=toA c=fileB d="fromB toB [overlap] [sigma]"
    read -r fb tb ov sg <<< "$d"; ov=${ov:-8}; sg=${sg:-26}
    D="$T/blur$i"; mkdir -p "$D"
    grab "$f" "$a" "$b" "$D" a; grab "$c" "$fb" "$tb" "$D" b
    na=$(( a < b ? b-a+1 : a-b+1 )); nb=$(( fb < tb ? tb-fb+1 : fb-tb+1 )); n=$((na+nb-ov))
    for ((k=0; k<n; k++)); do
      if ((k < na-ov)); then          # A goes out of focus
        s=$(awk -v k="$k" -v m="$((na-ov))" -v g="$sg" 'BEGIN{t=(k+1)/(m+1); printf "%.2f", g*t*t*(3-2*t)}')
        src=$(printf '%s/a%03d.png' "$D" "$k")
      elif ((k < na)); then           # fully blurred, A dissolves into B
        j=$((k-na+ov)); s=$sg
        mix=$(awk -v j="$j" -v m="$ov" 'BEGIN{t=(j+1)/(m+1); printf "%.1f", 100*t*t*(3-2*t)}')
        convert "$(printf '%s/a%03d.png' "$D" "$k")" "$(printf '%s/b%03d.png' "$D" "$j")" -compose blend -define compose:args="$mix" -composite "$D/mix.png"
        src="$D/mix.png"
      else                            # B comes into focus
        s=$(awk -v q="$((k-na))" -v m="$((nb-ov))" -v g="$sg" 'BEGIN{t=1-(q+1)/(m+1); printf "%.2f", g*t*t*(3-2*t)}')
        src=$(printf '%s/b%03d.png' "$D" "$((k-na+ov))")
      fi
      soften "$src" "$s" "$(printf '%s/o%03d.png' "$D" "$k")"
    done
    ffmpeg -nostdin -v error -y -framerate 24 -start_number 0 -i "$D/o%03d.png" -vf "format=yuv420p,setpts=N/24/TB" $ENC "$P"
    rm -rf "$D"
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
