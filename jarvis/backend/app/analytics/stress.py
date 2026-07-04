"""Стресс-тесты портфеля (Aladdin-for-one) + ребалансировка целыми лотами.

Два вида стрессов, оба прозрачны:
1. Исторический: худшее 21-дневное движение КАЖДОГО актива из доступной
   истории, применённое одновременно (консервативно: корреляция = 1).
2. Гипотетические сценарии с явными допущениями по классам активов —
   допущения показываются пользователю, а не прячутся.
"""
from __future__ import annotations

import pandas as pd

from app.analytics import portfolio
from app.warehouse import db

# Гипотетические сценарии: шок по классам активов, доли (напр. -0.10 = -10%)
SCENARIOS: list[dict] = [
    {"key": "rates_up_100", "title": "Ставки +100бп",
     "assumption": "акции −5%, TASE −4%, облигации −7% (дюрация ~7), крипто −10%, золото −2%",
     "shocks": {"equity": -0.05, "etf": -0.05, "index": -0.05,
                "crypto": -0.10, "commodity": -0.02, "fx": 0.0}},
    {"key": "global_selloff", "title": "Глобальная распродажа −20%",
     "assumption": "широкий рынок −20%, крипто падает с бетой ~2 (−40%), золото +5%",
     "shocks": {"equity": -0.20, "etf": -0.20, "index": -0.20,
                "crypto": -0.40, "commodity": 0.05, "fx": 0.0}},
    {"key": "crypto_winter", "title": "Крипто-зима",
     "assumption": "BTC/ETH −50%, остальное без изменений",
     "shocks": {"crypto": -0.50}},
    {"key": "shekel_down_10", "title": "Шекель −10%",
     "assumption": "ILS-активы теряют 10% долларовой стоимости; долларовые не меняются",
     "shocks": {"_ils_positions": -0.10}},
]

HORIZON_DAYS = 21  # «худший месяц»


def _worst_move(symbol: str, days: int = HORIZON_DAYS) -> float | None:
    df = db.fetchdf(
        "SELECT date, close FROM prices_eod WHERE symbol=? ORDER BY date", [symbol])
    if len(df) < days + 5:
        return None
    closes = df["close"]
    fwd = closes.shift(-days) / closes - 1
    return float(fwd.min())


def historical_worst() -> dict:
    """Худший месяц каждого актива одновременно (консервативная оценка)."""
    pos = portfolio.positions_valued()
    if not pos["positions"]:
        return {"available": False}
    rows, total_loss = [], 0.0
    for p in pos["positions"]:
        worst = _worst_move(p["symbol"])
        if worst is None:
            worst = -0.15  # нет истории — консервативное допущение
        loss = p["value_usd"] * worst
        total_loss += loss
        rows.append({"symbol": p["symbol"], "value_usd": p["value_usd"],
                     "worst_move_pct": round(worst * 100, 1),
                     "loss_usd": round(loss, 0)})
    total = pos["totals"]["value_usd"]
    return {"available": True, "horizon_days": HORIZON_DAYS,
            "positions": rows,
            "total_loss_usd": round(total_loss, 0),
            "total_loss_pct": round(total_loss / total * 100, 1) if total else 0.0,
            "note": ("Худшие 21-дневные движения каждого актива из доступной истории, "
                     "одновременно (корреляция=1) — консервативная нижняя граница.")}


def hypothetical() -> dict:
    """Сценарные шоки по классам активов с явными допущениями."""
    pos = portfolio.positions_valued()
    if not pos["positions"]:
        return {"available": False}
    classes = {s: a for s, a in db.fetchall(
        "SELECT symbol, asset_class FROM securities")}
    total = pos["totals"]["value_usd"]
    out = []
    for sc in SCENARIOS:
        loss = 0.0
        for p in pos["positions"]:
            if "_ils_positions" in sc["shocks"]:
                shock = sc["shocks"]["_ils_positions"] if p["currency"] == "ILS" else 0.0
            else:
                shock = sc["shocks"].get(classes.get(p["symbol"], "equity"), 0.0)
            loss += p["value_usd"] * shock
        out.append({"key": sc["key"], "title": sc["title"],
                    "assumption": sc["assumption"],
                    "impact_usd": round(loss, 0),
                    "impact_pct": round(loss / total * 100, 1) if total else 0.0})
    return {"available": True, "scenarios": out}


def rebalance_suggestion() -> dict:
    """Ребалансировка к равным весам целыми лотами (DiscreteAllocation)."""
    pos = portfolio.positions_valued()
    if len(pos["positions"]) < 2:
        return {"available": False,
                "reason": "Нужно минимум 2 позиции для ребалансировки"}
    symbols = [p["symbol"] for p in pos["positions"]]
    prices = {p["symbol"]: p["price"] for p in pos["positions"]}
    total = pos["totals"]["value_usd"]
    target_w = {s: 1.0 / len(symbols) for s in symbols}
    try:
        from pypfopt.discrete_allocation import DiscreteAllocation

        da = DiscreteAllocation(target_w, pd.Series(prices), total_portfolio_value=total)
        alloc, leftover = da.greedy_portfolio()
    except Exception as e:
        return {"available": False, "reason": f"pypfopt: {e}"}
    trades = []
    current_qty = {p["symbol"]: p["qty"] for p in pos["positions"]}
    for s in symbols:
        diff = alloc.get(s, 0) - current_qty.get(s, 0)
        if abs(diff) * prices[s] < 50:  # игнорируем сделки мельче $50
            continue
        trades.append({"symbol": s, "action": "купить" if diff > 0 else "продать",
                       "qty": round(abs(diff), 4),
                       "approx_usd": round(abs(diff) * prices[s], 0)})
    return {"available": True, "target": "равные веса",
            "trades": trades, "leftover_usd": round(float(leftover), 2),
            "note": ("Целые лоты под ваш размер капитала. Перед исполнением "
                     "проверьте комиссии (экран NAV) — мелкие сделки могут не "
                     "окупаться. Не инвестиционный совет.")}
