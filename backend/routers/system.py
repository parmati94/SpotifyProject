"""Health + auth-status + logout endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.models.schemas import MessageResponse, SessionResponse

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/session", response_model=SessionResponse)
def session_status(request: Request) -> SessionResponse:
    return SessionResponse(authenticated=bool(request.session.get("token_info")))


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request) -> MessageResponse:
    request.session.clear()
    return MessageResponse(message="Logged out.")
