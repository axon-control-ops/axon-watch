"""Pre-dispatch scope guards for continuous worker runs."""

from __future__ import annotations

from typing import Any


def implementation_scope_block(
    *, task: dict[str, Any] | None, execution_policy: Any
) -> str | None:
    """Reason an implementation task cannot possibly write its own targets.

    Runs were burning a full shift and then failing at the completion gate with
    "produced no changed files", because the agent had no write scope covering
    the files the task expected. Catch that up front so the operator gets a
    routing error in seconds instead of a mystery no-op twenty minutes later.

    Deliberately narrow: only implementation tasks, and only when *nothing* the
    task expects is writable. Analysis, review and receipt-backed ops tasks are
    untouched, and a partial overlap still runs.
    """
    from app.workspace_agents.completion_gate import (
        expected_files_for_task,
        implementation_requested,
    )

    if not implementation_requested(task):
        return None

    write_paths = tuple(getattr(execution_policy, "write_paths", ()) or ())
    if not write_paths:
        return (
            "implementation task dispatched with no writable scope "
            f"(access={getattr(execution_policy, 'execution_access', 'unknown')}); "
            "check the workspace project.axon.yaml and the task's allowed_paths"
        )

    expected = [str(item).strip().lstrip("./") for item in (expected_files_for_task(task) or [])]
    expected = [item for item in expected if item]
    if not expected:
        return None

    def covered(candidate: str) -> bool:
        return any(
            candidate == root or candidate.startswith(f"{root.rstrip('/')}/")
            for root in (str(w).strip().lstrip("./") for w in write_paths)
        )

    if any(covered(item) for item in expected):
        return None
    return (
        "implementation task expects files outside the writable scope — "
        f"expected={', '.join(expected[:6])} vs writes={', '.join(map(str, write_paths))}; "
        "route this task to a role that owns those paths, or widen the task scope"
    )
