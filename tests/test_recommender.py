"""Recommender tests — catalog logic and Gemini parsing, no network."""

from types import SimpleNamespace

from backend.core.recommender.base import Seed, Suggestion
from backend.core.recommender.catalog import CatalogRecommender
from backend.core.recommender.gemini import GeminiRecommender


class FakeSpotify:
    def __init__(self, artists: dict[str, str], top_tracks: dict[str, list[dict]]):
        self.artists = artists          # name -> artist id
        self.top_tracks = top_tracks    # artist id -> raw tracks

    def search(self, q, type="artist", limit=1):
        for name, aid in self.artists.items():
            if name in q:
                return {"artists": {"items": [{"id": aid}]}}
        return {"artists": {"items": []}}

    def artist_top_tracks(self, artist_id):
        return {"tracks": self.top_tracks.get(artist_id, [])}


def _track(title, artist):
    return {"name": title, "artists": [{"name": artist}]}


def test_catalog_gathers_seed_artist_top_tracks():
    sp = FakeSpotify(
        artists={"Radiohead": "rh"},
        top_tracks={"rh": [_track("Creep", "Radiohead"), _track("No Surprises", "Radiohead")]},
    )
    rec = CatalogRecommender(sp)
    out = rec.recommend([Seed("Karma Police", "Radiohead")], count=5)
    titles = {s.title for s in out}
    assert titles == {"Creep", "No Surprises"}
    assert all(isinstance(s, Suggestion) for s in out)


def test_catalog_handles_unknown_artist():
    sp = FakeSpotify(artists={}, top_tracks={})
    rec = CatalogRecommender(sp)
    assert rec.recommend([Seed("X", "Unknown Artist")], count=5) == []


def test_catalog_empty_seeds():
    rec = CatalogRecommender(FakeSpotify({}, {}))
    assert rec.recommend([], count=5) == []


def test_gemini_empty_seeds_no_call():
    rec = GeminiRecommender(api_key="x")
    # No seeds -> short-circuits before any client/network use.
    assert rec.recommend([], count=5) == []


def test_gemini_parse_filters_blanks():
    response = SimpleNamespace(
        parsed=[
            SimpleNamespace(title="Good Song", artist="Real Artist"),
            SimpleNamespace(title="  ", artist="Missing Title"),
            SimpleNamespace(title="No Artist", artist=""),
        ]
    )
    out = GeminiRecommender._parse(response)
    assert out == [Suggestion("Good Song", "Real Artist")]


def test_gemini_parse_handles_none_parsed():
    assert GeminiRecommender._parse(SimpleNamespace(parsed=None)) == []
