"""
ws1_kappa.py - Cohen's kappa for the WS1.0 validation gate.

Computes inter-rater agreement between any two label columns in a CSV
(e.g. human vs dictionary, human vs LLM, or human vs human). The
pre-registered go/no-go threshold is kappa >= 0.70; below that the
classifier is revised before the full WS1 index is built.

Pure stdlib (no sklearn). Usage:
    python3 ws1_kappa.py --csv labelled.csv --col-a human_relevant_0_1 \
                         --col-b dict_relevant
"""
import csv, argparse


def cohen_kappa(pairs):
    """pairs: list of (a, b) categorical labels (strings)."""
    pairs = [(str(a).strip(), str(b).strip()) for a, b in pairs
             if str(a).strip() != "" and str(b).strip() != ""]
    n = len(pairs)
    if n == 0:
        return None, 0, {}
    cats = sorted({c for ab in pairs for c in ab})
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    pa = {c: sum(1 for a, _ in pairs if a == c) / n for c in cats}
    pb = {c: sum(1 for _, b in pairs if b == c) / n for c in cats}
    pe = sum(pa[c] * pb[c] for c in cats)
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 1e-12 else 1.0
    return kappa, n, {"po": po, "pe": pe, "cats": cats,
                      "agree": agree}


def interpret(k):
    if k is None:
        return "no overlapping labels"
    if k < 0:    return "worse than chance"
    if k < 0.20: return "slight"
    if k < 0.40: return "fair"
    if k < 0.60: return "moderate"
    if k < 0.70: return "substantial (below gate)"
    if k < 0.80: return "substantial (PASS)"
    return "almost perfect (PASS)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--col-a", required=True)
    ap.add_argument("--col-b", required=True)
    ap.add_argument("--gate", type=float, default=0.70)
    args = ap.parse_args()

    with open(args.csv, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for c in (args.col_a, args.col_b):
        if rows and c not in rows[0]:
            raise SystemExit(f"column '{c}' not in CSV. "
                             f"Have: {list(rows[0].keys())}")
    pairs = [(r[args.col_a], r[args.col_b]) for r in rows]
    k, n, info = cohen_kappa(pairs)

    print(f"  pairs scored : {n}")
    if k is None:
        print("  no overlapping non-empty labels"); return
    print(f"  categories   : {info['cats']}")
    print(f"  observed agr : {info['po']:.3f} ({info['agree']}/{n})")
    print(f"  expected agr : {info['pe']:.3f}")
    print(f"  Cohen's kappa: {k:.3f}  [{interpret(k)}]")
    print(f"  gate (>= {args.gate}): "
          f"{'PASS' if k >= args.gate else 'FAIL -> revise classifier'}")


if __name__ == "__main__":
    main()
