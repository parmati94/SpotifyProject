"""Playlist endpoints — thin handlers over core.playlists business logic."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.common.config import Settings, get_settings
from backend.common.constants import DEFAULT_IMAGE_URL
from backend.common.logging_config import logger
from backend.core import playlists as playlist_ops
from backend.core.recommender.base import Recommender, RecommenderError
from backend.core.recommender.factory import build_recommender
from backend.core.recommender.lastfm import LastfmRecommender
from backend.core.spotify_client import SpotifyClient
from backend.deps import (
    SESSION_VIBE_ENGINE_KEY,
    SESSION_VIBE_MODEL_KEY,
    get_client,
    get_recommender,
    selected_vibe_engine,
)
from backend.models.schemas import (
    FromPlaylistRequest,
    MessageResponse,
    PlaylistItem,
    PlaylistMutationResponse,
    PlaylistsResponse,
    VibeRequest,
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
                    id=p["id"],
                    name=p["name"],
                    total_tracks=p["tracks"]["total"],
                    image_url=images[0]["url"] if images else DEFAULT_IMAGE_URL,
                    recently_played=p.get("id") in recent_rank,
                    created_by_app=playlist_ops.is_app_created(p["name"], p.get("description")),
                )
            )
        except (KeyError, TypeError) as exc:
            logger.error("Skipping malformed playlist %r: %s", p.get("name"), exc)
    return PlaylistsResponse(playlists=items)


@router.post("/daily", response_model=PlaylistMutationResponse)
def create_daily(
    client: SpotifyClient = Depends(get_client),
    recommender: Recommender = Depends(get_recommender),
) -> PlaylistMutationResponse:
    res = _run(playlist_ops.create_daily_playlist, client, recommender)
    return PlaylistMutationResponse(message=res.message, id=res.playlist_id, name=res.name, total_tracks=res.track_count)


@router.delete("/daily", response_model=MessageResponse)
def delete_daily(client: SpotifyClient = Depends(get_client)) -> MessageResponse:
    return MessageResponse(message=playlist_ops.delete_daily_playlists(client))


@router.post("/weekly", response_model=PlaylistMutationResponse)
def extend_weekly(
    client: SpotifyClient = Depends(get_client),
    recommender: Recommender = Depends(get_recommender),
) -> PlaylistMutationResponse:
    res = _run(playlist_ops.extend_weekly_playlist, client, recommender)
    return PlaylistMutationResponse(message=res.message, id=res.playlist_id, name=res.name, total_tracks=res.track_count)


@router.post("/from-playlist", response_model=PlaylistMutationResponse)
def create_from_playlist(
    body: FromPlaylistRequest,
    client: SpotifyClient = Depends(get_client),
    recommender: Recommender = Depends(get_recommender),
) -> PlaylistMutationResponse:
    res = _run(
        playlist_ops.create_playlist_from_playlist,
        client,
        recommender,
        body.source_playlist,
        body.target_playlist,
        body.num_songs,
    )
    return PlaylistMutationResponse(message=res.message, id=res.playlist_id, name=res.name, total_tracks=res.track_count)


@router.post("/vibe", response_model=PlaylistMutationResponse)
def create_vibe(
    body: VibeRequest,
    request: Request,
    client: SpotifyClient = Depends(get_client),
    settings: Settings = Depends(get_settings),
) -> PlaylistMutationResponse:
    # A valid engine override is persisted so the panel's picker remembers it; an
    # invalid/absent one falls through to the session default (best-available LLM).
    if body.engine and settings.resolve_vibe_engine(body.engine) == body.engine:
        request.session[SESSION_VIBE_ENGINE_KEY] = body.engine
    engine = selected_vibe_engine(request, settings)
    if engine is None:
        raise HTTPException(
            status_code=400, detail="Vibe mode needs a configured LLM (Claude or Gemini)."
        )
    # Persist the model choice for this engine (default when unset/invalid) so the panel's
    # sub-selector remembers it, then build with it.
    model = settings.resolve_model(engine, body.model)
    request.session[SESSION_VIBE_MODEL_KEY] = model
    recommender = build_recommender(settings, client.sp, engine, model)
    # Grounded count-fill: when the LLM lands short, top up from Last.fm similarity rather
    # than padding with more LLM guesses. Only available when a Last.fm key is configured.
    fill_recommender = (
        LastfmRecommender(settings.lastfm_api_key) if settings.lastfm_api_key else None
    )
    res = _run(
        lambda: playlist_ops.create_vibe_playlist(
            client, recommender, body.description, body.num_songs,
            name_it=body.name_it, fill_recommender=fill_recommender,
            source_playlist=body.source_playlist,
        )
    )
    return PlaylistMutationResponse(message=res.message, id=res.playlist_id, name=res.name, total_tracks=res.track_count)


def _run(fn, *args) -> playlist_ops.PlaylistResult:
    """Call a core playlist op, mapping known failures to clean HTTP errors:
    ValueError → 400 (e.g. nothing resolved); RecommenderError → 502 with the
    engine's reason (e.g. Claude credits exhausted, bad key, rate limit)."""
    try:
        return fn(*args)
    except RecommenderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
