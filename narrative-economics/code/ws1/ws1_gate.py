"""
ws1_gate.py — WS1.0 validation gate: all κ pairs.

Merges two human-coded CSVs with dictionary labels from fragments.csv,
computes Cohen's κ for every pair × dimension, and reports the gate.
"""
import csv, sys, os

sys.path.insert(0, os.path.dirname(__file__))
from ws1_kappa import cohen_kappa, interpret


def load_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def relevance_label(row, col="human_relevant_0_1"):
    v = str(row.get(col, "")).strip()
    return v if v in ("0", "1") else None


def valence_label(row, col="human_valence_minus_plus_none"):
    v = str(row.get(col, "")).strip().lower()
    return v if v in ("minus", "plus", "none", "mixed") else None


def compute_and_print(name, pairs_raw):
    pairs = [(a, b) for a, b in pairs_raw if a is not None and b is not None]
    k, n, info = cohen_kappa(pairs)
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"  pairs: {n}")
    if k is None:
        print("  NO OVERLAPPING LABELS")
        return None
    print(f"  categories : {info['cats']}")
    print(f"  observed   : {info['po']:.3f} ({info['agree']}/{n})")
    print(f"  expected   : {info['pe']:.3f}")
    print(f"  κ = {k:.4f}  [{interpret(k)}]")
    gate = k >= 0.70
    print(f"  gate ≥ 0.70: {'PASS ✓' if gate else 'FAIL ✗'}")
    return k


def main():
    h1_path = sys.argv[1]
    h2_path = sys.argv[2]
    frag_path = sys.argv[3] if len(sys.argv) > 3 else None

    h1_rows = load_csv(h1_path)
    h2_rows = load_csv(h2_path)
    h1 = {r["frag_id"]: r for r in h1_rows}
    h2 = {r["frag_id"]: r for r in h2_rows}

    frag = {}
    if frag_path:
        frag_rows = load_csv(frag_path)
        frag = {r["frag_id"]: r for r in frag_rows}

    common_ids = sorted(set(h1) & set(h2))
    print(f"Human-1 rows: {len(h1)}")
    print(f"Human-2 rows: {len(h2)}")
    print(f"Common frag_ids: {len(common_ids)}")
    if frag:
        print(f"Dictionary fragments: {len(frag)}")
        print(f"Overlap with human sample: {len(set(common_ids) & set(frag))}")

    results = {}

    # --- Inter-human ---
    pairs_rel = [(relevance_label(h1[fid]), relevance_label(h2[fid]))
                 for fid in common_ids]
    results["H1 vs H2 — relevance"] = compute_and_print(
        "INTER-HUMAN: relevance (0/1)", pairs_rel)

    pairs_val = [(valence_label(h1[fid]), valence_label(h2[fid]))
                 for fid in common_ids]
    results["H1 vs H2 — valence"] = compute_and_print(
        "INTER-HUMAN: valence (minus/plus/none/mixed)", pairs_val)

    # only among jointly-relevant fragments
    pairs_val_rel = [(valence_label(h1[fid]), valence_label(h2[fid]))
                     for fid in common_ids
                     if relevance_label(h1[fid]) == "1"
                     and relevance_label(h2[fid]) == "1"]
    results["H1 vs H2 — valence|rel"] = compute_and_print(
        "INTER-HUMAN: valence among BOTH-relevant", pairs_val_rel)

    # --- Human vs Dictionary ---
    if frag:
        for label, hx, name in [("H1", h1, "Human-1"), ("H2", h2, "Human-2")]:
            ids = sorted(set(hx) & set(frag))
            dict_rel = [(relevance_label(hx[fid]),
                         str(frag[fid]["relevant"]))
                        for fid in ids]
            results[f"{label} vs Dict — relevance"] = compute_and_print(
                f"{name} vs DICTIONARY: relevance (0/1)", dict_rel)

            dict_val = [(valence_label(hx[fid]),
                         frag[fid]["valence_dict"].strip())
                        for fid in ids
                        if valence_label(hx[fid]) is not None
                        and frag[fid]["valence_dict"].strip() != ""]
            results[f"{label} vs Dict — valence"] = compute_and_print(
                f"{name} vs DICTIONARY: valence", dict_val)

            dict_val_rel = [(valence_label(hx[fid]),
                             frag[fid]["valence_dict"].strip())
                            for fid in ids
                            if relevance_label(hx[fid]) == "1"
                            and str(frag[fid]["relevant"]) == "1"]
            results[f"{label} vs Dict — valence|rel"] = compute_and_print(
                f"{name} vs DICTIONARY: valence among BOTH-relevant", dict_val_rel)

    # --- Summary ---
    print(f"\n{'='*60}")
    print("SUMMARY TABLE")
    print(f"{'='*60}")
    print(f"{'Comparison':<40} {'κ':>8} {'Gate':>8}")
    print(f"{'-'*40} {'-'*8} {'-'*8}")
    for name, k in results.items():
        if k is None:
            print(f"{name:<40} {'N/A':>8} {'—':>8}")
        else:
            gate = "PASS" if k >= 0.70 else "FAIL"
            print(f"{name:<40} {k:>8.3f} {gate:>8}")

    # --- Disagreement analysis ---
    print(f"\n{'='*60}")
    print("DISAGREEMENT EXAMPLES (inter-human, relevance)")
    print(f"{'='*60}")
    disagree = [(fid, h1[fid], h2[fid]) for fid in common_ids
                if relevance_label(h1[fid]) != relevance_label(h2[fid])
                and relevance_label(h1[fid]) is not None
                and relevance_label(h2[fid]) is not None]
    print(f"Total disagreements: {len(disagree)}")
    for fid, r1, r2 in disagree[:10]:
        print(f"\n  {fid}: H1={r1['human_relevant_0_1']} H2={r2['human_relevant_0_1']}")
        text = r1.get("text", "")[:120]
        print(f"    \"{text}...\"")

    print(f"\n{'='*60}")
    print("DISAGREEMENT EXAMPLES (inter-human, valence)")
    print(f"{'='*60}")
    disagree_v = [(fid, h1[fid], h2[fid]) for fid in common_ids
                  if valence_label(h1[fid]) != valence_label(h2[fid])
                  and valence_label(h1[fid]) is not None
                  and valence_label(h2[fid]) is not None]
    print(f"Total disagreements: {len(disagree_v)}")
    for fid, r1, r2 in disagree_v[:10]:
        print(f"\n  {fid}: H1={r1['human_valence_minus_plus_none']} H2={r2['human_valence_minus_plus_none']}")
        text = r1.get("text", "")[:120]
        print(f"    \"{text}...\"")


if __name__ == "__main__":
    main()
