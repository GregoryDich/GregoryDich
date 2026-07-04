"""Композитные ранги value / momentum / quality (StarMine-lite).

Ранг = перцентиль внутри локальной вселенной, 0–100 (выше = лучше).
Прозрачно: value — дёшево по P/E и P/B; momentum — 6-мес рост цены;
quality — ROE и маржа.
"""
from __future__ import annotations

import pandas as pd

from app.warehouse import db


def _pct_rank(s: pd.Series, ascending: bool) -> pd.Series:
    return (s.rank(ascending=ascending, pct=True) * 100).round(0)


def universe_ranks() -> pd.DataFrame:
    """DataFrame: symbol, value_rank, momentum_rank, quality_rank, composite."""
    fund = db.fetchdf(
        "SELECT symbol, pe, pb, dividend_yield, roe, net_margin, rev_growth, "
        "market_cap, source FROM fundamentals")
    if fund.empty:
        return fund
    mom = db.fetchdf(
        """WITH last AS (
             SELECT symbol, close, row_number() OVER (PARTITION BY symbol ORDER BY date DESC) rn
             FROM prices_eod)
           SELECT a.symbol, a.close / b.close - 1 AS mom6m
           FROM last a JOIN last b ON a.symbol = b.symbol
           WHERE a.rn = 1 AND b.rn = 127""")
    df = fund.merge(mom, on="symbol", how="left")
    df["mom6m"] = df["mom6m"].fillna(0.0)

    value = (_pct_rank(df["pe"], ascending=False) + _pct_rank(df["pb"], ascending=False)) / 2
    momentum = _pct_rank(df["mom6m"], ascending=True)
    quality = (_pct_rank(df["roe"], ascending=True) + _pct_rank(df["net_margin"], ascending=True)) / 2

    df["value_rank"] = value.round(0)
    df["momentum_rank"] = momentum.round(0)
    df["quality_rank"] = quality.round(0)
    df["composite"] = ((value + momentum + quality) / 3).round(0)
    df["mom6m_pct"] = (df["mom6m"] * 100).round(1)
    return df.drop(columns=["mom6m"])
