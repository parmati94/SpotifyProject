"""Seeding tests — blended/deduped/capped top tracks, recency-weighted playlist sample."""

import random

from backend.core.recommender.base import Seed
from backend.core.spotify_client import SpotifyClient, _recency_weighted_sample


class FakeSp:
    def __init__(self, top=None, playlist=None):
        self._top = top or {}
        self._playlist = playlist or []

    def current_user_top_tracks(self, time_range, limit, offset):
        return self._top.get(time_range, {"items": []})

    def playlist_items(self, playlist_id, offset=0, limit=100, fields=None):
        page = self._playlist[offset : offset + limit]
        return {"items": page, "total": len(self._playlist)}


def _t(name, artist="x"):
    return {"name": name, "artists": [{"name": artist}]}


def test_top_seeds_blend_and_dedupe():
    top = {
        "short_term": {"items": [_t("A"), _t("B")]},
        "medium_term": {"items": [_t("B"), _t("C")]},  # B duplicates short_term
        "long_term": {"items": [_t("D")]},
    }
    seeds = SpotifyClient(FakeSp(top=top)).top_track_seeds(limit=10)
    assert sorted(s.title for s in seeds) == ["A", "B", "C", "D"]  # union, deduped


def test_top_seeds_respects_cap():
    top = {"short_term": {"items": [_t(f"S{i}") for i in range(30)]}}
    assert len(SpotifyClient(FakeSp(top=top)).top_track_seeds(limit=10)) == 10


def test_top_seeds_empty_raises():
    import pytest

    with pytest.raises(ValueError):
        SpotifyClient(FakeSp(top={})).top_track_seeds()


def test_playlist_seeds_count_and_membership():
    items = [
        {"added_at": f"2020-01-{i:02d}T00:00:00Z", "track": _t(f"T{i}")} for i in range(1, 21)
    ]
    seeds = SpotifyClient(FakeSp(playlist=items)).playlist_seeds("pl1", limit=5)
    assert len(seeds) == 5
    assert all(s.title.startswith("T") for s in seeds)


def test_recency_weighted_sample_favors_recent():
    random.seed(42)
    newest_first = [Seed(str(i), "x") for i in range(100)]  # index 0 = newest
    picks = []
    for _ in range(200):
        picks += [int(s.title) for s in _recency_weighted_sample(newest_first, 10)]
    # Linear recency weighting -> expected index ~33; assert clearly below the midpoint.
    assert sum(picks) / len(picks) < 40
