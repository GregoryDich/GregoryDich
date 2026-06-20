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
3. **Human coding.** Two independent coders label `coding_sample.csv`
   (`human_relevant_0_1`, `human_valence_minus_plus_none`), blind to each
   other and to the machine labels.
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

## Notes

- The dictionary is **v0** — its whole purpose is to be tested and revised.
  An X−/X+ skew in the raw counts is expected and partly reflects dictionary
  coverage; the human-coded subsample is the ground truth that decides
  whether the instrument is trustworthy.
- Raw transcripts and verbatim-text CSVs are git-ignored (third-party
  caption copyright + size). Only code and count-level summaries are tracked.
