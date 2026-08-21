"""Executable verification-task contracts and terminal receipt evaluation."""

from __future__ import annotations

import logging
import os
import re
import shlex
from pathlib import Path
from typing import Any, Callable

from app.persistence import task_store

logger = logging.getLogger(__name__)

_VERIFICATION_COMMAND_RE = re.compile(
    r"`((?:npm test[^\n`]*|npm run[^\n`]*|npx (?:--no-install )?tsx[^\n`]*|npx (?:--no-install )?jest[^\n`]*))`",
    re.IGNORECASE,
)
_TEST_FILE_BACKTICK_RE = re.compile(
    r"`(tests/[^`\n]+\.(?:test|spec)\.(?:ts|tsx|js|jsx))`",
    re.IGNORECASE,
)
_GOAL_INLINE_COMMAND_RE = re.compile(
    r"(?<![/`])(npm test(?:\s+--\s+[^\n;`\[]+)?|npx (?:--no-install )?tsx[^\n;`\[]+|npx (?:--no-install )?jest[^\n;`\[]+)",
    re.IGNORECASE,
)
_SOURCE_RUN_RE = re.compile(r"\[from run (run_[a-f0-9]+)\]", re.IGNORECASE)
_MALFORMED_VERIFY_COMMAND_RE = re.compile(
    r"^(npm test-|npx jest-|npx tsx-)",
    re.IGNORECASE,
)
_VERIFICATION_SHELL_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("npm", "test"),
    ("npm", "run"),
    ("npx", "--no-install", "jest"),
    ("npx", "--no-install", "tsx"),
)
_UNSAFE_SHELL_CHARACTERS = frozenset(";&|><$()\\\r\n\x00")
# A job the watcher interrupted is a failure with a known cause, not an
# "incomplete" run that leaves the gate guessing.
_FAILED_JOB_STATUSES = frozenset({"failed", "timed_out", "cancelled"})


def _verification_command_is_valid(command: str) -> bool:
    raw = str(command or "")
    if any(character in raw for character in _UNSAFE_SHELL_CHARACTERS):
        return False
    cleaned = " ".join(raw.split()).strip()
    if not cleaned or _MALFORMED_VERIFY_COMMAND_RE.match(cleaned):
        return False
    try:
        argv = shlex.split(cleaned)
    except ValueError:
        return False
    if len(argv) < 2:
        return False
    lowered = tuple(part.lower() for part in argv)
    return any(lowered[: len(prefix)] == prefix for prefix in _VERIFICATION_SHELL_PREFIXES)


def _normalize_verification_command(command: str) -> str:
    cleaned = " ".join(str(command or "").split()).strip().rstrip(".")
    try:
        argv = shlex.split(cleaned)
    except ValueError:
        return cleaned
    if len(argv) >= 2 and argv[0].lower() == "npx" and argv[1].lower() in {"jest", "tsx"}:
        return " ".join(("npx", "--no-install", *argv[1:]))
    return cleaned


def select_verification_commands(commands: list[str], *, limit: int = 3) -> list[str]:
    """Normalize, validate, dedupe, and cap an arbitrary list of candidates.

    capability_routing.py has called this since 22bfded to filter a mix of
    freshly-extracted and single ad-hoc commands down to a safe, bounded set
    before attaching them to a routed task -- but the function was never
    added here, so every call crashed with an unconditional ImportError. It
    is the same normalize/validate pipeline extract_verification_commands
    already applies to fenced-block matches, generalized to any input list.
    """
    selected: list[str] = []
    seen: set[str] = set()
    for raw in commands or []:
        if len(selected) >= max(0, limit):
            break
        command = _normalize_verification_command(raw)
        if not _verification_command_is_valid(command) or command in seen:
            continue
        seen.add(command)
        selected.append(command)
    return selected


