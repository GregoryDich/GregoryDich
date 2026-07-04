"""Экран AI — копайлот над данными терминала."""
from fastapi import APIRouter
from pydantic import BaseModel

from app import config
from app.ai import copilot

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


@router.get("/status")
def status() -> dict:
    return {"llm_enabled": bool(config.ANTHROPIC_API_KEY),
            "model": copilot.MODEL if config.ANTHROPIC_API_KEY else None}


@router.post("/chat")
def chat(body: ChatIn) -> dict:
    return copilot.chat(body.message, body.history or None)
