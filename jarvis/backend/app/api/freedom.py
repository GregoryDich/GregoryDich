"""Экран Freedom (FIRE): точка финансовой безубыточности и сценарии пути.

Дисклеймер: все цифры — аналитика и прогнозы, не инвестиционный совет.
"""
from fastapi import APIRouter

from app.analytics import fire, portfolio
from app.profile import store as profile_store

router = APIRouter(prefix="/api/freedom", tags=["freedom"])

DISCLAIMER = ("Прогнозы и аналитика, не инвестиционный совет. "
              "Решения принимаете вы.")


@router.get("")
def freedom() -> dict:
    prof = profile_store.load()
    port = portfolio.positions_valued()
    # капитал = инвестируемый кэш из профиля + текущая стоимость портфеля
    capital = prof["capital"]["investable_usd"] + port["totals"]["value_usd"]
    s = fire.summary(capital, prof["monthly_expenses"], prof["swr"],
                     prof["monthly_contribution_usd"])
    s["portfolio_value_usd"] = port["totals"]["value_usd"]
    s["cash_usd"] = prof["capital"]["cash_usd"]
    s["cash_ils"] = prof["capital"]["cash_ils"]
    s["usd_ils"] = port["totals"].get("usd_ils")
    s["onboarded"] = prof["onboarded"]
    s["name"] = prof.get("name", "")
    s["disclaimer"] = DISCLAIMER
    return s
