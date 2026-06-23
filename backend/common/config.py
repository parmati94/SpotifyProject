"""Centralised configuration.

One place that reads the environment (and a `.env` file), validates it, and hands
typed settings to the rest of the app. Import `get_settings()` where you need values;
it is cached so the `.env` is read once and validation happens once.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.common.logging_config import logger

_COMMON = Path(__file__).resolve().parent  # backend/common/
_PKG = _COMMON.parent                      # backend/
_ROOT = _PKG.parent                        # repo root


class Settings(BaseSettings):
    # Environment variables take precedence; either .env location is read if present.
    model_config = SettingsConfigDict(
        env_file=(_ROOT / ".env", _PKG / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Spotify (required) ---
    client_id: str = Field(..., alias="CLIENT_ID")
    client_secret: str = Field(..., alias="CLIENT_SECRET")
    # Non-secret, environment-specific — set per deployment in docker-compose*.yml.
    # Default matches the prod container port (5470). Spotify forbids "localhost" —
    # loopback must be the explicit IP literal, matching the registered Redirect URI.
    redirect_uri: str = Field("http://127.0.0.1:5470/callback", alias="REDIRECT_URI")

    # --- Sessions (required) ---
    session_secret: str = Field(..., alias="SESSION_SECRET")

    # --- Recommendations ---
    recommender: Literal["gemini", "catalog"] = Field("gemini", alias="RECOMMENDER")
    gemini_api_key: str | None = Field(None, alias="GEMINI_API_KEY")
    # 2.5-flash is fast (~5s) and full-quality. 3.5-flash is currently badly degraded
    # (~30s); gemini-flash-lite-latest is fastest (~3s) if you want max speed.
    gemini_model: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL")

    # --- Logging ---
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @property
    def effective_recommender(self) -> Literal["gemini", "catalog"]:
        """Gemini needs a key; without one, degrade to the catalog engine."""
        if self.recommender == "gemini" and not self.gemini_api_key:
            logger.warning(
                "RECOMMENDER=gemini but GEMINI_API_KEY is unset; "
                "falling back to the catalog recommender."
            )
            return "catalog"
        return self.recommender


@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once. Raises on missing required values."""
    return Settings()  # type: ignore[call-arg]  # values come from env/.env
