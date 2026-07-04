"""Экран NEWS — нарративы и внимание."""
from fastapi import APIRouter

from app.narratives import service

router = APIRouter(prefix="/api/narratives", tags=["narratives"])


@router.get("")
def narratives() -> dict:
    return service.overview()
