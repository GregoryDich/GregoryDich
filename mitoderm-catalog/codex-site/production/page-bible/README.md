# MITODERM — Production Page Bible (13 products)

**One source of truth:** [REGISTRY.json](./REGISTRY.json) stores per-product stage, palette, cast status, scene durations, scroll lengths, draft CTA and protocol provenance. Approved-for-review packages add a referenced `STORYBOARD.json` for shot direction and source/approval metadata; timing remains in the registry. Per-product [PAGE.md] files are generated from the registry by `scripts/generate-page-bible.mjs`. **Do not manually edit the PAGE.md files.**

### Current workflow
1. Check user original product photos. **NAD.png** is the EXO-NAD gold/ivory canonical reference; the repo's product crops corroborate original appearance.
2. Check MITODERM-Protocols-HE.pdf (professional clinic), product catalog, original VM/BIOSPICULE packaging. Procedure detail on site is simplified, not an instructional protocol.
3. Lock each approved clinician image in one of three **female cosmetologist casting cohorts 18–35, 35–50, 50–80**. Distinct patient chosen separately based on treatment and user-approved reference. All people retain identity throughout same page.
4. Write storyboard and 3D prop preview without paid video generation. Only after approvals use Higgsfield for limited live environment/actor movement; exact typography and boxes remain separate deterministic layers.
5. Each site page follows V-TECH's film/scroll logic, one scene time window + scroll length, but **number and duration of scenes vary with the real action**.
6. Ending order: verified real before/after if available → exact kit → professional UTP/training → FAQ → related SKUs → B2B lead. No misleading before/after or invented claims.
7. Validate `node scripts/generate-page-bible.mjs --check`; update metadata under `REGISTRY.json` and regenerate. Later project implementation reads the registry, not separate duplicated ad-hoc descriptions.

### Directory and locks
- `REGISTRY.json` — source of truth for 13 products and design tokens.
- `pages/<slug>/PAGE.md` — one automatically generated screenplay / architecture per SKU.
- `PALETTE-CONTROLS.md` — how to keep colors tied to packaging; no green EXO-NAD.
- `CASTING-REFERENCES.md` — cosmetic practitioners 18–35 / 35–50 / 50–80, patient locks and approvals.
- `PROTOCOL-TRACE.md` — protocol evidence, conflicts and Instagram reference approval gate.
- `../../scripts/generate-page-bible.mjs` — generate/check command.

**V-TECH is frozen:** do not change its code, film, timing or live page while implementing this architecture. One character, one identity across all sections. **Current status: PREPRODUCTION ONLY.** No new pages/video published.

## EXO-NAD review package — 2026-11-13

[Open the complete Hebrew PAGE.md](pages/exo-nad/PAGE.md) · [Visual storyboard](pages/exo-nad/STORYBOARD.png) · [Live RTL preview source](pages/exo-nad/STORYBOARD.html) · [QA](pages/exo-nad/QA.md). Download the files with their relative assets to open HTML locally; GitHub blob view displays source, not a deployed website.

Status: `approval_ready_with_reference_holds`. Real product image and PDF pp.9–10 verified; cast, exact permitted procedure footage, clinical evidence and final copy approval remain open. No paid generations, production routes or V-TECH changes.

Generate with `node scripts/generate-page-bible.mjs` and `node scripts/render-approval-package.mjs`; validate both with `--check`. Browser verification: `node scripts/verify-approval-package.cjs` using installed Playwright/Chrome (see QA.md). Do not manually edit generated PAGE.md or STORYBOARD.html. No new dependencies are required by the generators.

Units: registry `scrollVh` is a count of **full viewport heights**, retained for compatibility; 10.35 means 1035 CSS vh. Film edit seconds are not treatment duration.

Next: [EXOSIGNAL HAIR source preparation](pages/exosignal-hair/NEXT-PACKAGE.md), then `continuation.queue`. Existing automation `6af73a565af08191bf0a4b0d3ee94430` remains unchanged; never create a duplicate.
