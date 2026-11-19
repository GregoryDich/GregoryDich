#!/bin/bash
# Re-encode the V-TECH scroll film at constant quality and build 1:1 comparison crops.
# Usage: film-encode2.sh <workdir>   (<workdir>/src/desktop.mp4 and src/mobile.mp4 are the masters;
#        optional older encodes in <workdir>/out/ are added to the comparison)
# Resumable: finished outputs are skipped. Frames are matched by number, not by timestamp.
W=${1:?workdir}; cd "$W" || exit 1
mkdir -p out2 cmp2; R=REPORT2.txt
ssim() { nice -n 15 ffmpeg -v info -i "$1" -i "$2" -lavfi "[0:v]setpts=N/24/TB[a];[1:v]setpts=N/24/TB[b];[a][b]ssim" -f null - 2>&1 | grep -o 'SSIM.*'; }
for tag in desktop mobile; do
  m=src/$tag.mp4; [ -f "$m" ] || continue
  if [ $tag = desktop ]; then crop="640:400:636:320"; old=out/desktop-2400k.mp4; else crop="640:400:86:420"; old=out/mobile-1000k.mp4; fi
  for crf in 20 22 24; do
    o=out2/$tag-crf$crf.mp4
    [ -f "$o" ] && continue
    nice -n 15 ffmpeg -v error -y -i "$m" -an -c:v libx264 -preset slower -tune film -profile:v high -pix_fmt yuv420p \
      -crf $crf -g 12 -keyint_min 12 -sc_threshold 0 -movflags +faststart "$o.tmp.mp4" && mv "$o.tmp.mp4" "$o"
    echo "$o size=$(stat -c %s "$o") $(ssim "$o" "$m")" >> $R
  done
  for n in 175 460 700; do
    [ -f cmp2/$tag-$n.png ] && continue
    ins="-i $m"; fl="[0:v]select=eq(n\\,$n),crop=$crop[m]"; lab="[m]"; i=1
    for f in out2/$tag-crf20.mp4 out2/$tag-crf24.mp4 $old; do
      [ -f "$f" ] || continue
      ins="$ins -i $f"; fl="$fl;[$i:v]select=eq(n\\,$n),crop=$crop[c$i]"; lab="$lab[c$i]"; i=$((i+1))
    done
    if [ $i -eq 4 ]; then stack="xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0"; else stack="hstack=inputs=$i"; fi
    ffmpeg -v error -y $ins -filter_complex "$fl;${lab}$stack" -frames:v 1 cmp2/$tag-$n.png
  done
done
echo DONE >> $R
