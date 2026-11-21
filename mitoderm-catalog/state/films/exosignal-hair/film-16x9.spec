# EXOSIGNAL HAIR, the desktop film (1912x1080): one unbroken movement, 24 fps, 1638 frames = 68.3 s.
# Version 3 (21/11): by the owner's words of 20/11 the treatment follows his real technique (the pen held at a
# slant like a pencil, a syringe in the other hand), the MITOSCAN screen has its real look with a pointing finger
# and no drawn marks, and the look inside the skin shows micro-channels with the serum spreading from them.
# Version 2 (1667 frames, with the drawn holds M1 and M2) is in git history.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> exosignal-hair-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py exosignal-hair-film.mp4 exosignal-hair-film-mobile.mp4 vertical-keys.json
#
# The clips dir holds the Kling 4.0 results (5 s = 121 frames, the bridge 3 s = 73 frames), named as below.
# Higgsfield job ids (the files are fetched by job id, show_generation_by_ids):
#   T1.mp4   97ee21f4-4c7f-4e38-96ef-7b8b7d9d2b0d   pack (K0) -> consultation (K1)
#   T2.mp4   fc266e00-f5dc-47ee-a030-fdc64b0b8bd4   consultation (K1) -> MITOSCAN (K3)
#   S1c.mp4  e6de4b40-5d19-4f78-a794-ea9172c380ce   MITOSCAN (K3) -> the tablet in the foreground (S1b frame 66)
#   S1b.mp4  bc70d306-9ad6-4ed9-8ade-926dd9134f08   used from frame 66: she points at the screen (K3Sn);
#                                                   frames 0-65 are out (a hidden jump between 65 and 66)
#   T3.mp4   76e565cf-bbc8-4214-b401-503ad17a53eb   MITOSCAN (K3) -> the ampoule (K4)
#   T4b.mp4  fce1b404-789a-4de6-8ce1-a6a57d6947bf   the ampoule (K4) -> the treatment: pen and syringe (K5n)
#   T5b.mp4  c0ef5c26-4cb3-49fa-b7ed-e111ab856799   used frames 1-40 forwards and back: the pen works along the
#                                                   parting; the rest is out (a hidden jump between 69 and 70)
#   D1c.mp4  68fd28ef-1c98-4737-97ca-34a6f8a0c4d2   the treatment (K5n) -> dive into the parting -> the cut-away (Y1n)
#   BL3.mp4  fca2ec74-2d23-470a-b024-52928a110613   the serum sinks into the micro-channels and spreads (Y1n -> Y2m)
#   D2x.mp4  1f9b93b5-a5d7-4317-9559-2bf5d61c2036   massage (K6) -> the cut-away with the serum (Y2m); runs backwards,
#                                                   so the film comes out of the skin straight onto the massage
#   E1.mp4   b3ac80cc-c401-4ca1-bd55-cd595ac824d5   massage (K6) -> the window, out of focus (W): the weeks of the course
#   E2b.mp4  68958e7c-dcad-4947-94d6-f03dc84b4e1a   the window (W) -> the follow-up scan, the screen after the course (K9n)
#   E3b.mp4  5197724a-0839-4b8a-bdc0-5c7367f1a6fa   the follow-up scan (K9n) -> the end of the visit (K7)
#   BE3.mp4  d6876543-935e-4b20-96e7-e72596076c11   3 s bridge between E3b frames 40 and 41 (a small pop); six frames used
#   T7c.mp4  e5348471-7e36-49c0-b83a-50b64624b4fd   the end pack (K0E) -> the end of the visit (K7); runs backwards
# Shot for version 3 and left out: D2c (56af9518-..., the treatment -> the cut-away), the bridges B5b (6ba0799a-...)
# and BS1 (424071fb-...), each with a hidden jump of its own.
# Out of the film since version 3: S1, M1, T4, D1b, BL2, D2b, T5, B5, E2, M2, E3 and marker-hold.py.
#
# T1 starts after its hidden jump (frame 25), so the film opens on a hold of T1 frame 25, not on the K0 still.
# Double speed (every 2nd frame): the camera move to the tablet and back, both dives.
#
# Film frames:  hold 0-60 | T1 61-155 | T2 156-275 | S1c 276-336 | S1b 337-391 | hold 392-404 | S1b back 405-432 |
#               S1c back 433-492 | T3 493-612 | T4b 613-732 | T5b 733-772 | T5b back 773-811 | D1c 812-872 |
#               BL3 873-993 | D2x back 994-1054 | E1 1055-1174 | E2b 1175-1295 | hold 1296-1331 | E3b 1332-1371 |
#               BE3 1372-1377 | E3b 1378-1457 | T7c back 1458-1577 | hold 1578-1637
hold T1.mp4 25 61
clip T1.mp4 26 120
clip T2.mp4 1 120
clip S1c.mp4 0 120 2
clip S1b.mp4 66 120
hold S1b.mp4 120 13
clip S1b.mp4 66 120 2 rev
clip S1c.mp4 0 118 2 rev
clip T3.mp4 1 120
clip T4b.mp4 1 120
clip T5b.mp4 1 40
clip T5b.mp4 1 39 1 rev
clip D1c.mp4 0 120 2
clip BL3.mp4 0 120
clip D2x.mp4 0 120 2 rev
clip E1.mp4 1 120
clip E2b.mp4 0 120
hold E2b.mp4 120 36
clip E3b.mp4 1 40
clip BE3.mp4 6 66 12
clip E3b.mp4 41 120
clip T7c.mp4 0 119 1 rev
hold T7c.mp4 0 60
