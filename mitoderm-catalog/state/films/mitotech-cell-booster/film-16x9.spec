# MITOTECH CELL BOOSTER, the desktop film, version 2 (22/11): a clinic procedure with microneedling, 24 fps,
# 505 frames = 21.0 s, one chapter. Version 1 (clinic, then her home) is kept as film-v1-16x9.spec.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> mitotech-cell-booster-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitotech-cell-booster-film.mp4 mitotech-cell-booster-film-mobile.mp4 vertical-keys.json
# The clips dir holds:
#   T1.mp4  the real box in the clinic (C1) -> the same frame, focus on the two women (C2); Kling 4.0, 1080p, 21/11
#   W.mp4   the close-up K3m: clear drops from a needle-free syringe and the pen at work on the cheek
#   BL.mp4  inside the skin: Y1 -> Y2m, the clear solution goes down the micro-channels
# Until the owner says ok to the still sheet, W.mp4 and BL.mp4 are free stand-ins (a slow camera move on K3m; a
# dissolve from Y1 to Y2m); the two paid clips then replace the files without changing this plan.
# The camera enters the skin and leaves it through soft-focus joins, with no push-in on the face: the caption of this
# page is the large page title on the right, and a push-in would bring the face under it.
# Film frames:  hold 0-47 | T1 48-147 | soft focus 148-179 | W 180-260 | soft focus 261-292 | BL 293-373 |
#               soft focus 374-405 | T1 backwards x2 406-456 | hold 457-504
# Chapters: 0-505
hold T1.mp4 0 48
clip T1.mp4 1 100
blur T1.mp4 101 120 W.mp4 0 19 8 26
clip W.mp4 20 100
blur W.mp4 101 120 BL.mp4 0 19 8 26
clip BL.mp4 20 100
blur BL.mp4 101 120 T1.mp4 120 101 8 26
clip T1.mp4 0 100 2 rev
hold T1.mp4 0 48
