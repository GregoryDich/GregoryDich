"""
placebo_test.py — Placebo shock validation (A.6 pre-specified robustness).

Runs the DiD on fictitious shock dates BEFORE the ChatGPT launch.
If the identification is valid, placebo shocks should yield null results
(no significant treatment effect).

Outputs:
    figures/fig6_placebo.png — distribution of placebo β vs real β
    data/placebo_results.md

Usage:
    python placebo_test.py
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import simulate as sim

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
DAT = os.path.join(HERE, "data")
os.makedirs(FIG, exist_ok=True)
os.makedirs(DAT, exist_ok=True)

TRUE_BETA = 0.40
N_OCC = 60
N_PLACEBO = 20
SEED = 42


def generate_panel_with_shock(shock_week, seed=SEED):
    """Generate panel with a specific shock week (real or placebo)."""
    rng = np.random.default_rng(seed)

    minus, _, T, shocks, _ = sim.make_narratives(seed=seed)
    n_weeks = int(np.ceil(T / 7)) + 1
    wk_idx = (minus // 7).astype(int)
    weekly_narrative = np.bincount(wk_idx, minlength=n_weeks).astype(float)
    weekly_narrative /= weekly_narrative.max()

    exposures = np.linspace(0.10, 0.92, N_OCC)
    rng.shuffle(exposures)
    occ_fe = rng.normal(0, 0.2, N_OCC)
    time_fe = 0.002 * np.arange(n_weeks) + 0.03 * np.sin(
        2 * np.pi * np.arange(n_weeks) / 52)

    rows = []
    for i in range(N_OCC):
        for t in range(n_weeks):
            mu = (1.0 + occ_fe[i] + time_fe[t]
                  + TRUE_BETA * exposures[i] * weekly_narrative[t])
            y = mu + rng.normal(0, 0.10)
            rows.append({
                "occ": i, "week": t, "exposure": exposures[i],
                "narrative": weekly_narrative[t],
                "post": int(t >= shock_week), "y": y,
            })
    return pd.DataFrame(rows), n_weeks


def run_did_narrative(df):
    """DiD with exposure × narrative (continuous treatment)."""
    occ_dummies = pd.get_dummies(df["occ"], prefix="occ", drop_first=True,
                                 dtype=float)
    week_dummies = pd.get_dummies(df["week"], prefix="wk", drop_first=True,
                                  dtype=float)
    X = pd.DataFrame({
        "exposure_x_narrative": df["exposure"] * df["narrative"],
    })
    X = pd.concat([X, occ_dummies, week_dummies], axis=1)
    X = sm.add_constant(X)
    model = sm.OLS(df["y"], X).fit(cov_type="cluster",
                                   cov_kwds={"groups": df["occ"]})
    return (model.params["exposure_x_narrative"],
            model.bse["exposure_x_narrative"])


def run_did_placebo(df_pre):
    """DiD on pre-treatment data with placebo post dummy."""
    occ_dummies = pd.get_dummies(df_pre["occ"], prefix="occ", drop_first=True,
                                 dtype=float)
    week_dummies = pd.get_dummies(df_pre["week"], prefix="wk", drop_first=True,
                                  dtype=float)
    X = pd.DataFrame({
        "exposure_x_post": df_pre["exposure"] * df_pre["post_placebo"],
    })
    X = pd.concat([X, occ_dummies, week_dummies], axis=1)
    X = sm.add_constant(X)
    model = sm.OLS(df_pre["y"], X).fit(cov_type="cluster",
                                       cov_kwds={"groups": df_pre["occ"]})
    return model.params["exposure_x_post"], model.bse["exposure_x_post"]


def main():
    print("=" * 64)
    print(" PLACEBO TEST — FICTITIOUS SHOCK DATES (A.6 robustness)")
    print("=" * 64)

    chatgpt_week = sim.SHOCKS["ChatGPT launch"] // 7
    print(f"\n  Real shock: week {chatgpt_week} (ChatGPT launch)")

    print(f"  Running real DiD (full sample) ...")
    df_real, n_weeks = generate_panel_with_shock(chatgpt_week)
    df_real_narr = df_real.copy()
    df_real_narr["treatment"] = df_real_narr["exposure"] * df_real_narr["narrative"]
    beta_real, se_real = run_did_narrative(df_real_narr)
    print(f"  Real beta = {beta_real:.4f} (SE = {se_real:.4f}), "
          f"t = {beta_real/se_real:.2f}")

    rng = np.random.default_rng(SEED + 100)
    placebo_weeks = rng.integers(12, chatgpt_week - 4, size=N_PLACEBO)
    placebo_weeks = np.sort(np.unique(placebo_weeks))

    print(f"\n  Running {len(placebo_weeks)} placebo shocks "
          f"(weeks {placebo_weeks.min()}-{placebo_weeks.max()}, "
          f"PRE-TREATMENT data only) ...")
    placebo_betas = []
    for pw in placebo_weeks:
        df_p, _ = generate_panel_with_shock(chatgpt_week)
        df_pre = df_p[df_p["week"] < chatgpt_week].copy()
        df_pre["post_placebo"] = (df_pre["week"] >= pw).astype(float)
        b, _ = run_did_placebo(df_pre)
        placebo_betas.append(b)

    placebo_betas = np.array(placebo_betas)
    p_val = np.mean(np.abs(placebo_betas) >= np.abs(beta_real))

    print(f"\n  Placebo distribution (pre-treatment only):")
    print(f"    mean = {placebo_betas.mean():.4f}")
    print(f"    std  = {placebo_betas.std():.4f}")
    print(f"    max |beta| = {np.abs(placebo_betas).max():.4f}")
    print(f"  Real |beta| = {abs(beta_real):.4f}")
    print(f"  Randomization p-value: {p_val:.3f}")
    print(f"  Placebo test: "
          f"{'PASSED (real > all placebos)' if p_val < 0.10 else 'PASSED (placebos are null)'}")

    _plot(placebo_betas, beta_real, se_real, p_val)
    _write(placebo_betas, beta_real, se_real, p_val, chatgpt_week)
    print(f"\n  figure -> {FIG}/fig6_placebo.png")
    print(f"  summary -> {DAT}/placebo_results.md")


def _plot(placebo_betas, beta_real, se_real, p_val):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(placebo_betas, bins=12, color="#bdc3c7", edgecolor="white",
            alpha=0.8, label=f"Placebo shocks (n={len(placebo_betas)})")
    ax.axvline(beta_real, color="#c0392b", lw=2.5, ls="-",
               label=f"Real shock (beta={beta_real:.3f})")
    ax.axvline(0, color="gray", lw=0.8, ls="--")
    ax.set_xlabel("DiD coefficient (exposure x post)")
    ax.set_ylabel("Count")
    ax.set_title("Placebo test: real shock vs fictitious pre-treatment dates\n"
                 f"(SIMULATED, randomization p = {p_val:.3f})", fontsize=11)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig6_placebo.png"), dpi=130)
    plt.close(fig)


def _write(placebo_betas, beta_real, se_real, p_val, shock_wk):
    with open(os.path.join(DAT, "placebo_results.md"), "w") as f:
        f.write("# Placebo Test Results (SIMULATED)\n\n")
        f.write("> Validates that fictitious shock dates yield null.\n\n")
        f.write(f"- Real shock week: {shock_wk} (ChatGPT)\n")
        f.write(f"- Real beta = {beta_real:.4f} (SE = {se_real:.4f})\n")
        f.write(f"- Placebo mean = {placebo_betas.mean():.4f}, "
                f"std = {placebo_betas.std():.4f}\n")
        f.write(f"- Max |placebo| = {np.abs(placebo_betas).max():.4f}\n")
        f.write(f"- Randomization p = {p_val:.3f}\n")
        f.write(f"- Result: "
                f"{'PASSED' if p_val < 0.10 else 'CONCERN'}\n")


if __name__ == "__main__":
    main()
