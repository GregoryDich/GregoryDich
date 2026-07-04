"""Экран Markets Overview (WEI) и графики (GP)."""
from fastapi import APIRouter, HTTPException

from app.services import market_data
from app.warehouse import db
from app.warehouse.universe import MARKET_GROUPS, UNIVERSE

router = APIRouter(prefix="/api/markets", tags=["markets"])


@router.get("/overview")
def overview() -> dict:
    groups = []
    for title, symbols in MARKET_GROUPS:
        ph = ",".join("?" for _ in symbols)
        rows = db.fetchall(
            f"""SELECT q.symbol, s.name, q.price, q.change_pct, q.source
                FROM quotes_latest q JOIN securities s USING(symbol)
                WHERE q.symbol IN ({ph})""", symbols)
        by_symbol = {r[0]: r for r in rows}
        groups.append({
            "title": title,
            "quotes": [
                {"symbol": s, "name": by_symbol[s][1], "price": by_symbol[s][2],
                 "change_pct": by_symbol[s][3], "source": by_symbol[s][4]}
                for s in symbols if s in by_symbol
            ],
        })
    return {"groups": groups, "status": market_data.data_status()}


@router.get("/watchlist")
def watchlist() -> dict:
    rows = db.fetchall(
        """SELECT w.symbol, s.name, s.asset_class, q.price, q.change_pct, q.source
           FROM watchlist w
           LEFT JOIN securities s USING(symbol)
           LEFT JOIN quotes_latest q USING(symbol)
           ORDER BY w.added_at""")
    return {"items": [
        {"symbol": r[0], "name": r[1], "asset_class": r[2],
         "price": r[3], "change_pct": r[4], "source": r[5]} for r in rows]}


@router.post("/watchlist/{symbol}")
def watchlist_add(symbol: str) -> dict:
    if symbol not in UNIVERSE:
        raise HTTPException(404, f"Символ {symbol} не в текущей вселенной MVP")
    db.execute("INSERT OR REPLACE INTO watchlist (symbol) VALUES (?)", [symbol])
    return {"ok": True}


@router.delete("/watchlist/{symbol}")
def watchlist_remove(symbol: str) -> dict:
    db.execute("DELETE FROM watchlist WHERE symbol=?", [symbol])
    return {"ok": True}


@router.get("/history/{symbol:path}")
def history(symbol: str, days: int = 365) -> dict:
    rows = db.fetchall(
        """SELECT date, open, high, low, close, volume, source FROM prices_eod
           WHERE symbol=? ORDER BY date DESC LIMIT ?""", [symbol, days])
    if not rows:
        raise HTTPException(404, f"Нет данных по {symbol}")
    rows = list(reversed(rows))
    return {
        "symbol": symbol,
        "name": UNIVERSE.get(symbol, {}).get("name", symbol),
        "source": rows[-1][6],
        "candles": [
            {"time": str(d), "open": o, "high": h, "low": lo, "close": c, "volume": v}
            for d, o, h, lo, c, v, _ in rows],
    }


@router.get("/heatmap")
def heatmap() -> dict:
    """Данные для treemap: акции по секторам, размер = |вес|, цвет = изменение."""
    rows = db.fetchall(
        """SELECT s.symbol, s.name, s.sector, q.price, q.change_pct
           FROM securities s JOIN quotes_latest q USING(symbol)
           WHERE s.asset_class = 'equity'""")
    return {"items": [
        {"symbol": r[0], "name": r[1], "sector": r[2] or "Другое",
         "price": r[3], "change_pct": r[4] or 0} for r in rows]}


@router.post("/refresh")
def refresh() -> dict:
    """Ручное обновление котировок (live → фолбэк → демо)."""
    return market_data.refresh_all_quotes()
