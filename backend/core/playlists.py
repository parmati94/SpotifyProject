"""Playlist business logic — the driver functions behind the API routes.

Each function orchestrates: gather seeds → recommend → resolve to real URIs → write to
Spotify. Routes stay thin by calling these; these stay testable by depending only on a
`SpotifyClient` and a `Recommender`.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime

from backend.common.constants import APP_PLAYLIST_MARKER
from backend.common.logging_config import logger
from .recommender.base import Recommender, Seed, VibeRecommender
from .resolver import resolve_all
from .spotify_client import SpotifyClient


@dataclass
class PlaylistResult:
    """Outcome of a create/extend op. `track_count` is the playlist's *full* track total
    after the op — the API returns it so the UI can show the right number immediately,
    since Spotify's playlist-list endpoint reports a stale 0 for a few seconds after
    creation. `playlist_id` lets the UI patch the exact playlist even when several share a
    name. All but `message` are None for informational no-op messages."""

    message: str
    playlist_id: str | None = None
    name: str | None = None
    track_count: int | None = None

WEEKLY_PLAYLIST_NAME = "Weekly Extended Playlist"
DEFAULT_DAILY_COUNT = 40
WEEKLY_EXTEND_COUNT = 40
DEFAULT_VIBE_COUNT = 40
_MAX_PLAYLIST_SONGS = 200
# Vibe builds cap lower than seed-from-playlist: a single free-text vibe has a real quality
# ceiling (the LLM exhausts on-vibe picks and drifts well before 200; even the Last.fm fill
# hits genre exhaustion). 100 is a generous upper bound that stays mostly on-vibe.
_MAX_VIBE_SONGS = 100
# Fallback name when the user opts out of AI naming (or the LLM returns none); keeps the
# date-named-daily heuristic in is_app_created clear of vibe playlists.
_VIBE_NAME_MAX = 40

# Hybrid vibe build (see PLANNING §12.2): the LLM interprets the vibe and supplies a clean
# *core* (its top picks); Last.fm similarity grounds and extends it. A/B/C testing showed the
# LLM over-concentrates on a few artists and drifts as it pads for count, while a Last.fm fill
# seeded by the LLM's clean head adds on-vibe variety — so we deliberately cap the LLM core at
# ~60% of the target and fill the rest, rather than only filling when the LLM comes up short.
# Thin cores are protected by the same ratio: fill never outweighs the core (it stays a
# majority), so a niche vibe yields a shorter playlist instead of a fill-dominated, drifty one.
_VIBE_CORE_FRACTION = 0.6   # LLM provides ~60% of the playlist; Last.fm fills the remainder
_VIBE_FILL_SEED_HEAD = 15   # how many top core tracks to seed Last.fm with

# When a vibe build attaches a source playlist (the "transform" mode — regenerate this
# playlist with a change applied), we hand the LLM a recency-weighted sample of that
# playlist as reference. Capped higher than the default 50 seeds: more reference better
# conveys a playlist's character, and `playlist_seeds` already scales the sample down for
# smaller playlists, so 100 is a ceiling, not a fixed cost.
_VIBE_SOURCE_SEED_MAX = 100

# Matches the daily naming format (e.g. "Jun-23-2026") — used to recognize dailies
# created before the description marker existed.
_DAILY_NAME_RE = re.compile(r"^[A-Z][a-z]{2}-\d{2}-\d{4}$")


def daily_playlist_name(today: datetime | None = None) -> str:
    """Daily playlists are named by date, e.g. 'Jun-22-2026'."""
    return (today or datetime.today()).strftime("%b-%d-%Y")


def is_app_created(name: str, description: str | None) -> bool:
    """Whether a playlist was made by this app. Primary signal is the description marker
    (reliable, set on everything we create going forward); the name heuristic backfills
    playlists created before the marker existed (the date-named daily, the weekly)."""
    if description and APP_PLAYLIST_MARKER in description:
        return True
    return name == WEEKLY_PLAYLIST_NAME or bool(_DAILY_NAME_RE.match(name))


def _recommend_uris(
    client: SpotifyClient,
    recommender: Recommender,
    seeds: list[Seed],
    count: int,
    *,
    exclude_uris: set[str] | None = None,
) -> list[str]:
    """seeds → recommender → resolve → dedupe → shuffle → slice to `count`."""
    if not seeds:
        return []
    logger.debug(
        "Build pipeline: %d seeds, requesting %d tracks (excluding %d existing)",
        len(seeds), count, len(exclude_uris or ()),
    )
    suggestions = recommender.recommend(seeds, count)
    logger.debug("Build pipeline: recommender returned %d suggestions; resolving", len(suggestions))
    uris = resolve_all(client.sp, suggestions, limit=count, exclude_uris=exclude_uris)
    random.shuffle(uris)
    logger.debug("Build pipeline: %d playable tracks after resolve/dedupe/slice", len(uris))
    return uris


def create_daily_playlist(
    client: SpotifyClient, recommender: Recommender, count: int = DEFAULT_DAILY_COUNT
) -> PlaylistResult:
    seeds = client.top_track_seeds()
    uris = _recommend_uris(client, recommender, seeds, count)
    if not uris:
        raise ValueError("No playable recommendations were found. Try again later.")
    name = daily_playlist_name()
    pid = client.create_playlist(client.current_user_id(), name, uris, description=APP_PLAYLIST_MARKER)
    logger.info("Daily playlist created: %s (%d tracks)", name, len(uris))
    return PlaylistResult(f"Daily playlist created with name: {name}", pid, name, len(uris))


def extend_weekly_playlist(client: SpotifyClient, recommender: Recommender) -> PlaylistResult:
    playlist_id = client.find_playlist_id(WEEKLY_PLAYLIST_NAME)
    if playlist_id is None:
        logger.info("%s does not exist; creating it.", WEEKLY_PLAYLIST_NAME)
        seeds = client.top_track_seeds()
        uris = _recommend_uris(client, recommender, seeds, WEEKLY_EXTEND_COUNT)
        if not uris:
            raise ValueError("No playable recommendations were found. Try again later.")
        pid = client.create_playlist(
            client.current_user_id(), WEEKLY_PLAYLIST_NAME, uris, description=APP_PLAYLIST_MARKER
        )
        return PlaylistResult(
            f"Playlist created with name: {WEEKLY_PLAYLIST_NAME}", pid, WEEKLY_PLAYLIST_NAME, len(uris)
        )

    existing = client.playlist_track_uris(playlist_id)
    seeds = client.top_track_seeds()
    uris = _recommend_uris(
        client, recommender, seeds, WEEKLY_EXTEND_COUNT, exclude_uris=existing
    )
    if not uris:
        raise ValueError("No new playable recommendations were found to add.")
    client.add_tracks(playlist_id, uris)
    logger.info("Extended %s by %d tracks.", WEEKLY_PLAYLIST_NAME, len(uris))
    return PlaylistResult(
        f"Weekly playlist extended by {len(uris)} tracks.",
        playlist_id,
        WEEKLY_PLAYLIST_NAME,
        len(existing) + len(uris),  # full total after the add, for the UI count patch
    )


def delete_daily_playlists(client: SpotifyClient) -> str:
    name = daily_playlist_name()
    ids = client.playlist_ids_by_name(name)
    if not ids:
        return f"No playlists exist with name: {name}"
    deleted = client.delete_playlists(ids)
    message = f"Deleted {deleted} playlist(s) with name: {name}"
    logger.info(message)
    return message


def create_playlist_from_playlist(
    client: SpotifyClient,
    recommender: Recommender,
    source_name: str,
    target_name: str,
    count: int,
) -> PlaylistResult:
    source_id = client.find_playlist_id(source_name)
    if source_id is None:
        return PlaylistResult("Playlist creation failed. Source playlist must already exist.")

    count = max(1, min(count, _MAX_PLAYLIST_SONGS))
    seeds = client.playlist_seeds(source_id)
    if not seeds:
        return PlaylistResult(f"Source playlist '{source_name}' has no usable tracks to seed from.")

    uris = _recommend_uris(client, recommender, seeds, count)
    if not uris:
        raise ValueError("No playable recommendations were found. Try again later.")
    pid = client.create_playlist(
        client.current_user_id(), target_name, uris, description=APP_PLAYLIST_MARKER
    )
    logger.info("Playlist created: %s (%d tracks)", target_name, len(uris))
    return PlaylistResult(f"Playlist created: {target_name}", pid, target_name, len(uris))


def _vibe_fallback_name(description: str) -> str:
    """Name for a vibe playlist when AI naming is off/unavailable — the trimmed vibe text."""
    text = " ".join(description.split())[:_VIBE_NAME_MAX].strip()
    return f"Vibe: {text}" if text else "Vibe playlist"


def _seeds_from_uris(client: SpotifyClient, uris: list[str]) -> list[Seed]:
    """Resolve verified track URIs back to {title, artist} seeds for the fill engine —
    canonical Spotify metadata makes cleaner Last.fm seeds than the LLM's raw titles."""
    if not uris:
        return []
    try:
        tracks = client.sp.tracks(uris).get("tracks", [])
    except Exception as exc:  # noqa: BLE001 — fill is best-effort; skip it on a lookup failure
        logger.warning("Vibe fill: seed lookup failed, skipping fill: %s", exc)
        return []
    seeds: list[Seed] = []
    for t in tracks:
        if not t:
            continue
        title = (t.get("name") or "").strip()
        artists = t.get("artists") or []
        artist = (artists[0].get("name") or "").strip() if artists else ""
        if title and artist:
            seeds.append(Seed(title, artist))
    return seeds


