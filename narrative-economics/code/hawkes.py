"""
hawkes.py — Univariate Hawkes process with exponential kernel.

Core instrument for the narrative-economics project (WS5).
phi(t) = alpha * exp(-beta * t),  baseline mu.
Branching ratio  n = alpha / beta  is the direct analog of R0:
    n < 1  -> subcritical (contagion dies out)
    n >= 1 -> explosive.

Used both to (a) estimate n from event timestamps by MLE, and
(b) simulate Hawkes event streams via the cluster representation.
"""
import numpy as np
from scipy.optimize import minimize


# ---------------------------------------------------------------------------
# Likelihood (Ogata recursion, O(n))
# ---------------------------------------------------------------------------
def _recursion_R(t, beta):
    """R_i = sum_{j<i} exp(-beta (t_i - t_j)), computed recursively."""
    n = len(t)
    R = np.zeros(n)
    for i in range(1, n):
        R[i] = np.exp(-beta * (t[i] - t[i - 1])) * (1.0 + R[i - 1])
    return R


def neg_loglik(log_params, t, T):
    """Negative log-likelihood; params in log-space for positivity."""
    mu, alpha, beta = np.exp(log_params)
    R = _recursion_R(t, beta)
    lam = mu + alpha * R
    if np.any(lam <= 0) or beta <= 0:
        return 1e12
    term_sum = np.sum(np.log(lam))
    integral = mu * T + (alpha / beta) * np.sum(1.0 - np.exp(-beta * (T - t)))
    return -(term_sum - integral)


def fit(t, T, x0=None):
    """Maximum-likelihood fit. Returns dict with mu, alpha, beta, n = alpha/beta."""
    t = np.sort(np.asarray(t, dtype=float))
    if x0 is None:
        mu0 = max(len(t) / (2.0 * T), 1e-3)
        gap = np.mean(np.diff(t)) if len(t) > 1 else 1.0
        beta0 = 1.0 / max(gap, 1e-3)
        alpha0 = 0.5 * beta0
        x0 = np.log([mu0, alpha0, beta0])
    res = minimize(neg_loglik, x0, args=(t, T), method="Nelder-Mead",
                   options={"maxiter": 8000, "xatol": 1e-7, "fatol": 1e-7})
    mu, alpha, beta = np.exp(res.x)
    return {"mu": mu, "alpha": alpha, "beta": beta,
            "branching_ratio": alpha / beta,
            "loglik": -res.fun, "success": bool(res.success)}


# ---------------------------------------------------------------------------
# Exact simulation via the cluster (immigrant-birth) representation
# ---------------------------------------------------------------------------
def simulate_cluster(mu, alpha, beta, T, exogenous=None, rng=None,
                     max_events=300000):
    """
    Simulate a Hawkes process on [0, T].

    mu, alpha, beta : baseline and exponential-kernel parameters.
    exogenous : optional list of (time, count) deterministic bursts
                (e.g. a media shock such as the ChatGPT launch).
                Each burst injects `count` immigrant events near `time`.
    Returns sorted event times (np.ndarray).
    """
    rng = rng or np.random.default_rng()
    n_branch = alpha / beta  # mean number of offspring per event

    # background immigrants ~ Poisson(mu) on [0, T]
    n_imm = rng.poisson(mu * T)
    immigrants = list(rng.uniform(0, T, n_imm))

    # exogenous shock bursts (with small jitter so times are distinct)
    if exogenous:
        for time, count in exogenous:
            count = int(count)
            immigrants += list(np.full(count, float(time)) + rng.uniform(0, 1, count))

    events = list(immigrants)
    queue = list(immigrants)
    while queue:
        parent = queue.pop()
        for _ in range(rng.poisson(n_branch)):
            child = parent + rng.exponential(1.0 / beta)
            if child < T:
                events.append(child)
                queue.append(child)
        if len(events) > max_events:
            break

    return np.sort(np.array([e for e in events if 0.0 <= e < T]))


# ---------------------------------------------------------------------------
# Parametric-bootstrap confidence interval for the branching ratio
# ---------------------------------------------------------------------------
def bootstrap_ci(fitted, T, B=100, level=0.90, rng=None):
    """Parametric bootstrap CI for n = alpha/beta, simulating from the fit."""
    rng = rng or np.random.default_rng(0)
    ns = []
    for _ in range(B):
        ev = simulate_cluster(fitted["mu"], fitted["alpha"], fitted["beta"],
                              T, rng=rng)
        if len(ev) < 20:
            continue
        try:
            ns.append(fit(ev, T)["branching_ratio"])
        except Exception:
            continue
    ns = np.array(ns)
    lo = np.percentile(ns, 100 * (1 - level) / 2)
    hi = np.percentile(ns, 100 * (1 + level) / 2)
    return lo, hi, ns
