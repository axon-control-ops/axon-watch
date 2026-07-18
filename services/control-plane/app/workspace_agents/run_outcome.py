"""Latest employee-role run outcome helpers for roster clarity."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store
from app.runs.service import list_runs

_MAX_DETAIL = 180


def _truncate(text: str, limit: int = _MAX_DETAIL) -> str:
    cleaned = " ".join(text.split()).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _failure_detail_from_history(history_ref: str) -> str | None:
    items = run_store.list_history(history_ref)
    for item in reversed(items):
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        receipt_type = str(receipt.get("type") or "").strip()
        summary = str(receipt.get("summary") or "").strip()
        if not summary:
            continue
        if receipt_type in {"run_failed", "runtime_dispatch", "finalization_error"}:
            return _truncate(summary)
    return None


def latest_role_run_outcome(workspace_id: str, role: str) -> dict[str, str] | None:
    """Return the newest role-tagged run outcome for roster/UI detail."""
    cleaned_role = str(role or "").strip().lower()
    normalized_workspace = workspace_id.strip()
    if not cleaned_role or not normalized_workspace:
        return None

    tagged = [
        run
        for run in list_runs()
        if str(run.get("workspace_id", "")).strip() == normalized_workspace
        and str(run.get("employee_role") or "").strip().lower() == cleaned_role
    ]
    if not tagged:
        return None

    tagged.sort(
        key=lambda run: str(run.get("updated_at") or run.get("ended_at") or run.get("started_at") or ""),
        reverse=True,
    )
    run = tagged[0]
    phase = str(run.get("phase") or "").strip()
    outcome = "failed" if phase == "failed" else ("completed" if phase == "completed" else phase)
    detail = str(run.get("current_step") or "").strip()
    if outcome == "failed":
        history_ref = str(run.get("history_ref") or "").strip()
        from_history = _failure_detail_from_history(history_ref) if history_ref else None
        if from_history:
            detail = from_history
        elif not detail or detail.lower() in {"run failed", "failed"}:
            detail = "Shift failed — open run history for receipts."
    elif not detail:
        detail = str(run.get("summary") or "").strip()

    return {
        "run_id": str(run.get("run_id") or ""),
        "outcome": outcome,
        "detail": _truncate(detail) if detail else "",
        "phase": phase,
        "terminal": "1" if is_terminal_phase(phase) else "0",
    }
