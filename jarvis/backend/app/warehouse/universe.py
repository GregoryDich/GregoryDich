"""Вселенная инструментов MVP: метаданные + базовые уровни для демо-генератора.

Тикеры в нотации Yahoo Finance. base — правдоподобный уровень цены для
детерминированного демо-режима (данные явно помечаются source='demo').
"""

UNIVERSE: dict[str, dict] = {
    # Индексы
    "^GSPC":     {"name": "S&P 500",            "asset_class": "index", "currency": "USD", "country": "US", "sector": "", "base": 6900, "vol": 0.011},
    "^NDX":      {"name": "Nasdaq 100",          "asset_class": "index", "currency": "USD", "country": "US", "sector": "", "base": 25400, "vol": 0.014},
    "^DJI":      {"name": "Dow Jones",           "asset_class": "index", "currency": "USD", "country": "US", "sector": "", "base": 49300, "vol": 0.010},
    "^VIX":      {"name": "VIX",                 "asset_class": "index", "currency": "USD", "country": "US", "sector": "", "base": 15.5, "vol": 0.06, "mean_revert": True},
    "^TA125.TA": {"name": "TA-125 (Тель-Авив)",  "asset_class": "index", "currency": "ILS", "country": "IL", "sector": "", "base": 3050, "vol": 0.010},
    # Валюты
    "ILS=X":     {"name": "USD/ILS",             "asset_class": "fx", "currency": "ILS", "country": "IL", "sector": "", "base": 3.32, "vol": 0.004},
    "EURUSD=X":  {"name": "EUR/USD",             "asset_class": "fx", "currency": "USD", "country": "EU", "sector": "", "base": 1.12, "vol": 0.004},
    # Крипто
    "BTC-USD":   {"name": "Bitcoin",             "asset_class": "crypto", "currency": "USD", "country": "", "sector": "", "base": 126000, "vol": 0.03},
    "ETH-USD":   {"name": "Ethereum",            "asset_class": "crypto", "currency": "USD", "country": "", "sector": "", "base": 4400, "vol": 0.038},
    # Товары
    "GC=F":      {"name": "Золото",              "asset_class": "commodity", "currency": "USD", "country": "", "sector": "", "base": 3350, "vol": 0.009},
    "CL=F":      {"name": "Нефть WTI",           "asset_class": "commodity", "currency": "USD", "country": "", "sector": "", "base": 71, "vol": 0.02},
    # ETF
    "SPY":       {"name": "SPDR S&P 500 ETF",    "asset_class": "etf", "currency": "USD", "country": "US", "sector": "", "base": 688, "vol": 0.011},
    "QQQ":       {"name": "Invesco QQQ",         "asset_class": "etf", "currency": "USD", "country": "US", "sector": "", "base": 618, "vol": 0.014},
    "VT":        {"name": "Vanguard Total World","asset_class": "etf", "currency": "USD", "country": "", "sector": "", "base": 135, "vol": 0.009},
    # Акции США
    "AAPL":      {"name": "Apple",               "asset_class": "equity", "currency": "USD", "country": "US", "sector": "Technology", "base": 270, "vol": 0.016},
    "MSFT":      {"name": "Microsoft",           "asset_class": "equity", "currency": "USD", "country": "US", "sector": "Technology", "base": 530, "vol": 0.015},
    "NVDA":      {"name": "NVIDIA",              "asset_class": "equity", "currency": "USD", "country": "US", "sector": "Technology", "base": 185, "vol": 0.028},
    "GOOGL":     {"name": "Alphabet",            "asset_class": "equity", "currency": "USD", "country": "US", "sector": "Communication", "base": 215, "vol": 0.017},
    "AMZN":      {"name": "Amazon",              "asset_class": "equity", "currency": "USD", "country": "US", "sector": "Consumer Cyclical", "base": 245, "vol": 0.018},
    "META":      {"name": "Meta Platforms",      "asset_class": "equity", "currency": "USD", "country": "US", "sector": "Communication", "base": 740, "vol": 0.02},
    "TSLA":      {"name": "Tesla",               "asset_class": "equity", "currency": "USD", "country": "US", "sector": "Consumer Cyclical", "base": 340, "vol": 0.034},
    # Израильские дуал-листинги (NASDAQ/NYSE)
    "TEVA":      {"name": "Teva Pharmaceutical", "asset_class": "equity", "currency": "USD", "country": "IL", "sector": "Healthcare", "base": 24, "vol": 0.02},
    "CHKP":      {"name": "Check Point",         "asset_class": "equity", "currency": "USD", "country": "IL", "sector": "Technology", "base": 235, "vol": 0.015},
    "NICE":      {"name": "NICE Ltd",            "asset_class": "equity", "currency": "USD", "country": "IL", "sector": "Technology", "base": 175, "vol": 0.018},
    "WIX":       {"name": "Wix.com",             "asset_class": "equity", "currency": "USD", "country": "IL", "sector": "Technology", "base": 190, "vol": 0.024},
    "MNDY":      {"name": "monday.com",          "asset_class": "equity", "currency": "USD", "country": "IL", "sector": "Technology", "base": 310, "vol": 0.028},
}

DEFAULT_WATCHLIST = ["SPY", "QQQ", "AAPL", "NVDA", "TEVA", "CHKP", "BTC-USD", "ILS=X"]

# Обзор рынков: порядок групп на экране WEI
MARKET_GROUPS: list[tuple[str, list[str]]] = [
    ("Индексы", ["^GSPC", "^NDX", "^DJI", "^VIX", "^TA125.TA"]),
    ("Валюты", ["ILS=X", "EURUSD=X"]),
    ("Крипто", ["BTC-USD", "ETH-USD"]),
    ("Товары", ["GC=F", "CL=F"]),
]

# Макро-серии MVP: id -> (title, unit, country, source, demo-параметры)
MACRO_SERIES: dict[str, dict] = {
    "FRED:DGS10":    {"title": "US 10Y Treasury Yield", "unit": "%", "country": "US", "fred": "DGS10", "base": 4.1, "vol": 0.03, "clip": (0.2, 9)},
    "FRED:DGS2":     {"title": "US 2Y Treasury Yield",  "unit": "%", "country": "US", "fred": "DGS2", "base": 3.7, "vol": 0.03, "clip": (0.1, 9)},
    "FRED:FEDFUNDS": {"title": "Fed Funds Rate",        "unit": "%", "country": "US", "fred": "FEDFUNDS", "base": 3.75, "vol": 0.01, "step": True, "clip": (0, 9)},
    "FRED:UNRATE":   {"title": "US Unemployment",       "unit": "%", "country": "US", "fred": "UNRATE", "base": 4.3, "vol": 0.02, "monthly": True, "clip": (2, 12)},
    "FRED:CPIYOY":   {"title": "US CPI YoY",            "unit": "%", "country": "US", "fred": "CPIAUCSL", "base": 2.6, "vol": 0.05, "monthly": True, "clip": (-1, 10), "transform": "yoy"},
    "BOI:POLICY":    {"title": "Ставка Банка Израиля",  "unit": "%", "country": "IL", "base": 3.75, "vol": 0.01, "step": True, "clip": (0, 8)},
    "BOI:USDILS":    {"title": "USD/ILS (представит.)", "unit": "ILS", "country": "IL", "base": 3.32, "vol": 0.004, "clip": (2.6, 4.6)},
    "IL:CPIYOY":     {"title": "Израиль CPI YoY",       "unit": "%", "country": "IL", "base": 2.9, "vol": 0.05, "monthly": True, "clip": (-1, 8)},
}
