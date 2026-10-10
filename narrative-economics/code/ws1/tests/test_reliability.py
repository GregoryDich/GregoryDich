#!/usr/bin/env python3
"""
tests/test_reliability.py - validation of ws1_reliability.py (and of the
practice-score export in make_artifact_page.py).

Runs with plain python3 (pytest optional):
    python3 tests/test_reliability.py            # or: python3 -m pytest tests/
The cross-checks need scikit-learn and krippendorff in the environment
(pip install scikit-learn krippendorff); ws1_reliability.py itself stays
stdlib-only. Tests that need a missing package, git history or node are
reported as SKIP, never silently passed.

All coder data here are SYNTHETIC (simulated or constructed labels on the
real fragment ids); nothing in this file is human coding.

Besides cross-checks of the statistics, the tests pin the protocol's
decisions on constructed data where the right answer is known exactly: the
section-9 outcome at and around the 0.70 boundary, which coders form the
primary pairs (and that a wrong choice flips the outcome), the inclusion
thresholds at their boundaries, the fragments of the conditional valence set,
the gold rule of D36.1 (the PI never votes, only breaks ties; tie-breaks
counted separately for relevance and valence; unresolved fragments listed),
the section-12 fragment exclusions (checked against an independent run on the
reduced fragment set) and the llm_labels.csv status handling.
"""
import csv, io, json, os, random, re, subprocess, sys, tempfile, unittest
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from fractions import Fraction

TESTS = os.path.dirname(os.path.abspath(__file__))
WS1 = os.path.dirname(TESTS)
sys.path.insert(0, WS1)
import ws1_reliability as R  # noqa: E402

REF, REF_SRC = R.load_reference()
IDS = sorted(REF)
VAL = R.VAL_CATS
PAGE_HEAD = ["frag_id", "text", "human_relevant_0_1", "human_valence_minus_plus_none", "position",
             "time_seconds", "coder", "codebook_version", "order_seed", "session_start", "session_end",
             "ui_language", "english_level", "source", "practice_correct", "practice_n"]


# ---------------------------------------------------------------------------
# simulation: gold labels + coders with known confusion rates
# ---------------------------------------------------------------------------
GOLD = {("0", "none"): 0.55, ("1", "minus"): 0.45 * 0.45, ("1", "plus"): 0.45 * 0.30,
        ("1", "mixed"): 0.45 * 0.05, ("1", "none"): 0.45 * 0.20}
FP_VAL = {"none": 0.5, "minus": 0.3, "plus": 0.15, "mixed": 0.05}


def coder_model(sens, spec, q):
    """P(label | gold): says relevant with prob sens (gold 1) or 1-spec (gold 0);
    if relevant and gold relevant, the gold valence with prob q, else one of the
    other three uniformly; false positives get valence from FP_VAL."""
    def model(g):
        r, v = g
        p1 = sens if r == "1" else 1 - spec
        out = {("0", "none"): 1 - p1}
        for c in VAL:
            out[("1", c)] = p1 * ((q if c == v else (1 - q) / 3) if r == "1" else FP_VAL[c])
        return out
    return model


def kappa_from_joint(J):
    tot = sum(J.values())
    po = sum(p for (a, b), p in J.items() if a == b) / tot
    ma, mb = defaultdict(float), defaultdict(float)
    for (a, b), p in J.items():
        ma[a] += p / tot
        mb[b] += p / tot
    pe = sum(ma[k] * mb[k] for k in ma)
    return (po - pe) / (1 - pe), po, ma, mb


def analytic(model_a, model_b, gold=GOLD):
    """Population kappa for the three protocol dimensions, plus Scott's pi
    (the large-sample limit of Krippendorff's alpha for two coders)."""
    joint = defaultdict(float)
    for g, pg in gold.items():
        for la, pa in model_a(g).items():
            for lb, pb in model_b(g).items():
                joint[(la, lb)] += pg * pa * pb
    rel, vall, vcond = defaultdict(float), defaultdict(float), defaultdict(float)
    for ((ra, va), (rb, vb)), p in joint.items():
        rel[(ra, rb)] += p
        vall[(va, vb)] += p
        if ra == "1" and rb == "1":
            vcond[(va, vb)] += p
    out = {"relevance": kappa_from_joint(rel)[0], "valence_all": kappa_from_joint(vall)[0],
           "valence_conditional": kappa_from_joint(vcond)[0]}
    _, po, ma, mb = kappa_from_joint(rel)
    pe = sum(((ma[k] + mb[k]) / 2) ** 2 for k in set(ma) | set(mb))
    out["scott_pi_relevance"] = (po - pe) / (1 - pe)
    return out


def draw(dist, rng):
    keys = list(dist)
    return rng.choices(keys, weights=[dist[k] for k in keys])[0]


def simulate(n, models, seed, gold=GOLD):
    rng = random.Random(seed)
    golds = [draw(gold, rng) for _ in range(n)]
    return golds, [[draw(m(g), rng) for g in golds] for m in models]


# ---------------------------------------------------------------------------
# synthetic coder files in the three formats
# ---------------------------------------------------------------------------
def write_page(path, coder, labels, source="public", english="fluent", ui="en", practice=(8, 8),
               times=None, bom=False, drop=(), extra_rows=(), seed=0, ref=None, practice_set=None):
    """labels: {fid: (rel, val)}; practice=None -> no practice columns (pre-fix export);
    practice_set: None -> no practice_set column (export before that column existed);
    ref: {fid: text} of another fragment set (default: the real 300)."""
    rng = random.Random(seed)
    ref = REF if ref is None else ref
    head = (PAGE_HEAD if practice is not None else PAGE_HEAD[:-2]) + (["practice_set"] if practice_set else [])
    order = [f for f in sorted(ref) if f not in drop]
    rng.shuffle(order)
    pos = {f: i + 1 for i, f in enumerate(order)}
    with open(path, "w", newline="", encoding="utf-8-sig" if bom else "utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        for fid in sorted(pos):
            rel, val = labels[fid]
            t = times[fid] if times else max(1, int(rng.lognormvariate(2.0, 0.5)))
            row = [fid, ref[fid], rel, val, pos[fid], t, coder, "v1", 12345,
                   "2026-10-01T10:00:00.000Z", "2026-10-01T10:45:00.000Z", ui, english, source]
            w.writerow(row + (list(practice) if practice is not None else []) + ([practice_set] if practice_set else []))
        for row in extra_rows:
            w.writerow(row)
    return path


def write_basic(path, labels, with_text=True, drop=()):
    """The 4-column format of gforms_to_csv.py (with_text=False, no --sample) or
    ws1_survey.html (with_text=True)."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frag_id", "text", "human_relevant_0_1", "human_valence_minus_plus_none"])
        for fid in IDS:
            if fid in drop:
                continue
            rel, val = labels[fid]
            w.writerow([fid, REF[fid] if with_text else "", rel, val])
    return path


def write_meta(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["coder", "source", "english_level", "practice_correct", "practice_n"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def sim_labels(n_coders, seed, sens=0.9, spec=0.9, q=0.8):
    golds, labs = simulate(len(IDS), [coder_model(sens, spec, q)] * n_coders, seed)
    return golds, [dict(zip(IDS, lab)) for lab in labs]


def make_synthetic_page_set(out_dir, seed=11, excluded=False):
    """SYNTHETIC page-format CSVs: the PI and two publicly recruited coders,
    plus (excluded=True) a publicly recruited coder who fails rule 5(b)."""
    _, (pi, a, b, c) = sim_labels(4, seed)
    cur = R.PRACTICE_SET_PROTOCOL
    files = [write_page(os.path.join(out_dir, "ws1_coded_SYN_PI.csv"), "SYN_PI", pi, source="researcher",
                        english="native", ui="ru", seed=seed, practice_set=cur),
             write_page(os.path.join(out_dir, "ws1_coded_SYN_public_A.csv"), "SYN_public_A", a,
                        english="fluent", ui="en", practice=(7, 8), seed=seed + 1, practice_set=cur),
             write_page(os.path.join(out_dir, "ws1_coded_SYN_public_B.csv"), "SYN_public_B", b,
                        english="good", ui="he", practice=(6, 8), seed=seed + 2, practice_set="untagged")]
    if excluded:
        files.append(write_page(os.path.join(out_dir, "ws1_coded_SYN_public_X.csv"), "SYN_public_X", c,
                                english="fluent", ui="en", practice=(5, 8), seed=seed + 3, practice_set=cur))
    return files


def write_llm_labels(path, labels, status=None, served=None, record=None):
    """llm_labels.csv in the format ws1_llm_channel.py writes (PROTOCOL 12.5.3):
    labels {fid: (rel, val)}; status {fid: status} (default ok). Rows that are
    not ok get empty labels, as the channel writes them, unless the status is
    given as (status, keep_labels=True). served: None (no model_served column)
    or {fid: model} with a default under key None. record: None, or a dict of
    run-record fields written to llm_labels_run.json next to the file
    ('labels_sha256': 'auto' = the file's real sha256)."""
    import hashlib
    status = status or {}
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["frag_id", "relevant_llm", "valence_llm", "status_llm"] + (["model_served"] if served else []))
        for f in sorted(labels):
            st = status.get(f, "ok")
            keep = isinstance(st, tuple)
            st = st[0] if keep else st
            rel, val = labels[f] if (st == "ok" or keep) else ("", "")
            w.writerow([f, rel, val, st] + ([served.get(f, served.get(None))] if served else []))
    if record is not None:
        rec = dict(record)
        if rec.get("labels_sha256") == "auto":
            rec["labels_sha256"] = hashlib.sha256(open(path, "rb").read()).hexdigest()
        with open(os.path.join(os.path.dirname(path), "llm_labels_run.json"), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    return path


def run(files, pi, meta=None, boot=200, seed=2026, **kw):
    """pi=None declares that the PI did not code (--no-pi)."""
    if pi is None:
        kw.setdefault("no_pi", True)
    return R.analyse(files, pi, R.read_meta(meta) if meta else None, boot, seed, **kw)


def write_set(d, labs, tag="", **per_coder):
    """One page file per coder; per_coder[name] = write_page keyword overrides."""
    return [write_page(os.path.join(d, f"{tag}{nm}.csv"), nm, lab, seed=i, **per_coder.get(nm, {}))
            for i, (nm, lab) in enumerate(labs.items())]


def skip(msg):
    raise unittest.SkipTest(msg)


def js_function(script, name):
    """Source of a top-level `function name(...) {...}` by brace matching
    (enough for the page's own functions, which have no braces in strings)."""
    start = script.index("function %s(" % name)
    depth, i = 0, script.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(script[i], 0)
        if depth == 0:
            return script[start:i + 1]
        i += 1


# ---------------------------------------------------------------------------
# (1) estimates vs analytic expectation
# ---------------------------------------------------------------------------
def test_kappa_matches_analytic_large_n():
    ma, mb = coder_model(0.92, 0.88, 0.80), coder_model(0.85, 0.93, 0.70)
    exp = analytic(ma, mb)
    _, (la, lb) = simulate(60000, [ma, mb], seed=1)
    pairs = {"relevance": [(a[0], b[0]) for a, b in zip(la, lb)],
             "valence_all": [(a[1], b[1]) for a, b in zip(la, lb)],
             "valence_conditional": [(a[1], b[1]) for a, b in zip(la, lb) if a[0] == "1" and b[0] == "1"]}
    for dim, P in pairs.items():
        k = R.kappa_counts(P)[0]
        assert abs(k - exp[dim]) < 0.02, (dim, k, exp[dim])
    units = [Counter([a[0], b[0]]) for a, b in zip(la, lb)]
    alpha = R.alpha_nominal(units)[0]
    assert abs(alpha - exp["scott_pi_relevance"]) < 0.02, (alpha, exp["scott_pi_relevance"])


def test_full_analysis_recovers_analytic_kappa():
    """The whole pipeline (page files -> eligibility -> primary pairs -> kappa,
    alpha) on 20,000 SYNTHETIC fragments recovers the population values within
    0.03. Sampling SD at this N, measured over 40 seeds: relevance 0.005,
    valence (all) 0.005, valence (both relevant) 0.008, so 0.03 is >= 3.8 SD and
    an error of 0.03 or more near the 0.70 gate is caught (the 300-fragment
    version allowed 0.17-0.25)."""
    m = coder_model(0.9, 0.9, 0.8)
    exp = analytic(m, m)
    N = 20000
    ref = {f"syn_{i:05d}": f"synthetic fragment number {i}" for i in range(N)}
    ids = sorted(ref)
    _, labs = simulate(N, [m, m, m], seed=5)
    with tempfile.TemporaryDirectory() as d:
        frag_csv = os.path.join(d, "fragments.csv")
        with open(frag_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["frag_id", "text"])
            w.writerows(sorted(ref.items()))
        files = [write_page(os.path.join(d, f"{nm}.csv"), nm, dict(zip(ids, lab)), ref=ref,
                            source="researcher" if nm == "PI" else "public", seed=i)
                 for i, (nm, lab) in enumerate(zip(("PI", "A", "B"), labs))]
        res = run(files, "PI", boot=0, fragments=frag_csv)
    assert res["meta"]["reference"]["n"] == N and res["primary"]["group"] == ["A", "B"]
    for dim in R.DIMS:
        v = res["primary"]["mean"][dim]["value"]
        assert abs(v - exp[dim]) < 0.03, (dim, v, exp[dim])
    # alpha over PI, A, B (three coders, same model): its large-sample limit is Scott's pi
    a = res["secondary"]["alpha"]["eligible"]["relevance"]["value"]
    assert abs(a - exp["scott_pi_relevance"]) < 0.03, (a, exp["scott_pi_relevance"])


# ---------------------------------------------------------------------------
# (2) cross-checks against sklearn and krippendorff
# ---------------------------------------------------------------------------
def test_cohen_kappa_vs_sklearn():
    try:
        from sklearn.metrics import cohen_kappa_score
    except ImportError:
        skip("scikit-learn not installed (pip install scikit-learn)")
    import warnings
    rng = random.Random(3)
    cases = 0
    for n in (5, 30, 300, 1000):
        for cats in (["0", "1"], list(VAL), ["minus", "plus"], ["a", "b", "c", "d", "e"]):
            for _ in range(10):
                bias = rng.random()
                a = [rng.choice(cats) for _ in range(n)]
                b = [x if rng.random() < bias else rng.choice(cats) for x in a]
                ours = R.kappa_counts(list(zip(a, b)))[0]
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    ref = cohen_kappa_score(a, b)
                if ref != ref:            # nan: sklearn's undefined case
                    assert ours is None
                else:
                    assert ours is not None and abs(ours - ref) < 1e-12, (ours, ref)
                cases += 1
    assert R.kappa_counts([("1", "1")] * 10)[0] is None          # pe = 1 -> undefined
    assert R.kappa_counts([])[0] is None
    assert cases == 160


def test_krippendorff_alpha_vs_package():
    try:
        import krippendorff
        import numpy as np
    except ImportError:
        skip("krippendorff/numpy not installed (pip install krippendorff)")
    rng = random.Random(4)
    for trial in range(60):
        m, n, k = rng.randint(2, 6), rng.randint(20, 300), rng.randint(2, 4)
        pmiss = rng.choice([0.0, 0.1, 0.3])
        truth = [rng.randrange(k) for _ in range(n)]
        data = [[(t if rng.random() < 0.7 else rng.randrange(k)) if rng.random() >= pmiss else None
                 for t in truth] for _ in range(m)]
        units = [Counter(data[c][u] for c in range(m) if data[c][u] is not None) for u in range(n)]
        ours = R.alpha_nominal(units)[0]
        arr = np.array([[np.nan if x is None else float(x) for x in row] for row in data])
        ref = krippendorff.alpha(reliability_data=arr, level_of_measurement="nominal")
        assert abs(ours - ref) < 1e-9, (trial, ours, ref)


def test_pipeline_numbers_vs_reference_packages():
    """The wired-up analysis (file reading, conditional subsets, alpha set)
    reproduces sklearn/krippendorff on the same labels."""
    try:
        from sklearn.metrics import cohen_kappa_score
        import krippendorff
        import numpy as np
    except ImportError:
        skip("scikit-learn/krippendorff not installed")
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b, c) = sim_labels(4, seed=21)
        files = [write_page(os.path.join(d, f"{nm}.csv"), nm, lab, seed=i)
                 for i, (nm, lab) in enumerate((("PI", pi), ("A", a), ("B", b), ("C", c)))]
        res = run(files, "PI", boot=0)
    pair = next(p for p in res["primary"]["pairs"] if (p["a"], p["b"]) == ("A", "B"))
    assert abs(pair["relevance"]["value"] - cohen_kappa_score([a[f][0] for f in IDS], [b[f][0] for f in IDS])) < 1e-12
    assert abs(pair["valence_all"]["value"] - cohen_kappa_score([a[f][1] for f in IDS], [b[f][1] for f in IDS])) < 1e-12
    both = [f for f in IDS if a[f][0] == "1" and b[f][0] == "1"]
    assert pair["valence_conditional"]["n"] == len(both)
    assert abs(pair["valence_conditional"]["value"]
               - cohen_kappa_score([a[f][1] for f in both], [b[f][1] for f in both])) < 1e-12
    code = {"0": 0, "1": 1}
    arr = np.array([[code[lab[f][0]] for f in IDS] for lab in (a, b, c, pi)], dtype=float)
    ref = krippendorff.alpha(reliability_data=arr, level_of_measurement="nominal")
    assert abs(res["secondary"]["alpha"]["eligible"]["relevance"]["value"] - ref) < 1e-9
    vcode = {v: i for i, v in enumerate(VAL)}
    arr = np.array([[vcode[lab[f][1]] if lab[f][0] == "1" else np.nan for f in IDS]
                    for lab in (a, b, c, pi)], dtype=float)
    ref = krippendorff.alpha(reliability_data=arr, level_of_measurement="nominal")
    assert abs(res["secondary"]["alpha"]["eligible"]["valence_conditional"]["value"] - ref) < 1e-9


# ---------------------------------------------------------------------------
# (3) edge cases
# ---------------------------------------------------------------------------
def test_one_coder_excluded_and_pi_never_primary():
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b, c) = sim_labels(4, seed=31)
        files = [write_page(os.path.join(d, "pi.csv"), "PI", pi, source="public", seed=1),
                 write_page(os.path.join(d, "a.csv"), "A", a, seed=2),
                 write_page(os.path.join(d, "b.csv"), "B", b, seed=3),
                 write_page(os.path.join(d, "c.csv"), "C", c, practice=(5, 8), seed=4)]
        res = run(files, "PI", boot=50)
        paths = R.write_outputs(res, os.path.join(d, "out"))
        rows = {r["coder"]: r for r in csv.DictReader(open(paths["exclusions"], encoding="utf-8"))}
    assert res["eligible"] == ["A", "B", "PI"]
    assert res["primary"]["group"] == ["A", "B"]           # PI is public and eligible, still not primary
    assert res["coders"]["C"]["rules"]["b"]["status"] == R.FAIL
    assert any("(b) FAILED" in r for r in res["coders"]["C"]["reasons"])
    assert rows["C"]["eligible"] == "no" and rows["C"]["rule_b"] == "fail" and "(b)" in rows["C"]["reasons"]
    assert rows["A"]["in_primary_pairs"] == "yes" and rows["PI"]["in_primary_pairs"] == "no"
    assert {r["other"] for r in res["secondary"]["pi_vs_each"]} == {"A", "B", "C"}
    for key in ("by_source", "by_ui_language"):         # section 7 groups: eligible non-PI coders only
        members = sorted(sum(res["secondary"][key]["groups"].values(), []))
        assert members == ["A", "B"], (key, members)


