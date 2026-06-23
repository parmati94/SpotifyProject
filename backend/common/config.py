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

# Human-readable engine names for the UI. Single source of truth shared by the
# availability list and any display.
ENGINE_LABELS = {
    "lastfm": "Last.fm",
    "gemini": "Gemini",
    "claude": "Claude",
    "catalog": "Spotify catalog",
}


class Settings(BaseSettings):
    # Environment variables take precedence. The project-root `.env` is the canonical
    # location; `backend/.env` is still read as a legacy fallback. Later entries win, so
    # root overrides backend if both somehow exist.
    model_config = SettingsConfigDict(
        env_file=(_PKG / ".env", _ROOT / ".env"),
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
    # Engine toggle. lastfm (default): real data-driven similarity, no key cost beyond
    # the free Last.fm key. gemini/claude: LLM engines. catalog: Spotify-native fallback.
    recommender: Literal["lastfm", "gemini", "claude", "catalog"] = Field(
        "lastfm", alias="RECOMMENDER"
    )
    # Last.fm — free key from https://www.last.fm/api (read methods need no secret).
    lastfm_api_key: str | None = Field(None, alias="LASTFM_API_KEY")
    # Gemini — free key (no card) from https://aistudio.google.com/apikey.
    gemini_api_key: str | None = Field(None, alias="GEMINI_API_KEY")
    # 2.5-flash is fast (~5s) and full-quality. 3.5-flash is currently badly degraded
    # (~30s); gemini-flash-lite-latest is fastest (~3s) if you want max speed.
    gemini_model: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL")
    # Claude — key + a little credit from https://console.anthropic.com (separate from
    # any Claude.ai/Max subscription).
    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    claude_model: str = Field("claude-sonnet-4-6", alias="CLAUDE_MODEL")

    # --- Logging ---
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # --- Dev auth bypass (NEVER enable in production) ---
    # Headless/LAN dev can't complete Spotify OAuth: a non-loopback http origin like
    # http://192.168.x.x:PORT/callback is an illegal redirect URI. With dev_auth on, the
    # /dev/login route seeds the session from a pre-captured refresh token (skipping the
    # browser round-trip entirely), and /callback logs the refresh token once so you can
    # capture it from a single real login on the HTTPS deploy. Defaults off; the prod
    # compose also pins it false so a shared .env can't leak it in.
    dev_auth: bool = Field(False, alias="DEV_AUTH")
    dev_refresh_token: str | None = Field(None, alias="DEV_REFRESH_TOKEN")

    def resolve_engine(
        self, engine: str
    ) -> Literal["lastfm", "gemini", "claude", "catalog"]:
        """Validate a requested engine against configured credentials. Each keyed
        engine needs its key; without it, degrade to the catalog engine (Spotify-native,
        always available) rather than failing a playlist build. Unknown engines also
        degrade to catalog. Drives both the env default and any runtime selection."""
        required_key = {
            "lastfm": self.lastfm_api_key,
            "gemini": self.gemini_api_key,
            "claude": self.anthropic_api_key,
        }.get(engine)
        if engine != "catalog" and not required_key:
            logger.warning(
                "Recommender %r requested but its API key is unset; falling back to "
                "the catalog recommender.", engine,
            )
            return "catalog"
        return engine  # type: ignore[return-value]

    @property
    def effective_recommender(self) -> Literal["lastfm", "gemini", "claude", "catalog"]:
        """The configured default engine (RECOMMENDER), resolved against credentials."""
        return self.resolve_engine(self.recommender)

    def available_engines(self) -> list[dict]:
        """Engines the user may pick from: the catalog fallback always, plus each keyed
        engine whose API key is configured. `model` carries the configured model for the
        LLM engines (for the UI to show, e.g. "Claude · claude-sonnet-4-6"), None for the
        others. Order: real engines first, catalog fallback last."""
        keyed = [
            ("lastfm", self.lastfm_api_key, None),
            ("gemini", self.gemini_api_key, self.gemini_model),
            ("claude", self.anthropic_api_key, self.claude_model),
        ]
        engines = [
            {"id": eid, "label": ENGINE_LABELS[eid], "model": model}
            for eid, key, model in keyed
            if key
        ]
        engines.append({"id": "catalog", "label": ENGINE_LABELS["catalog"], "model": None})
        return engines


@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once. Raises on missing required values."""
    return Settings()  # type: ignore[call-arg]  # values come from env/.env
