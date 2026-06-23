"""FastAPI application entry point.

Creates the app, wires session middleware, and includes the routers. All business
logic lives in `core/`; OAuth/token handling in `common/auth.py`; route handlers in
`routers/` stay thin. Run with: `uvicorn backend.main:app`.

URL scheme (same-origin behind nginx in production):
  /login, /callback        Spotify OAuth (proxied as-is)
  /api/*                   JSON endpoints called by the frontend
"""

from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from backend.common.config import get_settings
from backend.common.logging_config import logger
from backend.routers import oauth, playlists, system

settings = get_settings()  # validates required env on startup; fails loud if missing

app = FastAPI(title="SpotifyProject")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    https_only=False,  # set True behind HTTPS in production
)

app.include_router(oauth.router)
app.include_router(system.router)
app.include_router(playlists.router)

if settings.dev_auth:
    # Dev-only refresh-token login bypass; never reached in prod (flag defaults off and
    # the prod compose pins it false). Mounted conditionally so the route simply doesn't
    # exist otherwise.
    from backend.routers import dev

    app.include_router(dev.router)
    logger.warning("DEV_AUTH enabled — /dev/login (refresh-token bypass) is active.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
