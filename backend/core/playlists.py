"""Playlist business logic — the driver functions behind the API routes.

Each function orchestrates: gather seeds → recommend → resolve to real URIs → write to
Spotify. Routes stay thin by calling these; these stay testable by depending only on a
`SpotifyClient` and a `Recommender`.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime

from backend.common.constants import APP_PLAYLIST_MARKER
from backend.common.logging_config import logger
from .recommender.base import Recommender, Seed, VibeRecommender
from .resolver import resolve_all
from .spotify_client import SpotifyClient


@dataclass
class PlaylistResult:
    """Outcome of a create/extend op. `track_count` is the playlist's *full* track total
    after the op — the API returns it so the UI can show the right number immediately,
    since Spotify's playlist-list endpoint reports a stale 0 for a few seconds after
    creation. `playlist_id` lets the UI patch the exact playlist even when several share a
    name. All but `message` are None for informational no-op messages."""

    message: str
    playlist_id: str | None = None
    name: str | None = None
    track_count: int | None = None

WEEKLY_PLAYLIST_NAME = "Weekly Extended Playlist"
DEFAULT_DAILY_COUNT = 40
WEEKLY_EXTEND_COUNT = 40
DEFAULT_VIBE_COUNT = 40
_MAX_PLAYLIST_SONGS = 200
# Fallback name when the user opts out of AI naming (or the LLM returns none); keeps the
# date-named-daily heuristic in is_app_created clear of vibe playlists.
_VIBE_NAME_MAX = 40

# Matches the daily naming format (e.g. "Jun-23-2026") — used to recognize dailies
# created before the description marker existed.
_DAILY_NAME_RE = re.compile(r"^[A-Z][a-z]{2}-\d{2}-\d{4}$")


def daily_playlist_name(today: datetime | None = None) -> str:
    """Daily playlists are named by date, e.g. 'Jun-22-2026'."""
    return (today or datetime.today()).strftime("%b-%d-%Y")


def is_app_created(name: str, description: str | None) -> bool:
    """Whether a playlist was made by this app. Primary signal is the description marker
    (reliable, set on everything we create going forward); the name heuristic backfills
    playlists created before the marker existed (the date-named daily, the weekly)."""
    if description and APP_PLAYLIST_MARKER in description:
        return True
    return name == WEEKLY_PLAYLIST_NAME or bool(_DAILY_NAME_RE.match(name))


def _recommend_uris(
    client: SpotifyClient,
    recommender: Recommender,
    seeds: list[Seed],
    count: int,
    *,
    exclude_uris: set[str] | None = None,
) -> list[str]:
    """seeds → recommender → resolve → dedupe → shuffle → slice to `count`."""
    if not seeds:
        return []
    logger.debug(
        "Build pipeline: %d seeds, requesting %d tracks (excluding %d existing)",
        len(seeds), count, len(exclude_uris or ()),
    )
    suggestions = recommender.recommend(seeds, count)
    logger.debug("Build pipeline: recommender returned %d suggestions; resolving", len(suggestions))
    uris = resolve_all(client.sp, suggestions, limit=count, exclude_uris=exclude_uris)
    random.shuffle(uris)
    logger.debug("Build pipeline: %d playable tracks after resolve/dedupe/slice", len(uris))
    return uris


def create_daily_playlist(
    client: SpotifyClient, recommender: Recommender, count: int = DEFAULT_DAILY_COUNT
) -> PlaylistResult:
    seeds = client.top_track_seeds()
    uris = _recommend_uris(client, recommender, seeds, count)
    if not uris:
        raise ValueError("No playable recommendations were found. Try again later.")
    name = daily_playlist_name()
    pid = client.create_playlist(client.current_user_id(), name, uris, description=APP_PLAYLIST_MARKER)
    logger.info("Daily playlist created: %s (%d tracks)", name, len(uris))
    return PlaylistResult(f"Daily playlist created with name: {name}", pid, name, len(uris))


def extend_weekly_playlist(client: SpotifyClient, recommender: Recommender) -> PlaylistResult:
    playlist_id = client.find_playlist_id(WEEKLY_PLAYLIST_NAME)
    if playlist_id is None:
        logger.info("%s does not exist; creating it.", WEEKLY_PLAYLIST_NAME)
        seeds = client.top_track_seeds()
        uris = _recommend_uris(client, recommender, seeds, WEEKLY_EXTEND_COUNT)
        if not uris:
            raise ValueError("No playable recommendations were found. Try again later.")
        pid = client.create_playlist(
            client.current_user_id(), WEEKLY_PLAYLIST_NAME, uris, description=APP_PLAYLIST_MARKER
        )
        return PlaylistResult(
            f"Playlist created with name: {WEEKLY_PLAYLIST_NAME}", pid, WEEKLY_PLAYLIST_NAME, len(uris)
        )

    existing = client.playlist_track_uris(playlist_id)
    seeds = client.top_track_seeds()
    uris = _recommend_uris(
        client, recommender, seeds, WEEKLY_EXTEND_COUNT, exclude_uris=existing
    )
    if not uris:
        raise ValueError("No new playable recommendations were found to add.")
    client.add_tracks(playlist_id, uris)
    logger.info("Extended %s by %d tracks.", WEEKLY_PLAYLIST_NAME, len(uris))
    return PlaylistResult(
        f"Weekly playlist extended by {len(uris)} tracks.",
        playlist_id,
        WEEKLY_PLAYLIST_NAME,
        len(existing) + len(uris),  # full total after the add, for the UI count patch
    )


def delete_daily_playlists(client: SpotifyClient) -> str:
    name = daily_playlist_name()
    ids = client.playlist_ids_by_name(name)
    if not ids:
        return f"No playlists exist with name: {name}"
    deleted = client.delete_playlists(ids)
    message = f"Deleted {deleted} playlist(s) with name: {name}"
    logger.info(message)
    return message


def create_playlist_from_playlist(
    client: SpotifyClient,
    recommender: Recommender,
    source_name: str,
    target_name: str,
    count: int,
) -> PlaylistResult:
    source_id = client.find_playlist_id(source_name)
    if source_id is None:
        return PlaylistResult("Playlist creation failed. Source playlist must already exist.")

    count = max(1, min(count, _MAX_PLAYLIST_SONGS))
    seeds = client.playlist_seeds(source_id)
    if not seeds:
        return PlaylistResult(f"Source playlist '{source_name}' has no usable tracks to seed from.")

    uris = _recommend_uris(client, recommender, seeds, count)
    if not uris:
        raise ValueError("No playable recommendations were found. Try again later.")
    pid = client.create_playlist(
        client.current_user_id(), target_name, uris, description=APP_PLAYLIST_MARKER
    )
    logger.info("Playlist created: %s (%d tracks)", target_name, len(uris))
    return PlaylistResult(f"Playlist created: {target_name}", pid, target_name, len(uris))


def _vibe_fallback_name(description: str) -> str:
    """Name for a vibe playlist when AI naming is off/unavailable — the trimmed vibe text."""
    text = " ".join(description.split())[:_VIBE_NAME_MAX].strip()
    return f"Vibe: {text}" if text else "Vibe playlist"


def create_vibe_playlist(
    client: SpotifyClient,
    recommender: VibeRecommender,
    description: str,
    count: int = DEFAULT_VIBE_COUNT,
    *,
    name_it: bool = True,
) -> PlaylistResult:
    """Build a playlist from a free-text vibe via an LLM. The engine returns the song
    suggestions plus (when `name_it`) a name/description; we resolve to real URIs and
    write the playlist, falling back to a name derived from the vibe text if needed."""
    description = description.strip()
    if not description:
        raise ValueError("Describe the vibe you want before generating.")
    count = max(1, min(count, _MAX_PLAYLIST_SONGS))

    result = recommender.recommend_vibe(description, count, name_it=name_it)
    logger.debug("Vibe pipeline: engine returned %d suggestions; resolving", len(result.suggestions))
    uris = resolve_all(client.sp, result.suggestions, limit=count)
    if not uris:
        raise ValueError("No playable songs were found for that vibe. Try rewording it.")
    random.shuffle(uris)

    name = result.name if (name_it and result.name) else _vibe_fallback_name(description)
    # The app marker tags it as ours; prefix the LLM blurb when there is one.
    playlist_description = (
        f"{result.description} {APP_PLAYLIST_MARKER}" if result.description else APP_PLAYLIST_MARKER
    )
    pid = client.create_playlist(
        client.current_user_id(), name, uris, description=playlist_description
    )
    logger.info("Vibe playlist created: %s (%d tracks)", name, len(uris))
    return PlaylistResult(f"Vibe playlist created: {name}", pid, name, len(uris))