def extract_verification_commands(reply_text: str | None) -> list[str]:
    """Pull supported test commands from fenced, path-only, or inline text."""
    body = str(reply_text or "")
    commands: list[str] = []
    seen: set[str] = set()
    for match in _VERIFICATION_COMMAND_RE.finditer(body):
        parts = [part.strip() for part in re.split(r"\s&&\s", match.group(1)) if part.strip()]
        if not parts:
            continue
        valid_parts: list[str] = []
        for part in parts:
            command = _normalize_verification_command(part)
            if not _verification_command_is_valid(command):
                valid_parts = []
                break
            valid_parts.append(command)
        for command in valid_parts:
            if command not in seen:
                seen.add(command)
                commands.append(command)
    for match in _TEST_FILE_BACKTICK_RE.finditer(body):
        test_path = " ".join(match.group(1).split()).strip()
        command = f"npm test -- {test_path}"
        if _verification_command_is_valid(command) and command not in seen:
            seen.add(command)
            commands.append(command)
    for match in _GOAL_INLINE_COMMAND_RE.finditer(body):
        command = _normalize_verification_command(match.group(1))
        if _verification_command_is_valid(command) and command not in seen:
            seen.add(command)
            commands.append(command)
    return commands[:4]


_TEST_PATH_ARG_RE = re.compile(
    r"(?<![\w/.-])((?:[\w.-]+/)+[\w.-]+\.(?:test|spec)\.(?:ts|tsx|js|jsx|mjs|cjs))"
)
_PRUNED_SEARCH_DIRS = frozenset({"node_modules", ".git", ".venv", "dist", "build", "coverage"})
_MAX_SEARCH_DIRS = 4000


def _find_test_file_by_name(root: Path, filename: str) -> str | None:
    """Find a unique file with this basename, so a near-miss path is repairable."""
    matches: list[str] = []
    scanned = 0
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _PRUNED_SEARCH_DIRS]
        scanned += 1
        if scanned > _MAX_SEARCH_DIRS:
            break
        if filename in filenames:
            matches.append(str(Path(current, filename).relative_to(root)))
            if len(matches) > 1:
                return None
    return matches[0] if len(matches) == 1 else None


def resolve_verification_command(command: str, root: Path | None) -> tuple[str | None, str]:
    """Check a verify command's test paths before a run is spent on it.

    Returns ``(runnable_command, note)``. ``runnable_command`` is None when the
    command references a test file that does not exist and cannot be repaired —
    running it would only produce a "test path absent" failure.
    """
    cleaned = " ".join(str(command or "").split()).strip()
    if not cleaned:
        return None, "empty command"
    if root is None:
        return cleaned, ""

    resolved = cleaned
    notes: list[str] = []
    for referenced in dict.fromkeys(_TEST_PATH_ARG_RE.findall(cleaned)):
        if (root / referenced).is_file():
            continue
        suggestion = _find_test_file_by_name(root, Path(referenced).name)
        if suggestion is None:
            return None, f"test path `{referenced}` does not exist in the workspace"
        resolved = resolved.replace(referenced, suggestion)
        notes.append(f"repaired `{referenced}` → `{suggestion}`")
    return resolved, "; ".join(notes)


def source_run_from_verification_goal(goal: str) -> str | None:
    match = _SOURCE_RUN_RE.search(str(goal or ""))
    return match.group(1).strip() if match else None


def is_verification_task(task: dict[str, Any] | None) -> bool:
    if not isinstance(task, dict):
        return False
    return str(task.get("goal") or "").strip().lower().startswith("verification after")


def _split_compound_verification_commands(commands: list[str]) -> list[str]:
    """Split ``cmd1 && cmd2`` goal backticks into individually enqueueable jobs."""
    expanded: list[str] = []
    seen: set[str] = set()
    for command in commands:
        for part in re.split(r"\s&&\s", str(command or "")):
            normalized = _normalize_verification_command(part.strip())
            if not normalized or normalized in seen:
                continue
            if not _verification_command_is_valid(normalized):
                continue
            seen.add(normalized)
            expanded.append(normalized)
    return expanded


def verification_commands_for_task(task: dict[str, Any] | None) -> list[str]:
    if not isinstance(task, dict):
        return []
    blob = "\n".join(
        str(task.get(key) or "").strip()
        for key in ("goal", "acceptance_criteria")
        if str(task.get(key) or "").strip()
    )
    return _split_compound_verification_commands(extract_verification_commands(blob))