def test_fallback_to_non_pi_coders():
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b) = sim_labels(3, seed=32)
        files = [write_page(os.path.join(d, "pi.csv"), "PI", pi, source="researcher", seed=1),
                 write_page(os.path.join(d, "a.csv"), "A", a, source="public", seed=2),
                 write_page(os.path.join(d, "b.csv"), "B", b, source="researcher", seed=3)]
        res = run(files, "PI", boot=0)
    assert res["primary"]["group"] == ["A", "B"] and "1 publicly recruited" in res["primary"]["basis"]


def test_only_pi_eligible():
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b) = sim_labels(3, seed=33)
        files = [write_page(os.path.join(d, "pi.csv"), "PI", pi, seed=1),
                 write_basic(os.path.join(d, "gforms_A.csv"), a, with_text=False),
                 write_basic(os.path.join(d, "survey_B.csv"), b, with_text=True)]
        res = run(files, "PI", boot=50)
    assert res["eligible"] == ["PI"]
    assert res["primary"]["pairs"] == [] and res["decision"]["status"] == "NOT ASSESSABLE"
    for nm in ("gforms_A", "survey_B"):          # identity = file stem; nothing silently passed
        rules = res["coders"][nm]["rules"]
        assert [rules[k]["status"] for k in "abcd"] == [R.NA, R.NA, R.PASS, R.NA], rules
    # D36.1: the PI does not vote, so with no eligible non-PI coder there is no gold label
    gold = res["gold_rows"]
    assert all(g["n_voters"] == 0 and g["gold_relevant"] is None for g in gold)
    assert all(g["relevance_status"] == "unresolved: no voter gave a label" for g in gold)
    assert res["adjudication"]["unresolved_relevance"] == 300 and res["adjudication"]["voters"] == []
    assert any("rest on 0 eligible non-PI coder" in w for w in res["warnings"])
    # the sensitivity reading (the PI votes) takes the PI's labels
    assert [g["alt_pi_votes_relevant"] for g in gold] == [pi[f][0] for f in IDS]
    assert res["adjudication"]["sensitivity"]["pi_votes"]["fragments_relevance_differs"] == 300


def _uniform(rel, val):
    return {f: (rel, val) for f in IDS}


M, P, X, N, R0 = ("1", "minus"), ("1", "plus"), ("1", "mixed"), ("1", "none"), ("0", "none")


def _set(labs, i, **kv):
    for nm, v in kv.items():
        labs[nm][IDS[i]] = v


def test_gold_d36_1_tiebreaks_counted_separately():
    """D36.1 on constructed labels: the PI never votes; relevance ties (3) and
    valence ties (2) broken by the PI are counted separately; ties the PI cannot
    break are unresolved and listed; the 'PI votes' reading is the sensitivity
    analysis and differs exactly where the PI's vote matters."""
    labs = {nm: _uniform(*M) for nm in ("PI", "A", "B", "C", "D")}
    for i, pi_lab in ((0, M), (1, M), (2, R0)):     # relevance 2-2 among A-D, PI breaks the tie
        _set(labs, i, A=M, B=M, C=R0, D=R0, PI=pi_lab)
    _set(labs, 4, A=M, B=M, C=P, D=P, PI=P)          # valence 2-2, PI breaks -> plus
    _set(labs, 5, A=X, B=X, C=N, D=N, PI=X)          # valence 2-2, PI breaks -> mixed
    _set(labs, 6, A=M, B=M, C=P, D=P, PI=X)          # PI's valence not among the tied labels
    _set(labs, 7, A=M, B=M, C=P, D=P, PI=R0)         # PI did not mark it relevant
    _set(labs, 9, A=M, B=M, C=P, D=X, PI=P)          # plurality minus (2 of 4); PI's vote would tie it
    _set(labs, 10, A=R0, B=R0, C=R0, D=M, PI=M)      # PI against a clear majority: not a vote
    with tempfile.TemporaryDirectory() as d:
        res = run(write_set(d, labs), "PI", boot=0)
        paths = R.write_outputs(res, os.path.join(d, "out"))
        csv_rows = {r["frag_id"]: r for r in csv.DictReader(open(paths["gold"], encoding="utf-8"))}
        report = open(paths["report"], encoding="utf-8").read()
    g = {r["frag_id"]: r for r in res["gold_rows"]}
    f = IDS
    adj = res["adjudication"]
    assert adj["name"] == "pi_breaks_ties_only" and adj["voters"] == ["A", "B", "C", "D"]
    assert all(r["n_voters"] == 4 for r in res["gold_rows"])          # the PI is never counted
    assert (g[f[0]]["gold_relevant"], g[f[0]]["relevance_status"]) == ("1", R.TIEBREAK)
    assert (g[f[0]]["gold_valence"], g[f[0]]["valence_status"]) == ("minus", "majority")   # A, B only
    assert (g[f[2]]["gold_relevant"], g[f[2]]["gold_valence"]) == ("0", "none")
    assert g[f[2]]["valence_status"] == "rule: gold relevance 0 -> none"
    assert (g[f[4]]["gold_valence"], g[f[4]]["valence_status"]) == ("plus", R.TIEBREAK)
    assert (g[f[5]]["gold_valence"], g[f[5]]["valence_status"]) == ("mixed", R.TIEBREAK)
    assert g[f[6]]["gold_valence"] is None
    assert g[f[6]]["valence_status"] == "unresolved: tie, PI label not among the tied labels"
    assert g[f[7]]["gold_valence"] is None
    assert g[f[7]]["valence_status"] == "unresolved: tie, PI did not mark it relevant"
    assert (g[f[9]]["gold_valence"], g[f[9]]["valence_status"]) == ("minus", "majority")
    assert (g[f[10]]["gold_relevant"], g[f[10]]["votes_relevance"]) == ("0", "0:3;1:1")
    assert adj["pi_tiebreaks_relevance"] == 3 and adj["pi_tiebreaks_valence"] == 2
    assert adj["fragments_with_any_pi_tiebreak"] == 5
    assert adj["pi_decided_relevance"] == 3 and adj["pi_decided_valence"] == 2
    assert adj["unresolved_relevance"] == 0 and adj["unresolved_relevance_ids"] == []
    assert adj["unresolved_valence"] == 2 and adj["unresolved_valence_ids"] == [f[6], f[7]]
    assert adj["plurality_without_absolute_majority"] == {"relevance": 0, "valence": 1}
    assert adj["gold_relevant_counts"] == {"0": 2, "1": 298}
    # sensitivity reading: the PI votes (eligible) -> no relevance tie can occur with 5 voters
    alt = adj["sensitivity"]["pi_votes"]
    assert alt["voters"] == ["A", "B", "C", "D", "PI"]
    assert alt["pi_tiebreaks_relevance"] == 0 and alt["pi_tiebreaks_valence"] == 1       # f9
    assert alt["pi_decided_relevance"] == 3 and alt["pi_decided_valence"] == 3          # f4, f5, f9
    assert alt["fragments_relevance_differs"] == 0 and alt["fragments_valence_differs"] == 1
    assert g[f[9]]["alt_pi_votes_valence"] == "plus" and g[f[4]]["alt_pi_votes_valence"] == "plus"
    assert alt["unresolved_valence_ids"] == [f[6], f[7]]
    # outputs: no internal keys, alternative and exclusion columns present
    row = csv_rows[f[9]]
    assert row["alt_pi_votes_valence"] == "plus" and row["gold_valence"] == "minus"
    assert not any(k.startswith("_") for k in row)
    assert {row["in_codebook_anchors"], row["in_old_practice_paraphrases"]} <= {"yes", "no"}
    assert csv_rows["Zcpj-U5lcAc_000"]["in_codebook_anchors"] == "yes"
    assert csv_rows["Zcpj-U5lcAc_000"]["in_old_practice_paraphrases"] == "yes"
    assert "**PI tie-breaks**: relevance 3, valence 2" in report
    assert f"Unresolved** valence where gold relevance is 1: 2 ({f[6]}, {f[7]})" in report


