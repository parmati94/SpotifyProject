"""Pydantic v2 request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class SessionResponse(BaseModel):
    authenticated: bool


class PlaylistItem(BaseModel):
    name: str
    total_tracks: int
    image_url: str


class PlaylistsResponse(BaseModel):
    playlists: list[PlaylistItem]


class FromPlaylistRequest(BaseModel):
    source_playlist: str = Field(..., min_length=1)
    target_playlist: str = Field(..., min_length=1)
    num_songs: int = Field(..., ge=1, le=200)
