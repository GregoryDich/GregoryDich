"""Экран Macro & Economy (ECO): серии FRED/BoI/демо, кривая доходности."""
from fastapi import APIRouter, HTTPException

from app.services import market_data
from app.warehouse import db

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("/series")
def list_series() -> dict:
    rows = db.fetchall(
        "SELECT series_id, title, unit, country, source FROM macro_series ORDER BY country, series_id")
    return {"series": [
        {"id": r[0], "title": r[1], "unit": r[2], "country": r[3], "source": r[4]}
        for r in rows]}


@router.get("/series/{series_id:path}")
def series_data(series_id: str, days: int = 750) -> dict:
    meta = db.fetchall(
        "SELECT title, unit, country, source FROM macro_series WHERE series_id=?", [series_id])
    if not meta:
        raise HTTPException(404, f"Серия {series_id} не найдена")
    rows = db.fetchall(
        """SELECT date, value FROM macro_observations
           WHERE series_id=? ORDER BY date DESC LIMIT ?""", [series_id, days])
    rows = list(reversed(rows))
    title, unit, country, source = meta[0]
    return {"id": series_id, "title": title, "unit": unit, "country": country,
            "source": source,
            "points": [{"date": str(d), "value": v} for d, v in rows]}


@router.get("/yield-spread")
def yield_spread() -> dict:
    """Спред 10Y-2Y США — классический индикатор рецессии."""
    rows = db.fetchall(
        """SELECT a.date, a.value - b.value
           FROM macro_observations a
           JOIN macro_observations b ON a.date = b.date
           WHERE a.series_id='FRED:DGS10' AND b.series_id='FRED:DGS2'
           ORDER BY a.date DESC LIMIT 750""")
    rows = list(reversed(rows))
    return {"points": [{"date": str(d), "value": v} for d, v in rows]}


@router.post("/refresh")
def refresh() -> dict:
    return market_data.refresh_macro()
