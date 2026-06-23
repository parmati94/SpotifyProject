"""Thin wrapper over spotipy for all the Spotify reads/writes the app needs.

This is the only module that speaks the raw Spotify JSON shape; everything above it
deals in clean types (`Seed`, track URIs, playlist ids). The recommendation machinery
that used to live here (the dead `sp.recommendations` 5-seed apparatus) is gone — song
discovery now comes from `core.recommender` + `core.resolver`.
"""

from __future__ import annotations

import os
import random

from backend.common.logging_config import logger
from .recommender.base import Seed

# How many seed tracks to feed the recommender. More seeds = broader taste coverage;
# past ~50 it's diminishing returns + slower (one Last.fm call per seed). Env-tunable.
_MAX_SEEDS = max(1, int(os.getenv("MAX_SEEDS", "50")))
# Top-tracks listening windows — blended for the daily so it spans recent + enduring taste.
_TIME_RANGES = ("short_term", "medium_term", "long_term")


def _track_to_seed(track: dict) -> Seed | None:
    title = (track.get("name") or "").strip()
    artists = track.get("artists") or []
    artist = (artists[0].get("name") or "").strip() if artists else ""
    return Seed(title=title, artist=artist) if title and artist else None


def _key(seed: Seed) -> tuple[str, str]:
    return (seed.title.lower(), seed.artist.lower())


def _recency_weighted_sample(seeds_newest_first: list[Seed], n: int) -> list[Seed]:
    """Pick `n` seeds favoring the front of the list (recently added), without replacement.

    Uses Efraimidis–Spirakis weighted sampling: each item gets key = u**(1/weight) with a
    linear recency weight (newest = heaviest), and we take the top-n keys. Recent tracks are
    much more likely, but older ones can still appear — so a playlist's current lean dominates
    while keeping some breadth.
    """
    total = len(seeds_newest_first)
    keyed = []
    for i, seed in enumerate(seeds_newest_first):
        weight = total - i  # i=0 is newest → heaviest
        u = random.random() or 1e-12
        keyed.append((u ** (1.0 / weight), seed))
    keyed.sort(key=lambda k: k[0], reverse=True)
    return [seed for _, seed in keyed[:n]]


class SpotifyClient:
    def __init__(self, sp) -> None:
        self.sp = sp

    # --- user ---
    def current_user_id(self) -> str:
        return self.sp.me()["id"]

    # --- seeds ---
    def top_track_seeds(self, limit: int = _MAX_SEEDS) -> list[Seed]:
        """Seeds blended across all listening windows (recent + enduring), deduped and
        shuffled, capped at `limit`. Shuffled so a daily varies day to day."""
        seen: set[tuple[str, str]] = set()
        seeds: list[Seed] = []
        for time_range in _TIME_RANGES:
            logger.info("Getting top tracks for %s...", time_range)
            res = self.sp.current_user_top_tracks(time_range=time_range, limit=50, offset=0)
            for item in res.get("items", []):
                seed = _track_to_seed(item)
                if seed and _key(seed) not in seen:
                    seen.add(_key(seed))
                    seeds.append(seed)
        if not seeds:
            raise ValueError("No top tracks available to seed recommendations.")
        random.shuffle(seeds)
        chosen = seeds[:limit]
        logger.info("Seeded from %d top tracks (%d available).", len(chosen), len(seeds))
        return chosen

    def playlist_seeds(self, playlist_id: str, limit: int = _MAX_SEEDS) -> list[Seed]:
        """Recency-weighted sample of a playlist's tracks (up to `limit`). Spotify gives an
        `added_at` per track; recently-added tracks — the listener's current lean — are
        favored, with older ones still possible for breadth. Scales with playlist size."""
        entries: list[tuple[Seed, str]] = []
        offset = 0
        while True:
            batch = self.sp.playlist_items(
                playlist_id,
                offset=offset,
                limit=100,
                fields="total,items(added_at,track(name,artists(name)))",
            )
            items = batch.get("items", [])
            if not items:
                break
            for item in items:
                seed = _track_to_seed(item.get("track") or {})
                if seed:
                    entries.append((seed, item.get("added_at") or ""))
            offset += len(items)
            if offset >= batch.get("total", 0):
                break
        if not entries:
            return []
        # Newest first (ISO-8601 added_at sorts lexicographically), then recency-weighted pick.
        entries.sort(key=lambda e: e[1], reverse=True)
        n = min(limit, len(entries))
        chosen = _recency_weighted_sample([seed for seed, _ in entries], n)
        logger.info("Seeded from %d of %d playlist tracks (recency-weighted).", len(chosen), len(entries))
        return chosen

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
