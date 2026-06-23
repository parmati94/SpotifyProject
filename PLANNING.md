# SpotifyProject — Refactor Plan

> Status: **implemented** on `feature/llm-refactor` (Phases 0–5 done; Phase 6 optional).
> This document is the source of truth for the rework. §2/§10 describe the pre-work `master`
> state and the change map (historical); §3.2 and §5 reflect what was actually built. Key
> deltas from the original plan: the package was renamed `spotify_project/` → `backend/` and
> split into `main.py` + `routers/` + `common/` + `models/` (palworld-lens convention); the
> frontend uses Vite + Tailwind(PostCSS) + handlebars partials + bundled Alpine (satisfactory-lens
> convention), not the standalone Tailwind CLI; default model is `gemini-3.5-flash`.

---

## 1. Why we're doing this

Two forcing functions:

1. **The recommendations endpoint is dead.** Spotify deprecated `GET /v1/recommendations`
   (and `/v1/audio-features`, related-artists, etc.) on 2024-11-27. New/standard apps now
   get a `404`. Our entire app is built around `sp.recommendations(seed_tracks=...)`, so the
   core feature is non-functional on any fresh Spotify client ID.
2. **It's a first-ever project.** The structure reflects learning-in-progress: a global-state
   auth bug, CLI and API code tangled together, wildcard imports, `print()` debugging, an
   awkward "split tracks into lists of 5" apparatus that only existed to feed the 5-seed limit
   of the old endpoint, and a CRA frontend.

Goal: a clean, maintainable app where recommendations come from **Google Gemini (free tier)**,
the backend is properly layered, and the frontend is rebuilt in **Alpine.js + Tailwind**.

### Guiding principles
- **Swap, don't rewrite the world.** The Spotify read/write plumbing (top tracks, playlist
  create/add/delete) all still works. Only the *recommendation* step is dead. Keep what works.
- **One clean seam for recommendations** so the engine is swappable (Gemini today, local
  Ollama or a Spotify-native fallback tomorrow) without touching callers.
- **Free forever for personal volume.** ~2–8 LLM calls/day fits comfortably inside Gemini's
  free tier (no credit card). Design so a missing API key degrades gracefully, not crashes.

---

## 2. Current state — what exists and what's broken (accurate to `master`)

### Backend (`spotify_project/`)
```
api/controller.py     FastAPI routes (login, callback, session, playlist ops)
api/auth.py           spotify_auth(token_info, user_id) — per-user cache + token refresh
api/models.py         Pydantic v1 — single Playlist model
logging_config.py     structured logging (timed rotating file + console)
main/main.py          "driver" functions (create/extend/delete)
main/operations.py    all Spotify calls + the recommendation machinery
```

