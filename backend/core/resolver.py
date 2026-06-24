"""Resolve recommender suggestions to real, playable Spotify track URIs.

LLMs invent songs (and fabricate Spotify IDs — verified: 0/10 of Gemini's were
real), so we never trust a suggestion: each is searched on Spotify and only ones
whose returned track actually matches the suggested *artist and title* become URIs.
Several query strategies are tried in order of precision (field-scoped on the primary
artist, then looser free-text, with the LLM's "Series N - " title prefixes stripped),
and each candidate is verified before it's accepted — so a search that drifts to an
unrelated top hit ("Impulse NGHTMRE" → "Nightfall — Calmly") is dropped, not added.
We scan several results per query, since the right track is often ranked just behind
a more popular namesake.

Performance: suggestions are de-duplicated, looked up in a persistent cache, and
the remaining searches run on a small thread pool. Bounded concurrency (default 5)
is ~5x faster than serial without tripping Spotify's per-window rate limit;
spotipy's built-in 429/Retry-After backoff covers the occasional overage.
"""

from __future__ import annotations

import os
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from backend.common.logging_config import logger
from .recommender.base import Suggestion, preview
from .resolver_cache import cache

# Empirically the sweet spot: 5 workers ≈ 5x faster, no rate-limit hits; 10 was
# slower (tripped the limit, forced backoff). Override via env if needed.
_WORKERS = max(1, int(os.getenv("RESOLVER_WORKERS", "5")))

# Scan a handful of results per query, not just the top hit: the right track is often
# ranked behind a more popular namesake ("Crowd Control — Excision" sits below a dozen
# unrelated "Crowd Control"s). We verify each candidate, so going deeper is safe.
_SEARCH_LIMIT = 10

# Splits a credited artist string into individual artists: "Excision & Datsik",
# "A, B feat. C", "A x B" → ["Excision", "Datsik"] etc. Used to verify a search hit
# and to query on the primary artist (Spotify stores collaborators separately, so
# artist:"Excision & Datsik" matches nothing).
_ARTIST_SPLIT = re.compile(r"\s*(?:&|,|/|\bfeat\.?\b|\bft\.?\b|\bx\b|\bvs\.?\b)\s*", re.I)
# A leading "Something - " the LLM prepends from a series/source ("Destroid 5 - Crowd
# Control", "Deadmau5 - Fn Pig") that isn't part of the real track title.
_TITLE_PREFIX = re.compile(r"^.{1,40}?\s+-\s+(?=\S)")
# A leading "The " dropped when comparing artists, so "The Beatles" == "Beatles".
_LEADING_THE = re.compile(r"^the\s+", re.I)