def test_gold_pi_votes_reading_and_missing_pi_labels():
    """Three non-PI voters: relevance cannot tie, but when the PI votes it can
    (sensitivity reading). A PI who did not code a fragment cannot break its
    tie; with --no-pi every tie is unresolved."""
    three = {nm: _uniform(*M) for nm in ("PI", "A", "B", "C")}
    _set(three, 0, A=M, B=R0, C=R0, PI=M)            # record: 0 (2-1); PI votes: 2-2, PI breaks -> 1
    four = {nm: _uniform(*M) for nm in ("PI", "A", "B", "C", "D")}
    _set(four, 0, A=M, B=M, C=R0, D=R0, PI=M)        # tie, PI coded it -> tie-break
    _set(four, 3, A=M, B=M, C=R0, D=R0)              # tie, the PI's file has no row for it
    with tempfile.TemporaryDirectory() as d:
        r3 = run(write_set(d, three, "t"), "PI", boot=0)
        files4 = write_set(d, four, "f", PI={"drop": {IDS[3]}})
        r4 = run(files4, "PI", boot=0)
        r4_none = run([p for p in files4 if not p.endswith("fPI.csv")], None, boot=0)
    g = {r["frag_id"]: r for r in r3["gold_rows"]}
    assert (g[IDS[0]]["gold_relevant"], g[IDS[0]]["relevance_status"]) == ("0", "majority")
    assert g[IDS[0]]["pi_decided_relevance"] == "no"
    assert (g[IDS[0]]["alt_pi_votes_relevant"], g[IDS[0]]["alt_pi_votes_valence"]) == ("1", "minus")
    alt = r3["adjudication"]["sensitivity"]["pi_votes"]
    assert alt["pi_tiebreaks_relevance"] == 1 and alt["fragments_relevance_differs"] == 1
    assert r3["adjudication"]["pi_tiebreaks_relevance"] == 0
    # the PI's file lacks IDS[3]: the PI fails rule (c) but still breaks the IDS[0] tie (D36.1)
    g = {r["frag_id"]: r for r in r4["gold_rows"]}
    assert not r4["coders"]["PI"]["eligible"]
    assert (g[IDS[0]]["gold_relevant"], g[IDS[0]]["relevance_status"]) == ("1", R.TIEBREAK)
    assert g[IDS[3]]["gold_relevant"] is None
    assert g[IDS[3]]["relevance_status"] == "unresolved: tie, PI label missing"
    assert g[IDS[3]]["valence_status"] == "unresolved: relevance unresolved"
    assert r4["adjudication"]["unresolved_relevance_ids"] == [IDS[3]]
    # no gold valence either, but "unresolved valence" counts only fragments whose gold relevance is 1
    assert g[IDS[3]]["gold_valence"] is None and r4["adjudication"]["unresolved_valence_ids"] == []
    assert any("does not meet the inclusion rules but broke ties" in w for w in r4["warnings"])
    # no PI at all: both ties unresolved
    g = {r["frag_id"]: r for r in r4_none["gold_rows"]}
    assert g[IDS[0]]["relevance_status"] == "unresolved: tie, PI did not code"
    assert r4_none["adjudication"]["unresolved_relevance_ids"] == [IDS[0], IDS[3]]
    assert r4_none["adjudication"]["unresolved_valence"] == 0
    assert r4_none["adjudication"]["fragments_pi_decided"] == 0
    assert r4_none["adjudication"]["pi_tiebreaks_relevance"] == 0
    assert any("--no-pi" in w for w in r4_none["warnings"])


def test_missing_rows_partial_completer():
    drop = set(IDS[:10])
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b, c) = sim_labels(4, seed=34)
        files = [write_page(os.path.join(d, "pi.csv"), "PI", pi, seed=1),
                 write_page(os.path.join(d, "a.csv"), "A", a, seed=2),
                 write_page(os.path.join(d, "b.csv"), "B", b, seed=3),
                 write_page(os.path.join(d, "c.csv"), "C", c, drop=drop, seed=4),
                 write_page(os.path.join(d, "e.csv"), "E", c, drop=drop, practice=(5, 8), seed=5)]
        res = run(files, "PI", boot=0)
    assert not res["coders"]["E"]["eligible"]          # fails (b) and (c): not a partial completer
    cc = res["coders"]["C"]
    assert cc["missing"] == 10 and cc["completed"] == 290 and not cc["eligible"]
    assert cc["rules"]["c"]["status"] == R.FAIL and "10 missing" in cc["rules"]["c"]["detail"]
    assert res["secondary"]["alpha"]["partial_completers"] == ["C"]
    assert "C" in res["secondary"]["alpha"]["eligible_plus_partial"]["relevance"]["coders"]
    ac = next(p for p in res["secondary"]["all_pairs"] if (p["a"], p["b"]) == ("A", "C"))
    assert ac["relevance"]["n"] == 290


def test_bom_and_out_of_codebook_and_valence_on_irrelevant():
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a) = sim_labels(2, seed=35)
        a = dict(a)
        a[IDS[0]] = ("0", "minus")       # valence on a not-relevant row -> none
        a[IDS[1]] = ("1", " Minus ")     # case/whitespace: still the codebook label
        a[IDS[2]] = ("1", "neg")         # valence outside the codebook
        a[IDS[3]] = ("2", "none")        # relevance outside the codebook
        a[IDS[4]] = ("1", "")            # relevant without valence
        p = write_page(os.path.join(d, "a.csv"), "Anna", a, bom=True, seed=1)
        assert open(p, "rb").read(3) == b"\xef\xbb\xbf"
        res = run([write_page(os.path.join(d, "pi.csv"), "PI", pi, seed=2), p], "PI", boot=0)
    c = res["coders"]["Anna"]
    assert c["identity_from"] == "coder column" and c["n_rows"] == 300
    iss = {k: v["count"] for k, v in c["issues"].items()}
    assert iss["valence_on_not_relevant"] == 1 and iss["valence_out_of_codebook"] == 1
    assert iss["relevance_out_of_codebook"] == 1 and iss["valence_missing"] == 1
    assert c["completed"] == 297 and c["rules"]["c"]["status"] == R.FAIL


def test_duplicate_ids_fail_loudly():
    with tempfile.TemporaryDirectory() as d:
        _, (a,) = sim_labels(1, seed=36)
        dup = [IDS[5], REF[IDS[5]], "1", "plus", 301, 4, "Dup", "v1", 1, "", "", "en", "fluent", "public", 8, 8]
        p = write_page(os.path.join(d, "dup.csv"), "Dup", a, extra_rows=[dup])
        try:
            R.read_coder_file(p)
        except R.DataError as e:
            assert "duplicate frag_id" in str(e) and IDS[5] in str(e)
        else:
            raise AssertionError("duplicate frag_id was not rejected")
        out = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), p, "--pi", "X",
                              "--boot", "0", "--out-dir", os.path.join(d, "o")], capture_output=True, text=True)
        assert out.returncode != 0 and "duplicate frag_id" in out.stderr
        assert not os.path.exists(os.path.join(d, "o", "reliability_report.md"))


def test_three_formats_and_meta():
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b, c) = sim_labels(4, seed=37)
        files = [write_page(os.path.join(d, "ws1_coded_PI.csv"), "PI", pi, seed=1),
                 write_page(os.path.join(d, "ws1_coded_A.csv"), "A", a, practice=None, seed=2),
                 write_basic(os.path.join(d, "ws1_coded_B.csv"), b, with_text=False),
                 write_basic(os.path.join(d, "ws1_coded_C.csv"), c, with_text=True)]
        meta = write_meta(os.path.join(d, "coders.csv"), [
            {"coder": "A", "practice_correct": 7, "practice_n": 8, "source": "researcher"},
            {"coder": "ws1_coded_B", "source": "public", "english_level": "good", "practice_correct": 6, "practice_n": 8},
            {"coder": "ws1_coded_C", "source": "public", "english_level": "basic"},
            {"coder": "nobody", "source": "public"}])
        res = run(files, "PI", meta=meta, boot=0)
    C = res["coders"]
    assert C["PI"]["format"] == "page" and C["A"]["format"] == "page"
    assert C["ws1_coded_B"]["format"].startswith("4-column") and C["ws1_coded_C"]["format"].startswith("4-column")
    assert C["A"]["metadata"]["practice_correct"] == {"value": 7, "from": "--meta"}
    assert C["A"]["metadata"]["source"]["value"] == "public"      # file wins over --meta ...
    assert any("A: source: file says 'public', --meta says 'researcher'" in w for w in res["warnings"])
    assert C["A"]["eligible"]
    assert [C["ws1_coded_B"]["rules"][k]["status"] for k in "abcd"] == [R.PASS, R.PASS, R.PASS, R.NA]
    assert [C["ws1_coded_C"]["rules"][k]["status"] for k in "abcd"] == [R.FAIL, R.NA, R.PASS, R.NA]
    assert C["ws1_coded_C"]["issues"]["text_mismatch"]["count"] == 0
    assert any("'nobody' matches no input coder" in w for w in res["warnings"])
    assert res["eligible"] == ["A", "PI"]
    assert res["primary"]["group"] == ["A"] and res["primary"]["pairs"] == []
    assert res["decision"]["status"] == "NOT ASSESSABLE"


def test_not_recorded_is_never_passed():
    with tempfile.TemporaryDirectory() as d:
        _, (a, b) = sim_labels(2, seed=38)
        res = run([write_page(os.path.join(d, "a.csv"), "A", a, practice=None, seed=1),
                   write_page(os.path.join(d, "b.csv"), "B", b, practice=None, seed=2)], None, boot=0)
    for nm in ("A", "B"):
        r = res["coders"][nm]["rules"]["b"]
        assert r["status"] == R.NA and "not recorded" in r["detail"]
        assert not res["coders"][nm]["eligible"]
    assert res["decision"]["status"] == "NOT ASSESSABLE"


