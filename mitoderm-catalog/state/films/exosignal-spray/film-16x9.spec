# EXOSIGNAL SPRAY, the desktop film (1912x1080): one unbroken movement, 24 fps, 1148 frames = 47.8 s.
# Build:  ../tools/film-assemble.sh film-16x9.spec <clips dir> exosignal-spray-film.mp4 1912 1080
# Phone:  ../tools/vertical-from-horizontal.py exosignal-spray-film.mp4 exosignal-spray-film-mobile.mp4 vertical-keys.json
#
# The clips dir holds the Kling 4.0 results (5 s = 121 frames), named as below.
# Higgsfield job ids (the files are fetched by job id, show_generation_by_ids):
#   T1b.mp4  2b670ed8-44a9-495d-8409-fda133091a23   pack in the clinic (K0b) -> the same frame, focus on the people (K0f)
#   T2b.mp4  9e9a24a9-8262-4e4d-ac37-c69cb5d70ef8   she hands him the bottle, the camera moves in on it (K0f -> K3b)
#   T3.mp4   19ca4d2d-4305-4dff-84f6-ac7d98dc588b   the bottle in his hand stays, the clinic behind it becomes his home (K3b -> K3h)
#   T4.mp4   712a2d6d-84a0-4f99-bc56-84efe303a262   home: the camera pulls back, he shakes the bottle and parts his hair (K3h -> K4)
#   T5.mp4   5c4e7ae8-6461-4430-855f-ab2ac532d138   he sprays the parted line of scalp (K4 -> K5)
#   T6.mp4   a526b50f-a6b5-41fd-84d6-b05393a399f0   he sets the bottle down and massages his scalp (K5 -> K6)
#   T7.mp4   be6ba638-a36d-4f3f-9e3a-098eb7c9fd29   focus from him to the pack on the bathroom counter (K6 -> K7b)
#   T8.mp4   530c7e97-af2a-4e79-9442-d41be526ef81   the pack stays, the home behind it becomes the clinic again (K7b -> K0b)
#   T9.mp4   5b62bf39-7bfd-4887-8048-8285ef23b86e   follow-up visit: focus from the pack to the people (K0b -> K0g); then backwards
#
# The two background changes are the idea of this page: the product is what links the clinic and the home.
# T7, T8 and the last return to the pack play at double speed (every 2nd frame).
#
# Film frames:  hold 0-59 | T1b 60-179 | T2b 180-300 | T3 301-421 | T4 422-542 | T5 543-663 | T6 664-784 |
#               T7 785-845 | T8 846-906 | T9 907-1027 | T9 backwards 1028-1087 | hold 1088-1147
hold T1b.mp4 0 60
clip T1b.mp4 1 120
clip T2b.mp4 0 120
clip T3.mp4 0 120
clip T4.mp4 0 120
clip T5.mp4 0 120
clip T6.mp4 0 120
clip T7.mp4 0 120 2
clip T8.mp4 0 120 2
clip T9.mp4 0 120
clip T9.mp4 0 118 2 rev
hold T9.mp4 0 60
