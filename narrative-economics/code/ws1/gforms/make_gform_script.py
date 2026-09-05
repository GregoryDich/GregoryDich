#!/usr/bin/env python3
"""
make_gform_script.py - fill build_form.template.gs with the coding-sample
fragments -> generated/build_form.gs (paste into script.google.com).

Fragments come from ../coding_sample.csv (git-ignored: verbatim caption text).
If that file is missing they are recovered from ../ws1_survey.html, which
embeds the same fragments; --restore-sample writes coding_sample.csv back.

Usage:
    python3 make_gform_script.py                      # defaults
    python3 make_gform_script.py --restore-sample     # also rebuild coding_sample.csv from the HTML
"""
import argparse, csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
WS1 = os.path.dirname(HERE)


def load_from_csv(path):
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return [{"id": r["frag_id"], "text": r["text"]} for r in rows]


def load_from_html(path):
    html = open(path, encoding="utf-8").read()
    marker = "const FRAGMENTS = "
    i = html.index(marker) + len(marker)
    frags, _ = json.JSONDecoder().raw_decode(html, i)
    return frags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default=os.path.join(WS1, "coding_sample.csv"))
    ap.add_argument("--html", default=os.path.join(WS1, "ws1_survey.html"))
    ap.add_argument("--template", default=os.path.join(HERE, "build_form.template.gs"))
    ap.add_argument("--out", default=os.path.join(HERE, "generated", "build_form.gs"))
    ap.add_argument("--restore-sample", action="store_true",
                    help="if coding_sample.csv is missing, recreate it from the HTML")
    args = ap.parse_args()

    if os.path.exists(args.sample):
        frags, src = load_from_csv(args.sample), args.sample
    elif os.path.exists(args.html):
        frags, src = load_from_html(args.html), args.html
        if args.restore_sample:
            with open(args.sample, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["frag_id", "text", "human_relevant_0_1",
                            "human_valence_minus_plus_none"])
                for f in frags:
                    w.writerow([f["id"], f["text"], "", ""])
            print(f"restored {args.sample} ({len(frags)} rows)")
    else:
        raise SystemExit("no coding_sample.csv and no ws1_survey.html to recover from")

    ids = [f["id"] for f in frags]
    assert len(ids) == len(set(ids)), "duplicate frag_id in sample"
    assert all(f["text"].strip() for f in frags), "empty fragment text"

    template = open(args.template, encoding="utf-8").read()
    assert template.count("__FRAGMENTS_JSON__") == 1, "template placeholder missing/duplicated"
    # ASCII-only JSON so the file survives any copy-paste path into the Apps Script editor
    payload = json.dumps(frags, ensure_ascii=True, separators=(",", ":"))
    out = template.replace("__FRAGMENTS_JSON__", payload)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(out)

    words = sum(len(f["text"].split()) for f in frags)
    print(f"fragments: {len(frags)} (from {os.path.relpath(src, WS1)}), "
          f"~{words / len(frags):.0f} words each")
    print(f"wrote {os.path.relpath(args.out, WS1)} ({len(out) / 1024:.0f} KB)")
    print("next: script.google.com -> New project -> paste the file -> set CODER -> Run buildForm")


if __name__ == "__main__":
    main()