def test_median_time_rule():
    with tempfile.TemporaryDirectory() as d:
        _, (a,) = sim_labels(1, seed=39)
        fast = {f: (2 if i % 2 else 3) for i, f in enumerate(IDS)}    # median 2.5 s -> fail
        # skewed: median and mean on opposite sides of 3 s; the rule is the median
        slow_tail = {f: (2 if i < 160 else 20) for i, f in enumerate(IDS)}  # median 2, mean 10.4 -> fail
        fast_tail = {f: (4 if i < 160 else 1) for i, f in enumerate(IDS)}   # median 4, mean 2.6 -> pass
        res = run([write_page(os.path.join(d, "a.csv"), "A", a, times=fast),
                   write_page(os.path.join(d, "s.csv"), "S", a, times=slow_tail),
                   write_page(os.path.join(d, "f.csv"), "F", a, times=fast_tail)], None, boot=0)
    r = res["coders"]["A"]
    assert r["rules"]["d"]["status"] == R.FAIL and r["timing"]["median"] == 2.5
    assert r["timing"]["under_3s"] == 150 and abs(r["timing"]["share_under_3s"] - 0.5) < 1e-12
    assert res["coders"]["S"]["rules"]["d"]["status"] == R.FAIL and res["coders"]["S"]["timing"]["median"] == 2
    assert res["coders"]["F"]["rules"]["d"]["status"] == R.PASS and res["coders"]["F"]["timing"]["median"] == 4


def test_extra_channel_and_input_errors():
    """--channel (e.g. the LLM channel) is scored against gold; bad inputs stop the run."""
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b) = sim_labels(3, seed=40)
        files = [write_page(os.path.join(d, "pi.csv"), "PI", pi, seed=1),
                 write_page(os.path.join(d, "a.csv"), "A", a, seed=2),
                 write_page(os.path.join(d, "b.csv"), "B", b, seed=3)]
        llm_lab = {f: (R0 if 4 <= i < 40 else pi[f]) for i, f in enumerate(IDS)}
        llm = write_basic(os.path.join(d, "llm.csv"), llm_lab, with_text=False, drop=set(IDS[:4]))
        res = run(files, "PI", boot=0, channels=[f"LLM={llm}"])
        ch = res["machine_channels"]["LLM"]
        gold = res["gold_rows"]
        exp = R.kappa_counts([(g["gold_relevant"], llm_lab[g["frag_id"]][0]) for g in gold
                              if g["frag_id"] not in IDS[:4]])[0]
        assert ch["relevance"]["n"] == 296 and abs(ch["relevance"]["value"] - exp) < 1e-12
        assert not any("LLM channel" in w for w in res["warnings"])
        assert any("channel LLM: 4 reference fragment(s) not in the file" in w for w in res["warnings"])
        assert gold[10]["LLM_relevant"] == llm_lab[gold[10]["frag_id"]][0]
        # valence (both relevant) = fragments that gold AND the channel mark relevant
        both = [(g["gold_valence"], llm_lab[g["frag_id"]][1]) for g in gold if g["frag_id"] not in IDS[:4]
                and g["gold_relevant"] == "1" and llm_lab[g["frag_id"]][0] == "1" and g["gold_valence"]]
        assert ch["valence_conditional"]["n"] == len(both) < sum(g["gold_relevant"] == "1" for g in gold)
        assert abs(ch["valence_conditional"]["value"] - R.kappa_counts(both)[0]) < 1e-12
        assert Fraction(ch["valence_conditional"]["value_exact"]) == R.kappa_exact(both)
        for bad in (["dictionary_v1=" + llm], ["no_equals_sign"], ["gold=" + llm], ["my llm=" + llm]):
            try:
                run(files, "PI", boot=0, channels=bad)
            except R.DataError:
                pass
            else:
                raise AssertionError(f"--channel {bad} accepted")
        two = write_page(os.path.join(d, "two.csv"), "A", a, seed=5)
        lines = open(two, encoding="utf-8").read().splitlines()
        open(two, "w", encoding="utf-8").write("\n".join(lines[:-1] + [lines[-1].replace(",A,", ",Zed,")]) + "\n")
        nocol = os.path.join(d, "nocol.csv")
        open(nocol, "w", encoding="utf-8").write("frag_id,text,relevant\nx,y,1\n")
        for case, args in (("two coder names in one file", [files[0], two]),
                           ("same coder in two files", files + [write_page(os.path.join(d, "a2.csv"), "A", a)]),
                           ("missing column", [nocol])):
            try:
                run(args, "PI", boot=0)
            except R.DataError as e:
                assert str(e), case
            else:
                raise AssertionError(case + " accepted")


# ---------------------------------------------------------------------------
# (3b) gate decision, bootstrap CIs, gold rules, PI identity, protocol version
# ---------------------------------------------------------------------------
def test_decide_truth_table():
    """Section 9 as clarified in PROTOCOL 12.1(c): a mean below 0.70 on either
    dimension is FAIL whatever the other shows (undefined included); NOT
    ASSESSABLE only when nothing failed; valence fails 'alone' only when
    relevance passed; the 'two eligible coders' remark only when that is the cause."""
    def gate(r, v, cause="undefined_kappa"):
        def one(p, why):
            return {"pass": p, "why": why, **({"cause": cause} if p is None else {})}
        return {"relevance": one(r, "r"), "valence_conditional": one(v, "v")}
    assert R.decide(gate(True, True))["status"] == "PASS"
    d = R.decide(gate(True, False))
    assert d["status"] == "FAIL" and d["failed"] == ["valence"] and d["valence_only"]
    assert "fallback is a binary" in d["text"]
    d = R.decide(gate(False, True))
    assert d["status"] == "FAIL" and d["failed"] == ["relevance"] and not d["valence_only"]
    d = R.decide(gate(False, False))
    assert d["status"] == "FAIL" and d["failed"] == ["relevance", "valence"] and not d["valence_only"]
    # one dimension failed, the other undefined: the conjunction has failed (section 6)
    d = R.decide(gate(False, None))
    assert d["status"] == "FAIL" and d["failed"] == ["relevance"] and d["not_evaluated"] == ["valence"]
    assert not d["valence_only"] and "could not be evaluated (valence: v)" in d["text"]
    d = R.decide(gate(None, False))
    assert d["status"] == "FAIL" and d["failed"] == ["valence"] and d["not_evaluated"] == ["relevance"]
    assert not d["valence_only"] and "not a valence-only failure" in d["text"]
    assert "fallback is a binary" not in d["text"]
    for r, v in ((None, True), (True, None), (None, None)):
        d = R.decide(gate(r, v))
        assert d["status"] == "NOT ASSESSABLE" and d["failed"] == [] and not d["valence_only"], (r, v)
        assert "two eligible non-PI coders" not in d["text"] and "no mean pairwise κ is below 0.70" in d["text"]
    d = R.decide(gate(None, None, cause="no_primary_pair"))
    assert d["status"] == "NOT ASSESSABLE" and "two eligible non-PI coders" in d["text"]


def test_gate_fails_when_one_dimension_fails_and_the_other_is_undefined():
    """End to end (SYNTHETIC constructed labels): an eligible coder who marks every
    fragment not relevant makes two primary pairs' conditional-valence κ undefined
    (n = 0) and drags mean relevance κ below 0.70. Relevance has failed, so the
    gate has failed (12.1(c)); the report names the real cause of the undefined
    valence mean. Two coders who give every both-relevant fragment the same
    valence make that κ undefined by chance agreement 1: with relevance passed,
    nothing failed, so the gate is not assessable, for that stated reason."""
    with tempfile.TemporaryDirectory() as d:
        labs = design(["A", "B"], 60, 6)
        labs["Z"] = {f: ("0", "none") for f in IDS}
        fail = run(write_set(d, labs, tag="f_"), None, boot=0)
        same = design(["A", "B"], 60, 6, {"A": ["minus"] * 60, "B": ["minus"] * 60})
        na = run(write_set(d, same, tag="s_"), None, boot=0)
    assert fail["eligible"] == ["A", "B", "Z"] and len(fail["primary"]["pairs"]) == 3
    m = fail["primary"]["mean"]
    assert Fraction(m["relevance"]["value_exact"]) == design_kappa(60, 6) / 3       # A×Z, B×Z: κ 0
    und = m["valence_conditional"]["undefined_pairs"]
    assert [u["pair"] for u in und] == [["A", "Z"], ["B", "Z"]] and all(u["n"] == 0 for u in und)
    g = fail["primary"]["gate"]
    assert g["relevance"]["pass"] is False and g["valence_conditional"]["pass"] is None
    assert "2 of 3 primary pair(s)" in g["valence_conditional"]["why"]
    assert "A × Z: n = 0: no fragment that both coders marked relevant" in g["valence_conditional"]["why"]
    dec = fail["decision"]
    assert dec["status"] == "FAIL" and dec["failed"] == ["relevance"] and dec["not_evaluated"] == ["valence"]
    assert "two eligible non-PI coders" not in dec["text"] and "12.1(c)" in dec["text"]
    g = na["primary"]["gate"]
    assert g["relevance"]["pass"] is True and g["valence_conditional"]["pass"] is None
    assert "chance agreement = 1: both coders gave one and the same label to all 60" in g["valence_conditional"]["why"]
    dec = na["decision"]
    assert dec["status"] == "NOT ASSESSABLE" and dec["failed"] == [] and dec["not_evaluated"] == ["valence"]
    assert "two eligible non-PI coders" not in dec["text"] and "chance agreement = 1" in dec["text"]


def design(names, c, p, val_common=None):
    """SYNTHETIC labels with exactly known pairwise kappa: every coder marks
    the first c fragments relevant plus p private ones of its own (disjoint),
    so every pair disagrees on relevance on exactly 2p fragments. Valence on
    the c shared fragments: val_common[name] or alternating minus/plus."""
    labs = {}
    for j, nm in enumerate(names):
        lab = {f: ("0", "none") for f in IDS}
        vc = (val_common or {}).get(nm) or (["minus", "plus"] * c)[:c]
        for k, f in enumerate(IDS[:c]):
            lab[f] = ("1", vc[k])
        for f in IDS[c + j * p: c + (j + 1) * p]:
            lab[f] = ("1", "minus")
        labs[nm] = lab
    return labs


def design_kappa(c, p, n=300):
    """Exact relevance kappa of any pair in design(): equal marginals m = c + p,
    n - 2p agreements."""
    m = c + p
    s = m * m + (n - m) ** 2
    return Fraction(n * (n - 2 * p) - s, n * n - s)


def test_gate_decisions_on_constructed_kappas():
    def gate_run(d, labs, tag):
        files = [write_page(os.path.join(d, f"{tag}_{nm}.csv"), nm, lab, seed=i)
                 for i, (nm, lab) in enumerate(labs.items())]
        return run(files, None, boot=0)
    flip = ["minus", "plus"] * 50
    flipped = [("plus" if v == "minus" else "minus") if k < 30 else v for k, v in enumerate(flip)]
    with tempfile.TemporaryDirectory() as d:
        clear_pass = gate_run(d, design(["A", "B"], 60, 6), "p")                  # kappa 0.883
        rel_fail = gate_run(d, design(["A", "B"], 30, 12), "r")                   # kappa 0.668
        val_fail = gate_run(d, design(["A", "B"], 100, 2, {"A": flip, "B": flipped}), "v")
        exact = gate_run(d, design(["A", "B", "C"], 80, 20), "x")                 # each pair exactly 7/10
    m = clear_pass["primary"]["mean"]
    assert Fraction(m["relevance"]["value_exact"]) == design_kappa(60, 6) and m["valence_conditional"]["value"] == 1
    assert clear_pass["decision"]["status"] == "PASS"
    m = rel_fail["primary"]["mean"]
    assert Fraction(m["relevance"]["value_exact"]) == design_kappa(30, 12)
    assert 0.60 < m["relevance"]["value"] < 0.70 and m["valence_conditional"]["value"] == 1
    d = rel_fail["decision"]
    assert d["status"] == "FAIL" and d["failed"] == ["relevance"] and not d["valence_only"]
    # valence fails on the gated version (both relevant: 70 of 100 agree, kappa 0.4)
    # but would pass on the all-fragments version, which is reported, not gated
    m = val_fail["primary"]["mean"]
    assert m["relevance"]["value"] > 0.70 and abs(m["valence_conditional"]["value"] - 0.4) < 1e-12
    assert m["valence_all"]["value"] >= 0.70
    d = val_fail["decision"]
    assert d["status"] == "FAIL" and d["failed"] == ["valence"] and d["valence_only"]
    # boundary: three pairs of exactly 7/10 -> mean exactly 0.70 -> pass. A plain
    # float average of the pair kappas falls below 0.70, which used to FAIL the gate.
    assert design_kappa(80, 20) == Fraction(7, 10)
    m, pairs = exact["primary"]["mean"]["relevance"], exact["primary"]["pairs"]
    assert len(pairs) == 3 and all(p["relevance"]["value_exact"] == "7/10" for p in pairs)
    assert all(p["relevance"]["value"] == 0.7 for p in pairs)       # one correctly rounded division
    assert sum(p["relevance"]["value"] for p in pairs) / 3 < 0.70
    assert m["value_exact"] == "7/10" and m["value"] == 0.7
    assert exact["primary"]["gate"]["relevance"]["pass"] is True and exact["decision"]["status"] == "PASS"
    assert "exactly 7/10" in exact["primary"]["gate"]["relevance"]["why"]
    # values just below 0.70 are printed with the digits that show it
    assert R.vs_gate(Fraction(69996, 100000)) == "0.69996"
    assert R.vs_gate(Fraction(70004, 100000)) == "0.70004"


