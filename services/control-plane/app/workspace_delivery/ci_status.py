"""Apply GitHub workflow_run conclusions onto workspace delivery records."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.workspace_delivery import store as delivery_store
from app.workspace_delivery.config import get_workspace_delivery_policy
from app.workspace_delivery.receipts import emit_delivery_receipt

logger = logging.getLogger(__name__)


def _safe_emit(
    run_id: str,
    *,
    workspace_id: str,
    stage: str,
    summary: str,
    workflow_name: str = "",
    success: bool = True,
    refs: dict[str, Any] | None = None,
) -> None:
    if not run_id:
        return
    try:
        emit_delivery_receipt(
            run_id,
            stage=stage,
            summary=summary,
            success=success,
            refs=refs,
        )
    except Exception:  # noqa: BLE001 — CI status tracking must not fail closed on missing runs
        logger.exception("delivery receipt emit failed for %s stage=%s", run_id, stage)
    _post_delivery_update_to_agent_thread(
        workspace_id=workspace_id,
        run_id=run_id,
        stage=stage,
        workflow_name=workflow_name,
        refs=refs,
    )
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=f"workspace_delivery_{run_id}_{stage}")
    except Exception:  # noqa: BLE001 — receipt durability is the primary outcome
        logger.exception("delivery live update failed for %s stage=%s", run_id, stage)
    if stage in {"ci_green", "ci_red", "escalated", "blocked"}:
        try:
            delivery = delivery_store.get_delivery_by_run(run_id)
            task_id = str((delivery or {}).get("task_id") or "").strip()
            if task_id:
                from app.workspace_missions.service import kick_missions_for_task

                kick_missions_for_task(task_id)
        except Exception:  # noqa: BLE001 — mission projection must not break CI ingestion
            logger.exception("mission delivery refresh failed for %s", run_id)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _delivery_update_copy(*, stage: str, workflow_name: str, refs: dict[str, Any] | None) -> str:
    workflow = workflow_name.strip() or "CI"
    if stage == "ci_green":
        headline = f"CI update — {workflow} is green."
    elif stage == "ci_red":
        headline = f"CI update — {workflow} failed; I am preparing the next repair attempt."
    elif stage == "escalated":
        headline = f"CI update — {workflow} is blocked after its retry budget."
    else:
        headline = f"CI update — {workflow} is running."
    values = refs or {}
    lines = [headline]
    draft_pr = str(values.get("draft_pr_url") or "").strip()
    ci_url = str(values.get("ci_run_url") or "").strip()
    if draft_pr:
        lines.append(f"Draft PR: {draft_pr}")
    if ci_url:
        lines.append(f"Watch CI: {ci_url}")
    return "\n".join(lines)


def _post_delivery_update_to_agent_thread(
    *,
    workspace_id: str,
    run_id: str,
    stage: str,
    workflow_name: str,
    refs: dict[str, Any] | None,
) -> None:
    """Append the CI state to the owning agent's existing IDE thread once."""
    try:
        from app.persistence import chat_store

        thread = None
        history: list[dict[str, Any]] = []
        for candidate in chat_store.list_threads_for_workspace(workspace_id, thread_kind="ide", limit=50):
            candidate_history = chat_store.list_thread_messages(str(candidate["thread_id"]))
            if any(str(message.get("run_id") or "").strip() == run_id for message in candidate_history):
                thread = candidate
                history = candidate_history
                break
        if thread is None:
            return
        content = _delivery_update_copy(stage=stage, workflow_name=workflow_name, refs=refs)
        if any(
            str(message.get("run_id") or "").strip() == run_id
            and str(message.get("role") or "") == "agent"
            and str(message.get("content") or "").strip() == content
            for message in history[-30:]
        ):
            return
        chat_store.save_message(
            {
                "message_id": f"message_agent_{uuid4().hex}",
                "thread_id": str(thread["thread_id"]),
                "workspace_id": workspace_id,
                "run_id": run_id,
                "role": "agent",
                "content": content,
                "created_at": _utc_now_iso(),
            }
        )
    except Exception:  # noqa: BLE001 — delivery persistence must never fail closed on chat UX
        logger.exception("delivery thread update failed for %s stage=%s", run_id, stage)


def _queue_lead_after_ci_green(
    *,
    workspace_id: str,
    run_id: str,
    task_id: str | None,
    workflow_name: str,
    head_branch: str,
    html_url: str,
) -> None:
    """Give the workspace Lead the verified post-green handoff automatically."""
    try:
        from app.workspace_agents.lead_takeover_followup import enqueue_lead_follow_up_task

        follow_up = enqueue_lead_follow_up_task(
            workspace_id=workspace_id,
            employee_name="CI",
            employee_role="watcher",
            lead_next=(
                f"{workflow_name or 'CI'} is green on {head_branch or 'the delivery branch'}. "
                "Verify the PR/merge state and advance the next safe plan step."
            ),
            run_id=run_id,
            phase="completed",
            task_id=task_id,
        )
        if follow_up is not None:
            logger.info(
                "queued Lead CI-green follow-up workspace=%s delivery_run=%s task=%s",
                workspace_id,
                run_id,
                follow_up.get("task_id"),
            )
    except Exception:  # noqa: BLE001 — delivery state must not depend on handoff UX
        logger.exception("CI-green Lead handoff failed for %s", run_id)


