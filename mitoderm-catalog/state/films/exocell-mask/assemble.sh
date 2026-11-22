#!/bin/bash
# Assemble the EXOCELL MASK scroll film (storyboard version 3, 22/11) from the accepted clips.
# Usage: assemble.sh <clips dir> <output.mp4> [width height] [desktop|mobile] [last good frame of D] [join]
#   <clips dir> holds A.mp4 B.mp4 S.mp4 C.mp4 D.mp4 (Kling, 24 fps, 121 frames each; for the phone - the vertical
#   takes) and L.mp4 P.mp4 (Kling 4.0, 1912x1080, shot 22/11; the same horizontal files for both films).
#   desktop: 1912 1080 (default); mobile: 1080 1912.
#   join: frames by which P and C overlap (P ends and C starts on the still K2); 0 = a plain cut. The page film uses
#   6. Desktop: the two takes agree to a pixel there, so the last <join> frames of P cross-fade into the first of C.
#   Mobile: P is a close window and C a wider vertical take - a dissolve between two framings would show a double
#   image when the scroll stops on it, so the film cuts and C simply starts <join> frames later (same length).
#   The film on the page: "<c16 dir> out.mp4 1912 1080 desktop 54 6" and "<c9 dir> out.mp4 1080 1912 mobile 56 6".
# Layout at 24 fps, 990 frames with join 0 (chapter = frames; every number after chapter 05 moves back by <join>:
# 984 frames with join 6, chapter 05 = 468-666, 06 = 666-738, 07 = 738-846, 08 = 846-984):
#   01 pack 0-108 | 02 consultation 108-228 | 03 sachet 228-348 | 04 layers 348-468 | 05 mask on face 468-672
#   06 absorption 672-744 | 07 finish 744-852 | 08 pack 852-990
# A plays forward after a 24-frame hold of its first frame (144 frames), then hard cuts: B 0-83, S 0-119,
# L 0-119 (the layers come apart, the pale-blue paper part leaves, the white mask stays), P 0-119 (the white mask
# is laid on the face) running into C 0-83 (smoothing), C 84-120 plus a 35-frame hold of its last frame, then the
# finish and A played backwards with a hold of its first frame.
# Version 2 (20/11) held the still KL for 72 frames in chapter 04 and cut straight to C: neither the paper part
# coming off nor the mask being laid was seen - the owner's word of 21/11 asked for both.
# Finish (chapter 07): in clip D the hands pat the face until about frame 54 and are then raised in the air, so D
# plays 0..DEND forward and DEND..0 backwards (the patting reads the same both ways), padded to 114 frames; its
# last 6 frames dissolve into the last frame of A.
# Desktop only: clip A is cropped by 4% from the right (an object appears at the right edge late in the take).
# Mobile only: L and P are full-height windows cut from the horizontal clips (the hands with the layers; the
# patient's face with the mask); in the vertical clip C the cosmetologist straightens up out of the frame after
# frame 77, so chapter 06 is a cut-in on the patient's masked face (the lower right two thirds, enlarged 1.5x).
set -euo pipefail
C=${1:?clips dir}; O=${2:?output}; W=${3:-1912}; H=${4:-1080}; MODE=${5:-desktop}; DEND=${6:-54}; JOIN=${7:-0}
N="fps=24,scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1,format=yuv420p,settb=AVTB"
T="setpts=N/24/TB,fps=24,settb=AVTB"
if [ "$MODE" = desktop ]; then
  ACROP="crop=iw*0.958:ih*0.958:0:ih*0.021,"   # keep the left edge, drop the right 4%
  LCROP=""; PCROP=""; C2CROP=""
else
  ACROP=""
  LCROP="crop=ih*9/16:ih:iw*0.257:0,"          # the hands and the layers: 26-57% of the width (the whole white mask)
  PCROP="crop=ih*9/16:ih:iw*0.39:0,"           # the patient's face and the mask: 39-71% of the width
  C2CROP="crop=iw/1.5:ih/1.5:iw-ow:ih-oh,"      # cut-in on the patient's face
fi
DFWD=$((DEND + 1)); DPAD=$((114 - 2 * DFWD)); [ "$DPAD" -ge 0 ] || { echo "DEND too large"; exit 1; }
[ "$JOIN" -ge 0 ] && [ "$JOIN" -le 24 ] || { echo "join must be 0..24"; exit 1; }
CSTART=0
if [ "$JOIN" -gt 0 ] && [ "$MODE" = desktop ]; then
  PC="[p][c1]xfade=transition=fade:duration=$(awk -v j="$JOIN" 'BEGIN{printf "%.5f", j/24}'):offset=$(awk -v j="$JOIN" 'BEGIN{printf "%.5f", (120-j)/24}'),${T}[pc];"
else
  CSTART=$JOIN
  PC="[p][c1]concat=n=2:v=1:a=0,${T}[pc];"
fi
ffmpeg -nostdin -v error -y -i "$C/A.mp4" -i "$C/B.mp4" -i "$C/S.mp4" -i "$C/L.mp4" -i "$C/P.mp4" -i "$C/C.mp4" -i "$C/D.mp4" -filter_complex "
[0:v]${ACROP}${N},split=2[a1][a2];
[a1]tpad=start_mode=clone:start=23,${T}[afwd];
[1:v]${N},trim=end_frame=84,${T}[b];
[2:v]${N},trim=end_frame=120,${T}[s];
[3:v]${LCROP}${N},trim=end_frame=120,${T}[l];
[4:v]${PCROP}${N},trim=end_frame=120,${T}[p];
[5:v]split=2[c1i][c2i];
[c1i]${N},trim=start_frame=${CSTART}:end_frame=84,${T}[c1];
[c2i]trim=start_frame=84,setpts=PTS-STARTPTS,${C2CROP}${N},tpad=stop_mode=clone:stop=35,${T}[c2];
${PC}
[6:v]${N},trim=end_frame=${DFWD},${T},split=2[d1][d2];
[d2]reverse,tpad=stop_mode=clone:stop=${DPAD},${T}[d2r];
[d1][d2r]concat=n=2:v=1:a=0,${T}[d];
[a2]reverse,tpad=start_mode=clone:start=6:stop_mode=clone:stop=11,${T}[arev];
[d][arev]xfade=transition=fade:duration=0.25:offset=4.5,${T}[tail];
[afwd][b][s][l][pc][c2][tail]concat=n=7:v=1:a=0,${T}[out]" \
  -map "[out]" -an -c:v libx264 -preset slower -tune film -profile:v high -pix_fmt yuv420p -crf 22 \
  -g 12 -keyint_min 12 -sc_threshold 0 -movflags +faststart "$O"
E5=$((672 - JOIN))
echo "frames=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$O") size=$(stat -c %s "$O")"
echo "chapters: 0-108 | 108-228 | 228-348 | 348-468 | 468-$E5 | $E5-$((E5 + 72)) | $((E5 + 72))-$((E5 + 180)) | $((E5 + 180))-$((E5 + 318))"
