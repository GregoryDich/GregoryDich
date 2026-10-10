# WS1.0 — Narrative-index validation gate (real data)

First contact with real text. This is the cheap go/no-go test before the
full WS1 pipeline: do independent human coders following `CODEBOOK.md` v1
agree at Cohen's κ ≥ 0.70 on relevance and on valence (`PROTOCOL_WS1.0.md`
§1, §6)? If not, the codebook is revised (§9) before weeks are spent on the
full index. The machine channels (dictionary, LLM) are then validated
against the human gold labels (§7).

## Pipeline

1. **Collect transcripts.** YouTube auto-captions via `yt-dlp`, cleaned to
   plain text (`clean_vtt.py`), one `*.txt` per video.
2. **Segment + dictionary-classify.** `ws1_pipeline.py` packs the text into
   ~50-word fragments and applies the transparent keyword-dictionary channel
   (deterministic, reproducible). Outputs `fragments.csv`, `coding_sample.csv`,
   `ws1_summary.md`.
3. **Human coding.** Independent coders (§4) label the 300 fragments, blind
   to each other and to the machine labels, following `CODEBOOK.md`. The
   instrument of the protocol (§3) is the claude.ai page built by
   `make_artifact_page.py` (one fragment at a time, per-coder random order,
   8-item practice block with feedback, per-item timing). `ws1_survey.html`
   (open in a browser; no server, no going back) and a Google Form built by
   `gforms/` (see `gforms/README.md`) show the same fragments but record no
   timing and no practice score. All yield
   `frag_id, text, human_relevant_0_1, human_valence_minus_plus_none`.
4. **LLM channel.** `ws1_llm_channel.py` classifies the same fragments, one
   request per fragment, with the specification frozen in
   `PROTOCOL_WS1.0.md` §12.5.3 (the second pre-registered channel); see
   "LLM channel run" below.
5. **κ gate.** `ws1_reliability.py` (below) runs the pre-specified analysis.
   The gate is the mean pairwise κ among eligible non-PI human coders (§6),
   not human vs machine; neither machine channel is modified before the gate
   is computed (§12.6.1). `ws1_kappa.py` and `ws1_gate.py` are quick κ tools
   for any two label columns / two coder files.

## Run

```bash
cd <folder with the *.txt transcripts>
python3 ws1_pipeline.py --sample 300          # fragments.csv, coding_sample.csv (git-ignored)
# coders use the page built by make_artifact_page.py; each sends one CSV
python3 ws1_reliability.py coder_A.csv coder_B.csv coder_PI.csv --pi <PI coder id> \
    [--channel LLM=llm_labels.csv]            # the gate, exactly as PROTOCOL_WS1.0.md specifies
python3 verify_frozen_channels.py             # frozen machine channels unchanged?
```

`ws1_gate.py` / `ws1_kappa.py` are the earlier quick tools (pairwise κ only);
the gate of record is `ws1_reliability.py`.

## LLM channel run (`PROTOCOL_WS1.0.md` §12.5.3, §12.6)

The runner checks its four frozen identities (runner file, prompt, request
specification, input set) only against the `FROZEN` table of
`verify_frozen_channels.py`; it does not compare that table with the
protocol. A run counts as LLM channel v1 only if its run record carries the
values written in §12.5.3 (§12.6.2), so every invocation goes through the
verifier first:

```bash
# the runner is started only if the verifier exits 0 (hence &&)
python3 verify_frozen_channels.py && python3 ws1_llm_channel.py --dry-run   # no API call, no file written
python3 verify_frozen_channels.py && ANTHROPIC_API_KEY=... python3 ws1_llm_channel.py   # resumes if interrupted
python3 verify_frozen_channels.py   # after the run it also checks llm_labels_run.json; must exit 0
# then commit and push llm_labels.csv + llm_labels_run.json before the first coder CSV is opened
```

The run of record is the first complete run of channel v1 committed and
pushed before the first coder CSV is opened, at a commit at which the
verifier exits 0 (§12.6.2). The verifier checks every `llm_labels*_run.json`
of channel v1 in this folder: the four identities must be the frozen values
and `labels_sha256` the sha256 of its labels file. A replicate run uses a new
`--out` and a new `--log`; the raw log (`llm_raw_log*.jsonl`) is git-ignored.

## Reliability analysis (the human gate, `PROTOCOL_WS1.0.md`)

`ws1_reliability.py` runs the pre-specified analysis (protocol §5–9, with the
§12 addendum of v1.1: §12.1 corrections, §12.3 sensitivity analyses, §12.5
frozen channels; ROADMAP D36) on the per-coder CSVs, whichever instrument
produced them (claude.ai page, Google Forms via `gforms_to_csv.py`, or
`ws1_survey.html`). Stdlib only.

```bash
python3 ws1_reliability.py ws1_coded_*.csv (--pi "<PI's coder name>" | --no-pi) \
    [--meta coders.csv] [--boot 1000] [--seed 2026] [--out-dir results/] \
    [--channel LLM=llm_labels.csv] [--anchor-ids FILE|ID,ID] [--old-practice-ids FILE|ID,ID]
```

- Coder identity = the `coder` column, else the file stem. `--pi` must match
  one input coder (exactly, or ignoring case); otherwise the run stops with a
  non-zero exit, because the PI's coding must never enter the primary κ (§6).
  If the PI did not code, say so explicitly with `--no-pi` (old spelling
  `--pi-did-not-code` still accepted); every gold tie is then unresolved.
- `--meta` (columns `coder,source,english_level,practice_correct,practice_n`)
  supplies what the 4-column formats do not record. Missing data make the rule
  that needs them *not assessable*, which excludes the coder from the primary
  κ. Forms and `ws1_survey.html` exports carry no per-fragment time, so rule
  5(d) is never assessable for them.
