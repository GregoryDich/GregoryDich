"""API-key format, hashing and lookup (§11; docs/SECURITY.md §2.2).

Plaintext keys are ``tm_live_`` followed by 32 hex characters from a CSPRNG. Only the
SHA-256 hex digest is stored; the in-memory backend compares digests in constant time and
the Supabase backend delegates the lookup to ``authenticate_api_key``.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.services import ApiKeysService

API_KEY_PREFIX = "tm_live_"
API_KEY_RE = re.compile(r"^tm_live_[A-Za-z0-9]{32}$")
PREFIX_LENGTH = 12


def generate_api_key() -> tuple[str, str, str]:
    """``(plaintext, display_prefix, sha256_hex)`` for a new key."""
    plaintext = API_KEY_PREFIX + secrets.token_hex(16)
    return plaintext, plaintext[:PREFIX_LENGTH], hash_api_key(plaintext)


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def is_well_formed(plaintext: str) -> bool:
    return API_KEY_RE.match(plaintext) is not None


def hashes_match(stored_hash: str, presented_hash: str) -> bool:
    return hmac.compare_digest(stored_hash.encode("ascii"), presented_hash.encode("ascii"))


async def authenticate_api_key(plaintext: str, api_keys: ApiKeysService) -> UUID | None:
    """Owner of a presented ``X-API-Key`` or ``None``; malformed keys never reach storage."""
    if not is_well_formed(plaintext):
        return None
    return await api_keys.resolve(plaintext)


__all__ = [
    "API_KEY_PREFIX",
    "PREFIX_LENGTH",
    "authenticate_api_key",
    "generate_api_key",
    "hash_api_key",
    "hashes_match",
    "is_well_formed",
]
