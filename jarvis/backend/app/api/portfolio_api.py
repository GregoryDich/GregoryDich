"""Экран Portfolio & Risk (PORT): сделки, позиции, риск-метрики, CSV-импорт."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.analytics import portfolio, risk
from app.warehouse import db

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeIn(BaseModel):
    dt: str            # YYYY-MM-DD
    symbol: str
    side: str          # buy | sell
    qty: float
    price: float
    currency: str = "USD"
    fees: float = 0.0
    note: str = ""


@router.get("/positions")
def positions() -> dict:
    return portfolio.positions_valued()


@router.get("/trades")
def trades() -> dict:
    df = portfolio.load_trades()
    if df.empty:
        return {"trades": []}
    df = df.assign(dt=df["dt"].astype(str))
    # через to_json: numpy-типы (int32/float64) становятся JSON-безопасными
    import json
    return {"trades": json.loads(df.to_json(orient="records"))}


@router.post("/trades")
def add_trade(t: TradeIn) -> dict:
    if t.side not in ("buy", "sell"):
        raise HTTPException(422, "side должен быть buy или sell")
    db.execute(
        "INSERT INTO trades (dt, symbol, side, qty, price, currency, fees, note) VALUES (?,?,?,?,?,?,?,?)",
        [t.dt, t.symbol.upper(), t.side, t.qty, t.price, t.currency.upper(), t.fees, t.note])
    return {"ok": True}


@router.delete("/trades/{trade_id}")
def delete_trade(trade_id: int) -> dict:
    db.execute("DELETE FROM trades WHERE id=?", [trade_id])
    return {"ok": True}


@router.post("/trades/import")
async def import_csv(file: UploadFile) -> dict:
    """CSV с колонками: date,symbol,side,qty,price[,currency,fees,note]."""
    text = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    required = {"date", "symbol", "side", "qty", "price"}
    if not reader.fieldnames or not required.issubset({f.strip().lower() for f in reader.fieldnames}):
        raise HTTPException(422, f"CSV должен содержать колонки: {sorted(required)}")
    imported = 0
    for row in reader:
        r = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
        if not r.get("symbol"):
            continue
        db.execute(
            "INSERT INTO trades (dt, symbol, side, qty, price, currency, fees, note) VALUES (?,?,?,?,?,?,?,?)",
            [r["date"], r["symbol"].upper(), r["side"].lower(), float(r["qty"]),
             float(r["price"]), (r.get("currency") or "USD").upper(),
             float(r.get("fees") or 0), r.get("note") or ""])
        imported += 1
    return {"imported": imported}


@router.get("/realized")
def realized() -> dict:
    df = portfolio.realized_pnl(portfolio.load_trades())
    if df.empty:
        return {"items": [], "total_pnl": 0.0}
    import json
    return {"items": json.loads(df.to_json(orient="records")),
            "total_pnl": float(df["pnl"].sum())}


@router.get("/risk")
def risk_metrics() -> dict:
    returns = portfolio.portfolio_daily_returns()
    if returns.empty:
        return {"available": False,
                "reason": "Нет сделок или ценовой истории — импортируйте сделки."}
    bench = portfolio.benchmark_returns("SPY")
    capital = portfolio.positions_valued()["totals"]["value_usd"]
    m = risk.metrics(returns, bench, capital)
    m["available"] = True
    return m


@router.get("/equity-curve")
def equity_curve() -> dict:
    returns = portfolio.portfolio_daily_returns()
    if returns.empty:
        return {"points": []}
    equity = (1 + returns).cumprod()
    return {"points": [
        {"date": str(d.date()), "value": float(v)} for d, v in equity.items()]}
