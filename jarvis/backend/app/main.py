"""JARVIS backend: FastAPI + APScheduler. Точка входа: uvicorn app.main:app"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.api import (ai_api, alerts_api, calendar_api, freedom, macro, markets,
                     narratives_api, navigator_api, portfolio_api, profile_api,
                     screener_api)
from app.services import market_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("jarvis")

scheduler = None


def _start_scheduler() -> None:
    global scheduler
    from apscheduler.schedulers.background import BackgroundScheduler

    from app.alerts import engine

    scheduler = BackgroundScheduler(timezone=config.TIMEZONE)
    scheduler.add_job(market_data.refresh_all_quotes, "interval",
                      minutes=config.REFRESH_MINUTES, id="refresh_quotes")
    scheduler.add_job(engine.check_alerts, "interval",
                      minutes=config.REFRESH_MINUTES, id="check_alerts")
    scheduler.add_job(market_data.refresh_macro, "cron", hour=6, minute=45,
                      id="refresh_macro")
    scheduler.add_job(engine.morning_digest, "cron",
                      hour=config.DIGEST_HOUR, minute=config.DIGEST_MINUTE,
                      id="morning_digest")
    from app.alerts import notify
    scheduler.add_job(notify.ping_watchdog, "interval",
                      minutes=config.REFRESH_MINUTES, id="watchdog")
    scheduler.start()
    log.info("Scheduler started: refresh every %s min, digest %02d:%02d %s",
             config.REFRESH_MINUTES, config.DIGEST_HOUR, config.DIGEST_MINUTE,
             config.TIMEZONE)


@asynccontextmanager
async def lifespan(_: FastAPI):
    market_data.ensure_data()  # каждый экран должен рисоваться сразу (демо-фолбэк)
    _start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="JARVIS — персональный экономический менеджер",
              lifespan=lifespan)


@app.middleware("http")
async def basic_auth(request, call_next):
    """Пароль обязателен, если задан JARVIS_PASSWORD (для VPS/AWS-деплоя)."""
    if config.JARVIS_PASSWORD:
        import base64

        header = request.headers.get("authorization", "")
        ok = False
        if header.startswith("Basic "):
            try:
                _, _, pw = base64.b64decode(header[6:]).decode().partition(":")
                ok = pw == config.JARVIS_PASSWORD
            except Exception:
                ok = False
        elif header == f"Bearer {config.JARVIS_PASSWORD}":
            ok = True
        if not ok:
            from starlette.responses import Response

            return Response(status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="JARVIS"'})
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)

for r in (markets.router, macro.router, portfolio_api.router,
          freedom.router, profile_api.router, alerts_api.router,
          navigator_api.router, screener_api.router, calendar_api.router,
          ai_api.router, narratives_api.router):
    app.include_router(r)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "data": market_data.data_status()}


@app.get("/api/health/data")
def health_data() -> dict:
    return market_data.data_health()


# Прод-режим: собранный фронтенд раздаётся тем же процессом
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="ui")
