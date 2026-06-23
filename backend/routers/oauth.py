"""Spotify OAuth: kick off login and handle the callback.

These live at the top level (no /api prefix) and are proxied as-is by nginx so the
whole OAuth round-trip stays on the single public origin. On success the full
token_info is stored in the session; the browser is bounced back to the SPA.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from backend.common.auth import exchange_code, login_url
from backend.common.config import get_settings
from backend.common.logging_config import logger

router = APIRouter(tags=["auth"])


@router.get("/login")
def login() -> RedirectResponse:
    return RedirectResponse(login_url())


@router.get("/callback")
def callback(request: Request) -> RedirectResponse:
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(url="/?login=failure")
    try:
        token_info = exchange_code(code)
    except Exception as exc:  # noqa: BLE001
        logger.error("OAuth code exchange failed: %s", exc)
        return RedirectResponse(url="/?login=failure")
    if not token_info or "access_token" not in token_info:
        return RedirectResponse(url="/?login=failure")
    request.session["token_info"] = token_info
    logger.info("User authenticated; token stored in session.")
    if get_settings().dev_auth:
        # One-time capture: copy this into DEV_REFRESH_TOKEN on your dev box, then turn
        # DEV_AUTH back off here so refresh tokens stop hitting the logs.
        logger.warning(
            "DEV_AUTH capture — set DEV_REFRESH_TOKEN=%s", token_info.get("refresh_token")
        )
    return RedirectResponse(url="/?login=success")
