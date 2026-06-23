"""Dev-only auth bypass — NOT included unless Settings.dev_auth is on.

Seeds the session from a pre-captured refresh token so a headless/LAN dev instance can
"log in" without the Spotify OAuth round-trip (which is impossible at a non-loopback http
origin like http://192.168.x.x:PORT — an illegal redirect URI). The seeded token_info is
shaped exactly like a real login's, so every downstream path (refresh, API calls) is
unchanged. See backend/common/config.py for the capture workflow.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from backend.common.auth import dev_token_from_refresh
from backend.common.config import get_settings
from backend.common.logging_config import logger

router = APIRouter(tags=["dev"])


@router.get("/dev/login")
def dev_login(request: Request) -> RedirectResponse:
    settings = get_settings()
    if not settings.dev_auth:  # defence in depth; the route isn't even mounted otherwise
        raise HTTPException(status_code=404, detail="Not found")
    if not settings.dev_refresh_token:
        logger.error("DEV_AUTH is on but DEV_REFRESH_TOKEN is unset — cannot dev-login.")
        return RedirectResponse(url="/?login=failure")
    try:
        token_info = dev_token_from_refresh(settings.dev_refresh_token)
    except Exception as exc:  # noqa: BLE001 — surface as a clean login failure
        logger.error("Dev login failed (bad/expired DEV_REFRESH_TOKEN?): %s", exc)
        return RedirectResponse(url="/?login=failure")
    request.session["token_info"] = token_info
    logger.info("Dev login: session seeded from DEV_REFRESH_TOKEN.")
    return RedirectResponse(url="/?login=success")
