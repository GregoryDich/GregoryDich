"""Риск-метрики: сверка с руками посчитанными значениями."""
import numpy as np
import pandas as pd
import pytest

from app.analytics import risk


def test_max_drawdown_known():
    # equity: 1.1 → 0.55; просадка от пика 1.1 = -50%
    returns = pd.Series([0.10, -0.50])
    assert risk.max_drawdown(returns) == pytest.approx(-0.5)


def test_var_hist_uniform_tail():
    # 100 доходностей: одна -10%, остальные 0 → 1%-перцентиль тянется к -10%
    returns = pd.Series([-0.10] + [0.0] * 99)
    var99 = risk.var_hist(returns, 0.99)
    assert 0.0 < var99 <= 0.10
    # VaR95: 5-й перцентиль почти нулевой
    assert risk.var_hist(returns, 0.95) == pytest.approx(0.0, abs=1e-9)


def test_cvar_worse_or_equal_var():
    rng = np.random.RandomState(42)
    returns = pd.Series(rng.normal(0, 0.01, 500))
    assert risk.cvar_hist(returns, 0.95) >= risk.var_hist(returns, 0.95)


def test_beta_of_self_is_one():
    rng = np.random.RandomState(1)
    r = pd.Series(rng.normal(0, 0.01, 300))
    assert risk.beta(r, r) == pytest.approx(1.0)


def test_annualized_vol_scaling():
    rng = np.random.RandomState(7)
    r = pd.Series(rng.normal(0, 0.01, 10_000))
    # дневная сигма 1% → годовая ~ 15.87%
    assert risk.annualized_vol(r) == pytest.approx(0.01 * np.sqrt(252), rel=0.05)


def test_metrics_keys():
    rng = np.random.RandomState(3)
    r = pd.Series(rng.normal(0.0003, 0.01, 400))
    m = risk.metrics(r, r, capital=10_000)
    for key in ("ann_return", "ann_vol", "sharpe", "max_drawdown",
                "var95_daily", "cvar95_daily", "beta_spy", "var95_daily_usd"):
        assert key in m
