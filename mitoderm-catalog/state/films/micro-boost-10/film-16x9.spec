# MICRO BOOST 10%, the desktop film: one unbroken movement, 24 fps, 1023 frames = 42.6 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> micro-boost-10-film.mp4 1280 720   (first version, 720p)
# Phone:  ../tools/vertical-from-horizontal.py micro-boost-10-film.mp4 micro-boost-10-film-mobile.mp4 vertical-keys.json
# The clips dir holds the Kling 4.0 results from Atlas (5 s = 121 frames), launched by ../tools/atlas-clips.py.
#   T1  pack in the room (K0) -> the same frame, focus on the skin examination (K1)
#   T2  the couch reclines, she lies down, the cheek is patted dry (K1 -> K2)
#   T3  the tissue goes, the fingertips start the massage (K2 -> K3)
#   T4  the hands lift, "does it tingle?" (K3 -> K4)
#   D1  into the skin of the cheek (K4 -> Y1), at double speed
#   BL  the next product goes down the open paths (Y1 -> Y2)
#   D2  out of the skin, the mask is on the face (K6 -> Y2, played backwards at double speed)
#   T7  focus from the people to the pack (K6 -> K7); then the last frame is held
# Film frames:  hold 0-59 | T1 60-179 | T2 180-299 | T3 300-419 | T4 420-539 | D1 540-600 | BL 601-721 |
#               D2 backwards 722-782 | T7 783-902 | hold 903-1022
# Chapters: 0-105 | 105-250 | 250-470 | 470-570 | 570-760 | 760-850 | 850-940 | 940-1023
hold T1.mp4 0 60
clip T1.mp4 1 120
clip T2.mp4 1 120
clip T3.mp4 1 120
clip T4.mp4 1 120
clip D1.mp4 0 120 2
clip BL.mp4 0 120
clip D2.mp4 0 120 2 rev
clip T7.mp4 1 120
hold T7.mp4 120 120
