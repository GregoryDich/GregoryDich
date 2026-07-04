"""Навигатор аллокации: скоринг инвестиционных каналов для одного человека.

Метод честный и прозрачный:
- P(рост/флэт/падение) — ЧАСТОТЫ исходов скользящих окон длиной в горизонт
  по доступной истории представителя канала (никакой магии, только счёт);
- скор = сочетание исторической частоты роста, momentum и штрафа за
  волатильность, взвешенное под риск-профиль пользователя;
- издержки считаются на конкретный транш: комиссии входа/выхода, спред,
  израильский налог 25% на ОЖИДАЕМЫЙ прирост.

Всё это прогноз на основе прошлого — не гарантия и не инвестиционный совет.
Каждый прогноз пишется в журнал (петля самоулучшения S1) ДО того, как
известен исход.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.warehouse import db

FLAT_BAND_ANNUAL = 0.04  # ±4% годовых вокруг нуля считаем «флэтом», скейлится к горизонту

# Каналы: представитель, издержки на сделку, короткое обоснование источника издержек
CHANNELS: dict[str, dict] = {
    "ibkr": {
        "title": "США / глобал (IBKR)",
        "proxy": "SPY",
        "entry_fee_usd": 1.0,     # IBKR Lite/Pro минималка на сделку
        "exit_fee_usd": 1.0,
        "spread_pct": 0.0002,     # SPY сверхликвиден
        "tax_pct": 0.25,          # израильский налог на прирост капитала
        "note": "ETF на широкий рынок США через Interactive Brokers",
    },
    "tase": {
        "title": "Израиль (TASE)",
        "proxy": "^TA125.TA",
        "entry_fee_usd": 8.0,     # типичная комиссия израильского брокера/банка, мин. ₪
        "exit_fee_usd": 8.0,
        "spread_pct": 0.0015,
        "tax_pct": 0.25,
        "note": "Индексный фонд TA-125 через израильского брокера",
    },
    "crypto": {
        "title": "Крипто (BTC)",
        "proxy": "BTC-USD",
        "entry_fee_usd": 0.0,
        "exit_fee_usd": 0.0,
        "spread_pct": 0.003,      # комиссия+спред биржи ~0.3% на сторону
        "tax_pct": 0.25,
        "note": "Bitcoin на регулируемой бирже; высокая волатильность",
    },
    "deposits": {
        "title": "Депозит / money market",
        "proxy": None,            # доходность = ставка ЦБ, риск ~0
        "entry_fee_usd": 0.0,
        "exit_fee_usd": 0.0,
        "spread_pct": 0.0,
        "tax_pct": 0.25,          # налог на проценты (упрощение: та же ставка)
        "note": "Шекелевый/долларовый депозит около ставки ЦБ",
    },
    "bonds": {
        "title": "Облигации (10Y proxy)",
        "proxy": None,            # берём доходность 10Y как ожидание
        "entry_fee_usd": 2.0,
        "exit_fee_usd": 2.0,
        "spread_pct": 0.001,
        "tax_pct": 0.25,
        "note": "Гособлигации/ETF облигаций; доходность ≈ текущая 10Y",
    },
}


def _price_series(symbol: str) -> pd.Series:
    df = db.fetchdf(
        "SELECT date, close FROM prices_eod WHERE symbol=? ORDER BY date", [symbol])
    if df.empty:
        return pd.Series(dtype=float)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["close"]


def _latest_macro(series_id: str, default: float) -> float:
    rows = db.fetchall(
        "SELECT value FROM macro_observations WHERE series_id=? ORDER BY date DESC LIMIT 1",
        [series_id])
    return float(rows[0][0]) if rows else default


def outcome_frequencies(prices: pd.Series, horizon_months: int) -> dict:
    """Частоты исходов скользящих окон длиной horizon по всей истории."""
    window = max(horizon_months * 21, 21)
    if len(prices) < window + 21:
        return {"rise": None, "flat": None, "fall": None, "windows": 0}
    fwd = prices.shift(-window) / prices - 1
    fwd = fwd.dropna()
    band = FLAT_BAND_ANNUAL * horizon_months / 12
    n = len(fwd)
    return {
        "rise": float((fwd > band).mean()),
        "flat": float(((fwd >= -band) & (fwd <= band)).mean()),
        "fall": float((fwd < -band).mean()),
        "windows": int(n),
        "median_return": float(fwd.median()),
    }


def market_stats(prices: pd.Series) -> dict:
    if len(prices) < 130:
        return {"momentum_6m": 0.0, "ann_vol": 0.0, "max_drawdown": 0.0}
    rets = prices.pct_change().dropna()
    mom = float(prices.iloc[-1] / prices.iloc[-126] - 1)
    vol = float(rets.std(ddof=1) * np.sqrt(252))
    equity = (1 + rets).cumprod()
    mdd = float(((equity - equity.cummax()) / equity.cummax()).min())
    return {"momentum_6m": mom, "ann_vol": vol, "max_drawdown": mdd}


RISK_WEIGHTS = {
    #                (вес частоты роста, вес momentum, штраф волатильности)
    "conservative": (0.5, 0.2, 0.9),
    "balanced":     (0.5, 0.3, 0.5),
    "aggressive":   (0.45, 0.4, 0.25),
}


def score_channel(freq: dict, stats: dict, risk_profile: str) -> float:
    """0–100: прозрачная линейная комбинация; не «предсказание», а ранжир."""
    w_rise, w_mom, w_vol = RISK_WEIGHTS.get(risk_profile, RISK_WEIGHTS["balanced"])
    rise = freq.get("rise") or 0.5
    mom = max(min(stats["momentum_6m"], 0.5), -0.5) + 0.5   # → 0..1
    vol_pen = min(stats["ann_vol"], 1.0)
    raw = w_rise * rise + w_mom * mom - w_vol * vol_pen * 0.35
    return round(max(min(raw, 1.0), 0.0) * 100, 1)


def costs_on_tranche(ch: dict, tranche: float, expected_gain_pct: float) -> dict:
    """Издержки конкретного транша: вход+выход+спред+налог на ожидаемый прирост."""
    fees = ch["entry_fee_usd"] + ch["exit_fee_usd"]
    spread = tranche * ch["spread_pct"] * 2
    expected_gain = max(tranche * expected_gain_pct, 0.0)
    tax = expected_gain * ch["tax_pct"]
    total = fees + spread + tax
    return {
        "fees_usd": round(fees, 2),
        "spread_usd": round(spread, 2),
        "tax_on_expected_gain_usd": round(tax, 2),
        "total_usd": round(total, 2),
        "share_of_tranche_pct": round(total / tranche * 100, 2) if tranche else 0.0,
    }


def _rate_channel(key: str, ch: dict, horizon_months: int,
                  tranche: float, risk_profile: str) -> dict:
    """Оценка одного канала: частоты, статы, скор, издержки, обоснование."""
    if ch["proxy"]:
        prices = _price_series(ch["proxy"])
        freq = outcome_frequencies(prices, horizon_months)
        stats = market_stats(prices)
        score = score_channel(freq, stats, risk_profile)
        expected = freq.get("median_return") or 0.0
        reason = (f"За {freq['windows']} окон по {horizon_months} мес рынок рос в "
                  f"{(freq['rise'] or 0) * 100:.0f}% случаев (медиана "
                  f"{expected * 100:+.1f}%); 6-мес momentum {stats['momentum_6m'] * 100:+.1f}%, "
                  f"волатильность {stats['ann_vol'] * 100:.0f}%.")
        src_rows = db.fetchall(
            "SELECT source FROM prices_eod WHERE symbol=? ORDER BY date DESC LIMIT 1",
            [ch["proxy"]])
        data_source = src_rows[0][0] if src_rows else "none"
    else:
        # безрисковые каналы: доходность = текущая ставка, исходы детерминированы
        rate = (_latest_macro("BOI:POLICY", 3.75) if key == "deposits"
                else _latest_macro("FRED:DGS10", 4.1)) / 100
        expected = rate * horizon_months / 12
        freq = {"rise": 1.0, "flat": 0.0, "fall": 0.0, "windows": None,
                "median_return": expected}
        stats = {"momentum_6m": 0.0, "ann_vol": 0.0 if key == "deposits" else 0.07,
                 "max_drawdown": 0.0 if key == "deposits" else -0.1}
        base = 45.0 if key == "deposits" else 50.0
        score = round(base + rate * 200, 1)  # выше ставка — привлекательнее парковка
        reason = (f"Текущая ставка ≈ {rate * 100:.2f}% годовых; риск "
                  f"{'минимальный (депозит)' if key == 'deposits' else 'процентный (дюрация)'}.")
        data_source = "rate"
    return {
        "key": key, "title": ch["title"], "proxy": ch["proxy"], "note": ch["note"],
        "data_source": data_source,
        "probabilities": {"rise": freq["rise"], "flat": freq["flat"], "fall": freq["fall"]},
        "windows": freq.get("windows"),
        "expected_return_pct": round((freq.get("median_return") or 0.0) * 100, 2),
        "momentum_6m_pct": round(stats["momentum_6m"] * 100, 2),
        "ann_vol_pct": round(stats["ann_vol"] * 100, 1),
        "max_drawdown_pct": round(stats["max_drawdown"] * 100, 1),
        "score": score,
        "costs": costs_on_tranche(ch, tranche, freq.get("median_return") or 0.0),
        "reason": reason,
    }


def recommend(profile: dict, tranche: float = 1000.0,
              horizon_months: int = 12) -> dict:
    """Рекомендации по каналам из профиля. Прогнозы пишутся в журнал (S1)."""
    keys = [k for k in (profile.get("channels") or []) if k in CHANNELS] or list(CHANNELS)
    risk = profile.get("risk_profile", "balanced")
    rated = [_rate_channel(k, CHANNELS[k], horizon_months, tranche, risk) for k in keys]
    rated.sort(key=lambda r: -r["score"])

    _log_forecasts(rated, horizon_months)

    investable = profile.get("capital", {}).get("investable_usd", 0.0)
    n_tranches = int(investable // tranche) if tranche else 0
    return {
        "horizon_months": horizon_months,
        "tranche_usd": tranche,
        "available_tranches": n_tranches,
        "risk_profile": risk,
        "channels": rated,
        "currency_note": _currency_note(),
        "disclaimer": ("Частоты исходов посчитаны по доступной истории и не "
                       "гарантируют будущего. Это аналитика, не инвестиционный "
                       "совет — решение всегда за вами."),
    }


def _currency_note() -> str:
    usdils = _latest_macro("BOI:USDILS", 3.5)
    boi = _latest_macro("BOI:POLICY", 3.75)
    fed = _latest_macro("FRED:FEDFUNDS", 3.75)
    diff = fed - boi
    side = "долларе" if diff > 0.25 else ("шекеле" if diff < -0.25 else "обеих валютах")
    return (f"USD/ILS {usdils:.2f}; ставка ФРС {fed:.2f}% vs Банк Израиля {boi:.2f}% — "
            f"кэш выгоднее держать в {side}. Резерв на 3–6 мес расходов держите "
            f"в валюте расходов (₪).")


def _log_forecasts(rated: list[dict], horizon_months: int) -> None:
    """Петля S1: каждый прогноз записывается ДО исхода, для будущей калибровки."""
    for r in rated:
        db.execute(
            """INSERT INTO forecasts (channel, proxy, horizon_months, p_rise, p_flat,
                   p_fall, expected_return_pct, score)
               VALUES (?,?,?,?,?,?,?,?)""",
            [r["key"], r["proxy"], horizon_months,
             r["probabilities"]["rise"], r["probabilities"]["flat"],
             r["probabilities"]["fall"], r["expected_return_pct"], r["score"]])
