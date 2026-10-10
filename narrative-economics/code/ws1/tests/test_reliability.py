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

All coder data here are SYNTHETIC (simulated labels on the real fragment
ids); nothing in this file is human coding.
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
               times=None, bom=False, drop=(), extra_rows=(), seed=0, ref=None):
    """labels: {fid: (rel, val)}; practice=None -> no practice columns (pre-fix export);
    ref: {fid: text} of another fragment set (default: the real 300)."""
    rng = random.Random(seed)
    ref = REF if ref is None else ref
    head = PAGE_HEAD if practice is not None else PAGE_HEAD[:-2]
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
            w.writerow(row + (list(practice) if practice is not None else []))
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


def make_synthetic_page_set(out_dir, seed=11):
    """Three SYNTHETIC page-format CSVs: the PI and two publicly recruited coders."""
    _, (pi, a, b) = sim_labels(3, seed)
    return [write_page(os.path.join(out_dir, "ws1_coded_SYN_PI.csv"), "SYN_PI", pi, source="researcher",
                       english="native", ui="ru", seed=seed),
            write_page(os.path.join(out_dir, "ws1_coded_SYN_public_A.csv"), "SYN_public_A", a,
                       english="fluent", ui="en", practice=(7, 8), seed=seed + 1),
            write_page(os.path.join(out_dir, "ws1_coded_SYN_public_B.csv"), "SYN_public_B", b,
                       english="good", ui="he", practice=(6, 8), seed=seed + 2)]


def run(files, pi, meta=None, boot=200, seed=2026, **kw):
    """pi=None declares that the PI did not code (--pi-did-not-code)."""
    if pi is None:
        kw.setdefault("pi_did_not_code", True)
    return R.analyse(files, pi, R.read_meta(meta) if meta else None, boot, seed, **kw)


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
    gold = res["gold_rows"]
    assert all(g["n_voters"] == 1 and g["relevance_status"] == "majority" for g in gold)
    assert [g["gold_relevant"] for g in gold] == [pi[f][0] for f in IDS]
    assert any("rest on 1 eligible coder" in w for w in res["warnings"])


def _uniform(rel, val):
    return {f: (rel, val) for f in IDS}


