#!/usr/bin/env python3
"""
tests/test_practice_overlap.py - the 8 practice items of the coding page must
be constructed items, not paraphrases of the 300 evaluation fragments
(PROTOCOL_WS1.0.md section 3: "8 constructed practice items").

For every practice item in make_artifact_page.PRACTICE and every one of the 300
fragments (loaded exactly as the page loads them: coding_sample.csv if present,
else the FRAGMENTS array embedded in ws1_survey.html) it computes
  (a) the longest common run of consecutive words, case-insensitive,
      punctuation stripped;
  (b) the Jaccard similarity of the two content-word sets (stopwords removed).
It fails if any run is >= 5 words or any Jaccard is >= 0.25, and always prints
the five most similar pairs by each measure. These thresholds are a floor, not
a proof: the earlier practice set passed them too (max run 4, max Jaccard
0.205), so every item was also checked by reading all 300 fragments.

It also checks the practice-set identifier the page records (PRACTICE_SET,
exported per coder as `practice_set`), so a coder's practice score can be tied
to the items that coder saw.

Runs with plain python3 (pytest optional):
    python3 tests/test_practice_overlap.py      # or: python3 -m pytest tests/
"""
import csv, hashlib, io, json, os, re, subprocess, sys, tempfile, unittest

sys.dont_write_bytecode = True
TESTS = os.path.dirname(os.path.abspath(__file__))
WS1 = os.path.dirname(TESTS)
sys.path.insert(0, WS1)
import make_artifact_page as P  # noqa: E402

MAX_RUN = 5          # fail if a common run of this many words exists
MAX_JACCARD = 0.25   # fail if content-word Jaccard reaches this value
TOP = 5

# NLTK's English stopword list (179 words), written out so the test needs no
# download; apostrophes are removed below, exactly as in the tokenizer.
STOPWORDS = set(w.replace("'", "") for w in """
i me my myself we our ours ourselves you you're you've you'll you'd your yours
yourself yourselves he him his himself she she's her hers herself it it's its
itself they them their theirs themselves what which who whom this that that'll
these those am is are was were be been being have has had having do does did
doing a an the and but if or because as until while of at by for with about
against between into through during before after above below to from up down in
out on off over under again further then once here there when where why how all
any both each few more most other some such no nor not only own same so than too
very s t can will just don don't should should've now d ll m o re ve y ain aren
aren't couldn couldn't didn didn't doesn doesn't hadn hadn't hasn hasn't haven
haven't isn isn't ma mightn mightn't mustn mustn't needn needn't shan shan't
shouldn shouldn't wasn wasn't weren weren't won won't wouldn wouldn't
""".split())


def words(text):
    """Lower-case word tokens, punctuation stripped: apostrophes are dropped
    inside words (don't -> dont), every other non-alphanumeric splits."""
    t = text.lower().replace("’", "'").replace("‘", "'").replace("'", "")
    return re.findall(r"[a-z0-9]+", t)


def content(text):
    return {w for w in words(text) if w not in STOPWORDS}


def longest_run(a, b):
    """Longest common run of consecutive words of two token lists -> (length, words)."""
    best, end = 0, 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best, end = cur[j], i
        prev = cur
    return best, a[end - best:end]


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a or b) else 0.0


def load():
    frags, src = P.load_fragments(os.path.join(WS1, "coding_sample.csv"), os.path.join(WS1, "ws1_survey.html"))
    return frags, src


def pairs(practice, frags):
    out = []
    for k, item in enumerate(practice):
        iw, ic = words(item["text"]), content(item["text"])
        for f in frags:
            run, run_words = longest_run(iw, words(f["text"]))
            fc = content(f["text"])
            out.append({"item": k + 1, "frag_id": f["id"], "run": run, "run_words": " ".join(run_words),
                        "jaccard": jaccard(ic, fc), "shared": sorted(ic & fc)})
    return out


def report(rows):
    lines = [f"top {TOP} pairs by Jaccard of content words:"]
    for r in sorted(rows, key=lambda r: (-r["jaccard"], -r["run"], r["item"], r["frag_id"]))[:TOP]:
        lines.append(f"  item {r['item']} vs {r['frag_id']}: jaccard {r['jaccard']:.3f} "
                     f"(shared: {', '.join(r['shared'])}); longest run {r['run']}")
    lines.append(f"top {TOP} pairs by longest common run of words:")
    for r in sorted(rows, key=lambda r: (-r["run"], -r["jaccard"], r["item"], r["frag_id"]))[:TOP]:
        lines.append(f"  item {r['item']} vs {r['frag_id']}: longest run {r['run']} "
                     f"(\"{r['run_words']}\"); jaccard {r['jaccard']:.3f}")
    return "\n".join(lines)


FRAGS, FRAG_SRC = load()
ROWS = pairs(P.PRACTICE, FRAGS)


def test_inputs_complete():
    assert len(FRAGS) == 300 and len({f["id"] for f in FRAGS}) == 300, len(FRAGS)
    assert len(P.PRACTICE) == 8
    assert len(ROWS) == 8 * 300


def test_practice_items_well_formed():
    """rel in {0,1}; val in the four codes; rel 0 -> val none; one explanation per item per language."""
    for p in P.PRACTICE:
        assert set(p) == {"text", "rel", "val"}, p
        assert p["rel"] in ("0", "1") and p["val"] in ("minus", "plus", "mixed", "none"), p
        assert p["rel"] == "1" or p["val"] == "none", p
        assert p["text"].strip(), p
    for lang, d in P.I18N.items():
        why = d["practice.why"]
        assert len(why) == len(P.PRACTICE) and all(w.strip() for w in why), lang


