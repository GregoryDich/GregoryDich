# WS1.0 Coding Protocol — pre-specified before human coding

**Version 1.1 · 2026-10-10.** Version 1 (2026-09-18; sections 1–11) is to be deposited on OSF project `j89yt` together with `CODEBOOK.md` before any human coding begins; version 1.1 is deposited there before any human label is opened. Registration of the study: `osf.io/ehrac` (Part A). This document fixes *how* the reliability study is run and analysed; it does not change the pre-registered hypotheses.

*Changelog — v1.1 (2026-10-10): adds section 12, which freezes the dictionary and LLM classification channels before any human label is seen; sections 1–11 are unchanged from v1.*

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

## 12. Machine channels frozen before human coding (addendum v1.1, 2026-10-10)
Written on 2026-10-10, while human coding is under way and before any human label has been received by the researchers. It fixes the two machine classification channels of the registration, "a keyword dictionary and an LLM classifier" (A.2), compared as a dictionary-only and an LLM-only index (A.6, item 3); their agreement with the gold labels is a secondary analysis (section 7). Hashes are SHA-256 of the raw file bytes unless stated otherwise; `verify_frozen_channels.py` recomputes every hash in this section and exits non-zero on any mismatch.

**12.1 Dictionary channel v1.** `classify()` and its five term lists in `ws1_pipeline.py` as committed at `f4a1655` (file unchanged since `7eb5a1e`, the stance override of ROADMAP D29).
- `ws1_pipeline.py`: `6e090f195c91398ffe311d1107490667e028ad82656ef21c39e1f23e623dfbe1` (git blob `15759519ec822077ab755478193a6b270962fbed`).
- Term lists `AI_TERMS`, `OCC_TERMS`, `DISPLACE_TERMS`, `CREATE_TERMS`, `SKEPTICAL_TERMS`: `7ef9fec0aad7ddc70d7be88d9f33b92ab17630d1da2576bb5d6364b7c7b1a620`, the SHA-256 of the UTF-8 bytes of `json.dumps({name: list, ...}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`, lists in source order.
- Disclosure: `SKEPTICAL_TERMS` was added in `7eb5a1e` after the dictionary was compared with 50 labels produced in a chat session (D29), and was tuned in-sample on those 50 fragments (commit message of `7eb5a1e`). Which 50 fragments they were is not recorded in the repository. 31 of the 300 fragments contain at least one `SKEPTICAL_TERMS` entry, some of them very specific (e.g. "0.4%", "math doesn't add up"), so dictionary v1's agreement with the gold labels may be partly in-sample and is reported with this caveat.

**12.2 LLM channel v1.** `ws1_llm_channel.py`: one request to the Anthropic Messages API per fragment; fragments are never combined in one prompt.
- Model `claude-opus-5-5` (Claude Opus 5.5), the current Opus model and the default in Anthropic's Claude API reference (the `claude-api` reference bundled with Claude Code; model list as of 2026-10-06). The reference gives no dated snapshot identifier for this model; dated identifiers exist only for older models. A current model was preferred to an older dated snapshot because this channel, once validated, has to be applied to the full WS1 corpus, and older models are retired first (the reference lists several 2024–2025 models as retired or deprecated). The `model` field of every response is logged, so a change of the served model would be visible.
- Request: system prompt = the complete file `llm_channel_prompt_v1.txt` (`17a98727a1a018544fc5203676f0066c901853fbc8b3e394a4e39d1f52cfd340`); one user message, `Code this fragment.\n\n<fragment>\n{fragment}\n</fragment>` with the fragment text; `thinking: {"type": "adaptive"}`; `output_config.effort: "low"`; `max_tokens: 2048`; structured output (`output_config.format`, JSON schema: `relevant` integer in {0, 1}, `valence` in {minus, plus, mixed, none}, no other properties); the system prompt is marked for prompt caching (a cost and latency setting). No tools, no sampling parameters, no fallback model. The complete request, with the fragment as the placeholder `{fragment}` and the system text replaced by a reference to its hash, has SHA-256 `31611568e0657a2ad763e7a3fc1b11d0fcab956fcb478542713a5709efff49d6` (canonical JSON, `spec_sha256()`).
- Determinism: this model rejects `temperature`, `top_p` and `top_k`, and its reasoning cannot be switched off; Anthropic's reference notes that temperature 0 never guaranteed identical outputs on earlier models either. Effort is fixed at `low`, the reference's recommendation when determinism is the aim. Outputs are therefore not guaranteed to be identical from run to run; the labels of record are those of the first complete run (12.3).
- Prompt: the `CODEBOOK.md` v1 rules — the strict two-token relevance rule (AI referent AND labor referent AND a connection, judged from the fragment's own words only), the four valence categories, rule 1 (debunking destruction = plus), rule 2 (doubt about the cause = none), the decision flow and the output format. It contains no worked examples: none of the 300 fragments and none of the 8 practice items. The codebook's two decision-example tables are left out because most of their entries are shortened excerpts of fragments in the 300-fragment set; `tests/test_llm_channel.py` checks that the prompt shares no five-word sequence with any of the 300 fragments or the practice items.
- Pre-specified handling: HTTP 408, 409, 429 or ≥ 500 and connection errors are retried with exponential backoff (or after the server's `retry-after`), every attempt logged; any other API error stops the run, which resumes on the next start without repeating finished fragments. A refusal (`stop_reason: "refusal"`) is recorded, not retried and not sent to another model; the label stays missing. A reply that is not a valid label (cut off at `max_tokens`, or not matching the schema) leads to the identical request being repeated, at most 3 attempts in all, after which it is recorded as invalid and the label stays missing. `relevant = 0` with a valence other than `none` is recorded with valence `none` (codebook: "If relevance = 0, write none"), and the number of such cases is reported. Missing LLM labels are not imputed.
- Outputs: `llm_labels.csv` (`frag_id`, `relevant_llm`, `valence_llm`, `status_llm`, sorted by `frag_id`) and `llm_raw_log.jsonl` (every request with the system text replaced by its hash; every response as returned, with the served model, request id and token usage; timestamps; prompt and specification hashes). Input set: the 300 fragments, SHA-256 `603893308ce3bcf17aa71b33b39cfb0b8352192a754afa46d1a3e0aa425e47f2` of the canonical JSON `[[frag_id, text], ...]` sorted by `frag_id`.

**12.3 Commitments.**
1. Neither channel is modified until the WS1.0 gate (section 6) has been computed. `ws1_llm_channel.py` refuses to run if the prompt file or the request specification differs from the hashes above.
2. Any revision of either channel made after human labels have been seen is a new version (dictionary v2, LLM channel v2). It is evaluated only on fresh fragments that are not among these 300; results of a revised channel on these 300 fragments are reported, if at all, as in-sample.
3. If an API key is available in time, the LLM channel is run on all 300 fragments and the SHA-256 of `llm_labels.csv` and of `llm_raw_log.jsonl` is deposited on OSF (`j89yt`) before the human labels are opened. Otherwise the frozen specification in this section, with the files and hashes it names, is the commitment: the channel is run unchanged later, and the report states which of the two happened, with the timestamps from the log.
4. The 50 fragment labels produced on 2026-06-20 by the AI co-author inside a chat session (ROADMAP D29) are not output of this channel: they did not come from a reproducible call with a fixed model, prompt and parameters. They are excluded from every analysis under this protocol, as are the pre-test codings disclosed in section 11.
