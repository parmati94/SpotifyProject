"""Last.fm recommender tests — aggregation/weighting/dedupe, no network."""

from backend.core.recommender.base import Seed, Suggestion
from backend.core.recommender.lastfm import LastfmRecommender


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Routes a Last.fm request to a canned payload keyed by method + params."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        method = params["method"]
        if method == "track.getsimilar":
            key = ("track", params["artist"], params["track"])
        elif method == "artist.gettoptracks":
            key = ("toptracks", params["artist"])
        else:
            key = (method,)
        return FakeResp(self.routes.get(key, {}))


def _sim(track, artist, match):
    return {"name": track, "artist": {"name": artist}, "match": str(match)}


def _rec(routes):
    rec = LastfmRecommender("key")
    rec._session = FakeSession(routes)
    return rec


def test_lastfm_aggregates_and_ranks_by_match():
    # "Shared" is similar to BOTH seeds → its summed score (0.5+0.5) tops the singles.
    routes = {
        ("track", "Radiohead", "Karma Police"): {
            "similartracks": {"track": [_sim("No Surprises", "Radiohead", 0.9), _sim("Shared", "X", 0.5)]}
        },
        ("track", "Phoenix", "1901"): {
            "similartracks": {"track": [_sim("Shared", "X", 0.5), _sim("Lisztomania", "Phoenix", 0.8)]}
        },
    }
    rec = _rec(routes)
    out = rec.recommend([Seed("Karma Police", "Radiohead"), Seed("1901", "Phoenix")], 10)
    assert [s.title for s in out] == ["Shared", "No Surprises", "Lisztomania"]


def test_lastfm_excludes_seeds():
    routes = {
        ("track", "A", "a"): {"similartracks": {"track": [_sim("b", "B", 0.9), _sim("a", "A", 0.99)]}}
    }
    out = _rec(routes).recommend([Seed("a", "A")], 10)
    assert [s.title for s in out] == ["b"]  # the seed track itself is dropped


def test_lastfm_artist_fallback_when_no_similar():
    routes = {
        ("track", "A", "a"): {"similartracks": {"track": []}},  # no neighbours
        ("toptracks", "A"): {"toptracks": {"track": [_sim("a2", "A", None), _sim("a3", "A", None)]}},
    }
    rec = _rec(routes)
    out = rec.recommend([Seed("a", "A")], 10)
    assert {s.title for s in out} == {"a2", "a3"}
    assert any(c["method"] == "artist.gettoptracks" for c in rec._session.calls)


def test_lastfm_empty_seeds():
    assert _rec({}).recommend([], 10) == []


def test_lastfm_survives_api_error():
    class Boom(FakeSession):
        def get(self, url, params=None, timeout=None):
            raise RuntimeError("network down")

    rec = LastfmRecommender("key")
    rec._session = Boom({})
    assert rec.recommend([Seed("a", "A")], 10) == []  # degrades, no exception
