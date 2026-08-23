"""Detect a failing CI branch that is stale on CI-infra paths relative to its base.

Repair workers are given a natural-language goal and left to rediscover the
cause of a failure themselves. One recurring, budget-burning case: a PR
branch predates a fix that already landed on its base branch (a workflow
file, lint config, or a filename-checker script) — the base is green on this
same workflow, but the branch's own copy of that file is still broken. No
amount of editing SQL/app content on the branch will make the check pass;
the fix is to merge the base branch in first.

This module gives the repair goal a concrete, checkable hint for that case
instead of leaving the worker to burn its whole ``attempt_budget`` finding it
by trial and error — exactly what happened on ``worker/run_96147146e311``
(dashpro PR #39): the branch's ``db-lint.yml`` still used
``actions/setup-python@v5``, which fails on the Kali self-hosted runner,
while ``development`` had already moved to a system-Python venv.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Callable

logger = logging.getLogger(__name__)

GhRunner = Callable[[list[str]], str | None]

# Paths whose drift between base and head is a common false-content-fix trap:
# CI/lint infrastructure, not application logic.
DEFAULT_CI_INFRA_PATH_PREFIXES: tuple[str, ...] = (
    ".github/workflows/",
    ".github/actions/",
    ".sqlfluff",
    "scripts/check-migration-filenames.sh",
    "scripts/migration-filename-legacy-allowlist.txt",
    "scripts/workflow/",
)

_GH_TIMEOUT_SECONDS = 8


def _default_gh_runner(args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=_GH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.info("ci staleness gh lookup skipped: %s", exc)
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def pr_base_branch(runner: GhRunner, *, repo: str, head_branch: str) -> str | None:
    """Return the base branch of the open PR for ``head_branch``, if any."""
    if not repo or not head_branch:
        return None
    out = runner(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            head_branch,
            "--state",
            "open",
            "--json",
            "baseRefName",
            "--limit",
            "1",
        ]
    )
    if not out:
        return None
    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return None
    base = str(rows[0].get("baseRefName") or "").strip()
    return base or None


def base_branch_conclusion(
    runner: GhRunner, *, repo: str, workflow_name: str, base_branch: str
) -> dict[str, str] | None:
    """Latest completed conclusion of ``workflow_name`` on ``base_branch``."""
    if not repo or not workflow_name or not base_branch:
        return None
    out = runner(
        [
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            workflow_name,
            "--branch",
            base_branch,
            "--limit",
            "1",
            "--json",
            "conclusion,headSha,status",
        ]
    )
    if not out:
        return None
    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return None
    row = rows[0]
    return {
        "conclusion": str(row.get("conclusion") or "").strip().lower(),
        "head_sha": str(row.get("headSha") or "").strip(),
        "status": str(row.get("status") or "").strip().lower(),
    }


def drifted_ci_paths(
    runner: GhRunner,
    *,
    repo: str,
    base_branch: str,
    head_sha: str,
    path_prefixes: tuple[str, ...] = DEFAULT_CI_INFRA_PATH_PREFIXES,
) -> list[str]:
    """CI-infra paths present in ``base_branch`` but missing from ``head_sha``."""
    if not repo or not base_branch or not head_sha:
        return []
    out = runner(
        [
            "api",
            f"repos/{repo}/compare/{head_sha}...{base_branch}",
            "--jq",
            ".files[]?.filename",
        ]
    )
    if not out:
        return []
    changed = [line.strip() for line in out.splitlines() if line.strip()]
    return [p for p in changed if any(p.startswith(prefix) for prefix in path_prefixes)]


def stale_ci_infra_hint(
    *,
    repo: str,
    workflow_name: str,
    head_branch: str,
    head_sha: str,
    base_branch: str | None = None,
    gh_runner: GhRunner | None = None,
) -> str | None:
    """Return a repair-goal hint when base is green and head lacks base's CI-infra fixes.

    Fails open (returns ``None``) on any missing input, ``gh`` error, or when
    nothing looks stale — this must never be the reason a repair goal fails
    to build.
    """
    if not repo or not workflow_name or not head_branch or not head_sha:
        return None
    runner = gh_runner or _default_gh_runner
    try:
        resolved_base = base_branch or pr_base_branch(
            runner, repo=repo, head_branch=head_branch
        )
        if not resolved_base or resolved_base == head_branch:
            return None
        health = base_branch_conclusion(
            runner, repo=repo, workflow_name=workflow_name, base_branch=resolved_base
        )
        if not health or health.get("conclusion") != "success":
            return None
        drifted = drifted_ci_paths(
            runner, repo=repo, base_branch=resolved_base, head_sha=head_sha
        )
    except Exception:  # noqa: BLE001 — a hint must never break goal-building
        logger.exception("stale ci-infra hint failed for %s/%s", repo, head_branch)
        return None
    if not drifted:
        return None
    files = ", ".join(drifted[:5])
    more = f" (+{len(drifted) - 5} more)" if len(drifted) > 5 else ""
    return (
        f"{workflow_name} is green on `{resolved_base}` and this head is missing "
        f"{len(drifted)} CI-infra path change(s) already on it: {files}{more}. "
        f"Before editing SQL/app content, merge `{resolved_base}` into this branch "
        "(merge commit, fast-forward-safe push, never force-push) and re-run first — "
        "the failure is likely a stale workflow/lint config, not new content."
    )