def test_bootstrap_ci_matches_independent_percentiles():
    """CIs and point estimates against sklearn kappas on the same resamples and
    numpy.percentile; mean pairwise kappa = arithmetic mean of the pairs."""
    try:
        from sklearn.metrics import cohen_kappa_score
        import numpy as np
    except ImportError:
        skip("scikit-learn/numpy not installed")
    import warnings
    B, SEED = 200, 9
    _, (a, b, c) = sim_labels(3, seed=61)
    # D and E mark only three fragments relevant together: valence (both relevant)
    # is undefined in many resamples (empty, or one category only)
    dd, ee = _uniform("0", "none"), _uniform("0", "none")
    for f, v in zip(IDS[:3], ("minus", "minus", "plus")):
        dd[f] = ee[f] = ("1", v)
    dd[IDS[3]] = ("1", "plus")
    labs = {"A": a, "B": b, "C": c, "D": dd, "E": ee}
    with tempfile.TemporaryDirectory() as d:
        files = [write_page(os.path.join(d, f"{nm}.csv"), nm, lab, seed=i,
                            source="public" if nm in "ABC" else "researcher")
                 for i, (nm, lab) in enumerate(labs.items())]
        res = run(files, None, boot=B, seed=SEED)
    assert res["primary"]["group"] == ["A", "B", "C"]
    samples = R.Bootstrap(len(IDS), B, SEED).samples
    assert len(samples) == B and all(len(s) == len(IDS) and 0 <= min(s) and max(s) < len(IDS) for s in samples)
    distinct = sum(len(set(s)) for s in samples) / (B * len(IDS))   # with replacement: ~ 1 - 1/e
    assert 0.60 < distinct < 0.66, distinct

    def k_ref(x, y, dim, idx):
        if dim == "valence_conditional":
            u = [(x[IDS[i]][1], y[IDS[i]][1]) for i in idx if x[IDS[i]][0] == "1" and y[IDS[i]][0] == "1"]
        else:
            col = 0 if dim == "relevance" else 1
            u = [(x[IDS[i]][col], y[IDS[i]][col]) for i in idx]
        if not u:
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            k = cohen_kappa_score([p[0] for p in u], [p[1] for p in u])
        return None if k != k else float(k)

    def ci(reps):
        ok = [r for r in reps if r is not None]
        return [float(x) for x in np.percentile(ok, [2.5, 97.5])], len(reps) - len(ok)

    pair_rows = {(p["a"], p["b"]): p for p in res["primary"]["pairs"] + res["secondary"]["all_pairs"]}
    pairs = [("A", "B"), ("A", "C"), ("B", "C")]
    for dim in R.DIMS:
        reps = {}
        for pr in pairs + [("D", "E")]:
            reps[pr] = [k_ref(labs[pr[0]], labs[pr[1]], dim, s) for s in samples]
            got = pair_rows[pr][dim]
            exp_ci, undefined = ci(reps[pr])
            assert got["boot_undefined"] == undefined, (dim, pr)
            assert max(abs(u - v) for u, v in zip(got["ci95"], exp_ci)) < 1e-9, (dim, pr, got["ci95"], exp_ci)
            assert abs(got["value"] - k_ref(labs[pr[0]], labs[pr[1]], dim, range(len(IDS)))) < 1e-12
        mean = res["primary"]["mean"][dim]
        assert abs(mean["value"] - sum(pair_rows[pr][dim]["value"] for pr in pairs) / 3) < 1e-12
        assert Fraction(mean["value_exact"]) == sum(Fraction(pair_rows[pr][dim]["value_exact"]) for pr in pairs) / 3
        mreps = [None if any(reps[pr][i] is None for pr in pairs) else sum(reps[pr][i] for pr in pairs) / 3
                 for i in range(B)]
        exp_ci, undefined = ci(mreps)
        assert mean["boot_undefined"] == undefined
        assert max(abs(u - v) for u, v in zip(mean["ci95"], exp_ci)) < 1e-9, (dim, mean["ci95"], exp_ci)
    assert pair_rows[("D", "E")]["valence_conditional"]["boot_undefined"] > B // 10


def test_gold_valence_rule_relevant_voters_only():
    """Gold relevance 0 forces valence none; gold valence is voted only among
    the non-PI coders who marked the fragment relevant (a `none` from a coder
    who marked it not relevant is not a valence vote); the PI breaks a valence
    tie only with a valence the PI gave as relevant."""
    labs = {nm: _uniform(*M) for nm in ("PI", "A", "B", "C", "D", "E")}
    _set(labs, 0, A=M, B=R0, C=R0, D=R0, E=R0, PI=M)       # relevance 0 by 4-1 -> valence none
    _set(labs, 1, A=M, B=M, C=P, D=R0, E=R0, PI=R0)        # relevance 1 (3-2); valence minus 2-1
    _set(labs, 2, A=M, B=M, C=P, D=P, E=R0, PI=P)          # valence 2-2, PI (relevant) -> plus
    _set(labs, 3, A=M, B=M, C=P, D=P, E=R0, PI=R0)         # valence 2-2, PI not relevant -> unresolved
    with tempfile.TemporaryDirectory() as d:
        res = run(write_set(d, labs), "PI", boot=0)
    g = {r["frag_id"]: r for r in res["gold_rows"]}
    f = IDS
    assert (g[f[0]]["gold_relevant"], g[f[0]]["gold_valence"]) == ("0", "none")
    assert g[f[0]]["valence_status"] == "rule: gold relevance 0 -> none"
    # counting D's and E's `none` as valence votes would tie minus 2 / none 2
    assert (g[f[1]]["gold_relevant"], g[f[1]]["gold_valence"], g[f[1]]["valence_status"]) == ("1", "minus", "majority")
    assert g[f[1]]["votes_valence"] == "minus:2;plus:1"
    assert (g[f[2]]["gold_valence"], g[f[2]]["valence_status"]) == ("plus", R.TIEBREAK)
    assert g[f[3]]["gold_valence"] is None
    assert g[f[3]]["valence_status"] == "unresolved: tie, PI did not mark it relevant"
    adj = res["adjudication"]
    assert (adj["pi_tiebreaks_relevance"], adj["pi_tiebreaks_valence"]) == (0, 1)
    assert adj["unresolved_valence_ids"] == [f[3]]
    # no gold 'relevant, none' without a voter who said so
    assert all(not (r["gold_relevant"] == "1" and r["gold_valence"] == "none") for r in res["gold_rows"])


def test_pi_must_match_an_input_coder():
    """Section 6: the PI is never in the primary kappa, so an --pi that matches
    no coder stops the run instead of letting the PI's file through."""
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b) = sim_labels(3, seed=62)
        files = [write_page(os.path.join(d, "ws1_coded_Gregory.csv"), "Gregory", pi, source="researcher", seed=1),
                 write_page(os.path.join(d, "a.csv"), "A", a, source="researcher", seed=2),
                 write_page(os.path.join(d, "b.csv"), "B", b, source="researcher", seed=3)]
        for pi_arg, kw in (("Gregory Diachenko", {}), ("", {}), (None, {}), ("Gregory", {"no_pi": True}),
                           ("Gregory", {"pi_did_not_code": True})):
            try:
                R.analyse(files, pi_arg, None, 0, 1, **kw)
            except R.DataError as e:
                assert "--pi" in str(e)
            else:
                raise AssertionError(f"accepted --pi {pi_arg!r} {kw}")
        out = os.path.join(d, "o")
        p = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), *files,
                            "--pi", "Gregory Diachenko", "--boot", "0", "--out-dir", out],
                           capture_output=True, text=True)
        assert p.returncode != 0 and "matches none of the input coders" in p.stderr
        assert not os.path.exists(os.path.join(out, "reliability.json"))
        p = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), *files, "--boot", "0",
                            "--out-dir", out], capture_output=True, text=True)
        assert p.returncode != 0 and "--pi" in p.stderr          # one of the two is required
        p = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), *files, "--pi", "Gregory",
                            "--no-pi", "--boot", "0", "--out-dir", out], capture_output=True, text=True)
        assert p.returncode != 0 and "not allowed with" in p.stderr
        assert not os.path.exists(os.path.join(out, "reliability.json"))
        for flag in ("--no-pi", "--pi-did-not-code"):           # explicit declaration: the run proceeds
            p = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), *files, flag,
                                "--boot", "0", "--out-dir", out], capture_output=True, text=True)
            assert p.returncode == 0, p.stderr
            assert json.load(open(os.path.join(out, "reliability.json"), encoding="utf-8"))["meta"]["no_pi"] is True
        ok = run(files, "gregory", boot=0)                       # case-insensitive match
        declared = run(files, None, boot=0)
    assert ok["meta"]["pi"] == "Gregory" and ok["primary"]["group"] == ["A", "B"]
    assert declared["meta"]["pi"] is None and declared["primary"]["group"] == ["A", "B", "Gregory"]


def test_protocol_version_recorded():
    import hashlib
    p = R.protocol_info()
    raw = open(R.PROTOCOL_FILE, "rb").read()
    assert p["sha256"] == hashlib.sha256(raw).hexdigest()
    m = re.search(r"\*\*Version ([0-9.]+) · (\d{4}-\d{2}-\d{2})", raw.decode("utf-8"))
    assert m and (p["version"], p["date"]) == m.groups()
    assert p["version"] in R.PROTOCOL_KNOWN, ("new protocol version: check sections 5-9 against the "
                                              "script, then add it to PROTOCOL_KNOWN", p["version"])
    assert R.protocol_warnings(p) == [], R.protocol_warnings(p)
    # the version check itself: v1.1 is accepted only with its section 12; unknown versions warn
    sec11 = [str(i) for i in range(1, 12)]
    assert R.protocol_warnings(dict(p, version="1", sections=sec11)) == []
    assert R.protocol_warnings(dict(p, version="1.1", sections=sec11 + ["12"])) == []
    w = R.protocol_warnings(dict(p, version="1.1", sections=sec11))
    assert len(w) == 1 and "no section 12" in w[0]
    assert any("check them against this version" in x for x in R.protocol_warnings(dict(p, version="1.2")))
    assert any("check them against this version" in x for x in R.protocol_warnings(dict(p, version=None)))


# ---------------------------------------------------------------------------
# (4) bootstrap reproducibility
# ---------------------------------------------------------------------------
def test_bootstrap_reproducible_with_seed():
    with tempfile.TemporaryDirectory() as d:
        files = make_synthetic_page_set(d, seed=41)
        r1, r2, r3 = (run(files, "SYN_PI", boot=200, seed=s) for s in (7, 7, 8))
    cis = lambda r: [r["primary"]["mean"][x]["ci95"] for x in R.DIMS] + \
                    [r["secondary"]["alpha"]["eligible"][x]["ci95"] for x in R.DIMS]
    assert cis(r1) == cis(r2)
    assert cis(r1) != cis(r3)
    assert R.Bootstrap(300, 5, 1).samples == R.Bootstrap(300, 5, 1).samples
    assert all(r1["primary"]["mean"][x]["value"] == r3["primary"]["mean"][x]["value"] for x in R.DIMS)


