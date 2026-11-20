# EXOSIGNAL HAIR, the desktop film (1912x1080): one unbroken movement, 24 fps, 1008 frames = 42 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> exosignal-hair-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py exosignal-hair-film.mp4 exosignal-hair-film-mobile.mp4 vertical-keys.json
#
# The clips dir holds the Kling 4.0 results (5 s = 121 frames, bridges 3 s = 73 frames), named as below.
# Higgsfield job ids (the files are fetched by job id, show_generation_by_ids):
#   T1.mp4   97ee21f4-4c7f-4e38-96ef-7b8b7d9d2b0d   pack (K0) -> consultation (K1)
#   T2.mp4   fc266e00-f5dc-47ee-a030-fdc64b0b8bd4   consultation (K1) -> MITOSCAN (K3)
#   T3.mp4   76e565cf-bbc8-4214-b401-503ad17a53eb   MITOSCAN (K3) -> the ampoule (K4)
#   T4.mp4   a669e7d2-7c10-40d3-aefa-1c8e544e9af4   the ampoule (K4) -> MITOPEN (K5)
#   T5.mp4   cc6af771-f370-4956-99a7-af0e235cc80b   MITOPEN (K5) -> massage (K6)
#   B5.mp4   8fe451e4-05b7-4242-911c-639d4c6fbe9f   3 s bridge between T5 frames 86 and 87 (a hidden jump)
#   T6.mp4   805a35ef-b505-44cd-8d8a-941fada1eee8   massage (K6) -> the end of the visit (K7)
#   B6.mp4   6176724c-f053-4374-9072-621dedc7fa4d   3 s bridge between T6 frames 61 and 62 (a hidden jump)
#   T7c.mp4  e5348471-7e36-49c0-b83a-50b64624b4fd   the end pack (K0E) -> the end of the visit (K7); runs backwards
#
# T1 starts after its hidden jump (frame 25), so the film opens on a hold of T1 frame 25, not on the K0 still.
# The bridges play at double speed (every 2nd frame): 36 film frames each instead of a one-frame jump.
#
# Film frames:  hold 0-60 | T1 61-155 | T2 156-275 | T3 276-395 | T4 396-515 | T5 516-601 | B5 602-637 |
#               T5 638-671 | T6 672-732 | B6 733-768 | T6 769-827 | T7c backwards 828-947 | hold 948-1007
# Chapters (pilot/product-films.ts): 0-91 | 91-219 | 219-320 | 320-450 | 450-625 | 625-745 | 745-891 | 891-1008
hold T1.mp4 25 61
clip T1.mp4 26 120
clip T2.mp4 1 120
clip T3.mp4 1 120
clip T4.mp4 1 120
clip T5.mp4 1 86
clip B5.mp4 1 71 2
clip T5.mp4 87 120
clip T6.mp4 1 61
clip B6.mp4 1 71 2
clip T6.mp4 62 120
clip T7c.mp4 0 119 1 rev
hold T7c.mp4 0 60
