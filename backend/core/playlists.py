"""Playlist business logic — the driver functions behind the API routes.

Each function orchestrates: gather seeds → recommend → resolve to real URIs → write to
Spotify. Routes stay thin by calling these; these stay testable by depending only on a
`SpotifyClient` and a `Recommender`.
"""

from __future__ import annotations

import random
from datetime import datetime

from backend.common.logging_config import logger
from .recommender.base import Recommender, Seed
from .resolver import resolve_all
from .spotify_client import SpotifyClient

WEEKLY_PLAYLIST_NAME = "Weekly Extended Playlist"
DEFAULT_DAILY_COUNT = 40
WEEKLY_EXTEND_COUNT = 40
_MAX_PLAYLIST_SONGS = 200


def daily_playlist_name(today: datetime | None = None) -> str:
    """Daily playlists are named by date, e.g. 'Jun-22-2026'."""
    return (today or datetime.today()).strftime("%b-%d-%Y")


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
    suggestions = recommender.recommend(seeds, count)
    uris = resolve_all(client.sp, suggestions, limit=count, exclude_uris=exclude_uris)
    random.shuffle(uris)
    return uris


def create_daily_playlist(
    client: SpotifyClient, recommender: Recommender, count: int = DEFAULT_DAILY_COUNT
) -> str:
    seeds = client.top_track_seeds()
    uris = _recommend_uris(client, recommender, seeds, count)
    if not uris:
        raise ValueError("No playable recommendations were found. Try again later.")
    name = daily_playlist_name()
    client.create_playlist(client.current_user_id(), name, uris)
    logger.info("Daily playlist created: %s (%d tracks)", name, len(uris))
    return f"Daily playlist created with name: {name}"


def extend_weekly_playlist(client: SpotifyClient, recommender: Recommender) -> str:
    playlist_id = client.find_playlist_id(WEEKLY_PLAYLIST_NAME)
    if playlist_id is None:
        logger.info("%s does not exist; creating it.", WEEKLY_PLAYLIST_NAME)
        seeds = client.top_track_seeds()
        uris = _recommend_uris(client, recommender, seeds, WEEKLY_EXTEND_COUNT)
        if not uris:
            raise ValueError("No playable recommendations were found. Try again later.")
        client.create_playlist(client.current_user_id(), WEEKLY_PLAYLIST_NAME, uris)
        return f"Playlist created with name: {WEEKLY_PLAYLIST_NAME}"

    existing = client.playlist_track_uris(playlist_id)
    seeds = client.top_track_seeds()
    uris = _recommend_uris(
        client, recommender, seeds, WEEKLY_EXTEND_COUNT, exclude_uris=existing
    )
    if not uris:
        raise ValueError("No new playable recommendations were found to add.")
    client.add_tracks(playlist_id, uris)
    logger.info("Extended %s by %d tracks.", WEEKLY_PLAYLIST_NAME, len(uris))
    return f"Weekly playlist extended by {len(uris)} tracks."


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
) -> str:
    source_id = client.find_playlist_id(source_name)
    if source_id is None:
        return "Playlist creation failed. Source playlist must already exist."

    count = max(1, min(count, _MAX_PLAYLIST_SONGS))
    seeds = client.playlist_seeds(source_id)
    if not seeds:
        return f"Source playlist '{source_name}' has no usable tracks to seed from."

    uris = _recommend_uris(client, recommender, seeds, count)
    if not uris:
        raise ValueError("No playable recommendations were found. Try again later.")
    client.create_playlist(client.current_user_id(), target_name, uris)
    logger.info("Playlist created: %s (%d tracks)", target_name, len(uris))
    return f"Playlist created: {target_name}"
