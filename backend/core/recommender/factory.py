"""Pick and build the configured recommender.

Callers ask for "a recommender" and get back something satisfying the `Recommender`
protocol — they never branch on the engine. `Settings.effective_recommender` already
handles the "Gemini requested but no key" degrade-to-catalog decision.
"""

from __future__ import annotations

from backend.common.config import Settings
from .base import Recommender
from .catalog import CatalogRecommender
from .gemini import GeminiRecommender


def build_recommender(settings: Settings, sp) -> Recommender:
    if settings.effective_recommender == "gemini":
        assert settings.gemini_api_key  # guaranteed by effective_recommender
        return GeminiRecommender(settings.gemini_api_key, settings.gemini_model)
    return CatalogRecommender(sp)
