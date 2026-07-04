"""Единая HTTP-сессия с кэшем: free-tier лимиты требуют агрессивного кэширования."""
import requests
import requests_cache

from app import config

UA = {"User-Agent": "JARVIS personal terminal (research/personal use)"}

_session: requests.Session | None = None


def get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests_cache.CachedSession(
            str(config.HTTP_CACHE_PATH),
            backend="sqlite",
            expire_after=300,  # 5 минут по умолчанию
            allowable_codes=(200,),
        )
        _session.headers.update(UA)
    return _session


def get(url: str, timeout: int = 20, **kwargs) -> requests.Response:
    r = get_session().get(url, timeout=timeout, **kwargs)
    r.raise_for_status()
    return r
