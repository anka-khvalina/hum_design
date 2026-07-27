from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request


def get_settings(request: Request):
    return request.app.state.settings


def get_sessions(request: Request):
    return request.app.state.sessions


def get_knowledge(request: Request):
    return request.app.state.knowledge


def require_user(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return user
