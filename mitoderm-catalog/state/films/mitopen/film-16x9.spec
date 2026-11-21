# MITOPEN, the desktop film, DRAFT built without paid clips: 24 fps, 819 frames = 34.1 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> mitopen-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitopen-film.mp4 mitopen-film-mobile.mp4 vertical-keys.json
# The device is never drawn by a model: the real cut-out photo of the pen is placed on a plate generated without any
# device (build-pen-frames.py). The clips dir holds:
#   K0.png, K1.png  the pen sharp on the towel / the examination sharp - one plate, the same pen in the same place
#   K2.png          the camera at the pen (zoom 2); the pen comes from the full-size photo
#   Zin.mp4         camera move, zoom 1 -> 2, 48 frames      (build-pen-frames.py ... sequence=1,2,48 size=1912x1080)
#   Zin24.mp4       camera move, zoom 1 -> 2.4, 54 frames    (sequence=1,2.4,54)
#   Zdrift.mp4      camera move, zoom 2.4 -> 2, 48 frames    (sequence=2.4,2,48)
#   BL3.mp4         inside the skin: the serum goes down the micro-channels - the accepted clip of the EXOSIGNAL HAIR
#                   film (job fca2ec74-2d23-470a-b024-52928a110613), reused; no device and no people in it
# To come after the Atlas top-up and the owner's ok on the look (question 27): a live clip of the examination in
# place of the held still K1.
# Film frames:  pen close 0-53 | camera back 54-101 | hold 102-113 | focus 114-153 | examination 154-219 |
#               focus back 220-249 | camera to the ring and the button 250-302 | hold 303-338 | drift 339-385 |
#               hold 386-409 | into the skin 410-441 | micro-channels 442-522 | back to the pen 523-554 |
#               hold 555-602 | camera back 603-650 | hold 651-686 | focus 687-722 | examination 723-818
# Chapters: 0-134 | 134-235 | 235-339 | 339-426 | 426-552 | 552-603 | 603-705 | 705-819
hold K2.png 0 54
clip Zin.mp4 0 47 1 rev
hold K0.png 0 12
fade K0.png 0 K1.png 0 40
hold K1.png 0 66
fade K1.png 0 K0.png 0 30
clip Zin24.mp4 1 53
hold Zin24.mp4 53 36
clip Zdrift.mp4 1 47
hold K2.png 0 24
blur K2.png 0 19 BL3.mp4 0 19 8 26
clip BL3.mp4 20 100
blur BL3.mp4 101 120 K2.png 0 19 8 26
hold K2.png 0 48
clip Zin.mp4 0 47 1 rev
hold K0.png 0 36
fade K0.png 0 K1.png 0 36
hold K1.png 0 96
