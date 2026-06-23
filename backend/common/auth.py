"""Spotify OAuth + per-session token handling.

The web flow keeps the full `token_info` (access + refresh + expiry) in the signed
session cookie; there is no on-disk token cache. On each authenticated request we refresh
the access token if it has expired and write the new `token_info` back to the session.
"""

from __future__ import annotations

import spotipy
from fastapi import HTTPException, Request
from spotipy.oauth2 import SpotifyOAuth

from backend.common.config import get_settings
from backend.common.constants import SPOTIFY_SCOPE
from backend.common.logging_config import logger


class _NoCache(spotipy.cache_handler.CacheHandler):
    """Disable spotipy's disk cache — the session is our token store."""

    def get_cached_token(self):
        return None

    def save_token_to_cache(self, token_info):
        pass


def _oauth() -> SpotifyOAuth:
    s = get_settings()
    return SpotifyOAuth(
        client_id=s.client_id,
        client_secret=s.client_secret,
        redirect_uri=s.redirect_uri,
        scope=SPOTIFY_SCOPE,
        cache_handler=_NoCache(),
    )


def login_url() -> str:
    return _oauth().get_authorize_url()


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for a token_info dict."""
    return _oauth().get_access_token(code, as_dict=True, check_cache=False)


def dev_token_from_refresh(refresh_token: str) -> dict:
    """Dev-only: mint a fresh token_info from a stored refresh token, skipping the
    interactive OAuth flow. Lets a headless/LAN box authenticate without a browser
    round-trip or a registered redirect URI. Gated by Settings.dev_auth at the caller."""
    return _oauth().refresh_access_token(refresh_token)


def refresh_if_expired(token_info: dict) -> dict:
    oauth = _oauth()
    if oauth.is_token_expired(token_info):
        logger.info("Access token expired; refreshing.")
        return oauth.refresh_access_token(token_info["refresh_token"])
    return token_info


def spotify_from_session(request: Request) -> spotipy.Spotify:
    """Build an authenticated spotipy client from the session, refreshing as needed.

    Raises 401 if the session has no token (caller is not logged in).
    """
    token_info = request.session.get("token_info")
    if not token_info:
        raise HTTPException(status_code=401, detail="Not authenticated")
    fresh = refresh_if_expired(token_info)
    if fresh != token_info:
        request.session["token_info"] = fresh
    return spotipy.Spotify(auth=fresh["access_token"])
