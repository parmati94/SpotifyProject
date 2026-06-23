"""Playlist endpoints — thin handlers over core.playlists business logic."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.common.constants import DEFAULT_IMAGE_URL
from backend.common.logging_config import logger
from backend.core import playlists as playlist_ops
from backend.core.recommender.base import Recommender, RecommenderError
from backend.core.spotify_client import SpotifyClient
from backend.deps import get_client, get_recommender
from backend.models.schemas import (
    FromPlaylistRequest,
    MessageResponse,
    PlaylistItem,
    PlaylistsResponse,
)

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.get("", response_model=PlaylistsResponse)
def list_playlists(client: SpotifyClient = Depends(get_client)) -> PlaylistsResponse:
    playlists = client.all_playlists()
    # Float recently-played playlists to the top (in recency order); the rest keep their
    # original order. Stable sort + a large rank for non-recent ones does both.
    recent_rank = {pid: i for i, pid in enumerate(client.recently_played_playlist_ids())}
    playlists.sort(key=lambda p: recent_rank.get(p.get("id"), len(recent_rank) + 1))

    items: list[PlaylistItem] = []
    for p in playlists:
        try:
            images = p.get("images") or []
            items.append(
                PlaylistItem(
                    name=p["name"],
                    total_tracks=p["tracks"]["total"],
                    image_url=images[0]["url"] if images else DEFAULT_IMAGE_URL,
                    recently_played=p.get("id") in recent_rank,
                )
            )
        except (KeyError, TypeError) as exc:
            logger.error("Skipping malformed playlist %r: %s", p.get("name"), exc)
    return PlaylistsResponse(playlists=items)


@router.post("/daily", response_model=MessageResponse)
def create_daily(
    client: SpotifyClient = Depends(get_client),
    recommender: Recommender = Depends(get_recommender),
) -> MessageResponse:
    return MessageResponse(message=_run(playlist_ops.create_daily_playlist, client, recommender))


@router.delete("/daily", response_model=MessageResponse)
def delete_daily(client: SpotifyClient = Depends(get_client)) -> MessageResponse:
    return MessageResponse(message=playlist_ops.delete_daily_playlists(client))


@router.post("/weekly", response_model=MessageResponse)
def extend_weekly(
    client: SpotifyClient = Depends(get_client),
    recommender: Recommender = Depends(get_recommender),
) -> MessageResponse:
    return MessageResponse(message=_run(playlist_ops.extend_weekly_playlist, client, recommender))


@router.post("/from-playlist", response_model=MessageResponse)
def create_from_playlist(
    body: FromPlaylistRequest,
    client: SpotifyClient = Depends(get_client),
    recommender: Recommender = Depends(get_recommender),
) -> MessageResponse:
    return MessageResponse(
        message=_run(
            playlist_ops.create_playlist_from_playlist,
            client,
            recommender,
            body.source_playlist,
            body.target_playlist,
            body.num_songs,
        )
    )


def _run(fn, *args) -> str:
    """Call a core playlist op, mapping known failures to clean HTTP errors:
    ValueError → 400 (e.g. nothing resolved); RecommenderError → 502 with the
    engine's reason (e.g. Claude credits exhausted, bad key, rate limit)."""
    try:
        return fn(*args)
    except RecommenderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
