"""
ws1_pipeline.py - WS1.0 validation-gate pipeline (REAL DATA).

Reads cleaned YouTube transcripts (one *.txt per video, produced by
clean_vtt.py), segments them into codeable fragments, and applies the
transparent DICTIONARY classifier (one of the two pre-registered channels;
the LLM channel is applied separately). Produces:

    fragments.csv          - every fragment + dictionary labels
    coding_sample.csv      - ~N fragments with blank human-coding columns
    ws1_summary.md         - corpus + classification summary

This is the deterministic, reproducible half of the index. The whole point
of WS1.0 is to validate it (and the LLM channel) against human coding:
Cohen's kappa >= 0.70 is the go/no-go gate (see ws1_kappa.py).

Usage:
    python3 ws1_pipeline.py [--dir .] [--window 3] [--sample 300]
"""
import os, re, csv, glob, argparse, random

# ---- dictionaries (transparent, editable; v0 to be refined after WS1.0) ----
AI_TERMS = [
    "ai", "a.i.", "artificial intelligence", "chatgpt", "chat gpt", "gpt",
    "llm", "generative ai", "gen ai", "genai", "automation", "automate",
    "automated", "algorithm", "machine learning", "chatbot", "ai agent",
    "agentic", "openai", "anthropic", "claude", "gemini", "copilot", "robot",
]
OCC_TERMS = [
    "job", "jobs", "worker", "workers", "employee", "employees", "role",
    "roles", "position", "staff", "headcount", "workforce", "profession",
    "occupation", "hiring", "hire", "career", "white-collar", "white collar",
    "blue-collar", "blue collar", "entry-level", "entry level", "engineer",
    "developer", "programmer", "coder", "lawyer", "paralegal", "accountant",
    "analyst", "customer service", "customer support", "writer", "intern",
    "internship", "manager", "radiologist", "physician", "doctor", "teller",
    "bookkeeper", "clerk", "software engineer", "associate", "assistant",
]
DISPLACE_TERMS = [   # X- (destruction)
    "replace", "replacing", "replaced", "layoff", "layoffs", "laid off",
    "lay off", "fired", "firing", "fire ", "cut ", "cuts", "cutting",
    "eliminate", "eliminated", "eliminating", "displacement", "displace",
    "displaced", "lose their job", "lose your job", "losing jobs",
    "job loss", "job losses", "unemployment", "obsolete", "redundant",
    "downsize", "slash", "slashed", "wipe out", "purge", "take your job",
    "take our job", "took their job", "replace your job", "replace workers",
    "replace humans", "replacing humans", "no way in", "stop hiring",
    "hiring freeze", "avoid hiring",
]
CREATE_TERMS = [     # X+ (creation / augmentation / skeptical-debunk)
    "new job", "new jobs", "new role", "new roles", "created", "creating",
    "job creation", "create jobs", "hiring back", "rehire", "rehiring",
    "rehired", "augment", "augmentation", "opportunity", "opportunities",
    "demand for", "complement", "ai won't", "won't replace", "not replace",
    "didn't replace", "doesn't replace", "no evidence", "overstated",
    "exaggerat", "cover story", "excuse", "ai washing", "myth", "not happening",
    "no good evidence", "isn't replacing", "negligible", "augmenting",
    "new opportunities", "didn't take", "create new", "won't take your job",
]

BRACKET = re.compile(r"\[[^\]]*\]")            # [music], [laughter], ...
ARROWS = re.compile(r"&gt;|&gt;&gt;|>>|>")
AMP = re.compile(r"&amp;")
NBSP = re.compile(r"&nbsp;| ")
WS = re.compile(r"\s+")
SENT = re.compile(r"(?<=[.!?])\s+")


def clean_text(t):
    t = BRACKET.sub(" ", t)
    t = ARROWS.sub(" ", t)
    t = AMP.sub("&", t)
    t = NBSP.sub(" ", t)
    t = WS.sub(" ", t)
    return t.strip()


def has_any(text, terms):
    hits = [w for w in terms if w in text]
    return hits


def classify(frag):
    low = " " + frag.lower() + " "
    ai = has_any(low, AI_TERMS)
    occ = has_any(low, OCC_TERMS)
    dis = has_any(low, DISPLACE_TERMS)
    cre = has_any(low, CREATE_TERMS)
    relevant = bool(ai) and bool(occ) and (bool(dis) or bool(cre))
    if not relevant:
        valence = "none"
    elif len(dis) > len(cre):
        valence = "minus"
    elif len(cre) > len(dis):
        valence = "plus"
    else:
        valence = "mixed"
    return ai, occ, dis, cre, relevant, valence


