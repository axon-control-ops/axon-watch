"""Objective-aware completion gate for delegated worker deliveries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from app.persistence import run_store
from app.runs.service import append_run_execution_receipt
from app.workspace_agents.diff_policy import strip_control_plane_owned_paths
from app.workspace_agents.lead_verification_handoff import (
    is_verification_task,
    verification_terminal_jobs_for_run,
)
from app.workspace_agents.ops_delivery import no_change_delivery_is_successful_ops_task
from app.chat.reply_verification import extract_edit_paths


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


def _has_intent_word(text: str, words: Iterable[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


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
    if is_verification_task(task):
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
    explicitly_requests_implementation = _has_intent_word(
        assigned_blob,
        _IMPLEMENTATION_WORDS,
    )
    if no_change_delivery_is_successful_ops_task(task):
        return False
    # "Critically review X, suggest fixes, apply them" leads with review: the
    # diff is conditional on finding something. Counting the word "fix" as a
    # hard implementation demand fails an honest report with the misleading
    # reason "worker produced no changed files".
    if _leads_with_review_intent(task) and not _demands_unconditional_change(assigned_blob):
        return False
    if role in _IMPLEMENTATION_ROLES:
        return explicitly_requests_implementation or not _has_intent_word(
            assigned_blob,
            _REPORT_ONLY_WORDS,
        )
    return explicitly_requests_implementation


_REVIEW_LEAD_RE = re.compile(
    r"^\s*(?:please\s+)?(?:critically\s+)?"
    r"(review|re-?check|audit|critique|verify|validate|inspect|triage|assess)\b",
    re.IGNORECASE,
)
# Phrasing that still demands a diff even inside a review-shaped goal.
_UNCONDITIONAL_CHANGE_RE = re.compile(
    r"\b(implement|add|create|build|migrate|refactor|rewrite the (?:code|module|service))\b",
    re.IGNORECASE,
)


def _leads_with_review_intent(task: dict[str, Any]) -> bool:
    return bool(_REVIEW_LEAD_RE.match(str(task.get("goal") or "")))


def _demands_unconditional_change(assigned_blob: str) -> bool:
    return bool(_UNCONDITIONAL_CHANGE_RE.search(assigned_blob))


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


def _receipt_reported_changed_paths(reply_text: str) -> list[str]:
    """Changed paths explicitly backed by edit receipt blocks in the reply.

    Some report/ops tasks legitimately do not publish a product diff, but still
    create operator-facing notes inside the disposable checkout. Their completion
    receipt should not say ``changed_files=none`` when the reply contains a
    concrete ``:::edit path`` receipt.
    """
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in extract_edit_paths(reply_text or ""):
        path = str(raw or "").strip().lstrip("./")
        if not path or path in seen:
            continue
        seen.add(path)
        cleaned.append(path)
    return strip_control_plane_owned_paths(cleaned)


def _merge_receipt_paths_for_reporting(
    *,
    task: dict[str, Any] | None,
    paths: list[str],
    reply_text: str,
) -> list[str]:
    if implementation_requested(task):
        return paths
    receipt_paths = _receipt_reported_changed_paths(reply_text)
    if not receipt_paths:
        return paths
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*paths, *receipt_paths]:
        cleaned = str(item or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        merged.append(cleaned)
    return merged


def _validation_status(run_id: str, task: dict[str, Any]) -> tuple[bool, str]:
    run = run_store.get_run(run_id)
    if not isinstance(run, dict):
        return False, "missing run record"

    if is_verification_task(task):
        from app.workspace_agents.verification_execution import (
            describe_failed_jobs,
            job_failed,
            job_passed,
        )

        workspace_id = str(task.get("workspace_id") or "").strip()
        terminal_jobs = verification_terminal_jobs_for_run(workspace_id, run_id)
        passed_jobs = [job for job in terminal_jobs if job_passed(job)]
        if passed_jobs:
            return True, f"passed with {len(passed_jobs)} verification terminal job(s)"
        failed_jobs = [job for job in terminal_jobs if job_failed(job)]
        if failed_jobs:
            return False, (
                f"verification terminal jobs failed ({len(failed_jobs)}): "
                f"{describe_failed_jobs(failed_jobs)}"
            )
        if terminal_jobs:
            return False, "verification terminal jobs incomplete"
        return False, "missing verification terminal job receipts"

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
    paths = _merge_receipt_paths_for_reporting(
        task=task,
        paths=paths,
        reply_text=reply_text,
    )

    if not implementation_requested(task):
        if not isinstance(task, dict) or not str(task.get("goal") or "").strip():
            return CompletionGateResult(False, "assigned objective missing", paths, expected, "missing")
        if no_change_delivery_is_successful_ops_task(task):
            return CompletionGateResult(
                passed=True,
                reason="receipt-backed ops task",
                changed_paths=paths,
                expected_files=expected,
                validation_status="deferred to delivery receipt",
            )
        validation_ok, validation = _validation_status(run_id, task)
        if not validation_ok:
            return CompletionGateResult(
                False,
                f"non-implementation task did not provide required evidence: {validation}",
                paths,
                expected,
                validation,
            )
        return CompletionGateResult(
            passed=True,
            reason="non-implementation task",
            changed_paths=paths,
            expected_files=expected,
            validation_status=validation,
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


def _changed_expected_overlap_note(result: CompletionGateResult) -> str:
    """Flag when changed_files and expected_files share nothing in common.

    A receipt-backed ops/coordination pass legitimately has no product diff,
    so this is advisory, not a gate — but a completely disjoint changed/expected
    set on an otherwise-passing receipt is exactly the shape that let a blocked
    private-material delivery's changed_files (assets/TPS-PACK.zip, ...) sit
    next to an unrelated expected_files scope (docs/ops, docs/planning, ...)
    and still read as a clean pass to anyone skimming the receipt.
    """
    if not result.passed or not result.changed_paths or not result.expected_files:
        return ""
    changed = {path.strip().lstrip("./") for path in result.changed_paths if path.strip()}
    expected_roots = {path.strip().lstrip("./") for path in result.expected_files if path.strip()}
    overlaps = any(
        changed_path == root or changed_path.startswith(f"{root.rstrip('/')}/")
        for changed_path in changed
        for root in expected_roots
    )
    if overlaps:
        return ""
    return " · note=changed_files did not overlap expected_files"


def record_completion_gate_receipt(
    run_id: str,
    result: CompletionGateResult,
    *,
    actor: str = "workspace_scheduler",
    final: bool = False,
) -> dict[str, Any]:
    """Record a completion-gate receipt.

    ``final=False`` (the default) is used for the receipt recorded before
    ``publish_worker_isolation`` runs (see ``run_worker_delivery_gate``) — the
    delivery can still be blocked after this point (e.g. a private-material
    path gate), so it is labelled ``preflight`` rather than ``completion`` to
    avoid reading as the run's terminal verdict. Only the receipt recorded
    after a successful publish (``final=True``) uses ``completion=``.
    """
    status = "pass" if result.passed else "fail"
    label = "completion" if final else "preflight"
    paths = ", ".join(result.changed_paths[:8]) if result.changed_paths else "none"
    expected = ", ".join(result.expected_files[:8]) if result.expected_files else "task/role scope"
    commit = result.commit_sha or "pending"
    overlap_note = _changed_expected_overlap_note(result)
    return append_run_execution_receipt(
        run_id,
        receipt_type="completion_gate",
        actor=actor,
        success=result.passed,
        intent="worker_completion_gate",
        receipt_summary=(
            f"{label}={status} · reason={result.reason} · changed_files={paths} · "
            f"expected_files={expected} · validation={result.validation_status} · "
            f"commit={commit}{overlap_note}"
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
        and not is_verification_task(task)
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
    record_completion_gate_receipt(run_id, preflight, final=False)
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
        record_completion_gate_receipt(run_id, final, final=True)
        if not final.passed:
            return WorkerDeliveryGateOutcome(
                False,
                f"Workspace delivery blocked by completion gate: {final.reason}",
                preserve_isolation=True,
            )
    return WorkerDeliveryGateOutcome(True, "completion gate passed", publish=publish)
