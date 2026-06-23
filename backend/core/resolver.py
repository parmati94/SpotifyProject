"""Resolve recommender suggestions to real, playable Spotify track URIs.

LLMs invent songs (and fabricate Spotify IDs — verified: 0/10 of Gemini's were
real), so we never trust a suggestion: each is searched on Spotify and only ones
that actually resolve become URIs. A strict field-scoped query is tried first,
then a looser free-text query before giving up.

Performance: suggestions are de-duplicated, looked up in a persistent cache, and
the remaining searches run on a small thread pool. Bounded concurrency (default 5)
is ~5x faster than serial without tripping Spotify's per-window rate limit;
spotipy's built-in 429/Retry-After backoff covers the occasional overage.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from backend.common.logging_config import logger
from .recommender.base import Suggestion, preview
from .resolver_cache import cache

# Empirically the sweet spot: 5 workers ≈ 5x faster, no rate-limit hits; 10 was
# slower (tripped the limit, forced backoff). Override via env if needed.
_WORKERS = max(1, int(os.getenv("RESOLVER_WORKERS", "5")))


def _key(suggestion: Suggestion) -> str:
    return f"{suggestion.title.strip().lower()}|{suggestion.artist.strip().lower()}"


def resolve_one(sp, suggestion: Suggestion) -> str | None:
    """Return a Spotify track URI for `suggestion`, or None if it can't be found."""
    queries = (
        f'track:"{suggestion.title}" artist:"{suggestion.artist}"',  # strict
        f"{suggestion.title} {suggestion.artist}",                   # loose fallback
    )
    for kind, q in zip(("strict", "loose"), queries):
        try:
            res = sp.search(q=q, type="track", limit=1)
        except Exception as exc:  # noqa: BLE001 — one bad search shouldn't kill the batch
            logger.warning("Spotify search failed for %r: %s", q, exc)
            continue
        items = res.get("tracks", {}).get("items", [])
        if items:
            uri = items[0]["uri"]
            logger.debug(
                "Resolved %s — %s via %s query -> %s",
                suggestion.title, suggestion.artist, kind, uri,
            )
            return uri
    logger.debug("No Spotify match for %s — %s", suggestion.title, suggestion.artist)
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
