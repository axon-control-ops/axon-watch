"""Role-assignment guardrails and finding models for Lead team check-in."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.workspace_agents.failure_detail import (
    is_billing_failure,
    is_operator_stopped_failure,
    is_restart_interrupted_failure,
    is_runtime_auth_failure,
    is_usage_limit_failure,
)

ASSIGN_GOAL_PREFIX = "Lead assigned:"
ATTEND_GOAL_PREFIX = "VAXON attend:"
CHECKIN_GOAL_PREFIX = "Lead check-in:"
SPECIALIST_ROLES = frozenset({"watcher", "frontend", "backend", "integrations"})

FindingKind = Literal[
    "failed_shift",
    "monitor_alert",
    "connector_degraded",
    "operator_blocker",
    "critical_signal",
    "warning_signal",
    "open_handoff",
]


@dataclass(frozen=True)
class LeadCheckinFinding:
    kind: FindingKind
    workspace_id: str
    owner_role: str
    title: str
    detail: str
    dedupe_key: str
    escalate_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assign_owner_role_for_monitor(check_type: str, service: str = "") -> str:
    """Guardrail: map third-party / monitor signals to the owning specialist."""
    check = str(check_type or "").strip().lower()
    label = str(service or "").strip().lower()
    blob = f"{check} {label}"
    if any(token in blob for token in ("sentry", "ci", "fast gate", "github", "vercel")):
        return "watcher"
    if any(token in blob for token in ("posthog", "supabase", "storage", "imap", "email")):
        return "integrations"
    if any(token in blob for token in ("console", "ui", "frontend", "expo")):
        return "frontend"
    if any(
        token in blob
        for token in ("api", "control-plane", "control_plane", "control plane", "backend")
    ):
        return "backend"
    if "http_health" in check or "connector" in blob:
        return "integrations"
    return "watcher"


def assign_owner_role_for_failed_shift(role: str, detail: str) -> tuple[str, bool]:
    """Return (owner_role, escalate_only) for a failed specialist shift.

    Usage / auth / restart noise must not spawn code-repair tasks.
    """
    cleaned = str(role or "").strip().lower()
    if cleaned not in SPECIALIST_ROLES:
        return "watcher", True
    if (
        is_usage_limit_failure(detail)
        or is_runtime_auth_failure(detail)
        or is_billing_failure(detail)
    ):
        return cleaned, True
    if is_restart_interrupted_failure(detail) or is_operator_stopped_failure(detail):
        return cleaned, True
    return cleaned, False


__all__ = [
    "ASSIGN_GOAL_PREFIX",
    "ATTEND_GOAL_PREFIX",
    "CHECKIN_GOAL_PREFIX",
    "SPECIALIST_ROLES",
    "FindingKind",
    "LeadCheckinFinding",
    "assign_owner_role_for_failed_shift",
    "assign_owner_role_for_monitor",
]
