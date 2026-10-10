"""
audit_hardcoded.py — audit of the hand-typed ELOUNDOU_SAMPLE against the source.

The first version of code/exposure_scores.py (commit 492573c, 2026-06-14)
contained a dict ELOUNDOU_SAMPLE of 26 occupations with "approximate Eloundou
alpha scores" and no stated source. This script reads that dict from git (it
is not retyped anywhere), matches every entry to Eloundou et al.'s published
occ_level.csv and writes AUDIT_hardcoded_vs_source.md next to this file.

Usage (from anywhere inside the repository):
    python code/data/exposure/audit_hardcoded.py
"""
import ast
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, CODE)
import exposure_scores as es  # noqa: E402

AUDITED_COMMIT = "492573c"
AUDITED_PATH = "narrative-economics/code/exposure_scores.py"
OUT = os.path.join(HERE, "AUDIT_hardcoded_vs_source.md")
TOL = 0.02
# Successor codes for audited 2010-SOC codes absent from the 2018-SOC source.
# Used only for an informational title match, never for the verdict.
SOC2010_TO_2018 = {"31-1014": "31-1131"}  # Nursing Assistants
SHOWN = ["human_alpha", "gpt4_alpha", "human_beta", "gpt4_beta"]
FILE_COL = {k: es.ELOUNDOU_COLUMNS[k] for k in SHOWN}


def read_audited_dict():
    """Return ELOUNDOU_SAMPLE exactly as committed in AUDITED_COMMIT."""
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE,
                          capture_output=True, text=True, check=True).stdout.strip()
    src = subprocess.run(["git", "show", f"{AUDITED_COMMIT}:{AUDITED_PATH}"],
                         cwd=root, capture_output=True, text=True, check=True).stdout
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "ELOUNDOU_SAMPLE":
            return ast.literal_eval(node.value)
    raise RuntimeError("ELOUNDOU_SAMPLE not found in audited file")


N_SHUFFLES = 5000
SEED = 0
# Differences are compared as d <= tol + EPS so that a value exactly `tol`
# away (e.g. 0.08 vs 0.10) counts as within `tol` despite float rounding.
EPS = 1e-9


def within(d, tol=TOL):
    """True where |difference| d is at most `tol` (float-safe)."""
    return d <= tol + EPS


def chance_coverage(values, tol=TOL):
    """Share of [0, 1] lying within `tol` of at least one of `values`."""
    grid = np.linspace(0, 1, 100001)
    hit = np.zeros_like(grid, dtype=bool)
    for v in values:
        hit |= within(np.abs(grid - v), tol)
    return hit.mean()


def count_hits(values, pools, tol):
    """Number of i with values[i] within `tol` of some number in pools[i]."""
    return int(sum(np.any(within(np.abs(p - v), tol)) for v, p in zip(values, pools)))


def shuffle_null(values, pools, tol=TOL, n=N_SHUFFLES, seed=SEED):
    """Hit counts after shuffling `values` across occupations (seeded).

    Keeps the distribution of the hard-coded values but breaks their link to
    a particular occupation, so it asks whether near-hits are
    occupation-specific rather than whether they beat uniform random numbers.
    """
    rng = np.random.default_rng(seed)
    values = np.asarray(values)
    return np.array([count_hits(rng.permutation(values), pools, tol)
                     for _ in range(n)])


def fmt(x):
    return "" if pd.isna(x) else f"{x:.3f}"


