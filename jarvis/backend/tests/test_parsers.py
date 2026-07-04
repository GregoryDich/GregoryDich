"""Парсеры live-коннекторов на записанных фикстурах реальных форматов —
сеть не нужна, ломающиеся изменения формата ловятся тестом."""
import datetime as dt
import json
from pathlib import Path

import pytest

from app.connectors import live

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def json(self):
        return json.loads(self.text)


@pytest.fixture()
def fake_get(monkeypatch):
    """Подменяет live.get так, чтобы он отдавал файл-фикстуру."""
    def use(fixture_name: str):
        text = (FIXTURES / fixture_name).read_text()
        monkeypatch.setattr(live, "get", lambda url, **kw: FakeResponse(text))
    return use


def test_fred_parser_drops_missing(fake_get):
    fake_get("fred_dgs10.csv")
    df = live.fred_series("DGS10")
    # 4 строки в фикстуре, одна с '.' (нет данных) — выпадает
    assert len(df) == 3
    assert df.iloc[-1]["value"] == pytest.approx(4.31)
    assert df.iloc[0]["date"] == dt.date(2026, 6, 29)


def test_boi_parser_maps_sdmx_columns(fake_get):
    fake_get("boi_usdils.csv")
    df = live.boi_usdils()
    assert len(df) == 3
    assert df.iloc[-1]["value"] == pytest.approx(3.312)
    assert df.iloc[0]["date"] == dt.date(2026, 6, 30)


def test_stooq_parser_and_symbol_mapping(fake_get):
    fake_get("stooq_aapl.csv")
    df = live.stooq_history("AAPL")
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(df) == 3
    assert df.iloc[0]["close"] == pytest.approx(270.25)
    # маппинг тикеров Yahoo → Stooq
    assert live._stooq_symbol("AAPL") == "aapl.us"
    assert live._stooq_symbol("^GSPC") == "^spx"
    assert live._stooq_symbol("ILS=X") == "usdils"


def test_coingecko_parser(fake_get):
    fake_get("coingecko_simple.json")
    data = live.coingecko_simple()
    assert data["bitcoin"]["usd"] == 126000
    assert data["ethereum"]["usd_24h_change"] == pytest.approx(1.06)
