"""
build_poc.py — Proof of concept: competing-narrative R0 / infection curves.

Default (works offline, in this sandbox):
    python build_poc.py                # --source simulate
Live data (where GDELT egress is allowed):
    python build_poc.py --source gdelt

Outputs:
    figures/fig1_infection_curves.png
    figures/fig2_branching_ratios.png
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

    # --- Hawkes MLE: branching ratio n (= R0 analog) ---
    fm, fp = hawkes.fit(minus, T), hawkes.fit(plus, T)
    rng = np.random.default_rng(seed)
    lom, him, _ = hawkes.bootstrap_ci(fm, T, B=bootstrap, rng=rng)
    lop, hip, _ = hawkes.bootstrap_ci(fp, T, B=bootstrap, rng=rng)

    # --- weekly series + exponential-growth R0 (exposition) ---
    wkm, cm = weekly_counts(minus, T)
    wkp, cp = weekly_counts(plus, T)
    r0g_m, _, _ = growth.exp_growth_r0(wkm, cm)
    r0g_p, _, _ = growth.exp_growth_r0(wkp, cp)

    # --- report ---
    print("\n  Hawkes branching ratio  n = alpha/beta  (analog of R0):")
    print(f"   X- destruction : n_hat = {fm['branching_ratio']:.3f}  "
          f"[90% CI {lom:.3f}, {him:.3f}]   (true {truth['n_minus']:.2f})")
    print(f"   X+ creation    : n_hat = {fp['branching_ratio']:.3f}  "
          f"[90% CI {lop:.3f}, {hip:.3f}]   (true {truth['n_plus']:.2f})")
    h6 = fm["branching_ratio"] > fp["branching_ratio"]
    print(f"\n  H6 (negative more contagious than positive): "
          f"{'SUPPORTED' if h6 else 'not supported'} in this run")
    print(f"  exp-growth R0 proxy:  X- = {r0g_m:.2f}   X+ = {r0g_p:.2f}")

    _fig1(wkm, cm, wkp, cp, shocks)
    _fig2(fm, fp, (lom, him), (lop, hip), truth)
    _write_summary(fm, fp, (lom, him), (lop, hip), truth, r0g_m, r0g_p, h6,
                   len(minus), len(plus), wkm, cm, cp)
    print(f"\n  figures -> {FIG}\n  summary -> {DAT}/poc_summary.md")


def _fig1(wkm, cm, wkp, cp, shocks):
    dm = [sim.week_to_date(w) for w in wkm]
    dp = [sim.week_to_date(w) for w in wkp]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.plot(dm, cm, color="#c0392b", lw=1.8, label="X−  destruction  «ИИ заберёт работу»")
    ax.plot(dp, cp, color="#2e8b57", lw=1.8, label="X+  creation  «ИИ даёт возможность»")
    for name, day in shocks.items():
        d = sim.week_to_date(day / 7)
        ax.axvline(d, color="#888", ls="--", lw=0.8, alpha=0.7)
        ax.text(d, ax.get_ylim()[1] * 0.96, name, rotation=90,
                va="top", ha="right", fontsize=7, color="#555")
    ax.set_title("Кривые заражения конкурирующих нарративов об ИИ  "
                 "(SIMULATED — валидация прибора)", fontsize=11)
    ax.set_ylabel("Недельная интенсивность нарратива (упоминания)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig1_infection_curves.png"), dpi=130)
    plt.close(fig)


def _fig2(fm, fp, cim, cip, truth):
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    labels = ["X−\ndestruction", "X+\ncreation"]
    vals = [fm["branching_ratio"], fp["branching_ratio"]]
    los = [vals[0] - cim[0], vals[1] - cip[0]]
    his = [cim[1] - vals[0], cip[1] - vals[1]]
    colors = ["#c0392b", "#2e8b57"]
    ax.bar(labels, vals, yerr=[los, his], capsize=8, color=colors, alpha=0.85,
           edgecolor="black", linewidth=0.8)
    ax.axhline(1.0, color="black", ls="--", lw=1.0)
    ax.text(1.45, 1.01, "n = 1  (критичность)", fontsize=8, color="black")
    for i, (v, tr) in enumerate(zip(vals, [truth["n_minus"], truth["n_plus"]])):
        ax.text(i, v + 0.03, f"n̂={v:.2f}\n(true {tr:.2f})", ha="center", fontsize=9)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Branching ratio  n  (= аналог R₀)")
    ax.set_title("Заразность нарративов: H6 — негатив заразнее\n"
                 "(SIMULATED — валидация прибора)", fontsize=10)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig2_branching_ratios.png"), dpi=130)
    plt.close(fig)


def _write_summary(fm, fp, cim, cip, truth, r0m, r0p, h6, nm, npl, wk, cm, cp):
    np.savetxt(os.path.join(DAT, "weekly_series.csv"),
               np.column_stack([wk, cm[:len(wk)], cp[:len(wk)]]),
               delimiter=",", header="week,destruction,creation", comments="")
    with open(os.path.join(DAT, "poc_summary.md"), "w") as f:
        f.write("# Proof of Concept — результаты (SIMULATED)\n\n")
        f.write("> Числа симулированы для валидации прибора, не доказательство.\n\n")
        f.write(f"- События: X− = {nm}, X+ = {npl}\n")
        f.write(f"- Hawkes n̂(X−) = {fm['branching_ratio']:.3f} "
                f"[90% CI {cim[0]:.3f}, {cim[1]:.3f}], true {truth['n_minus']:.2f}\n")
        f.write(f"- Hawkes n̂(X+) = {fp['branching_ratio']:.3f} "
                f"[90% CI {cip[0]:.3f}, {cip[1]:.3f}], true {truth['n_plus']:.2f}\n")
        f.write(f"- exp-growth R₀: X− = {r0m:.2f}, X+ = {r0p:.2f}\n")
        f.write(f"- H6 (негатив заразнее): {'SUPPORTED' if h6 else 'not supported'}\n")


def run_gdelt():
    import gdelt_client
    print("Fetching live GDELT competing-narrative timelines ...")
    tl = gdelt_client.fetch_competing()
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for key, color, lab in [("minus", "#c0392b", "X− destruction"),
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
    ap.add_argument("--source", choices=["simulate", "gdelt"], default="simulate")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--bootstrap", type=int, default=100)
    args = ap.parse_args()
    if args.source == "gdelt":
        run_gdelt()
    else:
        run_simulate(seed=args.seed, bootstrap=args.bootstrap)