def main():
    audited = read_audited_dict()
    onet = es.load_eloundou_onet()
    soc = es.load_eloundou().set_index("soc")
    measures = list(es.ELOUNDOU_MEASURES)

    rows, lines = [], []
    for (code, title), h in audited.items():
        if code in soc.index:
            r = soc.loc[code]
            d_h, d_g = abs(h - r["human_alpha"]), abs(h - r["gpt4_alpha"])
            closest = min(d_h, d_g)
            detail = onet[onet["soc"] == code]
            det_hit = bool(within(np.minimum((detail["human_alpha"] - h).abs(),
                                             (detail["gpt4_alpha"] - h).abs())).any())
            verdict = f"matches within {TOL}" if within(closest) else "differs"
            src_label = (r["title"] if r["n_onet"] == 1
                         else f"mean of {int(r['n_onet'])} O*NET-SOC codes")
            # Best match over all six measures and all detailed codes.
            errs = {(d["onet_soc"], c): abs(h - d[c])
                    for _, d in detail.iterrows() for c in measures}
            (best_code, best_col), best_err = min(errs.items(), key=lambda t: t[1])
            rows.append(dict(soc=code, title=title, hard=h, closest=closest,
                             verdict=verdict, **{m: r[m] for m in measures},
                             any6=best_err, any6_col=best_col, any6_code=best_code,
                             cover=chance_coverage(detail[measures].to_numpy().ravel()),
                             det_hit=det_hit))
            lines.append(f"| {code} | {title} | {src_label} | {h:.2f} | "
                         + " | ".join(fmt(r[m]) for m in SHOWN)
                         + f" | {closest:.3f} | **{verdict}** |")
            if r["n_onet"] > 1:
                for _, d in detail.iterrows():
                    dc = min(abs(h - d["human_alpha"]), abs(h - d["gpt4_alpha"]))
                    lines.append(f"| ↳ {d['onet_soc']} | | {d['title']} | | "
                                 + " | ".join(fmt(d[m]) for m in SHOWN)
                                 + f" | {dc:.3f} | (detail) |")
        else:
            rows.append(dict(soc=code, hard=h, verdict="no matching SOC code in source"))
            lines.append(f"| {code} | {title} | — (code not in source) | {h:.2f} | "
                         "| | | | | **no matching SOC code in source** |")
            new = SOC2010_TO_2018.get(code)
            if new and new in soc.index:
                r = soc.loc[new]
                dc = min(abs(h - r["human_alpha"]), abs(h - r["gpt4_alpha"]))
                lines.append(f"| ↳ {new} | | {r['title']} (2018-SOC successor; "
                             f"title match, informational) | | "
                             + " | ".join(fmt(r[m]) for m in SHOWN)
                             + f" | {dc:.3f} | (would be: "
                             + ("matches" if within(dc) else "differs") + ") |")

    res = pd.DataFrame(rows)
    m = res[res["verdict"] != "no matching SOC code in source"].copy()
    n_match = int((m["verdict"] != "differs").sum())
    n_diff = int((m["verdict"] == "differs").sum())
    n_none = int(len(res) - len(m))

    fit = []
    for c in measures:
        err = (m["hard"] - m[c]).abs()
        fit.append((c, es.ELOUNDOU_COLUMNS[c], err.mean(), err.max(),
                    int(within(err).sum()), m["hard"].corr(m[c]),
                    m["hard"].corr(m[c], method="spearman")))
    exp_any = m["cover"].sum()
    obs_any = int(within(m["any6"]).sum())
    max_h_alpha = soc["human_alpha"].max()

    # Pools of published numbers per occupation. `detail_pools` (six measures
    # x detailed codes) is the pool of the any-measure check above;
    # `round_pools` adds the six 6-digit means, for the rounding test.
    detail_pools = [onet.loc[onet["soc"] == c, measures].to_numpy(float).ravel()
                    for c in m["soc"]]
    round_pools = [np.concatenate([p, soc.loc[c, measures].to_numpy(float)])
                   for p, c in zip(detail_pools, m["soc"])]
    null = shuffle_null(m["hard"].to_numpy(), detail_pools)
    p_null = float((null >= obs_any).mean())
    round_any = count_hits(m["hard"].to_numpy(), round_pools, 0.005)

    with open(OUT, "w") as f:
        w = f.write
        w("# Audit: hand-typed \"Eloundou alpha\" values vs. the published source\n\n")
        w("Generated by `code/data/exposure/audit_hardcoded.py` on data retrieved "
          "2026-10-10. Do not edit by hand; rerun the script.\n\n")
        w("## What was audited\n\n")
        w(f"`ELOUNDOU_SAMPLE` in `code/exposure_scores.py` as committed in "
          f"`{AUDITED_COMMIT}` (2026-06-14, \"Add exposure scores module (WS3)\"): "
          f"{len(audited)} occupations, each with a value labelled \"approximate "
          "Eloundou alpha score\". The values are read from git by the script, "
          "not retyped. No source was cited, no Eloundou data file was ever "
          "committed to the repository, and `ROADMAP.md` (line 74) recorded at the "
          "time that the module was still waiting for the full CSV.\n\n")
        w("Source compared against: `code/data/exposure/eloundou/occ_level.csv` "
          "from github.com/openai/GPTs-are-GPTs (SHA-256 "
          f"`{es.SOURCES['eloundou/occ_level.csv']['sha256']}`; see README.md).\n\n")
        w("## Method\n\n")
        w("- Each hard-coded 6-digit SOC code is matched to all O*NET-SOC 8-digit "
          "codes that start with it. When several exist, each is listed (↳ rows) "
          "and the verdict uses their unweighted mean, the aggregation rule of "
          "`exposure_scores.py`.\n")
        w("- *Closest real alpha* = the smaller of |hard-coded − human_rating_alpha| "
          "and |hard-coded − dv_rating_alpha| (dv = GPT-4 rating).\n")
        w(f"- Verdict: **matches within {TOL}** if that difference is ≤ {TOL}; "
          "**differs** otherwise; **no matching SOC code in source** if the code "
          "does not occur in the file. A 2010-SOC code with a 2018-SOC successor "
          "is shown for information under the unmatched row; it does not change "
          "the verdict.\n\n")
        w("## Table\n\n")
        w("| SOC | Title (hard-coded) | Source occupation | Hard-coded | "
          "human_rating_alpha | dv_rating_alpha | human_rating_beta | "
          "dv_rating_beta | abs diff vs closest alpha | Verdict |\n")
        w("|---|---|---|---:|---:|---:|---:|---:|---:|---|\n")
        w("\n".join(lines) + "\n\n")
        w("## Summary\n\n")
        w(f"- Entries audited: {len(res)}. Code found in source: {len(m)}; "
          f"no matching SOC code: {n_none}.\n")
        w(f"- Against the closest real alpha: **{n_match} match within {TOL}, "
          f"{n_diff} differ.**\n")
        w(f"- Absolute error vs. closest real alpha (n = {len(m)}): "
          f"max = {m['closest'].max():.3f}, mean = {m['closest'].mean():.3f}, "
          f"median = {m['closest'].median():.3f}. With a looser tolerance of "
          f"0.05, {int(within(m['closest'], 0.05).sum())} of {len(m)} would "
          "match.\n")
        w(f"- Detailed-code check: {int(m['det_hit'].sum())} of {len(m)} values are "
          f"within {TOL} of the alpha of at least one individual O*NET-SOC "
          "code (instead of the 6-digit mean).\n")
        w(f"- Same {len(m)} occupations: mean hard-coded value "
          f"{m['hard'].mean():.3f}; mean real human_rating_alpha "
          f"{m['human_alpha'].mean():.3f}; dv_rating_alpha "
          f"{m['gpt4_alpha'].mean():.3f}. (All {len(res)} hard-coded values: "
          f"mean {res['hard'].mean():.3f}.)\n")
        w(f"- {int((res['hard'] > max_h_alpha).sum())} hard-coded values exceed "
          f"{max_h_alpha:.3f}, the largest human_rating_alpha of any occupation "
          "in the whole file.\n\n")
        w("Fit of the hard-coded values to each published measure (n = "
          f"{len(m)}, 6-digit means):\n\n")
        w("| Measure | File column | Mean abs error | Max abs error | "
          f"Within {TOL} | Pearson r | Spearman ρ |\n|---|---|---:|---:|---:|---:|---:|\n")
        for c, col, mae, mx, k, pr, sr in fit:
            w(f"| {c} | {col} | {mae:.3f} | {mx:.3f} | {k} | {pr:.2f} | {sr:.2f} |\n")
        hits = m[within(m["any6"])]
        hit_cols = hits["any6_col"].value_counts()
        w("\nAny-measure check: if any of the six measures, for any detailed "
          f"code, may count as a match, {obs_any} of {len(m)} values fall within "
          f"{TOL} of some published number. Two reference points:\n\n"
          f"- Uniform random numbers in [0, 1] would do so for {exp_any:.1f} of "
          f"{len(m)} occupations in expectation (the published values cover that "
          f"much of [0, 1] at ±{TOL}).\n"
          f"- Shuffle null: the same {len(m)} hard-coded values assigned to the "
          f"occupations at random ({N_SHUFFLES:,} shuffles, seed {SEED}) give a "
          f"mean of {null.mean():.2f} hits (95th percentile "
          f"{np.percentile(null, 95):.0f}); P(null ≥ {obs_any}) = {p_null:.4f}. "
          "The near-hits are therefore occupation-specific, not an artefact of "
          "the values' overall distribution.\n\n"
          f"The {obs_any} hits are spread over {len(hit_cols)} different "
          "measures:\n\n")
        w("| SOC | Title (hard-coded) | Hard-coded | Nearest published value | "
          "Measure | O*NET-SOC | abs diff |\n|---|---|---:|---:|---|---|---:|\n")
        by_code = onet.set_index("onet_soc")
        for _, r in hits.iterrows():
            nearest = by_code.loc[r["any6_code"], r["any6_col"]]
            w(f"| {r['soc']} | {r['title']} | {r['hard']:.2f} | {nearest:.3f} | "
              f"{r['any6_col']} | {r['any6_code']} | {r['any6']:.3f} |\n")
        w("\n## Conclusion\n\n")
        best = min(fit, key=lambda t: t[2])
        # Values copied from one column and rounded to 2 decimals would lie
        # within 0.005 of that column (6-digit mean or some detailed code).
        rounding = {}
        for c in measures:
            k = 0
            for _, r in m.iterrows():
                vals = onet.loc[onet["soc"] == r["soc"], c].tolist() + [r[c]]
                k += any(within(abs(r["hard"] - v), 0.005) for v in vals)
            rounding[c] = k
        top = max(rounding, key=rounding.get)
        hi_r = max(fit, key=lambda t: t[5])
        w("**Verdict: the hard-coded values are unsourced and cannot be "
          "reproduced from the published data, by any single column or any mix "
          "of columns; they were also mislabelled as alpha.** How they were "
          "produced cannot be established from the record. The evidence below "
          "rules out copying; it does not distinguish invention from an "
          "informed approximation of several measures.\n\n")
        w("1. No published number, in any column or mix of columns, reproduces "
          "them. Values copied and rounded to two decimals would all lie within "
          "0.005 of their source. Single-column test: the most such agreements "
          f"any one column achieves is {rounding[top]} of {len(m)} ({top}). "
          "Mixed-column test: allowing each value to come from *any* of the six "
          "measures, at any detailed code or the 6-digit mean, the number "
          f"within 0.005 of a published number is {round_any} of {len(m)}. The "
          f"best-fitting column by mean error ({best[0]}) is off by "
          f"{best[2]:.3f} on average and by up to {best[3]:.3f}.\n")
        w(f"2. Under the label they carried (alpha), {n_match} of {len(m)} agree "
          f"within {TOL}; the mean error is {m['closest'].mean():.2f}. For the "
          f"same {len(m)} occupations, the hard-coded mean is "
          f"{m['hard'].mean():.3f}, against real alpha means of "
          f"{m['human_alpha'].mean():.3f} (human) and {m['gpt4_alpha'].mean():.3f} "
          f"(GPT-4). {int((res['hard'] > max_h_alpha).sum())} values exceed the "
          "largest human alpha of any occupation in the file. The values are "
          "not alpha.\n")
        w(f"3. The values are not random either. They rank occupations much as "
          f"the published beta/zeta measures do (Pearson r up to {hi_r[5]:.2f}, "
          f"{hi_r[0]}), and {obs_any} of {len(m)} land within {TOL} of *some* "
          f"published number for the same occupation, against a shuffle-null "
          f"mean of {null.mean():.2f} (P = {p_null:.4f}). So the near-hits are "
          f"occupation-specific. They are spread over {len(hit_cols)} different "
          f"measures, and point 1 shows that only {round_any} of {len(m)} is "
          "even consistent with a rounded copy. This fits an approximation "
          "informed by the published results. It does not identify a "
          "source.\n")
        w("4. Git history: the dict arrived in a single commit with no data file, "
          "the comment calls the values \"approximate\", and ROADMAP.md recorded "
          "that the source CSV was still awaited.\n\n")
        w("Where they were used: no code imports `exposure_scores`; the DiD, "
          "placebo and pipeline simulations draw synthetic exposures from "
          "`np.linspace(0.10, 0.92, N)` and never used these numbers, and no "
          "figure or report in `code/data/` contains them. The values are "
          "described as Eloundou alpha scores in `README.md` (line 24) and "
          "`ROADMAP.md` (lines 74 and 274); those descriptions need correcting. "
          "The module now loads the published file and contains none of the "
          "hand-typed numbers.\n")
    assert count_hits(m["hard"].to_numpy(), detail_pools, TOL) == obs_any
    print(f"wrote {OUT}")
    print(f"matched {n_match}, differ {n_diff}, no code {n_none}; "
          f"closest-alpha MAE {m['closest'].mean():.3f}, max {m['closest'].max():.3f}; "
          f"any-of-six hits {obs_any} vs uniform {exp_any:.1f}, "
          f"shuffle null mean {null.mean():.2f} (p={p_null:.4f}); "
          f"any-measure rounding hits {round_any}/{len(m)}")


if __name__ == "__main__":
    main()
