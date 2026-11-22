# MICRO BOOST 10%, the desktop film, version 2 (22/11): the white syringe is in the film. 24 fps, 1081 frames = 45.0 s.
# Version 1 (no syringe) is kept as film-v1-16x9.spec; everything not named here is as in version 1.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> micro-boost-10-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py micro-boost-10-film.mp4 micro-boost-10-film-mobile.mp4 vertical-keys.json
# New in version 2 (the owner's photos of the real syringe, 22/11):
#   C   a close-up: the cosmetologist's gloved hand lays the serum on the cheek from the real syringe, drop by drop
#       (K3c -> K3c, the camera stands). Kling 4.0, 1080p, 5 s. Until the owner says ok to the still K3c the clip is
#       not paid for: C.mp4 is then a stand-in, the still with a slow push-in (C-standin.mp4)
#   T3  is cut in two: frames 1-19 the tissue goes away (her hand goes down, out of the frame), frames 69-120 the
#       massage with both hands; between them stands the close-up, joined by soft focus on both sides
# Film frames:  hold 0-59 | focus 60-99 | hold 100-117 | settle 118-123 | T2 124-149 | soft-focus join 150-181 |
#               T2 182-220 | T3 221-239 | soft focus 240-261 | C 262-352 | soft focus 353-374 | T3 375-426 |
#               T4 427-546 | D1 547-646 | BL 647-766 | settle 767-772 | D2 backwards 773-872 | settle 873-878 |
#               hold 879-920 | focus 921-960 | hold 961-1080
# Chapters: 0-82 | 82-166 | 166-427 | 427-586 | 586-832 | 832-941 | 941-1011 | 1011-1081
hold K0p.png 0 60
fade K0p.png 0 K1.png 0 40
hold K1.png 0 18
fade K1.png 0 T2.mp4 0 6
clip T2.mp4 1 26
blur T2.mp4 27 46 T2.mp4 62 81 8 26
clip T2.mp4 82 120
clip T3.mp4 1 19
blur T3.mp4 20 34 C.mp4 0 14 8 26
clip C.mp4 15 105
blur C.mp4 106 120 T3.mp4 54 68 8 26
clip T3.mp4 69 120
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
