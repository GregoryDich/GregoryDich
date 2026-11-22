# MICRO BOOST 10%, the desktop film: one visit to the clinic in one unbroken movement, 24 fps, 995 frames = 41.5 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> micro-boost-10-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py micro-boost-10-film.mp4 micro-boost-10-film-mobile.mp4 vertical-keys.json
# The clips dir holds the Kling 4.0 results from Atlas (1080p, 5 s = 121 frames) and the still frames:
#   K0p.png, K1.png  the pack sharp / the skin examination sharp - K0p is built from K1 (build-k7.py), so the opening
#                    focus pull is a free dissolve
#   T2  she lies down on the reclined couch, the cheek is patted dry (K1 -> K2). The clip has a hidden cut at frame 52
#       (wide framing with a large box -> closer framing with a smaller box) and the cosmetologist's head leaves the
#       frame around frames 43-70, so frames 27-81 are replaced by a soft-focus join: 27-46 go out of focus, dissolve
#       into 62-81 while fully blurred, and those come into focus
#   T3  the tissue goes, the fingertips of both hands massage the cheek (K2 -> K3)
#   T4  the hands lift, she opens her eyes: "does it tingle?" (K3 -> K4)
#   D1  into the skin of the cheek (K4 -> Y1); the still tail of the clip runs twice as fast
#   BL  the golden product goes down along the spicules (Y1 -> Y2)
#   D2  out of the skin: the mask is on the face (K6 -> Y2, played backwards; its still part twice as fast)
#   K6.png, K7.png   the mask scene sharp / the pack sharp - K7 is built from K6 (build-k7.py): a free dissolve
# Film frames:  hold 0-59 | focus 60-99 | hold 100-117 | settle 118-123 | T2 124-149 | soft-focus join 150-181 |
#               T2 182-220 | T3 221-340 | T4 341-460 | D1 461-560 | BL 561-680 | settle 681-686 |
#               D2 backwards 687-786 | settle 787-792 | hold 793-834 | focus 835-874 | hold 875-994
# Chapters: 0-82 | 82-166 | 166-341 | 341-500 | 500-746 | 746-855 | 855-925 | 925-995
hold K0p.png 0 60
fade K0p.png 0 K1.png 0 40
hold K1.png 0 18
fade K1.png 0 T2.mp4 0 6
clip T2.mp4 1 26
blur T2.mp4 27 46 T2.mp4 62 81 8 26
clip T2.mp4 82 120
clip T3.mp4 1 120
clip T4.mp4 1 120
clip D1.mp4 1 80
clip D1.mp4 82 120 2
clip BL.mp4 1 120
fade BL.mp4 120 D2.mp4 120 6
clip D2.mp4 80 119 2 rev
clip D2.mp4 0 79 1 rev
fade D2.mp4 0 K6.png 0 6
hold K6.png 0 42
fade K6.png 0 K7.png 0 40
hold K7.png 0 120
