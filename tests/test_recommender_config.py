"""Engine availability + resolution — the rules the UI selector is built from."""

from backend.common.config import Settings


def _settings(**over):
    """A Settings instance built without env/validation, so tests can dial individual
    credential/model fields. Only the engine-selection methods are exercised."""
    base = dict(
        recommender="lastfm",
        lastfm_api_key=None,
        gemini_api_key=None,
        gemini_model="gemini-2.5-flash",
        anthropic_api_key=None,
        claude_model="claude-sonnet-4-6",
    )
    base.update(over)
    return Settings.model_construct(**base)


def test_available_engines_are_credential_gated():
    s = _settings(lastfm_api_key="lk", anthropic_api_key="ak")  # no gemini key
    engines = s.available_engines()
    assert [e["id"] for e in engines] == ["lastfm", "claude", "catalog"]


def test_available_engines_always_include_catalog():
    assert _settings().available_engines() == [
        {"id": "catalog", "label": "Spotify catalog", "model": None}
    ]


def test_llm_engines_carry_their_model():
    s = _settings(gemini_api_key="gk", anthropic_api_key="ak")
    by_id = {e["id"]: e for e in s.available_engines()}
    assert by_id["gemini"]["model"] == "gemini-2.5-flash"
    assert by_id["claude"]["model"] == "claude-sonnet-4-6"
    assert by_id["catalog"]["model"] is None


def test_resolve_engine_degrades_without_key():
    s = _settings(lastfm_api_key="lk")  # claude has no key
    assert s.resolve_engine("claude") == "catalog"
    assert s.resolve_engine("lastfm") == "lastfm"


def test_resolve_unknown_engine_degrades():
    assert _settings().resolve_engine("nonsense") == "catalog"
