"""Claude (Anthropic) recommender — the higher-quality LLM option.

Same shape as the Gemini engine: ask the model for similar songs and parse a clean
`{title, artist}` list via structured output (no brittle text parsing). The Anthropic
SDK auto-retries 429/5xx with backoff; a hard failure degrades to an empty list rather
than crashing a playlist build. Like any LLM, output is verified by the resolver before
anything is added.
"""

from __future__ import annotations

import time

from pydantic import BaseModel

from backend.common.logging_config import logger
from .base import Recommender, RecommenderError, Seed, Suggestion, preview

_OVER_REQUEST = 1.25  # ask for ~25% more than needed to absorb resolver misses
_MAX_TOKENS = 8000    # enough for a few hundred {title, artist} pairs


class _Item(BaseModel):
    title: str
    artist: str


class _SuggestionList(BaseModel):
    songs: list[_Item]


class ClaudeRecommender(Recommender):
    def __init__(
        self, api_key: str, model: str = "claude-sonnet-4-6", max_tokens: int = _MAX_TOKENS
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._client = None  # lazily constructed (keeps import side-effect-free)

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    @staticmethod
    def _build_prompt(seeds: list[Seed], count: int) -> str:
        seed_lines = "\n".join(f"- {s.title} — {s.artist}" for s in seeds)
        return (
            "You are a music recommender. Given these seed tracks the listener already "
            f"enjoys, suggest {count} different, real, currently-existing songs they would "
            "also like. Vary the artists, avoid repeating the seed tracks, and do not invent "
            "songs that do not exist.\n\n"
            f"Seed tracks:\n{seed_lines}"
        )

    def recommend(self, seeds: list[Seed], count: int) -> list[Suggestion]:
        if not seeds or count <= 0:
            return []

        ask = max(count, int(count * _OVER_REQUEST))
        prompt = self._build_prompt(seeds, ask)
        logger.debug(
            "Claude: requesting %d suggestions (model=%s) from %d seeds: %s",
            ask, self._model, len(seeds), preview(seeds),
        )
        logger.debug("Claude prompt:\n%s", prompt)
        try:
            started = time.perf_counter()
            response = self._get_client().messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
                output_format=_SuggestionList,
            )
        except Exception as exc:  # noqa: BLE001 — surface the cause (credits/auth/rate limit)
            logger.warning("Claude request failed: %s", exc)
            raise RecommenderError(f"Claude request failed: {exc}") from exc

        parsed = getattr(response, "parsed_output", None)
        if not parsed or not parsed.songs:
            logger.warning("Claude returned no usable suggestions.")
            return []
        out: list[Suggestion] = []
        for item in parsed.songs:
            title = (item.title or "").strip()
            artist = (item.artist or "").strip()
            if title and artist:
                out.append(Suggestion(title=title, artist=artist))
        logger.debug(
            "Claude: %d usable suggestions (of %d raw) in %.2fs: %s",
            len(out), len(parsed.songs), time.perf_counter() - started, preview(out),
        )
        return out
