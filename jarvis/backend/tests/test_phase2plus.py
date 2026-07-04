"""Фазы 2–5: Навигатор, скринер, календарь, копайлот, нарративы, стресс, auth."""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.navigator.channels import outcome_frequencies


@pytest.fixture()
def client(fresh_db):
    from app.main import app

    with TestClient(app) as c:
        c.post("/api/profile", json={
            "monthly_expenses": {"rent": 1000, "food": 500, "clothing": 100,
                                 "utilities_subscriptions": 200, "daily_free": 200},
            "capital": {"investable_usd": 8000},
            "channels": ["ibkr", "tase", "crypto", "deposits"],
            "risk_profile": "balanced"})
        for t in ({"dt": "2025-06-02", "symbol": "SPY", "side": "buy", "qty": 3, "price": 600},
                  {"dt": "2025-07-01", "symbol": "BTC-USD", "side": "buy", "qty": 0.01, "price": 110000}):
            c.post("/api/portfolio/trades", json=t)
        yield c


# --- Навигатор ---------------------------------------------------------------

def test_outcome_frequencies_monotonic_rise():
    # строго растущий ряд → 100% окон в росте
    prices = pd.Series(np.linspace(100, 200, 400))
    f = outcome_frequencies(prices, horizon_months=3)
    assert f["rise"] == pytest.approx(1.0)
    assert f["fall"] == pytest.approx(0.0)


def test_navigator_endpoint(client):
    r = client.get("/api/navigator?tranche=1000&horizon=12").json()
    assert r["channels"], "каналы не рассчитаны"
    keys = [c["key"] for c in r["channels"]]
    assert set(keys) == {"ibkr", "tase", "crypto", "deposits"}
    scores = [c["score"] for c in r["channels"]]
    assert scores == sorted(scores, reverse=True), "не отсортировано по скору"
    for c in r["channels"]:
        p = c["probabilities"]
        if c["proxy"]:  # рыночные каналы: вероятности из частот, сумма ~1
            assert p["rise"] + p["flat"] + p["fall"] == pytest.approx(1.0, abs=0.01)
        assert c["costs"]["total_usd"] >= 0
        assert "не инвестиционный совет" not in c["reason"]  # дисклеймер один, наверху
    assert "не инвестиционный совет" in r["disclaimer"]
    # петля S1: прогнозы записаны в журнал
    j = client.get("/api/navigator/forecasts").json()["forecasts"]
    assert len(j) == 4


# --- Скринер и дип-дайв --------------------------------------------------------

def test_screener_and_filters(client):
    all_rows = client.get("/api/screener").json()["rows"]
    assert len(all_rows) >= 10
    assert all(0 <= r["composite"] <= 100 for r in all_rows)
    cheap = client.get("/api/screener?max_pe=15").json()["rows"]
    assert all(r["pe"] <= 15 for r in cheap)
    assert len(cheap) < len(all_rows)


def test_deep_dive(client):
    r = client.get("/api/ticker/AAPL").json()
    assert r["name"] == "Apple"
    assert r["quote"]["price"] > 0
    assert r["fundamentals"]["pe"] > 0
    assert "high_52w" in r["stats"]
    assert r["dividends"], "у демо-AAPL должны быть дивиденды"


# --- Календарь -----------------------------------------------------------------

def test_calendar(client):
    r = client.get("/api/calendar?days=45").json()
    assert r["events"], "календарь пуст"
    kinds = {e["kind"] for e in r["events"]}
    assert kinds <= {"dividend", "earnings", "macro", "cb"}
    dates = [e["date"] for e in r["events"]]
    assert dates == sorted(dates)


# --- Копайлот (фолбэк без ключа) -------------------------------------------------

def test_ai_status_and_fallback(client):
    assert client.get("/api/ai/status").json()["llm_enabled"] is False
    r = client.post("/api/ai/chat", json={"message": "как мой портфель?"}).json()
    assert r["used_llm"] is False
    assert "Портфель" in r["reply"] and "SPY" in r["reply"]
    r2 = client.post("/api/ai/chat", json={"message": "далеко до свободы?"}).json()
    assert "своб" in r2["reply"].lower()


def test_ai_sql_guard():
    from app.ai.copilot import _safe_sql

    assert _safe_sql("SELECT * FROM trades") == "SELECT * FROM trades"
    for bad in ("DROP TABLE trades", "SELECT 1; DELETE FROM trades",
                "insert into trades VALUES (1)"):
        with pytest.raises(ValueError):
            _safe_sql(bad)


# --- Нарративы -------------------------------------------------------------------

def test_narratives_demo(client):
    r = client.get("/api/narratives").json()
    assert len(r["themes"]) == 5
    t = r["themes"][0]
    assert t["source"] == "demo"  # в песочнице GDELT недоступен
    assert len(t["values"]) == len(t["dates"]) == 365
    assert "z" in t["spike"]
    assert "r0" in t["r0"] or t["r0"].get("r0") is not None or "note" in t["r0"]


# --- Стресс и ребалансировка -------------------------------------------------------

def test_stress(client):
    r = client.get("/api/portfolio/stress").json()
    h = r["historical"]
    assert h["available"] and h["total_loss_usd"] < 0
    assert any(row["worst_move_pct"] < 0 for row in h["positions"])
    hyp = r["hypothetical"]
    crypto_winter = next(s for s in hyp["scenarios"] if s["key"] == "crypto_winter")
    assert crypto_winter["impact_usd"] < 0  # BTC в портфеле есть


def test_rebalance(client):
    r = client.get("/api/portfolio/rebalance").json()
    assert r["available"] is True
    assert isinstance(r["trades"], list)


# --- Auth ---------------------------------------------------------------------------

def test_basic_auth_gate(fresh_db, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "JARVIS_PASSWORD", "secret123")
    from app.main import app

    with TestClient(app) as c:
        assert c.get("/api/health").status_code == 401
        ok = c.get("/api/health", headers={"Authorization": "Bearer secret123"})
        assert ok.status_code == 200
