"""Telegram-бот (aiogram): интерактив к JARVIS из чата.

Запускается отдельным процессом ТОЛЬКО при заданном TELEGRAM_BOT_TOKEN:
    .venv/bin/python -m app.alerts.bot

Команды:
    /digest — утренний дайджест сейчас
    /port   — сводка портфеля
    /fire   — прогресс к точке безубыточности
Бот отвечает только своему владельцу (TELEGRAM_CHAT_ID) — чужие сообщения игнорирует.
"""
from __future__ import annotations

import asyncio
import logging

from app import config


async def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN не задан в .env — боту нечем авторизоваться")

    from aiogram import Bot, Dispatcher
    from aiogram.filters import Command
    from aiogram.types import Message

    from app.alerts import engine
    from app.analytics import fire, portfolio
    from app.profile import store as profile_store

    bot = Bot(config.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    owner = str(config.TELEGRAM_CHAT_ID)

    def is_owner(m: Message) -> bool:
        return owner != "" and str(m.chat.id) == owner

    @dp.message(Command("digest"))
    async def cmd_digest(m: Message) -> None:
        if not is_owner(m):
            return
        await m.answer(engine.morning_digest())

    @dp.message(Command("port"))
    async def cmd_port(m: Message) -> None:
        if not is_owner(m):
            return
        p = portfolio.positions_valued()
        t = p["totals"]
        lines = [f"💼 Портфель: ${t['value_usd']:,.0f} ({t['pnl_pct']:+.1f}%)"]
        lines += [f"  {x['symbol']}: ${x['value_usd']:,.0f} ({x['pnl_pct']:+.1f}%)"
                  for x in p["positions"][:10]]
        await m.answer("\n".join(lines) if p["positions"] else "Портфель пуст")

    @dp.message(Command("fire"))
    async def cmd_fire(m: Message) -> None:
        if not is_owner(m):
            return
        prof = profile_store.load()
        p = portfolio.positions_valued()
        capital = prof["capital"]["investable_usd"] + p["totals"]["value_usd"]
        s = fire.summary(capital, prof["monthly_expenses"], prof["swr"],
                         prof["monthly_contribution_usd"])
        await m.answer(
            f"🎯 Свобода: {s['progress']:.1%}\n"
            f"Цель: ${s['target_capital']:,.0f}, капитал: ${capital:,.0f}\n"
            f"Пассивный доход: ${s['passive_income_monthly']:,.0f}/мес "
            f"из ${s['monthly_expenses']:,.0f} нужных")

    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
