# EXOSIGNAL HAIR, the desktop film (1912x1080): one unbroken movement, 24 fps, 1667 frames = 69.5 s.
# Version 2 (20/11, evening): the MITOSCAN screen, the look inside the skin and the follow-up scan were added.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> exosignal-hair-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py exosignal-hair-film.mp4 exosignal-hair-film-mobile.mp4 vertical-keys.json
#
# The clips dir holds the Kling 4.0 results (5 s = 121 frames, bridges 3 s = 73 frames), named as below.
# Higgsfield job ids (the files are fetched by job id, show_generation_by_ids):
#   T1.mp4   97ee21f4-4c7f-4e38-96ef-7b8b7d9d2b0d   pack (K0) -> consultation (K1)
#   T2.mp4   fc266e00-f5dc-47ee-a030-fdc64b0b8bd4   consultation (K1) -> MITOSCAN (K3)
#   S1.mp4   385c88b1-a1eb-4a34-b9b0-457855d46f1f   MITOSCAN (K3) -> the tablet screen, the probe on the parting (K3S3)
#   T3.mp4   76e565cf-bbc8-4214-b401-503ad17a53eb   MITOSCAN (K3) -> the ampoule (K4)
#   T4.mp4   a669e7d2-7c10-40d3-aefa-1c8e544e9af4   the ampoule (K4) -> MITOPEN (K5)
#   D1b.mp4  d1aa8cd1-5cda-45f5-9566-ff13c0486c65   MITOPEN (K5) -> dive into the parting -> the hair in a skin cut-away (Y1)
#   BL2.mp4  48c7b903-6aca-404e-a830-82a7a26cb719   the serum runs down the hair into the follicle to the bulb (Y1 -> Y2)
#   D2b.mp4  a13ffb4a-98ec-455f-a551-7d2d0182a77a   MITOPEN (K5) -> the cut-away with the serum inside (Y2); runs backwards
#   T5.mp4   cc6af771-f370-4956-99a7-af0e235cc80b   MITOPEN (K5) -> massage (K6)
#   B5.mp4   8fe451e4-05b7-4242-911c-639d4c6fbe9f   3 s bridge between T5 frames 86 and 87 (a hidden jump)
#   E1.mp4   b3ac80cc-c401-4ca1-bd55-cd595ac824d5   massage (K6) -> the window, out of focus (W): the weeks of the course
#   E2.mp4   d7092cc2-4951-4c1b-a2d9-ecb70d456727   the window (W) -> the follow-up scan, the tablet after the course (K9)
#   E3.mp4   0248dd08-84d2-4874-ba6a-f053ae89b7c2   the follow-up scan (K9) -> the end of the visit (K7)
#   T7c.mp4  e5348471-7e36-49c0-b83a-50b64624b4fd   the end pack (K0E) -> the end of the visit (K7); runs backwards
# Not from Kling: M1.mp4 and M2.mp4, 96 frames each, are held tablet shots with dashed circles drawn on the screen:
#   python3 marker-hold.py <S1 frame 120.png> <S1 frame 120.png> M1.mp4 96
#   python3 marker-hold.py <E2 frame 120.png> <E3 frame 0.png>  M2.mp4 96     (the base cross-fades from E2 to E3)
# Out of the film since version 2: T6 (805a35ef-b505-44cd-8d8a-941fada1eee8) and its bridge B6 (6176724c-...).
#
# T1 starts after its hidden jump (frame 25), so the film opens on a hold of T1 frame 25, not on the K0 still.
# The bridge, the camera moves to and from the tablet, both dives and the pen work after the dive play at double
# speed (every 2nd frame).
#
# Film frames:  hold 0-60 | T1 61-155 | T2 156-275 | S1 276-336 | M1 337-432 | S1 back 433-492 | T3 493-612 |
#               T4 613-732 | D1b 733-793 | BL2 794-914 | D2b back 915-975 | T5 976-1018 | B5 1019-1054 |
#               T5 1055-1088 | E1 1089-1209 | E2 1210-1270 | M2 1271-1366 | E3 1367-1486 | T7c back 1487-1606 |
#               hold 1607-1666
hold T1.mp4 25 61
clip T1.mp4 26 120
clip T2.mp4 1 120
clip S1.mp4 0 120 2
clip M1.mp4 0 95
clip S1.mp4 0 118 2 rev
clip T3.mp4 1 120
clip T4.mp4 1 120
clip D1b.mp4 0 120 2
clip BL2.mp4 0 120
clip D2b.mp4 0 120 2 rev
clip T5.mp4 1 86 2
clip B5.mp4 1 71 2
clip T5.mp4 87 120
clip E1.mp4 0 120
clip E2.mp4 0 120 2
clip M2.mp4 0 95
clip E3.mp4 1 120
clip T7c.mp4 0 119 1 rev
hold T7c.mp4 0 60
