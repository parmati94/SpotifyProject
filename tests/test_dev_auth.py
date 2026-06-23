"""Dev refresh-token login bypass (DEV_AUTH). The route is mounted only when enabled,
so these drive the handler directly with a stubbed session + settings."""

import os

os.environ.setdefault("CLIENT_ID", "test-id")
os.environ.setdefault("CLIENT_SECRET", "test-secret")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import pytest  # noqa: E402

from backend.common.config import Settings  # noqa: E402
from backend.routers import dev as dev_router  # noqa: E402


class _Req:
    """Minimal stand-in for Starlette's Request — the handler only touches .session."""

    def __init__(self):
        self.session = {}


def _settings(**over):
    base = dict(dev_auth=True, dev_refresh_token="rt-123")
    base.update(over)
    return Settings.model_construct(**base)


def test_dev_login_seeds_session_from_refresh_token(monkeypatch):
    monkeypatch.setattr(dev_router, "get_settings", _settings)
    monkeypatch.setattr(
        dev_router,
        "dev_token_from_refresh",
        lambda t: {"access_token": "fresh", "refresh_token": t, "expires_at": 999},
    )
    req = _Req()
    resp = dev_router.dev_login(req)
    assert req.session["token_info"]["access_token"] == "fresh"
    assert resp.headers["location"] == "/?login=success"


def test_dev_login_fails_cleanly_without_token(monkeypatch):
    monkeypatch.setattr(dev_router, "get_settings", lambda: _settings(dev_refresh_token=None))
    req = _Req()
    resp = dev_router.dev_login(req)
    assert "token_info" not in req.session
    assert resp.headers["location"] == "/?login=failure"


def test_dev_login_404_when_disabled(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(dev_router, "get_settings", lambda: _settings(dev_auth=False))
    with pytest.raises(HTTPException) as exc:
        dev_router.dev_login(_Req())
    assert exc.value.status_code == 404
