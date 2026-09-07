"""Runtime configuration.

Every credential is read from the process environment (pydantic-settings). No file is ever
read for secrets; ``.env.example`` documents the variables and the MCP client config or the
shell is expected to export them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Platform = Literal["instagram", "facebook", "tiktok", "youtube"]
PLATFORMS: tuple[Platform, ...] = ("instagram", "facebook", "tiktok", "youtube")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    snapplay_api_url: str = "https://api.snapplay.ai"
    snapplay_api_key: str | None = None
    snapplay_job_timeout_seconds: float = 600.0
    snapplay_poll_interval_seconds: float = 2.0

    growth_db_path: Path = Path("./growth.db")
    growth_work_dir: Path = Path("./work")

    licensed_clips_dir: Path = Path("./licensed_clips")
    fma_api_key: str | None = None
    fma_api_url: str = "https://freemusicarchive.org/api/get"

    elevenlabs_api_key: str | None = None
    elevenlabs_api_url: str = "https://api.elevenlabs.io"
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    remotion_dir: Path = Path("./remotion")
    remotion_browser_executable: str | None = None
    remotion_gl: str | None = None
    remotion_concurrency: int = 2
    ffmpeg_bin: str = "ffmpeg"
    ffmpeg_font_file: str | None = None

    meta_graph_api_url: str = "https://graph.facebook.com"
    meta_upload_api_url: str = "https://rupload.facebook.com"
    meta_api_version: str = "v21.0"
    meta_ig_user_id: str | None = None
    meta_ig_access_token: str | None = None
    meta_page_id: str | None = None
    meta_page_access_token: str | None = None

    tiktok_api_url: str = "https://open.tiktokapis.com"
    tiktok_access_token: str | None = None

    youtube_api_url: str = "https://www.googleapis.com"
    youtube_access_token: str | None = None

    growth_max_posts_per_day_instagram: int = Field(default=5, ge=0)
    growth_max_posts_per_day_facebook: int = Field(default=5, ge=0)
    growth_max_posts_per_day_tiktok: int = Field(default=3, ge=0)
    growth_max_posts_per_day_youtube: int = Field(default=4, ge=0)
    # Bounded waits for platform-side processing polls (seconds between attempts).
    publish_poll_interval_seconds: float = 5.0
    publish_poll_attempts: int = 60

    def platform_configured(self, platform: Platform) -> bool:
        match platform:
            case "instagram":
                return bool(self.meta_ig_user_id and self.meta_ig_access_token)
            case "facebook":
                return bool(self.meta_page_id and self.meta_page_access_token)
            case "tiktok":
                return bool(self.tiktok_access_token)
            case "youtube":
                return bool(self.youtube_access_token)

    def configured_platforms(self) -> list[Platform]:
        return [p for p in PLATFORMS if self.platform_configured(p)]

    def max_posts_per_day(self, platform: Platform) -> int:
        return int(getattr(self, f"growth_max_posts_per_day_{platform}"))


def get_settings() -> Settings:
    """Build settings from the current environment (cheap; called per tool invocation)."""
    return Settings()
