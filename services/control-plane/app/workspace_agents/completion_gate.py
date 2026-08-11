"""Objective-aware completion gate for delegated worker deliveries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from app.persistence import run_store
from app.runs.service import append_run_execution_receipt
from app.workspace_agents.diff_policy import strip_control_plane_owned_paths
from app.workspace_agents.ops_delivery import no_change_delivery_is_successful_ops_task


_IMPLEMENTATION_ROLES = frozenset({"frontend", "backend", "integrations"})
_REPORTING_ROLES = frozenset({"lead", "watcher"})
_IMPLEMENTATION_WORDS = frozenset(
    {
        "add",
        "build",
        "change",
        "code",
        "create",
        "design",
        "edit",
        "fix",
        "implement",
        "redesign",
        "refactor",
        "route",
        "update",
        "wire",
    }
)
_VALIDATION_WORDS = frozenset(
    {"check", "command", "lint", "test", "typecheck", "validate", "validation", "verification", "verify"}
)
_REPORT_ONLY_WORDS = frozenset(
    {
        "audit",
        "check",
        "confirm",
        "inspect",
        "monitor",
        "report",
        "review",
        "triage",
        "validate",
        "verification",
        "verify",
    }
)
_STOP_WORDS = frozenset(
    {
        "after",
        "assigned",
        "criteria",
        "current",
        "exact",
        "file",
        "files",
        "from",
        "goal",
        "into",
        "only",
        "request",
        "task",
        "that",
        "this",
        "with",
        "work",
    }
)


@dataclass(frozen=True)
class CompletionGateResult:
    passed: bool
    reason: str
    changed_paths: list[str]
    expected_files: list[str]
    validation_status: str
    commit_sha: str = ""


@dataclass(frozen=True)
class WorkerDeliveryGateOutcome:
    passed: bool
    reason: str
    publish: Any | None = None
    preserve_isolation: bool = False


def implementation_requested(task: dict[str, Any] | None) -> bool:
    """True when the task asks for product/code changes, not just coordination."""
    if not isinstance(task, dict):
        return False
    role = str(task.get("owner_role") or "").strip().lower()
    # Leads coordinate and watchers verify. Their inherited parent-plan text
    # can mention a fix, but their own delivery is a report/decision rather
    # than a product diff. Requiring changed files here falsely fails a valid
    # monitoring shift and leaves the fleet stuck in an error state.
    if role in _REPORTING_ROLES:
        return False
    assigned_blob = " ".join(
        str(task.get(key) or "") for key in ("goal", "acceptance_criteria")
    ).lower()
    explicitly_requests_implementation = any(word in assigned_blob for word in _IMPLEMENTATION_WORDS)
    if no_change_delivery_is_successful_ops_task(task):
        return False
    if role in _IMPLEMENTATION_ROLES:
        return explicitly_requests_implementation or not any(
            word in assigned_blob for word in _REPORT_ONLY_WORDS
        )
    return explicitly_requests_implementation


def expected_files_for_task(task: dict[str, Any] | None) -> list[str]:
    if not isinstance(task, dict):
        return []
    raw = task.get("allowed_paths")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _split_identifier(text: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", spaced.lower())


def _objective_tokens(task: dict[str, Any]) -> set[str]:
    text = " ".join(
        str(task.get(key) or "") for key in ("goal", "acceptance_criteria")
    )
    tokens = {
        token
        for token in _split_identifier(text)
        if len(token) >= 3 and token not in _STOP_WORDS
    }
    # Keep role nouns useful for UI task matching.
    return tokens


def _path_tokens(paths: Iterable[str]) -> set[str]:
    tokens: set[str] = set()
    for path in paths:
        tokens.update(_split_identifier(path))
    return {token for token in tokens if len(token) >= 3}


def _changed_files_non_empty(root: Path, paths: Iterable[str]) -> bool:
    for raw in paths:
        path = root / str(raw).strip().lstrip("./")
        try:
            if path.is_file() and path.stat().st_size > 0:
                return True
        except OSError:
            continue
    return False


def _worker_reported_changed_files(reply_text: str, paths: Iterable[str]) -> bool:
    reply = str(reply_text or "")
    if not reply.strip():
        return False
    lowered = reply.lower()
    if not any(marker in lowered for marker in ("changed", "modified", "updated", "files")):
        return False
    for path in paths:
        cleaned = str(path or "").strip()
        if cleaned and cleaned in reply:
            return True
    return bool(re.search(r"\b[\w.-]+\.(tsx?|jsx?|vue|css|py|sql|md)\b", reply))


def _validation_status(run_id: str, task: dict[str, Any]) -> tuple[bool, str]:
    run = run_store.get_run(run_id)
    if not isinstance(run, dict):
        return False, "missing run record"
    history = run_store.list_history(str(run.get("history_ref") or ""))
    latest_acceptance = None
    has_check_outputs = False
    for item in history:
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        receipt_type = str(receipt.get("type") or "")
        summary = str(receipt.get("summary") or "")
        if receipt_type == "acceptance_evidence":
            latest_acceptance = receipt
        if receipt_type == "acceptance_check_outputs" and bool(receipt.get("success", True)):
            has_check_outputs = True
    if latest_acceptance is None:
        return False, "missing acceptance_evidence receipt"
    if "acceptance=pass" not in str(latest_acceptance.get("summary") or ""):
        return False, str(latest_acceptance.get("summary") or "acceptance did not pass")

    blob = " ".join(
        str(task.get(key) or "") for key in ("goal", "acceptance_criteria")
    ).lower()
    requires_command_output = any(word in blob for word in _VALIDATION_WORDS)
    if requires_command_output and not has_check_outputs:
        return False, "missing validation command outputs"
    return True, "passed" + (" with command outputs" if has_check_outputs else "")


def evaluate_pre_publish_completion_gate(
    *,
    run_id: str,
    task: dict[str, Any] | None,
    isolation_root: Path,
    reply_text: str,
    changed_paths: list[str] | None = None,
) -> CompletionGateResult:
    """Reject stale/no-op/wrong-objective implementation runs before publish."""
    expected = expected_files_for_task(task)
    paths = strip_control_plane_owned_paths(changed_paths or [])
    if changed_paths is None:
        from app.workspace_delivery.publish import list_isolation_changed_paths

        paths = strip_control_plane_owned_paths(list_isolation_changed_paths(isolation_root))

    if not implementation_requested(task):
        return CompletionGateResult(
            passed=True,
            reason="non-implementation task",
            changed_paths=paths,
            expected_files=expected,
            validation_status="not required",
        )
    if not isinstance(task, dict) or not str(task.get("goal") or "").strip():
        return CompletionGateResult(False, "assigned objective missing", paths, expected, "missing")
    if not paths:
        return CompletionGateResult(
            False,
            "implementation requested but worker produced no changed files",
            paths,
            expected,
            "not checked",
        )
    if not _worker_reported_changed_files(reply_text, paths):
        return CompletionGateResult(
            False,
            "worker did not report changed files in handoff",
            paths,
            expected,
            "not checked",
        )
    if not _changed_files_non_empty(isolation_root, paths):
        return CompletionGateResult(
            False,
            "changed files are empty or unreadable",
            paths,
            expected,
            "not checked",
        )
    objective = _objective_tokens(task)
    overlap = objective & _path_tokens(paths)
    if objective and not overlap:
        return CompletionGateResult(
            False,
            "changed files do not map to assigned objective",
            paths,
            expected,
            "not checked",
        )
    validation_ok, validation = _validation_status(run_id, task)
    if not validation_ok:
        return CompletionGateResult(False, validation, paths, expected, validation)
    return CompletionGateResult(True, "completion gate passed", paths, expected, validation)


def evaluate_post_publish_completion_gate(
    *,
    task: dict[str, Any] | None,
    delivery: dict[str, Any] | None,
    preflight: CompletionGateResult,
) -> CompletionGateResult:
    """Require a commit hash after a code-changing worker publish."""
    if not implementation_requested(task):
        return preflight
    commit_sha = ""
    if isinstance(delivery, dict):
        commit_sha = str(delivery.get("commit_sha") or "").strip()
        refs = delivery.get("refs") if isinstance(delivery.get("refs"), dict) else {}
        commit_sha = commit_sha or str(refs.get("commit_sha") or "").strip()
    if not commit_sha:
        return CompletionGateResult(
            False,
            "code change requested but delivery has no commit hash",
            preflight.changed_paths,
            preflight.expected_files,
            preflight.validation_status,
        )
    return CompletionGateResult(
        True,
        "completion gate passed",
        preflight.changed_paths,
        preflight.expected_files,
        preflight.validation_status,
        commit_sha=commit_sha,
    )


def record_completion_gate_receipt(
    run_id: str,
    result: CompletionGateResult,
    *,
    actor: str = "workspace_scheduler",
) -> dict[str, Any]:
    status = "pass" if result.passed else "fail"
    paths = ", ".join(result.changed_paths[:8]) if result.changed_paths else "none"
    expected = ", ".join(result.expected_files[:8]) if result.expected_files else "task/role scope"
    commit = result.commit_sha or "pending"
    return append_run_execution_receipt(
        run_id,
        receipt_type="completion_gate",
        actor=actor,
        success=result.passed,
        intent="worker_completion_gate",
        receipt_summary=(
            f"completion={status} · reason={result.reason} · changed_files={paths} · "
            f"expected_files={expected} · validation={result.validation_status} · "
            f"commit={commit}"
        ),
    )


def run_worker_delivery_gate(
    *,
    workspace_id: str,
    run_id: str,
    task_id: str,
    task: dict[str, Any] | None,
    isolation_root: Path,
    reply_text: str,
) -> WorkerDeliveryGateOutcome:
    from app.runs.service import get_run
    from app.workspace_agents.verifier_contract import (
        has_passing_acceptance_evidence,
        run_requires_acceptance_evidence,
    )
    from app.workspace_delivery import publish_worker_isolation

    run_snapshot = get_run(run_id)
    if (
        run_requires_acceptance_evidence(run_snapshot)
        and not has_passing_acceptance_evidence(run_id)
        and not no_change_delivery_is_successful_ops_task(task)
    ):
        return WorkerDeliveryGateOutcome(
            False,
            "Workspace delivery blocked: missing or failing acceptance_evidence (Gate 6)",
            preserve_isolation=True,
        )

    preflight = evaluate_pre_publish_completion_gate(
        run_id=run_id,
        task=task,
        isolation_root=isolation_root,
        reply_text=reply_text,
    )
    record_completion_gate_receipt(run_id, preflight)
    if not preflight.passed:
        return WorkerDeliveryGateOutcome(
            False,
            f"Workspace delivery blocked by completion gate: {preflight.reason}",
            preserve_isolation=True,
        )

    publish = publish_worker_isolation(
        workspace_id=workspace_id,
        run_id=run_id,
        isolation_root=isolation_root,
        task_id=task_id,
        turn_subject=str(task.get("goal") or "") if isinstance(task, dict) else None,
    )
    if publish.ok and publish.stage != "no_change":
        final = evaluate_post_publish_completion_gate(
            task=task,
            delivery=publish.delivery,
            preflight=preflight,
        )
        record_completion_gate_receipt(run_id, final)
        if not final.passed:
            return WorkerDeliveryGateOutcome(
                False,
                f"Workspace delivery blocked by completion gate: {final.reason}",
                preserve_isolation=True,
            )
    return WorkerDeliveryGateOutcome(True, "completion gate passed", publish=publish)
