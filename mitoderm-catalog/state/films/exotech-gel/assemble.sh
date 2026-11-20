#!/bin/bash
# Assemble the EXOTECH GEL scroll film from the accepted clips and stills.
# Usage: assemble.sh <clips dir> <output.mp4> [width height] [desktop|mobile] [last good frame of D]
#   <clips dir> holds A.mp4 B.mp4 C.mp4 D.mp4 (Kling, 24 fps, 121 frames each), K3.png (the open box) and
#   K6.png (the jar at home). desktop: 1912 1080 (default); mobile: 1080 1912.
# Layout, 822 frames at 24 fps (chapter = frames):
#   01 pack 0-108 | 02 recommendation 108-228 | 03 open box 228-336 | 04 application 336-420
#   05 absorbed 420-492 | 06 every day 492-576 | 07 next visit 576-684 | 08 pack 684-822
# A plays forward after a 24-frame hold of its first frame (144 frames); hard cut to B 0-83; the open-box still
# held 108 frames with a slow push-in; C 0-83; C 84-120 and back 119-85 (the circles read the same both ways, so
# there is no frozen face); the jar still held 84 frames with a slow push-in; D 0-113, its last 6 frames dissolving
# into A played backwards, which ends on a hold of its first frame.
# If the second half of D is unusable, pass its last good frame: D plays 0..N forward and then backwards.
# Edges: in the desktop A an object appears at the left edge late in the take, in the mobile A at the right edge;
# 4% is cropped from that side.
set -euo pipefail
C=${1:?clips dir}; O=${2:?output}; W=${3:-1912}; H=${4:-1080}; MODE=${5:-desktop}; DEND=${6:-113}
N="fps=24,scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1,format=yuv420p,settb=AVTB"
T="setpts=N/24/TB,fps=24,settb=AVTB"
if [ "$MODE" = desktop ]; then
  ACROP="crop=iw*0.958:ih*0.958:iw-ow:ih*0.021,"   # keep the right edge, drop the left 4%
  K3X=0.37; K3Y=0.45; K6X=0.34; K6Y=0.50
else
  ACROP="crop=iw*0.958:ih*0.958:0:ih*0.021,"       # keep the left edge, drop the right 4%
  K3X=0.50; K3Y=0.62; K6X=0.50; K6Y=0.43           # the open box must not grow downwards into the caption
fi
still() {  # <input label> <frames> <anchor x> <anchor y> <output label>
  echo "[$1]scale=$((W*2)):$((H*2)):force_original_aspect_ratio=increase,crop=$((W*2)):$((H*2)),zoompan=z='1+0.06*on/$(($2-1))':x='(iw-iw/zoom)*$3':y='(ih-ih/zoom)*$4':d=1:s=${W}x${H}:fps=24,trim=end_frame=$2,setsar=1,format=yuv420p,${T}[$5];"
}
if [ "$DEND" -ge 113 ]; then
  DPART="[5:v]${N},trim=end_frame=114,${T}[d];"
else
  FWD=$((DEND + 1)); BACK=$((114 - FWD)); FROM=$((DEND - BACK)); PAD=0
  if [ "$FROM" -lt 0 ]; then PAD=$((-FROM)); FROM=0; fi
  DPART="[5:v]${N},split=2[dA][dB];[dA]trim=end_frame=${FWD},${T}[d1];[dB]trim=start_frame=${FROM}:end_frame=${DEND},${T},reverse,tpad=stop_mode=clone:stop=${PAD},${T}[d2];[d1][d2]concat=n=2:v=1:a=0,${T}[d];"
fi
ffmpeg -v error -y -i "$C/A.mp4" -i "$C/B.mp4" -loop 1 -framerate 24 -t 5 -i "$C/K3.png" -i "$C/C.mp4" \
  -loop 1 -framerate 24 -t 4 -i "$C/K6.png" -i "$C/D.mp4" -filter_complex "
[0:v]${ACROP}${N},split=2[a1][a2];
[a1]tpad=start_mode=clone:start=23,${T}[afwd];
[1:v]${N},trim=end_frame=84,${T}[b];
$(still 2:v 108 $K3X $K3Y k3)
[3:v]${N},split=3[cA][cB][cC];
[cA]trim=end_frame=84,${T}[c1];
[cB]trim=start_frame=84,${T}[c2f];
[cC]trim=start_frame=85:end_frame=120,${T},reverse,${T}[c2r];
[c2f][c2r]concat=n=2:v=1:a=0,${T}[c2];
$(still 4:v 84 $K6X $K6Y k6)
${DPART}
[a2]reverse,tpad=start_mode=clone:start=6:stop_mode=clone:stop=11,${T}[arev];
[d][arev]xfade=transition=fade:duration=0.25:offset=4.5,${T}[tail];
[afwd][b][k3][c1][c2][k6][tail]concat=n=7:v=1:a=0,${T}[out]" \
  -map "[out]" -an -c:v libx264 -preset slower -tune film -profile:v high -pix_fmt yuv420p -crf 22 \
  -g 12 -keyint_min 12 -sc_threshold 0 -movflags +faststart "$O"
echo "frames=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$O") size=$(stat -c %s "$O")"
