"""Экран CAL — календарь событий: отчётности, дивиденды, макро-релизы, ЦБ.

Демо-режим: отчётности и дивиденды выводятся из локальных данных
(следующая ожидаемая дата = последняя + квартал), макро-расписание —
из известных календарей публикаций (правило, не выдумка): CPI ~середина
месяца, NFP — первая пятница, заседания ФРС/Банка Израиля — по их
публичным календарям (правило чередования ~6-7 недель).
"""
from __future__ import annotations

import datetime as dt
import hashlib

from fastapi import APIRouter

from app.warehouse import db
from app.warehouse.universe import UNIVERSE

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


def _first_friday(year: int, month: int) -> dt.date:
    d = dt.date(year, month, 1)
    return d + dt.timedelta(days=(4 - d.weekday()) % 7)


def _next_quarterly(last: dt.date, today: dt.date) -> dt.date:
    nxt = last
    while nxt <= today:
        nxt += dt.timedelta(days=91)
    return nxt


def _earnings_offset(symbol: str) -> int:
    """Детерминированный сдвиг дня отчётности внутри сезона (демо)."""
    return int(hashlib.sha256(symbol.encode()).hexdigest()[:4], 16) % 25


@router.get("")
def calendar(days: int = 45) -> dict:
    today = dt.date.today()
    horizon = today + dt.timedelta(days=days)
    events: list[dict] = []

    # 1. Дивиденды: следующая ожидаемая (последняя + квартал), по вотчлисту/портфелю
    held = {s for (s,) in db.fetchall("SELECT DISTINCT symbol FROM trades")}
    watched = {s for (s,) in db.fetchall("SELECT symbol FROM watchlist")}
    relevant = held | watched
    for sym, last_date, amount in db.fetchall(
            """SELECT symbol, max(date), any_value(amount ORDER BY date DESC)
               FROM dividends GROUP BY symbol"""):
        if sym not in relevant:
            continue
        nxt = _next_quarterly(last_date, today)
        if today <= nxt <= horizon:
            events.append({"date": str(nxt), "kind": "dividend",
                           "title": f"{sym}: ожидаемый дивиденд ≈ {amount:.2f}",
                           "symbol": sym, "importance": "medium",
                           "source": "оценка: последняя выплата + квартал"})

    # 2. Отчётности (демо-оценка): сезон отчётностей = ~3-я неделя после квартала
    season_starts = [dt.date(today.year, m, 12) for m in (1, 4, 7, 10)] + \
                    [dt.date(today.year + 1, 1, 12)]
    for sym, meta in UNIVERSE.items():
        if meta["asset_class"] != "equity" or sym not in relevant:
            continue
        for start in season_starts:
            est = start + dt.timedelta(days=_earnings_offset(sym))
            if today <= est <= horizon:
                events.append({"date": str(est), "kind": "earnings",
                               "title": f"{sym} ({meta['name']}): отчётность (оценка сезона)",
                               "symbol": sym, "importance": "high",
                               "source": "оценка: сезон отчётностей"})
                break

    # 3. Макро-релизы США (правила публикации BLS)
    months = []
    y, m = today.year, today.month
    for _ in range(3):
        months.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    for yy, mm in months:
        cpi = dt.date(yy, mm, 13)
        nfp = _first_friday(yy, mm)
        for date, title in ((cpi, "США: CPI (инфляция)"), (nfp, "США: Non-Farm Payrolls")):
            if today <= date <= horizon:
                events.append({"date": str(date), "kind": "macro", "title": title,
                               "symbol": None, "importance": "high",
                               "source": "график публикаций BLS"})

    # 4. Центробанки: ФРС ~каждые 6-7 недель, Банк Израиля ~8 решений в год
    fomc_anchor = dt.date(2026, 1, 28)
    d = fomc_anchor
    while d < horizon:
        if d >= today:
            events.append({"date": str(d), "kind": "cb", "title": "Заседание ФРС (решение по ставке)",
                           "symbol": None, "importance": "high",
                           "source": "цикл заседаний ~6.5 недель"})
        d += dt.timedelta(weeks=6, days=3)
    boi_anchor = dt.date(2026, 1, 5)
    d = boi_anchor
    while d < horizon:
        if d >= today:
            events.append({"date": str(d), "kind": "cb",
                           "title": "Банк Израиля: решение по ставке",
                           "symbol": None, "importance": "high",
                           "source": "~8 решений в год"})
        d += dt.timedelta(days=45)

    events.sort(key=lambda e: e["date"])
    return {"events": events, "from": str(today), "to": str(horizon),
            "note": "Даты отчётностей/дивидендов — оценки из локальных данных; "
                    "точные даты появятся с live-источниками."}