def _hybrid_blend(
    client: SpotifyClient, fill_recommender: Recommender, llm_uris: list[str], target: int
) -> list[str]:
    """Blend the LLM's clean *core* with a grounded Last.fm fill (the "B" strategy).

    Takes the LLM's top ~`_VIBE_CORE_FRACTION` of the target as the core (its highest-ranked,
    cleanest picks — the drift and artist over-concentration show up further down the list),
    then fills the rest from Last.fm similarity seeded by the head of that core. Last.fm's
    cross-seed aggregation extends the vibe with real, co-listened tracks (grounded, no
    hallucination) and broadens artist variety. The fill never outweighs the core — the final
    total is capped at `core / _VIBE_CORE_FRACTION` — so a thin core (niche vibe the LLM
    couldn't fill) yields a shorter playlist rather than a fill-dominated, drifty one.

    Best-effort: any Last.fm/lookup miss just returns the core as-is."""
    core = llm_uris[: max(1, round(target * _VIBE_CORE_FRACTION))]
    # Keep the LLM core a majority: cap the total at core / fraction (≈ target for a healthy
    # core, less for a thin one), and never exceed the requested target.
    max_total = min(target, round(len(core) / _VIBE_CORE_FRACTION))
    need = max_total - len(core)
    if need <= 0:
        return core
    seeds = _seeds_from_uris(client, core[:_VIBE_FILL_SEED_HEAD])
    if not seeds:
        return core
    logger.debug(
        "Vibe hybrid: LLM core=%d (of %d resolved), filling %d from Last.fm (target=%d)",
        len(core), len(llm_uris), need, target,
    )
    suggestions = fill_recommender.recommend(seeds, need)
    fill = resolve_all(client.sp, suggestions, limit=need, exclude_uris=set(core))
    logger.info(
        "Vibe hybrid: %d LLM core + %d Last.fm fill = %d tracks (target %d).",
        len(core), len(fill), len(core) + len(fill), target,
    )
    return core + fill


