#!/usr/bin/env python3
"""
gforms_to_csv.py - convert a Google Forms responses export (wide: one column
per question) into the long per-coder CSV that ws1_gate.py / ws1_kappa.py read.

Get the export: open the form -> Responses -> three-dot menu ->
"Download responses (.csv)". (Linking to Sheets and File -> Download -> CSV
gives the same layout.)

Usage:
    python3 gforms_to_csv.py responses.csv [--sample ../coding_sample.csv] [--out-dir .]

Writes one file per submitted response: ws1_coded_<coder>.csv with columns
    frag_id, text, human_relevant_0_1, human_valence_minus_plus_none
"""
import argparse, csv, os, re

QCOL = re.compile(r"^\[([^\]]+)\]\s*([12])\.")   # "[frag_id] 1. ..." / "[frag_id] 2. ..."


def map_rel(v):
    v = v.strip().lower()
    if v.startswith("yes"): return "1"
    if v.startswith("no"):  return "0"
    return None


def map_val(v):
    v = v.strip().lower()
    if "(minus)" in v or v.startswith("alarming"):   return "minus"
    if "(plus)" in v or v.startswith("reassuring"):  return "plus"
    if v.startswith("mixed"):                        return "mixed"
    if "(none)" in v or v.startswith("neutral"):     return "none"
    return None


def safe_name(s):
    s = re.sub(r"[^A-Za-z0-9_\-]+", "_", s.strip()).strip("_")
    return s or "coder"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses")
    ap.add_argument("--sample", default=None, help="coding_sample.csv, to attach fragment text")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    with open(args.responses, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    if len(rows) < 2:
        raise SystemExit("no responses in the export yet")
    header, data = rows[0], rows[1:]

    # map columns -> (frag_id, question number)
    qcols, name_col = {}, None
    for j, h in enumerate(header):
        m = QCOL.match(h.strip())
        if m:
            qcols[j] = (m.group(1), int(m.group(2)))
        elif "coder" in h.lower() or "your name" in h.lower():
            name_col = j
    frag_ids = sorted({fid for fid, _ in qcols.values()})
    if not frag_ids:
        raise SystemExit("no '[frag_id] 1./2.' question columns found - is this the right export?")
    print(f"export: {len(data)} response(s), {len(frag_ids)} fragments, "
          f"{len(qcols)} question columns")

    text = {}
    if args.sample and os.path.exists(args.sample):
        with open(args.sample, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                text[r["frag_id"]] = r["text"]

    os.makedirs(args.out_dir, exist_ok=True)
    used = {}
    for k, row in enumerate(data, 1):
        coder = row[name_col].strip() if name_col is not None and name_col < len(row) else ""
        coder = safe_name(coder or f"response{k}")
        used[coder] = used.get(coder, 0) + 1
        if used[coder] > 1:
            coder = f"{coder}_{used[coder]}"
            print(f"  ! duplicate coder name in row {k} -> writing as {coder}")

        rel, val = {}, {}
        for j, (fid, q) in qcols.items():
            v = row[j] if j < len(row) else ""
            if q == 1: rel[fid] = map_rel(v)
            else:      val[fid] = map_val(v)

        answered = sum(1 for fid in frag_ids if rel.get(fid) is not None)
        inconsistent = 0
        out_rows = []
        for fid in frag_ids:
            r = rel.get(fid)
            v = val.get(fid)
            if r == "0":
                v = "none"                       # valence page was skipped by design
            elif r == "1" and v is None:
                v, inconsistent = "none", inconsistent + 1
            out_rows.append([fid, text.get(fid, ""), r if r is not None else "", v or ""])

        path = os.path.join(args.out_dir, f"ws1_coded_{coder}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["frag_id", "text", "human_relevant_0_1", "human_valence_minus_plus_none"])
            w.writerows(out_rows)

        n_rel = sum(1 for r in out_rows if r[2] == "1")
        flag = "" if answered == len(frag_ids) else f"  ! INCOMPLETE ({answered}/{len(frag_ids)} answered)"
        flag += f"  ! {inconsistent} relevant rows without valence" if inconsistent else ""
        print(f"  {coder}: relevant {n_rel}/{answered} -> {path}{flag}")

    print("next: python3 ../ws1_gate.py ws1_coded_A.csv ws1_coded_B.csv ../fragments.csv")


if __name__ == "__main__":
    main()
