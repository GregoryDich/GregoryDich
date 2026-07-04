"""Доставка уведомлений: Telegram + резервный ntfy одним вызовом (Apprise).

Резервный канал — осознанное требование: при потере Telegram-аккаунта
алерты продолжают приходить через ntfy-топик.
"""
from __future__ import annotations

import logging

from app import config

log = logging.getLogger("jarvis.notify")


def channels() -> list[str]:
    urls = []
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        urls.append(f"tgram://{config.TELEGRAM_BOT_TOKEN}/{config.TELEGRAM_CHAT_ID}")
    if config.NTFY_TOPIC:
        urls.append(f"ntfy://{config.NTFY_TOPIC}")
    return urls


def send(title: str, body: str) -> dict:
    """Возвращает {sent: bool, channels: n}. Без каналов — пишет в лог (dry-run)."""
    urls = channels()
    if not urls:
        log.info("[dry-run notify] %s — %s", title, body)
        return {"sent": False, "channels": 0, "dry_run": True}
    import apprise

    ap = apprise.Apprise()
    for u in urls:
        ap.add(u)
    ok = ap.notify(title=title, body=body)
    return {"sent": bool(ok), "channels": len(urls), "dry_run": False}
