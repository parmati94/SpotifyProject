"""Claude recommender tests — parsing + graceful degradation, no network."""

from types import SimpleNamespace

import pytest

from backend.core.recommender.base import RecommenderError, Seed, Suggestion
from backend.core.recommender.claude import ClaudeRecommender, _Item, _SuggestionList


class FakeMessages:
    def __init__(self, parsed=None, raise_exc=None):
        self.parsed = parsed
        self.raise_exc = raise_exc
        self.calls = 0

    def parse(self, **kwargs):
        self.calls += 1
        if self.raise_exc:
            raise self.raise_exc
        return SimpleNamespace(parsed_output=self.parsed)


def _rec(messages):
    rec = ClaudeRecommender("key")
    rec._client = SimpleNamespace(messages=messages)  # bypass lazy SDK import
    return rec


def test_claude_parses_and_filters_blanks():
    parsed = _SuggestionList(songs=[
        _Item(title="Song A", artist="Artist A"),
        _Item(title="  ", artist="No Title"),
        _Item(title="No Artist", artist=""),
    ])
    out = _rec(FakeMessages(parsed=parsed)).recommend([Seed("s", "a")], 5)
    assert out == [Suggestion("Song A", "Artist A")]


def test_claude_empty_seeds_no_call():
    msgs = FakeMessages(parsed=_SuggestionList(songs=[]))
    assert _rec(msgs).recommend([], 5) == []
    assert msgs.calls == 0  # short-circuits before any API call


def test_claude_raises_recommender_error_on_failure():
    # A hard failure (e.g. credits exhausted) surfaces as RecommenderError, not [].
    rec = _rec(FakeMessages(raise_exc=RuntimeError("credit balance too low")))
    with pytest.raises(RecommenderError, match="credit balance too low"):
        rec.recommend([Seed("s", "a")], 5)


def test_claude_handles_empty_result():
    assert _rec(FakeMessages(parsed=_SuggestionList(songs=[]))).recommend([Seed("s", "a")], 5) == []
