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


def get_recommender(
    sp: spotipy.Spotify = Depends(get_spotify),
    settings: Settings = Depends(get_settings),
) -> Recommender:
    return build_recommender(settings, sp)
