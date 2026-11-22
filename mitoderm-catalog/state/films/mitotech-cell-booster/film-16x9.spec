# MITOTECH CELL BOOSTER, the desktop film, version 3 (22/11): the kit opens. 24 fps, 654 frames = 27.3 s, one chapter.
# Version 2 (no opening) is kept as film-v2-16x9.spec, version 1 (clinic, then her home) as film-v1-16x9.spec.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> mitotech-cell-booster-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitotech-cell-booster-film.mp4 mitotech-cell-booster-film-mobile.mp4 vertical-keys.json
# The clips dir holds:
#   T1.mp4  the real box in the clinic (C1) -> the same frame, focus on the two women (C2); Kling 4.0, 1080p, 21/11
#   O.mp4   the kit opens, as on the owner's example of 22/11: an exact 3D model built from his print files and
#           rendered here (kit3d.py ... clip=121 holdin=24; no paid generation). Frames 0-23 the closed box,
#           24-98 the lid goes back on its ribbon, 99-120 the open kit
#   W.mp4   the close-up K3m: clear drops from a needle-free syringe and the pen at work on the cheek
#   BL.mp4  inside the skin: Y1 -> Y2m, the clear solution goes down the micro-channels
# The order is the protocol's: clean skin and the examination, the booster is prepared (the kit), the drops with
# the pen, the solution in the skin. The scenes meet in soft focus; the open kit is held so it can be looked at.
# Film frames:  hold 0-47 | T1 48-147 | soft focus 148-179 | O 180-260 | the open kit held 261-296 |
#               soft focus 297-328 | W 329-409 | soft focus 410-441 | BL 442-522 | soft focus 523-554 |
#               T1 backwards x2 555-605 | hold 606-653
# Chapters: 0-654
hold T1.mp4 0 48
clip T1.mp4 1 100
blur T1.mp4 101 120 O.mp4 0 19 8 26
clip O.mp4 20 100
hold O.mp4 100 36
blur O.mp4 101 120 W.mp4 0 19 8 26
clip W.mp4 20 100
blur W.mp4 101 120 BL.mp4 0 19 8 26
clip BL.mp4 20 100
blur BL.mp4 101 120 T1.mp4 120 101 8 26
clip T1.mp4 0 100 2 rev
hold T1.mp4 0 48
