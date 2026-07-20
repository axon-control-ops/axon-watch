"""Read-side run queries and summaries."""

from __future__ import annotations

from typing import Any

from app.chat.command_intent import humanize_run_summary
from app.domain.run_state import is_terminal_phase
from app.persistence import run_store


def _approval_record_for_run(record: dict[str, Any]) -> dict[str, str]:
    return {
        "approval_id": f"approval_{record['run_id']}",
        "run_id": record["run_id"],
        "workspace_id": record["workspace_id"],
    }


def list_runs() -> list[dict[str, Any]]:
    return run_store.list_runs()


def is_background_employee_run(record: dict[str, Any]) -> bool:
    """True for scheduled role-tagged worker shifts (not operator-initiated runs)."""
    return bool(str(record.get("employee_role") or "").strip())


def list_active_runs() -> list[dict[str, Any]]:
    return [record for record in run_store.list_runs() if not is_terminal_phase(record["phase"])]


def list_operator_facing_runs() -> list[dict[str, Any]]:
    """Persisted runs the operator should see (excludes role-tagged worker shifts)."""
    return [
        record for record in run_store.list_runs() if not is_background_employee_run(record)
    ]


def list_operator_facing_active_runs() -> list[dict[str, Any]]:
    """Active runs the operator should see in briefing, summary, and fleet health."""
    return [
        record for record in list_active_runs() if not is_background_employee_run(record)
    ]


def list_pending_approval_runs() -> list[dict[str, Any]]:
    return [record for record in run_store.list_runs() if record["phase"] == "awaiting_approval"]


def list_pending_review_runs() -> list[dict[str, Any]]:
    return [record for record in run_store.list_runs() if record["phase"] == "review_ready"]


def list_pending_approval_records() -> list[dict[str, str]]:
    return [_approval_record_for_run(record) for record in list_pending_approval_runs()]


def approval_summary() -> dict[str, Any]:
    pending_runs = list_pending_approval_runs()
    latest_approval_at = max((record["updated_at"] for record in pending_runs), default=None)
    return {
        "pending_count": len(pending_runs),
        "highest_severity": None,
        "latest_approval_at": latest_approval_at,
    }


def to_runtime_summary_active_run(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record["run_id"],
        "workspace_id": record["workspace_id"],
        "mode": record["mode"],
        "status": record["status"],
        "phase": record["phase"],
        "title": humanize_run_summary(str(record["summary"])),
        "detail": record["detail"],
        "lane_id": record["lane_id"],
        "updated_at": record["updated_at"],
    }


__all__ = [
    "approval_summary",
    "is_background_employee_run",
    "list_active_runs",
    "list_operator_facing_runs",
    "list_operator_facing_active_runs",
    "list_pending_approval_records",
    "list_pending_approval_runs",
    "list_pending_review_runs",
    "list_runs",
    "to_runtime_summary_active_run",
]
