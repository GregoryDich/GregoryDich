#!/bin/bash
# Assemble the EXOCELL MASK scroll film (storyboard version 2) from the accepted clips.
# Usage: assemble.sh <clips dir> <output.mp4> [width height] [desktop|mobile] [last good frame of D]
#   <clips dir> holds A.mp4 B.mp4 S.mp4 C.mp4 D.mp4 (Kling, 24 fps, 121 frames each) and KL.png (the layers still).
#   desktop: 1912 1080 (default); mobile: 1080 1912.
# Layout, 822 frames at 24 fps (chapter = frames):
#   01 pack 0-108 | 02 consultation 108-228 | 03 sachet 228-348 | 04 layers 348-420 | 05 mask on face 420-504
#   06 absorption 504-576 | 07 finish 576-684 | 08 pack 684-822
# A plays forward after a 24-frame hold of its first frame (144 frames), then hard cuts: B 0-83, S 0-119,
# the layers still held 72 frames with a slow push-in, C 0-83, C 84-120 plus a 35-frame hold of its last frame,
# then the finish and A played backwards with a hold of its first frame.
# Finish (chapter 07): in clip D the hands pat the face until about frame 54 and are then raised in the air, so D
# plays 0..DEND forward and DEND..0 backwards (the patting reads the same both ways), padded to 114 frames; its
# last 6 frames dissolve into the last frame of A.
# Desktop only: clip A is cropped by 4% from the right (an object appears at the right edge late in the take).
# Mobile only: in the vertical clip C the cosmetologist straightens up out of the frame after frame 77, so
# chapter 06 is a cut-in on the patient's masked face (the lower right two thirds of the frame, enlarged 1.5x).
set -euo pipefail
C=${1:?clips dir}; O=${2:?output}; W=${3:-1912}; H=${4:-1080}; MODE=${5:-desktop}; DEND=${6:-54}
N="fps=24,scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1,format=yuv420p,settb=AVTB"
T="setpts=N/24/TB,fps=24,settb=AVTB"
if [ "$MODE" = desktop ]; then
  ACROP="crop=iw*0.958:ih*0.958:0:ih*0.021,"   # keep the left edge, drop the right 4%
  KX=0.38; KY=0.45                              # push-in towards the hands, left of centre
  C2CROP=""
else
  ACROP=""; KX=0.5; KY=0.38
  C2CROP="crop=iw/1.5:ih/1.5:iw-ow:ih-oh,"      # cut-in on the patient's face
fi
DFWD=$((DEND + 1)); DPAD=$((114 - 2 * DFWD)); [ "$DPAD" -ge 0 ] || { echo "DEND too large"; exit 1; }
ffmpeg -v error -y -i "$C/A.mp4" -i "$C/B.mp4" -i "$C/S.mp4" -loop 1 -framerate 24 -t 3 -i "$C/KL.png" -i "$C/C.mp4" -i "$C/D.mp4" -filter_complex "
[0:v]${ACROP}${N},split=2[a1][a2];
[a1]tpad=start_mode=clone:start=23,${T}[afwd];
[1:v]${N},trim=end_frame=84,${T}[b];
[2:v]${N},trim=end_frame=120,${T}[s];
[3:v]scale=$((W*2)):$((H*2)):force_original_aspect_ratio=increase,crop=$((W*2)):$((H*2)),zoompan=z='1+0.06*on/71':x='(iw-iw/zoom)*${KX}':y='(ih-ih/zoom)*${KY}':d=1:s=${W}x${H}:fps=24,trim=end_frame=72,setsar=1,format=yuv420p,${T}[kl];
[4:v]split=2[c1i][c2i];
[c1i]${N},trim=end_frame=84,${T}[c1];
[c2i]trim=start_frame=84,setpts=PTS-STARTPTS,${C2CROP}${N},tpad=stop_mode=clone:stop=35,${T}[c2];
[5:v]${N},trim=end_frame=${DFWD},${T},split=2[d1][d2];
[d2]reverse,tpad=stop_mode=clone:stop=${DPAD},${T}[d2r];
[d1][d2r]concat=n=2:v=1:a=0,${T}[d];
[a2]reverse,tpad=start_mode=clone:start=6:stop_mode=clone:stop=11,${T}[arev];
[d][arev]xfade=transition=fade:duration=0.25:offset=4.5,${T}[tail];
[afwd][b][s][kl][c1][c2][tail]concat=n=7:v=1:a=0,${T}[out]" \
  -map "[out]" -an -c:v libx264 -preset slower -tune film -profile:v high -pix_fmt yuv420p -crf 22 \
  -g 12 -keyint_min 12 -sc_threshold 0 -movflags +faststart "$O"
echo "frames=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$O") size=$(stat -c %s "$O")"
