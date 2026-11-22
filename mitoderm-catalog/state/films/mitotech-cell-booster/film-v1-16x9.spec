# MITOTECH CELL BOOSTER, the desktop film: clinic, then her home, 24 fps, 468 frames = 19.5 s, one chapter.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> mitotech-cell-booster-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitotech-cell-booster-film.mp4 mitotech-cell-booster-film-mobile.mp4 vertical-keys.json
# The clips dir holds T1.mp4 (Kling 4.0 from Atlas, 1080p, 121 frames) and the stills C1.png, H0.png, H1.png
# (the real box placed by ../tools/place-pack.py, the same place in all of them).
#   T1  the real box in the clinic (C1) -> the same frame, focus on the treatment (C2); then backwards
#   --  free dissolve: the box stays, the clinic behind it becomes her home (C1 -> H0): the protocol gives the rest
#       of the solution to the client for home use, and the kit is an 8-week home programme
#   --  free focus pull at home (H0 -> H1 -> H0): both frames are one plate, so a dissolve is a true focus change
# Film frames:  hold 0-47 | T1 48-167 | hold 168-191 | T1 backwards x2 192-251 | settle 252-259 | dissolve 260-299 |
#               hold 300-323 | focus 324-353 | hold 354-389 | focus back 390-419 | hold 420-467
# Chapters: 0-468
hold T1.mp4 0 48
clip T1.mp4 1 120
hold T1.mp4 120 24
clip T1.mp4 1 119 2 rev
fade T1.mp4 0 C1.png 0 8
fade C1.png 0 H0.png 0 40
hold H0.png 0 24
fade H0.png 0 H1.png 0 30
hold H1.png 0 36
fade H1.png 0 H0.png 0 30
hold H0.png 0 48