def segment(text, target_words):
    """Pack sentences into ~target_words fragments; hard-split run-on
    sentences (YouTube auto-captions often carry no punctuation at all,
    which would otherwise collapse a whole video into one fragment)."""
    sents = [s.strip() for s in SENT.split(text) if s.strip()]
    frags, cur, cur_w = [], [], 0
    for s in sents:
        words = s.split()
        if len(words) > target_words * 1.6:       # run-on -> hard word-split
            if cur:
                frags.append(" ".join(cur)); cur, cur_w = [], 0
            for k in range(0, len(words), target_words):
                frags.append(" ".join(words[k:k + target_words]))
            continue
        cur.append(s); cur_w += len(words)
        if cur_w >= target_words:
            frags.append(" ".join(cur)); cur, cur_w = [], 0
    if cur:
        frags.append(" ".join(cur))
    return [f for f in frags if len(f.split()) >= 5]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".")
    ap.add_argument("--target-words", type=int, default=50, dest="target_words")
    ap.add_argument("--sample", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    files = sorted(f for f in glob.glob(os.path.join(args.dir, "*.txt"))
                   if os.path.basename(f) != "ALL_TRANSCRIPTS.txt")
    if not files:
        print("No transcript .txt files found in", os.path.abspath(args.dir))
        raise SystemExit(1)

    rows = []
    per_video = {}
    for f in files:
        vid = re.sub(r"\.txt$", "", os.path.basename(f))
        raw = open(f, encoding="utf-8", errors="ignore").read()
        text = clean_text(raw)
        frags = segment(text, args.target_words)
        counts = {"n": 0, "rel": 0, "minus": 0, "plus": 0, "mixed": 0}
        for j, fr in enumerate(frags):
            ai, occ, dis, cre, rel, val = classify(fr)
            rows.append({
                "video_id": vid, "frag_id": f"{vid}_{j:03d}", "text": fr,
                "ai": "|".join(ai), "occ": "|".join(occ),
                "displace": "|".join(dis), "create": "|".join(cre),
                "relevant": int(rel), "valence_dict": val,
            })
            counts["n"] += 1
            if rel:
                counts["rel"] += 1
                counts[val] = counts.get(val, 0) + 1
        per_video[vid] = counts

    # write all fragments
    out = os.path.join(args.dir, "fragments.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # coding sample: enrich for relevance (~70% relevant, 30% not) so coders
    # see both classes; blank human columns to fill in.
    rng = random.Random(args.seed)
    rel_rows = [r for r in rows if r["relevant"] == 1]
    non_rows = [r for r in rows if r["relevant"] == 0]
    n_rel = min(len(rel_rows), int(args.sample * 0.7))
    n_non = min(len(non_rows), args.sample - n_rel)
    sample = rng.sample(rel_rows, n_rel) + rng.sample(non_rows, n_non)
    rng.shuffle(sample)
    cs = os.path.join(args.dir, "coding_sample.csv")
    with open(cs, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frag_id", "text", "human_relevant_0_1",
                    "human_valence_minus_plus_none"])
        for r in sample:
            w.writerow([r["frag_id"], r["text"], "", ""])

    # summary
    tot = len(rows)
    rel = sum(r["relevant"] for r in rows)
    minus = sum(1 for r in rows if r["valence_dict"] == "minus")
    plus = sum(1 for r in rows if r["valence_dict"] == "plus")
    mixed = sum(1 for r in rows if r["valence_dict"] == "mixed")
    sm = os.path.join(args.dir, "ws1_summary.md")
    with open(sm, "w", encoding="utf-8") as fh:
        fh.write("# WS1.0 Dictionary-Classification Summary (REAL DATA)\n\n")
        fh.write(f"- Videos: {len(files)}\n")
        fh.write(f"- Fragments (~{args.target_words} words each): {tot}\n")
        fh.write(f"- AI x occupation relevant: {rel} ({rel/tot*100:.1f}%)\n")
        fh.write(f"- Destruction (X-): {minus}\n")
        fh.write(f"- Creation/skeptical (X+): {plus}\n")
        fh.write(f"- Mixed: {mixed}\n")
        fh.write(f"- Coding sample for human validation: {len(sample)} "
                 f"-> coding_sample.csv\n\n")
        fh.write("## Per-video\n\n")
        fh.write("| video | frags | relevant | X- | X+ | mixed |\n")
        fh.write("|-------|-------|----------|----|----|-------|\n")
        for vid, c in per_video.items():
            fh.write(f"| {vid} | {c['n']} | {c['rel']} | {c['minus']} "
                     f"| {c['plus']} | {c.get('mixed',0)} |\n")

    print(f"videos={len(files)} fragments={tot} relevant={rel} "
          f"X-={minus} X+={plus} mixed={mixed}")
    print(f"-> fragments.csv, coding_sample.csv ({len(sample)} rows), ws1_summary.md")


if __name__ == "__main__":
    main()
