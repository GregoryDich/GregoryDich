"""CRUD алертов + тест доставки + дайджест по запросу."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.alerts import engine, notify
from app.warehouse import db

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertIn(BaseModel):
    symbol: str
    condition: str  # above | below
    level: float
    note: str = ""


@router.get("")
def list_alerts() -> dict:
    rows = db.fetchall(
        """SELECT id, symbol, condition, level, active, note,
                  created_at, last_triggered_at
           FROM alerts ORDER BY created_at DESC""")
    return {"alerts": [
        {"id": r[0], "symbol": r[1], "condition": r[2], "level": r[3],
         "active": r[4], "note": r[5], "created_at": str(r[6]),
         "last_triggered_at": str(r[7]) if r[7] else None} for r in rows]}


@router.post("")
def create_alert(a: AlertIn) -> dict:
    if a.condition not in ("above", "below"):
        raise HTTPException(422, "condition должен быть above или below")
    db.execute(
        "INSERT INTO alerts (symbol, condition, level, note) VALUES (?,?,?,?)",
        [a.symbol.upper(), a.condition, a.level, a.note])
    return {"ok": True}


@router.delete("/{alert_id}")
def delete_alert(alert_id: int) -> dict:
    db.execute("DELETE FROM alerts WHERE id=?", [alert_id])
    return {"ok": True}


@router.post("/check")
def check_now() -> dict:
    return {"triggered": engine.check_alerts()}


@router.post("/test")
def test_delivery() -> dict:
    """Проверка каналов доставки (Telegram + ntfy)."""
    result = notify.send("JARVIS: тест", "Каналы доставки работают ✅")
    result["configured_channels"] = len(notify.channels())
    return result


@router.post("/digest")
def digest_now() -> dict:
    return {"text": engine.morning_digest()}
