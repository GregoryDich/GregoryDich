"""Точка финансовой безубыточности (FIRE): правило изъятия 4% и сценарии пути.

Цель = годовые базовые расходы / SWR. Пассивный доход = капитал * SWR / 12.
Точка безубыточности достигнута, когда пассивный доход покрывает базовые расходы.
"""
from __future__ import annotations

MAX_YEARS = 100


def monthly_expenses_total(expenses: dict[str, float]) -> float:
    return float(sum(v or 0 for v in expenses.values()))


def fire_target(monthly_expenses: float, swr: float = 0.04) -> float:
    """Капитал, при котором изъятие swr в год покрывает расходы."""
    if swr <= 0:
        raise ValueError("SWR must be positive")
    return monthly_expenses * 12 / swr


def passive_income_monthly(capital: float, swr: float = 0.04) -> float:
    return capital * swr / 12


def progress(capital: float, monthly_expenses: float, swr: float = 0.04) -> float:
    """Доля пути к цели, 0..1+ (может быть >1, если цель уже пройдена)."""
    target = fire_target(monthly_expenses, swr)
    return capital / target if target > 0 else 0.0


def months_to_target(capital: float, monthly_contribution: float,
                     annual_return: float, target: float) -> int | None:
    """Месяцев до цели при ежемесячном взносе и годовой доходности.

    None — цель недостижима за MAX_YEARS (взнос и доходность слишком малы).
    """
    if capital >= target:
        return 0
    r = (1 + annual_return) ** (1 / 12) - 1
    value = capital
    for month in range(1, MAX_YEARS * 12 + 1):
        value = value * (1 + r) + monthly_contribution
        if value >= target:
            return month
    return None


def scenarios(capital: float, monthly_expenses: float, swr: float = 0.04,
              contributions: list[float] | None = None,
              returns: list[float] | None = None) -> list[dict]:
    """Сетка сценариев «взнос × доходность» → лет до точки безубыточности."""
    contributions = contributions or [250, 500, 1000, 2000]
    returns = returns or [0.04, 0.06, 0.08]
    target = fire_target(monthly_expenses, swr)
    rows = []
    for c in contributions:
        row = {"contribution": c, "years": {}}
        for r in returns:
            m = months_to_target(capital, c, r, target)
            row["years"][f"{r:.0%}"] = round(m / 12, 1) if m is not None else None
        rows.append(row)
    return rows


def summary(capital: float, expenses: dict[str, float], swr: float = 0.04,
            monthly_contribution: float = 500) -> dict:
    monthly = monthly_expenses_total(expenses)
    target = fire_target(monthly, swr) if monthly else 0.0
    months = (months_to_target(capital, monthly_contribution, 0.06, target)
              if monthly else None)
    return {
        "monthly_expenses": monthly,
        "expenses_breakdown": expenses,
        "swr": swr,
        "target_capital": target,
        "current_capital": capital,
        "progress": progress(capital, monthly, swr) if monthly else 0.0,
        "passive_income_monthly": passive_income_monthly(capital, swr),
        "gap_monthly": max(monthly - passive_income_monthly(capital, swr), 0.0),
        "years_to_target_base": round(months / 12, 1) if months is not None else None,
        "scenarios": scenarios(capital, monthly, swr) if monthly else [],
    }
