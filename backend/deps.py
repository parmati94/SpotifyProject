"""FastAPI dependencies — wire requests to the core layer.

Routes declare what they need (a `SpotifyClient`, a `Recommender`) and these provide it,
keeping the route handlers thin and free of construction/auth detail.
"""

from __future__ import annotations

import spotipy
from fastapi import Depends, Request

from backend.common.auth import spotify_from_session
from backend.common.config import Settings, get_settings
from backend.core.recommender.base import Recommender
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


def selected_engine(request: Request, settings: Settings) -> str:
    """The engine for this session: the user's runtime selection if set, else the
    configured default (RECOMMENDER). Always resolved against credentials, so a stale
    selection whose key was since removed degrades to catalog rather than erroring."""
    requested = request.session.get(SESSION_ENGINE_KEY) or settings.recommender
    return settings.resolve_engine(requested)


def get_recommender(
    request: Request,
    sp: spotipy.Spotify = Depends(get_spotify),
    settings: Settings = Depends(get_settings),
) -> Recommender:
    return build_recommender(settings, sp, selected_engine(request, settings))
