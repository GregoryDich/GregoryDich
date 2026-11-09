> Historical pilot record. Superseded by vtech-collection-release.md and the current vtech-pilot-motion.json.

# MITODERM implementation update 2026-11-08

This is an incremental update to the existing MITODERM v2 website, implementing the agreed v4 pilot. The original approved lineup, exact packaging, Rubik, near-black and product palette remain the visual foundation.

## Release scope
- Homepage: existing interactive lineup; inquiry available immediately; task selector; dedicated V-Tech invitation; professional support; persistent inquiry form.
- V-Tech: source-verified brand portrait with face visible; exact two-component kit; role of MITOPEN and face/neck/decollete; factual kit details; professional guidance.
- Existing URLs for the other 12 products remain available.
- Lead modal is accessible from the first screen; chosen product is prefilled. POST /api/leads confirms a D1 write before success.
- WhatsApp is an optional user-initiated channel. No messages or newsletters are sent automatically.

## Evidence and source corrections
- Figma file x7NyyASEmlMwazkZmZwOXk, catalog page793:2 and protocol page758:2.
- V-Tech source frames824:94 and824:114; protocol PDF pages2-3.
- V-Tech contains Serum plus Gel Mask. EXOCELL and Derma Recovery are separate products.
- V-Tech kit: 5x5ml serum plus 5x5ml gel-mask sachets, per catalog824:112.
- The catalog says V-Tech maintenance every6months; the PDF and protocol Figma say2-3months. No universal maintenance interval is published in this pilot.
- PDF SPF50/7days differs from Figma SPF30/5days. No synthesized numeric aftercare instruction is published.
- MITOTECH clarity/time conflicts and PDF heading/image mismatch remain unresolved; no generated preparation scene is asserted.
- QR on catalog793:435 and protocols1040:2 resolves to https://api.whatsapp.com/send?phone=972543262182&text=שלום. Existing phone agrees. WhatsApp changed from547621889 to543262182.
- Email info@mitoderm.com retained from the existing site; it is not printed in the supplied covers.
- Broad before/after gallery is shared across product pages and is not used as V-Tech proof.

## Asset provenance
- /assets/vtech/system-kit.webp: exact source product image from catalog824:128, resized losslessly in geometry, alpha retained, WebP1600x1468.
- /assets/vtech/brand-face.webp: https://www.mitoderm.com/images/backgrounds/introBG.png, used as a brand portrait, not a clinical result or procedure.
- Existing device and product images retain their original source manifest.
- Existing launch cover, OG, favicon and icons retained.

## Motion scope and remaining production work
The user's approved lineup and v4 distinction govern this existing-site update: packaging can move with scrolling; clinical procedures play forward. Existing layered source-photo motion and a620ms navigation transition are implemented. The scaffold scroll-scrub engine remains unchanged.
No generated clinic video is claimed complete. Higgsfield balance was1credit. A first high-quality2k image estimate was2.75credits and a5s Kling3.0pro silent clip estimate7.5credits. No generation was submitted.
The prepared production prompts are in vtech-pilot-motion.json. Clinical scenes require a verified application reference and sufficient credit balance. No invented result, treatment setting or patient case appears.

## Validation
- Lead service tests:7 passing scenarios in Node22 with in-memory SQLite, including persistence, idempotency, validation, origin/body/honeypot rejection, failure handling and rate limits.
- Sandbox lacks Bun and installed project dependencies; platform build is the authoritative TypeScript/build check.
- UI source review covers native dialog focus, semantic fields, reduced motion, touch first/second click behavior, product URLs and source assets.
- Full motion-film gate remains pending production media, not silently marked passed.
