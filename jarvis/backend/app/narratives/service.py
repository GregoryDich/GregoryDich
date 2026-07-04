"""News & Narratives: интенсивность нарративов + «заразность» (R₀).

Уникальная фича JARVIS: к каждому нарративу считается эпидемический R₀-прокси
по методу из исследовательского проекта пользователя (narrative-economics,
growth.exp_growth_r0 — R₀ из скорости экспоненциального взлёта внимания).

Live-источник — GDELT DOC 2.0 (timelinevol); в песочнице/оффлайне —
детерминированные демо-серии с честной пометкой source='demo'.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import sys
from pathlib import Path

import numpy as np

# Темы: заголовок + GDELT-запрос (для live-режима)
THEMES: dict[str, dict] = {
    "ai_jobs": {
        "title": "ИИ и занятость",
        "query": '("AI will take" OR "AI replacing" OR "AI job losses") (jobs OR layoffs)',
        "burst_days": [40, 140, 260], "base": 0.08,
    },
    "recession": {
        "title": "Рецессия США",
        "query": '(recession OR "hard landing") (economy OR Fed)',
        "burst_days": [90, 300], "base": 0.12,
    },
    "rates": {
        "title": "Ставки ЦБ",
        "query": '("interest rates" OR "rate cut" OR "rate hike") (Fed OR ECB)',
        "burst_days": [30, 120, 210, 330], "base": 0.15,
    },
    "israel_econ": {
        "title": "Экономика Израиля",
        "query": '(Israel) (economy OR shekel OR "Bank of Israel" OR tech)',
        "burst_days": [70, 200], "base": 0.05,
    },
    "crypto": {
        "title": "Крипто-нарратив",
        "query": '(bitcoin OR crypto) (rally OR crash OR ETF OR halving)',
        "burst_days": [55, 180, 310], "base": 0.10,
    },
}

DEMO_DAYS = 365
_REPO_ROOT = Path(__file__).resolve().parents[3].parent  # .../GregoryDich
_NARR_CODE = _REPO_ROOT / "narrative-economics" / "code"


def _load_research_module(name: str):
    """Импорт модуля из narrative-economics/code без установки пакета."""
    path = _NARR_CODE / f"{name}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"narrative_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"narrative_{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


def _seed_for(name: str) -> int:
    return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)


def demo_series(theme_key: str) -> tuple[list[str], list[float]]:
    """Демо-интенсивность: базовый уровень + эпидемические всплески с затуханием."""
    cfg = THEMES[theme_key]
    rng = np.random.RandomState(_seed_for(theme_key))
    n = DEMO_DAYS
    base = cfg["base"]
    series = base * (1 + 0.15 * rng.standard_normal(n)).clip(0.3)
    for burst_day in cfg["burst_days"]:
        magnitude = base * rng.uniform(2.5, 5.0)
        growth_len = rng.randint(5, 12)
        for i in range(n - burst_day):
            day = burst_day + i
            if i < growth_len:                    # экспоненциальный взлёт
                series[day] += magnitude * (i + 1) / growth_len
            else:                                  # затухание
                series[day] += magnitude * np.exp(-(i - growth_len) / 12)
    today = dt.date.today()
    dates = [(today - dt.timedelta(days=n - 1 - i)).isoformat() for i in range(n)]
    return dates, [round(float(v), 4) for v in series]


def live_series(theme_key: str) -> tuple[list[str], list[float]]:
    """GDELT timelinevol через клиент исследовательского проекта."""
    gdelt = _load_research_module("gdelt_client")
    if gdelt is None:
        raise RuntimeError("narrative-economics/code недоступен")
    dates, intensity = gdelt.fetch_timeline(THEMES[theme_key]["query"], timespan="12m")
    return [d[:10] for d in dates], intensity


def r0_proxy(values: list[float]) -> dict:
    """R₀ нарратива из скорости взлёта (growth.exp_growth_r0 из исследования)."""
    growth = _load_research_module("growth")
    weekly = [float(np.sum(values[i:i + 7])) for i in range(0, len(values) - 6, 7)]
    weeks = list(range(len(weekly)))
    if growth is None or len(weekly) < 10:
        return {"r0": None, "note": "недостаточно данных"}
    try:
        r0, r_day, window_start = growth.exp_growth_r0(weeks, weekly)
        return {"r0": round(float(r0), 2), "r_per_day": round(float(r_day), 4),
                "takeoff_week": int(window_start)}
    except Exception as e:
        return {"r0": None, "note": str(e)[:80]}


def attention_spike(values: list[float], window: int = 30) -> dict:
    """Насколько текущее внимание к теме аномально: z-score к скользящему фону."""
    arr = np.asarray(values, dtype=float)
    if len(arr) < window + 7:
        return {"z": 0.0, "level": "н/д"}
    recent = arr[-7:].mean()
    bg = arr[-window - 7:-7]
    z = float((recent - bg.mean()) / (bg.std(ddof=1) + 1e-9))
    level = "🔥 всплеск" if z > 2 else ("повышенное" if z > 1 else "фон")
    return {"z": round(z, 2), "level": level}


def overview() -> dict:
    """Все темы: серия, R₀, всплеск, источник."""
    out = []
    for key, cfg in THEMES.items():
        source = "demo"
        try:
            dates, values = live_series(key)
            source = "gdelt"
        except Exception:
            dates, values = demo_series(key)
        out.append({
            "key": key, "title": cfg["title"], "source": source,
            "dates": dates, "values": values,
            "r0": r0_proxy(values),
            "spike": attention_spike(values),
            "query": cfg["query"],
        })
    out.sort(key=lambda t: -(t["spike"]["z"] or 0))
    return {"themes": out,
            "method": ("R₀ — эпидемический прокси «заразности» нарратива из скорости "
                       "его взлёта (метод исследования narrative-economics); "
                       "R₀>1 — история распространяется сама.")}
