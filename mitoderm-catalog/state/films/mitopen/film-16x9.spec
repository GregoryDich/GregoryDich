# MITOPEN, the desktop film, version 3 - the page's own scenes with its own patient P2: 24 fps, 974 frames = 40.6 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> mitopen-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitopen-film.mp4 mitopen-film-mobile.mp4 vertical-keys.json
# The pen on the towel is never drawn by a model: the real cut-out photo is placed on a plate generated without any
# device (build-pen-frames.py). The clips dir holds:
#   K0.png, K1.png  the pen sharp on the towel / the examination sharp - one plate, the same pen in the same place
#   K2.png          the camera at the pen (zoom 2); the pen comes from the full-size photo
#   Zin.mp4, Zin24.mp4, Zdrift.mp4   free camera moves on the real pen (build-pen-frames.py, sequences 1,2,48 /
#                   1,2.4,54 / 2.4,2,48 at 1912x1080)
#   E.mp4   PAID, to shoot after the owner's ok on the sheet: the live examination, K1 -> K1 (ends where it starts)
#   D.mp4   PAID: the pen works on the cheek for two seconds, then the camera goes into the skin, K3e -> Y1
#   BL.mp4  PAID: the product goes down the micro-channels, Y1 -> Y2
# Until the three clips are shot the same file names hold free stand-ins made of the page's own stills: E is the
# still K1, D is a push-in on K3e that dissolves into Y1, BL is Y1 dissolving into Y2. The film can be assembled and
# checked, and the real clips only replace the files. With the real D: check where the camera starts to move before
# keeping the forwards-back-forwards turn at its frames 47/21.
# The owner's word of 21/11: "Mitopen - show microneedling". Version 2 (film-v2-16x9.spec, wire-v2.json) showed it
# with three clips borrowed from the EXOSIGNAL HAIR film (another patient, the scalp); here it is the page's own scene
# on the face of P2.
# Film frames:  pen close 0-53 | camera back 54-101 | hold 102-113 | focus 114-153 | examination 154-273 |
#               focus back 274-303 | camera to the ring and the button 304-356 | hold 357-392 |
#               soft focus to the treatment 393-424 | the pen works on the cheek 425-504 | into the skin 505-577 |
#               the product goes down the micro-channels 578-677 | back to the pen 678-709 | hold 710-757 |
#               camera back 758-805 | hold 806-841 | focus 842-877 | examination 878-973
# Chapters: 0-134 | 134-289 | 289-409 | 409-520 | 520-694 | 694-758 | 758-860 | 860-974
hold K2.png 0 54
clip Zin.mp4 0 47 1 rev
hold K0.png 0 12
fade K0.png 0 K1.png 0 40
clip E.mp4 1 120
fade E.mp4 120 K0.png 0 30
clip Zin24.mp4 1 53
hold Zin24.mp4 53 36
blur Zdrift.mp4 1 20 D.mp4 0 19 8 26
clip D.mp4 20 47
clip D.mp4 21 46 1 rev
clip D.mp4 22 120
clip BL.mp4 1 100
blur BL.mp4 101 120 K2.png 0 19 8 26
hold K2.png 0 48
clip Zin.mp4 0 47 1 rev
hold K0.png 0 36
fade K0.png 0 K1.png 0 36
hold K1.png 0 96
