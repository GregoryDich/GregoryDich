"""Профиль и онбординг-мастер."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.profile import store

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    # произвольное подмножество полей профиля; глубокое слияние на сервере
    model_config = {"extra": "allow"}


@router.get("")
def get_profile() -> dict:
    return store.load()


@router.get("/onboarding")
def onboarding_questions() -> dict:
    return {"questions": store.ONBOARDING_QUESTIONS}


@router.post("")
def save_profile(update: ProfileUpdate) -> dict:
    return store.save(update.model_dump())
