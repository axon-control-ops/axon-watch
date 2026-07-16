"""Route registration for the control-plane FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI

from app.routes import (
    chat,
    data,
    email_reply,
    email_settings,
    health,
    inbox_watch,
    operator,
    plans,
    runs,
    runtime,
    safe_improvement,
    skills,
    vault_http,
    workspaces,
)


def register_routes(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(runtime.router)
    app.include_router(vault_http.router)
    app.include_router(data.router)
    app.include_router(inbox_watch.router)
    app.include_router(operator.router)
    app.include_router(email_settings.router)
    app.include_router(email_reply.router)
    app.include_router(chat.router)
    app.include_router(plans.router)
    app.include_router(runs.router)
    app.include_router(workspaces.router)
    app.include_router(skills.router)
    # Session toggle is always mounted; proposal routes stay 404 until enabled.
    app.include_router(safe_improvement.router)
