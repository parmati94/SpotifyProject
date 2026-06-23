"""Resolver tests — verify suggestions become real URIs, with no live Spotify calls."""

from backend.core.recommender.base import Suggestion
from backend.core.resolver import resolve_all, resolve_one


class FakeSpotify:
    """Minimal stand-in for spotipy. `catalog` maps a query substring -> track uri."""

    def __init__(self, catalog: dict[str, str], *, fail_on: str | None = None):
        self.catalog = catalog
        self.fail_on = fail_on
        self.queries: list[str] = []

    def search(self, q, type="track", limit=1):
        self.queries.append(q)
        if self.fail_on and self.fail_on in q:
            raise RuntimeError("simulated Spotify error")
        for needle, uri in self.catalog.items():
            if needle in q:
                return {"tracks": {"items": [{"uri": uri}]}}
        return {"tracks": {"items": []}}


def test_resolve_one_strict_hit():
    sp = FakeSpotify({'track:"Karma Police"': "spotify:track:KP"})
    uri = resolve_one(sp, Suggestion("Karma Police", "Radiohead"))
    assert uri == "spotify:track:KP"
    # Strict query should be tried first and succeed without the loose fallback.
    assert len(sp.queries) == 1


def test_resolve_one_falls_back_to_loose_query():
    # Strict (quoted) query misses; loose free-text query hits.
    sp = FakeSpotify({"Such Great Heights The Postal Service": "spotify:track:SGH"})
    uri = resolve_one(sp, Suggestion("Such Great Heights", "The Postal Service"))
    assert uri == "spotify:track:SGH"
    assert len(sp.queries) == 2  # strict then loose


def test_resolve_one_returns_none_when_unfindable():
    sp = FakeSpotify({})
    assert resolve_one(sp, Suggestion("Made Up Song", "Nobody")) is None


def test_resolve_one_survives_search_error():
    sp = FakeSpotify({}, fail_on="track:")  # strict query raises
    # The loose query still runs and finds nothing -> None, no exception bubbles up.
    assert resolve_one(sp, Suggestion("X", "Y")) is None


def test_resolve_all_dedupes_and_respects_limit():
    sp = FakeSpotify(
        {
            "A1": "spotify:track:1",
            "A2": "spotify:track:2",
            "A3": "spotify:track:3",
        }
    )
    suggestions = [
        Suggestion("A1", "x"),
        Suggestion("A2", "x"),
        Suggestion("A2", "x"),  # duplicate resolves to same uri -> dropped
        Suggestion("A3", "x"),
    ]
    uris = resolve_all(sp, suggestions, limit=2)
    assert uris == ["spotify:track:1", "spotify:track:2"]


def test_resolve_all_excludes_existing():
    sp = FakeSpotify({"A1": "spotify:track:1", "A2": "spotify:track:2"})
    uris = resolve_all(
        sp,
        [Suggestion("A1", "x"), Suggestion("A2", "x")],
        exclude_uris={"spotify:track:1"},
    )
    assert uris == ["spotify:track:2"]


def test_resolve_all_skips_unresolvable():
    sp = FakeSpotify({"Real": "spotify:track:R"})
    uris = resolve_all(sp, [Suggestion("Ghost", "x"), Suggestion("Real", "x")])
    assert uris == ["spotify:track:R"]


def test_resolve_all_dedupes_suggestions_before_searching():
    # Same track three times (case/whitespace-insensitive) → searched once, not thrice.
    sp = FakeSpotify({'track:"Song A"': "spotify:track:A"})
    suggestions = [
        Suggestion("Song A", "x"),
        Suggestion("Song A", "x"),
        Suggestion(" song a ", "X"),
    ]
    assert resolve_all(sp, suggestions) == ["spotify:track:A"]
    assert len(sp.queries) == 1  # one strict query for the single unique suggestion
