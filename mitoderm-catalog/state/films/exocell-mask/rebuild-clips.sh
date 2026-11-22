#!/bin/bash
# rebuild-clips.sh <dir>
# Puts back everything assemble.sh needs, free of charge, after the temporary folder is lost (a container restart):
# <dir>/c16 gets the seven clips of the desktop film, <dir>/c9 the seven clips of the phone film. All of them are
# fetched from durable copies (requests.json, reshoot_22_11.backup); a clip that is already there is never overwritten.
#   A B S C D - the clips of 20/11 (Kling, 121 frames; horizontal takes for c16, vertical takes for c9)
#   L P       - the clips of 22/11 (Kling 4.0, 1912x1080): the layers come apart; the white mask is laid on the face.
#               The same horizontal files serve both films (the phone film cuts full-height windows out of them).
# Then: assemble.sh <dir>/c16 exocell-mask-film.mp4 1912 1080 desktop 54 6
#       assemble.sh <dir>/c9 exocell-mask-film-mobile.mp4 1080 1912 mobile 56 6
# Needs curl.
set -euo pipefail
D=${1:?dir}; mkdir -p "$D/c16" "$D/c9"
BASE=https://d2ol7oe51mr4n9.cloudfront.net/user_2wup4xNeevN3QH5Pxv4g6PWRmPW
get() { [ -s "$D/$2" ] || curl -sf --max-time 180 -o "$D/$2" "$BASE/$1" || { echo "cannot fetch $2"; exit 1; }; }
get cf4ae2f7-1b32-4e5a-b925-8edb4dd79a15.mp4 c16/A.mp4   # the pack close, the camera pulls back
get 4e4785f7-ae73-48e6-9796-ea9bbc4ab06c.mp4 c16/B.mp4   # the consultation
get 97331a4f-a3cd-4a70-a21b-7b964bf21e7d.mp4 c16/S.mp4   # the sachet is open, the mask comes out
get 9a75a41a-c1ed-4917-9b27-f5417126f978.mp4 c16/C.mp4   # the mask on the face is smoothed, then rest
get 13331d68-80c1-4d45-8525-9d7080c5c07f.mp4 c16/D.mp4   # the finish
get 4181bc7c-8a67-4e4e-b8f0-c35ebdb3fcbd.mp4 c9/A.mp4
get 790c08ef-df67-4719-ab46-516701ad8154.mp4 c9/B.mp4
get 2d577bde-3b07-41d5-9a23-b71372e0b065.mp4 c9/S.mp4
get b337fd74-ff6a-4c33-849c-21194618419a.mp4 c9/C.mp4
get 7eea109f-6ed2-4609-b8e0-c6aaa5acc691.mp4 c9/D.mp4
for d in c16 c9; do
  get 6f52f6db-4354-4eda-9971-3429022b746d.mp4 $d/L.mp4  # the layers come apart, the white mask stays
  get 7262942d-74bc-459a-a86a-e6e8725c228f.mp4 $d/P.mp4  # the white mask is laid on the face
done
echo "c16: $(ls "$D/c16" | tr '\n' ' ')"; echo "c9: $(ls "$D/c9" | tr '\n' ' ')"
