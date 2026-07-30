"""Confirm and clear stale / useless CI remediation alerts.

VAXON and the worker scheduler use this after a Fast Gate (or other bound
workflow) is confirmed green again, or when a signal is a known drill /
superseded head.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any, Callable

from app.adapters.watch_client import reset_watch_inbox_cache
from app.ci_remediation import store as ci_store

logger = logging.getLogger(__name__)

BranchHealth = dict[str, str]
BranchHealthFetcher = Callable[[str, str], BranchHealth | None]


def parse_dedupe_parts(dedupe_key: str) -> dict[str, str]:
    """Parse ``ci:owner/repo:workflow:branch:sha`` (branch may contain colons)."""
    raw = str(dedupe_key or "").strip()
    if not raw.startswith("ci:"):
        return {}
    body = raw[3:]
    parts = body.split(":")
    if len(parts) < 4:
        return {}
    repo = parts[0]
    workflow = parts[1]
    head_sha = parts[-1]
    head_branch = ":".join(parts[2:-1])
    return {
        "repo": repo,
        "workflow_name": workflow,
        "head_branch": head_branch,
        "head_sha": head_sha,
    }


def is_drill_branch(head_branch: str) -> bool:
    branch = str(head_branch or "").strip().lower()
    return branch.startswith("drill/") or "/drill/" in branch or branch.startswith("drill-")


def classify_stale_reason(
    signal: dict[str, Any],
    *,
    branch_health: BranchHealth | None,
) -> str | None:
    """Return a resolve reason when the signal is confirmed stale/useless."""
    meta = signal.get("meta") if isinstance(signal.get("meta"), dict) else {}
    head_branch = str(meta.get("head_branch") or "").strip()
    parts = parse_dedupe_parts(str(signal.get("dedupe_key") or ""))
    if not head_branch:
        head_branch = parts.get("head_branch") or ""
    signal_sha = parts.get("head_sha") or ""

    title = str(signal.get("title") or "").lower()
    summary = str(signal.get("summary") or "").lower()
    if is_drill_branch(head_branch) or "drill/" in title or "drill:" in summary:
        return "stale_drill"

    if not branch_health:
        return None
    conclusion = str(branch_health.get("conclusion") or "").strip().lower()
    latest_sha = str(branch_health.get("head_sha") or "").strip().lower()
    if conclusion != "success":
        return None
    if not latest_sha:
        return "stale_superseded_by_green"
    if signal_sha and signal_sha.lower() == latest_sha:
        return "stale_recovered_green"
    return "stale_superseded_by_green"


def fetch_branch_health_via_gh(
    workflow_name: str,
    head_branch: str,
    *,
    repo: str = "axon-control-ops/axon-watch",
) -> BranchHealth | None:
    """Confirm latest workflow conclusion for a branch via ``gh`` (fail-open)."""
    workflow = str(workflow_name or "").strip()
    branch = str(head_branch or "").strip()
    if not workflow or not branch or is_drill_branch(branch):
        return None
    try:
        completed = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--repo",
                repo,
                "--workflow",
                workflow,
                "--branch",
                branch,
                "--limit",
                "1",
                "--json",
                "conclusion,headSha,databaseId,status",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.info("ci stale sweep gh lookup skipped: %s", exc)
        return None
    if completed.returncode != 0:
        return None
    try:
        rows = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    if not isinstance(row, dict):
        return None
    return {
        "conclusion": str(row.get("conclusion") or "").strip().lower(),
        "head_sha": str(row.get("headSha") or "").strip(),
        "run_id": str(row.get("databaseId") or "").strip(),
        "status": str(row.get("status") or "").strip().lower(),
    }


def resolve_open_for_branch_success(
    *,
    workflow_name: str,
    head_branch: str,
    head_sha: str = "",
    reason: str = "stale_superseded_by_green",
) -> list[dict[str, Any]]:
    """Resolve open failure alerts for a workflow/branch after a confirmed green run."""
    workflow = str(workflow_name or "").strip().lower()
    branch = str(head_branch or "").strip()
    want_sha = str(head_sha or "").strip().lower()
    if not workflow or not branch:
        return []
    resolved: list[dict[str, Any]] = []
    for signal in ci_store.list_open_signals():
        meta = signal.get("meta") if isinstance(signal.get("meta"), dict) else {}
        signal_workflow = str(meta.get("workflow_name") or "").strip().lower()
        signal_branch = str(meta.get("head_branch") or "").strip()
        parts = parse_dedupe_parts(str(signal.get("dedupe_key") or ""))
        if not signal_branch:
            signal_branch = parts.get("head_branch") or ""
        if not signal_workflow:
            signal_workflow = str(parts.get("workflow_name") or "").strip().lower()
        if signal_workflow != workflow or signal_branch != branch:
            continue
        signal_sha = str(parts.get("head_sha") or "").strip().lower()
        # Keep a failure for the same head unless this exact sha just went green.
        if want_sha and signal_sha and signal_sha == want_sha:
            row = ci_store.resolve_signal(
                str(signal.get("signal_id") or ""),
                reason="stale_recovered_green",
            )
        elif want_sha and signal_sha and signal_sha != want_sha:
            row = ci_store.resolve_signal(
                str(signal.get("signal_id") or ""),
                reason=reason,
            )
        else:
            row = ci_store.resolve_signal(
                str(signal.get("signal_id") or ""),
                reason=reason,
            )
        if row is not None:
            resolved.append(row)
            dedupe = str(signal.get("dedupe_key") or "").strip()
            if dedupe:
                ci_store.set_event_status(dedupe, "resolved")
    if resolved:
        reset_watch_inbox_cache()
    return resolved


def sweep_stale_ci_signals(
    *,
    include_drills: bool = True,
    confirm_with_gh: bool = True,
    branch_health_fetcher: BranchHealthFetcher | None = None,
    max_resolve: int = 40,
) -> dict[str, Any]:
    """Scan open CI alerts; resolve only after stale/useless confirmation."""
    fetcher = branch_health_fetcher
    if fetcher is None and confirm_with_gh:
        fetcher = lambda workflow, branch: fetch_branch_health_via_gh(workflow, branch)

    health_cache: dict[tuple[str, str], BranchHealth | None] = {}
    resolved: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for signal in ci_store.list_open_signals():
        if len(resolved) >= max(1, int(max_resolve)):
            break
        meta = signal.get("meta") if isinstance(signal.get("meta"), dict) else {}
        workflow = str(meta.get("workflow_name") or "Axon-X Fast Gate").strip()
        branch = str(meta.get("head_branch") or "").strip()
        parts = parse_dedupe_parts(str(signal.get("dedupe_key") or ""))
        if not branch:
            branch = parts.get("head_branch") or ""
        if not workflow and parts.get("workflow_name"):
            workflow = parts["workflow_name"]

        health: BranchHealth | None = None
        if include_drills and is_drill_branch(branch):
            health = None
        elif fetcher is not None and workflow and branch:
            key = (workflow.lower(), branch)
            if key not in health_cache:
                try:
                    health_cache[key] = fetcher(workflow, branch)
                except Exception:  # noqa: BLE001 — sweep must stay fail-open
                    logger.exception("branch health fetch failed for %s %s", workflow, branch)
                    health_cache[key] = None
            health = health_cache[key]

        reason = classify_stale_reason(signal, branch_health=health)
        if reason is None:
            skipped.append(
                {
                    "signal_id": str(signal.get("signal_id") or ""),
                    "reason": "still_active_or_unconfirmed",
                }
            )
            continue
        if reason == "stale_drill" and not include_drills:
            skipped.append(
                {
                    "signal_id": str(signal.get("signal_id") or ""),
                    "reason": "drill_skipped",
                }
            )
            continue
        row = ci_store.resolve_signal(str(signal.get("signal_id") or ""), reason=reason)
        if row is None:
            continue
        resolved.append(row)
        dedupe = str(signal.get("dedupe_key") or "").strip()
        if dedupe:
            ci_store.set_event_status(dedupe, "resolved")

    if resolved:
        reset_watch_inbox_cache()
    return {
        "work_source": "ci_stale_signal_sweep",
        "resolved_count": len(resolved),
        "resolved_signal_ids": [str(r.get("signal_id") or "") for r in resolved],
        "skipped": skipped,
    }
