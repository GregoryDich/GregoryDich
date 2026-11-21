# DERMA RECOVERY CREAM, the desktop film, DRAFT built without paid clips: 24 fps, 881 frames = 36.7 s.
# Build:  ../tools/film-assemble.sh film-draft-16x9.spec <clips dir> derma-recovery-cream-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py derma-recovery-cream-film.mp4 derma-recovery-cream-film-mobile.mp4 vertical-keys-draft.json
# The Atlas balance is spent, so the three clips of film-16x9.spec are not shot yet. This draft stands on the page
# until then: every frame is an approved still, the camera moves are enlargements of the stills (../tools/still-zoom.sh)
# and the scenes are joined by soft focus (piece "blur"). The people do not move in it. The clips dir holds:
#   C1.png, C2.png, H0.png, H1.png, H3.png   the stills (the real box in one place in the first four)
#   ZH1.mp4   still-zoom.sh H1.png ZH1.mp4 48 1.00 1.08 0.48 0.36    a slow push toward her at the mirror
#   ZH2.mp4   still-zoom.sh H2.png ZH2.mp4 110 1.04 1.55 0.45 0.44   the cream; the camera moves in toward the cheek
#   ZYe.mp4   still-zoom.sh Ye.png ZYe.mp4 96 1.00 1.08 0.30 0.45    inside the skin, a slow drift
#   ZH3.mp4   still-zoom.sh H3.png ZH3.mp4 96 1.50 1.00 0.45 0.44    the camera pulls back: the cream is absorbed
# Film frames:  hold 0-59 | focus 60-99 | hold 100-135 | focus back 136-165 | clinic -> home 166-213 | hold 214-237 |
#               focus 238-277 | push 278-304 | soft focus 305-336 | the cream 337-406 | into the skin 407-438 |
#               inside 439-494 | out 495-526 | pull-back 527-602 | hold 603-614 | soft focus to the pack 615-646 |
#               hold 647-676 | home -> clinic 677-724 | hold 725-748 | focus 749-784 | hold 785-880
# Chapters: 0-80 | 80-190 | 190-422 | 422-510 | 510-630 | 630-700 | 700-767 | 767-881
# Captions in film order: page sections 1, 2, 5, 3, 4, 6, 7, 8 (STORYBOARD.md).
hold C1.png 0 60
fade C1.png 0 C2.png 0 40
hold C2.png 0 36
fade C2.png 0 C1.png 0 30
fade C1.png 0 H0.png 0 48
hold H0.png 0 24
fade H0.png 0 H1.png 0 40
clip ZH1.mp4 1 27
blur ZH1.mp4 28 47 ZH2.mp4 0 19 8 26
clip ZH2.mp4 20 89
blur ZH2.mp4 90 109 ZYe.mp4 0 19 8 26
clip ZYe.mp4 20 75
blur ZYe.mp4 76 95 ZH3.mp4 0 19 8 26
clip ZH3.mp4 20 95
hold H3.png 0 12
blur H3.png 0 19 H0.png 0 19 8 26
hold H0.png 0 30
fade H0.png 0 C1.png 0 48
hold C1.png 0 24
fade C1.png 0 C2.png 0 36
hold C2.png 0 96