# ---------------------------------------------------------------------------
# dictionary v0 reconstruction, CLI end to end, page export
# ---------------------------------------------------------------------------
def test_dictionary_v0_matches_git_history():
    texts = [REF[f] for f in IDS]
    rel0 = sum(1 for t in texts if R.classify_v0(t)[4])
    # Regression values on the 300 fragments. D36.2: the sample was drawn with
    # dictionary v1, strata 140 / 160 (R.DRAW_STRATA_V1); the 136 / 164 written in
    # PROTOCOL section 2 is the v0 count on the same fragments, and every
    # v0-relevant fragment is v1-relevant (see the comment above V0_COMMIT).
    import ws1_pipeline
    set0 = {f for f in IDS if R.classify_v0(REF[f])[4]}
    set1 = {f for f in IDS if ws1_pipeline.classify(REF[f])[-2]}
    assert rel0 == 136 and len(texts) - rel0 == 164
    assert (len(set1), len(texts) - len(set1)) == R.DRAW_STRATA_V1 == (140, 160) and set0 <= set1
    assert R.input_set_sha256(REF) == R.EVAL_INPUT_SHA256      # the PROTOCOL 12.2 input set
    # git-independent: sha256 of the four term lists as they are in `git show
    # 7eb5a1e^:narrative-economics/code/ws1/ws1_pipeline.py` (computed from git, not from the copy)
    import hashlib
    lists = json.dumps({k: v for k, v in R.V0_LISTS.items()}, sort_keys=True).encode()
    assert hashlib.sha256(lists).hexdigest() == "273eb194f7c1c9d59ea204aa7ec96bc2147ae8938a31398c98e26cc743bc436c"
    check = R.v0_git_check(texts)
    if check["status"] != "identical":
        skip("git history not available: " + check["detail"])
    src = subprocess.run(["git", "-C", WS1, "show", f"{R.V0_COMMIT}:{R.V0_PATH}"],
                         capture_output=True, check=True).stdout.decode()
    m = re.search(r"\ndef classify\(frag\):\n(.*?)\n\n", src, re.S)
    body = re.sub(r"\b(AI|OCC|DISPLACE|CREATE)_TERMS\b", r"V0_\1_TERMS", m.group(1)).replace("has_any(", "v0_has_any(")
    import inspect
    ours = inspect.getsource(R.classify_v0).split("\n", 1)[1].rstrip("\n")
    assert ours == body.rstrip("\n"), "classify_v0 body is not a verbatim copy"
    parent = subprocess.run(["git", "-C", WS1, "rev-parse", "7eb5a1e^"], capture_output=True, text=True)
    assert parent.stdout.strip() == R.V0_COMMIT


def test_cli_end_to_end():
    """PI + two public coders + one excluded public coder + an LLM channel in the
    llm_labels.csv format, through the command line. The section-9 decision in
    the outputs is checked against kappas computed here from the labels."""
    _, (pi, a, b, x) = sim_labels(4, seed=51)
    with tempfile.TemporaryDirectory() as d:
        files = make_synthetic_page_set(d, seed=51, excluded=True)
        llm = write_llm_labels(os.path.join(d, "llm_labels.csv"), a, status={IDS[7]: "refusal", IDS[8]: "invalid"})
        out = os.path.join(d, "out")
        p = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), *files,
                            "--pi", "SYN_PI", "--boot", "200", "--out-dir", out, "--channel", f"LLM={llm}"],
                           capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        res = json.load(open(os.path.join(out, "reliability.json"), encoding="utf-8"))
        gold = list(csv.DictReader(open(os.path.join(out, "gold_labels.csv"), encoding="utf-8")))
        excl = list(csv.DictReader(open(os.path.join(out, "exclusions.csv"), encoding="utf-8")))
        report = open(os.path.join(out, "reliability_report.md"), encoding="utf-8").read()
    assert len(gold) == 300 and len(excl) == 4 and "text" not in gold[0]
    assert res["eligible"] == ["SYN_PI", "SYN_public_A", "SYN_public_B"]
    assert res["primary"]["group"] == ["SYN_public_A", "SYN_public_B"]
    assert {r["coder"]: r["eligible"] for r in excl}["SYN_public_X"] == "no"
    # the decision, recomputed here from the labels (exact kappas, exact comparison)
    k_rel = R.kappa_exact([(a[f][0], b[f][0]) for f in IDS])
    k_val = R.kappa_exact([(a[f][1], b[f][1]) for f in IDS if a[f][0] == "1" and b[f][0] == "1"])
    assert Fraction(res["primary"]["mean"]["relevance"]["value_exact"]) == k_rel
    assert Fraction(res["primary"]["mean"]["valence_conditional"]["value_exact"]) == k_val
    exp = "PASS" if k_rel >= Fraction(7, 10) and k_val >= Fraction(7, 10) else "FAIL"
    assert res["decision"]["status"] == exp and f"**Gate: {exp}.**" in report and f"GATE: {exp}" in p.stdout
    # gold of record = D36.1 (A and B vote, the PI breaks ties), recomputed here
    for g in gold:
        ra, rb, rp = a[g["frag_id"]][0], b[g["frag_id"]][0], pi[g["frag_id"]][0]
        assert g["gold_relevant"] == (ra if ra == rb else rp)
        assert g["relevance_status"] == ("majority" if ra == rb else R.TIEBREAK)
    ties = sum(a[f][0] != b[f][0] for f in IDS)
    assert res["adjudication"]["pi_tiebreaks_relevance"] == ties > 0
    assert f"**PI tie-breaks**: relevance {ties}, valence {res['adjudication']['pi_tiebreaks_valence']}" in report
    assert res["machine_channels"]["dictionary_v0"]["provenance"]["n_relevant"] == 136
    assert res["machine_channels"]["dictionary_v1"]["provenance"]["n_relevant"] == 140
    assert res["machine_channels"]["dictionary_v1"]["provenance"]["matches_protocol_frozen"] is True
    assert res["machine_channels"]["dictionary_v0"]["provenance"]["terms_sha256"] == R.V0_TERMS_SHA256
    llm_prov = res["machine_channels"]["LLM"]["provenance"]
    assert llm_prov["run_record"]["found"] is False and any("no run record" in w for w in res["warnings"])
    assert llm_prov["excluded_status_not_ok"] == {"invalid": 1, "refusal": 1} and llm_prov["n_labelled"] == 298
    assert res["machine_channels"]["LLM"]["relevance"]["n"] == 298
    sets = res["sensitivity"]["fragment_sets"]
    assert [(k, v["n"]) for k, v in sets.items()] == [("excl_anchors", 284), ("excl_old_practice", 225),
                                                       ("excl_both", 217)]
    assert set(sets["excl_both"]["excluded"]) == set(R.CODEBOOK_ANCHOR_FRAG_IDS) | set(R.OLD_PRACTICE_PARAPHRASED_FRAG_IDS)
    for k, v in sets.items():
        assert f"sensitivity {k} ({v['n']} fragments)" in p.stdout
        assert v["primary"]["decision"]["status"] in ("PASS", "FAIL")
    assert "## 1. Decision" in report and "Krippendorff" in report
    assert "## 7. Sensitivity analyses: fragment exclusions (PROTOCOL §12.3)" in report
    assert "| §6 mean pairwise κ: relevance (all fragments) |" in report
    assert "Disclosure (PROTOCOL §12.2(b), §12.5.1)" in report and "same ids as PROTOCOL §12.3: yes" in report
    assert {r["coder"]: r["practice_set"] for r in excl} == {"SYN_PI": R.PRACTICE_SET_PROTOCOL, "SYN_public_A":
                                                            R.PRACTICE_SET_PROTOCOL, "SYN_public_B": "untagged",
                                                            "SYN_public_X": R.PRACTICE_SET_PROTOCOL}
    assert (f"Practice set `{R.PRACTICE_SET_PROTOCOL}` (the items the LLM prompt carries; instruction parity, "
            "PROTOCOL §12.4 item 2 and §12.5.3): SYN_PI, SYN_public_A, SYN_public_X. Any other set, `untagged` "
            "or not recorded: SYN_public_B (untagged).") in report
    proto = R.protocol_info()
    assert res["meta"]["protocol"]["sha256"] == proto["sha256"] and "text" not in res["meta"]["protocol"]
    assert f"protocol PROTOCOL_WS1.0.md v{proto['version']} ({proto['date']})" in report
    assert res["meta"]["reference"]["is_protocol_input_set"] is True
    assert {"pi_decided_relevance", "alt_pi_votes_relevant", "alt_pi_votes_valence", "in_codebook_anchors",
            "in_old_practice_paraphrases", "LLM_relevant"} <= set(gold[0])


# ---------------------------------------------------------------------------
# (5) the protocol's decisions on constructed data (mutation-sensitive)
# ---------------------------------------------------------------------------
def test_gate_threshold_boundaries():
    """Mean kappa just below, exactly at and just above 0.70 (exact designs):
    FAIL / PASS / PASS. A threshold of 0.69 or 0.71, or a strict >, changes one
    of the three outcomes."""
    cases = {"below": (28, 10), "exact": (80, 20), "above": (25, 9)}
    exp_k = {k: design_kappa(*v) for k, v in cases.items()}
    assert Fraction(69, 100) < exp_k["below"] < Fraction(7, 10) == exp_k["exact"] < exp_k["above"] < Fraction(71, 100)
    out = {}
    with tempfile.TemporaryDirectory() as d:
        for k, (c, p) in cases.items():
            names = ["A", "B", "C"] if k == "exact" else ["A", "B"]
            out[k] = run(write_set(d, design(names, c, p), k), None, boot=0)
    for k, res in out.items():
        m = res["primary"]["mean"]
        assert Fraction(m["relevance"]["value_exact"]) == exp_k[k], k
        assert m["valence_conditional"]["value_exact"] == "1/1"
    assert out["below"]["decision"]["status"] == "FAIL" and out["below"]["decision"]["failed"] == ["relevance"]
    assert out["below"]["primary"]["gate"]["relevance"]["pass"] is False
    assert out["exact"]["decision"]["status"] == "PASS"
    assert out["above"]["decision"]["status"] == "PASS"


def test_primary_pair_selection_decides_gate():
    """A, B: publicly recruited, eligible, identical labels. R (researcher,
    eligible), PI (public, eligible) and X (public, fails rule b) code the
    opposite relevance. Only A x B is a primary pair, so the gate passes; any
    rule that let R, the PI or X into the pairs would fail it. With only one
    public coder, all eligible non-PI coders form the pairs."""
    base = design(["A"], 60, 0)["A"]
    inv = {f: (R0 if base[f][0] == "1" else M) for f in IDS}
    labs = {"A": base, "B": dict(base), "R": inv, "PI": dict(inv), "X": dict(inv)}
    with tempfile.TemporaryDirectory() as d:
        res = run(write_set(d, labs, R={"source": "researcher"}, X={"practice": (5, 8)}), "PI", boot=0)
        res1 = run(write_set(d, {"A": base, "B": dict(base), "R": dict(base), "PI": inv}, "one",
                             B={"source": "researcher"}, R={"source": "other"}), "PI", boot=0)
    assert res["eligible"] == ["A", "B", "PI", "R"]
    assert res["primary"]["group"] == ["A", "B"] and [(p["a"], p["b"]) for p in res["primary"]["pairs"]] == [("A", "B")]
    assert res["primary"]["mean"]["relevance"]["value_exact"] == "1/1"
    assert res["decision"]["status"] == "PASS"
    assert R.kappa_exact([(base[f][0], inv[f][0]) for f in IDS]) < 0        # a pair with R, PI or X
    assert res1["primary"]["group"] == ["A", "B", "R"] and "1 publicly recruited" in res1["primary"]["basis"]
    assert len(res1["primary"]["pairs"]) == 3 and res1["decision"]["status"] == "PASS"


def test_inclusion_rule_boundaries():
    """Every section-5 threshold at its boundary: practice 6 of 8 (also 6 of 7
    recorded) passes and 5 of 8 fails; median exactly 3.0 s passes and 2.9 s
    fails; English 'good' passes and 'basic' fails; 300 of 300 passes and 299
    fails. Excluded coders code the opposite relevance, so letting any of them
    in would also fail the gate."""
    base = design(["A"], 60, 0)["A"]
    inv = {f: (R0 if base[f][0] == "1" else M) for f in IDS}
    ok = {"P6": {"practice": (6, 8)}, "P6of7": {"practice": (6, 7)}, "T3": {"times": {f: 3.0 for f in IDS}},
          "Egood": {"english": "good"}, "C300": {}}
    bad = {"P5": {"practice": (5, 8)}, "T29": {"times": {f: 2.9 for f in IDS}},
           "Ebasic": {"english": "basic"}, "C299": {"drop": {IDS[0]}}}
    labs = {nm: dict(base) for nm in ok}
    labs.update({nm: dict(inv) for nm in bad})
    with tempfile.TemporaryDirectory() as d:
        res = run(write_set(d, labs, **ok, **bad), None, boot=0)
    C = res["coders"]
    assert res["eligible"] == sorted(ok) and res["primary"]["group"] == sorted(ok)
    assert C["P6"]["rules"]["b"]["status"] == R.PASS and C["P6of7"]["rules"]["b"]["status"] == R.PASS
    assert "only 7 of 8 practice items recorded" in C["P6of7"]["rules"]["b"]["detail"]
    assert C["P5"]["rules"]["b"]["status"] == R.FAIL
    assert C["T3"]["rules"]["d"]["status"] == R.PASS and C["T3"]["timing"]["median"] == 3.0
    assert C["T29"]["rules"]["d"]["status"] == R.FAIL
    assert C["Egood"]["rules"]["a"]["status"] == R.PASS and C["Ebasic"]["rules"]["a"]["status"] == R.FAIL
    assert C["C300"]["rules"]["c"]["status"] == R.PASS and C["C299"]["rules"]["c"]["status"] == R.FAIL
    for nm in bad:
        assert [k for k, v in C[nm]["rules"].items() if v["status"] != R.PASS] == [
            {"P5": "b", "T29": "d", "Ebasic": "a", "C299": "c"}[nm]], nm
    assert res["decision"]["status"] == "PASS"


