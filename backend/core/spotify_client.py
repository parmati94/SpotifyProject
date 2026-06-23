"""Thin wrapper over spotipy for all the Spotify reads/writes the app needs.

This is the only module that speaks the raw Spotify JSON shape; everything above it
deals in clean types (`Seed`, track URIs, playlist ids). The recommendation machinery
that used to live here (the dead `sp.recommendations` 5-seed apparatus) is gone — song
discovery now comes from `core.recommender` + `core.resolver`.
"""

from __future__ import annotations

from backend.common.logging_config import logger
from .recommender.base import Seed

# Top-tracks time ranges, tried in order until one yields enough seeds.
_TIME_RANGES = ("short_term", "medium_term", "long_term")
_MIN_SEEDS = 20


def _track_to_seed(track: dict) -> Seed | None:
    title = (track.get("name") or "").strip()
    artists = track.get("artists") or []
    artist = (artists[0].get("name") or "").strip() if artists else ""
    return Seed(title=title, artist=artist) if title and artist else None


class SpotifyClient:
    def __init__(self, sp) -> None:
        self.sp = sp

    # --- user ---
    def current_user_id(self) -> str:
        return self.sp.me()["id"]

    # --- seeds ---
    def top_track_seeds(self, limit: int = _MIN_SEEDS) -> list[Seed]:
        """Seeds from the user's top tracks, preferring the most recent listening."""
        last: list[Seed] = []
        for time_range in _TIME_RANGES:
            logger.info("Getting top tracks for %s...", time_range)
            res = self.sp.current_user_top_tracks(time_range=time_range, limit=limit, offset=0)
            seeds = [s for s in map(_track_to_seed, res.get("items", [])) if s]
            last = seeds
            if len(seeds) >= _MIN_SEEDS:
                return seeds
        if not last:
            raise ValueError("No top tracks available to seed recommendations.")
        return last

    def playlist_seeds(self, playlist_id: str, limit: int = 50) -> list[Seed]:
        """Seeds from the tracks of an existing playlist."""
        seeds: list[Seed] = []
        offset = 0
        while len(seeds) < limit:
            batch = self.sp.playlist_items(playlist_id, offset=offset, limit=100)
            items = batch.get("items", [])
            if not items:
                break
            for item in items:
                seed = _track_to_seed(item.get("track") or {})
                if seed:
                    seeds.append(seed)
            offset += len(items)
            if offset >= batch.get("total", 0):
                break
        return seeds[:limit]

    # --- playlist reads ---
    def all_playlists(self) -> list[dict]:
        playlists: list[dict] = []
        offset = 0
        while True:
            batch = self.sp.current_user_playlists(offset=offset, limit=50)
            items = batch.get("items", [])
            playlists.extend(items)
            offset += len(items)
            if not items or offset >= batch.get("total", 0):
                break
        return playlists

    def find_playlist_id(self, name: str) -> str | None:
        """First playlist id matching `name`, or None. Prefer ids over names elsewhere."""
        for p in self.all_playlists():
            if p["name"] == name:
                return p["id"]
        return None

    def playlist_ids_by_name(self, name: str) -> list[str]:
        return [p["id"] for p in self.all_playlists() if p["name"] == name]

    def playlist_track_count(self, playlist_id: str) -> int:
        return self.sp.playlist_items(playlist_id, offset=0, limit=1).get("total", 0)

    def playlist_track_uris(self, playlist_id: str) -> set[str]:
        """All track URIs currently in a playlist (used to avoid re-adding dupes)."""
        uris: set[str] = set()
        offset = 0
        while True:
            batch = self.sp.playlist_items(playlist_id, offset=offset, limit=100)
            items = batch.get("items", [])
            for item in items:
                track = item.get("track") or {}
                if track.get("uri"):
                    uris.add(track["uri"])
            offset += len(items)
            if not items or offset >= batch.get("total", 0):
                break
        return uris

    # --- playlist writes ---
    def create_playlist(self, user_id: str, name: str, uris: list[str], description: str = "") -> str:
        logger.info("Creating playlist %r with %d tracks...", name, len(uris))
        playlist = self.sp.user_playlist_create(
            user_id, name, public=False, collaborative=False, description=description
        )
        playlist_id = playlist["id"]
        self.add_tracks(playlist_id, uris)
        return playlist_id

    def add_tracks(self, playlist_id: str, uris: list[str]) -> None:
        for i in range(0, len(uris), 100):  # Spotify caps adds at 100 per call
            self.sp.playlist_add_items(playlist_id, uris[i : i + 100])

    def delete_playlists(self, playlist_ids: list[str]) -> int:
        for playlist_id in playlist_ids:
            self.sp.current_user_unfollow_playlist(playlist_id)
        return len(playlist_ids)
