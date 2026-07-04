"""End-to-end API-тесты на демо-данных (сеть не нужна)."""
import io

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(fresh_db):
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_health_and_demo_mode(client):
    r = client.get("/api/health").json()
    assert r["ok"] is True
    assert r["data"]["mode"] == "demo"  # в песочнице сети нет — честный демо-режим


def test_markets_overview(client):
    r = client.get("/api/markets/overview").json()
    titles = [g["title"] for g in r["groups"]]
    assert "Индексы" in titles and "Крипто" in titles
    quotes = [q for g in r["groups"] for q in g["quotes"]]
    assert len(quotes) >= 8
    assert all(q["price"] > 0 for q in quotes)
    assert all(q["source"] == "demo" for q in quotes)


def test_history_endpoint(client):
    r = client.get("/api/markets/history/AAPL?days=100").json()
    assert r["symbol"] == "AAPL"
    assert len(r["candles"]) == 100
    c = r["candles"][-1]
    assert c["low"] <= c["close"] <= c["high"]


def test_macro_series(client):
    series = client.get("/api/macro/series").json()["series"]
    ids = {s["id"] for s in series}
    assert {"FRED:DGS10", "BOI:POLICY", "BOI:USDILS"} <= ids
    data = client.get("/api/macro/series/FRED:DGS10").json()
    assert len(data["points"]) > 100
    spread = client.get("/api/macro/yield-spread").json()
    assert spread["points"]


def test_onboarding_and_freedom_flow(client):
    q = client.get("/api/profile/onboarding").json()["questions"]
    assert any(x["id"] == "monthly_expenses" for x in q)

    before = client.get("/api/freedom").json()
    assert before["onboarded"] is False

    client.post("/api/profile", json={
        "name": "Test",
        "monthly_expenses": {"rent": 1200, "food": 500, "clothing": 100,
                             "utilities_subscriptions": 150, "daily_free": 250},
        "capital": {"investable_usd": 50_000},
        "monthly_contribution_usd": 1000,
        "channels": ["ibkr", "crypto"],
    })
    f = client.get("/api/freedom").json()
    assert f["onboarded"] is True
    assert f["monthly_expenses"] == 2200
    assert f["target_capital"] == pytest.approx(660_000)
    assert f["scenarios"]
    assert "не инвестиционный совет" in f["disclaimer"]


def test_portfolio_flow(client):
    client.post("/api/portfolio/trades", json={
        "dt": "2025-06-02", "symbol": "SPY", "side": "buy",
        "qty": 10, "price": 600.0, "fees": 1.0})
    csv_data = ("date,symbol,side,qty,price,currency,fees\n"
                "2025-06-03,AAPL,buy,5,250,USD,1\n"
                "2025-06-04,BTC-USD,buy,0.05,110000,USD,5\n")
    r = client.post("/api/portfolio/trades/import",
                    files={"file": ("trades.csv", io.BytesIO(csv_data.encode()), "text/csv")})
    assert r.json()["imported"] == 2

    pos = client.get("/api/portfolio/positions").json()
    symbols = {p["symbol"] for p in pos["positions"]}
    assert symbols == {"SPY", "AAPL", "BTC-USD"}
    assert pos["totals"]["value_usd"] > 0
    assert pos["totals"]["value_ils"] > pos["totals"]["value_usd"]  # курс > 1

    risk = client.get("/api/portfolio/risk").json()
    assert risk["available"] is True
    assert risk["ann_vol"] > 0
    assert risk["var95_daily"] >= 0

    curve = client.get("/api/portfolio/equity-curve").json()
    assert len(curve["points"]) > 50


def test_alerts_flow(client):
    price = client.get("/api/markets/overview").json()["groups"][0]["quotes"][0]
    # порог заведомо ниже текущей цены → сработает сразу
    client.post("/api/alerts", json={
        "symbol": price["symbol"], "condition": "above",
        "level": price["price"] * 0.5})
    triggered = client.post("/api/alerts/check").json()["triggered"]
    assert len(triggered) == 1
    alerts = client.get("/api/alerts").json()["alerts"]
    assert alerts[0]["active"] is False  # одноразовый алерт погашен

    test_send = client.post("/api/alerts/test").json()
    assert test_send["dry_run"] is True  # каналы не сконфигурированы в тестах


def test_digest_builds(client):
    text = client.post("/api/alerts/digest").json()["text"]
    assert "JARVIS" in text and "Индексы" in text
