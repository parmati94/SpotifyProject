"""Pick and build the configured recommender.

Callers ask for "a recommender" and get back something satisfying the `Recommender`
protocol — they never branch on the engine. `Settings.effective_recommender` has already
resolved the "engine requested but no key" degrade-to-catalog decision.
"""

from __future__ import annotations

from backend.common.config import ENGINE_LABELS, Settings
from backend.common.logging_config import logger
from .base import Recommender
from .catalog import CatalogRecommender


def build_recommender(
    settings: Settings, sp, engine: str | None = None, model: str | None = None
) -> Recommender:
    # Caller may pass an already-resolved engine (e.g. a per-session selection);
    # otherwise fall back to the configured default. Either way the engine is assumed
    # resolved — its key is guaranteed present for keyed engines.
    if engine is None:
        engine = settings.effective_recommender
    # Resolve the model against the provider's configured list (a requested one that
    # isn't offered, or None, degrades to the provider default). None for non-LLM engines.
    model = settings.resolve_model(engine, model)

    if engine == "lastfm":
        from .lastfm import LastfmRecommender

        recommender: Recommender = LastfmRecommender(settings.lastfm_api_key)
    elif engine == "gemini":
        from .gemini import GeminiRecommender

        recommender = GeminiRecommender(settings.gemini_api_key, model)
    elif engine == "claude":
        from .claude import ClaudeRecommender

        recommender = ClaudeRecommender(settings.anthropic_api_key, model)
    else:
        recommender = CatalogRecommender(sp)

    # Surface the active engine at INFO (model included for the LLM engines) so the
    # logs always show which recommender served a build, not just its output.
    logger.info(
        "Recommender engine: %s%s",
        ENGINE_LABELS.get(engine, engine),
        f" ({model})" if model else "",
    )
    return recommender
