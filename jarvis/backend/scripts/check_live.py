"""Проверка живых источников данных — запустить при первом старте на Mac:

    cd jarvis/backend && .venv/bin/python scripts/check_live.py

Показывает, какие бесплатные API доступны из этой сети и что вернули.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.connectors import live  # noqa: E402

CHECKS = [
    ("Yahoo (yfinance)  AAPL история", lambda: f"{len(live.yahoo_history('AAPL', '1mo'))} дней"),
    ("Yahoo дивиденды   SPY", lambda: f"{len(live.yahoo_dividends('SPY'))} выплат за 2г"),
    ("Yahoo TASE        ^TA125.TA", lambda: f"{len(live.yahoo_history('^TA125.TA', '1mo'))} дней"),
    ("Stooq (фолбэк)    AAPL", lambda: f"{len(live.stooq_history('AAPL'))} дней"),
    ("FRED              DGS10", lambda: f"{len(live.fred_series('DGS10'))} точек"),
    ("Банк Израиля      USD/ILS", lambda: f"{len(live.boi_usdils(30))} точек"),
    ("Frankfurter       USD→ILS,EUR", lambda: str(live.frankfurter_latest()["rates"])),
    ("CoinGecko         BTC,ETH", lambda: str(live.coingecko_simple())[:60]),
]


def main() -> int:
    failures = 0
    print("JARVIS: проверка живых источников\n" + "=" * 50)
    for name, fn in CHECKS:
        try:
            result = fn()
            print(f"  ✅ {name}: {result}")
        except Exception as e:
            failures += 1
            print(f"  ❌ {name}: {type(e).__name__}: {str(e)[:80]}")
    print("=" * 50)
    print("Все источники живы ✅" if failures == 0
          else f"Недоступно источников: {failures} — JARVIS будет использовать фолбэки/демо")
    return 1 if failures == len(CHECKS) else 0


if __name__ == "__main__":
    raise SystemExit(main())
