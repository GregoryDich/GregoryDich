"""
build_poc.py — Proof of concept: competing-narrative R0 / infection curves.

Default (works offline, in this sandbox):
    python build_poc.py                # --source simulate
Live data (where GDELT egress is allowed):
    python build_poc.py --source gdelt

Outputs:
    figures/fig1_infection_curves.png
    figures/fig2_branching_ratios.png
    figures/fig3_shock_baseline.png
    data/poc_summary.md
    data/weekly_series.csv

NOTE: simulate-mode numbers are SIMULATED — they validate the instrument,
they are NOT evidence. The same estimators consume real event streams.
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import hawkes
import growth
import simulate as sim

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
DAT = os.path.join(HERE, "data")
os.makedirs(FIG, exist_ok=True)
os.makedirs(DAT, exist_ok=True)


def weekly_counts(events, T):
    nweeks = int(np.ceil(T / 7)) + 1
    wk = (np.asarray(events) // 7).astype(int)
    return np.arange(nweeks), np.bincount(wk, minlength=nweeks)


def run_simulate(seed=42, bootstrap=100):
    print("=" * 64)
    print(" PROOF OF CONCEPT  —  SIMULATED DATA (instrument validation)")
    print("=" * 64)

    minus, plus, T, shocks, truth = sim.make_narratives(seed=seed)
    print(f" events: destruction(X-)={len(minus)}  creation(X+)={len(plus)}  T={T}d")

    # --- Naive Hawkes MLE ---
    fm, fp = hawkes.fit(minus, T), hawkes.fit(plus, T)
    rng = np.random.default_rng(seed)
    lom, him, _ = hawkes.bootstrap_ci(fm, T, B=bootstrap, rng=rng)
    lop, hip, _ = hawkes.bootstrap_ci(fp, T, B=bootstrap, rng=rng)

    # --- Shock-aware Hawkes MLE (WS5.1 de-biasing) ---
    print("\n  Fitting shock-aware model (time-varying baseline) ...")
    fsm = hawkes.fit_shock_aware(minus, T, sim.SHOCK_TIMES_MINUS)
    fsp = hawkes.fit_shock_aware(plus, T, sim.SHOCK_TIMES_PLUS)
    rng2 = np.random.default_rng(seed + 1)
    bootstrap_sa = max(bootstrap // 2, 30)
    losm, hism, _ = hawkes.bootstrap_ci_shock_aware(
        fsm, T, B=bootstrap_sa, rng=rng2)
    losp, hisp, _ = hawkes.bootstrap_ci_shock_aware(
        fsp, T, B=bootstrap_sa, rng=rng2)

    # --- weekly series + exponential-growth R0 ---
    wkm, cm = weekly_counts(minus, T)
    wkp, cp = weekly_counts(plus, T)
    r0g_m, _, _ = growth.exp_growth_r0(wkm, cm)
    r0g_p, _, _ = growth.exp_growth_r0(wkp, cp)

    # --- report ---
    print("\n  Hawkes branching ratio  n = alpha/beta  (analog of R0):")
    print(f"   X- destruction : naive n_hat = {fm['branching_ratio']:.3f}  "
          f"[90% CI {lom:.3f}, {him:.3f}]")
    print(f"   X+ creation    : naive n_hat = {fp['branching_ratio']:.3f}  "
          f"[90% CI {lop:.3f}, {hip:.3f}]")

    bias_m_naive = abs(fm["branching_ratio"] - truth["n_minus"]) / truth["n_minus"] * 100
    bias_p_naive = abs(fp["branching_ratio"] - truth["n_plus"]) / truth["n_plus"] * 100
    bias_m_sa = abs(fsm["branching_ratio"] - truth["n_minus"]) / truth["n_minus"] * 100
    bias_p_sa = abs(fsp["branching_ratio"] - truth["n_plus"]) / truth["n_plus"] * 100

    print("\n  Shock-aware (de-biased, WS5.1):")
    print(f"   X- destruction : n_hat = {fsm['branching_ratio']:.3f}  "
          f"[90% CI {losm:.3f}, {hism:.3f}]   "
          f"bias: {bias_m_naive:.0f}% -> {bias_m_sa:.0f}%   (true {truth['n_minus']:.2f})")
    print(f"   X+ creation    : n_hat = {fsp['branching_ratio']:.3f}  "
          f"[90% CI {losp:.3f}, {hisp:.3f}]   "
          f"bias: {bias_p_naive:.0f}% -> {bias_p_sa:.0f}%   (true {truth['n_plus']:.2f})")
    print(f"   gamma (shock decay): X- = {fsm['gamma']:.4f} "
          f"(half-life {np.log(2)/fsm['gamma']:.1f}d)  "
          f"X+ = {fsp['gamma']:.4f} "
          f"(half-life {np.log(2)/fsp['gamma']:.1f}d)")

    h6_naive = fm["branching_ratio"] > fp["branching_ratio"]
    h6_sa = fsm["branching_ratio"] > fsp["branching_ratio"]
    print(f"\n  H6 (negative more contagious): "
          f"naive={'SUPPORTED' if h6_naive else 'NOT SUPPORTED'}  "
          f"shock-aware={'SUPPORTED' if h6_sa else 'NOT SUPPORTED'}")
    print(f"  exp-growth R0 proxy:  X- = {r0g_m:.2f}   X+ = {r0g_p:.2f}")

    _fig1(wkm, cm, wkp, cp, shocks)
    _fig2(fm, fp, (lom, him), (lop, hip),
          fsm, fsp, (losm, hism), (losp, hisp), truth)
    _fig3(fsm, fsp, T)
    _write_summary(fm, fp, (lom, him), (lop, hip),
                   fsm, fsp, (losm, hism), (losp, hisp),
                   truth, r0g_m, r0g_p, h6_naive, h6_sa,
                   len(minus), len(plus), wkm, cm, cp)
    print(f"\n  figures -> {FIG}\n  summary -> {DAT}/poc_summary.md")


def _fig1(wkm, cm, wkp, cp, shocks):
    dm = [sim.week_to_date(w) for w in wkm]
    dp = [sim.week_to_date(w) for w in wkp]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.plot(dm, cm, color="#c0392b", lw=1.8,
            label="X-  destruction")
    ax.plot(dp, cp, color="#2e8b57", lw=1.8,
            label="X+  creation")
    for name, day in shocks.items():
        d = sim.week_to_date(day / 7)
        ax.axvline(d, color="#888", ls="--", lw=0.8, alpha=0.7)
        ax.text(d, ax.get_ylim()[1] * 0.96, name, rotation=90,
                va="top", ha="right", fontsize=7, color="#555")
    ax.set_title("Competing AI narrative infection curves  "
                 "(SIMULATED)", fontsize=11)
    ax.set_ylabel("Weekly narrative intensity (mentions)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig1_infection_curves.png"), dpi=130)
    plt.close(fig)


def _fig2(fm, fp, cim, cip, fsm, fsp, csm, csp, truth):
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    x = np.array([0.0, 2.0])
    w = 0.35

    nv = [fm["branching_ratio"], fp["branching_ratio"]]
    nlo = [nv[0] - cim[0], nv[1] - cip[0]]
    nhi = [cim[1] - nv[0], cip[1] - nv[1]]
    ax.bar(x - w / 2, nv, w, yerr=[nlo, nhi], capsize=6,
           color=["#e8a0a0", "#a0d0a0"], edgecolor="black", lw=0.6,
           label="Naive MLE (biased)")

    sv = [fsm["branching_ratio"], fsp["branching_ratio"]]
    slo = [sv[0] - csm[0], sv[1] - csp[0]]
    shi = [csm[1] - sv[0], csp[1] - sv[1]]
    ax.bar(x + w / 2, sv, w, yerr=[slo, shi], capsize=6,
           color=["#c0392b", "#2e8b57"], edgecolor="black", lw=0.6,
           label="Shock-aware MLE (WS5.1)")

    tv = [truth["n_minus"], truth["n_plus"]]
    for i in range(2):
        ax.plot([x[i] - 0.5, x[i] + 0.5], [tv[i], tv[i]],
                "k--", lw=1.2, alpha=0.7)
        ax.text(x[i] + 0.55, tv[i], f"true={tv[i]:.2f}",
                fontsize=8, va="center")
        ax.text(x[i] - w / 2, nv[i] + max(nhi[i], 0.02) + 0.02,
                f"n={nv[i]:.2f}", ha="center", fontsize=8, color="#888")
        ax.text(x[i] + w / 2, sv[i] + max(shi[i], 0.02) + 0.02,
                f"n={sv[i]:.2f}", ha="center", fontsize=8, fontweight="bold")

    ax.axhline(1.0, color="black", ls=":", lw=0.8)
    ax.text(2.6, 1.01, "n = 1 (criticality)", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(["X-\ndestruction", "X+\ncreation"])
    ax.set_ylim(0, 1.25)
    ax.set_ylabel("Branching ratio  n  (R0 analog)")
    ax.set_title("De-biasing: naive vs shock-aware Hawkes MLE\n"
                 "(SIMULATED — instrument validation)", fontsize=10)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig2_branching_ratios.png"), dpi=130)
    plt.close(fig)


def _fig3(fsm, fsp, T):
    days = np.linspace(0, T, 2000)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    for ax, fitted, color, label in [
        (ax1, fsm, "#c0392b", "X- destruction"),
        (ax2, fsp, "#2e8b57", "X+ creation"),
    ]:
        base = hawkes.baseline_at(days, fitted["mu0"], fitted["gamma"],
                                  fitted["shock_times"],
                                  fitted["shock_deltas"])
        dates = [sim.week_to_date(d / 7) for d in days]
        ax.fill_between(dates, fitted["mu0"], base, color=color, alpha=0.3)
        ax.plot(dates, base, color=color, lw=1.5, label=label)
        ax.axhline(fitted["mu0"], color="gray", ls=":", lw=0.8,
                   label=f"mu0 = {fitted['mu0']:.4f}")
        hl = np.log(2) / fitted["gamma"]
        ax.text(0.98, 0.92,
                f"gamma = {fitted['gamma']:.4f}  (t1/2 = {hl:.0f} d)",
                transform=ax.transAxes, ha="right", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8))
        ax.set_ylabel("mu(t)  baseline intensity")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(alpha=0.25)

    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("Estimated shock-aware baseline mu(t)\n"
                 "(SIMULATED — exogenous shock absorption)",
                 fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig3_shock_baseline.png"), dpi=130)
    plt.close(fig)


def _write_summary(fm, fp, cim, cip, fsm, fsp, csm, csp,
                   truth, r0m, r0p, h6_naive, h6_sa,
                   nm, npl, wk, cm, cp):
    np.savetxt(os.path.join(DAT, "weekly_series.csv"),
               np.column_stack([wk, cm[:len(wk)], cp[:len(wk)]]),
               delimiter=",", header="week,destruction,creation", comments="")
    with open(os.path.join(DAT, "poc_summary.md"), "w") as f:
        f.write("# Proof of Concept Results (SIMULATED)\n\n")
        f.write("> Numbers are simulated to validate the instrument, "
                "not evidence.\n\n")
        f.write(f"- Events: X- = {nm}, X+ = {npl}\n\n")
        f.write("## Naive Hawkes MLE\n")
        f.write(f"- n_hat(X-) = {fm['branching_ratio']:.3f} "
                f"[90% CI {cim[0]:.3f}, {cim[1]:.3f}], "
                f"true {truth['n_minus']:.2f}\n")
        f.write(f"- n_hat(X+) = {fp['branching_ratio']:.3f} "
                f"[90% CI {cip[0]:.3f}, {cip[1]:.3f}], "
                f"true {truth['n_plus']:.2f}\n")
        f.write(f"- H6: {'SUPPORTED' if h6_naive else 'not supported'}\n\n")
        f.write("## Shock-aware Hawkes MLE (de-biased, WS5.1)\n")
        f.write(f"- n_hat(X-) = {fsm['branching_ratio']:.3f} "
                f"[90% CI {csm[0]:.3f}, {csm[1]:.3f}], "
                f"true {truth['n_minus']:.2f}\n")
        f.write(f"- n_hat(X+) = {fsp['branching_ratio']:.3f} "
                f"[90% CI {csp[0]:.3f}, {csp[1]:.3f}], "
                f"true {truth['n_plus']:.2f}\n")
        f.write(f"- gamma decay: X- = {fsm['gamma']:.4f} "
                f"(t1/2 = {np.log(2)/fsm['gamma']:.1f}d), "
                f"X+ = {fsp['gamma']:.4f} "
                f"(t1/2 = {np.log(2)/fsp['gamma']:.1f}d)\n")
        f.write(f"- H6: {'SUPPORTED' if h6_sa else 'not supported'}\n\n")
        bm_n = abs(fm["branching_ratio"] - truth["n_minus"]) \
            / truth["n_minus"] * 100
        bp_n = abs(fp["branching_ratio"] - truth["n_plus"]) \
            / truth["n_plus"] * 100
        bm_s = abs(fsm["branching_ratio"] - truth["n_minus"]) \
            / truth["n_minus"] * 100
        bp_s = abs(fsp["branching_ratio"] - truth["n_plus"]) \
            / truth["n_plus"] * 100
        f.write("## Bias reduction\n")
        f.write(f"- X-: {bm_n:.0f}% -> {bm_s:.0f}%\n")
        f.write(f"- X+: {bp_n:.0f}% -> {bp_s:.0f}%\n\n")
        f.write("## Exp-growth R0 proxy\n")
        f.write(f"- X- = {r0m:.2f}, X+ = {r0p:.2f}\n")


def run_gdelt():
    import gdelt_client
    print("Fetching live GDELT competing-narrative timelines ...")
    tl = gdelt_client.fetch_competing()
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for key, color, lab in [("minus", "#c0392b", "X- destruction"),
                            ("plus", "#2e8b57", "X+ creation")]:
        dates, inten = tl[key]
        x = [matplotlib.dates.datestr2num(d[:8]) for d in dates]
        ax.plot_date(x, inten, "-", color=color, lw=1.6, label=lab)
        wk = np.arange(len(inten))
        r0, _, _ = growth.exp_growth_r0(wk, inten)
        print(f"  {lab}: exp-growth R0 proxy = {r0:.2f}")
    ax.set_title("GDELT live narrative intensity (REAL DATA)")
    ax.legend(); ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig1_gdelt_live.png"), dpi=130)
    print(f"  figure -> {FIG}/fig1_gdelt_live.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["simulate", "gdelt"],
                    default="simulate")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--bootstrap", type=int, default=100)
    args = ap.parse_args()
    if args.source == "gdelt":
        run_gdelt()
    else:
        run_simulate(seed=args.seed, bootstrap=args.bootstrap)