def test_ties_and_pi_tiebreaks():
    f0, f1, f2 = IDS[0], IDS[1], IDS[2]
    base = {nm: _uniform("1", "minus") for nm in ("PI", "A", "B", "C", "D")}
    # f0: relevance 2-2 among A..D, PI votes 1 -> 3-2 majority (PI is an eligible voter)
    for nm, r in zip(("A", "B", "C", "D"), "1100"):
        base[nm][f0] = (r, "minus" if r == "1" else "none")
    # f1: valence minus,minus,plus,plus + PI none -> tie, PI label not among tied -> unresolved
    for nm, v in zip(("A", "B", "C", "D", "PI"), ("minus", "minus", "plus", "plus", "none")):
        base[nm][f1] = ("1", v)
    # f2: A,B minus; C,D plus; PI plus -> 3-2 for plus
    for nm, v in zip(("A", "B", "C", "D", "PI"), ("minus", "minus", "plus", "plus", "plus")):
        base[nm][f2] = ("1", v)
    with tempfile.TemporaryDirectory() as d:
        files = [write_page(os.path.join(d, f"{nm}.csv"), nm, lab, seed=i) for i, (nm, lab) in enumerate(base.items())]
        res = run(files, "PI", boot=0)
        g = {r["frag_id"]: r for r in res["gold_rows"]}
        assert g[f0]["gold_relevant"] == "1" and g[f0]["relevance_status"] == "majority"
        assert g[f1]["gold_valence"] is None and "not among the tied" in g[f1]["valence_status"]
        assert g[f2]["gold_valence"] == "plus" and g[f2]["valence_status"] == "majority"
        # PI does not vote, only breaks ties: f0 relevance (2-2) and f2 valence (2-2)
        # become PI tie-breaks; f0 valence is then minus (A, B, the only voters who
        # marked it relevant); f1 stays unresolved
        alt = res["adjudication"]["sensitivity"]["pi_breaks_ties_only"]
        assert alt["pi_tiebreaks_relevance"] == 1 and alt["pi_tiebreaks_valence"] == 1, alt
        assert g[f0]["alt_pi_breaks_ties_only_relevant"] == "1" and g[f0]["alt_pi_breaks_ties_only_valence"] == "minus"
        # the PI decided f0 relevance (A, B vs C, D split) and f2 valence (2-2 split) in the reading of record
        assert g[f0]["pi_decided_relevance"] == "yes" and g[f2]["pi_decided_valence"] == "yes"
        assert g[f1]["pi_decided_valence"] == "no"
        # 4 voters, PI declared not to have coded: ties unresolved, and an
        # unresolved relevance leaves the valence unresolved although A and B
        # (the voters who marked f0 relevant) agree on minus
        res2 = run([p for p in files if not p.endswith("PI.csv")], None, boot=0)
        g2 = {r["frag_id"]: r for r in res2["gold_rows"]}
        assert g2[f0]["gold_relevant"] is None and g2[f0]["relevance_status"] == "unresolved: tie, PI did not code"
        assert g2[f0]["gold_valence"] is None and g2[f0]["valence_status"] == "unresolved: relevance unresolved"
        assert any("--pi-did-not-code" in w for w in res2["warnings"])
        assert res2["adjudication"]["fragments_pi_decided"] == 0
        # three voters (PI eligible) on a 3-way valence split -> PI tie-break counted
        three = {nm: _uniform("1", "minus") for nm in ("PI", "A", "B")}
        for nm, v in zip(("A", "B", "PI"), ("minus", "plus", "mixed")):
            three[nm][f1] = ("1", v)
        files3 = [write_page(os.path.join(d, f"t_{nm}.csv"), nm, lab, seed=i) for i, (nm, lab) in enumerate(three.items())]
        res3 = run(files3, "PI", boot=0)
    g3 = {r["frag_id"]: r for r in res3["gold_rows"]}
    assert g3[f1]["gold_valence"] == "mixed" and g3[f1]["valence_status"] == "PI tie-break"
    assert res3["adjudication"]["pi_tiebreaks_valence"] == 1
    assert res3["adjudication"]["fragments_with_any_pi_tiebreak"] == 1


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
        llm = write_basic(os.path.join(d, "llm.csv"), pi, with_text=False, drop=set(IDS[:4]))
        res = run(files, "PI", boot=0, channels=[f"LLM={llm}"])
        ch = res["machine_channels"]["LLM"]
        gold = res["gold_rows"]
        exp = R.kappa_counts([(g["gold_relevant"], pi[g["frag_id"]][0]) for g in gold
                              if g["frag_id"] not in IDS[:4]])[0]
        assert ch["relevance"]["n"] == 296 and abs(ch["relevance"]["value"] - exp) < 1e-12
        assert not any("LLM channel" in w for w in res["warnings"])
        assert gold[10]["LLM_relevant"] == pi[gold[10]["frag_id"]][0]
        # valence (both relevant) = fragments that gold AND the channel mark relevant
        both = [(g["gold_valence"], pi[g["frag_id"]][1]) for g in gold if g["frag_id"] not in IDS[:4]
                and g["gold_relevant"] == "1" and pi[g["frag_id"]][0] == "1"]
        assert ch["valence_conditional"]["n"] == len(both) < sum(g["gold_relevant"] == "1" for g in gold)
        assert abs(ch["valence_conditional"]["value"] - R.kappa_counts(both)[0]) < 1e-12
        # llm_labels.csv as ws1_llm_channel.py writes it (PROTOCOL 12.2): refusals have empty labels
        llm2 = os.path.join(d, "llm_labels.csv")
        with open(llm2, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["frag_id", "relevant_llm", "valence_llm", "status_llm"])
            for i, f in enumerate(IDS):
                w.writerow([f, "", "", "refusal"] if i < 2 else [f, pi[f][0], pi[f][1], "ok"])
        res_l = run(files, "PI", boot=0, channels=[f"LLM={llm2}"])
        cl = res_l["machine_channels"]["LLM"]
        assert cl["provenance"]["status_llm_counts"] == {"refusal": 2, "ok": 298}
        assert cl["provenance"]["n_labelled"] == 298 and cl["relevance"]["n"] == 298
        exp2 = R.kappa_counts([(g["gold_relevant"], pi[g["frag_id"]][0]) for g in res_l["gold_rows"]
                               if g["frag_id"] not in IDS[:2]])[0]
        assert abs(cl["relevance"]["value"] - exp2) < 1e-12
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
    def gate(r, v):
        return {"relevance": {"pass": r, "why": "r"}, "valence_conditional": {"pass": v, "why": "v"}}
    assert R.decide(gate(True, True))["status"] == "PASS"
    d = R.decide(gate(True, False))
    assert d["status"] == "FAIL" and d["failed"] == ["valence"] and d["valence_only"]
    d = R.decide(gate(False, True))
    assert d["status"] == "FAIL" and d["failed"] == ["relevance"] and not d["valence_only"]
    d = R.decide(gate(False, False))
    assert d["status"] == "FAIL" and d["failed"] == ["relevance", "valence"] and not d["valence_only"]
    for r, v in ((None, True), (True, None), (None, False), (False, None), (None, None)):
        assert R.decide(gate(r, v))["status"] == "NOT ASSESSABLE", (r, v)


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


