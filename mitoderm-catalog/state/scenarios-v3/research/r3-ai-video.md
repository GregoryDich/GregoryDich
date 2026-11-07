# R3. Photoreal AI video for the MITODERM clinic films: realism, Higgsfield models, cost

Date: 2026-11-08. Method: WebSearch summaries only. WebFetch to higgsfield.ai failed (ENOTFOUND, host not allowed in this session), no MCP was called. Prices are third-party or vendor-blog figures and CONFLICT; every number below must be confirmed on the Higgsfield cost button before spending. Balance: 1 credit, free plan (orchestrator check 06/11 19:25 and 08/11 00:45). Paid generation is not approved.

## 1. Why AI video looks "cartoonish" and what professionals do

Causes (sources agree, mostly vendor blogs, so treat settings as starting points):
- Generators smooth pores and fine skin texture and over-sharpen edges, so faces read waxy; temporal smoothing also removes the per-frame noise real footage has. (https://invideo.io/faq/why-does-ai-generated-video-look-plasticky-or-fake-and/, https://www.atlabs.ai/ja/blog/why-your-ai-videos-look-fake-(and-how-to-fix-them-step-by-step), https://flick.art/blog/how-to-make-realistic-ai-videos)
- Vague words ("cinematic", "3D render", "octane render", "4K") make the model fill lens, light and palette with the average of that tag, which is stylised. (https://invideo.io/faq/why-does-using-cinematic-in-an-ai-video-prompt-produce/, https://hailuoai.video/pages/blog/photorealism-prompts)
- Model mismatch: a stylised model asked for realism looks plastic. (https://www.nemovideo.com/blog/why-ai-videos-look-fake-how-to-fix)

What works:
1. Photoreal still first, then image-to-video; the still is the start frame (Hailuo guide above). Stills keep skin imperfections (pores, lines) via a portrait pass in a photoreal image model.
2. Camera language, no CGI words: focal length and aperture ("35mm, handheld, subtle shake", "85mm, shallow depth of field"), a named light source and time of day, "natural skin texture", "light film grain", muted grade. (https://budgetpixel.com/blog/the-dop-cheat-code-stop-prompting-pictures-start-dialing-in-lenses, https://kling.ai/topics/photorealistic-ai-video)
3. Short shots (4-5 s), one motion per shot; cut often so drift never shows.
4. Identity: one reference portrait or character sheet reused as an Element / omni_reference in every clip (https://higgsfield.ai/blog/consistent-characters-locations, https://higgsfield.ai/blog/seedance-2-5-on-higgsfield-2026). Caveat: training is image-side (Soul ID); in video use the saved reference, do not assume a face lock (https://www.frankx.ai/guides/higgsfield-soul-id-character-consistency).
5. Post, in this order: upscale, light blur, fine grain (about 15-20%), grade to a live-action reference. Grain after blur, not before. (https://invideo.io/blog/ai-video-post-production/, https://www.topazlabs.com/ai-creators)
6. Product fidelity (our hard rule): never trust the model with the label. Start/end frames from real renders; keep the product a locked still and animate only the scene; composite the approved label/packshot in post; for handled packs generate with a placeholder and swap (Genjutsu); cut to real renders for close-ups; check fidelity frame by frame separately from motion. (https://magichour.ai/blog/how-to-keep-products-consistent-in-ai-videos, https://domoai.app/blog/ai-product-videos-without-warping-the-product, https://www.seedance.tv/blog/how-to-keep-product-shape-consistent-in-ai-video-ads, https://diyai.io/ai-tools/video-generation/ai-product-video-generator/). Small text is garbled even with image-to-video, so compositing is the usual fix.

## 2. Higgsfield: model per shot type (ids from higgsfield-models.json)

| Shot | Model id | Params | Note |
|---|---|---|---|
| Photoreal clinic and people, start+end frames | seedance_2_5 | start_image + end_image, 4-30 s (use 4-5), 1080p, 16:9 / 9:16, bitrate high | main workhorse; needs Plus or above |
| Facial emotion ("wow") | minimax_hailuo (variant minimax-2.3) | start_image (+end_image), 6 s, 1080 | tags: facial, emotion; 512 res not usable with end frame |
| Hands applying serum, macro | seedance_2_5 or gemini_omni_flash_1_2 | start image macro still, 4-5 s, 1080p (4K on Gemini) | test first |
| Product flying/rotating from our render | seedance_2_5 or flux_3_video with start/end = our renders; or no AI: animate our three.js/Blender render | 5 s | safest: real render, AI only for the surroundings |
| Replace placeholder bottle with packshot | hf_mult_replace_object (draft: hf_mult_replace_object_flash) | video_references 4-30 s source + image_references packshots, 1080p | verify label every frame |
| One cosmetologist across 13 films | seedance_2_5 omni_reference / image_references; stills from gpt_image_2_6 (Soul ID optional) | same 3-5 references (face, hair, coat, three angles) in every call | plan a locked reference sheet |
| Drafts then finals | seedance_2_5 | 480p draft, finalize at 1080p within 7 days via draft_job_id (billed full duration) | ~1/5 price of final |
| 4K | flux_3_video (up to 4K), gemini_omni_flash_1_2 (4K), or upscale_video | | seedance tops out at 1080p; 4K via upscale |
| 9:16 | seedance_2_5, kling3_0_turbo, gemini_omni_flash_1_2 | aspect_ratio 9:16 | regenerate from a 9:16 start frame, do not crop |

## 3. Prices (conflicting; see costs.json)

Plans (USD/month): set A (Higgsfield blog): Starter 15 / 200 cr, Plus 49 / 1000 (39 annual), Ultra 129 / 3000. Set B (Krea, 31 Aug 2026): Starter 19 / 270, Plus 59 (47 annual) / 1200, Ultra 129 (99 annual) / 3000. Older names: Basic 9, Pro 29/600, Ultimate 49/1200, Creator 249/6000. Sources: https://www.krea.ai/blog/higgsfield-pricing-explained-2026-unlimited-credits-and-real-monthly-costs, https://higgsfield.ai/blog/higgsfield-pricing-explained, https://creatify.ai/blog/higgsfield-pricing-(2026)-plans-and-what-you-ll-actually-pay, https://lumalabs.ai/news/higgsfield-pricing. Seedance 2.5 needs Plus+ (https://higgsfield.ai/changelog). Credits do not roll over; packs expire in 90 days; free plan has no commercial use.

Per generation: Seedance 2.5, 8 s: 24 cr at 480p, 56 at 720p, 128 at 1080p (https://higgsfield.ai/blog/seedance-2-5-pricing-2026); another post says 72 cr for 8 s 1080p. Seedance 2.0: 22 cr/5 s 720p, 45-60 at 1080p (https://www.toolcolumn.com/learn/higgsfield-credits-explained, https://www.wireflow.ai/blog/higgsfield-ai-pricing). Kling 3.0: ~7-10 cr/5 s. Veo 3.1: ~40 cr/4 s, Fast ~16. Genjutsu swap: ~105 cr/14 s at 720p, 144 at 1080p (15 s), Lite ~30 cr/14 s, about a third (https://aliteq.com/what-is-higgsfield-genjutsu, https://creaa.ai/blog/higgsfield-genjutsu-alternative). Not published: upscale, Soul, Hailuo, Flux 3, Gemini Omni, Nano Banana Pro (implied ~2 cr). One review says Higgsfield stopped listing per-clip costs on 31 Oct 2026 (https://aifunnelinsider.com/higgsfield-ai-review-2026/).

## 4. Cost model (credits / USD; assumptions in costs.json)

| | Low | Likely | High |
|---|---|---|---|
| One film (45 s, 16:9 + 9:16, drafts, stills, swap, 4K on hero) | 1,313 cr / $56 | 3,628 cr / $181 | 8,147 cr / $570 |
| Transition clip 3 s | 75 cr | 153 cr | 291 cr |
| Sample (EXO-NAD film + transition) | 1,388 cr / $60 | 3,781 cr / $189 | 8,438 cr / $591 |
| Series (13 films + 13 transitions + home) | 18,476 cr / $794 | 50,463 cr / $2,523 | 112,424 cr / $7,870 |

Plan: sample likely needs Ultra (3000 cr) plus a pack, or Plus for several months; low fits Plus. Series at likely scale is about 17 Ultra-months, so ask Higgsfield for a volume or Business deal, or price the same job via API (Segmind lists Seedance 2.5 at $0.5876/s 1080p, giving about $127 for the likely finals, consistent with our $130; https://www.segmind.com/models/seedance-2.5/pricing). Biggest levers: crop 9:16 instead of regenerating (-30%), fewer finals via good drafts, product close-ups from real renders (no AI).

Recommendation: before the owner pays, buy nothing; test one shot on Plus (about 1000 credits) to measure real per-second cost, skin realism and label drift.
