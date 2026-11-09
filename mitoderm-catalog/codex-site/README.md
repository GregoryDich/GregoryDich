# MITODERM — cinematic website

Independent Hebrew/RTL website with the complete13-product collection and the approved V-TECH procedure story. Developed in the Codex workspace. Higgsfield supplies only generated media; the application has no Higgsfield login or SDK.

## Local development

Use Node22 or newer and pnpm. Install from the committed lockfile, then run `pnpm dev`. Run `pnpm build` for the Cloudflare-compatible Vinext build. The application uses the Next app-directory route convention and React19.

## Content

The opening always shows the whole collection, including MITOTECH and all4 BIOSPICULE products. Selecting V-TECH leads through package, consultation, MITOPEN, serum, gel mask, documented-case request, a scroll-controlled opening of the original kit5+5 and related products. Other product routes are retained.

The collection uses a gentle light-and-camera loop that pauses on selection and respects reduced motion. V-TECH uses the same photograph from the collection through the clinic entry, with a proportionate desktop scale. The faster kit opening and dark/gold training section are documented in `production/VTECH-V7-RELEASE.md`, including the current release status.

The case dataset is deliberately empty until approved, attributable V-TECH results are supplied. Generated process footage is labelled as an illustration and is not used as proof of outcomes.

## Media

`mitoderm/media-urls.json` maps the approved logical media names to permanent media-storage URLs. Videos and images containing people are not committed to the public source repository. The encoded desktop/mobile videos and their exact-frame posters have already been uploaded; no new generation is required to run this code. Product cutouts, the original40-frame kit opening and Rubik fonts are included. The kit frames are reused unchanged from the existing project; see `production/VTECH-V6-RELEASE.md` and `production/vtech-unboxing-source.json`.

## Leads

`/api/leads` uses raw Cloudflare D1 binding `DB`. Drizzle migrations contain3 tables for leads, a rate-limit salt and hashed rate-limit counters. The existing validation, same-origin checks, idempotency and rate limits are preserved. There is no CRM/email integration and no public API for reading leads. Database contents and secrets are not part of the repository.

## Hosting

`.openai/hosting.json` is the deployment manifest for the separate preview. The source can also be adapted to another Cloudflare deployment with the same D1 schema. GitHub stores source and history; it is not by itself the server-side application host. Static GitHub Pages alone cannot run the D1 lead endpoint.

The previous Higgsfield-hosted version remains an archived build; its URL is not the new application address.
