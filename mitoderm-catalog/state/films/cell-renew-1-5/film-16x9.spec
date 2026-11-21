# CELL RENEW 1.5%, the desktop film: one unbroken movement, 24 fps, 849 frames = 35.4 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> cell-renew-1-5-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py cell-renew-1-5-film.mp4 cell-renew-1-5-film-mobile.mp4 vertical-keys.json
# The clips dir holds the Kling 4.0 results from Atlas (1080p, 5 s = 121 frames) and the still frames:
#   H0.png, H1.png   the pack at home sharp / she at the mirror sharp - one plate, so the focus pull is a free dissolve
#   T2  the camera comes closer, the box leaves the frame, the massage begins (H1 -> H2)
#   D1  the massage, then into the skin of the cheek (H2 -> Yc)
#   D2  out of the skin: she is smoothing the cream (H3 -> Yc, played backwards)
#   T5  the camera pulls back, the box comes in and the focus settles on it. Only frames 1-81 are used: at frame 82
#       the clip jumps to the pose of its last still (a hidden cut). The last 12 frames are slowed to ease the stop.
#   E0.png  frame 81 of T5 with the real box render placed exactly over the box (at 137,207, height 856 in 1912x1080)
#   E1.png, E2.png  the clinic plate with the same box in the same place: box sharp / the two women sharp
# Film frames:  hold 0-59 | focus 60-99 | hold 100-111 | settle 112-117 | T2 118-237 | D1 238-358 | hold 359-394 |
#               D2 backwards 395-515 | T5 516-584 | T5 slowed 585-608 | settle 609-614 | hold 615-644 |
#               home -> clinic 645-692 | hold 693-716 | focus 717-752 | hold 753-848
# Chapters: 0-75 | 75-190 | 190-290 | 290-455 | 455-575 | 575-655 | 655-725 | 725-849
hold H0.png 0 60
fade H0.png 0 H1.png 0 40
hold H1.png 0 12
fade H1.png 0 T2.mp4 0 6
clip T2.mp4 1 120
clip D1.mp4 0 120
hold D1.mp4 120 36
clip D2.mp4 0 120 1 rev
clip T5.mp4 1 69
slow T5.mp4 70 81 2
fade T5.mp4 81 E0.png 0 6
hold E0.png 0 30
fade E0.png 0 E1.png 0 48
hold E1.png 0 24
fade E1.png 0 E2.png 0 36
hold E2.png 0 96
