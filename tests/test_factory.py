"""Factory selection tests — the right engine is built per effective_recommender."""

from types import SimpleNamespace

from backend.core.recommender.catalog import CatalogRecommender
from backend.core.recommender.claude import ClaudeRecommender
from backend.core.recommender.factory import build_recommender
from backend.core.recommender.gemini import GeminiRecommender
from backend.core.recommender.lastfm import LastfmRecommender


def _settings(engine):
    # Duck-typed stand-in for Settings — build_recommender only reads these attrs.
    return SimpleNamespace(
        effective_recommender=engine,
        lastfm_api_key="lk",
        gemini_api_key="gk",
        gemini_model="gemini-2.5-flash",
        anthropic_api_key="ak",
        claude_model="claude-sonnet-4-6",
    )


def test_factory_builds_lastfm():
    assert isinstance(build_recommender(_settings("lastfm"), None), LastfmRecommender)


def test_factory_builds_gemini():
    assert isinstance(build_recommender(_settings("gemini"), None), GeminiRecommender)


def test_factory_builds_claude():
    assert isinstance(build_recommender(_settings("claude"), None), ClaudeRecommender)


def test_factory_builds_catalog():
    assert isinstance(build_recommender(_settings("catalog"), None), CatalogRecommender)
