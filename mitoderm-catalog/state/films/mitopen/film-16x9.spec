# MITOPEN, the desktop film, version 3 - the page's own scenes with its own patient P2: 24 fps, 952 frames = 39.7 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> mitopen-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitopen-film.mp4 mitopen-film-mobile.mp4 vertical-keys.json
# The pen on the towel is never drawn by a model: the real cut-out photo is placed on a plate generated without any
# device (build-pen-frames.py). The clips dir holds:
#   K0.png, K1.png  the pen sharp on the towel / the examination sharp - one plate, the same pen in the same place
#   K2.png          the camera at the pen (zoom 2); the pen comes from the full-size photo
#   Zin.mp4, Zin24.mp4, Zdrift.mp4   free camera moves on the real pen (build-pen-frames.py, sequences 1,2,48 /
#                   1,2.4,54 / 2.4,2,48 at 1912x1080)
#   E.mp4   the live examination, K1 -> K1 (ends where it starts) - job 0cdacfbe45db4cc28cd86c070c9dac6a
#   D.mp4   the pen works on the cheek, then the camera goes into the skin, K3e -> Y1 - job
#           b8bdc295dc1d44beab428809c3e9ad82. The camera drifts slowly from the first frame and pushes in from about
#           frame 50, so the work is not played forwards and back (the drift would reverse): frames 20-49 are shown
#           twice each (piece "slow" - on a scrolled film that is simply a longer look), then the dive plays as shot
#   BL.mp4  the product goes down the micro-channels, Y1 -> Y2 - job 57aa8f6291874b5c9907634cf1b1a374
# Shot on 22/11 after the owner's ok on the still sheet (three Kling 4.0 clips, 1080p, 5 s, 1.07 USD each); no
# retakes. rebuild-clips.sh makes free stand-ins for these three files only where a file is missing.
# The owner's word of 21/11: "Mitopen - show microneedling". Version 2 (film-v2-16x9.spec, wire-v2.json) showed it
# with three clips borrowed from the EXOSIGNAL HAIR film (another patient, the scalp); here it is the page's own scene
# on the face of P2.
# Film frames:  pen close 0-53 | camera back 54-101 | hold 102-113 | focus 114-153 | examination 154-273 |
#               focus back 274-303 | camera to the ring and the button 304-356 | hold 357-392 |
#               soft focus to the treatment 393-424 | the pen works on the cheek 425-484 | into the skin 485-555 |
#               the product goes down the micro-channels 556-655 | back to the pen 656-687 | hold 688-735 |
#               camera back 736-783 | hold 784-819 | focus 820-855 | examination 856-951
# Chapters: 0-134 | 134-289 | 289-409 | 409-505 | 505-672 | 672-736 | 736-838 | 838-952
hold K2.png 0 54
clip Zin.mp4 0 47 1 rev
hold K0.png 0 12
fade K0.png 0 K1.png 0 40
clip E.mp4 1 120
fade E.mp4 120 K0.png 0 30
clip Zin24.mp4 1 53
hold Zin24.mp4 53 36
blur Zdrift.mp4 1 20 D.mp4 0 19 8 26
slow D.mp4 20 49 2
clip D.mp4 50 120
clip BL.mp4 1 100
blur BL.mp4 101 120 K2.png 0 19 8 26
hold K2.png 0 48
clip Zin.mp4 0 47 1 rev
hold K0.png 0 36
fade K0.png 0 K1.png 0 36
hold K1.png 0 96
