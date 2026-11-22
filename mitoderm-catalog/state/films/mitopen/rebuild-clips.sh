#!/bin/bash
# rebuild-clips.sh <clips dir>
# Puts back everything film-16x9.spec needs, free of charge, after the temporary folder is lost (a container restart):
#   - the plate without the device and the page's own stills are fetched from the durable copies (requests.json,
#     "backup");
#   - the frames with the real pen (K0, K1, K2) and the three camera moves on it (Zin, Zin24, Zdrift) are built again
#     by build-pen-frames.py;
#   - E, D, BL get free stand-ins ONLY where a file is missing: a real paid clip in the folder is never overwritten.
# Then: ../tools/film-assemble.sh film-16x9.spec <clips dir> mitopen-film.mp4 1912 1080
# Needs ImageMagick, ffmpeg, curl.
set -euo pipefail
C=${1:?clips dir}; mkdir -p "$C"
HERE=$(cd "$(dirname "$0")" && pwd); T=$HERE/../tools
PEN=$HERE/../../../codex-site/public/assets/products/mitopen.webp
BASE=https://d2ol7oe51mr4n9.cloudfront.net/user_2wup4xNeevN3QH5Pxv4g6PWRmPW
ENC="-an -c:v libx264 -preset medium -crf 8 -pix_fmt yuv420p -r 24"
N="scale=1912:1080:force_original_aspect_ratio=increase,crop=1912:1080,setsar=1,format=yuv420p"
get() { [ -s "$C/$2" ] || curl -sf --max-time 180 -o "$C/$2" "$BASE/$1" || { echo "cannot fetch $2"; exit 1; }; }
get 99ae1715-38b7-432c-a371-561e58cd10ad.png A-plate.png   # the room, M and P2, a towel on the table, no device
get 961a3230-80cd-4f4e-bf60-3e49e9b5ad73.png K3e.png       # the pen on the cheek (K3d with the streak patched)
get 695caf1d-2dc1-497a-865f-053119f8d863.png Y1.png        # inside the skin: the row of micro-channels
get 23f1d615-bf1c-4efa-af37-f29884fbc001.png Y2.png        # the product goes down the channels
python3 "$HERE/build-pen-frames.py" "$C/A-plate.png" "$PEN" "$C" > /dev/null                 # K0.png, K1.png
python3 "$HERE/build-pen-frames.py" "$C/A-plate.png" "$PEN" "$C" zoom=2 > /dev/null          # K2.png
move() {  # <name> <sequence>
  rm -rf "$C/.seq-$1" "$C/$1.mp4"; python3 "$HERE/build-pen-frames.py" "$C/A-plate.png" "$PEN" "$C/.seq-$1" "sequence=$2" size=1912x1080 > /dev/null
  ffmpeg -nostdin -v error -y -framerate 24 -i "$C/.seq-$1/z%03d.png" $ENC "$C/$1.mp4"; rm -rf "$C/.seq-$1"
}
# the three moves are rendered frame by frame (about five minutes each), so they run side by side
move Zin 1,2,48 & move Zin24 1,2.4,54 & move Zdrift 2.4,2,48 & wait
for f in Zin Zin24 Zdrift; do [ -s "$C/$f.mp4" ] || { echo "the camera move $f was not built"; exit 1; }; done
W=$C/.standin; rm -rf "$W"; mkdir -p "$W"
if [ ! -s "$C/E.mp4" ]; then   # the camera breathes in and out on K1 and ends exactly where it starts
  bash "$T/still-zoom.sh" "$C/K1.png" "$W/E1.mp4" 61 1.00 1.035 0.52 0.40 > /dev/null
  bash "$T/still-zoom.sh" "$C/K1.png" "$W/E2.mp4" 60 1.035 1.00 0.52 0.40 > /dev/null
  printf 'clip E1.mp4 0 60\nclip E2.mp4 0 59\n' > "$W/E.spec"
  bash "$T/film-assemble.sh" "$W/E.spec" "$W" "$C/E.mp4" 1912 1080 > /dev/null
fi
if [ ! -s "$C/D.mp4" ]; then   # almost still for two seconds, a push-in toward the working end, a soft-focus join into Y1
  bash "$T/still-zoom.sh" "$C/K3e.png" "$W/DA.mp4" 48 1.00 1.02 0.52 0.72 > /dev/null
  bash "$T/still-zoom.sh" "$C/K3e.png" "$W/DB.mp4" 56 1.02 2.60 0.52 0.72 > /dev/null
  cp "$C/Y1.png" "$W/Y1.png"
  printf 'clip DA.mp4 0 47\nclip DB.mp4 0 43\nblur DB.mp4 44 55 Y1.png 0 24 8 26\n' > "$W/D.spec"
  bash "$T/film-assemble.sh" "$W/D.spec" "$W" "$C/D.mp4" 1912 1080 > /dev/null
fi
if [ ! -s "$C/BL.mp4" ]; then  # Y1 dissolves into Y2: the same channels, the product comes in
  ffmpeg -nostdin -v error -y -loop 1 -framerate 24 -i "$C/Y1.png" -loop 1 -framerate 24 -i "$C/Y2.png" -filter_complex \
    "[0:v]$N[x];[1:v]$N[y];[x][y]blend=all_expr='A+(B-A)*(3*pow(clip((N-12)/96\,0\,1)\,2)-2*pow(clip((N-12)/96\,0\,1)\,3))',format=yuv420p" \
    -frames:v 121 $ENC "$C/BL.mp4"
fi
rm -rf "$W"
echo "clips dir ready: $(ls "$C" | tr '\n' ' ')"
