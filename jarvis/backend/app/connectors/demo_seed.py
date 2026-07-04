"""Детерминированный демо-режим: синтетические ряды, когда live-источники недоступны.

Всё, что сгенерировано здесь, помечается source='demo' и честно показывается в UI.
Генерация детерминирована (seed от имени тикера) — тесты и скриншоты воспроизводимы.
"""
from __future__ import annotations

import datetime as dt
import hashlib

import numpy as np
import pandas as pd

from app.warehouse import db
from app.warehouse.universe import MACRO_SERIES, UNIVERSE

DEMO_DAYS = 750  # ~3 года торговых дней


def _seed_for(name: str) -> int:
    return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)


def _trading_dates(n: int, end: dt.date | None = None) -> list[dt.date]:
    end = end or dt.date.today()
    dates: list[dt.date] = []
    d = end
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d)
        d -= dt.timedelta(days=1)
    return list(reversed(dates))


def make_ohlcv(symbol: str, n_days: int = DEMO_DAYS) -> pd.DataFrame:
    """Геометрическое случайное блуждание вокруг базового уровня инструмента."""
    meta = UNIVERSE[symbol]
    rng = np.random.RandomState(_seed_for(symbol))
    vol = meta.get("vol", 0.015)
    drift = 0.0002 if meta["asset_class"] not in ("fx",) else 0.0
    rets = rng.normal(drift, vol, n_days)
    if meta.get("mean_revert"):  # VIX-подобные
        rets = rets - 0.02 * np.cumsum(rets) / np.arange(1, n_days + 1)
    path = np.exp(np.cumsum(rets))
    close = meta["base"] * path / path[-1]  # приводим конец ряда к базовому уровню
    dates = _trading_dates(n_days)
    intraday = np.abs(rng.normal(0, vol / 2, n_days))
    open_ = close * (1 + rng.normal(0, vol / 3, n_days))
    high = np.maximum(open_, close) * (1 + intraday)
    low = np.minimum(open_, close) * (1 - intraday)
    volume = rng.lognormal(15, 0.4, n_days)
    return pd.DataFrame(
        {"date": dates, "open": open_, "high": high, "low": low,
         "close": close, "volume": volume}
    )


def make_macro(series_id: str, n_days: int = DEMO_DAYS) -> pd.DataFrame:
    cfg = MACRO_SERIES[series_id]
    rng = np.random.RandomState(_seed_for(series_id))
    n = n_days // 21 if cfg.get("monthly") else n_days
    steps = rng.normal(0, cfg.get("vol", 0.02), n)
    if cfg.get("step"):  # ставки ЦБ меняются редко и ступенчато
        steps = np.where(rng.random(n) < 0.03, np.round(rng.normal(0, 0.25, n) * 4) / 4, 0.0)
    path = cfg["base"] + np.cumsum(steps)
    path = path - (path[-1] - cfg["base"])  # конец ряда в базовом значении
    lo, hi = cfg.get("clip", (-1e9, 1e9))
    path = np.clip(path, lo, hi)
    all_dates = _trading_dates(n_days)
    dates = all_dates[::21][:n] if cfg.get("monthly") else all_dates
    return pd.DataFrame({"date": dates[: len(path)], "value": path[: len(dates)]})


def seed_securities() -> None:
    for sym, m in UNIVERSE.items():
        db.execute(
            "INSERT OR REPLACE INTO securities VALUES (?,?,?,?,?,?)",
            [sym, m["name"], m["asset_class"], m["currency"], m["country"], m["sector"]],
        )


def seed_prices(symbols: list[str] | None = None) -> int:
    """Заполнить prices_eod/quotes_latest демо-данными для тикеров без данных."""
    symbols = symbols or list(UNIVERSE.keys())
    seeded = 0
    for sym in symbols:
        (have,) = db.fetchall("SELECT count(*) FROM prices_eod WHERE symbol=?", [sym])[0]
        if have > 0:
            continue
        df = make_ohlcv(sym).assign(symbol=sym, source="demo")
        db.insert_df(
            "INSERT OR REPLACE INTO prices_eod "
            "SELECT symbol, date, open, high, low, close, volume, source FROM _df",
            df,
        )
        last, prev = df.iloc[-1], df.iloc[-2]
        change = (last.close / prev.close - 1) * 100
        db.execute(
            "INSERT OR REPLACE INTO quotes_latest VALUES (?,?,?,current_timestamp,?)",
            [sym, float(last.close), float(change), "demo"],
        )
        seeded += 1
    return seeded


def seed_dividends() -> int:
    """Демо-дивиденды для ETF/акций: квартальные, годовая доходность 0.5–2.5%
    (детерминированно от тикера). Крипта/FX/индексы не платят."""
    seeded = 0
    for sym, meta in UNIVERSE.items():
        if meta["asset_class"] not in ("etf", "equity"):
            continue
        (have,) = db.fetchall("SELECT count(*) FROM dividends WHERE symbol=?", [sym])[0]
        if have > 0:
            continue
        rng = np.random.RandomState(_seed_for(sym + ":div"))
        annual_yield = 0.005 + rng.random() * 0.02
        quarterly = meta["base"] * annual_yield / 4
        dates = _trading_dates(DEMO_DAYS)[::63]  # ~раз в квартал
        rows = pd.DataFrame({"date": dates,
                             "amount": [quarterly] * len(dates)})
        rows = rows.assign(symbol=sym, source="demo")
        db.insert_df(
            "INSERT OR REPLACE INTO dividends SELECT symbol, date, amount, source FROM _df",
            rows)
        seeded += 1
    return seeded


def seed_fundamentals() -> int:
    """Демо-фундаментал для акций/ETF: правдоподобные детерминированные
    значения (source='demo') — чтобы скринер и дип-дайв жили без сети."""
    seeded = 0
    for sym, meta in UNIVERSE.items():
        if meta["asset_class"] not in ("equity", "etf"):
            continue
        (have,) = db.fetchall(
            "SELECT count(*) FROM fundamentals WHERE symbol=?", [sym])[0]
        if have > 0:
            continue
        rng = np.random.RandomState(_seed_for(sym + ":fund"))
        is_tech = meta.get("sector") == "Technology"
        pe = float(rng.uniform(22, 55) if is_tech else rng.uniform(8, 30))
        db.execute(
            "INSERT OR REPLACE INTO fundamentals VALUES (?,?,?,?,?,?,?,?,?, current_timestamp)",
            [sym, pe, float(rng.uniform(1.2, 12)),
             float(rng.uniform(0.0, 3.0)), float(rng.uniform(5, 45)),
             float(rng.uniform(3, 35)), float(rng.uniform(-5, 40)),
             float(meta["base"] * rng.uniform(1e8, 2e9)), "demo"])
        seeded += 1
    return seeded


def seed_macro() -> int:
    seeded = 0
    for sid, cfg in MACRO_SERIES.items():
        db.execute(
            "INSERT OR REPLACE INTO macro_series VALUES (?,?,?,?,?)",
            [sid, cfg["title"], cfg["unit"], cfg["country"], "demo"],
        )
        (have,) = db.fetchall("SELECT count(*) FROM macro_observations WHERE series_id=?", [sid])[0]
        if have > 0:
            continue
        df = make_macro(sid).assign(series_id=sid)
        db.insert_df(
            "INSERT OR REPLACE INTO macro_observations "
            "SELECT series_id, date, value FROM _df",
            df,
        )
        seeded += 1
    return seeded


def seed_all() -> dict:
    seed_securities()
    return {"prices": seed_prices(), "macro": seed_macro(),
            "dividends": seed_dividends(), "fundamentals": seed_fundamentals()}