def verification_approved_command_prefixes() -> tuple[tuple[str, ...], ...]:
    return _VERIFICATION_SHELL_PREFIXES


def resolve_verification_baseline(
    *,
    workspace_id: str,
    task: dict[str, Any],
    bound_project_root: Path | None = None,
) -> tuple[str | None, str | None]:
    """Resolve the implementation commit/ref that a verification shift must test."""
    from app.safe_improvement.isolated_executor import _resolve_git_ref_commit
    from app.terminal.workspace_roots import resolve_workspace_root
    from app.workspace_delivery import store as delivery_store

    source_run = source_run_from_verification_goal(str(task.get("goal") or ""))
    if not source_run:
        return None, None
    try:
        bound = bound_project_root or resolve_workspace_root(workspace_id)
    except Exception:  # noqa: BLE001
        bound = None

    visited: set[str] = set()
    current = source_run
    for _ in range(6):
        if not current or current in visited:
            break
        visited.add(current)
        delivery = delivery_store.get_delivery_by_run(current)
        if isinstance(delivery, dict):
            commit_sha = str(delivery.get("commit_sha") or "").strip()
            worker_branch = str(delivery.get("worker_branch") or "").strip()
            if commit_sha:
                return commit_sha, worker_branch or f"worker/{current}"
            if worker_branch and bound is not None:
                resolved = _resolve_git_ref_commit(bound, worker_branch)
                if resolved:
                    return resolved, worker_branch

        worker_branch = f"worker/{current}"
        if bound is not None:
            resolved = _resolve_git_ref_commit(bound, worker_branch)
            if resolved:
                return resolved, worker_branch
        try:
            from app.runs.service import get_run

            run = get_run(current)
        except Exception:  # noqa: BLE001
            run = None
        task_id = str((run or {}).get("task_id") or "").strip()
        prior_task = task_store.get_task(task_id) if task_id else None
        if prior_task and is_verification_task(prior_task):
            parent = source_run_from_verification_goal(str(prior_task.get("goal") or ""))
            if parent and parent != current:
                current = parent
                continue
        break

    return None, None


def verification_terminal_jobs_for_run(
    workspace_id: str,
    run_id: str,
) -> list[dict[str, Any]]:
    from app.terminal.agent_jobs import list_agent_terminal_jobs

    clean_run = str(run_id or "").strip()
    clean_workspace = str(workspace_id or "").strip()
    if not clean_run or not clean_workspace:
        return []
    return [
        job
        for job in list_agent_terminal_jobs(clean_workspace, limit=100)
        if str(job.get("run_id") or "") == clean_run
    ]


def job_passed(job: dict[str, Any]) -> bool:
    if str(job.get("status") or "").strip().lower() != "completed":
        return False
    exit_code = job.get("exit_code")
    return exit_code is not None and int(exit_code) == 0


def job_failed(job: dict[str, Any]) -> bool:
    status = str(job.get("status") or "").strip().lower()
    if status in _FAILED_JOB_STATUSES:
        return True
    exit_code = job.get("exit_code")
    return status == "completed" and exit_code is not None and int(exit_code) != 0


def describe_failed_jobs(jobs: list[dict[str, Any]]) -> str:
    """Name what actually broke so the operator card is actionable."""
    details: list[str] = []
    for job in jobs[:3]:
        command = str(job.get("command") or job.get("job_id") or "job").strip()
        status = str(job.get("status") or "").strip().lower()
        reason = str(job.get("failure_reason") or "").strip()
        if reason:
            outcome = reason
        elif status == "completed":
            outcome = f"exit {job.get('exit_code')}"
        else:
            outcome = status or "unknown"
        details.append(f"`{command[:80]}` → {outcome}")
    return "; ".join(details)