def test_conditional_valence_set_exact():
    """Valence (both marked relevant) is computed on exactly the fragments both
    coders marked relevant; valence (all fragments) on all, `none` for
    non-relevant. Constructed: 50 both relevant (40 agree), 30 relevant for A
    only, 220 neither."""
    a, b = _uniform(*R0), _uniform(*R0)
    for i in range(50):
        a[IDS[i]] = M if i % 2 else P
        b[IDS[i]] = a[IDS[i]] if i < 40 else (P if a[IDS[i]] == M else M)
    for i in range(50, 80):
        a[IDS[i]] = M
    with tempfile.TemporaryDirectory() as d:
        res = run(write_set(d, {"A": a, "B": b}), None, boot=0)
    pr = res["primary"]["pairs"][0]
    cond = [(a[f][1], b[f][1]) for f in IDS[:50]]
    assert pr["valence_conditional"]["n"] == 50
    assert Fraction(pr["valence_conditional"]["value_exact"]) == R.kappa_exact(cond)
    assert pr["valence_all"]["n"] == 300
    assert Fraction(pr["valence_all"]["value_exact"]) == R.kappa_exact([(a[f][1], b[f][1]) for f in IDS])
    assert pr["valence_conditional"]["confusion"]["matrix"]["minus"]["none"] == 0
    assert pr["valence_all"]["confusion"]["matrix"]["minus"]["none"] == 30
    # gated: conditional valence 0.6 fails although the all-fragments version is higher
    assert R.kappa_exact(cond) == Fraction(3, 5)
    assert res["decision"]["status"] == "FAIL" and res["decision"]["failed"] == ["valence"]
    assert pr["valence_all"]["value"] > pr["valence_conditional"]["value"]


def test_sensitivity_exclusions_match_reduced_reference():
    """Each section-12 sensitivity set gives exactly the statistics of an
    independent run whose reference contains only the remaining fragments
    (same coders, same seed): primary pairs and mean with CIs, gate, alpha, PI
    comparisons, all pairs, timing, machine channels and the gold summary.
    Coders A and B agree everywhere except on the excluded fragments."""
    _, (pi, a, c) = sim_labels(3, seed=71)
    drop = set(R.CODEBOOK_ANCHOR_FRAG_IDS) | set(R.OLD_PRACTICE_PARAPHRASED_FRAG_IDS)
    b = {f: (a[f] if f not in drop else (R0 if a[f][0] == "1" else M)) for f in IDS}
    labs = {"PI": pi, "A": a, "B": b, "C": c}
    with tempfile.TemporaryDirectory() as d:
        files = write_set(d, labs, PI={"source": "researcher"}, C={"source": "researcher", "practice": (4, 8)})
        llm = write_llm_labels(os.path.join(d, "llm.csv"), c, status={IDS[3]: "refusal"})
        res = run(files, "PI", boot=60, seed=5, channels=[f"LLM={llm}"])
        reduced = {}
        for name in ("excl_anchors", "excl_both"):
            keep = [f for f in IDS if f not in res["sensitivity"]["fragment_sets"][name]["excluded"]]
            ref_csv = os.path.join(d, f"ref_{name}.csv")
            with open(ref_csv, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["frag_id", "text"])
                w.writerows([f, REF[f]] for f in keep)
            reduced[name] = run(files, "PI", boot=60, seed=5, channels=[f"LLM={llm}"], fragments=ref_csv,
                                anchor_ids=((), "test"), old_practice_ids=((), "test"))
    sets = res["sensitivity"]["fragment_sets"]
    assert {k: v["n"] for k, v in sets.items()} == {"excl_anchors": 284, "excl_old_practice": 225, "excl_both": 217}
    assert sets["excl_anchors"]["excluded"] == sorted(R.CODEBOOK_ANCHOR_FRAG_IDS)
    assert sets["excl_old_practice"]["excluded"] == sorted(R.OLD_PRACTICE_PARAPHRASED_FRAG_IDS)
    assert sets["excl_both"]["primary"]["mean"]["relevance"]["value_exact"] == "1/1"
    assert res["primary"]["mean"]["relevance"]["value"] < 0.70 < sets["excl_both"]["primary"]["mean"]["relevance"]["value"]
    assert res["decision"]["status"] == "FAIL" and sets["excl_both"]["primary"]["decision"]["status"] == "PASS"
    for name, red in reduced.items():
        st = sets[name]
        assert red["meta"]["reference"]["n"] == st["n"]
        assert red["eligible"] == res["eligible"] and red["primary"]["group"] == res["primary"]["group"]
        for key in ("pairs", "mean", "gate"):
            assert st["primary"][key] == red["primary"][key], (name, key)
        for key in ("alpha", "pi_vs_each", "by_source", "by_ui_language", "all_pairs"):
            assert st["secondary"][key] == red["secondary"][key], (name, key)
        assert st["secondary"]["timing"] == {nm: c["timing"] for nm, c in red["coders"].items()}
        for ch in ("dictionary_v0", "dictionary_v1", "LLM"):
            for dim in R.DIMS:
                assert st["machine_channels"][ch][dim] == red["machine_channels"][ch][dim], (name, ch, dim)
        keep = ("pi_tiebreaks_relevance", "pi_tiebreaks_valence", "unresolved_relevance_ids",
                "unresolved_valence_ids", "gold_relevant_counts", "gold_valence_counts", "status_counts")
        assert {k: st["adjudication"][k] for k in keep} == {k: red["adjudication"][k] for k in keep}, name


def test_exclusion_lists_constants_and_overrides():
    """The hard-coded lists (PROTOCOL section 12) are the 16 + 75 ids supplied,
    all among the 300; CLI overrides are reported, and an id outside the
    reference stops the run (it would silently shrink the exclusion)."""
    A, O = R.CODEBOOK_ANCHOR_FRAG_IDS, R.OLD_PRACTICE_PARAPHRASED_FRAG_IDS
    assert len(A) == len(set(A)) == 16 and len(O) == len(set(O)) == 75
    assert set(A) | set(O) <= set(IDS) and len(set(A) & set(O)) == 8
    assert list(A) == sorted(A) and list(O) == sorted(O)
    with tempfile.TemporaryDirectory() as d:
        _, (a, b) = sim_labels(2, seed=72)
        files = write_set(d, {"A": a, "B": b})
        idfile = os.path.join(d, "anchors.txt")
        open(idfile, "w", encoding="utf-8").write("frag_id\n# two anchors only\n" + IDS[0] + "\n" + IDS[1] + ", " + IDS[2] + "\n")
        out = os.path.join(d, "o")
        p = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), *files, "--no-pi",
                            "--boot", "0", "--out-dir", out, "--anchor-ids", idfile,
                            "--old-practice-ids", ",".join(O[:5])], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        res = json.load(open(os.path.join(out, "reliability.json"), encoding="utf-8"))
        lists = res["sensitivity"]["exclusion_lists"]
        assert lists["anchors"]["ids"] == IDS[:3] and lists["anchors"]["overridden"] is True
        assert lists["old_practice"]["ids"] == sorted(O[:5])
        assert res["sensitivity"]["fragment_sets"]["excl_both"]["n"] == 300 - len(set(IDS[:3]) | set(O[:5]))
        assert any("--anchor-ids" in w and "overrides" in w for w in res["warnings"])
        for spec in (f"{IDS[0]},not_a_fragment_000", f"{IDS[0]},{IDS[0]}", "not_a_fragment_000"):
            p = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), *files, "--no-pi",
                                "--boot", "0", "--out-dir", os.path.join(d, "o2"), "--anchor-ids", spec],
                               capture_output=True, text=True)
            assert p.returncode != 0 and "--anchor-ids" in p.stderr, (spec, p.stderr)
        assert not os.path.exists(os.path.join(d, "o2"))
    lst = R.exclusion_lists(IDS, {}, open(R.PROTOCOL_FILE, encoding="utf-8").read(), [])
    assert lst["anchors"]["ids"] == sorted(A) and lst["old_practice"]["n"] == 75


def test_frozen_identity_guards():
    """The run stops when the embedded dictionary v0 is not the one frozen in
    PROTOCOL 12.5.2, and warns when dictionary v1, the reference fragments or
    the drawing strata differ from 12.5.1 / 12.5.3 / 12.1(a). (The guards are
    exercised by patching the frozen value, since the real files match.)"""
    with tempfile.TemporaryDirectory() as d:
        _, (a, b) = sim_labels(2, seed=75)
        files = write_set(d, {"A": a, "B": b})
        saved = (R.V0_TERMS_SHA256, R.V1_FROZEN_BLOB, R.EVAL_INPUT_SHA256, R.DRAW_STRATA_V1)
        try:
            R.V0_TERMS_SHA256 = "0" * 64
            try:
                run(files, None, boot=0)
            except R.DataError as e:
                assert "12.5.2" in str(e)
            else:
                raise AssertionError("altered dictionary v0 accepted")
            R.V0_TERMS_SHA256 = saved[0]
            R.V1_FROZEN_BLOB = "0" * 40
            R.DRAW_STRATA_V1 = (136, 164)
            w = run(files, None, boot=0)["warnings"]
            assert any("not the version frozen in PROTOCOL section 12.5.1" in x for x in w)
            assert any("drawing strata recorded in section 12.1(a) are 136 / 164" in x for x in w)
            R.EVAL_INPUT_SHA256 = "0" * 64
            res = run(files, None, boot=0)
            assert any("not the evaluation input set" in x for x in res["warnings"])
            assert res["meta"]["reference"]["is_protocol_input_set"] is False
        finally:
            R.V0_TERMS_SHA256, R.V1_FROZEN_BLOB, R.EVAL_INPUT_SHA256, R.DRAW_STRATA_V1 = saved


def test_llm_labels_status_handling():
    """llm_labels.csv (ws1_llm_channel.py): only status ok is compared; refusal,
    invalid and pending rows are excluded and reported, also when a row carries
    labels; status ok without a valid label is reported; a file with some but
    not all of the four columns stops the run."""
    _, (pi, a, b, llm) = sim_labels(4, seed=73)
    status = {IDS[0]: "refusal", IDS[1]: "refusal", IDS[2]: ("invalid", True), IDS[3]: "pending"}
    with tempfile.TemporaryDirectory() as d:
        files = write_set(d, {"PI": pi, "A": a, "B": b})
        path = write_llm_labels(os.path.join(d, "llm_labels.csv"), llm, status=status)
        rows = open(path, encoding="utf-8").read().splitlines()
        rows[5] = rows[5].split(",")[0] + ",,,ok"                  # IDS[4]: status ok, no label
        open(path, "w", encoding="utf-8").write("\n".join(rows) + "\n")
        res = run(files, "PI", boot=0, channels=[f"LLM={path}"])
        bad = os.path.join(d, "bad.csv")
        open(bad, "w", encoding="utf-8").write("frag_id,relevant_llm,valence_llm\n" + IDS[0] + ",1,minus\n")
        try:
            run(files, "PI", boot=0, channels=[f"LLM={bad}"])
        except R.DataError as e:
            assert "status_llm" in str(e)
        else:
            raise AssertionError("llm_labels.csv without status_llm accepted")
    prov = res["machine_channels"]["LLM"]["provenance"]
    assert prov["status_llm_counts"] == {"invalid": 1, "ok": 296, "pending": 1, "refusal": 2}
    assert prov["excluded_status_not_ok"] == {"invalid": 1, "pending": 1, "refusal": 2}
    assert prov["excluded_status_not_ok_ids"]["refusal"] == IDS[:2]
    assert prov["labels_present_but_status_not_ok"] == [IDS[2]]
    assert prov["status_ok_without_valid_label"] == [IDS[4]]
    assert prov["n_labelled"] == 295
    gold = res["gold_rows"]
    keep = [g for g in gold if g["frag_id"] not in IDS[:5]]
    exp = R.kappa_exact([(g["gold_relevant"], llm[g["frag_id"]][0]) for g in keep if g["gold_relevant"]])
    ch = res["machine_channels"]["LLM"]
    assert Fraction(ch["relevance"]["value_exact"]) == exp
    assert gold[2]["LLM_relevant"] is None and gold[2]["LLM_valence"] is None   # invalid row's labels not used
    assert any("status_llm other than ok excluded" in w for w in res["warnings"])
    assert any("status ok but no valid label" in w for w in res["warnings"])


