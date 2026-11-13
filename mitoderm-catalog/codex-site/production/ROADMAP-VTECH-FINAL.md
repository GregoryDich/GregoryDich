# MITODERM / V-TECH — Final polish roadmap

**State (2026-11-11):** V-TECH v8 is the last confirmed live release; the v9 code is in `claude/mitoderm-figma-catalog-74tbuw`. TypeScript, production build and Chromium browser QA **PASS (186/186)** on five viewport sizes, reduced motion, opened/reversed scrub, background image and related product decoding. Last verified code commit: `8b8e2df8d9646b04d71939a2a488838f974de2a8`; [CI run #42988503683](https://github.com/GregoryDich/GregoryDich/actions/runs/42988503683). **NOT DEPLOYED TO SITES. Safari/manual live QA and production deployment are pending.** Keep v8 as a rollback reference. Only V-TECH may be implemented until it passes review. Twelve other pages are storyboard-only.

## Stages and acceptance
- [x] **1. Audit real pack mechanism:** review IMG_9258.MOV, IMG_9253–9257.jpg, approved V-TECH open kit photograph, previous v8 behavior; gold sleeve slides strictly along carton axis, then black case folds open.
- [x] **2. Architecture and product storyboard:** document approved art direction, patient-to-product handoff and specific kit geometry; preserve good patient/procedure shots.
- [x] **3. Source code — first implementation:** in `mitoderm/pilot`, amend VTechKitSequence.tsx, VTechPackFlight.tsx, vtech-pack-flight.css. The exterior sleeve uses ONE real pack photograph; inner right door comes from the verified open-kit photograph and swings around hinge; no fabricated ampoules or new 3D carton; background carries the same clinic. **Pending visual QA.**
- [x] **4. Below-fold design — first implementation:** editorial HTML chapter replaces three numbered training cards; stage shows real clinic still with black-gold scrim; related products are a calm asymmetrical gallery. **Pending visual QA.**
- [ ] **5. Quality gates (Chromium desktop/mobile PASS; Safari/manual production QA pending):** Automated TypeScript + build + 186/186 Chromium checks passed in [GitHub Actions #42988503683](https://github.com/GregoryDich/GregoryDich/actions/runs/42988503683); [screenshots/artifact](https://github.com/GregoryDich/GregoryDich/actions/runs/42988503683/artifacts/13841075570). Inspect scrub forward and backward with mobile 320/390/430px, desktop 1366/1440/1920px, Chrome/Safari, reduced motion, keyboard, CTA; inspect image crop, logo, 5 serum vials, 5 gel masks and contact form. Correct failures.
- [ ] **6. Release:** compare first/last frames, deploy through the original Sites publisher, verify live `/products/v-tech-system` and front-page entry, capture proof frames and append deployment/version SHA.

## v9 motion brief
Main collection → same pack reaches clinic table → same clinician and patient → treatment → real evidence ONLY → visible reorientation toward clinic table, no artificial 38px blur/blank gradient → pack in offer frame. Package: sleeve slides up → black inner book case revealed → the RIGHT black panel opens about its hinge → 5 ampoules (2+2+1) and gold mask sachet are displayed → sleeve rests left as the approved final photo. The full transition is reversible through scroll, tap is an optional shortcut. Do not invent a new carton, replace text, or swap foil color in the middle.

## Documentation and launch blockers
- No invented clinical before/after. For case study require real before/after, same zone/light/crop, dates, sessions, consent and approved claims; otherwise request professional documentation.
- Use synthetic film only as illustrative; preserve the recurring clinician's identity and natural patient skin.
- Training price, program/terms and lead recipient must be verified; CTA must remain from first screen. Test lead submission and actual notification before marketing.
- FPS/seeking performance and CWV are measured (not assumed). Targets: LCP <= 2.5s, INP <= 200ms, CLS <= 0.1.
- To preserve continuity, don't globally regenerate the approved narrative film just to solve one problematic transition.

## V9 visual QA log — 11 November 2026

- Verified 1440×900, 1920×1080, 390×844, 320×568, 430×932; no horizontal overflow; all kit frames loaded. Scroll back closes the kit; reduced-motion switches to linear semantic view.
- Real pack sleeve and black hinged case appear in order. Previous duplicate closed product on background was corrected by using the V-TECH mask/procedure still, not an image with a duplicate box.
- The training section is an editorial scene (not three equal steps) and the related product images load; their WebP files require proper decoding before first visual capture. ProductImage can request synchronous decoding for this small gallery.
- Human screenshot review is recorded for desktop/mobile in the CI artifact, but **Safari, production live refresh, and real lead-form delivery remain unverified**.
- Higgsfield was NOT used and no paid credits were charged. Previous approved procedural story remains unchanged. Synthetic face/skin refinements need a separate locked-identity media review.


## V9.2 QA update — 13 November 2026

- **Automated Chromium QA: 222/222 PASS**, 0 issues — [GitHub Actions run #43414323156](https://github.com/GregoryDich/GregoryDich/actions/runs/43414323156). This covers TypeScript, production build, desktop 1440/1920, phones 320/390/430, scrubbing forwards and backwards, image decode, reduced motion, and full-height training poster.
- **Visual fixes made since v9:** remove overlapping second navigation during cinematic playback; hide mobile offer copy while the sleeve is being removed and restore it when the kit is opened; suppress distracting face behind the product while retaining an unblurred clinic environment; correct the `<picture>` wrapper to full height in block 8; await decoded patient poster for reliable scene-to-scene visual QA.
- **Visual evidence:** [screenshots artifact](https://github.com/GregoryDich/GregoryDich/actions/runs/43414323156) with closed/sleeve/hinge/opened/training/product-gallery frames on five screen sizes. Mobile training now includes the clinician and patient through the full section instead of only at the top.
- **Remaining limitations:** no access in this session to the original ChatGPT Sites publisher for `mitoderm-cinematic.evenradish1.chatgpt.site`. Live v8 remains unchanged; do **not** advertise v9.2 as deployed. Safari-specific test, real lead delivery, final visual signoff, and any Higgsfield patient-skin retouch are pending. Do not use AI-generated before/after as evidence.
