# MITOPEN, the desktop film, VERSION 2 (superseded on 22/11 by film-16x9.spec; kept for a quick way back):
# a draft built without paid clips, 24 fps, 887 frames = 37.0 s.
# Build:  ../tools/film-assemble.sh film-v2-16x9.spec <clips dir> mitopen-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py mitopen-film.mp4 mitopen-film-mobile.mp4 vertical-keys-v2.json
# The device is never drawn by a model: the real cut-out photo of the pen is placed on a plate generated without any
# device (build-pen-frames.py). The clips dir holds:
#   K0.png, K1.png  the pen sharp on the towel / the examination sharp - one plate, the same pen in the same place
#   K2.png          the camera at the pen (zoom 2); the pen comes from the full-size photo
#   Zin.mp4         camera move, zoom 1 -> 2, 48 frames      (build-pen-frames.py ... sequence=1,2,48 size=1912x1080)
#   Zin24.mp4       camera move, zoom 1 -> 2.4, 54 frames    (sequence=1,2.4,54)
#   Zdrift.mp4      camera move, zoom 2.4 -> 2, 48 frames    (sequence=2.4,2,48)
#   T5b.mp4, D1c.mp4, BL3.mp4   the microneedling itself and the look inside the skin - the accepted clips of the
#                   EXOSIGNAL HAIR film, reused: the pen works along the parting with the serum from a syringe
#                   (T5b, job c0ef5c26-4cb3-49fa-b7ed-e111ab856799, frames 1-40 forwards and back - the rest has a
#                   hidden jump), the camera dives into the parting to the cut-away (D1c, job
#                   68fd28ef-1c98-4737-97ca-34a6f8a0c4d2), the serum goes down the micro-channels (BL3, job
#                   fca2ec74-2d23-470a-b024-52928a110613). The owner's word of 21/11: "Mitopen - show microneedling".
#                   The patient in these clips is the one of the hair page, not P2.
# To come after the Atlas top-up and the owner's ok on the look (question 27): the page's own microneedling scene with
# P2 and a live clip of the examination in place of the held still K1.
# Film frames:  pen close 0-53 | camera back 54-101 | hold 102-113 | focus 114-153 | examination 154-219 |
#               focus back 220-249 | camera to the ring and the button 250-302 | hold 303-338 |
#               soft focus to the treatment 339-370 | the pen works along the parting 371-429 |
#               into the skin 430-490 | micro-channels 491-590 | back to the pen 591-622 | hold 623-670 |
#               camera back 671-718 | hold 719-754 | focus 755-790 | examination 791-886
# Chapters: 0-134 | 134-235 | 235-355 | 355-430 | 430-607 | 607-671 | 671-773 | 773-887
hold K2.png 0 54
clip Zin.mp4 0 47 1 rev
hold K0.png 0 12
fade K0.png 0 K1.png 0 40
hold K1.png 0 66
fade K1.png 0 K0.png 0 30
clip Zin24.mp4 1 53
hold Zin24.mp4 53 36
blur Zdrift.mp4 1 20 T5b.mp4 1 20 8 26
clip T5b.mp4 21 40
clip T5b.mp4 1 39 1 rev
clip D1c.mp4 0 120 2
clip BL3.mp4 1 100
blur BL3.mp4 101 120 K2.png 0 19 8 26
hold K2.png 0 48
clip Zin.mp4 0 47 1 rev
hold K0.png 0 36
fade K0.png 0 K1.png 0 36
hold K1.png 0 96
