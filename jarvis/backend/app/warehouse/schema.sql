-- Единое хранилище JARVIS (DuckDB). Security master + рынки + макро + портфель + алерты.

CREATE TABLE IF NOT EXISTS securities (
    symbol      VARCHAR PRIMARY KEY,   -- тикер в нотации Yahoo (AAPL, ILS=X, BTC-USD, ^GSPC)
    name        VARCHAR,
    asset_class VARCHAR,               -- equity | etf | index | fx | crypto | commodity | rate
    currency    VARCHAR,
    country     VARCHAR,
    sector      VARCHAR
);

CREATE TABLE IF NOT EXISTS prices_eod (
    symbol  VARCHAR,
    date    DATE,
    open    DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
    volume  DOUBLE,
    source  VARCHAR,                   -- yahoo | stooq | demo
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS quotes_latest (
    symbol     VARCHAR PRIMARY KEY,
    price      DOUBLE,
    change_pct DOUBLE,                 -- изменение к предыдущему закрытию, %
    ts         TIMESTAMP,
    source     VARCHAR                 -- live | delayed | demo
);

CREATE TABLE IF NOT EXISTS fx_rates (
    base   VARCHAR, quote VARCHAR, date DATE,
    rate   DOUBLE, source VARCHAR,
    PRIMARY KEY (base, quote, date)
);

CREATE TABLE IF NOT EXISTS macro_series (
    series_id VARCHAR PRIMARY KEY,     -- FRED:DGS10, BOI:POLICY_RATE, DBN:...
    title     VARCHAR,
    unit      VARCHAR,
    country   VARCHAR,
    source    VARCHAR
);

CREATE TABLE IF NOT EXISTS macro_observations (
    series_id VARCHAR, date DATE, value DOUBLE,
    PRIMARY KEY (series_id, date)
);

CREATE SEQUENCE IF NOT EXISTS trades_seq;
CREATE TABLE IF NOT EXISTS trades (
    id       INTEGER PRIMARY KEY DEFAULT nextval('trades_seq'),
    dt       DATE NOT NULL,
    symbol   VARCHAR NOT NULL,
    side     VARCHAR NOT NULL,         -- buy | sell
    qty      DOUBLE NOT NULL,
    price    DOUBLE NOT NULL,
    currency VARCHAR DEFAULT 'USD',
    fees     DOUBLE DEFAULT 0,
    note     VARCHAR
);

CREATE SEQUENCE IF NOT EXISTS alerts_seq;
CREATE TABLE IF NOT EXISTS alerts (
    id                INTEGER PRIMARY KEY DEFAULT nextval('alerts_seq'),
    symbol            VARCHAR NOT NULL,
    condition         VARCHAR NOT NULL, -- above | below
    level             DOUBLE NOT NULL,
    active            BOOLEAN DEFAULT TRUE,
    note              VARCHAR,
    created_at        TIMESTAMP DEFAULT current_timestamp,
    last_triggered_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dividends (
    symbol VARCHAR,
    date   DATE,
    amount DOUBLE,                     -- на одну бумагу, в валюте инструмента
    source VARCHAR,                    -- yahoo | demo
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol   VARCHAR PRIMARY KEY,
    added_at TIMESTAMP DEFAULT current_timestamp
);
