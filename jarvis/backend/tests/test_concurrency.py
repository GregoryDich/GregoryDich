"""Конкурентный smoke-тест: тот самый тест, который поймал бы гонку DuckDB.

20 потоков одновременно бьют по всем GET-эндпоинтам и проверяют не только
статус, но и ФОРМУ ответа — при гонке result set'ов эндпоинты возвращали
чужие/пустые данные без ошибок HTTP.
"""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(fresh_db):
    from app.main import app

    with TestClient(app) as c:
        # немного состояния, чтобы у всех эндпоинтов были данные
        c.post("/api/profile", json={
            "monthly_expenses": {"rent": 1000, "food": 500, "clothing": 100,
                                 "utilities_subscriptions": 200, "daily_free": 200},
            "capital": {"investable_usd": 10_000}})
        c.post("/api/portfolio/trades", json={
            "dt": "2025-06-02", "symbol": "SPY", "side": "buy",
            "qty": 5, "price": 600.0})
        c.post("/api/alerts", json={"symbol": "SPY", "condition": "below", "level": 1.0})
        yield c


CHECKS = [
    ("/api/health", lambda j: j["ok"] is True),
    ("/api/markets/overview", lambda j: len(j["groups"]) >= 3
        and all(q["price"] > 0 for g in j["groups"] for q in g["quotes"])),
    ("/api/markets/watchlist", lambda j: len(j["items"]) >= 1),
    ("/api/markets/history/AAPL?days=50",
        lambda j: len(j["candles"]) == 50
        and all(c["low"] <= c["close"] <= c["high"] for c in j["candles"])),
    ("/api/markets/heatmap", lambda j: len(j["items"]) >= 5),
    ("/api/macro/series", lambda j: len(j["series"]) >= 5),
    ("/api/macro/series/FRED:DGS10", lambda j: len(j["points"]) > 100),
    ("/api/macro/yield-spread", lambda j: len(j["points"]) > 100),
    ("/api/freedom", lambda j: j["target_capital"] > 0),
    ("/api/portfolio/positions",
        lambda j: j["positions"] and j["positions"][0]["symbol"] == "SPY"),
    ("/api/portfolio/risk", lambda j: "available" in j),
    ("/api/portfolio/equity-curve", lambda j: "points" in j),
    ("/api/alerts", lambda j: len(j["alerts"]) == 1),
]


def test_concurrent_requests_return_consistent_shapes(client):
    def hit(i: int) -> None:
        path, check = CHECKS[i % len(CHECKS)]
        r = client.get(path)
        assert r.status_code == 200, f"{path}: HTTP {r.status_code}"
        assert check(r.json()), f"{path}: неконсистентный ответ под нагрузкой"

    with ThreadPoolExecutor(max_workers=20) as pool:
        # 8 полных проходов по всем эндпоинтам, вперемешку
        list(pool.map(hit, range(len(CHECKS) * 8)))
