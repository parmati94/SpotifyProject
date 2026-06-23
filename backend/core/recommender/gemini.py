"""Gemini-backed recommender (the default engine).

Asks Gemini for similar songs and returns them as plain `{title, artist}` suggestions.
We use structured output (a JSON schema) so there is no brittle text parsing, and we
deliberately over-request to absorb the resolver dropping hallucinated/unfindable tracks.

The client is created lazily so importing this module never requires the SDK to dial out,
and a transient API error degrades to an empty list rather than crashing a playlist build.
"""

from __future__ import annotations

import time

from pydantic import BaseModel

from backend.common.logging_config import logger
from .base import Recommender, RecommenderError, Seed, Suggestion, preview

# Over-request multiplier: ask for ~25% more than needed so resolver misses
# (hallucinated songs, punctuation mismatches) still leave enough real tracks.
_OVER_REQUEST = 1.25
_MAX_RETRIES = 3


class _SuggestionSchema(BaseModel):
    """Shape Gemini must return for each item (drives `response_schema`)."""

    title: str
    artist: str


class GeminiRecommender(Recommender):
    def __init__(
        self, api_key: str, model: str = "gemini-2.5-flash", temperature: float = 1.0
    ) -> None:
        self._api_key = api_key
        self._model = model
        # Gemini 3 flash degrades badly (huge latency) at low temperature; keep it at
        # 1.0. Also better for a recommender — more variety across runs.
        self._temperature = temperature
        self._client = None  # lazily constructed

    def _get_client(self):
        if self._client is None:
            from google import genai  # imported lazily to keep import side-effect-free

            self._client = genai.Client(api_key=self._api_key)
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

        from google.genai import types

        ask = max(count, int(count * _OVER_REQUEST))
        prompt = self._build_prompt(seeds, ask)
        logger.debug(
            "Gemini: requesting %d suggestions (model=%s, temp=%s) from %d seeds: %s",
            ask, self._model, self._temperature, len(seeds), preview(seeds),
        )
        logger.debug("Gemini prompt:\n%s", prompt)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[_SuggestionSchema],
            temperature=self._temperature,  # 1.0 — see __init__ (latency + variety)
            # "Suggest similar songs" needs no chain-of-thought; disabling thinking
            # cuts latency substantially on flash models that default it on.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        client = self._get_client()
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                started = time.perf_counter()
                response = client.models.generate_content(
                    model=self._model, contents=prompt, config=config
                )
                suggestions = self._parse(response)
                logger.debug(
                    "Gemini: %d usable suggestions in %.2fs (attempt %d): %s",
                    len(suggestions), time.perf_counter() - started, attempt,
                    preview(suggestions),
                )
                return suggestions
            except Exception as exc:  # noqa: BLE001 — degrade, don't crash a playlist build
                retryable = _is_retryable(exc)
                logger.warning(
                    "Gemini request failed (attempt %d/%d, retryable=%s): %s",
                    attempt, _MAX_RETRIES, retryable, exc,
                )
                if retryable and attempt < _MAX_RETRIES:
                    time.sleep(2 ** (attempt - 1))  # 1s, 2s backoff
                    continue
                raise RecommenderError(f"Gemini request failed: {exc}") from exc
        raise RecommenderError("Gemini request failed after retries.")

    @staticmethod
    def _parse(response) -> list[Suggestion]:
        parsed = getattr(response, "parsed", None) or []
        out: list[Suggestion] = []
        for item in parsed:
            title = getattr(item, "title", "").strip()
            artist = getattr(item, "artist", "").strip()
            if title and artist:
                out.append(Suggestion(title=title, artist=artist))
        if not out:
            logger.warning("Gemini returned no usable suggestions.")
        return out


def _is_retryable(exc: Exception) -> bool:
    """Rate limits (429) and 5xx are worth a retry; everything else is not."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code == 429 or 500 <= code < 600
    text = str(exc).lower()
    return "429" in text or "rate" in text or "unavailable" in text or "internal" in text
