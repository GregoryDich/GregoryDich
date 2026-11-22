#!/bin/bash
# rebuild-clips.sh <clips dir>
# Puts back everything film-16x9.spec needs, free of charge, after the temporary folder is lost (a container restart):
# the three paid clips and the rendered opening are fetched from their durable copies (requests.json,
# reshoot_22_11.backup and opening_22_11); a clip that is already in the folder is never overwritten.
#   T1 - the box in the clinic, the focus goes to the two women (shot 21/11)
#   O  - the kit opens on the table: rendered from the exact 3D model (kit3d.py, 85 minutes), then given its margins
#        (extend-frames.py). How to make it again from nothing: requests.json, opening_22_11
#   W  - clear drops of the solution and the MITOPEN pen at work on the cheek (shot 22/11)
#   BL - the clear solution goes down the micro-channels (shot 22/11)
# Then: ../tools/film-assemble.sh film-16x9.spec <clips dir> mitotech-cell-booster-film.mp4 1912 1080
#       ../tools/vertical-from-horizontal.py mitotech-cell-booster-film.mp4 mitotech-cell-booster-film-mobile.mp4 vertical-keys.json
# Needs curl.
set -euo pipefail
C=${1:?clips dir}; mkdir -p "$C"
BASE=https://d2ol7oe51mr4n9.cloudfront.net/user_2wup4xNeevN3QH5Pxv4g6PWRmPW
get() { [ -s "$C/$2" ] || curl -sf --max-time 180 -o "$C/$2" "$BASE/$1" || { echo "cannot fetch $2"; exit 1; }; }
get 8cef1e06-f239-4328-a9bd-49a4eddd51c9.mp4 T1.mp4
get 7766df7a-0379-4ce7-b15b-5f6edbcf4fab.mp4 O.mp4
get 54acb3a5-0f74-4d9b-98bb-cb6bc322b4b7.mp4 W.mp4
get 8fb8f93b-f9ed-4f15-ad46-5b228b915419.mp4 BL.mp4
echo "clips dir ready: $(ls "$C" | tr '\n' ' ')"
