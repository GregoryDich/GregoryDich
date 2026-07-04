"""Точка финансовой безубыточности (FIRE): правило изъятия 4% и сценарии пути.

Цель = годовые базовые расходы / SWR — В СЕГОДНЯШНИХ ДЕНЬГАХ.
Чтобы цель в сегодняшних деньгах была честной, путь к ней считается на
РЕАЛЬНОЙ доходности: (1+номинал)/(1+инфляция) − 1. Взнос считается
постоянным в реальном выражении (номинально растёт с инфляцией) —
стандартная модель для планирования FIRE.
"""
from __future__ import annotations

MAX_YEARS = 100
DEFAULT_INFLATION = 0.03


def monthly_expenses_total(expenses: dict[str, float]) -> float:
    return float(sum(v or 0 for v in expenses.values()))


def fire_target(monthly_expenses: float, swr: float = 0.04) -> float:
    """Капитал (в сегодняшних деньгах), при котором изъятие swr в год покрывает расходы."""
    if swr <= 0:
        raise ValueError("SWR must be positive")
    return monthly_expenses * 12 / swr


def real_rate(nominal: float, inflation: float) -> float:
    """Реальная годовая доходность из номинальной (уравнение Фишера)."""
    return (1 + nominal) / (1 + inflation) - 1


def passive_income_monthly(capital: float, swr: float = 0.04) -> float:
    return capital * swr / 12


def progress(capital: float, monthly_expenses: float, swr: float = 0.04) -> float:
    """Доля пути к цели, 0..1+ (может быть >1, если цель уже пройдена)."""
    target = fire_target(monthly_expenses, swr)
    return capital / target if target > 0 else 0.0


def months_to_target(capital: float, monthly_contribution: float,
                     annual_return: float, target: float,
                     inflation: float = 0.0) -> int | None:
    """Месяцев до цели (в сегодняшних деньгах) при ежемесячном взносе.

    annual_return — НОМИНАЛЬНАЯ доходность; рост считается на реальной ставке,
    поэтому target не индексируется. None — цель недостижима за MAX_YEARS.
    """
    if capital >= target:
        return 0
    rr = real_rate(annual_return, inflation)
    r = (1 + rr) ** (1 / 12) - 1
    value = capital
    for month in range(1, MAX_YEARS * 12 + 1):
        value = value * (1 + r) + monthly_contribution
        if value >= target:
            return month
    return None


def scenarios(capital: float, monthly_expenses: float, swr: float = 0.04,
              contributions: list[float] | None = None,
              returns: list[float] | None = None,
              inflation: float = DEFAULT_INFLATION) -> list[dict]:
    """Сетка сценариев «взнос × номинальная доходность» → лет до точки
    безубыточности. Внутри — реальные ставки; колонки подписаны номиналом."""
    contributions = contributions or [250, 500, 1000, 2000]
    returns = returns or [0.04, 0.06, 0.08]
    target = fire_target(monthly_expenses, swr)
    rows = []
    for c in contributions:
        row = {"contribution": c, "years": {}}
        for r in returns:
            m = months_to_target(capital, c, r, target, inflation)
            row["years"][f"{r:.0%}"] = round(m / 12, 1) if m is not None else None
        rows.append(row)
    return rows


def summary(capital: float, expenses: dict[str, float], swr: float = 0.04,
            monthly_contribution: float = 500,
            inflation: float = DEFAULT_INFLATION) -> dict:
    monthly = monthly_expenses_total(expenses)
    target = fire_target(monthly, swr) if monthly else 0.0
    base_nominal = 0.06
    months = (months_to_target(capital, monthly_contribution, base_nominal,
                               target, inflation)
              if monthly else None)
    return {
        "monthly_expenses": monthly,
        "expenses_breakdown": expenses,
        "swr": swr,
        "inflation": inflation,
        "base_nominal_return": base_nominal,
        "base_real_return": real_rate(base_nominal, inflation),
        "target_capital": target,
        "current_capital": capital,
        "progress": progress(capital, monthly, swr) if monthly else 0.0,
        "passive_income_monthly": passive_income_monthly(capital, swr),
        "gap_monthly": max(monthly - passive_income_monthly(capital, swr), 0.0),
        "years_to_target_base": round(months / 12, 1) if months is not None else None,
        "scenarios": scenarios(capital, monthly, swr, inflation=inflation) if monthly else [],
    }
