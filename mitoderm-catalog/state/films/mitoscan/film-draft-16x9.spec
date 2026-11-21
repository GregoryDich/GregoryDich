# MITOSCAN, the desktop film, DRAFT built without any new shooting: 24 fps, 801 frames = 33.4 s.
# Build:  ../tools/film-assemble.sh film-draft-16x9.spec <clips dir> mitoscan-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitoscan-film.mp4 mitoscan-film-mobile.mp4 vertical-keys-draft.json
# The page cannot be shot yet: the only real photo of the system is 340x288 px and there are no real screen
# captures as files (STORYBOARD.md, "what is missing"). Until they arrive the page shows the diagnosis as it was
# shot for the EXOSIGNAL HAIR film, which the owner accepted on 21/11: the same room and cosmetologist, the patient
# of the hair page. The clips dir is the clips of that film (jobs in state/films/exosignal-hair/film-16x9.spec):
#   S1b  she points at the screen with the scan; used from frame 66 (a hidden jump before it)
#   T2   the consultation, then the probe goes onto the parting
#   S1c  the screen with the scan comes into the foreground
#   E2b  the window, then the follow-up scan: the same area after the course
#   E3b  the end of the visit; BE3 is a six-frame bridge over a small pop between its frames 40 and 41
# The owner's word of 21/11: MITOSCAN is a clinic procedure; the page was the only one without a film.
# Film frames:  the screen 0-59 | soft focus 60-91 | the consultation and the probe 92-191 | the screen comes
#               forward 192-312 | she points at the screen 313-367 | hold 368-397 | soft focus: weeks pass 398-429 |
#               the follow-up scan 430-530 | hold 531-602 | the end of the visit 603-728 | hold 729-800
# Chapters: 0-76 | 76-145 | 145-313 | 313-414 | 414-545 | 545-603 | 603-700 | 700-801
hold S1b.mp4 120 60
blur S1b.mp4 120 101 T2.mp4 1 20 8 26
clip T2.mp4 21 120
clip S1c.mp4 0 120
clip S1b.mp4 66 120
hold S1b.mp4 120 30
blur S1b.mp4 120 101 E2b.mp4 0 19 8 26
clip E2b.mp4 20 120
hold E2b.mp4 120 72
clip E3b.mp4 1 40
clip BE3.mp4 6 66 12
clip E3b.mp4 41 120
hold E3b.mp4 120 72