def test_llm_run_record_and_served_model():
    """The run record next to llm_labels.csv is read: its labels_sha256 must be
    the file's, the input set the protocol's, the run complete, and its four
    identities those written in PROTOCOL 12.5.3 (a run whose record carries
    other values is not LLM channel v1, 12.6.2, even if the verifier's FROZEN
    table was changed to match it); more than one served model is flagged."""
    _, (pi, a, b, llm) = sim_labels(4, seed=74)
    good = dict(R.LLM_V1_IDENTITY, channel=R.LLM_V1_CHANNEL, run_id="r1", complete=True, labels_sha256="auto",
                models_served=["claude-opus-5-5"], raw_log_sha256="0" * 64)
    other = dict(good, runner_sha256="0" * 64, prompt_sha256="1" * 64, spec_sha256="2" * 64)
    with tempfile.TemporaryDirectory() as d:
        files = write_set(d, {"PI": pi, "A": a, "B": b})
        cases = {}
        for tag, rec, served in (("ok", good, {None: "claude-opus-5-5"}),
                                 ("stale", dict(good, labels_sha256="f" * 64), {None: "claude-opus-5-5"}),
                                 ("other", other, {None: "claude-opus-5-5"}),
                                 ("partial", dict(good, complete=False, input_set_sha256="x"),
                                  {None: "claude-opus-5-5", IDS[9]: "other-model"})):
            sub = os.path.join(d, tag)
            os.makedirs(sub)
            path = write_llm_labels(os.path.join(sub, "llm_labels.csv"), llm, served=served, record=rec)
            res = run(files, "PI", boot=0, channels=[f"LLM={path}"])
            cases[tag] = (res, R.write_outputs(res, os.path.join(sub, "out")))
        report = open(cases["ok"][1]["report"], encoding="utf-8").read()
        report_other = open(cases["other"][1]["report"], encoding="utf-8").read()
        # the verifier's FROZEN table changed to match another runner: still not channel v1
        table = os.path.join(d, "verify_frozen_channels.py")
        src = open(R.VERIFY_FILE, encoding="utf-8").read()
        open(table, "w", encoding="utf-8").write(src.replace(R.LLM_V1_IDENTITY["runner_sha256"], "0" * 64))
        saved = R.VERIFY_FILE
        R.VERIFY_FILE = table
        try:
            res_t = run(files, "PI", boot=0, channels=[f"LLM={os.path.join(d, 'other', 'llm_labels.csv')}"])
        finally:
            R.VERIFY_FILE = saved
    res, _ = cases["ok"]
    prov = res["machine_channels"]["LLM"]["provenance"]
    assert prov["model_served_counts_ok_rows"] == {"claude-opus-5-5": 300}
    rr = prov["run_record"]
    assert rr["found"] and rr["run_id"] == "r1" and rr["labels_sha256_matches"] and rr["input_set_matches_protocol"]
    assert rr["identity_matches_protocol"] and rr["identity_differs"] == [] and rr["channel"] == R.LLM_V1_CHANNEL
    assert not any("run record" in w or "served by more than one model" in w or "LLM channel v1" in w
                   or "NOT LLM CHANNEL" in w for w in res["warnings"])
    assert "Run record `llm_labels_run.json`" in report and "labels_sha256 matches this file: True" in report
    assert "as written in §12.5.3: True" in report
    w = cases["stale"][0]["warnings"]
    assert any("not the labels_sha256 of its run record" in x for x in w)
    assert not any("NOT LLM CHANNEL" in x for x in w)
    rr = cases["other"][0]["machine_channels"]["LLM"]["provenance"]["run_record"]
    assert rr["labels_sha256_matches"] and not rr["identity_matches_protocol"]
    assert rr["identity_differs"] == ["runner_sha256", "prompt_sha256", "spec_sha256"]
    w = cases["other"][0]["warnings"]
    assert [x for x in w if "NOT LLM CHANNEL v1" in x and "runner_sha256 000000000000" in x
            and "spec_sha256 222222222222" in x and "12.6.2" in x], w
    assert "not LLM channel v1" in report_other and "differ: runner_sha256, prompt_sha256, spec_sha256" in report_other
    w = res_t["warnings"]
    assert any("NOT LLM CHANNEL v1" in x for x in w)
    assert [x for x in w if x.startswith("LLM channel v1 identity: the FROZEN table of verify_frozen_channels.py")
            and "['runner_sha256']" in x], w
    w = cases["partial"][0]["warnings"]
    assert any("does not mark the run complete" in x for x in w)
    assert any("names input set x" in x for x in w)
    assert any("served by more than one model" in x for x in w)
    assert any("NOT LLM CHANNEL v1" in x and "input_set_sha256" in x for x in w)


def test_llm_frozen_consistency():
    """The LLM channel v1 identities held here must be written in section 12 of
    the protocol on disk and equal the verifier's FROZEN table (which the runner
    reads); each difference is named."""
    text = open(R.PROTOCOL_FILE, encoding="utf-8").read()
    table = R.frozen_table()
    assert table is not None and R.llm_frozen_consistency(text) == [] and R.llm_frozen_consistency(text, table) == []
    p = R.llm_frozen_consistency(text, dict(table, llm_spec_sha256="f" * 64))
    assert len(p) == 1 and "FROZEN table" in p[0] and "['spec_sha256']" in p[0]
    p = R.llm_frozen_consistency(text.replace(R.LLM_V1_IDENTITY["prompt_sha256"], "0" * 64), table)
    assert len(p) == 1 and "section 12 on disk" in p[0] and "['prompt_sha256']" in p[0]
    assert R.frozen_table(os.path.join(WS1, "no_such_file.py")) is None
    p = R.llm_frozen_consistency(text, {})
    assert len(p) == 1 and "['runner_sha256', 'prompt_sha256', 'spec_sha256', 'input_set_sha256']" in p[0]


def test_constants_agree_with_protocol_and_verifier():
    """The exclusion lists, the input-set hash, the practice set and the
    dictionary identities held here are the ones written in PROTOCOL section 12
    and held by verify_frozen_channels.py; a protocol line that lists other ids
    (or is missing) is reported."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("vfc", os.path.join(WS1, "verify_frozen_channels.py"))
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    assert sorted(V.SENSITIVITY_SETS["codebook_anchors"]) == list(R.CODEBOOK_ANCHOR_FRAG_IDS)
    assert sorted(V.SENSITIVITY_SETS["old_practice_paraphrased"]) == list(R.OLD_PRACTICE_PARAPHRASED_FRAG_IDS)
    assert V.FROZEN["input_set_sha256"] == R.EVAL_INPUT_SHA256
    assert V.FROZEN["practice_set"] == R.PRACTICE_SET_PROTOCOL
    assert (V.FROZEN["dict_v0_git_blob"], V.FROZEN["dict_v0_file_sha256"], V.FROZEN["dict_v0_terms_sha256"]) == \
        (R.V0_BLOB, R.V0_FILE_SHA256, R.V0_TERMS_SHA256)
    assert V.FROZEN["dict_v1_git_blob"] == R.V1_FROZEN_BLOB
    assert R.terms_sha256(R.V0_LISTS) == R.V0_TERMS_SHA256
    for k, fk in R.VERIFY_KEYS.items():                  # LLM channel v1 identities (12.5.3)
        assert V.FROZEN[fk] == R.LLM_V1_IDENTITY[k], k
    assert V.RUN_RECORD_KEYS == R.VERIFY_KEYS and V.LLM_CHANNEL == R.LLM_V1_CHANNEL
    spec = importlib.util.spec_from_file_location("llmch", os.path.join(WS1, "ws1_llm_channel.py"))
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    assert L.FROZEN_KEYS == R.VERIFY_KEYS and L.CHANNEL == R.LLM_V1_CHANNEL
    text = open(R.PROTOCOL_FILE, encoding="utf-8").read()
    for value in (R.EVAL_INPUT_SHA256, R.PRACTICE_SET_PROTOCOL, R.V0_FILE_SHA256, R.V0_TERMS_SHA256, R.V1_FROZEN_BLOB,
                  *R.LLM_V1_IDENTITY.values()):
        assert value in text, value
    w = []
    lists = R.exclusion_lists(IDS, {}, text, w)
    assert w == [] and lists["anchors"]["matches_protocol_12_3"] and lists["old_practice"]["matches_protocol_12_3"]
    assert lists["anchors"]["n_in_protocol_12_3"] == 16 and lists["old_practice"]["n_in_protocol_12_3"] == 75
    dropped = text.replace("`jynC9SncpDM_000`, ", "", 1)          # one id fewer on the anchors line
    w = []
    lists = R.exclusion_lists(IDS, {}, dropped, w)
    assert lists["anchors"]["matches_protocol_12_3"] is False and any("differ from section 12.3" in x for x in w)
    w = []
    lists = R.exclusion_lists(IDS, {}, text.replace("- (b) Earlier practice items:", "- (b) Practice:"), w)
    assert lists["old_practice"]["matches_protocol_12_3"] is None and any("could not be checked" in x for x in w)


def test_page_practice_first_attempt_export():
    """make_artifact_page.py: practice_correct/practice_n = first entry per
    practice item, also after a JSON round trip (resumed session)."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        skip("node not installed")
    with tempfile.TemporaryDirectory() as d:
        page = os.path.join(d, "page.html")
        subprocess.run([sys.executable, os.path.join(WS1, "make_artifact_page.py"), "--out", page],
                       check=True, capture_output=True)
        script = re.search(r"<script>(.*?)</script>", open(page, encoding="utf-8").read(), re.S).group(1)
        fns = "\n".join(js_function(script, name) for name in ("csvCell", "practiceFirst", "buildCSV"))
        practice = [{"i": 0, "ok": False}, {"i": 0, "ok": True}, {"i": 1, "ok": True}, {"i": 2, "ok": True},
                    {"i": 2, "ok": False}, {"i": 2, "ok": True}, {"i": 3, "ok": True}, {"i": 4, "ok": True},
                    {"i": 5, "ok": True}, {"i": 6, "ok": False}, {"i": 7, "ok": True}]
        S = {"coder": "Anna", "seed": 1, "startedAt": "s", "finishedAt": "e", "lang": "ru", "english": "good",
             "source": "public", "practice": practice,
             "answers": [{"frag_id": IDS[1], "rel": "0", "val": "none", "position": 1, "secs": 4},
                         {"frag_id": IDS[0], "rel": "1", "val": "minus", "position": 2, "secs": 7}]}
        js = (f"const FRAGMENTS = {json.dumps([{'id': f, 'text': REF[f]} for f in IDS[:2]])};\n"
              f"const CODEBOOK = 'v1'; let LANG = 'en';\n"
              f"let S = JSON.parse(JSON.stringify({json.dumps(S)}));\n{fns}\n"
              "process.stdout.write(JSON.stringify(practiceFirst()) + '\\n' + buildCSV());\n")
        jf = os.path.join(d, "t.js")
        open(jf, "w", encoding="utf-8").write(js)
        out = subprocess.run(["node", jf], capture_output=True, text=True, check=True).stdout
        first, csv_text = out.split("\n", 1)
        assert json.loads(first) == {"ok": 6, "n": 8}           # old count (all ok entries) would be 8
        rows = list(csv.DictReader(io.StringIO(csv_text)))
        assert [r["practice_correct"] for r in rows] == ["6", "6"] and rows[0]["practice_n"] == "8"
        cf = os.path.join(d, "anna.csv")
        open(cf, "w", encoding="utf-8").write(csv_text)
        parsed = R.read_coder_file(cf)
    assert parsed["format"] == "page" and parsed["session"]["practice_correct"] == "6"
    # practice entries without a set id (saved by a page built before the id existed) export as untagged
    assert parsed["session"].get("practice_set") == "untagged", parsed["session"]


# ---------------------------------------------------------------------------
def main():
    tests = [(k, v) for k, v in sorted(globals().items(), key=lambda kv: kv[1].__code__.co_firstlineno
                                       if callable(kv[1]) and hasattr(kv[1], "__code__") else 0)
             if k.startswith("test_") and callable(v)]
    results = Counter()
    for name, fn in tests:
        try:
            with redirect_stdout(io.StringIO()):
                fn()
            print(f"PASS  {name}")
            results["pass"] += 1
        except unittest.SkipTest as e:
            print(f"SKIP  {name}: {e}")
            results["skip"] += 1
        except Exception as e:  # noqa: BLE001
            import traceback
            print(f"FAIL  {name}: {e.__class__.__name__}: {e}")
            traceback.print_exc()
            results["fail"] += 1
    print(f"\n{results['pass']} passed, {results['fail']} failed, {results['skip']} skipped "
          f"(reference fragments: {os.path.basename(REF_SRC)}, {len(IDS)})")
    sys.exit(1 if results["fail"] else 0)


if __name__ == "__main__":
    main()
