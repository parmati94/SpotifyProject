"""The recommendation seam.

Everything that needs song suggestions depends on the `Recommender` protocol, never
on a concrete engine. That keeps the engine swappable: Gemini today, a Spotify-native
catalog fallback, or a local model tomorrow — without touching callers.

A recommender deals only in plain `{title, artist}` data. Turning a suggestion into a
real, playable Spotify URI is the resolver's job (`core.resolver`), so engines stay
free of Spotify specifics and easy to unit-test.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


def preview(items, limit: int = 10) -> str:
    """Compact 'Title — Artist, ...' rendering of seeds/suggestions for DEBUG logs,
    truncated to `limit` with a '(+N more)' tail so big lists stay one readable line.
    Works for anything with .title/.artist (both Seed and Suggestion)."""
    shown = ", ".join(f"{i.title} — {i.artist}" for i in items[:limit])
    extra = len(items) - limit
    return f"{shown} (+{extra} more)" if extra > 0 else (shown or "(none)")


class RecommenderError(RuntimeError):
    """An engine failed hard (auth, exhausted credits, rate limit, network) after its
    own retries. Distinct from "no results" — surfaced to the user with the cause,
    instead of silently producing an empty playlist and saying "try again later"."""


@dataclass(frozen=True)
class Seed:
    """A track the user already likes, used to steer recommendations."""

    title: str
    artist: str


@dataclass(frozen=True)
class Suggestion:
    """A recommended track, not yet verified against Spotify."""

    title: str
    artist: str


@runtime_checkable
class Recommender(Protocol):
    def recommend(self, seeds: list[Seed], count: int) -> list[Suggestion]:
        """Return up to ~`count` suggestions similar to `seeds`.

        Implementations may return more than `count` (callers over-request to absorb
        resolver misses) and should never raise for "no results" — return an empty
        list instead.
        """
        ...
