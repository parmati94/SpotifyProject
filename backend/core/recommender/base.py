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


@dataclass(frozen=True)
class VibeResult:
    """A vibe-mode build: the suggested tracks plus an optional LLM-authored playlist
    name and description. `name`/`description` are None when naming wasn't requested or
    the model didn't return them; the caller supplies a fallback name in that case."""

    suggestions: list[Suggestion]
    name: str | None = None
    description: str | None = None


@runtime_checkable
class VibeRecommender(Protocol):
    """A recommender that can build from a free-text "vibe" instead of seed tracks.

    Only the LLM engines implement this — interpreting natural language ("rainy sunday
    coffee-shop jazz") is exactly what the data engines (lastfm/catalog) structurally
    can't do. Same contract as `recommend`: over-request is allowed, "no results" returns
    an empty `VibeResult`, and a hard engine failure raises `RecommenderError`.

    When `seeds` is given (a sample of an existing playlist), the build is a *transform*:
    regenerate that playlist with the free-text instruction applied — see `vibe_prompt`."""

    def recommend_vibe(
        self, description: str, count: int, *, name_it: bool, seeds: list[Seed] | None = None
    ) -> VibeResult:
        ...


# The vibe-mode prompt is shared verbatim by every LLM engine (the model interprets the
# request; only the API plumbing differs per engine), so it lives here rather than being
# copy-pasted into each. Two variants: a pure free-text vibe, and — when `seeds` from an
# existing playlist are supplied — a transform that regenerates that playlist with one change.
_VIBE_QUALITY_RULES = (
    "- Cohesion beats variety. Every song must match the requested energy and mood: "
    "a high-energy/aggressive request gets zero mellow, chill, or sentimental "
    "tracks, and vice versa. When in doubt, leave it out.\n"
    "- Never pad. If you cannot find enough songs that strongly fit, return fewer — "
    "a shorter on-vibe playlist beats a padded one with off-vibe filler.\n"
    "- Prefer different artists, but only among songs that already fit; never trade "
    "fit for variety.\n"
    "- Only real, officially released songs available on major streaming "
    "services — prefer original studio releases, and avoid bootleg remixes, "
    "mashups, white-labels, and any title you are not confident exists. Do not "
    "invent titles or artists."
)


def _naming_clause(name_it: bool) -> str:
    return (
        " Also provide a short, evocative playlist name (at most 40 characters) and a "
        "single-sentence description that captures the vibe."
        if name_it
        else " Leave playlist_name and playlist_description empty."
    )


def vibe_prompt(
    description: str, count: int, *, name_it: bool, seeds: list[Seed] | None = None
) -> str:
    """Build the vibe-mode prompt shared by all LLM engines.

    Without `seeds`: a pure free-text vibe ("rainy sunday coffee-shop jazz"). With `seeds`
    (a recency-weighted sample of an existing playlist): a *transform* — regenerate that
    playlist with the instruction applied, shifting the dimension the listener named and
    preserving the rest. Either way the same quality/anti-hallucination rules apply."""
    naming = _naming_clause(name_it)
    if seeds:
        seed_lines = "\n".join(f"- {s.title} — {s.artist}" for s in seeds)
        return (
            "You are an expert music curator. The listener has an existing playlist and "
            "wants a NEW playlist derived from it, with one change applied.\n\n"
            f'Their instruction: "{description}".\n\n'
            f"Reference playlist (a sample of its tracks):\n{seed_lines}\n\n"
            "Read the reference playlist to understand its character — genre/sub-genre, "
            "mood, energy or intensity level, era, and the kind of artists in it. Then "
            "apply the instruction as a transformation: shift the dimension the listener "
            "asked to change, and preserve everything they did NOT mention. Suggest up to "
            f"{count} real, currently-existing songs for the transformed playlist.\n\n"
            "Rules:\n"
            "- This is a regeneration, not an edit. Suggest new tracks that fit the "
            "transformed character. You may keep a few reference tracks where they still "
            "fit, but do not simply copy the playlist.\n"
            "- Honor the instruction decisively. 'Less hardcore' means clearly softer "
            "across the whole playlist, not a couple of token mellow tracks.\n"
            "- Preserve the un-mentioned character: keep the reference's genre family, era, "
            "and overall taste except where the instruction overrides them.\n"
            f"{_VIBE_QUALITY_RULES}"
            f"{naming}"
        )
    return (
        "You are an expert music curator. Build a tightly cohesive playlist for this "
        f'listener request: "{description}".\n\n'
        "First read the request for its specific intent — genre/sub-genre, mood, energy "
        "or intensity level, era, and any activity or setting. Then suggest up to "
        f"{count} real, currently-existing songs where EVERY track clearly fits ALL of "
        "those dimensions.\n\n"
        "Rules:\n"
        f"{_VIBE_QUALITY_RULES}"
        f"{naming}"
    )