- Page exports carry `practice_correct`/`practice_n` (first attempt per
  practice item) since 2026-10-10, and `practice_set` (which practice items
  the coder saw) after that; older page exports need `--meta` for rule 5(b).
  The report shows each coder's practice set and which coders saw set
  `3fa31542cb4a`, the items the LLM prompt carries (instruction parity, §12.4).
- The gate compares the exact mean of the exact pair κs (rational arithmetic
  with `fractions.Fraction`) with 7/10, so a κ of exactly 0.70 passes.
  Decision (§9 as clarified in §12.1(c)): a mean below 0.70 on either gated
  dimension is FAIL, whatever the other dimension shows, an undefined mean
  included; *not assessable* only when nothing failed and a mean is undefined
  (a pair with n = 0, or chance agreement 1; the report names the pairs and
  the cause) or there is no primary pair. Valence fails "alone" (the §9
  fallback) only when relevance passed.
  `ws1_gate.py` (the older two-file summary) compares with a 1e-9 tolerance
  for the same reason.
- Gold labels (§8 as clarified in §12.1(b), D36.1): the PI does **not** vote. Gold
  relevance = plurality among the eligible non-PI coders; a tie is broken by
  the PI's label (counted as a PI tie-break); if the PI did not code that
  fragment (or `--no-pi`), it is unresolved. Gold valence (gold relevance 1)
  = plurality among the eligible non-PI coders who marked the fragment
  relevant; a tie is broken by the PI only if the PI marked it relevant,
  otherwise unresolved. Gold relevance 0 forces valence `none`. The PI's
  label breaks ties whether or not the PI meets the §5 rules (a warning says
  when an ineligible PI broke ties). PI tie-breaks are counted separately for
  relevance and valence and the unresolved fragment ids are listed;
  unresolved fragments are left out of the comparisons with gold on that
  dimension. The reading "the PI votes" (when the PI meets §5) is reported as
  a sensitivity analysis (`alt_pi_votes_*` columns, and the machine channels
  scored against it).
- Sensitivity analyses (§12.3, D36.3): every primary and secondary statistic is
  reported on all fragments and (a) without the 16 fragments quoted as anchors
  in `CODEBOOK.md` (15 in its tables, one in its rule text), (b) without the 75 fragments the old practice items
  paraphrased, (c) without both (83). The lists are the constants
  `CODEBOOK_ANCHOR_FRAG_IDS` and `OLD_PRACTICE_PARAPHRASED_FRAG_IDS`;
  `--anchor-ids` / `--old-practice-ids` override them (a file of frag_ids or
  a comma-separated list; the report says so, and an id outside the reference
  stops the run). Each run compares the lists with the ids written on the two
  §12.3 protocol lines and warns on any difference. Inclusion, the primary
  pairs and the gold labels are fixed on all fragments; the gate is computed
  on all fragments (the sensitivity sets only report what the gate rule
  would give).
- `--channel LLM=llm_labels.csv` reads the file of `ws1_llm_channel.py`
  (§12.5.3: `frag_id, relevant_llm, valence_llm, status_llm[, model_served]`);
  only rows with `status_llm = ok` are compared, the others (refusal,
  invalid, pending) are counted, listed and excluded, even when they carry
  labels. Served models are counted. The run record next to the file
  (`llm_labels_run.json`) is read when present: a `labels_sha256` that is not
  the file's, another input set, or an incomplete run is a warning; no run
  record is a warning too. Its four identities (runner, prompt, request
  specification, input set) are compared with the values of §12.5.3
  (`LLM_V1_IDENTITY`): any difference is a loud "NOT LLM CHANNEL v1" warning,
  because such labels are neither the run of record nor a replicate (§12.6.2).
  The run also warns if those values are missing from §12 of the protocol on
  disk or differ from the verifier's `FROZEN` table. A file with the coder columns
  (`frag_id, human_relevant_0_1, human_valence_minus_plus_none`) also works.
- Writes `reliability_report.md`, `reliability.json`, `gold_labels.csv` (no
  fragment text) and `exclusions.csv`. Duplicate `frag_id`s stop the run. The
  report records the protocol version and sha256 it was run against and the
  SHA-256 of the evaluation input set (the 300 `frag_id`+text, §12.5.3 (iv);
  a different reference set is a warning).
- Dictionary v1 is `ws1_pipeline.classify` (checked against the blob frozen in
  §12.5.1); v0 is a verbatim copy of the pre-stance-fix version (`a238489` =
  `7eb5a1e^`), identified by the file sha256, git blob and term-list sha256 of
  §12.5.2 and checked against git at run time; §7 compares both with gold.
- Tests: `python3 tests/test_reliability.py` (cross-checks need
  `pip install scikit-learn krippendorff`). They use synthetic labels only.

## Notes

- Dictionary **v1** (`ws1_pipeline.classify`, with the stance override of
  ROADMAP D29) is the current dictionary, frozen in `PROTOCOL_WS1.0.md`
  §12.5.1, and the one that drew the 300-fragment sample (§12.1(a), D36.2:
  strata 140 relevant / 160 non-relevant; §2's 136 / 164 is the v0 count on
  the same fragments). v1 was revised after a comparison with 50 labels the
  AI co-author produced in a chat session (D29), so its agreement with the
  LLM channel is not fully independent evidence (§12.2(b)); each channel is
  validated against the human gold labels. Any revision after human labels
  are seen is a new version, evaluated on fresh fragments (§12.6).
- An X−/X+ skew in the raw dictionary counts is expected and partly reflects
  dictionary coverage; the human gold labels decide whether the instrument is
  trustworthy.
- Raw transcripts and verbatim-text CSVs are git-ignored (third-party
  caption copyright + size). Only code and count-level summaries are tracked.
