"""
simulate.py — Two competing AI narratives as Hawkes processes.

Scenario for the proof-of-concept (SIMULATED ground truth):
    Destruction narrative (X-):  more contagious, large exogenous bursts.
    Creation   narrative (X+):  less contagious, smaller bursts.

The simulation lets us validate the whole pipeline end-to-end and check
that the Hawkes MLE recovers  n(X-) > n(X+)  (illustrating hypothesis H6).
Real GDELT/YouTube/Reddit event streams plug into the SAME estimators.
"""
import numpy as np
from datetime import date, timedelta
from hawkes import simulate_cluster

START = date(2022, 1, 1)
END = date(2026, 6, 1)


def _d(y, m, dd):
    return (date(y, m, dd) - START).days


T = (END - START).days

# Exogenous narrative shocks (see NARRATIVE_SHOCKS_REGISTRY.md), day index.
SHOCKS = {
    "ChatGPT launch": _d(2022, 11, 30),
    "GPT-4":          _d(2023, 3, 14),
    "Goldman 300M":   _d(2023, 3, 26),
    "WGA strike":     _d(2023, 5, 2),
    "IMF 40%":        _d(2024, 1, 14),
    "Oracle 30k":     _d(2026, 3, 31),
}

# True branching ratios baked into the simulation (the pipeline must recover these).
TRUE_N_MINUS = 0.85   # destruction: highly contagious
TRUE_N_PLUS = 0.55    # creation:    less contagious

SHOCK_TIMES_MINUS = [
    SHOCKS["ChatGPT launch"], SHOCKS["GPT-4"],
    SHOCKS["Goldman 300M"], SHOCKS["WGA strike"],
    SHOCKS["IMF 40%"], SHOCKS["Oracle 30k"],
]

SHOCK_TIMES_PLUS = [
    SHOCKS["ChatGPT launch"], SHOCKS["GPT-4"],
    _d(2023, 6, 1), _d(2024, 2, 1), SHOCKS["Oracle 30k"],
]


def make_narratives(seed=42):
    """Return (events_minus, events_plus, T, SHOCKS, truth)."""
    rng = np.random.default_rng(seed)

    beta_m = 0.20
    exo_minus = [
        (SHOCKS["ChatGPT launch"], 120), (SHOCKS["GPT-4"], 70),
        (SHOCKS["Goldman 300M"], 60), (SHOCKS["WGA strike"], 50),
        (SHOCKS["IMF 40%"], 55), (SHOCKS["Oracle 30k"], 90),
    ]
    minus = simulate_cluster(mu=0.03, alpha=TRUE_N_MINUS * beta_m, beta=beta_m,
                             T=T, exogenous=exo_minus, rng=rng)

    beta_p = 0.18
    exo_plus = [
        (SHOCKS["ChatGPT launch"], 40), (SHOCKS["GPT-4"], 45),
        (_d(2023, 6, 1), 25), (_d(2024, 2, 1), 30), (SHOCKS["Oracle 30k"], 20),
    ]
    plus = simulate_cluster(mu=0.04, alpha=TRUE_N_PLUS * beta_p, beta=beta_p,
                            T=T, exogenous=exo_plus, rng=rng)

    truth = {"n_minus": TRUE_N_MINUS, "n_plus": TRUE_N_PLUS}
    return minus, plus, T, SHOCKS, truth


def week_to_date(week_index):
    return START + timedelta(days=int(7 * week_index))
