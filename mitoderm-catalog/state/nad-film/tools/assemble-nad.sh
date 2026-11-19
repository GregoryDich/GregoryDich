#!/bin/bash
# Assemble the EXO-NAD scroll film from the approved clips (see PROGRESS.md for the clip links).
# Usage: assemble-nad.sh <clips dir> <output.mp4> [width height]
#   <clips dir> holds A-final.mp4 B.mp4 C-sample.mp4 D.mp4 E.mp4 F.mp4 (24 fps, 121 frames each).
# Layout, 834 frames at 24 fps (scene = frames):
#   01 kit 0-108 | 02 consultation 108-198 | 03 peel 198-306 | 04 normaliser 306-427 | 05 serum 427-520
#   06 close 520-616 | 07 evidence 616-707 | 08 complete system 707-834
# A plays forward (after a 24-frame hold of its first frame) and blends into B over 6 frames; C, D, E are hard
# cuts (D in full, so the scene ends after the towel is gone; E only up to frame 93: after that the cosmetologist leaves the frame); F plays reversed and its last
# frame is held; A reversed closes the film after a 6-frame blend and a 12-frame hold.
set -euo pipefail
C=${1:?clips dir}; O=${2:?output}; W=${3:-1912}; H=${4:-1080}
N="fps=24,scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1,format=yuv420p,settb=AVTB"
T="setpts=N/24/TB,fps=24,settb=AVTB"
ffmpeg -v error -y -i "$C/A-final.mp4" -i "$C/B.mp4" -i "$C/C-sample.mp4" -i "$C/D.mp4" -i "$C/E.mp4" -i "$C/F.mp4" -filter_complex "
[0:v]${N},split=2[a1][a2];
[a1]tpad=start_mode=clone:start=23,${T}[p1];
[1:v]${N},trim=end_frame=60,${T}[b];
[p1][b]xfade=transition=fade:duration=0.25:offset=5.75,${T}[p1b];
[2:v]${N},trim=end_frame=108,${T}[c];
[3:v]${N},${T}[d];
[4:v]${N},trim=end_frame=93,${T}[e];
[5:v]${N},reverse,tpad=stop_mode=clone:stop=66,${T}[f];
[p1b][c][d][e][f]concat=n=5:v=1:a=0,${T}[p2];
[a2]reverse,tpad=stop_mode=clone:stop=12,${T}[ar];
[p2][ar]xfade=transition=fade:duration=0.25:offset=29.208333,${T}[out]" \
  -map "[out]" -an -c:v libx264 -preset slower -tune film -profile:v high -pix_fmt yuv420p -crf 22 \
  -g 12 -keyint_min 12 -sc_threshold 0 -movflags +faststart "$O"
echo "frames=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$O") size=$(stat -c %s "$O")"
