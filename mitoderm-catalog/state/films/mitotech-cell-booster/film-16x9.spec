# MITOTECH CELL BOOSTER, the desktop film: one short movement, 24 fps, 432 frames = 18 s, one chapter.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> mitotech-cell-booster-film.mp4 1280 720   (first version, 720p)
# Phone:  ../tools/vertical-from-horizontal.py mitotech-cell-booster-film.mp4 mitotech-cell-booster-film-mobile.mp4 vertical-keys.json
#   T1  the real box in the clinic (C1) -> the same frame, focus on the treatment (C2); then backwards
# Film frames:  hold 0-59 | T1 60-179 | hold 180-251 | T1 backwards 252-371 | hold 372-431
# Chapters: 0-432
hold T1.mp4 0 60
clip T1.mp4 1 120
hold T1.mp4 120 72
clip T1.mp4 1 120 1 rev
hold T1.mp4 0 60
