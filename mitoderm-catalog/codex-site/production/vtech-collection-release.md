# MITODERM — collection to V-TECH production handoff

Updated: 2026-11-08 UTC. This update supersedes the earlier pilot-only plan in implementation-2026-11-08.md.

## Approved narrative and implementation

1. Home opens with the complete inventory of13 genuine product cutouts, including MITOTECH and all4 BIOSPICULE products. Mobile opens with a compact whole-family composition, then a large product selection rail.
2. One click/tap selects a product. Its existing image moves forward; the V-TECH route opens on its large package.
3. A generated5-second desktop film, and a separately composed portrait film, scrub from the package to the consultation. Their exact encoded last frames continue into the consultation section.
4. MITOPEN, serum and transparent gel mask are3 separate4-second forward-playing demonstration clips. Scrolling selects the episode; scrolling backwards does not reverse treatment.
5. The same face/cheek is the focus of this branch. A scalp story is outside this approved first build.
6. Documented before/after cases share one carousel, with arrows and dots and no comparison divider. The data array is deliberately empty until product-specific evidence and publication approval are supplied. The live empty state offers a professional case request; generated treatment footage is never used as proof of outcomes.
7. Kit:5 x5ml V-TECH SERUM plus5 x5ml V-TECH GEL MASK, with price and training inquiries.
8. Related products are separate from the kit. EXOCELL and EXOTECH are face-line companions; MITOPEN, MICRO BOOST10% and DERMA RECOVERY are additional professional options, not mandatory sequential steps.

The opening is always the collection. A direct product URL remains available for intentional deep links.

## Source and identity

Original product cutouts retain src/mitoderm/assets.json provenance. The clinic film references the user-supplied MITODERM actress/model and the same illustrated mature patient throughout. This is a generated process illustration, not documentary footage of an actual treated patient. No skin transformation or measured improvement is claimed.

The encoded kit artwork was visually counted:5 amber serum vials and5 gold mask sachets. Source kit quantity follows catalog frame824:112. Formula copy is based on the catalog. Conflicting numerical maintenance/aftercare instructions from different source versions are intentionally not merged into advice.

## Files

- Home.tsx and pilot/home-cinema.css: inventory, desktop stage, mobile family overview and selection.
- pilot/Experience.tsx and product-flight.css: source-image navigation transition and product-aware inquiry dialog.
- scroll-scrub-scenes.ts: intro composition/data for the existing, unchanged scroll engine.
- pilot/VTech.tsx, CinematicStage.tsx, VTechDetails.tsx and vtech-cinema.css: the V-TECH sequence and forward-only clinical media.
- pilot/case-data.ts: approved-case contract and empty current dataset.
- public/assets/world/vtech-*: selected encoded media only.
- production/vtech-pilot-motion.json: generated asset and cost manifest.

## Interaction and accessibility

Native anchors retain direct URLs; modified clicks are not intercepted. One click/tap opens a product. Reduced motion bypasses the flight and displays stills without fetching clinical videos. Treatment clips start after35% of the image enters the viewport, pause offscreen and offer play/pause/replay. The existing scrub controller retains blob seeking, mobile sources, poster safety, reduced motion and teardown.

The early inquiry and kit inquiry open the existing accessible dialog. The selected product is carried into the form. POST /api/leads persists to D1 before success is shown; there is no new CRM/email notification integration. WhatsApp opens only after a visitor chooses that external link.

## Verification and release record

- Source UI contract passed.
- Actual13-product inventory and all4 BIOSPICULE retained.
- Selected video boundary frames and mobile crops visually reviewed before integration.
- All posters derived from the actual encoded files; audio removed from the deployed clips.
- No dependency or lockfile changes. Node22 is available; Bun and project node_modules are absent in this sandbox. The ordinary platform deploy runs the authoritative typecheck and build.
- Full source/media checks, final Git revision and deployment result are recorded in the final release report after the media pack is complete.
- Existing website remains unlisted in the community feed. Public-access checks from the sandbox encountered Cloudflare403/1010; deployed status alone does not prove anonymous browser availability. No authentication policy was modified.

## Remaining content dependency

Supply approved, attributable V-TECH before/after pairs with publication approval, treatment context and assessment timing to populate the prepared carousel. No actual patient case is fabricated to fill that gap.
