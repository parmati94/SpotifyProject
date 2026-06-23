"""Pick and build the configured recommender.

Callers ask for "a recommender" and get back something satisfying the `Recommender`
protocol — they never branch on the engine. `Settings.effective_recommender` has already
resolved the "engine requested but no key" degrade-to-catalog decision.
"""

from __future__ import annotations

from backend.common.config import Settings
from .base import Recommender
from .catalog import CatalogRecommender


def build_recommender(settings: Settings, sp) -> Recommender:
    engine = settings.effective_recommender  # keys guaranteed present for keyed engines
    if engine == "lastfm":
        from .lastfm import LastfmRecommender

        return LastfmRecommender(settings.lastfm_api_key)
    if engine == "gemini":
        from .gemini import GeminiRecommender

        return GeminiRecommender(settings.gemini_api_key, settings.gemini_model)
    if engine == "claude":
        from .claude import ClaudeRecommender

        return ClaudeRecommender(settings.anthropic_api_key, settings.claude_model)
    return CatalogRecommender(sp)
