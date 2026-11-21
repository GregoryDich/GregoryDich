# CELLULAR AGE DEFENSE 2.5%, the desktop film: one unbroken movement, 24 fps, 1274 frames = 53.1 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> cellular-age-defense-2-5-film.mp4 1280 720   (first version, 720p)
# Phone:  ../tools/vertical-from-horizontal.py cellular-age-defense-2-5-film.mp4 cellular-age-defense-2-5-film-mobile.mp4 vertical-keys.json
# The clips dir holds the Kling 4.0 results from Atlas (5 s = 121 frames), launched by ../tools/atlas-clips.py.
#   T1  the pack in the clinic (C1) -> the same frame, focus on the skin examination (C2); also backwards and once more at the end
#   --  free dissolve: the pack stays, the clinic behind it becomes her home in the evening (C1 -> H0)
#   T2  focus from the pack to her at the mirror (H0 -> H1)
#   T3  the camera comes closer, the box leaves the frame, the massage begins (H1 -> H2)
#   D1  the massage, then into the skin of the cheek (H2 -> Yd)
#   D2  out of the skin: she is smoothing the cream (H3 -> Yd, played backwards)
#   T5  the camera pulls back, the focus returns to the pack (H3 -> H0)
#   --  free dissolve: the home becomes the clinic again (H0 -> C1)
# Film frames:  hold 0-59 | T1 60-179 | T1 backwards x2 180-239 | dissolve 240-287 | hold 288-311 | T2 312-431 |
#               T3 432-551 | D1 552-672 | hold 673-708 | D2 backwards 709-829 | T5 830-949 | hold 950-985 |
#               dissolve 986-1033 | hold 1034-1057 | T1 1058-1177 | hold 1178-1273
# Chapters: 0-105 | 105-265 | 265-640 | 640-770 | 770-890 | 890-1000 | 1000-1110 | 1110-1274
hold T1.mp4 0 60
clip T1.mp4 1 120
clip T1.mp4 0 118 2 rev
fade T1.mp4 0 T2.mp4 0 48
hold T2.mp4 0 24
clip T2.mp4 1 120
clip T3.mp4 1 120
clip D1.mp4 0 120
hold D1.mp4 120 36
clip D2.mp4 0 120 1 rev
clip T5.mp4 1 120
hold T5.mp4 120 36
fade T5.mp4 120 T1.mp4 0 48
hold T1.mp4 0 24
clip T1.mp4 1 120
hold T1.mp4 120 96
