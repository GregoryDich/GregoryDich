# CELL RENEW 1.5%, the desktop film: one unbroken movement, 24 fps, 1022 frames = 42.6 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> cell-renew-1-5-film.mp4 1280 720   (first version, 720p)
# Phone:  ../tools/vertical-from-horizontal.py cell-renew-1-5-film.mp4 cell-renew-1-5-film-mobile.mp4 vertical-keys.json
# The clips dir holds the Kling 4.0 results from Atlas (5 s = 121 frames), launched by ../tools/atlas-clips.py.
#   T1  the pack at home (H0) -> the same frame, focus on her at the mirror (H1)
#   T2  the camera comes closer, the box leaves the frame, the massage begins (H1 -> H2)
#   D1  the massage, then into the skin of the cheek (H2 -> Yc)
#   D2  out of the skin: she is smoothing the cream (H3 -> Yc, played backwards)
#   T5  the camera pulls back, the focus returns to the pack (H3 -> H0)
#   --  free dissolve: the pack stays, the home behind it becomes the clinic (H0 -> C1)
#   T7  focus from the pack to the cosmetologist and the patient (C1 -> C2); then the last frame is held
# Film frames:  hold 0-59 | T1 60-179 | T2 180-299 | D1 300-420 | hold 421-456 | D2 backwards 457-577 |
#               T5 578-697 | hold 698-733 | dissolve 734-781 | hold 782-805 | T7 806-925 | hold 926-1021
# Chapters: 0-110 | 110-250 | 250-380 | 380-520 | 520-640 | 640-745 | 745-850 | 850-1022
hold T1.mp4 0 60
clip T1.mp4 1 120
clip T2.mp4 1 120
clip D1.mp4 0 120
hold D1.mp4 120 36
clip D2.mp4 0 120 1 rev
clip T5.mp4 1 120
hold T5.mp4 120 36
fade T5.mp4 120 T7.mp4 0 48
hold T7.mp4 0 24
clip T7.mp4 1 120
hold T7.mp4 120 96
