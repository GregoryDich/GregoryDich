"""
local_projection.py — Jordà (2005) local-projection impulse-response functions.

Tests the temporal ordering claim (H1): narrative → behavior → productivity.
Pre-specified lags: 4, 8, 12, 16 weeks. All lags reported — no selection.

Design:
    At each horizon h, estimate:
        Y_{t+h} = α + β_h · Shock_t + Γ · Controls_t + ε_{t+h}

    If narrative causes behavior (H1): β_h > 0 for behavior at h = 4–8 weeks,
    while β_h ≈ 0 for productivity at h < 12 weeks.

Usage:
    python local_projection.py
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import simulate as sim

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
DAT = os.path.join(HERE, "data")
os.makedirs(FIG, exist_ok=True)
os.makedirs(DAT, exist_ok=True)

HORIZONS = [0, 2, 4, 6, 8, 10, 12, 14, 16, 20, 24]
SEED = 42


def generate_time_series(seed=SEED):
    """Generate simulated time series: narrative → behavior → productivity.

    DGP (true temporal ordering):
        Narrative_t = Hawkes simulation (exogenous)
        Behavior_t  = 0.3 * Narrative_{t-4} + noise  (lags 4 weeks)
        Productivity_t = 0.2 * Narrative_{t-12} + noise (lags 12 weeks)

    H1 predicts: behavior responds to narrative BEFORE productivity does.
    """
    rng = np.random.default_rng(seed)

    minus, _, T, shocks, _ = sim.make_narratives(seed=seed)
    n_weeks = int(np.ceil(T / 7)) + 1
    wk_idx = (minus // 7).astype(int)
    narrative = np.bincount(wk_idx, minlength=n_weeks).astype(float)
    narrative = (narrative - narrative.mean()) / (narrative.std() + 1e-8)

    behavior = np.zeros(n_weeks)
    productivity = np.zeros(n_weeks)

    for t in range(n_weeks):
        if t >= 4:
            behavior[t] = 0.30 * narrative[t - 4]
        if t >= 12:
            productivity[t] = 0.20 * narrative[t - 12]
        behavior[t] += rng.normal(0, 0.15)
        productivity[t] += rng.normal(0, 0.15)

    df = pd.DataFrame({
        "week": np.arange(n_weeks),
        "narrative": narrative,
        "behavior": behavior,
        "productivity": productivity,
    })
    return df


def local_projection(df, shock_col, response_col, horizons=HORIZONS,
                     controls=None, n_lags_control=4):
    """Estimate LP-IRF: response to a unit shock at each horizon h.

    Returns arrays of (betas, ses, ci_lo, ci_hi) for each horizon.
    """
    betas, ses = [], []
    T = len(df)
    shock = df[shock_col].values
    resp = df[response_col].values

    for h in horizons:
        t_start = n_lags_control
        t_end = T - h
        if t_end <= t_start + 10:
            betas.append(np.nan)
            ses.append(np.nan)
            continue

        y_h = resp[t_start + h:t_end + h]
        x_shock = shock[t_start:t_end]

        X_data = {"shock": x_shock}
        for lag in range(1, n_lags_control + 1):
            X_data[f"y_lag{lag}"] = resp[t_start - lag:t_end - lag]
            X_data[f"s_lag{lag}"] = shock[t_start - lag:t_end - lag]

        X = pd.DataFrame(X_data)
        X = sm.add_constant(X)

        model = sm.OLS(y_h, X).fit(cov_type="HAC",
                                   cov_kwds={"maxlags": max(h, 4)})
        betas.append(model.params["shock"])
        ses.append(model.bse["shock"])

    betas = np.array(betas, dtype=float)
    ses = np.array(ses, dtype=float)
    ci_lo = betas - 1.645 * ses
    ci_hi = betas + 1.645 * ses
    return betas, ses, ci_lo, ci_hi


def plot_irf(horizons, betas_beh, ses_beh, betas_prod, ses_prod):
    """Plot LP-IRF: behavior vs productivity response to narrative shock."""
    fig, ax = plt.subplots(figsize=(10, 5.5))

    h = np.array(horizons)

    ax.fill_between(h, betas_beh - 1.645 * ses_beh,
                    betas_beh + 1.645 * ses_beh,
                    alpha=0.15, color="#2c3e50")
    ax.plot(h, betas_beh, "o-", color="#2c3e50", lw=2,
            markersize=5, label="Behavior (reskilling)")

    ax.fill_between(h, betas_prod - 1.645 * ses_prod,
                    betas_prod + 1.645 * ses_prod,
                    alpha=0.15, color="#c0392b")
    ax.plot(h, betas_prod, "s--", color="#c0392b", lw=2,
            markersize=5, label="Productivity")

    ax.axhline(0, color="gray", ls="-", lw=0.8)
    ax.axvline(4, color="#2c3e50", ls=":", lw=1, alpha=0.5)
    ax.axvline(12, color="#c0392b", ls=":", lw=1, alpha=0.5)
    ax.text(4.3, ax.get_ylim()[1] * 0.85 if ax.get_ylim()[1] > 0 else 0.2,
            "behavior\nresponds\n(4 wk)", fontsize=7, color="#2c3e50")
    ax.text(12.3, ax.get_ylim()[1] * 0.85 if ax.get_ylim()[1] > 0 else 0.2,
            "productivity\nresponds\n(12 wk)", fontsize=7, color="#c0392b")

    ax.set_xlabel("Horizon h (weeks after narrative shock)")
    ax.set_ylabel("Response (LP-IRF coefficient)")
    ax.set_title("Local-projection IRF: Narrative → Behavior → Productivity\n"
                 "(SIMULATED — validates H1 temporal ordering)", fontsize=11)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig5_lp_irf.png"), dpi=130)
    plt.close(fig)


def main():
    print("=" * 64)
    print(" LOCAL-PROJECTION IRF — TEMPORAL ORDERING (H1 core test)")
    print("=" * 64)

    print("\n  DGP: narrative → behavior (lag 4wk) → productivity (lag 12wk)")
    df = generate_time_series()
    print(f"  Time series: {len(df)} weeks")

    print("\n  Estimating LP-IRF for behavior ...")
    betas_beh, ses_beh, _, _ = local_projection(
        df, "narrative", "behavior", HORIZONS)

    print("  Estimating LP-IRF for productivity ...")
    betas_prod, ses_prod, _, _ = local_projection(
        df, "narrative", "productivity", HORIZONS)

    print("\n  Results (90% CI):")
    print(f"  {'Horizon':>8} {'Behavior':>12} {'Productivity':>14}")
    print(f"  {'':>8} {'β (SE)':>12} {'β (SE)':>14}")
    for i, h in enumerate(HORIZONS):
        b_str = f"{betas_beh[i]:.3f} ({ses_beh[i]:.3f})"
        p_str = f"{betas_prod[i]:.3f} ({ses_prod[i]:.3f})"
        marker = ""
        if not np.isnan(betas_beh[i]) and abs(betas_beh[i]) > 1.645 * ses_beh[i]:
            marker += " *"
        print(f"  h={h:>3}wk  {b_str:>16}  {p_str:>16}{marker}")

    beh_peak = HORIZONS[np.nanargmax(np.abs(betas_beh))]
    prod_peak = HORIZONS[np.nanargmax(np.abs(betas_prod))]
    h1_supported = beh_peak < prod_peak
    print(f"\n  Behavior peaks at h={beh_peak}wk, productivity at h={prod_peak}wk")
    print(f"  H1 (narrative → behavior BEFORE productivity): "
          f"{'SUPPORTED' if h1_supported else 'NOT SUPPORTED'}")

    plot_irf(np.array(HORIZONS), betas_beh, ses_beh, betas_prod, ses_prod)
    print(f"\n  figure -> {FIG}/fig5_lp_irf.png")

    with open(os.path.join(DAT, "lp_irf_results.md"), "w") as f:
        f.write("# Local-Projection IRF Results (SIMULATED)\n\n")
        f.write("> Validates temporal ordering test for H1.\n\n")
        f.write(f"- DGP: behavior lags narrative by 4 wk; "
                f"productivity lags by 12 wk\n")
        f.write(f"- Behavior peak response at h = {beh_peak} weeks\n")
        f.write(f"- Productivity peak response at h = {prod_peak} weeks\n")
        f.write(f"- H1: {'SUPPORTED' if h1_supported else 'NOT SUPPORTED'}\n")

    print(f"  summary -> {DAT}/lp_irf_results.md")


if __name__ == "__main__":
    main()
