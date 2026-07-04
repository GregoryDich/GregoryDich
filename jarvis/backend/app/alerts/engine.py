"""Движок алертов и утренний дайджест. Вызывается APScheduler'ом из main.py."""
from __future__ import annotations

import datetime as dt
import logging

from app.alerts import notify
from app.analytics import fire, portfolio
from app.profile import store as profile_store
from app.warehouse import db
from app.warehouse.universe import MARKET_GROUPS, UNIVERSE

log = logging.getLogger("jarvis.alerts")


def check_alerts() -> list[dict]:
    """Проверить активные пороговые алерты по последним котировкам."""
    triggered = []
    rows = db.fetchall(
        """SELECT a.id, a.symbol, a.condition, a.level, q.price
           FROM alerts a JOIN quotes_latest q ON q.symbol = a.symbol
           WHERE a.active""")
    for alert_id, symbol, condition, level, price in rows:
        hit = (condition == "above" and price >= level) or \
              (condition == "below" and price <= level)
        if not hit:
            continue
        name = UNIVERSE.get(symbol, {}).get("name", symbol)
        title = f"🔔 {symbol}: {'выше' if condition == 'above' else 'ниже'} {level}"
        body = f"{name}: текущая цена {price:.2f} (порог {level})."
        notify.send(title, body)
        db.execute(
            "UPDATE alerts SET active=FALSE, last_triggered_at=current_timestamp WHERE id=?",
            [alert_id])
        triggered.append({"id": alert_id, "symbol": symbol, "price": price})
    return triggered


def _fmt_quote(symbol: str, price: float, change: float) -> str:
    name = UNIVERSE.get(symbol, {}).get("name", symbol)
    arrow = "▲" if change >= 0 else "▼"
    return f"{name}: {price:,.2f} {arrow}{abs(change):.2f}%"


def morning_digest() -> str:
    """Собрать и отправить утренний мини-дайджест (RU)."""
    lines = [f"☀️ JARVIS — утро {dt.date.today():%d.%m.%Y}", ""]
    for group, symbols in MARKET_GROUPS:
        rows = db.fetchall(
            f"""SELECT symbol, price, change_pct FROM quotes_latest
                WHERE symbol IN ({','.join('?' for _ in symbols)})""", symbols)
        if rows:
            lines.append(f"— {group}:")
            lines += ["  " + _fmt_quote(s, p, c or 0) for s, p, c in rows]
    p = portfolio.positions_valued()
    if p["positions"]:
        t = p["totals"]
        lines += ["", f"💼 Портфель: ${t['value_usd']:,.0f} "
                      f"({t['pnl_pct']:+.1f}% всего, ₪{t['value_ils']:,.0f})"]
    prof = profile_store.load()
    capital = prof["capital"]["investable_usd"] + p["totals"]["value_usd"]
    monthly = fire.monthly_expenses_total(prof["monthly_expenses"])
    if monthly:
        f = fire.summary(capital, prof["monthly_expenses"], prof["swr"],
                         prof["monthly_contribution_usd"])
        lines += ["", f"🎯 Свобода: {f['progress']:.1%} пути, пассивный доход "
                      f"${f['passive_income_monthly']:,.0f}/мес из ${monthly:,.0f} нужных"]
    text = "\n".join(lines)
    notify.send("JARVIS: утренний дайджест", text)
    return text
