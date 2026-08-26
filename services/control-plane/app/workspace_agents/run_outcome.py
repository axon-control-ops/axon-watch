"""Latest employee-role run outcome helpers for roster clarity."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store
from app.runs.service import list_runs
from app.workspace_agents.failure_detail import (
    is_restart_interrupted_failure,
    normalize_operator_failure_detail,
)
from app.workspace_agents.critical_review_clause import MISSING_CONFIDENCE_DETAIL

_MAX_DETAIL = 180


def _truncate(text: str, limit: int = _MAX_DETAIL) -> str:
    cleaned = " ".join(text.split()).strip()
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[: max(0, limit - 1)]
    # Prefer breaking on a word boundary so operator-facing detail doesn't end
    # mid-word (e.g. "unpaid invoic…"). Fall back to the hard cut only when
    # there's no reasonable break point (one very long token).
    boundary = cut.rfind(" ")
    if boundary > limit * 0.6:
        cut = cut[:boundary]
    return f"{cut.rstrip()}…"


def _run_stamp(run: dict[str, Any]) -> str:
    return str(
        run.get("updated_at") or run.get("ended_at") or run.get("started_at") or ""
    )


def _is_missing_confidence_failure(detail: str | None) -> bool:
    cleaned = " ".join(str(detail or "").split()).strip().lower()
    if not cleaned:
        return False
    if "critical review clause missing" in cleaned:
        return True
    marker = " ".join(MISSING_CONFIDENCE_DETAIL.lower().split())
    return marker[:48] in cleaned


def _failure_detail_for_run(run: dict[str, Any]) -> str:
    detail = str(run.get("current_step") or "").strip()
    history_ref = str(run.get("history_ref") or "").strip()
    from_history = _failure_detail_from_history(history_ref) if history_ref else None
    if from_history:
        detail = from_history
    elif not detail or detail.lower() in {"run failed", "failed"}:
        detail = "Shift failed — open run history for receipts."
    return normalize_operator_failure_detail(detail) if detail else ""


def _select_role_outcome_run(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the roster outcome run.

    Prefer newest terminal work, but do not let a stale missing-Confidence Critical
    Review failure eclipse a later successful completion for the same role.
    """

    def _sort_key(run: dict[str, Any]) -> tuple[str, int, str]:
        stamp = _run_stamp(run)
        phase = str(run.get("phase") or "").strip()
        # Same-second ties: prefer completed IDE retries over older failed tags.
        phase_rank = 2 if phase == "completed" else (0 if phase == "failed" else 1)
        return (stamp, phase_rank, str(run.get("run_id") or ""))

    ordered = sorted(candidates, key=_sort_key, reverse=True)
    top = ordered[0]
    top_phase = str(top.get("phase") or "").strip()
    if top_phase != "failed":
        return top

    top_stamp = _run_stamp(top)
    # Prefer a successful completion that is at least as new as this failure —
    # covers missing-Confidence, Gate 6 delivery blocks, and stale tags after IDE retries.
    later_completed = [
        run
        for run in ordered
        if str(run.get("phase") or "").strip() == "completed"
        and _run_stamp(run) >= top_stamp
    ]
    if later_completed:
        return later_completed[0]

    return top


def _successful_critical_review_detail(run: dict[str, Any]) -> str | None:
    """Return a short success detail when Lane B finished Critical Review before cancel."""
    history_ref = str(run.get("history_ref") or "").strip()
    if not history_ref:
        return None
    for item in reversed(run_store.list_history(history_ref)):
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        receipt_type = str(receipt.get("type") or "").strip()
        summary = str(receipt.get("summary") or "").strip()
        if receipt_type == "critical_review" and summary:
            lowered = summary.lower()
            if "success=true" in lowered or "confidence:" in lowered:
                return _truncate(summary)
        if receipt_type == "runtime_dispatch" and "success=true" in summary.lower():
            # Keep scanning — prefer an explicit Critical Review when present.
            continue
    return None


def _is_restart_interrupt_without_success(run: dict[str, Any]) -> bool:
    """Skip restart cancels unless the shift already delivered a successful Critical Review."""
    if not _is_restart_interrupt_run(run):
        return False
    return _successful_critical_review_detail(run) is None


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
    if step and is_restart_interrupted_failure(step):
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
        summary = str(receipt.get("summary") or "").strip()
        if summary and is_restart_interrupted_failure(summary):
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
        and not str(run.get("dismiss_reason") or "").strip()
    ]
    # Employee IDE retries historically omitted employee_role — recover via thread link.
    try:
        from app.persistence import chat_store

        seen = {str(run.get("run_id") or "") for run in tagged}
        for thread in chat_store.list_threads_for_workspace(
            normalized_workspace,
            thread_kind="ide",
            limit=50,
        ):
            if str(thread.get("employee_role") or "").strip().lower() != cleaned_role:
                continue
            linked_run_id = str(thread.get("run_id") or "").strip()
            if not linked_run_id or linked_run_id in seen:
                continue
            try:
                linked = run_store.get_run(linked_run_id)
            except Exception:  # noqa: BLE001 — roster must stay fail-open
                linked = None
            if not isinstance(linked, dict):
                continue
            if str(linked.get("workspace_id") or "").strip() != normalized_workspace:
                continue
            if str(linked.get("dismiss_reason") or "").strip():
                continue
            # Heal untagged IDE completions so roster stops clinging to older failures.
            if cleaned_role and not str(linked.get("employee_role") or "").strip():
                linked = dict(linked)
                linked["employee_role"] = cleaned_role
                # Thread updated_at is a reliable "this was the latest IDE work" clock.
                thread_updated = str(thread.get("updated_at") or "").strip()
                run_updated = str(linked.get("updated_at") or "").strip()
                if thread_updated and thread_updated > run_updated:
                    linked["updated_at"] = thread_updated
                try:
                    linked = run_store.save_run(linked)
                except Exception:  # noqa: BLE001 — roster must stay fail-open
                    pass
            tagged.append(linked)
            seen.add(linked_run_id)
    except Exception:  # noqa: BLE001 — roster must stay fail-open
        pass
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
    candidates = [run for run in candidates if not _is_restart_interrupt_without_success(run)]
    if not candidates:
        return None
    run = _select_role_outcome_run(candidates)
    phase = str(run.get("phase") or "").strip()
    success_detail = _successful_critical_review_detail(run)
    # Restart may cancel the run after Lane B already finished Critical Review —
    # treat that as completed so Team does not cling to an older usage failure.
    if success_detail and phase in {"cancelled", "failed"} and _is_restart_interrupt_run(run):
        return {
            "run_id": str(run.get("run_id") or ""),
            "outcome": "completed",
            "detail": success_detail,
            "phase": "completed",
            "terminal": "1",
        }
    outcome = "failed" if phase == "failed" else ("completed" if phase == "completed" else phase)
    detail = str(run.get("current_step") or "").strip()
    if outcome == "failed":
        detail = _failure_detail_for_run(run) or detail
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
