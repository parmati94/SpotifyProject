"""Pydantic v2 request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class SessionResponse(BaseModel):
    authenticated: bool
    # Dev-only: tells the SPA to route "Connect" through /dev/login. Always false in prod.
    dev: bool = False


class PlaylistItem(BaseModel):
    name: str
    total_tracks: int
    image_url: str
    recently_played: bool = False


class PlaylistsResponse(BaseModel):
    playlists: list[PlaylistItem]


class RecommenderInfo(BaseModel):
    id: str
    label: str
    model: str | None = None


class RecommenderStatus(BaseModel):
    """The session's active engine plus the list it may switch between (credential-gated)."""
    active: str
    available: list[RecommenderInfo]


class SetRecommenderRequest(BaseModel):
    engine: str = Field(..., min_length=1)


class FromPlaylistRequest(BaseModel):
    source_playlist: str = Field(..., min_length=1)
    target_playlist: str = Field(..., min_length=1)
    num_songs: int = Field(..., ge=1, le=200)
