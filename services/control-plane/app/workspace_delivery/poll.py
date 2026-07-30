"""Bounded poll fallback when GitHub workflow webhooks are delayed."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from typing import Any

from app.workspace_delivery import store as delivery_store
from app.workspace_delivery.ci_status import apply_ci_status_to_delivery
from app.workspace_delivery.config import get_workspace_delivery_policy
from app.workspace_delivery.gh_cli import resolve_gh_cli

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def poll_pending_deliveries(*, limit: int = 20) -> list[dict[str, Any]]:
    """Mark timed-out ci_pending deliveries as blocked; best-effort gh status when available."""
    updated: list[dict[str, Any]] = []
    # Lightweight scan via latest per workspace is insufficient; query by stage.
    # store has no list_by_stage — use sqlite through find via workspace policies.
    from app.workspace_delivery.config import load_workspace_delivery_policies

    for workspace_id, policy in load_workspace_delivery_policies().items():
        if not policy.enabled:
            continue
        delivery = delivery_store.latest_workspace_delivery(workspace_id)
        if delivery is None:
            continue
        if str(delivery.get("stage") or "") != "ci_pending":
            continue
        created = _parse_iso(str(delivery.get("updated_at") or delivery.get("created_at") or ""))
        if created is None:
            continue
        age = (_utc_now() - created.astimezone(timezone.utc)).total_seconds()
        if age < float(policy.ci_poll_timeout_seconds):
            # Optional live check with gh when still inside the window.
            branch = str(delivery.get("worker_branch") or "").strip()
            sha = str(delivery.get("commit_sha") or "").strip()
            if branch and shutil_which_gh() and policy.workflow_names:
                live = _gh_latest_conclusion(
                    workflow=policy.workflow_names[0],
                    branch=branch,
                    sha=sha,
                )
                if live:
                    record = apply_ci_status_to_delivery(
                        workspace_id=workspace_id,
                        head_branch=branch,
                        head_sha=sha,
                        kind=live["kind"],
                        html_url=live.get("html_url") or "",
                        conclusion=live.get("conclusion") or "",
                        workflow_name=policy.workflow_names[0],
                    )
                    if record:
                        updated.append(record)
            continue

        blocker = (
            f"CI pending timed out after {policy.ci_poll_timeout_seconds}s "
            f"without a webhook conclusion"
        )
        record = delivery_store.update_delivery(
            str(delivery["delivery_id"]),
            stage="blocked",
            blocker=blocker,
            refs={"blocker": blocker},
        )
        if record:
            updated.append(record)
        if len(updated) >= limit:
            break
    return updated


def shutil_which_gh() -> bool:
    return resolve_gh_cli() is not None


def _gh_latest_conclusion(
    *,
    workflow: str,
    branch: str,
    sha: str,
) -> dict[str, str] | None:
    gh_bin = resolve_gh_cli()
    if not gh_bin:
        return None
    try:
        completed = subprocess.run(
            [
                gh_bin,
                "run",
                "list",
                "--workflow",
                workflow,
                "--branch",
                branch,
                "--limit",
                "5",
                "--json",
                "databaseId,status,conclusion,url,headSha",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    try:
        import json

        rows = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list):
        return None
    match = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if sha and str(row.get("headSha") or "").startswith(sha[:7]):
            match = row
            break
    if match is None and rows:
        match = rows[0] if isinstance(rows[0], dict) else None
    if not isinstance(match, dict):
        return None
    status = str(match.get("status") or "").strip().lower()
    conclusion = str(match.get("conclusion") or "").strip().lower()
    url = str(match.get("url") or "").strip()
    if status != "completed":
        return {"kind": "pending", "conclusion": status or "pending", "html_url": url}
    if conclusion == "success":
        return {"kind": "success", "conclusion": "success", "html_url": url}
    if conclusion == "failure":
        return {"kind": "failure", "conclusion": "failure", "html_url": url}
    return None
