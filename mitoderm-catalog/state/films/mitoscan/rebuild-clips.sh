#!/bin/bash
# rebuild-clips.sh <clips dir>
# Puts back everything film-16x9.spec needs, free of charge, after the temporary folder is lost (a container restart):
#   - the stills that cannot be made from the repository are fetched from the durable copies (requests.json, "backup");
#   - the stills with the real system (K0r, K1r, Sr), the camera move to the system and back (ZS, ZS0), the two end
#     frames (K0s, K0b) and the slow move on the last still (ZE) are built again by the recorded commands;
#   - the three paid clips C1, C2, C3 (shot 22/11, requests.json, jobs) are fetched from their durable copies; a clip
#     that is already in the folder is never overwritten.
# Then: ../tools/film-assemble.sh film-16x9.spec <clips dir> mitoscan-film.mp4 1912 1080
# Needs ImageMagick, ffmpeg, curl.
set -euo pipefail
C=${1:?clips dir}; mkdir -p "$C"
HERE=$(cd "$(dirname "$0")" && pwd); T=$HERE/../tools
REAL=$HERE/../../../protocols/print/img/mitoscan.webp
BASE=https://d2ol7oe51mr4n9.cloudfront.net/user_2wup4xNeevN3QH5Pxv4g6PWRmPW
ENC="-an -c:v libx264 -preset medium -crf 8 -pix_fmt yuv420p -r 24"
get() { [ -s "$C/$2" ] || curl -sf --max-time 180 -o "$C/$2" "$BASE/$1" || { echo "cannot fetch $2"; exit 1; }; }
get 1d922c8f-9416-4a9a-88fa-92d7c397e33d.png P1.png              # the scene without the device
get 7f40ac5b-6aa2-4983-89f9-c344188b6a21.png system-scan.png     # the real photo with the scan fitted into its display
get 448be68d-48b8-47f4-a673-a652c22b1b00.png N.png               # the look with the naked eye
get b354aa3c-4462-4f8a-b8be-8b8d3f9f1c71.png K3q.png             # the handset on the parting
get 77b0bd8b-328c-4057-a974-97f1a7e4b951.png E.png               # the end of the visit
get 9cadcc47-dead-449f-996b-c30699ef1487.mp4 C1.mp4              # the look with the naked eye
get 05ccf252-fe35-4230-994a-b1f73fc8e5c8.mp4 C2.mp4              # the handset glides along the parting
get ae9f640e-39d7-4b57-93f7-f25f54d6b350.mp4 C3.mp4              # she points at the screen, the patient looks
place() { python3 "$T/place-pack.py" "$C/P1.png" "$1" "$C/$2" at=36,985 height=470 mirror=0.10,50 contact=0.25 "${@:3}" > /dev/null; }
place "$REAL" K0r.png plate_blur=9
place "$REAL" K1r.png pack_blur=5
place "$C/system-scan.png" Sr.png
move() {  # <name> <sequence> <blur>
  rm -rf "$C/.seq-$1" "$C/$1.mp4"; python3 "$HERE/build-system-frames.py" "$C/P1.png" "$C/system-scan.png" "$C/.seq-$1" "sequence=$2" "blur=$3" size=1912x1080 > /dev/null
  ffmpeg -nostdin -v error -y -framerate 24 -i "$C/.seq-$1/z%03d.png" $ENC "$C/$1.mp4"; rm -rf "$C/.seq-$1"
}
move ZS 1,2,72 0,9 & move ZS0 2,1,48 9,9 & wait
for f in ZS ZS0; do [ -s "$C/$f.mp4" ] || { echo "the camera move $f was not built"; exit 1; }; done
python3 "$HERE/build-system-frames.py" "$C/P1.png" "$C/system-scan.png" "$C" zoom=1 blur=9 size=1912x1080 name=K0s.png > /dev/null
python3 "$HERE/build-system-frames.py" "$C/P1.png" "$REAL" "$C" zoom=1 blur=9 size=1912x1080 name=K0b.png > /dev/null
bash "$T/still-zoom.sh" "$C/E.png" "$C/ZE.mp4" 120 1.00 1.06 0.45 0.40 > /dev/null
echo "clips dir ready: $(ls "$C" | tr '\n' ' ')"