def _norm(s: str) -> str:
    """Lowercase, transliterate accents (é→e, ÿ→y), strip everything but alphanumerics —
    so 'NGHTMRE' == 'Nghtmre', 'Deadmau5' == 'deadmau5', 'Beyoncé' == 'Beyonce', and
    'JAŸ-Z' == 'Jay-Z' when comparing."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _primary_artist(artist: str) -> str:
    """The first credited artist — what we field-scope the query on, since Spotify
    stores collaborators as separate artists."""
    parts = [p for p in _ARTIST_SPLIT.split(artist) if p.strip()]
    return parts[0] if parts else artist


def _title_variants(title: str) -> list[str]:
    """The title plus de-noised forms to try: with a leading 'X - ' prefix dropped and
    with a trailing '(… Remix)'/'[… Edit]' parenthetical removed. Order-preserving,
    de-duped; the original always comes first."""
    variants = [title]
    stripped = _TITLE_PREFIX.sub("", title).strip()
    if stripped:
        variants.append(stripped)
    base = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]\s*$", "", title).strip()
    if base:
        variants.append(base)
    return list(dict.fromkeys(v for v in variants if v))


def _artist_key(s: str) -> str:
    """Comparison key for an artist name: `_norm` with a leading 'The ' dropped, so
    'The Beatles' == 'Beatles'."""
    return _norm(_LEADING_THE.sub("", s.strip()))


def _artist_matches(suggested_artist: str, track_artists: list[str]) -> bool:
    """True if the suggestion's artist genuinely corresponds to the track Spotify
    returned. A search will happily return its top hit for *any* words ("Impulse
    NGHTMRE" → "Nightfall — Calmly"), so we reject a candidate whose artist doesn't
    match. We require an *exact* (normalized) name match, not a substring — substring
    matching let "Excision" match the unrelated band "Indecent Excision". The whole
    suggested string is checked first (so a name containing a split char, e.g.
    "Tyler, The Creator", still matches), then each credited collaborator."""
    actual = {_artist_key(a) for a in track_artists if _artist_key(a)}
    if not actual:
        return False
    if _artist_key(suggested_artist) in actual:
        return True
    return any(_artist_key(p) in actual for p in _ARTIST_SPLIT.split(suggested_artist) if _artist_key(p))


def _title_matches(suggested_title: str, track_title: str) -> bool:
    """True if a suggested title (or one of its de-noised variants) corresponds to the
    track's title — substring either way, so 'Bass Cannon' matches 'Bass Cannon -
    Crankdat Remix' and 'WTF' matches 'WTF!?', but 'WTF' won't match 'Lone Wolf'."""
    actual = _norm(track_title)
    return any(
        v and actual and (v in actual or actual in v)
        for v in (_norm(t) for t in _title_variants(suggested_title))
    )


def _key(suggestion: Suggestion) -> str:
    return f"{suggestion.title.strip().lower()}|{suggestion.artist.strip().lower()}"


def resolve_one(sp, suggestion: Suggestion) -> str | None:
    """Return a Spotify track URI for `suggestion`, or None if no Spotify track matches
    it on both artist and title.

    Tries several queries in order of precision and returns the first result that
    verifies — so an unfindable suggestion drops out (absorbed by the over-request)
    rather than resolving to whatever unrelated track Spotify ranked first."""
    title, artist = suggestion.title, suggestion.artist
    primary = _primary_artist(artist)
    # Most precise first: field-scoped on the primary artist for each title variant,
    # then loose free-text. De-duped, order preserved.
    queries = [f'track:"{tv}" artist:"{primary}"' for tv in _title_variants(title)]
    queries += [f"{title} {artist}", f"{title} {primary}"]
    for q in dict.fromkeys(queries):
        try:
            res = sp.search(q=q, type="track", limit=_SEARCH_LIMIT)
        except Exception as exc:  # noqa: BLE001 — one bad search shouldn't kill the batch
            logger.warning("Spotify search failed for %r: %s", q, exc)
            continue
        for track in res.get("tracks", {}).get("items", []):
            track_artists = [a["name"] for a in track.get("artists", [])]
            if _artist_matches(artist, track_artists) and _title_matches(title, track["name"]):
                logger.debug(
                    "Resolved %s — %s -> %s (%s — %s)",
                    title, artist, track["uri"], track["name"], ", ".join(track_artists),
                )
                return track["uri"]
    logger.debug("No verified Spotify match for %s — %s", title, artist)
    return None


def _resolve_cached(sp, suggestion: Suggestion) -> str | None:
    """resolve_one, but served from / populated into the URI cache."""
    key = _key(suggestion)
    hit = cache.get(key)
    if hit is not None:
        logger.debug("Resolver cache hit: %s — %s -> %s", suggestion.title, suggestion.artist, hit)
        return hit
    uri = resolve_one(sp, suggestion)
    if uri:
        cache.put(key, uri)
    return uri


def resolve_all(
    sp,
    suggestions: list[Suggestion],
    *,
    limit: int | None = None,
    exclude_uris: set[str] | None = None,
    max_workers: int = _WORKERS,
) -> list[str]:
    """Resolve suggestions to URIs: de-dupe → cache/search (parallel) → de-dupe → slice.

    Order is preserved so the recommender's ranking is respected; callers shuffle
    afterwards for variety.
    """
    # 1) Drop duplicate suggestions so we never search the same track twice.
    seen_keys: set[str] = set()
    unique: list[Suggestion] = []
    for s in suggestions:
        k = _key(s)
        if k not in seen_keys:
            seen_keys.add(k)
            unique.append(s)
    if not unique:
        return []
    logger.debug(
        "Resolver: %d suggestions, %d unique after dedupe", len(suggestions), len(unique)
    )

    # 2) Resolve (cache hit or Spotify search) on a bounded pool; map preserves order.
    with ThreadPoolExecutor(max_workers=min(max_workers, len(unique))) as pool:
        resolved = list(pool.map(lambda s: _resolve_cached(sp, s), unique))
    cache.flush()

    # Surface the suggestions that found no Spotify match (LLM hallucinations, typos,
    # regional gaps) — the main reason a build comes up short.
    unresolved = [s for s, uri in zip(unique, resolved) if uri is None]
    if unresolved:
        logger.debug(
            "Resolver: %d/%d suggestions had no Spotify match: %s",
            len(unresolved), len(unique), preview(unresolved),
        )

    # 3) De-dupe URIs, drop excluded, slice to limit.
    seen_uris: set[str] = set(exclude_uris or set())
    uris: list[str] = []
    for uri in resolved:
        if uri is None or uri in seen_uris:
            continue
        seen_uris.add(uri)
        uris.append(uri)
        if limit is not None and len(uris) >= limit:
            break
    logger.info("Resolved %d/%d unique suggestions to playable tracks.", len(uris), len(unique))
    return uris
