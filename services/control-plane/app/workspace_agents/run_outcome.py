"""Latest employee-role run outcome helpers for roster clarity."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store
from app.runs.service import list_runs
from app.workspace_agents.failure_detail import normalize_operator_failure_detail

_MAX_DETAIL = 180
_RESTART_INTERRUPT_MARKERS = (
    "Run interrupted by control-plane restart",
    "Run cancelled after control-plane restart",
    "Run paused after control-plane restart",
)


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
        if receipt_type in {
            "run_failed",
            "runtime_dispatch",
            "finalization_error",
            "control_plane_restart",
        }:
            return _truncate(summary)
    return None


def _is_restart_interrupt_run(run: dict[str, Any]) -> bool:
    """Return True when a run ended only because the control-plane process restarted."""
    step = str(run.get("current_step") or "").strip()
    if any(marker in step for marker in _RESTART_INTERRUPT_MARKERS):
        return True
    history_ref = str(run.get("history_ref") or "").strip()
    if not history_ref:
        return False
    for item in reversed(run_store.list_history(history_ref)):
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        if str(receipt.get("type") or "").strip() == "control_plane_restart":
            return True
    return False


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

    # Prefer finished shifts over newer paused/in-flight runs so fleet stop does not
    # hide the last failed/completed receipt on the roster.
    terminal = [
        run
        for run in tagged
        if is_terminal_phase(str(run.get("phase") or "").strip())
    ]
    candidates = terminal if terminal else tagged
    candidates = [run for run in candidates if not _is_restart_interrupt_run(run)]
    if not candidates:
        return None
    candidates.sort(
        key=lambda run: str(run.get("updated_at") or run.get("ended_at") or run.get("started_at") or ""),
        reverse=True,
    )
    run = candidates[0]
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

    if detail:
        detail = normalize_operator_failure_detail(detail)

    return {
        "run_id": str(run.get("run_id") or ""),
        "outcome": outcome,
        "detail": _truncate(detail) if detail else "",
        "phase": phase,
        "terminal": "1" if is_terminal_phase(phase) else "0",
    }
