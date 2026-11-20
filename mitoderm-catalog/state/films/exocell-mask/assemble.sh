#!/bin/bash
# Assemble the EXOCELL MASK scroll film (storyboard version 2) from the accepted clips.
# Usage: assemble.sh <clips dir> <output.mp4> [width height] [desktop|mobile]
#   <clips dir> holds A.mp4 B.mp4 S.mp4 C.mp4 D.mp4 (Kling, 24 fps, 121 frames each) and KL.png (the layers still).
#   desktop: 1912 1080 (default); mobile: 1080 1912.
# Layout, 822 frames at 24 fps (chapter = frames):
#   01 pack 0-108 | 02 consultation 108-228 | 03 sachet 228-348 | 04 layers 348-420 | 05 mask on face 420-504
#   06 absorption 504-576 | 07 finish 576-684 | 08 pack 684-822
# A plays forward after a 24-frame hold of its first frame (144 frames), then hard cuts: B 0-83, S 0-119,
# the layers still held 72 frames with a slow push-in, C in full plus a 35-frame hold of its last frame,
# D 0-113 whose last 6 frames dissolve into the last frame of A; then A plays backwards and its first frame is held.
# Desktop only: clip A is cropped by 4% from the right (an object appears at the right edge late in the take).
set -euo pipefail
C=${1:?clips dir}; O=${2:?output}; W=${3:-1912}; H=${4:-1080}; MODE=${5:-desktop}
N="fps=24,scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1,format=yuv420p,settb=AVTB"
T="setpts=N/24/TB,fps=24,settb=AVTB"
if [ "$MODE" = desktop ]; then
  ACROP="crop=iw*0.958:ih*0.958:0:ih*0.021,"   # keep the left edge, drop the right 4%
  KX=0.38; KY=0.45                              # push-in towards the hands, left of centre
else
  ACROP=""; KX=0.5; KY=0.38
fi
ffmpeg -v error -y -i "$C/A.mp4" -i "$C/B.mp4" -i "$C/S.mp4" -loop 1 -framerate 24 -t 3 -i "$C/KL.png" -i "$C/C.mp4" -i "$C/D.mp4" -filter_complex "
[0:v]${ACROP}${N},split=2[a1][a2];
[a1]tpad=start_mode=clone:start=23,${T}[afwd];
[1:v]${N},trim=end_frame=84,${T}[b];
[2:v]${N},trim=end_frame=120,${T}[s];
[3:v]scale=$((W*2)):$((H*2)):force_original_aspect_ratio=increase,crop=$((W*2)):$((H*2)),zoompan=z='1+0.06*on/71':x='(iw-iw/zoom)*${KX}':y='(ih-ih/zoom)*${KY}':d=1:s=${W}x${H}:fps=24,trim=end_frame=72,setsar=1,format=yuv420p,${T}[kl];
[4:v]${N},tpad=stop_mode=clone:stop=35,${T}[c];
[5:v]${N},trim=end_frame=114,${T}[d];
[a2]reverse,tpad=start_mode=clone:start=6:stop_mode=clone:stop=11,${T}[arev];
[d][arev]xfade=transition=fade:duration=0.25:offset=4.5,${T}[tail];
[afwd][b][s][kl][c][tail]concat=n=6:v=1:a=0,${T}[out]" \
  -map "[out]" -an -c:v libx264 -preset slower -tune film -profile:v high -pix_fmt yuv420p -crf 22 \
  -g 12 -keyint_min 12 -sc_threshold 0 -movflags +faststart "$O"
echo "frames=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$O") size=$(stat -c %s "$O")"
