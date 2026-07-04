"""Профиль пользователя: онбординг-вопросы, хранение в gitignored YAML.

Профиль определяет: страну, валюты, расходы (цель FIRE), доступные каналы
инвестиций и видимые экраны. Под капотом движок умеет больше — профиль
решает, что показывать этому человеку.
"""
from __future__ import annotations

import copy

import yaml

from app import config
from app.warehouse import db
from app.warehouse.universe import DEFAULT_WATCHLIST

DEFAULT_PROFILE: dict = {
    "onboarded": False,
    "name": "",
    "country": "IL",
    "base_currency": "USD",
    "local_currency": "ILS",
    "language": "ru",
    "monthly_expenses": {  # базовые нужды — из них считается точка безубыточности
        "rent": 0.0,
        "food": 0.0,
        "clothing": 0.0,
        "utilities_subscriptions": 0.0,  # связь, электричество, вода, подписки
        "daily_free": 0.0,               # небольшая часть свободных денег
    },
    "capital": {
        "investable_usd": 0.0,
        "cash_usd": 0.0,
        "cash_ils": 0.0,
    },
    "monthly_contribution_usd": 500.0,
    "swr": 0.04,
    "expected_inflation": 0.03,  # цель FIRE в сегодняшних деньгах → путь на реальной ставке
    "risk_profile": "balanced",   # conservative | balanced | aggressive
    "horizon_years": 10,
    "channels": [],               # доступные каналы: ibkr, tase, crypto, deposits, bonds
    "visible_screens": ["freedom", "markets", "portfolio", "macro", "alerts"],
}

# Онбординг: вопросы мастера первого запуска (фронтенд рендерит по этой схеме)
ONBOARDING_QUESTIONS: list[dict] = [
    {"id": "name", "type": "text", "title": "Как к вам обращаться?",
     "hint": "Имя используется только локально."},
    {"id": "country", "type": "select", "title": "Страна проживания",
     "options": [{"v": "IL", "label": "Израиль"}, {"v": "US", "label": "США"},
                 {"v": "EU", "label": "Евросоюз"}, {"v": "OTHER", "label": "Другая"}],
     "hint": "Определяет локальный рынок, валюту и налоговые допущения."},
    {"id": "monthly_expenses", "type": "expenses", "title": "Базовые расходы в месяц (USD)",
     "fields": [
         {"k": "rent", "label": "Аренда/жильё"},
         {"k": "food", "label": "Еда"},
         {"k": "clothing", "label": "Одежда"},
         {"k": "utilities_subscriptions", "label": "Связь, коммуналка, подписки"},
         {"k": "daily_free", "label": "Свободные ежедневные траты"},
     ],
     "hint": "Из этой суммы считается ваша точка финансовой безубыточности."},
    {"id": "capital", "type": "capital", "title": "Текущий капитал",
     "fields": [
         {"k": "investable_usd", "label": "Инвестируемый капитал, USD"},
         {"k": "cash_usd", "label": "Наличные/счета, USD"},
         {"k": "cash_ils", "label": "Наличные/счета, ILS"},
     ]},
    {"id": "monthly_contribution_usd", "type": "number",
     "title": "Сколько готовы откладывать в месяц (USD)?"},
    {"id": "expected_inflation_pct", "type": "number",
     "title": "Ожидаемая инфляция, % в год",
     "hint": "По умолчанию 3%. Цель считается в сегодняшних деньгах, "
             "доходность — за вычетом инфляции."},
    {"id": "channels", "type": "multiselect", "title": "Какие каналы инвестиций вам доступны?",
     "options": [
         {"v": "ibkr", "label": "Interactive Brokers (США/глобал)"},
         {"v": "tase", "label": "Израильский брокер / банк (TASE)"},
         {"v": "crypto", "label": "Криптобиржа"},
         {"v": "deposits", "label": "Депозиты / money market"},
         {"v": "bonds", "label": "Облигации"},
     ],
     "hint": "Навигатор аллокации будет считать транши только по доступным каналам."},
    {"id": "risk_profile", "type": "select", "title": "Отношение к риску",
     "options": [{"v": "conservative", "label": "Консервативное"},
                 {"v": "balanced", "label": "Сбалансированное"},
                 {"v": "aggressive", "label": "Агрессивное"}]},
    {"id": "horizon_years", "type": "number", "title": "Горизонт инвестирования, лет"},
]


def load() -> dict:
    if config.PROFILE_PATH.exists():
        data = yaml.safe_load(config.PROFILE_PATH.read_text()) or {}
        merged = copy.deepcopy(DEFAULT_PROFILE)
        _deep_update(merged, data)
        return merged
    return copy.deepcopy(DEFAULT_PROFILE)


def save(updates: dict) -> dict:
    profile = load()
    pct = updates.pop("expected_inflation_pct", None)  # ответ онбординга в процентах
    if pct is not None:
        updates["expected_inflation"] = float(pct) / 100
    _deep_update(profile, updates)
    profile["onboarded"] = True
    config.PROFILE_PATH.write_text(
        yaml.safe_dump(profile, allow_unicode=True, sort_keys=False))
    _ensure_watchlist()
    return profile


def _ensure_watchlist() -> None:
    (n,) = db.fetchall("SELECT count(*) FROM watchlist")[0]
    if n == 0:
        for sym in DEFAULT_WATCHLIST:
            db.execute("INSERT OR REPLACE INTO watchlist (symbol) VALUES (?)", [sym])


def _deep_update(dst: dict, src: dict) -> None:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v
