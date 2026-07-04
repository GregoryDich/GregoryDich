"""Позиции из сделок: метод средней стоимости, ручная сверка."""
import pandas as pd
import pytest

from app.analytics.portfolio import positions_from_trades


def _trades(rows):
    return pd.DataFrame(rows, columns=["dt", "symbol", "side", "qty", "price", "currency", "fees"])


def test_single_buy_with_fees():
    pos = positions_from_trades(_trades(
        [("2025-01-01", "AAPL", "buy", 10, 100.0, "USD", 10.0)]))
    row = pos.iloc[0]
    assert row.qty == 10
    assert row.cost_basis == pytest.approx(1010.0)
    assert row.avg_cost == pytest.approx(101.0)


def test_two_buys_average_cost():
    pos = positions_from_trades(_trades([
        ("2025-01-01", "AAPL", "buy", 10, 100.0, "USD", 0.0),
        ("2025-02-01", "AAPL", "buy", 10, 120.0, "USD", 0.0),
    ]))
    row = pos.iloc[0]
    assert row.qty == 20
    assert row.avg_cost == pytest.approx(110.0)


def test_sell_reduces_proportionally():
    pos = positions_from_trades(_trades([
        ("2025-01-01", "AAPL", "buy", 20, 110.0, "USD", 0.0),
        ("2025-03-01", "AAPL", "sell", 10, 150.0, "USD", 0.0),
    ]))
    row = pos.iloc[0]
    assert row.qty == 10
    assert row.cost_basis == pytest.approx(1100.0)  # половина базы 2200
    assert row.avg_cost == pytest.approx(110.0)     # средняя не меняется при продаже


def test_full_exit_drops_position():
    pos = positions_from_trades(_trades([
        ("2025-01-01", "TSLA", "buy", 5, 300.0, "USD", 0.0),
        ("2025-04-01", "TSLA", "sell", 5, 350.0, "USD", 0.0),
    ]))
    assert pos.empty