def classify_workflow_status(payload: dict[str, Any]) -> dict[str, str] | None:
    """Normalize success / failure / in-progress workflow_run events."""
    run = payload.get("workflow_run")
    if not isinstance(run, dict):
        return None
    action = str(payload.get("action") or "").strip().lower()
    status = str(run.get("status") or "").strip().lower()
    conclusion = str(run.get("conclusion") or "").strip().lower()

    repo = payload.get("repository")
    owner = ""
    repo_name = ""
    if isinstance(repo, dict):
        repo_name = str(repo.get("name") or "").strip()
        owner_obj = repo.get("owner")
        if isinstance(owner_obj, dict):
            owner = str(owner_obj.get("login") or "").strip()
        full_name = str(repo.get("full_name") or "").strip()
        if not owner and "/" in full_name:
            owner, repo_name = full_name.split("/", 1)

    workflow_name = str(run.get("name") or "").strip()
    head_branch = str(run.get("head_branch") or "").strip()
    head_sha = str(run.get("head_sha") or "").strip()
    run_id = str(run.get("id") or "").strip()
    html_url = str(run.get("html_url") or "").strip()
    if not owner or not repo_name or not workflow_name or not run_id:
        return None

    kind = ""
    if status in {"queued", "in_progress", "waiting", "requested", "pending"}:
        kind = "pending"
    elif action == "completed" or status == "completed":
        if conclusion == "success":
            kind = "success"
        elif conclusion == "failure":
            kind = "failure"
        else:
            kind = conclusion or "completed"
    if not kind:
        return None

    return {
        "kind": kind,
        "github_owner": owner,
        "github_repo": repo_name,
        "workflow_name": workflow_name,
        "head_branch": head_branch,
        "head_sha": head_sha,
        "run_id": run_id,
        "html_url": html_url,
        "conclusion": conclusion or kind,
    }


def apply_ci_status_to_delivery(
    *,
    workspace_id: str,
    head_branch: str,
    head_sha: str,
    kind: str,
    html_url: str = "",
    conclusion: str = "",
    workflow_name: str = "",
) -> dict[str, Any] | None:
    delivery = delivery_store.find_delivery_by_branch_sha(
        workspace_id=workspace_id,
        worker_branch=head_branch,
        commit_sha=head_sha or None,
    )
    if delivery is None and head_branch:
        delivery = delivery_store.find_delivery_by_branch_sha(
            workspace_id=workspace_id,
            worker_branch=head_branch,
        )
    if delivery is None:
        return None

    run_id = str(delivery.get("run_id") or "").strip()
    delivery_id = str(delivery.get("delivery_id") or "").strip()
    attempt = int(delivery.get("attempt") or 0)
    budget = int(delivery.get("attempt_budget") or 3)
    policy = get_workspace_delivery_policy(workspace_id)
    if policy is not None and not int(delivery.get("attempt_budget") or 0):
        budget = int(policy.attempt_budget)

    if kind == "pending":
        updated = delivery_store.update_delivery(
            delivery_id,
            stage="ci_pending",
            ci_run_url=html_url or None,
            ci_conclusion=conclusion or "pending",
            clear_blocker=True,
        )
        _safe_emit(
            run_id,
            workspace_id=workspace_id,
            stage="ci_pending",
            summary=f"CI pending for {workflow_name or 'workflow'}",
            workflow_name=workflow_name,
            refs={
                "ci_run_url": html_url,
                "worker_branch": head_branch,
                "commit_sha": head_sha,
            },
        )
        return updated

    if kind == "success":
        updated = delivery_store.update_delivery(
            delivery_id,
            stage="ci_green",
            ci_run_url=html_url or None,
            ci_conclusion="success",
            clear_blocker=True,
        )
        _safe_emit(
            run_id,
            workspace_id=workspace_id,
            stage="ci_green",
            summary=f"CI green for {workflow_name or 'workflow'}",
            workflow_name=workflow_name,
            refs={
                "ci_run_url": html_url,
                "worker_branch": head_branch,
                "commit_sha": head_sha,
                "draft_pr_url": delivery.get("draft_pr_url"),
            },
        )
        _queue_lead_after_ci_green(
            workspace_id=workspace_id,
            run_id=run_id,
            task_id=str(delivery.get("task_id") or "").strip() or None,
            workflow_name=workflow_name,
            head_branch=head_branch,
            html_url=html_url,
        )
        return updated

    if kind != "failure":
        return delivery

    next_attempt = attempt + 1
    if next_attempt >= budget:
        blocker = (
            f"CI failed after {next_attempt}/{budget} attempts"
            + (f" ({workflow_name})" if workflow_name else "")
        )
        updated = delivery_store.update_delivery(
            delivery_id,
            stage="escalated",
            attempt=next_attempt,
            ci_run_url=html_url or None,
            ci_conclusion="failure",
            blocker=blocker,
            refs={"attempt": next_attempt, "blocker": blocker},
        )
        _safe_emit(
            run_id,
            workspace_id=workspace_id,
            stage="escalated",
            summary=blocker,
            workflow_name=workflow_name,
            success=False,
            refs={
                "ci_run_url": html_url,
                "attempt": next_attempt,
                "blocker": blocker,
                "worker_branch": head_branch,
                "commit_sha": head_sha,
            },
        )
        return updated

    updated = delivery_store.update_delivery(
        delivery_id,
        stage="ci_red",
        attempt=next_attempt,
        ci_run_url=html_url or None,
        ci_conclusion="failure",
        refs={"attempt": next_attempt},
    )
    _safe_emit(
        run_id,
        workspace_id=workspace_id,
        stage="ci_red",
        summary=f"CI red attempt {next_attempt}/{budget}",
        workflow_name=workflow_name,
        success=False,
        refs={
            "ci_run_url": html_url,
            "attempt": next_attempt,
            "worker_branch": head_branch,
            "commit_sha": head_sha,
        },
    )
    return updated