def test_no_long_common_word_run():
    bad = [r for r in ROWS if r["run"] >= MAX_RUN]
    assert not bad, [(r["item"], r["frag_id"], r["run"], r["run_words"]) for r in bad]


def test_content_word_jaccard_below_threshold():
    bad = [r for r in ROWS if r["jaccard"] >= MAX_JACCARD]
    assert not bad, [(r["item"], r["frag_id"], round(r["jaccard"], 3), r["shared"]) for r in bad]


# Identifier of the practice set used by every page built from 17a5ebd to 61e80bb (same eight
# texts and answers throughout), computed with the rule of make_artifact_page.PRACTICE_SET.
OLD_PRACTICE_SET = "13a6364e02dc"


def practice_set_id(practice):
    return hashlib.sha256(json.dumps(practice, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()[:12]


def js_function(script, name):
    """Source of a top-level `function name(...) {...}` by brace matching."""
    start = script.index("function %s(" % name)
    depth, i = 0, script.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(script[i], 0)
        if depth == 0:
            return script[start:i + 1]
        i += 1


def test_practice_set_id():
    """PRACTICE_SET is the documented hash of the current items and answers, not the old set's."""
    assert P.PRACTICE_SET == practice_set_id(P.PRACTICE), P.PRACTICE_SET
    assert P.PRACTICE_SET != OLD_PRACTICE_SET


def test_page_records_practice_set():
    """Built page: each checked practice answer stores PRACTICE_SET, and the CSV column
    practice_set names the set(s) of the first attempts that practice_correct counts;
    entries saved by an older page (no set field) export as 'untagged'."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        raise unittest.SkipTest("node not installed")
    new = P.PRACTICE_SET
    cases = {   # name: (S.practice entries in order, expected practice_set, expected practice_correct)
        "all new": ([{"i": k, "ok": True, "set": new} for k in range(8)], new, 8),
        "all old page": ([{"i": k, "ok": k != 3} for k in range(8)], "untagged", 7),
        # items 0-2 checked on the old page, then republished; item 0 re-checked on the new page
        # (a later entry, so not a first attempt and not counted)
        "crossed republish": ([{"i": k, "ok": True} for k in range(3)] + [{"i": 0, "ok": False, "set": new}]
                              + [{"i": k, "ok": k != 5, "set": new} for k in range(3, 8)],
                              f"{new}+untagged", 7),
    }
    with tempfile.TemporaryDirectory() as d:
        page = os.path.join(d, "page.html")
        subprocess.run([sys.executable, os.path.join(WS1, "make_artifact_page.py"), "--out", page],
                       check=True, capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        script = re.search(r"<script>(.*?)</script>", open(page, encoding="utf-8").read(), re.S).group(1)
        assert f'const PRACTICE_SET = "{new}";' in script
        assert "set: PRACTICE_SET" in js_function(script, "showFeedback")
        fns = "\n".join(js_function(script, n) for n in ("csvCell", "practiceFirst", "buildCSV"))
        frags = FRAGS[:2]
        for name, (practice, want_set, want_ok) in cases.items():
            S = {"coder": "T", "seed": 1, "startedAt": "s", "finishedAt": "e", "lang": "en", "english": "good",
                 "source": "public", "practice": practice,
                 "answers": [{"frag_id": f["id"], "rel": "0", "val": "none", "position": k + 1, "secs": 5}
                             for k, f in enumerate(frags)]}
            js = (f"const FRAGMENTS = {json.dumps(frags)};\nconst CODEBOOK = 'v1'; let LANG = 'en';\n"
                  f"let S = JSON.parse(JSON.stringify({json.dumps(S)}));\n{fns}\n"
                  "process.stdout.write(buildCSV());\n")
            jf = os.path.join(d, "t.js")
            open(jf, "w", encoding="utf-8").write(js)
            out = subprocess.run(["node", jf], capture_output=True, text=True, check=True).stdout
            rows = list(csv.DictReader(io.StringIO(out)))
            assert len(rows) == 2, (name, out)
            got = {(r["practice_set"], r["practice_correct"], r["practice_n"]) for r in rows}
            assert got == {(want_set, str(want_ok), "8")}, (name, got)


def main():
    print(f"fragments: {len(FRAGS)} from {os.path.basename(FRAG_SRC)}; practice items: {len(P.PRACTICE)}; "
          f"pairs: {len(ROWS)}; fail if run >= {MAX_RUN} words or Jaccard >= {MAX_JACCARD}")
    print(f"max longest run: {max(r['run'] for r in ROWS)} words; max Jaccard: {max(r['jaccard'] for r in ROWS):.3f}")
    print(report(ROWS))
    print(f"practice set: {P.PRACTICE_SET} (earlier set: {OLD_PRACTICE_SET})")
    fails = 0
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_") and callable(v)]:
        try:
            fn()
            print(f"PASS  {name}")
        except unittest.SkipTest as e:
            print(f"SKIP  {name}: {e}")
        except AssertionError as e:
            print(f"FAIL  {name}: {e}")
            fails += 1
    print(f"\n{'FAILED' if fails else 'OK'}: {fails} failing test(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
