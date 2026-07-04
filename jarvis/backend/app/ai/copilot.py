"""AI Copilot: чат над собственными данными терминала.

С ANTHROPIC_API_KEY — настоящий агент (Claude + tool-use над DuckDB).
Без ключа — честный фолбэк: несколько встроенных интентов + инструкция,
как включить полный режим. Портфельные данные не покидают машину без
явно заданного ключа.
"""
from __future__ import annotations

import json
import re

from app import config
from app.analytics import fire, portfolio
from app.profile import store as profile_store
from app.warehouse import db

MODEL = __import__("os").getenv("JARVIS_LLM_MODEL", "claude-sonnet-5")

SQL_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|create|drop|alter|attach|copy|pragma|install|load|export)\b",
    re.IGNORECASE)

SYSTEM = """Ты — JARVIS, персональный экономический менеджер одного пользователя.
Отвечай кратко и по-русски. У тебя есть инструменты над локальной DuckDB
(таблицы: securities, prices_eod, quotes_latest, macro_series,
macro_observations, trades, dividends, fundamentals, alerts, forecasts).
Все суммы в USD, если не указано иное. Данные могут быть демо — источник
указан в колонках source. Любые прогнозы сопровождай напоминанием, что
это аналитика, а не инвестиционный совет."""

TOOLS = [
    {"name": "run_sql",
     "description": "Выполнить ОДИН SELECT-запрос к локальной DuckDB терминала.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "SELECT ... (только чтение)"}},
         "required": ["query"]}},
    {"name": "get_positions",
     "description": "Текущие позиции портфеля с P&L, дивидендами и весами.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_freedom",
     "description": "Прогресс к точке финансовой безубыточности (FIRE).",
     "input_schema": {"type": "object", "properties": {}}},
]


def _safe_sql(query: str) -> str:
    q = query.strip().rstrip(";")
    if ";" in q or not q.lower().startswith("select") or SQL_FORBIDDEN.search(q):
        raise ValueError("Разрешён один SELECT-запрос без DML/DDL")
    return q


def _run_tool(name: str, args: dict) -> str:
    if name == "run_sql":
        df = db.fetchdf(_safe_sql(args["query"]))
        return df.head(50).to_json(orient="records", date_format="iso")
    if name == "get_positions":
        return json.dumps(portfolio.positions_valued(), default=str, ensure_ascii=False)
    if name == "get_freedom":
        prof = profile_store.load()
        capital = (prof["capital"]["investable_usd"]
                   + portfolio.positions_valued()["totals"]["value_usd"])
        return json.dumps(
            fire.summary(capital, prof["monthly_expenses"], prof["swr"],
                         prof["monthly_contribution_usd"],
                         inflation=prof.get("expected_inflation", 0.03)),
            default=str, ensure_ascii=False)
    return json.dumps({"error": f"unknown tool {name}"})


def chat_llm(message: str, history: list[dict] | None = None) -> str:
    """Полный режим: Claude с tool-use, до 8 шагов инструментов."""
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    messages = list(history or []) + [{"role": "user", "content": message}]
    for _ in range(8):
        resp = client.messages.create(
            model=MODEL, max_tokens=1500, system=SYSTEM,
            tools=TOOLS, messages=messages)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type == "tool_use":
                try:
                    out = _run_tool(block.name, block.input)
                except Exception as e:
                    out = json.dumps({"error": str(e)})
                results.append({"type": "tool_result",
                                "tool_use_id": block.id, "content": out[:20000]})
        messages.append({"role": "user", "content": results})
    return "Не уложился в лимит шагов инструментов — уточните вопрос."


def chat_fallback(message: str) -> str:
    """Без ключа: несколько встроенных интентов, чтобы экран был живым."""
    m = message.lower()
    if re.search(r"портфел|позици|p&l|пнл", m):
        p = portfolio.positions_valued()
        t = p["totals"]
        if not p["positions"]:
            return "Портфель пуст — добавьте сделки на экране PORT."
        lines = [f"Портфель: ${t['value_usd']:,.0f} ({t['pnl_pct']:+.1f}% total return, "
                 f"дивиденды ${t['dividends_usd']:,.0f})"]
        lines += [f"• {x['symbol']}: ${x['value_usd']:,.0f} ({x['pnl_pct']:+.1f}%)"
                  for x in p["positions"][:8]]
        return "\n".join(lines)
    if re.search(r"свобод|fire|цел|безубыт", m):
        prof = profile_store.load()
        capital = (prof["capital"]["investable_usd"]
                   + portfolio.positions_valued()["totals"]["value_usd"])
        s = fire.summary(capital, prof["monthly_expenses"], prof["swr"],
                         prof["monthly_contribution_usd"],
                         inflation=prof.get("expected_inflation", 0.03))
        return (f"Прогресс к свободе: {s['progress']:.1%}. Цель ${s['target_capital']:,.0f} "
                f"(в сегодняшних деньгах), пассивный доход ${s['passive_income_monthly']:,.0f}"
                f"/мес из ${s['monthly_expenses']:,.0f} нужных. "
                f"До цели ~{s['years_to_target_base']} лет при текущем взносе.")
    if re.search(r"рынк|рынок|котиров|индекс", m):
        rows = db.fetchall(
            """SELECT s.name, q.price, q.change_pct FROM quotes_latest q
               JOIN securities s USING(symbol)
               WHERE s.asset_class = 'index' LIMIT 6""")
        return "\n".join(f"• {n}: {p:,.2f} ({c:+.2f}%)" for n, p, c in rows)
    return ("Полный ИИ-режим не включён: задайте ANTHROPIC_API_KEY в jarvis/.env — "
            "тогда я смогу отвечать на произвольные вопросы, писать SQL к вашим "
            "данным и объяснять движения портфеля. Пока умею без ключа: "
            "«портфель», «свобода», «рынки».")


def chat(message: str, history: list[dict] | None = None) -> dict:
    if config.ANTHROPIC_API_KEY:
        try:
            return {"reply": chat_llm(message, history), "used_llm": True}
        except Exception as e:
            return {"reply": f"Ошибка LLM: {e}. Фолбэк:\n\n{chat_fallback(message)}",
                    "used_llm": False}
    return {"reply": chat_fallback(message), "used_llm": False}


def polish_digest(raw_text: str) -> str:
    """LLM-редактура утреннего дайджеста (если ключ есть), иначе — как есть."""
    if not config.ANTHROPIC_API_KEY:
        return raw_text
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=MODEL, max_tokens=800,
            system="Перепиши финансовый дайджест живым русским языком: 5-8 предложений, "
                   "сначала главное, без воды, сохрани все цифры точными.",
            messages=[{"role": "user", "content": raw_text}])
        return "".join(b.text for b in resp.content if b.type == "text") or raw_text
    except Exception:
        return raw_text
