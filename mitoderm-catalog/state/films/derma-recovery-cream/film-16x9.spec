# DERMA RECOVERY CREAM, the desktop film: clinic -> home -> clinic in one unbroken movement, 24 fps.
# BUILT on 22/11 from the three clips shot that night (jobs in requests.json). The pieces repeat the finished film
# of CELLULAR AGE DEFENSE 2.5%; D1 is inside the skin from its frame 72 and D2 from its frame 68, so the two
# "twice as fast" tails and the chapter borders stay as planned.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> derma-recovery-cream-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py derma-recovery-cream-film.mp4 derma-recovery-cream-film-mobile.mp4 vertical-keys.json
# The clips dir holds the Kling 4.0 results from Atlas (1080p, 5 s = 121 frames) and the still frames:
#   C1.png, C2.png  the pack in the clinic sharp / the cream after the treatment sharp - one plate, the real box in one
#                   place, so the focus pulls are free dissolves
#   H0.png, H1.png  the same box at her home in the morning sharp / she at the mirror sharp - the box stands where it
#                   stands in C1, so clinic -> home is a free dissolve with the box unmoving
#   T3  the camera comes closer, the box leaves the frame, she applies the cream (H1 -> H2)
#   D1  the cream, then into the skin of the cheek (H2 -> Ye)
#   D2  out of the skin: the cream is absorbed, she smiles (H3 -> Ye, played backwards)
#   H3.png  the last home scene (the first frame of D2), held for a moment before the focus leaves it
#   The pull-back to the pack is not shot (a clip of that kind gets a hidden cut): the scene goes out of focus and the
#   pack frame H0 comes into focus (piece "blur").
# Film frames: hold 0-59 | focus 60-99 | hold 100-135 | focus back 136-165 | clinic -> home 166-213 |
#               hold 214-237 | focus 238-277 | hold 278-289 | settle 290-295 | T3 296-415 | D1 416-520 | hold 521-544 |
#               settle 545-550 | D2 backwards 551-655 | settle 656-661 | hold 662-673 | soft focus to the pack 674-705 |
#               hold 706-735 | home -> clinic 736-783 | hold 784-807 | focus 808-843 | hold 844-939
# Chapters: 0-80 | 80-190 | 190-462 | 462-596 | 596-690 | 690-760 | 760-826 | 826-940
# Captions in film order: page sections 1, 2, 5, 3, 4, 6, 7, 8 (STORYBOARD.md).
hold C1.png 0 60
fade C1.png 0 C2.png 0 40
hold C2.png 0 36
fade C2.png 0 C1.png 0 30
fade C1.png 0 H0.png 0 48
hold H0.png 0 24
fade H0.png 0 H1.png 0 40
hold H1.png 0 12
fade H1.png 0 T3.mp4 0 6
clip T3.mp4 1 120
clip D1.mp4 1 90
clip D1.mp4 92 120 2
hold D1.mp4 120 24
fade D1.mp4 120 D2.mp4 120 6
clip D2.mp4 90 119 2 rev
clip D2.mp4 0 89 1 rev
fade D2.mp4 0 H3.png 0 6
hold H3.png 0 12
blur H3.png 0 19 H0.png 0 19 8 26
hold H0.png 0 30
fade H0.png 0 C1.png 0 48
hold C1.png 0 24
fade C1.png 0 C2.png 0 36
hold C2.png 0 96