def build_verification_acceptance_evaluation(
    *, run_id: str, task: dict[str, Any]
) -> dict[str, Any]:
    """Build Gate 6 evidence from terminal receipts rather than source diffs."""
    from app.persistence import run_store
    from app.runs.service import get_run
    from app.workspace_agents.verifier_checks import VERIFIER_IDENTITY

    commands = verification_commands_for_task(task)
    jobs = verification_terminal_jobs_for_run(str(task.get("workspace_id") or ""), run_id)
    run = get_run(run_id)
    history = run_store.list_history(str(run.get("history_ref") or ""))
    enqueued = sum(
        1
        for entry in history
        if isinstance(entry, dict)
        and str((entry.get("receipt") or {}).get("type") or "")
        == "verification_terminal_enqueued"
    )
    failed = [job for job in jobs if job_failed(job)]
    passed = [job for job in jobs if job_passed(job)]
    required = min(len(commands), 3) if commands else max(1, enqueued or len(passed))
    checks = [
        {
            "name": "verification_terminal_job",
            "passed": True,
            "detail": str(job.get("command") or job.get("job_id") or "terminal job"),
        }
        for job in passed
    ]
    if failed:
        summary = (
            f"acceptance=fail · verification jobs failed={len(failed)} ok={len(passed)} · "
            f"{describe_failed_jobs(failed)}"
        )
        passed_gate = False
    elif len(passed) >= required and required > 0:
        summary = f"acceptance=pass · verification jobs={len(passed)}/{required}"
        passed_gate = True
    elif not jobs and enqueued == 0:
        summary = "acceptance=fail · no verification terminal jobs recorded"
        checks = []
        passed_gate = False
    else:
        summary = f"acceptance=fail · verification jobs incomplete ok={len(passed)}/{required}"
        passed_gate = False
    return {
        "passed": passed_gate,
        "summary": summary,
        "checks": checks,
        "actor": VERIFIER_IDENTITY,
    }


def complete_verification_no_change_delivery(
    *,
    run_id: str,
    task: dict[str, Any],
    fail_worker_run: Callable[[str], dict[str, Any] | None],
) -> dict[str, Any] | None:
    from app.runs.service import RunLifecycleError, append_run_execution_receipt, complete_run
    from app.workspace_agents.verifier_contract import record_acceptance_evaluation

    evaluation = build_verification_acceptance_evaluation(run_id=run_id, task=task)
    if not evaluation.get("passed"):
        return fail_worker_run(
            "Workspace delivery blocked: verification jobs did not pass "
            f"({evaluation.get('summary') or 'missing terminal receipts'})"
        )
    record_acceptance_evaluation(run_id, evaluation)
    try:
        finalized = complete_run(run_id)
        append_run_execution_receipt(
            run_id,
            receipt_type="worker_delivery_verification_receipt",
            actor="workspace_scheduler",
            receipt_summary=(
                "Workspace delivery completed: verification shift required "
                "terminal job receipts; no publishable code changes."
            ),
        )
        return finalized
    except RunLifecycleError as exc:
        logger.exception("complete_run after verification delivery failed for %s", run_id)
        return fail_worker_run(f"Verification delivery succeeded but complete_run failed: {exc}")


def verification_worker_prompt_clause(*, workspace_id: str, task: dict[str, Any]) -> str:
    if not is_verification_task(task):
        return ""
    commands = verification_commands_for_task(task)
    workspace = workspace_id.strip()
    wrapped = (
        "; ".join(
            f"`axon-agent-terminal-job --workspace {workspace} -- {command}`"
            for command in commands[:3]
        )
        if commands
        else f"`axon-agent-terminal-job --workspace {workspace} -- <verify-command>`"
    )
    return (
        " VERIFICATION SHIFT: run the scoped verify commands first — in a sandbox "
        "disposable checkout you may run approved `npm test` / `npx --no-install jest` "
        "directly in Shell when node_modules is present; otherwise use "
        f"{wrapped}. Attach stdout/stderr receipts before static review. "
        "Do not claim tests passed without command output."
    )


__all__ = [
    "build_verification_acceptance_evaluation",
    "complete_verification_no_change_delivery",
    "describe_failed_jobs",
    "extract_verification_commands",
    "is_verification_task",
    "job_failed",
    "job_passed",
    "resolve_verification_baseline",
    "resolve_verification_command",
    "source_run_from_verification_goal",
    "verification_approved_command_prefixes",
    "verification_commands_for_task",
    "verification_terminal_jobs_for_run",
    "verification_worker_prompt_clause",
]
