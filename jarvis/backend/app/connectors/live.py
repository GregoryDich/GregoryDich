"""Live-коннекторы бесплатных источников. Каждый возвращает pandas и бросает
исключение при недоступности — фолбэк-цепочку решает services.market_data.

Источники: Yahoo (yfinance), Stooq CSV, FRED (fredgraph.csv без ключа / API с ключом),
Bank of Israel SDMX, Frankfurter FX, CoinGecko.
"""
from __future__ import annotations

import io

import pandas as pd

from app import config
from app.connectors.http import get


# --- Yahoo (yfinance) -------------------------------------------------------

def yahoo_history(symbol: str, period: str = "2y") -> pd.DataFrame:
    import yfinance as yf  # импорт внутри: тяжёлый и не нужен в демо-режиме

    df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
    if df.empty:
        raise RuntimeError(f"yahoo: empty history for {symbol}")
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["Date"]).dt.date
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                              "Close": "close", "Volume": "volume"})[
        ["date", "open", "high", "low", "close", "volume"]]


def yahoo_dividends(symbol: str, period: str = "2y") -> pd.DataFrame:
    """Дивиденды на одну бумагу: DataFrame(date, amount). Пустой — если не платит."""
    import yfinance as yf

    s = yf.Ticker(symbol).history(period=period, interval="1d", actions=True)
    if s.empty or "Dividends" not in s.columns:
        return pd.DataFrame(columns=["date", "amount"])
    div = s[s["Dividends"] > 0]["Dividends"].reset_index()
    return pd.DataFrame({"date": pd.to_datetime(div["Date"]).dt.date,
                         "amount": div["Dividends"].astype(float)})


# --- Stooq (фолбэк, CSV без ключа) -----------------------------------------

def _stooq_symbol(symbol: str) -> str:
    s = symbol.lower()
    mapping = {"^gspc": "^spx", "^ndx": "^ndx", "^dji": "^dji", "ils=x": "usdils", "eurusd=x": "eurusd"}
    if s in mapping:
        return mapping[s]
    if s.endswith(".ta") or s.startswith("^") or "=" in s or "-" in s:
        return s.replace("=x", "").replace("-", "")
    return f"{s}.us"  # американские акции/ETF


def stooq_history(symbol: str) -> pd.DataFrame:
    url = f"https://stooq.com/q/d/l/?s={_stooq_symbol(symbol)}&i=d"
    r = get(url)
    df = pd.read_csv(io.StringIO(r.text))
    if df.empty or "Close" not in df.columns:
        raise RuntimeError(f"stooq: no data for {symbol}")
    df.columns = [c.lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df[["date", "open", "high", "low", "close", "volume"]]


# --- FRED -------------------------------------------------------------------

def fred_series(fred_id: str) -> pd.DataFrame:
    """Без ключа: публичный fredgraph.csv. С ключом: официальный API."""
    if config.FRED_API_KEY:
        url = ("https://api.stlouisfed.org/fred/series/observations"
               f"?series_id={fred_id}&api_key={config.FRED_API_KEY}&file_type=json")
        obs = get(url).json()["observations"]
        df = pd.DataFrame(obs)[["date", "value"]]
    else:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_id}"
        df = pd.read_csv(io.StringIO(get(url).text))
        df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


def fred_yoy(fred_id: str) -> pd.DataFrame:
    """YoY-процент из уровня (для CPI): value_t / value_{t-12m} - 1."""
    df = fred_series(fred_id).set_index("date")
    df.index = pd.to_datetime(df.index)
    yoy = (df["value"].pct_change(12) * 100).dropna()
    return pd.DataFrame({"date": yoy.index.date, "value": yoy.values})


# --- Bank of Israel (SDMX) ---------------------------------------------------

BOI_BASE = "https://edge.boi.gov.il/FusionEdgeServer/sdmx/v2/data/dataflow/BOI.STATISTICS"


def boi_usdils(last_n: int = 750) -> pd.DataFrame:
    """Представительный курс USD/ILS Банка Израиля (без ключа)."""
    url = (f"{BOI_BASE}/EXR/1.0/RER_USD_ILS?lastNObservations={last_n}"
           "&format=csv")
    df = pd.read_csv(io.StringIO(get(url).text))
    cols = {c.lower(): c for c in df.columns}
    date_col = cols.get("time_period") or cols.get("date")
    val_col = cols.get("obs_value") or cols.get("value")
    if not date_col or not val_col:
        raise RuntimeError("boi: unexpected CSV columns")
    out = pd.DataFrame({"date": pd.to_datetime(df[date_col]).dt.date,
                        "value": pd.to_numeric(df[val_col], errors="coerce")})
    return out.dropna()


# --- Frankfurter (FX, без ключа) ---------------------------------------------

def frankfurter_latest(base: str = "USD", symbols: str = "ILS,EUR") -> dict:
    return get(f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={symbols}").json()


# --- CoinGecko ----------------------------------------------------------------

def coingecko_simple(ids: str = "bitcoin,ethereum") -> dict:
    url = ("https://api.coingecko.com/api/v3/simple/price"
           f"?ids={ids}&vs_currencies=usd&include_24hr_change=true")
    return get(url).json()
