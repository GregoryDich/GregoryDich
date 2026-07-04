"""Риск-метрики портфеля (Aladdin-for-one, базовый уровень).

Все функции принимают pd.Series дневных доходностей (доли, не %).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def annualized_return(returns: pd.Series) -> float:
    if len(returns) == 0:
        return 0.0
    total = float((1 + returns).prod())
    years = len(returns) / TRADING_DAYS
    return total ** (1 / years) - 1 if years > 0 and total > 0 else 0.0


def annualized_vol(returns: pd.Series) -> float:
    return float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS)) if len(returns) > 1 else 0.0


def sharpe(returns: pd.Series, rf_annual: float = 0.0) -> float:
    vol = annualized_vol(returns)
    if vol == 0:
        return 0.0
    return (annualized_return(returns) - rf_annual) / vol


def sortino(returns: pd.Series, rf_annual: float = 0.0) -> float:
    downside = returns[returns < 0]
    if len(downside) < 2:
        return 0.0
    dvol = float(downside.std(ddof=1) * np.sqrt(TRADING_DAYS))
    return (annualized_return(returns) - rf_annual) / dvol if dvol else 0.0


def max_drawdown(returns: pd.Series) -> float:
    """Максимальная просадка кривой капитала, отрицательное число (доля)."""
    if len(returns) == 0:
        return 0.0
    equity = (1 + returns).cumprod()
    peak = equity.cummax()
    return float(((equity - peak) / peak).min())


def var_hist(returns: pd.Series, confidence: float = 0.95) -> float:
    """Исторический дневной VaR: потеря, которую не превысим с данной уверенностью.

    Возвращает положительное число (долю). VaR 95% = 0.02 → «в 95% дней
    потеря не превысит 2%».
    """
    if len(returns) < 20:
        return 0.0
    return float(-np.percentile(returns, (1 - confidence) * 100))


def cvar_hist(returns: pd.Series, confidence: float = 0.95) -> float:
    """Expected Shortfall: средняя потеря в худших (1-confidence) днях."""
    if len(returns) < 20:
        return 0.0
    cutoff = np.percentile(returns, (1 - confidence) * 100)
    tail = returns[returns <= cutoff]
    return float(-tail.mean()) if len(tail) else 0.0


def beta(returns: pd.Series, benchmark: pd.Series) -> float:
    joined = pd.concat([returns, benchmark], axis=1, join="inner").dropna()
    if len(joined) < 20:
        return 0.0
    cov = joined.cov().iloc[0, 1]
    var_b = joined.iloc[:, 1].var(ddof=1)
    return float(cov / var_b) if var_b else 0.0


RELIABLE_MIN_DAYS = 120  # меньше ~полугода истории — метрики ненадёжны


def metrics(returns: pd.Series, benchmark: pd.Series | None = None,
            capital: float | None = None) -> dict:
    out = {
        "reliability": "ok" if len(returns) >= RELIABLE_MIN_DAYS else "low",
        "ann_return": annualized_return(returns),
        "ann_vol": annualized_vol(returns),
        "sharpe": sharpe(returns),
        "sortino": sortino(returns),
        "max_drawdown": max_drawdown(returns),
        "var95_daily": var_hist(returns, 0.95),
        "cvar95_daily": cvar_hist(returns, 0.95),
        "var99_daily": var_hist(returns, 0.99),
        "n_days": int(len(returns)),
    }
    if benchmark is not None:
        out["beta_spy"] = beta(returns, benchmark)
    if capital:
        out["var95_daily_usd"] = out["var95_daily"] * capital
        out["cvar95_daily_usd"] = out["cvar95_daily"] * capital
    return out
