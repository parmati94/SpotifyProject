"""Spotify-native fallback recommender.

Used when no Gemini key is configured (or as an explicit `RECOMMENDER=catalog`). It needs
zero external services: for each seed it finds the artist on Spotify and gathers that
artist's top tracks, producing `{title, artist}` candidates that the resolver then
verifies like any other suggestion.

Deliberately avoids Spotify's deprecated discovery endpoints (`/recommendations`,
`/audio-features`, related-artists) — only still-live catalog reads are used.
"""

from __future__ import annotations

import random

from backend.common.logging_config import logger
from .base import Recommender, Seed, Suggestion


class CatalogRecommender(Recommender):
    """Builds candidates from seed artists' top tracks. Needs a live Spotify client."""

    def __init__(self, sp) -> None:
        self._sp = sp

    def _artist_id(self, artist_name: str) -> str | None:
        try:
            res = self._sp.search(q=f'artist:"{artist_name}"', type="artist", limit=1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Artist lookup failed for %r: %s", artist_name, exc)
            return None
        items = res.get("artists", {}).get("items", [])
        return items[0]["id"] if items else None

    def _top_tracks(self, artist_id: str) -> list[Suggestion]:
        try:
            res = self._sp.artist_top_tracks(artist_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("artist_top_tracks failed for %s: %s", artist_id, exc)
            return []
        out: list[Suggestion] = []
        for track in res.get("tracks", []):
            title = track.get("name", "").strip()
            artists = track.get("artists", [])
            artist = artists[0]["name"].strip() if artists else ""
            if title and artist:
                out.append(Suggestion(title=title, artist=artist))
        return out

    def recommend(self, seeds: list[Seed], count: int) -> list[Suggestion]:
        if not seeds or count <= 0:
            return []

        seen: set[tuple[str, str]] = set()
        candidates: list[Suggestion] = []
        for artist_name in {s.artist for s in seeds}:  # dedupe seed artists
            artist_id = self._artist_id(artist_name)
            if artist_id is None:
                continue
            for suggestion in self._top_tracks(artist_id):
                key = (suggestion.title.lower(), suggestion.artist.lower())
                if key not in seen:
                    seen.add(key)
                    candidates.append(suggestion)

        random.shuffle(candidates)
        logger.info("Catalog recommender produced %d candidates.", len(candidates))
        # Over-return a little; the resolver/pipeline slices to the final count.
        return candidates[: max(count * 2, count)]
