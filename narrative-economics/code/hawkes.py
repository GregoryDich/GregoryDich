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


# ---------------------------------------------------------------------------
# Shock-aware baseline:  μ(t) = μ₀ + Σ_k δ_k exp(-γ(t − s_k)) 1(t ≥ s_k)
# ---------------------------------------------------------------------------
def baseline_at(t_arr, mu0, gamma, shock_times, shock_deltas):
    """Time-varying baseline at each event time (vectorized over shocks)."""
    t_arr = np.asarray(t_arr, dtype=float)
    shock_times = np.asarray(shock_times, dtype=float)
    shock_deltas = np.asarray(shock_deltas, dtype=float)
    base = np.full(len(t_arr), mu0)
    dt = t_arr[np.newaxis, :] - shock_times[:, np.newaxis]
    mask = dt >= 0
    safe_dt = np.where(mask, dt, 0.0)
    base += np.sum(shock_deltas[:, np.newaxis] * np.exp(-gamma * safe_dt)
                   * mask, axis=0)
    return base


def _baseline_integral(T, mu0, gamma, shock_times, shock_deltas):
    """∫₀ᵀ μ(t) dt for the shock-aware baseline."""
    integral = mu0 * T
    for s_k, d_k in zip(shock_times, shock_deltas):
        if s_k < T:
            integral += (d_k / gamma) * (1.0 - np.exp(-gamma * (T - s_k)))
    return integral


def neg_loglik_shock_aware(log_params, t, T, shock_times):
    """Negative log-likelihood with time-varying baseline."""
    n_shocks = len(shock_times)
    params = np.exp(log_params)
    mu0, alpha, beta, gamma = params[:4]
    deltas = params[4:4 + n_shocks]
    R = _recursion_R(t, beta)
    base = baseline_at(t, mu0, gamma, shock_times, deltas)
    lam = base + alpha * R
    if np.any(lam <= 0):
        return 1e12
    term_sum = np.sum(np.log(lam))
    excite_int = (alpha / beta) * np.sum(1.0 - np.exp(-beta * (T - t)))
    base_int = _baseline_integral(T, mu0, gamma, shock_times, deltas)
    return -(term_sum - base_int - excite_int)


def fit_shock_aware(t, T, shock_times, x0=None):
    """MLE with shock-aware baseline μ(t). Returns dict with mu0, alpha,
    beta, gamma, shock_deltas, branching_ratio."""
    t = np.sort(np.asarray(t, dtype=float))
    shock_times = np.asarray(shock_times, dtype=float)
    n_shocks = len(shock_times)
    if x0 is None:
        naive = fit(t, T)
        mu0 = max(naive["mu"] * 0.3, 1e-4)
        alpha0 = naive["alpha"] * 0.7
        beta0 = naive["beta"]
        gamma0 = 0.05
        delta_inits = []
        for s_k in shock_times:
            mask = (t >= s_k) & (t < s_k + 30.0)
            rate = float(np.sum(mask)) / 30.0
            delta_inits.append(max(rate - mu0, mu0))
        x0 = np.log([mu0, alpha0, beta0, gamma0] + delta_inits)
    res = minimize(neg_loglik_shock_aware, x0, args=(t, T, shock_times),
                   method="Nelder-Mead",
                   options={"maxiter": 20000, "xatol": 1e-8, "fatol": 1e-8})
    params = np.exp(res.x)
    mu0, alpha, beta, gamma = params[:4]
    deltas = params[4:4 + n_shocks]
    return {"mu0": mu0, "alpha": alpha, "beta": beta, "gamma": gamma,
            "shock_deltas": deltas, "branching_ratio": alpha / beta,
            "loglik": -res.fun, "success": bool(res.success),
            "shock_times": shock_times}


def simulate_shock_aware(mu0, alpha, beta, gamma, shock_times, shock_deltas,
                         T, rng=None, max_events=300000):
    """Simulate Hawkes process with shock-aware baseline via cluster method."""
    rng = rng or np.random.default_rng()
    n_branch = alpha / beta
    n_bg = rng.poisson(mu0 * T)
    immigrants = list(rng.uniform(0, T, n_bg))
    for s_k, d_k in zip(shock_times, shock_deltas):
        if s_k >= T:
            continue
        expected = (d_k / gamma) * (1.0 - np.exp(-gamma * (T - s_k)))
        n_shock = rng.poisson(max(expected, 0))
        if n_shock > 0:
            u = rng.uniform(0, 1, n_shock)
            decay_total = 1.0 - np.exp(-gamma * (T - s_k))
            times = s_k - (1.0 / gamma) * np.log(1.0 - u * decay_total)
            immigrants.extend(times.tolist())
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


def bootstrap_ci_shock_aware(fitted, T, B=100, level=0.90, rng=None):
    """Parametric bootstrap CI for branching ratio under shock-aware model."""
    rng = rng or np.random.default_rng(0)
    shock_times = fitted["shock_times"]
    x0 = np.log(np.concatenate([[fitted["mu0"], fitted["alpha"],
                                  fitted["beta"], fitted["gamma"]],
                                 fitted["shock_deltas"]]))
    ns = []
    for _ in range(B):
        ev = simulate_shock_aware(
            fitted["mu0"], fitted["alpha"], fitted["beta"], fitted["gamma"],
            shock_times, fitted["shock_deltas"], T, rng=rng)
        if len(ev) < 20:
            continue
        try:
            ns.append(fit_shock_aware(ev, T, shock_times, x0=x0)
                      ["branching_ratio"])
        except Exception:
            continue
    ns = np.array(ns)
    if len(ns) == 0:
        return 0.0, 1.0, ns
    lo = np.percentile(ns, 100 * (1 - level) / 2)
    hi = np.percentile(ns, 100 * (1 + level) / 2)
    return lo, hi, ns
