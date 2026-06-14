"""
run_all.py — Master orchestration: runs the full analysis pipeline.

Executes all validation modules in sequence and produces a unified report.
This is the "code against simulated data" deliverable — proves every piece
of the pre-registered analysis works before real data arrives.

Usage:
    python run_all.py [--bootstrap N]  (default N=50)

Outputs:
    figures/fig1-fig6 (all regenerated)
    data/full_pipeline_report.md
"""
import os
import sys
import time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

DAT = os.path.join(HERE, "data")
os.makedirs(DAT, exist_ok=True)


def banner(text):
    print(f"\n{'='*64}")
    print(f"  {text}")
    print(f"{'='*64}\n")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    t0 = time.time()
    results = {}

    # --- Module 1: Hawkes R0 estimation (WS5) ---
    banner("MODULE 1: Hawkes R0 — naive + shock-aware (WS5/5.1)")
    import hawkes
    import simulate as sim

    minus, plus, T, shocks, truth = sim.make_narratives(seed=args.seed)

    fm = hawkes.fit(minus, T)
    fp = hawkes.fit(plus, T)
    fsm = hawkes.fit_shock_aware(minus, T, sim.SHOCK_TIMES_MINUS)
    fsp = hawkes.fit_shock_aware(plus, T, sim.SHOCK_TIMES_PLUS)

    results["hawkes"] = {
        "naive_n_minus": fm["branching_ratio"],
        "naive_n_plus": fp["branching_ratio"],
        "sa_n_minus": fsm["branching_ratio"],
        "sa_n_plus": fsp["branching_ratio"],
        "true_n_minus": truth["n_minus"],
        "true_n_plus": truth["n_plus"],
        "h6_supported": fsm["branching_ratio"] > fsp["branching_ratio"],
    }
    print(f"  Shock-aware: n(X-)={fsm['branching_ratio']:.3f}, "
          f"n(X+)={fsp['branching_ratio']:.3f}")
    print(f"  H6: {'SUPPORTED' if results['hawkes']['h6_supported'] else 'NOT SUPPORTED'}")

    # --- Module 2: DiD identification (WS4) ---
    banner("MODULE 2: DiD — TWFE + event study (WS4)")
    import did_simulate
    import pandas as pd
    import statsmodels.api as sm

    df, chatgpt_week, n_weeks = did_simulate.generate_panel(seed=args.seed)
    beta_hat, se, ci, _ = did_simulate.run_twfe(df)
    bin_centers, coefs, ses, _ = did_simulate.run_event_study(
        df, chatgpt_week, n_weeks, bin_size=8)
    p_pre = did_simulate.pretrend_test(bin_centers, coefs, ses)

    results["did"] = {
        "beta_hat": beta_hat,
        "se": se,
        "ci": ci,
        "true_beta": did_simulate.TRUE_BETA,
        "bias_pct": abs(beta_hat - did_simulate.TRUE_BETA) / did_simulate.TRUE_BETA * 100,
        "in_ci": ci[0] <= did_simulate.TRUE_BETA <= ci[1],
        "pretrend_p": p_pre,
        "pretrends_flat": p_pre > 0.10,
    }
    print(f"  TWFE: beta={beta_hat:.4f} (true={did_simulate.TRUE_BETA}), "
          f"bias={results['did']['bias_pct']:.1f}%")
    print(f"  Pre-trends: p={p_pre:.3f} "
          f"({'flat' if p_pre > 0.10 else 'CONCERN'})")

    # --- Module 3: LP-IRF temporal ordering (A.4) ---
    banner("MODULE 3: LP-IRF temporal ordering (A.4, core H1)")
    import local_projection as lp

    df_ts = lp.generate_time_series(seed=args.seed)
    betas_beh, ses_beh, _, _ = lp.local_projection(
        df_ts, "narrative", "behavior", lp.HORIZONS)
    betas_prod, ses_prod, _, _ = lp.local_projection(
        df_ts, "narrative", "productivity", lp.HORIZONS)

    beh_peak = lp.HORIZONS[np.nanargmax(np.abs(betas_beh))]
    prod_peak = lp.HORIZONS[np.nanargmax(np.abs(betas_prod))]

    results["lp_irf"] = {
        "behavior_peak_h": beh_peak,
        "productivity_peak_h": prod_peak,
        "h1_supported": beh_peak < prod_peak,
        "behavior_coef_at_peak": float(betas_beh[lp.HORIZONS.index(beh_peak)]),
        "productivity_coef_at_peak": float(betas_prod[lp.HORIZONS.index(prod_peak)]),
    }
    print(f"  Behavior peaks at h={beh_peak}wk, productivity at h={prod_peak}wk")
    print(f"  H1: {'SUPPORTED' if beh_peak < prod_peak else 'NOT SUPPORTED'}")

    # --- Module 4: Placebo test (A.6) ---
    banner("MODULE 4: Placebo test (A.6 robustness)")
    import placebo_test as pt

    df_real, _ = pt.generate_panel_with_shock(chatgpt_week)
    df_real["treatment"] = df_real["exposure"] * df_real["narrative"]
    beta_real, se_real = pt.run_did_narrative(df_real)

    rng = np.random.default_rng(args.seed + 100)
    placebo_weeks = rng.integers(12, chatgpt_week - 4, size=pt.N_PLACEBO)
    placebo_weeks = np.sort(np.unique(placebo_weeks))
    placebo_betas = []
    for pw in placebo_weeks:
        df_p, _ = pt.generate_panel_with_shock(chatgpt_week)
        df_pre = df_p[df_p["week"] < chatgpt_week].copy()
        df_pre["post_placebo"] = (df_pre["week"] >= pw).astype(float)
        b, _ = pt.run_did_placebo(df_pre)
        placebo_betas.append(b)
    placebo_betas = np.array(placebo_betas)
    p_rand = np.mean(np.abs(placebo_betas) >= np.abs(beta_real))

    results["placebo"] = {
        "real_beta": beta_real,
        "placebo_max": float(np.abs(placebo_betas).max()),
        "p_randomization": p_rand,
        "passed": p_rand < 0.10,
    }
    print(f"  Real beta={beta_real:.4f}, max placebo={np.abs(placebo_betas).max():.4f}")
    print(f"  Randomization p={p_rand:.3f}: "
          f"{'PASSED' if p_rand < 0.10 else 'CONCERN'}")

    # --- Summary ---
    elapsed = time.time() - t0
    banner("PIPELINE SUMMARY")

    all_pass = all([
        results["hawkes"]["h6_supported"],
        results["did"]["in_ci"],
        results["did"]["pretrends_flat"],
        results["lp_irf"]["h1_supported"],
        results["placebo"]["passed"],
    ])

    checks = [
        ("H6 (negative more contagious)", results["hawkes"]["h6_supported"]),
        ("TWFE recovers true beta", results["did"]["in_ci"]),
        ("Pre-trends flat", results["did"]["pretrends_flat"]),
        ("H1 temporal ordering", results["lp_irf"]["h1_supported"]),
        ("Placebo test", results["placebo"]["passed"]),
    ]

    for name, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\n  Overall: {'ALL CHECKS PASS' if all_pass else 'SOME CHECKS FAILED'}")
    print(f"  Elapsed: {elapsed:.1f}s")

    _write_report(results, checks, elapsed)
    print(f"\n  Full report -> {DAT}/full_pipeline_report.md")


