# WS1.0 — Narrative-index validation gate (real data)

First contact with real text. This is the cheap go/no-go test before the
full WS1 pipeline: does our "AI × occupation displacement" classifier agree
with human coders at Cohen's κ ≥ 0.70? If not, we revise the instrument
before spending weeks on the full index.

## Pipeline

1. **Collect transcripts.** YouTube auto-captions via `yt-dlp`, cleaned to
   plain text (`clean_vtt.py`), one `*.txt` per video.
2. **Segment + dictionary-classify.** `ws1_pipeline.py` packs the text into
   ~50-word fragments and applies the transparent keyword-dictionary channel
   (deterministic, reproducible). Outputs `fragments.csv`, `coding_sample.csv`,
   `ws1_summary.md`.
3. **Human coding.** Two independent coders label the 300 fragments, blind
   to each other and to the machine labels, following `CODEBOOK.md`. Two
   equivalent instruments show one fragment at a time in a per-coder random
   order: `ws1_survey.html` (open in a browser; no server, no going back) or
   a Google Form built by `gforms/` (see `gforms/README.md`), or the
   claude.ai page built by `make_artifact_page.py` (adds an 8-item practice
   block with feedback and per-item timing). All yield
   `frag_id, text, human_relevant_0_1, human_valence_minus_plus_none`.
4. **LLM channel.** The same fragments are classified by an LLM with a fixed
   rubric (the second pre-registered channel).
5. **κ gate.** `ws1_kappa.py` computes agreement between any two label
   columns. Gate: κ ≥ 0.70 (human vs machine). Below → revise dictionary /
   prompt and re-test.

## Run

```bash
cd <folder with the *.txt transcripts>
python3 ws1_pipeline.py --sample 300
# ... two humans fill coding_sample.csv ...
python3 ws1_kappa.py --csv coding_sample.csv \
    --col-a human_relevant_0_1 --col-b human2_relevant   # inter-human
```

## Reliability analysis (the human gate, `PROTOCOL_WS1.0.md`)

`ws1_reliability.py` runs the pre-specified analysis (protocol §5–9) on the
per-coder CSVs, whichever instrument produced them (claude.ai page, Google
Forms via `gforms_to_csv.py`, or `ws1_survey.html`). Stdlib only.

```bash
python3 ws1_reliability.py ws1_coded_*.csv (--pi "<PI's coder name>" | --pi-did-not-code) \
    [--meta coders.csv] [--boot 1000] [--seed 2026] [--out-dir results/] \
    [--channel LLM=llm_labels.csv]
```

- Coder identity = the `coder` column, else the file stem. `--pi` must match
  one input coder (exactly, or ignoring case); otherwise the run stops, because
  the PI's coding must never enter the primary κ (§6). If the PI did not code,
  say so with `--pi-did-not-code`.
- `--meta` (columns `coder,source,english_level,practice_correct,practice_n`)
  supplies what the 4-column formats do not record. Missing data make the rule
  that needs them *not assessable*, which excludes the coder from the primary
  κ. Forms and `ws1_survey.html` exports carry no per-fragment time, so rule
  5(d) is never assessable for them.
- Page exports carry `practice_correct`/`practice_n` (first attempt per
  practice item) since 2026-10-10; older page exports need `--meta`.
- The gate compares the exact mean of the exact pair κs (rational arithmetic)
  with 0.70, so a κ of exactly 0.70 passes.
- Gold labels (§8) follow the first reading in `ADJ_READINGS`: eligible coders
  vote (the PI too when eligible), ties go to the PI's label, valence is voted
  among the voters who marked the fragment relevant. Two other readings (PI
  only breaks ties; valence voted over all labels) are reported as
  sensitivity analyses and as `alt_*` columns. The report counts PI tie-breaks
  and the gold labels the PI's label decided.
- `--channel LLM=llm_labels.csv` reads the file of `ws1_llm_channel.py`
  (§12.2) or any file with the coder columns.
- Writes `reliability_report.md`, `reliability.json`, `gold_labels.csv` (no
  fragment text) and `exclusions.csv`. Duplicate `frag_id`s stop the run. The
  report records the protocol version and sha256 it was run against.
- Dictionary v1 is `ws1_pipeline.classify`; v0 is a verbatim copy of the
  pre-stance-fix version (`7eb5a1e^`), checked against git at run time.
- Tests: `python3 tests/test_reliability.py` (cross-checks need
  `pip install scikit-learn krippendorff`).

## Notes

- The dictionary is **v0** — its whole purpose is to be tested and revised.
  An X−/X+ skew in the raw counts is expected and partly reflects dictionary
  coverage; the human-coded subsample is the ground truth that decides
  whether the instrument is trustworthy.
- Raw transcripts and verbatim-text CSVs are git-ignored (third-party
  caption copyright + size). Only code and count-level summaries are tracked.