def test_gold_rules_and_readings():
    f0, f1 = IDS[0], IDS[1]
    # five eligible voters: the PI and A-D
    five = {nm: _uniform("1", "minus") for nm in ("PI", "A", "B", "C", "D")}
    for nm in ("PI", "B", "C", "D"):        # f0: relevance 0 by 4 to 1
        five[nm][f0] = ("0", "none")
    # f1: A, B relevant/minus, C relevant/plus, D and the PI not relevant
    five["C"][f1], five["D"][f1], five["PI"][f1] = ("1", "plus"), ("0", "none"), ("0", "none")
    # three voters: the PI and A, B
    three = {nm: _uniform("1", "minus") for nm in ("PI", "A", "B")}
    three["B"][f0], three["PI"][f0] = ("1", "plus"), ("0", "none")                  # A minus, B plus, PI not relevant
    three["A"][f1], three["B"][f1], three["PI"][f1] = ("1", "plus"), ("0", "none"), ("1", "mixed")
    with tempfile.TemporaryDirectory() as d:
        res5 = run([write_page(os.path.join(d, f"5{nm}.csv"), nm, lab, seed=i) for i, (nm, lab) in enumerate(five.items())],
                   "PI", boot=0)
        res3 = run([write_page(os.path.join(d, f"3{nm}.csv"), nm, lab, seed=i) for i, (nm, lab) in enumerate(three.items())],
                   "PI", boot=0)
    g = {r["frag_id"]: r for r in res5["gold_rows"]}
    # gold relevance 0 -> valence none, whatever the minority's valence
    assert (g[f0]["gold_relevant"], g[f0]["gold_valence"]) == ("0", "none")
    assert g[f0]["valence_status"] == "rule: gold relevance 0 -> none"
    # valence is voted among those who marked it relevant: minus 2, plus 1
    assert (g[f1]["gold_relevant"], g[f1]["gold_valence"], g[f1]["valence_status"]) == ("1", "minus", "majority")
    # voting over all-fragments labels instead: minus 2 / none 2, the PI's `none` breaks
    # the tie -> 'relevant, none' that no coder who marked it relevant chose
    assert g[f1]["alt_valence_over_all_labels_valence"] == "none"
    adj = res5["adjudication"]
    assert adj["relevant_none_without_support"] == 0
    assert adj["sensitivity"]["valence_over_all_labels"]["relevant_none_without_support"] == 1
    g = {r["frag_id"]: r for r in res3["gold_rows"]}
    # A minus, B plus, PI not relevant: a valence tie the PI cannot break
    assert (g[f0]["gold_relevant"], g[f0]["gold_valence"]) == ("1", None)
    assert g[f0]["valence_status"] == "unresolved: tie, PI did not mark it relevant"
    assert g[f0]["alt_valence_over_all_labels_valence"] == "none"
    assert g[f0]["alt_pi_breaks_ties_only_valence"] is None
    # f1: A relevant, B not, PI relevant -> 2 to 1, no tie, but the PI's vote decided it;
    # valence: A plus, PI mixed -> tie broken by the PI (who marked it relevant)
    assert (g[f1]["gold_relevant"], g[f1]["relevance_status"]) == ("1", "majority")
    assert (g[f1]["gold_valence"], g[f1]["valence_status"]) == ("mixed", "PI tie-break")
    assert g[f1]["pi_decided_relevance"] == "yes" and g[f1]["pi_decided_valence"] == "yes"
    assert g[f0]["pi_decided_relevance"] == "no"
    adj = res3["adjudication"]
    assert adj["pi_tiebreaks_relevance"] == 0 and adj["pi_decided_relevance"] == 1
    assert adj["pi_tiebreaks_valence"] == 1 and adj["unresolved_valence"] == 1
    assert adj["sensitivity"]["valence_over_all_labels"]["relevant_none_without_support"] == 1