def _write_report(results, checks, elapsed):
    with open(os.path.join(DAT, "full_pipeline_report.md"), "w") as f:
        f.write("# Full Pipeline Validation Report (SIMULATED)\n\n")
        f.write("> All numbers are from simulated data. "
                "This validates the instrument, not the hypothesis.\n\n")

        f.write("## Validation Checklist\n\n")
        for name, passed in checks:
            mark = "PASS" if passed else "FAIL"
            f.write(f"- [{mark}] {name}\n")

        f.write("\n## Module 1: Hawkes R0 (WS5/5.1)\n")
        h = results["hawkes"]
        f.write(f"- Shock-aware n(X-) = {h['sa_n_minus']:.3f} "
                f"(true {h['true_n_minus']:.2f})\n")
        f.write(f"- Shock-aware n(X+) = {h['sa_n_plus']:.3f} "
                f"(true {h['true_n_plus']:.2f})\n")
        f.write(f"- H6: {'SUPPORTED' if h['h6_supported'] else 'NOT SUPPORTED'}\n")

        f.write("\n## Module 2: DiD (WS4)\n")
        d = results["did"]
        f.write(f"- beta_hat = {d['beta_hat']:.4f} "
                f"(true {d['true_beta']}, bias {d['bias_pct']:.1f}%)\n")
        f.write(f"- 95% CI: [{d['ci'][0]:.4f}, {d['ci'][1]:.4f}], "
                f"true in CI: {d['in_ci']}\n")
        f.write(f"- Pre-trend p = {d['pretrend_p']:.3f}\n")

        f.write("\n## Module 3: LP-IRF (A.4)\n")
        lp = results["lp_irf"]
        f.write(f"- Behavior peaks at h = {lp['behavior_peak_h']} weeks "
                f"(coef = {lp['behavior_coef_at_peak']:.3f})\n")
        f.write(f"- Productivity peaks at h = {lp['productivity_peak_h']} weeks "
                f"(coef = {lp['productivity_coef_at_peak']:.3f})\n")
        f.write(f"- H1: {'SUPPORTED' if lp['h1_supported'] else 'NOT SUPPORTED'}\n")

        f.write("\n## Module 4: Placebo (A.6)\n")
        p = results["placebo"]
        f.write(f"- Real beta = {p['real_beta']:.4f}\n")
        f.write(f"- Max |placebo| = {p['placebo_max']:.4f}\n")
        f.write(f"- Randomization p = {p['p_randomization']:.3f}\n")

        f.write(f"\n---\nElapsed: {elapsed:.1f}s\n")


if __name__ == "__main__":
    main()
