"""Workspace agent role catalog and display constants."""

from __future__ import annotations

WORKSPACE_AGENT_STATUSES = (
    "idle",
    "watching",
    "planning",
    "executing",
    "verifying",
    "blocked",
    "waiting_approval",
    "handoff_ready",
)

EMPLOYEE_SCHEDULES = ("always_on", "continuous", "on_demand")

ROLE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "lead",
        "label": "Lead",
        "summary": "Owns priorities, handoffs, and final review",
        "default_schedule": "on_demand",
    },
    {
        "id": "watcher",
        "label": "Watcher",
        "summary": "Monitors signals and runtime health around the clock",
        "default_schedule": "always_on",
    },
    {
        "id": "frontend",
        "label": "Frontend",
        "summary": "Owns UI/UX surfaces and shell polish",
        "default_schedule": "continuous",
    },
    {
        "id": "backend",
        "label": "Backend",
        "summary": "Owns APIs, control plane, and persistence",
        "default_schedule": "continuous",
    },
    {
        "id": "integrations",
        "label": "Integrations",
        "summary": "Owns connectors and cross-service wiring",
        "default_schedule": "continuous",
    },
    {
        "id": "workspace_agent",
        "label": "General",
        "summary": "General company employee for assigned workspace work",
        "default_schedule": "on_demand",
    },
    {
        "id": "overview_agent",
        "label": "Overview",
        "summary": "Cross-workspace overview and routing",
        "default_schedule": "on_demand",
    },
)

# Fallback display names when a company omits employee.name in config.
_DEFAULT_ROLE_NAMES = {
    "lead": "Mira",
    "watcher": "Rowan",
    "frontend": "Jules",
    "backend": "Reed",
    "integrations": "Quinn",
    "workspace_agent": "Alex",
    "overview_agent": "Sage",
}

_ROLE_BY_ID = {entry["id"]: entry for entry in ROLE_CATALOG}

_SCHEDULE_LABELS = {
    "always_on": "Always on (24/7)",
    "continuous": "Continuous",
    "on_demand": "On demand",
}

_DEFAULT_OWNS = {
    "lead": "priorities, handoffs, and product direction",
    "watcher": "signals, connectors, and runtime health",
    "frontend": "UI/UX, shell, and frontend polish",
    "backend": "APIs, control plane, and persistence",
    "integrations": "connectors and integrated services",
}

_BRAND_CASE = {
    "axon": "Axon",
    "dashpro": "DashPro",
}