def test_pi_must_match_an_input_coder():
    """Section 6: the PI is never in the primary kappa, so an --pi that matches
    no coder stops the run instead of letting the PI's file through."""
    with tempfile.TemporaryDirectory() as d:
        _, (pi, a, b) = sim_labels(3, seed=62)
        files = [write_page(os.path.join(d, "ws1_coded_Gregory.csv"), "Gregory", pi, source="researcher", seed=1),
                 write_page(os.path.join(d, "a.csv"), "A", a, source="researcher", seed=2),
                 write_page(os.path.join(d, "b.csv"), "B", b, source="researcher", seed=3)]
        for pi_arg, kw in (("Gregory Diachenko", {}), ("", {}), ("Gregory", {"pi_did_not_code": True})):
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
    # Regression values on the 300 fragments. 136 / 164 is also the split stated
    # in PROTOCOL section 2, but it does not show which dictionary drew the
    # sample: every v0-relevant fragment is v1-relevant here, so a v1 draw gives
    # 136 under v0 as well (see the comment above V0_COMMIT).
    import ws1_pipeline
    set0 = {f for f in IDS if R.classify_v0(REF[f])[4]}
    set1 = {f for f in IDS if ws1_pipeline.classify(REF[f])[-2]}
    assert rel0 == 136 and len(texts) - rel0 == 164
    assert len(set1) == 140 and set0 <= set1
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
    with tempfile.TemporaryDirectory() as d:
        files = make_synthetic_page_set(d, seed=51)
        out = os.path.join(d, "out")
        p = subprocess.run([sys.executable, os.path.join(WS1, "ws1_reliability.py"), *files,
                            "--pi", "SYN_PI", "--boot", "200", "--out-dir", out], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        assert "GATE:" in p.stdout
        res = json.load(open(os.path.join(out, "reliability.json"), encoding="utf-8"))
        gold = list(csv.DictReader(open(os.path.join(out, "gold_labels.csv"), encoding="utf-8")))
        excl = list(csv.DictReader(open(os.path.join(out, "exclusions.csv"), encoding="utf-8")))
        report = open(os.path.join(out, "reliability_report.md"), encoding="utf-8").read()
    assert len(gold) == 300 and len(excl) == 3 and "text" not in gold[0]
    assert res["decision"]["status"] in ("PASS", "FAIL")
    assert res["primary"]["group"] == ["SYN_public_A", "SYN_public_B"]
    assert res["machine_channels"]["dictionary_v0"]["provenance"]["n_relevant"] == 136
    assert res["machine_channels"]["dictionary_v1"]["provenance"]["matches_protocol_12_1"] is True
    assert "## 1. Decision" in report and "Krippendorff" in report
    proto = R.protocol_info()
    assert res["meta"]["protocol"]["sha256"] == proto["sha256"]
    assert f"protocol PROTOCOL_WS1.0.md v{proto['version']} ({proto['date']})" in report
    assert "Gold labels decided by the PI's label" in report
    assert {"pi_decided_relevance", "alt_pi_breaks_ties_only_valence",
            "alt_valence_over_all_labels_valence"} <= set(gold[0])


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
