"""Smoke tests for the API wiring — routes, schemas, dependency overrides.

No live Spotify/Gemini: the Spotify dependency is overridden with a fake, and the
recommender is overridden to return canned suggestions.
"""

import os

import pytest

os.environ.setdefault("CLIENT_ID", "test-id")
os.environ.setdefault("CLIENT_SECRET", "test-secret")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("RECOMMENDER", "catalog")  # no Gemini key needed

from fastapi.testclient import TestClient  # noqa: E402

from backend import main as controller  # noqa: E402
from backend.deps import get_client, get_recommender  # noqa: E402
from backend.core.recommender.base import Seed, Suggestion  # noqa: E402
from backend.core.spotify_client import SpotifyClient  # noqa: E402


class FakeSp:
    """Just enough spotipy surface for the playlist ops used in these tests."""

    def __init__(self):
        self.created = []
        self.added = []

    def me(self):
        return {"id": "user1"}

    def current_user_top_tracks(self, time_range, limit, offset):
        items = [{"name": f"Song {i}", "artists": [{"name": f"Artist {i}"}]} for i in range(20)]
        return {"items": items}

    def search(self, q, type="track", limit=1):
        return {"tracks": {"items": [{"uri": f"spotify:track:{abs(hash(q)) % 9999}"}]}}

    def current_user_playlists(self, offset=0, limit=50):
        return {"items": [], "total": 0}

    def user_playlist_create(self, user, name, public, collaborative, description):
        self.created.append(name)
        return {"id": "pl1"}

    def playlist_add_items(self, playlist_id, items):
        self.added.extend(items)


class FakeRecommender:
    def recommend(self, seeds, count):
        return [Suggestion(f"Rec {i}", f"RecArtist {i}") for i in range(count)]


@pytest.fixture
def client():
    fake_sp = FakeSp()
    controller.app.dependency_overrides[get_client] = lambda: SpotifyClient(fake_sp)
    controller.app.dependency_overrides[get_recommender] = lambda: FakeRecommender()
    with TestClient(controller.app) as c:
        c.fake_sp = fake_sp
        yield c
    controller.app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_session_unauthenticated(client):
    assert client.get("/api/session").json() == {"authenticated": False, "dev": False}


def test_dev_login_route_absent_when_disabled(client):
    # DEV_AUTH is off in tests, so the bypass route isn't even mounted.
    assert client.get("/dev/login", follow_redirects=False).status_code == 404


def test_login_redirects_to_spotify(client):
    r = client.get("/login", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "accounts.spotify.com" in r.headers["location"]


def test_callback_without_code_fails(client):
    r = client.get("/callback", follow_redirects=False)
    assert r.headers["location"] == "/?login=failure"


def test_create_daily(client):
    r = client.post("/api/playlists/daily")
    assert r.status_code == 200
    assert "Daily playlist created" in r.json()["message"]
    assert client.fake_sp.created  # a playlist was actually created
    assert client.fake_sp.added    # with tracks


def test_recommender_failure_returns_502_with_reason(client):
    # If the engine fails hard (e.g. Claude credits exhausted), the user gets a 502
    # carrying the cause — not a misleading "no recommendations, try again later" 400.
    from backend.core.recommender.base import RecommenderError

    class Failing:
        def recommend(self, seeds, count):
            raise RecommenderError("Claude request failed: credit balance is too low")

    controller.app.dependency_overrides[get_recommender] = lambda: Failing()
    r = client.post("/api/playlists/daily")
    assert r.status_code == 502
    assert "credit balance is too low" in r.json()["detail"]


def test_from_playlist_validation_rejects_bad_count(client):
    r = client.post(
        "/api/playlists/from-playlist",
        json={"source_playlist": "src", "target_playlist": "tgt", "num_songs": 9999},
    )
    assert r.status_code == 422  # pydantic rejects num_songs > 200


def _settings_with_keys():
    # Last.fm + Claude keyed (Gemini deliberately not), built without env/validation.
    from backend.common.config import Settings

    return Settings.model_construct(
        recommender="lastfm",
        lastfm_api_key="lk",
        gemini_api_key=None,
        gemini_model="gemini-2.5-flash",
        anthropic_api_key="ak",
        claude_model="claude-sonnet-4-6",
    )


def test_recommender_status_lists_available_and_active(client):
    from backend.common.config import get_settings

    controller.app.dependency_overrides[get_settings] = _settings_with_keys
    data = client.get("/api/recommender").json()
    assert [e["id"] for e in data["available"]] == ["lastfm", "claude", "catalog"]
    assert data["active"] == "lastfm"  # the configured default
    claude = next(e for e in data["available"] if e["id"] == "claude")
    assert claude["model"] == "claude-sonnet-4-6"


def test_recommender_switch_persists_in_session(client):
    from backend.common.config import get_settings

    controller.app.dependency_overrides[get_settings] = _settings_with_keys
    assert client.put("/api/recommender", json={"engine": "claude"}).json()["active"] == "claude"
    # Same client keeps the session cookie, so the choice survives the next request.
    assert client.get("/api/recommender").json()["active"] == "claude"


def test_recommender_rejects_unavailable_engine(client):
    from backend.common.config import get_settings

    controller.app.dependency_overrides[get_settings] = _settings_with_keys
    r = client.put("/api/recommender", json={"engine": "gemini"})  # no Gemini key
    assert r.status_code == 400
