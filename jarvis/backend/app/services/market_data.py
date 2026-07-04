"""Оркестрация данных: live → фолбэк → демо. Пишет в DuckDB, помечая источник.

Правило честности: UI всегда видит, откуда данные (live | delayed | demo).
"""
from __future__ import annotations

import logging

import pandas as pd

from app.connectors import demo_seed, live
from app.warehouse import db
from app.warehouse.universe import MACRO_SERIES, UNIVERSE

log = logging.getLogger("jarvis.market_data")


def _store_history(symbol: str, df: pd.DataFrame, source: str) -> None:
    out = df[["date", "open", "high", "low", "close", "volume"]].copy()
    out["volume"] = out["volume"].fillna(0)
    out = out.assign(symbol=symbol, source=source)
    db.insert_df(
        "INSERT OR REPLACE INTO prices_eod "
        "SELECT symbol, date, open, high, low, close, volume, source FROM _df",
        out,
    )
    if len(df) >= 2:
        last, prev = df.iloc[-1], df.iloc[-2]
        change = (last.close / prev.close - 1) * 100
        db.execute(
            "INSERT OR REPLACE INTO quotes_latest VALUES (?,?,?,current_timestamp,?)",
            [symbol, float(last.close), float(change),
             "delayed" if source in ("yahoo", "stooq") else source],
        )


def refresh_symbol(symbol: str) -> str:
    """Обновить один тикер. Возвращает использованный источник."""
    for source, fn in (("yahoo", live.yahoo_history), ("stooq", live.stooq_history)):
        try:
            df = fn(symbol)
            _store_history(symbol, df, source)
            return source
        except Exception as e:  # сеть/лимит/парсинг — пробуем следующий источник
            log.debug("%s failed for %s: %s", source, symbol, e)
    return "unavailable"


def refresh_all_quotes() -> dict[str, int]:
    """Фоновая задача: обновить всю вселенную; чего нет нигде — добить демо-сидом."""
    counts = {"live": 0, "unavailable": 0}
    for sym in UNIVERSE:
        src = refresh_symbol(sym)
        counts["live" if src != "unavailable" else "unavailable"] += 1
    demo_seed.seed_securities()
    seeded = demo_seed.seed_prices()
    counts["demo_seeded"] = seeded
    return counts


def refresh_macro() -> dict[str, int]:
    counts = {"live": 0, "unavailable": 0}
    for sid, cfg in MACRO_SERIES.items():
        try:
            if sid == "BOI:USDILS":
                df = live.boi_usdils()
            elif cfg.get("fred") and cfg.get("transform") == "yoy":
                df = live.fred_yoy(cfg["fred"])
            elif cfg.get("fred"):
                df = live.fred_series(cfg["fred"])
            else:
                raise RuntimeError("no live source configured")
            db.executemany("INSERT OR REPLACE INTO macro_observations VALUES (?,?,?)",
                           [[sid, r.date, float(r.value)] for r in df.itertuples()])
            db.execute("UPDATE macro_series SET source='live' WHERE series_id=?", [sid])
            counts["live"] += 1
        except Exception as e:
            log.debug("macro %s unavailable: %s", sid, e)
            counts["unavailable"] += 1
    counts["demo_seeded"] = demo_seed.seed_macro()
    return counts


def ensure_data() -> None:
    """При старте: гарантировать, что каждый экран может отрисоваться."""
    demo_seed.seed_securities()
    demo_seed.seed_prices()
    demo_seed.seed_macro()
    for sym in db.fetchall("SELECT symbol FROM watchlist"):
        pass  # watchlist наполняется в profile.store при онбординге


def data_status() -> dict:
    """Сводка честности данных для бейджа в шапке терминала."""
    rows = db.fetchall(
        "SELECT source, count(*) FROM quotes_latest GROUP BY source")
    by_source = {s: n for s, n in rows}
    total = sum(by_source.values()) or 1
    demo_share = by_source.get("demo", 0) / total
    mode = "demo" if demo_share > 0.5 else ("mixed" if demo_share > 0 else "live")
    return {"mode": mode, "by_source": by_source}
