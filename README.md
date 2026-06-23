# SpotifyProject

AI-generated Spotify playlists. Connect your account and the app builds fresh playlists
from your listening — a daily mix, a rolling weekly playlist, or a new playlist seeded from
any of your existing ones. Song suggestions come from **Google Gemini**; every suggestion is
verified against Spotify before it's added, so playlists only ever contain real, playable tracks.

> **Why the rework?** Spotify deprecated its `/v1/recommendations` endpoint (Nov 2024), which
> the original app was built around. Recommendations now come from an LLM behind a swappable
> seam (`backend/core/recommender/`), the backend was re-layered, and the old Create-React-App
> frontend was replaced with an Alpine.js + Tailwind UI. The whole thing now ships as a single
> nginx + uvicorn container.

## Architecture

```
frontend/   Alpine.js + Tailwind, built with Vite (HTML partials + JS modules) → static dist/
backend/    FastAPI app
  main.py            app entry (uvicorn backend.main:app)
  routers/           HTTP routes (oauth, system, playlists)
  common/            config (pydantic-settings), auth (OAuth + session), logging, constants
  models/            pydantic v2 schemas
  core/              domain logic
    spotify_client.py    spotipy wrapper (top tracks, playlist CRUD, search)
    recommender/         the swappable engine: gemini (default) | catalog (fallback)
    resolver.py          verifies suggestions → real Spotify track URIs
    playlists.py         business logic behind each route
```

In production a single container runs **nginx** (serves the built frontend, reverse-proxies
`/api`, `/login`, `/callback`) and **uvicorn** (FastAPI), managed by **supervisor** — everything
is same-origin, so there's no CORS and the OAuth redirect targets one URL.

## Prerequisites

1. **Spotify app** — create one at <https://developer.spotify.com/dashboard> for a
   `CLIENT_ID` / `CLIENT_SECRET`. Add your redirect URI (see below) under **Settings → Redirect URIs**.
2. **Gemini API key** (optional but recommended) — free, no credit card, from
   <https://aistudio.google.com/apikey>. Without it the app falls back to the `catalog`
   recommender (Spotify-native, lower quality) instead of failing.

## Configuration

Config is split by sensitivity: **secrets live in `./.env`** at the project root (gitignored,
secrets-only), **non-secret config lives in `docker-compose*.yml`** (committed, reviewable).
Compose pulls the secrets via `env_file` and sets the non-secrets inline; `backend/common/config.py`
holds sane defaults as a fallback. Copy `.env.example` to `./.env` to start. (A legacy
`backend/.env` is still read if present, but the root `.env` is the canonical location.)

**Secrets — in `./.env`:**

| Variable | Required | Notes |
|----------|----------|-------|
| `CLIENT_ID`, `CLIENT_SECRET` | ✅ | From the Spotify dashboard |
| `SESSION_SECRET` | ✅ | `openssl rand -hex 32` |
| `LASTFM_API_KEY` | — | Enables the default `lastfm` engine — free key from [last.fm/api](https://www.last.fm/api) |
| `GEMINI_API_KEY` | — | Enables the `gemini` engine ([free](https://aistudio.google.com/apikey)) |
| `ANTHROPIC_API_KEY` | — | Enables the `claude` engine ([console](https://console.anthropic.com), needs credit) |

(Any keyed engine without its key degrades to the `catalog` engine, which needs none.)

**Non-secret config — in `docker-compose*.yml` (defaults in `config.py`):**

| Variable | Notes |
|----------|-------|
| `REDIRECT_URI` | Must exactly match a registered Redirect URI **and** the origin you serve from. Spotify [forbids `localhost`](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri) — use the loopback IP literal (`http://127.0.0.1:PORT/callback`) and browse via `127.0.0.1` too |
| `RECOMMENDER` | **Default** engine: `lastfm` (default) · `gemini` · `claude` · `catalog` — each user can switch at runtime in Settings (see below) |
| `GEMINI_MODEL` | Defaults to `gemini-2.5-flash` |
| `CLAUDE_MODEL` | Defaults to `claude-sonnet-4-6` |
| `LOG_LEVEL` | `INFO` by default |

### Recommendation engines

Song suggestions come from a swappable engine; every suggestion is then verified against Spotify
search before it's added, so playlists only ever contain real, playable tracks.

`RECOMMENDER` sets the **default** engine. From the **Settings** panel each user can switch between
the engines you've supplied credentials for — the selector only lists engines whose API key is
present, shows each LLM's configured model, and the active engine appears as a pill in the header.
The choice is stored per session (the signed cookie), so different users get independent engines
with no shared server state.

| Engine | What it is | Trade-off |
|--------|------------|-----------|
| **`lastfm`** (default) | Last.fm `track.getSimilar` — real co-listening data, aggregated across your seeds | Fast (~1s), free, no hallucination. The data-driven replacement for Spotify's dead recommendations endpoint. |
| **`gemini`** | Google Gemini LLM | Free; latency/quality vary by model. |
| **`claude`** | Anthropic Claude (Sonnet 4.6) | Highest-quality LLM; ~$0.01–0.06 per build. |
| **`catalog`** | Seed artists' top tracks via Spotify | No external key; the always-works fallback. |

## Run with Docker (production)

```bash
docker compose up -d        # uses parmati/spotifyproject:latest
```

Set the env values in `docker-compose.yml` (or your environment). It publishes `5470:80`, so
register `http://127.0.0.1:5470/callback` as the Spotify Redirect URI and set `REDIRECT_URI`
to match. Open <http://127.0.0.1:5470>.

## Local development

Dev runs the app in Docker via `docker-compose.dev.yml`, built with `uvicorn --reload` and
bind-mounting `backend/`, so backend edits restart the API automatically. The frontend is the
built `dist/` mounted into nginx — rebuild it on the host whenever you change the UI.

```bash
# build the frontend once (Node 20+); add `-- --watch` to rebuild continuously
cd frontend && npm install && npm run build

# from the repo root: start the dev container (publishes :5471)
docker compose -f docker-compose.dev.yml up --build
```

Open <http://127.0.0.1:5471> and register `http://127.0.0.1:5471/callback` as a Redirect URI
on the Spotify app. Edit `backend/` → the API auto-reloads. Edit the UI → re-run `npm run build`
and the mounted `dist/` updates nginx live (no container restart needed).

## Tests

```bash
pip install pytest
PYTHONPATH=. pytest -q
```

Covers the resolver (suggestion → URI verification), both recommenders, and API route wiring
with the Spotify dependency mocked — no live Spotify/Gemini calls needed.

## Features

- **Daily mix** — a fresh playlist seeded from your recent top tracks, named for today's date.
- **Weekly playlist** — grows a rolling "Weekly Extended Playlist" with new picks (created if absent).
- **Create from a playlist** — seed a brand-new playlist from any existing one, choosing the size.
- **Clear today** — delete every playlist named after today's date (handy for a re-roll).
