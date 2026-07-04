"""Конфигурация JARVIS. Все секреты — только из окружения (.env), не из кода."""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
JARVIS_DIR = BACKEND_DIR.parent


def _load_dotenv() -> None:
    """Мини-загрузчик .env без внешней зависимости (не перетирает окружение)."""
    env_path = JARVIS_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

DATA_DIR = Path(os.getenv("JARVIS_DATA_DIR", str(JARVIS_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "jarvis.duckdb"
PROFILE_PATH = DATA_DIR / "profile.local.yaml"
HTTP_CACHE_PATH = DATA_DIR / "http_cache"

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Пароль для доступа к терминалу (обязателен при выгрузке на VPS/AWS)
JARVIS_PASSWORD = os.getenv("JARVIS_PASSWORD", "")
# Dead-man's switch: URL healthchecks.io, пингуется после каждого фонового цикла
HEALTHCHECKS_URL = os.getenv("HEALTHCHECKS_URL", "")

DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "7"))
DIGEST_MINUTE = int(os.getenv("DIGEST_MINUTE", "30"))
TIMEZONE = os.getenv("JARVIS_TZ", "Asia/Jerusalem")

# Интервал фонового обновления котировок и проверки алертов, минуты
REFRESH_MINUTES = int(os.getenv("JARVIS_REFRESH_MINUTES", "5"))
