"""Gate 6 — mandatory acceptance evidence before worker publish surfaces.

Workers (runs bound to a task_id) cannot reach review_ready or complete from
executing without a passing acceptance_evidence receipt. Operator thin-slice
runs without a task_id keep the prior lifecycle (Gate 6 focuses on leased work).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.persistence import run_store

logger = logging.getLogger(__name__)

ACCEPTANCE_RECEIPT_TYPE = "acceptance_evidence"
ACCEPTANCE_PASS_MARKER = "acceptance=pass"
ACCEPTANCE_FAIL_MARKER = "acceptance=fail"


def record_acceptance_evidence(
    run_id: str,
    *,
    passed: bool,
    summary: str,
    actor: str = "verifier",
) -> dict[str, Any]:
    """Persist a machine-checkable acceptance receipt on the run history."""
    from app.runs.service import append_run_execution_receipt
    from app.workspace_agents.verifier_checks import assert_verifier_identity

    assert_verifier_identity(actor)
    marker = ACCEPTANCE_PASS_MARKER if passed else ACCEPTANCE_FAIL_MARKER
    cleaned = " ".join(str(summary or "").split()) or "acceptance evidence"
    return append_run_execution_receipt(
        run_id,
        receipt_type=ACCEPTANCE_RECEIPT_TYPE,
        receipt_summary=f"{marker} · {cleaned}" if marker not in cleaned else cleaned,
        actor=actor,
        success=passed,
        intent="gate6_acceptance",
    )


def record_acceptance_evaluation(run_id: str, evaluation: dict[str, Any]) -> dict[str, Any]:
    """Persist structured check outputs from the immutable verifier role."""
    from app.runs.service import append_run_execution_receipt
    from app.workspace_agents.verifier_checks import VERIFIER_IDENTITY, assert_verifier_identity

    actor = str(evaluation.get("actor") or VERIFIER_IDENTITY)
    assert_verifier_identity(actor)
    passed = bool(evaluation.get("passed"))
    summary = str(evaluation.get("summary") or "")
    receipt = record_acceptance_evidence(
        run_id,
        passed=passed,
        summary=summary,
        actor=actor,
    )
    checks = evaluation.get("checks") or []
    if checks:
        names = ",".join(str(item.get("name") or "?") for item in checks)
        append_run_execution_receipt(
            run_id,
            receipt_type="acceptance_check_outputs",
            receipt_summary=f"checks={names} count={len(checks)} passed={passed}",
            actor=actor,
            success=passed,
            intent="gate6_check_outputs",
        )
    return receipt


def latest_acceptance_evidence(run_id: str) -> dict[str, Any] | None:
    from app.runs.service import RunNotFoundError

    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")
    history = run_store.list_history(str(record["history_ref"]))
    for entry in reversed(history):
        receipt = entry.get("receipt") if isinstance(entry, dict) else None
        if not isinstance(receipt, dict):
            continue
        if str(receipt.get("type") or "") != ACCEPTANCE_RECEIPT_TYPE:
            continue
        return {
            "receipt": receipt,
            "entry": entry,
            "passed": ACCEPTANCE_PASS_MARKER in str(receipt.get("summary") or ""),
        }
    return None


def has_passing_acceptance_evidence(run_id: str) -> bool:
    latest = latest_acceptance_evidence(run_id)
    return bool(latest and latest.get("passed"))


def require_acceptance_evidence(run_id: str) -> None:
    """Fail closed when a worker run lacks a passing acceptance receipt."""
    from app.runs.service import RunLifecycleError

    latest = latest_acceptance_evidence(run_id)
    if latest is None:
        raise RunLifecycleError(
            "review_ready/complete blocked: missing acceptance_evidence receipt (Gate 6)",
        )
    if not latest.get("passed"):
        summary = str((latest.get("receipt") or {}).get("summary") or "").strip()
        detail = f" ({summary})" if summary else ""
        raise RunLifecycleError(
            "review_ready/complete blocked: acceptance_evidence did not pass "
            f"(Gate 6){detail}",
        )


def run_requires_acceptance_evidence(record: dict[str, Any] | None) -> bool:
    if not isinstance(record, dict):
        return False
    return bool(str(record.get("task_id") or "").strip())


def enforce_acceptance_for_publish(run_id: str) -> None:
    from app.runs.service import get_run

    record = get_run(run_id)
    if run_requires_acceptance_evidence(record):
        require_acceptance_evidence(run_id)


def _resolve_workspace_root(
    record: dict[str, Any],
    workspace_root: str | Path | None,
) -> Path | None:
    if workspace_root is not None:
        root = Path(workspace_root)
        return root if root.is_dir() else None
    workspace_id = str(record.get("workspace_id") or "").strip()
    if not workspace_id:
        return None
    try:
        from app.terminal.workspace_roots import resolve_workspace_root

        return Path(resolve_workspace_root(workspace_id))
    except Exception:  # noqa: BLE001 — Gate 6 falls back to inspect profile
        logger.exception("Gate 6 workspace root resolve failed for %s", workspace_id)
        return None


def ensure_acceptance_before_publish(
    run_id: str,
    *,
    workspace_root: str | Path | None = None,
    changed_paths: list[str] | None = None,
) -> dict[str, Any] | None:
    """Run/record Gate 6 evidence for task-bound runs before complete/review_ready.

    Never treats Critical Review confidence as acceptance. Records pass or fail
    evidence; callers still invoke complete_run / mark_review_ready which enforce.
    """
    from app.project_contract.loader import ProjectContractError
    from app.runs.service import get_run
    from app.workspace_agents.verifier_checks import (
        evaluate_acceptance,
        load_repo_contract,
    )
    from app.workspace_agents.verifier_runner import (
        execute_check_plan,
        inspect_fallback_contract,
        list_changed_paths,
        read_path_texts,
    )

    record = get_run(run_id)
    if not run_requires_acceptance_evidence(record):
        return None
    if has_passing_acceptance_evidence(run_id):
        return None

    from app.workspace_agents.diff_policy import strip_control_plane_owned_paths

    root = _resolve_workspace_root(record, workspace_root)
    paths = list(changed_paths) if changed_paths is not None else []
    if not paths and root is not None:
        paths = list_changed_paths(root)
    # The control plane writes its own bookkeeping (.axon-si/*, the research
    # MCP config) into the isolation worktree. Counting those as agent-changed
    # paths failed correct runs — including read-only consultative ones — with
    # "acceptance=fail · policy=out_of_scope" for files the agent never wrote.
    paths = strip_control_plane_owned_paths(paths)

    task_allowed_paths: list[str] = []
    task_id = str(record.get("task_id") or "").strip()
    if task_id:
        from app.persistence import task_store

        task = task_store.get_task(task_id)
        if isinstance(task, dict):
            raw_allowed = task.get("allowed_paths")
            if isinstance(raw_allowed, list):
                task_allowed_paths = [
                    str(item).strip() for item in raw_allowed if str(item).strip()
                ]

    if root is None:
        contract = inspect_fallback_contract()
        mode = "inspect_fallback_no_root"
        check_results: dict[str, dict[str, Any]] = {}
        path_to_text: dict[str, str] = {}
    else:
        try:
            contract = load_repo_contract(str(root))
            check_results = execute_check_plan(
                root,
                contract,
                changed_paths=paths,
            )
            path_to_text = read_path_texts(root, paths)
            mode = "contract"
        except ProjectContractError as exc:
            logger.info("Gate 6 using inspect fallback for %s: %s", run_id, exc)
            contract = inspect_fallback_contract()
            mode = "inspect_fallback_no_contract"
            check_results = {}
            path_to_text = read_path_texts(root, paths)

    evaluation = evaluate_acceptance(
        contract=contract,
        check_results=check_results,
        changed_paths=paths,
        path_to_text=path_to_text,
        task_allowed_paths=task_allowed_paths,
    )
    payload = evaluation.to_dict()
    payload["summary"] = f"{evaluation.summary} · mode={mode} · paths={len(paths)}"
    return record_acceptance_evaluation(run_id, payload)
