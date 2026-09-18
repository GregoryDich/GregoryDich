# WS1.0 Coding Protocol — pre-specified before human coding

**Version 1 · 2026-09-18 · to be deposited on OSF project `j89yt` together with `CODEBOOK.md` before any human coding begins.** Registration of the study: `osf.io/ehrac` (Part A). This document fixes *how* the reliability study is run and analysed; it does not change the pre-registered hypotheses.

## 1. Purpose
Estimate the inter-coder reliability of the AI × jobs narrative coding scheme (`CODEBOOK.md` v1: relevance 0/1; valence minus / plus / mixed / none) and apply the pre-registered go/no-go gate for WS1: **Cohen's κ ≥ 0.70** for relevance and for valence.

## 2. Materials
300 fragments (~50 words each) drawn from 14 YouTube auto-transcripts on AI and work (video IDs deposited with the data), stratified as 136 dictionary-relevant / 164 dictionary-non-relevant with seed 42 (`ws1_pipeline.py`). This is a **reliability sample**, chosen to contain both classes; it is not an estimate of the corpus. Corpus-level validation (≥1,000 fragments, crowd coders) is WS1 step 1c.

## 3. Instrument
Web page (`make_artifact_page.py`): one fragment at a time; per-coder random order seeded by the coder's pseudonym; relevance first, valence only if relevant; no back navigation; 8 constructed practice items with immediate feedback before the 300; instructions in English, Russian and Hebrew — **fragments always in English**. The page records per fragment: label, position in the coder's order, seconds spent; per session: pseudonym, self-reported English level, recruitment source (public post / researcher personally / other), interface language, start and end timestamps, codebook version. Results are exported by the coder as CSV.

## 4. Coders and recruitment
The PI, personal acquaintances of the PI, and volunteers recruited through an anonymous public post (`RECRUITMENT.md`). The recruitment text describes the task only as coding "how videos talk about AI and work"; no hypothesis is mentioned. Coders are asked to work alone and not to discuss fragments. Coders give consent on the page to publication of their pseudonymised coding. No personal data beyond a self-chosen pseudonym is collected.

## 5. Inclusion rules (fixed in advance)
A coder's data enter the primary analysis if all hold: (a) self-reported English level *good*, *fluent* or *native*; (b) practice score ≥ 6 of 8 on the first attempt; (c) all 300 fragments completed; (d) median time per fragment ≥ 3 seconds. Excluded coders are reported with the reason; their data are kept for secondary analysis.

## 6. Primary analysis
Cohen's κ, computed separately for relevance (2 categories, all 300 fragments) and valence (4 categories, on fragments both coders marked relevant; a second version on all 300 with *none* for non-relevant is reported as well), with 95% bootstrap confidence intervals (1,000 resamples over fragments).
**Primary pair(s):** if two or more *publicly recruited* coders are eligible, all pairs among them; otherwise all pairs among eligible non-PI coders. **The PI's coding is never part of the primary κ.** Gate: mean pairwise κ ≥ 0.70 on both dimensions.

## 7. Secondary analyses
Krippendorff's α across all eligible coders (also using partial completions); κ of the PI versus each other coder; κ by recruitment source and by interface language; agreement of the machine channels (dictionary v0/v1, LLM) with adjudicated gold labels; timing distributions.

## 8. Adjudication
Gold label per fragment = majority among eligible coders; ties are broken by the PI's label, and the number of PI tie-breaks is reported.

## 9. Decision rule
Gate passed → WS1 starts with the codebook unchanged. Gate failed → codebook v2 written from the disagreement patterns, deposited on OSF, and the reliability study repeated with new or re-trained coders; if valence alone fails twice, the fallback is a binary alarming/reassuring scheme, declared as a deviation.

## 10. Data deposit
Raw per-coder CSVs (pseudonymised), the κ report, this protocol, `CODEBOOK.md` v1 and the recruitment text are deposited on OSF when the analysis is complete.

## 11. Disclosure
`CODEBOOK.md` v1 was written on 2026-06-20, after the OSF registration (2026-06-19) and after a pre-test in which two large language models coded the same 300 fragments (κ 0.48 for relevance, 0.22 for valence). That pre-test motivated rules 1–2 of the codebook (debunking = plus; doubt about the cause = none). The LLM codings are not human data and are not used in any reliability estimate.
