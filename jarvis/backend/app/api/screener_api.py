"""Экран EQS — скринер по локальной базе + дип-дайв FA по тикеру."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query

from app.analytics import ranks
from app.warehouse import db
from app.warehouse.universe import UNIVERSE

router = APIRouter(prefix="/api", tags=["screener"])


@router.get("/screener")
def screener(max_pe: float | None = Query(None),
             min_div_yield: float | None = Query(None),
             min_quality: float | None = Query(None),
             min_composite: float | None = Query(None),
             sector: str | None = Query(None)) -> dict:
    df = ranks.universe_ranks()
    if df.empty:
        return {"rows": [], "note": "Фундаментал ещё не загружен"}
    meta = db.fetchdf("SELECT symbol, name, sector, asset_class FROM securities")
    df = df.merge(meta, on="symbol", how="left")
    if max_pe is not None:
        df = df[df["pe"] <= max_pe]
    if min_div_yield is not None:
        df = df[df["dividend_yield"] >= min_div_yield]
    if min_quality is not None:
        df = df[df["quality_rank"] >= min_quality]
    if min_composite is not None:
        df = df[df["composite"] >= min_composite]
    if sector:
        df = df[df["sector"].str.contains(sector, case=False, na=False)]
    df = df.sort_values("composite", ascending=False)
    return {"rows": json.loads(df.to_json(orient="records")),
            "universe_size": int(len(df))}


@router.get("/ticker/{symbol:path}")
def deep_dive(symbol: str) -> dict:
    """FA: профиль, котировка, фундаментал, ранги, дивиденды, 52-нед статы."""
    sec = db.fetchall(
        "SELECT name, asset_class, currency, country, sector FROM securities WHERE symbol=?",
        [symbol])
    if not sec:
        raise HTTPException(404, f"{symbol} не найден в текущей вселенной")
    name, asset_class, currency, country, sector = sec[0]

    quote = db.fetchall(
        "SELECT price, change_pct, source FROM quotes_latest WHERE symbol=?", [symbol])
    prices = db.fetchdf(
        "SELECT date, close FROM prices_eod WHERE symbol=? ORDER BY date DESC LIMIT 252",
        [symbol])
    stats = {}
    if not prices.empty:
        closes = prices["close"]
        stats = {"high_52w": float(closes.max()), "low_52w": float(closes.min()),
                 "ret_1y_pct": round(float(closes.iloc[0] / closes.iloc[-1] - 1) * 100, 1)}

    fund_rows = ranks.universe_ranks()
    fund = None
    if not fund_rows.empty:
        match = fund_rows[fund_rows["symbol"] == symbol]
        if not match.empty:
            fund = json.loads(match.iloc[0].to_json())

    divs = db.fetchall(
        "SELECT date, amount, source FROM dividends WHERE symbol=? ORDER BY date DESC LIMIT 12",
        [symbol])

    return {
        "symbol": symbol, "name": name, "asset_class": asset_class,
        "currency": currency, "country": country, "sector": sector,
        "quote": ({"price": quote[0][0], "change_pct": quote[0][1],
                   "source": quote[0][2]} if quote else None),
        "stats": stats,
        "fundamentals": fund,
        "dividends": [{"date": str(d), "amount": a, "source": s} for d, a, s in divs],
        "in_universe": symbol in UNIVERSE,
    }
