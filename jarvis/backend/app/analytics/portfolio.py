"""Портфель из журнала сделок: позиции (метод средней стоимости), стоимость,
мультивалютная оценка USD/ILS, дневная кривая доходности для риск-метрик.
"""
from __future__ import annotations

import pandas as pd

from app.warehouse import db


def positions_from_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Схлопнуть сделки в позиции. Средняя стоимость; продажа уменьшает
    количество и базу пропорционально (реализованный P&L — Фаза 2)."""
    positions: dict[str, dict] = {}
    for t in trades.sort_values("dt").itertuples():
        p = positions.setdefault(t.symbol, {"qty": 0.0, "cost": 0.0, "currency": t.currency})
        if t.side == "buy":
            p["qty"] += t.qty
            p["cost"] += t.qty * t.price + (t.fees or 0)
        elif t.side == "sell":
            if p["qty"] > 0:
                share = min(t.qty / p["qty"], 1.0)
                p["cost"] *= (1 - share)
            p["qty"] = max(p["qty"] - t.qty, 0.0)
    rows = [
        {"symbol": s, "qty": p["qty"], "avg_cost": p["cost"] / p["qty"] if p["qty"] else 0.0,
         "cost_basis": p["cost"], "currency": p["currency"]}
        for s, p in positions.items() if p["qty"] > 1e-9
    ]
    return pd.DataFrame(rows)


def load_trades() -> pd.DataFrame:
    return db.fetchdf("SELECT id, dt, symbol, side, qty, price, currency, fees, note FROM trades ORDER BY dt")


def latest_prices(symbols: list[str]) -> dict[str, tuple[float, str]]:
    if not symbols:
        return {}
    ph = ",".join("?" for _ in symbols)
    rows = db.fetchall(
        f"SELECT symbol, price, source FROM quotes_latest WHERE symbol IN ({ph})", symbols)
    return {s: (p, src) for s, p, src in rows}


def usd_ils_rate() -> float:
    rows = db.fetchall(
        "SELECT price FROM quotes_latest WHERE symbol='ILS=X'")
    if rows and rows[0][0]:
        return float(rows[0][0])
    rows = db.fetchall(
        "SELECT value FROM macro_observations WHERE series_id='BOI:USDILS' ORDER BY date DESC LIMIT 1")
    return float(rows[0][0]) if rows else 3.5


def positions_valued() -> dict:
    trades = load_trades()
    if trades.empty:
        return {"positions": [], "totals": {"value_usd": 0.0, "value_ils": 0.0,
                "cost_usd": 0.0, "pnl_usd": 0.0, "pnl_pct": 0.0,
                "usd_ils": usd_ils_rate()}, "sources": []}
    pos = positions_from_trades(trades)
    prices = latest_prices(pos["symbol"].tolist())
    fx = usd_ils_rate()
    out, sources = [], set()
    for r in pos.itertuples():
        price, src = prices.get(r.symbol, (r.avg_cost, "cost"))
        sources.add(src)
        # позиции в ILS переводим в USD по текущему курсу
        to_usd = 1.0 / fx if r.currency == "ILS" else 1.0
        value_usd = r.qty * price * to_usd
        cost_usd = r.cost_basis * to_usd
        out.append({
            "symbol": r.symbol, "qty": r.qty, "avg_cost": r.avg_cost,
            "price": price, "price_source": src, "currency": r.currency,
            "value_usd": value_usd, "value_ils": value_usd * fx,
            "pnl_usd": value_usd - cost_usd,
            "pnl_pct": (value_usd / cost_usd - 1) * 100 if cost_usd else 0.0,
        })
    total_v = sum(p["value_usd"] for p in out)
    total_c = sum(p["cost_basis"] / (fx if p["currency"] == "ILS" else 1.0)
                  for p in pos.to_dict("records"))
    for p in out:
        p["weight_pct"] = p["value_usd"] / total_v * 100 if total_v else 0.0
    return {
        "positions": sorted(out, key=lambda x: -x["value_usd"]),
        "totals": {"value_usd": total_v, "value_ils": total_v * fx,
                   "cost_usd": total_c, "pnl_usd": total_v - total_c,
                   "pnl_pct": (total_v / total_c - 1) * 100 if total_c else 0.0,
                   "usd_ils": fx},
        "sources": sorted(sources),
    }


def portfolio_daily_returns(lookback_days: int = 500) -> pd.Series:
    """Кривая дневных доходностей: восстановление количества бумаг во времени
    из сделок × дневные закрытия. Валютный эффект ILS-позиций — Фаза 2."""
    trades = load_trades()
    if trades.empty:
        return pd.Series(dtype=float)
    symbols = trades["symbol"].unique().tolist()
    ph = ",".join("?" for _ in symbols)
    prices = db.fetchdf(
        f"SELECT symbol, date, close FROM prices_eod WHERE symbol IN ({ph}) ORDER BY date",
        symbols)
    if prices.empty:
        return pd.Series(dtype=float)
    wide = prices.pivot(index="date", columns="symbol", values="close").ffill()
    wide.index = pd.to_datetime(wide.index)
    wide = wide.tail(lookback_days)

    trades["dt"] = pd.to_datetime(trades["dt"])
    signed = trades.assign(
        signed_qty=trades.apply(lambda t: t.qty if t.side == "buy" else -t.qty, axis=1))
    qty_changes = signed.pivot_table(index="dt", columns="symbol",
                                     values="signed_qty", aggfunc="sum")
    holdings = qty_changes.reindex(wide.index.union(qty_changes.index)).fillna(0).cumsum()
    holdings = holdings.reindex(wide.index).ffill().fillna(0)

    common = [c for c in wide.columns if c in holdings.columns]
    value = (wide[common] * holdings[common]).sum(axis=1)
    value = value[value > 0]
    return value.pct_change().dropna()


def benchmark_returns(symbol: str = "SPY", lookback_days: int = 500) -> pd.Series:
    df = db.fetchdf(
        "SELECT date, close FROM prices_eod WHERE symbol=? ORDER BY date", [symbol])
    if df.empty:
        return pd.Series(dtype=float)
    df["date"] = pd.to_datetime(df["date"])
    s = df.set_index("date")["close"].tail(lookback_days)
    return s.pct_change().dropna()
