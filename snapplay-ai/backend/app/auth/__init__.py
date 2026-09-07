"""Request authentication (docs/API_CONTRACT.md §1, §11): JWT verification and API keys."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

AuthMethod = Literal["jwt", "api_key"]


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller; API keys act as their owner (§11)."""

    user_id: UUID
    email: str | None
    via: AuthMethod


__all__ = ["AuthMethod", "Principal"]