def create_vibe_playlist(
    client: SpotifyClient,
    recommender: VibeRecommender,
    description: str,
    count: int = DEFAULT_VIBE_COUNT,
    *,
    name_it: bool = True,
    fill_recommender: Recommender | None = None,
    source_playlist: str | None = None,
) -> PlaylistResult:
    """Build a playlist from a free-text vibe via an LLM. The engine returns the song
    suggestions plus (when `name_it`) a name/description; we resolve to real URIs and
    write the playlist, falling back to a name derived from the vibe text if needed.

    When `source_playlist` is given, the build is a *transform*: a recency-weighted sample
    of that playlist is handed to the LLM as reference and the vibe text is applied as a
    change to it (regenerate, not edit — see `vibe_prompt`).

    When `fill_recommender` is supplied (Last.fm), the build is a hybrid: the LLM's clean
    core plus a grounded Last.fm fill — see `_hybrid_blend`. Off by default (None) so callers
    without a Last.fm key get the raw LLM list unchanged."""
    description = description.strip()
    if not description:
        raise ValueError("Describe the vibe you want before generating.")
    count = max(1, min(count, _MAX_VIBE_SONGS))

    seeds = None
    if source_playlist:
        source_id = client.find_playlist_id(source_playlist)
        if source_id is None:
            raise ValueError(f"Source playlist '{source_playlist}' was not found.")
        seeds = client.playlist_seeds(source_id, limit=_VIBE_SOURCE_SEED_MAX)
        if not seeds:
            raise ValueError(f"Source playlist '{source_playlist}' has no usable tracks to build from.")

    result = recommender.recommend_vibe(description, count, name_it=name_it, seeds=seeds)
    logger.debug("Vibe pipeline: engine returned %d suggestions; resolving", len(result.suggestions))
    uris = resolve_all(client.sp, result.suggestions, limit=count)
    if not uris:
        raise ValueError("No playable songs were found for that vibe. Try rewording it.")
    # Hybrid blend: keep the LLM's clean core, ground/extend the rest from Last.fm (more
    # cohesion + artist variety than letting the LLM pad for count). Falls through to the raw
    # LLM list when no Last.fm key is configured.
    if fill_recommender is not None:
        uris = _hybrid_blend(client, fill_recommender, uris, count)
    random.shuffle(uris)

    name = result.name if (name_it and result.name) else _vibe_fallback_name(description)
    # The app marker tags it as ours; prefix the LLM blurb when there is one.
    playlist_description = (
        f"{result.description} {APP_PLAYLIST_MARKER}" if result.description else APP_PLAYLIST_MARKER
    )
    pid = client.create_playlist(
        client.current_user_id(), name, uris, description=playlist_description
    )
    logger.info("Vibe playlist created: %s (%d tracks)", name, len(uris))
    return PlaylistResult(f"Vibe playlist created: {name}", pid, name, len(uris))
