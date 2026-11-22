# MITOSCAN, the desktop film of the page's own scenes: 24 fps, 837 frames = 34.9 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> mitoscan-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitoscan-film.mp4 mitoscan-film-mobile.mp4 vertical-keys.json
# The system is never drawn by a model: the real photo (protocols/print/img/mitoscan.webp) is placed on a plate
# generated without any device. The clips dir holds:
#   K0r.png, K1r.png  the system sharp on the table / the people sharp - one plate (P1), the same system in the same
#                     place (tools/place-pack.py at=36,985 height=470), so the focus pull is a free dissolve
#   C1.mp4  PAID, to shoot after the owner's ok on the sheet: the look with the naked eye (starts at N)
#   C2.mp4  PAID: the handset glides along the parting (starts at K3q)
#   C3.mp4  PAID: she points at the screen, the patient looks (starts at Sr)
#   ZS.mp4  free: the camera comes close to the real system with the scan on its display, 72 frames
#           (build-system-frames.py P1.png system-scan.png <dir> sequence=1,2,72 blur=0,9 size=1912x1080)
#   ZS0.mp4 free: the camera goes back, the room stays soft, 48 frames (sequence=2,1,48 blur=9,9)
#   K0s.png, K0b.png  the last frame of ZS0 (the scan on the display) and the same frame with the Mitoscan logo on the
#                     display (build-system-frames.py ... zoom=1 blur=9 size=1912x1080): the display changes, the system
#                     stays pixel for pixel
#   ZE.mp4  free: the end of the visit, a slow move on the still E (tools/still-zoom.sh E.png ZE.mp4 120 1 1.06 0.45 0.40)
# The move stops at zoom 2: on a 1440x900 screen the film keeps its left edge (wire.json, "anchor": "left" - the
# system stands 26 px from it) and a closer system would reach the caption.
# Until the three clips are shot the same file names hold free stand-ins (still-zoom.sh on N, K3q, Sr, 121 frames):
# the film can be assembled and checked, and the real clips only replace the files.
# The scenes do not meet frame to frame (each clip starts at its own still), so every change of scene is a soft-focus
# join (piece "blur"): no hidden cut, no generated transition.
# Film frames:  system 0-59 | focus to the people 60-95 | hold 96-107 | soft focus 108-139 | the look with the naked
#               eye 140-220 | soft focus 221-252 | the handset on the parting 253-333 | soft focus 334-365 | she
#               points at the screen 366-446 | soft focus 447-478 | the camera comes to the system 479-530 | hold
#               531-572 | the camera goes back 573-620 | the display: scan -> logo 621-650 | hold 651-704 | soft
#               focus 705-736 | the end of the visit 737-836
# Chapters: 0-124 | 124-237 | 237-350 | 350-463 | 463-573 | 573-651 | 651-721 | 721-837
hold K0r.png 0 60
fade K0r.png 0 K1r.png 0 36
hold K1r.png 0 12
blur K1r.png 0 19 C1.mp4 0 19 8 26
clip C1.mp4 20 100
blur C1.mp4 101 120 C2.mp4 0 19 8 26
clip C2.mp4 20 100
blur C2.mp4 101 120 C3.mp4 0 19 8 26
clip C3.mp4 20 100
blur C3.mp4 101 120 ZS.mp4 0 19 8 26
clip ZS.mp4 20 71
hold ZS.mp4 71 42
clip ZS0.mp4 0 47
fade K0s.png 0 K0b.png 0 30
hold K0b.png 0 54
blur K0b.png 0 19 ZE.mp4 0 19 8 26
clip ZE.mp4 20 119
