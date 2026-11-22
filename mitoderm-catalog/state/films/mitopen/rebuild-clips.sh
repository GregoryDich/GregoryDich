#!/bin/bash
# rebuild-clips.sh <clips dir>
# Puts back everything film-16x9.spec needs, free of charge, after the temporary folder is lost (a container restart):
#   - the plate without the device and the page's own stills are fetched from the durable copies (requests.json,
#     "backup");
#   - the frames with the real pen (K0, K1, K2) and the three camera moves on it (Zin, Zin24, Zdrift) are built again
#     by build-pen-frames.py;
#   - the three paid clips E, D, BL (shot 22/11, requests.json, own_scenes_22_11.jobs) are fetched from their durable
#     copies; a clip that is already in the folder is never overwritten.
# Then: ../tools/film-assemble.sh film-16x9.spec <clips dir> mitopen-film.mp4 1912 1080
# Needs ImageMagick, ffmpeg, curl.
set -euo pipefail
C=${1:?clips dir}; mkdir -p "$C"
HERE=$(cd "$(dirname "$0")" && pwd)
PEN=$HERE/../../../codex-site/public/assets/products/mitopen.webp
BASE=https://d2ol7oe51mr4n9.cloudfront.net/user_2wup4xNeevN3QH5Pxv4g6PWRmPW
ENC="-an -c:v libx264 -preset medium -crf 8 -pix_fmt yuv420p -r 24"
get() { [ -s "$C/$2" ] || curl -sf --max-time 180 -o "$C/$2" "$BASE/$1" || { echo "cannot fetch $2"; exit 1; }; }
get 99ae1715-38b7-432c-a371-561e58cd10ad.png A-plate.png   # the room, M and P2, a towel on the table, no device
get 961a3230-80cd-4f4e-bf60-3e49e9b5ad73.png K3e.png       # the pen on the cheek (K3d with the streak patched)
get 695caf1d-2dc1-497a-865f-053119f8d863.png Y1.png        # inside the skin: the row of micro-channels
get 23f1d615-bf1c-4efa-af37-f29884fbc001.png Y2.png        # the product goes down the channels
get 3a578e61-38d6-46f1-9b54-5e7ec4ec3080.mp4 E.mp4         # the live examination
get b272c02a-49ed-4f3a-bb70-939b3198fc44.mp4 D.mp4         # the pen works on the cheek, the camera goes into the skin
get 72b10e13-36f8-4281-834f-b512fbf759ed.mp4 BL.mp4        # the product goes down the micro-channels
python3 "$HERE/build-pen-frames.py" "$C/A-plate.png" "$PEN" "$C" > /dev/null                 # K0.png, K1.png
python3 "$HERE/build-pen-frames.py" "$C/A-plate.png" "$PEN" "$C" zoom=2 > /dev/null          # K2.png
move() {  # <name> <sequence>
  rm -rf "$C/.seq-$1" "$C/$1.mp4"; python3 "$HERE/build-pen-frames.py" "$C/A-plate.png" "$PEN" "$C/.seq-$1" "sequence=$2" size=1912x1080 > /dev/null
  ffmpeg -nostdin -v error -y -framerate 24 -i "$C/.seq-$1/z%03d.png" $ENC "$C/$1.mp4"; rm -rf "$C/.seq-$1"
}
# the three moves are rendered frame by frame (about five minutes each), so they run side by side
move Zin 1,2,48 & move Zin24 1,2.4,54 & move Zdrift 2.4,2,48 & wait
for f in Zin Zin24 Zdrift; do [ -s "$C/$f.mp4" ] || { echo "the camera move $f was not built"; exit 1; }; done
echo "clips dir ready: $(ls "$C" | tr '\n' ' ')"
