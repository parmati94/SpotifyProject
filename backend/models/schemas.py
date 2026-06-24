"""Pydantic v2 request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class PlaylistMutationResponse(MessageResponse):
    # Id/name + full track count of the affected playlist, so the UI can show the right
    # count right away (Spotify's playlist-list reports a stale 0 just after creation) and
    # patch the exact playlist even when several share a name (e.g. two dailies same day).
    id: str | None = None
    name: str | None = None
    total_tracks: int | None = None


class SessionResponse(BaseModel):
    authenticated: bool
    # Dev-only: tells the SPA to route "Connect" through /dev/login. Always false in prod.
    dev: bool = False


class PlaylistItem(BaseModel):
    # Spotify playlist id — unique key for the UI (playlist names are NOT unique; e.g.
    # you can have two dailies named the same date).
    id: str
    name: str
    total_tracks: int
    image_url: str
    recently_played: bool = False
    # True for playlists this app made (daily/weekly/created-from) — drives the UI tabs.
    created_by_app: bool = False


class PlaylistsResponse(BaseModel):
    playlists: list[PlaylistItem]


class RecommenderInfo(BaseModel):
    id: str
    label: str
    # The engine's default model (a display sub-label); None for lastfm/catalog.
    model: str | None = None
    # All selectable models for this engine (drives the model sub-selector); empty for
    # non-LLM engines and for LLMs configured with a single model.
    models: list[str] = []


class RecommenderStatus(BaseModel):
    """The session's active engine + model plus the list it may switch between."""
    active: str
    active_model: str | None = None
    available: list[RecommenderInfo]


class SetRecommenderRequest(BaseModel):
    engine: str = Field(..., min_length=1)
    # Optional model within the chosen engine; ignored if not offered by that engine.
    model: str | None = None


class VibeStatus(BaseModel):
    """Vibe mode's LLM picker state: the active engine and the LLM-only list to choose
    from. `active` is None and `available` is empty when no LLM key is configured, which
    the UI reads as "hide vibe mode entirely"."""
    active: str | None = None
    active_model: str | None = None
    available: list[RecommenderInfo]


class FromPlaylistRequest(BaseModel):
    source_playlist: str = Field(..., min_length=1)
    target_playlist: str = Field(..., min_length=1)
    num_songs: int = Field(..., ge=1, le=200)


class VibeRequest(BaseModel):
    # Free-text description of the playlist to build ("rainy sunday coffee-shop jazz").
    description: str = Field(..., min_length=1, max_length=300)
    # Capped lower than from-playlist (200): a single free-text vibe has a real quality
    # ceiling — the LLM exhausts genuinely on-vibe picks well before 200 and starts to drift.
    num_songs: int = Field(40, ge=1, le=100)
    name_it: bool = True
    # Optional per-request LLM override; when a valid LLM, it's also persisted to the
    # session so the vibe panel's picker remembers it. Absent ⇒ use the session default.
    engine: str | None = None
    # Optional model within that LLM; persisted likewise. Ignored if the engine doesn't offer it.
    model: str | None = None