> Note: this reflects `master` **after** the recent merges (PRs #9/#10, etc.). Earlier drafts
> of this plan described an older tree — the CLI and `config.py` are already gone (see below).

**Already addressed since the first iteration** (do NOT re-plan these):
- ✅ **Auth rebuilt** — no more global token. `controller.get_spotify()` reads `user_id` +
  `token_info` from the session, and `auth.spotify_auth()` **refreshes expired tokens**. Each
  user gets a `.cache-{user_id}` file.
- ✅ **CLI removed** — `main/input.py` deleted; `main.py` is API-driver functions only.
- ✅ **`main/config.py` removed** — auth moved to `api/auth.py`.
- ✅ **Structured logging** — `logging_config.py`; `print()` replaced with `logger` calls.
- ✅ **CORS fixed** — `allow_origins=[FRONTEND_URL]` (no longer `["*"]` with credentials).
- ✅ New endpoints: `/health_check`, `/check_session`, `/logout`; richer `/get_all_playlists`
  (name, total_tracks, image_url + error handling).

**Problems that REMAIN, in priority order:**

| # | Issue | Where | Severity |
|---|-------|-------|----------|
| 1 | **Recommendations endpoint dead** — still the core blocker | `operations.py:114` (`sp.recommendations`) | Blocker |
| 2 | The `track_split` → lists-of-5 → `num_lists` size math exists *only* to feed the old 5-seed endpoint. Obsolete with an LLM | `operations.py` (`track_split`, `get_recommendations`, `get_recommendation_tracks`) | High (delete it) |
| 3 | **Hardcoded session secret** `"sovhioadufhg"` | `controller.py:39` | Medium |
| 4 | Playlist lookups by **name**, scanning all playlists (O(n) calls, breaks on duplicate names) | `operations.playlist_exists_with_id` | Medium |
| 5 | Wildcard imports (`from ..main.operations import *`, `from ..main.main import *`) | `controller.py`, `main.py` | Low–Med |
| 6 | Pydantic v1, no type hints, no tests, no error model | repo-wide | Low–Med |
| 7 | Per-user `.cache-{user_id}` files on disk + a redundant `_save_token_info` in `/callback` (session already holds the token) — works, but tangled | `auth.py`, `controller.callback` | Low |

### Frontend (`client/`)
- **Create React App** (`react-scripts 5.0.1`) — slow, needs `--openssl-legacy-provider`, effectively unmaintained.
- Runtime API base URL injected via a `set-env.js` + `public/env-config.js` string-replace hack.
- FontAwesome for icons.
- We're replacing this wholesale with Alpine + Tailwind (see §5).

### Deploy
- Two containers (`frontend` CRA dev server on :3000, `api` uvicorn on :8000) via `docker-compose.yml`.
- `REDIRECT_URI` / `FRONTEND_URL` wired through env vars.
- **CI exists:** `.github/workflows/docker-image.yml` builds/pushes images (the README's
  "build pipeline → private Docker repo"). Will need rewriting for the single-image build.

---

## 3. Target architecture

### 3.1 Big picture decision: one container, nginx + supervisord (the house pattern)

Collapse the two containers into **a single image** using the same pattern as the other apps
(e.g. NotifyAgent): **nginx serves the static Alpine/Tailwind frontend and reverse-proxies
`/api/*` to a uvicorn process**, with **supervisord** managing both processes. Everything is
**same-origin**, which kills the `set-env.js` runtime-config hack, kills CORS entirely, and
makes the OAuth redirect trivial (one origin to register).

Why nginx in front (vs. FastAPI serving the HTML itself): nginx is the right tool for static
assets, it's the established pattern across your apps, and it keeps a clean split between
"serve the UI" and "run the API" inside the one container. The frontend is a static build
(`index.html` + compiled `app.css` + Alpine), so nginx serves it directly off disk.

```
  ┌───────────────────────── single container ─────────────────────────┐
  │  supervisord (manages both processes)                              │
  │                                                                    │
  │   ┌── nginx (:8080) ──────────────────────────────────────────┐   │
  │   │   location /          → static/  (index.html, app.css,     │   │
  │   │                          alpine)                           │   │
  │   │   location /api/      → proxy_pass → uvicorn               │   │
  │   │   location /login,                                         │   │
  │   │            /callback  → proxy_pass → uvicorn (OAuth)       │   │
  │   └────────────────────────────┬───────────────────────────────┘   │
  │                                │                                   │
  │   ┌── uvicorn (FastAPI, :8000)─┴───────────────────────────────┐   │
  │   │   /api/playlists/*   JSON endpoints (called by Alpine)     │   │
  │   │   /login, /callback  Spotify OAuth                         │   │
  │   └────────────────────────────────────────────────────────────┘   │
  └────────────────────────────────────────────────────────────────────┘
            host: one published port (e.g. 8080 → chosen host port)
```

FastAPI keeps `root_path="/api"` (matching the NotifyAgent setup) so route paths and the proxy
prefix line up. The OAuth routes (`/login`, `/callback`) are proxied through nginx as well so
the whole flow stays on the single public origin.

> Alternative kept on the table: keep them split if the frontend ever needs to deploy
> independently. Default is the single nginx+supervisord image to match the rest of the fleet.

### 3.2 New backend layout — IMPLEMENTED

> The package was renamed `spotify_project/` → **`backend/`** (it sits alongside the new
> top-level `frontend/`, matching the fleet — see satisfactory-lens / palworld-lens). The
> `api/controller.py` blob was split into `main.py` + `routers/` per the palworld-lens FastAPI
> convention. Config/auth/logging live under `common/`; schemas under `models/`.

```
backend/
  main.py                   # FastAPI app entry: middleware + include_router (uvicorn backend.main:app)
  deps.py                   # FastAPI deps: get_client(), get_recommender() (session-based)
  common/
    config.py               # pydantic-settings: env + validation, one place (get_settings)
    auth.py                 # Spotify OAuth + per-session token storage & auto-refresh
    logging_config.py       # structured logging (kept)
    constants.py            # SPOTIFY_SCOPE, DEFAULT_IMAGE_URL
  models/
    schemas.py              # pydantic v2 request/response models
  routers/
    oauth.py                # /login, /callback
    system.py               # /api/health, /api/session, /api/logout
    playlists.py            # /api/playlists{, /daily, /weekly, /from-playlist}
  core/
    spotify_client.py       # wraps spotipy: top tracks, playlist CRUD, search
    playlists.py            # business logic: create_daily, extend, delete, from_playlist
    resolver.py             # {artist,title} suggestion -> verified Spotify track URI
    recommender/
      base.py               # Recommender Protocol (the swappable seam)
      gemini.py             # GeminiRecommender (default)
      catalog.py            # Spotify-native fallback (artist top tracks) — implemented
      factory.py            # build_recommender(settings, sp) → picks engine
```

Imports are absolute (`from backend.common... import ...`), matching palworld-lens. CLI was
already gone; the old driver functions now live in `core/playlists.py`.

---

## 4. The recommendation engine (the heart of the rework)

### 4.1 The seam

Define one interface; everything else depends on it.

```python
# core/recommender/base.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class Seed:
    title: str
    artist: str

@dataclass
class Suggestion:
    title: str
    artist: str

class Recommender(Protocol):
    def recommend(self, seeds: list[Seed], count: int) -> list[Suggestion]: ...
```

### 4.2 GeminiRecommender

- SDK: `google-genai` (`pip install google-genai`). Model: `gemini-flash` (latest flash).
- Auth: `GEMINI_API_KEY` from env (free key via Google AI Studio, no card).
- **Use structured output** (JSON schema / `response_schema`) so we get back a clean list of
  `{artist, title}` — no brittle text parsing.

```python
# sketch
prompt = (
    "You are a music recommender. Given these seed tracks, suggest {count} similar "
    "songs the listener would enjoy. Vary artists. Return real, existing songs.\n"
    + "\n".join(f"- {s.title} — {s.artist}" for s in seeds)
)
# response_schema = list[{"title": str, "artist": str}]
```

- Ask for **~25% more than needed** (e.g. want 40 → request 50) to absorb resolver misses.

### 4.3 The resolver (hallucination safety net)

LLMs occasionally invent songs. Doesn't matter — we verify every suggestion against Spotify
and drop anything that doesn't resolve:

```python
# core/resolver.py
def resolve(sp, suggestion) -> str | None:
    res = sp.search(q=f'track:"{suggestion.title}" artist:"{suggestion.artist}"',
                    type="track", limit=1)
    items = res["tracks"]["items"]
    return items[0]["uri"] if items else None
```

Pipeline: `seeds → Gemini → suggestions → resolve each → dedupe (vs seeds + existing playlist)
→ shuffle → slice to N → add to playlist`. Only **real, playable** URIs ever get added.

### 4.4 What this deletes

The entire 5-seed apparatus is obsolete:
- `track_split`, the `num_lists` math, `get_recommendations`, `get_recommendation_tracks`
- Size is now just a number (`count`), not `num_lists * 20`.

### 4.5 Fallback (optional, nice-to-have)

`catalog.py`: if `GEMINI_API_KEY` is unset or Gemini errors, build candidates from
still-live Spotify endpoints (seed artists' top tracks + albums, dedupe, shuffle). Zero
external deps. Wire selection in `config.py` (`RECOMMENDER=gemini|catalog`).

---

## 5. Frontend rework — Alpine.js + Tailwind (full greenfield)

> **Scope change (2026-06-22):** this is no longer "feature parity then polish." The old
> CRA UI is being **thrown away wholesale** — almost none of it is reused. We're building a
> genuinely nice, modern UI from scratch.

### 5.1 Approach — match the house Alpine convention (per `satisfactory-lens`)
The earlier "standalone Tailwind CLI, Alpine via CDN" idea is **dropped**. Its only upside
was avoiding a Node toolchain, but Node is only needed at **build** time (a Docker builder
stage) — the runtime image is still just nginx static + uvicorn. So we adopt Paul's real
convention, which buys partials, JS modules, fingerprinted assets, and an HMR dev server:

- **Vite** (multi-page) builds the frontend → static `dist/`. Dev server proxies `/api`,
  `/login`, `/callback` to uvicorn.
- **Tailwind 3.4 via PostCSS** (`tailwind.config.js` + `postcss.config.js`), not the CLI.
- **`vite-plugin-handlebars`** for HTML **partials** (`{{> header }}`, `{{> toast }}`, …) —
  compose the UI from reusable pieces under `frontend/partials/`.
- **Alpine 3.x** installed as a dependency and bundled: a single `Alpine.data('app', …)`
  root in `frontend/js/app.js`, with feature logic split into ES modules spread into the
  root (`...playlistActions()`, …), mirroring `satisfactory-lens/js/app.js`.
- **`api.js`**: a namespaced `api` object over a small `apiFetch` wrapper (throws on non-2xx
  with the server's `detail`), exactly like the reference project.
- **Theming**: dark, Spotify-flavored. Accent palette via CSS variables + Tailwind
  `accent-*` / semantic `ok|warn|danger` colors (same mechanism as the reference).
- **Served same-origin** (nginx static `/` + proxy `/api`,`/login`,`/callback`) → no CORS,
  no `set-env.js`.

Proposed layout (under a new top-level `frontend/`, replacing `client/`):
```
frontend/
  index.html                 # composed from partials
  js/{app.js, api.js, playlistActions.js}
  partials/{head,header,footer,toast,confirm-dialog, ...}.html
  css/main.css               # Tailwind entry + theme vars
  tailwind.config.js  postcss.config.js  vite.config.js  package.json
```

### 5.2 Screens / components
A single-page, tabbed/sectioned dashboard (not a wall of gradient buttons). Candidate shape —
final layout is the builder's call:
| Area | Interactivity (Alpine) |
|------|------------------------|
| Auth gate | reads `?login=success|failure`; `/api/session` on load; "Connect Spotify" → `/login`; logout |
| Quick actions | Create Daily (`POST /api/playlists/daily`), Extend Weekly (`POST /api/playlists/weekly`), Delete Daily (confirm → `DELETE`) — each with inline busy state + toast |
| Create from playlist | source dropdown (`GET /api/playlists`), target name, count slider → `POST /api/playlists/from-playlist` |
| Playlist browser | cards (art, name, track count) from `/api/playlists`, searchable; "use as source" affordance |
| Settings | theme picker (accent), persisted to localStorage |

Shared Alpine bits: `apiFetch`/`api`, a global busy/`actionLoading` mutex, a promise-based
`showConfirm` modal, and an auto-dismissing `actionResult` toast — all per the reference.

### 5.3 Why Alpine+Tailwind (still) fits
Interactivity is modest (buttons, dropdowns, modals, toasts, a card grid) — no SPA framework
needed. Alpine keeps state co-located; Tailwind + partials keep markup DRY without a heavy
build. It also matches the rest of the fleet, so the deploy/CI story is shared.

---

## 6. Auth — mostly done, remaining polish

The big rebuild is **already complete**: session-based `user_id` + `token_info`, with
`auth.spotify_auth()` refreshing expired tokens. What's left is cleanup:

- **Load the session secret from env** (`SESSION_SECRET`) — currently hardcoded
  `"sovhioadufhg"` in `controller.py:39`.
- **Simplify token caching:** the session already holds `token_info`; the per-user
  `.cache-{user_id}` files + `_save_token_info()` in `/callback` are redundant for the web
  flow. Either lean fully on the session, or keep the cache but drop the duplicate write.
- **CORS:** once we move to the single nginx+supervisord origin (§3.1), the CORS middleware
  can largely go away (same-origin). Until then, the current `allow_origins=[FRONTEND_URL]`
  is correct.

---

## 7. Config, secrets, deployment

- **`config.py` with `pydantic-settings`**: `CLIENT_ID`, `CLIENT_SECRET`, `REDIRECT_URI`,
  `GEMINI_API_KEY`, `SESSION_SECRET`, `RECOMMENDER`. Validate on startup; fail loud if missing.
- `.env.example` updated with the new keys (esp. `GEMINI_API_KEY`).
- **Dockerfile (multi-stage, single image — `satisfactory-lens` pattern):**
  - *Stage 1 (builder):* `node:20-slim`; `npm ci` + `vite build` the `frontend/` → `dist/`.
  - *Stage 2 (runtime):* `python:3.12-slim` + `nginx` + `supervisor`; `pip install` the API;
    copy `frontend/dist` into nginx's web root (`/usr/share/nginx/html`).
  - Ship an `nginx.conf` (static `/` with `try_files … /index.html`, immutable cache on
    `/assets/`, `proxy_pass` for `/api` + `/login` + `/callback`, a `/health` 200) and a
    `supervisor/supervisord.conf` (programs: `nginx`, `uvicorn`). Expose one port (`80`).
  - Retire `client/Dockerfile`.
- **docker-compose.yml**: down to **one service** (the combined image), one published port;
  drop `FRONTEND_*` plumbing and the `REACT_APP_API_BASE_URL` injection. `REDIRECT_URI` now
  points at the single origin.
- Bump deps: pydantic v2, current spotipy, current FastAPI/uvicorn.
- README rewrite: new setup (Gemini key, single container), remove CRA instructions.

---

## 8. Open decisions (resolve as we go — defaults in **bold**)

1. **Single service vs. two.** → **One container: nginx + supervisord** (nginx serves static
   frontend, proxies `/api` + OAuth to uvicorn), matching the other apps. (Reconsider only if
   independent frontend deploy is wanted.)
2. **CLI: keep or drop?** → Already **dropped** (`input.py` deleted). Keep driver logic in
   `core/` callable from a thin optional script if ever needed.
3. **Tailwind/frontend build:** ~~standalone CLI~~ → **Vite + Tailwind(PostCSS) + handlebars
   partials + bundled Alpine**, matching `satisfactory-lens`. Node is build-time only (Docker
   builder stage); runtime stays nginx-static + uvicorn. (Reversed 2026-06-22 — the rework went
   full greenfield, where partials/modules/HMR clearly win. See §5.1.)
4. **Fallback recommender:** ship `catalog.py` now or later? → **Stub the interface now,
   implement Gemini first, add catalog fallback if time allows.**
5. **Gemini model:** pin `gemini-flash` latest; revisit if quality/limits warrant.
6. **Persistence:** sessions in-memory (fine for single-user/home use) vs. a store. →
   **In-memory** to start; note it resets on restart.

---

## 9. Phased execution plan

Work on a branch off `master` (e.g. `feature/llm-refactor`). Each phase should leave the app
runnable.

- **Phase 0 — Scaffolding & safety**
  - Branch. Add `config.py` (pydantic-settings), `.env.example` keys (incl. `GEMINI_API_KEY`,
    `SESSION_SECRET`). (Structured logging already exists — `logging_config.py`.)
  - Pin/bump deps (pydantic v2, spotipy, fastapi).
- **Phase 1 — Auth polish** (most of this is already done — see §6)
  - Move session secret to env; trim the redundant `.cache-{user_id}` write. *Not* a rebuild.
- **Phase 2 — Recommendation seam + Gemini**
  - `recommender/base.py`, `gemini.py`, `resolver.py`. Unit-test the resolver with mocked search.
  - Delete `track_split` / `get_recommendations` / `num_lists` math.
- **Phase 3 — Re-layer backend**
  - `core/spotify_client.py`, `core/playlists.py`; thin `controller.py`; `schemas.py` (v2);
    namespaced routes (`/api/...`); ID-based playlist lookups where practical.
- **Phase 4 — Frontend (Alpine + Tailwind)**
  - Build the static views in §5.2; wire to JSON endpoints. (Served by nginx in Phase 5;
    during dev, point at the uvicorn origin.)
- **Phase 5 — Single-container deploy & docs**
  - Multi-stage Dockerfile (assets stage + nginx/supervisor runtime); `nginx.conf` +
    `supervisord.conf`; set FastAPI `root_path="/api"`; one-service compose; rewrite README;
    final manual test of every flow on the single origin.
- **Phase 6 — (optional)** catalog fallback, basic tests, GitHub Action build.

---

## 10. File-by-file change map (quick reference)

| Path | Action |
|------|--------|
| `spotify_project/main/operations.py` | Split: Spotify I/O → `core/spotify_client.py`; **delete** recommendation machinery (`track_split`/`get_recommendations`/`get_recommendation_tracks`) |
| `spotify_project/main/main.py` | Driver fns → `core/playlists.py` |
| `spotify_project/api/auth.py` | Keep (already does refresh); fold into `auth/session.py`; trim redundant cache write |
| `spotify_project/logging_config.py` | Keep as-is (already good) |
| `spotify_project/api/controller.py` | Slim to thin routes; env session secret; drop CORS once same-origin |
| `spotify_project/api/models.py` | → `api/schemas.py`, pydantic v2 |
| `spotify_project/requirements.txt` | + `google-genai`, `pydantic-settings`; bump pydantic→v2, spotipy, fastapi |
| `spotify_project/.env.example` | + `GEMINI_API_KEY`, `SESSION_SECRET`, `RECOMMENDER` |
| `client/` (CRA) | **Remove**; replace with `web/templates` + `web/static` (or new `frontend/`) |
| `client/set-env.js`, `public/env-config.js` | **Delete** (same-origin removes the need) |
| `nginx.conf` | **New** — static at `/`, `proxy_pass` for `/api` + `/login` + `/callback` |
| `supervisord.conf` | **New** — manages `nginx` + `uvicorn` in the one container |
| `Dockerfile` | **New** multi-stage (assets → nginx/supervisor runtime); retire `client/Dockerfile` |
| `docker-compose.yml` | Collapse to single service, one published port |
| `.github/workflows/docker-image.yml` | Rewrite to build/push the single combined image |
| `README.md` | Rewrite for new architecture |

---

## 11. Risks & watch-items
- **Gemini free-tier rate limits / ToS:** fine for personal volume; free tier may use inputs
  for product improvement (non-issue for "suggest songs"). Handle 429s with a small backoff.
- **Resolver match quality:** strict `track:"x" artist:"y"` can miss on punctuation/remixes.
  Fallback to a looser query before giving up; always cap at requested `count`.
- **Spotify OAuth redirect:** `REDIRECT_URI` must be registered in the Spotify dashboard and
  must match the deployed origin exactly (single-service simplifies this).
- **Don't reintroduce duplicate-name playlist bugs:** prefer operating on playlist IDs.
