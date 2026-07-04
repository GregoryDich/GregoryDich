"""Дивиденды и реализованный P&L: ручные сверки на контролируемых данных."""
import pandas as pd
import pytest

from app.analytics import portfolio
from app.warehouse import db


def _trades(rows):
    return pd.DataFrame(rows, columns=["dt", "symbol", "side", "qty", "price", "currency", "fees"])


def test_realized_pnl_partial_sell():
    # купил 10 @ 100, продал 5 @ 120 → реализовано 5*(120-100) = 100
    df = portfolio.realized_pnl(_trades([
        ("2025-01-01", "AAPL", "buy", 10, 100.0, "USD", 0.0),
        ("2025-06-01", "AAPL", "sell", 5, 120.0, "USD", 0.0),
    ]))
    assert len(df) == 1
    assert df.iloc[0].pnl == pytest.approx(100.0)
    assert df.iloc[0].cost == pytest.approx(500.0)


def test_realized_pnl_fees_reduce_both_sides():
    # комиссия покупки входит в базу, комиссия продажи режет выручку
    df = portfolio.realized_pnl(_trades([
        ("2025-01-01", "AAPL", "buy", 10, 100.0, "USD", 10.0),
        ("2025-06-01", "AAPL", "sell", 10, 120.0, "USD", 5.0),
    ]))
    # база 1010, выручка 1195 → pnl 185
    assert df.iloc[0].pnl == pytest.approx(185.0)


def test_dividends_received_by_holding_date(fresh_db):
    db.execute("INSERT INTO dividends VALUES ('AAPL', DATE '2025-02-01', 1.0, 'demo')")
    db.execute("INSERT INTO dividends VALUES ('AAPL', DATE '2024-12-01', 1.0, 'demo')")
    db.execute(
        "INSERT INTO trades (dt, symbol, side, qty, price, currency, fees) "
        "VALUES (DATE '2025-01-01', 'AAPL', 'buy', 10, 100, 'USD', 0)")
    got = portfolio.dividends_received(portfolio.load_trades())
    # декабрьский дивиденд — до покупки, не наш; февральский: 10 бумаг × 1.0
    assert got == {"AAPL": pytest.approx(10.0)}


def test_daily_returns_include_dividend(fresh_db):
    # два дня, цена не меняется, во второй день дивиденд 1.0 на бумагу
    for d, c in (("2025-03-03", 100.0), ("2025-03-04", 100.0)):
        db.execute(
            "INSERT INTO prices_eod VALUES ('XDIV', ?, ?, ?, ?, ?, 0, 'demo')",
            [d, c, c, c, c])
    db.execute("INSERT INTO dividends VALUES ('XDIV', DATE '2025-03-04', 1.0, 'demo')")
    db.execute(
        "INSERT INTO trades (dt, symbol, side, qty, price, currency, fees) "
        "VALUES (DATE '2025-03-03', 'XDIV', 'buy', 10, 100, 'USD', 0)")
    r = portfolio.portfolio_daily_returns()
    # (1000 + 10 - 1000) / 1000 = 1%
    assert len(r) == 1
    assert float(r.iloc[0]) == pytest.approx(0.01)


def test_positions_valued_includes_dividends(fresh_db):
    db.execute(
        "INSERT INTO prices_eod VALUES ('XDIV', DATE '2025-03-03', 100, 100, 100, 100, 0, 'demo')")
    db.execute(
        "INSERT OR REPLACE INTO quotes_latest VALUES ('XDIV', 100.0, 0.0, current_timestamp, 'demo')")
    db.execute("INSERT INTO dividends VALUES ('XDIV', DATE '2025-03-04', 1.0, 'demo')")
    db.execute(
        "INSERT INTO trades (dt, symbol, side, qty, price, currency, fees) "
        "VALUES (DATE '2025-03-03', 'XDIV', 'buy', 10, 100, 'USD', 0)")
    res = portfolio.positions_valued()
    p = res["positions"][0]
    # цена не изменилась, но P&L положителен на сумму дивидендов
    assert p["dividends_usd"] == pytest.approx(10.0)
    assert p["pnl_usd"] == pytest.approx(10.0)
    assert res["totals"]["dividends_usd"] == pytest.approx(10.0)
