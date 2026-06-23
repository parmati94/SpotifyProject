"""Last.fm recommender — data-driven seed similarity (the default engine).

For each seed track we ask Last.fm for similar tracks (`track.getSimilar`), then
aggregate across all seeds weighted by Last.fm's `match` score — so songs that are
similar to *several* of the listener's seeds rank highest. Results are real,
existing tracks (collaborative-filtering data, not an LLM guess), so there's nothing
to hallucinate; the resolver just maps name → Spotify URI.

This is effectively the replacement for Spotify's dead `/v1/recommendations`.
"""

from __future__ import annotations

import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests

from backend.common.logging_config import logger
from .base import Recommender, Seed, Suggestion, preview

_API = "https://ws.audioscrobbler.com/2.0/"
_WORKERS = max(1, int(os.getenv("LASTFM_WORKERS", "5")))
_SIMILAR_PER_SEED = 50  # track.getSimilar results per seed
_OVER_REQUEST = 1.25    # over-return to absorb resolver misses


class LastfmRecommender(Recommender):
    def __init__(self, api_key: str, timeout: float = 8.0) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._session = requests.Session()  # pooled, shared across worker threads

    def _get(self, method: str, **params) -> dict:
        params.update(method=method, api_key=self._api_key, format="json", autocorrect=1)
        try:
            resp = self._session.get(_API, params=params, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 — one bad call shouldn't kill the batch
            logger.warning("Last.fm %s failed: %s", method, exc)
            return {}

    def _similar_for_seed(self, seed: Seed) -> list[tuple[Suggestion, float]]:
        data = self._get(
            "track.getsimilar", artist=seed.artist, track=seed.title, limit=_SIMILAR_PER_SEED
        )
        out = _parse_similar_tracks(data)
        if out:
            logger.debug(
                "Last.fm: %d similar tracks for seed %s — %s", len(out), seed.title, seed.artist
            )
            return out
        # Fallback: the seed track wasn't found / had no neighbours — surface more of
        # the same artist so the seed still contributes something.
        top = self._get("artist.gettoptracks", artist=seed.artist, limit=10)
        fallback = _parse_top_tracks(top)
        logger.debug(
            "Last.fm: no neighbours for seed %s — %s; fell back to %d artist top tracks",
            seed.title, seed.artist, len(fallback),
        )
        return fallback

    def recommend(self, seeds: list[Seed], count: int) -> list[Suggestion]:
        if not seeds or count <= 0:
            return []

        seed_keys = {(_norm(s.title), _norm(s.artist)) for s in seeds}
        scores: dict[tuple[str, str], float] = defaultdict(float)
        chosen: dict[tuple[str, str], Suggestion] = {}

        with ThreadPoolExecutor(max_workers=min(_WORKERS, len(seeds))) as pool:
            for res in pool.map(self._similar_for_seed, seeds):
                for suggestion, match in res:
                    key = (_norm(suggestion.title), _norm(suggestion.artist))
                    if key in seed_keys:  # never recommend the seeds back
                        continue
                    scores[key] += match
                    chosen.setdefault(key, suggestion)

        ranked = sorted(
            chosen.values(),
            key=lambda s: scores[(_norm(s.title), _norm(s.artist))],
            reverse=True,
        )
        ask = max(count, int(count * _OVER_REQUEST))
        out = ranked[:ask]
        logger.info("Last.fm produced %d candidates from %d seeds.", len(out), len(seeds))
        logger.debug(
            "Last.fm top candidates (by aggregate match score): %s", preview(out)
        )
        return out


def _norm(s: str) -> str:
    return s.strip().lower()


def _to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _parse_similar_tracks(data: dict) -> list[tuple[Suggestion, float]]:
    tracks = (data.get("similartracks") or {}).get("track") or []
    out: list[tuple[Suggestion, float]] = []
    for t in tracks:
        title = (t.get("name") or "").strip()
        artist = ((t.get("artist") or {}).get("name") or "").strip()
        if title and artist:
            out.append((Suggestion(title, artist), _to_float(t.get("match"))))
    return out


def _parse_top_tracks(data: dict) -> list[tuple[Suggestion, float]]:
    tracks = (data.get("toptracks") or {}).get("track") or []
    out: list[tuple[Suggestion, float]] = []
    for t in tracks:
        title = (t.get("name") or "").strip()
        artist = ((t.get("artist") or {}).get("name") or "").strip()
        if title and artist:
            out.append((Suggestion(title, artist), 0.3))  # down-weighted vs real neighbours
    return out
