"""FastAPI dependencies — wire requests to the core layer.

Routes declare what they need (a `SpotifyClient`, a `Recommender`) and these provide it,
keeping the route handlers thin and free of construction/auth detail.
"""

from __future__ import annotations

import spotipy
from fastapi import Depends, Request

from backend.common.auth import spotify_from_session
from backend.common.config import Settings, get_settings
from backend.core.recommender.base import Recommender, VibeRecommender
from backend.core.recommender.factory import build_recommender
from backend.core.spotify_client import SpotifyClient


def get_spotify(request: Request) -> spotipy.Spotify:
    return spotify_from_session(request)


def get_client(sp: spotipy.Spotify = Depends(get_spotify)) -> SpotifyClient:
    return SpotifyClient(sp)


# Session key holding a user's runtime engine selection. Stored in the signed session
# cookie (same place as the Spotify token), so the choice is per-user/per-browser and
# multiple users get independent engines with no shared server state.
SESSION_ENGINE_KEY = "recommender"
# Model within the selected engine. Validated against the active engine's model list, so a
# stale model (engine switched, or env list changed) degrades to that engine's default.
SESSION_ENGINE_MODEL_KEY = "recommender_model"


def selected_engine(request: Request, settings: Settings) -> str:
    """The engine for this session: the user's runtime selection if set, else the
    configured default (RECOMMENDER). Always resolved against credentials, so a stale
    selection whose key was since removed degrades to catalog rather than erroring."""
    requested = request.session.get(SESSION_ENGINE_KEY) or settings.recommender
    return settings.resolve_engine(requested)


def selected_model(request: Request, settings: Settings, engine: str) -> str | None:
    """The model for this session's recommendation engine, validated against that engine's
    configured list (degrades to its default; None for non-LLM engines)."""
    return settings.resolve_model(engine, request.session.get(SESSION_ENGINE_MODEL_KEY))


def get_recommender(
    request: Request,
    sp: spotipy.Spotify = Depends(get_spotify),
    settings: Settings = Depends(get_settings),
) -> Recommender:
    engine = selected_engine(request, settings)
    return build_recommender(settings, sp, engine, selected_model(request, settings, engine))


# Vibe mode's LLM selection — a separate slot from SESSION_ENGINE_KEY so the free-text
# engine and the seed-based engine are chosen independently. LLM-only; never lastfm/catalog.
SESSION_VIBE_ENGINE_KEY = "vibe_engine"
SESSION_VIBE_MODEL_KEY = "vibe_model"


def selected_vibe_engine(request: Request, settings: Settings) -> str | None:
    """The LLM serving vibe mode this session: the user's pick if still available, else
    the best available LLM, else None when no LLM key is configured (vibe disabled)."""
    return settings.resolve_vibe_engine(request.session.get(SESSION_VIBE_ENGINE_KEY))


def selected_vibe_model(request: Request, settings: Settings, engine: str) -> str | None:
    """The model for vibe mode's LLM, validated against that engine's configured list."""
    return settings.resolve_model(engine, request.session.get(SESSION_VIBE_MODEL_KEY))


def get_vibe_recommender(
    request: Request,
    sp: spotipy.Spotify = Depends(get_spotify),
    settings: Settings = Depends(get_settings),
) -> VibeRecommender | None:
    """The vibe engine for this request, or None when no LLM is configured. The LLM
    engines all satisfy `VibeRecommender`; `build_recommender` returns the concrete one."""
    engine = selected_vibe_engine(request, settings)
    if engine is None:
        return None
    model = selected_vibe_model(request, settings, engine)
    return build_recommender(settings, sp, engine, model)  # type: ignore[return-value]
