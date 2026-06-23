"""Thread-safe, persistent cache of resolved Spotify URIs.

Maps a normalized `title|artist` key to a verified track URI so repeat
recommendations (which overlap heavily for one user over time) skip the Spotify
search entirely. Only *hits* are cached — a miss might become findable later, so
we re-search those. Persisted as JSON; safe for the resolver's worker threads.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from backend.common.logging_config import logger

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / ".cache" / "resolver_cache.json"


class ResolverCache:
    def __init__(self, path: str | os.PathLike | None) -> None:
        self.enabled = True
        self._path = Path(path) if path else None
        self._lock = threading.Lock()
        self._data: dict[str, str] = {}
        self._loaded = False
        self._dirty = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if self._path and self._path.exists():
            try:
                self._data = json.loads(self._path.read_text())
                logger.info("Resolver cache loaded (%d entries).", len(self._data))
            except Exception as exc:  # noqa: BLE001 — a bad cache file shouldn't break resolving
                logger.warning("Resolver cache load failed: %s", exc)

    def get(self, key: str) -> str | None:
        if not self.enabled:
            return None
        with self._lock:
            self._ensure_loaded()
            return self._data.get(key)

    def put(self, key: str, uri: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._ensure_loaded()
            if self._data.get(key) != uri:
                self._data[key] = uri
                self._dirty = True

    def flush(self) -> None:
        """Persist pending changes once (called after a resolve batch)."""
        if not self.enabled or not self._path:
            return
        with self._lock:
            if not self._dirty:
                return
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self._data))
                tmp.replace(self._path)  # atomic
                self._dirty = False
            except Exception as exc:  # noqa: BLE001
                logger.warning("Resolver cache save failed: %s", exc)

    def clear(self) -> None:
        with self._lock:
            self._data = {}
            self._loaded = True
            self._dirty = False


# Singleton used by the resolver. Path overridable via env (kept out of pydantic
# settings since it's a local operational knob, like LOG_LEVEL in logging_config).
cache = ResolverCache(os.getenv("RESOLVER_CACHE_PATH", str(_DEFAULT_PATH)))
