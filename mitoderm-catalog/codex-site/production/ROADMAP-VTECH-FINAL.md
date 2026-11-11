# MITODERM / V-TECH — Final polish roadmap

**State (2026-11-11):** V-TECH v8 is the last confirmed deployed release. v9 code changes are in `claude/mitoderm-figma-catalog-74tbuw`. **TypeScript and production build PASS** via GitHub Actions run #42973775598, completed on 2026-11-11. v9 has **NOT yet passed visual/browser QA and has NOT been deployed**. Keep v8 as a rollback reference. Only V-TECH may be implemented until it passes review. Twelve other pages are storyboard-only.

## Stages and acceptance
- [x] **1. Audit real pack mechanism:** review IMG_9258.MOV, IMG_9253–9257.jpg, approved V-TECH open kit photograph, previous v8 behavior; gold sleeve slides strictly along carton axis, then black case folds open.
- [x] **2. Architecture and product storyboard:** document approved art direction, patient-to-product handoff and specific kit geometry; preserve good patient/procedure shots.
- [x] **3. Source code — first implementation:** in `mitoderm/pilot`, amend VTechKitSequence.tsx, VTechPackFlight.tsx, vtech-pack-flight.css. The exterior sleeve uses ONE real pack photograph; inner right door comes from the verified open-kit photograph and swings around hinge; no fabricated ampoules or new 3D carton; background carries the same clinic. **Pending visual QA.**
- [x] **4. Below-fold design — first implementation:** editorial HTML chapter replaces three numbered training cards; stage shows real clinic still with black-gold scrim; related products are a calm asymmetrical gallery. **Pending visual QA.**
- [ ] **5. Quality gates (build PASS; visual QA pending):** TypeScript and production build passed in [GitHub Actions #42973775598](https://github.com/GregoryDich/GregoryDich/actions/runs/42973775598). Inspect scrub forward and backward with mobile 320/390/430px, desktop 1366/1440/1920px, Chrome/Safari, reduced motion, keyboard, CTA; inspect image crop, logo, 5 serum vials, 5 gel masks and contact form. Correct failures.
- [ ] **6. Release:** compare first/last frames, deploy through the original Sites publisher, verify live `/products/v-tech-system` and front-page entry, capture proof frames and append deployment/version SHA.

## v9 motion brief
Main collection → same pack reaches clinic table → same clinician and patient → treatment → real evidence ONLY → visible reorientation toward clinic table, no artificial 38px blur/blank gradient → pack in offer frame. Package: sleeve slides up → black inner book case revealed → the RIGHT black panel opens about its hinge → 5 ampoules (2+2+1) and gold mask sachet are displayed → sleeve rests left as the approved final photo. The full transition is reversible through scroll, tap is an optional shortcut. Do not invent a new carton, replace text, or swap foil color in the middle.

## Documentation and launch blockers
- No invented clinical before/after. For case study require real before/after, same zone/light/crop, dates, sessions, consent and approved claims; otherwise request professional documentation.
- Use synthetic film only as illustrative; preserve the recurring clinician's identity and natural patient skin.
- Training price, program/terms and lead recipient must be verified; CTA must remain from first screen. Test lead submission and actual notification before marketing.
- FPS/seeking performance and CWV are measured (not assumed). Targets: LCP <= 2.5s, INP <= 200ms, CLS <= 0.1.
- To preserve continuity, don't globally regenerate the approved narrative film just to solve one problematic transition.
