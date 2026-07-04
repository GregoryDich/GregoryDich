"""Экран NAV — Навигатор аллокации."""
from fastapi import APIRouter, Query

from app.navigator import channels
from app.profile import store as profile_store
from app.warehouse import db

router = APIRouter(prefix="/api/navigator", tags=["navigator"])


@router.get("")
def recommendations(tranche: float = Query(1000.0, gt=0),
                    horizon: int = Query(12, ge=1, le=120)) -> dict:
    profile = profile_store.load()
    return channels.recommend(profile, tranche=tranche, horizon_months=horizon)


@router.get("/forecasts")
def forecast_journal(limit: int = 50) -> dict:
    """Журнал прогнозов — фундамент будущей калибровки (S1)."""
    rows = db.fetchall(
        """SELECT made_at, channel, horizon_months, p_rise, p_flat, p_fall,
                  expected_return_pct, score, outcome
           FROM forecasts ORDER BY made_at DESC LIMIT ?""", [limit])
    return {"forecasts": [
        {"made_at": str(r[0]), "channel": r[1], "horizon_months": r[2],
         "p_rise": r[3], "p_flat": r[4], "p_fall": r[5],
         "expected_return_pct": r[6], "score": r[7], "outcome": r[8]}
        for r in rows]}
