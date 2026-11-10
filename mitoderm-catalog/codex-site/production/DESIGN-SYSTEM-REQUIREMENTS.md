# MITODERM / Cinematic professional product page requirements

## Brand and composition
Premium medically credible B2B: near-black #0a0a0b/#111114, satin gold #c9a24b with gentle #dfba74 accents, off-white text, Rubik. Hebrew RTL with BDI isolation for product names/units. No fake metallic overglow, generic particles, stock-looking models, beige page switches or text baked into footage. Desktop copy generally right, product/action composition left; phone gets its own vertical framing and safe areas.

## Narrative and UX
One visitor journey: **choose product → see patient's actual concern → product/procedure → verifiable evidence → accurate kit → professional offer/education → complementary products**. CTA available from first viewport. Sticky cinematic stage scroll-scrubs at the user's speed and reverses correctly. Motion transitions are driven by camera/object, not sudden blur, hard cuts or arbitrary object morphing. Last frame of shot A matches first of B (crop, scale, lighting and camera); no repeated box from a different render. Use selected assets as ground truth.

## Actors and product fidelity
Approved recurring MITODERM clinician remains identical. Patient is one locked reference identity within each film; natural skin with nonuniform pores, wrinkles and normal behavior; don't invent instant biological effects. Label synthetic scenarios as illustrations.
Use one stable physically correct model/approved photograph for pack throughout. Gold outer sleeve slides off in actual direction; inner book case opens on hinge; sachet and 5 glass vials don't teleport; lid and sleeve can settle into the approved open-kit composition. Studio gold lighting must not visibly change material color, lettering or reflections frame to frame.

## Layer stack
- Background: one coherent photoreal clinic, stable lighting, enough visual information behind hero.
- Product and motion: physical/rigged exact packaging, relative position follows scroll.
- Content: separate live HTML/Rubik heading, professional benefits, case captions, CTA.
- User controls: navigation, progress bar, pointer/touch and keyboard. Never cover face/pack with text or create accidental modal.
No synthetic before-after; consent + data + comparable photos required.

## Editorial rules after chapter 7
Block 8 is NOT three equal numbered cards. Use continuation from the patient/product scene into generous editorial typography, quiet clinic photograph, specific practice/education details, one main CTA, small accordions for concrete questions. Associated products in sparse, unboxed editorial gallery, not a repetitive card grid. Do not claim that related products are included in V-TECH kit.

## Accessibility and performance
Mobile breakpoints test 320/390/430, desktop 1366/1440/1920. Contrast, focus, >=44px tap targets, reduced-motion static semantic alternative, load poster before film, separate 9:16 composition, low-data mode. Target measured CWV LCP<=2.5, INP<=200ms, CLS<=0.1. Product photo/face must remain visible, avoid horizontal scroll. Keep clickable anchors usable and lead source/product preserved.

## Production/QA gates
Source of product facts: MITODERM protocols and approved product catalog. Unknown claims and numbers are marked NEEDS APPROVAL. Each release must be built and visually inspected (forward/backward scrub and direct jump), then published with screenshot/proof and actual commit + deployed version. Code changes alone must NEVER be reported as deployed.
