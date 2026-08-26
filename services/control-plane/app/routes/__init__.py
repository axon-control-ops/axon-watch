"""Route registration for the control-plane FastAPI app."""

from __future__ import annotations

from fastapi import FastAPI

from app.routes import (
    chat,
    constitution,
    data,
    desktop,
    email_reply,
    email_settings,
    fleet_self_heal,
    github_ci_webhook,
    health,
    host,
    inbox_watch,
    lead_planner,
    missions,
    operator,
    plans,
    platform_recovery,
    runs,
    runtime,
    safe_improvement,
    skills,
    tasks,
    vault_http,
    worker_scheduler,
    workspaces,
    workspace_delivery_status,
    workspace_sandbox,
    workspaces_agent_jobs,
)


def register_routes(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(runtime.router)
    app.include_router(vault_http.router)
    app.include_router(data.router)
    app.include_router(inbox_watch.router)
    app.include_router(host.router)
    app.include_router(operator.router)
    app.include_router(constitution.router)
    app.include_router(email_settings.router)
    app.include_router(email_reply.router)
    app.include_router(chat.router)
    app.include_router(plans.router)
    app.include_router(runs.router)
    app.include_router(workspaces.router)
    app.include_router(workspace_delivery_status.router)
    app.include_router(workspace_sandbox.router)
    app.include_router(workspaces_agent_jobs.router)
    app.include_router(worker_scheduler.router)
    app.include_router(tasks.router)
    app.include_router(lead_planner.router)
    app.include_router(missions.router)
    app.include_router(skills.router)
    app.include_router(github_ci_webhook.router)
    app.include_router(fleet_self_heal.router)
    app.include_router(platform_recovery.router)
    # Session toggle is always mounted; proposal routes stay 404 until enabled.
    app.include_router(safe_improvement.router)
    # Desktop API + optional SPA catch-all (must be last).
    desktop.register_desktop_routes(app)
