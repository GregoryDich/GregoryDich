"""
growth.py — Epidemic R0 from the early exponential growth rate.

Exposition / robustness companion to the Hawkes branching ratio.
During take-off, cumulative incidence of a contagion grows ~ exp(r*t).
With a mean generation interval T_g, a simple epidemic mapping gives
    R0 ~ exp(r * T_g).
This is the intuitive SIR-flavoured picture for the paper's narrative;
the Hawkes branching ratio is the primary, defensible estimator.
"""
import numpy as np


def exp_growth_r0(weeks, counts, generation_days=4.0, window_weeks=8):
    """
    Estimate an R0 proxy from the steepest positive take-off window.

    weeks, counts : weekly index and weekly event counts.
    generation_days : assumed mean generation interval (days).
    window_weeks : width of the take-off window scanned.
    Returns (R0, r_per_day, window_start_week).
    """
    y = np.log(np.asarray(counts, float) + 1.0)
    best = (-np.inf, None)
    for s in range(0, len(y) - window_weeks):
        xw = np.arange(window_weeks)
        yw = y[s:s + window_weeks]
        r_week = np.polyfit(xw, yw, 1)[0]  # slope of log-counts per week
        if r_week > best[0]:
            best = (r_week, s)
    r_week, s = best
    r_day = r_week / 7.0
    R0 = float(np.exp(r_day * generation_days))
    return R0, r_day, s
