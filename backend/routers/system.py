"""Health + auth-status + logout endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.common.config import Settings, get_settings
from backend.deps import (
    SESSION_ENGINE_KEY,
    SESSION_ENGINE_MODEL_KEY,
    selected_engine,
    selected_model,
    selected_vibe_engine,
    selected_vibe_model,
)
from backend.models.schemas import (
    MessageResponse,
    RecommenderInfo,
    RecommenderStatus,
    SessionResponse,
    SetRecommenderRequest,
    VibeStatus,
)

router = APIRouter(prefix="/api", tags=["system"])


def _recommender_status(request: Request, settings: Settings) -> RecommenderStatus:
    available = [RecommenderInfo(**e) for e in settings.available_engines()]
    active = selected_engine(request, settings)
    return RecommenderStatus(
        active=active,
        active_model=selected_model(request, settings, active),
        available=available,
    )


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/session", response_model=SessionResponse)
def session_status(
    request: Request, settings: Settings = Depends(get_settings)
) -> SessionResponse:
    return SessionResponse(
        authenticated=bool(request.session.get("token_info")), dev=settings.dev_auth
    )


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request) -> MessageResponse:
    request.session.clear()
    return MessageResponse(message="Logged out.")


@router.get("/recommender", response_model=RecommenderStatus)
def get_recommender_status(
    request: Request, settings: Settings = Depends(get_settings)
) -> RecommenderStatus:
    """This session's active engine and the credential-gated list it may switch between."""
    return _recommender_status(request, settings)


@router.put("/recommender", response_model=RecommenderStatus)
def set_recommender(
    body: SetRecommenderRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> RecommenderStatus:
    """Switch this session's engine. Only the available (credential-backed) engines are
    accepted; the choice is stored in the session cookie, so it's per-user."""
    available = {e["id"] for e in settings.available_engines()}
    if body.engine not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Engine '{body.engine}' is unavailable. Choose one of: "
            f"{', '.join(sorted(available))}.",
        )
    request.session[SESSION_ENGINE_KEY] = body.engine
    # Re-resolve the model against the new engine's list so switching engines can't leave
    # a stale cross-engine model behind (None for non-LLM engines).
    request.session[SESSION_ENGINE_MODEL_KEY] = settings.resolve_model(body.engine, body.model)
    return _recommender_status(request, settings)


@router.get("/vibe", response_model=VibeStatus)
def get_vibe_status(
    request: Request, settings: Settings = Depends(get_settings)
) -> VibeStatus:
    """The LLM picker state for vibe mode: this session's active LLM and the LLM-only
    list it may switch between. Empty list ⇒ no LLM configured ⇒ the UI hides vibe mode."""
    available = [RecommenderInfo(**e) for e in settings.available_vibe_engines()]
    active = selected_vibe_engine(request, settings)
    return VibeStatus(
        active=active,
        active_model=selected_vibe_model(request, settings, active) if active else None,
        available=available,
    )
